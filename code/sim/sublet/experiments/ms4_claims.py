"""The MS4 claims report (design/sim_spec_ms4.md §1.4 items 1, 2 and 5; deliverable D38, unit U25; open choices
M30, M32).

Reads the MS4 summaries and the records that §3-§7 name under an input root and writes the report
code/sim/out/ms4_claims.md and ms4_claims.json, on the model of ms3_claims (whose helpers it uses; ms3_claims changes
only by C17): one row per check of §3.11 (E7), §4.9 (E3), §5.7 (E5), §6.9 (E4) and §7.9 (E8), in the spec's order,
with the check id, the claim (the spec row and the summary's `claim` field), the design's status label for the claim
it tests (copied from the spec or the design, never upgraded; null where the check tests no theory claim, with what
it tests), the reference value and file, the regenerated value and file, and the verdict; then Table III's measured
height next to its budget (§1.4 item 5, from code/sim/out/figs/floats_heights_ms4.json), the small glyphs of every MS4
figure (§1.4 item 1), the copy records of e3, e4, e5, e7 and e8, the job records of every MS4 experiment folder
against its job list, and the caption drafts (§8.1: Fig. 4's caption is drafted here; §9: Table III's caption facts).

  python -m sublet.experiments.ms4_claims [--root DIR] [--out-dir DIR] [--no-figures] [--only NAME ...]
                                          [--extracts DIR]

  --root DIR      the input root, a folder with the repository's layout (code/sim/out/e7/main/summary.json, ...):
                  default SUBLET_FIGS_IN_ROOT (the variable of figs.inputs), else the repository; the tests pass
                  the MS4 fixture tree tests/fixtures_figs_ms4/inputs/
  --out-dir DIR   where ms4_claims.md and ms4_claims.json go: default the repository's code/sim/out when the root is
                  the repository; required with any other root
  --no-figures    skip the figure reruns (the 'figures' block says so)
  --only NAME     rerun only these figures (names as style.save's: fig4, sf_e5, ...)
  --extracts DIR  the folder of the figure extracts <name>.json (default <root>/code/sim/out/figs)

Run from code/sim in the 3 GB scope. Exit 0 once the report is written, whatever its verdicts.

Rows and verdicts. A row reads its check entry checks.<id> of the experiment's summary: E7's from
code/sim/out/e7/main/summary.json, whose `checks` holds every id of §3.11 once, combined over the four part
summaries (entry {status, claim, parts {<part>: the part's entry}, part_status}; §3.11, "Where the checks are"), and
the others from e3/, e5/, e4/ and e8/summary.json. `status` is one of §2.6's: pass, fail, missing, pending,
explained, informative. Verdicts (§1.4 item 2; MS3 spec §1.4 item 2):
  reproduced   status pass of a check that reproduces an earlier value (kind 'reproduction': E7-7, E4-1)
  holds        status pass of a property check
  bug          status fail; also a status outside §2.6's vocabulary, 'explained' (no check of §3.11, §4.9, §5.7,
               §6.9 or §7.9 allows an explanation: their verdict rules are "else bug" or "informative"),
               'informative' where the spec sets a pass condition, an input that is not a JSON object, and every
               row of a summary whose meta.reduced is true (a smoke run, never a result): for E7 also when a part
               summary that main's combined entry used is reduced, or when that part summary's own entry no longer
               has the status main copied (main's entry is stale: the part's summary was rebuilt after main's);
               for E3-7 also when e3/gate.json is reduced
  explained    never in MS4 (kept for the vocabulary: a check whose spec allowed it would carry its text)
  informative  the rows the spec marks informative (they report a value and have no pass condition; E3-7 and E4-5
               are informative unless the summary says fail: a gate whose config hash or MILP limit is not the
               grid's, a combiner run above 5.83 on an exact core export)
  missing      the check's output, summary or job is absent (or the summary says missing)
  pending      the summary says pending (a rerun or MILP job outstanding)
The informative rows carry the spec's reading as their note (`remark`). Nothing is computed here: every value is read.

Criterion (§1.4 item 2): it holds iff no row is 'bug' and every row other than reproduced, holds and informative is
'explained' with its text; since no MS4 row may be explained, it holds iff every row is reproduced, holds or
informative, and a missing or pending row keeps it from holding until its output exists. The job records
(jobs_block) do not enter it: a summary built from a partial job set marks its checks over the runs that exist, so
the report's head lists the jobs without an 'ok' record, and tests/test_ms4_out.py fails on those outside Q39's MILP
rule (§1.4 item 3).

Figures (§1.4 item 1): every MS4 figure script (MS4_FIGURE_SCRIPTS: Fig. 4, §8.1, and the eight supplementary
scripts of §8.2) is rerun in this process with --from-extract <extracts>/<name>.json, its PDF, extract, preview and
tables going to a temporary folder (SUBLET_FIGS_PDF_DIR, SUBLET_FIGS_OUT_DIR, SUBLET_FIGS_TABLES_DIR set for the run,
SUBLET_FIGS_IN_ROOT to the root; never paper/ nor code/sim/out/figs/), and the report that figs.common.cli returns
gives its small_glyphs ([size, text] of every mathtext text with glyphs below style.SCRIPT_MIN_PT, 6.3 pt); a figure
whose extract is missing is listed as 'missing', one whose script is missing, names another figure or raises
(finalize() included) as 'error'.

Output schema of ms4_claims.json (key paths; the .md shows the same content as tables):
  meta.module, meta.spec, meta.git_revision, meta.written, meta.input_root, meta.input_root_is_repository
  meta.out_dir, meta.inputs.<repository-relative name>   'ok' | 'missing' | 'invalid JSON: ...' (files read)
  criterion.holds, criterion.text, criterion.reasons, criterion.n_rows, criterion.counts.<verdict>,
  criterion.bug, criterion.missing, criterion.pending, criterion.explained, criterion.unexplained   (ms3_claims')
  rows[]                             one per check, in the order of SPECS:
    id, experiment ('E7', 'E3', 'E5', 'E4', 'E8'), section ('§3.11', ...), kind ('reproduction' | 'property' |
    'informative'), claim.spec, claim.summary (the summary's claim field or null), status_label (the design's
    label, copied; null where the check tests no theory claim), status_label_note, reference.value (the spec's
    text), reference.values {path: value} (read from the entry where the summary records them), reference.file,
    regenerated.value {path: value} (fields of the check entry: '#x' as 'len(x)', 'min:x', 'max:x' and 'sum:x' as
    'min(x)', 'max(x)', 'sum(x)' over a list or the values of a mapping, 'a[*].b' the list of b over the list a,
    'a.*.b' the mapping {key: b} over the mapping a), regenerated.file, summary_status (the status read, or null),
    verdict, explanation (null in MS4), note (why a row is missing, pending or a bug, and the informative rows'
    remarks; else null), parts (E7 rows: {part: the part's status in main's entry})
  floats.file, floats.present, floats.rows[] {float, name, measured_pages, budget_pages, within_budget,
    difference_pages, source}, floats.note
  figures.run (bool), figures.extracts, figures.rows[] {figure, script, extract, status ('ok' | 'missing' |
    'error'), small_glyphs [[size, text]], n_small_glyphs, n_glyph_warnings, min_glyph_pt, text_pt, error},
    figures.counts.<status>, figures.note
  copy_checks.records.<exp> for exp in e3, e4, e5, e7, e8: file, present, pass, exp_matches, commit (the clone's
    commit), time, failed (the names of the failed checks), parts, records_by_status; copy_checks.commits (the
    distinct clone commits of the present records), copy_checks.one_commit (null without a record), copy_checks.note
  jobs.rows.<folder> for folder in e7/main, e7/stress, e7/gap, e7/allow, e3, e5, e4, e8: manifest, present,
    n_listed, by_status {status: n} ('no record' where a listed job has none), n_blocking, blocking [{job, kind,
    status}] (at most 50), n_milp_lp_fallback, milp_lp_fallback (MILP jobs whose output is a lower bound,
    LB_MILP_PREFIXES, with status wall_limit or oom_at_3G: LB = LP, §2.5), n_unlisted_records, n_unreadable_records,
    summary_jobs_missing, summary_ignored_outputs, summary_outputs_missing (lengths of the summary's meta lists)
  jobs.n_blocking, jobs.note
  captions.fig4 {text, n_chars, max_chars, within_limit, values {own_capacity_usd, n_alignments, n_policy_seeds,
    u}, notes, sources}; captions.table3 {certificates (the line of Table III's caption), held, n, by_case, B0_rule,
    gamma, kappa, info_class_reported, own_capacity_usd_median, scope, source, notes}
"""
from __future__ import annotations

import argparse
import contextlib
import io
import os
import shutil
import statistics
import sys
import tempfile
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from .. import paths
from . import ms3_claims as m3
from . import ms3_common as mc

SPEC_DOC = "design/sim_spec_ms4.md"
OUT_MD, OUT_JSON = "ms4_claims.md", "ms4_claims.json"
ENV_IN_ROOT, ENV_FIG_DIRS = m3.ENV_IN_ROOT, m3.ENV_FIG_DIRS

OUT = "code/sim/out"
E7_PARTS = ("main", "stress", "gap", "allow")              # ms3_common.COPY_PARTS['e7'] (C20)
E7_SUM = f"{OUT}/e7/main/summary.json"
E7_PART_SUM = {p: f"{OUT}/e7/{p}/summary.json" for p in E7_PARTS}
E3_SUM, E3_GATE = f"{OUT}/e3/summary.json", f"{OUT}/e3/gate.json"
E5_SUM, E4_SUM, E8_SUM = f"{OUT}/e5/summary.json", f"{OUT}/e4/summary.json", f"{OUT}/e8/summary.json"
TABLE3 = f"{OUT}/e7/table3.json"
FLOATS = f"{OUT}/figs/floats_heights_ms4.json"               # paper/layout_check/pageplan/floats_heights.py --ms4
FLOAT_NAMES = {"table3_e7": "Table III"}
COPY_EXPS = ("e3", "e4", "e5", "e7", "e8")
JOB_FOLDERS = ("e7/main", "e7/stress", "e7/gap", "e7/allow", "e3", "e5", "e4", "e8")   # §3-§7 order
# the MILP jobs whose output is a lower bound, to which Q39's rule (LB = LP at the wall-clock limit or the cap, §2.5)
# applies: E3's MILPs (§4.6) and E4's OPT_eager of the ratio days (§6.7); E4's P-hat day jobs (e4:phat, kind 'milp')
# are plans, and e4:pcols fails unless every one of them is 'ok' (§6.5), so they are blocking like any other job
LB_MILP_PREFIXES = ("e3:milp:", "e4:eager:")
VERDICTS, OK_VERDICTS = m3.VERDICTS, m3.OK_VERDICTS
FIG4_CAPTION_MAX = 3 * 140                                   # plan §5: at most 3 lines of about 140 characters

# status labels copied from the spec (§3.1, §4.1, §6.1) and design/Sublet_design.md (§2.9, §5.2.4, Table 5.9), in
# the drivers' ASCII (C1-C3); never upgraded. Each "; "-separated part of a label that carries a status word is a
# verbatim copy, or "ID (text)" whose text opens the ID's parenthesis in those documents (tests/test_ms4_claims.py
# checks this); a part without a status word says what the check tests.
W_AB = m3.W_AB      # "Theorem W(a)(b) (PROVEN for the engine as implemented under C1-C3, audited); W(c) (CONJECTURE)"
M4 = "Proposition M4 (PROVEN)"
M6 = "Proposition M6 (PROVEN)"
C3_P7 = "C3-P7 (PROVEN, elementary)"
C3_T9 = "C3-T9 (PROVEN; numerically checked)"
C3_T11 = "C3-T11 (PROVEN; numerically checked)"
C3_L10 = "C3-L10 (PROVEN; numerically checked)"


# ---------------------------------------------------------------- the rows (the spec's tables)
@dataclass(frozen=True)
class Spec:
    """One check of §3.11-§7.9: id, experiment, section, kind ('reproduction', 'property' or 'informative'), the spec
    row's content, the design's status label of the claim it tests (None: no theory claim, then `label_note` says
    what it tests), the summary it reads, the reference (the spec's text and the file), the entry's fields shown as
    the regenerated value (paths as `_get`), the entry's fields that hold the reference values, the regenerated
    value's file (default: the summary's checks.<id>), whether the spec allows the verdict 'explained' (no MS4
    check does), further files whose meta.reduced true makes the row a bug, and the informative rows' remark (the
    spec's reading of the value)."""
    id: str
    exp: str
    section: str
    kind: str
    claim: str
    label: Optional[str]
    label_note: Optional[str] = None
    summary: str = ""
    reference: str = ""
    reference_file: str = ""
    fields: tuple = ()
    ref_fields: tuple = ()
    regenerated_file: Optional[str] = None
    explainable: bool = False
    also_reduced: tuple = ()
    remark: Optional[str] = None


def _rows_spec() -> tuple:
    guard = "code/sim/sublet/algos/guard.py (Theorem W, module docstring); design/Sublet_design.md §2.9"
    m4 = "design/Sublet_design.md §5.2.4 (Propositions M4, M6)"
    e7 = dict(exp="E7", section="§3.11", summary=E7_SUM)
    e3 = dict(exp="E3", section="§4.9", summary=E3_SUM)
    e5 = dict(exp="E5", section="§5.7", summary=E5_SUM)
    e4 = dict(exp="E4", section="§6.9", summary=E4_SUM)
    e8 = dict(exp="E8", section="§7.9", summary=E8_SUM)
    return (
        # §3.11 E7 (main's combined entries; parts main, stress, gap, allow)
        Spec("E7-1", kind="property", **e7,
             claim="every A8 run of E7 (all six grids) has a certificate with available true; in every run of "
                   "Theorem W's proven cases (W(a), W(b)) held is true; W(c) runs are counted and listed with their "
                   "t_a", label=W_AB,
             reference="held in every proven-case run; W(c) runs counted (Table III's caption)",
             reference_file=guard,
             fields=("part_status", "sum:parts.*.n_runs", "sum:parts.*.n_unavailable", "sum:parts.*.n_failures",
                     "sum:parts.*.n_w_c", "parts.*.certificates.held"),
             remark="W(c) runs (CONJECTURE) are counted, not bugs; their number goes to Table III's caption"),
        Spec("E7-2", kind="property", **e7,
             claim="every run, BL2's sub-runs included: invariant_failures empty and gpu_only_lease_slots 0",
             label=None, label_note="the engine's invariants",
             reference="no invariant failure, no GPU-only lease slot", reference_file="design/Sublet_design.md §5.2",
             fields=("part_status", "sum:parts.*.n_runs", "sum:parts.*.n_sub_runs",
                     "sum:parts.*.n_invariant_failures", "sum:parts.*.n_gpu_only")),
        Spec("E7-3", kind="property", **e7,
             claim="every gap rerun: ratio_validity('slow', ...) None; its alignment's LP record has status 0 "
                   "(optimal) and the instance and schedule hashes of the run; all runs of one alignment have one "
                   "schedule hash; every engine run in plan class P1 has ratio_LB >= 1 - 1e-6 (Proposition M4(b) "
                   "with Proposition M6); BL2's summed runs are exempt from the P1 test",
             label=f"{M4}; {M6}",
             reference="ratio_LB >= 1 - 1e-6 for P1 runs; LP status 0 with the run's instance and schedule hashes",
             reference_file=m4,
             fields=("parts.gap.n_runs", "parts.gap.lp_alignments", "#parts.gap.ratio_validity_not_none",
                     "parts.gap.n_runs_without_lp", "#parts.gap.lp_not_optimal", "#parts.gap.hash_mismatch",
                     "#parts.gap.alignments_with_several_schedules", "parts.gap.n_p1", "#parts.gap.p1_below",
                     "parts.gap.min_ratio_LB_p1", "parts.gap.bl2_exempt"),
             ref_fields=("parts.gap.tolerance",)),
        Spec("E7-4", kind="property", **e7,
             claim="accounting identity: total - overflow = own_capacity_usd(inst) for every run, and BL0a's "
                   "total-accounting cost = BL0a + own capacity (1e-9 relative)",
             label=None, label_note="both accountings (Q32, M2), a property of the build",
             reference="own_capacity_usd(inst) (drivers/provision.py), 1e-9 relative",
             reference_file="code/sim/sublet/drivers/provision.py (own_capacity_usd)",
             fields=("part_status", "sum:parts.*.n_runs", "max:parts.*.max_rel_diff", "sum:parts.*.n_failures"),
             ref_fields=("parts.main.tolerance",)),
        Spec("E7-5", kind="property", **e7,
             claim="BL0a: e6.bl0a_all(inst) equals BL0a's engine run on every gap-rerun instance (1e-9 relative); "
                   "BL0b is recorded in both accountings per alignment",
             label=None, label_note="the analytic BL0a against its engine run (M23)",
             reference="BL0a's engine run on the gap instance (1e-9 relative); BL0b in both accountings",
             reference_file="code/sim/sublet/experiments/e6.py (bl0a_all); drivers/provision.py (bl0b_usd)",
             fields=("part_status", "parts.gap.bl0a_by_alignment.*.rel_diff", "parts.gap.alignments_missing",
                     "#parts.gap.failures", "#parts.gap.runs_with_another_bl0a",
                     "parts.main.alignments_without_bl0b"),
             ref_fields=("parts.gap.tolerance",)),
        Spec("E7-6", kind="property", **e7,
             claim="the allowance rule (M36): every A8 run outside the allowance sweep records B0_rule '0.1*BL0a', "
                   "B0 = 0.1 x e6.bl0a_all of its own instance, resolved gamma 1 and kappa null; the sweep's runs "
                   "record their own rule",
             label=None, label_note="the allowance rule of M36 (§3.3), a parameter setting of A8",
             reference="B0_rule '0.1*BL0a' (ms4_common.B0_RULE), B0 = 0.1 x BL0a to 1e-12 relative, gamma 1, kappa "
                       "null; the sweep's own rules",
             reference_file="code/sim/sublet/experiments/ms4_common.py (B0_RULE, sublet_params, allowance_record)",
             fields=("part_status", "sum:parts.*.n_runs", "sum:parts.*.n_failures", "parts.*.rules_found"),
             ref_fields=("parts.main.tolerance",)),
        Spec("E7-7", kind="reproduction", **e7,
             claim="the allowance sweep's runs at B0 = 10% reproduce the main grid's Sublet runs at alignment 1 under "
                   "L-tr and the stress block's Sublet runs, seed by seed (totals equal to 1e-9 USD)",
             label=None, label_note="the identity of the sweep's 10% cells with the main grid and the stress block",
             reference="the main grid's (L-tr, alignment 1) and the stress block's Sublet runs, seed by seed",
             reference_file=f"{OUT}/e7/main/runs/, {OUT}/e7/stress/runs/ (run files, not versioned)",
             fields=("parts.allow.b0", "parts.allow.n_pairs", "#parts.allow.failures", "#parts.allow.missing",
                     "max:parts.allow.pairs[*].abs_diff"),
             ref_fields=("parts.allow.tolerance_usd",)),
        Spec("E7-8", kind="informative", **e7,
             claim="W0 per policy (stress block), against Q44's criterion S (W0 <= 1.05, note §5.6)",
             label=None, label_note="Q44's criterion S (design/q44_practical_sublet.md §5.6), a design criterion",
             reference="criterion S: W0 <= 1.05", reference_file="design/q44_practical_sublet.md §5.5, §5.6",
             fields=("parts.stress.W0.*.value", "parts.stress.W0.*.mode", "parts.stress.meets_criterion_S",
                     "parts.stress.misses_criterion_S"),
             remark="W0 is reported against criterion S as measured; BL0a has W0 = 1 by definition (§3.9)"),
        Spec("E7-9", kind="informative", **e7,
             claim="saving over BL0a against the cross-region links n (Fig. 4(b)), with one BL0a at every n",
             label=None, label_note="pooling over the routing graphs of M1 (§3.7(c)), a measurement",
             reference="one BL0a at every n (BL0a does not depend on routing)", reference_file="§3.7(c)",
             fields=("parts.main.saving_pct_median", "parts.main.one_bl0a_per_alignment",
                     "parts.main.bl0a_max_rel_diff_over_mu_and_n", "parts.main.cross_region_arcs_equal_links"),
             remark="reported as measured; only the cross-region routing arcs differ between the points (§3.7(c))"),
        Spec("E7-10", kind="informative", **e7,
             claim="Sublet's slow-grid ratio to the LB against BL5's (decision B1; design §2.7, the slow-grid item "
                   "of the must-not-claim list)",
             label=None, label_note="a measured comparison (decision B1); the column's bound is that of E7-3",
             reference="BL5's ratio to the merged LP bound", reference_file=f"{OUT}/e7/gap/lb/lp_c<C>.json",
             fields=("parts.gap.sublet_ratio_LB_median", "parts.gap.bl5_ratio_LB_median", "parts.gap.sublet_over_bl5",
                     "parts.gap.ratio_LB_median_range", "parts.gap.label"),
             remark="reported as measured, labeled an upper bound on the ratio to OPT(sigma, omega) against a merged "
                    "bound (§3.8, M39); no trace-lender advantage of Sublet on the slow grid is claimed (§3.1)"),
        Spec("E7-11", kind="informative", **e7,
             claim="abort shares and first-abort slots of the A8 rows in every grid; under the sweep's theory "
                   "default, the share of runs that abort at slot 1 or earlier",
             label=None, label_note="the guard's aborts under M36's allowance, a measurement",
             reference="Table III's abort-share column (M24)", reference_file=TABLE3,
             fields=("parts.main.by_grid.*.abort_share", "parts.stress.by_grid.*.abort_share",
                     "parts.gap.by_grid.*.abort_share", "parts.allow.theory_default"),
             remark="the stress block's and the sweep's abort shares go to the supplement (M24)"),
        Spec("E7-12", kind="informative", **e7,
             claim="policies whose median cost exceeds BL0a (A6, M38)",
             label=None, label_note="a measurement (decision B1, M38)",
             reference="BL0a (week cost / BL0a = 1)", reference_file=E7_SUM + " meta.bl0a_usd",
             fields=("parts.main.above_bl0a_headline", "parts.main.median_overflow_over_bl0a_headline"),
             remark="reported as measured under decision B1 (M38); the must-not-claim list of §3.1 applies"),
        # §4.9 E3
        Spec("E3-1", kind="property", **e3,
             claim="every bracket of siloed/shared OPT has lo <= b (1 + 1e-9) (the siloed optimum is at most b times "
                   "the shared one, the copy argument of design §5.5 E3)",
             label=None, label_note="the copy argument of design §5.5 E3 (each borrower may copy the shared plan); "
                                    "C3-P7 gives the factor's attainment, not this bound",
             reference="b (1 + 1e-9)", reference_file="design/Sublet_design.md §5.5 E3",
             fields=("n_brackets", "n_above_b", "#refused", "max_lo_over_b")),
        Spec("E3-2", kind="property", **e3,
             claim="at b = 1 the siloed sub-instance has the shared instance's instance_hash, and each siloed run's "
                   "total equals its shared counterpart's (Sublet-siloed and Sublet, A6-siloed and A6)",
             label=None, label_note="the b = 1 identity of the siloed runner",
             reference="equal hashes; totals to 1e-9 USD", reference_file=E3_SUM + " (the shared runs at b = 1)",
             fields=("n_cells", "#hash_differs", "n_pairs", "#failures", "max_abs_diff")),
        Spec("E3-3", kind="property", **e3,
             claim="every siloed run's components and total equal the sums of its sub-runs', recomputed from the "
                   "stored run rows, and run_siloed's summed per-slot series sum to its summed components",
             label=None, label_note="the siloed runner's sums (drivers/siloed.py)",
             reference="the sums of the sub-runs (1e-9 USD)", reference_file=f"{OUT}/e3/runs/cells/ (run rows)",
             fields=("n_runs", "#failures", "max_abs_diff", "max_abs_diff_alg", "max_abs_diff_per_slot",
                     "n_per_slot_missing")),
        Spec("E3-4", kind="property", **e3,
             claim="every run and sub-run: invariant_failures empty, gpu_only_lease_slots 0, ratio_validity None and "
                   "the cell's realized schedule; every shared run of plan class P1 has ratio_LB >= 1 - 1e-6",
             label=M4, reference="no failure; ratio_LB >= 1 - 1e-6 for P1 runs", reference_file=m4,
             fields=("n_runs", "n_runs_and_sub_runs", "#invariant_failures", "#gpu_only_lease_slots",
                     "#ratio_validity_not_none", "#schedule_mismatch", "n_p1", "#p1_below", "min_ratio_LB_p1")),
        Spec("E3-5", kind="property", **e3,
             claim="every Sublet run and Sublet-siloed sub-run: certificate held in Theorem W's proven cases; W(c) "
                   "runs counted and reported", label=W_AB,
             reference="held in every proven-case run", reference_file=guard,
             fields=("n", "held", "n_failures", "n_w_c", "by_case")),
        Spec("E3-6", kind="informative", **e3,
             claim="the share of the factor that survives, (siloed/shared OPT)/b per (b, u), and the count of "
                   "borrowers without overflow per (b, day) (plan §7)",
             label=f"{C3_P7}; trace instances leave the core, so the policies' ratios are diagnostics",
             reference="the factor b, attained on C3-P7's instance", reference_file="code/theory_checks/c3/out/"
                                                                                   "c4_lower.txt (d)",
             fields=("factor_share.*.8.point", "factor_share.*.8.lo", "factor_share.*.8.hi",
                     "#borrowers_without_overflow"),
             remark="if the gain is small it is reported against the proven factor anyway (plan §7)"),
        Spec("E3-7", kind="informative", **e3,
             claim="the gate record (§4.4): its config hash equals the grid's, its MILPs ran under the grid's "
                   "milp_limit_s(), and its bracket, borrower shares and allowance needs (shared and per sub-run) "
                   "are those reported",
             label=None, label_note="the gate of §1.2 item 6 (M7), the provenance of the grid",
             reference="the grid's config hash (e3.grid_config_hash()) and MILP limit (ms3_common.milp_limit_s())",
             reference_file=E3_GATE,
             fields=("config_hash", "config_hash_equal", "gate_milp_limits_s", "milp_limit_equal", "bracket",
                     "allowance.shared.need_over_bl0a", "allowance.shared.margin_usd", "allowance.shared.t_a_at_B0"),
             ref_fields=("grid_config_hash", "milp_limit_s"),
             regenerated_file=f"{E3_SUM} checks.E3-7 (from {E3_GATE})", also_reduced=(E3_GATE,),
             remark="informative unless the gate's config hash or MILP limit is not the grid's (then fail); the "
                    "answer to M7 on these numbers is recorded in §12 (§4.4)"),
        # §5.7 E5
        Spec("E5-1", kind="property", **e5,
             claim="every run: invariant_failures empty, gpu_only_lease_slots 0; no run of an ok job lost to an "
                   "error (meta.run_errors)", label=None, label_note="the engine's invariants and the job records",
             reference="no failure, no lost run", reference_file=E5_SUM + " meta.run_errors",
             fields=("n_runs", "n_runs_expected", "n_runs_lost", "n_invariant_failures", "n_gpu_only_lease_slots")),
        Spec("E5-2", kind="property", **e5,
             claim="long menu: A6-rule and A6-always2 have n_exp_total 0 and buys 0 in every run, provided "
                   "max_l lam_s[j, l] <= 3,600 s for every LLM j of the instance",
             label=None, label_note="the exposure definition of the redundancy rule (design §3.2.6), a heuristic",
             reference="n_exp_total 0 and buys 0 (contracts with H_k >= lambda_min never create exposure)",
             reference_file="design/Sublet_design.md §3.2.6; code/sim/sublet/algos/redundancy.py",
             fields=("n_runs", "n_checked", "n_unchecked", "lam_s_max_by_llm", "n_failures"),
             ref_fields=("limit_s",)),
        Spec("E5-3", kind="property", **e5,
             claim="A6-always2: every run with n_exp_total > 0 has buys + no_site > 0; the entry also gives the "
                   "placed share buys / (buys + no_site)",
             label=None, label_note="the redundancy rule's 'always2' mode (design §3.2.6), a heuristic",
             reference="buys + no_site > 0 wherever a group has an exposed replica",
             reference_file="design/Sublet_design.md §3.2.6",
             fields=("n_runs", "n_runs_exposed", "n_failures", "buys_total", "no_site_total", "placed_share")),
        Spec("E5-4", kind="informative", **e5,
             claim="per (level, menu): the BL3 variants whose median cost over BL0a and median fallback share after "
                   "reclaims are both below those of every A6 mode (Pareto gains), the long menu reported "
                   "separately, with the number of (level, menu) whose three A6 modes gave the same run",
             label=None, label_note="the design's reading of E5 (design §5.5 E5), a measurement",
             reference="every A6 mode (cost over BL0a, fallback share after reclaims)", reference_file=E5_SUM +
                                                                                                    " pareto",
             fields=("n_cells_with_gain", "n_cells_undecided", "n_cells_a6_identical", "long_menu", "short_menu"),
             remark="clear Pareto gains of BL3 over A6 in the long-notice menu would argue against the rule "
                    "(design §5.5 E5)"),
        Spec("E5-5", kind="property", **e5,
             claim="every Sublet run: certificate held in Theorem W's proven cases; W(c) runs counted; no Sublet run "
                   "lost to an error", label=W_AB,
             reference="held in every proven-case run; no lost run", reference_file=guard,
             fields=("runs", "held", "n_failures", "n_w_c", "n_runs_lost", "by_case", "B0_rules")),
        Spec("E5-6", kind="informative", **e5,
             claim="the share of A6-rule runs that bought a spare, per (level, menu) over every mu of the point and "
                   "per mu, against the rule's prediction (spares only for pools above about 32 exposed replicas at "
                   "alpha = 0.40)",
             label=None, label_note="the redundancy rule's prediction (design §5.5 E5), a measurement",
             reference="spares only for pools above the spare threshold",
             reference_file="code/analysis/out/a5b_exposure_thresholds.json (spare_threshold)",
             fields=("threshold", "prediction", "by_level_menu.*.*.share_with_buys"),
             remark="reported against the rule's prediction, as measured"),
        # §6.9 E4
        Spec("E4-1", kind="reproduction", **e4,
             claim="job e4:repro reruns repro_c5_la and compares with MS2 spec §17.3 R7's values of c3/out/c5_la.txt "
                   "(a) and (b): E4's bug test of C3-T9, C3-T11 and the combiner",
             label=f"{C3_T9}; {C3_T11}",
             reference="R7: c5_la.txt (a), (b) and c5_la_nearest.txt, exact to their printed digits",
             reference_file="code/theory_checks/c3/out/c5_la.txt, c5_la_nearest.txt",
             fields=("files.*.lines_equal", "json.*.n_mismatch", "json.*.max_rel_diff", "quick"),
             regenerated_file=f"{OUT}/e4/repro_check.json; {E4_SUM} checks.E4-1"),
        Spec("E4-2", kind="property", **e4,
             claim="C3-L10 on the core: every row of e4/repro/c5_la_repro.json has eta_chk true; on the trace ratio "
                   "days the slack and the bracket of P-hat's MILP over OPT_eager (refuted, confirmed), reported",
             label=C3_L10, reference="eta_chk true in every core row; trace and bracket informative",
             reference_file=f"{OUT}/e4/repro/c5_la_repro.json",
             fields=("core.n_rows", "core.n_eta_chk_false", "trace.n_runs", "trace.n_negative", "trace.min_slack",
                     "bracket.n", "bracket.n_refuted", "bracket.n_confirmed"),
             remark="a bug only on the core rows; the trace slack and the bracket are informative (§6.9)"),
        Spec("E4-3", kind="property", **e4,
             claim="every run: invariant_failures empty, gpu_only_lease_slots 0; every ratio run: ratio_validity None",
             label=None, label_note="the engine's invariants and the ratios' grid (design §5.2.4)",
             reference="no failure; ratio_validity None", reference_file="design/Sublet_design.md §5.2.4",
             fields=("n_runs", "n_ratio_runs", "#invariant_failures", "#gpu_only_lease_slots",
                     "#ratio_validity_not_none")),
        Spec("E4-4", kind="informative", **e4,
             claim="the method of each P-hat day (milp, lp_round, none) and the MILPs' statuses and gaps",
             label=None, label_note="the P-hat MILPs (§6.5), a measurement",
             reference="the MILP rule of M9 (time limit milp_limit_s())", reference_file=f"{OUT}/e4/lb/phat/",
             fields=("n_days", "n_ok", "methods", "milp_status", "n_at_limit", "max_gap", "#lp_round_days",
                     "#not_ok")),
        Spec("E4-5", kind="informative", **e4,
             claim="every A5 and A6-pred run: real cost over min{C_FP, C_R}, against 5.83; every instance's core "
                   "export recorded with its exact and notes, or 'not exportable'",
             label=f"{C3_T11}; trace instances are not exact core exports, so the ratio is a diagnostic",
             reference="5.83 (C3-T11, for the accounted cost on the core with eager accounting)",
             reference_file="design/theory/c3_c4_c5_general.md (C3-T11)",
             fields=("n_runs", "n_above_bound", "#bugs_on_exact_exports", "core_export", "max_real_over_min"),
             ref_fields=("bound",),
             remark="a bug only on an exact core export, which E4's trace instances are not (§6.9)"),
        Spec("E4-6", kind="informative", **e4,
             claim="week cost of A5 and A6-pred over A6 without predictions, per (panel, prediction) (M37)",
             label=None, label_note="a measurement (M37)",
             reference="A6 without predictions of the same (panel, alignment, mu, seed)",
             reference_file=E4_SUM + " week.<panel>.<mu>.none.A6",
             fields=("n_entries", "min:entries[*].median", "max:entries[*].median"),
             remark="reported as measured; no gain from predictions is claimed (M37)"),
        # §7.9 E8
        Spec("E8-1", kind="property", **e8,
             claim="conservation in every replay: every copy served by own capacity, a leased replica or fallback "
                   "exactly once, and the served and fallback weighted tokens sum to the stream's total",
             label=None, label_note="the replay's conservation (model validity, design Table 5.9: no claim)",
             reference="counts exact, tokens to 1e-9 relative", reference_file=f"{OUT}/e8/runs/pairs/ (replay "
                                                                               "records)",
             fields=("n", "n_expected", "n_fail", "max_tokens_rel_diff")),
        Spec("E8-2", kind="property", **e8,
             claim="fluid mode: the replay fed the instance's per-fast-slot demand as rates, with capacity kappa_j "
                   "W(f) and cheapest-first routing, reproduces the engine's routing and fallback components",
             label=None, label_note="the replay's fluid mode against the engine (model validity)",
             reference="the engine's routing and fallback components (1e-6 relative)",
             reference_file=f"{OUT}/e8/runs/fluid/ (the fluid runs)",
             fields=("n", "n_expected", "n_fail", "max_rel_diff_routing", "max_rel_diff_fallback",
                     "stranding_max_rel_diff"),
             ref_fields=("tol", "floor_usd")),
        Spec("E8-3", kind="property", **e8,
             claim="every fluid run: invariant_failures empty, gpu_only_lease_slots 0",
             label=None, label_note="the engine's invariants", reference="no failure",
             reference_file=f"{OUT}/e8/runs/fluid/",
             fields=("n_runs", "n_expected", "n_fail", "n_invariant_failures", "n_gpu_only_lease_slots")),
        Spec("E8-4", kind="informative", **e8,
             claim="the error E per (tier, window, mu)",
             label=None, label_note="model validity (design Table 5.9: no claim)",
             reference="E = (C_replay - C_fluid) / C_replay", reference_file="§7.6",
             fields=("n_cells", "n_cells_with_value", "median_range", "at_mu_1"),
             remark="model validity, reported as measured (design §5.5 E8)"),
        Spec("E8-5", kind="informative", **e8,
             claim="the Mooncake hour's error with and without prefix hits",
             label=None, label_note="model validity (design Table 5.9: no claim)",
             reference="the global infinite-cache hit ratio (an upper bound on any replica-level ratio)",
             reference_file=f"{OUT}/e8/summary.json meta.mooncake_trace",
             fields=("error", "hit_ratio", "global_hit_ratio", "n"),
             remark="a one-hour sensitivity, reported as measured (§7.7)"),
    )


# ---------------------------------------------------------------- values, verdicts and rows
_MISSING = object()
_OPS = (("#", "len"), ("min:", "min"), ("max:", "max"), ("sum:", "sum"))


def _num(x) -> bool:
    return m3._num(x)


def _get(obj: Any, path: str) -> Any:
    """A field of a check entry: 'a.b' (nested keys), 'a[*].b' (the list of b over the list a), 'a.*.b' (the mapping
    {key: b} over the mapping a), '#path' (its length), 'min:path', 'max:path' and 'sum:path' (of the finite numbers
    of a list or of a mapping's values). _MISSING where a key is absent; a key may not contain '.'."""
    for op, _ in _OPS:
        if path.startswith(op):
            v = _get(obj, path[len(op):])
            if v is _MISSING or v is None:
                return v
            if op == "#":
                return len(v) if isinstance(v, (list, dict)) else _MISSING
            vals = list(v.values()) if isinstance(v, dict) else v if isinstance(v, list) else [v]
            nums = [x for x in vals if _num(x)]
            if not nums:
                return None
            return min(nums) if op == "min:" else max(nums) if op == "max:" else sum(nums)
    cur = obj
    parts = path.split(".")
    for i, p in enumerate(parts):
        rest = ".".join(parts[i + 1:])
        if p == "*":
            if not isinstance(cur, dict):
                return _MISSING
            return {k: (_none(_get(v, rest)) if rest else v) for k, v in cur.items()}
        if p.endswith("[*]"):
            lst = cur.get(p[:-3], _MISSING) if isinstance(cur, dict) else _MISSING
            if not isinstance(lst, list):
                return _MISSING
            return [_none(_get(x, rest)) if rest else x for x in lst]
        if not isinstance(cur, dict) or p not in cur:
            return _MISSING
        cur = cur[p]
    return cur


def _none(v):
    return None if v is _MISSING else v


def _field_name(path: str) -> str:
    for op, name in _OPS:
        if path.startswith(op):
            return f"{name}({path[len(op):]})"
    return path


def _values(entry: dict, fields) -> dict:
    return {_field_name(f): _none(_get(entry, f)) for f in fields}


def verdict(kind: str, status: Optional[str], explainable: bool = False) -> tuple[str, Optional[str]]:
    """(verdict, note) of a check entry's status (§1.4 item 2, §2.6): pass gives reproduced or holds by the row's
    kind (informative rows stay informative), fail gives bug, explained is accepted only where the spec allows it
    (no MS4 check does), informative only for the rows the spec marks informative, missing and pending stay; any
    other status is a bug."""
    if status == "pass":
        if kind == "informative":
            return "informative", "the summary says pass; the spec marks the row informative"
        return ("reproduced" if kind == "reproduction" else "holds"), None
    if status == "fail":
        return "bug", None
    if status == "explained":
        return ("explained", None) if explainable else (
            "bug", "status 'explained' where the spec allows no explanation (no check of §3.11, §4.9, §5.7, §6.9 "
                   "or §7.9 allows one)")
    if status == "informative":
        return ("informative", None) if kind == "informative" else \
            ("bug", "status 'informative' where the spec sets a pass condition")
    if status in ("missing", "pending"):
        return status, None
    if status == "bug_input":
        return "bug", None
    return "bug", f"status {status!r} outside the vocabulary of §2.6"


def _reduced(S: Any) -> bool:
    """Whether a summary or record comes from a reduced (smoke) run: meta.reduced true (the drivers' --reduced)."""
    return m3._reduced(S)


def _e7_parts(spec: Spec, entry: dict, inp) -> tuple[list, list]:
    """E7 rows: (the reduced part summaries, the stale parts) among the parts whose entries main's combined entry
    used (an entry copied from the part summary carries 'part'); a part summary whose own checks.<id> has another
    status than the one main copied makes main's entry stale (the part was rebuilt after main's summary)."""
    reduced, stale = [], []
    for p, pe in m3._d(entry.get("parts")).items():
        if p == "main" or p not in E7_PART_SUM or not isinstance(pe, dict) or pe.get("part") != p:
            continue
        P, _ = inp.load(E7_PART_SUM[p])
        if P is None:
            continue
        if _reduced(P):
            reduced.append(E7_PART_SUM[p])
        cur = m3._d(m3._d(P.get("checks")).get(spec.id)).get("status")
        if cur != pe.get("status"):
            stale.append(f"{p} (main copied {pe.get('status')!r}, {E7_PART_SUM[p]} now says {cur!r})")
    return reduced, stale


def _entry_note(entry: dict, status: Optional[str]) -> Optional[str]:
    """Why a summary's check is missing, pending or failed, from its own fields (why, where, note, the notes of
    main's combined E7 entry per part, and for pending the outstanding lists)."""
    bits = [str(entry[k]) for k in ("why", "where", "note", "pass_note") if entry.get(k)]
    for p, pe in m3._d(entry.get("parts")).items():
        pe = m3._d(pe)
        if pe.get("status") in ("missing", "pending", "fail"):
            why = "; ".join(str(pe[k]) for k in ("why", "note", "_note") if pe.get(k))
            bits.append(f"part {p}: {pe.get('status')}" + (f" ({why})" if why else ""))
    if status == "pending":
        for k in ("rerun_pending", "pending", "unresolved"):
            if isinstance(entry.get(k), (list, dict)) and entry[k]:
                bits.append(f"{k}: {len(entry[k])}")
    return "; ".join(bits) or None


def build_row(spec: Spec, inp) -> dict:
    """One row of the report for `spec` (module docstring, rows[])."""
    src = spec.summary
    S, prob = inp.load(src)
    reduced_src: list = []
    stale: list = []
    if S is None:
        entry = m3._absent(src, prob)
    elif "checks" in S and not isinstance(S["checks"], dict):
        entry = {"status": "bug_input", "_note": f"{src}: checks is not an object"}
    else:
        entry = m3._d(S.get("checks")).get(spec.id)
        if not isinstance(entry, dict):
            entry = {"status": "missing", "_note": f"no entry checks.{spec.id} in {src}"}
        if _reduced(S):
            reduced_src.append(src)
        for rel in spec.also_reduced:
            R, _ = inp.load(rel)
            if R is not None and _reduced(R):
                reduced_src.append(rel)
        if spec.exp == "E7":
            r, stale = _e7_parts(spec, entry, inp)
            reduced_src += r
    status = entry.get("status")
    reg_file = spec.regenerated_file or f"{src} checks.{spec.id}"
    parts = m3._d(entry.get("parts"))
    if spec.exp == "E7" and parts:
        reg_file += f" (combined over the parts {', '.join(parts)})"
    v, vnote = verdict(spec.kind, status, spec.explainable)
    expl = None
    why_not = None
    if v == "explained":
        expl = str(entry["explanation"]) if entry.get("explanation") else None
        why_not = None if expl else "the summary gives no explanation"
    notes = [x for x in (entry.get("_note"), vnote, why_not) if x]
    if status in ("missing", "pending", "fail"):
        n = _entry_note(entry, status)
        if n:
            notes.append(n)
    if status == "fail" and not notes:
        notes.append(f"the summary's status is 'fail' (see {reg_file})")
    if status in ("missing", "pending") and not notes:
        notes.append("the summary gives no reason")
    if stale:
        v, expl = "bug", None
        notes.insert(0, "main's combined entry is stale: " + "; ".join(stale))
    if reduced_src:
        v, expl = "bug", None
        notes.insert(0, f"{', '.join(dict.fromkeys(reduced_src))} from a reduced run (meta.reduced true; smoke), "
                        "never a result")
    if v == "informative" and spec.remark:
        notes.append(spec.remark)
    row = {"id": spec.id, "experiment": spec.exp, "section": spec.section, "kind": spec.kind,
           "claim": {"spec": spec.claim, "summary": entry.get("claim")},
           "status_label": spec.label, "status_label_note": spec.label_note if spec.label is None else None,
           "reference": {"value": spec.reference, "values": _values(entry, spec.ref_fields),
                         "file": spec.reference_file},
           "regenerated": {"value": _values(entry, spec.fields), "file": reg_file},
           "summary_status": None if status == "bug_input" else status, "verdict": v, "explanation": expl,
           "note": "; ".join(notes) or None}
    if spec.exp == "E7":
        row["parts"] = {p: m3._d(pe).get("status") for p, pe in parts.items()}
    return row


def _row_or_bug(spec: Spec, inp) -> dict:
    """build_row, or, where an input has a shape the drivers never write (§2.6) and reading it raises, a 'bug' row
    that names the error, so that the report is still written."""
    try:
        return build_row(spec, inp)
    except Exception as err:
        row = {"id": spec.id, "experiment": spec.exp, "section": spec.section, "kind": spec.kind,
               "claim": {"spec": spec.claim, "summary": None}, "status_label": spec.label,
               "status_label_note": spec.label_note if spec.label is None else None,
               "reference": {"value": spec.reference, "values": {}, "file": spec.reference_file},
               "regenerated": {"value": {}, "file": spec.regenerated_file or spec.summary},
               "summary_status": None, "verdict": "bug", "explanation": None,
               "note": f"the row's input has a shape the drivers do not write ({type(err).__name__}: {err})"[:300]}
        if spec.exp == "E7":
            row["parts"] = {}
        return row


def criterion(rows: list) -> dict:
    """§1.4 item 2 (ms3_claims.criterion): holds iff no row is 'bug' and every row other than reproduced, holds and
    informative is 'explained' with its text."""
    return m3.criterion(rows)


# ---------------------------------------------------------------- floats, copy checks
def floats_block(inp) -> dict:
    """§1.4 item 5: Table III's measured height next to its 0.125-page budget (floats_heights_ms4.json, C21)."""
    F, prob = inp.load(FLOATS)
    out = {"file": FLOATS, "present": F is not None, "rows": []}
    if F is None:
        out["note"] = (f"{FLOATS} {prob} (paper/layout_check/pageplan/floats_heights.py --ms4 writes it from "
                       "paper/floats/table3_e7.tex)")
        return out
    for k, v in m3._d(F.get("floats")).items():
        v = m3._d(v)
        out["rows"].append({"float": FLOAT_NAMES.get(k, k), "name": k, **{f: v.get(f) for f in (
            "measured_pages", "budget_pages", "within_budget", "difference_pages", "source")}})
    names = [r["name"] for r in out["rows"]]
    over = [r for r in out["rows"] if r["within_budget"] is False]
    if "table3_e7" not in names:
        out["note"] = f"{FLOATS} records no table3_e7 (Table III); floats found: {names or 'none'}"
    elif over:
        out["note"] = ("; ".join(f"{r['float']} exceeds its budget by {m3._fmt(r['difference_pages'], 4)} page"
                               for r in over)
                       + " (M27: §9's two steps are done in the build, the caption holds only the scope, the "
                         "allowance and the certificate count, and merging the USD and saving columns saves no line; "
                         "§1.5 item 9: all six data columns stay, "
                         "each carrying a different claim, and the excess comes out of the page reserve of plan §3.2)")
    else:
        out["note"] = "Table III within its budget"
    return out


def copy_block(inp) -> dict:
    """The copy records out/ms3_copy_<exp>.json of e3, e4, e5, e7 and e8 (§1.2, ms3_common.check_copy, C20 for
    E7's parts): pass, the clone's commit, the failed checks, the parts and the job records by status; and whether
    the present records name one clone commit (§1.2: one clone holds every MS4 run)."""
    recs = {}
    for exp in COPY_EXPS:
        rel = f"{OUT}/{mc.COPY_RECORD.format(exp=exp)}"
        rec, prob = inp.load(rel)
        e = {"file": rel, "present": rec is not None, "pass": None, "exp_matches": None, "commit": None, "time": None,
             "failed": [], "parts": None, "records_by_status": None}
        if rec is not None:
            e.update(**{"pass": rec.get("pass") is True, "exp_matches": rec.get("exp") == exp, "time": rec.get("time"),
                        "commit": rec.get("clone_commit"),
                        "failed": [k for k, v in m3._d(rec.get("checks")).items() if not v],
                        "parts": rec.get("parts"), "records_by_status": rec.get("records_by_status")})
        elif prob != "missing":
            e["note"] = prob
        recs[exp] = e
    commits = sorted({e["commit"] for e in recs.values() if e["present"] and isinstance(e["commit"], str)})
    present = [k for k, e in recs.items() if e["present"]]
    one = None if not present else (len(commits) == 1 and all(isinstance(recs[k]["commit"], str) for k in present))
    if not present:
        note = "no copy record (ms3_common --check-copy EXP CLONE writes them after the runs, §1.2)"
    else:
        bad = [k for k in present if not recs[k]["pass"] or not recs[k]["exp_matches"]]
        absent = [k for k in COPY_EXPS if not recs[k]["present"]]
        note = (f"{len(present)} of {len(COPY_EXPS)} records present"
                + (f" (none for {', '.join(absent)})" if absent else "")
                + (f"; failed: {', '.join(bad)}" if bad else "; every present record passes")
                + ("; one clone commit" if one else f"; clone commits {commits or 'unknown'}"))
    return {"records": recs, "commits": commits, "one_commit": one, "note": note}


# ---------------------------------------------------------------- the job records (§2.4)
def jobs_block(inp) -> dict:
    """Every listed job of each MS4 experiment folder (manifest.json `jobs`, plus the records '<exp>:manifest' and
    '<exp>:summary'; E7's four parts each with their own) against its record jobs/<id>.json (§2.4: only 'ok' counts as
    done): the jobs by status ('no record' where the record is absent), the jobs without an 'ok' record outside Q39's
    rule ('blocking'), the MILP jobs whose output is a lower bound (LB_MILP_PREFIXES) and whose LB falls back to the LP
    under that rule (status wall_limit or oom_at_3G, §2.5; an E4 P-hat day job so stopped is blocking), and the lengths
    of the summary's own lists (meta.jobs_missing, meta.ignored_outputs, meta.outputs_missing). test_ms4_out.py fails on
    a blocking job."""
    rows = {}
    for folder in JOB_FOLDERS:
        exp = folder.split("/")[0]
        man_rel, sum_rel = f"{OUT}/{folder}/manifest.json", f"{OUT}/{folder}/summary.json"
        M, prob = inp.load(man_rel)
        e = {"manifest": man_rel, "present": M is not None, "n_listed": None, "by_status": {}, "n_blocking": None,
             "blocking": [], "n_milp_lp_fallback": None, "milp_lp_fallback": [], "n_unlisted_records": None,
             "n_unreadable_records": None, "summary_jobs_missing": None, "summary_ignored_outputs": None,
             "summary_outputs_missing": None}
        if M is None:
            e["note"] = f"{man_rel} {prob}"
            rows[folder] = e
            continue
        jobs = M.get("jobs") if isinstance(M.get("jobs"), list) else []
        listed = [(m3._d(j).get("id"), m3._d(j).get("kind")) for j in jobs]
        listed += [(mc.job_id(exp, "manifest"), "pool"), (mc.job_id(exp, "summary"), "pool")]
        recs, bad = m3._job_statuses(inp.root / OUT / folder)
        by_status: dict = {}
        blocking, fallback = [], []
        for jid, kind in listed:
            st = recs.get(jid, "no record") if isinstance(jid, str) else "no job id"
            by_status[st] = by_status.get(st, 0) + 1
            if st == "ok":
                continue
            item = {"job": jid, "kind": kind, "status": st}
            lb_job = kind == "milp" and isinstance(jid, str) and jid.startswith(LB_MILP_PREFIXES)
            (fallback if lb_job and st in m3.MILP_LP_FALLBACK else blocking).append(item)
        ids = {j for j, _ in listed}
        S, _ = inp.load(sum_rel)
        meta = m3._d(m3._d(S).get("meta"))

        def _n(key):
            return len(meta[key]) if isinstance(meta.get(key), list) else None

        e.update(n_listed=len(listed) - 2, by_status=dict(sorted(by_status.items())), n_blocking=len(blocking),
                 blocking=blocking[:m3.JOBS_LIST_MAX], n_milp_lp_fallback=len(fallback),
                 milp_lp_fallback=fallback[:m3.JOBS_LIST_MAX], n_unlisted_records=sum(1 for j in recs if j not in ids),
                 n_unreadable_records=bad, summary_jobs_missing=_n("jobs_missing"),
                 summary_ignored_outputs=_n("ignored_outputs"), summary_outputs_missing=_n("outputs_missing"))
        rows[folder] = e
    n_block = sum(r["n_blocking"] or 0 for r in rows.values())
    absent = [k for k, r in rows.items() if not r["present"]]
    note = (f"{n_block} listed job(s) without an 'ok' record outside Q39's MILP rule" if n_block else
            "every listed job has an 'ok' record, or is a MILP job whose LB is the LP under Q39's rule")
    if len(absent) == len(rows):
        note = f"no job list (manifest.json) for {', '.join(absent)}"
    elif absent:
        note += f"; no job list for {', '.join(absent)}"
    return {"rows": rows, "n_blocking": n_block, "note": note}


# ---------------------------------------------------------------- figures (§1.4 item 1)
# the MS4 figure scripts (relative to code/sim) with their names (style.save's): Fig. 4 (§8.1), then the eight
# supplementary scripts of §8.2 in path order (MS4 dropped sf_e3_u with M41); the names are those of
# style.FIGURES['fig4'] and style.SUPP_POLICIES_MS4 (tests/test_ms4_claims.py checks this)
MS4_FIGURE_SCRIPTS = (
    ("fig4", "figs/fig4_e7_e3.py"),
    ("sf_e3_mu", "figs/supp/sf_e3_mu.py"), ("sf_e3_util", "figs/supp/sf_e3_util.py"), ("sf_e4", "figs/supp/sf_e4.py"),
    ("sf_e5", "figs/supp/sf_e5.py"), ("sf_e7_allow", "figs/supp/sf_e7_allow.py"),
    ("sf_e7_mix", "figs/supp/sf_e7_mix.py"), ("sf_e7_mu", "figs/supp/sf_e7_mu.py"), ("sf_e8", "figs/supp/sf_e8.py"),
)


def figure_scripts() -> list[tuple[str, str, str]]:
    """(figure name, module, script path relative to code/sim) of the nine MS4 figure scripts MS4_FIGURE_SCRIPTS, Fig.
    4 first, the supplementary scripts in path order. The names are fixed by the spec (§8.1, §8.2), so a script that
    does not exist yet is still listed (figures_block reports it as an error)."""
    return [(name, rel[:-len(".py")].replace("/", "."), rel) for name, rel in MS4_FIGURE_SCRIPTS]


def _script_name(path: Path) -> Optional[str]:
    m = m3._NAME_RE.search(path.read_text(encoding="utf-8"))
    return m.group(1) if m else None


def figures_block(root: Path, extracts: Path, only=None, scripts=None) -> dict:
    """Rerun every MS4 figure script (or those named in `only`; `scripts` replaces figure_scripts() in tests) with
    --from-extract <extracts>/<name>.json in this process, all outputs in a temporary folder that is removed
    afterwards, and list each figure's small_glyphs from the report of figs.common.cli (module docstring)."""
    scripts = list(scripts) if scripts is not None else figure_scripts()
    if only:
        unknown = sorted(set(only) - {n for n, _, _ in scripts})
        if unknown:
            raise ValueError(f"no figure script named {unknown} (known: {[n for n, _, _ in scripts]})")
        scripts = [s for s in scripts if s[0] in set(only)]
    rows = []
    tmp = Path(tempfile.mkdtemp(prefix="ms4_claims_figs_"))
    keys = ENV_FIG_DIRS + (ENV_IN_ROOT,)
    saved = {k: os.environ.get(k) for k in keys}
    try:
        for k, sub in zip(ENV_FIG_DIRS, ("pdf", "out", "tables")):
            os.environ[k] = str(tmp / sub)
        os.environ[ENV_IN_ROOT] = str(root)
        m3._figs_import("figs.style")           # the figure style (and its matplotlib setup) before pyplot
        import matplotlib.pyplot as plt
        for name, module, script in scripts:
            ext = Path(extracts) / f"{name}.json"
            r = {"figure": name, "script": script, "extract": str(ext), "status": "missing", "small_glyphs": [],
                 "n_small_glyphs": 0, "n_glyph_warnings": 0, "min_glyph_pt": None, "text_pt": None, "error": None}
            rows.append(r)
            path = paths.SIM / script
            if not path.is_file():
                r.update(status="error", error=f"script {script} missing")
                continue
            got = _script_name(path)
            if got is not None and got != name:
                r.update(status="error", error=f"{script} draws {got!r}, not {name!r}")
                continue
            if not ext.is_file():
                continue
            buf = io.StringIO()
            try:
                with warnings.catch_warnings(record=True) as caught, contextlib.redirect_stdout(buf):
                    warnings.simplefilter("always")
                    rep = m3._figs_import(module).main(["--from-extract", str(ext)])
                outside = [p for p in (rep.get("pdf"), rep.get("json")) if p and not m3._under(p, tmp)]
                if outside:
                    raise RuntimeError(f"wrote outside the temporary folder: {outside}")
                small = [list(x) for x in rep.get("small_glyphs") or []]
                r.update(status="ok", small_glyphs=small, n_small_glyphs=len(small),
                         n_glyph_warnings=sum(1 for w in caught if type(w.message).__name__ == "GlyphSizeWarning"),
                         min_glyph_pt=rep.get("min_glyph_pt"), text_pt=rep.get("text_pt"))
            except (Exception, SystemExit) as err:
                r.update(status="error", error=f"{type(err).__name__}: {err}"[:500])
            finally:
                plt.close("all")
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        shutil.rmtree(tmp, ignore_errors=True)
    counts = {s: sum(1 for r in rows if r["status"] == s) for s in ("ok", "missing", "error")}
    return {"run": True, "extracts": str(extracts), "rows": rows, "counts": counts,
            "note": f"{len(rows)} figure script(s) rerun with --from-extract into a temporary folder (removed)"}


# ---------------------------------------------------------------- caption drafts (§8.1, §9)
FIG4_MODULE = "figs.fig4_e7_e3"           # its caption() drafts Fig. 4's caption, here and in the figure's extract


def _median(xs) -> Optional[float]:
    nums = [float(x) for x in xs if _num(x)]
    return statistics.median(nums) if nums else None


def captions_block(inp) -> dict:
    """The caption drafts: Fig. 4's (§8.1, drafted here by figs.fig4_e7_e3.caption, the function that writes the
    figure extract's labels.caption, every number read from an out/ file: own capacity, the median over the alignments
    of e7/main/summary.json meta.own_capacity_usd in whole USD with a thousands separator, the form whose length §8.1
    counts (417 characters at six digits, 4 alignments x 3 seeds); the alignments and policy seeds of its meta.grids;
    u from e3/summary.json meta.grid.u) and the facts of Table III's caption (§9, from e7/table3.json
    caption: the certificate count over every A8 run of E7, held in N of N with the W(a), W(b) and W(c) counts, the
    allowance and the information class)."""
    M, _ = inp.load(E7_SUM)
    E3, _ = inp.load(E3_SUM)
    meta, g3 = m3._d(m3._d(M).get("meta")), m3._d(m3._d(m3._d(E3).get("meta")).get("grid"))
    grids = m3._d(meta.get("grids"))
    own = _median(m3._d(meta.get("own_capacity_usd")).values())
    n_c = len(grids["alignments"]) if isinstance(grids.get("alignments"), list) else None
    n_p = len(grids["policy_seeds"]) if isinstance(grids.get("policy_seeds"), list) else None
    us = g3.get("u") if isinstance(g3.get("u"), list) else []
    u = us[0] if len(us) == 1 else None
    lacking = []
    if own is None:
        lacking.append(f"{E7_SUM} meta.own_capacity_usd missing")
    if n_c is None or n_p is None:
        lacking.append(f"{E7_SUM} meta.grids.alignments or policy_seeds missing")
    if not _num(u):
        lacking.append(f"{E3_SUM} meta.grid.u is not one number")
    text = None if lacking else m3._figs_import(FIG4_MODULE).caption(own, n_c, n_p, float(u))
    notes = lacking + (["drafted from a reduced run (never a result)"] if _reduced(M) or _reduced(E3) else [])
    fig4 = {"text": text, "n_chars": len(text) if text else None, "max_chars": FIG4_CAPTION_MAX,
            "within_limit": (len(text) <= FIG4_CAPTION_MAX) if text else None,
            "values": {"own_capacity_usd": own, "n_alignments": n_c, "n_policy_seeds": n_p, "u": u},
            "notes": notes, "sources": [E7_SUM, E3_SUM]}
    T, prob = inp.load(TABLE3)
    cap = m3._d(m3._d(T).get("caption"))
    cert = m3._d(cap.get("certificates"))
    by = m3._d(cert.get("by_case"))
    t3notes = [] if T is not None else [f"{TABLE3} {prob}"]
    if T is not None and _reduced(T):
        t3notes.append("table3.json is from a reduced run (never a result)")
    line = None
    if _num(cert.get("n")) and _num(cert.get("held")):
        cases = ", ".join(f"{c} {m3._d(by.get(c)).get('runs')}" for c in ("W(a)", "W(b)", "W(c)"))
        line = f"certificate held in {cert['held']} of {cert['n']} A8 runs ({cases})"
    elif T is not None:
        t3notes.append(f"{TABLE3} caption.certificates incomplete")
    own3 = m3._d(cap.get("own_capacity_usd")).get("median")
    t3 = {"certificates": line, "held": cert.get("held"), "n": cert.get("n"), "by_case": by or None,
          "B0_rule": cap.get("B0_rule"), "gamma": cap.get("gamma"), "kappa": cap.get("kappa"),
          "info_class_reported": cap.get("info_class_reported"), "own_capacity_usd_median": own3,
          "scope": cap.get("scope"), "source": TABLE3, "notes": t3notes}
    return {"fig4": fig4, "table3": t3}


# ---------------------------------------------------------------- the report
def build(root=None, *, figures: bool = True, only=None, extracts=None) -> dict:
    """The report (module docstring, ms4_claims.json) from the files under the input root."""
    root = Path(root).resolve() if root is not None else m3._default_root()
    inp = m3._Inputs(root)
    rows = [_row_or_bug(s, inp) for s in SPECS]
    crit = criterion(rows)
    fl = floats_block(inp)
    cp = copy_block(inp)
    jb = jobs_block(inp)
    cap = captions_block(inp)
    ex = Path(extracts).resolve() if extracts is not None else root / OUT / "figs"
    fg = figures_block(root, ex, only) if figures else \
        {"run": False, "extracts": str(ex), "rows": [], "counts": {}, "note": "not run (--no-figures)"}
    meta = {"module": "sublet.experiments.ms4_claims", "spec": f"{SPEC_DOC} §1.4", "git_revision": mc.git_revision(),
            "written": mc._now(), "input_root": str(root), "input_root_is_repository": m3._is_repo(root),
            "inputs": dict(sorted(inp.status.items()))}
    return {"meta": meta, "criterion": crit, "rows": rows, "floats": fl, "figures": fg, "copy_checks": cp,
            "jobs": jb, "captions": cap}


def markdown(rep: dict) -> str:
    """ms4_claims.md: the head (the criterion, figures, floats, copy checks, jobs), the claims tables per experiment
    with their notes, Table III's height, the figures' small glyphs, the copy checks, the jobs and the captions."""
    fmt, kv, cell = m3._fmt, m3._kv, m3._cell
    m, c = rep["meta"], rep["criterion"]
    L = ["# MS4 claims report (design/sim_spec_ms4.md §1.4)", ""]
    where = "the repository" if m["input_root_is_repository"] else \
        f"`{m['input_root']}` (not the repository: a test or fixture tree, whose values are not results)"
    L.append(f"Written {m['written']} by `{m['module']}` at revision {m['git_revision']}; inputs under {where}.")
    L.append("")
    L.append(f"**Criterion of §1.4 item 2: {'holds' if c['holds'] else 'does not hold'}.** {c['reasons']}.")
    L.append("")
    L.append(f"Rows: {c['n_rows']}; " + ", ".join(f"{v} {n}" for v, n in c["counts"].items()) + ".")
    L.append("")
    fg = rep["figures"]
    if fg["run"]:
        cn = fg["counts"]
        n_small = sum(1 for r in fg["rows"] if r["n_small_glyphs"])
        L.append(f"Figures (§1.4 item 1): {cn.get('ok', 0)} of {len(fg['rows'])} redrawn from their extracts with "
                 f"finalize() passing, {cn.get('missing', 0)} extract(s) missing, {cn.get('error', 0)} error(s); "
                 f"{n_small} figure(s) with mathtext glyphs below {m3._script_min_pt():g} pt, i.e. below a "
                 f"first-level script of {m3._text_min_pt():g}-pt text (listed below; plan §5 allows first-level "
                 "scripts).")
    else:
        L.append("Figures (§1.4 item 1): not rerun (--no-figures).")
    L.append("")
    fl = rep["floats"]
    if fl["present"] and fl["rows"]:
        L.append("Floats (§1.4 item 5): " + "; ".join(
            f"{r['float']} {fmt(r['measured_pages'], 4)} page (budget {fmt(r['budget_pages'], 4)})"
            for r in fl["rows"]) + f" ({fl['note']}).")
    else:
        L.append(f"Floats (§1.4 item 5): {fl['note']}.")
    L.append("")
    cp = rep["copy_checks"]
    L.append("Copy checks: " + "; ".join(
        f"{exp} {('pass' if e['pass'] else 'FAIL') if e['present'] else 'no record'}"
        for exp, e in cp["records"].items()) + f" ({cp['note']}).")
    L.append("")
    jb = rep["jobs"]
    L.append("Jobs (§2.4): " + "; ".join(
        (f"{k} {r['n_listed']} listed, " + ", ".join(f"{st} {n}" for st, n in r["by_status"].items())
         if r["present"] else f"{k} no job list") for k, r in jb["rows"].items()) + f" ({jb['note']}).")
    L.append("")
    for exp in dict.fromkeys(r["experiment"] for r in rep["rows"]):
        rs = [r for r in rep["rows"] if r["experiment"] == exp]
        L.append(f"## {exp} ({rs[0]['section']})")
        L.append("")
        body = []
        for r in rs:
            lab = r["status_label"] or f"none: {r['status_label_note']}"
            k = kv(r["reference"]["values"])
            ref = r["reference"]["value"] + (f" ({k})" if k else "")
            body.append([r["id"], r["claim"]["spec"], lab, f"{ref}; `{r['reference']['file']}`",
                         f"{kv(r['regenerated']['value']) or '–'}; `{r['regenerated']['file']}`",
                         f"**{r['verdict']}**"])
        L.append("| Check | Claim | Status label | Reference (file) | Regenerated (file) | Verdict |")
        L.append("|---|---|---|---|---|---|")
        L += ["| " + " | ".join(cell(x) for x in row) + " |" for row in body]
        L.append("")
        notes = [r for r in rs if r["explanation"] or r["note"] or
                 (r["claim"]["summary"] and r["claim"]["summary"] != r["claim"]["spec"])]
        for r in notes:
            bits = []
            if r["explanation"]:
                bits.append(f"explained: {r['explanation']}")
            if r["note"]:
                bits.append(r["note"])
            if r["claim"]["summary"]:
                bits.append(f"the summary's claim: {r['claim']['summary']}")
            L.append(f"- {r['id']}: " + ". ".join(bits))
        if notes:
            L.append("")
    L.append("## Table III's height (§1.4 item 5)")
    L.append("")
    if fl["present"] and fl["rows"]:
        L.append(mc.md_table(["Float", "Measured (page)", "Budget (page)", "Within budget", "Difference (page)",
                              "Source"],
                             [[r["float"], r["measured_pages"], r["budget_pages"], fmt(r["within_budget"]),
                               r["difference_pages"], f"`{r['source']}`"] for r in fl["rows"]]))
        L.append(f"From `{fl['file']}`; {fl['note']}.")
    else:
        L.append(f"{fl['note']}.")
    L.append("")
    L.append("## Figures: small glyphs (§1.4 item 1)")
    L.append("")
    if fg["run"]:
        L.append(f"| Figure | Script | Status | Small glyphs | Glyphs below {m3._script_min_pt():g} pt (size, text) |")
        L.append("|---|---|---|---|---|")
        for r in fg["rows"]:
            what = ", ".join(m3._glyph(g) for g in r["small_glyphs"]) if r["status"] == "ok" else \
                (r["error"] or f"extract `{r['extract']}` missing")
            L.append("| " + " | ".join(cell(x) for x in (r["figure"], f"`{r['script']}`", r["status"],
                                                          r["n_small_glyphs"] if r["status"] == "ok" else "–",
                                                          what or "none")) + " |")
        L.append("")
        L.append(f"{fg['note']}; extracts from `{fg['extracts']}`.")
    else:
        L.append(f"{fg['note']}.")
    L.append("")
    L.append("## Copy checks (§1.2)")
    L.append("")
    L.append(mc.md_table(["Experiment", "Record", "Present", "Pass", "Commit", "Time", "Failed checks"],
                         [[exp, f"`{e['file']}`", fmt(e["present"]), fmt(e["pass"]), e["commit"], e["time"],
                           ", ".join(e["failed"]) or "–"] for exp, e in cp["records"].items()]).rstrip("\n"))
    L.append("")
    L.append(f"{cp['note'][0].upper() + cp['note'][1:]}.")
    L.append("")
    L.append("## Jobs (§2.4, §2.5)")
    L.append("")
    L.append(mc.md_table(["Folder", "Job list", "Listed", "Records by status", "Without 'ok' (blocking)",
                          "MILP, LB = LP (Q39)", "Summary: jobs_missing, ignored_outputs, outputs_missing"],
                         [[k, f"`{r['manifest']}`", r["n_listed"], fmt(r["by_status"]) if r["present"] else "–",
                           r["n_blocking"], r["n_milp_lp_fallback"],
                           f"{fmt(r['summary_jobs_missing'])}, {fmt(r['summary_ignored_outputs'])}, "
                           f"{fmt(r['summary_outputs_missing'])}"]
                          for k, r in jb["rows"].items()]).rstrip("\n"))
    L.append("")
    L.append(f"{jb['note'][0].upper() + jb['note'][1:]}. The jobs without an 'ok' record outside Q39's MILP rule are "
             f"listed below, at most {m3.JOBS_LIST_MAX} per folder; a MILP job stopped at the wall-clock limit or by "
             "the cap leaves the LP as its LB (§2.5).")
    for k, r in jb["rows"].items():
        if r["blocking"]:
            L.append("")
            L.append(f"- {k}: " + "; ".join(f"`{x['job']}` ({x['kind']}, {x['status']})" for x in r["blocking"])
                     + (f"; ... ({r['n_blocking']} in all)" if r["n_blocking"] > len(r["blocking"]) else ""))
    L.append("")
    L.append("## Caption drafts (§8.1, §9)")
    L.append("")
    f4, t3 = rep["captions"]["fig4"], rep["captions"]["table3"]
    if f4["text"]:
        L.append(f"Fig. 4 ({f4['n_chars']} characters, at most {f4['max_chars']}): {f4['text']}")
    else:
        L.append(f"Fig. 4: no draft ({'; '.join(f4['notes'])}).")
    if f4["text"] and f4["notes"]:
        L.append("")
        L.append(f"Fig. 4 notes: {'; '.join(f4['notes'])}.")
    L.append("")
    if t3["certificates"]:
        L.append(f"Table III's caption (from `{t3['source']}`): {t3['certificates']}; B0_rule {t3['B0_rule']}, "
                 f"gamma {fmt(t3['gamma'])}, kappa {fmt(t3['kappa'])}; information class "
                 f"{t3['info_class_reported']}; own capacity (median over the alignments) "
                 f"{fmt(t3['own_capacity_usd_median'])} USD per week"
                 + (f" ({'; '.join(t3['notes'])})" if t3["notes"] else "") + ".")
    else:
        L.append(f"Table III's caption: no certificate count ({'; '.join(t3['notes']) or 'missing'}).")
    return "\n".join(L) + "\n"


def write(rep: dict, out_dir) -> tuple[Path, Path]:
    out = Path(out_dir)
    rep["meta"]["out_dir"] = str(out.resolve())
    pj = mc.dump_json(rep, out / OUT_JSON)
    pm = mc.write_text(markdown(rep), out / OUT_MD)
    return pm, pj


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m sublet.experiments.ms4_claims",
                                 description=__doc__.strip().split("\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", type=Path, default=None,
                    help=f"input root with the repository's layout (default {ENV_IN_ROOT}, else the repository)")
    ap.add_argument("--out-dir", type=Path, default=None,
                    help="folder of ms4_claims.md and .json (default the repository's code/sim/out when the root is "
                         "the repository; required otherwise)")
    ap.add_argument("--no-figures", action="store_true", help="skip the figure reruns")
    ap.add_argument("--only", nargs="+", metavar="NAME", default=None, help="rerun only these figures")
    ap.add_argument("--extracts", type=Path, default=None,
                    help="folder of the figure extracts <name>.json (default <root>/code/sim/out/figs)")
    a = ap.parse_args(argv)
    root = a.root.resolve() if a.root is not None else m3._default_root()
    if a.out_dir is None:
        if not m3._is_repo(root):
            ap.error(f"--out-dir is required when the input root ({root}) is not the repository")
        a.out_dir = paths.SIM_OUT
    rep = build(root, figures=not a.no_figures, only=a.only, extracts=a.extracts)
    pm, pj = write(rep, a.out_dir)
    c, fg = rep["criterion"], rep["figures"]
    figs = (", ".join(f"{k} {v}" for k, v in fg["counts"].items()) if fg["run"] else "not run")
    print(f"[ms4_claims] wrote {pm} and {pj}: criterion {'holds' if c['holds'] else 'does not hold'} ("
          + ", ".join(f"{v} {n}" for v, n in c["counts"].items() if n) + f"); figures: {figs}", flush=True)
    return 0


SPECS = _rows_spec()

if __name__ == "__main__":
    sys.exit(main())
