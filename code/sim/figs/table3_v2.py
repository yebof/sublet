"""Table III v2: E7 on the confirmation weeks per policy (design/sublet_v2.md §11, W2, W6, W9, W10), the float
paper/floats/table3_v2.tex (label tab:e7) and its extract code/sim/out/figs/table3_v2.json.

The paper's Table III (W6; the frozen table3_e7.tex of MS4 stays as it is). Inputs, through figs.inputs (so that
SUBLET_FIGS_IN_ROOT redirects them): the versioned summaries code/sim/out/sublet_v2/main/summary.json and
second/summary.json, analysis.json, second's merged gap LP files lb/gap_lp_c<c>.json, and (W10) the unversioned run
files that alone hold the total accounting, the references BL0a total and BL0b and the week instance's mu/beta-tilde:
main/runs/<job>.json of every row's L-tr week job and second/runs/<job>.json of the first row tag's gap jobs. Every
run file read is listed in the extract with its sha256 (runs_sha256); every other number comes from the summaries
(overflow USD is r0 x bl0a_usd, W10). Weeks, gap days, seeds, modes, tags of H1's and H2b's sets and every count are
read from the inputs, never fixed here (the reduced fixtures have other ones).

Rows (W2), in this order, each named by its style.POLICIES label (MS5b registry, C41; never a legacy key): Sublet,
Sublet one-way, BL1-GP, BL1N, BL5N, BL1, BL1-BO, BL5-cur, BL5-tau60, BL2, BL3-0, BL4, A6, BL0a (ROWS: tag and key).
Columns, each the median over the weeks of main's week runs under L-tr at main's one policy seed, computed with the
registered week bootstrap (ms5b_common.bootstrap_median_ci, seed 20261031, 10,000 resamples; W9), whose 95% interval
and per-week values go to the extract only (the supplement prints them, W2):
  1. USD per week in thousands, one decimal, overflow (r0 x bl0a_usd) with the total accounting (runs/: accountings
     of the L-tr run, total_usd) in parentheses; BL0a: its bl0a_usd, and its total bl0a_total_usd from the
     references of the same run files;
  2. saving over BL0a in percent, overflow accounting, 100 (1 - r0), one decimal (none above 100 in magnitude);
  3. ALG/LB on the gap days of part second (one day of each of its gap cells; the merged LP bound, as in MS4), the
     summary's gap_ratio at the gap rows' seed, two decimals; BL0a: the gap rows' bl0a_usd over gap_lp (one value per
     cell, the same in every row of the cell); "--" for a tag with no gap run (BL2, A6 and Sublet one-way);
  4. RC under L-tr (main.RC, r0 under L-tr minus r0 under L-hon, §4.5; D6), three decimals, since its values are
     mostly below 0.03 BL0a; "--" for BL0a, which has no runs;
  5. W0 (main.W0, the largest r0 over the five stress modes), three decimals (as built, so that a median just below
     1, A6's, does not print as 1.00 beside BL1-GP's 1.009); BL0a: the largest ratio of its bl0a_usd under a stress
     mode to its bl0a_usd under L-tr in the main rows of the week (1 by definition; MS4 printed 1.00 too);
  6. p*, from analysis.json reported.intensity_curves (main's and second's curves merged, prereg B8) on the weeks of
     second's week runs: per week the first iid reclaim probability p with r0 > 1 (first_p_above_1), else none; the
     cell is the lower median over those weeks (the ceil(n/2)-th smallest value, none counted as above every p; as
     built: W2 says "the median", and with four weeks the mean of the middle two would print 0.65 for BL4 (weeks at
     0.34, 0.5, 0.8, 0.8) and "none" for BL1N, which crosses in two of the four weeks, so the lower median is used,
     a grid point and never more favorable than half of the weeks), two decimals; "none" if that value is none and
     every week's curve reaches the grid's largest p, else "$>$p_max" with p_max the largest p of the tag's curves
     (BL2, A6 and Sublet one-way ran only p in {0, 0.05, 0.2}: their "none" reads "not reached at p <= 0.2", W2);
     "--" for BL0a.
A null or missing value raises MissingKey (no partial median); a cell printed "--" has its reason in notes. Layout
(as built; NAME_COL_W, TABLE_ENV): the names wrap in a ragged-right column with a hanging indent (W2 allows a wrapped
name column; two names wrap), in a tabular* of \\columnwidth whose slack goes between the number columns; the float
compiles without an overfull box (tests/test_floats_ms5b.py), and floats_heights.py --ms5b measures it against
BUDGETS_MS5B (C43; informative, W11's FL-1).

Caption (W2; every number read from the inputs). As built, it is split: the float's \\caption (small capitals in the
class) is the scope, and a note in roman below the table holds the rest (in small capitals the whole text took 16 lines
of the column); labels.caption is the two in one text, the caption draft that the claims report reads. The scope: what
the table is ("E7 per policy"; print check of U38), the confirmation weeks, the lender (the schedule of the L-tr lender
model in the run files read for the references, 'trace'), the full menu (text: no output records the menu's name; as
MS4's table3.json scope), mu/beta-tilde from the gap run files' week_overrides (the E7 week instance whose first day
each gap rerun takes; the only output that records it), the policy seed. The note: ALG/LB's gap days, horizon, grid (the
LP files' grid) and menu ("reduced", text: MS4 printed the base name e7r, an experiment-derived name that M17 keeps
out of the main text; sf_e9.TABLE_MENU names it so too); p*'s readings (where a row's p* is 0, "0.00: r0 > 1 already
without reclaims", p = 0 being L-hon; print check of U38: "p = 0: no reclaim" did not say what A6's 0.00 means); the
guarded rows' allowance min{W_k, LB'} with kappa None (prereg B5; read from the guarded rows' B0_rule, which must be the
'lb' rule); the certificate: Theorem W's envelope held in every guarded run of part main (guard_summary's held and
n_runs over all its lender modes, the cases counted over main.guarded), naming the guarded runs of tags without a row
here (Sublet-MS4, the legacy one-way guard at B0 = 10% BL0a, in the supplement) with their count, since the count is not
over the rows shown alone (as built); G3(b) at this allowance rests on Corollary G3' and is not checked per run (prereg
C3), stated for the guarded rows around A9 only (main's meta.tags a9_family: Sublet and Sublet one-way), since
design/sublet_v2.md §2.6 claims G3(b) for those and Table II v2 gives BL1-GP none (as built); the aborts of each guarded
row over its runs in main (every mode; Sublet one-way's 42 of 112 are the evidence for projection, beside Sublet's
none), and for a guarded row with aborts under L-tr (main.guarded, mode L-tr; _trace_aborts) the weeks,
its r0 there and its distance to Sublet's r0 in the other weeks, so that the reader sees that its medians mix two modes
(print check of U38: Sublet one-way's median USD, 25.3k, is 72% of All-fallback's while its median saving is 44.5%,
since it aborts at slots 0-22 in 6 of the 16 weeks and equals Sublet in the other 10, and the median of each column
falls in other weeks); H1's set (analysis.json H2.set, the set H2 compares with, which is H1's by §6), named by labels
in the rows' order, with the lagged BL5, which has no row here, pointed to the supplement; BL0b's median ratio to
BL0a in overflow accounting (runs/ references; in total accounting the ratio is about eight times smaller, so the note
names the accounting). It says "H1's set", never "every baseline" (W11, C-H2b), and states no H1 or H2 count (Fig. 4
v2's caption carries H1's margin).

MS6 (design/ms6_spec.md M7, M17; unit U45): the caption names results by \\ref to the paper's labels of
design/ms6_spec.md §5 and no experiment ID. The title says what the table is, "End-to-end cost per policy, medians of
16 confirmation weeks (...)" (M17: no "E7"; as built, "medians of 16", not "medians over the 16", keeps the class's
small capitals on two lines); the note writes Theorem~\\ref{thm:fullmodel}'s envelope for Theorem W's, its cases (a)
and (b) for W(a) and W(b), and W(c), a conjecture after the theorem in the paper, as "the conjectured case" and only
where it has runs (cases_text; U46, second review; the counts are still read from main.guarded's cases), "the ratio
bound at this allowance rests on Corollary~\\ref{cor:ratio}" for "G3(b) at this allowance rests on Corollary G3'" (G3(b) and
G3'(b') are one corollary, M14), and the MS4 configuration's allowance as "($B_0$ = 10\\% of All-fallback)" where its
registry label (sublet_ms4, C41, unchanged) writes "($B_0=10\\%$ BL0a)" (note_label). W2's content is unchanged. The
label stub paper/generated/labels_stub.tex gives the numbers for the height measurement (floats_heights.py --ms5b).

C50 (design/ms6_spec.md §7.2, the D5 review; with D4's as-built list of script items, §7.1 D4): the note uses Section
VII's words. ALG/LB is the first day of the gap weeks with "5-min routing" (grid_text: the routing interval of the bench
grid in q44_study.GRIDS, for "slow grid"), "over the LP bound" (the LB of the setup; "merged" is a solver detail), "an
upper bound on the ratio to the offline optimum" (for "the gap"); the certificate's lender modes are "trace, five
stress and honoring lenders" (modes_text, for "all 7 lender modes"); and "Corollary~\\ref{cor:ratio}(b) holds for
Sublet and Sublet, one-way, on core instances only" for "the ratio bound at this allowance rests on Corollary
\\ref{cor:ratio} ..., not checked per run", since the corollary holds on the network core and reaches Sublet only on
core instances (statements review S2: no ratio is claimed for the week runs, which is what prereg C3's "not checked per
run" said; the shorter text keeps the note's height, measured with floats_heights.py --ms5b in a scratch folder; part
(b) is the one at Sublet's allowance, COR_PART_LB, as Table II v2 cites it). --from-extract recomputes the caption, the note and labels.caption from caption_source, so
that the versioned float and extract follow a wording change without the unversioned run files.

C51: no H2b sentence
(Section VII's "Pre-registered outcomes" reports H2b once; caption_source keeps its numbers); a guarded row's aborts
under L-tr give only what its medians need, its weeks at the all-fallback bill and the rest at Sublet's cost (no
slots); Corollary~\\ref{cor:ratio}(b)'s scope reads "on core instances (Lemma~\\ref{lem:projection}(e))".

C52 (design/ms7/plan.md §4, unit T1: the manuscript scan and the glossary of T1): the title drops the policy seed (run
configuration; the week labels stay, since Fig. 4(b) prints them); the note names the guarded rows' allowance "the
per-group allowance" and writes its cap with the paper's macro \\Wk (B_peak; \\providecommand gives it when the float
is compiled alone) and without "kappa none" (the code's kappa=None, which a reader cannot use), writes "Theorem
\\ref{thm:fullmodel}'s bound held" (the certificate checks the bounds of parts (a) and (b), not Theorem
\\ref{thm:envelope}'s envelope), names the configuration whose runs the count includes as the main text does,
"Lagged RetroRenting + one-way guard ($B_0$ = 10% of the all-fallback bill)" (note_label with FB_BILL; no "the
supplement's"), and lists the policies of H1 after "Primary baselines (H1):" (Section VII-C's "the primary
baselines", which it defines as the policies this note lists), for "H1's set:".

The extract (format of table3_e7's: {"table", "sources", "data"}) holds every printed cell with its value, interval,
per-week values and note, the caption, the note and their numbers (caption_source), labels.caption, meta {git_revision,
reduced (any summary's meta.reduced), sources (the summaries and analysis.json)}, runs_sha256 and the tables block
{"table3_v2.tex": {"scope": {tags, keys, cells, gap_cells, p_star_cells, modes, seeds}}}; --from-extract rewrites
the float from it alone. The float goes to --out DIR, else SUBLET_FIGS_PDF_DIR when it is set (a scratch build or a
test never writes into paper/; as built, so that tests/fixtures_figs_ms5b/refresh_extracts.py, which runs main([])
with the figure folders redirected, works), else paper/floats/; input from a reduced run (meta.reduced) is never
written into paper/floats/.

Run from code/sim: python -m figs.table3_v2 [--out DIR] [--from-extract [JSON]].
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sys
from pathlib import Path
from typing import Mapping, Sequence

from figs import style
from figs.common import MissingKey, need
from figs.inputs import Inputs
from sublet.experiments import ms5b_common as m5b          # read-only: the registered bootstrap and mode names
from sublet.experiments.ms3_common import job_file_name
from sublet.experiments.q44_study import GRIDS as BENCH_GRIDS   # C50: read-only, the routing interval of a bench grid

NAME = "table3_v2"
CONF = "code/sim/out/sublet_v2"
MAIN = f"{CONF}/main/summary.json"
SECOND = f"{CONF}/second/summary.json"
ANALYSIS = f"{CONF}/analysis.json"
FLOATS_DIR = style.REPO / "paper" / "floats"
DASH = "--"                     # a null cell: an en dash in LaTeX
# W2's rows in order: (tag of the confirmation, MS5b registry key); BL0a is the analytic reference
ROWS = (("Sublet", "sublet_v2"), ("Sublet-1way", "sublet_1way"), ("BL1-GP", "bl1_gp"), ("BL1N", "bl1n"),
        ("BL5N", "bl5n"), ("BL1", "bl1"), ("BL1-BO", "bl1_bo"), ("BL5-cur", "bl5_cur"), ("BL5-tau60", "bl5_tau60"),
        ("BL2", "bl2"), ("BL3-0", "bl3_0"), ("BL4", "bl4"), ("A6", "a6"), ("BL0a", "bl0a"))
REFERENCE = "BL0a"
HEADLINE = "Sublet"
# tags that the caption names without a row here, with their registry keys: the lagged BL5 of H1's set (D7) and the
# legacy guarded row Sublet-MS4, whose runs the certificate count of part main includes (W2)
CAPTION_ONLY = {"BL5": "bl5_lag", "Sublet-MS4": "sublet_ms4"}
BL0B_KEY = "bl0b"
# (column, decimals): USD in thousands, saving, gap, RC, W0, p*
COLUMNS = (("usd", 1), ("saving_pct", 1), ("gap", 2), ("RC", 3), ("W0", 3), ("p_star", 2))
HEADER = (("", "Policy"), ("USD/week (k)", "overflow (total)"), ("Saving", r"(\%)"), ("ALG/", "LB"), ("", "RC"),
          ("", "$W_0$"), ("", r"$p^\ast$"))
# the names in a ragged-right column of NAME_COL_W with a hanging indent (W2: a wrapped name column), the numbers
# right-aligned (USD, saving) or centered (the columns of one width); a tabular* of \columnwidth whose slack goes
# between the columns (\extracolsep{\fill}) on top of at least 4 pt. At \footnotesize the six number columns of
# real-scale cells take 144 pt with their headers, so NAME_COL_W (76 pt) leaves about 5.4 pt between the columns and
# holds every name but "RetroRenting + notice layer" and "SpotHedge-style, N_Extra = 0" on one line (natural widths
# measured with the class: 72-75 pt for "Greedy + notice layer", "Per-borrower ski rental" and "RetroRenting,
# tau >= 1 h"; as built, a first layout with 3.5 pt between the columns and a 66-pt name column wrapped five names and
# ran the RC, W0 and p* columns together). tests/test_floats_ms5b.py compiles it without an overfull box.
NAME_COL_W = r"0.302\columnwidth"
TABLE_ENV = (r"\setlength{\tabcolsep}{2pt}" "\n"
             r"\begin{tabular*}{\columnwidth}{@{\extracolsep{\fill}}"
             r">{\raggedright\arraybackslash\hangindent=0.6em\hangafter=1}p{" + NAME_COL_W + r"}rrcccc@{}}")
TABLE_END = r"\end{tabular*}"
LB_RULE = "lb: min{W_k(t), LB'(t)}, kappa None"            # the guarded rows' B0_rule at Sublet's allowance
# C52 (design/ms7/plan.md §4, T1 glossary G5, G6): Section VI's name of Sublet's allowance, its cap by the paper's macro
# \Wk (B_peak, design W_k), no "kappa none" (the code's kappa=None; the allowance has no kappa)
LB_RULE_TEX = r"per-group allowance $\min\{\Wk,\mathrm{LB}'\}$"                                           # C52
# C52: the definition of \Wk that paper/macros.tex gives, for the float compiled alone (floats_heights.py, the tests);
# \providecommand does nothing in the paper, as in paper/floats/alg1_guard_v2.tex
WK_MACRO = r"\providecommand{\Wk}{B_{\mathrm{peak}}}%"                                                    # C52
PRIMARY = "Primary baselines (H1)"     # C52 (T1 glossary G3): Section VII-C's name of H1's comparison set
# C50 (D5 review): the part of Corollary \ref{cor:ratio} at Sublet's allowance B <= LB' (the guarded rows' rule LB_RULE;
# Table II v2 cites it so); the note says that it holds on core instances, so no ratio is claimed for these runs
COR_PART_LB = "(b)"
# MS6, print check of the gate (U46; design/ms6_spec.md M11): a normalized cost is written "of the all-fallback bill",
# so the note's ratios to BL0a read "times the all-fallback bill" (not "times All-fallback", which reads as a policy);
# the MS4 configuration's allowance keeps M7's words, "($B_0$ = 10% of All-fallback)" (note_label)
FB_BILL = "the all-fallback bill"
HORIZON_WORDS = {10080: "week", 1440: "day"}
WD_TOL = 1e-9                   # relative: BL0a's USD equal in every row of a week and mode, or of a gap cell


def tex_value(v: float | None, d: int) -> str:
    """A number with d decimals, a negative sign as a math minus; DASH for a missing value."""
    if v is None:
        return DASH
    s = f"{float(v):.{d}f}"
    if float(s) == 0.0:
        s = s.lstrip("-")                                # no "-0.0"
    return "$-$" + s[1:] if s.startswith("-") else s


def tex_p(p: float) -> str:
    """A grid value of p in a caption ('0.2', '1')."""
    return f"{float(p):g}"


def _num(cell: str) -> float:
    try:
        return float(str(cell).split(":")[-1].lstrip("c"))
    except ValueError:
        return math.inf


def weeks_text(cells: Sequence[str], one: str = "week", many: str = "weeks") -> str:
    """'weeks 301--316' for a run of consecutive integer cells, 'week 101' for one, else the list."""
    ws = sorted(cells, key=_num)
    nums = [_num(c) for c in ws]
    if len(ws) == 1:
        return f"{one} {ws[0]}"
    if all(math.isfinite(x) and x.is_integer() for x in nums) and nums == list(
            range(int(nums[0]), int(nums[0]) + len(nums))):
        return f"{many} {int(nums[0])}--{int(nums[-1])}"
    return f"{many} " + ", ".join(ws)


def horizon_text(minutes) -> str:
    """'day' for 1440 min, 'week' for 10080, else '<h> min'."""
    h = float(minutes)
    return HORIZON_WORDS.get(int(h), f"{h:g} min") if h.is_integer() else f"{h:g} min"


def stat(values: Sequence[float]) -> dict:
    """The median with its week-bootstrap 95% interval (ms5b_common.bootstrap_median_ci, as registered)."""
    b = m5b.bootstrap_median_ci([float(v) for v in values])
    return {"median": b["median"], "ci": b["ci"], "n": b["n"], "B": b["B"], "seed": b["seed"]}


def lower_median(values: Sequence[float | None]) -> float | None:
    """The ceil(n/2)-th smallest value, None counted as above every value (None if it is the one)."""
    if not values:
        raise MissingKey(f"{NAME}: no value for a lower median")
    v = sorted(values, key=lambda x: math.inf if x is None else float(x))
    return v[(len(v) + 1) // 2 - 1]


# ---------------------------------------------------------------------------------------------------------------
# Reading the inputs
def _runs_of(summary: Mapping, what: str) -> list:
    rows = need(summary, "runs", what=what)
    if not isinstance(rows, list):
        raise MissingKey(f"{what}: runs is {type(rows).__name__}, not a list")
    return rows


def _rev_reduced(summaries: Mapping[str, Mapping]) -> tuple:
    revs = {p: (s.get("meta") or {}).get("git_revision") for p, s in summaries.items()}
    reduced = {p: bool((s.get("meta") or {}).get("reduced", False)) for p, s in summaries.items()}
    uniq = set(revs.values())
    return (uniq.pop() if len(uniq) == 1 else None), revs, any(reduced.values()), reduced


class RunFiles:
    """The run files read (W10): parsed through Inputs (so recorded as sources) with their sha256."""

    def __init__(self, inp: Inputs) -> None:
        self.inp = inp
        self.sha: dict[str, str] = {}
        self._cache: dict[str, dict] = {}

    def read(self, part: str, job: str) -> dict:
        rel = f"{CONF}/{part}/runs/{job_file_name(job)}"
        if rel not in self._cache:
            raw = self.inp.path(rel).read_bytes()
            self.sha[rel] = hashlib.sha256(raw).hexdigest()
            self._cache[rel] = json.loads(raw)
        return self._cache[rel]

    def run(self, part: str, job: str, mode: str, seed: int) -> dict:
        d = self.read(part, job)
        hits = [r for r in need(d, "runs", what=job)
                if r.get("mode") == mode and int(r.get("policy_seed", -1)) == seed]
        if len(hits) != 1:
            raise MissingKey(f"{part}/runs of {job}: {len(hits)} runs under {mode} at policy seed {seed}, not 1")
        return hits[0]


def _index(rows: list, kind: str) -> dict:
    """{(tag, mode, cell, seed): row} of the rows of one kind ('week', 'gap')."""
    out = {}
    for r in rows:
        if r.get("kind") != kind:
            continue
        key = (r["tag"], r["mode"], str(r["cell"]), int(r["seed"]))
        if key in out:
            raise MissingKey(f"two {kind} rows for {key}")
        out[key] = r
    return out


def _same(values: Sequence[float], what: str) -> float:
    v = [float(x) for x in values]
    if not v:
        raise MissingKey(f"{what}: no value")
    if max(v) - min(v) > WD_TOL * max(1.0, abs(v[0])):
        raise MissingKey(f"{what}: values differ ({min(v)!r} to {max(v)!r})")
    return v[0]


# ---------------------------------------------------------------------------------------------------------------
def _usd_cell(by_week_ovf: dict, by_week_tot: dict) -> dict:
    o, t = stat(list(by_week_ovf.values())), stat(list(by_week_tot.values()))
    text = tex_value(o["median"] * 1e-3, 1) + f" ({tex_value(t['median'] * 1e-3, 1)})"
    return {"text": text, "overflow": {**o, "by_cell": by_week_ovf}, "total": {**t, "by_cell": by_week_tot},
            "note": None}


def _value_cell(by_cell: dict, d: int, note: str | None = None) -> dict:
    s = stat(list(by_cell.values()))
    return {"text": tex_value(s["median"], d), "value": s["median"], "ci": s["ci"], "n": s["n"], "by_cell": by_cell,
            "note": note}


def _dash_cell(note: str) -> dict:
    return {"text": DASH, "value": None, "ci": [None, None], "n": 0, "by_cell": {}, "note": note}


def _p_star_cell(curves: Mapping, tag: str, weeks: Sequence[str], grid_top: float) -> dict:
    by_cell, top = {}, {}
    for w in weeks:
        c = need(curves, tag, w, what=f"{ANALYSIS} reported.intensity_curves")
        pts = [(float(p), r) for p, r in need(c, "points", what=f"{ANALYSIS} intensity curve {tag}.{w}")]
        measured = [p for p, r in pts if r is not None]
        if not measured:
            raise MissingKey(f"{ANALYSIS}: intensity curve {tag}.{w} has no point")
        top[w] = max(measured)
        first = c.get("first_p_above_1")
        if first is None:
            above = [p for p, r in pts if r is not None and float(r) > 1.0]
            if above:
                raise MissingKey(f"{ANALYSIS}: {tag}.{w} has r0 > 1 at p = {min(above)} but first_p_above_1 null")
        by_cell[w] = None if first is None else float(first)
    v = lower_median(list(by_cell.values()))
    reach = min(top.values())
    if v is not None:
        text, reading = tex_value(v, 2), None
    elif reach >= grid_top:
        text, reading = "none", "none"
    else:
        text, reading = "$>$" + tex_p(reach), f">{tex_p(reach)}"
    return {"text": text, "value": v, "by_cell": by_cell, "grid_max": top, "reading": reading,
            "note": None if v is not None else (f"r0 <= 1 at every p <= {tex_p(reach)} in at least half of the weeks")}


def build(inp: Inputs) -> dict:
    main, second, ana = inp.json(MAIN), inp.json(SECOND), inp.json(ANALYSIS)
    rev, revs, reduced, reduced_by = _rev_reduced({"main": main, "second": second})
    trace, hon, stress = m5b.TRACE_MODE, m5b.HON_MODE, tuple(m5b.stress_modes())
    week_rows = _index(_runs_of(main, MAIN), "week")
    seeds = sorted({k[3] for k in week_rows})
    if len(seeds) != 1:
        raise MissingKey(f"{MAIN}: the week runs have policy seeds {seeds}, not one")
    seed = seeds[0]
    weeks = sorted({k[2] for k in week_rows if k[1] == trace}, key=_num)
    if not weeks:
        raise MissingKey(f"{MAIN}: no week run under {trace}")
    tags = [t for t, _ in ROWS]
    keys = {t: k for t, k in ROWS}
    for t, k in ROWS:
        style.policy(k)                                   # a registry key (KeyError otherwise)
    runs = RunFiles(inp)
    W0 = need(main, "W0", str(seed), what=MAIN)
    RC = need(main, "RC", what=MAIN)

    # the references of each week, and the lender of L-tr, from the first row tag's L-tr run file
    first = tags[0]
    refs, lenders = {}, set()
    for w in weeks:
        r = week_rows.get((first, trace, w, seed))
        if r is None:
            raise MissingKey(f"{MAIN}: no {first} run under {trace} in week {w}")
        f = runs.read("main", r["job"])
        refs[w] = need(f, "instances", "base", "references", what=f"run file of {r['job']}")
        lenders.add(str(need(f, "lender_models", trace, "schedule", what=f"run file of {r['job']}")))
    if len(lenders) != 1:
        raise MissingKey(f"{MAIN}: the run files record the {trace} schedules {sorted(lenders)}")
    # BL0a's USD per week and mode, equal over the rows of the week and mode
    bl0a = {(w, m): _same([r["bl0a_usd"] for (t, mm, ww, s), r in week_rows.items() if mm == m and ww == w],
                          f"{MAIN} bl0a_usd in week {w} under {m}")
            for w in weeks for m in (trace,) + stress}

    # gap days of part second
    gap_rows = _index(_runs_of(second, SECOND), "gap")
    gap_cells = sorted({k[2] for k in gap_rows}, key=_num)
    if not gap_cells:
        raise MissingKey(f"{SECOND}: no gap run (the ALG/LB column and mu/beta-tilde need them)")
    gap_lp = need(second, "gap_lp", what=SECOND)
    gap_ratio = need(second, "gap_ratio", what=SECOND)
    gap_seeds = sorted({k[3] for k in gap_rows})
    lp_files = {c: inp.json(f"{CONF}/second/lb/gap_lp_{c.split(':')[-1]}.json") for c in gap_cells}
    grids = {need(f, "grid", what="gap LP file") for f in lp_files.values()}
    gap_h = {int(need(f, "horizon_min", what="gap LP file")) for f in lp_files.values()}
    if len(grids) != 1 or len(gap_h) != 1:
        raise MissingKey(f"{SECOND}: the gap LP files have grids {sorted(grids)} and horizons {sorted(gap_h)}")
    # mu / beta-tilde of the E7 week instances: the gap run files' week_overrides (the only output recording it)
    gap_first = next(t for t in tags if any(k[0] == t for k in gap_rows))
    mus = set()
    for c in gap_cells:
        r = next(r for k, r in gap_rows.items() if k[0] == gap_first and k[2] == c)
        info = need(runs.read("second", r["job"]), "instance_info", "week_overrides", what=f"run file of {r['job']}")
        mus.add(float(need(info, "stranding.mu_over_beta_tilde", what=f"week_overrides of {r['job']}")))
    if len(mus) != 1:
        raise MissingKey(f"{SECOND}: the gap run files record mu/beta-tilde {sorted(mus)}")

    # p* weeks: those of second's week runs
    p_weeks = sorted({str(r["cell"]) for r in _runs_of(second, SECOND) if r.get("kind") == "week"}, key=_num)
    curves = need(ana, "reported", "intensity_curves", what=ANALYSIS)
    grid_top = max(float(p) for t in curves for w in curves[t] for p, r in (curves[t][w].get("points") or [])
                   if r is not None)

    out_rows = {}
    for tag in tags:
        cells = {}
        if tag == REFERENCE:
            ovf = {w: bl0a[(w, trace)] for w in weeks}
            tot = {w: float(need(refs[w], "bl0a_total_usd", what="references")) for w in weeks}
            cells["usd"] = _usd_cell(ovf, tot)
            cells["saving_pct"] = _value_cell({w: 100.0 * (1.0 - ovf[w] / bl0a[(w, trace)]) for w in weeks}, 1,
                                              "0 by definition (BL0a / BL0a)")
            g = {}
            for c in gap_cells:
                b = _same([r["bl0a_usd"] for k, r in gap_rows.items() if k[2] == c], f"{SECOND} bl0a_usd of {c}")
                g[c] = b / float(need(gap_lp, c, what=f"{SECOND} gap_lp"))
            cells["gap"] = _value_cell(g, 2, "bl0a_usd / gap_lp of the gap rows")
            cells["RC"] = _dash_cell("BL0a has no runs (an analytic reference)")
            cells["W0"] = _value_cell({w: max(bl0a[(w, m)] / bl0a[(w, trace)] for m in stress) for w in weeks}, 3,
                                      "largest BL0a under a stress mode over BL0a under L-tr (1 by definition)")
            cells["p_star"] = _dash_cell("BL0a has no runs (an analytic reference)")
        else:
            r0, ovf, tot = {}, {}, {}
            for w in weeks:
                row = week_rows.get((tag, trace, w, seed))
                if row is None or row.get("r0") is None:
                    raise MissingKey(f"{MAIN}: no {tag} run with r0 under {trace} in week {w}")
                r0[w] = float(row["r0"])
                ovf[w] = r0[w] * float(row["bl0a_usd"])
                run = runs.run("main", row["job"], trace, seed)
                tot[w] = float(need(run, "accountings", "total_usd", what=f"run file of {row['job']}"))
            cells["usd"] = _usd_cell(ovf, tot)
            cells["saving_pct"] = _value_cell({w: 100.0 * (1.0 - r0[w]) for w in weeks}, 1)
            g = {c: gap_ratio.get(f"{tag}:{c}:{s}") for c in gap_cells for s in gap_seeds
                 if (tag, trace, c, s) in gap_rows}
            if g:
                if len(g) != len(gap_cells) or any(v is None for v in g.values()):
                    raise MissingKey(f"{SECOND}: gap_ratio of {tag} missing on some gap cell ({g})")
                notes = sorted({str(gap_rows[(tag, trace, c, s)].get("ratio_validity")) for c in gap_cells
                                for s in gap_seeds if (tag, trace, c, s) in gap_rows} - {"None"})
                cells["gap"] = _value_cell({c: float(v) for c, v in g.items()}, 2, "; ".join(notes) or None)
            else:
                cells["gap"] = _dash_cell("no gap run")
            cells["RC"] = _value_cell({w: float(need(RC, tag, trace, w, str(seed), what=f"{MAIN} RC"))
                                       for w in weeks}, 3)
            cells["W0"] = _value_cell({w: float(need(W0, tag, w, what=f"{MAIN} W0.{seed}")) for w in weeks}, 3)
            cells["p_star"] = _p_star_cell(curves, tag, p_weeks, grid_top)
        out_rows[tag] = {"label": style.policy(keys[tag]).label, "style_key": keys[tag], "cells": cells}

    cap = caption_source(main, ana, refs, weeks, gap_cells, p_weeks, seed, out_rows, grids.pop(), gap_h.pop(),
                         mus.pop(), grid_top, lenders.pop())
    notes = {f"{tag}.{col}": c["note"] for tag, r in out_rows.items() for col, c in r["cells"].items()
             if c["text"] == DASH or c.get("note")}
    scope = {"tags": tags, "keys": [keys[t] for t in tags], "cells": weeks, "gap_cells": gap_cells,
             "p_star_cells": p_weeks, "modes": [trace, *stress, hon], "seeds": [seed]}
    title, note = caption_parts(cap)
    return {"order": tags, "rows": out_rows, "columns": [c for c, _ in COLUMNS], "header": [list(h) for h in HEADER],
            "caption": title, "note": note, "labels": {"caption": caption_text(cap)}, "caption_source": cap,
            "notes": notes,
            "tables": {f"{NAME}.tex": {"scope": scope}},
            "statistic": {"median": f"ms5b_common.bootstrap_median_ci over the weeks (seed {m5b.BOOT_SEED}, "
                                    f"{m5b.BOOT_B} resamples, 95% percentile interval); p*: the lower median over the "
                                    "p* weeks", "B": m5b.BOOT_B, "seed": m5b.BOOT_SEED},
            "meta": {"git_revision": rev, "git_revisions": revs, "reduced": reduced, "reduced_by_part": reduced_by,
                     "sources": [MAIN, SECOND, ANALYSIS]},
            "runs_sha256": dict(sorted(runs.sha.items())),
            "sources": list(inp.sources)}


def caption_source(main, ana, refs, weeks, gap_cells, p_weeks, seed, rows, grid, gap_h, mu, grid_top, lender) -> dict:
    """Every number and name the caption prints, read from the inputs (W2)."""
    guarded = need(main, "guarded", what=MAIN)
    meta_tags = need(main, "meta", "tags", what=MAIN)
    gs = need(main, "guard_summary", what=MAIN)
    n_runs, held = int(need(gs, "n_runs", what=f"{MAIN} guard_summary")), int(need(gs, "held", what=MAIN))
    if len(guarded) != n_runs:
        raise MissingKey(f"{MAIN}: guard_summary.n_runs {n_runs} but {len(guarded)} guarded rows")
    cases = {c: sum(1 for g in guarded if g.get("case") == c) for c in ("W(a)", "W(b)", "W(c)")}
    if sum(cases.values()) != n_runs:
        raise MissingKey(f"{MAIN}: guarded rows with a case other than W(a), W(b), W(c)")
    row_tags = [t for t, _ in ROWS]
    g_tags = [t for t in row_tags if any(g["tag"] == t for g in guarded)]
    rules = {g["B0_rule"] for g in guarded if g["tag"] in g_tags}
    if rules != {LB_RULE}:
        raise MissingKey(f"{MAIN}: the guarded rows of the table have the allowances {sorted(rules)}, not {LB_RULE!r}")
    # the guarded runs of tags without a row here (the legacy Sublet-MS4), which the count of part main includes
    elsewhere = {}
    for g in guarded:
        if g["tag"] not in row_tags:
            elsewhere[g["tag"]] = elsewhere.get(g["tag"], 0) + 1
    unnamed = sorted(t for t in elsewhere if t not in CAPTION_ONLY)
    if unnamed:
        raise MissingKey(f"{MAIN}: guarded runs of the tags {unnamed}, which have neither a row nor a caption key")
    # G3(b) at 'lb' through Corollary G3': the guarded rows around A9 (design/sublet_v2.md §2.6; Table II v2)
    g3b = [t for t in g_tags if bool(need(meta_tags, t, "a9_family", what=f"{MAIN} meta.tags"))]
    aborts = {t: [sum(1 for g in guarded if g["tag"] == t and g.get("aborted")),
                  sum(1 for g in guarded if g["tag"] == t)] for t in g_tags}
    trace_aborts = _trace_aborts(main, guarded, g_tags, weeks, seed)
    h2, h2b = need(ana, "H2", what=ANALYSIS), need(ana, "H2b", what=ANALYSIS)
    h1_set = list(need(h2, "set", what=f"{ANALYSIS} H2"))
    keys = {**{t: k for t, k in ROWS}, **CAPTION_ONLY}
    unknown = [t for t in h1_set + list(need(h2b, "set", what=ANALYSIS)) if t not in keys]
    if unknown:
        raise MissingKey(f"{ANALYSIS}: no registry key for the tags {unknown} of H1's or H2b's set")
    h2b_weeks = need(h2b, "weeks", what=f"{ANALYSIS} H2b")
    not_below = {p: [str(wk["week"]) for wk in h2b_weeks
                     if not float(wk["Sublet"]) < float(need(wk, "others", p, what=f"{ANALYSIS} H2b"))]
                 for p in h2b["set"]}
    equal = {p: [str(wk["week"]) for wk in h2b_weeks if float(wk["Sublet"]) == float(wk["others"][p])]
             for p in h2b["set"]}
    bl0b = [float(need(refs[w], "bl0b_overflow_usd", what="references")) / float(need(refs[w], "bl0a_usd",
                                                                                     what="references"))
            for w in weeks]
    readings = {t: rows[t]["cells"]["p_star"].get("reading") for t in row_tags if t != REFERENCE}
    return {
        "weeks": weeks, "n_weeks": len(weeks), "seed": seed, "mu_over_beta_tilde": mu, "lender": lender,
        "menu": "full", "gap_cells": gap_cells, "gap_horizon_min": gap_h, "gap_grid": grid, "gap_menu": "reduced",
        "p_star_cells": p_weeks, "p_grid_max": grid_top, "p_readings": readings,
        "p_zero_rows": [t for t in row_tags if t != REFERENCE and rows[t]["cells"]["p_star"].get("value") == 0.0],
        "allowance_rule": LB_RULE, "guarded_rows": g_tags, "g3b_rows": g3b,
        "certificates": {"n": n_runs, "held": held, "by_case": cases, "n_modes": len({g["mode"] for g in guarded}),
                         "elsewhere": dict(sorted(elsewhere.items()))}, "aborts": aborts,
        "trace_aborts": trace_aborts,
        "h1_set": h1_set,
        "h2b": {"set": list(h2b["set"]), "not_below_weeks": not_below, "equal_weeks": equal,
                "n_weeks": int(need(h2b, "n_weeks", what=ANALYSIS)),
                "below_1": int(need(h2b, "weeks_below_1", what=ANALYSIS)),
                "pass": bool(need(h2b, "pass", what=ANALYSIS))},
        "bl0b_over_bl0a": {**stat(bl0b), "by_cell": dict(zip(weeks, bl0b))},
        "labels": {**{t: style.policy(k).label for t, k in keys.items()}, "BL0b": style.policy(BL0B_KEY).label},
    }


def _trace_aborts(main: Mapping, guarded: Sequence[Mapping], g_tags: Sequence[str], weeks: Sequence[str],
                  seed: int) -> dict:
    """Per guarded row with an abort under L-tr (main.guarded, mode L-tr, at the week runs' policy seed): the weeks it
    aborted in, the abort slots t_a, its r0 in those weeks and, in the other weeks, the largest |r0 - r0(Sublet)|
    (main.table), so that the note can say that its medians mix two modes (print check of U38: Sublet one-way's
    25.3k USD beside its 44.5% saving)."""
    trace = m5b.TRACE_MODE
    table = need(main, "table", what=MAIN)

    def r0(tag, w):
        return float(need(table, tag, trace, w, str(seed), what=f"{MAIN} table"))

    out = {}
    for t in g_tags:
        rows = [g for g in guarded if g["tag"] == t and g["mode"] == trace and int(g.get("seed", seed)) == seed]
        ab = sorted((str(g["cell"]) for g in rows if g.get("aborted")), key=_num)
        if not ab:
            continue
        slots = [int(g["t_a"]) for g in rows if g.get("aborted") and g.get("t_a") is not None]
        rest = [w for w in weeks if w not in ab]
        out[t] = {"weeks": ab, "n_weeks": len(weeks), "t_a": [min(slots), max(slots)] if slots else None,
                  "r0_aborted": [min(r0(t, w) for w in ab), max(r0(t, w) for w in ab)],
                  "other_weeks": rest,
                  "other_max_abs_diff_to_" + HEADLINE: (max(abs(r0(t, w) - r0(HEADLINE, w)) for w in rest)
                                                        if rest and t != HEADLINE else None)}
    return out


def _seq(items: Sequence[str]) -> str:
    """'a', 'a and b', 'a; b; and c' (labels hold commas, so a longer list is split by semicolons)."""
    items = list(items)
    if len(items) <= 2:
        return " and ".join(items)
    return "; ".join(items[:-1]) + "; and " + items[-1]


def _cells_text(cells: Sequence[str]) -> str:
    """'weeks 301--304' from the gap cells 'gap:c301', ..."""
    return weeks_text([str(c).split(":")[-1].lstrip("c") for c in cells])


# MS6 M7: the registry label of the MS4 configuration (sublet_ms4, C41) writes its allowance as "($B_0=10\%$ BL0a)";
# the note writes it in words, "($B_0$ = 10\% of All-fallback)", with ties so that no line starts with "="; C52 (T1
# glossary G4, G12): "of the all-fallback bill", as the main text names this configuration (caption_parts passes FB_BILL)
B0_OF_BL0A = re.compile(r"\(\$B_0=(\d+(?:\.\d+)?)\\%\$ BL0a\)")


def note_label(label: str, reference: str) -> str:
    """A registry label as the note prints it (MS6 M7): "($B_0=10\\%$ BL0a)" becomes "($B_0$~=~10\\% of <reference>)",
    the reference 'the all-fallback bill' (C52: FB_BILL; as built, the label of BL0a, 'All-fallback'); every other
    label unchanged."""
    return B0_OF_BL0A.sub(lambda m: f"($B_0$~=~{m.group(1)}\\% of {reference})", label)


def case_text(case: str) -> str:
    """A case of main.guarded as the note prints it (MS6 M7): 'W(a)' -> '(a)', the part of the paper's Theorem
    \\ref{thm:fullmodel} (Theorem W in the design); 'W(c)', which the paper states as a conjecture after the theorem
    and not as a part of it (design/ms6_spec.md §5), -> 'the conjectured case' (U46, second review)."""
    return "the conjectured case" if case == "W(c)" else re.sub(r"^W(?=\()", "", case)


def cases_text(by_case: Mapping) -> str:
    """The note's count of guarded runs per case of Theorem \\ref{thm:fullmodel}: 'cases (a) n, (b) n', with the
    conjectured case W(c) only where it has runs (U46, second review: the theorem has no part (c))."""
    return "cases " + ", ".join(f"{case_text(k)} {v}" for k, v in by_case.items() if k != "W(c)" or v)


NUMBER_WORDS = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight", 9: "nine"}


def grid_text(grid: str) -> str:
    """C50 (D5 review): a bench grid in Section VII's words, its routing interval ("5-min routing" for the slow grid,
    q44_study.GRIDS: time.fast_slot_min 5), not the design name "slow grid"."""
    over = BENCH_GRIDS.get(grid)
    if not over or "time.fast_slot_min" not in over:
        raise MissingKey(f"{NAME}: no routing interval for the gap's grid {grid!r} in q44_study.GRIDS")
    return f"{over['time.fast_slot_min']:g}-min routing"


def modes_text(n_modes: int) -> str:
    """C50 (D5 review): the lender modes of the certificate count by Section VII's lenders, "trace, five stress and
    honoring lenders" (ms5b_common.conf_modes: L-tr, the five stress modes and L-hon), not "all 7 lender modes"; a
    count that is not every mode of the confirmation is refused."""
    stress = len(m5b.stress_modes())
    if n_modes != len(m5b.conf_modes()):
        raise MissingKey(f"{NAME}: the guarded runs cover {n_modes} lender modes, not the {len(m5b.conf_modes())} of "
                         "the confirmation")
    return f"trace, {NUMBER_WORDS.get(stress, str(stress))} stress and honoring lenders"


def caption_text(cap: Mapping) -> str:
    """The caption draft (W2): the title and the note of caption_parts in one text (labels.caption)."""
    return " ".join(caption_parts(cap))


def _trace_abort_text(cap: Mapping, lab: Mapping, t: str) -> str:
    """' (under the trace lender in k of n weeks, at the all-fallback bill; in the rest at Sublet's cost)' for a guarded
    row with aborts under L-tr, what its medians need (C51: no slots; "the all-fallback bill" where r0 prints 1.000,
    else "<r0> times" it); '' else."""
    ta = (cap.get("trace_aborts") or {}).get(t)
    if not ta:
        return ""
    k, n = len(ta["weeks"]), ta["n_weeks"]
    lo, hi = (tex_value(v, 3) for v in ta["r0_aborted"])
    cost = FB_BILL if lo == hi == tex_value(1.0, 3) else f"{lo if lo == hi else lo + '--' + hi} times {FB_BILL}"
    s = f" (under the trace lender in {k} of {n} week{'s' if n != 1 else ''}, at {cost}"     # MS6 U46: M11; C51
    d = ta.get("other_max_abs_diff_to_" + HEADLINE)
    if ta["other_weeks"] and d is not None:
        near = "at" if d == 0.0 else f"within {d:.4f} of"
        s += f"; in the rest {near} {lab[HEADLINE]}'s cost"                                                  # C51
    return s + ")"


def caption_parts(cap: Mapping) -> tuple[str, str]:
    """(title, note) of the caption (W2): the title, the float's \\caption, is the scope; the note below the table
    holds ALG/LB's and p*'s readings, the guarded rows' allowance, certificate and aborts, H1's set and
    BL0b's ratio (as built: in the class's small capitals the whole text took 16 lines of the column, the note in roman
    takes about a third fewer). Every number from caption_source; the math of a label in the note is boxed, so that a
    line does not break inside it ("N_Extra = / 0")."""
    # C52 (T1 glossary G4, G12): the MS4 configuration's allowance "of the all-fallback bill" (as built, "of
    # All-fallback", BL0a's label)
    lab = {k: re.sub(r"\$([^$]*)\$", r"\\mbox{$\1$}", note_label(v, FB_BILL)) for k, v in cap["labels"].items()}
    n, w = cap["n_weeks"], weeks_text(cap["weeks"])
    # C52 (T1 scan): no policy seed in the title (run configuration); the week labels stay (Fig. 4(b) prints them)
    title = ("End-to-end cost per policy, "                                    # MS6 M17: no experiment ID
             + (f"medians of {n} confirmation weeks" if n > 1 else "the confirmation week")
             + f" ({w.split(' ', 1)[1]}; {cap['lender']} lender, {cap['menu']} menu, "
               f"$\\mu/\\tilde\\beta={cap['mu_over_beta_tilde']:g}$).")                                  # C52
    s = []
    if cap["gap_cells"]:
        # C50 (D5 review): Section VII's words, "5-min routing", "the LP bound" (of the setup's LB) and "an upper
        # bound on the ratio to the offline optimum", for "slow grid", "the merged LP bound" and "the gap"
        s.append(f"ALG/LB: the first {horizon_text(cap['gap_horizon_min'])} of {_cells_text(cap['gap_cells'])} "
                 f"({grid_text(cap['gap_grid'])}, {cap['gap_menu']} menu) over the LP bound, an upper bound on the "
                 "ratio to the offline optimum.")                                                         # C50
    partial = sorted({r for r in cap["p_readings"].values() if r and r.startswith(">")})
    zero = [f"{tex_value(0.0, 2)}: $r_0>1$ already without reclaims"] if cap.get("p_zero_rows") else []
    reads = zero + [f"none: $r_0\\le1$ at every $p\\le{tex_p(cap['p_grid_max'])}$"] + [
        f"$>${r[1:]}: likewise, but only $p\\le{r[1:]}$ ran" for r in partial]
    s.append(f"$p^\\ast$: lower median over {weeks_text(cap['p_star_cells'])} of the first i.i.d.\\ reclaim "
             f"probability with $r_0>1$ ({'; '.join(reads)}).")
    c = cap["certificates"]
    cases = cases_text(c["by_case"])                                                    # MS6 M7; U46
    aborted = [t for t, (a, _) in cap["aborts"].items() if a > 0]
    ab = "; ".join(f"{lab[t]} aborted in {a} of {m} runs" + _trace_abort_text(cap, lab, t)
                   for t, (a, m) in cap["aborts"].items() if a > 0)
    rest = [lab[t] for t in cap["guarded_rows"] if t not in aborted]
    if rest:
        ab = (ab + "; " if ab else "") + f"{_seq(rest)} in none"
    # C52 (T1 glossary G4): the configuration by its name, as the main text names it (as built, "the supplement's")
    other = _seq([f"{k} of {lab[t]}" for t, k in c["elsewhere"].items()])                               # C52
    g3 = cap["g3b_rows"]
    # MS6 M7: the results by \ref to the paper's labels (design/ms6_spec.md §5); C52 (T1 scan): Theorem
    # \ref{thm:fullmodel}'s "bound" (the certificate checks its parts (a) and (b); "envelope" is Theorem
    # \ref{thm:envelope}'s)
    s.append(f"Guarded rows: {LB_RULE_TEX}. Theorem~\\ref{{thm:fullmodel}}'s bound held in {c['held']} of {c['n']} "
             f"guarded runs ({modes_text(c['n_modes'])}; " + (f"{other}; " if other else "") + f"{cases})"  # C50; C52
             + (f"; Corollary~\\ref{{cor:ratio}}{COR_PART_LB} holds for {_seq([lab[t] for t in g3])}, on core "
                "instances (Lemma~\\ref{lem:projection}(e))" if g3 else "") + f"; {ab}.")          # C50; C51
    order = [t for t, _ in ROWS] + list(CAPTION_ONLY)
    h1set = [lab[t] + (" (supplement)" if t in CAPTION_ONLY else "")
             for t in sorted(cap["h1_set"], key=lambda t: order.index(t))]
    s.append(f"{PRIMARY}: {_seq(h1set)}.")      # C51: no H2b sentence (Section VII reports H2b once); C52: G3
    s.append(f"{lab['BL0b']}: {cap['bl0b_over_bl0a']['median']:.1f} times {FB_BILL} in overflow accounting.")   # U46
    return title, " ".join(s)


def float_tex(data: Mapping) -> str:
    """The float paper/floats/table3_v2.tex."""
    meta = data["meta"]
    lines = [
        "% Table III v2: E7 on the confirmation weeks per policy (design/sublet_v2.md §11, W2). Written by "
        "code/sim/figs/table3_v2.py",
        f"% from code/sim/out/sublet_v2/ (git revision {meta.get('git_revision')}); do not edit. Rows: style.POLICIES "
        "labels (MS5b registry);",
        "% columns: USD per week in thousands, overflow (total) accounting; saving over BL0a (%, overflow); ALG / "
        "merged LP bound on",
        "% the gap days; RC under L-tr; W0; p*. Medians over the weeks (registered bootstrap); intervals and per-week "
        "values in the",
        "% extract code/sim/out/figs/table3_v2.json and in the supplement. Cites nothing. Needs booktabs and array.",
        # MS6 M7: the note's results by \ref
        "% Names results by \\ref to the paper's labels (design/ms6_spec.md M7, §5); no experiment ID (M17). Note "
        "shortened (C51).",
        # C52 (design/ms7/plan.md §4, T1): the glossary's names; \Wk provided for the float compiled alone
        "% MS7 T1 (C52): the T1 glossary's names (per-group allowance with \\Wk, primary baselines); \\providecommand "
        "gives \\Wk its paper/macros.tex definition when the float is compiled alone."]
    if meta.get("reduced"):
        lines.append("% REDUCED INPUT (meta.reduced true): a smoke run, not a result.")
    lines += [r"\begin{table}[t]", WK_MACRO, r"\caption{" + data["caption"] + "}", r"\label{tab:e7}",   # C52
              r"\centering\footnotesize", TABLE_ENV, r"\toprule"]
    head = data["header"]
    lines.append(" & ".join(h[0] for h in head) + r" \\")
    lines.append(" & ".join(h[1] for h in head) + r" \\")
    lines.append(r"\midrule")
    for tag in data["order"]:
        r = data["rows"][tag]
        lines.append(" & ".join([r["label"]] + [r["cells"][c]["text"] for c in data["columns"]]) + r" \\")
    lines += [r"\bottomrule", TABLE_END + r"\par\vspace{2pt}",
              r"\parbox{\columnwidth}{\footnotesize\raggedright " + data["note"] + "}", r"\end{table}"]
    return "\n".join(lines) + "\n"


def float_dir(out: str | os.PathLike | None) -> Path:
    """--out, else SUBLET_FIGS_PDF_DIR when set (scratch builds and tests), else paper/floats/."""
    if out:
        return Path(out)
    env = os.environ.get(style.ENV_PDF_DIR)
    return Path(env) if env else FLOATS_DIR


def write_float(data: Mapping, out_dir: Path) -> Path:
    if data["meta"].get("reduced") and Path(out_dir).resolve() == FLOATS_DIR.resolve():
        raise SystemExit(f"{NAME}: the inputs are from a reduced run (meta.reduced); the float is not written into "
                         f"{FLOATS_DIR} (give --out DIR)")
    out_dir.mkdir(parents=True, exist_ok=True)
    tmp = out_dir / f".{NAME}.tex.partial"
    tmp.write_text(float_tex(data), encoding="utf-8")
    os.replace(tmp, out_dir / f"{NAME}.tex")
    return out_dir / f"{NAME}.tex"


def write_extract(data: Mapping, sources: Sequence[str]) -> Path:
    """code/sim/out/figs/table3_v2.json (SUBLET_FIGS_OUT_DIR): every printed cell with its value and note."""
    _, out = style.output_dirs()
    out.mkdir(parents=True, exist_ok=True)
    payload = {"table": NAME, "sources": [style.check_source(s) for s in sources],
               "data": {k: v for k, v in data.items() if k != "sources"}}
    tmp = out / f".{NAME}.json.partial"
    tmp.write_text(json.dumps(payload, indent=1, allow_nan=False) + "\n", encoding="utf-8")
    os.replace(tmp, out / f"{NAME}.json")
    return out / f"{NAME}.json"


def main(argv: Sequence[str] | None = None) -> dict:
    ap = argparse.ArgumentParser(prog=f"python -m figs.{NAME}", description=__doc__.split("\n")[0])
    ap.add_argument("--out", default=None, metavar="DIR",
                    help=f"folder of the float (default: SUBLET_FIGS_PDF_DIR if set, else {FLOATS_DIR})")
    ap.add_argument("--from-extract", nargs="?", const="", default=None, metavar="JSON",
                    help=f"rewrite the float from the extract alone (default code/sim/out/figs/{NAME}.json under the "
                         "input root)")
    args = ap.parse_args(argv)
    if args.from_extract is None:
        inp = Inputs()
        data = json.loads(json.dumps(build(inp), allow_nan=False))
        sources = list(data.pop("sources"))
    else:
        if args.from_extract:
            payload = json.loads(Path(args.from_extract).read_text(encoding="utf-8"))
        else:
            payload = Inputs().json(f"code/sim/out/figs/{NAME}.json")
        if payload.get("table") != NAME:
            raise style.StyleError(f"{args.from_extract or NAME} is the extract of {payload.get('table')!r}, "
                                   f"not {NAME!r}")
        data, sources = dict(payload["data"]), list(payload.get("sources") or [])
        # C50 (D5 review): the caption, the note and the caption draft are text over caption_source's numbers, so a
        # wording change reaches the float from the extract alone (the run files that build() reads are not versioned)
        data["caption"], data["note"] = caption_parts(data["caption_source"])                         # C50
        data["labels"] = {**data.get("labels", {}), "caption": caption_text(data["caption_source"])}  # C50
    tex = write_float(data, float_dir(args.out))
    ext = write_extract(data, sources)
    print(f"[{NAME}] wrote {tex} and {ext} ({len(data['order'])} rows, {len(data['notes'])} cell notes, "
          f"{len(data['runs_sha256'])} run files)")
    return {"tex": str(tex), "json": str(ext), "data": data, "sources": sources}


if __name__ == "__main__":
    main(sys.argv[1:])
