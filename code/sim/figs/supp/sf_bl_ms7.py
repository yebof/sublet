"""sf_bl_ms7: Sublet against the stronger baselines of the MS7 baseline study (X4) on the confirmation weeks, with the
tables e7r_tags.tex, e7r_margins.tex and e7r_grid.tex and the data file baseline_study_runs.csv (design/ms7/w_spec.md
§4, unit W-G4 B; design/ms7/registration.md §2 and §3, X4; design/ms7/plan.md X4; change C58).

Claims: none of its own. Every number is read from the registered analysis of the baseline study (e7r_analysis.py,
its sha256 in design/ms7/registration.md), the frozen selection of the tuned settings (e7r_select.py) and the summaries
of the parts tune and confirm; medians and min-max over weeks, sign counts, no interval and no p-value (design/ms7/
plan.md D4; registration §3).

Figure (W2 x 2.5 in, C58 block B). One question: how far does Sublet stay ahead of each stronger baseline, week by
week? A forest plot of Sublet's paired margins (the confirmation's convention, ms5b_common.paired_margins: the
policy's value minus Sublet's in the same week, positive when Sublet costs less) over the evaluation weeks (read from
the analysis; 301-316 in the runs), one row per rule and three panels: (a) r0 under the trace lender, (b) W0, the
largest r0 over the five stress lenders of the confirmation, (c) W0+, the largest over those and the six new ones (the
adaptive lender through its equivalence with the eager one). Each marker is the median over the weeks of the
per-week margin, its bar the min-max over the weeks; Sublet is the vertical line at 0. The rows (fig_rows): each
primary baseline as built with an arrow to its transplant of Algorithm 2's base contract kbar (the analysis's
as_built_vs_c2 pairs); SpotHedge-style with one and with two spares per pool, each with an arrow to the variant with
spares per LLM, none while idle, and kbar; MPC (the setting of rule T, the registry's "MPC") and the oracle forecast, a
labeled lookahead reference that no comparison set holds and that ran under the trace and the honoring lender only (so
(b) and (c) have no oracle point); and protected-only critical-ratio renting. The oracle forecast is MPC's as-built
setting with the realized demand of the window (ms7_baselines.MS7_TAGS), so it is drawn as the variant of rule T's
setting, in one row with an arrow, only where that setting differs from it in the forecast alone (mpc_oracle_paired:
the same registry id and the same parameters but 'forecast'); otherwise MPC and the oracle forecast are two rows of
one rule each (review of W-G4 B: the oracle is not rule T's variant when T changed the contract rule or the replanning,
as on the reduced runs). A row of two rules names the base rule by its registry label and the variant by the part of
its registry label that differs, after an arrow ("Greedy renting -> kbar contract"; ROW_SUFFIX, checked against the
registry); the two markers of a row are offset vertically (DODGE_PT), the base rule above. The tuned settings, the
comparison sets' best members and every other tag are in the tables.

As built (choices that w_spec §4 leaves open):
* W2 x 2.5 in (block B; registered at 2.4 by unit W-G4-0; 2.5 with GROUP_GAP 0.1 gave nine or ten rows a pitch of
  more than the 13.25-pt height of a 9-pt name with kbar: 13.6 pt with ten; C62: the 7-pt names' boxes at most 11.5
  pt high, the pitch 13.8 pt with ten under the 2-pt room of TOP_ROOM_PT), names as the y tick labels of (a), the arrow
  of a name STIX's (ARROW; C62 fix round: Liberation Sans's U+2192, as built, is 0.23 em high and centered 0.17 em
  above the baseline, small and low next to the lower case); each panel its own x axis, on a symmetric log scale,
  linear within +-LINTHRESH (0.1) and logarithmic beyond (final render, C58: on a linear axis the spares' margins, up to 2.6 on r0
  and 3.3 on W0, squeezed MPC's and the transplants' margins, 0.01 to 0.2 on r0, into a few points next to Sublet's
  line; figs/fig7_e2_e6.py's precedent), its major ticks the decades 0, +-0.1, +-1, ... in the panel (or, when every
  value lies in the linear part, the first step of X_STEPS that gives 3 to 5 ticks), light vertical grid lines at
  them but 0, no minor ticks (C62; as built minor ticks at 2..9 times a decade beyond 0.1), the limits padded by
  X_PAD in the scale's coordinates and widened so that the end tick labels stay inside the panel; groups of rows
  (transplants, spares, MPC, protected-only) separated by thin light lines; an arrow only where its two medians are
  ARROW_MIN_PT apart or more (its head would cover them; 16 pt since the final render).
* C62: the panel titles at the caption size (style.LABEL_PT) on their letters' baseline; the row names with math on
  the plain names' baseline and right end as printed (common.align_baselines; common.align_right_math, C62 fix
  round: the PDF rounds a mathtext line's width up to a whole pt, and as built such names ended up to 0.9 pt short of
  the plain ones); Sublet's line named "Sublet" above (a), in its
  label color, and the x label without "(Sublet: the line at 0)".
* labels.caption is a caption draft with every count read from the inputs (weeks, the numbers of stress lenders).

Tables (after hook, figs.common.write_table: SUBLET_FIGS_TABLES_DIR, else SUBLET_FIGS_PDF_DIR when set, else
paper/supplement/tables/), from the extract's `tables`, so --from-extract rewrites them; each entry carries a `scope`:
  e7r_tags.tex      every tag of the analysis (its tags block: the confirmation's fifteen with their runs of part main
                    and the six new lenders, the transplants, protected-only renting, the spares, MPC at its tuned
                    settings, the tuned settings and the oracle): median and min-max over the weeks of r0 under L-tr,
                    W0, W0+ and RC under L-tr (the analysis's tag statistics), with the identity of the repeated
                    trace-lender runs with the confirmation's, the lender invariance of protected-only renting and
                    the aliases (a W setting equal to its T setting) in the caption;
  e7r_margins.tex   Sublet's margin over every other tag and over the best member of each comparison set (the
                    analysis's margins and best_of): weeks won, tied and lost (a missing run counts as a loss, shown as
                    +m; the oracle's worst cases, by design not run, as 'not run'), median and min-max, on r0 under
                    L-tr, W0 and W0+;
  e7r_grid.tex      the tuned settings: every configuration of the tuning grids (selection.json's families) with its
                    setting in words (from its parameters over ms7_baselines.KNOB_DEFAULTS), its medians of r0 under
                    L-tr and of W0 on the tuning weeks, its eligibility and the selections of rules T and W, and for the
                    as-built and the selected configurations their medians on the confirmation weeks and whether T and
                    W hold there (the analysis's confirm block), with the provenance of the selection (the analysis's
                    check (iv)) in the caption;
  baseline_study_runs.csv
                    every run behind the tables: part (eval, confirm, tune), policy (registry label; a tuning
                    configuration by its family and number), tag, lender, week, policy seed, r0, RC (eval: r0 minus r0
                    under L-hon of the same policy and week) and the run's source (the confirmation's part main for the
                    confirmation's tags under its seven lenders, this study otherwise); an alias's runs are its
                    target's and appear once; the extract's tables.baseline_study_runs holds the values, the columns,
                    the row count and the sha256, and the after hook refuses to write a file of another sha256.
Every table is a longtable (ms5b_e7_lib.longtable: one-column mode, "Table <n>, continued"); the tuning table is set
in \\scriptsize.

Inputs (RUN_INPUTS; figs.inputs, so SUBLET_FIGS_IN_ROOT redirects them): code/sim/out/e7r/analysis.json,
tune/selection.json, tune/summary.json and confirm/summary.json, the MS7 run outputs copied in after the runs
(figs/rebuild.py keeps the entry pending until then). A missing input stops the script with exit code 2 and the file
named; input from a reduced (smoke) run is never written into paper/ or code/sim/out/figs/ (ms7_e7r_lib.guard_reduced).
Run from code/sim: python -m figs.supp.sf_bl_ms7 [--from-extract [JSON]].
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import sys
from typing import Any, Mapping, Sequence

import numpy as np
from matplotlib.scale import SymmetricalLogTransform
from matplotlib.ticker import FixedLocator, NullLocator

from figs import style
from figs.common import MissingKey, align_baselines, align_right_math, cli, need, text_width_in, write_table
from figs.inputs import Inputs
from figs.supp import ms5b_e7_lib as L
from figs.supp import ms7_e7r_lib as E
from figs.supp.ms4_lib import center_xlabel

NAME = "sf_bl_ms7"
KEYS = style.SUPP_POLICIES_MS7[NAME]
TABLES = ("e7r_tags.tex", "e7r_margins.tex", "e7r_grid.tex", "baseline_study_runs.csv")
RUNS_CSV = TABLES[-1]
RUN_INPUTS = (E.ANALYSIS, E.SELECTION, E.TUNE, E.CONFIRM)
INPUTS = RUN_INPUTS
style.register_supplementary(NAME, "W2", 2.5)
REF = "sublet_v2"
METRICS = ("r0_tr", "W0", "W0plus")
# the rows of the figure after the transplant pairs (as_built_vs_c2): (base tag, variant tag or None)
SPARES_PAIRS = (("BL3-1", "BL3-1-llm"), ("BL3-2", "BL3-2-llm"))
MPC_PAIR = ("MPC-T", "MPC-oracle")
SINGLES = ("A9-P",)
# the part of a variant's registry label that the row prints after the arrow, by the variant's kind, and how the
# registry label is made from the base's (checked in build)
ROW_SUFFIX = {"transplant": r"$\bar{k}$ contract", "spares": "per LLM", "oracle": "oracle forecast"}
# the arrow of a row name: STIX's right arrow, 0.39 em high and centered at half the x height of Liberation Sans (0.26
# em), its ink 2.7 to 3.1 pt from its neighbors', a word space (2.5 to 2.6 pt) and up to 0.5 pt (\! takes back part
# of mathtext's box; with the spaces alone 3.7 to 4.1 pt). The text font's
# U+2192, as built (" \u2192 "), is 0.23 em high and centered 0.17 em above the baseline, small and low next to 7-pt
# lower case (C62 fix round); mathtext's \rightarrow is that glyph too (mathtext.rm is Liberation Sans), while
# \mathbb names a font that the custom fontset lacks, so mathtext takes the arrow from mathtext.fallback (stixsans)
ARROW = r" $\!\mathbb{\rightarrow}\!$ "
DODGE_PT = 2.6                  # the two markers of a row this far above and below its center
GROUP_GAP = 0.1                 # extra space between groups of rows (row units; review of W-G4 B: 0.25 left ten
                                # rows, MPC and its oracle apart, 13.06 pt apart, under the 13.25-pt names)
ROW_PAD = 0.5                   # the y axis beyond the first and the last row (row units)
TICK_END_PT = 1.0               # an x tick label ends at least this far inside its panel
X_STEPS = (0.01, 0.02, 0.025, 0.05, 0.1, 0.2, 0.25, 0.5, 1.0, 2.0)
X_PAD = 0.06                    # the x range beyond the data, as a share of its span (in the scale's coordinates)
LINTHRESH = 0.1                 # the x axes: symmetric log, linear within +-LINTHRESH (final render, C58)
LINSCALE = 1.0                  # the linear part as wide as one decade
DECADES = (-10.0, -1.0, -0.1, 0.0, 0.1, 1.0, 10.0)        # the major ticks of a panel beyond the linear part
ARROW_MIN_PT = 16.0             # no arrow between two medians closer than this (its head would cover them; final
#                                 render, C58: at 10 pt the arrows of 10 to 15 pt were a head without a shaft, which read
#                                 as one more marker)
ARROW_STYLE = "-|>,head_length=0.36,head_width=0.18"     # 0.8 of style.arrow's head (as figs/fig4_v3.py's (c))
ARROW_SHRINK_PT = 4.0           # an arrow ends this far from the centers of its two markers
# C62: the panel titles at style.LABEL_PT (the caption size; common.panel_title sets TICK_PT) on their letters'
# baseline; light vertical grid lines at the decades, no minor ticks (as built, 2..9 times each decade: a comb on
# decades about 0.35 in wide); the groups of rows apart by thin light lines (as ms7_a_lib's rows, not the reference
# grey of the zero line); Sublet's line named above (a)
TITLE_GAP_PT = E.TITLE_GAP_PT   # a title starts this far right of its letter's box (common.panel_title)
TOP_ROOM_PT = 2.0               # the axes this much below the standard top, the letters and titles not: Sublet's name
#                                 above its line ends 3.2 pt above the line's top (1.2 pt in the standard layout)
GRID_DECADES = True            # light vertical lines at the major ticks but 0 (Sublet's line)
SEPARATOR_PT = 0.4              # the line between two groups of rows (ms7_a_lib.SEPARATOR_PT)
LABELS = {"x": "Policy minus Sublet in the same week", "sublet": "Sublet",
          "titles": {"r0_tr": "Trace cost $r_0$", "W0": "Worst case $W_0$", "W0plus": "Worst case $W_0^{+}$"},
          "caption": ("Sublet against the stronger baselines on weeks {weeks} ({n_weeks} week{s}, policy seed 0): the "
                      "paired margin, a policy's cost minus Sublet's in the same week (positive: Sublet costs less), "
                      "of (a)~$r_0$ under the trace lender L-tr, (b)~$W_0$, the largest $r_0$ over the {n_w0} stress "
                      "lenders of the confirmation, and (c)~$W_0^{{+}}$, the largest over these and the {n_new} new "
                      "ones (the adaptive lender through its equivalence with the eager lender). Markers: medians "
                      "over the weeks; bars: min--max; the vertical line is Sublet. Each $x$ axis is linear within "
                      "$\\pm${linthresh} and logarithmic beyond. In a row of two rules the upper "
                      "marker is the first rule and the lower its variant, with an arrow from the first to the second "
                      "where the two are apart: {n_c2} primary baselines as built to their transplants of "
                      "Algorithm~2's base contract $\\bar k$; SpotHedge-style with spares per pool to spares per LLM, "
                      "none while idle, with $\\bar k${mpc_pair}. {mpc_rows}Every policy's values: "
                      "Tables~\\ref{{tab:e7r-tags}} and \\ref{{tab:e7r-margins}}."),
          # C58 (review of W-G4 B): the MPC part of the caption, by mpc_oracle_paired
          "mpc_pair": "; and MPC at the setting of rule T to the same setting with the oracle forecast",
          "mpc_rows": {"paired": "The oracle forecast is a lookahead reference that no comparison set holds; it ran "
                                 "under L-tr and L-hon only. ",
                       "apart": "MPC is drawn at the setting of rule T and, in its own row, the oracle forecast at "
                                "MPC's as-built setting, a lookahead reference that no comparison set holds and that "
                                "ran under L-tr and L-hon only. ",
                       "oracle_only": "The oracle forecast, at MPC's as-built setting, is a lookahead reference that "
                                      "no comparison set holds and that ran under L-tr and L-hon only. ",
                       "mpc_only": "MPC is drawn at the setting of rule T. "}}


# ---------------------------------------------------------------------------------------------------------------
# rows of the figure
def _check_variant(kind: str, base: str, variant: str) -> None:
    b, v = E.label(base), E.label(variant)
    want = {"transplant": f"{b}, {ROW_SUFFIX['transplant']}",
            "spares": b[:-len("per pool")] + ROW_SUFFIX["spares"] if b.endswith(" per pool") else None,
            "oracle": f"{b}, {ROW_SUFFIX['oracle']}"}[kind]
    if v != want:
        raise style.StyleError(f"{NAME}: the registry label of {variant!r} is {v!r}, not {want!r} (ROW_SUFFIX)")


def _setting(info: Mapping | None) -> tuple | None:
    """(registry id, parameters but 'forecast') of an analysis tag block; None without a dict of parameters."""
    if not info or not isinstance(info.get("params"), dict):
        return None
    return info.get("policy_id"), {k: v for k, v in info["params"].items() if k != "forecast"}


def mpc_oracle_paired(an: Mapping) -> bool:
    """Whether the oracle forecast is rule T's MPC setting with the oracle forecast (the same registry id and the same
    parameters but 'forecast'; the parameters are minimal, ms7_baselines.minimal, so equal settings have equal dicts):
    only then is it drawn as MPC's variant (C58, review of W-G4 B)."""
    tags = an.get("tags") or {}
    a, b = _setting(tags.get(MPC_PAIR[0])), _setting(tags.get(MPC_PAIR[1]))
    return a is not None and a == b


def fig_rows(an: Mapping) -> tuple[list[dict], list[str]]:
    """The figure's rows [{label, kind, group, members: [{tag, key, role, <metric>: margin stats}]}] and the tags of
    the rows that the analysis does not have (a family without an eligible tuning configuration has no tuned tag): a
    row keeps the rules it has, a row of one rule is named by that rule's registry label, a row of none is left out.
    MPC and the oracle forecast share a row only where mpc_oracle_paired (C58, review of W-G4 B)."""
    pairs = [(need(p, "as_built", what=E.ANALYSIS), need(p, "c2", what=E.ANALYSIS))
             for p in need(an, "as_built_vs_c2", what=E.ANALYSIS)]
    mpc = ([("mpc", "oracle", MPC_PAIR[0], MPC_PAIR[1])] if mpc_oracle_paired(an)
           else [("mpc", None, t, None) for t in MPC_PAIR])
    spec = ([("transplants", "transplant", a, c) for a, c in pairs]
            + [("spares", "spares", a, c) for a, c in SPARES_PAIRS]
            + mpc
            + [("protected", None, t, None) for t in SINGLES])
    rows, absent = [], []
    margins = need(an, "margins", what=E.ANALYSIS)
    for group, kind, base, var in spec:
        members = []
        for role, t in (("base", base), ("variant", var)):
            if t is None:
                continue
            if t not in margins:
                absent.append(t)
                continue
            mg = margins[t]
            members.append({"tag": t, "key": E.key(t), "role": role,
                            **{m: E.stats_of(need(mg, m, what=f"{E.ANALYSIS} margins.{t}")) for m in METRICS}})
        if not members:
            continue
        if len(members) == 2:
            _check_variant(kind, base, var)
            text = E.label(base) + ARROW + ROW_SUFFIX[kind]
        else:
            text = E.label(members[0]["tag"])
        rows.append({"label": text, "kind": kind if len(members) == 2 else "single", "group": group,
                     "members": members})
    keys = {m["key"] for r in rows for m in r["members"]} | {REF}
    if not keys <= set(KEYS) or set(KEYS) - keys != {E.key(t) for t in absent}:
        raise style.StyleError(f"{NAME}: the figure's keys {sorted(keys)} and the absent tags {absent} are not "
                               f"SUPP_POLICIES_MS7[{NAME!r}]")
    return rows, absent


# ---------------------------------------------------------------------------------------------------------------
# tables
def _tag_rows(an: Mapping) -> list[dict]:
    tags = need(an, "tags", what=E.ANALYSIS)
    out = []
    for t in E.tag_order(tags):
        x = tags[t]
        rc = (x.get("RC") or {}).get(E.TRACE)
        out.append({"tag": t, "key": E.key(t), "label": E.label(t), "group": E.group_of(t, x),
                    "sources": list(x.get("sources") or []), "reproduces_main": x.get("reproduces_main"),
                    "r0_tr": E.stats_of(x.get("r0_tr")), "W0": E.stats_of(x.get("W0")),
                    "W0plus": E.stats_of(x.get("W0plus")), "RC_tr": E.stats_of(rc),
                    "modes": list(x.get("modes") or [])})
    return out


def tags_table(an: Mapping, sel: Mapping) -> dict:
    rows = _tag_rows(an)
    aliases = dict(sel.get("aliases") or {})
    for r in rows:
        r["alias_of"] = aliases.get(r["tag"])
    ch = an.get("checks") or {}
    return {"rows": rows, "aliases": aliases, "identity": ch.get("identity_summary"),
            "a9p_invariance": {k: (ch.get("a9p_invariance") or {}).get(k) for k in ("max_spread", "modes")},
            "scope": {"tags": [r["tag"] for r in rows], "weeks": [str(w) for w in an["weeks"]],
                      "metrics": ["r0_tr", "W0", "W0plus", "RC_tr"]}}


SET_TEXT = {"as_built": "the primary baselines", "notice_aware": "the notice-aware policies",
            "c2": r"the $\bar{k}$ transplants", "spares": "the spare variants", "tuned_T": "the settings of rule T",
            "tuned_W": "the settings of rule W", "all_online": "all baselines"}       # review of W-G4 B


def _n_settings(tags: Mapping, members: Sequence[str]) -> int:
    """The distinct settings among a comparison set's members: tags with the same registry id and the same parameters
    are one setting (integration review of X4: six tuned tags equal other members, e.g. BL1-T = BL1-BO, so the set of
    all baselines holds 31 tags and 25 settings); a tag without parameters counts as its own setting."""
    keys = set()
    for m in members:
        x = tags.get(m) or {}
        keys.add((x.get("policy_id"), json.dumps(x["params"], sort_keys=True)) if isinstance(x.get("params"), dict)
                 else ("tag", m))
    return len(keys)


def margins_table(an: Mapping) -> dict:
    tags = need(an, "tags", what=E.ANALYSIS)
    margins = need(an, "margins", what=E.ANALYSIS)
    rows = []
    for t in E.tag_order(tags):
        if t == "Sublet":
            continue
        mg = need(margins, t, what=E.ANALYSIS)
        rows.append({"tag": t, "label": E.label(t), "group": E.group_of(t, tags[t]),
                     **{m: E.stats_of(mg.get(m)) for m in METRICS}})
    sets = []
    for name, b in need(an, "best_of", what=E.ANALYSIS).items():
        if name not in SET_TEXT:
            raise MissingKey(f"{E.ANALYSIS}: comparison set {name!r} has no text (SET_TEXT)")
        members = list(b.get("members") or [])
        sets.append({"set": name, "members": members, "absent": list(b.get("absent") or []),
                     "n_settings": _n_settings(tags, members),
                     **{m: E.stats_of((b.get("margins") or {}).get(m)) for m in METRICS}})
    # the tags that no comparison set holds (an alias, a W setting equal to its T setting, read as its target), for
    # the caption (review of W-G4 B: the set of all baselines leaves out more than Sublet and the oracle)
    alias = {t: str(s).split("alias of ", 1)[1].rstrip(")") for t, x in tags.items() for s in x.get("sources") or []
             if "alias of " in str(s)}
    held = {m for st in sets for m in st["members"]}
    left_out = [r["tag"] for r in rows if alias.get(r["tag"], r["tag"]) not in held]
    return {"rows": rows, "sets": sets, "left_out": left_out,
            "scope": {"tags": [r["tag"] for r in rows], "sets": [s["set"] for s in sets],
                      "weeks": [str(w) for w in an["weeks"]], "metrics": list(METRICS)}}


def _knob_defaults() -> dict:
    from sublet.experiments import ms7_baselines as mb          # the policies' frozen defaults (read-only)
    return {k: dict(v) for k, v in mb.KNOB_DEFAULTS.items()}


_CONTRACT = {"kstar": r"$k^{\ast}$", "c2": r"$\bar{k}$"}


def setting_text(family: str, policy_id: str, params: Mapping, defaults: Mapping) -> str:
    """A tuning configuration in words, from its parameters over the policy's defaults (ms7_baselines.KNOB_DEFAULTS);
    a value the words do not know is printed as knob=value."""
    p = {**defaults.get(policy_id, {}), **dict(params)}
    other = []

    def word(knob, table):
        v = p.get(knob)
        if v in table:
            return table[v]
        other.append(f"{knob}={v}")
        return None
    parts: list = []
    if family == "BL1":
        parts = [word("demand_stat", {"max": "slot maximum", "mean": "slot mean"}),
                 word("defer_release", {True: "deferred release", False: "immediate release"})]
        parts.append("back-off" if p.get("backoff_cap") is not None else "no back-off")
        parts.append(_CONTRACT.get(p.get("contract_rule", "kstar"), None) or word("contract_rule", {}))
    elif family == "BL2":
        parts = [word("keep", {"none": "keep $0$", "s0": "keep $s_0$"}),
                 word("defer_release", {True: "deferred release", False: "immediate release"}),
                 word("contract_rule", _CONTRACT)]
    elif family == "BL3":
        n = p.get("n_extra")
        if n == 0:
            parts = [r"$N_{\mathrm{Extra}}=0$", word("zone", {"lender": "lender zones", "group": "group zones"}),
                     word("react_at", {"notice": "react at the notice", "death": "react at the death"})]
        else:
            scope = (p.get("extra_scope"), p.get("extra_when_idle"))
            sc = {("pool", True): "per pool", ("llm", False): "per LLM, none while idle"}.get(scope)
            if sc is None:
                other.append(f"extra_scope={scope[0]}, extra_when_idle={scope[1]}")
            parts = [rf"$N_{{\mathrm{{Extra}}}}={n}$" + (f" {sc}" if sc else "")]
        parts.append(word("contract_rule", _CONTRACT))
    elif family == "BL4":
        parts = [f"$W={p.get('window_min')}$ min", word("contract_rule", _CONTRACT)]
    elif family == "BL5":
        parts = [word("use_current_slot", {True: "current slot", False: "lagged slot"})]
        if p.get("tau_min") is not None:
            parts.append(rf"$\tau\geq{int(p['tau_min']) // 60}$ h" if int(p["tau_min"]) % 60 == 0 else
                         f"tau_min={p['tau_min']}")
        parts += [word("lookback", {None: "look-back unlimited", 288: "look-back one day"}),
                  word("refetch_after_reclaim", {"rule": "re-fetch by the rule", "immediate": "re-fetch at once"}),
                  word("contract_rule", _CONTRACT)]
    elif family == "MPC":
        parts = [word("forecast", {"persistence": "persistence", "ewma": "moving average", "oracle": "oracle"}),
                 word("replan_slots", {1: "replan every slot", 3: "replan every 3 slots"}),
                 word("contract_rule", _CONTRACT)]
    else:
        other.append(f"params={dict(params)}")
    return ", ".join([x for x in parts if x] + other)


def family_name(family: str) -> str:
    """A tuning family's name: the label of its rule-T key without ', tuned (trace)' (MPC: 'MPC')."""
    lab = E.label(f"{family}-T") if family != "MPC" else E.label("MPC")
    for suffix in (", tuned (trace)", ", as built"):
        if lab.endswith(suffix):
            return lab[:-len(suffix)]
    return lab


def grid_table(sel: Mapping, an: Mapping) -> dict:
    """Every configuration of the tuning grids with its medians on the tuning weeks (selection.json), the selections
    of rules T and W, and, for the as-built setting and the selected ones, the medians on the confirmation weeks and
    whether T and W hold there (the analysis's confirm block)."""
    defaults = _knob_defaults()
    fams = need(sel, "families", what=E.SELECTION)
    conf = an.get("confirm") or {}
    rows = []
    for fam, f in fams.items():
        cf = ((conf.get("families") or {}).get(fam)) or {}
        tag_of = {f.get("default"): cf.get("as_built")}
        for rule in ("T", "W"):                 # a configuration that is T and W reads T's runs (the same runs)
            if f.get(rule) is not None:
                tag_of.setdefault(f[rule], f"{fam}-{rule}")
        cfgs = sorted(need(f, "configs", what=E.SELECTION).items(), key=lambda kv: kv[1]["index"])
        for name, c in cfgs:
            t = tag_of.get(name)
            holds = {rule: cf.get(f"{rule}_holds") for rule in ("T", "W") if name == f.get(rule)}
            rows.append({"family": fam, "family_name": family_name(fam), "config": name, "number": c["index"] + 1,
                         "setting": setting_text(fam, c["policy_id"], c.get("params") or {}, defaults),
                         "median_r0_tr": c.get("median_r0_tr"), "median_W0": c.get("median_W0"),
                         "eligible": bool(c.get("eligible")), "n_missing": len(c.get("missing") or []),
                         "as_built": name == f.get("default"), "T": name == f.get("T"), "W": name == f.get("W"),
                         "confirm_tag": t,
                         "conf_r0_tr": None if t is None else (cf.get("median_r0_tr") or {}).get(t),
                         "conf_W0": None if t is None else (cf.get("median_W0") or {}).get(t), "holds": holds})
    prov = dict((an.get("checks") or {}).get("provenance") or {})
    return {"rows": rows, "weeks": [str(w) for w in sel.get("weeks") or []],
            "confirm_weeks": [str(w) for w in conf.get("weeks") or []], "provenance": prov,
            "rules": dict((sel.get("meta") or {}).get("rules") or {}),
            "scope": {"configs": [r["config"] for r in rows], "families": list(fams),
                      "weeks": [str(w) for w in sel.get("weeks") or []],
                      "confirm_weeks": [str(w) for w in conf.get("weeks") or []]}}


# ---------------------------------------------------------------------------------------------------------------
# the data file of every run
RUNS_COLUMNS = ("part", "policy", "tag", "lender", "week", "policy_seed", "r0", "rc", "source")


def runs_block(an: Mapping, sel: Mapping, tune: Mapping, conf: Mapping) -> dict:
    """Every run's r0 by part, tag and lender, the values in the order of the part's weeks (null: no run): eval from
    the analysis's merged rows (an alias left out: its runs are its target's), confirm and tune from their summaries.
    The source of an eval value is the confirmation's part main for a tag whose rows combine main's runs with eval's,
    under the seven lenders of the confirmation (the analysis's rule 'table'), else this study."""
    conf_modes = (E.TRACE,) + tuple((an.get("meta") or {}).get("stress_modes") or ()) + (E.HON,)
    aliases = dict(sel.get("aliases") or {})
    weeks = [str(w) for w in an["weeks"]]
    ev = []
    for t in E.tag_order(an["tags"]):
        if t in aliases:
            continue
        x = an["tags"][t]
        main = any(str(s).startswith("confirmation main") for s in x.get("sources") or [])
        for m in sorted(x.get("modes") or [], key=E.mode_rank):
            vals = [((x["per_week"].get(w) or {}).get("r0") or {}).get(m) for w in weeks]
            ev.append([t, m, vals, "confirmation" if main and m in conf_modes else "this study"])
    parts = {"eval": {"weeks": weeks, "rows": ev}}
    for part, s, src in (("confirm", conf, E.CONFIRM), ("tune", tune, E.TUNE)):
        ws = [str(w) for w in need(s, "meta", "weeks", what=src)]
        rows = []
        tab = need(s, "table", what=src)
        for t in sorted(tab, key=lambda t: (t.rsplit("-g", 1)[0], t)):
            for m in sorted(tab[t], key=E.mode_rank):
                rows.append([t, m, [L.val(tab, t, m, w) for w in ws], "this study"])
        parts[part] = {"weeks": ws, "rows": rows}
    return parts


def _policy_of(part: str, tag: str, tune_tags: Mapping) -> str:
    if part == "tune":
        fam = (tune_tags.get(tag) or {}).get("family") or tag.split("-g")[0]
        i = tag.rsplit("-g", 1)[-1]
        return f"{L.plain_label(family_name(fam))}, setting {int(i) + 1}" if i.isdigit() else tag
    return L.plain_label(E.label(tag))


def _csv_num(v) -> str:
    return "" if v is None else format(float(v), ".6f")


def runs_csv(block: Mapping) -> str:
    """The data file RUNS_CSV from the extract's tables.baseline_study_runs (one line per run with a value)."""
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(RUNS_COLUMNS)
    names = block["policy_names"]
    for part in ("eval", "confirm", "tune"):
        p = block["parts"][part]
        hon = {}
        if part == "eval":
            hon = {t: vals for t, m, vals, _s in p["rows"] if m == E.HON}
        for t, m, vals, src in p["rows"]:
            for i, wk in enumerate(p["weeks"]):
                v = vals[i]
                if v is None:
                    continue
                h = (hon.get(t) or [None] * len(p["weeks"]))[i]
                rc = None if part != "eval" or m == E.HON or h is None else float(v) - float(h)
                w.writerow([part, names[part][t], t, E.mode_plain(m), wk, 0, _csv_num(v), _csv_num(rc), src])
    return buf.getvalue()


def runs_entry(parts: Mapping, tune: Mapping) -> dict:
    tune_tags = (tune.get("meta") or {}).get("tags") or {}
    names = {part: {t: _policy_of(part, t, tune_tags) for t, *_ in p["rows"]} for part, p in parts.items()}
    block = {"parts": parts, "policy_names": names}
    text = runs_csv(block)
    return {**block, "file": RUNS_CSV, "columns": list(RUNS_COLUMNS), "n_rows": text.count("\n") - 1,
            "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "scope": {"parts": list(parts), "tags": sorted({t for p in parts.values() for t, *_ in p["rows"]}),
                      "weeks": {k: list(p["weeks"]) for k, p in parts.items()}}}


# ---------------------------------------------------------------------------------------------------------------
def build(inp: Inputs) -> dict:
    an = E.read(inp, E.ANALYSIS, NAME)
    sel = E.read(inp, E.SELECTION, NAME)
    tune = E.read(inp, E.TUNE, NAME)
    conf = E.read(inp, E.CONFIRM, NAME)
    weeks = E.check_weeks(an, E.ANALYSIS)
    meta = an.get("meta") or {}
    stress, new = list(meta.get("stress_modes") or []), list(meta.get("new_modes") or [])
    if not stress or not new:
        raise MissingKey(f"{E.ANALYSIS}: meta.stress_modes or meta.new_modes is missing")
    for what, ws in ((E.SELECTION, sel.get("weeks")), (E.TUNE, (tune.get("meta") or {}).get("weeks"))):
        if [str(w) for w in ws or []] != [str(w) for w in (sel.get("weeks") or [])]:
            raise style.StyleError(f"{what}: the tuning weeks {ws} are not the selection's {sel.get('weeks')}")
    cweeks = [str(w) for w in ((an.get("confirm") or {}).get("weeks") or [])]
    if cweeks != [str(w) for w in (conf.get("meta") or {}).get("weeks") or []]:
        raise style.StyleError(f"{E.CONFIRM}: its weeks are not the analysis's confirm weeks {cweeks}")
    rows, absent = fig_rows(an)
    parts = runs_block(an, sel, tune, conf)
    out = {"keys": list(KEYS), "weeks": weeks, "metrics": list(METRICS), "rows": rows, "absent": absent,
           "mpc_oracle_paired": mpc_oracle_paired(an), "n_transplants": len(an["as_built_vs_c2"]),
           "modes": {"stress": stress, "new": new, "w0plus": list(meta.get("w0plus_modes") or [])},
           "tables": {"e7r_tags": tags_table(an, sel), "e7r_margins": margins_table(an),
                      "e7r_grid": grid_table(sel, an),
                      "baseline_study_runs": runs_entry(parts, tune)},
           "labels": dict(LABELS),
           "meta": {**E.meta_of({"analysis": an, "selection": sel, "tune": tune, "confirm": conf}),
                    "analysis_sha256": meta.get("script_sha256"), "eval_git_revision": meta.get("eval_git_revision")}}
    out["labels"]["caption"] = caption(out)
    out["meta"]["sources"] = list(inp.sources)
    return out


def caption(d: Mapping) -> str:
    n = len(d["weeks"])
    absent = d.get("absent") or []
    drawn = {m["tag"] for r in d["rows"] for m in r["members"]}
    if d["mpc_oracle_paired"]:
        mpc_pair, mpc_rows = LABELS["mpc_pair"], LABELS["mpc_rows"]["paired"]
    else:                                   # C58 (review of W-G4 B): the oracle is not rule T's variant
        which = ("apart" if set(MPC_PAIR) <= drawn else "oracle_only" if MPC_PAIR[1] in drawn
                 else "mpc_only" if MPC_PAIR[0] in drawn else None)
        mpc_pair, mpc_rows = "", ("" if which is None else LABELS["mpc_rows"][which])
    return LABELS["caption"].format(weeks=L.week_span(d["weeks"]), n_weeks=n, s="s" if n != 1 else "",
                                    n_w0=E.count(len(d["modes"]["stress"])), n_new=E.count(len(d["modes"]["new"])),
                                    n_c2=E.count(d["n_transplants"]), mpc_pair=mpc_pair, mpc_rows=mpc_rows,
                                    linthresh=f"{LINTHRESH:g}") + \
        ((" Not in the analysis: " + E.join(L.tex(E.label(t)) for t in absent) + ".") if absent else "")


# ---------------------------------------------------------------------------------------------------------------
# drawing
def row_positions(rows: Sequence[Mapping]) -> list[float]:
    """y of each row (the first on top), with GROUP_GAP between groups."""
    ys, y, prev = [], 0.0, None
    for r in rows:
        if prev is not None and r["group"] != prev:
            y -= GROUP_GAP
        ys.append(y)
        y -= 1.0
        prev = r["group"]
    return [v - min(ys) for v in ys]


def _scale() -> SymmetricalLogTransform:
    """The x axes' transform: symmetric log, linear within +-LINTHRESH (as ax.set_xscale('symlog', ...) sets it)."""
    return SymmetricalLogTransform(10, LINTHRESH, LINSCALE)


def _fwd(v: Sequence[float]) -> np.ndarray:
    return _scale().transform(np.asarray(v, dtype=float))


def _inv(v: Sequence[float]) -> np.ndarray:
    return _scale().inverted().transform(np.asarray(v, dtype=float))


def x_ticks(lo: float, hi: float) -> list[float]:
    """The major ticks in [lo, hi]: the decades of DECADES where the range leaves the linear part (at least two of
    them), else the first step of X_STEPS that gives 3 to 5 ticks."""
    if max(abs(lo), abs(hi)) > LINTHRESH:
        dec = [v for v in DECADES if lo - 1e-12 <= v <= hi + 1e-12]
        if len(dec) >= 2:
            return dec
    for st in X_STEPS:
        t = [round(k * st, 10) for k in range(math.ceil(lo / st - 1e-9), math.floor(hi / st + 1e-9) + 1)]
        if 3 <= len(t) <= 5:
            return t
    return [round(lo, 3), 0.0, round(hi, 3)] if lo < 0 < hi else [round(lo, 3), round(hi, 3)]


def x_range(rows: Sequence[Mapping], metric: str) -> tuple[float, float]:
    """The data range of a panel (medians and bar ends, and Sublet's 0), padded by X_PAD of its span in the scale's
    coordinates."""
    vals = [0.0] + [v for r in rows for m in r["members"] for f in ("median", "min", "max")
                    for v in [(m.get(metric) or {}).get(f)] if v is not None]
    tl, th = _fwd([min(vals), max(vals)])
    span = max(th - tl, 1e-6)
    lo, hi = _inv([tl - X_PAD * span, th + X_PAD * span])
    return float(lo), float(hi)


def x_axis(ax, lo: float, hi: float) -> list[float]:
    """Scale, limits and ticks of a panel: ticks over the data range [lo, hi]; the limits widened, where needed, so that
    the first and the last tick label end TICK_END_PT inside the panel (the panels of a row stand 0.14 in apart), in
    the scale's coordinates."""
    ax.set_xscale("symlog", linthresh=LINTHRESH, linscale=LINSCALE)
    ticks = x_ticks(lo, hi)
    fig = ax.figure
    w_pt = style.axes_rect_in(ax)[2] * style.BP_PER_IN
    half = [0.5 * text_width_in(fig, style.PLAIN(t)) * style.BP_PER_IN + TICK_END_PT for t in (ticks[0], ticks[-1])]
    t0, t1 = _fwd([ticks[0], ticks[-1]])
    tlo, thi = _fwd([lo, hi])
    # solve lo' and hi' so that tick0 - lo' >= half0 * (hi' - lo') / w_pt and hi' - tick1 >= half1 * (hi' - lo') / w_pt
    for _ in range(20):
        per = (thi - tlo) / w_pt
        lo2, hi2 = min(tlo, t0 - half[0] * per), max(thi, t1 + half[1] * per)
        if (lo2, hi2) == (tlo, thi):
            break
        tlo, thi = lo2, hi2
    lo, hi = (float(v) for v in _inv([tlo, thi]))
    ax.set_xlim(lo, hi)
    ax.xaxis.set_major_locator(FixedLocator(ticks))
    ax.xaxis.set_major_formatter(style.PLAIN)
    ax.xaxis.set_minor_locator(NullLocator())           # C62: no comb of minor ticks on the short decades
    if GRID_DECADES:
        for t in ticks:
            if t != 0.0:
                g = ax.axvline(t, color=style.GRID_GREY, linewidth=style.GRID_PT, zorder=0.5, label="_nolegend_")
                g._sublet_role = "grid"
    return ticks


def draw_panel(ax, rows: Sequence[Mapping], ys: Sequence[float], metric: str, dodge: float) -> list:
    """Sublet's line, the group dividers, the bars, markers and arrows of one panel; returns the drawn points
    [(key, x, y)]."""
    p = style.policy(REF)
    ln = ax.axvline(0.0, color=p.color, linewidth=style.LINE_PT, zorder=style.Z_REFERENCE + 0.1, label="_nolegend_")
    ln._sublet_policy = REF
    ln._sublet_role = "sublet_zero"
    for i in range(1, len(rows)):
        if rows[i]["group"] != rows[i - 1]["group"]:
            sep = ax.axhline(0.5 * (ys[i] + ys[i - 1]), color=style.GRID_GREY, linewidth=SEPARATOR_PT, zorder=0.6,
                             label="_nolegend_")
            sep._sublet_role = "separator"
    pts = []
    for r, y in zip(rows, ys):
        two = len(r["members"]) > 1
        drawn = []
        for m in r["members"]:
            st = m.get(metric) or {}
            if st.get("median") is None:
                continue
            yy = y + (dodge if m["role"] == "base" else -dodge) if two else y
            if st.get("min") is not None and st.get("max") is not None and st["max"] > st["min"]:
                style.errorbars(ax, m["key"], [st["median"]], [yy], [st["min"]], [st["max"]], orientation="x")
            mk = style.scatter_policy(ax, m["key"], [st["median"]], [yy])
            mk._sublet_role = "median"
            drawn.append((m["key"], float(st["median"]), yy))
        pts += drawn
        if len(drawn) == 2:
            (k0, x0, y0), (k1, x1, y1) = drawn
            a, b = ax.transData.transform((x0, y0)), ax.transData.transform((x1, y1))
            if float(np.hypot(*(a - b))) * 72.0 / ax.figure.dpi >= ARROW_MIN_PT:
                arr = style.arrow(ax, (x0, y0), (x1, y1), color=style.policy(k0).label_color, linewidth=0.6,
                                  shrinkA=ARROW_SHRINK_PT, shrinkB=ARROW_SHRINK_PT, arrowstyle=ARROW_STYLE)
                arr._sublet_role = "arrow"
                arr._sublet_pair = (k0, k1)
    return pts


def draw(data: Mapping) -> Any:
    fig = style.new_figure(NAME)
    rows, lab = data["rows"], data["labels"]
    names = [r["label"] for r in rows]
    left = style.ytick_reserve(fig, names)
    axes = style.panel_row(fig, [1.0, 1.0, 1.0], sharey=[False, True, True], left=[left, None, None],
                           top=style.MARGIN_TOP + TOP_ROOM_PT / style.BP_PER_IN)
    ys = row_positions(rows)
    y0, y1 = min(ys) - ROW_PAD, max(ys) + ROW_PAD
    axes[0].set_ylim(y0, y1)
    h_pt = style.axes_rect_in(axes[0])[3] * style.BP_PER_IN
    dodge = DODGE_PT * (y1 - y0) / h_pt
    for ax, metric in zip(axes, data["metrics"]):
        x_axis(ax, *x_range(rows, metric))
        draw_panel(ax, rows, ys, metric, dodge)
    axes[0].set_yticks(ys)
    axes[0].set_yticklabels(names)
    for ax in axes:
        ax.tick_params(axis="y", length=0)          # (it resets the tick labels' transforms: before align_baselines)
    align_baselines([tk.label1 for tk in axes[0].yaxis.get_major_ticks()])     # C62: names with math on the pitch
    align_right_math([tk.label1 for tk in axes[0].yaxis.get_major_ticks()])  # and at the plain names' right end
    center_xlabel(axes, lab["x"])
    letters = style.panel_letters(axes)
    E.raise_letters(letters, TOP_ROOM_PT / style.BP_PER_IN)
    for letter, metric in zip(letters, data["metrics"]):
        E.title(letter, lab["titles"][metric])
    sublet_label(axes[0], letters[0], lab.get("sublet"))
    fig._sublet_axes = axes
    return fig


def sublet_label(ax, letter, text: str | None):
    """Sublet's name in its label color, centered over its line at 0 of `ax`, on the letters' baseline above the axes
    (C62: in place of the x label's "(Sublet: the line at 0)"); not drawn where it would come within TITLE_GAP_PT of
    another text on that line or leave the page."""
    from matplotlib.transforms import blended_transform_factory
    if not text:
        return None
    fig = ax.figure
    t = fig.text(0.0, letter.get_position()[1], text, transform=blended_transform_factory(ax.transData, fig.transFigure),
                 ha="center", va="baseline", fontsize=style.TICK_PT, color=style.policy(REF).label_color)
    r = fig.canvas.get_renderer()
    bb, pad = t.get_window_extent(r), TITLE_GAP_PT * fig.dpi / style.BP_PER_IN
    for o in fig.texts:
        if o is t or not o.get_text():
            continue
        ob = o.get_window_extent(r)
        if bb.x0 < ob.x1 + pad and ob.x0 < bb.x1 + pad and bb.y0 < ob.y1 and ob.y0 < bb.y1:
            t.remove()
            return None
    if bb.x0 < 0:
        t.remove()
        return None
    t._sublet_role, t._sublet_policy = "direct_label", REF
    return t


# ---------------------------------------------------------------------------------------------------------------
# LaTeX
NAME_IN = 1.95                  # the name column of e7r_tags and e7r_margins (in)


def _with_groups(items: Sequence[Mapping], cells) -> tuple[list, list]:
    """The rows and the indices before which a rule goes (a change of group, ms7_e7r_lib.GROUP_ORDER)."""
    rows, groups, prev = [], [], None
    for x in items:
        if x["group"] != prev:
            groups.append(len(rows))
            prev = x["group"]
        rows.append(cells(x))
    return rows, groups


def groups_text(items: Sequence[Mapping]) -> str:
    """The groups of a table's rows in their order, for its caption (ms7_e7r_lib.GROUP_TEXT)."""
    seen = list(dict.fromkeys(x["group"] for x in items))
    return E.join(E.GROUP_TEXT[g] for g in seen)


def _bound(x) -> str:
    return "0" if not x else L.bound_text(float(x))


def tags_tex(t: Mapping, d: Mapping) -> str:
    def cells(r):
        mark = (r"$^{\dagger}$" if r.get("alias_of") else "") + (r"$^{\ddagger}$" if r.get("reproduces_main") is False
                                                                  else "")
        return [L.rag(L.tex(r["label"]) + mark), E.med_range(r["r0_tr"]), E.med_range(r["W0"]),
                E.med_range(r["W0plus"]), E.med_range(r["RC_tr"])]
    rows, groups = _with_groups(t["rows"], cells)
    ids = t.get("identity") or {}
    inv = t.get("a9p_invariance") or {}
    n_w = len(d["weeks"])
    ident = ""
    if ids.get("pairs_with_cells"):
        ident = (f" The runs repeated at this study's code version equal the confirmation's in "
                 f"{ids['identical']} of {ids['pairs_with_cells']} pairs of policies with the same rule and settings "
                 f"({ids['cells']:,} shared runs; largest difference {_bound(ids.get('max_abs_diff'))}).")
    inv_t = ""
    if inv.get("max_spread") is not None:
        nm = E.count(len(inv.get("modes") or []))
        inv_t = (f" Protected-only renting holds no revocable lease: its $r_0$ is the same under all {nm} lenders in "
                 f"every week." if inv["max_spread"] == 0 else
                 f" Protected-only renting's $r_0$ differs across its {nm} lenders by at most "
                 f"{_bound(inv['max_spread'])} in any week.")
    alias = ""
    if t.get("aliases"):
        al = sorted(t["aliases"])
        alias = (r" $^{\dagger}$For " + E.join(L.tex(E.label(a)) for a in al) + ", the setting of rule W equals "
                 "that of rule T; " + ("it" if len(al) == 1 else "each") + " ran once.")
    repro = ""
    if any(r.get("reproduces_main") is False for r in t["rows"]):
        repro = r" $^{\ddagger}$Its repeated trace-lender runs differ from the confirmation's."
    cap = (r"Every policy of the baseline study on weeks " + L.week_span(d["weeks"]) + f" ({n_w} week"
           + ("s" if n_w != 1 else "") + r", policy seed 0): $r_0$ under the trace lender L-tr, $W_0$ (the largest "
           r"$r_0$ over the " + E.count(len(d["modes"]["stress"])) + r" stress lenders of the confirmation), $W_0^{+}$ "
           r"(over these and the " + E.count(len(d["modes"]["new"])) + r" new ones) and the revocation cost RC under "
           r"L-tr; "
           r"median and, in parentheses, min--max over the weeks. Rules separate " + groups_text(t["rows"])
           + r". The confirmation's policies take their runs under "
           r"its seven lenders from the confirmation. MPC with the oracle forecast, at MPC's as-built setting, ran "
           r"under L-tr and L-hon only."
           + ident + inv_t + alias + repro + r" Every run is in the data file " + L.tex(RUNS_CSV) + ".")
    return L.longtable("@{}p{" + f"{NAME_IN}in" + "}cccc@{}", cap, "tab:e7r-tags",
                       ["Policy", r"$r_0$, L-tr", "$W_0$", r"$W_0^{+}$", "RC, L-tr"], rows, groups=groups,
                       tabcolsep="2.4pt")


def margins_tex(t: Mapping, d: Mapping) -> str:
    def cells(r):
        out = [L.rag(L.tex(r["label"]))]
        for m in METRICS:
            if r["group"] == "mpc-reference" and not (r[m] or {}).get("n"):
                out += ["not run", "--"]                 # the lookahead reference ran under L-tr and L-hon only
            else:
                out += [E.wtl(r[m]), E.med_range(r[m])]
        return out
    rows, groups = _with_groups(t["rows"], cells)
    groups.append(len(rows))
    absent = []
    for s in t["sets"]:
        n_set = s["n_settings"]
        out = [L.rag(r"Best of " + SET_TEXT[s["set"]] + f" ({n_set})")]
        for m in METRICS:
            out += [E.wtl(s[m]), E.med_range(s[m])]
        rows.append(out)
        absent += [a for a in s["absent"] if a not in absent]
    n_w = len(d["weeks"])
    cap = (r"Sublet's margin over every policy of the baseline study and over the best member of each comparison "
           r"set on weeks " + L.week_span(d["weeks"]) + f" ({n_w} week" + ("s" if n_w != 1 else "") + r"): a "
           r"policy's value minus Sublet's in the same week (positive: Sublet costs less), on $r_0$ under L-tr, "
           r"$W_0$ and $W_0^{+}$; weeks won, tied and lost (W/T/L; +$m$: $m$ weeks without a run, counted as losses), "
           r"median and min--max over the weeks with a value. Rules separate " + groups_text(t["rows"]) + r", and the "
           r"best members of the comparison sets. The best member of a set is, per week and metric, its "
           r"member of least value (number of distinct settings in parentheses); the sets are the primary baselines as "
           r"built, the notice-aware policies, the transplants of the $\bar{k}$ contract, the spare variants, the "
           r"settings of rules T and W, and all baselines, these sets together with protected-only renting"
           + ("" if not t.get("left_out") else
              r" (no set holds " + E.join(L.tex(E.label(x)) for x in t["left_out"]) + ")")
           + r". MPC with the oracle forecast, at MPC's as-built setting, ran under L-tr and L-hon only (not run: "
           r"$W_0$ and $W_0^{+}$ need the stress lenders)."
           + (r" Not run: " + E.join(L.tex(E.label(a)) for a in absent) + "." if absent else ""))
    head_top = (r" & \multicolumn{2}{c}{$r_0$, L-tr} & \multicolumn{2}{c}{$W_0$} & \multicolumn{2}{c}{$W_0^{+}$} \\"
                "\n" r"\cmidrule(lr){2-3}\cmidrule(lr){4-5}\cmidrule(l){6-7}")
    return L.longtable("@{}p{" + f"{NAME_IN}in" + "}cccccc@{}", cap, "tab:e7r-margins",
                       ["Policy", "W/T/L", "Median (min--max)", "W/T/L", "Median (min--max)", "W/T/L",
                        "Median (min--max)"], rows, groups=groups, tabcolsep="2.0pt", head_top=head_top)


def grid_tex(t: Mapping, d: Mapping) -> str:
    rows, groups, prev = [], [], None
    for r in t["rows"]:
        first = r["family"] != prev
        if first:
            groups.append(len(rows))
            prev = r["family"]
        sel = [x for x, on in (("as built", r["as_built"]), ("T", r["T"]), ("W", r["W"])) if on]
        elig = "yes" if r["eligible"] else f"no ({r['n_missing']} missing)"
        holds = ", ".join(f"{k} {'yes' if v else 'no'}" for k, v in r["holds"].items() if v is not None)
        rows.append([L.rag(L.tex(r["family_name"])) if first else "", str(r["number"]), L.rag(r["setting"]),
                     E.num(r["median_r0_tr"]), E.num(r["median_W0"]), elig, ", ".join(sel),
                     "" if r["confirm_tag"] is None else E.num(r["conf_r0_tr"]),
                     "" if r["confirm_tag"] is None else E.num(r["conf_W0"]), holds])
    pv = t.get("provenance") or {}
    prov = ""
    if pv:
        same = pv.get("eval_selection_equal") and pv.get("confirm_selection_equal")
        prov = (r" The evaluation and confirmation parts recorded the selection that the analysis read ("
                + ("the same file" if same else "not the same file in every part") + r"), and the three parts ran "
                + ("at one code version" if pv.get("one_commit") else "at more than one code version") + ".")
    n = len(t["rows"])
    dw, cw = L.week_span(t["weeks"]), L.week_span(t["confirm_weeks"])
    cap = (r"The tuned settings: the " + str(n) + r" configurations of the tuning grids, each family's numbered in "
           r"grid order from the as-built one, with the median $r_0$ under L-tr and the median $W_0$ over the tuning "
           r"weeks " + dw + r" (policy seed 0) and whether every run of the configuration is there (eligible); rule T "
           r"selects the eligible configuration of least median $r_0$, ties by grid order, and rule W the one of "
           r"least median $W_0$, ties by the median $r_0$, then grid order. The as-built and the selected "
           r"configurations ran again on the confirmation weeks " + cw + r", with their medians there: T holds where "
           r"its median $r_0$ is at most the as-built setting's, W where its median $W_0$ is. The selection program "
           r"was registered with the analysis before the runs." + prov)
    head_top = (r" & & & \multicolumn{4}{c}{Weeks " + dw + r"} & \multicolumn{3}{c}{Weeks " + cw + r"} \\" "\n"
                r"\cmidrule(lr){4-7}\cmidrule(l){8-10}")
    return L.longtable("@{}p{1.0in}rp{2.8in}ccccccl@{}", cap, "tab:e7r-grid",            # 2.8in: no overfull box
                       ["Family", "No.", "Setting", r"$r_0$, L-tr", "$W_0$", "Eligible", "Selected", r"$r_0$, L-tr",
                        "$W_0$", "Holds"], rows, groups=groups, tabcolsep="2.2pt", size=r"\scriptsize", keep=0,
                       head_top=head_top)


def write_tables(data: Mapping, report: Mapping) -> None:
    """The three tables and the data file RUNS_CSV from the extract's `tables` (the file's sha256 checked against the
    extract's)."""
    E.guard_reduced(data, NAME)
    t = data["tables"]
    head = L.table_head
    paths = [write_table(TABLES[0], head(NAME, [E.ANALYSIS, E.SELECTION]) + tags_tex(t["e7r_tags"], data)),
             write_table(TABLES[1], head(NAME, [E.ANALYSIS]) + margins_tex(t["e7r_margins"], data)),
             write_table(TABLES[2], head(NAME, [E.SELECTION, E.ANALYSIS]) + grid_tex(t["e7r_grid"], data))]
    text = runs_csv(t["baseline_study_runs"])
    if hashlib.sha256(text.encode("utf-8")).hexdigest() != t["baseline_study_runs"]["sha256"]:
        raise style.StyleError(f"{NAME}: {RUNS_CSV} differs from the sha256 that the extract records")
    paths.append(write_table(RUNS_CSV, text))
    print(f"[{NAME}] wrote {', '.join(str(p) for p in paths)}")


def main(argv: Sequence[str] | None = None) -> dict:
    def build_checked(inp: Inputs) -> dict:
        d = build(inp)
        E.guard_reduced(d, NAME)
        return d

    def draw_checked(d: Mapping) -> Any:
        E.guard_reduced(d, NAME)
        return draw(d)

    try:
        return cli(NAME, build_checked, draw_checked, argv, supplementary=True, after=write_tables, doc=__doc__)
    except E.MissingInput as err:
        print(err.code, file=sys.stderr)
        raise SystemExit(2) from None


if __name__ == "__main__":
    main(sys.argv[1:])
