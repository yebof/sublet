"""sf_e7_decomp: the decomposition of Sublet on the confirmation weeks, with the tables e7v2_weeks.tex,
e7v2_pareto.tex, e7v2_rc.tex, e7v2_seeds.tex, e7v2_table3_intervals.tex, e7v2_h3.tex and ms5b_outcomes.tex and the
data file e7v2_rc_runs.csv (design/sublet_v2.md §11, W2, W4, W9, W10; §2.3, §3, §4.5, §6; prereg §5, "reported in
full", and §6).

Figure (W2 x 2.4 in, C41). A9's ablations and the transplants against Sublet (W4: "per-week or median L-tr r0 vs
W0"): for each policy, its paired differences from Sublet on each of the confirmation weeks of part main (16 on the
confirmation; read from the data), Delta r0 = r0(policy) - r0(Sublet) under the trace lender (x) and Delta W0 =
W0(policy) - W0(Sublet) (y; W0 the largest r0 over the five stress modes, main's W0 block), policy seed 0; the marker
is the median over the weeks of each difference, the bars their 95% week-bootstrap intervals
(ms5b_common.bootstrap_median_ci, seed 20261031, 10,000 resamples; W9). Paired differences, as H1's margin is paired
(§4.5), since the ablations' trace costs differ from Sublet's by less than the spread of r0 over the weeks. Sublet is
the origin; positive is worse than Sublet on both axes; grey lines mark 0. (a) Critical-ratio renting (A9, Sublet's
inner policy) and its ablations of §2.3 (CR, the planning half alone; no make-before-break; no commitment rule; no
insurance; the baselines' k* contract; no site marking). (b) The transplants and the guard: greedy renting (BL1) with
A9's notice layer (BL1N) and with Sublet's guard (BL1-GP), RetroRenting-style (BL5-cur) with A9.3 and A9.4 (BL5N),
each joined to its base by an arrow in the base's label color, and Sublet's guard without projection (Sublet,
one-way).

As built (choices that §11 leaves open):
* Labels. Fourteen keys with labels up to 1.9 in do not fit a legend row, so each point is named directly. C62
  (name_column): a name sits beside its point (right of its marker and interval bars, above or below its marker, or
  left of them) where that place is free (NAME_CLEAR_PT from every mark, NAME_SEP_PT from the other names, and, right
  or left of the point, AMBIG_PT free of other points beyond it, so that no name between two points reads as either's);
  the others go to a column right of the panel's data, stacked in the order of the points' heights as close to them
  as the names allow (common.stack_labels), each with a thin grey leader to its point that moves by the least shift up
  to LEADER_SHIFT_PT that keeps NAME_CLEAR_PT from the other points' marks and the names; the places are chosen
  together, beside the points before the column. As built until C62 every name was in the column, and in (b) the
  leaders of the cluster near (0.06, 0.2) crossed the other points' bars. Where a point's Delta r0 bar is clipped at
  the spine's end, its arrowhead points into the column at the point's height, and the column puts the point's own
  name there and no other (Sublet one-way's name, not Sublet's, at the origin). In (a) an ablation's name drops the
  prefix "Critical-ratio renting, " that the panel title carries ("no insurance", ...); every other name is the
  registry label. Points whose medians and interval ends agree within COINCIDE_TOL (A9 and its no-insurance ablation
  with Sublet at the origin) share one name, the others' names on lines of their own after "= " (name_groups; the
  extract's `coincide`). The data widths of the panels are DATA_SHARE of the row's (C62; as built, equal), and each
  panel's y axis has its label (C62; as built, only (a)'s), the titles at the caption size
  (ms5b_e7_lib.caption_title).
* Each panel has its own axes (print check 2026-11-03): x, since the ablations differ from Sublet by hundredths and
  the transplants by tenths, with ticks of the first step of X_STEPS that gives 3 to 5 ticks over the data; y, since
  (a) holds both the ablations' W0 differences of tenths and two of hundredths below 0 (no commitment rule, no site
  marking), so (a)'s Delta W0 axis is symlog (SYMLOG: linear within +-0.02, as style.symlog_minutes, no minor
  ticks; ticks 0, +-linthresh and the powers of 10 at least Y_TICK_GAP_PT apart) and (b)'s linear. An interval that
  ends beyond CLIP_FACTOR times the largest median difference of its panel is drawn to the end of its spine with an
  arrowhead (its end value in the caption: a number at the spine's end read as part of the name beside it). Where a
  point's Delta r0 interval is clipped so, its weeks right of the drawn range (beyond: Sublet one-way's six weeks in
  which its guard aborts in every run) are counted on a second line of its name with their Delta r0 range, and the
  caption gives their weeks, their Delta r0 and Delta W0 and the aborts (part main's guarded runs of the tag).
* labels.caption is a caption draft with every count read from the inputs; it states that the weeks are rotations
  of one series (the statistics descriptive, §4.5), the scale of (a), the coinciding points, the ablations whose
  Delta W0 interval lies below 0, and the weeks right of the drawn range.

Tables (after hook, figs.common.write_table; from the extract's `tables`, so --from-extract rewrites them; each entry
of `tables` carries a `scope` for the claims report, W11):
  e7v2_weeks.tex             per-week L-tr r0 and W0 of every tag of part main (the 22 tags of §3, A9's ablations and
                             the transplants included) with the median over the weeks and its 95% interval;
  e7v2_pareto.tex            per week, the Pareto front of L-tr r0 and W0 over the tags of §3 that are not ablations
                             of A9 (analysis.json reported.pareto_front; the set is ms5b_analysis.PARETO_TAGS) with each
                             member's values, whether Sublet is on it and the tags that dominate it with their margins;
                             the caption names the tags left out that run A9's code (BL1N) and, where the same tags
                             dominate Sublet in every week it is off the front, the largest margins;
  e7v2_rc.tex                RC under every mode (analysis.json reported.RC: part main's six modes on every week, part
                             second's modes on its weeks, each paired with main's L-hon run; seed 0, and seeds 1-2 of
                             part seeds in rows of their own), the median and its interval, with the medians of the
                             runs' fallback and stranding totals (USD) and MS4's fallback share after reclaims
                             (prereg l.235); every run's values are in the extract and in the data file below; the
                             caption notes where L-ad, L-eg and L-iid-1 (SAME_MODES) give equal RC on their common
                             weeks (same_modes);
  e7v2_rc_runs.csv           every run of e7v2_rc.tex (prereg l.235, "each run's fallback and stranding totals beside
                             it"): policy, tag, mode, week, policy seed, RC, fallback and stranding USD, share after
                             reclaims (rc_runs_csv); the extract's tables.e7v2_rc_runs holds its columns, row count,
                             sha256 and e7v2_rc's scope, and the after hook refuses to write a file of another sha256;
  e7v2_seeds.tex             part seeds: r0 under the seven modes, W0 and RC under L-tr for policy seeds 0 (main), 1
                             and 2 per week, with each tag's largest difference from seed 0; where a tag's seeds
                             agree, the caption gives the reason the data support (seed_draws: its inner policy is
                             seed-free and its safe expert, whose R holds the guard's draws, followed FB at every
                             slot; W4's "Sublet draws no random number" does not hold for the guard, which draws);
  e7v2_table3_intervals.tex  every cell of Table III v2 (W2: its 14 rows; USD per week in thousands in overflow and in
                             total accounting, the saving over BL0a, ALG/LB on the gap days, RC under L-tr, W0, p*) with
                             its median, its 95% interval and n; p* as Table III v2 computes it (figs/table3_v2.py:
                             the lower median over part second's weeks of the first p with r0 > 1, a week without one
                             ranked above every p, read 'none' or '>q'; p_star) with its per-week values in place of an
                             interval; BL0a's saving (0) and W0 (1) as Table III v2 prints them. Overflow USD is r0 x bl0a_usd (W10); the total accounting and BL0a's total
                             come from the run files of part main (W10: each file listed with its sha256 in
                             meta.runs_files). These cells are computed here from their definitions in W2;
  e7v2_h3.tex                H3's counts (§6) over every guarded run of the confirmation: per part, tag and group (the
                             job kind; E3's shared and siloed runs; the family of part fam), runs, certificates held,
                             envelope violations, aborts, aborts under Proposition P's hypotheses, switches of S,
                             robust-form slots, projected slots, K0 uses and dropped actions (the runs with a switch
                             or a robust-form slot in the extract), with the totals beside analysis.json's H3; a
                             column that is 0 in every row is left out and named in the caption;
  ms5b_outcomes.tex          each hypothesis of the pre-registration (H1-H6, H2b): kind, criterion (as registered, the
                             thresholds from analysis.json and ms5b_analysis), measured value and outcome, from
                             analysis.json.
Every table is a longtable (ms5b_e7_lib.longtable: one-column mode, a group of rows kept on one page, a two-line name
split over the group's first two rows, name_cells).

Inputs (W10): the summaries of parts main, seeds, second, e3, fam and grid and analysis.json
(code/sim/out/sublet_v2/); the run files code/sim/out/sublet_v2/main/runs/ of Table III v2's rows under the trace
lender (unversioned; listed with their sha256). Run from code/sim: python -m figs.supp.sf_e7_decomp
[--from-extract [JSON]].

C50 (design/ms6_spec.md §7.2, the D5 review; §7.1 D4's script items): the RC table's caption names "the fallback share
after reclaims that the earlier end-to-end study defined" for MS4's; every longtable's head on its later pages opens
with "Table <n>, continued" (ms5b_e7_lib.cont_head).

C58 (design/ms7/w_spec.md §3): the main text's Table III is the policy glossary since MS7 and its Table IV (tab:e7)
prints no p*, so e7v2_table3_intervals.tex's caption cites Table~\ref{tab:e7} by label, names the gap and p* as its
own columns and defines p* from the crossings' table instead of "as in Table III of the main text".
"""
from __future__ import annotations

import csv
import hashlib
import io
import itertools
import math
import statistics
import sys
from typing import Any, Mapping, Sequence

import numpy as np
from matplotlib.scale import SymmetricalLogTransform
from matplotlib.ticker import FixedLocator, NullLocator

from figs import style
from figs.common import MissingKey, align_baselines, cli, need, stack_labels, text_width_in, write_table
from figs.inputs import Inputs
from figs.supp import ms5b_e7_lib as L
from sublet.experiments import ms5b_analysis as MA
from sublet.experiments import ms5b_common as m5

NAME = "sf_e7_decomp"
KEYS = style.SUPP_POLICIES_MS5B[NAME]
TABLES = ("e7v2_weeks.tex", "e7v2_pareto.tex", "e7v2_rc.tex", "e7v2_seeds.tex", "e7v2_table3_intervals.tex",
          "e7v2_h3.tex", "ms5b_outcomes.tex", "e7v2_rc_runs.csv")
RC_RUNS = TABLES[-1]            # every run of e7v2_rc.tex (a data file of the supplement, beside its tables)
style.register_supplementary(NAME, "W2", 2.4)
REF = "sublet_v2"
PANELS = (("a", "Critical-ratio renting and its ablations",
           ("a9", "cr", "a9_nombb", "a9_nocommit", "a9_noins", "a9_kstar", "a9_static")),
          ("b", "Transplants and guards", ("bl1", "bl1n", "bl1_gp", "bl5_cur", "bl5n", "sublet_1way")))
ARROWS = (("bl1", "bl1n"), ("bl1", "bl1_gp"), ("bl5_cur", "bl5n"))      # base -> transplant or guarded
A9_PREFIX = style.POLICIES["a9"].label + ", "
if sorted({REF, *(k for _, _, ks in PANELS for k in ks)}) != sorted(KEYS):
    raise style.StyleError(f"{NAME}: the panels' keys must be SUPP_POLICIES_MS5B[{NAME!r}]")
# Table III v2's rows (W2), by tag; BL0a analytic
T3_TAGS = ("Sublet", "Sublet-1way", "BL1-GP", "BL1N", "BL5N", "BL1", "BL1-BO", "BL5-cur", "BL5-tau60", "BL2", "BL3-0",
           "BL4", "A6", "BL0a")
T3_COLUMNS = (("usd_overflow", "USD per week (k), overflow accounting", ".2f"),
              ("usd_total", "USD per week (k), total accounting", ".2f"),
              ("saving_pct", r"Saving over all-fallback (\%), overflow", ".1f"),
              ("gap", "ALG/LB on the gap days", ".3f"),
              ("rc", "RC under the trace lender", ".4f"),
              ("w0", "$W_0$, worst cost over the stress modes", ".3f"),
              ("p_star", "$p^\\ast$, first $p$ with $r_0>1$", "g"))
X_STEPS = (0.005, 0.01, 0.02, 0.025, 0.05, 0.1, 0.2, 0.25, 0.5)
Y_STEPS = (0.1, 0.2, 0.25, 0.5, 1.0)
MIN_TICKS, MAX_TICKS = 3, 5
PAD = 0.05                      # the data range beyond the points and intervals, as a share of its span
CLIP_FACTOR = 2.0               # an interval end beyond this times the panel's largest median difference is clipped
LABEL_GAP_PT = 7.0              # the name column this far right of the x spine's end
LABEL_RIGHT_PT = 2.0            # ... and this far inside the axes' right side
LEADER_PT = 0.4
LEADER_GREY = "#9E9E9E"
SYMLOG = {"a": 0.02}            # the panels whose Delta W0 axis is linear within +-linthresh and logarithmic beyond
LINSCALE = 1.0                  # as style.symlog_minutes
COINCIDE_TOL = 1e-4             # points whose medians and interval ends agree within this share one name and leader
Y_TICK_GAP_PT = 11.0            # the least distance between two tick labels of a symlog Delta W0 axis
SAME = "= "                     # a coinciding point's name, on the line below the first point's name
TOP_TICK_PT = 5.0               # the least distance of the highest y tick below the axes top
LEADER_SHIFT_PT = 12.0          # the largest move of a name that clears its leader of other points' bars and markers
DATA_SHARE = (0.42, 0.58)       # C62: the panels' shares of the row's data width (as built, equal): (a)'s names sit
#                                 beside points that lie within a hundredth of 0 but one, (b)'s cluster needs the room
MODE_ORDER = (L.TRACE,) + tuple(L.STRESS) + ("L-vr", "L-rf", "L-ad", "L-b999", "L-iid-0.1", "L-iid-0.34", "L-iid-0.5",
                                             "L-iid-0.8", "L-iid-1")
LABELS = {"x": r"$\Delta r_0$ against Sublet, L-tr", "y": r"$\Delta W_0$ against Sublet",
          "caption": ("The ablations of critical-ratio renting (A9, Sublet's inner policy) and the transplants against "
                      "Sublet on weeks {weeks} of part main ({n} weeks, policy seed 0): per week the difference from "
                      "Sublet of the cost over all-fallback under the trace lender ($\\Delta r_0$) and of the worst "
                      "cost over the five stress lenders ($\\Delta W_0$); medians over the weeks with 95\\% "
                      "week-bootstrap intervals ({B} resamples, seed {seed}; descriptive, the weeks being rotations of "
                      "one series). Sublet is the origin; positive is worse. (a) Critical-ratio renting and its "
                      "ablations{scale}; (b) greedy renting with critical-ratio renting's notice layer and with "
                      "Sublet's guard, RetroRenting-style with critical-ratio renting's contract rule and "
                      "make-before-break (arrows from the base policy, in its color), and Sublet's guard without "
                      "projection. {same}{lower}{beyond}{clip}Per-week values in Table~\\ref{{tab:e7v2-weeks}}."),
          "scale": ", with $\\Delta W_0$ on a scale linear within $\\pm{lt}$ and logarithmic beyond",
          "same": "{names} {verb} Sublet's medians and intervals (one name). ",
          "same_other": "{names} have equal medians and intervals (one name). ",
          "lower": ("{names} {verb} a lower $W_0$ than Sublet: median $\\Delta W_0$ {dw}{resp} (intervals below 0), "
                    "at a median $\\Delta r_0$ of {dr}. "),
          "beyond": "{name}: in week{s} {weeks}{aborts} $\\Delta r_0$ is {dr} and $\\Delta W_0$ {dw}, right of the "
                    "drawn range (its name gives the count){rest}. ",
          "aborts": ", in which its guard aborts in every run ({a} of its {n} runs of part main),",
          "rest": "; in the other {m} weeks it equals Sublet",
          "clip": "{name}'s interval on {axis} reaches {value:.2f} (arrow). "}


# ---------------------------------------------------------------------------------------------------------------
# the figure's data
def paired(main: Mapping, tag: str, weeks: Sequence[str]) -> dict:
    """Per week (Delta r0 under L-tr, Delta W0) of `tag` against Sublet, and their medians and intervals."""
    t, w0 = main["table"], need(main, "W0", "0", what=L.MAIN)
    dr, dw = [], []
    for w in weeks:
        a, b = L.val(t, tag, L.TRACE, w), L.val(t, "Sublet", L.TRACE, w)
        c, d = (w0.get(tag) or {}).get(w), (w0.get("Sublet") or {}).get(w)
        dr.append(None if a is None or b is None else a - b)
        dw.append(None if c is None or d is None else c - d)
    return {"tag": tag, "dr": L.med_ci(dr), "dw": L.med_ci(dw), "per_week": {w: [x, y] for w, x, y in zip(weeks, dr,
                                                                                                         dw)}}


def build(inp: Inputs) -> dict:
    parts = {p: inp.json(f) for p, f in L.PART_FILES.items()}
    an = inp.json(L.ANALYSIS)
    main = parts["main"]
    L.need_tags(main["table"], [L.TAG_OF_KEY[k] for k in KEYS], L.MAIN)
    weeks = L.weeks_of(main["table"], ["Sublet"], [L.TRACE])
    points = {k: paired(main, L.TAG_OF_KEY[k], weeks) for k in KEYS}
    runs_files: list = []
    tables = {"e7v2_weeks": weeks_table(main),
              "e7v2_pareto": pareto_table(main, an),
              "e7v2_rc": rc_table(parts, an),
              "e7v2_seeds": seeds_table(main, parts["seeds"], an),
              "e7v2_table3_intervals": table3_intervals(inp, main, parts["second"], an, runs_files),
              "e7v2_h3": h3_table(parts, an),
              "ms5b_outcomes": outcomes_table(an)}
    tables["e7v2_rc_runs"] = rc_runs_entry(tables["e7v2_rc"])
    out = {"keys": list(KEYS), "weeks": weeks, "points": points,
           "panels": [{"letter": a, "title": t, "keys": list(ks), "symlog": SYMLOG.get(a)} for a, t, ks in PANELS],
           "arrows": [list(a) for a in ARROWS], "bootstrap": dict(L.BOOT), "tables": tables,
           "labels": dict(LABELS),
           "meta": {**L.meta_of({**parts, "analysis": an}), "runs_files": runs_files}}
    out["clipped"] = clipped(out)
    out["coincide"] = [g for p in out["panels"] for g in name_groups(out, p["keys"]) if len(g) > 1]
    out["beyond"] = beyond(out, main)
    out["labels"]["caption"] = caption(out)
    out["meta"]["sources"] = list(inp.sources)
    return out


def clipped(d: Mapping) -> list[dict]:
    """The interval ends beyond the drawn ranges (ranges()): [{key, axis (dr or dw), end (lo or hi), value}]."""
    out = []
    for p, r in zip(d["panels"], ranges(d)):
        for k in p["keys"]:
            for f, lim in (("dr", r["x"]), ("dw", r["y"])):
                lo, hi = d["points"][k][f]["lo"], d["points"][k][f]["hi"]
                if lo is not None and lo < lim[0] - 1e-12:
                    out.append({"key": k, "axis": f, "end": "lo", "value": lo})
                if hi is not None and hi > lim[1] + 1e-12:
                    out.append({"key": k, "axis": f, "end": "hi", "value": hi})
    return out


def beyond(d: Mapping, main: Mapping | None = None) -> list[dict]:
    """The points whose Delta r0 interval is clipped on the right (clipped()), with their weeks whose Delta r0 lies
    right of the drawn x range (ranges()), which the median and the clipped bar hide: [{key, panel, weeks, n_weeks,
    dr: [min, max], dw: [min, max], equal_rest (Delta r0 and Delta W0 both 0 in every other week), aborts}]; aborts
    (from part main's guarded runs of the tag, None for an unguarded tag): {all: every run of part main in those weeks
    aborts and none in the others, n_aborted, n_runs}."""
    out = []
    cut = {c["key"] for c in clipped(d) if c["axis"] == "dr" and c["end"] == "hi"}
    for p, r in zip(d["panels"], ranges(d)):
        for k in p["keys"]:
            if k not in cut:
                continue
            pw = d["points"][k]["per_week"]
            far = [w for w, (x, _) in pw.items() if x is not None and x > r["x"][1] + 1e-12]
            if not far:
                continue
            rest = [v for w, v in pw.items() if w not in far]
            e = {"key": k, "panel": p["letter"], "weeks": far, "n_weeks": len(pw),
                 "dr": [min(pw[w][0] for w in far), max(pw[w][0] for w in far)],
                 "dw": [min(pw[w][1] for w in far if pw[w][1] is not None),
                        max(pw[w][1] for w in far if pw[w][1] is not None)],
                 "equal_rest": bool(rest) and all(x == 0.0 and y == 0.0 for x, y in rest), "aborts": None}
            g = [x for x in (main or {}).get("guarded") or [] if x.get("tag") == d["points"][k]["tag"]]
            if g:
                ab = {w: [bool(x.get("aborted")) for x in g if str(x.get("cell")) == w] for w in pw}
                e["aborts"] = {"all": all(ab[w] and all(ab[w]) for w in far)
                               and not any(any(ab[w]) for w in pw if w not in far),
                               "n_aborted": sum(sum(v) for v in ab.values()), "n_runs": len(g)}
            out.append(e)
    return out


def _num_text(v: float, fmt: str) -> str:
    s = format(float(v), fmt)
    return f"$-${s[1:]}" if s.startswith("-") else s


def caption(d: Mapping) -> str:
    lab = {p["letter"]: p for p in d["panels"]}
    clip = "".join(LABELS["clip"].format(name=style.POLICIES[c["key"]].label,
                                         axis="$\\Delta r_0$" if c["axis"] == "dr" else "$\\Delta W_0$",
                                         value=c["value"]) for c in d["clipped"])
    lt = lab.get("a", {}).get("symlog")
    scale = LABELS["scale"].format(lt=format(lt, "g")) if lt else ""
    same = ""
    for g in d.get("coincide") or []:
        others = [k for k in g if k != REF]
        if REF in g:
            same += LABELS["same"].format(names=_names_text(others), verb="has" if len(others) == 1 else "have")
        else:
            same += LABELS["same_other"].format(names=_names_text(others))
    neg = [k for p in d["panels"] for k in p["keys"] if (d["points"][k]["dw"]["hi"] or 0.0) < 0.0
           and d["points"][k]["dw"]["median"] is not None]
    lower = ""
    if neg:
        names = _names_text(neg)
        names = names[0].upper() + names[1:]
        lower = LABELS["lower"].format(
            names=names, verb="has" if len(neg) == 1 else "have",
            dw=" and ".join(_num_text(d["points"][k]["dw"]["median"], ".3f") for k in neg),
            dr=" and ".join(_num_text(d["points"][k]["dr"]["median"], ".4f") for k in neg),
            resp=", respectively" if len(neg) > 1 else "")
    far = ""
    for b in d.get("beyond") or []:
        ab = b.get("aborts") or {}
        far += LABELS["beyond"].format(
            name=style.POLICIES[b["key"]].label, s="s" if len(b["weeks"]) > 1 else "",
            weeks=L.join_labels(b["weeks"]),
            aborts=LABELS["aborts"].format(a=ab["n_aborted"], n=ab["n_runs"]) if ab.get("all") else "",
            dr=_span_text(b["dr"], "--"), dw=_span_text(b["dw"], "--"),
            rest=LABELS["rest"].format(m=b["n_weeks"] - len(b["weeks"])) if b["equal_rest"] else "")
    return LABELS["caption"].format(weeks=L.week_span(d["weeks"]), n=len(d["weeks"]), B=f"{L.BOOT['B']:,}",
                                    seed=L.BOOT["seed"], scale=scale, same=same, lower=lower, beyond=far, clip=clip)


def _names_text(keys: Sequence[str]) -> str:
    """Policies for a caption: registry labels, and the ablations of critical-ratio renting by their names in panel
    (a), quoted ("Critical-ratio renting and its ablation ``no insurance''", "the ablations ``no commitment rule''
    and ``no site marking''"); the list as ms5b_e7_lib.join_labels."""
    full = [style.POLICIES[k].label for k in keys if name_of(k) == style.POLICIES[k].label]
    abl = ["``" + name_of(k) + "''" for k in keys if name_of(k) != style.POLICIES[k].label]
    if not abl:
        return L.join_labels(full)
    lead = ("its" if "a9" in keys else "the") + " ablation" + ("s " if len(abl) > 1 else " ") + " and ".join(abl)
    return L.join_labels(full + [lead]) if full else lead


def _span_text(v: Sequence[float], dash: str) -> str:
    """'0.44--0.51' (two decimals; one value where both round alike)."""
    a, b = (format(float(x), ".2f") for x in v)
    return a if a == b else f"{a}{dash}{b}"


# ---------------------------------------------------------------------------------------------------------------
# the figure
def _steps(lo: float, hi: float, steps: Sequence[float]) -> list[float]:
    for st in steps:
        t = [round(k * st, 10) for k in range(math.ceil(lo / st - 1e-9), math.floor(hi / st + 1e-9) + 1)]
        if MIN_TICKS <= len(t) <= MAX_TICKS:
            return t
    return [round(lo, 4), round(hi, 4)]


def _symlog(linthresh: float):
    return SymmetricalLogTransform(10, linthresh, LINSCALE)


def ranges(d: Mapping) -> list[dict]:
    """Per panel the drawn ranges {x: (lo, hi), y: (lo, hi), symlog: linthresh or None} (panel_ranges)."""
    return [panel_ranges(d, p["keys"], p.get("symlog")) for p in d["panels"]]


def panel_ranges(d: Mapping, keys: Sequence[str], symlog: float | None = None) -> dict:
    """{x, y, symlog} of a panel's data (Sublet's origin, the medians and the interval ends), an interval end beyond
    CLIP_FACTOR times the panel's largest median difference left out (clipped), with PAD on each side (for a symlog
    y axis, PAD of the transformed span)."""
    out = {"symlog": symlog}
    for ax_name, f in (("x", "dr"), ("y", "dw")):
        meds = [0.0] + [d["points"][k][f]["median"] for k in keys if d["points"][k][f]["median"] is not None]
        big = max(abs(v) for v in meds) or 1e-3
        ends = [v for k in keys for v in (d["points"][k][f]["lo"], d["points"][k][f]["hi"])
                if v is not None and abs(v) <= CLIP_FACTOR * big]
        lo, hi = min(meds + ends), max(meds + ends)
        if ax_name == "y" and symlog:
            tf = _symlog(symlog)
            a, b = tf.transform_non_affine(np.array([lo, hi], dtype=float))
            span = max(b - a, 1e-6)
            lo, hi = (float(v) for v in tf.inverted().transform_non_affine(np.array([a - PAD * span,
                                                                                    b + PAD * span])))
        else:
            span = max(hi - lo, 1e-4)
            lo, hi = lo - PAD * span, hi + PAD * span
        out[ax_name] = (lo, hi)
    return out


def y_ticks(r: Mapping, height_pt: float) -> list[float]:
    """The y ticks of a panel: linear, the first step of Y_STEPS with MIN_TICKS to MAX_TICKS ticks; symlog, 0, the
    linear part's ends +-linthresh and the powers of 10 beyond, in that priority, each kept where its label is at
    least Y_TICK_GAP_PT from every kept one (the panel's height `height_pt`)."""
    y0, y1 = r["y"]
    lt = r.get("symlog")
    if not lt:
        return _steps(y0, y1, Y_STEPS)
    tf = _symlog(lt)
    a, b = tf.transform_non_affine(np.array([y0, y1], dtype=float))
    per_pt = height_pt / (b - a)
    cand = [0.0, lt, -lt]
    k = math.floor(math.log10(lt)) + 1
    while 10.0 ** k <= max(abs(y0), abs(y1)):
        cand += [10.0 ** k, -(10.0 ** k)]
        k += 1
    kept: list[float] = []
    for v in cand:
        if not y0 <= v <= y1:
            continue
        pos = float(tf.transform_non_affine(np.array([v]))[0]) * per_pt
        if all(abs(pos - float(tf.transform_non_affine(np.array([u]))[0]) * per_pt) >= Y_TICK_GAP_PT for u in kept):
            kept.append(round(v, 10))
    return sorted(kept)


def _tick_room(ax, ticks: Sequence[float], height_pt: float) -> None:
    """Raise the y axis top so that the highest tick lies at least TOP_TICK_PT below it (its label then stays clear of
    the panel title); the drawn data keep the panel's range."""
    if not ticks:
        return
    y0, y1 = ax.get_ylim()
    tf = ax.yaxis.get_transform()
    a, b, t = (float(v) for v in tf.transform(np.array([y0, y1, max(ticks)])))
    per_pt = (b - a) / height_pt
    if b - t < TOP_TICK_PT * per_pt:
        k = TOP_TICK_PT / height_pt
        new_b = (t - k * a) / (1.0 - k)
        ax.set_ylim(y0, float(tf.inverted().transform(np.array([new_b]))[0]))


def name_of(key: str) -> str:
    lab = style.POLICIES[key].label
    return lab[len(A9_PREFIX):] if key != "a9" and lab.startswith(A9_PREFIX) else lab


def _sig(d: Mapping, key: str) -> tuple | None:
    """(median, lo, hi) of Delta r0 and Delta W0, a missing end as the median; Sublet's origin all 0; None without
    a median."""
    if key == REF:
        return (0.0,) * 6
    out = []
    for f in ("dr", "dw"):
        s = d["points"][key][f]
        if s["median"] is None:
            return None
        out += [s["median"], s["median"] if s["lo"] is None else s["lo"], s["median"] if s["hi"] is None else s["hi"]]
    return tuple(out)


def name_groups(d: Mapping, keys: Sequence[str]) -> list[list[str]]:
    """The panel's points (Sublet's origin first, then the registry's legend order) in groups whose medians and
    interval ends agree within COINCIDE_TOL: one name and one leader per group."""
    groups: list[tuple[tuple, list[str]]] = []
    for k in [REF] + [x for x in style.legend_order(keys) if x != REF]:
        s = _sig(d, k)
        if s is None:
            continue
        for g in groups:
            if all(abs(a - b) <= COINCIDE_TOL for a, b in zip(g[0], s)):
                g[1].append(k)
                break
        else:
            groups.append((s, [k]))
    return [g for _, g in groups]


def group_text(d: Mapping, group: Sequence[str], panel: str) -> str:
    """A group's name: the first point's name, each coinciding point's on its own line after SAME, and for a point
    with weeks right of the drawn range (beyond) their count and Delta r0 on a line of its own."""
    lines = [name_of(group[0])] + [SAME + name_of(k) for k in group[1:]]
    for b in d.get("beyond") or []:
        if b["key"] in group and b["panel"] == panel:
            lines.append(f"{len(b['weeks'])} of {b['n_weeks']} weeks at $\\Delta r_0$ {_span_text(b['dr'], '–')}")
    return "\n".join(lines)


def draw_points(ax, d: Mapping, keys: Sequence[str], xr: tuple, yr: tuple) -> None:
    pts = d["points"]
    for k in style.legend_order(keys):
        p = pts[k]
        x, y = p["dr"]["median"], p["dw"]["median"]
        if x is None or y is None:
            continue
        for ax_name, f, lim in (("x", "dr", xr), ("y", "dw", yr)):
            lo, hi = p[f]["lo"], p[f]["hi"]
            if lo is None or hi is None or hi <= lo:
                continue
            a, b = max(lo, lim[0]), min(hi, lim[1])
            if ax_name == "x":
                style.errorbars(ax, k, [x], [y], [a], [b], orientation="x")
            else:
                style.errorbars(ax, k, [x], [y], [a], [b])
            for end, v, at in (("lo", lo, a), ("hi", hi, b)):
                if (end == "lo" and v < lim[0]) or (end == "hi" and v > lim[1]):
                    clip_mark(ax, k, (at, y) if ax_name == "x" else (x, at), ax_name, end)
        style.scatter_policy(ax, k, [x], [y])


def clip_mark(ax, key: str, at: tuple, ax_name: str, end: str) -> None:
    """An arrowhead at the clipped end of an interval bar, pointing out of the drawn range (the end value is in the
    caption: a number at the spine's end reads as part of the name beside it)."""
    c = style.policy(key).text_color
    sign = 1.0 if end == "hi" else -1.0
    dx, dy = (5.0 * sign, 0.0) if ax_name == "x" else (0.0, 5.0 * sign)
    a = ax.annotate("", xy=at, xytext=(-dx, -dy), textcoords="offset points",
                    arrowprops=dict(arrowstyle="-|>,head_length=0.4,head_width=0.2", color=c,
                                    linewidth=style.UNCERTAINTY_PT, shrinkA=0.0, shrinkB=0.0),
                    annotation_clip=False, zorder=style.Z_DATA + 0.1)
    a._sublet_role = "clip_arrow"


def _crosses(p1, p2, q1, q2) -> bool:
    """Whether the segments p1-p2 and q1-q2 cross (display coordinates; touching ends count)."""
    def orient(a, b, c):
        v = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
        return 0 if abs(v) < 1e-9 else (1 if v > 0 else -1)
    o1, o2, o3, o4 = orient(p1, p2, q1), orient(p1, p2, q2), orient(q1, q2, p1), orient(q1, q2, p2)
    return o1 * o2 <= 0 and o3 * o4 <= 0 and not (o1 == o2 == 0)


def _near(p1, p2, c, rad) -> bool:
    """Whether the segment p1-p2 passes within `rad` of the point c (display coordinates)."""
    (x1, y1), (x2, y2) = p1, p2
    dx, dy = x2 - x1, y2 - y1
    t = 0.0 if dx == dy == 0 else max(0.0, min(1.0, ((c[0] - x1) * dx + (c[1] - y1) * dy) / (dx * dx + dy * dy)))
    return math.hypot(x1 + t * dx - c[0], y1 + t * dy - c[1]) < rad


# ---------------------------------------------------------------------------------------------------------------
# C62: the names beside their points where the space is free, the others in the column with leaders
NAME_GAP_PT = 2.0               # a name beside its point starts this far beyond the point's marker or interval bar
NAME_CLEAR_PT = 1.5             # the least gap between a name or a leader and a mark it does not belong to
NAME_SEP_PT = 1.0               # the least gap between two names
AMBIG_PT = 8.0                  # a name right or left of its point keeps this much room free of other points beyond it
PLACES = ("right", "above_right", "below_right", "left")   # a name's places beside its point, in preference order
COLUMN = "column"               # ... and the column right of the data, last
PLACE_COST = {**{p: i for i, p in enumerate(PLACES)}, COLUMN: 2 * len(PLACES)}
MAX_PLACES = 2                  # the search tries at most this many free places beside a point (then the column)
ARROW_HALF_PT = 1.6             # half the width of an arrowhead (style.arrow, clip_mark), as an obstacle
COLUMN_BELOW_PT = 9.0           # a column name may reach this far below the axes (right of the x spine's end no tick
#                                 label lies there), so that a clipped point's two-line name has its first line at its
#                                 arrow on the zero line


class _Marks:
    """The marks of a panel as obstacles, in display pixels: circles (center, radius, owner) and segments (p, q, half
    width, owner); owner is the name group of the point that drew the mark (None for an arrow or a zero line)."""

    def __init__(self):
        self.circles: list = []
        self.segments: list = []

    def footprint(self, owner) -> tuple[float, float, float, float]:
        """(x0, y0, x1, y1) of every mark of `owner`."""
        xs, ys = [], []
        for (cx, cy), rad, o in self.circles:
            if o == owner:
                xs += [cx - rad, cx + rad]
                ys += [cy - rad, cy + rad]
        for p, q, hw, o in self.segments:
            if o == owner:
                xs += [p[0] - hw, p[0] + hw, q[0] - hw, q[0] + hw]
                ys += [p[1] - hw, p[1] + hw, q[1] - hw, q[1] + hw]
        return min(xs), min(ys), max(xs), max(ys)


def _marks(ax, d: Mapping, panel: Mapping, r: Mapping, groups: Sequence[Sequence[str]]) -> _Marks:
    """The panel's marks (_Marks): every point's marker and drawn interval bars (clipped to the panel's ranges) and its
    clip arrows, owned by its name group; the transplant arrows and the two zero lines, owned by none."""
    px = ax.figure.dpi / 72.0
    m = _Marks()
    owner = {k: tuple(g) for g in groups for k in g}
    keys = [REF, *panel["keys"]]
    tr = ax.transData.transform
    cuts = {(c["key"], c["axis"], c["end"]) for c in clipped(d)}
    for k in keys:
        if k not in owner:
            continue
        o = owner[k]
        rad = 0.5 * (style.policy(k).markersize + style.MARKER_EDGE_PT) * px
        if k == REF:
            m.circles.append((tuple(tr((0.0, 0.0))), rad, o))
            continue
        p = d["points"][k]
        x, y = p["dr"]["median"], p["dw"]["median"]
        if x is None or y is None:
            continue
        m.circles.append((tuple(tr((x, y))), rad, o))
        for f, lim in (("dr", r["x"]), ("dw", r["y"])):
            lo, hi = p[f]["lo"], p[f]["hi"]
            if lo is None or hi is None or hi <= lo:
                continue
            a, b = max(lo, lim[0]), min(hi, lim[1])
            ends = [(a, y), (b, y)] if f == "dr" else [(x, a), (x, b)]
            m.segments.append((tuple(tr(ends[0])), tuple(tr(ends[1])), 0.5 * style.UNCERTAINTY_PT * px, o))
            for end, at in (("lo", ends[0]), ("hi", ends[1])):
                if (k, f, end) in cuts:                  # the clip arrow beyond the bar's end
                    tip = np.asarray(tr(at), dtype=float)
                    back = np.array([-5.0, 0.0] if f == "dr" else [0.0, -5.0]) * px * (1 if end == "hi" else -1)
                    m.segments.append((tuple(tip + back), tuple(tip), ARROW_HALF_PT * px, o))
    for a, b in d["arrows"]:
        if a in panel["keys"] and b in panel["keys"]:
            pa, pb = d["points"][a], d["points"][b]
            m.segments.append((tuple(tr((pa["dr"]["median"], pa["dw"]["median"]))),
                               tuple(tr((pb["dr"]["median"], pb["dw"]["median"]))), ARROW_HALF_PT * px, None))
    (x0, x1), (y0, y1) = r["x"], ax.get_ylim()
    for p, q in (((x0, 0.0), (x1, 0.0)), ((0.0, y0), (0.0, y1))):
        m.segments.append((tuple(tr(p)), tuple(tr(q)), 0.5 * style.REFERENCE_PT * px, None))
    return m


def _seg_dist(p, q, a, b) -> float:
    """The least distance between the segments p-q and a-b (display coordinates; 0 where they cross)."""
    if _crosses(p, q, a, b):
        return 0.0

    def pt_seg(c, u, v):
        (x1, y1), (x2, y2) = u, v
        dx, dy = x2 - x1, y2 - y1
        t = 0.0 if dx == dy == 0 else max(0.0, min(1.0, ((c[0] - x1) * dx + (c[1] - y1) * dy) / (dx * dx + dy * dy)))
        return math.hypot(x1 + t * dx - c[0], y1 + t * dy - c[1])

    return min(pt_seg(p, a, b), pt_seg(q, a, b), pt_seg(a, p, q), pt_seg(b, p, q))


def _box_segs(box) -> list:
    x0, y0, x1, y1 = box
    return [((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))]


def _box_hits_seg(box, p, q, clear: float) -> bool:
    """Whether the segment p-q comes within `clear` of the box (inside it or nearer than `clear` to an edge)."""
    x0, y0, x1, y1 = box
    if any(x0 <= c[0] <= x1 and y0 <= c[1] <= y1 for c in (p, q)):
        return True
    return any(_seg_dist(p, q, a, b) < clear for a, b in _box_segs(box))


def _box_hits_circle(box, c, rad: float) -> bool:
    x0, y0, x1, y1 = box
    return math.hypot(max(x0 - c[0], 0.0, c[0] - x1), max(y0 - c[1], 0.0, c[1] - y1)) < rad


def _boxes_meet(a, b, sep: float) -> bool:
    return not (a[2] + sep <= b[0] or b[2] + sep <= a[0] or a[3] + sep <= b[1] or b[3] + sep <= a[1])


def _box_free(box, marks: _Marks, clear: float, skip=None) -> bool:
    """Whether the box keeps `clear` from every mark not owned by `skip`."""
    return (not any(_box_hits_circle(box, c, rad + clear) for c, rad, o in marks.circles if o != skip or skip is None)
            and not any(_box_hits_seg(box, p, q, hw + clear) for p, q, hw, o in marks.segments
                        if o != skip or skip is None))


def _leader_free(p, q, marks: _Marks, owner, boxes: Sequence, clear: float) -> bool:
    """Whether the leader p-q keeps `clear` from every mark of another group and from the names' boxes `boxes`."""
    for c, rad, o in marks.circles:
        if o != owner and _seg_dist(p, q, c, c) < rad + clear:
            return False
    for a, b, hw, o in marks.segments:
        if o != owner and _seg_dist(p, q, a, b) < hw + clear:
            return False
    return not any(_box_hits_seg(bx, p, q, clear) for bx in boxes)


def _place_boxes(point, rad: float, foot, w: float, h: float, gap: float) -> dict:
    """The boxes (x0, y0, x1, y1) of a w x h name beside a point (display coordinates) whose marker of radius `rad`
    and interval bars fill the footprint `foot`: right of the footprint and left of it, centered on the point; above
    and below the marker, starting `gap` right of it."""
    (cx, cy), (fx0, fy0, fx1, fy1) = point, foot
    xr = cx + rad + gap
    return {"right": (fx1 + gap, cy - 0.5 * h, fx1 + gap + w, cy + 0.5 * h),
            "above_right": (xr, cy + rad + 0.5 * gap, xr + w, cy + rad + 0.5 * gap + h),
            "below_right": (xr, cy - rad - 0.5 * gap - h, xr + w, cy - rad - 0.5 * gap),
            "left": (fx0 - gap - w, cy - 0.5 * h, fx0 - gap, cy + 0.5 * h)}


def name_column(ax, d: Mapping, panel: Mapping, x_end: float, r: Mapping | None = None) -> None:
    """The names of the panel's point groups (name_groups, group_text). C62: a name sits beside its point (PLACES:
    right of its marker and interval bars, above or below its marker, or left of them) where that place lies inside the
    axes, keeps NAME_CLEAR_PT from every mark (markers, interval bars, arrows, the zero lines) and NAME_SEP_PT from the
    other names, and, right or left of the point, has AMBIG_PT free of other points beyond it (a name between two
    points on one row reads as either's); the other names go to the column LABEL_GAP_PT right of the x spine's end
    (x_end), stacked by their points' heights (common.stack_labels within the axes, reaching COLUMN_BELOW_PT below
    them; a clipped point's name with its first line at its arrow), each with a grey leader from just
    left of the name to its point that moves by the least shift up to LEADER_SHIFT_PT (steps of 0.5 pt) that keeps
    NAME_CLEAR_PT from the other groups' marks and the names. The places are chosen together: the assignment of least
    PLACE_COST (beside a point before the column, then in PLACES' order) whose names are apart and whose column
    leaders are clear, at most MAX_PLACES free places per point tried. Where a point's Delta r0 bar is clipped at the
    spine's end, its arrowhead points into the column at the point's height: there lies its own name and no other.
    `r`: the panel's ranges (the drawn bars). Call once the axes limits are final. Each name's `_sublet_place` is its
    place; a column name's leader is a Text with `_sublet_role` "leader", except for a name at its point's clip arrow
    (`_sublet_at_arrow`), which the arrow joins to its point (as built until C62 every name was in the column with a
    leader, and leaders crossed other points' bars in (b))."""
    fig = ax.figure
    rend = fig.canvas.get_renderer()
    px = fig.dpi / 72.0
    to_pt = 1.0 / px
    pts = d["points"]
    r = r or panel_ranges(d, panel["keys"], panel.get("symlog"))
    groups = name_groups(d, panel["keys"])
    marks = _marks(ax, d, panel, r, groups)
    bb = ax.get_window_extent(rend)
    inside = (bb.x0 + 0.5 * px, bb.y0 + 0.5 * px, bb.x1 - 0.5 * px, bb.y1 - 0.5 * px)
    tr = ax.transData.transform
    items = []
    for g in groups:
        k = g[0]
        x, y = (0.0, 0.0) if k == REF else (pts[k]["dr"]["median"], pts[k]["dw"]["median"])
        t = style.direct_label(ax, k, x, y, text=group_text(d, g, panel["letter"]), dx=0.0, dy=0.0, ha="left",
                               va="bottom")
        t.set_multialignment("left")
        t._sublet_role = "name"
        t._sublet_keys = tuple(g)
        tb = t.get_window_extent(rend)
        rad = max(0.5 * (style.policy(q).markersize + style.MARKER_EDGE_PT) for q in g) * px
        own = tuple(g)
        cands = []
        for place, box in _place_boxes(tuple(tr((x, y))), rad, marks.footprint(own), tb.width, tb.height,
                                       NAME_GAP_PT * px).items():
            if not (box[0] >= inside[0] and box[1] >= inside[1] and box[2] <= inside[2] and box[3] <= inside[3]):
                continue
            if not _box_free(box, marks, NAME_CLEAR_PT * px):
                continue
            if place in ("right", "left"):
                reach = AMBIG_PT * px
                wide = (box[0], box[1], box[2] + reach, box[3]) if place == "right" else \
                    (box[0] - reach, box[1], box[2], box[3])
                if not _box_free(wide, marks, 0.0, skip=own):
                    continue
            cands.append((place, box))
        items.append({"keys": own, "x": x, "y": y, "text": t, "w": tb.width, "h": tb.height, "rad": rad,
                      "options": cands[:MAX_PLACES] + [(COLUMN, None)]})
    cut = {c["key"] for c in clipped(d) if c["axis"] == "dr" and c["end"] == "hi"}
    x_col = tr((x_end, 0.0))[0] + LABEL_GAP_PT * px
    best = None
    combos = sorted(itertools.product(*[range(len(it["options"])) for it in items]),
                    key=lambda c: (sum(PLACE_COST[it["options"][j][0]] for it, j in zip(items, c)), c))
    for combo in combos:
        cost = sum(PLACE_COST[it["options"][j][0]] for it, j in zip(items, combo))
        if best is not None and cost > best[0]:
            break
        direct = [(i, items[i]["options"][j][1]) for i, j in enumerate(combo) if items[i]["options"][j][0] != COLUMN]
        if any(_boxes_meet(a, b, NAME_SEP_PT * px) for (_, a), (_, b) in itertools.combinations(direct, 2)):
            continue
        col = [i for i, j in enumerate(combo) if items[i]["options"][j][0] == COLUMN]
        placed = _column(items, col, x_col, inside, cut, marks, [b for _, b in direct], px)
        if placed is None:
            continue
        boxes, unclear = placed
        if best is None or unclear < best[2]:
            best = (cost, combo, unclear, boxes)
        if unclear == 0:
            break
    if best is None:
        raise style.StyleError(f"{NAME} ({panel['letter']}): no place for the names")
    _, combo, _, boxes = best
    inv = ax.transData.inverted()
    for i, (it, j) in enumerate(zip(items, combo)):
        place, box = it["options"][j]
        t, (x, y) = it["text"], (it["x"], it["y"])
        p = tr((x, y))
        if place != COLUMN:
            t.xyann = ((box[0] - p[0]) * to_pt, (box[1] - p[1]) * to_pt)
            t._sublet_place = place
            continue
        box = boxes[i]
        t.xyann = ((box[0] - p[0]) * to_pt, (box[1] - p[1]) * to_pt)
        t._sublet_place = COLUMN
        lines = t.get_text().count("\n") + 1
        tip = tr((x, y))[1]
        t._sublet_at_arrow = bool(set(it["keys"]) & cut) and box[1] <= tip <= box[3]
        if t._sublet_at_arrow:                       # its clip arrow points at its first line: no leader beside it
            continue
        start = inv.transform((box[0] - 1.5 * px, 0.5 * (box[1] + box[3])))
        ld = ax.annotate("", xy=(x, y), xytext=tuple(start), textcoords="data",
                         arrowprops=dict(arrowstyle="-", color=LEADER_GREY, linewidth=LEADER_PT, shrinkA=0.0,
                                         shrinkB=(it["rad"] + 0.8 * px) * to_pt), zorder=style.Z_REFERENCE + 0.2)
        ld._sublet_role = "leader"


def _column(items: Sequence[Mapping], col: Sequence[int], x_col: float, inside, cut: set, marks: _Marks,
            direct: Sequence, px: float):
    """The column's boxes {item: box} for the items `col` (display coordinates), stacked by their points' heights
    within `inside`, reaching COLUMN_BELOW_PT below it (common.stack_labels; a clipped point's name with its first line
    at its arrow, alone there), each moved by the least shift up to LEADER_SHIFT_PT whose leader is clear
    (_leader_free), and the number of leaders left unclear; None where a column name meets a name beside its point."""
    if not col:
        return {}, 0
    tr = None
    tips, targets, hs = [], [], []
    owners = [n for n, i in enumerate(col) if set(items[i]["keys"]) & cut]
    for n, i in enumerate(col):
        it = items[i]
        ax = it["text"].axes
        tr = ax.transData.transform
        tips.append(tr((it["x"], it["y"]))[1])
        hs.append(it["h"])
        lines = it["text"].get_text().count("\n") + 1
        # C62: a clipped point's name aims its first line at the arrow (as built, its box's middle)
        targets.append(tips[-1] - (0.5 * it["h"] * (1.0 - 1.0 / lines) if n in owners else 0.0))
    gap = 0.6 * px
    floor = inside[1] - COLUMN_BELOW_PT * px
    stack = dict(gap=gap, bottom=floor, top=inside[3])
    centers = stack_labels(targets, hs, **stack)

    def on_arrow(n: int, cs) -> bool:
        return abs(cs[n] - tips[n]) <= 0.5 * hs[n] and all(
            abs(cs[m] - tips[n]) > 0.5 * hs[m] for m in range(len(col)) if m != n)

    for n in owners:
        if on_arrow(n, centers):
            continue
        for eps in (-1e-6, 1e-6):
            cs = stack_labels([v + (eps if m == n else 0.0) for m, v in enumerate(targets)], hs, **stack)
            if on_arrow(n, cs):
                centers = cs
                break

    def box(n: int, c: float):
        it = items[col[n]]
        return (x_col, c - 0.5 * hs[n], x_col + it["w"], c + 0.5 * hs[n])

    if any(_boxes_meet(box(n, c), b, NAME_SEP_PT * px) for n, c in enumerate(centers) for b in direct):
        return None
    steps = [0.0] + [s * v for v in np.arange(0.5, LEADER_SHIFT_PT + 1e-9, 0.5) for s in (-1.0, 1.0)]
    unclear = 0
    for n in range(len(col)):
        it = items[col[n]]
        tgt = tuple(tr((it["x"], it["y"])))
        ok = False
        for dv in steps:
            c = centers[n] + dv * px
            bx = box(n, c)
            if bx[1] < floor or bx[3] > inside[3] or any(
                    abs(c - centers[m]) < 0.5 * (hs[n] + hs[m]) + gap - 1e-9 for m in range(len(col)) if m != n):
                continue
            if any(_boxes_meet(bx, b, NAME_SEP_PT * px) for b in direct):
                continue
            if n in owners and on_arrow(n, centers) and abs(c - tips[n]) > 0.5 * hs[n]:
                continue
            others = [box(m, centers[m]) for m in range(len(col)) if m != n] + list(direct)
            if _leader_free((x_col - 1.5 * px, c), tgt, marks, it["keys"], others, NAME_CLEAR_PT * px):
                centers[n] = c
                ok = True
                break
        unclear += not ok
    return {col[n]: box(n, centers[n]) for n in range(len(col))}, unclear


def draw(data: Mapping) -> Any:
    fig = style.new_figure(NAME)
    lab = data["labels"]
    panels = data["panels"]
    rs = ranges(data)
    h_pt = (fig.get_size_inches()[1] - style.MARGIN_BOTTOM - style.MARGIN_TOP) * style.BP_PER_IN
    yts = [y_ticks(r, h_pt) for r in rs]
    # C62: each panel's y axis labeled, as its x axis is (each panel has its own scale; as built, (b)'s had no label)
    left = [style.ytick_reserve(fig, [style.PLAIN(v) for v in yt], ylabel=True) for yt in yts]
    widths_lab = [max(text_width_in(fig, group_text(data, g, p["letter"])) for g in name_groups(data, p["keys"]))
                  for p in panels]
    avail = style.W2 - sum(left) - style.MARGIN_RIGHT
    col = [w + (LABEL_GAP_PT + LABEL_RIGHT_PT) / 72.0 for w in widths_lab]
    data_ws = [(avail - sum(col)) * s for s in DATA_SHARE]
    if min(data_ws) < 1.0:
        raise style.StyleError(f"{NAME}: {min(data_ws):.2f} in left for a panel's data")
    widths = [w + c for w, c in zip(data_ws, col)]
    axes = style.panel_row(fig, widths, sharey=[False] * len(panels), left=left)
    for ax, p, r, yt, c, data_w in zip(axes, panels, rs, yts, col, data_ws):
        (x0, x1), yr = r["x"], r["y"]
        frac = c / (data_w + c)
        ax.set_xlim(x0, x1 + (x1 - x0) * frac / (1.0 - frac))
        if r["symlog"]:
            ax.set_yscale("symlog", linthresh=r["symlog"], linscale=LINSCALE)
            ax.yaxis.set_minor_locator(NullLocator())
        ax.set_ylim(*yr)
        _tick_room(ax, yt, h_pt)
        ax.spines["bottom"].set_bounds(x0, x1)
        ax.xaxis.set_major_locator(FixedLocator(_steps(x0, x1, X_STEPS)))
        ax.xaxis.set_major_formatter(style.PLAIN)
        ax.yaxis.set_major_locator(FixedLocator(yt))
        ax.yaxis.set_major_formatter(style.PLAIN)
        (hz,) = ax.plot([x0, x1], [0.0, 0.0], color=style.REFERENCE_GREY, linewidth=style.REFERENCE_PT,
                        zorder=style.Z_REFERENCE, label="_nolegend_")
        hz._sublet_role = "reference"
        (ln,) = ax.plot([0.0, 0.0], list(yr), color=style.REFERENCE_GREY, linewidth=style.REFERENCE_PT,
                        zorder=style.Z_REFERENCE, label="_nolegend_")
        ln._sublet_role = "reference"
        for a, b in data["arrows"]:
            if a in p["keys"] and b in p["keys"]:
                pa, pb = data["points"][a], data["points"][b]
                ar = style.arrow(ax, (pa["dr"]["median"], pa["dw"]["median"]),
                                 (pb["dr"]["median"], pb["dw"]["median"]), color=style.policy(a).label_color,
                                 shrinkA=3.5, shrinkB=3.5)
                ar._sublet_role = "arrow"
        style.scatter_policy(ax, REF, [0.0], [0.0])
        draw_points(ax, data, p["keys"], (x0, x1), yr)
        ax.set_xlabel(lab["x"])
        ax.xaxis.label.set_x(0.5 * (1.0 - frac))
    for ax in axes:
        ax.set_ylabel(lab["y"])
    align_baselines([ax.xaxis.label for ax in axes])
    for ax, p, r in zip(axes, panels, rs):
        name_column(ax, data, p, r["x"][1], r)
    letters = style.panel_letters(axes)
    for ax, letter, p in zip(axes, letters, panels):
        L.caption_title(ax, letter, p["title"])
    return fig

# ---------------------------------------------------------------------------------------------------------------
# tables' data
def weeks_table(main: Mapping) -> dict:
    t, w0 = main["table"], need(main, "W0", "0", what=L.MAIN)
    tags = [x for x in L.E7_TAGS if x in t] + sorted(x for x in t if x not in L.E7_TAGS)
    weeks = L.weeks_of(t, tags, [L.TRACE])
    rows = []
    for tag in tags:
        r0 = [L.val(t, tag, L.TRACE, w) for w in weeks]
        wv = [(w0.get(tag) or {}).get(w) for w in weeks]
        rows.append({"tag": tag, "key": L.KEY_OF_TAG[tag], "label": L.label(tag),
                     "r0": {"values": r0, **L.med_ci(r0)}, "W0": {"values": wv, **L.med_ci(wv)}})
    return {"weeks": weeks, "rows": rows,
            "scope": {"tags": tags, "weeks": weeks, "measures": ["r0 under L-tr", "W0"], "seeds": [0],
                      "parts": ["main"], "stress_modes": list(L.STRESS)}}


def _w0(main: Mapping, tag: str, w: str):
    return ((need(main, "W0", "0", what=L.MAIN).get(tag)) or {}).get(w)


def pareto_table(main: Mapping, an: Mapping) -> dict:
    front = need(an, "reported", "pareto_front", what=L.ANALYSIS)
    t = main["table"]
    tags = [x for x in MA.PARETO_TAGS if x in t]
    rows = []
    for w in sorted(front, key=int):
        pt = {x: (L.val(t, x, L.TRACE, w), _w0(main, x, w)) for x in tags}
        s = pt.get("Sublet")
        dom = [x for x, (a, b) in pt.items() if x != "Sublet" and None not in (a, b) and s and None not in s
               and a <= s[0] and b <= s[1] and (a < s[0] or b < s[1])]
        rows.append({"week": w, "front": [{"tag": x, "label": L.label(x), "r0": pt[x][0], "W0": pt[x][1]}
                                          for x in front[w]],
                     "sublet_on_front": "Sublet" in front[w], "sublet": {"r0": s[0] if s else None,
                                                                         "W0": s[1] if s else None},
                     "dominated_by": [{"tag": x, "label": L.label(x), "dr0": s[0] - pt[x][0], "dW0": s[1] - pt[x][1]}
                                      for x in dom]})
    left_out = [x for x in L.E7_TAGS if x in t and x not in tags]
    return {"rows": rows, "tags": tags,
            "left_out": [{"tag": x, "label": L.label(x), "kind": m5.tag(x).kind, "policy_id": m5.tag(x).id}
                         for x in left_out],
            "scope": {"weeks": [r["week"] for r in rows], "tags": tags, "candidates": tags,
                      "measures": ["r0 under L-tr", "W0"], "seeds": [0]}}


def rc_table(parts: Mapping, an: Mapping) -> dict:
    rc = need(an, "reported", "RC", what=L.ANALYSIS)
    runs = {}
    for p in ("main", "seeds", "second"):
        for r in parts[p].get("runs") or []:
            if r.get("kind") == "week":
                runs[(r["tag"], r["mode"], str(r["cell"]), str(r["seed"]))] = r
    tags = [x for x in L.E7_TAGS if x in rc] + sorted(x for x in rc if x not in L.E7_TAGS)
    rows = []
    for tag in tags:
        modes = [m for m in MODE_ORDER if m in rc[tag]] + sorted(m for m in rc[tag] if m not in MODE_ORDER)
        for seeds in (("0",), ("1", "2")):
            for m in modes:
                vals = [(w, s, v) for w, by_s in sorted(rc[tag][m].items(), key=lambda kv: int(kv[0]))
                        for s, v in by_s.items() if s in seeds]
                if not vals:
                    continue
                det = []
                for w, s, v in vals:
                    r = runs.get((tag, m, w, s)) or {}
                    det.append([w, int(s), v, r.get("fallback_usd"), r.get("stranding_usd"),
                                r.get("fallback_share_after_reclaims")])
                rows.append({"tag": tag, "label": L.label(tag), "mode": m, "seeds": [int(s) for s in seeds],
                             "rc": L.med_ci(v for *_, v in vals),
                             "fallback_usd": _median(x[3] for x in det), "stranding_usd": _median(x[4] for x in det),
                             "share_after_reclaims": _median(x[5] for x in det), "runs": det})
    weeks: dict = {}
    for r in rows:
        part = "main" if r["mode"] in MODE_ORDER[:1 + len(L.STRESS)] else "second"
        weeks.setdefault(part, set()).update(x[0] for x in r["runs"])
    return {"rows": rows, "same_modes": same_modes(rc),
            "scope": {"tags": tags, "modes": sorted({r["mode"] for r in rows}, key=_mode_key),
                      "seeds": sorted({s for r in rows for s in r["seeds"]}),
                      "weeks": {k: sorted(v, key=int) for k, v in sorted(weeks.items())},
                      "n_runs": sum(len(r["runs"]) for r in rows)}}


# the lenders that announce every revocable lease when its guaranteed period ends (sublet/lender.py: 'adaptive' adds
# the slot at which a lease's guaranteed period ends, 'eager' and iid_step at p = 1 announce every slot)
SAME_MODES = ("L-ad", "L-eg", "L-iid-1")


def same_modes(rc: Mapping) -> dict | None:
    """Whether the RC of every tag run under all of SAME_MODES agrees across them on every week where all of them ran
    (policy seed 0): {modes, weeks, n_tags, equal}; None where no tag has them all."""
    tags = [t for t in rc if all(m in rc[t] for m in SAME_MODES)]
    weeks = sorted({w for t in tags for w in rc[t][SAME_MODES[0]]
                    if all(((rc[t][m].get(w) or {}).get("0")) is not None for m in SAME_MODES)}, key=int)
    if not tags or not weeks:
        return None
    eq = all(abs(rc[t][m][w]["0"] - rc[t][SAME_MODES[0]][w]["0"]) <= 1e-12 for t in tags for m in SAME_MODES
             for w in weeks if all(((rc[t][x].get(w) or {}).get("0")) is not None for x in SAME_MODES))
    return {"modes": list(SAME_MODES), "weeks": weeks, "n_tags": len(tags), "equal": bool(eq)}


RC_RUNS_COLUMNS = ("policy", "tag", "lender_mode", "week", "policy_seed", "rc", "fallback_usd", "stranding_usd",
                   "fallback_share_after_reclaims")


def _csv_num(v, fmt: str) -> str:
    return "" if v is None else format(float(v), fmt)


def rc_runs_csv(t: Mapping) -> str:
    """The data file RC_RUNS: one line per run of e7v2_rc (its rows' `runs`): the policy's registry label (plain
    text), tag, lender mode, week, policy seed, RC (6 decimals), the fallback and stranding totals (USD, 2 decimals)
    and MS4's fallback share after reclaims (6 decimals)."""
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(RC_RUNS_COLUMNS)
    for r in t["rows"]:
        for week, seed, v, fb, st, sh in r["runs"]:
            w.writerow([L.plain_label(r["label"]), r["tag"], r["mode"], week, seed, _csv_num(v, ".6f"),
                        _csv_num(fb, ".2f"), _csv_num(st, ".2f"), _csv_num(sh, ".6f")])
    return buf.getvalue()


def rc_runs_entry(t: Mapping) -> dict:
    """The extract's entry of RC_RUNS: its file, columns, number of rows and sha256 (of rc_runs_csv, which the after
    hook writes from e7v2_rc's rows) and e7v2_rc's scope."""
    text = rc_runs_csv(t)
    return {"file": RC_RUNS, "columns": list(RC_RUNS_COLUMNS), "n_rows": text.count("\n") - 1,
            "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(), "scope": dict(t["scope"])}


def _mode_key(m: str) -> tuple:
    return (MODE_ORDER.index(m) if m in MODE_ORDER else len(MODE_ORDER), m)


def _median(vals):
    v = [float(x) for x in vals if x is not None]
    return statistics.median(v) if v else None


def seeds_table(main: Mapping, seeds: Mapping, an: Mapping) -> dict:
    st, mt = seeds["table"], main["table"]
    tags = [x for x in L.E7_TAGS if x in st]
    weeks = L.weeks_of(st, tags)
    sd = sorted({int(s) for by_m in st.values() for by_c in by_m.values() for by_s in by_c.values() for s in by_s})
    all_seeds = [0] + [s for s in sd if s != 0]
    modes = [m for m in m5.conf_modes() if any(m in st[x] for x in tags)]
    rc = need(an, "reported", "RC", what=L.ANALYSIS)
    rows = []
    for tag in tags:
        lines = []
        for m in modes:
            vals = {w: {str(s): L.val(mt if s == 0 else st, tag, m, w, s) for s in all_seeds} for w in weeks}
            lines.append({"what": m, "values": vals})
        w0 = {w: {str(s): (_w0(main, tag, w) if s == 0 else
                           ((seeds.get("W0") or {}).get(str(s), {}).get(tag) or {}).get(w)) for s in all_seeds}
              for w in weeks}
        lines.append({"what": "W0", "values": w0})
        rcl = {w: {str(s): ((rc.get(tag) or {}).get(L.TRACE) or {}).get(w, {}).get(str(s)) for s in all_seeds}
               for w in weeks}
        lines.append({"what": "RC L-tr", "values": rcl})
        diffs = [abs(v[str(s)] - v["0"]) for ln in lines for v in ln["values"].values() for s in all_seeds[1:]
                 if v.get(str(s)) is not None and v.get("0") is not None]
        rows.append({"tag": tag, "label": L.label(tag), "lines": lines, "max_diff": max(diffs) if diffs else None,
                     "n_compared": len(diffs), "draws": seed_draws(tag, seeds)})
    return {"weeks": weeks, "seeds": all_seeds, "modes": modes, "rows": rows,
            "scope": {"tags": tags, "weeks": weeks, "seeds": all_seeds, "modes": modes,
                      "measures": ["r0", "W0", "RC under L-tr"]}}


def seed_draws(tag: str, seeds: Mapping) -> dict:
    """What a tag's runs draw from the policy seed (the caption's reason when its seeds agree): seed_free, the tag
    draws no random number (ms5b_common.seed_free); for a guarded tag (A8P, A8), whether its inner policy is
    seed-free and, over its guarded runs of part seeds, how many followed FB at every slot (s_fb_all): the guard's
    other draws are its safe expert's (algos/guard.py, SafeExpert's R), so ms5b_common counts guarded tags as
    drawing."""
    out = {"seed_free": bool(m5.seed_free(tag)), "guarded": bool(m5.is_guarded(tag)), "inner": None,
           "inner_seed_free": None, "runs": 0, "s_fb_all": 0}
    if not out["guarded"]:
        return out
    t = m5.tag(tag)
    try:
        params = m5.PARAM_RULES[t.params](None) if isinstance(t.params, str) else dict(t.params)
    except (TypeError, ValueError, AttributeError):
        params = {}
    inner = params.get("inner")
    out["inner"] = inner
    if inner in m5.TAGS and not params.get("inner_params"):
        out["inner_seed_free"] = bool(m5.seed_free(inner))
    g = [x for x in seeds.get("guarded") or [] if x.get("tag") == tag]
    out["runs"], out["s_fb_all"] = len(g), sum(1 for x in g if x.get("s_fb_all") is True)
    return out


def table3_intervals(inp: Inputs, main: Mapping, second: Mapping, an: Mapping, runs_files: list) -> dict:
    """Table III v2's cells (W2) with their intervals: per tag of T3_TAGS (BL0a analytic) the medians over main's
    weeks (gap: over the gap days of part second), the run files of the total accounting recorded in runs_files."""
    t = main["table"]
    weeks = L.weeks_of(t, ["Sublet"], [L.TRACE])
    rows_by = {(r["tag"], str(r["cell"])): r for r in main.get("runs") or []
               if r.get("kind") == "week" and r.get("mode") == L.TRACE and int(r.get("seed", -1)) == 0}
    w0, rc = need(main, "W0", "0", what=L.MAIN), main.get("RC") or {}
    lp, ratio = second.get("gap_lp") or {}, second.get("gap_ratio") or {}
    days = sorted(lp, key=lambda c: int(c.split(":c")[-1]))
    gap_bl0a = {}
    for r in second.get("runs") or []:
        if r.get("kind") == "gap" and r.get("bl0a_usd") is not None:
            gap_bl0a[r["cell"]] = float(r["bl0a_usd"])
    curves = need(an, "reported", "intensity_curves", what=L.ANALYSIS)
    p_weeks = L.weeks_of(second["table"])
    grid_top = max(float(p) for by_w in curves.values() for c in by_w.values() for p, v in c.get("points") or []
                   if v is not None)
    bl0a_mode = {}                       # BL0a's USD per (week, mode): equal over the rows of a week and mode
    for r in main.get("runs") or []:
        if r.get("kind") == "week" and r.get("bl0a_usd") is not None and r.get("mode") in (L.TRACE, *L.STRESS):
            bl0a_mode.setdefault((str(r["cell"]), r["mode"]), float(r["bl0a_usd"]))
    bl0a_usd, bl0a_total = {}, {}
    rows = []
    for tag in T3_TAGS:
        cells: dict = {}
        if tag == "BL0a":
            for w in weeks:
                r = rows_by.get(("Sublet", w))
                if r is None:
                    raise MissingKey(f"{L.MAIN}: no L-tr run of Sublet in week {w} (for BL0a)")
                bl0a_usd[w] = float(r["bl0a_usd"])
            cells["usd_overflow"] = _cell([bl0a_usd[w] / 1e3 for w in weeks])
            cells["usd_total"] = _cell([bl0a_total[w] / 1e3 for w in weeks] if len(bl0a_total) == len(weeks)
                                       else [])
            # as Table III v2 (figs/table3_v2.py): BL0a's saving over itself (0) and its W0, the largest BL0a USD
            # under a stress mode over its USD under L-tr in the week (1 by definition); no RC and no p* (no runs)
            cells["saving_pct"] = {**_cell([100.0 * (1.0 - bl0a_usd[w] / bl0a_usd[w]) for w in weeks]),
                                   "note": "0 by definition"}
            cells["gap"] = _cell([gap_bl0a[d] / lp[d] for d in days if d in gap_bl0a])
            cells["w0"] = {**_cell([max(bl0a_mode[(w, m)] for m in L.STRESS) / bl0a_mode[(w, L.TRACE)]
                                    for w in weeks]), "note": "1 by definition"}
            for c in ("rc", "p_star"):
                cells[c] = {"median": None, "lo": None, "hi": None, "n": 0, "note": "all-fallback: analytic"}
        else:
            r0 = [L.val(t, tag, L.TRACE, w) for w in weeks]
            usd, tot = [], []
            for w in weeks:
                r = rows_by.get((tag, w))
                if r is None:
                    raise MissingKey(f"{L.MAIN}: no L-tr run of {tag} in week {w}")
                usd.append(r["r0"] * r["bl0a_usd"] / 1e3)
                rec, refs = run_record(inp, r, runs_files)
                tot.append(rec["accountings"]["total_usd"] / 1e3)
                bl0a_total.setdefault(w, float(refs["bl0a_total_usd"]))
            cells["usd_overflow"] = _cell(usd)
            cells["usd_total"] = _cell(tot)
            cells["saving_pct"] = _cell([None if v is None else 100.0 * (1.0 - v) for v in r0])
            cells["gap"] = _cell([ratio.get(f"{tag}:{d}:0") for d in days])
            cells["rc"] = _cell([(((rc.get(tag) or {}).get(L.TRACE) or {}).get(w) or {}).get("0") for w in weeks])
            cells["w0"] = _cell([(w0.get(tag) or {}).get(w) for w in weeks])
            cells["p_star"] = p_star(curves.get(tag) or {}, p_weeks, grid_top)
        rows.append({"tag": tag, "key": "bl0a" if tag == "BL0a" else L.KEY_OF_TAG[tag],
                     "label": style.POLICIES["bl0a"].label if tag == "BL0a" else L.label(tag), "cells": cells})
    return {"rows": rows, "columns": [{"key": k, "label": lab} for k, lab, _ in T3_COLUMNS], "weeks": weeks,
            "gap_days": days, "p_weeks": p_weeks, "p_grid_top": grid_top,
            "scope": {"tags": list(T3_TAGS), "columns": [k for k, _, _ in T3_COLUMNS], "weeks": weeks,
                      "gap_days": days, "p_weeks": p_weeks, "seeds": [0]}}


def _cell(vals) -> dict:
    return {**L.med_ci(vals), "note": None}


def run_record(inp: Inputs, row: Mapping, runs_files: list) -> tuple[dict, dict]:
    """The run of a summary row (its job's run file under main/runs/, the record of the row's mode and policy seed)
    and the file's references; the file is recorded in runs_files with its sha256 (W10)."""
    name = L.run_file("main", row["job"])
    if not inp.path(name).is_file():
        raise MissingKey(f"{name}: no such run file (main/runs/ is not versioned; build with the input root of the "
                         "confirmation's copy, W10)")
    if not any(f["path"] == name for f in runs_files):
        runs_files.append({"path": name, "sha256": L.sha256_of(inp.path(name))})
    payload = inp.json(name)
    recs = [x for x in payload.get("runs") or [] if x.get("mode") == row["mode"]
            and int(x.get("policy_seed", -1)) == int(row["seed"])]
    if len(recs) != 1:
        raise MissingKey(f"{name}: {len(recs)} runs of mode {row['mode']} and policy seed {row['seed']}")
    refs = need(payload, "instances", "base", "references", what=name)
    return recs[0], refs


def lower_median(values: Sequence) -> Any:
    """The ceil(n/2)-th smallest value, None counted as above every value (None if it is the one); Table III v2's
    statistic of p* (figs/table3_v2.py, lower_median), so that the two tables print the same cell."""
    v = sorted(values, key=lambda x: math.inf if x is None else float(x))
    return v[(len(v) + 1) // 2 - 1] if v else None


def p_star(curves_of_tag: Mapping, weeks: Sequence[str], grid_top: float) -> dict:
    """p* (W2) as Table III v2 computes it (figs/table3_v2.py, _p_star_cell): per week of `weeks` the first p with
    r0 > 1 (None: not reached), and the lower median over the weeks (None counted above every p; with four weeks the
    median of W2 would print the mean of the middle two, a value between grid points, or 'none' for a policy that
    crosses in half of the weeks); its reading 'none' where that is None and every week's curve reaches the grid's
    largest p (grid_top), else '>q' with q the least largest p over the weeks (BL2, A6 and Sublet one-way ran p <=
    0.2 only: 'not reached at p <= 0.2', W2). The per-week values stand in place of an interval."""
    per, vals, top = [], [], []
    for w in weeks:
        c = curves_of_tag.get(w)
        if c is None:
            per.append({"week": w, "first": None, "p_max": None})
            continue
        have = [float(p) for p, v in c.get("points") or [] if v is not None]
        f = c.get("first_p_above_1")
        per.append({"week": w, "first": f, "p_max": max(have) if have else None})
        vals.append(None if f is None else float(f))
        if have:
            top.append(max(have))
    med = lower_median(vals)
    reach = min(top) if top else None
    if med is not None or not vals:
        reading = None
    elif reach is not None and reach >= grid_top:
        reading = "none"
    else:
        reading = f">{format(reach, 'g')}" if reach is not None else None
    return {"median": med, "none": reading == "none", "reading": reading, "lo": None, "hi": None, "n": len(vals),
            "per_week": per, "statistic": "lower median",
            "note": None if med is not None else ("not reached" if reading else None)}


def h3_table(parts: Mapping, an: Mapping) -> dict:
    fam_of = {(r["cell"], r["tag"], r.get("mode"), r.get("seed")): r.get("fam") for r in parts["fam"].get("runs") or []
              if r.get("kind") == "fam"}
    groups: dict = {}
    for p in ("main", "seeds", "second", "e3", "fam", "grid"):
        for x in parts[p].get("guarded") or []:
            if p == "fam":
                g = fam_of.get((x["cell"], x["tag"], x.get("mode"), x.get("seed"))) or "?"
            elif p == "e3":
                g = "siloed" if x.get("borrower") is not None or x.get("mode") == "siloed" else "shared"
            else:
                g = next((kv.split("=", 1)[1] for kv in str(x.get("job", "")).split(":") if kv.startswith("k=")), "")
            c = groups.setdefault((p, x["tag"], g), {k: 0 for k in H3_COUNTS})
            proj = x.get("projection") or {}
            c["runs"] += 1
            c["held"] += x.get("held") is True
            c["env_violations"] += x.get("env_ok") is False
            c["aborts"] += bool(x.get("aborted"))
            c["aborts_prop_p"] += bool(x.get("project") is True and x.get("aborted") and x.get("s_fb_all")
                                       and x.get("t0g_bound_all"))
            c["switch_runs"] += bool(x.get("switches"))
            c["switches"] += int(x.get("switches") or 0)
            c["robust_runs"] += bool(x.get("robust_slots"))
            c["robust_slots"] += int(x.get("robust_slots") or 0)
            c["projected_slots"] += int(x.get("projected_slots") or 0)
            c["K0"] += int(proj.get("K0") or 0)
            c["dropped_buys"] += int(proj.get("dropped_buys") or 0)
            c["dropped_other"] += int(proj.get("dropped_other") or 0)
    order = {p: i for i, p in enumerate(("main", "seeds", "second", "e3", "fam", "grid"))}
    tag_rank = {t: i for i, t in enumerate(list(L.E7_TAGS) + ["Sublet-lag", "BL1-G", "BL5-G"])}
    rows = [{"part": p, "tag": t, "label": L.label(t), "group": g, **c}
            for (p, t, g), c in sorted(groups.items(), key=lambda kv: (order[kv[0][0]], tag_rank.get(kv[0][1], 99),
                                                                        kv[0][1], kv[0][2]))]
    total = {k: sum(r[k] for r in rows) for k in H3_COUNTS}
    h3 = need(an, "H3", what=L.ANALYSIS)
    return {"rows": rows, "total": total,
            "analysis": {k: h3.get(k) for k in ("n_runs", "n_not_held", "n_envelope_violations",
                                                "n_aborts_s_fb_bound_form", "aborts", "one_way_aborts",
                                                "runs_with_switches", "runs_with_robust_slots", "projected_slots",
                                                "dropped_buys", "K0")},
            "scope": {"parts": sorted({r["part"] for r in rows}, key=order.get),
                      "tags": sorted({r["tag"] for r in rows}), "n_runs": total["runs"]}}


H3_COUNTS = ("runs", "held", "env_violations", "aborts", "aborts_prop_p", "switch_runs", "switches", "robust_runs",
             "robust_slots", "projected_slots", "K0", "dropped_buys", "dropped_other")
# the printed columns (H3, §6: "switches of S, robust-form slots"; the runs with either stay in the extract, where
# analysis.json's H3 counts them)
H3_PRINT = ("runs", "held", "env_violations", "aborts", "aborts_prop_p", "switches", "robust_slots",
            "projected_slots", "K0", "dropped_buys", "dropped_other")


def _labels(tags) -> str:
    """The registry labels of `tags` as one list (ms5b_e7_lib.join_labels: semicolons where a label has a comma)."""
    return L.join_labels([L.tex(L.label(t)) for t in tags])


REG_WEEKS = len(m5.CONF_WEEKS)   # the registered number of confirmation weeks (§4.4(a)): the criteria's counts


def _g(x) -> str:
    return "--" if x is None else format(float(x), "g")


def _p_tex(p) -> str:
    if p is None:
        return "--"
    if p >= 1e-3:
        return f"{p:.4f}"
    m, e = f"{p:.1e}".split("e")
    return f"{m}\\times10^{{{int(e)}}}"


def outcomes_table(an: Mapping) -> dict:
    """One row per hypothesis (H1, H2, H2b, H3, H4, H5, H6): kind, criterion (the registered statement, prereg §5 as
    registered, with the thresholds of analysis.json and ms5b_analysis), the measured values and the outcome, all read
    from analysis.json."""
    rows = []
    h = need(an, "H1", what=L.ANALYSIS)
    th, mm = h.get("threshold") or {}, h.get("median_margin") or {}
    rows.append({"id": "H1", "kind": h.get("kind"), "pass": h.get("pass"),
                 "criterion": (f"Sublet's L-tr $r_0$ below the per-week minimum over H1's set "
                               f"({_labels((an.get('H2') or {}).get('set') or m5.H1_SET)}) in at least "
                               f"{th.get('wins')} of {REG_WEEKS} weeks (one-sided sign test), and the median "
                               f"paired margin at least {_g(th.get('median_margin'))} of the all-fallback bill "  # C59
                               f"with a week-bootstrap 95\\% "
                               f"interval above {_g(th.get('ci_low'))}"),
                 "measured": (f"{h.get('wins')} of {h.get('n_weeks')} weeks; median margin "
                              f"{L.num(mm.get('median'), '.4f')} {L.interval(*(mm.get('ci') or [None, None]), '.4f')}"
                              f"; sign test $p={_p_tex((h.get('sign_test') or {}).get('p'))}$; Wilcoxon "
                              f"$p={_p_tex((mm.get('wilcoxon') or {}).get('p'))}$")})
    h = need(an, "H2", what=L.ANALYSIS)
    n, k = h.get("n_weeks"), REG_WEEKS
    rows.append({"id": "H2", "kind": h.get("kind"), "pass": h.get("pass"),
                 "criterion": (f"Sublet's $W_0<1$ in {k} of {k} weeks and below the $W_0$ of every policy of H1's "
                               f"set in {k} of {k} weeks; the median of Sublet's $W_0$ at most {MA.H2_MEDIAN}"),
                 "measured": (f"below 1 in {h.get('weeks_below_1')} of {n} weeks, below H1's set in "
                              f"{h.get('weeks_below_set')} of {n}; median $W_0$ {L.num(h.get('median_W0'), '.3f')}")})
    h = need(an, "H2b", what=L.ANALYSIS)
    n = h.get("n_weeks")
    fails = []
    for wk in h.get("weeks") or []:
        if not wk.get("below_all"):
            lower = [t for t, v in (wk.get("others") or {}).items() if v is not None and wk.get("Sublet") is not None
                     and v <= wk["Sublet"]]
            fails.append(f"{wk['week']} ({_labels(lower) if lower else 'a missing run'}: "
                         + ", ".join(f"{L.num(wk['others'][t], '.3f')}" for t in lower)
                         + f" against {L.num(wk.get('Sublet'), '.3f')})")
    rows.append({"id": "H2b", "kind": h.get("kind"), "pass": h.get("pass"),
                 "criterion": f"Sublet's $W_0$ below that of {_labels(h.get('set') or m5.H2B_SET)} in "
                              f"{REG_WEEKS} of {REG_WEEKS} weeks",
                 "measured": (f"below the set in {h.get('weeks_below_set')} of {n} weeks"
                              + (f"; not in week{'s' if len(fails) > 1 else ''} " + "; ".join(fails) if fails
                                 else ""))})
    h = need(an, "H3", what=L.ANALYSIS)
    rows.append({"id": "H3", "kind": h.get("kind"), "pass": h.get("pass"),
                 "criterion": ("In every guarded run of the confirmation the certificate holds, with the envelope "
                               "$\\mathrm{ALG}(t)+R(t)\\le\\gamma C_S(t)+B(t)$ + tolerance at every executed slot; no "
                               "projecting run in which $S$ follows FB at every slot and T0g stays in bound form "
                               "aborts"),
                 "measured": (f"{h.get('n_runs'):,} guarded runs: {h.get('n_not_held')} certificates not held, "
                              f"{h.get('n_envelope_violations')} envelope violations, "
                              f"{h.get('n_aborts_s_fb_bound_form')} such aborts ({h.get('aborts')} aborts in all, "
                              f"{h.get('one_way_aborts')} in the one-way rows); {h.get('n_missing_guarded_runs')} "
                              f"missing runs")})
    h = need(an, "H4", what=L.ANALYSIS)
    rows.append({"id": "H4", "kind": h.get("kind"), "pass": h.get("pass"),
                 "criterion": ("On every counted F1/F2 run, critical-ratio renting equals RR-renew in total cost and "
                               "purchase count, and Sublet projects in no such run"),
                 "measured": (f"{h.get('n_counted_pairs')} counted pairs, {len(h.get('mismatches') or [])} "
                              f"mismatches, {len(h.get('missing_pairs') or [])} missing; Sublet projects in "
                              f"{h.get('sublet_projected_runs')} counted runs")})
    h = need(an, "H5", what=L.ANALYSIS)
    bs = h.get("b") or []
    no1 = [b for b in bs if not b.get("le_MS4")]
    no2 = [b for b in bs if not b.get("shared_below_siloed")]
    b2 = [b for b in bs if b["b"] >= 2]
    meas = (f"Sublet at most the legacy row at {len(bs) - len(no1)} of {len(bs)} values of $b$"
            + ("".join(f"; not at $b={b['b']}$ ({L.num(b['Sublet_shared'], '.4f')} against "
                       f"{L.num(b['Sublet_MS4_shared'], '.4f')})" for b in no1))
            + f"; shared below siloed at {len(b2) - len([b for b in no2 if b['b'] >= 2])} of the {len(b2)} values "
              f"$b\\ge2$" + "".join(f"; not at $b={b['b']}$" for b in no2))
    rows.append({"id": "H5", "kind": h.get("kind"), "pass": h.get("pass"),
                 # C59 (RC19(3)): the experiment by its name, as the pre-registration names its instances
                 "criterion": ("On the sharing instances (config seeds "
                               + ", ".join(str(s).lstrip("c") for s in h.get("seeds") or [])
                               + "), the median over the seeds of Sublet's ALG/LB at most that of the legacy row, "
                               + L.tex(L.label("Sublet-MS4")) + ", at every $b$, and Sublet's shared median below "
                               "its siloed one at every $b\\ge2$"),
                 "measured": meas})
    h = need(an, "H6", what=L.ANALYSIS)
    rows.append({"id": "H6", "kind": h.get("kind"), "pass": h.get("pass"),
                 "criterion": (f"The median of Sublet's $r_0$ minus critical-ratio renting's over the trace and "
                               f"stress week runs at most {h.get('threshold')} of the all-fallback bill"),  # C59
                 "measured": (f"0 (exactly; the median over {h.get('n')} runs)" if h.get("median_price") == 0.0
                              else f"{L.num(h.get('median_price'), '.4f')} of the all-fallback bill over "
                                   f"{h.get('n')} runs")})
    return {"rows": rows, "analysis_sha256": (an.get("meta") or {}).get("sha256"),
            "scope": {"hypotheses": [r["id"] for r in rows]}}


# ---------------------------------------------------------------------------------------------------------------
# LaTeX
MODE_TEX = {"L-b999": "L-tr, P99.9"}
PARETO_FMT = ".4f"              # a dominating policy can differ from Sublet by less than 0.0005 in both
NAME_IN = 2.0                   # the name column (in): the longest label, Sublet-MS4's, on two lines at 8 pt
NAME_COL = f"p{{{NAME_IN}in}}"
SEEDS_NAME_IN = 1.1             # the name columns of e7v2_seeds.tex and e7v2_table3_intervals.tex (in)
T3_NAME_IN = 1.45


def weeks_tex(t: Mapping, d: Mapping) -> str:
    blocks = L.chunks(t["weeks"], 8)
    cap = (r"Every week of part main (weeks " + L.week_span(t["weeks"]) + r", policy seed 0): the cost over "
           r"all-fallback under the trace lender, $r_0$, and the worst cost over the five stress lenders, $W_0$, of "
           r"every policy of the confirmation, the ablations of critical-ratio renting and the transplants "
           r"included, with the median over the weeks and its 95\% week-bootstrap interval (descriptive).")
    out = []
    for j, ws in enumerate(blocks):
        last = j == len(blocks) - 1
        idx = [t["weeks"].index(w) for w in ws]
        rows, groups = [], []
        for r in t["rows"]:
            groups.append(len(rows))
            nm = L.name_cells(L.tex(r["label"]), 2, NAME_IN)
            for k, (m, mt) in enumerate((("r0", "$r_0$"), ("W0", "$W_0$"))):
                s = r[m]
                rows.append([nm[k], mt] + [L.num(s["values"][i]) for i in idx]
                            + ([L.num(s["median"]), L.interval(s["lo"], s["hi"])] if last else []))
        head = ["Policy", ""] + list(ws) + (["Median", r"95\% interval"] if last else [])
        out.append(L.longtable("@{}" + NAME_COL + "l" + "r" * (len(ws) + (1 if last else 0)) + ("c" if last else "")
                               + "@{}", cap if j == 0 else
                               f"Table~\\ref{{tab:e7v2-weeks}}, continued: weeks {L.week_span(ws)}.",
                               "tab:e7v2-weeks", head, rows, groups=groups, cont=j == 0))
    return "\n".join(out)


def pareto_tex(t: Mapping, d: Mapping) -> str:
    rows = []
    for r in t["rows"]:
        front = "; ".join(f"{L.tex(m['label'])} ({L.num(m['r0'], PARETO_FMT)}, {L.num(m['W0'], PARETO_FMT)})"
                          for m in r["front"])
        dom = "; ".join(L.tex(x["label"]) for x in r["dominated_by"]) or "--"
        rows.append([r["week"], L.rag(front), "yes" if r["sublet_on_front"] else "no",
                     f"({L.num(r['sublet']['r0'], PARETO_FMT)}, {L.num(r['sublet']['W0'], PARETO_FMT)})",
                     L.rag(dom)])
    off = [r for r in t["rows"] if not r["sublet_on_front"]]
    a9_code = [x for x in t.get("left_out") or [] if x["kind"] != "ablation" and x["policy_id"] == "A9"]
    cap = (r"Per-week Pareto front of the trace cost $r_0$ and the worst cost $W_0$ (part main, policy seed 0) over "
           r"the " + str(len(t["tags"])) + r" policies of the confirmation that are not ablations of critical-ratio "
           r"renting in the registered analysis"
           + "".join(", which counts " + L.tex(x["label"]) + ", run by critical-ratio renting's code with other "
                     "parameters, as an ablation" for x in a9_code)
           + " (" + L.join_labels([L.tex(L.label(x)) for x in t["tags"]])
           + r"), each member with its ($r_0$, $W_0$); "
           r"whether Sublet is on the front, its values, and the policies that dominate it. Sublet is "
           + (r"on the front in every week." if not off else r"off the front in week" + ("s " if len(off) > 1 else " ")
              + L.join_labels([r["week"] for r in off]) + "." + _dominance_text(off)))
    return L.longtable("@{}lp{3.15in}cc" + "p{1.1in}@{}", cap, "tab:e7v2-pareto",
                       ["Week", r"Front: policy ($r_0$, $W_0$)", "Sublet on it", r"Sublet ($r_0$, $W_0$)",
                        "Dominating Sublet"], rows)


def _dominance_text(off: Sequence[Mapping]) -> str:
    """' In each of these weeks only X dominates it, by at most a in r0 and b in W0.' (bounds at one significant
    digit, L.bound_text), where the same policies dominate it in every such week; '' otherwise."""
    doms = [tuple(sorted(x["tag"] for x in r["dominated_by"])) for r in off]
    if not doms or len(set(doms)) != 1 or not doms[0]:
        return ""
    labels = {x["tag"]: x["label"] for r in off for x in r["dominated_by"]}
    dr = max(x["dr0"] for r in off for x in r["dominated_by"])
    dw = max(x["dW0"] for r in off for x in r["dominated_by"])
    who = L.join_labels([L.tex(labels[x]) for x in doms[0]]) + (", its inner policy," if doms[0] == ("A9",) else "")
    return (f" In {'each of these weeks' if len(off) > 1 else 'that week'} only {who} dominate"
            f"{'s' if len(doms[0]) == 1 else ''} it, by at most {L.bound_text(dr)} in $r_0$ and "
            f"{L.bound_text(dw)} in $W_0$.")


def rc_tex(t: Mapping, d: Mapping) -> str:
    rows, groups, prev = [], [], None
    size: dict = {}
    for r in t["rows"]:
        k = (r["tag"], tuple(r["seeds"]))
        size[k] = size.get(k, 0) + 1
    nm: list = []
    for r in t["rows"]:
        key = (r["tag"], tuple(r["seeds"]))
        if key != prev:
            groups.append(len(rows))
            nm = L.name_cells(L.tex(r["label"]) + ("" if r["seeds"] == [0] else ", seeds "
                                                   + "--".join(map(str, r["seeds"]))), size[key], NAME_IN)
        name = nm.pop(0)
        prev = key
        rows.append([name, MODE_TEX.get(r["mode"], r["mode"]), str(r["rc"]["n"]), L.num(r["rc"]["median"], ".4f"),
                     L.interval(r["rc"]["lo"], r["rc"]["hi"], ".4f"), L.num(r["fallback_usd"], ",.0f"),
                     L.num(r["stranding_usd"], ",.0f"), L.num(r["share_after_reclaims"], ".3f")])
    cap = (r"Revocation cost RC $=r_0(M)-r_0(\mbox{L-hon})$ under every lender mode $M$, each run paired with the "
           r"honoring lender's run of the same policy, week and policy seed (" + f"{t['scope']['n_runs']:,}"
           + r" runs; policy seed 0, and seeds 1--2 of part seeds in rows of their own): the number of runs, the "
           r"median RC and its 95\% bootstrap interval over the runs (over $n=4$ runs, the range of the runs), "
           r"and the medians of the runs' fallback and "
           r"stranding totals (USD) and of the fallback share after reclaims that the earlier end-to-end study "
           r"defined. Part main's modes on every week; "                   # C50: the paper's words for MS4 (D5 review)
           r"part second's (L-vr, L-rf, L-ad, L-tr with the P99.9 buffer, i.i.d.\ lenders L-iid-$p$) on its weeks."
           + _same_modes_text(t)
           + r" Every run's RC, fallback and stranding totals and share after reclaims ("
           + f"{t['scope']['n_runs']:,}" + r" rows) are in the supplementary data file " + L.tex(RC_RUNS) + ".")
    return L.longtable("@{}" + NAME_COL + "lrrcrrr@{}", cap, "tab:e7v2-rc",
                       ["Policy", "Lender", "$n$", "RC", "Interval", "Fallback", "Stranding",                # C59
                        "Share after recl."], rows, groups=groups)


def _same_modes_text(t: Mapping) -> str:
    """The caption's note that SAME_MODES give one condition on their common weeks, where the data show it: the rows
    of the modes run on exactly those weeks are equal, and a mode run on more weeks has the same runs on them."""
    sm = t.get("same_modes")
    if not sm or not sm.get("equal"):
        return ""
    wk = {m: sorted({x[0] for r in t["rows"] if r["mode"] == m and r["seeds"] == [0] for x in r["runs"]}, key=int)
          for m in sm["modes"]}
    same = [m for m in sm["modes"] if wk[m] == sm["weeks"]]
    more = [m for m in sm["modes"] if m not in same]
    out = (r" On weeks " + L.week_span(sm["weeks"]) + r" the runs under " + L.join_labels(sm["modes"])
           + r" have equal RC for every policy (each of these lenders announces every revocable lease when its "
             r"guaranteed period ends)")
    if len(same) > 1:
        out += r": the rows of " + L.join_labels(same) + " are equal" + (
            r" and repeat " + L.join_labels(more) + r"'s runs of those weeks" if more else "")
    return out + "."


def seeds_tex(t: Mapping, d: Mapping) -> str:
    weeks, seeds = t["weeks"], t["seeds"]
    rows, groups = [], []
    for r in t["rows"]:
        groups.append(len(rows))
        nm = L.name_cells(L.tex(r["label"]), len(r["lines"]), SEEDS_NAME_IN)
        for k, ln in enumerate(r["lines"]):
            what = {"W0": "$W_0$", "RC L-tr": "RC, L-tr"}.get(ln["what"], ln["what"])
            rows.append([nm[k], what]
                        + [L.num(ln["values"][w].get(str(s))) for w in weeks for s in seeds])
    same = [r for r in t["rows"] if r["max_diff"] == 0.0 and r["n_compared"]]
    diff = [f"{L.tex(r['label'])} {L.num(r['max_diff'], '.4f')}" for r in t["rows"] if r["max_diff"]]
    at = L.join_labels([str(x) for x in seeds[1:]])
    cap = (r"Policy seeds of part seeds (weeks " + L.week_span(weeks) + r"): $r_0$ under the seven lender modes, "
           r"$W_0$ and RC under the trace lender for policy seeds " + ", ".join(map(str, seeds))
           + r" (seed 0 from part main); a column is week/seed. "
           + "".join(r"Every value of " + L.tex(r["label"]) + r" at seed" + ("s " if len(seeds) > 2 else " ") + at
                     + r" equals seed 0's" + _draws_text(r) + ". " for r in same)
           + (r"Largest difference from seed 0: " + "; ".join(diff) + "." if diff else ""))
    head = ["Policy", ""] + [f"{w}/{s}" for w in weeks for s in seeds]
    return L.longtable("@{}p{" + str(SEEDS_NAME_IN) + "in}l" + "r" * (len(weeks) * len(seeds)) + "@{}", cap,
                       "tab:e7v2-seeds",
                       head, rows, groups=groups, tabcolsep="2.0pt")


def _draws_text(r: Mapping) -> str:
    """The reason that the data support for a tag whose seeds agree (seed_draws), as a clause; '' if none."""
    dr = r.get("draws") or {}
    if dr.get("seed_free"):
        return " (it draws no random number)"
    if dr.get("guarded") and dr.get("inner_seed_free") and dr.get("runs") and dr["s_fb_all"] == dr["runs"]:
        return (r": its inner policy draws no random number, and the safe expert, which holds the guard's random "
                r"draws, followed FB at every slot of all " + f"{dr['runs']:,}" + r" of its runs at these seeds")
    return ""


def t3_tex(t: Mapping, d: Mapping) -> str:
    fmt = {k: f for k, _, f in T3_COLUMNS}
    rows, groups = [], []
    for r in t["rows"]:
        groups.append(len(rows))
        nm = L.name_cells(L.tex(r["label"]), len(t["columns"]), T3_NAME_IN)
        for i, col in enumerate(t["columns"]):
            c = r["cells"][col["key"]]
            if col["key"] == "p_star":
                rd = c.get("reading")
                med = (L.num(c["median"], "g") if c["median"] is not None else
                       "none" if rd == "none" else f"$>${rd[1:]}" if rd else "--")
                per = ", ".join(_p_week(x, t["p_grid_top"]) for x in c.get("per_week") or [])
                rows.append([nm[i], L.rag(col["label"]), med, per or "--",
                             str(c["n"]) if c["n"] else "--"])
                continue
            f = fmt[col["key"]]
            rows.append([nm[i], L.rag(col["label"]), L.num(c["median"], f),
                         L.interval(c["lo"], c["hi"], f), str(c["n"]) if c["n"] else "--"])
    # C58 (MS7): the main text's Table III is now the policy glossary and Table IV (tab:e7) prints no p*, so the
    # caption cites tab:e7 by label and defines p* from the crossings' table
    cap = (r"The confirmation's cells behind Table~\ref{tab:e7} of the main text, with each policy's gap ALG/LB "
           r"and first crossing $p^\ast$ (weeks " + L.week_span(t["weeks"]) + r" of part main, trace "
           r"lender, policy seed 0; the gap on the days of part second): median; its 95\% week-bootstrap "
           r"interval over the weeks, and for the gap days the range over the days; and the number of values $n$ "
           r"(descriptive). $p^\ast$, the least reclaim probability $p$ "
           r"with a cost above all-fallback (Table~\ref{tab:e7v2-crossings}), is the "
           r"lower median over weeks " + L.week_span(t["p_weeks"]) + r" (a week without a crossing counted above "
           r"every $p$; `none': not reached on the grid up to $p=" + format(float(t["p_grid_top"]), "g") + r"$; $>q$: "
           r"not reached up to $q$, the grid's largest $p$ for that policy); the per-week first crossings, read the "
           r"same way, stand in place of an interval. Total accounting includes the borrowers' own capacity. "
           r"All-fallback's saving is 0 and its $W_0$ 1 by definition.")
    return L.longtable("@{}p{" + str(T3_NAME_IN) + "in}p{2.3in}rlr@{}", cap, "tab:e7v2-table3-intervals",
                       ["Policy", "Column", "Median", "Interval", "$n$"], rows, groups=groups)              # C59


def _p_week(x: Mapping, grid_top: float) -> str:
    """A week's first crossing: its p, 'none' where r0 <= 1 up to the grid's largest p, '>q' where that week's curve
    ends at q below it, '--' without a curve."""
    if x["first"] is not None:
        return format(float(x["first"]), "g")
    if x["p_max"] is None:
        return "--"
    return "none" if float(x["p_max"]) >= float(grid_top) else f"$>${format(float(x['p_max']), 'g')}"


# the printed columns of e7v2_h3.tex (H3_PRINT): head, caption text, and the phrase that names a column left out
# because it is 0 in every row
H3_COLS = {"runs": ("Runs", "runs", None),
           "held": ("Held", "certificates held", None),
           "env_violations": ("Env.", "envelope violations (Env.)", "an envelope violation"),
           "aborts": ("Aborts", "aborts", "an abort"),
           "aborts_prop_p": ("Under P", "aborts of projecting runs in which $S$ followed FB at every slot and T0g "
                                        "stayed in bound form (Under P)",
                             "an abort of a projecting run in which $S$ followed FB at every slot and T0g stayed in "
                             "bound form"),
           "switches": ("Switches", "switches of $S$", "a switch of $S$"),
           "robust_slots": ("Robust", "robust-form slots (Robust)", "a robust-form slot"),
           "projected_slots": ("Proj.\\ slots", "projected slots", "a projected slot"),
           "K0": ("K0", "K0 uses", "a K0 use"),
           "dropped_buys": ("Dropped Buys", "dropped Buys", "a dropped Buy"),
           "dropped_other": ("Other", "other dropped actions (Other)", "a dropped action other than a Buy")}


def _or_list(items: Sequence[str]) -> str:
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " or " + items[-1]


def h3_tex(t: Mapping, d: Mapping) -> str:
    """H3's counts; a column that is 0 in every row (and in the totals) is left out and named in the caption."""
    cols = [k for k in H3_PRINT if t["total"][k] or H3_COLS[k][2] is None]
    zero = [k for k in H3_PRINT if k not in cols]
    rows, groups, prev = [], [], None
    for r in t["rows"]:
        if r["part"] != prev:
            groups.append(len(rows))
        rows.append([r["part"] if r["part"] != prev else "", L.rag(L.tex(r["label"])), L.tex(r["group"])]
                    + [f"{r[k]:,}" for k in cols])
        prev = r["part"]
    groups.append(len(rows))
    rows.append(["all", "", ""] + [f"{t['total'][k]:,}" for k in cols])
    a = t["analysis"]
    cap = (r"H3's counts over every guarded run of the confirmation, by part, policy and runs (the job kind of the "
           r"week parts; the sharing study's shared and siloed runs; the family of part fam): "
           + ", ".join(H3_COLS[k][1] for k in cols[:-1]) + " and " + H3_COLS[cols[-1]][1] + ". "
           + (r"No run had " + _or_list([H3_COLS[k][2] for k in zero]) + r" (columns left out). " if zero else "")
           + r"The registered analysis counts "
           + f"{a.get('n_runs'):,} runs, {a.get('aborts'):,} aborts ({a.get('one_way_aborts'):,} in the one-way "
           r"rows), " + f"{a.get('runs_with_switches'):,} runs with a switch of $S$, "
           + f"{a.get('runs_with_robust_slots'):,} with a robust-form slot, "
           + f"{a.get('projected_slots'):,} projected slots, {a.get('K0'):,} K0 uses and "
           + f"{a.get('dropped_buys'):,} dropped Buys.")
    return L.longtable("@{}lp{2.8in}l" + "r" * len(cols) + "@{}", cap, "tab:e7v2-h3",
                       ["Part", "Policy", "Runs of"] + [H3_COLS[k][0] for k in cols], rows, groups=groups,
                       tabcolsep="2.6pt")


def outcomes_tex(t: Mapping, d: Mapping) -> str:
    rows = [[r["id"], L.tex(r["kind"] or "--"), L.rag(r["criterion"]), L.rag(r["measured"]),
             {True: "holds", False: "fails"}.get(r["pass"], "not decided")] for r in t["rows"]]
    cap = (r"Pre-registered outcomes of the confirmation: each hypothesis with its kind, its criterion as registered "
           r"(the thresholds of the frozen analysis), the measured values and the outcome, read from the analysis "
           r"output (the analysis script's sha256 " + str(t.get("analysis_sha256") or "--")[:16]
           + r"\ldots). The weeks are rotations of one series; the tests are descriptive.")
    return L.longtable("@{}lp{0.55in}p{2.45in}p{2.45in}l@{}", cap, "tab:ms5b-outcomes",
                       ["", "Kind", "Criterion", "Measured", "Outcome"], rows,
                       groups=list(range(1, len(rows))))


def write_tables(data: Mapping, report: Mapping) -> None:
    """The seven tables and the data file RC_RUNS from the extract's `tables` (figs.common.write_table; the file's
    sha256 checked against the extract's)."""
    t = data["tables"]
    head = L.table_head
    paths = [write_table(TABLES[0], head(NAME, [L.MAIN]) + weeks_tex(t["e7v2_weeks"], data)),
             write_table(TABLES[1], head(NAME, [L.ANALYSIS, L.MAIN]) + pareto_tex(t["e7v2_pareto"], data)),
             write_table(TABLES[2], head(NAME, [L.ANALYSIS, L.MAIN, L.SEEDS, L.SECOND]) + rc_tex(t["e7v2_rc"], data)),
             write_table(TABLES[3], head(NAME, [L.SEEDS, L.MAIN, L.ANALYSIS]) + seeds_tex(t["e7v2_seeds"], data)),
             write_table(TABLES[4], head(NAME, [L.MAIN, L.SECOND, L.ANALYSIS, f"{L.CONF}/main/runs/"])
                         + t3_tex(t["e7v2_table3_intervals"], data)),
             write_table(TABLES[5], head(NAME, list(L.PART_FILES.values()) + [L.ANALYSIS])
                         + h3_tex(t["e7v2_h3"], data)),
             write_table(TABLES[6], head(NAME, [L.ANALYSIS]) + outcomes_tex(t["ms5b_outcomes"], data))]
    text = rc_runs_csv(t["e7v2_rc"])
    if hashlib.sha256(text.encode("utf-8")).hexdigest() != t["e7v2_rc_runs"]["sha256"]:
        raise style.StyleError(f"{NAME}: {RC_RUNS} differs from the sha256 that the extract records")
    paths.append(write_table(RC_RUNS, text))
    print(f"[{NAME}] wrote {', '.join(str(p) for p in paths)}")


def main(argv: Sequence[str] | None = None) -> dict:
    return cli(NAME, build, draw, argv, supplementary=True, after=write_tables, doc=__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
