"""Helpers shared by the MS3 figure scripts (design/sim_spec_ms3.md §8; design/figure_plan.md §5).

Every figure script code/sim/figs/fig<N>_<exp>.py and code/sim/figs/supp/sf_*.py imports what it shares from here;
a supplementary figure that redraws a main-text panel at other parameters imports that panel's builder and drawer
from the main figure's script instead (sf_e10_rho from fig5_e1_e10 and fig6_e10; sf_e1_sched from fig5_e1_e10;
sf_e2_* and sf_e6a from fig7_e2_e6; sf_e10_cross from fig6_e10).

Command line (``cli``), one convention for every script, run from code/sim:

    python -m figs.<script> [--from-extract [JSON]]

Without the option the script builds its data from the result files (figs.inputs.Inputs: repository-relative
names under the input root, the repository or SUBLET_FIGS_IN_ROOT), draws and saves. ``--from-extract`` without an
argument redraws from the figure's own extract code/sim/out/figs/<name>.json read through ``Inputs.extract`` (so
under SUBLET_FIGS_IN_ROOT when it is set); ``--from-extract PATH`` reads that file instead (the tests pass
tests/fixtures_figs/<name>.json). The extract written by a redraw equals the one read (the MS5 rebuild).

Output folders:
  main-text PDFs              paper/figures/, or SUBLET_FIGS_PDF_DIR (style.save)
  supplementary PDFs          paper/supplement/figures/ (M39), or SUBLET_FIGS_PDF_DIR (``supp_pdf_dir``)
  extracts and PNG previews   code/sim/out/figs/, or SUBLET_FIGS_OUT_DIR (style.save)
  supplementary tables        SUBLET_FIGS_TABLES_DIR; else SUBLET_FIGS_PDF_DIR when it is set, so that a test or
                              scratch build that redirects the PDFs never writes into paper/; else
                              paper/supplement/tables/ (``tables_dir``, ``write_table``): e11_scope.tex
                              (sf_e11_guard) and e6a_cells.tex (sf_e6a)

Contents: strict access to summary keys (``need``, ``maybe``, ``num_items``, ``ci_of``, ``finite``,
``data_range``); the command line and output folders (``cli``, ``read_extract``, ``json_number``, ``supp_pdf_dir``,
``tables_dir``, ``write_table``, ``tex_num``); the E1 and E10 series builders and panel drawers (``e1_series``,
``draw_e1_ratio_panel``, ``inc_ticks``, ``e10_series``, ``e10_bound``, ``draw_e10_series`` and their axes); layout
helpers (``label_column``, ``right_theory_lines``, ``stack_labels``, ``place_clear``, ``thin_tick_labels``,
``same_tick_labels``, ``clear_floor``, ``panel_title``, ``legend_rows``, ``legend_headroom``, ...); keys and labels
placed on the free space of a panel (``agreement``, ``agree_key``, ``place_key``, ``place_label``, ``free_spot``);
C62: text as the PDF prints it, one implementation for every script (``in_pdf``, ``pdf_text_metrics``,
``math_rise_pt``, ``text_ink``, ``printed_baselines_pt``, ``letter_box``; mathtext on its plain neighbors' baseline
or right end: ``align_baselines``, ``align_printed_rows``, ``align_legend_rows``, ``align_right_math``; y labels at
one x: ``align_ylabels_x``).
"""
from __future__ import annotations

import argparse
import io
import json
import math
import os
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

import numpy as np
from matplotlib import cbook
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.mathtext import MathTextParser
from matplotlib.textpath import TextPath
from matplotlib.ticker import FixedLocator, NullFormatter
from matplotlib.transforms import ScaledTranslation

from figs import style
from figs.inputs import Inputs, extract_name

SUPP_PDF_DIR = style.REPO / "paper" / "supplement" / "figures"      # M39
TABLES_DIR = style.REPO / "paper" / "supplement" / "tables"
ENV_TABLES_DIR = "SUBLET_FIGS_TABLES_DIR"

E1 = "code/sim/out/e1/summary.json"
E10 = "code/sim/out/e10/summary.json"

# E1 tags (§4.3) and E10 tags (§5.5) by registry key. MS6 C46 (design/ms6_spec.md M2, M4): E1's guarded series, whose
# data tag stays "Sublet", is the one-way guard around the lagged BL5 at Algorithm 1's defaults, drawn as bl5_g1
E1_TAGS = {"bl5_g1": "Sublet", "a2_r1": "A2-r1", "a2_theory": "A2-th", "a3": "A3-ref", "a3_rot": "A3-rot"}
E1_FRAC_TAG, E1_FRAC_FIELD = "A2-r1", "P_over_LB"          # A2 fractional: P / LB of A2-r1's runs (§4.3)
E10_TAGS = {"rr_renew": "RR", "a2_theory": "A2-th", "a3": "A3-ref", "a3_rot": "A3-rot", "marking": "MARK"}
RHO_MAIN = 16                   # rho of the T4 family in the main text (§5.2; Figs. 5(c) and 6)

DODGE_OCT = 0.055               # x dodge between series against rho*, in octaves (not in §8)
INC_TICK = dict(marker="_", markersize=4.0, markeredgewidth=0.7, color="black", linestyle="none", zorder=3.0)
INC_TICK_REL = 0.01             # an incumbent tick only where it differs from the plotted ratio by more (not in §8)
INC_TICK_RULE = f"drawn only where it differs from the plotted ratio by more than {INC_TICK_REL:.0%}"
TICK_GAP_PT = 3.0               # least gap between neighboring x tick labels (thin_tick_labels; not in §8)
TOP_TICK_GAP_PT = 2.0           # least gap between the top y tick label and the axes top (ratio axes; not in §8)
LEADER_RUN_PT = 6.0             # extra x offset of a label column whose labels need leaders (not in §8)
LEADER_PT = 0.4                 # leader line width (not in §8)
LINE_STEP_PT = 1.2 * style.TICK_PT    # height of one line of a TICK_PT label (stack_labels, place_clear)
# a label line is level with a line's end within this: about half the cap height of a TICK_PT label (C62: 0.39 em,
# 2.73 pt at 7 pt; 3.5 pt at 9 pt, 2026-10-22 to C62)
LEVEL_PT = 0.39 * style.TICK_PT
COINCIDE_PT = 1.5               # line ends closer than this read as one point (about a marker's radius)
LEADER_CLEAR_PT = 3.0           # a leader ends where its line is this far from the data, if it can (leader_end)
KEY_PAD_PT = 1.5                # least clearance between a placed key or label and anything drawn (free_spot)
GRID_RES_PT = 0.5               # cell size of the occupancy grid of free_spot


# ---------------------------------------------------------------------------------------------------------------
# Summary access
class MissingKey(KeyError):
    """A key path that a figure reads is not in its input (design/sim_spec_ms3.md §8 names every path)."""

    def __str__(self) -> str:
        return str(self.args[0])


def need(d: Any, *path, what: str = "input") -> Any:
    """d[p0][p1]...; numbers in `path` are written as JSON keys (format(float(x), "g"), §2.4). Raises MissingKey
    naming the path and the keys found where it stops, or if a value on the path is null (with its '*_note')."""
    cur, done = d, []
    for p in path:
        key = p if isinstance(p, str) else format(float(p), "g")
        if not isinstance(cur, Mapping) or key not in cur:
            found = sorted(cur)[:12] if isinstance(cur, Mapping) else type(cur).__name__
            raise MissingKey(f"{what}: key {'.'.join(done + [key])!r} not found (keys there: {found})")
        if cur[key] is None:
            raise MissingKey(f"{what}: {'.'.join(done + [key])!r} is null ({cur.get(key + '_note')!r})")
        cur, done = cur[key], done + [key]
    return cur


def maybe(d: Any, *path) -> tuple[Any, str | None]:
    """(value, None) or (None, note): None where a key is missing or a value is null; the note is the '*_note'
    sibling of the null value (§2.6) or 'missing'."""
    cur = d
    for p in path:
        key = p if isinstance(p, str) else format(float(p), "g")
        if not isinstance(cur, Mapping) or key not in cur:
            return None, "missing"
        if cur[key] is None:
            return None, cur.get(key + "_note") or "null"
        cur = cur[key]
    return cur, None


def num_items(d: Mapping) -> list[tuple[float, str, Any]]:
    """(number, key, value) for the keys of `d` that are numbers ("16", "0.2"), sorted by number; '*_note' and
    other keys are skipped."""
    out = []
    for key, v in d.items():
        try:
            x = float(key)
        except (TypeError, ValueError):
            continue
        if math.isfinite(x):
            out.append((x, key, v))
    return sorted(out, key=lambda t: t[0])


def ci_of(entry: Mapping, field: str = "median_ci95") -> tuple[float | None, float | None]:
    lo, hi = (entry.get(field) or [None, None])[:2]
    return lo, hi


def finite(values) -> np.ndarray:
    """float64 array with None as NaN."""
    return np.array([np.nan if v is None else float(v) for v in values], dtype=float)


def data_range(*arrays) -> tuple[float, float]:
    """(min, max) of the finite positive values of the arrays."""
    v = np.concatenate([finite(a) for a in arrays if len(a)])
    v = v[np.isfinite(v) & (v > 0)]
    return float(v.min()), float(v.max())


# ---------------------------------------------------------------------------------------------------------------
# Command line and output folders
def read_extract(name: str, path: str | os.PathLike | None = None) -> tuple[dict, list]:
    """(data, sources) of the figure's own extract: `path`, else code/sim/out/figs/<name>.json under the input root
    (Inputs.extract: the repository, or SUBLET_FIGS_IN_ROOT). StyleError if it is another figure's extract."""
    if path:
        with open(path, encoding="utf-8") as f:
            payload = json.load(f)
    else:
        payload = Inputs().extract(name)
    if payload.get("figure") != name:
        raise style.StyleError(f"{path or extract_name(name)} is the extract of {payload.get('figure')!r}, "
                               f"not {name!r}")
    return payload["data"], list(payload.get("sources") or [])


def json_number(o):
    """json.dumps `default` for numpy scalars."""
    if isinstance(o, (np.integer, np.floating, np.bool_)):
        return o.item()
    raise TypeError(f"not JSON-serializable: {type(o).__name__}")


def supp_pdf_dir() -> Path:
    """paper/supplement/figures/ (M39), or SUBLET_FIGS_PDF_DIR when set (tests)."""
    return Path(os.environ.get(style.ENV_PDF_DIR) or SUPP_PDF_DIR)


def tables_dir() -> Path:
    """The folder of the supplementary tables: SUBLET_FIGS_TABLES_DIR; else SUBLET_FIGS_PDF_DIR when set (tests and
    scratch builds never write into paper/); else paper/supplement/tables/."""
    return Path(os.environ.get(ENV_TABLES_DIR) or os.environ.get(style.ENV_PDF_DIR) or TABLES_DIR)


def write_table(file_name: str, text: str) -> Path:
    """Write a supplementary table to tables_dir()/<file_name> (through a partial file renamed into place)."""
    d = tables_dir()
    d.mkdir(parents=True, exist_ok=True)
    tmp = d / f".{file_name}.partial"
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, d / file_name)
    return d / file_name


def tex_num(v, d: int = 3) -> str:
    """A table number with `d` decimals, '--' for a missing value."""
    return "--" if v is None else f"{float(v):.{d}f}"


def cli(name: str, build: Callable[[Inputs], dict], draw: Callable[[dict], Any], argv: Sequence[str] | None = None,
        *, supplementary: bool = False, after: Callable[[dict, dict], None] | None = None,
        extra_sources: Sequence[str] = (), doc: str | None = None) -> dict:
    """Build the data from the inputs (or read them from the extract with --from-extract [JSON]), draw, and save
    with style.save. The built data pass through JSON first, so that a figure drawn from its inputs and one drawn
    from its extract see the same values; `extra_sources` (e.g. a glob of run files read outside Inputs) follow the
    recorded inputs in the extract's sources. A supplementary figure's PDF goes to paper/supplement/figures/ (M39)
    unless SUBLET_FIGS_PDF_DIR is set. `after(data, report)` runs once the figure is saved (a table, a report
    line). Returns style.save's report."""
    ap = argparse.ArgumentParser(prog=f"python -m figs.{name}", description=(doc or "").strip().split("\n")[0])
    ap.add_argument("--from-extract", nargs="?", const="", default=None, metavar="JSON",
                    help=f"redraw from the extract alone (the MS5 rebuild; default {extract_name(name)} under the "
                         "input root)")
    args = ap.parse_args(argv)
    if args.from_extract is None:
        inp = Inputs()
        data = json.loads(json.dumps(build(inp), allow_nan=False, default=json_number))
        sources = list(inp.sources) + [s for s in extra_sources if s not in inp.sources]
    else:
        data, sources = read_extract(name, args.from_extract or None)
    fig = draw(data)
    rep = style.save(fig, name, data, sources=sources, pdf_dir=supp_pdf_dir() if supplementary else None)
    print(f"[{name}] wrote {rep['pdf']}, {rep['json']}; text {rep['text_pt']} pt, smallest glyph "
          f"{rep['min_glyph_pt']} pt")
    if after is not None:
        after(data, rep)
    return rep


# ---------------------------------------------------------------------------------------------------------------
# E1 series (Fig. 5(b), sf_e1_sched, sf_e1_rotation)
def e1_series(e1: Mapping, sched: str, mu, keys: Sequence[str], *, rho=None) -> dict:
    """Per registry key the E1 ratios under `sched`: against rho* at `mu` (rho None), or against mu at `rho`.
    Values: x, median, ci_lo, ci_hi (ratio_LB, Q39), inc_median (ratio_inc), note (the '*_note' of a null median,
    §8.7); a2_frac is A2-r1's P/LB."""
    out = {}
    block = need(e1, "ratios", sched, what=E1)
    if rho is None:
        pts = [(x, need(v, mu, what=f"{E1} ratios.{sched}.{kr}")) for x, kr, v in num_items(block)]
    else:
        pts = [(x, v) for x, _, v in num_items(need(block, rho, what=f"{E1} ratios.{sched}"))]
    for key in keys:
        tag = E1_FRAC_TAG if key == "a2_frac" else E1_TAGS[key]
        field = E1_FRAC_FIELD if key == "a2_frac" else "ratio_LB"
        s = {"x": [], "median": [], "ci_lo": [], "ci_hi": [], "inc_median": [], "note": []}
        for x, cell in pts:
            ent = need(cell, tag, field, what=f"{E1} ratios.{sched}")
            lo, hi = ci_of(ent)
            inc = None if key == "a2_frac" else maybe(cell, tag, "ratio_inc", "median")[0]
            note = None if ent.get("median") is not None else \
                (ent.get("median_note") or cell[tag].get("median_note") or "null")
            for f, v in zip(s, (x, ent.get("median"), lo, hi, inc, note)):
                s[f].append(v)
        out[key] = s
    return out


def draw_e1_ratio_panel(ax, series: Mapping, keys: Sequence[str]) -> None:
    """Medians with interval bars per key, dodged in x (DODGE_OCT octaves apart), and the black ticks at the median
    of ratio_inc where it differs from the median (inc_ticks)."""
    n = len(keys)
    for i, key in enumerate(keys):
        s = series[key]
        x = finite(s["x"]) * 2.0 ** (DODGE_OCT * (i - (n - 1) / 2))
        y, lo, hi = finite(s["median"]), finite(s["ci_lo"]), finite(s["ci_hi"])
        style.plot_policy(ax, key, x, y)
        ok = np.isfinite(lo) & np.isfinite(hi) & np.isfinite(y)
        if ok.any():
            style.errorbars(ax, key, x[ok], y[ok], lo[ok], hi[ok])
        inc_ticks(ax, x, y, s["inc_median"])


def inc_ticks(ax, x, y, inc) -> None:
    """Black ticks at the ratio to the MILP incumbents `inc`, only where it differs from the plotted ratio `y` by
    more than INC_TICK_REL (relative; INC_TICK_RULE, for the extract labels): where the two agree, a tick would only
    cover the marker (Fig. 5(b), sf_e1_sched, sf_e1_rotation, sf_e10b). A tick of a point whose ratio is missing is
    drawn."""
    x, y, inc = finite(x), finite(y), finite(inc)
    with np.errstate(divide="ignore", invalid="ignore"):
        far = ~np.isfinite(y) | (np.abs(inc / y - 1.0) > INC_TICK_REL)
    show = np.isfinite(x) & np.isfinite(inc) & far
    if show.any():
        ax.plot(x[show], inc[show], label="_nolegend_", **INC_TICK)


def rho_star_range(rhos, n_series: int) -> list[float]:
    """x range of a panel of dodged series against rho*: a quarter octave left of the smallest rho*, and just
    right of the largest rho*'s rightmost dodged marker (where the theory lines end and their labels start)."""
    rhos = [float(v) for v in rhos]
    return [min(rhos) / 2 ** 0.25, max(rhos) * 2.0 ** (DODGE_OCT * (n_series - 1) / 2 + 0.06)]


def rho_star_axis(ax, rhos, x_range, labels: Sequence[str] = (), *, prefer: Sequence[float] = ()) -> None:
    """log2 axis of rho* with ticks at the grid; with `labels`, a label column right of the data. Tick labels that
    would crowd their neighbors are left out (thin_tick_labels: 1.5 and 2 are 0.4 octave apart); the values in
    `prefer` are labeled first (rho = 2, the kink of max(2, rho), in a panel that draws it)."""
    style.log2_axis(ax, "x", ticks=sorted({float(v) for v in rhos}))
    if labels:
        label_column(ax, x_range[0], x_range[1], labels)
    else:
        ax.set_xlim(*x_range)
    thin_tick_labels(ax, prefer=prefer)


def max2rho(rho_values) -> dict:
    xs = sorted(set([float(v) for v in rho_values] + [2.0]))
    return {"rho": xs, "max2rho": [max(2.0, x) for x in xs]}


# ---------------------------------------------------------------------------------------------------------------
# E10 series (Fig. 5(c), Fig. 6, sf_e10_rho, sf_e10_cross, sf_e1_rotation)
def e10_series(e10: Mapping, sched: str, rho, keys: Sequence[str], *, part: str = "a",
               extra: Sequence[str] = ()) -> dict:
    """Per registry key the E10 points a.<sched>.<rho>.<m>.<tag>: m, ratio, ci_lo, ci_hi, T, note (+ `extra` fields
    of bounds.<rho>.<m>, e.g. k_star). A point whose entry or ratio is null or missing stays in the lists with null
    values and its '*_note' (§2.6, §8.7), so that its line has a gap there."""
    block = need(e10, part, sched, rho, what=E10)
    out = {}
    for key in keys:
        tag = E10_TAGS[key]
        s = {"m": [], "ratio": [], "ci_lo": [], "ci_hi": [], "T": [], "note": []}
        s.update({f: [] for f in extra})
        for m, mk, _ in num_items(block):
            ent, note = maybe(block, mk, tag)
            ent = ent if isinstance(ent, Mapping) else {}
            if note is None and ent.get("ratio") is None:
                note = ent.get("ratio_note") or "null"
            lo, hi = ci_of(ent, "ci95")
            for f, v in zip(("m", "ratio", "ci_lo", "ci_hi", "T", "note"),
                            (m, ent.get("ratio"), lo, hi, ent.get("T"), note)):
                s[f].append(v)
            for f in extra:
                s[f].append(maybe(e10, "bounds", rho, mk, f)[0])
        out[key] = s
    return out


def e10_bound(e10: Mapping, rho, field: str, *, m_min: float | None = None) -> dict:
    """bounds.<rho>.<m>.<field> as {m, value}, skipping nulls (LB_A at m = 2)."""
    out = {"m": [], "value": []}
    for m, _, cell in num_items(need(e10, "bounds", rho, what=E10)):
        v = cell.get(field) if isinstance(cell, Mapping) else None
        if v is None or (m_min is not None and m < m_min):
            continue
        out["m"].append(m)
        out["value"].append(v)
    return out


def draw_e10_series(ax, series: Mapping, keys: Sequence[str], *, env: tuple[str, str] | None = None,
                    envs: Mapping[str, tuple[str, str]] | None = None) -> None:
    for key in keys:
        s = series[key]
        x, y, lo, hi = finite(s["m"]), finite(s["ratio"]), finite(s["ci_lo"]), finite(s["ci_hi"])
        e = envs.get(key) if envs else env
        style.plot_policy(ax, key, x, y, env=e)
        ok = np.isfinite(lo) & np.isfinite(hi) & np.isfinite(y) & (hi > lo)
        if ok.any():
            style.errorbars(ax, key, x[ok], y[ok], lo[ok], hi[ok])


def m_axis(ax, ms, labels: Sequence[str] = ()) -> None:
    """log2 axis of the number of sites m; with `labels`, a label column right of the largest m. Tick labels that
    would crowd their neighbors in a narrow panel are left out (thin_tick_labels)."""
    ms = [float(m) for m in ms]
    ax.set_xlabel(r"Sites $m$")                 # before label_column, which centers it under the spine
    style.log2_axis(ax, "x", ticks=ms)
    lo, hi = min(ms) / 2 ** 0.25, max(ms)
    if labels:
        label_column(ax, lo, hi * 2 ** 0.12, labels)
    else:
        ax.set_xlim(lo, hi * 2 ** 0.25)
    thin_tick_labels(ax)


def thin_tick_labels(ax, gap_pt: float = TICK_GAP_PT, *, prefer: Sequence[float] | None = None) -> list[float]:
    """Leave out the x tick labels that would come closer than `gap_pt` to a neighboring label, after the x limits
    are final; the ticks stay, those left unlabeled at minor length (_label_only), so that a full-length tick does
    not read as a missing label. The labels of the values in `prefer` are kept first (remembered on the axis, so a
    later thinning keeps them), then the first and last labels where they clear those, then the others from the
    right end leftwards wherever they clear the labels kept (on a crowded log2 axis of m: 2, 4, 16, 64). A thinning
    done before (the x limits changed since) is undone first (_unthin); a no-op where every label clears its
    neighbors. Returns the labeled values."""
    if prefer is None:
        prefer = getattr(ax.xaxis, "_sublet_prefer", ())
    ax.xaxis._sublet_prefer = tuple(prefer)
    _unthin(ax)
    lo, hi = sorted(ax.get_xlim())
    tol = 1e-9 * max(abs(lo), abs(hi), 1e-300)
    locs = [float(v) for v in ax.xaxis.get_majorticklocs() if lo - tol <= v <= hi + tol]
    base = ax.xaxis.get_major_formatter()
    if len(locs) < 3:
        return locs
    dpi = ax.figure.dpi
    xs = [ax.transData.transform((v, 0.0))[0] / dpi for v in locs]
    half = [0.5 * text_width_in(ax.figure, base(v)) for v in locs]
    gap = gap_pt / style.BP_PER_IN

    def clears(i, j):
        a, b = sorted((i, j), key=lambda k: xs[k])
        return xs[b] - half[b] - (xs[a] + half[a]) >= gap

    first = [i for i, v in enumerate(locs) if any(abs(v - p) <= tol for p in prefer)]
    kept = [] if first else [0, len(locs) - 1]
    for i in first + [len(locs) - 1, 0]:
        if i not in kept and all(clears(i, k) for k in kept):
            kept.append(i)
    for i in range(len(locs) - 2, 0, -1):
        if i not in kept and all(clears(i, k) for k in kept):
            kept.append(i)
    if len(kept) == len(locs):
        return locs
    keep = [locs[i] for i in sorted(kept)]
    _label_only(ax, keep)
    return keep


def _unthin(ax) -> None:
    """Undo _label_only on the x axis of `ax` where it is still in effect: the axis's own locators and formatters
    back, every major tick labeled again."""
    axis = ax.xaxis
    done = getattr(axis, "_sublet_thinned", None)
    if done is not None and done["thinned"] is axis.get_major_locator():
        axis.set_major_locator(done["major_locator"])
        axis.set_major_formatter(done["major_formatter"])
        axis.set_minor_locator(done["minor_locator"])
        axis.set_minor_formatter(done["minor_formatter"])
    axis._sublet_thinned = None


def _label_only(ax, keep: Sequence[float]) -> None:
    """x tick labels at the values `keep` only (thin_tick_labels, same_tick_labels): they stay the major ticks, and
    the other major ticks in view become minor ticks, unlabeled and at minor length (rcParams xtick.minor.size), so
    that an unlabeled tick reads as an intermediate value rather than as a missing label (sf_e10_rho: m = 8 and 32).
    The axis's own locators and formatters are kept on it (_sublet_thinned) for _unthin."""
    _unthin(ax)
    axis = ax.xaxis
    lo, hi = sorted(ax.get_xlim())
    tol = 1e-9 * max(abs(lo), abs(hi), 1e-300)
    rest = [float(v) for v in axis.get_majorticklocs()
            if lo - tol <= v <= hi + tol and not any(abs(v - k) <= 1e-9 * max(1.0, abs(k)) for k in keep)]
    minor = [float(v) for v in axis.get_minorticklocs()]
    done = {"major_locator": axis.get_major_locator(), "major_formatter": axis.get_major_formatter(),
            "minor_locator": axis.get_minor_locator(), "minor_formatter": axis.get_minor_formatter()}
    thinned = FixedLocator(sorted(float(k) for k in keep))
    axis.set_major_locator(thinned)
    axis.set_minor_locator(FixedLocator(sorted(minor + rest)))
    axis.set_minor_formatter(NullFormatter())
    axis._sublet_thinned = {**done, "thinned": thinned}


def same_tick_labels(axes: Sequence) -> list[float]:
    """Label in every panel of a row the x tick values that every panel labels after thin_tick_labels, so that
    panels on one grid (m in sf_e10_rho) read alike; the other ticks at minor length (_label_only). Returns the
    labeled values."""
    sets = []
    for ax in axes:
        lo, hi = sorted(ax.get_xlim())
        fmt = ax.xaxis.get_major_formatter()
        sets.append({float(v) for v in ax.xaxis.get_majorticklocs() if lo <= v <= hi and fmt(v)})
    keep = sorted(set.intersection(*sets)) if sets else []
    for ax, labeled in zip(axes, sets):
        if set(keep) != labeled:
            _label_only(ax, keep)
    return keep


def _top_tick_room(ax) -> None:
    """Raise the top of a log y axis so that its highest tick label ends TOP_TICK_GAP_PT below the axes top, clear of
    a panel letter or title on the axes top (a tick label reaches about half its line height above its tick)."""
    y0, y1 = ax.get_ylim()
    ticks = [t for t in ax.yaxis.get_majorticklocs() if y0 <= t <= y1]
    if not ticks:
        return
    t = max(ticks)
    fig = ax.figure
    r = fig.canvas.get_renderer()
    to_pt = style.BP_PER_IN / fig.dpi
    up = [tk.label1.get_window_extent(r).y1 - ax.transData.transform((0.0, t))[1]
          for tk in ax.yaxis._update_ticks() if abs(tk.get_loc() - t) <= 1e-9 * t and tk.label1.get_visible()]
    # pt above the tick (a panel sharing its left neighbor's y axis hides its labels: then about half the size)
    room = (max(up) * to_pt if up else 0.5 * style.TICK_PT) + TOP_TICK_GAP_PT
    h_pt = style.axes_rect_in(ax)[3] * style.BP_PER_IN
    a = math.log(t / y0)                       # the tick's height above the axis bottom, in log units
    need = room * a / (h_pt - room)            # log units above the tick, on the scale that results
    if math.log(y1 / t) < need:
        ax.set_ylim(y0, t * math.exp(need))


def ratio_log2_axis(ax, lo: float, hi: float, *, margin_oct: float = 0.15) -> None:
    """log2 y axis with integer tick labels covering [lo, hi] (powers of two). The axis starts at most at the
    power of two at or below lo less 0.12 octave, so that markers at that value (a ratio of exactly 1) are not cut by
    the x axis; its top clears the highest tick label (_top_tick_room)."""
    lo2, hi2 = math.floor(math.log2(lo) + 1e-9), math.ceil(math.log2(hi) - 1e-9)
    ticks = [2.0 ** e for e in range(max(lo2, 0), hi2 + 1)]
    style.log2_axis(ax, "y", ticks=ticks)
    floor = 2.0 ** lo2 / 2 ** 0.12 if lo2 >= 0 else lo / 2 ** margin_oct
    ax.set_ylim(max(lo / 2 ** margin_oct, floor), hi * 2 ** margin_oct)
    _top_tick_room(ax)


def ratio_log10_axis(ax, lo: float, hi: float) -> None:
    """Base-10 log y axis for a ratio (plain labels at 1, 2, 5, 10, 20, ...) covering [min(lo, 1), hi]; its top
    clears the highest tick label (_top_tick_room)."""
    lo = min(lo, 1.0)
    y0, y1 = lo / 1.08, hi * 1.15
    for mant in ((1, 2, 5), (1, 1.5, 2, 3, 5, 7), (1, 1.2, 1.5, 2, 2.5, 3, 4, 5, 6, 8)):
        ticks = [m * 10.0 ** e for e in range(-1, 4) for m in mant if y0 <= m * 10.0 ** e <= y1]
        if len(ticks) >= 3:
            break
    style.log_axis(ax, "y", ticks=ticks)
    ax.set_ylim(y0, y1)
    _top_tick_room(ax)


# ---------------------------------------------------------------------------------------------------------------
# Labels and legends
def text_width_in(fig, text: str, size: float = style.TICK_PT) -> float:
    """Width in inches of the widest line of `text` at `size` pt (mathtext where the line has $...$)."""
    from matplotlib.font_manager import FontProperties
    canvas = fig.canvas
    r = canvas.get_renderer()
    prop = FontProperties(size=size)
    return max(r.get_text_width_height_descent(line, prop, ismath=line.count("$") >= 2)[0]
               for line in str(text).split("\n")) / fig.dpi


def text_height_pt(fig, text: str, size: float = style.TICK_PT) -> float:
    """C62 (group g1): height in pt of the layout box of `text` at `size` pt as matplotlib sets it (every line, the
    line spacing and mathtext's taller lines included; right_theory_lines(..., measured=True)). A mathtext line such
    as "LB$_A$ (private)" is about 1.4 pt taller at 7 pt than the 1.2 em that LINE_STEP_PT allows a line."""
    from matplotlib.text import Text
    t = Text(0.0, 0.0, str(text), fontsize=size)
    t.set_figure(fig)
    return t.get_window_extent(fig.canvas.get_renderer()).height * 72.0 / fig.dpi


def label_column(ax, x_lo: float, x_hi: float, texts: Sequence[str], *, pad_pt: float = 7.0) -> None:
    """Log x limits [x_lo, x_right] with a column right of x_hi that holds the widest of `texts` (theory labels
    drawn with theory_line(..., where="right") at their right end, x_hi), and the x spine ending at x_hi, with the
    x label centered under the spine (set_xlabel, which puts it at the middle, comes first). Used where the theory
    lines end among the data and no label inside the data area stays clear of it."""
    w = style.axes_rect_in(ax)[2]
    need_in = max(text_width_in(ax.figure, t) for t in texts) + pad_pt / style.BP_PER_IN
    f = min(need_in / w, 0.6)
    span = math.log2(x_hi / x_lo)
    ax.set_xlim(x_lo, x_lo * 2.0 ** (span / (1.0 - f)))
    ax.spines["bottom"].set_bounds(x_lo, x_hi)
    ax.xaxis.label.set_x(0.5 * (1.0 - f))
    ax._sublet_label_column = (x_lo, x_hi, tuple(texts), pad_pt)       # right_theory_lines widens it for leaders


def stack_labels(targets: Sequence[float], heights: Sequence[float], *, gap: float = 1.0,
                 bottom: float | None = None, top: float | None = None) -> list[float]:
    """Centers of labels of `heights` stacked in one column as close as possible to their `targets` (same units),
    in the targets' order, with `gap` between neighbors: labels that would overlap form a cluster, which sits at
    the least-squares position of its members (clusters merge until none overlap), so that a label clear of the
    others stays at its target; then the column is kept within [bottom, top]."""
    order = sorted(range(len(targets)), key=lambda i: targets[i])
    clusters: list[list] = []              # [members (indices in `order`), offsets from the first member, center0]
    for j, i in enumerate(order):
        clusters.append([[j], [0.0], float(targets[i])])
        while len(clusters) > 1:
            (ma, oa, ca), (mb, ob, cb) = clusters[-2], clusters[-1]
            top_a = ca + oa[-1] + 0.5 * heights[order[ma[-1]]]
            if top_a + gap <= cb - 0.5 * heights[order[mb[0]]] + 1e-9:
                break
            step = oa[-1] + 0.5 * (heights[order[ma[-1]]] + heights[order[mb[0]]]) + gap
            mem, off = ma + mb, oa + [step + o for o in ob]
            c0 = float(np.mean([targets[order[m]] - o for m, o in zip(mem, off)]))
            clusters[-2:] = [[mem, off, c0]]
    pos = [0.0] * len(targets)
    for mem, off, c0 in clusters:
        for m, o in zip(mem, off):
            pos[m] = c0 + o
    h = [heights[i] for i in order]
    if top is not None:                    # push down from the top, then up from the bottom
        for j in range(len(pos) - 1, -1, -1):
            lim = top - 0.5 * h[j] if j == len(pos) - 1 else pos[j + 1] - 0.5 * (h[j] + h[j + 1]) - gap
            pos[j] = min(pos[j], lim)
    if bottom is not None:
        for j in range(len(pos)):
            lim = bottom + 0.5 * h[j] if j == 0 else pos[j - 1] + 0.5 * (h[j - 1] + h[j]) + gap
            pos[j] = max(pos[j], lim)
    out = [0.0] * len(targets)
    for j, i in enumerate(order):
        out[i] = pos[j]
    return out


def line_offsets(n: int) -> list[float]:
    """Offsets (pt) of the text lines of an n-line label from its center, first line first."""
    return [(0.5 * (n - 1) - k) * LINE_STEP_PT for k in range(n)]


def place_clear(targets: Sequence[float], heights: Sequence[float], lines: Sequence[Sequence[float]],
                owns: Sequence[float], ends: Sequence[float], *, gap: float = 1.0, bottom: float, top: float,
                step: float = 0.25) -> list[float] | None:
    """Centers (pt) of labels stacked in one column, in the targets' order with `gap` between neighbors and inside
    [bottom, top], such that no label is read as another line's: no text line of a label (lines[i]: offsets from its
    center) is level with (within LEVEL_PT of) an end in `ends` other than its own (owns[i]), and each lies nearer to
    its own end than to any other; ends that chain within COINCIDE_PT of a label's own end count as its own (lines
    that end on one point, such as a limit and the policy that attains it). Among the placements that satisfy this,
    the one with the most labels at their targets, then the least total shift (dynamic programming over positions
    `step` apart, the targets included). None if no placement fits."""
    order = sorted(range(len(targets)), key=lambda i: targets[i])
    big = 1e6                                         # one label off its target outweighs any total shift
    pts = sorted(list(ends) + list(owns))
    cluster, g = [], 0                                # chains of ends within COINCIDE_PT of the next (one point)
    for j, e in enumerate(pts):
        g += bool(j) and e - pts[j - 1] > COINCIDE_PT
        cluster.append(g)
    cands, costs, backs = [], [], []
    for k, i in enumerate(order):
        lo, hi = bottom + 0.5 * heights[i], top - 0.5 * heights[i]
        if hi < lo:
            return None
        grid = np.arange(lo, hi + 1e-9, step)
        c = np.unique(np.concatenate([grid, [targets[i]] if lo <= targets[i] <= hi else []]))
        mine = cluster[pts.index(owns[i])]
        own = np.array([e for e, q in zip(pts, cluster) if q == mine])
        other = np.array([e for e, q in zip(pts, cluster) if q != mine])
        ok = np.ones(c.size, dtype=bool)
        if other.size:
            for off in lines[i]:
                y = (c + off)[:, None]
                d_own, d_other = np.abs(y - own).min(axis=1), np.abs(y - other).min(axis=1)
                ok &= (d_other > LEVEL_PT) & (d_own <= d_other)
        c = c[ok]
        if not c.size:
            return None
        cost = np.where(np.abs(c - targets[i]) <= 1e-9, 0.0, big) + np.abs(c - targets[i])
        back = np.full(c.size, -1)
        if k:
            sep = 0.5 * (heights[order[k - 1]] + heights[i]) + gap
            pc, prev = cands[-1], costs[-1]
            best = np.empty(prev.size, dtype=int)           # index of the least cost among prev[:j + 1]
            cur = 0
            for j in range(prev.size):
                cur = j if prev[j] < prev[cur] else cur
                best[j] = cur
            last = np.searchsorted(pc, c - sep + 1e-9, side="right") - 1
            fits = last >= 0
            c, cost, last = c[fits], cost[fits], last[fits]
            if not c.size:
                return None
            back = best[last]
            cost = cost + prev[back]
        cands.append(c)
        costs.append(cost)
        backs.append(back)
    out = [0.0] * len(targets)
    j = int(np.argmin(costs[-1]))
    for k in range(len(order) - 1, -1, -1):
        out[order[k]] = float(cands[k][j])
        j = int(backs[k][j])
    return out


def _data_ends_pt(ax) -> list[float]:
    """Heights (pt) of the ends of the policy lines of `ax`: the last finite point of each."""
    to_pt = 72.0 / ax.figure.dpi
    out = []
    for ln in ax.lines:
        if not hasattr(ln, "_sublet_policy"):
            continue
        xy = np.asarray(ln.get_xydata(), dtype=float)
        ok = np.isfinite(xy).all(axis=1)
        if ok.any():
            out.append(ax.transData.transform(xy[ok][np.argmax(xy[ok, 0])])[1] * to_pt)
    return out


def _data_polylines_pt(ax) -> list[np.ndarray]:
    """The policy lines of `ax` in display pt, split at missing points (markers are their vertices)."""
    to_pt = 72.0 / ax.figure.dpi
    out = []
    for ln in ax.lines:
        if not hasattr(ln, "_sublet_policy"):
            continue
        xy = np.asarray(ln.get_xydata(), dtype=float)
        ok = np.isfinite(xy).all(axis=1)
        pts = np.full_like(xy, np.nan)
        pts[ok] = ax.transData.transform(xy[ok]) * to_pt
        for run in np.split(pts, np.flatnonzero(~ok)):
            run = run[np.isfinite(run).all(axis=1)]
            if len(run):
                out.append(run)
    return out


def _dist_to_polylines(p: np.ndarray, polys: Sequence[np.ndarray]) -> np.ndarray:
    """Least distance (pt) of each point of p (n x 2) to the segments and vertices of the polylines."""
    d = np.full(len(p), np.inf)
    for poly in polys:
        a = poly[:-1] if len(poly) > 1 else poly
        b = poly[1:] if len(poly) > 1 else poly
        ab = b - a
        L2 = np.maximum((ab ** 2).sum(axis=1), 1e-12)
        t = np.clip(((p[:, None, :] - a[None]) * ab[None]).sum(axis=2) / L2[None], 0.0, 1.0)
        q = a[None] + t[..., None] * ab[None]
        d = np.minimum(d, np.sqrt(((p[:, None, :] - q) ** 2).sum(axis=2)).min(axis=1))
    return d


def leader_end(ax, x, y) -> tuple[float, float]:
    """Where a leader to the theory line (x, y) ends: on the line's last level stretch (its last points within
    LEVEL_PT of the last one's height on the drawn scale), at the rightmost point at least LEADER_CLEAR_PT from the
    policy lines and their markers, else at the point of the stretch farthest from them; a line's last point under a
    data marker would hide the leader's end."""
    to_pt = 72.0 / ax.figure.dpi
    xs, ys = finite(x), finite(y)
    ok = np.isfinite(xs) & np.isfinite(ys)
    xs, ys = xs[ok], ys[ok]
    order = np.argsort(xs)
    pts = ax.transData.transform(np.column_stack([xs[order], ys[order]])) * to_pt
    j = len(pts) - 1
    while j > 0 and abs(pts[j - 1, 1] - pts[-1, 1]) <= LEVEL_PT:
        j -= 1
    stretch = pts[j:]
    if len(stretch) > 1:
        samp = np.concatenate([np.linspace(stretch[k], stretch[k + 1], 41)[:-1] for k in range(len(stretch) - 1)]
                              + [stretch[-1:]])
    else:
        samp = stretch
    d = _dist_to_polylines(samp, _data_polylines_pt(ax))
    clear = np.flatnonzero(d >= LEADER_CLEAR_PT)
    k = int(clear.max()) if clear.size else int(len(d) - 1 - np.argmax(d[::-1]))
    return tuple(ax.transData.inverted().transform(samp[k] / to_pt))


def right_theory_lines(ax, specs: Sequence[Mapping], *, gap_pt: float = 1.0, dx_pt: float = 4.0,
                       clear_ends: bool = False, measured: bool = False, top_pad_pt: float = 0.0) -> list:
    """Theory lines labeled just right of their last point (theory_line(..., where="right")), after the axes
    limits are final; labels that would overlap are moved apart vertically (in label order by height) as little
    as possible (stack_labels: each group of touching labels centered on its lines, a label clear of the others
    left at its line) and kept inside the axes; dx_pt clears the last marker. Where a label is moved so far that
    its line's end lies outside its height, every moved label of its group of touching labels gets a thin grey
    leader to its line's end (the IEEE graphics guide: connect the label to the line), and then every label of the
    panel sits LEADER_RUN_PT further right, in a label column widened by as much (label_column, ticks thinned
    again). specs: dicts with x, y, kind, label (and optional theory_line keywords), and two options: first_line
    (True: a multi-line label hangs below its line's end with its first line level with it, where a label centered
    on the end would put its first line level with an end above) and leader_end ("flat": the leader, where there is
    one, ends on the line's last level stretch clear of the data, leader_end(), not at the last point, which a data
    marker may cover). With `clear_ends`, the labels are placed so that none is read as another line's (place_clear:
    no label line level with another line's end, theory or policy line, and each nearer its own end than any other;
    as many labels as possible at their ends), where such a placement fits; else as above. With `measured` (C62,
    group g1; off by default, which keeps every earlier figure as it was), each label's height is its layout box's
    (text_height_pt) and its lines are that height over their number apart, in place of LINE_STEP_PT per line, so
    that labels with mathtext lines, taller than 1.2 em, are stacked without overlapping. `top_pad_pt` (C62, group g1;
    0 by default) keeps the labels that far below the axes top, clear of a panel title above a label column."""
    to_pt = 72.0 / ax.figure.dpi
    rows = []
    for sp in specs:
        xs, ys = finite(sp["x"]), finite(sp["y"])
        ok = np.isfinite(xs) & np.isfinite(ys)
        if not ok.any():
            continue
        i = int(np.flatnonzero(ok)[np.argmax(xs[ok])])
        y_pt = ax.transData.transform((xs[i], ys[i]))[1] * to_pt
        n = str(sp["label"]).count("\n") + 1
        if measured:
            h = text_height_pt(ax.figure, sp["label"])
            offs = [o * h / (n * LINE_STEP_PT) for o in line_offsets(n)]
        else:
            h, offs = n * LINE_STEP_PT, line_offsets(n)
        target = y_pt + (offs[-1] if sp.get("first_line") else 0.0)
        # [target center, height, spec, placed center, end (data), end height (pt), text lines, line offsets]
        rows.append([target, h, sp, target, (xs[i], ys[i]), y_pt, n, offs])
    if rows:
        bb = ax.get_window_extent()
        new = None
        if clear_ends:
            new = place_clear([r[0] for r in rows], [r[1] for r in rows], [r[7] for r in rows],
                              [r[5] for r in rows], [r[5] for r in rows] + _data_ends_pt(ax), gap=gap_pt,
                              bottom=bb.y0 * to_pt, top=bb.y1 * to_pt - top_pad_pt)
        if new is None:
            new = stack_labels([r[0] for r in rows], [r[1] for r in rows], gap=gap_pt, bottom=bb.y0 * to_pt,
                               top=bb.y1 * to_pt - top_pad_pt)
        for r, y in zip(rows, new):
            r[3] = y
    rows.sort(key=lambda r: r[0])
    # groups of touching labels (in column order); a group with a label moved off its line's end gets leaders on
    # every moved label, so that no label is read as that of a line ending beside it
    group, g = [], 0
    for j, r in enumerate(rows):
        if j and r[3] - rows[j - 1][3] > 0.5 * (r[1] + rows[j - 1][1]) + gap_pt + 0.01:
            g += 1
        group.append(g)
    far = {group[j] for j, r in enumerate(rows) if abs(r[3] - r[0]) > 0.5 * r[1]}
    lead = [group[j] in far and abs(r[3] - r[0]) > 0.5 for j, r in enumerate(rows)]
    if any(lead):
        dx_pt += LEADER_RUN_PT
        col = getattr(ax, "_sublet_label_column", None)
        if col is not None:
            x_lo, x_hi, texts, pad = col
            label_column(ax, x_lo, x_hi, texts, pad_pt=pad + LEADER_RUN_PT)
            thin_tick_labels(ax)
    out = []
    for (_, _, sp, y_new, end, y_pt, _, _), leader in zip(rows, lead):
        kw = {k: v for k, v in sp.items() if k not in ("x", "y", "kind", "label", "first_line", "leader_end")}
        kw.setdefault("dx", dx_pt)
        out.append(style.theory_line(ax, sp["x"], sp["y"], sp["kind"], sp["label"], where="right",
                                     dy=y_new - y_pt, **kw))
        if leader:
            # from just left of the label to the line's end, or to its level stretch clear of the data
            to = leader_end(ax, sp["x"], sp["y"]) if sp.get("leader_end") == "flat" else end
            shift = (ax.transData.transform(end) - ax.transData.transform(to)) * to_pt
            ld = ax.annotate("", xy=to, xytext=(kw["dx"] - 1.0 + shift[0], y_new - y_pt + shift[1]),
                             textcoords="offset points",
                             arrowprops=dict(arrowstyle="-", color=style.THEORY_GREY, linewidth=LEADER_PT,
                                             shrinkA=0.0, shrinkB=2.5), zorder=style.Z_THEORY)
            ld._sublet_role = "theory_leader"
    return out


def panel_title(ax, letter, text: str, *, fontsize: float | None = None):
    """A panel title at the tick-label size (style.TICK_PT) on the baseline of the panel letter
    (style.panel_letters), just right of it; for the condition of a panel (lender, rho), where a note inside the
    axes would cover data. C62 (group g1): `fontsize` sets another size, such as style.LABEL_PT, the caption size
    that C62 gives panel titles (None keeps TICK_PT, as every earlier figure draws it); returns the title."""
    fig = ax.figure
    bb = letter.get_window_extent(fig.canvas.get_renderer())
    x = (bb.x1 / fig.dpi + 3.0 / 72.0) / fig.get_size_inches()[0]
    return fig.text(x, letter.get_position()[1], text, ha="left", va="baseline",
                    fontsize=style.TICK_PT if fontsize is None else fontsize)


def legend_rows(ax, rows: Sequence[Sequence[tuple]], *, gap_pt: float = 1.0, top_pt: float = 0.0,
                columnspacing: float = 1.2) -> list:
    """Frameless legend rows stacked down from the upper left corner of `ax`, one Legend per row with its entries
    side by side (rows: lists of (handle, label), e.g. the policies, then env_handles()). For a corner legend whose
    entries do not fit one row and whose two-column form would take a row more (Fig. 6, sf_e10_cross). The rows are
    figure legends anchored at `ax`, drawn after every axes, so that a row may extend over a right neighbor's
    headroom without that panel's background covering it; `top_pt` keeps the first row clear of panel titles drawn
    on the panel-letter baseline. Returns the legends (for legend_headroom)."""
    from matplotlib.legend import Legend
    fig = ax.figure
    r = fig.canvas.get_renderer()
    h_ax = ax.get_window_extent(r).height
    y, legs = 1.0 - top_pt * fig.dpi / 72.0 / h_ax, []
    for pairs in rows:
        handles, labels = zip(*pairs)
        leg = Legend(fig, list(handles), list(labels), loc="upper left", bbox_to_anchor=(0.0, y),
                     bbox_transform=ax.transAxes, ncol=len(handles), frameon=False, borderaxespad=0.0, borderpad=0.0,
                     columnspacing=columnspacing)
        fig.legends.append(leg)
        legs.append(leg)
        y -= (leg.get_window_extent(r).height + gap_pt * fig.dpi / 72.0) / h_ax
    return legs


def legend_headroom(ax, leg, *, data_top: float, pad_in: float = 0.04) -> None:
    """Raise the top of a y axis (log or linear) so that the legend `leg` (in an upper corner; or a list of
    legend_rows) sits above `data_top`; the y ticks above data_top are dropped and the y spine ends at data_top, so
    the legend sits on empty space. For panels whose corner legend has no empty corner (plan §5)."""
    fig = ax.figure
    legs = list(leg) if isinstance(leg, (list, tuple)) else [leg]
    r = fig.canvas.get_renderer()
    top_px = ax.get_window_extent(r).y1
    low_px = min(lg.get_window_extent(r).y0 for lg in legs)
    need_in = (top_px - low_px) / fig.dpi + pad_in      # the legends' depth below the axes top (pads included)
    h = style.axes_rect_in(ax)[3]
    y0, y1 = ax.get_ylim()
    top = max(y1, data_top)
    f = 1.0 / (1.0 - min(need_in / h, 0.6))
    if ax.get_yscale() == "log":
        ax.set_ylim(y0, y0 * math.exp(math.log(top / y0) * f))
    else:
        ax.set_ylim(y0, y0 + (top - y0) * f)
    ticks = [t for t in ax.get_yticks() if y0 <= t <= top * (1 + 1e-9)]
    ax.yaxis.set_major_locator(FixedLocator(ticks))
    ax.spines["left"].set_bounds(y0, top)


def clear_floor(ax, lo: float) -> None:
    """Lower the bottom of a log y axis, keeping its top (and a legend set on headroom above the data), so that the
    markers of the policy lines at `lo`, the lowest plotted value, clear the x spine by KEY_PAD_PT: the largest
    marker drawn (with its edge) and half the spine width below its center (Fig. 6: RR-renew's pentagon at a ratio
    of about 1 at m = 2)."""
    rad = max([0.5 * (ln.get_markersize() + ln.get_markeredgewidth()) for ln in ax.lines
               if hasattr(ln, "_sublet_policy") and ln.get_marker() not in (None, "None", "none", "")], default=0.0)
    need_pt = rad + 0.5 * style.AXES_PT + KEY_PAD_PT
    h_pt = style.axes_rect_in(ax)[3] * style.BP_PER_IN
    y0, y1 = ax.get_ylim()
    a, b, u = math.log(lo), math.log(y1), math.log(y0)
    if (a - u) / (b - u) * h_pt >= need_pt:
        return
    k = need_pt / h_pt
    floor = math.exp((a - k * b) / (1.0 - k))      # lo then sits need_pt above the bottom on the new scale
    bounds = ax.spines["left"].get_bounds()
    ax.set_ylim(floor, y1)
    if bounds is not None:
        ax.spines["left"].set_bounds(floor, bounds[1])


# ---------------------------------------------------------------------------------------------------------------
# Keys and labels on the free space of a panel
AGREE_SAME = "{a} = {b}"                       # key of two series equal at every point
AGREE_NEAR = "{a} ≈ {b} (within {pct}%)"      # key of two series within pct percent of each other at every point
AGREE_MAX_PCT = 5               # two series this close (or closer) at every point overlap on the drawn scales: a key


def agreement(a, b) -> dict | None:
    """How closely two series of equal length agree: max_rel_diff, the largest |a - b| / min(|a|, |b|) (0 where
    both values are 0), and within_pct, that difference in percent rounded up to a whole percent (0 where the
    series are equal at every point, to 1e-12). None unless both series have values at exactly the same points
    (a point that one series draws and the other lacks is not agreement), if no point has a value, or if a value is
    0 where the other is not (no finite relative difference)."""
    a, b = finite(a), finite(b)
    fa, fb = np.isfinite(a), np.isfinite(b)
    if a.shape != b.shape or not fa.any() or (fa != fb).any():
        return None
    a, b = a[fa], b[fa]
    lo, diff = np.minimum(np.abs(a), np.abs(b)), np.abs(a - b)
    if ((lo == 0) & (diff > 0)).any():
        return None
    d = float(np.max(np.where(lo == 0, 0.0, diff / np.where(lo == 0, 1.0, lo))))
    return {"max_rel_diff": d, "within_pct": 0 if d <= 1e-12 else int(math.ceil(100.0 * d - 1e-9))}


def agree_entry(key_a: str, key_b: str, a, b, max_pct: int) -> dict | None:
    """The coincidence key of the policies key_a and key_b (registry labels) with the series a and b, given at the
    same points: "A = B" where the two are equal at every point, "A ≈ B (within p%)" where they agree within
    p <= max_pct percent (agreement; no key where one series has a point the other lacks);
    None where they differ more, so that a key appears only if the series agree within its stated tolerance. A dict
    {pair, max_rel_diff, within_pct, key} for the extract."""
    ag = agreement(a, b)
    if ag is None or ag["within_pct"] > max_pct:
        return None
    la, lb = style.POLICIES[key_a].label, style.POLICIES[key_b].label
    text = AGREE_SAME.format(a=la, b=lb) if ag["within_pct"] == 0 else \
        AGREE_NEAR.format(a=la, b=lb, pct=ag["within_pct"])
    return {"pair": [key_a, key_b], **ag, "key": text}


def _box_sum(mask: np.ndarray, hj: int, wi: int) -> np.ndarray:
    """Sum of mask over every hj x wi window, indexed by the window's lower left cell."""
    s = np.zeros((mask.shape[0] + 1, mask.shape[1] + 1))
    s[1:, 1:] = mask.cumsum(axis=0).cumsum(axis=1)
    return s[hj:, wi:] - s[:-hj, wi:] - s[hj:, :-wi] + s[:-hj, :-wi]


def _dilate(mask: np.ndarray, r: int) -> np.ndarray:
    """Cells within r cells (a square) of a set cell."""
    if r <= 0:
        return mask
    p = np.pad(mask, r)
    return _box_sum(p, 2 * r + 1, 2 * r + 1) > 0


def _data_area_pt(ax) -> tuple[float, float, float, float]:
    """(x0, y0, x1, y1) in pt of the area of `ax` open to keys and labels: the axes (a label column included, where
    its theory labels and leaders leave room), ending at the y spine's top bound where it is set (legend headroom)."""
    to_pt = 72.0 / ax.figure.dpi
    bb = ax.get_window_extent(ax.figure.canvas.get_renderer())
    x0, y0, x1, y1 = bb.x0 * to_pt, bb.y0 * to_pt, bb.x1 * to_pt, bb.y1 * to_pt
    yb = ax.spines["left"].get_bounds()
    if yb is not None:
        y1 = min(y1, ax.transData.transform((ax.get_xlim()[0], max(yb)))[1] * to_pt)
    return x0, y0, x1, y1


def _occupancy(ax, skip=()) -> tuple[np.ndarray, float, float]:
    """Cells (GRID_RES_PT) of the open area of `ax` (_data_area_pt) within KEY_PAD_PT of anything drawn in it: lines
    (policy, theory and reference lines, leaders; not the y grid), markers, error bars, texts and legends; the cells
    within KEY_PAD_PT of the area's edges too. Returns (taken, x0, y0), the grid's lower left corner in pt."""
    fig = ax.figure
    r = fig.canvas.get_renderer()
    to_pt, res = 72.0 / fig.dpi, GRID_RES_PT
    x0, y0, x1, y1 = _data_area_pt(ax)
    nx, ny = max(int(math.ceil((x1 - x0) / res)), 1), max(int(math.ceil((y1 - y0) / res)), 1)
    pts, marks, boxes = [], [], []
    lw_max, rad_max = 0.0, 0.0

    def segments(p):                                   # sample points along the drawn segments (not across gaps)
        for a, b in zip(p[:-1], p[1:]):
            if np.isfinite(a).all() and np.isfinite(b).all():
                n = max(int(np.hypot(*(b - a)) / (0.5 * res)), 1) + 1
                pts.append(np.linspace(a, b, n))

    for ln in ax.lines:
        if ln in skip or not ln.get_visible():
            continue
        with np.errstate(all="ignore"):
            p = ln.get_transform().transform(np.asarray(ln.get_xydata(), dtype=float)) * to_pt
        if ln.get_linestyle() not in ("None", "none", "", " "):
            segments(p)
            lw_max = max(lw_max, ln.get_linewidth())
        if ln.get_marker() not in (None, "None", "none", "", " "):
            marks.append(p[np.isfinite(p).all(axis=1)])
            rad_max = max(rad_max, 0.5 * (ln.get_markersize() + ln.get_markeredgewidth()))
    for c in ax.collections:
        if c in skip or not c.get_visible() or not hasattr(c, "get_segments") or type(c).__name__ == "_YGrid":
            continue
        for seg in c.get_segments():
            segments(c.get_transform().transform(np.asarray(seg, dtype=float)) * to_pt)
            lw_max = max(lw_max, float(np.max(c.get_linewidths())))
    for t in ax.texts:
        if t in skip or not t.get_visible():
            continue
        if t.get_text().strip():
            boxes.append(t.get_window_extent(r))
        if getattr(t, "arrow_patch", None) is not None:       # a leader: from its end to just left of its label
            a = ax.transData.transform(t.xy) * to_pt
            segments(np.array([a, a + np.asarray(t.xyann, dtype=float)]))
    for leg in [a for a in ax.artists if type(a).__name__ == "Legend"] + [ax.get_legend()] + list(fig.legends):
        if leg is not None and leg not in skip and leg.get_visible():
            boxes.append(leg.get_window_extent(r))

    def cells(p):
        ij = np.floor((p - [x0, y0]) / res).astype(int)
        ok = (ij[:, 0] >= 0) & (ij[:, 0] < nx) & (ij[:, 1] >= 0) & (ij[:, 1] < ny)
        m = np.zeros((ny, nx), dtype=bool)
        m[ij[ok, 1], ij[ok, 0]] = True
        return m

    taken = np.zeros((ny, nx), dtype=bool)
    if pts:
        taken |= _dilate(cells(np.concatenate(pts)), int(math.ceil((0.5 * lw_max + KEY_PAD_PT) / res)))
    if marks:
        taken |= _dilate(cells(np.concatenate(marks)), int(math.ceil((rad_max + KEY_PAD_PT) / res)))
    for bb in boxes:
        i0 = int(math.floor((bb.x0 * to_pt - KEY_PAD_PT - x0) / res))
        i1 = int(math.ceil((bb.x1 * to_pt + KEY_PAD_PT - x0) / res))
        j0 = int(math.floor((bb.y0 * to_pt - KEY_PAD_PT - y0) / res))
        j1 = int(math.ceil((bb.y1 * to_pt + KEY_PAD_PT - y0) / res))
        taken[max(j0, 0):max(min(j1, ny), 0), max(i0, 0):max(min(i1, nx), 0)] = True
    e = int(math.ceil(KEY_PAD_PT / res))
    taken[:e, :] = taken[-e:, :] = True
    taken[:, :e] = taken[:, -e:] = True
    return taken, x0, y0


def free_spot(ax, w_pt: float, h_pt: float, near, *, others=None, margin_pt: float = 1.0,
              skip=()) -> tuple[float, float] | None:
    """Lower left corner (pt) of a w_pt x h_pt box in the open area of `ax` that comes no closer than KEY_PAD_PT to
    anything drawn (_occupancy), nearest to the points `near` (pt, n x 2): the least distance from the box to any of
    them. With `others` (pt), only boxes nearer to `near` than to any of `others` by margin_pt or more, so that a
    label is read as that of its own points, and among them the least distance to `near` less a quarter of the
    distance to `others` (up to a label line): a box next to its own points where no other points are close. None if
    no box fits."""
    taken, x0, y0 = _occupancy(ax, skip)
    res = GRID_RES_PT
    wi, hj = int(math.ceil(w_pt / res)), int(math.ceil(h_pt / res))
    if hj > taken.shape[0] or wi > taken.shape[1]:
        return None
    jj, ii = np.nonzero(_box_sum(taken, hj, wi) == 0)
    if not jj.size:
        return None
    bx0, by0 = x0 + ii * res, y0 + jj * res

    def dist(p):
        p = np.asarray(p, dtype=float).reshape(-1, 2)
        dx = np.maximum(np.maximum(bx0[:, None] - p[None, :, 0], 0.0), p[None, :, 0] - (bx0[:, None] + w_pt))
        dy = np.maximum(np.maximum(by0[:, None] - p[None, :, 1], 0.0), p[None, :, 1] - (by0[:, None] + h_pt))
        return np.sqrt(dx ** 2 + dy ** 2).min(axis=1)

    if not len(np.asarray(near, dtype=float).reshape(-1, 2)):
        return None                                     # no points to be near
    d = dist(near)
    if others is not None and len(others):
        d_o = dist(others)
        d = np.where(d + margin_pt <= d_o, d - 0.25 * np.minimum(d_o, LINE_STEP_PT), np.inf)
    k = int(np.argmin(d))
    return None if not np.isfinite(d[k]) else (float(bx0[k]), float(by0[k]))


def _halo_texts(texts) -> None:
    from matplotlib import patheffects
    for t in texts:
        t.set_path_effects([patheffects.withStroke(linewidth=style.LABEL_HALO_PT, foreground="white")])


def place_key(ax, pairs: Sequence[tuple], near, *, others=None, **legend_kw):
    """A frameless key (a Legend of (handle, text) pairs; a tuple of handles is drawn side by side) on the free space
    of `ax` nearest to the points `near` (pt; free_spot), its texts with a white halo over the y grid. None (and
    nothing drawn) if it fits nowhere."""
    from matplotlib.legend import Legend
    from matplotlib.legend_handler import HandlerTuple
    handles, texts = zip(*pairs)
    kw = dict(loc="lower left", bbox_to_anchor=(0.0, 0.0), bbox_transform=ax.transAxes, frameon=False,
              borderaxespad=0.0, borderpad=0.0, handler_map={tuple: HandlerTuple(ndivide=None, pad=0.3)})
    kw.update(legend_kw)
    leg = Legend(ax, list(handles), list(texts), **kw)
    ax.add_artist(leg)
    bb = leg.get_window_extent(ax.figure.canvas.get_renderer())
    to_pt = 72.0 / ax.figure.dpi
    spot = free_spot(ax, bb.width * to_pt, bb.height * to_pt, near, others=others, skip=(leg,))
    if spot is None:
        leg.remove()
        return None
    leg.set_bbox_to_anchor(tuple(ax.transAxes.inverted().transform(np.asarray(spot) / to_pt)), ax.transAxes)
    _halo_texts(leg.get_texts())
    leg._sublet_role = "key"
    return leg


def place_label(ax, text: str, near, *, others=None, **text_kw):
    """A label (TICK_PT) on the free space of `ax` nearest to the points `near` (pt) and nearer to them than to `others`
    (free_spot), with a white halo; None (and nothing drawn) if it fits nowhere."""
    kw = dict(fontsize=style.TICK_PT, ha="left", va="bottom", transform=ax.transAxes, zorder=style.Z_THEORY_LABEL)
    kw.update(text_kw)
    t = ax.text(0.0, 0.0, text, **kw)
    bb = t.get_window_extent(ax.figure.canvas.get_renderer())
    to_pt = 72.0 / ax.figure.dpi
    spot = free_spot(ax, bb.width * to_pt, bb.height * to_pt, near, others=others, skip=(t,))
    if spot is None:
        t.remove()
        return None
    t.set_position(tuple(ax.transAxes.inverted().transform(np.asarray(spot) / to_pt)))
    _halo_texts([t])
    t._sublet_role = "direct_label"
    return t


def points_pt(ax, x, y) -> np.ndarray:
    """The finite points (x, y) of `ax` in display pt (n x 2), for free_spot."""
    x, y = finite(x), finite(y)
    ok = np.isfinite(x) & np.isfinite(y)
    return ax.transData.transform(np.column_stack([x[ok], y[ok]])) * (72.0 / ax.figure.dpi)


def agree_key(ax, entry: Mapping | None, series: Mapping, *, x: str = "x", y: str = "y", **legend_kw):
    """The coincidence key of an agree_entry (both policies' markers side by side, then its text) on the free space
    next to the two series (series[key][x], series[key][y]); its text broken before the tolerance, then also before
    the "≈" or "=", where fewer lines fit nowhere, and without the markers (the text names both policies) where
    no form with them fits. Nothing where entry is None; StyleError where the key fits nowhere."""
    if not entry:
        return None
    a, b = entry["pair"]
    near = np.concatenate([points_pt(ax, series[k][x], series[k][y]) for k in (a, b)])
    hs = tuple(Line2D([], [], **style.policy_kwargs(k, lines=False)) for k in (a, b))
    kw = dict(handlelength=1.3)
    kw.update(legend_kw)
    two = entry["key"].replace(" (within", "\n(within")
    texts = (entry["key"], two, two.replace(" ≈ ", "\n≈ ").replace(" = ", "\n= "))
    for text in texts:
        leg = place_key(ax, [(hs, text)], near, **kw)
        if leg is not None:
            return leg
    for text in texts:
        t = place_label(ax, text, near)
        if t is not None:
            t._sublet_role = "key"
            return t
    raise style.StyleError(f"the key {entry['key']!r} fits nowhere on the free space of its panel")


# ---------------------------------------------------------------------------------------------------------------
# C62: text as the PDF prints it. Matplotlib's PDF backend sets a mathtext line from its own metrics, its width, height
# and depth rounded up to whole pt, and draws its glyphs from the rounded box, so that a mathtext label sits up to 1 pt
# off the baseline (or right end) of its plain neighbors. One implementation of each measurement and correction, for
# every figure script (their code as built in fig4_v3, fig4_v2, supp/ms7_x3_lib and supp/ms7_a_lib, moved here):
#   in_pdf, pdf_text_metrics, math_rise_pt, text_ink, printed_baselines_pt, letter_box   measurements
#   align_baselines      texts at fixed anchors (tick labels, axis labels, a title and its letter, a one-row key)
#   align_printed_rows   texts the layout places from their own metrics, its rows found from the printed baselines
#                        (a legend whose rows are not known by index), checked by a second PDF draw
#   align_legend_rows    a multi-row legend whose entries fill its columns first (entry i in row i mod rows)
#   align_right_math     right-aligned mathtext texts at their plain neighbors' right end
#   align_ylabels_x      y labels of placed axes at one x
def _fig_name(fig) -> str:
    return getattr(fig, "_sublet_name", "figure")


def in_pdf(fig, measure: Callable[[Any], Any]) -> Any:
    """measure(renderer), evaluated as `fig` is drawn into a PDF in memory (a draw_event of savefig): every artist
    placed as the PDF prints it, with the PDF backend's text metrics, at 72 dpi (display units are pt). The figure
    prints as the PDF, and Agg at the canvas's 100 dpi sets a mathtext line up to 2.4 pt higher (review of W-G2)."""
    out = []
    cid = fig.canvas.mpl_connect("draw_event", lambda ev: out.append(measure(ev.renderer)))
    try:
        fig.savefig(io.BytesIO(), format="pdf", bbox_inches=None)
    finally:
        fig.canvas.mpl_disconnect(cid)
    if not out:
        raise RuntimeError(f"{_fig_name(fig)}: the PDF draw of the figure ran no draw_event")
    return out[-1]


_MATH = MathTextParser("path")


def math_rise_pt(s: str, prop) -> float:
    """How far above its baseline the PDF draws the glyphs of line `s` (pt): mathtext's vector output (the PDF's, at 72
    dpi) rounds the line's height above the baseline up to a whole pt and sets the glyphs from the rounded top
    (_mathtext.Output.to_vector), so they rise by the rounding (up to 1 pt; the unrounded height from a parse at 100
    times the dpi); 0 for a plain line. TextPath's own rounding, at its 100-pt font scale, is below 0.09 pt at 9 pt
    (less at TICK_PT)."""
    if not cbook.is_math_text(s):
        return 0.0
    v, fine = _MATH.parse(s, 72, prop), _MATH.parse(s, 7200, prop)
    return float((v.height - v.depth) - (fine.height - fine.depth) / 100.0)


def text_ink(t, r) -> tuple[float, float]:
    """(bottom, top) of the glyphs' ink of text `t` (unrotated) as the PDF draws it (`r` the renderer of in_pdf's draw;
    display units pt): its first line's baseline (the layout box's top less the line's ascent) plus that line's glyph
    extent (TextPath) and rise (math_rise_pt), and its last line's baseline (the box's bottom plus the line's descent)
    plus that line's; ascent and descent at least those of "lp", as matplotlib sets lines (Text._get_layout)."""
    fig = t.get_figure(root=True)
    prop, to_px = t.get_fontproperties(), fig.dpi / 72.0
    lines = t.get_text().split("\n")
    bb = t.get_window_extent(r)
    _, lp_h, lp_d = r.get_text_width_height_descent("lp", prop, ismath=False)

    def metrics(s):
        _, h, d = r.get_text_width_height_descent(s, prop, ismath=cbook.is_math_text(s))
        ext = TextPath((0.0, 0.0), s, prop=prop).get_extents()
        rise = math_rise_pt(s, prop)
        return max(h, lp_h), max(d, lp_d), (ext.y0 + rise) * to_px, (ext.y1 + rise) * to_px

    h0, d0, _, top = metrics(lines[0])
    _, dn, bottom, _ = metrics(lines[-1])
    return bb.y0 + dn + bottom, bb.y1 - (h0 - d0) + top


_PDF_METRICS: dict = {}


def _probe_figure():
    """An empty figure with an Agg canvas, drawn by pdf_text_metrics (the text metrics do not depend on its size)."""
    fig = Figure(figsize=(1.0, 1.0), dpi=100)
    FigureCanvasAgg(fig)
    return fig


def pdf_text_metrics(items: Sequence[tuple[str, Any]]) -> list[tuple[float, float]]:
    """(height, descent) in pt of each one-line text (s, FontProperties) of `items` as the PDF backend measures it
    (in_pdf on an empty figure; mathtext rounded up to whole pt as the PDF sets it), cached."""
    todo = [(s, p) for s, p in items if (s, p) not in _PDF_METRICS]
    if todo:
        def measure(r):
            return {(s, p): r.get_text_width_height_descent(s, p, ismath=cbook.is_math_text(s))[1:] for s, p in todo}
        _PDF_METRICS.update(in_pdf(_probe_figure(), measure))
    return [tuple(float(v) for v in _PDF_METRICS[(s, p)]) for s, p in items]


def _va_baseline_pt(va: str, h: float, d: float) -> float:
    """Where matplotlib sets a one-line text's baseline relative to its anchor (pt, along the text's up direction) for
    the vertical alignment `va`, the line h high in all and d deep (Text._get_layout, unrotated or rotation_mode
    'anchor')."""
    return {"baseline": 0.0, "bottom": d, "top": d - h, "center": d - 0.5 * h, "center_baseline": -0.5 * (h - d)}[va]


def align_baselines(texts: Sequence[Any]) -> None:
    """Move each one-line mathtext text of `texts` (texts of one alignment, each at its own anchor) so that, as the PDF
    prints it, its glyphs' baseline lies as far from its anchor as the plain texts' of `texts` do (their mean; a plain
    "lp" where there is none) (C62 review). For texts whose anchors the layout does not set from their own metrics:
    a row of tick labels, axis labels, a panel title with its letter, a one-row key (a legend's packer places each
    label from its rounded height: align_printed_rows, align_legend_rows). Matplotlib sets a mathtext line from its own
    metrics, its height and depth rounded up to whole pt in the PDF, and its glyphs rise by the rounding
    (math_rise_pt), so that a key's mathtext label sat 0.9 pt above its plain neighbor, (a)'s two names with math
    0.45 pt off the rows' pitch and (b)'s "$W_0$ margin" 0.75 pt off "Cost margin" (fig4_v3). The shift is along the
    text's up direction (a y label's rotation, rotation_mode 'anchor'), recorded as t._sublet_baseline_shift_pt; it is
    exact for the PDF (the PNG preview, set by Agg, follows it to a fraction of a pt)."""
    texts = [t for t in texts if t.get_visible() and t.get_text() and "\n" not in t.get_text()]
    if not texts:
        return
    items = [(t.get_text(), t.get_fontproperties()) for t in texts]
    got = pdf_text_metrics(items)
    ref = pdf_text_metrics([("lp", p) for _, p in items])
    now = []
    for t, (s, prop), (h, d), (lh, ld) in zip(texts, items, got, ref):
        rot = float(t.get_rotation())
        if rot % 360.0 and t.get_rotation_mode() != "anchor":
            raise style.StyleError(f"{_fig_name(t.get_figure(root=True))}: align_baselines needs rotation_mode "
                                   f"'anchor' for rotated text {s!r}")
        now.append(_va_baseline_pt(t.get_verticalalignment(), max(h, lh), max(d, ld)) + math_rise_pt(s, prop))
    plain = [v for (s, _), v in zip(items, now) if not cbook.is_math_text(s)]
    for t, (s, prop), (lh, ld), v in zip(texts, items, ref, now):
        if not cbook.is_math_text(s):
            continue
        want = float(np.mean(plain)) if plain else _va_baseline_pt(t.get_verticalalignment(), lh, ld)
        shift = want - v
        rot = float(t.get_rotation())
        if abs(shift) < 1e-3:
            continue
        ux, uy = -math.sin(math.radians(rot)), math.cos(math.radians(rot))
        fig = t.get_figure(root=True)
        t.set_transform(t.get_transform() + ScaledTranslation(
            ux * shift / style.BP_PER_IN, uy * shift / style.BP_PER_IN, fig.dpi_scale_trans))
        t._sublet_baseline_shift_pt = round(shift, 4)


ROW_TOL_PT = 2.0               # align_printed_rows: texts whose printed baselines lie this close share a row


def printed_baselines_pt(fig, texts: Sequence[Any]) -> list[float]:
    """C62: the baseline (pt above the page's bottom) on which the PDF prints the glyphs of each one-line text of
    `texts`, measured in a PDF draw of `fig` (in_pdf): the layout box's bottom plus the line's descent (at least
    "lp"'s, as matplotlib sets a line) plus the rise of a mathtext line (math_rise_pt: the PDF backend rounds a
    mathtext line's height up to a whole pt)."""
    def measure(r):
        out = []
        for t in texts:
            s, prop = t.get_text(), t.get_fontproperties()
            _, _, d = r.get_text_width_height_descent(s, prop, ismath=cbook.is_math_text(s))
            _, _, ld = r.get_text_width_height_descent("lp", prop, ismath=False)
            out.append(float(t.get_window_extent(r).y0 + max(d, ld) + math_rise_pt(s, prop)))
        return out
    return in_pdf(fig, measure)


def align_printed_rows(fig, texts: Sequence[Any], *, tol_pt: float = ROW_TOL_PT) -> list[float]:
    """C62 (lesson of the main figures' review: labels that share a row share a baseline): move each one-line mathtext
    text of `texts` onto the mean printed baseline of the plain texts of its row (the texts whose printed baselines,
    printed_baselines_pt, lie within `tol_pt` of a neighbor's), for texts whose position the layout sets from their own
    metrics, such as a legend's labels, where align_baselines' fixed anchors do not hold (a legend's packer places a
    mathtext label from its rounded height: in fig4v2's two-row legend, "$W_0$ vs. $\\tau\\geq1$ h" printed 0.9 pt
    above its row and "$W_0$ vs. best" on its row). The rows are found from the printed baselines, so the texts need
    not be a legend's in its order (align_legend_rows takes a legend's rows by entry index instead). The shift is
    recorded as t._sublet_baseline_shift_pt and checked by a second PDF draw. Returns the shifts (pt) of `texts` in
    their order (0 for the unmoved)."""
    texts = [t for t in texts if t.get_visible() and t.get_text() and "\n" not in t.get_text()]
    if not texts:
        return []
    base = printed_baselines_pt(fig, texts)
    rows: list[list[int]] = []
    for i in sorted(range(len(texts)), key=lambda j: base[j]):
        if rows and base[i] - base[rows[-1][-1]] <= tol_pt:
            rows[-1].append(i)
        else:
            rows.append([i])
    shifts = [0.0] * len(texts)
    for row in rows:
        plain = [base[i] for i in row if not cbook.is_math_text(texts[i].get_text())]
        if not plain:
            continue
        want = float(np.mean(plain))
        for i in row:
            if cbook.is_math_text(texts[i].get_text()) and abs(want - base[i]) > 1e-3:
                shifts[i] = want - base[i]
                t = texts[i]
                t.set_transform(t.get_transform() + ScaledTranslation(0.0, shifts[i] / style.BP_PER_IN,
                                                                      fig.dpi_scale_trans))
                t._sublet_baseline_shift_pt = round(shifts[i], 4)
    after = printed_baselines_pt(fig, texts)
    for row in rows:
        plain = [after[i] for i in row if not cbook.is_math_text(texts[i].get_text())]
        if plain and max(abs(after[i] - float(np.mean(plain))) for i in row) > 0.05:
            raise style.StyleError(f"{_fig_name(fig)}: texts of one row print on baselines "
                                   f"{[after[i] for i in row]} pt")
    return shifts


def align_legend_rows(leg, rows: int) -> dict:
    """Put each mathtext label of a multi-row legend on the baseline of the plain labels of its row, as the PDF prints
    them (C62; supp/ms7_x3_lib's legend_row_baselines as built). A legend stacks each column's entries by their texts'
    heights, and a mathtext label is taller and sits higher in the PDF (its metrics rounded up to whole pt,
    math_rise_pt), so that in a two-row legend 'SpotHedge-style, $N_{\\mathrm{Extra}}=0$' printed 0.9 pt above its row
    and the label under it 0.6 pt below its own; align_baselines, which assumes texts at aligned anchors, fits a
    one-row key only. For a legend whose entries fill the columns first (style.legend_row's ncol = ceil(n / rows)), so
    that entry i is in row i mod rows (align_printed_rows finds the rows from the printed baselines instead, and checks
    the result). Each label's printed baseline is measured in the PDF draw (in_pdf: its layout box's bottom, its line's
    descent, at least that of 'lp', and the mathtext rise); a mathtext label moves by its row's mean plain baseline
    less its own (recorded as t._sublet_baseline_shift_pt). Returns {label: shift in pt}."""
    texts = list(leg.get_texts())
    fig = leg.get_figure(root=True)

    def measure(r):
        out = []
        for t in texts:
            s, prop = t.get_text(), t.get_fontproperties()
            _, _, d = r.get_text_width_height_descent(s, prop, ismath=cbook.is_math_text(s))
            _, _, ld = r.get_text_width_height_descent("lp", prop, ismath=False)
            out.append(t.get_window_extent(r).y0 + max(d, ld) + math_rise_pt(s, prop))
        return out
    base = in_pdf(fig, measure)                            # pt: the PDF draw is at 72 dpi
    shifts = {}
    for row in range(int(rows)):
        idx = [i for i in range(len(texts)) if i % int(rows) == row]
        plain = [base[i] for i in idx if not cbook.is_math_text(texts[i].get_text())]
        if not plain:
            continue
        want = float(np.mean(plain))
        for i in idx:
            t = texts[i]
            if not cbook.is_math_text(t.get_text()) or abs(want - base[i]) < 1e-3:
                continue
            shift = want - base[i]
            t.set_transform(t.get_transform() + ScaledTranslation(0.0, shift / style.BP_PER_IN,
                                                                  fig.dpi_scale_trans))
            t._sublet_baseline_shift_pt = round(shift, 4)
            shifts[t.get_text()] = round(shift, 4)
    return shifts


def align_right_math(texts: Sequence) -> None:
    """Move each one-line, unrotated mathtext text of `texts` that is set with ha 'right' (the rows' names) right by
    the PDF's rounding of its width: the PDF sets a mathtext line in a box of its width rounded up to a whole pt
    (matplotlib's _mathtext.Output.to_vector, at 72 dpi) and draws its glyphs from the box's left end, so that a
    right-aligned name with math ended up to 0.9 pt short of its plain neighbors (sf_bl_ms7's names; C62 fix round).
    The shift is recorded as t._sublet_right_shift_pt; it is exact for the PDF (the PNG preview, set by Agg at its
    own dpi, lies up to that much right of it)."""
    for t in texts:
        s = t.get_text()
        if (not t.get_visible() or not s or "\n" in s or not cbook.is_math_text(s)
                or t.get_horizontalalignment() != "right" or float(t.get_rotation()) % 360.0):
            continue
        prop = t.get_fontproperties()
        shift = float(_MATH.parse(s, 72, prop).width) - float(_MATH.parse(s, 7200, prop).width) / 100.0
        if abs(shift) < 1e-3:
            continue
        fig = t.get_figure(root=True)
        t.set_transform(t.get_transform() + ScaledTranslation(shift / style.BP_PER_IN, 0.0, fig.dpi_scale_trans))
        t._sublet_right_shift_pt = round(shift, 4)


def align_ylabels_x(axes: Sequence) -> None:
    """The y labels of `axes` at one x, the axes' label pad left of the leftmost of their y tick labels and spines
    (set_label_coords). Figure.align_ylabels aligns only axes with a subplotspec: fig4_v3's (b) sub-panels are placed
    axes, and as built "$W_0$ margin" sat 0.2 pt left of "Cost margin", by the width of its widest tick label."""
    fig = axes[0].figure
    r = fig.canvas.get_renderer()
    boxes = {ax: ax.get_window_extent(r) for ax in axes}
    x0 = min(min([tk.label1.get_window_extent(r).x0 for tk in ax.yaxis._update_ticks()
                  if tk.label1.get_visible() and tk.label1.get_text()] + [boxes[ax].x0]) for ax in axes)
    for ax in axes:
        x = x0 - ax.yaxis.labelpad * fig.dpi / 72.0
        ax.yaxis.set_label_coords((x - boxes[ax].x0) / boxes[ax].width, 0.5)


def letter_box(fig, letter: str) -> tuple[float, float]:
    """(width in inches, top above the baseline in pt) of a panel letter's text box (style.panel_letters' bold
    LETTER_PT)."""
    t = fig.text(0.0, 0.5, f"({letter})", fontsize=style.LETTER_PT, fontweight="bold", va="baseline")
    bb = t.get_window_extent(fig.canvas.get_renderer())
    y0 = fig.transFigure.transform((0.0, 0.5))[1]
    t.remove()
    return bb.width / fig.dpi, (bb.y1 - y0) * 72.0 / fig.dpi
