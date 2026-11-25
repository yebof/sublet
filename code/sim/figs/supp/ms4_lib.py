"""Helpers shared by the MS4 supplementary figure scripts figs/supp/sf_e3_*.py, sf_e4.py, sf_e5.py, sf_e7_*.py and
sf_e8.py (design/sim_spec_ms4.md §8.2; design/figure_plan.md §5). Not a figure script (no NAME): it reads nothing.

Contents: the registry keys of a summary's tags (``tag_of``: meta.tags.<tag>.style_key, the drivers' own map, §4.5,
§5.4, §6.6, §3.5); one point of a ``metrics.aggregate`` dict with its note (``agg_point``); per-key series against a
numeric level read with ``maybe`` so that a null or missing point stays in the lists with its note (``series_over``);
dodged policy series with their 95% intervals on a log x axis (``dodge``, ``draw_series``; a yellow policy line in a
black casing, ``line_casing``); log axes with plain tick
labels over a data range (``log_ticks``, ``log_axis_over``, ``level_axis``); the run counts of a summary's grid for
notes and captions (``grid_counts``, ``runs_text``); one x label centered under a row of panels
(``center_xlabel``); off-scale values drawn at an axis end as an arrow with the value, the value clear of the axes'
sides by OFF_SCALE_CLEAR_PT (``off_scale_marks``); the white halo of a direct label dropped where the label overlaps
no line, grid, bar, arrow or marker, so that it stays text in the PDF (``drop_idle_halos``).
MS6 C47 (design/ms6_spec.md M2, M4): the recorded style keys of the frozen summaries mapped to the configuration keys
that the relabeled figures draw (``DRAWN_KEY``, ``tag_of(..., drawn=...)``; a siloed form as the series id
"<key>:siloed", ``series_key``), and legend rows of entries side by side, split to fit the figure's width, for the
legends whose configuration labels style.legend_row's column-aligned rows cannot hold (``split_rows``,
``legend_rows_above``, ``legend_reserve_top``); a long label split into lines for tables and row labels
(``label_lines``), a label escaped for LaTeX outside its math (``tex_label``), and the guards' allowance share from a
summary's B0_rule (``b0_share_text``).
C62 (additive, opt-in): legend samples whose dashes are centered on them, with no sliver of a dash at an end
(``centered_dash_pairs``); the scripts set mathtext texts on their plain neighbors' baseline as the PDF prints them
with figs.common.align_baselines.
"""
from __future__ import annotations

import math
from typing import Any, Callable, Mapping, Sequence

import numpy as np
from matplotlib.ticker import NullFormatter, NullLocator

from figs import style
from figs.common import DODGE_OCT, MissingKey, _top_tick_room, clear_floor, finite, maybe, num_items, text_width_in

LOG_LADDERS = ((1.0, 10.0), (1.0, 2.0, 5.0), (1.0, 1.5, 2.0, 3.0, 5.0, 7.0),
               (1.0, 1.2, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 8.0))
LOG_LADDER_MID = (1.0, 3.0)     # between 1 per decade and 1, 2, 5: where the one has too few ticks, the other too many
LOG_MIN_TICKS = 3               # a log axis gets the coarsest ladder with at least this many ticks in range
LOG_MAX_TICKS = 6               # ... and at most this many, LOG_LADDER_MID in between (as built without it, a range of
#                                 2-3 decades got 2 ticks, since 1, 2, 5 gave 7)
LOG_PAD = 1.12                  # a log axis extends this factor beyond the data on each side (not in §8.2)


# MS6 C47 (design/ms6_spec.md M2, M4; the entry gate, MS5b's W8): the MS4 and MS5 summaries are frozen results and
# record the style keys of their build (meta.tags.<tag>.style_key); the relabeled figures of MS4's allowance (E3, E5,
# E7's main grid, S1, E9) draw, for each recorded key, the registry key of its configuration: the guard around the
# lagged BL5 at B0 = 10% BL0a (tag Sublet) as sublet_ms4, the lagged BL5 as bl5_lag, A8 around A7 at the same allowance
# (E7's and S1's tag A7G) as a7_ms4 (C46: not a7_g1, which is A8 around A7 at Algorithm 1's defaults)
DRAWN_KEY = {"sublet": "sublet_ms4", "bl5": "bl5_lag", "a7_guard": "a7_ms4"}
SILOED_FORM = ":siloed"         # a drawn series id "<key>:siloed": the key's siloed form, drawn in the sharing line
#                                 style (C46: no siloed registry key; sf_e3_util, sf_e3_mu)


def series_key(series: str) -> str:
    """The registry key of a drawn series id ("sublet_ms4:siloed" -> "sublet_ms4"; a key is its own)."""
    return series.split(":", 1)[0]


def tag_of(meta_tags: Mapping, keys: Sequence[str], what: str, *, drawn: Mapping[str, str] | None = None
           ) -> dict[str, str]:
    """{registry key: summary tag} from meta.tags.<tag>.style_key (the drivers write the map, §4.5, §5.4, §6.6, §3.5);
    with `drawn` ({recorded style key: drawn key or series id}, e.g. DRAWN_KEY), a tag's recorded key is first mapped
    to what the figure draws (C47); MissingKey if a key of `keys` has no tag."""
    drawn = drawn or {}
    by_key = {drawn.get(v.get("style_key"), v.get("style_key")): t for t, v in meta_tags.items()
              if isinstance(v, Mapping)}
    missing = [k for k in keys if k not in by_key]
    if missing:
        raise MissingKey(f"{what}: meta.tags has no tag with style_key {missing} (style keys there: {sorted(by_key)})")
    return {k: by_key[k] for k in keys}


LABEL_BREAK = " ("              # label_lines: a long label is split before its parenthesis ...
PLUS_BREAK = " + "              # ... and, where asked, before " + " (C47)
OF_BREAK = " of the "           # ... and, where asked, after " of the" (C59: the MS4 allowance in words)


def label_lines(label: str, *, plus: bool = False, of: bool = False) -> list[str]:
    """A registry label as the lines of a table cell or a row label (C47: sublet_ms4's "Lagged RetroRenting + one-way
    guard ($B_0=10\\%$ BL0a)", 3.1 in at 9 pt): split before its parenthesis (LABEL_BREAK) and, with `plus`, also
    before " + " (PLUS_BREAK; "Lagged RetroRenting", "+ one-way guard", "($B_0=10\\%$ BL0a)"); a label without either
    is one line. C59: with `of`, a line is also split after " of the" (OF_BREAK; the allowance in words,
    "($B_0=10\\%$ of the", "all-fallback bill)")."""
    stem, sep, rest = str(label).partition(LABEL_BREAK)
    lines = [stem, "(" + rest] if sep else [stem]
    if plus:
        lines = [part if i == 0 else "+ " + part for ln in lines for i, part in enumerate(ln.split(PLUS_BREAK))]
    if of:
        lines = [part for ln in lines for part in ln.replace(OF_BREAK, OF_BREAK.rstrip() + "\n").split("\n")]
    return lines


def tex_label(text: Any) -> str:
    """A label for LaTeX (C47, the tables that print sublet_ms4's "$B_0=10\\%$"): & % _ # escaped outside $...$, the
    math parts (mathtext, which LaTeX reads) kept (sf_s1._tex's rule)."""
    parts = str(text).split("$")
    for i in range(0, len(parts), 2):
        parts[i] = parts[i].replace("&", r"\&").replace("%", r"\%").replace("_", r"\_").replace("#", r"\#")
    return "$".join(parts)


def b0_share_text(rule: Any, tex: bool = False) -> str | None:
    """The allowance share of a summary's meta.B0_rule ("0.1*BL0a" -> "10%", "10\\%" with `tex`), for the notes and
    captions that state the guards' allowance (C47: the configuration keys sublet_ms4 and, in E7 and S1, a7_ms4 run at
    it); None where the rule is not of that form."""
    head, sep, _ = str(rule or "").partition("*")
    try:
        pct = f"{100.0 * float(head):g}" if sep else None
    except ValueError:
        return None
    return None if pct is None else pct + (r"\%" if tex else "%")


LEGEND_HANDLE_SHORT = 1.4       # em: the handle length of legend_rows_above (sf_e7_allow's LEGEND_HANDLE; style's
#                                 default is 2.0), so that a long configuration label fits its row (not in §8.2)
LEGEND_ROW_GAP_EM = 0.3         # legend_rows_above: the gap between two rows (the legend's labelspacing, rcParams)


def legend_reserve_top(rows: int) -> float:
    """The top margin (inches) above the panels for `rows` legend rows (style.panel_row's for legend=rows; C47: also
    three rows, which style.legend_row does not draw)."""
    return style.MARGIN_TOP + style.LEGEND_ROW * int(rows)


LABEL_WRAP_EM = 25.6            # C59 (RC19(3)): a legend label wider than this many ems that has a parenthesis goes
#                                 on two lines, split before it (label_lines): the MS4 allowance's labels in words
#                                 (sublet_ms4's 31.7 em, a7_ms4's 27.6 em; as built, with "BL0a", 25.0 em on one
#                                 line); every other label of the MS4 figures is narrower and stays on one line. Built
#                                 at 9 pt as 3.2 in; C62 keeps the rule in ems, so that the same labels wrap at TICK_PT
LABEL_WRAP_IN = LABEL_WRAP_EM * style.TICK_PT / style.BP_PER_IN    # 2.49 in at 7 pt (3.2 in at 9 pt)


def wrap_wide(fig, pairs: Sequence[tuple]) -> list:
    """C59: `pairs` ((handle, label)) with each label that is wider than LABEL_WRAP_IN and has a parenthesis on two
    lines (label_lines); the others unchanged."""
    return [(h, "\n".join(label_lines(t)) if LABEL_BREAK in str(t) and text_width_in(fig, str(t)) > LABEL_WRAP_IN
             else t) for h, t in pairs]


def split_rows(fig, pairs: Sequence[tuple], *, max_rows: int, handlelength: float = LEGEND_HANDLE_SHORT) -> list:
    """`pairs` ((handle, label), in their order) split into consecutive rows, each filled with as many entries as fit
    the figure's width less its right margin as one frameless legend row (measured on `fig`); StyleError where more
    than `max_rows` rows would be needed or one entry alone does not fit. C59: a label wider than LABEL_WRAP_IN with a
    parenthesis is first put on two lines (wrap_wide)."""
    import matplotlib as mpl
    from matplotlib.legend import Legend
    pairs = wrap_wide(fig, pairs)                                                                         # C59
    W = float(fig.get_size_inches()[0])
    limit = W - style.MARGIN_RIGHT + 1e-6
    r = fig.canvas.get_renderer()

    def width(group) -> float:
        with mpl.rc_context({"legend.handlelength": handlelength}):
            h, t = zip(*group)
            leg = Legend(fig, list(h), list(t), ncol=len(group), frameon=False, borderpad=0.0,
                         handler_map=dict(style.PAIR_HANDLER_MAP))
        return leg.get_window_extent(r).width / fig.dpi

    rows: list[list] = []
    for p in pairs:
        if rows and width(rows[-1] + [p]) <= limit:
            rows[-1].append(p)
        elif width([p]) <= limit:
            rows.append([p])
        else:
            raise style.StyleError(f"the legend entry {p[1]!r} is wider than the figure less its right margin")
    if len(rows) > max_rows:
        raise style.StyleError(f"the legend needs {len(rows)} rows of at most {W - style.MARGIN_RIGHT:.3f} in, more "
                               f"than {max_rows}")
    return rows


def legend_rows_above(fig, rows: Sequence[Sequence[tuple]], *, n_rows: int | None = None,
                      handlelength: float = LEGEND_HANDLE_SHORT, gap_em: float = LEGEND_ROW_GAP_EM) -> list:
    """C47 (design/ms6_spec.md M2): frameless legend rows above the panels, for a legend whose labels (a configuration's
    long registry label) style.legend_row's column-aligned rows cannot hold: each row of `rows` (from split_rows) is
    a figure legend of its entries side by side, centered over the panels (as legend_row), the rows stacked
    LEGEND_ROW_GAP_EM apart and centered as a block in the top reserve of `n_rows` (default len(rows)) legend rows
    (legend_reserve_top; place the panels with panel_row(..., top=legend_reserve_top(n_rows))), handles `handlelength`
    em long. Each legend's _sublet_role is "legend_row". StyleError where a panel reaches into the reserve or the
    block does not fit it. C59: `gap_em`, the gap between two rows (default LEGEND_ROW_GAP_EM). Returns the legends,
    top row first."""
    import matplotlib as mpl
    n_rows = len(rows) if n_rows is None else int(n_rows)
    W, H = (float(v) for v in fig.get_size_inches())
    reserve = style.LEGEND_ROW * n_rows
    rects = [ax._sublet_rect_in for ax in fig.axes if hasattr(ax, "_sublet_rect_in")]
    if not rects or min(H - (r[1] + r[3]) for r in rects) < style.MARGIN_TOP + reserve - style.GEOMETRY_TOL_IN:
        raise style.StyleError(f"legend_rows_above needs the top margin {style.MARGIN_TOP + reserve:.2f} in above "
                               "every panel (panel_row(..., top=legend_reserve_top(n_rows)))")
    xc = 0.5 * (min(r[0] for r in rects) + max(r[0] + r[2] for r in rects))
    r = fig.canvas.get_renderer()
    legs = []
    for group in rows:
        h, t = zip(*group)
        with mpl.rc_context({"legend.handlelength": handlelength}):
            leg = fig.legend(list(h), list(t), loc="center", ncol=len(group), frameon=False, borderaxespad=0.0,
                             borderpad=0.0, handler_map=dict(style.PAIR_HANDLER_MAP))
        leg._sublet_role = "legend_row"
        legs.append(leg)
    boxes = [lg.get_window_extent(r) for lg in legs]
    gap = gap_em * style.TICK_PT / style.BP_PER_IN                                                       # C59
    heights = [b.height / fig.dpi for b in boxes]
    block = sum(heights) + gap * (len(legs) - 1)
    if block > reserve + 1e-6 or max(b.width / fig.dpi for b in boxes) > W - style.MARGIN_RIGHT + 1e-6:
        for lg in legs:
            lg.remove()
        raise style.StyleError(f"the legend rows ({block:.2f} in high, at most {reserve:.2f}; widths "
                               f"{[round(b.width / fig.dpi, 2) for b in boxes]} in) do not fit above the panels")
    y = H - 0.5 * reserve + 0.5 * block                  # the block's top, in inches
    for lg, b, h in zip(legs, boxes, heights):
        w = b.width / fig.dpi
        x = min(max(xc, 0.5 * w), W - style.MARGIN_RIGHT - 0.5 * w)
        lg.set_bbox_to_anchor((x / W, (y - 0.5 * h) / H), transform=fig.transFigure)
        y -= h + gap
    return legs


def agg_point(entry: Any, field: str | None = None) -> dict:
    """{median, ci_lo, ci_hi, n, note} of a metrics.aggregate dict (entry[field] where `field` is given): None and the
    '*_note' of the null median (or 'missing') where the value is null or missing (§2.6)."""
    a = entry.get(field) if (field is not None and isinstance(entry, Mapping)) else entry
    if not isinstance(a, Mapping):
        note = (entry.get(f"{field}_note") if isinstance(entry, Mapping) and field else None) or "missing"
        return {"median": None, "ci_lo": None, "ci_hi": None, "n": 0, "note": note}
    lo, hi = (a.get("median_ci95") or [None, None])[:2]
    med = a.get("median")
    return {"median": med, "ci_lo": lo, "ci_hi": hi, "n": a.get("n"),
            "note": None if med is not None else (a.get("median_note") or a.get("note") or "null")}


def series_over(block: Mapping, levels: Sequence[tuple[float, str]], tag: str, read: Callable[[Any], dict],
                xname: str) -> dict:
    """One key's series {xname, median, ci_lo, ci_hi, n, note} over the numeric `levels` ((x, key) pairs) of
    `block`: read(block[key][tag]) for each level, a null or missing entry kept with its note (a gap in the line)."""
    s = {xname: [], "median": [], "ci_lo": [], "ci_hi": [], "n": [], "note": []}
    for x, k in levels:
        ent, note = maybe(block, k, tag)
        p = read(ent) if note is None else {"median": None, "ci_lo": None, "ci_hi": None, "n": 0, "note": note}
        s[xname].append(x)
        for f in ("median", "ci_lo", "ci_hi", "n", "note"):
            s[f].append(p[f])
    return s


def levels_of(block: Mapping, what: str) -> list[tuple[float, str]]:
    """(number, key) of the numeric keys of `block`, sorted (num_items); MissingKey if there is none."""
    out = [(x, k) for x, k, _ in num_items(block)]
    if not out:
        raise MissingKey(f"{what}: no numeric key (keys there: {sorted(block)[:12]})")
    return out


def dodge(x, i: int, n: int, oct_: float = DODGE_OCT) -> np.ndarray:
    """x shifted by (i - (n - 1) / 2) * oct_ octaves (series i of n on a log axis), so that their interval bars do not
    sit on each other."""
    return finite(x) * 2.0 ** (oct_ * (i - (n - 1) / 2.0))


CASING_PT = 0.6                 # a yellow policy line's black casing: this much wider than the line (not in §8.2)


def line_casing(ax, key: str, x, y) -> None:
    """A black line CASING_PT wider under the line of a policy whose marker edge is not its color (the yellow BL3 and
    BL4, edged in black): a 1-pt #F0E442 line prints lighter (grey 213) than the 0.5-pt reference line (#BDBDBD, 189)
    beside which it may run, so that in greyscale only its markers told it apart (sf_e7_mu, as built). Nothing for the
    other policies."""
    p = style.policy(key)
    if p.edgecolor is None or p.edgecolor.upper() == p.color.upper():
        return
    (ln,) = ax.plot(x, y, color=p.edgecolor, linewidth=p.linewidth + CASING_PT, linestyle="-", marker="None",
                    zorder=p.zorder - 0.02, solid_capstyle="butt", label="_nolegend_")
    ln._sublet_role = "casing"


def draw_series(ax, key: str, s: Mapping, xname: str, *, i: int = 0, n: int = 1, env: tuple[str, str] | None = None,
                oct_: float = DODGE_OCT, **overrides) -> None:
    """A policy's medians as a line with markers (gaps at null points) and its 95% intervals as bars, dodged as series
    i of n; a yellow policy's line in a black casing (line_casing)."""
    x = dodge(s[xname], i, n, oct_)
    y, lo, hi = finite(s["median"]), finite(s["ci_lo"]), finite(s["ci_hi"])
    line_casing(ax, key, x, y)
    style.plot_policy(ax, key, x, y, env=env, **overrides)
    ok = np.isfinite(x) & np.isfinite(y) & np.isfinite(lo) & np.isfinite(hi) & (hi > lo)
    if ok.any():
        style.errorbars(ax, key, x[ok], y[ok], lo[ok], hi[ok])


Z_LAYER_BARS = style.Z_SUBLET + 0.05      # draw_series_layered's second pass: interval bars above every line
Z_LAYER_MARKS = style.Z_SUBLET + 0.1      # ... and markers above the bars, Z_LAYER_STEP per unit of registry z-order
Z_LAYER_STEP = 0.1                        #     above Z_DATA (Sublet's last; all below Z_THEORY_LABEL)


def draw_series_layered(ax, series: Sequence[tuple], xname: str, *, n: int, oct_: float = DODGE_OCT) -> None:
    """draw_series for several series in two passes, as sf_e3_util's draw_panel (print check of 2026-10-27): first
    every series' line (its registry style, markers suppressed; a yellow policy's line in its black casing; Sublet's
    line above the others by its registry z-order), then every 95% interval bar (Z_LAYER_BARS) and every series'
    markers (a markers-only Line2D, `_sublet_role` "markers", at Z_LAYER_MARKS plus Z_LAYER_STEP per unit of registry
    z-order above Z_DATA), so that no line runs over another series' marker. `series` holds (key, s, i, env) tuples,
    i the dodge slot of n."""
    pts = []
    for key, s, i, env in series:
        x = dodge(s[xname], i, n, oct_)
        y, lo, hi = finite(s["median"]), finite(s["ci_lo"]), finite(s["ci_hi"])
        line_casing(ax, key, x, y)
        style.plot_policy(ax, key, x, y, env=env, markevery=[])
        pts.append((key, x, y, lo, hi, env))
    for key, x, y, lo, hi, _ in pts:
        ok = np.isfinite(x) & np.isfinite(y) & np.isfinite(lo) & np.isfinite(hi) & (hi > lo)
        if ok.any():
            style.errorbars(ax, key, x[ok], y[ok], lo[ok], hi[ok], zorder=Z_LAYER_BARS)
    for key, x, y, _, _, env in pts:
        kw = style.policy_kwargs(key, env=env, lines=False, label=False)
        kw["zorder"] = Z_LAYER_MARKS + Z_LAYER_STEP * (kw["zorder"] - style.Z_DATA)
        (mk,) = ax.plot(x, y, **kw)
        mk._sublet_role = "markers"
        mk._sublet_markers_of = key


def finite_values(*arrays) -> np.ndarray:
    vals = [finite(a) for a in arrays if len(a)]
    v = np.concatenate(vals) if vals else np.array([], dtype=float)
    return v[np.isfinite(v)]


def log_ticks(lo: float, hi: float) -> list[float]:
    """Ticks of a base-10 log axis on [lo, hi] (lo > 0): the coarsest ladder of LOG_LADDERS (mantissas per decade)
    that puts at least LOG_MIN_TICKS ticks in range; where that ladder puts more than LOG_MAX_TICKS there, the ladder
    LOG_LADDER_MID (1, 3) if it puts at least LOG_MIN_TICKS, else that ladder's ticks (never fewer than LOG_MIN_TICKS
    where a ladder gives them; an x axis thins crowded labels with common.thin_tick_labels); the finest ladder's ticks
    where none puts LOG_MIN_TICKS in range (a narrow range)."""
    e0, e1 = math.floor(math.log10(lo)) - 1, math.ceil(math.log10(hi)) + 1

    def in_range(lad):
        t = [m * 10.0 ** e for e in range(e0, e1 + 1) for m in lad if m < 10.0 or lad == (1.0, 10.0)]
        return sorted({round(v, 12) for v in t if lo * (1 - 1e-9) <= v <= hi * (1 + 1e-9)})

    ticks: list[float] = []
    for lad in LOG_LADDERS:
        ticks = in_range(lad)
        if len(ticks) >= LOG_MIN_TICKS:
            if len(ticks) > LOG_MAX_TICKS:
                mid = in_range(LOG_LADDER_MID)
                if LOG_MIN_TICKS <= len(mid) < len(ticks):
                    return mid
            return ticks
    return ticks


def grid_counts(grid: Mapping, what: str) -> tuple[int, int]:
    """(alignments, policy seeds) of a summary's grid (meta.grid or meta.grids: `alignments`, and `policy_seeds` or
    E8's single `policy_seed`), the counts a note or caption states (never typed); MissingKey where absent."""
    al = grid.get("alignments") if isinstance(grid, Mapping) else None
    se = grid.get("policy_seeds") if isinstance(grid, Mapping) else None
    if se is None and isinstance(grid, Mapping) and grid.get("policy_seed") is not None:
        se = [grid["policy_seed"]]
    if not isinstance(al, list) or not isinstance(se, list):
        raise MissingKey(f"{what}: no alignments or policy_seeds list in the grid")
    return len(al), len(se)


def runs_text(n_align: int, n_seeds: int, times: str = "x") -> str:
    """'4 alignments x 3 policy seeds', singular where a count is 1 (`times`: the multiplication sign)."""
    return (f"{n_align} alignment{'s' if n_align != 1 else ''} {times} {n_seeds} policy seed"
            f"{'s' if n_seeds != 1 else ''}")


def log_axis_over(ax, which: str, lo: float, hi: float, *, pad: float = LOG_PAD, ticks: Sequence[float] | None = None,
                  ) -> list[float]:
    """A base-10 log axis over [lo / pad, hi * pad] with plain tick labels (log_ticks over that range unless `ticks`)
    and no minor ticks; a y axis's top clears its highest tick label (common._top_tick_room, so that it stays clear of
    the panel letter) and its bottom the markers at `lo` (common.clear_floor; call after the series are drawn).
    Returns the ticks."""
    a, b = lo / pad, hi * pad
    t = list(ticks) if ticks is not None else log_ticks(a, b)
    style.log_axis(ax, which, ticks=t)
    axis = ax.xaxis if which == "x" else ax.yaxis
    axis.set_minor_locator(NullLocator())
    (ax.set_xlim if which == "x" else ax.set_ylim)(a, b)
    if which == "y":
        _top_tick_room(ax)
        clear_floor(ax, lo)
    return t


def level_axis(ax, levels: Sequence[float], *, which: str = "x", pad: float = 1.25) -> None:
    """A log axis whose ticks are the grid's levels (mu / beta~, smoothing windows), labeled plainly, with a margin of
    `pad` (a factor) beyond the first and last level, so that dodged markers and their bars stay inside."""
    lv = sorted(float(v) for v in levels)
    style.log_axis(ax, which, ticks=lv)
    axis = ax.xaxis if which == "x" else ax.yaxis
    axis.set_minor_locator(NullLocator())
    axis.set_minor_formatter(NullFormatter())
    (ax.set_xlim if which == "x" else ax.set_ylim)(lv[0] / pad, lv[-1] * pad)
    if which == "x":
        style.end_label_inside(ax)


def center_xlabel(axes, text: str) -> None:
    """One x label for a row of panels, centered under all of them (as the first panel's label, its x in that panel's
    axes fraction), where the label is wider than one panel (sf_e4, sf_e8)."""
    x0, _, w0, _ = style.axes_rect_in(axes[0])
    x1, _, w1, _ = style.axes_rect_in(axes[-1])
    axes[0].set_xlabel(text)
    axes[0].xaxis.label.set_x((0.5 * (x0 + x1 + w1) - x0) / w0)


ARROW_PT = 7.0                  # length of an off-scale arrow (not in §8.2)
OFF_SCALE_CLEAR_PT = 2.0        # an off-scale value label ends at least this far inside the axes' sides (not in §8.2)


def off_scale_marks(ax, xs, ys, *, floor: float, color: str, fmt: str = "{:.2g}",
                    clear_pt: float = OFF_SCALE_CLEAR_PT) -> list[dict]:
    """Points with y below `floor` drawn as a downward arrow ending on the axis floor, with their value printed above
    the arrow's tail, centered on it, so that a value off the axis is neither hidden nor stretches the axis (sf_e8
    (b)); call after the limits are final. A label that centered would come closer than `clear_pt` to a side of the
    axes (a y spine) or cross it is shifted sideways by the least amount that keeps it `clear_pt` inside (left-aligned
    `clear_pt` inside the left side where it is wider than the axes less both margins). As built the test was against
    the side itself, so a label centered 1 px inside sf_e8 (b)'s y spine stayed there and its minus sign read as a tick
    on the spine (print check). Returns [{x, y, label}] for the extract."""
    out = []
    fig = ax.figure
    r = fig.canvas.get_renderer()
    bb_ax = ax.get_window_extent(r)
    m_px = clear_pt * fig.dpi / style.BP_PER_IN
    to_pt = style.BP_PER_IN / fig.dpi
    for x, y in zip(finite(xs), finite(ys)):
        if not (np.isfinite(x) and np.isfinite(y)) or y >= floor:
            continue
        ann = ax.annotate("", xy=(x, floor), xytext=(0.0, ARROW_PT), textcoords="offset points",
                          xycoords="data", arrowprops=dict(arrowstyle="-|>,head_length=0.4,head_width=0.2",
                                                           color=color, linewidth=0.8, shrinkA=0.0, shrinkB=0.0),
                          annotation_clip=False, zorder=style.Z_DATA + 0.1)
        ann._sublet_role = "off_scale_arrow"
        lab = fmt.format(y).replace("-", "−")
        t = ax.annotate(lab, xy=(x, floor), xytext=(0.0, ARROW_PT + 0.5), textcoords="offset points", ha="center",
                        va="bottom", fontsize=style.TICK_PT, color=style.readable_on_white(color),
                        zorder=style.Z_THEORY_LABEL)
        bb = t.get_window_extent(r)
        lo, hi = bb_ax.x0 + m_px, bb_ax.x1 - m_px
        if bb.width > hi - lo:
            shift = lo - bb.x0
        elif bb.x0 < lo:
            shift = lo - bb.x0
        elif bb.x1 > hi:
            shift = hi - bb.x1
        else:
            shift = 0.0
        if shift:
            t.xyann = (shift * to_pt, ARROW_PT + 0.5)
        t._sublet_role = "off_scale_label"
        out.append({"x": float(x), "y": float(y), "label": lab})
    return out


HALO_SAMPLE_PT = 0.25           # drop_idle_halos samples drawn lines and arrows at this step (not in §8.2)


def _segment_samples(p: np.ndarray, step: float) -> np.ndarray:
    """Points every `step` along the finite segments of the polyline p (n x 2; not across a gap)."""
    out = [np.zeros((0, 2))]
    for a, b in zip(p[:-1], p[1:]):
        if np.isfinite(a).all() and np.isfinite(b).all():
            n = max(int(np.hypot(*(b - a)) / step), 1) + 1
            out.append(np.linspace(a, b, n))
    return np.concatenate(out)


def _box_dist(p: np.ndarray, box: tuple[float, float, float, float]) -> np.ndarray:
    """Distance (pt) of each point of p (n x 2) to the box (x0, y0, x1, y1); 0 inside."""
    x0, y0, x1, y1 = box
    dx = np.maximum(np.maximum(x0 - p[:, 0], 0.0), p[:, 0] - x1)
    dy = np.maximum(np.maximum(y0 - p[:, 1], 0.0), p[:, 1] - y1)
    return np.hypot(dx, dy)


def halo_overlaps(ax, t) -> list[str]:
    """What the box of the text t (its window extent, in pt) overlaps among the artists of `ax` that its white halo
    would mask: lines (within half their width) and their markers (within half their size and edge), line
    collections (error bars, the y grid, half their width), the axes' grid lines and spines, the arrows of
    annotations (their drawn paths) and patches (their extents). Texts are not included (finalize() checks text
    overlaps). The descriptions of the overlaps; empty where there are none."""
    fig = ax.figure
    r = fig.canvas.get_renderer()
    to_pt = style.BP_PER_IN / fig.dpi
    bb = t.get_window_extent(r)
    box = (bb.x0 * to_pt, bb.y0 * to_pt, bb.x1 * to_pt, bb.y1 * to_pt)
    hits = []

    def polyline(p, half: float, what: str) -> None:
        s = _segment_samples(p, HALO_SAMPLE_PT)
        if len(s) and (_box_dist(s, box) <= half).any():
            hits.append(what)

    grid = [ln for ln in list(ax.xaxis.get_gridlines()) + list(ax.yaxis.get_gridlines()) if ln.get_visible()]
    for ln in [ln for ln in ax.lines if ln.get_visible()] + grid:
        with np.errstate(all="ignore"):
            p = ln.get_transform().transform(np.asarray(ln.get_xydata(), dtype=float)) * to_pt
        if ln.get_linestyle() not in ("None", "none", "", " ") and ln.get_linewidth() > 0:
            polyline(p, 0.5 * ln.get_linewidth(), f"line {ln.get_label()!r}")
        if ln.get_marker() not in (None, "None", "none", "", " "):
            q = p[np.isfinite(p).all(axis=1)]
            if len(q) and (_box_dist(q, box) <= 0.5 * (ln.get_markersize() + ln.get_markeredgewidth())).any():
                hits.append(f"marker {ln.get_label()!r}")
    for c in ax.collections:
        if not c.get_visible() or not hasattr(c, "get_segments"):
            continue
        lw = float(np.max(c.get_linewidths())) if len(c.get_linewidths()) else 0.0
        for seg in c.get_segments():
            polyline(c.get_transform().transform(np.asarray(seg, dtype=float)) * to_pt, 0.5 * lw,
                     f"collection {type(c).__name__}")
    for name, sp in ax.spines.items():
        if sp.get_visible():
            polyline(sp.get_transform().transform(sp.get_path().vertices) * to_pt, 0.5 * sp.get_linewidth(),
                     f"spine {name}")
    for o in ax.texts:
        arrow = getattr(o, "arrow_patch", None)
        if o is t or arrow is None or not o.get_visible():
            continue
        o.update_positions(r)                           # the arrow's ends, as drawn
        path = arrow.get_transform().transform_path(arrow.get_path())     # in display coordinates
        for poly in path.to_polygons(closed_only=False):
            polyline(np.asarray(poly, dtype=float) * to_pt, 0.5 * arrow.get_linewidth(), "arrow")
    for pa in ax.patches:
        if pa.get_visible():
            e = pa.get_window_extent(r)
            if e.x0 * to_pt <= box[2] and e.x1 * to_pt >= box[0] and e.y0 * to_pt <= box[3] and e.y1 * to_pt >= box[1]:
                hits.append(f"patch {type(pa).__name__}")
    return sorted(set(hits))


def drop_idle_halos(ax, texts) -> list:
    """Drop the white halo (path effects) of each text of `texts` whose box overlaps nothing it would mask
    (halo_overlaps), so that matplotlib's PDF backend writes it as text, not as filled outlines (a halo is drawn as a
    stroked path, and the text with it: print check, such labels were missing from the PDF's text layer). Call once
    every artist of `ax` is drawn. Returns the texts whose halo was dropped."""
    out = []
    for t in texts:
        if t is None or not t.get_path_effects():
            continue
        if not halo_overlaps(ax, t):
            t.set_path_effects([])
            out.append(t)
    return out


DASH_RC = {"--": "lines.dashed_pattern", ":": "lines.dotted_pattern"}


def centered_dash_pairs(pairs: Sequence[tuple], handlelength: float, *, fontsize: float = style.TICK_PT) -> list:
    """C62 (group g4-ms4, additive): `pairs` ((handle, label)) with the on-off pattern of each dashed or dotted Line2D
    handle centered on its legend sample of `handlelength` em at `fontsize`, a dash in the middle and the two ends
    alike (a dash offset), so that no sliver of a dash shows at the sample's right end (fig7_e2_e6.centered_dashes'
    rule for a given handle length: at 2.0 em of 7-pt text the 3.0/1.6 dashes give three whole dashes, 0.9 pt free
    at each end, where the pattern started at the left end leaves a 0.2-pt sliver of a fourth). Other handles are
    returned unchanged. Call before the legend is made (a legend copies its handles' styles)."""
    import matplotlib as mpl
    from matplotlib.lines import Line2D
    if mpl.rcParams["lines.scale_dashes"]:
        raise style.StyleError("centered_dash_pairs assumes unscaled dash patterns (lines.scale_dashes off)")
    length = float(handlelength) * float(fontsize)
    out = []
    for h, lab in pairs:
        ls = h.get_linestyle() if isinstance(h, Line2D) else None
        pat = [float(v) for v in mpl.rcParams[DASH_RC[ls]]] if ls in DASH_RC else []
        if len(pat) == 2:
            h.set_linestyle(((0.5 * pat[0] - 0.5 * length) % sum(pat), pat))
        out.append((h, lab))
    return out


__all__ = ["DRAWN_KEY", "SILOED_FORM", "series_key", "tag_of", "label_lines", "tex_label", "b0_share_text",
           "wrap_wide",
           "split_rows", "legend_rows_above", "legend_reserve_top", "agg_point", "series_over", "levels_of", "dodge",
           "draw_series", "draw_series_layered", "finite_values", "log_ticks",
           "grid_counts", "runs_text", "line_casing", "log_axis_over", "level_axis", "center_xlabel", "off_scale_marks",
           "halo_overlaps", "drop_idle_halos", "centered_dash_pairs"]
