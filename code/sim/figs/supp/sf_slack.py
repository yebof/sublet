"""sf_slack: the lendable slack of the six spot GPU pools, redrawn (design/sim_spec_ms5.md §6, §7.3; M27, M28;
plan §4, part S-F).

Six panels in two rows of three, one per pool in the order of the npz (code/analysis/out/a1_slack_series.npz, written
by code/analysis/a1_lender_spotgpu.py: A10, A100-SXM4-80GB, A800-SXM4-80GB, GPU-series-1, GPU-series-2, H800; the
pools of a1_lender_spotgpu.json, checked equal). The slack is the pool's capacity minus the high-priority jobs'
occupancy, floored at 0, at the analysis's slots after the trace's first week, which the analysis drops; the slot
length is a9b_notice_buffer_24h.json's meta.slot_min (5 min), whose a1 entries name the npz and hold its series
lengths (checked equal). The trace's end is dropped too: the one slot at which every pool's slack rises by at least
TAIL_RISE of its capacity at once, and every slot after it (censored_tail: the last 18 slots, in which every pool's
slack lies near its capacity, an artifact of the trace's end as the first week is of its start; such a slot must lie
in the series' last day). Each panel: the daily band from minimum to maximum (a day holds 1440 / slot_min slots; the
last day the remaining slots) at alpha style.BAND_ALPHA and the daily mean as a style.LINE_PT line, both in the dark
end of the cividis ramp for non-policy categories (DATA_COLOR; plan §5: style.ramp(1), the ramp's midpoint #6C6D72, is
achromatic and lies next to the theory grey and the grey of the level's label, print check), against the time in days
(the day's center), shared per column (the top row without x tick labels, one x label centered under the bottom row);
its own y axis from 0 to the pool's capacity (a1_lender_spotgpu.json capacity_gpus), with at most YTICKS_MAX ticks
besides 0 whose labels end TOP_TICK_GAP_PT below the axes top (clear of the panel letter and title), labeled
"Slack (GPUs)" on the left column of each row (at 9 pt "Lendable GPUs" was as long as a panel is high and ran from
one panel letter to the next; fig2_e1a.clear_letter moves a label that reaches the letter); the P25 level as a
reference line (0.5 pt, #BDBDBD, on a white underlay of UNDERLAY_PT each side so that it reads on the band), drawn
above the band and below the mean line, labeled "P25" in a label column right of the data (the x spine ends at the
data's end; a label inside the dense series would need a halo that hides the data); the pool's name and capacity as
the panel's title on the baseline of its letter (common.panel_title), at the caption size (style.LABEL_PT, as C62 sets
panel titles; at TICK_PT as first restyled). No legend.

The level is P25 of a1_lender_spotgpu.json (leases.p25.window.L): the 25th percentile of the pool's slack over the
whole series (a1: np.percentile(s, 25)); a lease of that many GPUs is available in at least 75% of the slots
(level_reach_share, over the whole series, in the extract). It is not the top of the block the simulator offers
(design §5.2.2, sublet/instance.py lendable()): that applies the same quantile to the slack left after the lender's
notice buffer, (S - B(D_max))^+, and rounds it down to whole layers, so it lies at or below the line (the caption
says so). The line runs from 0 into the label column, REF_RUN_PT past the data's end, so that the light line, not the
data, enters its label; the label sits at the line's end, or, where the mean's last point is level with it (within
common.LEVEL_PT of its center, plan §5's label-column rule: in A800 and GPU-series-1 the daily mean ends at the
level), just above the line (else just below), with the line running on under it. A pool without the level above 0
(A10: zero slack in most slots; a1 records no level <= 0, and the slack is at least 0) says "P25 = 0" on the free
space nearest the panel's top right (M28; its level lies on the x spine), and the caption says when its slack is
zero.

Extract (M27; §6.2): per pool the capacity, the daily minimum, mean and maximum of the slack over the kept slots, the
levels P10, P25 and P50 (null with a note where a1_lender_spotgpu.json has none), the share of all slots whose slack
reaches the drawn level, the share of kept slots with zero slack and the pool's mean slack from the JSON (over all its
slots); for a pool without the level, its first day with slack above 0 and the range of its daily means after that
day; the slot length, the slot, kept-slot and day counts, the dropped end (its first slot, length and each pool's
rise); the sha256 of the three source files (check SL-1 compares them with the versioned files and the daily series
with its own recomputation from the npz within 1e-9).

Run from code/sim: python -m figs.supp.sf_slack [--from-extract [JSON]].
"""
from __future__ import annotations

import hashlib
import math
import sys
from typing import Any, Mapping, Sequence

import numpy as np
from matplotlib.font_manager import FontProperties
from matplotlib.ticker import FixedLocator, MaxNLocator

from figs import style
from figs.common import (LEVEL_PT, TOP_TICK_GAP_PT, MissingKey, align_baselines, cli, need, panel_title, place_label,
                         text_width_in)
from figs.fig2_e1a import clear_letter
from figs.inputs import Inputs
from figs.supp.ms4_lib import center_xlabel, drop_idle_halos

NAME = "sf_slack"
NPZ = "code/analysis/out/a1_slack_series.npz"
JSON = "code/analysis/out/a1_lender_spotgpu.json"
A9B = "code/analysis/out/a9b_notice_buffer_24h.json"     # meta.slot_min, lenders.a1:<pool>.{source, n_slots}
KEYS = style.SUPP_POLICIES_MS5[NAME]          # (): no policy is drawn
MIN_PER_DAY = 1440
TAIL_RISE = 0.5                               # the trace's end: every pool's slack rises by half its capacity at once
NUMBER_WORDS = {2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight", 9: "nine"}
LEVELS = ("p10", "p25", "p50")                # the lease levels of a1_lender_spotgpu.json (leases.<q>.window.L)
LEVEL_DRAWN = "p25"                           # the default lease-size quantile (design §5.2.2), of the raw slack here
COLS = 3                                      # two rows of three panels (§7.3)
ROW_GAP_IN = 0.22                             # from the top row's x axis to the bottom row's top: its letters and
#                                               titles clear of the top row's 3-pt ticks by about 5 pt (not in §7.3;
#                                               0.19 in before the print check, 0.25 in at 9 pt; C62: the 8-pt letters
#                                               are 0.01 in lower, and the panels take the rest of the 0.03 in; fix
#                                               round: with the titles at LABEL_PT, as high as the letters, their ink
#                                               ends 5.9 pt below the top row's tick ends, so 0.22 in stands)
YTICKS_MAX = 3                                # y ticks per panel at most besides 0 (not in §7.3)
LABEL_PAD_PT = 3.0                            # the level's label this far right of its line's end (not in §7.3)
REF_RUN_PT = 5.0                              # the level's line runs this far past the data's end (not in §7.3)
LINE_CLEAR_PT = 1.5                           # a label set above or below its line clears it by this (not in §7.3),
LINE_CLEAR_MAX_PT = 3.0                       # or by up to this where the mean's end is level with it (not in §7.3)
UNDERLAY_PT = 0.3                             # white underlay of the level's line, each side (not in §7.3)
DATA_COLOR = style.ramp(2)[0]                 # the dark end of plan §5's cividis ramp (#00224E)
style.register_supplementary(NAME, "W2", 2.5)
LABELS = {"x": "Time (days)", "y": "Slack (GPUs)", "level": "{name}", "no_level": "{name} = {value}",
          "title": "{pool}, {capacity} GPUs",
          "caption": ("Lendable slack (capacity minus the high-priority jobs' occupancy, at least 0) of the {n_pools} "
                      "GPU pools of Alibaba's cluster-trace-v2026-spot-gpu [duan2026gfs] at {slot_min}-min slots: "
                      "daily minimum to maximum (band) and daily mean (line) over {days:.0f} days from the end of the "
                      "trace's first week, which the analysis drops; each y axis runs from 0 to the pool's capacity "
                      "(title).{tail} Thin light line: {name}, the {q}th percentile of the pool's slack over the "
                      "whole series (the slack reaches it in at least {reach}% of the slots). At its default "
                      "lease-size quantile ({name}) the simulator takes this quantile of the slack left after the "
                      "lender's notice buffer and rounds it down to whole layers, so the top of the block a spot "
                      "lender offers lies at or below this line.{no_level}"),
          "caption_tail": (" The trace's last {n_tail} slots ({tail_min} min), in which every pool's slack jumps at "
                           "once to at least {share}% of its capacity, are left out."),
          "caption_no_level": " ({letter}) {pool}: {level}; its slack is zero in {share} of the slots{run}.",
          "caption_no_level_run": ", in every slot until day {d0}",
          "caption_no_level_after": ", and its daily mean is {lo}–{hi} GPUs from day {d1} on"}


def sha256_of(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def daily(s: np.ndarray, per_day: int) -> dict[str, list[float]]:
    """The daily minimum, mean and maximum of the slot series s: day d holds slots [d * per_day, (d + 1) * per_day),
    the last day the remaining slots."""
    s = np.asarray(s, dtype=float)
    n_d = -(-s.size // per_day)
    pad = np.full(n_d * per_day, np.nan)
    pad[:s.size] = s
    blocks = pad.reshape(n_d, per_day)
    return {"min": np.nanmin(blocks, axis=1).tolist(), "mean": np.nanmean(blocks, axis=1).tolist(),
            "max": np.nanmax(blocks, axis=1).tolist()}


def day_centers(n_slots: int, per_day: int, slot_min: float) -> np.ndarray:
    """The time in days of each day's center (the last day's center over its remaining slots)."""
    n_d = -(-int(n_slots) // per_day)
    start = np.arange(n_d) * per_day
    width = np.minimum(per_day, int(n_slots) - start)
    return (start + 0.5 * width) * float(slot_min) / MIN_PER_DAY


def censored_tail(series: Mapping[str, np.ndarray], capacity: Mapping[str, float], per_day: int) -> dict:
    """The trace's end that the figure leaves out: the one slot t at which every pool's slack rises by at least
    TAIL_RISE of its capacity at once, and the slots after it ({'start_slot': None, 'n_slots': 0} without such a
    slot). More than one such slot, or one before the series' last day, is an error: it would be data, not the end."""
    pools = list(series)
    m = np.vstack([np.asarray(series[p], dtype=float) / float(capacity[p]) for p in pools])
    n = m.shape[1]
    hits = (np.flatnonzero((np.diff(m, axis=1) >= TAIL_RISE).all(axis=0)) + 1).tolist()
    if not hits:
        return {"start_slot": None, "n_slots": 0, "rule": f"no slot at which every pool rises by {TAIL_RISE:g} of its "
                                                          "capacity at once"}
    if len(hits) > 1 or n - hits[0] > per_day:
        raise style.StyleError(f"{NAME}: every pool's slack rises by {TAIL_RISE:g} of its capacity at once at the "
                               f"slots {hits} of {n}: expected one such slot, in the series' last day")
    t = int(hits[0])
    return {"start_slot": t, "n_slots": n - t,
            "rule": f"the one slot at which every pool's slack rises by at least {TAIL_RISE:g} of its capacity at "
                    "once, and the slots after it",
            "rise_share": {p: float(m[i, t] - m[i, t - 1]) for i, p in enumerate(pools)},
            "min_share_after": {p: float(m[i, t:].min()) for i, p in enumerate(pools)}}


def slot_minutes(a9b: Mapping, lengths: Mapping[str, int]) -> int:
    """The slot length of the slack series: a9b_notice_buffer_24h.json's meta.slot_min, whose entry of every a1 pool
    names the npz and holds its series length."""
    slot = need(need(a9b, "meta", what=A9B), "slot_min", what=f"{A9B} meta")
    lenders = need(a9b, "lenders", what=A9B)
    for pool, n in lengths.items():
        ent = need(lenders, f"a1:{pool}", what=f"{A9B} lenders")
        if "a1_slack_series.npz" not in str(ent.get("source")) or ent.get("n_slots") != n:
            raise MissingKey(f"{A9B} lenders.a1:{pool} (source {ent.get('source')!r}, n_slots {ent.get('n_slots')!r}) "
                             f"does not describe {NPZ}'s series of {n} slots")
    if not isinstance(slot, int) or slot <= 0 or MIN_PER_DAY % slot:
        raise MissingKey(f"{A9B} meta.slot_min is {slot!r}, not a positive divisor of a day in minutes")
    return slot


def level_quantile() -> int:
    """The percentile of the drawn level, from its name (p25: 25)."""
    return int(LEVEL_DRAWN[1:])


def zero_run(day_max: Sequence[float], day_mean: Sequence[float]) -> dict:
    """For a pool without the level: its first day with slack above 0 (None if none) and the range of its daily means
    on the days after that day (None if none)."""
    above = np.flatnonzero(np.asarray(day_max, dtype=float) > 0.0)
    d0 = int(above[0]) if above.size else None
    after = [] if d0 is None else list(day_mean)[d0 + 1:]
    return {"first_day_above_0": d0, "mean_after": [float(min(after)), float(max(after))] if after else None}


def build(inp: Inputs) -> dict:
    meta = inp.json(JSON)
    a9b = inp.json(A9B)
    npz_path = inp.path(NPZ)
    with np.load(npz_path) as z:
        series = {k: np.asarray(z[k], dtype=float) for k in z.files}
    pools = list(series)
    json_pools = [k for k in meta if not k.startswith("_")]
    if sorted(pools) != sorted(json_pools):
        raise MissingKey(f"{NPZ} holds the pools {pools}, {JSON} {json_pools}: not the same pools")
    lengths = {k: int(v.size) for k, v in series.items()}
    if len(set(lengths.values())) != 1:
        raise style.StyleError(f"{NPZ}: the pools' series differ in length: {lengths}")
    if any(float(v.min()) < 0.0 for v in series.values()):
        raise style.StyleError(f"{NPZ}: negative slack (a1 floors it at 0)")
    n_slots = lengths[pools[0]]
    slot_min = slot_minutes(a9b, lengths)
    per_day = MIN_PER_DAY // slot_min
    caps = {p: float(need(need(meta, p, what=JSON), "capacity_gpus", what=f"{JSON} {p}")) for p in pools}
    tail = censored_tail(series, caps, per_day)
    n_kept = n_slots - tail["n_slots"]
    out = {}
    no_level_value = {}
    for pool in pools:
        s = series[pool][:n_kept]
        ent = need(meta, pool, what=JSON)
        leases = ent.get("leases") if isinstance(ent.get("leases"), Mapping) else {}
        levels = {}
        for q in LEVELS:
            lv = ((leases.get(q) or {}).get("window") or {}).get("L")
            levels[q] = None if lv is None else float(lv)
            if lv is None:
                levels[f"{q}_note"] = f"{JSON} {pool}.leases has no {q} (no lease level above 0)"
        drawn = levels[LEVEL_DRAWN]
        out[pool] = {"capacity_gpus": int(need(ent, "capacity_gpus", what=f"{JSON} {pool}")),
                     "slack_mean_gpus": need(ent, "slack_mean_gpus", what=f"{JSON} {pool}"),
                     "zero_share": float(np.mean(s == 0.0)), "levels": levels,
                     # the share of all slots (the dropped end included, as a1's quantile) at or above the level
                     "level_reach_share": None if drawn is None else float(np.mean(series[pool] >= drawn)),
                     **daily(s, per_day)}
        if drawn is None:
            # a1 records no level <= 0; the slack is at least 0, so the quantile over the whole series is 0
            v = float(np.percentile(series[pool], level_quantile()))
            if v != 0.0:
                raise style.StyleError(f"{NAME}: {JSON} {pool} has no {LEVEL_DRAWN}, but the npz's is {v:g}")
            no_level_value[pool] = v
            out[pool]["zero_run"] = zero_run(out[pool]["max"], out[pool]["mean"])
    n_days = len(out[pools[0]]["mean"])
    no_level = [p for p in pools if out[p]["levels"][LEVEL_DRAWN] is None]
    data = {"pools": pools, "series": out, "slot_min": slot_min, "slots_per_day": per_day,
            "n_slots": n_slots, "n_kept": n_kept, "tail": tail, "n_days": n_days,
            "last_day_slots": n_kept - (n_days - 1) * per_day, "days": n_kept * slot_min / MIN_PER_DAY,
            "level_drawn": LEVEL_DRAWN, "level_quantile": level_quantile(), "no_level": no_level,
            "source_sha256": {NPZ: sha256_of(npz_path), JSON: sha256_of(inp.path(JSON)), A9B: sha256_of(inp.path(A9B))},
            "sources": list(inp.sources)}
    name = LEVEL_DRAWN.upper()
    lab = {**LABELS, "level": LABELS["level"].format(name=name)}
    if no_level:
        (value,) = set(no_level_value.values())
        lab["no_level"] = LABELS["no_level"].format(name=name, value=style.PLAIN(value))
    data["labels"] = lab
    data["labels"]["caption"] = caption(data)
    return data


def _pct_down(share: float) -> int:
    """A share as a whole percent rounded down (a stated lower bound holds)."""
    return int(math.floor(100.0 * share + 1e-9))


def caption(data: Mapping) -> str:
    """The caption draft (§7.3: the trace, the 5-min slots, the days, the first week and the trace's end dropped, the
    definition of slack; the level and what it is not; the pools without it), every number read from the extract."""
    series, no_level, tail, lab = data["series"], data["no_level"], data["tail"], data["labels"]
    nl = ""
    for p in no_level:
        zr = series[p]["zero_run"]
        run = ""
        if zr["first_day_above_0"] is not None and zr["first_day_above_0"] > 0:
            run = LABELS["caption_no_level_run"].format(d0=zr["first_day_above_0"])
            if zr["mean_after"] is not None:
                lo, hi = zr["mean_after"]
                run += LABELS["caption_no_level_after"].format(lo=math.floor(lo), hi=math.ceil(hi),
                                                               d1=zr["first_day_above_0"] + 1)
        nl += LABELS["caption_no_level"].format(letter="abcdefghijklmnopqrstuvwxyz"[data["pools"].index(p)], pool=p,
                                                level=lab["no_level"], share=f"{100.0 * series[p]['zero_share']:.1f}%",
                                                run=run)
    tl = "" if not tail["n_slots"] else LABELS["caption_tail"].format(
        n_tail=tail["n_slots"], tail_min=tail["n_slots"] * data["slot_min"],
        share=_pct_down(min(tail["min_share_after"].values())))
    reach = [series[p]["level_reach_share"] for p in data["pools"] if series[p]["level_reach_share"] is not None]
    n = len(data["pools"])
    return LABELS["caption"].format(n_pools=NUMBER_WORDS.get(n, str(n)), slot_min=data["slot_min"], days=data["days"],
                                    tail=tl, name=lab["level"], q=data["level_quantile"],
                                    reach=_pct_down(min(reach)) if reach else "–", no_level=nl)


def tick_rise_pt(fig) -> float:
    """How far (pt) a y tick label (style.TICK_PT) reaches above its tick (a probe set as matplotlib sets y tick
    labels)."""
    r = fig.canvas.get_renderer()
    t = fig.text(0.0, 0.5, "0", fontproperties=FontProperties(size=style.TICK_PT), va="center_baseline")
    try:
        return (t.get_window_extent(r).y1 - 0.5 * fig.bbox.height) * style.BP_PER_IN / fig.dpi
    finally:
        t.remove()


def y_ticks(capacity: float, h_pt: float, rise_pt: float) -> list[float]:
    """Round y ticks from 0 within [0, capacity], at most YTICKS_MAX besides 0 (the capacity is in the title), each
    with its label ending TOP_TICK_GAP_PT below the top of an axes h_pt high (clear of the panel letter and title)."""
    cap = float(capacity)
    top = cap * (h_pt - TOP_TICK_GAP_PT - rise_pt) / h_pt
    for nbins in (YTICKS_MAX + 1, YTICKS_MAX):
        t = MaxNLocator(nbins, steps=[1, 2, 2.5, 5, 10], integer=True).tick_values(0.0, cap)
        t = [float(v) for v in t if 0.0 <= v <= top + 1e-9]
        if len(t) - 1 <= YTICKS_MAX:
            return t
    return t[:YTICKS_MAX + 1]


def x_ticks(days: float) -> list[float]:
    t = MaxNLocator(4, steps=[1, 2, 2.5, 5, 10], integer=True).tick_values(0.0, float(days))
    return [float(v) for v in t if 0.0 <= v <= float(days) + 1e-9]


def column_reserves(fig, ticks: Mapping[str, Sequence[float]], rows: Sequence[Sequence[str]]) -> list[float]:
    """The left reserve of each column, the same in both rows so that the columns align: the widest y tick label of
    the column's pools, and the y label in the first column (style.ytick_reserve)."""
    out = []
    for j in range(COLS):
        labels = [style.PLAIN(v) for r in rows if j < len(r) for v in ticks[r[j]]]
        out.append(style.ytick_reserve(fig, labels, ylabel=(j == 0)))
    return out


def label_column_in(fig, lab: Mapping) -> float:
    """The width (inches) of the label column right of the data: the level's line running REF_RUN_PT past the data,
    then its label (style.TICK_PT) with LABEL_PAD_PT on each side."""
    return text_width_in(fig, lab["level"]) + (REF_RUN_PT + 2.0 * LABEL_PAD_PT) / style.BP_PER_IN


def x_right(days: float, col_in: float, w_in: float) -> float:
    """The right x limit of a panel w_in inches wide whose data end at `days`, with a label column of col_in
    inches (at most half the panel)."""
    return float(days) / (1.0 - min(col_in / w_in, 0.5))


def level_line(ax, level: float, x_end: float, mean_end: float, days: float, lab: Mapping):
    """The level's reference line on its white underlay and its label (see the module docstring): the line from 0 to
    REF_RUN_PT past the data's end, the label LABEL_PAD_PT right of the line's end; where the mean's last point
    (x_end, mean_end) is level with that label (within LEVEL_PT of its center), the label sits LINE_CLEAR_PT above the
    line, else below it, inside the axes (up to LINE_CLEAR_MAX_PT off the line where the mean ends between the line
    and the label's center), and the line runs on under the label to its right end; where no placement clears the
    mean's end, the one farthest from it. Returns (line, label)."""
    fig = ax.figure
    r = fig.canvas.get_renderer()
    to_pt = style.BP_PER_IN / fig.dpi
    x1 = ax.get_xlim()[1]
    x_run = days + REF_RUN_PT / style.BP_PER_IN / style.axes_rect_in(ax)[2] * x1
    end_pt = ax.transData.transform((x_end, mean_end))[1] * to_pt
    bb_ax = ax.get_window_extent(r)
    lo_pt, hi_pt = bb_ax.y0 * to_pt, bb_ax.y1 * to_pt
    kw = dict(xy=(x_run, float(level)), textcoords="offset points", ha="left", fontsize=style.TICK_PT,
              color=style.THEORY_LABEL_GREY, zorder=style.Z_THEORY_LABEL)
    def probe(off, va):
        t = ax.annotate(lab["level"], xytext=off, va=va, **kw)
        bb = t.get_window_extent(r)
        t.remove()
        center = 0.5 * (bb.y0 + bb.y1) * to_pt
        return bb.y0 * to_pt >= lo_pt - 0.01 and bb.y1 * to_pt <= hi_pt + 0.01, center - end_pt

    places = (("end", 0.0, "center"), ("above", 1.0, "baseline"), ("below", -1.0, "top"))
    tried = []
    for mode, side, va in places:
        off = (LABEL_PAD_PT, side * LINE_CLEAR_PT)
        fits, d = probe(off, va)
        if side and abs(d) <= LEVEL_PT and side * d > 0:
            # the mean ends between the line and the label's center: move the label off the line, up to
            # LINE_CLEAR_MAX_PT, until its center clears that end
            dy = LINE_CLEAR_PT + LEVEL_PT + 0.25 - abs(d)
            if dy <= LINE_CLEAR_MAX_PT:
                off = (LABEL_PAD_PT, side * dy)
                fits, d = probe(off, va)
        tried.append((mode, off, va, fits, abs(d)))
        if fits and abs(d) > LEVEL_PT:
            break
    else:
        fit = [c for c in tried if c[3]] or tried
        tried.append(max(fit, key=lambda c: c[4]))
    mode, off, va, _, _ = tried[-1]
    t = ax.annotate(lab["level"], xytext=off, va=va, **kw)
    t._sublet_role = "reference_label"
    t._sublet_place = mode
    if mode == "end":
        x_line = x_run
    else:
        x_line = ax.transData.inverted().transform((t.get_window_extent(r).x1, 0.0))[0]
    under = ax.axhline(float(level), xmax=x_line / x1, color="white", linewidth=style.REFERENCE_PT + 2 * UNDERLAY_PT,
                       zorder=style.Z_DATA - 0.07, solid_capstyle="butt", label="_nolegend_")
    under._sublet_role = "reference_underlay"
    ref = style.reference_line(ax, y=float(level), xmax=x_line / x1, zorder=style.Z_DATA - 0.05,
                               solid_capstyle="butt")
    return ref, t


def draw_pool(ax, data: Mapping, pool: str, x: np.ndarray, lab: Mapping, x1: float,
              yticks: Sequence[float]) -> None:
    """One pool's band and mean line; the x axis from 0 to x1, the days and a label column right of the data
    (x_right), where the level's line ends and its label sits (level_line; as the theory labels of plan §5's
    amendment of 2026-10-20: over the dense series a label inside the data would need a halo that hides the data); a
    pool without the level says so on the free space nearest the panel's top right (common.place_label)."""
    s = data["series"][pool]
    lo, mean, hi = (np.asarray(s[f], dtype=float) for f in ("min", "mean", "max"))
    cap = float(s["capacity_gpus"])
    days = float(data["days"])
    band = ax.fill_between(x, lo, hi, color=DATA_COLOR, alpha=style.BAND_ALPHA, linewidth=0,
                           zorder=style.Z_DATA - 0.1)
    band._sublet_role = "slack_band"
    (line,) = ax.plot(x, mean, color=DATA_COLOR, linewidth=style.LINE_PT, zorder=style.Z_DATA,
                      solid_joinstyle="round")
    line._sublet_role = "slack_mean"
    ax.set_xlim(0.0, x1)
    ax.spines["bottom"].set_bounds(0.0, days)
    ax.set_ylim(0.0, cap)
    ax.yaxis.set_major_locator(FixedLocator(list(yticks)))
    ax.yaxis.set_major_formatter(style.PLAIN)
    ax.xaxis.set_major_locator(FixedLocator(x_ticks(days)))
    ax.xaxis.set_major_formatter(style.PLAIN)
    level = s["levels"].get(data["level_drawn"])
    if level is not None:
        ref, _ = level_line(ax, float(level), float(x[-1]), float(mean[-1]), days, lab)
        ref._sublet_level = data["level_drawn"]
    else:
        to_pt = style.BP_PER_IN / ax.figure.dpi
        corner = np.array([ax.transData.transform((days, cap))]) * to_pt
        t = place_label(ax, lab["no_level"], corner, color=style.THEORY_LABEL_GREY)
        if t is None:
            raise style.StyleError(f"{NAME}: no room in the panel of {pool} for {lab['no_level']!r}")
        drop_idle_halos(ax, [t])
        t._sublet_role = "reference_label"


def draw(data: Mapping) -> Any:
    lab = data["labels"]
    pools = list(data["pools"])
    rows = [pools[i:i + COLS] for i in range(0, len(pools), COLS)]
    if len(rows) != 2 or any(len(r) != COLS for r in rows):
        raise style.StyleError(f"{NAME}: two rows of {COLS} pools expected, got {pools}")
    fig = style.new_figure(NAME)
    W, H = fig.get_size_inches()
    h = (H - style.MARGIN_BOTTOM - style.MARGIN_TOP - ROW_GAP_IN) / 2.0
    rise = tick_rise_pt(fig)
    ticks = {p: y_ticks(data["series"][p]["capacity_gpus"], h * style.BP_PER_IN, rise) for p in pools}
    left = column_reserves(fig, ticks, rows)
    top_row = style.panel_row(fig, (1,) * COLS, left=left, bottom=H - style.MARGIN_TOP - h, top=style.MARGIN_TOP)
    bottom_row = style.panel_row(fig, (1,) * COLS, left=left, bottom=style.MARGIN_BOTTOM,
                                 top=style.MARGIN_TOP + h + ROW_GAP_IN)
    x = day_centers(data["n_kept"], data["slots_per_day"], data["slot_min"])
    axes = top_row + bottom_row
    x1 = x_right(data["days"], label_column_in(fig, lab), style.axes_rect_in(axes[0])[2])   # one x range for all
    for ax, pool in zip(axes, pools):
        draw_pool(ax, data, pool, x, lab, x1, ticks[pool])
    for ax in top_row:
        ax.tick_params(axis="x", labelbottom=False)
    for r in (top_row, bottom_row):
        r[0].set_ylabel(lab["y"])
    center_xlabel(bottom_row, lab["x"])
    letters = style.panel_letters(axes)
    # C62 (fix round): the titles at the caption size (style.LABEL_PT; at TICK_PT as first restyled), on the letters'
    # baseline as printed (plain text, as the letters)
    titles = [panel_title(ax, letter, lab["title"].format(pool=pool, capacity=data["series"][pool]["capacity_gpus"]),
                          fontsize=style.LABEL_PT) for ax, letter, pool in zip(axes, letters, pools)]
    align_baselines(letters + titles)
    for r, letter in ((top_row, letters[0]), (bottom_row, letters[COLS])):
        clear_letter(r[0], letter)
    return fig


def main(argv: Sequence[str] | None = None) -> dict:
    return cli(NAME, build, draw, argv, supplementary=True, doc=__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
