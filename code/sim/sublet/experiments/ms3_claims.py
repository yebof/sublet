"""The MS3 claims report (design/sim_spec_ms3.md §1.4 items 1, 2 and 5; deliverable D29, unit U18).

Reads the MS3 summaries and the records that §3.3-§7.3 name under an input root and writes the report
code/sim/out/ms3_claims.md and ms3_claims.json: one row per check of §3.3 (E11), §4.6 (E1), §5.5 (E10), §6.9 (E2)
and §7.3 (E6), in the spec's order, with the check id, the claim (the spec row and the summary's `claim` field),
the design's status label for the claim it tests (copied from the spec, never upgraded; null where the check tests
no theory claim, with what it tests), the reference value and file, the regenerated value and file, and the
verdict; then the measured heights of Tables I, II and Algorithm 1 next to their budgets (§1.4 item 5, from
code/sim/out/figs/floats_heights.json), the small glyphs of every figure (§1.4 item 1), the copy checks and the job
records of every experiment folder against its job list.

  python -m sublet.experiments.ms3_claims [--root DIR] [--out-dir DIR] [--no-figures] [--only NAME ...]
                                          [--extracts DIR]

  --root DIR      the input root, a folder with the repository's layout (code/sim/out/e1/summary.json, ...):
                  default SUBLET_FIGS_IN_ROOT (the variable of figs.inputs), else the repository; the tests pass
                  the synthetic fixture tree tests/fixtures_figs/inputs/
  --out-dir DIR   where ms3_claims.md and ms3_claims.json go: default the repository's code/sim/out when the root
                  is the repository; required with any other root
  --no-figures    skip the figure reruns (the 'figures' block says so)
  --only NAME     rerun only these figures (names as style.save's: fig5, sf_e10b, ...)
  --extracts DIR  the folder of the figure extracts <name>.json (default <root>/code/sim/out/figs)

Run from code/sim in the 3 GB scope. Exit 0 once the report is written, whatever its verdicts.

Rows and verdicts. A row reads its check entry checks.<id> of the experiment's summary (code/sim/out/e1/,
e10/, e2/, e6/a/ for E6-1 to E6-5 and e6/b/ for E6-6), whose `status` is one of §2.6's: pass, fail, missing,
pending, explained, informative, elsewhere. The E11 rows and E1-1 are computed here from the files §3.3 and §4.6
name (E11-0: code/sim/out/ms3_e11_0.json; E11-1: e11/summary.json checks.V1-V7; E11-2: its
certificate_full_model and D5.certificate; E11-3: code/sim/out/figs/fig1.json `same_as_first_study` and
`first_study`; E11-4: Fig. 3's values in code/sim/out/figs/fig3.json against figs.fig3_e11.collect_a and
collect_b run on code/sim/out/q44_study/summary.json and (c)'s series from its D5: every drawn number, (a) x, y,
x_min, y_min and the per-instance D1, W0 behind them and the criteria region, (b) per lender mode x, median, ci_lo,
ci_hi, n and the intensity, (c) per rho1 mean, min, max, runs and the revocable-only limit; the G3(b) line not
compared; E1-1, whose summary status is 'elsewhere': figs/fig2.json data.b.E1_1). Verdicts:
  reproduced   status pass of a check that reproduces an earlier value (the row's kind 'reproduction')
  holds        status pass of a property check (kind 'property')
  bug          status fail; also a status outside §2.6's vocabulary, 'elsewhere' on a row other than E1-1,
               'explained' where the spec allows no explanation, 'informative' where the spec sets a pass
               condition, an input that is not a JSON object, and every row of a summary whose meta.reduced is
               true (a smoke run, never a result)
  explained    status explained where the spec allows it (E2-5); its text needs the E2-5 MILP records to confirm
               every episode below 1 - 1e-9 as a counterexample to Claim D2 (else the row has no text)
  informative  the rows the spec marks informative (they report a value and have no pass condition)
  missing      the check's output, summary or job is absent (or the summary says missing)
  pending      the summary says pending (a rerun or MILP job outstanding)
The computation is the module's own only for E11-4's collectors; everything else is read.

Criterion (§1.4 item 2): it holds iff no row is 'bug' and every row other than reproduced, holds and informative
is 'explained' with its text; a missing or pending row therefore makes it not hold until its output exists. The
job records (jobs_block) do not enter it: a summary built from a partial job set marks its checks over the runs
that exist, so the report's head lists the jobs without an 'ok' record, and tests/test_ms3_out.py fails on those
outside Q39's MILP rule (§1.4 item 3).

Figures (§1.4 item 1): every MS3 figure script (the 20 of MS3_FIGURE_SCRIPTS, MS4 addition C17) is rerun in this
process with --from-extract <extracts>/<name>.json, its PDF, extract, preview and tables going to a temporary folder
(SUBLET_FIGS_PDF_DIR, SUBLET_FIGS_OUT_DIR, SUBLET_FIGS_TABLES_DIR set for the run, SUBLET_FIGS_IN_ROOT to the
root; never paper/ nor code/sim/out/figs/), and the report that figs.common.cli returns gives its small_glyphs
([size, text] of every mathtext text with glyphs below style.SCRIPT_MIN_PT, 6.3 pt); a figure whose extract is missing is listed as
'missing', one whose script raises (finalize() included) as 'error'.

Output schema of ms3_claims.json (key paths; the .md shows the same content as tables):
  meta.module, meta.spec, meta.git_revision, meta.written, meta.input_root, meta.input_root_is_repository
  meta.out_dir, meta.inputs.<repository-relative name>   'ok' | 'missing' | 'invalid JSON: ...' (files read)
  criterion.holds                    bool (§1.4 item 2)
  criterion.text                     'holds: ...' or 'does not hold: ...' with the reasons
  criterion.reasons                  the reasons alone (the sentence after the verdict in the .md's head)
  criterion.n_rows, criterion.counts.<verdict>   the number of rows per verdict (every verdict listed)
  criterion.bug, criterion.missing, criterion.pending, criterion.explained, criterion.unexplained   check ids
  rows[]                             one per check, in the order of SPECS:
    id, experiment ('E11', 'E1', 'E10', 'E2', 'E6'), section ('§3.3', ...), kind ('reproduction' | 'property'
    | 'informative'), claim.spec, claim.summary (the summary's claim field or null), status_label (the
    design's label, copied; null where the check tests no theory claim), status_label_note, reference.value
    (the spec's text), reference.values {path: value} (read from the entry where the summary records them),
    reference.file, regenerated.value {path: value} (fields of the check entry: '#x' as 'len(x)', 'min:x' as
    'min(x)', 'max:x' as 'max(x)', 'a[*].b' the list of b over a), regenerated.file, summary_status (the status
    read, or null), verdict, explanation (text of an 'explained' row, else null), note (why a row is missing,
    pending or a bug, and the informative rows' remarks; else null), detail (E11-4: the compared values)
  floats.file, floats.present, floats.rows[] {float, name, measured_pages, budget_pages, within_budget,
    difference_pages, source}, floats.note
  figures.run (bool), figures.extracts, figures.rows[] {figure, script, extract, status ('ok' | 'missing' |
    'error'), small_glyphs [[size, text]], n_small_glyphs, n_glyph_warnings, min_glyph_pt, text_pt, error},
    figures.counts.<status>, figures.note
  copy_checks.<exp> for exp in e11, e1, e10, e2, e6: file, present, pass, commit (the clone's commit, or E11's
    manifest revision), time, failed (the names of the failed checks), records_by_status (null for e11)
  jobs.rows.<folder> for folder in e1, e10, e2, e6/a, e6/b: manifest, present, n_listed, by_status {status: n}
    ('no record' where a listed job has none), n_blocking, blocking [{job, kind, status}] (at most 50), n_milp_lp_
    fallback, milp_lp_fallback (MILP jobs with status wall_limit or oom_at_3G: LB = LP, §2.5), n_unlisted_records,
    n_unreadable_records, summary_jobs_missing, summary_ignored_outputs (lengths of the summary's meta lists)
  jobs.n_blocking, jobs.note
"""
from __future__ import annotations

import argparse
import contextlib
import importlib
import io
import json
import math
import os
import re
import shutil
import sys
import tempfile
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Optional

from .. import paths
from . import ms3_common as mc

SPEC_DOC = "design/sim_spec_ms3.md"
OUT_MD, OUT_JSON = "ms3_claims.md", "ms3_claims.json"
ENV_IN_ROOT = "SUBLET_FIGS_IN_ROOT"            # figs.inputs.ENV_IN_ROOT (not imported: figs loads matplotlib)
ENV_FIG_DIRS = ("SUBLET_FIGS_PDF_DIR", "SUBLET_FIGS_OUT_DIR", "SUBLET_FIGS_TABLES_DIR")

OUT = "code/sim/out"
E1_SUM, E10_SUM, E2_SUM = f"{OUT}/e1/summary.json", f"{OUT}/e10/summary.json", f"{OUT}/e2/summary.json"
E6A_SUM, E6B_SUM = f"{OUT}/e6/a/summary.json", f"{OUT}/e6/b/summary.json"
E11_SUM, Q44_SUM, E11_0 = f"{OUT}/e11/summary.json", f"{OUT}/q44_study/summary.json", f"{OUT}/ms3_e11_0.json"
FIG1, FIG2, FIG3 = f"{OUT}/figs/fig1.json", f"{OUT}/figs/fig2.json", f"{OUT}/figs/fig3.json"
FLOATS = f"{OUT}/figs/floats_heights.json"
COPY_EXPS = ("e1", "e10", "e2", "e6")
FLOAT_NAMES = {"table1_price_of_revocation": "Table I", "table2_policies": "Table II", "alg1_guard": "Algorithm 1"}
VERDICTS = ("reproduced", "holds", "informative", "explained", "bug", "missing", "pending")
OK_VERDICTS = ("reproduced", "holds", "informative")
V_CHECKS = ("V1", "V2", "V3", "V4", "V5", "V6", "V7")

# status labels copied from the spec (§3.3, §4.1, §5.1, §6.1, §7.1) and design/Sublet_design.md (Table 5.9, §2.9,
# §5.2.4), in the drivers' ASCII (C1-C3, rho, tau, >=); never upgraded. Each "; "-separated part of a label that
# carries a status word is a verbatim copy, or "ID (text)" whose text opens the ID's parenthesis in those documents
# (tests/test_ms3_claims.py checks this); a part without a status word says what the check tests.
W_AB = "Theorem W(a)(b) (PROVEN for the engine as implemented under C1-C3, audited); W(c) (CONJECTURE)"
C3_L2 = "C3-L2 (PROVEN, pathwise, tight for every rho)"
O1_A = "O1-A (PROVEN for m >= 3 under one-notice I1 and the assumptions of design §1.8.3)"
C2_P8 = ("C2-P8 (lower bound PROVEN, table values interval-certified, equality VERIFIED NUMERICALLY at alpha = 0.3, "
         "CONJECTURE in general)")
C2_SW = ("every per-lender H*_mu at a lender's IR price is the C2-SW formula, CONJECTURE "
         "(code/sim/out/ms2_checks/e2_reactions.json, field status)")


# ---------------------------------------------------------------- the rows (the spec's tables)
@dataclass(frozen=True)
class Spec:
    """One check of §3.3-§7.3: id, experiment, section, kind ('reproduction', 'property' or 'informative'), the spec
    row's content, the design's status label of the claim it tests (None: no theory claim, then `label_note` says
    what it tests), the summary it reads (None: computed here by `compute`), the reference (the spec's text and the
    file), the entry's fields shown as the regenerated value (paths as `_get`), the entry's fields that hold the
    reference values, the regenerated value's file (default: the summary's checks.<id>), and whether the spec
    allows the verdict 'explained'."""
    id: str
    exp: str
    section: str
    kind: str
    claim: str
    label: Optional[str]
    label_note: Optional[str] = None
    summary: Optional[str] = None
    reference: str = ""
    reference_file: str = ""
    fields: tuple = ()
    ref_fields: tuple = ()
    regenerated_file: Optional[str] = None
    explainable: bool = False
    compute: Optional[Callable] = None


def _rows_spec() -> tuple:
    C3O = "code/theory_checks/c3/out"
    return (
        # §3.3 E11
        Spec("E11-0", "E11", "§3.3", "property",
             "the copy of §3.2 step 1: manifest.json meta.git_revision is E11's commit; every run file that records "
             "a git revision records it; the file list and the sha256 of every file equal the clone's",
             None, "the provenance of the copy (no claim of the design)", None,
             f"the clone's files and their sha256; revision {mc.E11_REVISION} (§3.1)", "E11's clone (record field "
             "'clone')", ("pass", "n_files_copy", "n_files_clone", "n_sha256_mismatch", "n_only_in_copy",
                          "n_only_in_clone", "manifest_git_revision", "n_run_revision_differs",
                          "n_runs_no_revision_other", "n_runs_unreadable"),
             regenerated_file=E11_0, compute=_e11_0),
        Spec("E11-1", "E11", "§3.3", "property",
             "e11/summary.json checks.V1-V7 each pass; V3 is computed from T2_ad (it was 'not run' in the first "
             "study, q44_study/summary.json checks.V3.why)",
             None, "the Q44 study's checks V1-V7 (design/q44_practical_sublet.md §8.2)", None,
             "each pass (V1 against the values of its reference_file, V5 against c4_lower.json)",
             f"{E11_SUM} (checks.V1.reference_file, checks.V5.reference_file)", V_CHECKS + ("V3_pairs",),
             ("V1_reference_file", "V5_reference_file"), regenerated_file=f"{E11_SUM} checks.V1-V7",
             compute=_e11_1),
        Spec("E11-2", "E11", "§3.3", "property",
             "certificate_full_model.all_held and the certificate of every core-export run (D5.certificate) true; a "
             "run in Theorem W's proven cases whose ALG(T) exceeds its bound plus the tolerance is a bug",
             W_AB, None, None, "every certificate held (all_held true, no failure listed)",
             "code/sim/sublet/algos/guard.py (Theorem W, module docstring); design/Sublet_design.md §2.9",
             ("full_model_all_held", "full_model_held", "full_model_runs", "full_model_failures",
              "core_all_held", "core_held", "core_runs", "core_failures"),
             regenerated_file=f"{E11_SUM} certificate_full_model, D5.certificate", compute=_e11_2),
        Spec("E11-3", "E11", "§3.3", "informative",
             "identity of the Fig. 1(b) run (§8.1's rule) with the first study's file of the same path (t_a, ALG_T, "
             "the guard record), and whether the rule picks the same path in both (informative, M42)",
             None, "the identity of one run between the two studies (M42)", None,
             "the first study's run file of the same path", f"{FIG1} data.first_study",
             ("run_file", "same_as_first_study", "t_a", "ALG_T", "identical"),
             regenerated_file=f"{FIG1} data", compute=_e11_3),
        Spec("E11-4", "E11", "§3.3", "informative",
             "Fig. 3's numbers versus the first study's: fig3.json carries E11's values; the first study's come from "
             "fig3_e11.collect_a and collect_b on q44_study/summary.json and (c)'s series from its D5; (c)'s G3(b) "
             "line is not compared (informative; changes under L-co are expected from S11)",
             None, "measurements (Fig. 3's values), no pass condition", None,
             "the first study's Fig. 3 values (collect_a, collect_b, D5)", Q44_SUM,
             ("n_compared", "n_differ", "n_differ_a", "n_differ_b", "n_differ_c", "max_abs_diff_a", "max_abs_diff_b",
              "max_abs_diff_c", "largest_a", "largest_b", "largest_c", "n_without_counterpart", "e11_revision"),
             regenerated_file=f"{FIG3} data.a, data.b, data.c", compute=_e11_4),
        # §4.6 E1
        Spec("E1-1", "E1", "§4.6", "reproduction",
             "Fig. 2(b)'s rho at maas_p99_median equals a11's rows.*.rho (computed by the Fig. 2 script into "
             "figs/fig2.json data.b.E1_1; e1/summary.json gives it the status 'elsewhere'); 1e-12 relative",
             None, "the calibration formula of a11 (field_sources.rho)", E1_SUM,
             "rows.maas_a10.<t>.<s>.by_contract.<k>.rho", "code/analysis/out/a11_calibration.json",
             ("n", "max_rel_err", "tol", "price_ref"), regenerated_file=f"{FIG2} data.b.E1_1", compute=_e1_1),
        Spec("E1-2", "E1", "§4.6", "property",
             "instance_rho after beta_for_rho equals rho* for both LLMs, every config seed (1e-9)",
             None, "the construction of the per-LLM fee (C12)", E1_SUM,
             "rho* in {1.5, 2, 4, 8, 16} (the target)", f"{E1_SUM} meta.fees",
             ("n_cells", "max_abs_diff", "#failures")),
        Spec("E1-3", "E1", "§4.6", "reproduction",
             "tight family at T = 60 equals c3/out/c3_benchmark.json a[*] (OPT_eager, OPT_none, "
             "OPTeager_over_OPTnone); at every T the MILP values equal the closed forms (1e-9, status 0, gap 0)",
             C3_L2 + "; core.opt_omega and core.opt_eager (Proposition M1, Corollary M2, PROVEN)",
             None, E1_SUM, "c3_benchmark.json a[*] at T = 60; the closed forms of §4.4",
             f"{C3O}/c3_benchmark.json",
             ("n_rows", "n_T60_compared", "max_abs_diff_T60_vs_reference", "max_rel_diff_closed_form",
              "#not_optimal_or_gap", "#above_max2rho"), regenerated_file=f"{OUT}/e1/tight_family.json check_E1_3"),
        Spec("E1-4", "E1", "§4.6", "property",
             "on every instance with an exact core export, OPT_eager / OPT(sigma, omega) <= max(2, rho) (C3-L2); "
             "the tight family and c3_benchmark.json b (re-solved, reproduced to 1e-9, at most 1.513) are exact; "
             "on the trace instances the bracket is a diagnostic",
             C3_L2, None, E1_SUM, "max(2, rho); c3_benchmark.json b[*].per_rate[*].eager_over_omega",
             f"{C3O}/c3_benchmark.json",
             ("core_b_n", "core_b_max_eager_over_omega", "core_b_max_abs_diff", "core_b_reproduced",
              "core_b_all_within_bound", "#tight_family_above_max2rho", "trace_exports.n_exact",
              "trace_brackets_diagnostic.n_lo_above_max2rho"),
             regenerated_file=f"{OUT}/e1/core_b.json, tight_family.json; {E1_SUM} checks.E1-4"),
        Spec("E1-5", "E1", "§4.6", "property",
             "every Sublet run's certificate held in Theorem W's proven cases; W(c) runs reported", W_AB, None,
             E1_SUM, "ALG(T) within Theorem W's bound in every proven case", "code/sim/sublet/algos/guard.py",
             ("runs", "n_failures", "n_w_c", "by_case")),
        Spec("E1-6", "E1", "§4.6", "property",
             "every E1(b) run: invariant_failures empty, gpu_only_lease_slots 0, ratio_validity None; plan class P1 "
             "runs have ratio_LB >= 1 - 1e-6 (LB <= OPT_P1 <= ALG)", "Proposition M4 (PROVEN)", None, E1_SUM,
             "no failure; ratio_LB >= 1 - 1e-6 for P1 runs", "design/Sublet_design.md §5.2.4 (Proposition M4)",
             ("n_runs", "#invariant_failures", "#gpu_only_lease_slots", "#ratio_validity_not_none", "n_p1",
              "#p1_below", "min_ratio_LB_p1")),
        Spec("E1-7", "E1", "§4.6", "reproduction",
             "A3 in reference mode with rbar = 1 and with the theory rbar reproduces c3/out/c4_lower.json a "
             "(pd_r1, pd_r1_min, pd_rth, pd_rth_min) through E10-1",
             "C3-T4 (PROVEN)", None, E1_SUM, "c4_lower.json a (pd_r1, pd_r1_min, pd_rth, pd_rth_min)",
             f"{C3O}/c4_lower.json", ("n_points", "max_abs_diff_pd_columns"),
             regenerated_file=f"{OUT}/e10/repro.json (E10-1); {E1_SUM} checks.E1-7"),
        Spec("E1-8", "E1", "§4.6", "informative",
             "ratios above max(2, rho) on trace instances are not bugs (plan §7); counted and reported",
             "C3-Cor3 (PROVEN); trace instances leave the ORML core, so their ratios are diagnostics", None,
             E1_SUM, "max(2, rho*)", f"{E1_SUM} ratios.*.max2rho", ("n_runs_above", "#by_point")),
        # §5.5 E10
        Spec("E10-1", "E10", "§5.5", "reproduction",
             "at T = 48, m in {2, 3, 4, 6}, rho in {2, 4, 8, 16}, RR-renew, stay and A3's reference mode (rbar = 1 "
             "and theory), seeds 0-3, under 'adaptive', reproduce c4_lower.json a (rr, stay, pd_r1, pd_r1_min, "
             "pd_rth, pd_rth_min, LB_T); exact to 1e-9", "C3-T4 (PROVEN)", None, E10_SUM,
             "c4_lower.json a (rr, stay, pd_r1, pd_r1_min, pd_rth, pd_rth_min, LB_T)", f"{C3O}/c4_lower.json",
             ("n_points", "max_abs_diff", "#failures"), regenerated_file=f"{OUT}/e10/repro.json; {E10_SUM} "
                                                                         "checks.E10-1"),
        Spec("E10-2", "E10", "§5.5", "property",
             "C3-T4: every run under 'adaptive' has ALG/OPT >= LB_T - 1e-9",
             "C3-T4 (PROVEN, pathwise for deterministic algorithms against the adaptive-offline lender)", None,
             E10_SUM, "LB_T = (A0 beta + a T) / ((A0/m + 1) beta + a (T + D))", f"{E10_SUM} bounds",
             ("n_runs", "min_ratio_over_LB_T", "#failures")),
        Spec("E10-3", "E10", "§5.5", "property",
             "O1-B: every RR-renew run, under every lender, has ALG <= min{rho (1 + D/T) OPT, 2 m OPT + a D} "
             "(1 + 1e-9)", "O1-B (PROVEN, any lender)", None, E10_SUM,
             "min{rho (1 + D/T) OPT, 2 m OPT + a D}", f"{E10_SUM} checks.E10-3 (per run)",
             ("n_runs", "max_alg_over_bound", "#failures")),
        Spec("E10-4", "E10", "§5.5", "property",
             "under safe_site, OPT = Phi beta + a T on every schedule (1e-9)",
             O1_A + "; the check tests its Claim 1 (design/theory/o1_oblivious_lender.md)", None,
             E10_SUM, "Phi beta + a T", f"{E10_SUM} a.safe_site.*", ("n_runs", "max_rel_diff")),
        Spec("E10-5", "E10", "§5.5", "property",
             "O1-A: at m >= 3 the upper end of the 95% interval of E[ALG]/OPT under safe_site at k* is at least "
             "LB_A(k*) - 1e-9; a point below is rerun with seeds 30-129 (pending until then), still below is a bug",
             O1_A, None, E10_SUM, "LB_A(k*)", f"{E10_SUM} bounds.<rho>.<m>.LB_A; code/theory_checks/c3/o1/out/"
                                               "o1_lb.json A",
             ("n_points", "#flagged", "#still_flagged_after_rerun", "#rerun_pending")),
        Spec("E10-6", "E10", "§5.5", "property",
             "O1-D: the lower end of the 95% interval of marking's ratio is at most 2 h_m + 1 (reruns as E10-5)",
             "O1-D (PROVEN)", None, E10_SUM, "2 h_m + 1", f"{E10_SUM} bounds.<rho>.<m>.two_h_m_plus_1",
             ("n_points", "#flagged", "#still_flagged_after_rerun", "#rerun_pending")),
        Spec("E10-7", "E10", "§5.5", "informative",
             "O1-C: marking's ratio under iid_step at p* against max_p LB_C (a limit; finite runs may lie below)",
             "O1-C (PROVEN with tau >= 1); a T -> infinity limit that bounds no finite run", None, E10_SUM,
             "max_p LB_C", f"{E10_SUM} bounds.<rho>.<m>.LB_C_max",
             ("#points", "min:points[*].ratio_minus_LB_C", "max:points[*].ratio_minus_LB_C")),
        Spec("E10-8", "E10", "§5.5", "informative",
             "C-O1a: RR-renew's ratio under 'adaptive' against rho m / (m + rho - 1)",
             "C-O1a (VERIFIED NUMERICALLY / CONJECTURE)", None, E10_SUM, "rho m / (m + rho - 1)",
             f"{E10_SUM} bounds.<rho>.<m>.limit",
             ("#points", "min:points[*].ratio_over_limit", "max:points[*].ratio_over_limit")),
        Spec("E10-9", "E10", "§5.5", "reproduction",
             "o1_lb.lb_A, lb_C through import_ref reproduce o1_lb.json A at every listed (rho, m), and "
             "summary.json bounds equals them there (exact)",
             O1_A + "; O1-C (PROVEN with tau >= 1): the values of LB_A and LB_C", None, E10_SUM,
             "o1_lb.json A (k, LB_A, p, LB_C)", "code/theory_checks/c3/o1/out/o1_lb.json",
             ("n_listed", "recompute_pass", "#bounds_mismatch"), regenerated_file=f"{OUT}/e10/repro.json o1_lb; "
                                                                                 f"{E10_SUM} bounds"),
        Spec("E10-10", "E10", "§5.5", "informative",
             "E10(b): ratios growing faster than min(rho, m) in m at fixed rho (informative evidence against C-O1b; "
             "the entry lists stale_milp_records)", "C-O1b (CONJECTURE)", None, E10_SUM,
             "min(rho, m) and min(rho, 1 + log2 m), orders up to polylog factors", f"{E10_SUM} checks.E10-10.series",
             ("n_runs", "n_empty_instances", "#series", "#stale_milp_records")),
        # §6.9 E2
        Spec("E2-1", "E2", "§6.9", "reproduction",
             "the finer-grid game reproduces por_default.json table_por_switch_beta at mu = 1, lambda = "
             "inputs.lambda_default, Hs = H_BASE (the same floats); exact to 1e-12",
             C2_P8, None, E2_SUM,
             "table_por_switch_beta CR at Hs in H_BASE", "code/theory_checks/c2/out/por_default.json",
             ("max_abs_diff", "tolerance", "#missing_Hs", "rows[*].CR"), ("rows[*].CR_ref",),
             regenerated_file=f"{OUT}/e2/game.json; {E2_SUM} checks.E2-1"),
        Spec("E2-2", "E2", "§6.9", "property",
             "(a) the cell kinds, A1's insurance decision and its reaction per mu, recomputed by c2rule at each "
             "e2_reactions.json row's units, equal the row's (exact); (b) A1's units of the run against the row's "
             "(informative, differences listed)", C2_SW, None, E2_SUM,
             "e2_reactions.json rows (kind, insure_up_front, reaction, units)",
             "code/sim/out/ms2_checks/e2_reactions.json",
             ("a.n_rows", "#a.mismatches", "#a.alpha_kind_mismatches", "b.n_cells", "b.n_differences")),
        Spec("E2-3", "E2", "§6.9", "property",
             "Q42 (a): at mu = 1 on every cell, A1 and 'always cold' give identical ledgers where A1 does not insure; "
             "all three rules identical where it insures (1e-9 USD)",
             None, "the coincidence of the rules (Q42 (a)), a property of the build", E2_SUM,
             "A1's ledgers (1e-9 USD)", f"{E2_SUM} checks.E2-3",
             ("n_cells", "n_compared", "max_abs_diff_a1_cold", "max_abs_diff_insured", "#violations")),
        Spec("E2-3b", "E2", "§6.9", "property",
             "band-less layers: every band-less DP value at most the layer's fallback cost (1e-9 USD)",
             None, "the band-less layers (M48)", E2_SUM, "the layer's fallback cost", f"{E2_SUM} bandless",
             ("n_bandless", "max_dp_minus_fallback", "n_dp_missing", "#violations")),
        Spec("E2-4", "E2", "§6.9", "property",
             "every run: invariant_failures empty, gpu_only_lease_slots 0; every DP within its domain (status "
             "optimal)", None, "the engine's invariants and the DP's domain", E2_SUM, "no failure",
             f"{E2_SUM} checks.E2-4",
             ("n_runs", "n_invariant_failures", "n_gpu_only_lease_slots", "n_dp", "n_dp_not_optimal",
              "n_dp_domain_error")),
        Spec("E2-5", "E2", "§6.9", "property",
             "per-episode ratio at least 1 - 1e-9 (the DP is OPT on the episode's domain); below it a bug unless "
             "opt.milp.solve_opt on that episode returns an incumbent below the DP value (a confirmed counterexample "
             "to Claim D2: explained); pending while such an episode's MILP job has not run; ALG below the MILP's "
             "lower bound is a bug in any case", "Claim D2 (CONJECTURE)", None, E2_SUM, "1 - 1e-9",
             f"{E2_SUM} checks.E2-5",
             ("n_episodes", "min_ratio", "n_below", "n_candidates", "#unresolved", "#ep_milp_stale", "#milp"),
             explainable=True),
        Spec("E2-6", "E2", "§6.9", "informative",
             "the sum of the layers' DPs against the joint MILP's lower bound on 1-day instances",
             None, "open (MS1 spec §7.6): whether the sum of the layers' DPs equals the joint optimum", E2_SUM,
             "LB_joint = max(LP, dual bound)", f"{OUT}/e2/joint_milp.json",
             ("#rows", "min:rows[*].ratio_sum_dp_over_LB", "max:rows[*].ratio_sum_dp_over_LB")),
        Spec("E2-7", "E2", "§6.9", "informative",
             "a ratio above 2 - alpha at H >= H*_mu is not a bug on trace episodes (the bug test on C2-core "
             "instances is the harness's, MS2 spec §16)",
             "C2-T4 (PROVEN under (C'), tau = 0); " + C2_SW, None,
             E2_SUM, "2 - alpha_k at H >= H*_mu of the cell's e2_reactions.json row",
             "code/sim/out/ms2_checks/e2_reactions.json", ("by_group.maas", "by_group.spot")),
        # §7.3 E6
        Spec("E6-1", "E6", "§7.3", "property",
             "C2-T2 in the harness and A1's insurance rule: (a) the harness's INS worst ratio within "
             "[CR_ins (1 - 1e-3), CR_ins + 1e-9], (b) insure_up_front equals the direct formula and A1 reports it "
             "(exact)", "C2-T2 (PROVEN for insurance held to the end of the demand)", None, E6A_SUM,
             "CR_ins = max(2 - alpha, alpha_p / alpha); the direct formula with families.lb_react",
             "code/theory_checks/c2/out/por_default.json (inputs)",
             ("a.n", "a.n_fail", "b.n", "b.n_fail", "b.a1.n", "b.a1.n_fail"),
             regenerated_file=f"{OUT}/e6/a/runs/c2t2.json (job e6:a_c2t2); {E6A_SUM} checks.E6-1"),
        Spec("E6-2", "E6", "§7.3", "property",
             "linearity in a_p and in mu: INS and WARM reruns at r = 3, mu = 1 and WARM at r = 1.1, mu = 2 give "
             "A + a_p G + mu_fb W with the reference run's plan; A1's C2 units at c in {2, 3, 4} equal those at c = 1 "
             "(1e-9 relative)", None, "the linearity of E6(a)'s evaluation (M28)", E6A_SUM,
             "A + a_p(r) G + mu_fb(mu) W of the reference run", f"{E6A_SUM} checks.E6-2",
             ("n", "n_fail", "units_across_alignments.n", "units_across_alignments.n_fail")),
        Spec("E6-3", "E6", "§7.3", "property",
             "BL7 equals E2's cold, non-insured run of the same key (alignment 1, mu = 1, every 10th MaaS key; "
             "identical totals to 1e-9 USD)", None, "the identity of BL7 with E2's cold runs", E6A_SUM,
             "E2's cold, non-insured run of the same key", f"{OUT}/e2/runs/cells/ (E2's run files)",
             ("n", "n_fail", "n_without_e2_cold")),
        Spec("E6-4", "E6", "§7.3", "property",
             "where A1 neither insures nor pre-warms, the cell value is exactly 1",
             None, "a property of the heatmap value (M29)", E6A_SUM, "1", f"{OUT}/e6/a/heatmap.json",
             ("n_pairs", "max_abs_dev")),
        Spec("E6-5", "E6", "§7.3", "informative",
             "the cells where insuring pays on the traces (react_over_ins above 1) and the boundary's insuring "
             "region r < r*(H) differ, listed with their inputs (the experiment's question)",
             "C2-T3 (PROVEN for tau = 0): LB_react(H) <= CR_react(H), the boundary's certified bound", None,
             E6A_SUM, "r*(H) of the certified bound", f"{OUT}/e6/a/boundary.json", ("n_cells", "n_disagree")),
        Spec("E6-6", "E6", "§7.3", "property",
             "E6(b) runs: no invariant failure, no GPU-only lease slot", None, "the engine's invariants", E6B_SUM,
             "no failure", f"{E6B_SUM} checks.E6-6", ("n_runs", "n_invariant_failures", "n_gpu_only_lease_slots")),
    )


# ---------------------------------------------------------------- inputs
class _Inputs:
    """The files of the report under the input root, each read once; `status` records what was found."""

    def __init__(self, root: Path):
        self.root = Path(root)
        self.status: dict = {}
        self._cache: dict = {}

    def load(self, rel: str) -> tuple[Any, Optional[str]]:
        """(parsed JSON object, None), or (None, 'missing' | 'invalid JSON: ...'); every input of the report is a
        JSON object, so valid JSON of another type (a list, a number) is 'invalid JSON: not an object'."""
        if rel not in self._cache:
            p = self.root / rel
            if not p.is_file():
                self._cache[rel] = (None, "missing")
            else:
                try:
                    d = json.loads(p.read_text(encoding="utf-8"))
                    self._cache[rel] = (d, None) if isinstance(d, dict) else \
                        (None, f"invalid JSON: not an object ({type(d).__name__})")
                except (OSError, ValueError, RecursionError) as err:
                    self._cache[rel] = (None, f"invalid JSON: {err}"[:200])
            self.status[rel] = self._cache[rel][1] or "ok"
        return self._cache[rel]


def _d(x) -> dict:
    """x if it is a dict, else {} (a field of an input whose shape is not the drivers')."""
    return x if isinstance(x, dict) else {}


def _absent(rel: str, problem: str) -> dict:
    """The entry of a check whose input is absent ('missing') or not JSON (a bug, §2.6 writes only JSON)."""
    if problem == "missing":
        return {"status": "missing", "_note": f"{rel} missing"}
    return {"status": "bug_input", "_note": f"{rel}: {problem}"}


# ---------------------------------------------------------------- the computed rows (E11, E1-1)
def _e11_0(inp: _Inputs) -> dict:
    rec, prob = inp.load(E11_0)
    if rec is None:
        return _absent(E11_0, prob)
    failed = [k for k, v in _d(rec.get("checks")).items() if not v]
    e = {k: rec.get(k) for k in ("pass", "n_files_copy", "n_files_clone", "n_sha256_mismatch", "n_only_in_copy",
                                 "n_only_in_clone", "manifest_git_revision", "n_run_revision_differs",
                                 "n_runs_no_revision_other", "n_runs_unreadable")}
    e.update(status="pass" if rec.get("pass") is True else "fail", _ref_file=rec.get("clone"))
    if failed:
        e["_note"] = f"failed: {', '.join(failed)}"
    return e


def _e11_1(inp: _Inputs) -> dict:
    S, prob = inp.load(E11_SUM)
    if S is None:
        return _absent(E11_SUM, prob)
    ch = _d(S.get("checks"))
    st = {v: _d(ch.get(v)).get("status") for v in V_CHECKS}
    e = {**st, "V3_pairs": _d(ch.get("V3")).get("pairs"),
         "V1_reference_file": _d(ch.get("V1")).get("reference_file"),
         "V5_reference_file": _d(ch.get("V5")).get("reference_file")}
    if any(s == "fail" for s in st.values()):
        e["status"] = "fail"
    elif all(s == "pass" for s in st.values()):
        e["status"] = "pass"
    else:
        e["status"] = "missing"
        e["_note"] = "not every check of V1-V7 ran: " + ", ".join(f"{k} {v!r}" for k, v in st.items() if v != "pass")
    rev = _d(S.get("meta")).get("git_revision")
    if rev != mc.E11_REVISION:
        e["_note"] = (e.get("_note", "") + f"; e11/summary.json meta.git_revision {rev!r}, not E11's").lstrip("; ")
    return e


def _cert(c: Any) -> tuple:
    if not isinstance(c, dict):
        return None, None, None, None
    tot = _d(c.get("total"))
    n_fail = sum(len(_d(v).get("failures") or []) for v in _d(c.get("by_tag_mode")).values())
    return c.get("all_held"), tot.get("held"), tot.get("runs"), n_fail


def _e11_2(inp: _Inputs) -> dict:
    S, prob = inp.load(E11_SUM)
    if S is None:
        return _absent(E11_SUM, prob)
    fa, fh, fr, ff = _cert(S.get("certificate_full_model"))
    ca, ch, cr, cf = _cert(_d(S.get("D5")).get("certificate"))
    e = {"full_model_all_held": fa, "full_model_held": fh, "full_model_runs": fr, "full_model_failures": ff,
         "core_all_held": ca, "core_held": ch, "core_runs": cr, "core_failures": cf}
    if fa is None or ca is None:
        e.update(status="missing", _note="certificate_full_model or D5.certificate missing in e11/summary.json")
    else:
        e["status"] = "pass" if (fa is True and ca is True and not ff and not cf) else "fail"
    return e


def _e11_3(inp: _Inputs) -> dict:
    P, prob = inp.load(FIG1)
    if P is None:
        return _absent(FIG1, prob)
    d = _d(P.get("data"))
    fs = d.get("first_study")
    if not isinstance(fs, dict):
        return {"status": "missing", "_note": f"{FIG1} has no data.first_study (E11-3's comparison)"}
    ident = _d(fs.get("identical"))
    same = bool(d.get("same_as_first_study")) and bool(fs.get("same_path")) and bool(ident) and all(ident.values())
    e = {"status": "informative", "run_file": d.get("run_file"), "same_as_first_study": d.get("same_as_first_study"),
         "t_a": _d(fs.get("t_a")).get("e11"), "ALG_T": _d(fs.get("ALG_T")).get("e11"),
         "identical": same, "_ref_file": fs.get("same_file") or fs.get("pick"),
         "_ref_values": {"t_a": _d(fs.get("t_a")).get("first_study"),
                         "ALG_T": _d(fs.get("ALG_T")).get("first_study")}}
    if same:
        e["_note"] = ("the rule picks the same path in both studies and the run is identical (t_a, ALG_T and every "
                      "guard series)")
    else:
        diff = sorted(k for k, v in ident.items() if not v)
        e["_note"] = ("the run differs from the first study's" + (f" in {', '.join(diff)}" if diff else "")
                      + (" (the rule picks another path)" if not fs.get("same_path") else "")
                      + ": explained (M42) by the package changes between 472b353 and 29919ea in algos/guard.py "
                        "(audit fixes F1, F2), algos/a6.py (two lines), lender.py (S11, the correlated schedule "
                        "only) and experiments/q44_winddown.py; the audit's identity sample "
                        "(code/sim/out/audit_fm/identity.json) does not contain this run")
    return e


def _figs_import(name: str):
    """A module of the figure package (code/sim/figs), importable from code/sim."""
    if str(paths.SIM) not in sys.path:
        sys.path.insert(0, str(paths.SIM))
    return importlib.import_module(name)


def _series_c(f3, Q: dict) -> dict:
    """(c) of Fig. 3 from a summary's D5 (fig3_e11.collect_c without its G3(b) inputs, which come from run files):
    rho1, the revocable-only limit and, per registry key of fig3_e11.C_TAGS, the mean, min, max and runs of the
    ratio at each rho1."""
    fam = Q["D5"]["families"][f3.C_FAMILY]
    keys = sorted((k for k in fam if k.endswith(f"_T{f3.C_T}:{f3.C_MODE}")), key=lambda k: fam[k]["rho1"])
    series = {f3.TAG_KEY[t]: {"tag": t, "x": [fam[k]["rho1"] for k in keys],
                              **{f: [fam[k]["ratio"][t][f] for k in keys] for f in E11_4_C}} for t in f3.C_TAGS}
    return {"rho1": [fam[k]["rho1"] for k in keys], "series": series,
            "revocable_only_limit": [fam[k]["bounds"]["revocable_only_asymptote_a1rho1_over_a2"] for k in keys]}


# the fields of Fig. 3 that E11-4 compares (every drawn number and the per-instance values behind (a)'s extremes;
# (b) and (c) matched by lender mode and by rho1, so a reordering is not a difference)
E11_4_A = ("x", "y", "x_min", "y_min")
E11_4_A_INST = ("D1", "W0")
E11_4_CRIT = ("x_max", "y_max")
E11_4_B = ("x", "median", "ci_lo", "ci_hi", "n")
E11_4_C = ("mean", "min", "max", "runs")


def _diff_row(panel: str, key: str, field: str, at, e11, first) -> dict:
    ok = all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in (e11, first))
    ad = abs(float(e11) - float(first)) if ok else None
    rd = ad / abs(float(first)) if ok and float(first) != 0 else None
    return {"panel": panel, "key": key, "field": field, "at": at, "e11": e11, "first_study": first,
            "abs_diff": ad, "rel_diff": rd}


def _by(xs, vals) -> dict:
    """{x: value} of two parallel lists (a list shorter than the other is cut, a missing one is empty)."""
    return dict(zip(xs or [], vals or []))


def _fig3_rows(d: dict, first: dict) -> list:
    """The compared values of Fig. 3, one row each (module docstring, E11-4): (a) per registry key x, y, x_min,
    y_min and D1.<instance>, W0.<instance>, and the criteria region's x_max, y_max; (b) per key and lender mode x,
    median, ci_lo, ci_hi, n, and the intensity per mode; (c) per key and rho1 mean, min, max, runs, and the
    revocable-only limit per rho1. A value without a counterpart in the first study has abs_diff None."""
    rows = []
    fa = first["a"]["series"]
    for key, s in d["a"]["series"].items():
        f = fa.get(key) or {}
        rows += [_diff_row("a", key, k, None, s.get(k), f.get(k)) for k in E11_4_A]
        rows += [_diff_row("a", key, k, i, v, (f.get(k) or {}).get(i)) for k in E11_4_A_INST
                 for i, v in (s.get(k) or {}).items()]
    crit, fcrit = d["a"].get("criteria") or {}, first["a"].get("criteria") or {}
    rows += [_diff_row("a", "criteria", k, None, crit.get(k), fcrit.get(k)) for k in E11_4_CRIT]
    fb = first["b"]["series"]
    for key, s in d["b"]["series"].items():
        f = fb.get(key) or {}
        for k in E11_4_B:
            ref = _by(f.get("modes"), f.get(k))
            rows += [_diff_row("b", key, k, m, v, ref.get(m)) for m, v in zip(s["modes"], s[k])]
    ref = _by(first["b"].get("modes"), first["b"].get("intensity"))
    rows += [_diff_row("b", "intensity", "intensity", m, v, ref.get(m))
             for m, v in zip(d["b"]["modes"], d["b"]["intensity"])]
    fc = first["c"]["series"]
    for key, s in d["c"]["series"].items():
        f = fc.get(key) or {}
        for k in E11_4_C:
            ref = _by(f.get("x"), f.get(k))
            rows += [_diff_row("c", key, k, x, v, ref.get(x)) for x, v in zip(s["x"], s[k])]
    ref = _by(first["c"].get("rho1"), first["c"].get("revocable_only_limit"))
    rows += [_diff_row("c", "revocable_only_limit", "revocable_only_limit", x, v, ref.get(x))
             for x, v in zip(d["c"]["rho1"], d["c"]["revocable_only_limit"])]
    return rows


def _e11_4(inp: _Inputs) -> dict:
    P, prob = inp.load(FIG3)
    if P is None:
        return _absent(FIG3, prob)
    Q, prob = inp.load(Q44_SUM)
    if Q is None:
        return _absent(Q44_SUM, prob)
    try:
        f3 = _figs_import("figs.fig3_e11")
        first = {"a": f3.collect_a(Q), "b": f3.collect_b(Q), "c": _series_c(f3, Q)}
    except Exception as err:          # a first-study summary without the keys Fig. 3 reads
        return {"status": "missing", "_note": f"the collectors failed on {Q44_SUM}: {type(err).__name__}: {err}"}
    d = P.get("data") if isinstance(P.get("data"), dict) else {}
    try:
        rows = _fig3_rows(d, first)
    except (KeyError, TypeError, AttributeError) as err:
        return {"status": "missing", "_note": f"{FIG3} lacks Fig. 3's series ({type(err).__name__}: {err})"}
    e = {"status": "informative", "n_compared": sum(1 for r in rows if r["abs_diff"] is not None),
         "n_differ": sum(1 for r in rows if r["abs_diff"]),
         "n_without_counterpart": sum(1 for r in rows if r["abs_diff"] is None), "e11_revision": d.get("git_revision"),
         "_detail": rows}
    per = []
    for panel in ("a", "b", "c"):
        pr = [r for r in rows if r["panel"] == panel and r["abs_diff"] is not None]
        top = max(pr, key=lambda r: r["abs_diff"], default=None)
        nd = sum(1 for r in pr if r["abs_diff"])
        e[f"n_differ_{panel}"] = nd
        e[f"max_abs_diff_{panel}"] = None if top is None else top["abs_diff"]
        e[f"largest_{panel}"] = None if top is None else \
            ("all equal" if not top["abs_diff"] else
             f"{top['key']} {top['field']}" + ("" if top["at"] is None else f" at {top['at']}"))
        diff_fields = sorted({r["field"] for r in pr if r["abs_diff"]})
        per.append(f"({panel}) {nd} of {len(pr)}" + (f" ({', '.join(diff_fields)})" if diff_fields else ""))
    e["_note"] = (f"{e['n_differ']} of {e['n_compared']} compared values differ: {'; '.join(per)}; the figure and "
                  "the text use E11's values (changes under L-co are expected from S11, §3.3)")
    return e


def _e1_1(inp: _Inputs) -> dict:
    S, _ = inp.load(E1_SUM)
    claim = _d(_d(_d(S).get("checks")).get("E1-1")).get("claim")
    P, prob = inp.load(FIG2)
    if P is None:
        e = _absent(FIG2, prob)
        e["_note"] += " (figs/fig2_e1a.py computes E1-1 into data.b.E1_1)"
        return {**e, "claim": claim}
    c = _d(_d(P.get("data")).get("b")).get("E1_1")
    if not isinstance(c, dict):
        return {"status": "missing", "claim": claim, "_note": f"{FIG2} has no data.b.E1_1"}
    e = {k: c.get(k) for k in ("n", "max_rel_err", "tol", "price_ref")}
    e.update(status="pass" if c.get("pass") is True else "fail", claim=claim)
    st = _d(_d(_d(S).get("checks")).get("E1-1")).get("status")
    if S is not None and st != "elsewhere":
        e["_note"] = f"e1/summary.json gives E1-1 the status {st!r}, not 'elsewhere' (§4.6)"
    return e


# ---------------------------------------------------------------- values, verdicts and rows
_MISSING = object()


def _get(obj: Any, path: str) -> Any:
    """A field of a check entry: 'a.b' (nested keys), 'a[*].b' (the list of b over the list a), '#path' (its length),
    'min:path' and 'max:path' (of the finite numbers of a list). _MISSING where a key is absent."""
    for op in ("#", "min:", "max:"):
        if path.startswith(op):
            v = _get(obj, path[len(op):])
            if v is _MISSING or v is None:
                return v
            if op == "#":
                return len(v) if isinstance(v, (list, dict)) else _MISSING
            nums = [x for x in v if isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)]
            return (min(nums) if op == "min:" else max(nums)) if nums else None
    cur = obj
    parts = path.split(".")
    for i, p in enumerate(parts):
        if p.endswith("[*]"):
            lst = cur.get(p[:-3], _MISSING) if isinstance(cur, dict) else _MISSING
            if not isinstance(lst, list):
                return _MISSING
            rest = ".".join(parts[i + 1:])
            return [_none(_get(x, rest)) if rest else x for x in lst]
        if not isinstance(cur, dict) or p not in cur:
            return _MISSING
        cur = cur[p]
    return cur


def _none(v):
    return None if v is _MISSING else v


def _field_name(path: str) -> str:
    for op, name in (("#", "len"), ("min:", "min"), ("max:", "max")):
        if path.startswith(op):
            return f"{name}({path[len(op):]})"
    return path


def _values(entry: dict, fields) -> dict:
    return {_field_name(f): _none(_get(entry, f)) for f in fields}


def verdict(kind: str, status: Optional[str], explainable: bool = False) -> tuple[str, Optional[str]]:
    """(verdict, note) of a check entry's status (§1.4 item 2, §2.6): pass gives reproduced or holds by the row's
    kind (informative rows stay informative), fail gives bug, explained is accepted only where the spec allows it,
    informative only for the rows the spec marks informative, missing and pending stay; any other status is a
    bug."""
    if status == "pass":
        if kind == "informative":
            return "informative", "the summary says pass; the spec marks the row informative"
        return ("reproduced" if kind == "reproduction" else "holds"), None
    if status == "fail":
        return "bug", None
    if status == "explained":
        return ("explained", None) if explainable else ("bug", "status 'explained' where the spec allows no "
                                                                "explanation")
    if status == "informative":
        return ("informative", None) if kind == "informative" else \
            ("bug", "status 'informative' where the spec sets a pass condition")
    if status in ("missing", "pending"):
        return status, None
    if status == "bug_input":
        return "bug", None
    if status == "elsewhere":
        return "bug", "'elsewhere' is allowed only for E1-1 (§4.6)"
    return "bug", f"status {status!r} outside the vocabulary of §2.6"


def _num(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def _e2_5_counterexamples(entry: dict) -> tuple[list, Optional[str]]:
    """The E2-5 MILP records that confirm a counterexample to Claim D2 (the MILP's incumbent below the episode's DP
    value by more than the entry's tolerance, 1e-9 relative, and every rule's verdict 'explained: ...'), and why
    the records do not explain the row (None when every episode below 1 - 1e-9 has such a record: none
    unresolved, no stale job, as many confirmed episodes as candidates)."""
    tol = entry.get("tolerance") if _num(entry.get("tolerance")) else 1e-9
    conf, other = [], []
    for m in entry.get("milp") if isinstance(entry.get("milp"), list) else []:
        m = _d(m)
        dp, inc = m.get("dp"), m.get("incumbent")
        rules = m.get("rules") if isinstance(m.get("rules"), list) else []
        vs = [_d(v).get("verdict") for v in rules]
        ok = (_num(dp) and _num(inc) and inc < dp * (1 - tol) and bool(vs)
              and all(isinstance(v, str) and v.startswith("explained") for v in vs))
        (conf if ok else other).append(m)
    eps = {tuple(_d(m.get("episode")).get(k) for k in ("job", "series", "layer", "f_a")) for m in conf}
    n_cand = entry.get("n_candidates")
    why = []
    if entry.get("unresolved"):
        why.append(f"{len(entry['unresolved'])} episode(s) below 1 - 1e-9 without an E2-5 MILP record (unresolved)")
    if entry.get("ep_milp_stale"):
        why.append(f"{len(entry['ep_milp_stale'])} E2-5 job(s) ran on another candidate list (ep_milp_stale)")
    if other:
        why.append(f"{len(other)} E2-5 MILP record(s) without an incumbent below the DP value or with a verdict "
                   "other than 'explained'")
    if not conf:
        why.append("no E2-5 MILP record confirms a counterexample to Claim D2")
    elif isinstance(n_cand, int) and len(eps) < n_cand:
        why.append(f"{len(eps)} confirmed episode(s) for {n_cand} episode(s) below 1 - 1e-9 (n_candidates)")
    return conf, ("; ".join(why) or None)


def _explanation(spec: Spec, entry: dict) -> tuple[Optional[str], Optional[str]]:
    """(text, None) of an 'explained' row, or (None, why there is none). For E2-5 (the only row the spec lets be
    explained) the text needs the E2-5 MILP records to confirm every episode below 1 - 1e-9 as a counterexample to
    Claim D2 (_e2_5_counterexamples); it is then the summary's `explanation` field if it has one, else those
    records (episode, DP value, MILP incumbent, verdicts)."""
    if spec.id != "E2-5":
        return (str(entry["explanation"]), None) if entry.get("explanation") else \
            (None, "the summary gives no explanation")
    conf, why = _e2_5_counterexamples(entry)
    if why is not None:
        return None, f"not explained: {why}"
    if entry.get("explanation"):
        return str(entry["explanation"]), None
    eps = []
    for m in conf:
        ep = _d(m.get("episode"))
        vs = sorted({_d(v).get("verdict") for v in m.get("rules") or [] if _d(v).get("verdict")})
        eps.append(f"{ep.get('job')} series {ep.get('series')} layer {ep.get('layer')} f_a {ep.get('f_a')}: DP "
                   f"{_fmt(m.get('dp'))}, MILP incumbent {_fmt(m.get('incumbent'))} ({'; '.join(vs)})")
    head = (f"{entry.get('n_below')} per-episode ratios below 1 - 1e-9 (minimum {_fmt(entry.get('min_ratio'))}) in "
            f"{len(conf)} episode(s), each a confirmed counterexample to Claim D2 (CONJECTURE): opt.milp.solve_opt "
            "on it returned an incumbent below the DP value")
    return head + ": " + " | ".join(eps[:10]) + (f" | ... ({len(eps)} in all)" if len(eps) > 10 else ""), None


def _entry_note(entry: dict, status: Optional[str]) -> Optional[str]:
    """Why a summary's check is missing, pending or failed, from its own fields (why, where, pass_note, note, the
    stale note, missing_Hs, and for pending the outstanding lists)."""
    bits = [str(entry[k]) if k in ("why", "pass_note", "note", "ep_milp_stale_note") else f"{k}: {_fmt(entry[k])}"
            for k in ("why", "where", "pass_note", "note", "ep_milp_stale_note", "missing_Hs") if entry.get(k)]
    if status == "pending":
        for k in ("rerun_pending", "unresolved", "ep_milp_stale"):
            if isinstance(entry.get(k), (list, dict)) and entry[k]:
                bits.append(f"{k}: {len(entry[k])}")
    return "; ".join(bits) or None


def _reduced(S: Any) -> bool:
    """Whether a summary comes from a reduced (smoke) run: meta.reduced true (the drivers' --reduced lists)."""
    return _d(_d(S).get("meta")).get("reduced") is True


def build_row(spec: Spec, inp: _Inputs) -> dict:
    """One row of the report for `spec` (module docstring, rows[])."""
    src = spec.summary
    if spec.compute is not None:
        entry = spec.compute(inp)
    else:
        S, prob = inp.load(src)
        if S is None:
            entry = _absent(src, prob)
        elif "checks" in S and not isinstance(S["checks"], dict):
            entry = {"status": "bug_input", "_note": f"{src}: checks is not an object"}
        else:
            entry = _d(S.get("checks")).get(spec.id)
            if not isinstance(entry, dict):
                entry = {"status": "missing", "_note": f"no entry checks.{spec.id} in {src}"}
            if _reduced(S):
                entry = {**entry, "_reduced": True}
    status = entry.get("status")
    reg_file = spec.regenerated_file or (f"{src} checks.{spec.id}" if src else None)
    v, vnote = verdict(spec.kind, status, spec.explainable)
    expl, why_not = _explanation(spec, entry) if v == "explained" else (None, None)
    notes = [x for x in (entry.get("_note"), vnote, why_not) if x]
    if spec.compute is None and status in ("missing", "pending", "fail"):
        n = _entry_note(entry, status)
        if n:
            notes.append(n)
    if status == "fail" and not notes:
        notes.append(f"the summary's status is 'fail' (see {reg_file})")
    if status in ("missing", "pending") and not notes:
        notes.append("the summary gives no reason")
    if entry.get("_reduced"):
        v, expl = "bug", None
        notes.insert(0, f"{src} is from a reduced run (meta.reduced true; smoke), never a result")
    ref_values = {**_values(entry, spec.ref_fields), **(entry.get("_ref_values") or {})}
    row = {"id": spec.id, "experiment": spec.exp, "section": spec.section, "kind": spec.kind,
           "claim": {"spec": spec.claim, "summary": entry.get("claim")},
           "status_label": spec.label, "status_label_note": spec.label_note if spec.label is None else None,
           "reference": {"value": spec.reference, "values": ref_values,
                         "file": entry.get("_ref_file") or spec.reference_file},
           "regenerated": {"value": _values(entry, spec.fields), "file": reg_file},
           "summary_status": None if status == "bug_input" else status, "verdict": v, "explanation": expl,
           "note": "; ".join(notes) or None}
    if "_detail" in entry:
        row["detail"] = entry["_detail"]
    return row


def _row_or_bug(spec: Spec, inp: _Inputs) -> dict:
    """build_row, or, where an input has a shape the drivers never write (§2.6) and reading it raises, a 'bug' row
    that names the error, so that the report is still written."""
    try:
        return build_row(spec, inp)
    except Exception as err:
        return {"id": spec.id, "experiment": spec.exp, "section": spec.section, "kind": spec.kind,
                "claim": {"spec": spec.claim, "summary": None}, "status_label": spec.label,
                "status_label_note": spec.label_note if spec.label is None else None,
                "reference": {"value": spec.reference, "values": {}, "file": spec.reference_file},
                "regenerated": {"value": {}, "file": spec.regenerated_file or spec.summary},
                "summary_status": None, "verdict": "bug", "explanation": None,
                "note": f"the row's input has a shape the drivers do not write ({type(err).__name__}: {err})"[:300]}


def criterion(rows: list) -> dict:
    """§1.4 item 2: holds iff no row is 'bug' and every row other than reproduced, holds and informative is
    'explained' with its text."""
    ids = {v: [r["id"] for r in rows if r["verdict"] == v] for v in VERDICTS}
    unexplained = [r["id"] for r in rows if r["verdict"] not in OK_VERDICTS
                   and not (r["verdict"] == "explained" and r["explanation"])]
    holds = not ids["bug"] and not unexplained
    if holds:
        reasons = (f"No row is a bug, and every row is reproduced, holds, informative or explained "
                   f"({len(ids['explained'])} explained)")
    else:
        parts = []
        if ids["bug"]:
            parts.append(f"{len(ids['bug'])} bug row(s) ({', '.join(ids['bug'])})")
        for v in ("missing", "pending"):
            if ids[v]:
                parts.append(f"{len(ids[v])} {v} row(s) ({', '.join(ids[v])})")
        other = [i for i in unexplained if i not in ids["missing"] + ids["pending"] + ids["bug"]]
        if other:
            parts.append(f"{len(other)} explained row(s) without a text ({', '.join(other)})")
        reasons = "; ".join(parts)
        if ids["missing"] or ids["pending"]:
            reasons += ("; a missing or pending row has no explanation, so the criterion cannot hold until its "
                        "output exists")
        reasons = reasons[0].upper() + reasons[1:]
    text = ("holds: " if holds else "does not hold: ") + reasons[0].lower() + reasons[1:]
    return {"holds": holds, "text": text, "reasons": reasons, "n_rows": len(rows),
            "counts": {v: len(ids[v]) for v in VERDICTS},
            "bug": ids["bug"], "missing": ids["missing"], "pending": ids["pending"], "explained": ids["explained"],
            "unexplained": unexplained}


# ---------------------------------------------------------------- floats, copy checks
def floats_block(inp: _Inputs) -> dict:
    """§1.4 item 5: the measured heights of Tables I, II and Algorithm 1 next to their budgets (floats_heights.json)."""
    F, prob = inp.load(FLOATS)
    out = {"file": FLOATS, "present": F is not None, "rows": []}
    if F is None:
        out["note"] = f"{FLOATS} {prob} (paper/layout_check/pageplan/floats_heights.py writes it)"
        return out
    for k, v in (F.get("floats") or {}).items():
        out["rows"].append({"float": FLOAT_NAMES.get(k, k), "name": k, **{f: v.get(f) for f in (
            "measured_pages", "budget_pages", "within_budget", "difference_pages", "source")}})
    over = [r["float"] for r in out["rows"] if r["within_budget"] is False]
    out["note"] = (f"{len(over)} of {len(out['rows'])} floats exceed their budget ({', '.join(over)}); recorded, no "
                   "float trimmed (decision of 2026-10-20, §9)") if over else "every float within its budget"
    return out


def copy_block(inp: _Inputs) -> dict:
    """The copy records: E11-0's (ms3_e11_0.json) and each experiment's out/ms3_copy_<exp>.json (§1.2), with the
    job records counted by status (records_by_status, null for E11)."""
    out = {}
    for exp in ("e11",) + COPY_EXPS:
        rel = E11_0 if exp == "e11" else f"{OUT}/{mc.COPY_RECORD.format(exp=exp)}"
        rec, prob = inp.load(rel)
        e = {"file": rel, "present": rec is not None, "pass": None, "commit": None, "time": None, "failed": [],
             "records_by_status": None}
        if rec is not None:
            e.update(**{"pass": rec.get("pass") is True, "time": rec.get("time"),
                        "commit": rec.get("manifest_git_revision") if exp == "e11" else rec.get("clone_commit"),
                        "failed": [k for k, v in _d(rec.get("checks")).items() if not v],
                        "records_by_status": None if exp == "e11" else rec.get("records_by_status")})
        elif prob != "missing":
            e["note"] = prob
        out[exp] = e
    return out


# ---------------------------------------------------------------- the job records (§2.4)
JOB_FOLDERS = ("e1", "e10", "e2", "e6/a", "e6/b")     # the experiment folders with a job list (manifest.json)
MILP_LP_FALLBACK = ("wall_limit", "oom_at_3G")        # a MILP job whose LB is the LP (Q39's rule, mc.lb_record)
JOBS_LIST_MAX = 50


def _job_statuses(top: Path) -> tuple[dict, int]:
    """{job id: status} of the job records jobs/*.json under `top`, and the number of records that are not a JSON
    object with a string 'job' (counted, not keyed)."""
    st, bad = {}, 0
    d = top / "jobs"
    for p in sorted(d.glob("*.json")) if d.is_dir() else []:
        try:
            r = json.loads(p.read_bytes()) if p.is_file() else None
        except (OSError, ValueError, RecursionError):
            r = None
        if isinstance(r, dict) and isinstance(r.get("job"), str):
            v = r.get("status")
            st[r["job"]] = v if isinstance(v, str) else f"<{v!r}>"[:40]
        else:
            bad += 1
    return st, bad


def jobs_block(inp: _Inputs) -> dict:
    """Every listed job of each experiment folder (manifest.json `jobs`, plus the records '<exp>:manifest' and
    '<exp>:summary') against its record jobs/<id>.json (§2.4: only 'ok' counts as done): the jobs by status ('no
    record' where the record is absent), the jobs without an 'ok' record outside Q39's rule ('blocking'), the MILP
    jobs whose LB falls back to the LP under that rule (status wall_limit or oom_at_3G, §2.5), and the summary's own
    lists of missing jobs and ignored outputs (meta.jobs_missing of E2 and E6, meta.ignored_outputs of E1 and E10).
    A summary built from a partial job set still marks its checks over the runs that exist, so this block, not
    the rows, shows such jobs; test_ms3_out.py fails on a blocking job."""
    rows = {}
    for part in JOB_FOLDERS:
        exp = part.split("/")[0]
        man_rel, sum_rel = f"{OUT}/{part}/manifest.json", f"{OUT}/{part}/summary.json"
        M, prob = inp.load(man_rel)
        e = {"manifest": man_rel, "present": M is not None, "n_listed": None, "by_status": {}, "n_blocking": None,
             "blocking": [], "n_milp_lp_fallback": None, "milp_lp_fallback": [], "n_unlisted_records": None,
             "n_unreadable_records": None, "summary_jobs_missing": None, "summary_ignored_outputs": None}
        if M is None:
            e["note"] = f"{man_rel} {prob}"
            rows[part] = e
            continue
        jobs = M.get("jobs") if isinstance(M.get("jobs"), list) else []
        listed = [(_d(j).get("id"), _d(j).get("kind")) for j in jobs]
        listed += [(mc.job_id(exp, "manifest"), "pool"), (mc.job_id(exp, "summary"), "pool")]
        recs, bad = _job_statuses(inp.root / OUT / part)
        by_status: dict = {}
        blocking, fallback = [], []
        for jid, kind in listed:
            st = recs.get(jid, "no record") if isinstance(jid, str) else "no job id"
            by_status[st] = by_status.get(st, 0) + 1
            if st == "ok":
                continue
            item = {"job": jid, "kind": kind, "status": st}
            (fallback if kind == "milp" and st in MILP_LP_FALLBACK else blocking).append(item)
        ids = {j for j, _ in listed}
        S, _ = inp.load(sum_rel)
        meta = _d(_d(S).get("meta"))
        e.update(n_listed=len(listed) - 2, by_status=dict(sorted(by_status.items())), n_blocking=len(blocking),
                 blocking=blocking[:JOBS_LIST_MAX], n_milp_lp_fallback=len(fallback),
                 milp_lp_fallback=fallback[:JOBS_LIST_MAX], n_unlisted_records=sum(1 for j in recs if j not in ids),
                 n_unreadable_records=bad,
                 summary_jobs_missing=len(meta["jobs_missing"]) if isinstance(meta.get("jobs_missing"), list)
                 else None,
                 summary_ignored_outputs=len(meta["ignored_outputs"]) if isinstance(meta.get("ignored_outputs"), list)
                 else None)
        rows[part] = e
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
_NAME_RE = re.compile(r'^NAME = "([^"]+)"', re.M)

# MS4 addition C17 (design/sim_spec_ms4.md §2.3): the 20 MS3 figure scripts (relative to code/sim), the six
# main-text scripts and the 14 supplementary scripts of design/sim_spec_ms3.md §8.7, each group in path order, so
# that the MS3 report keeps its rows when the MS4 scripts (figs/fig4_e7_e3.py, the MS4 figs/supp/sf_*.py) exist
MS3_FIGURE_SCRIPTS = (
    "figs/fig1_guard.py", "figs/fig2_e1a.py", "figs/fig3_e11.py", "figs/fig5_e1_e10.py", "figs/fig6_e10.py",
    "figs/fig7_e2_e6.py",
    "figs/supp/sf_e10_cross.py", "figs/supp/sf_e10_rho.py", "figs/supp/sf_e10b.py", "figs/supp/sf_e11_fam.py",
    "figs/supp/sf_e11_guard.py", "figs/supp/sf_e11_inst.py", "figs/supp/sf_e1_rotation.py",
    "figs/supp/sf_e1_sched.py", "figs/supp/sf_e2_mu_cost.py", "figs/supp/sf_e2_mu_ep.py", "figs/supp/sf_e2_pool.py",
    "figs/supp/sf_e2_por.py", "figs/supp/sf_e6a.py", "figs/supp/sf_e6b.py",
)


def figure_scripts() -> list[tuple[str, str, str]]:
    """(figure name, module, script path relative to code/sim) of the 20 MS3 figure scripts MS3_FIGURE_SCRIPTS
    (C17), main-text figures first, each group in path order; the name is the script's NAME."""
    out = []
    for rel in MS3_FIGURE_SCRIPTS:
        p = paths.SIM / rel
        module = rel[:-len(".py")].replace("/", ".")
        m = _NAME_RE.search(p.read_text(encoding="utf-8"))
        name = m.group(1) if m else getattr(_figs_import(module), "NAME")
        out.append((name, module, rel))
    return out


def _under(p, top: Path) -> bool:
    try:
        Path(p).resolve().relative_to(top.resolve())
        return True
    except ValueError:
        return False


def _script_min_pt() -> float:
    """figs.style.SCRIPT_MIN_PT (the smallest glyph finalize() accepts without a warning), imported when needed."""
    return float(_figs_import("figs.style").SCRIPT_MIN_PT)


def _text_min_pt() -> float:
    """figs.style.TEXT_MIN_PT (the smallest figure text; 9 pt until C62, 7 pt since), imported when needed."""
    return float(_figs_import("figs.style").TEXT_MIN_PT)


def figures_block(root: Path, extracts: Path, only=None) -> dict:
    """Rerun every figure script (or those named in `only`) with --from-extract <extracts>/<name>.json in this
    process, all outputs in a temporary folder that is removed afterwards, and list each figure's small_glyphs from
    the report of figs.common.cli (module docstring)."""
    scripts = figure_scripts()
    if only:
        unknown = sorted(set(only) - {n for n, _, _ in scripts})
        if unknown:
            raise ValueError(f"no figure script named {unknown} (known: {[n for n, _, _ in scripts]})")
        scripts = [s for s in scripts if s[0] in set(only)]
    rows = []
    tmp = Path(tempfile.mkdtemp(prefix="ms3_claims_figs_"))
    keys = ENV_FIG_DIRS + (ENV_IN_ROOT,)
    saved = {k: os.environ.get(k) for k in keys}
    try:
        for k, sub in zip(ENV_FIG_DIRS, ("pdf", "out", "tables")):
            os.environ[k] = str(tmp / sub)
        os.environ[ENV_IN_ROOT] = str(root)
        _figs_import("figs.style")              # the figure style (and its matplotlib setup) before pyplot
        import matplotlib.pyplot as plt
        for name, module, script in scripts:
            ext = Path(extracts) / f"{name}.json"
            r = {"figure": name, "script": script, "extract": str(ext), "status": "missing", "small_glyphs": [],
                 "n_small_glyphs": 0, "n_glyph_warnings": 0, "min_glyph_pt": None, "text_pt": None, "error": None}
            rows.append(r)
            if not ext.is_file():
                continue
            buf = io.StringIO()
            try:
                with warnings.catch_warnings(record=True) as caught, contextlib.redirect_stdout(buf):
                    warnings.simplefilter("always")
                    rep = _figs_import(module).main(["--from-extract", str(ext)])
                outside = [p for p in (rep.get("pdf"), rep.get("json")) if p and not _under(p, tmp)]
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


# ---------------------------------------------------------------- the report
def build(root=None, *, figures: bool = True, only=None, extracts=None) -> dict:
    """The report (module docstring, ms3_claims.json) from the files under the input root."""
    root = Path(root).resolve() if root is not None else _default_root()
    inp = _Inputs(root)
    rows = [_row_or_bug(s, inp) for s in SPECS]
    crit = criterion(rows)
    fl = floats_block(inp)
    cp = copy_block(inp)
    jb = jobs_block(inp)
    ex = Path(extracts).resolve() if extracts is not None else root / OUT / "figs"
    fg = figures_block(root, ex, only) if figures else \
        {"run": False, "extracts": str(ex), "rows": [], "counts": {}, "note": "not run (--no-figures)"}
    meta = {"module": "sublet.experiments.ms3_claims", "spec": f"{SPEC_DOC} §1.4", "git_revision": mc.git_revision(),
            "written": mc._now(), "input_root": str(root), "input_root_is_repository": _is_repo(root),
            "inputs": dict(sorted(inp.status.items()))}
    return {"meta": meta, "criterion": crit, "rows": rows, "floats": fl, "figures": fg, "copy_checks": cp,
            "jobs": jb}


def _default_root() -> Path:
    env = os.environ.get(ENV_IN_ROOT)
    return Path(env).resolve() if env else paths.REPO.resolve()


def _is_repo(root: Path) -> bool:
    return Path(root).resolve() == paths.REPO.resolve()


def _fmt(v, digits: int = 6) -> str:
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, float):
        return f"{v:.{digits}g}"
    if isinstance(v, list):
        inner = ", ".join(_fmt(x, digits) for x in v[:8])
        return f"[{inner}{', ...' if len(v) > 8 else ''}]"
    if isinstance(v, dict):
        return "{" + ", ".join(f"{k}: {_fmt(x, digits)}" for k, x in v.items()) + "}"
    return str(v)


def _kv(d: dict) -> str:
    """'k v; k v' of a value dict; '' when every value is null (a missing row)."""
    if all(v is None for v in d.values()):
        return ""
    return "; ".join(f"{k} {_fmt(v)}" for k, v in d.items())


def _cell(s: str) -> str:
    return str(s).replace("|", "\\|").replace("\n", " ")


def _glyph(g) -> str:
    size, text = (list(g) + [None, None])[:2]
    return f"{_fmt(size, 3)} pt `{str(text).replace('`', chr(39))}`"


def markdown(rep: dict) -> str:
    """ms3_claims.md: the head (the criterion, figures, floats, copy checks), the claims tables per experiment with
    their notes, the floats, the figures' small glyphs and the copy checks."""
    m, c = rep["meta"], rep["criterion"]
    L = ["# MS3 claims report (design/sim_spec_ms3.md §1.4)", ""]
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
                 f"{n_small} figure(s) with mathtext glyphs below {_script_min_pt():g} pt, i.e. below a first-level "
                 f"script of {_text_min_pt():g}-pt text (listed below; plan §5 allows first-level scripts).")
    else:
        L.append("Figures (§1.4 item 1): not rerun (--no-figures).")
    L.append("")
    fl = rep["floats"]
    if fl["present"]:
        L.append("Floats (§1.4 item 5): " + "; ".join(
            f"{r['float']} {_fmt(r['measured_pages'], 4)} page (budget {_fmt(r['budget_pages'], 4)})"
            for r in fl["rows"]) + f" ({fl['note']}).")
    else:
        L.append(f"Floats (§1.4 item 5): {fl['note']}.")
    L.append("")
    L.append("Copy checks: " + "; ".join(
        f"{exp} {('pass' if e['pass'] else 'FAIL') if e['present'] else 'no record'}"
        for exp, e in rep["copy_checks"].items()) + ".")
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
            kv = _kv(r["reference"]["values"])
            ref = r["reference"]["value"] + (f" ({kv})" if kv else "")
            body.append([r["id"], r["claim"]["spec"], lab, f"{ref}; `{r['reference']['file']}`",
                         f"{_kv(r['regenerated']['value']) or '–'}; `{r['regenerated']['file']}`",
                         f"**{r['verdict']}**"])
        L.append("| Check | Claim | Status label | Reference (file) | Regenerated (file) | Verdict |")
        L.append("|---|---|---|---|---|---|")
        L += ["| " + " | ".join(_cell(x) for x in row) + " |" for row in body]
        L.append("")
        notes = [r for r in rs if r["explanation"] or r["note"] or
                 (r["claim"]["summary"] and r["claim"]["summary"] != r["claim"]["spec"])]
        if notes:
            for r in notes:
                bits = []
                if r["explanation"]:
                    bits.append(f"explained: {r['explanation']}")
                if r["note"]:
                    bits.append(r["note"])
                if r["claim"]["summary"]:
                    bits.append(f"the summary's claim: {r['claim']['summary']}")
                L.append(f"- {r['id']}: " + ". ".join(bits))
            L.append("")
    L.append("## Floats (§1.4 item 5)")
    L.append("")
    if fl["present"]:
        L.append(mc.md_table(["Float", "Measured (page)", "Budget (page)", "Within budget", "Difference (page)",
                              "Source"],
                             [[r["float"], r["measured_pages"], r["budget_pages"], _fmt(r["within_budget"]),
                               r["difference_pages"], f"`{r['source']}`"] for r in fl["rows"]]))
        L.append(f"From `{fl['file']}`; {fl['note']}.")
    else:
        L.append(f"{fl['note']}.")
    L.append("")
    L.append("## Figures: small glyphs (§1.4 item 1)")
    L.append("")
    if fg["run"]:
        L.append(f"| Figure | Script | Status | Small glyphs | Glyphs below {_script_min_pt():g} pt (size, text) |")
        L.append("|---|---|---|---|---|")
        for r in fg["rows"]:
            what = ", ".join(_glyph(g) for g in r["small_glyphs"]) if r["status"] == "ok" else \
                (r["error"] or f"extract `{r['extract']}` missing")
            L.append("| " + " | ".join(_cell(x) for x in (r["figure"], f"`{r['script']}`", r["status"],
                                                           r["n_small_glyphs"] if r["status"] == "ok" else "–",
                                                           what or "none")) + " |")
        L.append("")
        L.append(f"{fg['note']}; extracts from `{fg['extracts']}`.")
    else:
        L.append(f"{fg['note']}.")
    L.append("")
    L.append("## Copy checks (§1.2, §3.2 step 1)")
    L.append("")
    L.append(mc.md_table(["Experiment", "Record", "Present", "Pass", "Commit", "Time", "Failed checks"],
                         [[exp, f"`{e['file']}`", _fmt(e["present"]), _fmt(e["pass"]), e["commit"], e["time"],
                           ", ".join(e["failed"]) or "–"] for exp, e in rep["copy_checks"].items()]).rstrip("\n"))
    L.append("")
    L.append("## Jobs (§2.4, §2.5)")
    L.append("")
    L.append(mc.md_table(["Folder", "Job list", "Listed", "Records by status", "Without 'ok' (blocking)",
                          "MILP, LB = LP (Q39)", "Summary: jobs_missing, ignored_outputs"],
                         [[k, f"`{r['manifest']}`", r["n_listed"], _fmt(r["by_status"]) if r["present"] else "–",
                           r["n_blocking"], r["n_milp_lp_fallback"],
                           f"{_fmt(r['summary_jobs_missing'])}, {_fmt(r['summary_ignored_outputs'])}"]
                          for k, r in jb["rows"].items()]).rstrip("\n"))
    L.append("")
    L.append(f"{jb['note'][0].upper() + jb['note'][1:]}. The jobs without an 'ok' record outside Q39's MILP rule are "
             f"listed below, at most {JOBS_LIST_MAX} per folder; a MILP job stopped at the wall-clock limit or by the "
             "cap leaves the LP as its LB (§2.5).")
    for k, r in jb["rows"].items():
        if r["blocking"]:
            L.append("")
            L.append(f"- {k}: " + "; ".join(f"`{x['job']}` ({x['kind']}, {x['status']})" for x in r["blocking"])
                     + (f"; ... ({r['n_blocking']} in all)" if r["n_blocking"] > len(r["blocking"]) else ""))
    return "\n".join(L) + "\n"


def write(rep: dict, out_dir) -> tuple[Path, Path]:
    out = Path(out_dir)
    rep["meta"]["out_dir"] = str(out.resolve())
    pj = mc.dump_json(rep, out / OUT_JSON)
    pm = mc.write_text(markdown(rep), out / OUT_MD)
    return pm, pj


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m sublet.experiments.ms3_claims",
                                 description=__doc__.strip().split("\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", type=Path, default=None,
                    help=f"input root with the repository's layout (default {ENV_IN_ROOT}, else the repository)")
    ap.add_argument("--out-dir", type=Path, default=None,
                    help="folder of ms3_claims.md and .json (default the repository's code/sim/out when the root is "
                         "the repository; required otherwise)")
    ap.add_argument("--no-figures", action="store_true", help="skip the figure reruns")
    ap.add_argument("--only", nargs="+", metavar="NAME", default=None, help="rerun only these figures")
    ap.add_argument("--extracts", type=Path, default=None,
                    help="folder of the figure extracts <name>.json (default <root>/code/sim/out/figs)")
    a = ap.parse_args(argv)
    root = a.root.resolve() if a.root is not None else _default_root()
    if a.out_dir is None:
        if not _is_repo(root):
            ap.error(f"--out-dir is required when the input root ({root}) is not the repository")
        a.out_dir = paths.SIM_OUT
    rep = build(root, figures=not a.no_figures, only=a.only, extracts=a.extracts)
    pm, pj = write(rep, a.out_dir)
    c, fg = rep["criterion"], rep["figures"]
    figs = (", ".join(f"{k} {v}" for k, v in fg["counts"].items()) if fg["run"] else "not run")
    print(f"[ms3_claims] wrote {pm} and {pj}: criterion {'holds' if c['holds'] else 'does not hold'} ("
          + ", ".join(f"{v} {n}" for v, n in c["counts"].items() if n) + f"); figures: {figs}", flush=True)
    return 0


SPECS = _rows_spec()

if __name__ == "__main__":
    sys.exit(main())
