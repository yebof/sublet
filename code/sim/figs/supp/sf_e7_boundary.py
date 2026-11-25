"""sf_e7_boundary: part `second`'s boundary conditions per policy, with the tables e7v2_boundary.tex, e7v2_lag.tex,
e7v2_e5.tex and e7v2_gap.tex (design/sublet_v2.md §11, W4, W9, W10; §4.4(b); prereg §5, "reported in full": L-vr,
L-rf, L-ad, the P99.9 buffer, the E5 menus, lagged demand, the gap-day ALG/LB).

Figure (W2 x 2.5 in; C41's 2.4 in, C59).
One row per policy of part second's lender grid (the twelve tags of §4.4(b), ROW_TAGS: Sublet
and the critical-ratio inner policy, the greedy family, the RetroRenting family with the legacy Sublet-MS4, then CoCaR
and SpotHedge), named once on the y axis of (a); one panel per condition, the panels sharing the rows: (a) L-vr (the
trace lender with buffer violations as reclaims without notice), (b) L-rf (the trace lender refusing purchases on
unavailable layers), (c) L-ad (the adaptive lender, which announces every lease at the end of its guaranteed period),
(d) the P99.9 buffer under the trace lender (L-b999), (e) lagged demand under the trace lender: in the rows of Sublet,
critical-ratio renting, greedy renting and RetroRenting-style, the same policy on slot t - 1's demand (Sublet, lagged;
Critical-ratio renting, lagged; Greedy renting, lagged; and RetroRenting's lagged build, part main's tag BL5, which
§4.4(b) puts beside them), each in its own registry style. A row's marker is the median cost over all-fallback over
part second's weeks (301-304 on the confirmation; read from the data) with its 95% week-bootstrap interval as a
horizontal bar (ms5b_common.bootstrap_median_ci, seed 20261031, 10,000 resamples; W9; C59: over 4 weeks the interval
is the range of the weeks' values, and the captions call it so), policy seed 0; the grey tick is
the row's policy's median under the trace lender on the same weeks (part main), so that each panel shows the change
from L-tr; the grey line marks all-fallback (cost 1).

As built (choices that §11 leaves open):
* Legends do not fit (sixteen keys, the longest label 3.1 in at 7 pt), so the rows carry the names (W4: direct
  labels); a name wider than ROW_WRAP_IN is split once at a word break (ms5b_e7_lib.wrap: Sublet-MS4's). The rows are
  placed by the measured heights of their names (row_layout: one gap between neighboring names, at least
  ROW_GAP_MIN_PT), not at one pitch (Sublet-MS4's name takes two lines); the y unit is the point. (As built at 9 pt,
  twelve names filled the 1.85-in axes nearly to the point.)
* C62: every other row (Sublet's first) lies on a light grey band (ROW_BAND_GREY, row_bands) that runs from the left
  edge of the names through every panel, so that a row's marker in (d) or (e) is read against its name; a band's edges
  are the midpoints between neighboring rows' centers (the axes' top and bottom at the ends), and the panels' axes
  have no face of their own. The panel titles are set at the caption size (ms5b_e7_lib.caption_title). (d)'s title
  and the caption draft write the percentile in upper case, "P99.9", as every other figure and the caption do (C62
  fix round; its tables and sf_e7_decomp's since the integration, MODE_TEX).
* Panel (e)'s markers are the lagged variants' keys (their labels are the row's name with ", lagged"; the panel title
  says so; the caption draft says that its markers are the lagged variants' styles), and its grey ticks are the
  unlagged policies' L-tr medians.
* x ranges (x_ranges; print check 2026-11-03): the panels share the range of their data, their grey ticks and 1,
  except a panel whose span exceeds WIDE_FACTOR times the median panel's (L-ad), which has its own (the caption
  says so); x ticks the first step of X_STEPS with X_MIN_TICKS to X_MAX_TICKS ticks; one x label centered under the
  row; the panel titles are the conditions' short names (the caption draft defines them).
* L-vr (print check 2026-11-03): L-vr differs from L-tr only where a buffer violation occurs, so the build counts
  the violations of its runs from their run files (violations; second/runs/, each listed with its sha256, W10) and
  checks whether its costs equal L-tr's; where none occurred, (a)'s title says "no violation" and the caption and
  e7v2_boundary.tex say so. L-ad, the eager lender L-eg (part main) and the i.i.d. lender at p = 1 each announce
  every revocable lease when its guaranteed period ends (sublet/lender.py); where their costs agree for every row
  and week (same_modes), the captions say so.
* labels.caption is a caption draft with every count and week read from the inputs.

Tables (after hook, figs.common.write_table; from the extract's `tables`, so --from-extract rewrites them), each with
its scope in the extract for the claims report (W11):
  e7v2_boundary.tex  per policy of ROW_TAGS: r0 under L-tr (part main, the reference), L-vr, L-rf, L-ad and the
                     P99.9 buffer on each week of part second, with the median and its 95% interval;
  e7v2_lag.tex       per lagged pair (Sublet, critical-ratio renting, greedy renting under part second's lag tags;
                     RetroRenting-style against its lagged build, both from part main): r0 unlagged and lagged under
                     the trace lender and their difference on each week, with medians and intervals;
  e7v2_e5.tex        the E5 menus (short: spot-like contracts; long: long-notice contracts; each with the protected
                     contract) under the trace lender and all1 (the correlated lender with every site in one group),
                     E5 config seeds of part second (a spanning head "E5 config seed" over them): r0 of the six E5
                     tags per config seed with the median and interval;
  e7v2_gap.tex       ALG/LB on the gap days (one day of each week on the e7r menu with s5_tau5_H5, the merged LP
                     bound of second/gap_lp; an upper bound on the gap) per tag and day, with all-fallback's
                     (bl0a_usd / gap_lp of the day's gap rows) and the LP bound in USD; the caption gives the
                     contracts as (tau, H) pairs read from ms4_common.H5_OVERRIDES.
Every table is a longtable (ms5b_e7_lib.longtable: one-column mode, a group kept on one page, name_cells).

Inputs (W10): the summaries of parts second and main (code/sim/out/sublet_v2/<part>/summary.json) and the L-vr run
files of part second's week jobs of ROW_TAGS (code/sim/out/sublet_v2/second/runs/, unversioned; listed with their
sha256 in meta.runs_files). Run from code/sim: python -m figs.supp.sf_e7_boundary [--from-extract [JSON]].
"""
from __future__ import annotations

import math
import re
import sys
from typing import Any, Mapping, Sequence

import matplotlib as mpl
from matplotlib.ticker import FixedLocator

from figs import style
from figs.common import MissingKey, align_baselines, cli, need, text_width_in, write_table
from figs.inputs import Inputs
from figs.supp import ms5b_e7_lib as L
from figs.supp.ms4_lib import center_xlabel
from sublet.experiments import ms4_common as m4
from sublet.experiments import ms5b_common as m5

NAME = "sf_e7_boundary"
KEYS = style.SUPP_POLICIES_MS5B[NAME]
TABLES = ("e7v2_boundary.tex", "e7v2_lag.tex", "e7v2_e5.tex", "e7v2_gap.tex")
style.register_supplementary(NAME, "W2", 2.5)        # C59: was 2.4 in, for the guard's name on three lines (row_name)
# the rows, top to bottom: no two names with a math part ($...$, 11.5 pt high) next to each other
ROW_TAGS = ("Sublet", "A9", "BL1", "BL1-BO", "BL1N", "BL1-GP", "BL5-cur", "BL5-tau60", "BL5N", "Sublet-MS4", "BL4",
            "BL3-0")
# the lagged variant of a row's policy: (tag, part whose L-tr runs hold it)
LAG = {"Sublet": ("Sublet-lag", "second"), "A9": ("A9-lag", "second"), "BL1": ("BL1-lag", "second"),
       "BL5-cur": ("BL5", "main")}
PANELS = (("a", "L-vr", "L-vr"), ("b", "L-rf", "L-rf"), ("c", "L-ad", "L-ad"), ("d", "L-b999", "P99.9 buffer"),
          ("e", "lag", "Lagged demand"))
if sorted({L.KEY_OF_TAG[t] for t in ROW_TAGS} | {L.KEY_OF_TAG[t] for t, _ in LAG.values()}) != sorted(KEYS):
    raise style.StyleError(f"{NAME}: the rows and lagged variants must be SUPP_POLICIES_MS5B[{NAME!r}]")
E5_TAGS = ("Sublet", "A9", "BL3-0", "BL5", "BL5-cur", "Sublet-MS4")
E5_MENUS = ("short", "long")
E5_LEVELS = ("trace", "all1")
PANEL_GAP_IN = 0.2              # a panel's reserve left of its axes (style.LEFT_SHARED 0.14 in: "2" and "0.5" of
#                                 neighboring panels read as one number)
ROW_WRAP_IN = 1.6               # a row name wider than this is split once at a word break
ROW_NAME_MAX_IN = 2.0           # C59 (RC19(3)): a name that the split leaves wider than this (the MS4 allowance's label
ROW_LINE_IN = 1.45              # in words, 2.16 in on two lines at 9 pt; as built 1.78 in) is broken at its spaces into
#                                 lines of at most ROW_LINE_IN (three lines, 1.42 in), so that the panels keep their
#                                 width; at 7 pt (C62) its two lines are 1.68 in wide and the rule does not apply
ROW_BAND_GREY = "#F2F2F2"       # C62: the band behind every other row (row_bands; lighter than style.SHADE_GREY)
ROW_BAND_INSET_IN = 0.02        # C62: the bands start this far right of the page's left edge (the names 0.04 in)
X_STEPS = (0.1, 0.2, 0.25, 0.5, 1.0)
X_MIN_TICKS, X_MAX_TICKS = 3, 4
X_PAD = 0.05                    # the x range beyond the data, as a share of its span
WIDE_FACTOR = 1.5               # a panel whose data span exceeds this times the median panel's gets its own x range
VIOLATION_MODE = "L-vr"         # the condition that turns buffer violations into reclaims without notice
SAME_MODES = (("L-ad", "second"), ("L-eg", "main"), (m5.iid_mode(1.0), "second"))   # announce every revocable lease
#                                 when its guaranteed period ends (sublet/lender.py: adaptive, eager, iid_step p = 1)
TICK_HALF = 3.2                 # the grey L-tr tick's half height (pt; the rows' y unit is the point)
TICK_PT = 0.8
ROW_GAP_MIN_PT = 0.6            # the least gap between two row names' boxes (finalize's overlap tolerance is 0.5 pt)
LABELS = {"x": "Cost / all-fallback",
          "caption": ("Boundary conditions of part second on weeks {weeks} ({n_weeks} week{s}, policy seed 0), one "
                      "row per policy: the median cost over all-fallback with its range over the weeks (the weeks "
                      "being rotations of one series) under "
                      "(a) L-vr, the trace lender with buffer violations turned into reclaims without notice{vr}; (b) "
                      "L-rf, the trace lender refusing purchases on unavailable layers; (c) L-ad, the adaptive "
                      "lender, which announces every lease at the end of its guaranteed period{ad}; (d) the trace "
                      "lender with the P99.9 lease buffer; (e) the trace lender with demand lagged by one slot, for "
                      "the policy of its row on slot $t-1$'s demand (RetroRenting-style: its lagged build), each "
                      "marker in the lagged variant's style. Grey ticks: the row's policy under the trace lender on "
                      "the same weeks (part main); grey line: all-fallback. {wide}Per-week values in "
                      "Tables~\\ref{{tab:e7v2-boundary}} and \\ref{{tab:e7v2-lag}}; the E5 menus and the gap days in "
                      "Tables~\\ref{{tab:e7v2-e5}} and \\ref{{tab:e7v2-gap}}."),
          "vr": (": no buffer violation occurred in its {n} runs{eq}"),
          "vr_eq": ", so its cost equals the trace lender's for every policy on every week",
          "ad": (" (on these weeks its cost equals that of the eager lender L-eg and of the i.i.d. lender at $p=1$ "
                 "for every policy: each announces every revocable lease when its guaranteed period ends)"),
          "wide": "Panel ({letters}) has its own $x$ range. ",
          "title_vr": "{title}: no violation"}


def _series(table: Mapping, tag: str, mode: str, cells: Sequence[str]) -> dict:
    vals = [L.val(table, tag, mode, c) for c in cells]
    return {"tag": tag, "mode": mode, "cells": list(cells), "values": vals, **L.med_ci(vals)}


def build(inp: Inputs) -> dict:
    second, main = inp.json(L.SECOND), inp.json(L.MAIN)
    st, mt = need(second, "table", what=L.SECOND), need(main, "table", what=L.MAIN)
    L.need_tags(st, ROW_TAGS + tuple(t for t, p in LAG.values() if p == "second") + E5_TAGS, L.SECOND)
    L.need_tags(mt, ROW_TAGS + tuple(t for t, p in LAG.values() if p == "main"), L.MAIN)
    weeks = L.weeks_of(st, ROW_TAGS, [m for _, m, _ in PANELS if m != "lag"])
    if not weeks:
        raise MissingKey(f"{L.SECOND}: no week run under {[m for _, m, _ in PANELS]}")
    rows = []
    for tag in ROW_TAGS:
        r = {"tag": tag, "key": L.KEY_OF_TAG[tag], "label": L.label(tag), "ref": _series(mt, tag, L.TRACE, weeks),
             "modes": {m: _series(st, tag, m, weeks) for _, m, _ in PANELS if m != "lag"}}
        if tag in LAG:
            lt, part = LAG[tag]
            r["lag"] = {**_series(st if part == "second" else mt, lt, L.TRACE, weeks), "key": L.KEY_OF_TAG[lt],
                        "part": part}
        rows.append(r)
    runs_files: list = []
    vr = violations(inp, second, weeks, runs_files)
    vr["equals_trace"] = all(r["modes"][VIOLATION_MODE]["values"] == r["ref"]["values"] for r in rows)
    same = same_modes(st, mt, weeks)
    panels = [{"letter": a, "mode": m, "title": LABELS["title_vr"].format(title=t)
               if m == VIOLATION_MODE and vr["runs"] and vr["count"] == 0 else t} for a, m, t in PANELS]
    out = {"keys": list(KEYS), "weeks": weeks, "rows": rows, "panels": panels, "bootstrap": dict(L.BOOT),
           "violations": vr, "same_modes": same,
           "tables": {"e7v2_boundary": boundary_table(rows, weeks, vr, same), "e7v2_lag": lag_table(rows, weeks),
                      "e7v2_e5": e5_table(second), "e7v2_gap": gap_table(second)},
           "labels": dict(LABELS),
           "meta": {**L.meta_of({"second": second, "main": main}), "runs_files": runs_files}}
    out["x_ranges"] = x_ranges(out)
    out["labels"]["caption"] = caption(out)
    out["meta"]["sources"] = list(inp.sources)
    return out


def caption(d: Mapping) -> str:
    nw, vr, same = len(d["weeks"]), d["violations"], d.get("same_modes") or {}
    vrt = (LABELS["vr"].format(n=vr["runs"], eq=LABELS["vr_eq"] if vr["equals_trace"] else "")
           if vr["runs"] and vr["count"] == 0 else "")
    wide = [p["letter"] for p, r in zip(d["panels"], d["x_ranges"]) if r["own"]]
    return LABELS["caption"].format(weeks=L.week_span(d["weeks"]), n_weeks=nw, s="s" if nw != 1 else "",
                                    B=f"{L.BOOT['B']:,}", seed=L.BOOT["seed"], vr=vrt,
                                    ad=LABELS["ad"] if same.get("equal") else "",
                                    wide=LABELS["wide"].format(letters=", ".join(wide)) if wide else "")


def violations(inp: Inputs, second: Mapping, weeks: Sequence[str], runs_files: list) -> dict:
    """The buffer violations of the VIOLATION_MODE runs of ROW_TAGS on `weeks` (policy seed 0), from their run files
    of part second (second/runs/, unversioned; each listed in runs_files with its sha256, W10): {mode, runs, count}."""
    rows = [r for r in second.get("runs") or [] if r.get("kind") == "week" and r.get("mode") == VIOLATION_MODE
            and r.get("tag") in ROW_TAGS and str(r.get("cell")) in weeks and int(r.get("seed", -1)) == 0]
    count = 0
    for r in rows:
        name = L.run_file("second", r["job"])
        if not inp.path(name).is_file():
            raise MissingKey(f"{name}: no such run file (second/runs/ is not versioned; build with the input root of "
                             "the confirmation's copy, W10)")
        if not any(f["path"] == name for f in runs_files):
            runs_files.append({"path": name, "sha256": L.sha256_of(inp.path(name))})
        recs = [x for x in inp.json(name).get("runs") or [] if x.get("mode") == VIOLATION_MODE
                and int(x.get("policy_seed", -1)) == 0]
        if len(recs) != 1:
            raise MissingKey(f"{name}: {len(recs)} runs of mode {VIOLATION_MODE} and policy seed 0")
        count += int(need(recs[0], "buffer_violations", "count", what=name))
    return {"mode": VIOLATION_MODE, "runs": len(rows), "count": count}


def same_modes(st: Mapping, mt: Mapping, weeks: Sequence[str]) -> dict:
    """Whether every row's r0 agrees under all of SAME_MODES on every week: {modes, weeks, equal}."""
    eq = True
    for tag in ROW_TAGS:
        for w in weeks:
            vals = [L.val(st if part == "second" else mt, tag, m, w) for m, part in SAME_MODES]
            if any(v is None for v in vals) or max(vals) - min(vals) > 1e-12:
                eq = False
    return {"modes": [m for m, _ in SAME_MODES], "weeks": list(weeks), "equal": eq}


def x_ranges(d: Mapping) -> list[dict]:
    """Per panel the drawn x range {lo, hi, own}: the panels share the range of their data (medians, interval ends,
    the grey ticks) and 1 (all-fallback), except a panel whose span exceeds WIDE_FACTOR times the median panel's,
    which has its own; X_PAD on each side."""
    spans = []
    for p in d["panels"]:
        vals = [1.0]
        for r in d["rows"]:
            s = r.get("lag") if p["mode"] == "lag" else r["modes"].get(p["mode"])
            if s is None:
                continue
            vals += [v for v in (s["median"], s["lo"], s["hi"], r["ref"]["median"]) if v is not None]
        spans.append((min(vals), max(vals)))
    med = sorted(b - a for a, b in spans)[len(spans) // 2]
    own = [b - a > WIDE_FACTOR * med for a, b in spans]
    shared = [sp for sp, o in zip(spans, own) if not o]
    lo_s, hi_s = min(a for a, _ in shared), max(b for _, b in shared)
    out = []
    for (a, b), o in zip(spans, own):
        lo, hi = (a, b) if o else (lo_s, hi_s)
        pad = X_PAD * max(hi - lo, 1e-6)
        out.append({"lo": lo - pad, "hi": hi + pad, "own": o})
    return out


# ---------------------------------------------------------------------------------------------------------------
# tables' data
def boundary_table(rows: Sequence[Mapping], weeks: Sequence[str], vr: Mapping | None = None,
                   same: Mapping | None = None) -> dict:
    modes = [L.TRACE] + [m for _, m, _ in PANELS if m != "lag"]
    return {"weeks": list(weeks), "modes": modes, "violations": dict(vr or {}), "same_modes": dict(same or {}),
            "rows": [{"tag": r["tag"], "label": r["label"],
                      "by_mode": {L.TRACE: r["ref"], **r["modes"]}} for r in rows],
            "scope": {"tags": [r["tag"] for r in rows], "modes": modes, "weeks": list(weeks), "seeds": [0],
                      "parts": {"main": [L.TRACE], "second": modes[1:]}}}


def lag_table(rows: Sequence[Mapping], weeks: Sequence[str]) -> dict:
    pairs = []
    for r in rows:
        if "lag" not in r:
            continue
        a, b = r["ref"]["values"], r["lag"]["values"]
        diff = [None if x is None or y is None else y - x for x, y in zip(a, b)]
        pairs.append({"tag": r["tag"], "label": r["label"], "lag_tag": r["lag"]["tag"],
                      "lag_label": L.label(r["lag"]["tag"]), "lag_part": r["lag"]["part"], "base": r["ref"],
                      "lagged": {k: r["lag"][k] for k in ("values", "median", "lo", "hi", "n")},
                      "diff": {"values": diff, **L.med_ci(diff)}})
    return {"weeks": list(weeks), "pairs": pairs,
            "scope": {"tags": [p["tag"] for p in pairs] + [p["lag_tag"] for p in pairs], "modes": [L.TRACE],
                      "weeks": list(weeks), "seeds": [0]}}


def e5_table(second: Mapping) -> dict:
    t = second["table"]
    cells = sorted({c.split(":", 1)[1] for tag in E5_TAGS for lv in E5_LEVELS for c in (t[tag].get(lv) or {})},
                   key=lambda c: int(c.lstrip("c")))
    if not cells:
        raise MissingKey(f"{L.SECOND}: no E5 run under {E5_LEVELS}")
    rows = []
    for menu in E5_MENUS:
        for lv in E5_LEVELS:
            for tag in E5_TAGS:
                vals = [L.val(t, tag, lv, f"{menu}:{c}") for c in cells]
                rows.append({"menu": menu, "level": lv, "tag": tag, "label": L.label(tag), "values": vals,
                             **L.med_ci(vals)})
    return {"cells": cells, "rows": rows,
            "scope": {"tags": list(E5_TAGS), "menus": list(E5_MENUS), "levels": list(E5_LEVELS), "cells": cells,
                      "seeds": [0]}}


def gap_table(second: Mapping) -> dict:
    lp = need(second, "gap_lp", what=L.SECOND)
    ratio = need(second, "gap_ratio", what=L.SECOND)
    days = sorted(lp, key=lambda c: int(c.split(":c")[-1]))
    tags = [t for t in ROW_TAGS if any(f"{t}:{d}:0" in ratio for d in days)]
    bl0a = {}
    for r in second["runs"]:
        if r.get("kind") == "gap" and r.get("bl0a_usd") is not None:
            bl0a.setdefault(r["cell"], set()).add(round(float(r["bl0a_usd"]), 6))
    if any(len(bl0a.get(d, ())) != 1 for d in days):
        raise MissingKey(f"{L.SECOND}: the gap rows of a day must share one bl0a_usd ({bl0a})")
    rows = []
    for tag in tags:
        vals = [ratio.get(f"{tag}:{d}:0") for d in days]
        rows.append({"tag": tag, "key": L.KEY_OF_TAG[tag], "label": L.label(tag), "values": vals, **L.med_ci(vals)})
    b = [next(iter(bl0a[d])) / lp[d] for d in days]
    rows.append({"tag": "BL0a", "key": "bl0a", "label": style.POLICIES["bl0a"].label, "values": b, **L.med_ci(b)})
    return {"days": days, "lp_usd": [lp[d] for d in days], "bl0a_usd": [next(iter(bl0a[d])) for d in days],
            "rows": rows, "scope": {"tags": tags + ["BL0a"], "days": days, "modes": [L.TRACE], "seeds": [0]}}


# ---------------------------------------------------------------------------------------------------------------
def row_name(fig, label: str) -> str:
    """A row's name: ms5b_e7_lib.wrap at ROW_WRAP_IN; C59: where that leaves a line wider than ROW_NAME_MAX_IN, the
    label broken at its spaces outside $...$ into lines of at most ROW_LINE_IN (the words stay the label's)."""
    w = L.wrap(fig, label, ROW_WRAP_IN)
    if text_width_in(fig, w) <= ROW_NAME_MAX_IN:
        return w
    words, part = [], ""
    for tok in str(label).split(" "):
        part = tok if not part else part + " " + tok
        if part.count("$") % 2 == 0:
            words.append(part)
            part = ""
    if part:
        words.append(part)
    lines, cur = [], ""
    for word in words:
        t = word if not cur else cur + " " + word
        if cur and text_width_in(fig, t) > ROW_LINE_IN:
            lines.append(cur)
            cur = word
        else:
            cur = t
    lines.append(cur)
    return "\n".join(lines)


def row_layout(fig, rows: Sequence[Mapping], height_pt: float) -> tuple[list[str], list[float]]:
    """(names, centers): each row's name (wrapped at ROW_WRAP_IN) and its center in points from the axes top. The
    names' boxes at TICK_PT (measured at 7 pt: 7.2 pt, 10.1 pt with a math part, 18.7 pt on two lines; at 9 pt,
    until C62, 8.6, 11.5 and 21.7 pt; C62: each one-line name counted at the tallest one-line name's height, so that
    the one-line rows share one pitch) are stacked with
    one gap between neighbors and half a gap above the first and below the last, filling `height_pt`; StyleError
    where the gap would be below ROW_GAP_MIN_PT (finalize() would find the names overlapping)."""
    names = [row_name(fig, r["label"]) for r in rows]                                                    # C59
    r = fig.canvas.get_renderer()
    heights = []
    for n in names:
        t = fig.text(0.0, 0.0, n, fontsize=style.TICK_PT, va="center")
        heights.append(t.get_window_extent(r).height * style.BP_PER_IN / fig.dpi)
        t.remove()
    # C62: every one-line name takes the height of the tallest one-line name (a math part's), so that the one-line
    # rows share one pitch and the bands behind them (row_bands) one height
    one = max((h for h, n in zip(heights, names) if "\n" not in n), default=0.0)
    heights = [h if "\n" in n else one for h, n in zip(heights, names)]
    gap = (height_pt - sum(heights)) / len(names)
    if gap < ROW_GAP_MIN_PT:
        raise style.StyleError(f"{NAME}: the row names need {sum(heights):.1f} pt, the axes have {height_pt:.1f} pt")
    centers, y = [], 0.5 * gap
    for h in heights:
        centers.append(y + 0.5 * h)
        y += h + gap
    return names, centers


def x_ticks(lo: float, hi: float) -> list[float]:
    for stp in X_STEPS:
        t = [round(k * stp, 10) for k in range(math.ceil(lo / stp - 1e-9), math.floor(hi / stp + 1e-9) + 1)]
        if X_MIN_TICKS <= len(t) <= X_MAX_TICKS:
            return t
    return [round(lo, 2), round(hi, 2)]


def draw(data: Mapping) -> Any:
    fig = style.new_figure(NAME)
    rows, panels = data["rows"], data["panels"]
    wrapped = [row_name(fig, r["label"]) for r in rows]                                                  # C59
    reserve = max(text_width_in(fig, n) for n in wrapped) + (mpl_tick_in() + 0.04)
    n = len(panels)
    axes = style.panel_row(fig, [1.0] * n, sharey=[False] + [True] * (n - 1),
                           left=[reserve] + [PANEL_GAP_IN] * (n - 1))
    h_pt = style.axes_rect_in(axes[0])[3] * style.BP_PER_IN
    names, centers = row_layout(fig, rows, h_pt)
    for ax, p, xr in zip(axes, panels, data.get("x_ranges") or x_ranges(data)):
        x0, x1 = xr["lo"], xr["hi"]
        ticks = x_ticks(x0, x1)
        ax.set_xlim(x0, x1)
        if x0 < 1.0 < x1:
            style.reference_line(ax, x=1.0)
        for r, y in zip(rows, centers):
            if p["mode"] == "lag":
                if "lag" not in r:
                    continue
                s, key = r["lag"], r["lag"]["key"]
            else:
                s, key = r["modes"][p["mode"]], r["key"]
            ref = r["ref"]["median"]
            if ref is not None:
                (tk,) = ax.plot([ref, ref], [y - TICK_HALF, y + TICK_HALF], color=style.THEORY_GREY,
                                linewidth=TICK_PT, solid_capstyle="butt", zorder=style.Z_REFERENCE + 0.1)
                tk._sublet_role = "reference_tick"
            if s["median"] is None:
                continue
            if s["lo"] is not None and s["hi"] is not None and s["hi"] > s["lo"]:
                style.errorbars(ax, key, [s["median"]], [y], [s["lo"]], [s["hi"]], orientation="x")
            style.scatter_policy(ax, key, [s["median"]], [y])
        ax.set_ylim(h_pt, 0.0)
        ax.xaxis.set_major_locator(FixedLocator(ticks))
        ax.xaxis.set_major_formatter(style.PLAIN)
        ax.tick_params(axis="y", length=0)
    axes[0].set_yticks(centers, names)
    for t in axes[0].get_yticklabels():
        t.set_verticalalignment("center")
    # C62: a name with a mathtext part sits on the plain names' baseline offset from its row's center, as the PDF
    # prints it (as built, 0.7 pt higher: matplotlib rounds a mathtext line's height up to a whole pt there)
    align_baselines(axes[0].get_yticklabels())
    center_xlabel(axes, data["labels"]["x"])
    letters = style.panel_letters(axes)
    for ax, letter, p in zip(axes, letters, panels):
        L.caption_title(ax, letter, p["title"])
    row_bands(fig, axes, centers, h_pt, reserve)
    return fig


def row_bands(fig, axes, centers: Sequence[float], h_pt: float, reserve: float) -> list:
    """C62: a ROW_BAND_GREY band behind every other row (the first, Sublet's, included), from ROW_BAND_INSET_IN
    inside the name column's left edge (`reserve` left of the first panel) to the right edge of the last panel, its edges the midpoints
    between neighboring rows' centers (`centers`, pt from the axes top; the axes' top and bottom at the ends). The
    bands are figure rectangles below the axes (zorder -1), whose faces are hidden. Returns the bands."""
    from matplotlib.patches import Rectangle
    x0 = style.axes_rect_in(axes[0])[0] - reserve + ROW_BAND_INSET_IN   # the longest name starts 0.04 in further
    _, y0, _, h = style.axes_rect_in(axes[0])
    x1 = sum(style.axes_rect_in(axes[-1])[0:3:2])
    top = y0 + h                                                   # inches from the figure's bottom
    edges = [0.0] + [0.5 * (a + b) for a, b in zip(centers, centers[1:])] + [h_pt]
    W, H = (float(v) for v in fig.get_size_inches())                # placed in figure fractions (transFigure), as
    #                                                                 style.ink_outside_sides requires
    out = []
    for i in range(0, len(centers), 2):
        a, b = edges[i] / style.BP_PER_IN, edges[i + 1] / style.BP_PER_IN
        r = Rectangle((x0 / W, (top - b) / H), (x1 - x0) / W, (b - a) / H, transform=fig.transFigure,
                      facecolor=ROW_BAND_GREY, edgecolor="none", linewidth=0.0, zorder=-1.0)
        r._sublet_role = "row_band"
        fig.add_artist(r)
        out.append(r)
    for ax in axes:
        ax.patch.set_visible(False)
    return out


def mpl_tick_in() -> float:
    """The y tick's length plus its pad (in): the name's distance from the spine."""
    return (mpl.rcParams["ytick.major.size"] + mpl.rcParams["ytick.major.pad"]) / style.BP_PER_IN


# ---------------------------------------------------------------------------------------------------------------
# LaTeX
MODE_TEX = {L.TRACE: "L-tr (part main)", "L-vr": "L-vr", "L-rf": "L-rf", "L-ad": "L-ad",
            "L-b999": "P99.9 buffer"}
NAME_IN = 2.0                   # the name column (in): the longest label, Sublet-MS4's, on two lines at 8 pt
NAME_COL = f"p{{{NAME_IN}in}}"


def _cells(vals, fmt=".3f") -> list[str]:
    return [L.num(v, fmt) for v in vals]


def _stat(s: Mapping, fmt=".3f") -> list[str]:
    return [L.num(s["median"], fmt), L.interval(s["lo"], s["hi"], fmt)]


def boundary_tex(t: Mapping, d: Mapping) -> str:
    weeks = t["weeks"]
    rows, groups = [], []
    for r in t["rows"]:
        groups.append(len(rows))
        nm = L.name_cells(L.tex(r["label"]), len(t["modes"]), NAME_IN)
        for j, m in enumerate(t["modes"]):
            s = r["by_mode"][m]
            rows.append([nm[j], MODE_TEX.get(m, L.tex(m))] + _cells(s["values"])
                        + _stat(s))
    vr, same = t.get("violations") or {}, t.get("same_modes") or {}
    cap = (r"Boundary conditions of part second (weeks " + L.week_span(weeks) + r", policy seed 0): cost over "
           r"all-fallback $r_0$ per week under the trace lender (part main, the reference), L-vr (buffer violations "
           r"as reclaims without notice), L-rf (purchases on unavailable layers refused), L-ad (every lease announced "
           r"at the end of its guaranteed period) and the P99.9 buffer, with the median and the range over the "
           r"weeks."                                                                                       # C59
           + (f" No buffer violation occurred in the {vr['runs']} L-vr runs"
              + (r", so L-vr's rows equal the trace lender's for every policy" if vr.get("equals_trace") else "")
              + "." if vr.get("runs") and vr.get("count") == 0 else "")
           + (r" On these weeks L-ad gives the same $r_0$ as the eager lender L-eg and the i.i.d.\ lender at $p=1$ "
              r"for every policy (each announces every revocable lease when its guaranteed period ends)."
              if same.get("equal") else ""))
    return L.longtable("@{}" + NAME_COL + "l" + "r" * (len(weeks) + 1) + "c@{}", cap, "tab:e7v2-boundary",
                       ["Policy", "Lender"] + list(weeks) + ["Median", "Range"], rows, groups=groups)       # C59


def lag_tex(t: Mapping, d: Mapping) -> str:
    weeks = t["weeks"]
    rows, groups = [], []
    for p in t["pairs"]:
        groups.append(len(rows))
        nm = L.name_cells(L.tex(p["label"]), 3, NAME_IN)
        for j, (what, s) in enumerate((("unlagged", p["base"]), ("lagged", p["lagged"]),
                                       ("lagged $-$ unlagged", p["diff"]))):
            rows.append([nm[j], what] + _cells(s["values"]) + _stat(s))
    parts = []
    for part in sorted({p["lag_part"] for p in t["pairs"]}, key=lambda x: (x != "second", x)):
        labs = [L.tex(p["lag_label"]) for p in t["pairs"] if p["lag_part"] == part]
        parts.append(L.join_labels(labs) + f" from part {part}")
    cap = (r"Lagged demand under the trace lender (weeks " + L.week_span(weeks) + r", policy seed 0): $r_0$ of each "
           r"policy on the revealed slot's demand (part main) and on slot $t-1$'s demand, and their difference, per "
           r"week, with the median and the range over the weeks. The lagged runs: " + "; ".join(parts) + ".")  # C59
    return L.longtable("@{}" + NAME_COL + "l" + "r" * (len(weeks) + 1) + "c@{}", cap, "tab:e7v2-lag",
                       ["Policy", "Demand"] + list(weeks) + ["Median", "Range"], rows, groups=groups)       # C59


def e5_tex(t: Mapping, d: Mapping) -> str:
    cells = t["cells"]
    rows, groups, prev = [], [], None
    for r in t["rows"]:
        if (r["menu"], r["level"]) != prev:
            groups.append(len(rows))
        first = (r["menu"], r["level"]) != prev
        prev = (r["menu"], r["level"])
        rows.append([r["menu"] if first else "", r["level"] if first else "", L.rag(L.tex(r["label"]))]
                    + _cells(r["values"])
                    + _stat(r))
    cap = (r"E5's menus in part second (one week, E5 config seeds " + ", ".join(c.lstrip("c") for c in cells)
           + r", policy seed 0): $r_0$ per config seed on the short menu (spot-like contracts with notice up to "
           r"2~min, and the protected contract) and the long menu (notice 60--240~min, and the protected contract), "
           r"under the trace lender and all1 (the correlated lender with every site in one group), with the median "
           r"and the range over the config seeds.")                                                        # C59
    n = len(cells)
    return L.longtable("@{}ll" + NAME_COL + "r" * (n + 1) + "c@{}", cap, "tab:e7v2-e5",
                       ["Menu", "Lender", "Policy"] + [c.lstrip("c") for c in cells] + ["Median", "Range"],  # C59
                       rows, groups=groups,
                       head_top=(r" & & & \multicolumn{" + str(n) + r"}{c}{E5 config seed} & & \\ \cmidrule(lr){4-"
                                 + str(3 + n) + "}"))


def gap_tex(t: Mapping, d: Mapping) -> str:
    days = t["days"]
    heads = [x.split(":c")[-1] for x in days]
    rows = [[L.rag(L.tex(r["label"]))] + _cells(r["values"]) + _stat(r) for r in t["rows"]]
    rows.append([r"LP bound (USD)"] + [L.num(v, ",.0f") for v in t["lp_usd"]] + ["", ""])
    cap = (r"Gap days of part second (the first day of each of weeks " + L.week_span(heads) + r", policy seed 0; one "
           r"day of the reduced-menu instance on the slow grid, with the revocable contracts " + _menu_text()
           + r"): cost over the merged LP lower bound, ALG/LB, an upper bound on each policy's gap, per day, with the "
           r"median and the range over the days; all-fallback's from its cost over the bound.")            # C59
    return L.longtable("@{}" + NAME_COL + "r" * (len(days) + 1) + "c@{}", cap, "tab:e7v2-gap",
                       ["Policy"] + heads + ["Median", "Range"], rows, groups=[len(rows) - 2, len(rows) - 1])  # C59


def _menu_text() -> str:
    """The gap days' revocable contracts (ms4_common.H5_OVERRIDES: the menu with the contract of H = 5 min in place
    of H = 2 min) as '$(\\tau,H)$ = (5, 5), (5, 60) and (60, 0)~min', read from the contract ids."""
    pairs = []
    for cid in m4.H5_OVERRIDES["lender_defaults.menu"]:
        m = re.search(r"tau(\d+)_H(\d+)", cid)
        if m is None:
            raise MissingKey(f"ms4_common.H5_OVERRIDES: contract id {cid!r} without tau and H")
        pairs.append(f"({m.group(1)}, {m.group(2)})")
    return r"$(\tau,H)$ = " + (", ".join(pairs[:-1]) + " and " + pairs[-1] if len(pairs) > 1 else pairs[0]) + "~min"


def write_tables(data: Mapping, report: Mapping) -> None:
    """The four tables from the extract's `tables` (figs.common.write_table)."""
    t = data["tables"]
    paths = [write_table(TABLES[0], L.table_head(NAME, [L.SECOND, L.MAIN]) + boundary_tex(t["e7v2_boundary"], data)),
             write_table(TABLES[1], L.table_head(NAME, [L.SECOND, L.MAIN]) + lag_tex(t["e7v2_lag"], data)),
             write_table(TABLES[2], L.table_head(NAME, [L.SECOND]) + e5_tex(t["e7v2_e5"], data)),
             write_table(TABLES[3], L.table_head(NAME, [L.SECOND]) + gap_tex(t["e7v2_gap"], data))]
    print(f"[{NAME}] wrote {', '.join(str(p) for p in paths)}")


def main(argv: Sequence[str] | None = None) -> dict:
    return cli(NAME, build, draw, argv, supplementary=True, after=write_tables, doc=__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
