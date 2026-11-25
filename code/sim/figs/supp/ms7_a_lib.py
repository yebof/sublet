"""Helpers shared by the MS7 supplementary scripts of writer unit W-G4 A, figs/supp/sf_lag_v2.py (the causal-demand
runs) and figs/supp/sf_oos.py (the out-of-sample folds) (design/ms7/w_spec.md §4, unit W-G4; design/ms7/registration.md
§3; change C58). Not a figure script (no NAME): it reads nothing.

Contents:
  inputs        ``MissingInput`` (exit code 2, the file named) and ``read_json``, which reads a repository-relative
                result file through figs.inputs.Inputs after checking that it exists (a run output that is not yet
                copied in, design/ms7/registration.md, stops the build with exit code 2; figs/rebuild.py keeps the
                entry pending until then)
  reduced data  ``guard_reduced``: data from a reduced (smoke) run is never written into the versioned folders
                paper/supplement/figures/, paper/supplement/tables/ or code/sim/out/figs/ (stage 3's rule, review of
                W-G2: a reduced extract there would end the rebuild entry's pending state); ``main`` wraps
                figs.common.cli with that guard (before any file is written, on both the build and the
                --from-extract path) and the exit code 2 of a missing input
  panel (a)     the per-week (or per-cell) margins in two sub-panels on one x axis (``split_rows``,
                ``draw_margins``; fig4_v3's panel (b), whose marker-overlap check fig4_v2.marker_overlaps it uses):
                each series a black marker of SERIES_STYLES, dodged, a reference line at 0, and every column with a
                negative or missing value of a sub-panel's series shaded in that sub-panel; the two y labels at one x
                and on one baseline as printed (common.align_ylabels_x, align_baselines; C62)
  dot rows      ``draw_rows``: one row per policy named on the y axis (the first panel; the next one shares it), per
                row two series offset up and down, each its median (marker) and its min-max (a bar), thin grey
                separators between the groups of rows, a grey reference line; ``names_reserve`` keeps a gutter
                (NAMES_GUTTER_PT) between the widest name and the panel on its left
  keys          ``handles``: the legend entries of the series (black, as drawn); ``letter_keys`` (C62): a panel's key
                in one row on its letter's baseline, right of the letter, the axes lowered by KEY_ROOM_PT below the
                standard top so that the letters stay where style.panel_letters sets them in a figure without keys
                (fig4_v3's keys, set here as plain texts on the letter's baseline, so that the key and the letter
                share one baseline exactly); ``line_label`` a reference line's name above its axes, on the letters'
                baseline, in style.THEORY_LABEL_GREY; ``line_label_inside`` (C62 fix round) a rows panel's
                reference line named inside its axes at the line's top end (else its bottom end), clear of the data,
                the line stopping short of the name
  tables        ``longtable`` (ms5b_e7_lib.longtable's table with rules and blocks kept on one page set apart, e.g. a
                rule between groups of policies and the two lines of each policy together), ``med_rows`` (a two-row
                group: medians, then [min, max]), ``num``/``interval`` from figs.supp.ms5b_e7_lib, ``prose`` (a
                registry label inside a sentence); ``csv_entry``, ``csv_from_entry`` for the per-run data file of
                each experiment, kept in the extract as its lines (a data file of the supplement beside the tables,
                as e7v2_rc_runs.csv), its sha256 checked when the after hook writes it
"""
from __future__ import annotations

import csv
import hashlib
import io
import math
import statistics
import sys
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

import numpy as np
from matplotlib.font_manager import FontProperties
from matplotlib.lines import Line2D
from matplotlib.textpath import TextPath
from matplotlib.ticker import FixedLocator, MaxNLocator

from figs import common, style
from figs import fig4_v2 as v2
from figs.common import align_baselines, align_right_math, align_ylabels_x
from figs.inputs import Inputs
from figs.supp import ms5b_e7_lib as L

# ---------------------------------------------------------------------------------------------------------------
# inputs


class MissingInput(SystemExit):
    """A required input file is missing (exit code 2, the file named)."""


def read_json(inp: Inputs, name: str, run_inputs: Sequence[str], script: str) -> Any:
    """`name` (repository-relative) parsed as JSON through `inp`; MissingInput naming the file if it is absent."""
    p = inp.root / style.check_source(name)
    if not p.is_file():
        what = ("an MS7 run output (design/ms7/registration.md; copied in after the runs)" if name in run_inputs else
                "a versioned result file")
        raise MissingInput(f"[{script}] required input {name} is missing under {inp.root} ({what})")
    return inp.json(name)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------------------------------------------
# reduced data and the command line
def _versioned_dirs() -> tuple[Path, ...]:
    return (common.SUPP_PDF_DIR.resolve(), common.TABLES_DIR.resolve(), Path(style.DEFAULT_OUT_DIR).resolve(),
            (style.REPO / "paper").resolve())


def _inside(p: Path, top: Path) -> bool:
    return p == top or top in p.parents


def guard_reduced(script: str, data: Mapping) -> None:
    """SystemExit (a message, never a file written) if `data` comes from a reduced run (meta.reduced) and any output
    folder (the supplementary PDF folder, the extract folder, the tables folder) is a versioned one or lies in
    paper/."""
    if not (data.get("meta") or {}).get("reduced"):
        return
    outs = {"PDF": common.supp_pdf_dir(), "extract": style.output_dirs()[1], "tables": common.tables_dir()}
    bad = [f"{k} folder {p}" for k, p in outs.items()
           if any(_inside(Path(p).resolve(), d) for d in _versioned_dirs())]
    if bad:
        raise SystemExit(f"[{script}] the inputs are from a reduced run (meta.reduced): nothing is written into "
                         f"{', '.join(bad)}; set {style.ENV_PDF_DIR}, {style.ENV_OUT_DIR} (and "
                         f"{common.ENV_TABLES_DIR}) to scratch folders")


def main(script: str, build: Callable[[Inputs], dict], draw: Callable[[Mapping], Any], argv, *,
         after: Callable[[dict, dict], None], doc: str) -> dict:
    """figs.common.cli (supplementary, with the after hook) with guard_reduced on the built or read data before
    anything is written, and exit code 2 (the file named on stderr) for a missing input."""
    def build_checked(inp: Inputs) -> dict:
        data = build(inp)
        guard_reduced(script, data)
        return data

    def draw_checked(data: Mapping) -> Any:
        guard_reduced(script, data)
        return draw(data)

    try:
        return common.cli(script, build_checked, draw_checked, argv, supplementary=True, after=after, doc=doc)
    except MissingInput as err:
        print(err.code, file=sys.stderr)
        raise SystemExit(2) from None


# ---------------------------------------------------------------------------------------------------------------
# statistics
def describe(values: Sequence[float | None]) -> dict:
    """{n, n_missing, median, min, max} of the values that exist (statistics.median)."""
    v = [float(x) for x in values if x is not None]
    return {"n": len(v), "n_missing": sum(1 for x in values if x is None),
            "median": float(statistics.median(v)) if v else None, "min": min(v) if v else None,
            "max": max(v) if v else None}


def signs(values: Sequence[float | None]) -> dict:
    """describe() with the counts of values above, at and below 0."""
    v = [float(x) for x in values if x is not None]
    return {**describe(values), "n_pos": sum(1 for x in v if x > 0), "n_zero": sum(1 for x in v if x == 0),
            "n_neg": sum(1 for x in v if x < 0)}


# ---------------------------------------------------------------------------------------------------------------
# figure: series styles and legend
SERIES_COLOR = "#000000"
SERIES_STYLES = {   # black markers (no policy), distinct in (marker, fill); "a"/"b" the series of panel (a),
    "a": dict(marker="h", markerfacecolor=SERIES_COLOR, markersize=3.6),           # "c"/"d" those of the rows
    "b": dict(marker="s", markerfacecolor="white", markersize=3.0),
    "c": dict(marker="D", markerfacecolor=SERIES_COLOR, markersize=3.2),
    "d": dict(marker="o", markerfacecolor="white", markersize=3.4),
}
BAR_PT = style.UNCERTAINTY_PT
MAX_MARKER_OVERLAP = v2.MAX_MARKER_OVERLAP
DODGE = 0.25                    # (a): the first series this many columns left of its column, the second as far right
SUB_GAP_IN = 0.10               # (a): between the two sub-panels
PAD = 0.08                      # the data range this share beyond the data
ROW_OFFSET = 0.18               # rows: the first series this many rows above the row's center, the second as far below
ROW_PAD = 0.4                   # rows: the y range this many rows beyond the first and the last row's center (as built
#                                 at 9 pt: at 0.5 the names of twelve rows under a legend row were 10.26 pt apart)
SEPARATOR_PT = 0.4              # rows: the grey line between two groups of rows
NAMES_GUTTER_PT = 12.0          # rows: the widest name this far right of the panel on its left (C62: as built the
#                                 widest name ended 2 pt from (a)'s right spine and read as continuing its row)
# keys on the letters' baseline (C62; the legend row they replace took 0.21 in of the height)
KEY_GAP_PT = 3.0                # a key starts this far right of its panel letter's box (fig4_v3.KEY_X_GAP_PT)
KEY_MARK_GAP_PT = 2.0           # an entry's handle ends this far left of its label
KEY_COL_GAP_PT = style.TICK_PT  # between two entries (1.0 em, the legend's column spacing at TICK_PT)
KEY_BAR_PT = 9.0                # the bar of a handle with a bar (a median and its min-max)
KEY_AXES_GAP_PT = 3.0           # from a key's ink to the top of the axes below it (fig4_v3.KEY_AXES_GAP_PT)
LETTER_RISE_PT = 1.2            # style.panel_letters: the letter's baseline this far above its axes' top


def series_kwargs(s: str) -> dict:
    kw = dict(color=SERIES_COLOR, linestyle="none", markeredgecolor=SERIES_COLOR,
              markeredgewidth=style.MARKER_EDGE_PT, zorder=style.Z_DATA)
    kw.update(SERIES_STYLES[s])
    return kw


def handles(entries: Sequence[tuple[str, str, bool]]) -> list:
    """Legend entries (handle, label) for (series style, label, with a bar): a marker, or a marker on a short bar
    (a median with its min-max bar)."""
    out = []
    for s, label, bar in entries:
        kw = series_kwargs(s)
        if bar:
            kw.update(linestyle="-", linewidth=BAR_PT)
        out.append((Line2D([], [], **kw), label))
    return out


def _glyph_span_pt(text: str, size: float = style.TICK_PT) -> tuple[float, float]:
    """(bottom, top) of `text`'s glyphs relative to its baseline (pt) at `size` (TextPath; plain text)."""
    e = TextPath((0.0, 0.0), text, prop=FontProperties(size=size)).get_extents()
    return float(e.y0), float(e.y1)


KEY_MARK_RISE_PT = 0.5 * _glyph_span_pt("H")[1]      # a key's marker centered at half the cap height (2.5 pt)


def _marker_radius_pt(s: str) -> float:
    kw = SERIES_STYLES[s]
    return 0.5 * (float(kw["markersize"]) + style.MARKER_EDGE_PT)


def key_room_in(styles: Sequence[str]) -> float:
    """How much lower (in) than in a figure without keys the axes of a row with letter keys start, so that the keys'
    ink (the labels' descenders, the markers of `styles`) ends KEY_AXES_GAP_PT above them: style.panel_letters sets
    the letters' baseline LETTER_RISE_PT above the axes, and letter_keys sets the letters back to that height."""
    depth = max([-_glyph_span_pt("gjpqy")[0]] + [_marker_radius_pt(s) - KEY_MARK_RISE_PT for s in styles])
    return max(0.0, depth + KEY_AXES_GAP_PT - LETTER_RISE_PT) / style.BP_PER_IN


def letter_keys(fig, letters: Sequence, keys: Mapping[int, Sequence[tuple[str, str, bool]]], room_in: float) -> list:
    """Raise every panel letter by `room_in` (back to where style.panel_letters sets it above axes placed without the
    keys' room, key_room_in) and set the key of panel i (keys[i]: (series style, label, with a bar) per entry) in one
    row on its letter's baseline, KEY_GAP_PT right of the letter's box: per entry the series' marker (on a
    KEY_BAR_PT bar where it has one), centered KEY_MARK_RISE_PT above the baseline, then its label (TICK_PT, va
    'baseline'; a mathtext label moved onto the plain texts' baseline as printed, common.align_baselines). Returns
    the keys' artists (role 'key'); each label records its panel letter (_sublet_key_of)."""
    W, H = (float(v) for v in fig.get_size_inches())
    for t in letters:
        x, y = t.get_position()
        t.set_position((x, y + room_in / H))
    r = fig.canvas.get_renderer()
    pt = 1.0 / style.BP_PER_IN
    out = []
    for i, entries in keys.items():
        letter = letters[i]
        x_in = letter.get_window_extent(r).x1 / fig.dpi + KEY_GAP_PT * pt
        base_in = letter.get_position()[1] * H
        texts = []
        for k, (s, label, bar) in enumerate(entries):
            if k:
                x_in += KEY_COL_GAP_PT * pt
            rad = _marker_radius_pt(s)
            w = KEY_BAR_PT if bar else 2.0 * rad
            xc, yc = x_in + 0.5 * w * pt, base_in + KEY_MARK_RISE_PT * pt
            if bar:                 # in figure fractions (style.ink_outside_sides moves only those)
                b = Line2D([x_in / W, (x_in + w * pt) / W], [yc / H, yc / H], color=SERIES_COLOR, linewidth=BAR_PT,
                           solid_capstyle="butt", transform=fig.transFigure)
                b._sublet_role = "key"
                fig.add_artist(b)
                out.append(b)
            m = Line2D([xc / W], [yc / H], transform=fig.transFigure, **series_kwargs(s))
            m._sublet_role = "key"
            fig.add_artist(m)
            out.append(m)
            x_in += (w + KEY_MARK_GAP_PT) * pt
            t = fig.text(x_in / W, base_in / H, label, ha="left", va="baseline", fontsize=style.TICK_PT)
            t._sublet_role, t._sublet_key_of = "key", letter.get_text()
            texts.append(t)
            out.append(t)
            x_in += common.text_width_in(fig, label)
        align_baselines([letter] + texts)
    return out


def align_xlabels(axes: Sequence) -> None:
    """The x labels of a row of panels (`axes`, each its own x label) on one baseline as printed: matplotlib sets them
    at one height below tick labels of one height, and a mathtext label sits up to 1 pt off its plain neighbors
    (common.align_baselines; C62)."""
    align_baselines([ax.xaxis.label for ax in axes])


def line_label(ax, x: float, text: str, letter, *, avoid: Sequence = ()):
    """`text` (TICK_PT, style.THEORY_LABEL_GREY) centered over the vertical reference line at x of `ax`, on the
    baseline of `letter` (its panel's letter, above the axes); None (nothing drawn) where it would come within
    KEY_GAP_PT of a text of `avoid` (the letters and keys) or reach beyond the page."""
    from matplotlib.transforms import blended_transform_factory
    fig = ax.figure
    tr = blended_transform_factory(ax.transData, fig.transFigure)
    t = fig.text(x, letter.get_position()[1], text, transform=tr, ha="center", va="baseline", fontsize=style.TICK_PT,
                 color=style.THEORY_LABEL_GREY)
    r = fig.canvas.get_renderer()
    bb, pad = t.get_window_extent(r), KEY_GAP_PT * fig.dpi / 72.0
    W = fig.get_size_inches()[0] * fig.dpi
    for a in avoid:
        if not hasattr(a, "get_text"):
            continue
        ab = a.get_window_extent(r)
        if bb.x0 < ab.x1 + pad and ab.x0 < bb.x1 + pad and bb.y0 < ab.y1 and ab.y0 < bb.y1:
            t.remove()
            return None
    if bb.x0 < 0 or bb.x1 > W:
        t.remove()
        return None
    t._sublet_role = "line_label"
    return t


LINE_LABEL_PAD_PT = 1.5         # line_label_inside: the label's ink this far inside the axes' top (or bottom) edge
LINE_LABEL_GAP_PT = 1.5         # line_label_inside: the reference line stops this far short of the label's ink
LINE_LABEL_CLEAR_PT = 2.0       # line_label_inside: the label's ink at least this far from every drawn median and bar


def _data_boxes_px(ax) -> list[tuple[float, float, float, float]]:
    """The display boxes (x0, y0, x1, y1; px) of the rows' medians (each marker's square) and bars (each segment with
    half its line width) of a rows panel (draw_rows' roles 'median:*' and 'bar:*')."""
    px = ax.figure.dpi / style.BP_PER_IN
    out = []
    for ln in ax.lines:
        role = str(getattr(ln, "_sublet_role", ""))
        if not role.startswith(("median:", "bar:")):
            continue
        xy = ax.transData.transform(np.column_stack([ln.get_xdata(), ln.get_ydata()]).astype(float))
        if role.startswith("median:"):
            r = 0.5 * (float(ln.get_markersize()) + float(ln.get_markeredgewidth())) * px
            out += [(x - r, y - r, x + r, y + r) for x, y in xy]
        else:
            h = 0.5 * float(ln.get_linewidth()) * px
            out.append((float(xy[:, 0].min()), float(xy[:, 1].min()) - h, float(xy[:, 0].max()),
                        float(xy[:, 1].max()) + h))
    return out


def _center_baseline_pt(fig, text: str) -> float:
    """How far (pt) above its anchor a one-line plain `text` at TICK_PT sets its baseline under va 'center_baseline'
    (negative: below), as matplotlib sets a y tick label's (the rows' names)."""
    r = fig.canvas.get_renderer()
    y = []
    for va in ("baseline", "center_baseline"):
        t = fig.text(0.5, 0.5, text, fontsize=style.TICK_PT, va=va)
        y.append(t.get_window_extent(r).y0)        # the box's bottom: the baseline minus the same descent in both
        t.remove()
    return (y[1] - y[0]) * style.BP_PER_IN / fig.dpi


LINE_LABEL_SIDES = (("top", "center"), ("top", "right"), ("top", "left"), ("bottom", "center"), ("bottom", "right"),
                    ("bottom", "left"))  # line_label_inside: the places it tries, in order


def line_label_inside(ax, x: float, text: str):
    """`text` (TICK_PT, style.THEORY_LABEL_GREY) on the vertical reference line at x of a rows panel `ax`, inside the
    axes at the line's top end, on the baseline of the first row's name (the top y tick; a plain name's baseline as
    matplotlib sets it), lowered where its ink would come within LINE_LABEL_PAD_PT of the axes' top: centered on the
    line, which then stops LINE_LABEL_GAP_PT short of the label's ink, so that the label caps it; where a median or bar
    of the rows comes within LINE_LABEL_CLEAR_PT of its ink there, beside the line's top end (its ink LINE_LABEL_GAP_PT
    right of the line, else left of it; the line whole), then at the line's bottom end likewise (on the last row's
    baseline, raised likewise; LINE_LABEL_SIDES). C62 fix round: as built the label stood above the axes on the
    letter's baseline, right of (b)'s key, and read as a key entry without a sample. The label records its place
    (_sublet_place, (end, side)). None (nothing drawn, the line whole) where every place is taken or leaves the axes."""
    fig = ax.figure
    px = fig.dpi / style.BP_PER_IN
    lo, hi = _glyph_span_pt(text)
    line = next((ln for ln in ax.lines if getattr(ln, "_sublet_role", "") == "reference"
                 and np.allclose(np.asarray(ln.get_xdata(), dtype=float), x)), None)
    r = fig.canvas.get_renderer()
    box = ax.get_window_extent(r)
    data = _data_boxes_px(ax)
    clear, gap = LINE_LABEL_CLEAR_PT * px, LINE_LABEL_GAP_PT * px
    y0, y1 = sorted(ax.get_ylim())
    ticks = [float(v) for v in ax.get_yticks() if y0 <= v <= y1] or [y1, y0]
    rise = _center_baseline_pt(fig, text)
    for end, side in LINE_LABEL_SIDES:
        row = max(ticks) if end == "top" else min(ticks)
        row_px = float(ax.transData.transform((x, row))[1])
        base = row_px + rise * px                                   # on the row's names' baseline
        if end == "top":
            shift = min(0.0, box.y1 - (LINE_LABEL_PAD_PT + hi) * px - base)
        else:
            shift = max(0.0, box.y0 + (LINE_LABEL_PAD_PT - lo) * px - base)
        base += shift
        dx = {"center": 0.0, "right": gap, "left": -gap}[side] / px
        # va 'center_baseline' at the row, as the names: the same baseline in the PDF, whose text metrics differ from
        # the renderer's here by up to 0.4 pt (an explicit baseline from these metrics sat 0.34 pt below "Sublet")
        t = ax.annotate(text, xy=(x, row), xycoords="data", xytext=(dx, shift / px), textcoords="offset points",
                        ha={"center": "center", "right": "left", "left": "right"}[side], va="center_baseline",
                        fontsize=style.TICK_PT, color=style.THEORY_LABEL_GREY, zorder=style.Z_THEORY_LABEL,
                        annotation_clip=False)
        bb = t.get_window_extent(r)
        ink = (bb.x0, base + lo * px, bb.x1, base + hi * px)
        hit = any(ink[0] - clear < d[2] and d[0] < ink[2] + clear and ink[1] - clear < d[3] and d[1] < ink[3] + clear
                  for d in data)
        if hit or ink[0] < box.x0 or ink[2] > box.x1:
            t.remove()
            continue
        if line is not None and side == "center":
            y = ((ink[1] - gap - box.y0) / box.height) if end == "top" else ((ink[3] + gap - box.y0) / box.height)
            line.set_ydata([0.0, y] if end == "top" else [y, 1.0])
        t._sublet_role, t._sublet_place = "reference_label", (end, side)
        return t
    return None


# ---------------------------------------------------------------------------------------------------------------
# figure: panel (a), the margins per column in two sub-panels
def split_rows(fig, ax, n: int = 2, gap_in: float = SUB_GAP_IN) -> list:
    """`ax`'s slot as `n` axes on one x axis (top first), `gap_in` apart; each records its rectangle (finalize's
    geometry check) and the slot's left edge (panel_letters); the upper ones hide their x tick labels."""
    x, y, w, h = ax._sublet_rect_in
    slot = ax._sublet_slot_left_in
    fig.delaxes(ax)
    W, H = (float(v) for v in fig.get_size_inches())
    hs = (h - (n - 1) * gap_in) / n
    out = []
    for i in range(n):
        y0 = y + h - (i + 1) * hs - i * gap_in
        sub = fig.add_axes((x / W, y0 / H, w / W, hs / H), sharex=out[0] if out else None)
        sub._sublet_rect_in = (x, y0, w, hs)
        sub._sublet_slot_left_in = slot
        out.append(sub)
    for sub in out[:-1]:
        sub.tick_params(axis="x", labelbottom=False)
    return out


def _ylim(values: Sequence[float]) -> tuple[float, float]:
    vals = [0.0] + [float(v) for v in values]
    lo, hi = min(vals), max(vals)
    pad = PAD * (hi - lo) if hi > lo else 0.05
    return lo - pad, hi + pad


Y_LOCATOR = dict(nbins=3, steps=[1, 2, 5, 10])
RESERVE_GAP_IN = 0.06          # (a): the y label this far right of the slot's left edge, at least


def _values(a: Mapping, keys: Sequence[str]) -> list[float]:
    return [float(v) for k in keys for v in a[k] if v is not None and math.isfinite(float(v))]


def margins_reserve(fig, a: Mapping) -> float:
    """The left reserve (in) of panel (a): the widest y tick label that its sub-panels will show (their limits and
    Y_LOCATOR's ticks, as draw_margins sets them) with the y label, at least style.LEFT_LABEL."""
    labels = []
    for _, keys in a["subpanels"]:
        lo, hi = _ylim(_values(a, keys))
        labels += [style.PLAIN(v) for v in MaxNLocator(**Y_LOCATOR).tick_values(lo, hi) if lo <= v <= hi]
    return max(style.LEFT_LABEL, style.ytick_reserve(fig, labels, ylabel=True, gap=RESERVE_GAP_IN))


def flagged_columns(xs: Sequence, series: Mapping[str, Sequence], keys: Sequence[str]) -> list:
    """The columns (as in xs) where a series of `keys` is negative or missing."""
    return [x for i, x in enumerate(xs) if any(series[k][i] is None or float(series[k][i]) < 0 for k in keys)]


def draw_margins(axes: Sequence, a: Mapping, styles: Mapping[str, str], ylabels: Mapping[str, str],
                 xlabel: str) -> None:
    """Panel (a): a['x'] the columns (numbers), a['subpanels'] [[name, [series...]], ...] top first, a[series] the
    values per column (None: missing); each series in styles[series] (SERIES_STYLES), the first of a sub-panel DODGE
    left of its column and the second DODGE right; every column in a['shaded'][name] shaded in that sub-panel;
    StyleError where two markers of a sub-panel overlap by more than MAX_MARKER_OVERLAP of a marker."""
    x = np.asarray([float(v) for v in a["x"]])
    x0, x1 = (float(x.min()), float(x.max())) if x.size else (0.0, 1.0)
    for ax, (name, keys) in zip(axes, a["subpanels"]):
        ax.set_xlim(x0 - 0.7, x1 + 0.7)
        vals = []
        for j, k in enumerate(keys):
            dx = (-DODGE if j == 0 else DODGE) if len(keys) == 2 else 0.0
            y = np.asarray([np.nan if v is None else float(v) for v in a[k]])
            ok = np.isfinite(y)
            vals += list(y[ok])
            if ok.any():
                (ln,) = ax.plot(x[ok] + dx, y[ok], label="_nolegend_", **series_kwargs(styles[k]))
                ln._sublet_role = f"margin:{k}"
        style.reference_line(ax, y=0.0)
        ax.set_ylim(*_ylim(vals))
        ax.yaxis.set_major_locator(MaxNLocator(**Y_LOCATOR))
        ax.yaxis.set_major_formatter(style.PLAIN)
        ax.set_ylabel(ylabels[name])
        y0, y1 = ax.get_ylim()
        for c in a["shaded"][name]:
            r = style.shade_region(ax, (float(c) - 0.5, float(c) + 0.5), (y0, y1))
            r._sublet_role, r._sublet_column = "shade", str(c)
        worst = v2.marker_overlaps(ax)
        if worst and worst[0]["share"] > MAX_MARKER_OVERLAP:
            raise style.StyleError(f"panel (a): markers overlap by more than {MAX_MARKER_OVERLAP:.2f} of a marker: "
                                   f"{worst[:3]}")
    bottom = axes[-1]
    bottom.xaxis.set_major_formatter(style.PLAIN)
    bottom.set_xlabel(xlabel)
    v2.week_tick_labels(bottom, list(x))
    align_ylabels_x(list(axes))             # C62: Figure.align_ylabels leaves axes without a subplotspec as they are
    align_baselines([ax.yaxis.label for ax in axes])


# ---------------------------------------------------------------------------------------------------------------
# figure: rows
def row_limits(rows: Sequence[Mapping], series: Sequence[str], ref: float) -> tuple[float, float]:
    """The x range of a rows panel: every median, min and max of `series` and the reference, padded by PAD."""
    vals = [ref]
    for r in rows:
        for s in series:
            e = r.get(s) or {}
            vals += [float(e[k]) for k in ("median", "min", "max") if e.get(k) is not None]
    lo, hi = min(vals), max(vals)
    pad = PAD * (hi - lo) if hi > lo else 0.05
    return lo - pad, hi + pad


def draw_rows(ax, rows: Sequence[Mapping], series: Sequence[str], styles: Mapping[str, str], *, ref: float,
              xlabel: str, names: Sequence[str] | None, separators: Sequence[int]) -> None:
    """One rows panel: rows[i] {'key', s: {'median', 'min', 'max'}} top first at y = n - 1 - i; the first series
    ROW_OFFSET above the center and the second as far below (a single series at the center), each its median as a
    marker of styles[s] and its [min, max] as a BAR_PT bar; `names` as the y tick labels (None: none, a panel that
    shares its neighbor's rows), a mathtext name on the plain names' baseline and right end as printed (align_baselines,
    align_right_math; C62); a grey
    line between rows i - 1 and i for i in `separators`; a grey reference line at x = ref."""
    n = len(rows)
    ys = np.arange(n - 1, -1, -1, dtype=float)
    for j, s in enumerate(series):
        dy = (ROW_OFFSET if j == 0 else -ROW_OFFSET) if len(series) == 2 else 0.0
        kw = series_kwargs(styles[s])
        for y, r in zip(ys, rows):
            e = r.get(s) or {}
            if e.get("median") is None:
                continue
            bar = ax.plot([e["min"], e["max"]], [y + dy, y + dy], color=SERIES_COLOR, linewidth=BAR_PT,
                          solid_capstyle="butt", zorder=style.Z_DATA - 0.01, label="_nolegend_")[0]
            bar._sublet_role = f"bar:{s}"
            (m,) = ax.plot([e["median"]], [y + dy], label="_nolegend_", **kw)
            m._sublet_role, m._sublet_row = f"median:{s}", r["key"]
    for i in separators:
        sep = ax.axhline(n - i - 0.5, color=style.GRID_GREY, linewidth=SEPARATOR_PT, zorder=0.6)
        sep._sublet_role = "separator"
    style.reference_line(ax, x=ref)
    ax.set_ylim(-ROW_PAD, n - 1 + ROW_PAD)
    ax.yaxis.set_major_locator(FixedLocator(list(ys)))
    if names is not None:
        if len(names) != n:
            raise style.StyleError(f"draw_rows: {len(names)} names for {n} rows")
        ax.set_yticklabels(list(names))
    ax.tick_params(axis="y", length=0)          # (it resets the tick labels' transforms: before align_baselines)
    if names is not None:
        align_baselines([tk.label1 for tk in ax.yaxis.get_major_ticks()])
        align_right_math([tk.label1 for tk in ax.yaxis.get_major_ticks()])     # C62 fix round
    ax.xaxis.set_major_locator(MaxNLocator(nbins=4, steps=[1, 2, 2.5, 5, 10]))
    ax.xaxis.set_major_formatter(style.PLAIN)
    ax.set_xlabel(xlabel)
    common.thin_tick_labels(ax)


def names_reserve(fig, names: Sequence[str]) -> float:
    """The left reserve (in) of a rows panel: its widest name as a y tick label (TICK_PT) with the tick pad, and the
    gutter NAMES_GUTTER_PT to the panel on its left."""
    return style.ytick_reserve(fig, list(names)) + NAMES_GUTTER_PT / style.BP_PER_IN


# ---------------------------------------------------------------------------------------------------------------
# tables
def num(v, fmt: str = ".3f") -> str:
    """ms5b_e7_lib.num without a negative zero: a value that rounds to zero prints unsigned ('0.000', not '$-$0.000';
    MS7 print check, 2026-11-11)."""
    s = L.num(v, fmt)
    if s.startswith("$-$"):
        try:
            if float(s[3:].replace(",", "")) == 0.0:
                return s[3:]
        except ValueError:
            pass
    return s


def interval(lo, hi, fmt: str = ".3f") -> str:
    """ms5b_e7_lib.interval with num's unsigned zero."""
    return "--" if lo is None or hi is None else f"[{num(lo, fmt)}, {num(hi, fmt)}]"


FEWER_MARK = r"$^\dagger$"


def fewer_mark(s: Mapping | None) -> str:
    """FEWER_MARK where a statistic exists but leaves out a missing value (its n_missing > 0: a median over fewer
    weeks or cells than the others; review of W-G4 A), else ''."""
    s = s or {}
    return FEWER_MARK if s.get("median") is not None and (s.get("n_missing") or 0) > 0 else ""


def med_rows(stats: Sequence[Mapping | None], fmt: str = ".3f", extra: Sequence[str] | None = None) -> list[list[str]]:
    """Two table rows from per-column stats: the medians (FEWER_MARK where a value is missing), then [min, max] ('--'
    where a column has none); `extra` cells follow the medians (and blanks the ranges)."""
    top = [num((s or {}).get("median"), fmt) + fewer_mark(s) for s in stats]
    low = [interval((s or {}).get("min"), (s or {}).get("max"), fmt) for s in stats]
    if extra:
        top += list(extra)
        low += [""] * len(extra)
    return [top, low]


def longtable(colspec: str, caption: str, label: str, header: Sequence[str], rows: Sequence[Sequence[str]], *,
              rules: Sequence[int] = (), together: Sequence[Sequence[int]] = (), head_top: str | None = None,
              size: str = r"\footnotesize", tabcolsep: str = "2.4pt") -> str:
    """ms5b_e7_lib.longtable's table (one-column mode, booktabs rules, its caption and label on the first page, the
    head with "Table <n>, continued" on the later pages, rows ended by \\tabularnewline) with a rule before each row
    index of `rules` and, apart from them, blocks of rows kept on one page: each [first, last] of `together` ends
    every row before `last` with \\tabularnewline* (longtable's row end without a page break), e.g. the two lines of
    one policy."""
    head = ((head_top + "\n") if head_top else "") + " & ".join(header) + r" \\"
    lines = [L.ONE_COLUMN, r"\begingroup" + size + r"\setlength{\tabcolsep}{" + tabcolsep + "}",
             r"\begin{longtable}{" + colspec + "}", r"\caption{" + caption + r"}\label{" + label + r"}\\",
             r"\toprule", head, r"\midrule\endfirsthead", L.cont_head(len(header)), r"\toprule", head,
             r"\midrule\endhead", r"\bottomrule\endlastfoot"]
    nobreak = {i for a, b in together for i in range(a, b)}
    for i, r in enumerate(rows):
        if i in set(rules) and i:
            lines.append(r"\midrule")
        lines.append(" & ".join(r) + (r" \tabularnewline*" if i in nobreak else r" \tabularnewline"))
    lines += [r"\end{longtable}", r"\endgroup", ""]
    return "\n".join(lines)


def prose(label: str) -> str:
    """A registry label inside a sentence: its first letter in lower case where the first word is a common word
    (Greedy, Critical-ratio, Per-borrower), not a name (Sublet, RetroRenting, SpotHedge, CoCaR, MPC)."""
    first = label.split(" ", 1)[0].rstrip(",")
    if first == "Sublet" or any(c.isupper() for c in first[1:]) or not first[:1].isupper():
        return label
    return label[0].lower() + label[1:]


def csv_text(columns: Sequence[str], rows: Sequence[Sequence]) -> str:
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(columns)
    for r in rows:
        w.writerow(["" if v is None else v for v in r])
    return buf.getvalue()


def csv_num(v, fmt: str = ".6f") -> str:
    return "" if v is None or (isinstance(v, float) and not math.isfinite(v)) else format(float(v), fmt)


def csv_entry(file_name: str, columns: Sequence[str], rows: Sequence[Sequence], scope: Mapping) -> dict:
    """The extract's entry of a data file: its file name, columns, its lines (without the header; one string each),
    number of rows, sha256 of the whole text and its scope."""
    text = csv_text(columns, rows)
    lines = text.splitlines()
    return {"file": file_name, "columns": list(columns), "n_rows": len(lines) - 1, "lines": lines[1:],
            "sha256": sha256_text(text), "scope": dict(scope)}


def csv_from_entry(entry: Mapping) -> str:
    """The data file's text from its extract entry (header and lines); StyleError where its sha256 differs."""
    buf = io.StringIO()
    csv.writer(buf, lineterminator="\n").writerow(entry["columns"])
    text = buf.getvalue() + "".join(f"{ln}\n" for ln in entry["lines"])
    if sha256_text(text) != entry["sha256"]:
        raise style.StyleError(f"{entry['file']}: the text differs from the sha256 that the extract records")
    return text


__all__ = ["MissingInput", "read_json", "guard_reduced", "main", "describe", "signs", "SERIES_STYLES", "series_kwargs",
           "handles", "key_room_in", "letter_keys", "align_xlabels", "line_label",
           "line_label_inside", "split_rows", "flagged_columns", "margins_reserve", "draw_margins", "row_limits",
           "draw_rows", "names_reserve", "longtable", "prose", "FEWER_MARK", "fewer_mark", "med_rows", "csv_text",
           "csv_num", "csv_entry", "csv_from_entry", "num", "interval"]
