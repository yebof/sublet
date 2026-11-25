"""sf_e6b: E6(b), menus of growing richness (design/sim_spec_ms3.md §8.7, §7.2; plan §4, part S-F).

A6 (practical, the policy whose contract rules P1-P4 choose among contracts) on bench_e7r for one week under the
cumulative menus R, R+P, R+P+1h and R+P+1h+H (§7.2, M31), at mu / beta~ = 1 (e6/b/summary.json menus.<menu>.1):
(a) total cost over BL0a as a horizontal bar per menu (the median over 4 alignments x 3 policy seeds), stacked by
    cost component in a grey ramp (the segments split the median in proportion to the components' mean ratios to
    BL0a, components_over_bl0a), outlined in A6's color, with the 95% bootstrap interval of the median; the key
    names the outline and whiskers (labels "a6");
(b) the GPU-hour share per contract class (gpu_hour_share), stacked.
A segment narrower than SMALL_PT (stranding in (a); protected and GFS-like in (b)) is printed as text with its share
of the bar in percent at the bar's end, inside the bar left of the slivers (in (a) left of the whisker), in black or
white for contrast with the segments under it (small_shares).
cost(R) / cost(menu) and the mu side points at R+P are in the extract.

C62 (2026-11-24; the look of Fig. 3(a)): (a)'s components in Fig. 3(a)'s fills (COMPONENT_FILLS: lease light
grey, routing hatched, fallback mid grey, stranding near black; the grey ramp until C62) and its bar height; the
all-fallback level 1 as a reference line in (a); each panel's key one row on its letter's line (letter_key) instead
of a band inside the axes above the bars, so that the figure is 1.9 in high (2.2 in until C62) with the bars as high
as before; "Lease" for "Lease (rent, billed term)"; (b) slightly wider than (a) (AXES_RATIOS), for its key. The data
and their extract entries are unchanged.

The component split reads menus.<menu>.<mu>.components_over_bl0a ({component: mean over the runs}, as e6.py writes
it; §7.2's key list does not name it); where it is null the bar is drawn unstacked and the extract says so.

Run from code/sim: python -m figs.supp.sf_e6b [--from-extract [JSON]].
"""
from __future__ import annotations

import sys
import warnings
from typing import Any, Mapping, Sequence

from matplotlib.font_manager import FontProperties
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

from figs import style
from figs.common import cli, need, num_items, text_width_in
from figs.fig7_e2_e6 import text_on
from figs.inputs import Inputs

NAME = "sf_e6b"
E6B = "code/sim/out/e6/b/summary.json"
MENUS = ("R", "R+P", "R+P+1h", "R+P+1h+H")                  # §7.2, cumulative
MU = 1
COMPONENT_ORDER = ("lease", "loading", "routing", "fallback", "stranding")
# C62: "Lease" as in Fig. 3(a)'s key ("Lease (rent, billed term)" until C62, too long for (a)'s key on its letter's
# line, letter_key)
COMPONENT_LABEL = {"lease": "Lease", "loading": "Loading", "routing": "Routing",
                   "fallback": "Fallback", "stranding": "Stranding"}
CLASS_ORDER = ("spot-like", "AEP-82-like", "general", "GFS-like", "protected")
CLASS_LABEL = {"spot-like": "Spot-like", "AEP-82-like": "AEP-82-like", "general": "General", "GFS-like": "GFS-like",
               "protected": "Protected"}          # contract classes (types.py) in sentence case (plan §5)
# C62: 1.9 in (2.2 until C62): the keys moved from a band inside the axes, above the bars, to the panel letters'
# line (letter_key), which costs no height; the four rows are 0.35 in apart (0.32 in under the keys' band), the bars
# 14.1 pt high as before (BAR_H)
style.register_supplementary(NAME, "W2", 1.9)
BAR_H = 0.56                       # C62: Fig. 3(a)'s bar height in rows (fig4_v3.A_BAR_H; 0.62 at 9 pt)
BAR_EDGE_PT = 0.8                  # A6's outline of a bar in (a)
SMALL_PT = 2.0                     # a segment narrower than this cannot be matched to its key color: printed
SMALL_GAP_PT = 2.0                 # from the printed shares to the slivers
WHISKER_GAP_PT = 4.0               # C62: from the printed shares to the whisker in (a) (2 pt, SMALL_GAP_PT, until C62:
#                                    the whisker read as the text's underline continued)
# C62: (a)'s components in the fills of Fig. 3(a) (fig4_v3.COMPONENT_FILLS, C19): lease
# light grey, routing (and loading, zero here) white with a dense dark hatch, fallback mid grey, stranding near black,
# so that neighboring segments differ in lightness or texture in greyscale and the supplement's cost bars read as the
# main text's (until C62, four steps of the grey ramp, in which routing, a sliver, read as lease)
COMPONENT_FILLS = {"lease": {"facecolor": "#D9D9D9", "hatch": None},
                   "loading": {"facecolor": "#FFFFFF", "hatch": "xxxx"},
                   "routing": {"facecolor": "#FFFFFF", "hatch": "//////"},
                   "fallback": {"facecolor": "#808080", "hatch": None},
                   "stranding": {"facecolor": "#1A1A1A", "hatch": None}}
HATCH_COLOR = "#1A1A1A"            # the hatch lines (style's hatch.linewidth, 0.4 pt), as fig4_v3.HATCH_COLOR
OTHER_FILL = "#BDBDBD"             # a component outside COMPONENT_FILLS (none in e6/b/summary.json)
KEY_GAP_PT = 5.0                   # C62: from a panel letter's right end to its key (letter_key)
KEY_END_GAP_PT = 6.0               # C62: a key ends at least this far left of the next panel's slot or the page edge
KEY_HANDLE_EM = 1.0                # C62: a key's patches 1.0 x 0.8 em (7 x 5.6 pt) and 0.8 em between its entries, so
KEY_COLUMN_EM = 0.8                # that (b)'s five classes fit on its letter's line (3.0 in; 3.2 in at 1.2 and 1.0 em)
AXES_RATIOS = (0.94, 1.06)         # C62: (b) 0.19 in wider than (a), whose x axis has room to spare beyond the
#                                    whiskers, so that (b)'s key ends inside the page (letter_key)


def component_groups(raw: Mapping) -> dict:
    """Ledger components grouped as E2's totals (§6.7): lease_* -> lease, stranding_* -> stranding; 'total' and
    the parts of a group whose sum is also listed (lease, stranding) are left out, so nothing counts twice."""
    keys = {k: float(v) for k, v in raw.items() if v is not None and k != "total" and not k.endswith("_note")}
    out: dict = {}
    for k, v in keys.items():
        g = next((g for g in ("lease", "stranding") if k == g or k.startswith(g + "_")), k)
        if g != k and g in keys:
            continue                                     # a part of a group whose sum is listed
        out[g] = out.get(g, 0.0) + v
    return out


def menu_entry(e6b: Mapping, menu: str, mu) -> dict:
    """One menu at one mu; a menu without runs (e6.py writes `note`, n_runs 0 and every field null with its
    '*_note') gives a null total and empty shares with its note (§2.6), drawn as an empty row."""
    ent = need(e6b, "menus", menu, mu, what=E6B)
    cost = ent.get("cost_over_bl0a") if isinstance(ent.get("cost_over_bl0a"), Mapping) else {}
    lo, hi = (cost.get("median_ci95") or [None, None])[:2]
    total = cost.get("median")
    comps, note = {}, None
    raw = ent.get("components_over_bl0a")
    if isinstance(raw, Mapping) and raw:
        comps = component_groups(raw)
    elif total is not None:
        note = "menus.<menu>.<mu>.components_over_bl0a null: bar drawn unstacked"
    shares = ent.get("gpu_hour_share") if isinstance(ent.get("gpu_hour_share"), Mapping) else {}
    out = {"menu": menu, "mu": float(mu), "total": total, "ci_lo": lo, "ci_hi": hi, "components": comps,
           "components_note": note, "cost_R_over_cost": ent.get("cost_R_over_cost"),
           "shares": {k: v for k, v in shares.items() if not k.endswith("_note")}}
    if total is None:
        out["note"] = ent.get("note") or cost.get("note") or cost.get("median_note") or "null"
    return out


def build(inp: Inputs) -> dict:
    e6b = inp.json(E6B)
    menus = need(e6b, "menus", what=E6B)
    order = [m for m in MENUS if m in menus] + [m for m in menus if m not in MENUS and not m.endswith("_note")]
    missing = [m for m in MENUS if m not in menus]
    if missing:
        raise KeyError(f"{E6B}: menus {missing} missing")
    a = {m: menu_entry(e6b, m, MU) for m in order}
    side = {m: {k: menu_entry(e6b, m, mu) for mu, k, _ in num_items(menus[m]) if mu != MU} for m in order}
    notes = sorted({v["components_note"] for v in a.values() if v["components_note"]})
    for n in notes:
        warnings.warn(f"{NAME}: {n}", style.FigureWarning, stacklevel=2)
    return {"menus": order, "a": a, "b": {m: a[m]["shares"] for m in order},
            "mu_side_points": side,
            "labels": {"a_x": "Total cost / all-fallback", "b_x": "GPU-hour share", "y": "Menu",
                       "components": COMPONENT_LABEL, "classes": CLASS_LABEL, "no_data": "no runs",
                       "a6": style.policy("a6").label, "small": "{} {}%",
                       "note": "A6 on bench_e7r, one week, mu/beta~ = 1; whiskers: 95% bootstrap of the median over "
                               "4 alignments x 3 seeds; segments split the median total in proportion to the "
                               "components' mean ratios to BL0a", "components_note": notes},
            "sources": list(inp.sources)}


def _ordered(keys, order) -> list[str]:
    return [k for k in order if k in keys] + sorted(k for k in keys if k not in order)


def percent(share: float) -> str:
    """A share in percent with one decimal ('<0.1' below 0.05%)."""
    return "<0.1" if share < 0.0005 else f"{100.0 * share:.1f}"


def small_shares(ax, i: int, segs: Sequence[tuple], label: str, *, end: float | None = None,
                 end_gap_pt: float = SMALL_GAP_PT, va: str = "center") -> None:
    """Row i's segments (name, left, width, color) narrower than SMALL_PT, printed as labels["small"] (name and share
    of the bar in percent), joined by commas, right-aligned SMALL_GAP_PT left of the first of them (or `end_gap_pt`
    left of `end`, the whisker's left end in (a), if that lies further left), inside the bar and vertically centered
    (`va`), in black or white for the segments under the text (text_on); StyleError if the text would start left of
    the axis. sf_e7_mix imports it: the defaults keep its drawing; sf_e6b's own (a) and (b) pass (C62) end_gap_pt
    WHISKER_GAP_PT and va 'center_baseline', the menu names' alignment (with 'center' the text sat 0.7 pt below
    them)."""
    to_pt = 72.0 / ax.figure.dpi
    pt = (ax.transData.transform((1.0, i))[0] - ax.transData.transform((0.0, i))[0]) * to_pt   # points per unit
    total = sum(w for _, _, w, _ in segs)
    small = [(n, x0, w) for n, x0, w, _ in segs if w * pt < SMALL_PT and w > 0]
    if not small or total <= 0:
        return
    text = ", ".join(label.format(n, percent(w / total)) for n, _, w in small)
    right = min(x0 for _, x0, _ in small) - SMALL_GAP_PT / pt
    if end is not None:
        right = min(right, end - end_gap_pt / pt)
    left = right - text_width_in(ax.figure, text) * 72.0 / pt
    under = [c for _, x0, w, c in segs if x0 < right and x0 + w > left and w > 0]
    if not under or left < ax.get_xlim()[0]:
        raise style.StyleError(f"{NAME}: no room left of the narrow segments of row {i} for {text!r}")
    ax.text(right, i, text, ha="right", va=va, fontsize=style.TICK_PT, color=text_on(under), zorder=1.8)


def letter_key(ax, letter, pairs: Sequence[tuple], *, end_in: float):
    """C62: a panel's key as one frameless row on its letter's line (as Fig. 2(a)'s key, fig2_e1a.key_a): starting
    KEY_GAP_PT right of the bold letter, its labels on the letter's baseline (the legend's bottom, without border
    padding, is its text's descent line, "lp" as matplotlib lays text out; anchored that far below the baseline),
    which costs the figure no height (until C62 the keys filled a band inside the axes above the bars, which the y
    range was extended for). StyleError if the row ends less than KEY_END_GAP_PT left of `end_in` (inches: the next
    panel's slot, or the page's right margin)."""
    fig = ax.figure
    r = fig.canvas.get_renderer()
    _, _, descent = r.get_text_width_height_descent("lp", FontProperties(size=style.TICK_PT), ismath=False)
    W, H = fig.get_size_inches()
    x0 = letter.get_window_extent(r).x1 / fig.dpi + KEY_GAP_PT / style.BP_PER_IN
    base_in = letter.get_position()[1] * H
    h, t = zip(*pairs)
    # in figure coordinates (style.ink_outside_sides checks the page with a border that moves only what is placed
    # through fig.transFigure)
    leg = ax.legend(list(h), list(t), loc="lower left", bbox_to_anchor=(x0 / W, (base_in - descent / fig.dpi) / H),
                    bbox_transform=fig.transFigure, ncol=len(h), frameon=False, borderpad=0.0, borderaxespad=0.0,
                    handlelength=KEY_HANDLE_EM, handleheight=0.8, columnspacing=KEY_COLUMN_EM)
    leg._sublet_role = "letter_key"
    end = leg.get_window_extent(r).x1 / fig.dpi
    if end > end_in - KEY_END_GAP_PT / style.BP_PER_IN + 1e-9:
        raise style.StyleError(f"{NAME}: the key of {letter.get_text()} ends at {end:.3f} in, less than "
                               f"{KEY_END_GAP_PT} pt left of {end_in:.3f} in")
    return leg


SEPARATOR_PT = 0.4                 # (b): the white line between neighboring segments of a bar


def separators(ax, i: int, segs: Sequence[tuple], texts: Sequence) -> None:
    """(b) (C62): a white SEPARATOR_PT line at each boundary between two segments of row i (segs: (name, left, width,
    color)) across the bar, except under a printed share (`texts`, small_shares'), whose letters it would cut (as
    built, the segments' white edges ran between "F" and "S" of "GFS-like 0.6%, ..." where the text crosses from the
    AEP-82-like into the general segment); after the final scales."""
    r = ax.figure.canvas.get_renderer()
    inv = ax.transData.inverted()
    spans = [tuple(inv.transform([(bb.x0, 0.0), (bb.x1, 0.0)])[:, 0]) for bb in (t.get_window_extent(r) for t in texts)]
    drawn = [(x0, w) for _, x0, w, _ in segs if w > 0]
    for (x0, w), _ in zip(drawn[:-1], drawn[1:]):
        x = x0 + w
        if any(a <= x <= b for a, b in spans):
            continue
        ax.plot([x, x], [i - BAR_H / 2, i + BAR_H / 2], color="white", linewidth=SEPARATOR_PT, solid_capstyle="butt",
                zorder=1.55, label="_nolegend_")


def component_fill(c: str) -> dict:
    """barh / Patch keyword arguments of a component's fill (COMPONENT_FILLS; the hatch in HATCH_COLOR, no edge)."""
    f = COMPONENT_FILLS.get(c, {"facecolor": OTHER_FILL, "hatch": None})
    return dict(facecolor=f["facecolor"], edgecolor=HATCH_COLOR, linewidth=0, hatch=f["hatch"])


def draw(data: Mapping) -> Any:
    """C62: (a)'s components in Fig. 3(a)'s fills (COMPONENT_FILLS), its bars Fig. 3(a)'s height (BAR_H) and the
    all-fallback level 1 as a reference line; each panel's key on its letter's line (letter_key), so that the bars
    take the axes' full height (the figure is 0.3 in lower)."""
    lab = data["labels"]
    menus = data["menus"]
    fig = style.new_figure(NAME)
    left = style.ytick_reserve(fig, menus, ylabel=True)
    ax_a, ax_b = style.panel_row(fig, AXES_RATIOS, left=(left, style.LEFT_SHARED))
    a6 = style.policy("a6")
    comps = _ordered({c for m in menus for c, v in data["a"][m]["components"].items() if v > 0},
                     COMPONENT_ORDER)                    # a component that is zero in every menu has no segment
    fills = {c: component_fill(c) for c in comps}
    segs_a, segs_b = {}, {}                              # row: [(name, left, width, color)] (small_shares)
    for i, m in enumerate(menus):
        e = data["a"][m]
        total = e["total"]
        if total is None:                                # a menu without runs: an empty row, its note in the extract
            for ax in (ax_a, ax_b):
                ax.text(0.01, i, lab.get("no_data", "no runs"), transform=ax.get_yaxis_transform(), ha="left",
                        va="center", fontsize=style.TICK_PT, color=style.THEORY_LABEL_GREY)
            continue
        csum = sum(e["components"].get(c, 0.0) for c in comps)
        x0, segs_a[i] = 0.0, []
        for c in comps:
            v = e["components"].get(c, 0.0)
            w = total * v / csum if csum > 0 else 0.0
            ax_a.barh(i, w, left=x0, height=BAR_H, zorder=1.5, **fills[c])
            segs_a[i].append((lab["components"].get(c, c), x0, w, fills[c]["facecolor"]))
            x0 += w
        if not comps:
            ax_a.barh(i, total, height=BAR_H, color=OTHER_FILL, linewidth=0, zorder=1.5)
        ax_a.barh(i, total, height=BAR_H, fill=False, edgecolor=a6.color, linewidth=BAR_EDGE_PT, zorder=1.6)
        if e["ci_lo"] is not None and e["ci_hi"] is not None:
            style.errorbars(ax_a, "a6", [total], [i], [e["ci_lo"]], [e["ci_hi"]], orientation="x", zorder=1.7)
    xmax = max(max(data["a"][m]["ci_hi"] or 0.0, data["a"][m]["total"] or 0.0) for m in menus) or 1.0
    ax_a.set_xlim(0, xmax * 1.04)
    style.reference_line(ax_a, x=1.0)                    # C62: the all-fallback bill, behind the bars
    ax_a.set_yticks(range(len(menus)), menus)
    ax_a.set_xlabel(lab["a_x"])
    ax_a.set_ylabel(lab["y"])
    ax_a.xaxis.set_major_formatter(style.PLAIN)
    classes = _ordered({k for m in menus for k, v in data["b"][m].items() if v}, CLASS_ORDER)   # no all-zero class
    colors = dict(zip(classes, style.ramp(len(classes), "cividis")))
    for i, m in enumerate(menus):
        x0, segs_b[i] = 0.0, []
        for k in classes:
            v = float(data["b"][m].get(k) or 0.0)
            ax_b.barh(i, v, left=x0, height=BAR_H, color=colors[k], linewidth=0, zorder=1.5)
            segs_b[i].append((lab.get("classes", {}).get(k, k), x0, v, colors[k]))
            x0 += v
    ax_b.set_xlim(0, 1)
    ax_b.set_yticks(range(len(menus)), [""] * len(menus))
    ax_b.set_xlabel(lab["b_x"])
    ax_b.xaxis.set_major_formatter(style.PLAIN)
    for ax in (ax_a, ax_b):
        ax.set_ylim(len(menus) - 0.5, -0.5)              # menu R on top, the rows filling the axes
    small = lab.get("small", "{} {}%")
    for i, m in enumerate(menus):                        # after the final scales
        if i in segs_a:
            small_shares(ax_a, i, segs_a[i], small, end=data["a"][m]["ci_lo"], end_gap_pt=WHISKER_GAP_PT,
                         va="center_baseline")
        if i in segs_b:
            n_texts = len(ax_b.texts)
            small_shares(ax_b, i, segs_b[i], small, va="center_baseline")
            separators(ax_b, i, segs_b[i], ax_b.texts[n_texts:])
    for ax in (ax_a, ax_b):
        ax.tick_params(axis="y", length=0)
        ax.spines["left"].set_visible(False)
    letter_a, letter_b = style.panel_letters([ax_a, ax_b])
    # the keys: (a) the components, then A6's outline and whisker as one entry; (b) the contract classes
    pairs = [(Patch(**fills[c]), lab["components"].get(c, c)) for c in comps]
    pairs.append(((Patch(fill=False, edgecolor=a6.color, linewidth=BAR_EDGE_PT),
                   Line2D([], [], color=a6.text_color, linewidth=style.UNCERTAINTY_PT)), lab.get("a6", a6.label)))
    W = fig.get_size_inches()[0]
    letter_key(ax_a, letter_a, pairs, end_in=ax_b._sublet_slot_left_in)
    if classes:
        letter_key(ax_b, letter_b, [(Patch(facecolor=colors[k], edgecolor="none"), lab.get("classes", {}).get(k, k))
                                    for k in classes], end_in=W - style.MARGIN_RIGHT)
    return fig


def main(argv: Sequence[str] | None = None) -> dict:
    return cli(NAME, build, draw, argv, supplementary=True, doc=__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
