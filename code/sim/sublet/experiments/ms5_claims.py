"""The MS5 claims report (design/sim_spec_ms5.md §1.4 items 1, 2 and 5, §9; deliverable D44, unit U30; open choice
M34).

Reads the MS5 summaries and records under an input root and writes the report code/sim/out/ms5_claims.md and
ms5_claims.json, on the model of ms4_claims (whose helpers, and ms3_claims', it uses): one row per check of §3.10 (S1,
part sweep), §4.7 (Q28, part q28), §5.9 (E9), §6.3 (the slack series) and §8.4 (the frozen rebuild), 16 rows in the
spec's order, with the check id, the claim (the spec row and the summary's `claim` field), the design's status label
for the claim it tests (copied, never upgraded; null where the check tests no theory claim, with what it tests), the
reference value and file, the regenerated value and file, and the verdict; then the small glyphs of the three MS5
figures (§1.4 item 1), the copy records of s1 and e9, the job records of out/s1/sweep/, out/s1/q28/ and out/e9/
against their job lists, the rebuild record, and the caption drafts of the three figures from their extracts.

  python -m sublet.experiments.ms5_claims [--root DIR] [--out-dir DIR] [--no-figures] [--only NAME ...]
                                          [--extracts DIR]

  --root DIR      the input root, a folder with the repository's layout (code/sim/out/s1/sweep/summary.json, ...):
                  default SUBLET_FIGS_IN_ROOT (the variable of figs.inputs), else the repository; the tests pass
                  copies of the MS5 fixture tree tests/fixtures_figs_ms5/inputs/
  --out-dir DIR   where ms5_claims.md and ms5_claims.json go: default the repository's code/sim/out when the root is
                  the repository; required with any other root
  --no-figures    skip the figure reruns (the 'figures' block says so)
  --only NAME     rerun only these figures (sf_e9, sf_s1, sf_slack)
  --extracts DIR  the folder of the figure extracts <name>.json (default <root>/code/sim/out/figs)

Run from code/sim in the 3 GB scope. Exit 0 once the report is written, whatever its verdicts.

Rows and verdicts. The S1, Q28 and E9 rows read checks.<id> of code/sim/out/s1/sweep/summary.json,
code/sim/out/s1/q28/summary.json and code/sim/out/e9/summary.json, whose `status` is one of MS4 spec §2.6's: pass,
fail, missing, pending, explained, informative. Three rows are computed here:
  E9-4  as amended on 2026-10-30 (design/sim_spec_ms5.md §5.9): from checks.E9-4 of E9's summary, whose own status
        counts an LP that M18's memory gate skipped as a failure, the LPs whose only problem is the gate are listed
        as gated and do not fail the row; it holds iff no LP job failed or is missing and every other LP was solved to
        optimality inside the cap; a reduced E9 summary makes it a bug;
  SL-1  from code/sim/out/figs/sf_slack.json and the three analysis outputs it names: the extract's daily minimum,
        mean and maximum of every pool against this report's own recomputation from
        code/analysis/out/a1_slack_series.npz (the slot length a9b_notice_buffer_24h.json's meta.slot_min; the
        trace's end left out from the one slot at which every pool's slack rises by at least half its capacity at
        once, a1_lender_spotgpu.json's capacities; days of 1440 / slot_min slots, the last day the remaining slots;
        within 1e-9), its pools, slot, kept-slot and day counts and the end's first slot against the recomputation's,
        and its source digests against the sha256 of the files under the root (§6.3);
  RB-1  from code/sim/out/figs/rebuild.json, the record of code/sim/figs/run_all.sh (figs/rebuild.py): status pass,
        mode check, ONLY unset, run at the root of the repository it rebuilt with no tracked file changed (the clean
        clone of §1.4 item 5), the coverage holding (no file without its entry, no entry without its file), every
        output identical, both float-height measurements equal on every key but 'written', every hand-set file
        unchanged; and the record current: every output's versioned sha256 in the record equals the sha256 of that
        file under the root now (a figure rewritten after the exit run makes the record stale, a bug) (§8.4).
Verdicts (§1.4 item 2):
  reproduced   status pass of the check that reproduces an earlier value (S1-0, E7's twelve runs)
  holds        status pass of a property check
  bug          status fail; also a status outside §2.6's vocabulary, 'explained' (no check of §3.10, §4.7, §5.9,
               §6.3 or §8.4 allows an explanation: their verdict rules are "or bug" or "informative"), 'informative'
               where the spec sets a pass condition, an input that is not a JSON object, and every row of a summary
               whose meta.reduced is true (a smoke run, never a result)
  explained    never in MS5 (kept for the vocabulary)
  informative  S1-4, Q28-4 and E9-5 (they report a value and have no pass condition)
  missing      the check's output, summary or record is absent (or the summary says missing)
  pending      the summary says pending
The informative rows carry the spec's reading as their note (`remark`). Nothing is computed for the S1, Q28 and E9
rows but E9-4: every value is read.

Criterion (§1.4 item 2): it holds iff every row is reproduced, holds or informative (no MS5 row may be explained); a
missing or pending row keeps it from holding until its output exists. The job records (jobs_block) do not enter it:
the report's head lists the jobs without an 'ok' record, and tests/test_ms5_out.py fails on them (§1.4 item 3).

Figures (§1.4 item 1): the three MS5 figure scripts (MS5_FIGURE_SCRIPTS) are rerun in this process with
--from-extract <extracts>/<name>.json by ms4_claims.figures_block, every output (PDF, extract, preview and the tables
of sf_s1 and sf_e9) in a temporary folder that is removed afterwards; each figure's small_glyphs ([size, text] of every
mathtext text with glyphs below style.SCRIPT_MIN_PT, 6.3 pt) come from the report of figs.common.cli.

Output schema of ms5_claims.json (key paths; the .md shows the same content as tables):
  meta.module, meta.spec, meta.git_revision, meta.written, meta.input_root, meta.input_root_is_repository,
  meta.out_dir, meta.inputs.<repository-relative name>   'ok' | 'missing' | 'invalid JSON: ...' (files read)
  criterion.holds, criterion.text, criterion.reasons, criterion.n_rows, criterion.counts.<verdict>,
  criterion.bug, criterion.missing, criterion.pending, criterion.explained, criterion.unexplained   (ms3_claims')
  rows[]   one per check, in the order of SPECS: id, experiment ('S1', 'Q28', 'E9', 'SL', 'RB'), section ('§3.10',
           '§4.7', '§5.9', '§6.3', '§8.4'), kind ('reproduction' | 'property' | 'informative'), claim.spec,
           claim.summary, status_label, status_label_note, reference.value, reference.values {path: value},
           reference.file, regenerated.value {path: value} (fields of the check entry, paths as ms4_claims._get),
           regenerated.file, summary_status, verdict, explanation (null in MS5), note
  figures.run, figures.extracts, figures.rows[] {figure, script, extract, status ('ok' | 'missing' | 'error'),
           small_glyphs, n_small_glyphs, n_glyph_warnings, min_glyph_pt, text_pt, error}, figures.counts, figures.note
  copy_checks.records.<exp> for exp in s1, e9: file, present, pass, exp_matches, commit (the clone's commit), time,
           failed, parts, records_by_status; copy_checks.commits, copy_checks.one_commit, copy_checks.note
  jobs.rows.<folder> for folder in s1/sweep, s1/q28, e9: manifest, present, n_listed, by_status, n_blocking,
           blocking [{job, kind, status}] (at most 50), n_unlisted_records, n_unreadable_records,
           summary_jobs_missing, summary_ignored_outputs; jobs.n_blocking, jobs.note
  rebuild  file, present, status, pass, mode, only, git_revision, tracked_files_dirty, root_is_repository, written,
           versions, fonts, n_scripts, n_outputs, n_identical, different, not_written, unlisted, missing,
           heights_equal, hand_set_ok, note
  captions.<figure> for sf_s1, sf_e9, sf_slack: text (the extract's labels.caption), n_chars, reduced, source, notes
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

import numpy as np

from .. import paths
from . import ms3_claims as m3
from . import ms3_common as mc
from . import ms4_claims as m4c

SPEC_DOC = "design/sim_spec_ms5.md"
OUT_MD, OUT_JSON = "ms5_claims.md", "ms5_claims.json"
ENV_IN_ROOT = m3.ENV_IN_ROOT

OUT = "code/sim/out"
SWEEP_SUM, Q28_SUM, E9_SUM = f"{OUT}/s1/sweep/summary.json", f"{OUT}/s1/q28/summary.json", f"{OUT}/e9/summary.json"
SLACK_EXTRACT = f"{OUT}/figs/sf_slack.json"
SLACK_NPZ, SLACK_JSON = "code/analysis/out/a1_slack_series.npz", "code/analysis/out/a1_lender_spotgpu.json"
SLACK_A9B = "code/analysis/out/a9b_notice_buffer_24h.json"     # meta.slot_min: the slot of the slack series (§6.1)
SLACK_TAIL_RISE = 0.5                                 # the trace's end (§6.2): every pool rises by half its capacity
SL1_TOL = 1e-9                                        # §6.3
REBUILD = f"{OUT}/figs/rebuild.json"                  # figs/rebuild.py's record (§8.3), copied after the exit run
COPY_EXPS = ("s1", "e9")
JOB_FOLDERS = ("s1/sweep", "s1/q28", "e9")            # §3.8, §4.6, §5.7
VERDICTS, OK_VERDICTS = m3.VERDICTS, m3.OK_VERDICTS
W_AB = m3.W_AB      # "Theorem W(a)(b) (PROVEN for the engine as implemented under C1-C3, audited); W(c) (CONJECTURE)"
SECTIONS = "§3.10, §4.7, §5.9, §6.3 or §8.4"

# the MS5 figure scripts (relative to code/sim) with their names (style.save's), in path order; the names are those
# of style.SUPP_POLICIES_MS5 (tests/test_ms5_claims.py checks this)
MS5_FIGURE_SCRIPTS = (("sf_e9", "figs/supp/sf_e9.py"), ("sf_s1", "figs/supp/sf_s1.py"),
                      ("sf_slack", "figs/supp/sf_slack.py"))


# ---------------------------------------------------------------- the rows (the spec's tables)
@dataclass(frozen=True)
class Spec:
    """One check of §3.10-§8.4 (as ms4_claims.Spec): id, experiment, section, kind, the spec row's content, the
    design's status label (None: then `label_note` says what the check tests), the summary it reads, the reference
    (the spec's text and the file), the entry's fields shown as the regenerated and the reference values, the
    regenerated value's file, whether the spec allows 'explained' (no MS5 check does), the informative rows' remark,
    and for a computed row the function that builds its entry from the inputs."""
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
    remark: Optional[str] = None
    compute: Optional[Callable] = None


def _rows_spec() -> tuple:
    guard = "code/sim/sublet/algos/guard.py (Theorem W, module docstring); design/Sublet_design.md §2.9"
    s1 = dict(exp="S1", section="§3.10", summary=SWEEP_SUM)
    q28 = dict(exp="Q28", section="§4.7", summary=Q28_SUM)
    e9 = dict(exp="E9", section="§5.9", summary=E9_SUM)
    cert = ("n_runs", "certificates.n", "certificates.held", "n_unavailable", "n_failures", "n_w_c")
    return (
        # §3.10 S1, part sweep
        Spec("S1-0", kind="reproduction", **s1,
             claim="the default point's twelve runs equal E7's (out/e7/main/summary.json runs.1.Sublet: median, p95, "
                   "max and mean of overflow_usd within 1e-9 relative, and the instance hashes of meta.instances "
                   "equal)", label=None, label_note="the identity of S1's default point with E7's runs (M1)",
             reference="E7's runs.1.Sublet overflow_usd (median, p95, max, mean) within 1e-9 relative; the instance "
                       "hashes of meta.instances", reference_file=f"{OUT}/e7/main/summary.json",
             fields=("n_runs", "n_runs_equal", "max:overflow_usd.*.rel_diff", "stats_differ", "hashes_differ",
                     "hashes_missing"),
             ref_fields=("tolerance", "overflow_usd.median.e7")),
        Spec("S1-1", kind="property", **s1,
             claim="every point is built as §3.4 states: its instance hash differs from the default's, the demand, "
                   "compared client by client, and BL0a equal the default's exactly on the rows without Gamma, the "
                   "points with g^lay 16 have every LLM on a fitting site, and every LLM but S at sS0 has clients",
             label=None, label_note="the build of the points (§3.4, M3)",
             reference="the default build of the same alignment", reference_file="design/sim_spec_ms5.md §3.4",
             fields=("n_instances", "n_failures", "#g16_fits", "#rows_without_gamma")),
        Spec("S1-2", kind="property", **s1,
             claim="every A8 run has its certificate, and it holds (Theorem W(a)(b))", label=W_AB,
             reference="held in every proven-case run; W(c) runs counted", reference_file=guard,
             fields=cert + ("n_run_errors",)),
        Spec("S1-3", kind="property", **s1, claim="no run has an invariant failure",
             label=None, label_note="the engine's invariants", reference="no invariant failure",
             reference_file="design/Sublet_design.md §5.2",
             fields=("n_runs", "n_invariant_failures", "n_runs_with_gpu_only_lease_slots")),
        Spec("S1-4", kind="informative", **s1,
             claim="the saving per point and the span per row (informative); with the rows whose span exceeds 10 "
                   "percentage points named",
             label=None, label_note="a sensitivity study with no theory claim (design §5.5, S1)",
             reference="the default point's median saving over BL0a", reference_file=SWEEP_SUM + " rows.<row>.default",
             fields=("#saving_pct_median", "min:saving_pct_median", "max:saving_pct_median", "max:span",
                     "rows_span_above_threshold", "rows_incomplete"),
             ref_fields=("threshold_pp", "saving_pct_median.default"),
             remark="reported as measured; S1 is a sensitivity study in the supplement with no claim (§3.1)"),
        # §4.7 Q28, part q28
        Spec("Q28-1", kind="property", **q28,
             claim="every run of every policy under both variants finishes with no invariant failure and handles "
                   "every refusal and every violation death (no error record)",
             label=None, label_note="the policies' handling of refused purchases and violation deaths (MS2 spec §20 "
                                    "item 23)",
             reference="no invariant failure, no error record", reference_file="design/Sublet_design.md §5.2.2, §7.5",
             fields=("n_runs", "n_sub_runs", "n_invariant_failures", "n_run_errors", "n_job_failures",
                     "refusals_unavailable_total", "violation_deaths_total")),
        Spec("Q28-2", kind="property", **q28,
             claim="every L-vr run reports no ratio (ratio_validity non-null) and every L-rf run on the trace "
                   "schedule keeps its ratio validity as under the default lender; every stress run file records "
                   "its variant's lender model",
             label=None, label_note="the ratio rule of design §5.2.4 under the stress variants",
             reference="ratio_validity non-null under L-vr; under L-rf as under the default lender",
             reference_file="code/sim/sublet/drivers/run.py (ratio_validity); design/Sublet_design.md §5.2.4",
             fields=("grids", "n_vr", "n_vr_with_a_ratio", "n_rf", "n_rf_changed", "n_files_checked",
                     "n_wrong_lender_model")),
        Spec("Q28-3", kind="property", **q28,
             claim="every A8 run under both variants has its certificate, and it holds", label=W_AB,
             reference="held in every proven-case run; W(c) runs counted", reference_file=guard,
             fields=cert + ("n_run_errors",)),
        Spec("Q28-4", kind="informative", **q28,
             claim="the change of each policy's median cost over BL0a against its reference, the refusals and the "
                   "violation victims (informative)",
             label=None, label_note="Q28's stress variants (design §7.5), a measurement",
             reference="E7's runs.1.<tag> (BL3: part q28's default jobs; Sublet also S1's default point)",
             reference_file=f"{OUT}/e7/main/summary.json; {SWEEP_SUM}",
             fields=("delta_overflow_over_bl0a.rf", "delta_overflow_over_bl0a.vr",
                     "delta_overflow_over_bl0a_s1_default", "refusals_unavailable_median.rf",
                     "violation_victims_median.vr", "saving_rises"),
             remark="reported as measured against each policy's reference under the default lender (§4.4)"),
        # §5.9 E9
        Spec("E9-1", kind="property", **e9,
             claim="every run job finished with status ok inside the 3 GB cap, with no invariant failure",
             label=None, label_note="the job records and the engine's invariants", reference="status ok, no failure",
             reference_file="design/sim_spec_ms5.md §0 item 2",
             fields=("n_jobs", "jobs_by_status", "n_failed", "n_missing", "n_runs", "n_runs_with_invariant_failures",
                     "n_over_cap"), ref_fields=("cap_mb",)),
        Spec("E9-2", kind="property", **e9,
             claim="per run, C27's counts equal the grid (n_slow_steps = 288, n_fast_steps = 1,440), and "
                   "slow_step_s_sum + fast_step_s_sum + reset_s + finish_s does not exceed wall_s by more than 1e-6 s",
             label=None, label_note="the engine's loop times (C27)",
             reference="the grid's step counts; the sums at most wall_s + 1e-6 s",
             reference_file="code/sim/sublet/engine.py (RunResult.runtime, C27)",
             fields=("n_runs", "grids", "n_failures", "max_excess_s"), ref_fields=("tolerance_s",)),
        Spec("E9-3", kind="property", **e9,
             claim="every A8 run has its certificate, and it holds (Theorem W(a)(b))", label=W_AB,
             reference="held in every proven-case run; W(c) runs counted", reference_file=guard, fields=cert),
        Spec("E9-4", kind="property", **e9,
             claim="every LP job ended ok, and every LP under M18's gate was solved to optimality (linprog status 0, "
                   "HiGHS's model status 7, 'Optimal') inside the 3 GB cap; an LP whose estimate is not under the gate "
                   "is not solved and is listed as gated (amended on 2026-10-30)",
             label=None, label_note="the LP bound's solves (M17, M18)",
             reference="linprog status 0, HiGHS model status 7; gated LPs listed",
             reference_file="code/sim/sublet/opt/milp.py (solve_lp); design/sim_spec_ms5.md §5.9",
             fields=("n_jobs", "jobs_by_status", "n_lps", "n_not_optimal", "n_gated", "gated", "n_failed",
                     "n_missing", "summary_status"),
             ref_fields=("gate_mb", "time_limit_s"),
             regenerated_file=f"{E9_SUM} checks.E9-4 (recomputed by this report, §5.9 as amended)",
             compute=lambda inp: _e9_4(inp)),
        Spec("E9-5", kind="informative", **e9,
             claim="per point and policy, the loops per simulated hour against real time, the slow-step P99 and "
                   "maximum against the 300-s slot, the fast-step P99 against the 60-s slot, the setup, the peak "
                   "memory and the LP's time (informative); the ratio to real time of the largest point of each menu "
                   "named",
             label=None, label_note="a system measurement with no claim (design §5.5, E9)",
             reference="real time 3,600 s per simulated hour; slots of 300 s and 60 s",
             reference_file="design/sim_spec_ms5.md §5.6",
             fields=("largest_point_by_menu.*.point", "largest_point_by_menu.*.sites_x_llms",
                     "largest_point_by_menu.*.policies.Sublet.real_time_over_loops",
                     "largest_point_by_menu.*.policies.A6.real_time_over_loops", "flags.slow_step_max_over_slot",
                     "flags.fast_step_p99_over_slot", "flags.loops_over_real_time"),
             ref_fields=("real_time_s_per_h", "slow_slot_s", "fast_slot_s"),
             remark="reported as measured; E9 has no claim (§5.1)"),
        # §6.3, computed here
        Spec("SL-1", exp="SL", section="§6.3", kind="property",
             claim="the extract's daily series equal a recomputation from the npz without the trace's end (minimum, "
                   "mean and maximum per day within 1e-9), and its source digests equal the versioned files'",
             label=None, label_note="the slack extract against its analysis outputs (§6)",
             summary=SLACK_EXTRACT, reference="the npz's daily minimum, mean and maximum without the trace's end "
                                              "(within 1e-9); the sha256 of the npz and the two JSON files",
             reference_file=f"{SLACK_NPZ}; {SLACK_JSON}; {SLACK_A9B}",
             fields=("n_pools", "n_days", "n_slots", "n_kept", "tail_start_slot", "max_abs_diff", "digests_equal",
                     "#failures"),
             ref_fields=("tolerance", "slots_per_day", "tail_rise"),
             regenerated_file=f"{SLACK_EXTRACT} (recomputed by this report)", compute=lambda inp: _sl1(inp)),
        # §8.4, computed here
        Spec("RB-1", exp="RB", section="§8.4", kind="property",
             claim="the exit run of run_all.sh with CHECK=1 in a clean clone: every output identical, no file without "
                   "its entry, the float heights equal",
             label=None, label_note="the frozen rebuild (design §5.2.6, M30)", summary=REBUILD,
             reference="every output byte-identical with its versioned file; the float heights equal on every key but "
                       "'written'; no file without its entry", reference_file="code/sim/figs/rebuild.py",
             fields=("mode", "only", "git_revision", "tracked_files_dirty", "n_outputs", "n_identical",
                     "#different", "#unlisted", "#missing", "heights_equal", "hand_set_ok", "#stale", "#problems"),
             regenerated_file=f"{REBUILD} (read by this report)", compute=lambda inp: _rb1(inp)),
    )


# ---------------------------------------------------------------- computed rows (E9-4, SL-1, RB-1)
GATE_SKIP = "is not under the gate"                    # e9.run_lp's skip reason of an LP above M18's gate


def _e9_4(inp) -> dict:
    """E9-4 as amended on 2026-10-30 (§5.9): from the E9 summary's checks.E9-4, whose own status counts an LP that
    M18's gate skipped as a failure (e9.check_e9_4), the LPs whose only problem is the gate are listed as gated and
    do not fail the row. It holds iff no LP job failed, none is missing, and every other LP was solved to optimality
    inside the cap; a reduced summary makes the row a bug (_reduced)."""
    S, prob = inp.load(E9_SUM)
    if S is None:
        return m3._absent(E9_SUM, prob)
    entry = m3._d(m3._d(S.get("checks")).get("E9-4"))
    if not entry:
        return {"status": "missing", "_note": f"no entry checks.E9-4 in {E9_SUM}", "_reduced": m3._reduced(S)}
    listed = entry.get("not_optimal") if isinstance(entry.get("not_optimal"), list) else []
    gated, other = [], []
    for x in listed:
        probs = m3._d(x).get("problems") or []
        (gated if probs and all(GATE_SKIP in str(q) for q in probs) else other).append(x)
    n_listed = entry.get("n_not_optimal") or 0
    notes = []
    if n_listed > len(listed):
        other.append({"problems": [f"{n_listed - len(listed)} LP(s) beyond the summary's list"]})
    if gated:
        notes.append(f"{len(gated)} LP(s) above M18's gate not solved (gated, §5.9 as amended): "
                     + ", ".join(str(m3._d(x).get("job")) for x in gated))
    if other:
        notes.append("not optimal: " + "; ".join(f"{m3._d(x).get('job')}: {m3._d(x).get('problems')}"
                                                 for x in other[:5]))
    if entry.get("n_failed") or other:
        status = "fail"
    elif entry.get("n_missing") or not entry.get("n_lps"):
        status = "missing"
    else:
        status = "pass"
    return {**entry, "status": status, "summary_status": entry.get("status"),
            "gated": [m3._d(x).get("job") for x in gated], "n_gated": len(gated),
            "_reduced": m3._reduced(S), "_note": "; ".join(notes) or None}
def _sha256(p: Path) -> Optional[str]:
    if not Path(p).is_file():
        return None
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def daily(s, per_day: int) -> dict:
    """The daily minimum, mean and maximum of a slot series: day d holds the slots [d * per_day, (d + 1) * per_day),
    the last day the remaining slots (§6.2); this report's own recomputation, for SL-1."""
    s = np.asarray(s, dtype=float)
    n_full = s.size // per_day
    out = {"min": [], "mean": [], "max": []}
    if n_full:
        b = s[:n_full * per_day].reshape(n_full, per_day)
        out = {"min": b.min(axis=1).tolist(), "mean": b.mean(axis=1).tolist(), "max": b.max(axis=1).tolist()}
    if s.size > n_full * per_day:
        rest = s[n_full * per_day:]
        for k, f in (("min", np.min), ("mean", np.mean), ("max", np.max)):
            out[k].append(float(f(rest)))
    return out


def tail_start(series: dict, capacity: dict) -> tuple:
    """(first slot of the trace's end or None, every slot at which each pool's slack rises by at least
    SLACK_TAIL_RISE of its capacity from the slot before); §6.2's rule, this report's own recomputation."""
    pools = list(series)
    n = len(next(iter(series.values())))
    rises = np.ones(max(n - 1, 0), dtype=bool)
    for p in pools:
        x = np.asarray(series[p], dtype=float) / float(capacity[p])
        rises &= (x[1:] - x[:-1]) >= SLACK_TAIL_RISE
    hits = [int(i) + 1 for i in np.flatnonzero(rises)]
    return (hits[0] if len(hits) == 1 else None), hits


def _sl1(inp) -> dict:
    """SL-1 (§6.3) from the extract and the three analysis outputs under the root."""
    E, prob = inp.load(SLACK_EXTRACT)
    e = {"tolerance": SL1_TOL, "slots_per_day": None, "tail_rise": SLACK_TAIL_RISE, "n_pools": None,
         "n_days": None, "n_slots": None, "n_kept": None, "tail_start_slot": None, "max_abs_diff": None,
         "digests_equal": None, "failures": []}
    if E is None:
        return {**e, **m3._absent(SLACK_EXTRACT, prob)}
    npz, js, a9 = inp.root / SLACK_NPZ, inp.root / SLACK_JSON, inp.root / SLACK_A9B
    if not npz.is_file() or not js.is_file() or not a9.is_file():
        miss = [r for r, p in ((SLACK_NPZ, npz), (SLACK_JSON, js), (SLACK_A9B, a9)) if not p.is_file()]
        return {**e, "status": "missing", "_note": f"{', '.join(miss)} missing"}
    data = m3._d(E.get("data"))
    series = m3._d(data.get("series"))
    fails = []
    meta = json.loads(js.read_text())
    slot_min = m3._d(json.loads(a9.read_text()).get("meta")).get("slot_min")
    if not isinstance(slot_min, int) or slot_min <= 0 or 1440 % slot_min:
        return {**e, "status": "fail", "failures": [f"{SLACK_A9B} meta.slot_min is {slot_min!r}"],
                "_note": f"{SLACK_A9B} meta.slot_min is {slot_min!r}"}
    per_day = 1440 // slot_min
    if data.get("slots_per_day") != per_day or data.get("slot_min") != slot_min:
        fails.append(f"slot_min {data.get('slot_min')!r} and slots_per_day {data.get('slots_per_day')!r}, not "
                     f"{slot_min} and {per_day}")
    with np.load(npz) as z:
        pools = list(z.files)
        full = {p: np.asarray(z[p], dtype=float) for p in pools}
    n_slots = {p: int(v.size) for p, v in full.items()}
    ns = sorted(set(n_slots.values()))
    if len(ns) != 1:
        note = f"{SLACK_NPZ}: the pools' series differ in length: {n_slots}"
        return {**e, "status": "fail", "slots_per_day": per_day, "n_slots": ns, "failures": [note], "_note": note}
    t0, hits = tail_start(full, {p: m3._d(meta.get(p)).get("capacity_gpus") or 1.0 for p in pools})
    if len(hits) > 1 or (t0 is not None and ns[-1] - t0 > per_day):
        fails.append(f"slots at which every pool rises by {SLACK_TAIL_RISE:g} of its capacity: {hits}; expected at "
                     "most one, in the last day")
    n_kept = ns[0] if t0 is None else t0
    worst = 0.0
    for pool in pools:
        ent = m3._d(series.get(pool))
        if not ent:
            fails.append(f"{pool}: not in the extract")
            continue
        want = daily(full[pool][:n_kept], per_day)
        for k in ("min", "mean", "max"):
            got = ent.get(k)
            if not isinstance(got, list) or len(got) != len(want[k]):
                fails.append(f"{pool}.{k}: {len(got) if isinstance(got, list) else got!r} days, the npz gives "
                             f"{len(want[k])}")
                continue
            try:
                d = float(np.max(np.abs(np.asarray(got, dtype=float) - np.asarray(want[k]))))
            except (TypeError, ValueError):
                fails.append(f"{pool}.{k}: not numbers")
                continue
            if not d <= SL1_TOL:          # NaN fails too
                fails.append(f"{pool}.{k}: max abs diff {d:.3g} > {SL1_TOL:g}")
            worst = max(worst, d) if np.isfinite(d) else float("inf")
    extra = sorted(set(series) - set(pools))
    if extra:
        fails.append(f"pools in the extract but not in the npz: {extra}")
    if list(data.get("pools") or []) != pools:
        fails.append(f"the extract's pools {data.get('pools')!r} are not the npz's {pools}")
    if len(ns) != 1 or data.get("n_slots") != ns[0]:
        fails.append(f"n_slots {data.get('n_slots')!r} against the npz's {ns}")
    tl = m3._d(data.get("tail"))
    n_tail = 0 if t0 is None else ns[-1] - t0
    if data.get("n_kept") != n_kept or tl.get("start_slot") != t0 or tl.get("n_slots") != n_tail:
        fails.append(f"n_kept {data.get('n_kept')!r} and the end's first slot {tl.get('start_slot')!r} and length "
                     f"{tl.get('n_slots')!r} against {n_kept}, {t0!r} and {n_tail}")
    n_days = -(-n_kept // per_day)
    want_days = {"n_days": n_days, "last_day_slots": n_kept - (n_days - 1) * per_day}
    for k, v in want_days.items():
        if data.get(k) != v:
            fails.append(f"{k} {data.get(k)!r} against {v}")
    days = data.get("days")
    if not isinstance(days, (int, float)) or not abs(float(days) - n_kept * slot_min / 1440) <= SL1_TOL:
        fails.append(f"days {days!r} against {n_kept * slot_min / 1440!r}")
    dig = m3._d(data.get("source_sha256"))
    digests = {r: {"extract": dig.get(r), "file": _sha256(f)} for r, f in ((SLACK_NPZ, npz), (SLACK_JSON, js),
                                                                           (SLACK_A9B, a9))}
    deq = all(v["extract"] == v["file"] for v in digests.values())
    if not deq:
        fails.append("source digests differ: " + ", ".join(k for k, v in digests.items() if v["extract"] != v["file"]))
    return {**e, "status": "fail" if fails else "pass", "claim": None, "slots_per_day": per_day,
            "n_pools": len(pools), "n_days": n_days, "n_slots": ns[0] if len(ns) == 1 else ns,
            "n_kept": n_kept, "tail_start_slot": t0, "max_abs_diff": None if not np.isfinite(worst) else worst,
            "digests_equal": deq, "digests": digests, "failures": fails[:50], "_note": "; ".join(fails[:10]) or None}


def _rb1(inp) -> dict:
    """RB-1 (§8.4) from the rebuild record: the exit run's conditions (module docstring) and the record current."""
    R, prob = inp.load(REBUILD)
    if R is None:
        return m3._absent(REBUILD, prob)
    meta, cov, tot = m3._d(R.get("meta")), m3._d(R.get("coverage")), m3._d(R.get("totals"))
    heights = m3._d(R.get("heights"))
    hand = R.get("hand_set") if isinstance(R.get("hand_set"), list) else []
    outs = R.get("outputs") if isinstance(R.get("outputs"), list) else []
    probs = []
    if R.get("status") != "pass" or R.get("pass") is not True:
        probs.append(f"status {R.get('status')!r}, pass {R.get('pass')!r}"
                     + (f" ({'; '.join(map(str, R.get('reasons') or []))[:300]})" if R.get("reasons") else ""))
    if meta.get("mode") != "check":
        probs.append(f"mode {meta.get('mode')!r}, not 'check' (CHECK=1)")
    if meta.get("only") is not None:
        probs.append(f"ONLY {meta.get('only')!r}: not the full list")
    if meta.get("root_is_repository") is not True:
        probs.append("the run compared a root other than its repository")
    if meta.get("tracked_files_dirty") is not False:
        probs.append(f"tracked_files_dirty {meta.get('tracked_files_dirty')!r} (not a clean clone)")
    if cov.get("ok") is not True:
        probs.append(f"coverage: {len(cov.get('unlisted') or [])} file(s) without an entry, "
                     f"{len(cov.get('missing') or [])} listed file(s) missing")
    if tot.get("different") or tot.get("not_written") or tot.get("failed"):
        probs.append(f"{len(tot.get('different') or [])} output(s) differ, {len(tot.get('not_written') or [])} not "
                     f"written, {len(tot.get('failed') or [])} script(s) not ok")
    h_eq = {k: m3._d(heights.get(k)).get("equal") for k in ("plain", "ms4")}
    if not all(v is True for v in h_eq.values()):
        probs.append(f"float heights equal {h_eq}")
    hs_ok = bool(hand) and all(m3._d(h).get("ok") is True for h in hand)
    if not hs_ok:
        probs.append("a hand-set file changed or is not the one measured" if hand else "no hand-set check")
    if R.get("unexpected"):
        probs.append(f"{len(R['unexpected'])} unexpected file(s) written")
    if not outs:
        probs.append("no output compared")
    stale = [o.get("path") for o in map(m3._d, outs)
             if isinstance(o.get("path"), str) and o.get("versioned_sha256") != _sha256(inp.root / o["path"])]
    if stale:
        probs.append(f"the record is stale: {len(stale)} versioned file(s) changed since the run ({stale[:5]})")
    return {"status": "fail" if probs else "pass", "claim": None, "mode": meta.get("mode"), "only": meta.get("only"),
            "git_revision": meta.get("git_revision"), "tracked_files_dirty": meta.get("tracked_files_dirty"),
            "written": meta.get("written"), "n_outputs": tot.get("n_outputs"), "n_identical": tot.get("n_identical"),
            "different": list(tot.get("different") or []), "unlisted": list(cov.get("unlisted") or []),
            "missing": list(cov.get("missing") or []), "heights_equal": h_eq, "hand_set_ok": hs_ok, "stale": stale,
            "problems": probs, "_note": "; ".join(probs) or None}


# ---------------------------------------------------------------- verdicts and rows
def verdict(kind: str, status: Optional[str], explainable: bool = False) -> tuple[str, Optional[str]]:
    """(verdict, note) of a check entry's status (§1.4 item 2; ms4_claims.verdict with the MS5 sections): pass gives
    reproduced or holds by the row's kind (informative rows stay informative), fail gives bug, explained is accepted
    only where the spec allows it (no MS5 check does), informative only for the rows the spec marks informative,
    missing and pending stay; any other status is a bug."""
    if status == "pass":
        if kind == "informative":
            return "informative", "the summary says pass; the spec marks the row informative"
        return ("reproduced" if kind == "reproduction" else "holds"), None
    if status in ("fail", "bug_input"):
        return "bug", None
    if status == "explained":
        return ("explained", None) if explainable else (
            "bug", f"status 'explained' where the spec allows no explanation (no check of {SECTIONS} allows one)")
    if status == "informative":
        return ("informative", None) if kind == "informative" else \
            ("bug", "status 'informative' where the spec sets a pass condition")
    if status in ("missing", "pending"):
        return status, None
    return "bug", f"status {status!r} outside the vocabulary of MS4 spec §2.6"


def build_row(spec: Spec, inp) -> dict:
    """One row of the report for `spec` (module docstring, rows[])."""
    src = spec.summary
    reduced = False
    if spec.compute is not None:
        entry = spec.compute(inp)
        reduced = bool(entry.pop("_reduced", False))
    else:
        S, prob = inp.load(src)
        if S is None:
            entry = m3._absent(src, prob)
        elif "checks" in S and not isinstance(S["checks"], dict):
            entry = {"status": "bug_input", "_note": f"{src}: checks is not an object"}
        else:
            entry = m3._d(S.get("checks")).get(spec.id)
            if not isinstance(entry, dict):
                entry = {"status": "missing", "_note": f"no entry checks.{spec.id} in {src}"}
            reduced = m3._reduced(S)
    status = entry.get("status")
    reg_file = spec.regenerated_file or f"{src} checks.{spec.id}"
    v, vnote = verdict(spec.kind, status, spec.explainable)
    notes = [x for x in (entry.get("_note"), vnote) if x]
    if spec.compute is None and status in ("missing", "pending", "fail"):
        n = m4c._entry_note(entry, status)
        if n:
            notes.append(n)
    if status == "fail" and not notes:
        notes.append(f"the summary's status is 'fail' (see {reg_file})")
    if status in ("missing", "pending") and not notes:
        notes.append("the summary gives no reason")
    if reduced:
        v = "bug"
        notes.insert(0, f"{src} is from a reduced run (meta.reduced true; smoke), never a result")
    if v == "informative" and spec.remark:
        notes.append(spec.remark)
    return {"id": spec.id, "experiment": spec.exp, "section": spec.section, "kind": spec.kind,
            "claim": {"spec": spec.claim, "summary": entry.get("claim")},
            "status_label": spec.label, "status_label_note": spec.label_note if spec.label is None else None,
            "reference": {"value": spec.reference, "values": m4c._values(entry, spec.ref_fields),
                          "file": spec.reference_file},
            "regenerated": {"value": m4c._values(entry, spec.fields), "file": reg_file},
            "summary_status": None if status == "bug_input" else status, "verdict": v, "explanation": None,
            "note": "; ".join(dict.fromkeys(notes)) or None}


def _row_or_bug(spec: Spec, inp) -> dict:
    """build_row, or, where an input has a shape the drivers never write and reading it raises, a 'bug' row that
    names the error, so that the report is still written."""
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
    """§1.4 item 2 (ms3_claims.criterion)."""
    return m3.criterion(rows)


# ---------------------------------------------------------------- copy checks, jobs, rebuild record, captions
def copy_block(inp, exps=COPY_EXPS) -> dict:
    """The copy records out/ms3_copy_<exp>.json of s1 and e9 (§1.2; S1's two parts through C30): pass, the clone's
    commit, the failed checks, the parts and the job records by status; and whether the present records name one
    clone commit (§1.2: one clone holds the MS5 runs)."""
    recs = {}
    for exp in exps:
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
        absent = [k for k in exps if not recs[k]["present"]]
        note = (f"{len(present)} of {len(exps)} records present"
                + (f" (none for {', '.join(absent)})" if absent else "")
                + (f"; failed: {', '.join(bad)}" if bad else "; every present record passes")
                + ("; one clone commit" if one else f"; clone commits {commits or 'unknown'}"))
    return {"records": recs, "commits": commits, "one_commit": one, "note": note}


def jobs_block(inp, folders=JOB_FOLDERS) -> dict:
    """Every listed job of each MS5 folder (manifest.json `jobs`, plus the records '<exp>:manifest' and
    '<exp>:summary'; S1's two parts each with their own) against its record jobs/<id>.json (§2.4: only 'ok' counts as
    done): the jobs by status ('no record' where the record is absent) and those without an 'ok' record (MS5 has no
    MILP job, so Q39's rule does not apply and every one of them is blocking), and the lengths of the summary's lists
    meta.jobs_missing and meta.ignored_outputs. test_ms5_out.py fails on a blocking job."""
    rows = {}
    for folder in folders:
        exp = folder.split("/")[0]
        man_rel, sum_rel = f"{OUT}/{folder}/manifest.json", f"{OUT}/{folder}/summary.json"
        M, prob = inp.load(man_rel)
        e = {"manifest": man_rel, "present": M is not None, "n_listed": None, "by_status": {}, "n_blocking": None,
             "blocking": [], "n_unlisted_records": None, "n_unreadable_records": None, "summary_jobs_missing": None,
             "summary_ignored_outputs": None}
        if M is None:
            e["note"] = f"{man_rel} {prob}"
            rows[folder] = e
            continue
        jobs = M.get("jobs") if isinstance(M.get("jobs"), list) else []
        listed = [(m3._d(j).get("id"), m3._d(j).get("kind")) for j in jobs]
        listed += [(mc.job_id(exp, "manifest"), "pool"), (mc.job_id(exp, "summary"), "pool")]
        recs, bad = m3._job_statuses(inp.root / OUT / folder)
        by_status: dict = {}
        blocking = []
        for jid, kind in listed:
            st = recs.get(jid, "no record") if isinstance(jid, str) else "no job id"
            by_status[st] = by_status.get(st, 0) + 1
            if st != "ok":
                blocking.append({"job": jid, "kind": kind, "status": st})
        ids = {j for j, _ in listed}
        S, _ = inp.load(sum_rel)
        meta = m3._d(m3._d(S).get("meta"))

        def _n(key):
            return len(meta[key]) if isinstance(meta.get(key), list) else None

        e.update(n_listed=len(listed) - 2, by_status=dict(sorted(by_status.items())), n_blocking=len(blocking),
                 blocking=blocking[:m3.JOBS_LIST_MAX], n_unlisted_records=sum(1 for j in recs if j not in ids),
                 n_unreadable_records=bad, summary_jobs_missing=_n("jobs_missing"),
                 summary_ignored_outputs=_n("ignored_outputs"))
        rows[folder] = e
    n_block = sum(r["n_blocking"] or 0 for r in rows.values())
    absent = [k for k, r in rows.items() if not r["present"]]
    note = (f"{n_block} listed job(s) without an 'ok' record" if n_block else "every listed job has an 'ok' record")
    if len(absent) == len(rows):
        note = f"no job list (manifest.json) for {', '.join(absent)}"
    elif absent:
        note += f"; no job list for {', '.join(absent)}"
    return {"rows": rows, "n_blocking": n_block, "note": note}


def rebuild_block(inp) -> dict:
    """The record of the frozen rebuild (figs/rebuild.py, §8.3), as found: its mode, commit, tools, fonts and counts
    (RB-1 gives the verdict)."""
    R, prob = inp.load(REBUILD)
    out = {"file": REBUILD, "present": R is not None}
    if R is None:
        out["note"] = (f"{REBUILD} {prob} (CHECK=1 code/sim/figs/run_all.sh in a clean clone writes it to its "
                       "temporary folder, from which it is copied, §8.4)")
        return out
    meta, cov, tot = m3._d(R.get("meta")), m3._d(R.get("coverage")), m3._d(R.get("totals"))
    hand = R.get("hand_set") if isinstance(R.get("hand_set"), list) else []
    out.update(status=R.get("status"), **{"pass": R.get("pass")}, mode=meta.get("mode"), only=meta.get("only"),
               git_revision=meta.get("git_revision"), tracked_files_dirty=meta.get("tracked_files_dirty"),
               root_is_repository=meta.get("root_is_repository"), written=meta.get("written"),
               versions=meta.get("versions"), fonts=meta.get("fonts"), n_scripts=tot.get("n_scripts"),
               n_outputs=tot.get("n_outputs"), n_identical=tot.get("n_identical"),
               different=tot.get("different") or [], not_written=tot.get("not_written") or [],
               unlisted=cov.get("unlisted") or [], missing=cov.get("missing") or [],
               heights_equal=tot.get("heights_equal"), hand_set_ok=bool(hand) and all(
                   m3._d(h).get("ok") is True for h in hand),
               note=f"{tot.get('n_identical')} of {tot.get('n_outputs')} outputs identical in mode "
                    f"{meta.get('mode')!r} at {meta.get('git_revision')}")
    return out


def captions_block(inp, extracts: Path) -> dict:
    """The caption drafts of the three MS5 figures (§1.4 item 2): each extract's labels.caption, written by its script
    from the summaries; a draft from a reduced run (the extract's meta.reduced) is never a result."""
    out = {}
    for name, _ in MS5_FIGURE_SCRIPTS:
        p = Path(extracts) / f"{name}.json"
        rel = f"{OUT}/figs/{name}.json"
        E, prob = inp.load(rel) if Path(extracts).resolve() == (inp.root / OUT / "figs").resolve() else \
            _load_abs(p)
        data = m3._d(m3._d(E).get("data"))
        text = m3._d(data.get("labels")).get("caption")
        red = m3._d(data.get("meta")).get("reduced") is True
        notes = []
        if E is None:
            notes.append(f"{p} {prob}")
        elif not isinstance(text, str):
            notes.append("the extract has no labels.caption")
        if red:
            notes.append("drafted from a reduced run (never a result)")
        out[name] = {"text": text if isinstance(text, str) else None,
                     "n_chars": len(text) if isinstance(text, str) else None, "reduced": red, "source": str(p),
                     "notes": notes}
    return out


def _load_abs(p: Path):
    d = mc.read_json(p)
    if d is None:
        return None, "missing" if not Path(p).is_file() else "invalid JSON"
    return (d, None) if isinstance(d, dict) else (None, "invalid JSON: not an object")


# ---------------------------------------------------------------- figures (§1.4 item 1)
def figure_scripts() -> list[tuple[str, str, str]]:
    """(figure name, module, script path relative to code/sim) of the three MS5 figure scripts, in path order."""
    return [(name, rel[:-len(".py")].replace("/", "."), rel) for name, rel in MS5_FIGURE_SCRIPTS]


def figures_block(root: Path, extracts: Path, only=None) -> dict:
    """ms4_claims.figures_block on the three MS5 scripts: rerun with --from-extract <extracts>/<name>.json in this
    process, every output in a temporary folder that is removed afterwards."""
    return m4c.figures_block(root, extracts, only, scripts=figure_scripts())


# ---------------------------------------------------------------- the report
def build(root=None, *, figures: bool = True, only=None, extracts=None) -> dict:
    """The report (module docstring, ms5_claims.json) from the files under the input root."""
    root = Path(root).resolve() if root is not None else m3._default_root()
    inp = m3._Inputs(root)
    rows = [_row_or_bug(s, inp) for s in SPECS]
    crit = criterion(rows)
    cp = copy_block(inp)
    jb = jobs_block(inp)
    rb = rebuild_block(inp)
    ex = Path(extracts).resolve() if extracts is not None else root / OUT / "figs"
    cap = captions_block(inp, ex)
    fg = figures_block(root, ex, only) if figures else \
        {"run": False, "extracts": str(ex), "rows": [], "counts": {}, "note": "not run (--no-figures)"}
    meta = {"module": "sublet.experiments.ms5_claims", "spec": f"{SPEC_DOC} §1.4, §9",
            "git_revision": mc.git_revision(), "written": mc._now(), "input_root": str(root),
            "input_root_is_repository": m3._is_repo(root), "inputs": dict(sorted(inp.status.items()))}
    return {"meta": meta, "criterion": crit, "rows": rows, "figures": fg, "copy_checks": cp, "jobs": jb,
            "rebuild": rb, "captions": cap}


def markdown(rep: dict) -> str:
    """ms5_claims.md: the head (the criterion, figures, copy checks, jobs, the rebuild), the claims tables per
    experiment with their notes, the figures' small glyphs, the copy checks, the jobs, the rebuild record and the
    caption drafts."""
    fmt, kv, cell = m3._fmt, m3._kv, m3._cell
    m, c = rep["meta"], rep["criterion"]
    L = ["# MS5 claims report (design/sim_spec_ms5.md §1.4, §9)", ""]
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
    rb = rep["rebuild"]
    L.append(f"Rebuild (§1.4 item 5): {rb['note']}" + (f"; pass {fmt(rb.get('pass'))}" if rb["present"] else "") + ".")
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
        notes = [r for r in rs if r["note"] or (r["claim"]["summary"] and r["claim"]["summary"] != r["claim"]["spec"])]
        for r in notes:
            bits = [r["note"]] if r["note"] else []
            if r["claim"]["summary"]:
                bits.append(f"the summary's claim: {r['claim']['summary']}")
            L.append(f"- {r['id']}: " + ". ".join(bits))
        if notes:
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
    L.append("## Jobs (§2.4)")
    L.append("")
    L.append(mc.md_table(["Folder", "Job list", "Listed", "Records by status", "Without 'ok' (blocking)",
                          "Summary: jobs_missing, ignored_outputs"],
                         [[k, f"`{r['manifest']}`", r["n_listed"], fmt(r["by_status"]) if r["present"] else "–",
                           r["n_blocking"], f"{fmt(r['summary_jobs_missing'])}, {fmt(r['summary_ignored_outputs'])}"]
                          for k, r in jb["rows"].items()]).rstrip("\n"))
    L.append("")
    L.append(f"{jb['note'][0].upper() + jb['note'][1:]}.")
    for k, r in jb["rows"].items():
        if r["blocking"]:
            L.append("")
            L.append(f"- {k}: " + "; ".join(f"`{x['job']}` ({x['kind']}, {x['status']})" for x in r["blocking"])
                     + (f"; ... ({r['n_blocking']} in all)" if r["n_blocking"] > len(r["blocking"]) else ""))
    L.append("")
    L.append("## Rebuild record (§8.3)")
    L.append("")
    if rb["present"]:
        L.append(f"`{rb['file']}`: status {rb['status']}, mode {rb['mode']}, ONLY {fmt(rb['only'])}, revision "
                 f"{rb['git_revision']} (tracked files dirty: {fmt(rb['tracked_files_dirty'])}), written "
                 f"{rb['written']}; {rb['n_identical']} of {rb['n_outputs']} outputs identical over {rb['n_scripts']} "
                 f"scripts; differ: {', '.join(rb['different']) or 'none'}; not written: "
                 f"{', '.join(rb['not_written']) or 'none'}; without an entry: {', '.join(rb['unlisted']) or 'none'}; "
                 f"listed but missing: {', '.join(rb['missing']) or 'none'}; float heights equal "
                 f"{fmt(rb['heights_equal'])}; hand-set files unchanged {fmt(rb['hand_set_ok'])}.")
        L.append("")
        L.append("Tools: " + fmt(rb["versions"]) + ".")
        L.append("")
        L.append("Fonts: " + "; ".join(f"{k} `{m3._d(v).get('path')}` sha256 {m3._d(v).get('sha256')}"
                                       for k, v in m3._d(rb["fonts"]).items()) + ".")
    else:
        L.append(f"{rb['note']}.")
    L.append("")
    L.append("## Caption drafts (§1.4 item 2)")
    L.append("")
    for name, cp_ in rep["captions"].items():
        if cp_["text"]:
            L.append(f"{name} ({cp_['n_chars']} characters): {cp_['text']}"
                     + (f" ({'; '.join(cp_['notes'])})" if cp_["notes"] else ""))
        else:
            L.append(f"{name}: no draft ({'; '.join(cp_['notes']) or 'missing'}).")
        L.append("")
    return "\n".join(L).rstrip("\n") + "\n"


def write(rep: dict, out_dir) -> tuple[Path, Path]:
    out = Path(out_dir)
    rep["meta"]["out_dir"] = str(out.resolve())
    pj = mc.dump_json(rep, out / OUT_JSON)
    pm = mc.write_text(markdown(rep), out / OUT_MD)
    return pm, pj


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m sublet.experiments.ms5_claims",
                                 description=__doc__.strip().split("\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", type=Path, default=None,
                    help=f"input root with the repository's layout (default {ENV_IN_ROOT}, else the repository)")
    ap.add_argument("--out-dir", type=Path, default=None,
                    help="folder of ms5_claims.md and .json (default the repository's code/sim/out when the root is "
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
    print(f"[ms5_claims] wrote {pm} and {pj}: criterion {'holds' if c['holds'] else 'does not hold'} ("
          + ", ".join(f"{v} {n}" for v, n in c["counts"].items() if n) + f"); figures: {figs}", flush=True)
    return 0


SPECS = _rows_spec()

if __name__ == "__main__":
    sys.exit(main())
