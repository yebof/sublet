"""sf_e7_grid_dev: part grid of the confirmation, development-exposed (design/sublet_v2.md §11, W4, W7, W9, W10;
§4.1, §4.4(e), §6 "reported in full"; plan §4, part S-F).

Continuity only: E7's alignments 1-4 and the Q44 held-out cells were read in development (§4.1), so nothing here is a
confirmation result; the titles of (a) and (b) ((c) continues (b)), the caption and both tables say
"development-exposed".

Inputs (versioned): code/sim/out/sublet_v2/grid/summary.json (runs: the week runs of the alignments, the gap days and
the Q44 runs, each with its r0 = cost / BL0a; W0.<seed>.<tag>.<alignment>; gap_ratio; meta.tags) and E11's
code/sim/out/e11/summary.json (D2.<instance>: the median r0 per lender mode over E11's held-out cells with their counts,
the stress modes and W0 per policy; D4.thresholds.y_S, criterion S's y). The alignments, instances, cells, modes and
seeds are read from the runs, never typed (the reduced fixtures have other ones). No runs/ file is read (W10; the
extract's meta.runs_files is empty). E11's rows are named by their MS5b keys (C41, W7): BL1-G as bl1_g1 (Greedy +
one-way guard), BL5-G as bl5_g1 (Lagged RetroRenting + one-way guard) and BL5, the lagged build, as bl5_lag; E11's A7
rows (PS, PS-G) are not drawn.

Q44's definitions (q44_summary, E11 D2 and D4): per cell and mode r0 averaged over the policy seeds; per instance and
mode the median over the held-out cells; W0 per policy and instance the largest such median over the instance's stress
modes (q44_study.MODES[mode]['stress'], imported read-only, among the modes run there); criterion S holds for a policy
when W0 <= 1 + y_S on every instance (y_S from E11's D4.thresholds). Criterion T (D1 <= 1 + x_T on three instances, D1
the cost over the best of BL1, BL2 and BL5) is not computable: part grid runs no renting baseline on these cells
(§4.4(e): Sublet, A9 and BL1-GP); the caption and the table say so, and the table's T column gives E11's own T
verdicts (D4.criteria.<tag>.T, over E11's cells and baselines) for E11's rows. E11's medians are E11's own (its cells:
I1 there also holds the I1-d100 cells; its commit), set beside the grid's, not paired with them.

Layout (W2 x 2.4 in, C41), three panels sharing one linear y axis (cost over all-fallback, the level 1 a reference
line), the series dodged in x by DODGE (categorical x), markers only (the x categories have no order to join):
(a) E7, trace lender, against the alignment: the median over the policy seeds of r0 with the range over the seeds
    (bars) for Sublet, Critical-ratio renting (A9), Greedy + guard (BL1-GP), RetroRenting-style, lagged (BL5) and Greedy
    renting (BL1); the other tags of part grid are in e7v2_grid.tex;
(b) the Q44 held-out cells, trace lender, against the instance: the median r0 of Sublet, A9 and BL1-GP (part grid) and
    of E11's BL1-G, BL5-G and BL5;
(c) the same policies' W0 per instance, with criterion S's threshold 1 + y_S as a second reference line, labeled on the
    free space next to it (common.place_label).
In every panel the series sit left to right in the legend's order (style.legend_order, read down the legend's
columns), so that a series keeps its place in each group and its position backs up its marker in greyscale, where the
orange and light-blue triangles print at one grey (print check of 2026-11-03). The legend is two rows of markers
without line segments, as every panel draws markers only (the seven keys need 7.7 in in one row at 7 pt), with a
handle length of LEGEND_HANDLE em (rcParams for the legend_row call; 2.0 left a gap of about 10 pt between a marker and
its name). C62: the panel titles at the caption size (ms5b_e7_lib.caption_title; (c)'s, with its mathtext W0, on the
letters' baseline as the PDF prints it).
The set of the figure in style.SUPP_POLICIES_MS5B is the seven keys drawn (changed by U39b from C41's 22 E7 tags,
which no panel draws legibly and two of whose (marker, fill) pairs E11's guarded rows take).

Tables (TABLES; written by the after hook from the extract's `tables`, each with its `scope`; booktabs and array):
  e7v2_grid.tex  every tag of part grid (style.POLICIES labels): r0 under the trace lender at each alignment, r0 under
                 each stress lender at the alignment(s) with stress runs (ms5b_common.stress_modes' order) and W0 there
                 (each the median over the policy seeds), and the gap days' ALG / merged LP (the median over the days
                 of the median over the seeds); the caption gives, from the runs, the tags that ran fewer policy
                 seeds (seed_sets) and those whose seeds give equal values in every entry, the tags that abort in
                 every grid run with the abort slots (aborts, from the runs' guard records), and the largest range
                 over the seeds of any r0 entry; it explains a dash only where a cell has none.
                 Its scope lists the tags, modes, seeds, alignments and the gap days' cells (gap:c<c>), the cell ids
                 of the summary's week and gap runs
  e7v2_q44.tex   per drawn policy and instance the cells, the median r0 under the trace lender, W0 with its mode, and
                 criteria S and T, E11's rows marked with their source: T is not computable for part grid's rows and
                 is E11's own verdict (D4.criteria.<tag>.T, over E11's cells and baselines) for E11's rows

The caption draft (labels.caption) reads every count from the inputs. Run from code/sim:
python -m figs.supp.sf_e7_grid_dev [--from-extract [JSON]] (figs.common.cli).

C50 (design/ms6_spec.md §7.2, the D5 review; §7.1 D4's script items): the caption names the gap days' menu "the
reduced menu", not by its base name e7r.
"""
from __future__ import annotations

import re
import statistics
import sys
from typing import Any, Mapping, Sequence

import matplotlib
import numpy as np

from figs import style
from figs.common import MissingKey, cli, finite, need, place_label, points_pt, write_table
from figs.inputs import Inputs
from figs.supp.ms5b_e7_lib import caption_title
from figs.supp.ms4_lib import drop_idle_halos
from figs.supp.sf_e3_v2 import tex_f, tex_label
from figs.supp.sf_e7_mix import _tex_text
from sublet.experiments.ms5b_common import stress_modes as e7_stress_modes
from sublet.experiments.q44_study import MODES as Q44_MODES

NAME = "sf_e7_grid_dev"
GRID = "code/sim/out/sublet_v2/grid/summary.json"
E11 = "code/sim/out/e11/summary.json"
KEYS = style.SUPP_POLICIES_MS5B[NAME]          # the seven keys drawn
# every E7 tag of part grid by registry key (C41), in §3's order (the table's rows)
GRID_KEY = {"Sublet": "sublet_v2", "A9": "a9", "Sublet-1way": "sublet_1way", "BL1-GP": "bl1_gp",
            "Sublet-MS4": "sublet_ms4", "BL1": "bl1", "BL1-BO": "bl1_bo", "BL2": "bl2", "BL3-0": "bl3_0",
            "BL4": "bl4", "BL5-cur": "bl5_cur", "BL5": "bl5_lag", "BL5-tau60": "bl5_tau60", "BL5N": "bl5n",
            "BL1N": "bl1n", "CR": "cr", "A9-noMBB": "a9_nombb", "A9-noCommit": "a9_nocommit", "A9-noIns": "a9_noins",
            "A9-kstar": "a9_kstar", "A9-static": "a9_static", "A6": "a6"}
E11_KEY = {"BL1-G": "bl1_g1", "BL5-G": "bl5_g1", "BL5": "bl5_lag"}       # E11's rows (W4, W7)
A_TAGS = ("Sublet", "A9", "BL1-GP", "BL5", "BL1")                       # (a), part grid
Q_GRID_TAGS = ("Sublet", "A9", "BL1-GP")                                # (b), (c): part grid ...
Q_E11_TAGS = ("BL1-G", "BL5-G", "BL5")                                  # ... and E11
TRACE = "L-tr"
# dodge slots, left to right, per panel; drawing order: Sublet last
A_SLOTS = ("sublet_v2", "a9", "bl1_gp", "bl5_lag", "bl1")
Q_SLOTS = ("sublet_v2", "a9", "bl1_gp", "bl1_g1", "bl5_g1", "bl5_lag")
A_SLOTS = tuple(style.legend_order(A_SLOTS))     # left to right in the legend's order (print check of 2026-11-03)
Q_SLOTS = tuple(style.legend_order(Q_SLOTS))
LEGEND_HANDLE = 0.8              # the legend's handle length (em) for markers without line segments (not in §8)
DODGE = 0.13                     # x offset between neighboring slots, in categories (not in §8)
Y_STEPS = (0.05, 0.1, 0.2, 0.25, 0.5)
THRESHOLD_DASH = (0, (3.0, 1.6))  # (c): criterion S's threshold, a dashed reference line (the level 1 is solid)
LABEL_RAISE = 0.04               # (c): the y top is raised by this share of the range until the S label fits ...
MAX_RAISE = 10                   # ... at most this many times (not in §8)
TITLE_CLEAR_PT = 3.0             # (c): the S label stays below this line under the axes top (the panel title above)
TABLES = ("e7v2_grid.tex", "e7v2_q44.tex")
CELL_Q = re.compile(r"^(I\d+):c(\d+)$")
style.register_supplementary(NAME, "W2", 2.4)
LABELS = {"y": "Cost / all-fallback", "a_x": "Alignment, trace lender", "b_x": "Instance, trace lender",
          # C59 (RC19(3)): the panel titles in words (as built "E7, development-exposed", "Q44, development-exposed"
          # and "Q44, worst case $W_0$"); the caption says that the whole figure is development-exposed
          "c_x": "Instance", "titles": {"a": "End-to-end week", "b": "Guard study's held-out cells",
                                        "c": r"Held-out cells, worst case $W_0$"},
          "threshold": r"S: $W_0\leq{v:g}$", "dev": "development-exposed",
          "T": "not computable: part grid runs no renting baseline (BL1, BL2, BL5) on these cells",
          "order": "the series sit left to right in the legend's order, read down its columns"}


# ---------------------------------------------------------------------------------------------------------------
# inputs
def tag_order(s: Mapping) -> list[str]:
    tags = need(s, "meta", "tags", what=GRID)
    bad = [t for t in tags if t not in GRID_KEY]
    if bad:
        raise MissingKey(f"{GRID}: tags without a registry key: {bad}")
    return [t for t in GRID_KEY if t in tags]


def by_cell(runs: Sequence[Mapping], kind: str) -> dict:
    """{(tag, cell, mode): {seed: r0}} of the ok runs of `kind`."""
    out: dict = {}
    for r in runs:
        if r.get("kind") == kind and r.get("status") == "ok" and r.get("r0") is not None:
            out.setdefault((r["tag"], str(r["cell"]), r["mode"]), {})[int(r["seed"])] = float(r["r0"])
    return out


def seed_point(vals: Mapping) -> dict:
    """{median, lo, hi, n} over the policy seeds."""
    v = list(vals.values())
    if not v:
        return {"median": None, "lo": None, "hi": None, "n": 0}
    return {"median": float(np.median(v)), "lo": min(v), "hi": max(v), "n": len(v)}


def alignments_of(week: Mapping) -> list[str]:
    return sorted({c for _, c, _ in week}, key=lambda c: (float(c) if c.replace(".", "").isdigit() else 1e9, c))


def w0_at(s: Mapping, tag: str, cell: str) -> dict:
    """W0 of the summary (W0.<seed>.<tag>.<cell>) over the policy seeds with a value."""
    vals = {}
    for seed, by in (s.get("W0") or {}).items():
        v = ((by or {}).get(tag) or {}).get(cell)
        if v is not None:
            vals[int(seed)] = float(v)
    return seed_point(vals)


def gap_of(s: Mapping, tag: str) -> dict:
    """The gap days' ALG / merged LP: per day the median over the seeds, then the median over the days."""
    days: dict = {}
    for k, v in (s.get("gap_ratio") or {}).items():
        t, _, day, seed = k.rsplit(":", 3)
        if t == tag and v is not None:
            days.setdefault(day, []).append(float(v))
    per = {d: float(np.median(v)) for d, v in sorted(days.items())}
    return {"by_day": per, "median": float(np.median(list(per.values()))) if per else None, "n_days": len(per)}


def q44_grid(runs: Sequence[Mapping]) -> dict:
    """Per instance: the held-out cells, the modes, and per tag the median r0 per mode (cell values averaged over the
    seeds), W0 and its mode (Q44's definitions)."""
    q = by_cell(runs, "q44")
    insts: dict = {}
    for tag, cell, mode in q:
        m = CELL_Q.match(cell)
        if m is None:
            raise MissingKey(f"{GRID}: Q44 cell {cell!r} is not of the form I<k>:c<n>")
        insts.setdefault(m.group(1), {"cells": set(), "modes": set()})
        insts[m.group(1)]["cells"].add(cell)
        insts[m.group(1)]["modes"].add(mode)
    out = {}
    for inst in sorted(insts, key=lambda i: int(i[1:])):
        cells = sorted(insts[inst]["cells"], key=lambda c: int(CELL_Q.match(c).group(2)))
        modes = [m for m in Q44_MODES if m in insts[inst]["modes"]]
        stress = [m for m in modes if Q44_MODES[m]["stress"]]
        tags = {}
        for tag in Q_GRID_TAGS:
            med = {}
            for mode in modes:
                vals = [statistics.fmean(q[(tag, c, mode)].values()) for c in cells if (tag, c, mode) in q]
                med[mode] = {"median": float(np.median(vals)) if vals else None, "cells": len(vals)}
            w = [(med[m]["median"], m) for m in stress if med[m]["median"] is not None]
            tags[tag] = {"by_mode": med, "r0_tr": med.get(TRACE, {}).get("median"),
                         "W0": max(w)[0] if w else None, "W0_mode": max(w)[1] if w else None}
        out[inst] = {"cells": cells, "modes": modes, "stress_modes": stress, "tags": tags}
    return out


def q44_e11(e11: Mapping, insts: Sequence[str]) -> dict:
    d2 = need(e11, "D2", what=E11)
    out = {}
    for inst in insts:
        blk = need(d2, inst, what=f"{E11} D2")
        tr = need(blk, "modes", TRACE, what=f"{E11} D2.{inst}")
        tags = {}
        for tag in Q_E11_TAGS:
            w = need(blk, "W0", tag, what=f"{E11} D2.{inst}")
            tags[tag] = {"r0_tr": need(tr, "r0", tag, what=f"{E11} D2.{inst}.modes.{TRACE}").get("median"),
                         "W0": w.get("W0"), "W0_mode": w.get("argmax_mode")}
        out[inst] = {"cells": tr.get("cells"), "stress_modes": list(blk.get("stress_modes") or []), "tags": tags}
    return out


def aborts_of(runs: Sequence[Mapping], tag: str) -> dict:
    """The guard's aborts in the tag's ok week and gap runs: runs, aborted, the abort slots t_a with their counts and
    whether the safe expert followed all-fallback after every abort (s_fb_all)."""
    rs = [r for r in runs if r.get("kind") in ("week", "gap") and r.get("status") == "ok" and r.get("tag") == tag]
    ab = [r["guard"] for r in rs if (r.get("guard") or {}).get("aborted")]
    slots: dict = {}
    for g in ab:
        k = str(g.get("t_a"))
        slots[k] = slots.get(k, 0) + 1
    return {"runs": len(rs), "aborted": len(ab), "t_a": dict(sorted(slots.items(), key=lambda kv: (-kv[1], kv[0]))),
            "s_fb_all": bool(ab) and all(g.get("s_fb_all") is True for g in ab)}


def seed_sets(runs: Sequence[Mapping], tags: Sequence[str]) -> dict:
    """{tag: sorted policy seeds} of the ok week and gap runs."""
    out = {t: set() for t in tags}
    for r in runs:
        if r.get("kind") in ("week", "gap") and r.get("status") == "ok" and r.get("tag") in out:
            out[r["tag"]].add(int(r["seed"]))
    return {t: sorted(v) for t, v in out.items()}


def criterion_s(w0s: Sequence, y: float) -> bool | None:
    """S on the instances given: W0 <= 1 + y on every one; None where an instance has no W0."""
    if not w0s or any(v is None for v in w0s):
        return None
    return all(v <= 1.0 + y + 1e-12 for v in w0s)


def caption(d: Mapping) -> str:
    a, q = d["a"], d["q44"]
    n_al = len(a["alignments"])
    insts = q["instances"]
    s_of = {k: v["S"] for k, v in q["series"].items()}
    holds = [style.POLICIES[k].label for k, v in s_of.items() if v is True]
    fails = [style.POLICIES[k].label for k, v in s_of.items() if v is False]
    # labels may hold commas ("RetroRenting-style, lagged"): the lists are separated by semicolons
    s_text = "".join(t for t in ((f" It holds for {'; '.join(holds)}." if holds else ""),
                                 (f" It fails for {'; '.join(fails)}." if fails else "")))
    rng = a.get("max_range")
    hidden = (f" Ranges narrower than a marker are hidden by it (the largest is {rng:.3f}); every entry is in Table "
              f"e7v2_grid." if rng is not None else "")
    # (a)'s tags that ran fewer policy seeds than the table's (the grid table's seed_sets, from the runs)
    t = (d.get("tables") or {}).get("e7v2_grid") or {}
    few = {}
    for tag in A_TAGS:
        ss = (t.get("seed_sets") or {}).get(tag)
        if ss and ss != list(t.get("seeds") or ss):
            few.setdefault(", ".join(str(x) for x in ss), []).append(style.POLICIES[GRID_KEY[tag]].label)
    one = "".join(f"; {'; '.join(names)} ran policy seed{'s' if ',' in ss else ''} {ss} only"
                  for ss, names in few.items())
    return (f"Part grid, development-exposed (continuity, not a confirmation result). (a) The end-to-end week at "
            f"{n_al} alignment"
            f"{'s' if n_al != 1 else ''} under the trace lender: cost over all-fallback, the median over the policy "
            f"seeds with their range{one}.{hidden} (b), (c) The guard study's held-out cells of {len(insts)} instance"
            f"{'s' if len(insts) != 1 else ''}: the median cost under the trace lender and W0, the largest median over "
            f"the stress lenders; Greedy + one-way guard, Lagged RetroRenting + one-way guard and the lagged "
            f"RetroRenting-style rule from the guard study's summary (its cells). In every panel {LABELS['order']}. "
            f"Criterion S: W0 <= {1 + q['y_S']:g} on every instance.{s_text} Criterion T is {LABELS['T']} (the guard "
            f"study's own T for its rows is in Table e7v2_q44).")                                       # C59


def build(inp: Inputs) -> dict:
    s, e11 = inp.json(GRID), inp.json(E11)
    meta = need(s, "meta", what=GRID)
    runs = need(s, "runs", what=GRID)
    tags = tag_order(s)
    missing = [t for t in A_TAGS + Q_GRID_TAGS if t not in tags]
    if missing:
        raise MissingKey(f"{GRID}: meta.tags lacks {missing}")
    e11_tags = need(e11, "meta", "tags", what=E11)
    missing = [t for t in Q_E11_TAGS if t not in e11_tags]
    if missing:
        raise MissingKey(f"{E11}: meta.tags lacks {missing}")
    week = by_cell(runs, "week")
    als = alignments_of(week)
    stress_al = [c for c in als if any(m != TRACE for _, cc, m in week if cc == c)]
    e7_stress = [m for m in e7_stress_modes() if any(mm == m for _, _, mm in week)]
    gap_cells = sorted({str(r["cell"]) for r in runs if r.get("kind") == "gap"},
                       key=lambda c: (len(c), c))
    # (a) and the grid table
    rows = {}
    for tag in tags:
        rows[tag] = {"key": GRID_KEY[tag], "r0": {c: seed_point(week.get((tag, c, TRACE), {})) for c in als},
                     "stress": {c: {m: seed_point(week.get((tag, c, m), {})) for m in e7_stress} for c in stress_al},
                     "W0": {c: w0_at(s, tag, c) for c in stress_al}, "gap": gap_of(s, tag)}
    # the largest range over the policy seeds of any r0 entry of the grid table (the caption; seeds 1-2 in full)
    spread = [(p["hi"] - p["lo"], tag) for tag, r in rows.items()
              for p in list(r["r0"].values()) + [q for by in r["stress"].values() for q in by.values()]
              if p["n"] > 1]
    seed_range = {"max": max(spread)[0], "tag": max(spread)[1]} if spread else {"max": None, "tag": None}
    a = {"alignments": als, "series": {}}
    for tag in A_TAGS:
        ser = {"tag": tag, "median": [], "lo": [], "hi": [], "n": []}
        for c in als:
            p = rows[tag]["r0"][c]
            for f in ("median", "lo", "hi", "n"):
                ser[f].append(p[f])
        a["series"][GRID_KEY[tag]] = ser
    rngs = [hi_ - lo_ for ser in a["series"].values() for lo_, hi_ in zip(ser["lo"], ser["hi"])
            if lo_ is not None and hi_ is not None]
    a["max_range"] = max(rngs) if rngs else None
    # (b), (c) and the Q44 table
    qg = q44_grid(runs)
    insts = list(qg)
    qe = q44_e11(e11, insts)
    y_s = float(need(e11, "D4", "thresholds", "y_S", what=E11))
    x_t = float(need(e11, "D4", "thresholds", "x_T", what=E11))
    crit = need(e11, "D4", "criteria", what=E11)
    series = {}
    for tag in Q_GRID_TAGS:
        ser = {"tag": tag, "source": "grid", "r0_tr": [qg[i]["tags"][tag]["r0_tr"] for i in insts],
               "W0": [qg[i]["tags"][tag]["W0"] for i in insts], "W0_mode": [qg[i]["tags"][tag]["W0_mode"]
                                                                          for i in insts]}
        ser["S"] = criterion_s(ser["W0"], y_s)
        series[GRID_KEY[tag]] = ser
    for tag in Q_E11_TAGS:
        ser = {"tag": tag, "source": "e11", "r0_tr": [qe[i]["tags"][tag]["r0_tr"] for i in insts],
               "W0": [qe[i]["tags"][tag]["W0"] for i in insts], "W0_mode": [qe[i]["tags"][tag]["W0_mode"]
                                                                          for i in insts]}
        ser["S"] = criterion_s(ser["W0"], y_s)
        ser["T_e11"] = need(crit, tag, what=f"{E11} D4.criteria").get("T")     # E11's own (its cells, baselines)
        series[E11_KEY[tag]] = ser
    q = {"instances": insts, "y_S": y_s, "x_T": x_t, "series": series,
         "grid_cells": {i: qg[i]["cells"] for i in insts}, "grid_modes": {i: qg[i]["modes"] for i in insts},
         "grid_stress_modes": {i: qg[i]["stress_modes"] for i in insts},
         "grid_by_mode": {i: {t: qg[i]["tags"][t]["by_mode"] for t in Q_GRID_TAGS} for i in insts},
         "e11_cells": {i: qe[i]["cells"] for i in insts}, "e11_stress_modes": {i: qe[i]["stress_modes"]
                                                                              for i in insts},
         "criterion_T": LABELS["T"]}
    seeds = sorted({int(r["seed"]) for r in runs if r.get("kind") in ("week", "gap")})
    grid_t = {"file": TABLES[0], "tags": tags, "rows": rows, "alignments": als, "stress_alignments": stress_al,
              "stress_modes": e7_stress, "seeds": seeds, "seed_range": seed_range,
              "seed_sets": seed_sets(runs, tags), "aborts": {t: aborts_of(runs, t) for t in tags},
              "gap_days": sorted({d for t in tags for d in rows[t]["gap"]["by_day"]}),
              "scope": {"tags": tags, "alignments": als, "stress_alignments": stress_al, "gap_cells": gap_cells,
                        "cells": als + gap_cells, "seeds": seeds,
                        "modes": sorted({str(r["mode"]) for r in runs if r.get("kind") in ("week", "gap")})}}
    q44_t = {"file": TABLES[1], "scope": {"tags": list(Q_GRID_TAGS), "e11_tags": list(Q_E11_TAGS),
                                          "instances": insts, "cells": {i: qg[i]["cells"] for i in insts}}}
    d = {"a": a, "q44": q, "labels": dict(LABELS),
         "meta": {"git_revision": {"grid": meta.get("git_revision"),
                                   "e11": (e11.get("meta") or {}).get("git_revision")},
                  "reduced": bool(meta.get("reduced")), "sources": list(inp.sources), "runs_files": []},
         "tables": {"e7v2_grid": grid_t, "e7v2_q44": q44_t}}
    d["labels"]["caption"] = caption(d)
    return d


# ---------------------------------------------------------------------------------------------------------------
# figure
def y_ticks(lo: float, hi: float) -> list[float]:
    """Evenly stepped ticks over [lo, hi]: the smallest step of Y_STEPS with at most six ticks in range."""
    for step in Y_STEPS:
        t = [k * step for k in range(int(np.ceil(lo / step - 1e-9)), int(np.floor(hi / step + 1e-9)) + 1)]
        if len(t) <= 6:
            return [round(v, 10) for v in t]
    return [lo, hi]


def draw_points(ax, slots: Sequence[str], series: Mapping, field: str, lo: str | None = None,
                hi: str | None = None) -> list[float]:
    """Markers at the categories 0..n-1 dodged into `slots` (drawn in reverse slot order, Sublet last), with bars from
    `lo` to `hi` where given; returns the values drawn."""
    n = len(slots)
    vals = []
    for key in reversed(slots):
        s = series[key]
        y = finite(s[field])
        x = np.arange(len(y), dtype=float) + DODGE * (slots.index(key) - (n - 1) / 2)
        if lo is not None:
            l, h = finite(s[lo]), finite(s[hi])
            ok = np.isfinite(y) & np.isfinite(l) & np.isfinite(h) & (h > l)
            if ok.any():
                style.errorbars(ax, key, x[ok], y[ok], l[ok], h[ok])
            vals += [v for v in np.concatenate([l, h]) if np.isfinite(v)]
        style.scatter_policy(ax, key, x, y)
        vals += [v for v in y if np.isfinite(v)]
    return vals


def _title_blocker(ax):
    """An invisible segment (display coordinates, no width) TITLE_CLEAR_PT below the axes top, which
    common.free_spot reads as drawn, so that a label placed on the panel's free space stays clear of the panel title
    on the letter's baseline just above the axes (free_spot sees only the axes' own artists). The caller removes it."""
    from matplotlib.collections import LineCollection
    from matplotlib.transforms import IdentityTransform
    bb = ax.get_window_extent(ax.figure.canvas.get_renderer())
    y = bb.y1 - TITLE_CLEAR_PT * ax.figure.dpi / 72.0
    lc = LineCollection([[(bb.x0, y), (bb.x1, y)]], colors="none", linewidths=0.0, transform=IdentityTransform())
    ax.add_collection(lc, autolim=False)
    return lc


def category_axis(ax, labels: Sequence[str], xlabel: str) -> None:
    ax.set_xticks(list(range(len(labels))), list(labels))
    ax.set_xlim(-0.5, len(labels) - 0.5)
    ax.tick_params(axis="x", length=0)
    ax.set_xlabel(xlabel)


def draw(data: Mapping) -> Any:
    lab = data["labels"]
    fig = style.new_figure(NAME)
    ax_a, ax_b, ax_c = style.panel_row(fig, (1, 1, 1), legend=2, sharey=(False, True, True))
    a, q = data["a"], data["q44"]
    vals = draw_points(ax_a, A_SLOTS, a["series"], "median", "lo", "hi")
    vals += draw_points(ax_b, Q_SLOTS, q["series"], "r0_tr")
    vals += draw_points(ax_c, Q_SLOTS, q["series"], "W0")
    thr = 1.0 + float(q["y_S"])
    lo, hi = min(vals + [1.0]), max(vals + [thr])
    pad = 0.06 * (hi - lo)
    ax_a.set_ylim(lo - pad, hi + pad)
    ax_a.set_yticks(y_ticks(lo - pad, hi + pad))
    ax_a.yaxis.set_major_formatter(style.PLAIN)
    ax_a.set_ylabel(lab["y"])
    category_axis(ax_a, [str(c) for c in a["alignments"]], lab["a_x"])
    category_axis(ax_b, q["instances"], lab["b_x"])
    category_axis(ax_c, q["instances"], lab["c_x"])
    for ax in (ax_a, ax_b, ax_c):
        style.reference_line(ax, y=1.0)
    style.reference_line(ax_c, y=thr, linestyle=THRESHOLD_DASH)
    # criterion S's label on the free space nearest to its line and nearer to it than to the level 1
    # (common.free_spot); where none is free, the shared y axis is raised by LABEL_RAISE of its range at a time
    xs = np.linspace(-0.5, len(q["instances"]) - 0.5, 50)
    for _ in range(MAX_RAISE + 1):
        blocker = _title_blocker(ax_c)
        t = place_label(ax_c, lab["threshold"].format(v=thr), points_pt(ax_c, xs, np.full_like(xs, thr)),
                        others=points_pt(ax_c, xs, np.ones_like(xs)), color=style.THEORY_LABEL_GREY)
        blocker.remove()
        if t is not None:
            break
        y0, y1 = ax_a.get_ylim()
        ax_a.set_ylim(y0, y1 + LABEL_RAISE * (y1 - y0))
    else:
        raise style.StyleError(f"{NAME} (c): the label of criterion S's threshold fits nowhere")
    drop_idle_halos(ax_c, [t])                     # text in the PDF where its halo would mask nothing
    letters = style.panel_letters([ax_a, ax_b, ax_c])
    for ax, letter, p in zip((ax_a, ax_b, ax_c), letters, ("a", "b", "c")):
        caption_title(ax, letter, lab["titles"][p])
    with matplotlib.rc_context({"legend.handlelength": LEGEND_HANDLE}):
        style.legend_row(fig, KEYS, rows=2, lines=False)
    return fig


# ---------------------------------------------------------------------------------------------------------------
# tables
GRID_NAME_COL = "5.6cm"         # e7v2_grid.tex's policy column (wrapped; needs the array package)


NUM_WORDS = {2: "Two", 3: "Three", 4: "Four", 5: "Five", 6: "Six", 7: "Seven", 8: "Eight", 9: "Nine", 10: "Ten"}


def seeds_text(t: Mapping, name: Mapping) -> str:
    """The tags that ran other policy seeds than the table's (seed_sets), and those whose seeds give equal values in
    every r0 entry, read from the extract; names separated by semicolons (labels may hold commas)."""
    full = list(t["seeds"])
    by: dict = {}
    for tag in t["tags"]:
        ss = (t.get("seed_sets") or {}).get(tag)
        if ss and ss != full:
            by.setdefault(tuple(ss), []).append(tag)
    out = ""
    for ss, tags in by.items():
        seeds = r"policy seed" + ("s " if len(ss) != 1 else " ") + ", ".join(str(x) for x in ss)
        n = NUM_WORDS.get(len(tags), str(len(tags)))
        out += (f" {n} tags ran {seeds} only: " + "; ".join(name[x] for x in tags) + "." if len(tags) > 1
                else f" {name[tags[0]]} ran {seeds} only.")
    same = [tag for tag in t["tags"] if all(p["n"] > 1 and p["hi"] == p["lo"] for p in
                                             list(t["rows"][tag]["r0"].values())
                                             + [q for by_ in t["rows"][tag]["stress"].values() for q in by_.values()])]
    if same:
        out += " Equal over the policy seeds in every entry: " + "; ".join(name[x] for x in same) + "."
    return out


def aborts_text(t: Mapping, name: Mapping, cells: Mapping) -> str:
    """The tags whose guard aborts in every grid run, with the commonest abort slot and what follows the abort (the
    safe expert on all-fallback, s_fb_all; then, where every entry of the row reads 1.000, that this is why)."""
    out = ""
    for tag in t["tags"]:
        a = (t.get("aborts") or {}).get(tag) or {}
        if not a.get("runs") or a.get("aborted") != a.get("runs"):
            continue
        slot, k = next(iter(a["t_a"].items()))
        follows = ""
        if a.get("s_fb_all"):
            ones = [c for c in cells[tag][:-1] if c != "--"]          # r0 and W0 (not the gap days' ALG/LB)
            follows = r" and then follows all-fallback" + (r", hence its $r_0$ and $W_0$ entries of 1.000"
                                                            if ones and all(c == "1.000" for c in ones) else "")
        out += (" " + name[tag] + r" aborts in every one of its " + str(a["runs"]) + r" grid runs (at slot " + slot
                + " in " + str(k) + ")" + follows + ".")
    return out


def grid_tex(t: Mapping, dev: str) -> str:
    als, st, sm = t["alignments"], t["stress_alignments"], t["stress_modes"]
    n_st = len(sm) + 1                                     # per stress alignment: its modes and W0
    cols = r"@{}>{\raggedright\arraybackslash}p{" + GRID_NAME_COL + "}" + "r" * (len(als) + n_st * len(st) + 1) \
        + "@{}"
    head1 = (r" & \multicolumn{" + str(len(als)) + r"}{c}{$r_0$, trace lender, alignment}"
             + "".join(r" & \multicolumn{" + str(n_st) + r"}{c}{Alignment " + c + r", stress lenders}" for c in st)
             + r" & Gap days \\")
    first = 2 + len(als)
    rule = r"\cmidrule(lr){2-" + str(first - 1) + "}" + "".join(
        r"\cmidrule(lr){" + f"{first + k * n_st}-{first + (k + 1) * n_st - 1}" + "}" for k in range(len(st)))
    head2 = (r"Policy & " + " & ".join(als) + "".join(" & " + " & ".join(MODE_TEX.get(m, _tex_text(m)) for m in sm)
                                                      + r" & $W_0$" for _ in st) + r" & ALG/LB \\")
    sr = t.get("seed_range") or {}
    spread = (r" The largest range over the policy seeds of any $r_0$ entry is " + tex_f(sr["max"])
              + r" (" + tex_label(style.POLICIES[GRID_KEY[sr["tag"]]].label) + r").") \
        if sr.get("max") is not None else ""
    name = {tag: tex_label(style.POLICIES[t["rows"][tag]["key"]].label) for tag in t["tags"]}
    seeds = ", ".join(str(x) for x in t["seeds"])
    body, row_cells = [], {}
    for tag in t["tags"]:
        r = t["rows"][tag]
        cells = [tex_f(r["r0"][c]["median"]) for c in als]
        for c in st:
            cells += [tex_f(r["stress"][c][m]["median"]) for m in sm] + [tex_f(r["W0"][c]["median"])]
        cells.append(tex_f(r["gap"]["median"]))
        row_cells[tag] = cells
        body.append(f"{name[tag]} & " + " & ".join(cells) + r" \\")
    dashes = any(c == "--" for cells in row_cells.values() for c in cells)
    lines = [r"\begin{table*}[t]",
             r"\caption{Part grid, " + dev + r" (continuity, not a confirmation result): every tag's cost over "
             r"all-fallback $r_0$ under the trace lender at E7's alignments " + ", ".join(als) + r", under each "
             r"stress lender at alignment" + ("s " if len(st) != 1 else " ") + ", ".join(st) + r", the one"
             + ("s" if len(st) != 1 else "") + r" with stress runs, with $W_0$, the largest of them (each the median "
             r"over the policy seeds " + seeds + r"), and the gap days' cost over the merged LP bound (slow grid, "
             r"reduced menu; the median over the " + str(len(t["gap_days"])) + r" days of the median over the "
             r"seeds)."                                                    # C50: "reduced menu" for e7r (D5 review)
             + seeds_text(t, name) + aborts_text(t, name, row_cells)
             + (r" A dash marks a cell without runs." if dashes else "")
             + spread + "}",
             r"\label{tab:e7v2-grid}", r"\centering\footnotesize", r"\setlength{\tabcolsep}{3.4pt}",
             r"\begin{tabular}{" + cols + "}", r"\toprule", head1, rule, head2, r"\midrule"]
    lines += body + [r"\bottomrule", r"\end{tabular}", r"\end{table*}", ""]
    return "\n".join(lines)


def _s_text(v) -> str:
    return "--" if v is None else ("holds" if v else "fails")


MODE_TEX = {"L-eg": "eager", "L-ss": "safe-site", "L-co": "correlated", "L-iid-0.05": r"i.i.d.\ 0.05",
            "L-iid-0.2": r"i.i.d.\ 0.2"}


def q44_tex(q: Mapping, dev: str) -> str:
    insts = q["instances"]
    cols = r"@{}>{\raggedright\arraybackslash}p{4.8cm}l" + "rr" * len(insts) + "ll@{}"
    head1 = "Policy & Source & " + " & ".join(r"\multicolumn{2}{c}{" + i + "}" for i in insts) + r" & S & T \\"
    rule = "".join(r"\cmidrule(lr){" + f"{3 + 2 * k}-{4 + 2 * k}" + "}" for k in range(len(insts)))
    head2 = " &  & " + " & ".join(r"$r_0$ & $W_0$" for _ in insts) + r" &  &  \\"
    why = q["criterion_T"].partition(": ")[2] or q["criterion_T"]
    gcells = "; ".join(f"{i} {len(q['grid_cells'][i])}" for i in insts)
    ecells = "; ".join(f"{i} {q['e11_cells'][i]}" for i in insts)
    lines = [r"\begin{table*}[t]",
             # C59 (RC19(3)): the guard study by its name (as built "Q44" and "E11")
             r"\caption{The guard study's held-out cells, " + dev + r": per policy and instance the median cost over "
             r"all-fallback under the trace lender ($r_0$) and $W_0$, the largest median over the instance's stress "
             r"lenders (the guard study's definitions; the lender that sets $W_0$ on the line below), and criterion "
             r"S ($W_0\leq"
             + f"{1 + q['y_S']:g}" + r"$ on every instance). Part grid's cells per instance: " + gcells
             + r"; the guard study's rows are its medians over its own held-out cells (" + ecells + r"), set beside "
             r"them, not paired. Criterion T is not computable for part grid's rows (a dash): "
             + _tex_text(why).replace("(BL1, BL2, BL5)", "(greedy renting, per-borrower ski rental and RetroRenting-style)")
             + r"; for the guard study's rows its column gives the guard study's own verdict over its cells, "
             r"$D_1\leq"
             + f"{1 + q['x_T']:g}" + r"$ on at least three of the instances, $D_1$ the cost over the best of these three.}",
             r"\label{tab:e7v2-q44}", r"\centering\footnotesize", r"\setlength{\tabcolsep}{3.4pt}",
             r"\begin{tabular}{" + cols + "}", r"\toprule", head1, rule, head2, r"\midrule"]
    for key, s in q["series"].items():
        src = "part grid" if s["source"] == "grid" else "guard study"                                # C59
        vals = " & ".join(f"{tex_f(r)} & {tex_f(w)}" for r, w in zip(s["r0_tr"], s["W0"]))
        modes = []
        for m in s["W0_mode"]:
            modes += ["", MODE_TEX.get(m, "--" if m is None else _tex_text(m))]
        t_cell = _s_text(s.get("T_e11")) if s["source"] == "e11" else "--"
        lines.append(f"{tex_label(style.POLICIES[key].label)} & {src} & {vals} & {_s_text(s['S'])} & {t_cell} \\\\")
        lines.append(" &  & " + " & ".join(modes) + r" &  &  \\")
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table*}", ""]
    return "\n".join(lines)


def write_tables(data: Mapping, report: Mapping) -> None:
    t = data["tables"]
    dev = data["labels"]["dev"]
    head = f"% Written by code/sim/figs/supp/{NAME}.py from {GRID} and {E11}; do not edit.\n"
    paths = [write_table(TABLES[0], head + grid_tex(t["e7v2_grid"], dev)),
             write_table(TABLES[1], head + q44_tex(data["q44"], dev))]
    print(f"[{NAME}] wrote {', '.join(str(p) for p in paths)}")


def main(argv: Sequence[str] | None = None) -> dict:
    return cli(NAME, build, draw, argv, supplementary=True, after=write_tables, doc=__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
