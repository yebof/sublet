"""sf_e8: E8, the fluid model's cost error against the request-level replay (design/sim_spec_ms4.md §8.2, §7; plan §4,
part S-F).

E = (C_replay - C_fluid) / C_replay, both in overflow accounting (§7.6), against the demand-smoothing window (5, 15,
60 min; log x):
(a) per LLM tier S, M, L (non-policy categories in the three darker of style.ramp(4, "cividis"), plan §5, each with
    its own marker: the lightest of ramp(3) printed at the reference line's grey), A6's fluid runs replayed with the
    Azure 2024 conversation requests at mu / beta~ = 1: the median over the alignments with their minimum and maximum
    as a bar (e8/summary.json error.<tier>.<win>.1);
(b) the Mooncake conversation hour (tier M, mu / beta~ = 1, alignment 1) without and with prefix hits, two grey
    shades (mooncake.<win>.<prefix>, prefix 'off' and 'on'), replayed through the placements of each window's fluid
    run in its hour of largest fluid overflow (§7.7), which can differ between windows (mooncake.<win>.<prefix>.hour,
    in the extract as b.<prefix>.hour).
The level E = 0 is a reference line. The windows are the summary's keys (meta.grid.windows): a reduced summary keys
only its grid (windows 5 and 60), so a window it lacks is absent rather than null and has no point.

E is at most 1 (C_fluid >= 0) but unbounded below: with prefix hits the replay can cost far less than the fluid model
(C_replay near 0), so E can be far below -1. A value below FLOOR is drawn as a downward arrow ending on the axis
floor at FLOOR with its value printed above it (ms4_lib.off_scale_marks, the value at least 2 pt inside the y spine),
so that one hour does not stretch the axis and hide the other values; a min-max bar whose minimum lies below FLOOR
ends at the floor in an arrowhead (bar_cut_marks); the extract lists these points (`off_scale`, the minimum's value
with field 'min', the rule in labels.off_scale). The other mu values (0.2, 0.5, 2) are in the extract (`mu_all`), not
drawn. The y label is "Relative cost error $E$" (E as a math symbol, italic).

No legend: the series are labeled directly in 7 pt (style.TICK_PT), so that both panels keep their full height (as
built, a three-row tier legend over (a), with (b)'s spine held level, left the data about half the height of the
figure, and (b)'s legend showed a diamond on a line for prefix hits, a series drawn only as arrows; print check). (a):
"S", "M", "L" in each tier's color (darkened to 4.5:1 against white, style.readable_on_white) right of the line's last
point, stacked apart where they would touch (common.stack_labels); the x axes of both panels extend right far enough
to hold them, so that the windows sit at one position in both panels. (b): each prefix mode's name in its grey (darkened
likewise) on the free space nearest its points (common.place_label), for prefix hits nearest the off-scale values too;
a mode with every value off scale is named "... (off scale)", in two lines where one does not fit; a label keeps
its white halo only where its box overlaps a line, grid, bar, arrow or marker (ms4_lib.drop_idle_halos: a haloed
label is written to the PDF as outlines, not text, and as built both labels were missing from its text layer; print
check). The y ticks are at 1, 2, 5 x 10^k, about Y_BINS of them (the automatic locator gave -1, -0.75, ..., 0 at
full height, whose wider labels pushed (b)'s y label onto (a)'s end labels).

labels.note states the caption material, computed from the summary, with the policy named by its legend name
(meta.policy.id through STYLE_KEY to its style.POLICIES label): where (b)'s hour is placed, by the hour's index in
the week per window, the windows that share an hour grouped (hour_note; print check: at 60 min the hour is not that
of 5 and 15 min); with prefix hits, whether the replayed hour has no routing, fallback or stranding cost at every
window (C_replay then equals the fluid run's lease cost, within LEASE_REL; the costs by window are stated), and the
replayed block-hit ratio against the trace's infinite-cache ratio (mooncake.<win>.on.hit_ratio, global_hit_ratio),
which bounds any replica-level ratio from above (check E8-5).

C62 (7-pt text): each panel has a title on its letter's baseline naming its replay (labels.titles: "Azure 2024 week,
per LLM tier", "Mooncake hour, tier M"), so that the end labels S, M, L read as tiers; (b) shares (a)'s y label, E in
both, so its left reserve holds its tick labels alone (as built a second "Relative cost error E" stood between the
panels) and the panels gain the width; the y ticks are fixed at the data's limits and the top of each y axis is raised
where its highest tick label would come within TOP_TICK_GAP_PT of the axes top (top_tick_room), clear of the letter
and title above it. Fix round: the titles at the caption size (style.LABEL_PT, as C62 sets panel titles; at TICK_PT as
first restyled), (a)'s at least TITLE_GAP_PT left of (b)'s letter (title_clear; 7.1 pt on the real data).

Run from code/sim: python -m figs.supp.sf_e8 [--from-extract [JSON]].
"""
from __future__ import annotations

import sys
from typing import Any, Mapping, Sequence

import numpy as np
from matplotlib.ticker import FixedLocator, MaxNLocator

from figs import style
from figs.common import (KEY_PAD_PT, TOP_TICK_GAP_PT, align_baselines, cli, finite, maybe, need, num_items, panel_title,
                         place_label, points_pt, stack_labels, text_width_in)
from figs.inputs import Inputs
from figs.supp.ms4_lib import (ARROW_PT, center_xlabel, dodge, drop_idle_halos, finite_values, level_axis,
                               off_scale_marks)

NAME = "sf_e8"
E8 = "code/sim/out/e8/summary.json"
KEYS = style.SUPP_POLICIES_MS4[NAME]          # none: tiers and prefix modes are non-policy categories
TIERS = ("S", "M", "L")
TIER_MARKERS = {"S": "o", "M": "s", "L": "^"}
PREFIX = ("off", "on")
PREFIX_MARKERS = {"off": "o", "on": "D"}
MU = 1
FLOOR = -1.0                  # (b): the axis floor; a value below it is drawn as an arrow with its value
Y_PAD = 0.08                  # y margin beyond the drawn values, as a share of their range (not in §8.2)
DODGE_OCT_E8 = 0.06           # x dodge between the series, in octaves
X_PAD = 1.35                  # the x axes extend this factor beyond the first and last window (at least)
Y_BINS, Y_STEPS = 4, (1, 2, 5, 10)    # y ticks at 1, 2, 5 x 10^k, about 4: -1, -0.5, 0 in (b) (the auto locator
#                                     gave -1, -0.75, ... at full height, whose wider labels pushed (b)'s y label onto
#                                     (a)'s end labels)
END_DX_PT = 2.0               # (a): gap between a line's last marker and its label (not in §8.2)
END_GAP_PT = 0.5              # (a): least gap between two stacked end labels (not in §8.2)
REPLAY_PARTS = ("routing", "fallback", "stranding")
LEASE_REL = 1e-9              # C_replay equals the lease cost within this relative tolerance (float sums)
STYLE_KEY = {"A6": "a6"}      # the summary's meta.policy.id -> its registry key, whose label the note names
TITLE_GAP_PT = 4.0            # C62 fix round: a panel title ends at least this far left of the next panel's letter
style.register_supplementary(NAME, "W1", 2.2)
# C62: panel titles name each panel's replay (the caption's (a) and (b)), on the letters' baseline
LABELS = {"x": "Smoothing window (min)", "y": r"Relative cost error $E$",
          "titles": {"a": "Azure 2024 week, per LLM tier", "b": "Mooncake hour, tier M"},
          "tier": "Tier {}", "tier_end": "{}", "prefix": {"off": "No prefix hits", "on": "Prefix hits"},
          "all_off_scale": "{} (off scale)",
          "off_scale": f"values below {FLOOR:g} are drawn as an arrow to the axis floor at {FLOOR:g} with the value "
                       f"printed above it; a min-max bar whose minimum lies below {FLOOR:g} ends there in an "
                       "arrowhead (its value in off_scale)",
          "hour": "replayed through the placements of each window's fluid run in its hour of largest fluid overflow: "
                  "{hours}",
          "note": "E = (C_replay - C_fluid) / C_replay, overflow accounting; (a) {policy}'s fluid runs replayed with the "
                  "Azure 2024 conversation week at mu/beta~ = 1, median over the alignments with min-max bars, the "
                  "tiers S, M, L labeled at the line ends; (b) the Mooncake conversation hour, tier M, mu/beta~ = 1, "
                  "alignment 1"}


def build(inp: Inputs) -> dict:
    e8 = inp.json(E8)
    err = need(e8, "error", what=E8)
    a, mu_all = {}, {}
    for t in TIERS:
        s = {"win": [], "median": [], "min": [], "max": [], "n": [], "note": []}
        for w, wk, by_mu in num_items(need(err, t, what=f"{E8} error")):
            ent, note = maybe(by_mu, MU)
            ent = ent if isinstance(ent, Mapping) else {}
            for f, v in zip(s, (w, ent.get("median"), ent.get("min"), ent.get("max"), ent.get("n"),
                                note or (None if ent.get("median") is not None else ent.get("median_note") or "null"))):
                s[f].append(v)
            mu_all.setdefault(t, {})[wk] = {mk: (v.get("median") if isinstance(v, Mapping) else None)
                                            for _, mk, v in num_items(by_mu)}
        a[t] = s
    b = {}
    mc = need(e8, "mooncake", what=E8)
    ghr = set()
    for pre in PREFIX:
        s = {"win": [], "error": [], "hit_ratio": [], "C_fluid": [], "C_replay": [], "lease": [], "replay": [],
             "hour": [], "note": []}
        for w, wk, by_pre in num_items(mc):
            ent, note = maybe(by_pre, pre)
            ent = ent if isinstance(ent, Mapping) else {}
            s["win"].append(w)
            s["error"].append(ent.get("error"))
            s["hit_ratio"].append(ent.get("hit_ratio"))
            s["C_fluid"].append(ent.get("C_fluid"))
            s["C_replay"].append(ent.get("C_replay"))
            fl, rp = ent.get("fluid"), ent.get("replay")
            s["lease"].append(fl.get("lease") if isinstance(fl, Mapping) else None)
            s["replay"].append({f: rp.get(f) for f in REPLAY_PARTS} if isinstance(rp, Mapping) else None)
            hr = ent.get("hour")
            s["hour"].append({"index": hr.get("index"), "start_s": hr.get("start_s")} if isinstance(hr, Mapping)
                             else None)
            s["note"].append(note or (None if ent.get("error") is not None else ent.get("error_note") or "null"))
            if ent.get("global_hit_ratio") is not None:
                ghr.add(ent["global_hit_ratio"])
        b[pre] = s
    off = [{"panel": "b", "prefix": pre, "win": w, "error": v} for pre in PREFIX
           for w, v in zip(b[pre]["win"], b[pre]["error"]) if v is not None and v < FLOOR]
    off += [{"panel": "a", "tier": t, "win": w, "value": v, "field": f} for t in TIERS for f in ("median", "min")
            for w, v in zip(a[t]["win"], a[t][f]) if v is not None and v < FLOOR]
    global_hr = sorted(ghr)[0] if len(ghr) == 1 else None
    pid, _ = maybe(e8, "meta", "policy", "id")
    head = LABELS["note"].format(policy=style.POLICIES[STYLE_KEY[pid]].label if pid in STYLE_KEY else
                                 (pid or "the policy"))
    hours = hour_note(b)
    note = "; ".join(p for p in (f"{head}, {hours}" if hours else head, prefix_note(b["on"], global_hr)) if p)
    return {"a": a, "b": b, "mu_all": mu_all, "off_scale": off, "floor": FLOOR, "global_hit_ratio": global_hr,
            "windows": sorted({w for t in TIERS for w in a[t]["win"]} | {w for p in PREFIX for w in b[p]["win"]}),
            "labels": {**LABELS, "note": note},
            "meta": {"git_revision": need(e8, "meta", "git_revision", what=E8), "reduced": bool(e8["meta"].get("reduced")),
                     "grid": e8["meta"].get("grid")},
            "sources": list(inp.sources)}


def _vals(v: Sequence[float]) -> str:
    return ", ".join(f"{x:.3g}" for x in v)


def _wins(ws: Sequence[float]) -> str:
    """'5 and 15 min', '5, 15 and 60 min'."""
    w = [f"{v:g}" for v in ws]
    return (w[0] if len(w) == 1 else ", ".join(w[:-1]) + " and " + w[-1]) + " min"


def hour_note(b: Mapping) -> str:
    """The clause, appended to (b)'s sentence of the note, on where (b)'s Mooncake hour is placed, from the summary
    (mooncake.<win>.<prefix>.hour): the hour of the week with the largest fluid overflow in each window's fluid run
    (§7.7), by its index (counted from 0; a start second other than index x 3600 is stated), the windows that share
    an hour grouped. Where the two prefix modes of a window name different hours, each mode's hour is given; empty
    where no window has an hour."""
    by_win: dict[float, dict] = {}
    for pre in PREFIX:
        for w, h in zip(b[pre]["win"], b[pre].get("hour", [])):
            if isinstance(h, Mapping) and h.get("index") is not None:
                by_win.setdefault(w, {})[pre] = h
    if not by_win:
        return ""

    def idx(h: Mapping) -> str:
        i = int(h["index"])
        ok = h.get("start_s") is None or int(h["start_s"]) == 3600 * i
        return f"{i}" if ok else f"{i} (start {int(h['start_s'])} s)"
    groups: dict[str, list] = {}
    for w in sorted(by_win):
        hs = by_win[w]
        key = (idx(next(iter(hs.values()))) if len({idx(h) for h in hs.values()}) == 1 else
               ", ".join(f"{idx(h)} ({LABELS['prefix'][p].lower()})" for p, h in hs.items()))
        groups.setdefault(key, []).append(w)
    parts = [f"hour {k}{' of the week (counted from 0)' if i == 0 else ''} at {_wins(ws)}"
             for i, (k, ws) in enumerate(groups.items())]
    return LABELS["hour"].format(hours=", ".join(parts))


def prefix_note(on: Mapping, global_hr: float | None) -> str:
    """The caption clause on (b)'s prefix hits, from the summary: whether the replayed hour has no routing, fallback or
    stranding cost at every window with an error (C_replay is then the lease cost alone, within LEASE_REL), with the
    costs by window; the replayed block-hit ratio against the trace's infinite-cache ratio. Empty without an error."""
    idx = [i for i, e in enumerate(on["error"]) if e is not None]
    if not idx:
        return ""
    wins = ", ".join(f"{on['win'][i]:g}" for i in idx)
    rep = [on["replay"][i] for i in idx]
    c_rep, c_fl, lease = ([on[f][i] for i in idx] for f in ("C_replay", "C_fluid", "lease"))
    have = all(isinstance(r, Mapping) and all(r.get(f) is not None for f in REPLAY_PARTS) for r in rep) and \
        all(v is not None for v in c_rep + c_fl + lease)
    if not have:
        return ""
    lease_only = all(r[f] == 0 for r in rep for f in REPLAY_PARTS) and \
        all(abs(c - ls) <= LEASE_REL * max(1.0, abs(ls)) for c, ls in zip(c_rep, lease))
    if lease_only:
        s = (f"(b) with prefix hits the replayed hour has no routing, fallback or stranding cost at any window, so "
             f"C_replay is the lease cost alone ({_vals(c_rep)} at {wins} min, against C_fluid {_vals(c_fl)})")
    else:
        parts = "; ".join(f"{f} {_vals([r[f] for r in rep])}" for f in REPLAY_PARTS)
        s = (f"(b) with prefix hits the replayed hour's costs at {wins} min: lease {_vals(lease)}; {parts}; C_replay "
             f"{_vals(c_rep)} against C_fluid {_vals(c_fl)}")
    hr = [on["hit_ratio"][i] for i in idx if on["hit_ratio"][i] is not None]
    if hr:
        lo, hi = min(hr), max(hr)
        rng = f"{lo:.3f}" if f"{lo:.3f}" == f"{hi:.3f}" else f"{lo:.3f}-{hi:.3f}"
        s += f"; each replica keeps an infinite prefix cache, and the replayed block-hit ratio is {rng}"
        if global_hr is not None:
            s += (f", against the trace's infinite-cache ratio {global_hr:.3f}, an upper bound on any replica-level "
                  "ratio (E8-5)")
    return s


def y_limits(values, floor: float) -> tuple[float, float, bool]:
    """(lo, hi, clipped) of a linear E axis: the drawn values and 0 with a margin, the bottom at `floor` (less the
    margin) where a value lies below it."""
    v = finite_values(values)
    clipped = bool(v.size and v.min() < floor)
    v = np.append(v[v >= floor], 0.0)
    lo, hi = float(v.min()), float(v.max())
    if clipped:
        lo = floor
    pad = Y_PAD * max(hi - lo, 0.1)
    return lo - pad, hi + pad, clipped


def top_tick_room(ax) -> None:
    """C62: raise the top of a linear y axis so that its highest tick label ends TOP_TICK_GAP_PT below the axes top,
    clear of the panel letter and title on the axes top (common._top_tick_room's rule for log axes): (b)'s narrow left
    reserve (its tick labels alone) puts its letter over its tick labels' column."""
    y0, y1 = ax.get_ylim()
    ticks = [t for t in ax.yaxis.get_majorticklocs() if y0 <= t <= y1]
    if not ticks:
        return
    t = max(ticks)
    r = ax.figure.canvas.get_renderer()
    to_pt = style.BP_PER_IN / ax.figure.dpi
    up = [tk.label1.get_window_extent(r).y1 - ax.transData.transform((0.0, t))[1]
          for tk in ax.yaxis._update_ticks() if abs(tk.get_loc() - t) <= 1e-9 * max(1.0, abs(t))
          and tk.label1.get_visible()]
    room = (max(up) * to_pt if up else 0.5 * style.TICK_PT) + TOP_TICK_GAP_PT
    h_pt = style.axes_rect_in(ax)[3] * style.BP_PER_IN
    if (y1 - t) / (y1 - y0) * h_pt < room:
        ax.set_ylim(y0, (t * h_pt - room * y0) / (h_pt - room))


def draw_a(ax, a: Mapping, lab: Mapping, colors: Mapping, floor: float) -> None:
    n = len(TIERS)
    for i, t in enumerate(TIERS):
        s = a[t]
        x = dodge(s["win"], i, n, DODGE_OCT_E8)
        y, lo, hi = finite(s["median"]), finite(s["min"]), finite(s["max"])
        kw = dict(color=colors[t], marker=TIER_MARKERS[t], markersize=style.MARKER_PT,
                  markeredgewidth=style.MARKER_EDGE_PT, markeredgecolor=colors[t], markerfacecolor=colors[t],
                  linewidth=style.LINE_PT, zorder=style.Z_DATA, label=lab["tier"].format(t))
        yc = np.where(np.isfinite(y) & (y < floor), np.nan, y)
        ax.plot(x, yc, **kw)
        ok = np.isfinite(lo) & np.isfinite(hi) & np.isfinite(y) & (hi > lo)
        if ok.any():
            ax.errorbar(x[ok], y[ok], yerr=np.vstack([y[ok] - np.maximum(lo[ok], floor), np.maximum(hi[ok], floor)
                                                      - y[ok]]).clip(min=0), fmt="none", ecolor=colors[t],
                        elinewidth=style.UNCERTAINTY_PT, capsize=0, zorder=style.Z_DATA - 0.01, label="_nolegend_")
        bar_cut_marks(ax, x[ok & (y >= floor) & (lo < floor)], floor, colors[t])


CUT_ARROW_PT = 0.6 * ARROW_PT     # (a): length of the arrowhead that ends a bar cut at the floor (not in §8.2)


def bar_cut_marks(ax, xs, floor: float, color: str) -> None:
    """An arrowhead on the bar of each x in `xs`, pointing down onto the axis floor, where the bar's minimum lies below
    it (the value is in the extract's off_scale), so that a cut bar does not read as a minimum of `floor`."""
    for x in xs:
        ann = ax.annotate("", xy=(x, floor), xytext=(0.0, CUT_ARROW_PT), textcoords="offset points", xycoords="data",
                          arrowprops=dict(arrowstyle="-|>,head_length=0.4,head_width=0.2", color=color,
                                          linewidth=style.UNCERTAINTY_PT, shrinkA=0.0, shrinkB=0.0),
                          annotation_clip=False, zorder=style.Z_DATA + 0.05)
        ann._sublet_role = "bar_cut_arrow"


def draw_b(ax, b: Mapping, lab: Mapping, shades: Mapping, floor: float) -> None:
    for i, pre in enumerate(PREFIX):
        s = b[pre]
        x = dodge(s["win"], i, len(PREFIX), DODGE_OCT_E8)
        y = finite(s["error"])
        yc = np.where(np.isfinite(y) & (y < floor), np.nan, y)
        ax.plot(x, yc, color=shades[pre], marker=PREFIX_MARKERS[pre], markersize=style.MARKER_PT,
                markeredgewidth=style.MARKER_EDGE_PT, markeredgecolor=shades[pre],
                markerfacecolor=shades[pre] if pre == "off" else "white", linewidth=style.LINE_PT, zorder=style.Z_DATA,
                label=lab["prefix"][pre])


def end_items(a: Mapping, floor: float) -> list[tuple[str, float, float]]:
    """(tier, x, y) of each tier line's last drawn point (dodged x; a median below the floor is not drawn)."""
    out = []
    for i, t in enumerate(TIERS):
        x, y = dodge(a[t]["win"], i, len(TIERS), DODGE_OCT_E8), finite(a[t]["median"])
        ok = np.nonzero(np.isfinite(x) & np.isfinite(y) & (y >= floor))[0]
        if ok.size:
            j = ok[np.argmax(x[ok])]
            out.append((t, float(x[j]), float(y[j])))
    return out


def end_room(ax, items: Sequence[tuple[str, float, float]], lab: Mapping) -> float | None:
    """The right x limit of a log axis (left limit kept) at which the end labels of `items` fit inside the axes:
    each label END_DX_PT right of its marker's edge and KEY_PAD_PT clear of the axes' right side; None if the
    current limit holds them."""
    x_lo, x_hi = ax.get_xlim()
    w_pt = style.axes_rect_in(ax)[2] * style.BP_PER_IN
    span = np.log(x_hi / x_lo)
    need = span
    for t, x, _ in items:
        room = 0.5 * (style.MARKER_PT + style.MARKER_EDGE_PT) + END_DX_PT + \
            text_width_in(ax.figure, lab["tier_end"].format(t)) * style.BP_PER_IN + KEY_PAD_PT
        if room >= w_pt:
            continue
        need = max(need, w_pt * np.log(x / x_lo) / (w_pt - room))
    return float(x_lo * np.exp(need)) if need > span * (1 + 1e-12) else None


def end_labels(ax, items: Sequence[tuple[str, float, float]], lab: Mapping, colors: Mapping) -> list:
    """The tier names right of the lines' last points, in the tiers' colors darkened for text, stacked apart in one
    column where they would touch (stack_labels), inside the axes' height."""
    if not items:
        return []
    fig = ax.figure
    r = fig.canvas.get_renderer()
    to_pt = style.BP_PER_IN / fig.dpi
    dx = 0.5 * (style.MARKER_PT + style.MARKER_EDGE_PT) + END_DX_PT
    texts = []
    for t, x, y in items:
        txt = ax.annotate(lab["tier_end"].format(t), xy=(x, y), xytext=(dx, 0.0), textcoords="offset points",
                          ha="left", va="center", fontsize=style.TICK_PT, color=style.readable_on_white(colors[t]),
                          zorder=style.Z_THEORY_LABEL, annotation_clip=False)
        txt._sublet_role = "direct_label"
        texts.append(txt)
    ys = [ax.transData.transform((x, y))[1] * to_pt for _, x, y in items]
    hs = [t.get_window_extent(r).height * to_pt for t in texts]
    bb = ax.get_window_extent(r)
    pos = stack_labels(ys, hs, gap=END_GAP_PT, bottom=bb.y0 * to_pt, top=bb.y1 * to_pt)
    for txt, y0, y1 in zip(texts, ys, pos):
        txt.xyann = (dx, y1 - y0)
    return texts


def prefix_labels(ax, b: Mapping, lab: Mapping, shades: Mapping, floor: float, marks: Mapping) -> list:
    """Each prefix mode's name on the free space of (b) nearest its drawn points (and, for a mode with off-scale
    values, the tops of their printed values), nearer to them than to the other mode's (common.place_label); a mode
    whose every value is off scale is named "<name> (off scale)", in two lines where one does not fit. StyleError
    where a name fits nowhere."""
    to_pt = style.BP_PER_IN / ax.figure.dpi
    r = ax.figure.canvas.get_renderer()
    pts = {}
    for i, pre in enumerate(PREFIX):
        x, y = dodge(b[pre]["win"], i, len(PREFIX), DODGE_OCT_E8), finite(b[pre]["error"])
        on = np.isfinite(y) & (y >= floor)
        p = [points_pt(ax, x[on], y[on])]
        p += [np.array([[0.5 * (bb.x0 + bb.x1) * to_pt, bb.y1 * to_pt]]) for bb in
              (t.get_window_extent(r) for t in marks.get(pre, []))]
        pts[pre] = np.concatenate([q.reshape(-1, 2) for q in p]) if p else np.zeros((0, 2))
    out = []
    for pre in PREFIX:
        if not len(pts[pre]):
            continue
        y = finite(b[pre]["error"])
        all_off = bool(np.isfinite(y).any() and (y[np.isfinite(y)] < floor).all())
        name = lab["prefix"][pre]
        texts = [lab["all_off_scale"].format(name), lab["all_off_scale"].format(name).replace(" (", "\n(")] \
            if all_off else [name]
        others = np.concatenate([pts[q] for q in PREFIX if q != pre])
        t = None
        for text in texts:
            t = place_label(ax, text, pts[pre], others=others if len(others) else None,
                            color=style.readable_on_white(shades[pre]))
            if t is not None:
                break
        if t is None:
            raise style.StyleError(f"{NAME} (b): the label {texts[-1]!r} fits nowhere on the free space")
        t._sublet_prefix = pre
        out.append(t)
    return out


def title_clear(letters: Sequence, titles: Sequence) -> None:
    """C62 fix round: each panel title (at LABEL_PT) ends at least TITLE_GAP_PT left of the next panel's letter, else
    StyleError (finalize() catches an overlap only; a title that ran up to (b)'s letter would read as one line)."""
    if not titles:
        return
    fig = titles[0].get_figure(root=True)
    r = fig.canvas.get_renderer()
    to_pt = style.BP_PER_IN / fig.dpi
    for t, nxt in zip(titles, letters[1:]):
        gap = (nxt.get_window_extent(r).x0 - t.get_window_extent(r).x1) * to_pt
        if gap < TITLE_GAP_PT:
            raise style.StyleError(f"{NAME}: the title {t.get_text()!r} ends {gap:.1f} pt left of the next letter "
                                   f"(at least {TITLE_GAP_PT:g} pt)")


def draw(data: Mapping) -> Any:
    lab = data["labels"]
    fig = style.new_figure(NAME)
    # C62: (b) shares (a)'s y label (the same E), so its reserve holds its tick labels alone (as built, a second "Relative
    # cost error E" between the panels, 0.43 in): the panels gain the difference
    lo_b, hi_b, _ = y_limits(np.concatenate([finite(data["b"][p]["error"]) for p in PREFIX]), float(data["floor"]))
    ticks_b = [t for t in MaxNLocator(nbins=Y_BINS, steps=Y_STEPS).tick_values(lo_b, hi_b) if lo_b <= t <= hi_b]
    ax_a, ax_b = style.panel_row(fig, (1, 1), left=(None, style.ytick_reserve(fig, [style.PLAIN(t) for t in ticks_b])))
    # the three darker of four cividis shades: the lightest of three (#d6c35d) prints at the reference line's grey
    colors = dict(zip(TIERS, style.ramp(len(TIERS) + 1, "cividis")))
    # the two darkest of three grey shades: the lightest prints like the 0.5-pt reference line
    shades = dict(zip(PREFIX, style.ramp(len(PREFIX) + 1, "greys")))
    floor = float(data["floor"])
    draw_a(ax_a, data["a"], lab, colors, floor)
    draw_b(ax_b, data["b"], lab, shades, floor)
    for ax, vals in ((ax_a, [data["a"][t][f] for t in TIERS for f in ("median", "min", "max")]),
                     (ax_b, [data["b"][p]["error"] for p in PREFIX])):
        lo, hi, _ = y_limits(np.concatenate([finite(v) for v in vals]) if vals else [], floor)
        ax.set_ylim(lo, hi)
        ax.yaxis.set_major_locator(MaxNLocator(nbins=Y_BINS, steps=Y_STEPS))
        ax.yaxis.set_major_formatter(style.PLAIN)
        style.reference_line(ax, y=0.0)
        level_axis(ax, data["windows"], pad=X_PAD)
        ax.yaxis.set_major_locator(FixedLocator([t for t in ax.get_yticks() if lo <= t <= hi]))
        top_tick_room(ax)                  # C62
    ax_a.set_ylabel(lab["y"])
    # room right of (a)'s lines for their labels, the same x limits in (b) (the windows at one position in both)
    items = end_items(data["a"], floor)
    right = end_room(ax_a, items, lab)
    if right is not None:
        for ax in (ax_a, ax_b):
            ax.set_xlim(ax.get_xlim()[0], right)
    # the values below the floor, once the limits are final (their labels stay on the page)
    for i, t in enumerate(TIERS):
        off_scale_marks(ax_a, dodge(data["a"][t]["win"], i, len(TIERS), DODGE_OCT_E8), data["a"][t]["median"],
                        floor=floor, color=colors[t])
    marks = {}
    for i, pre in enumerate(PREFIX):
        n0 = len(ax_b.texts)
        off_scale_marks(ax_b, dodge(data["b"][pre]["win"], i, len(PREFIX), DODGE_OCT_E8), data["b"][pre]["error"],
                        floor=floor, color=shades[pre])
        marks[pre] = [t for t in ax_b.texts[n0:] if getattr(t, "_sublet_role", "") == "off_scale_label"]
    center_xlabel([ax_a, ax_b], lab["x"])
    letters = style.panel_letters([ax_a, ax_b])
    # C62 (fix round): the titles at the caption size (style.LABEL_PT; at TICK_PT as first restyled), on the letters'
    # baseline as printed; (a)'s ends TITLE_GAP_PT or more left of (b)'s letter (title_clear)
    titles = [panel_title(ax, letter, lab["titles"][p], fontsize=style.LABEL_PT)
              for ax, letter, p in zip((ax_a, ax_b), letters, ("a", "b")) if lab.get("titles", {}).get(p)]
    align_baselines(letters + titles)
    title_clear(letters, titles)
    end_labels(ax_a, items, lab, colors)
    drop_idle_halos(ax_b, prefix_labels(ax_b, data["b"], lab, shades, floor, marks))
    return fig


def main(argv: Sequence[str] | None = None) -> dict:
    return cli(NAME, build, draw, argv, supplementary=True, doc=__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
