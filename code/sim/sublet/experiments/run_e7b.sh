#!/usr/bin/env bash
# E7b: budget caps of MS8 (design/ms8/plan.md D2, X6, D4). Runs the jobs of sublet.experiments.e7b under the slot
# semaphore shared with MS3-MS7 (ms3_lib.sh: one 3G scope per job, at most MS3_HOST_SLOTS jobs on the host), one part at
# a time, each part with its own output folder MS3_OUT = out/e7b/<part> (jobs/, logs/, runs/, retry/, manifest.json,
# summary.json, tables.md, run_e7b.log; ms3_common.COPY_PARTS['e7b']).
#
#   E7B_PART="week" sublet/experiments/run_e7b.sh [--reduced]      then
#   E7B_PART="sens" sublet/experiments/run_e7b.sh [--reduced]
#
# Parts in this order, both in the clean clone of the run commit (the commit that merges design/ms8/registration.md,
# D4): week (weeks 301-316 x the 13 modes of E7r's part eval), then sens (the five S1 v2 points), after which
# e7b_analysis.py writes out/e7b/analysis.json and analysis.md (it reads both parts' summaries and the frozen summaries
# of out/sublet_v2/main, out/e7r/eval and out/s1v2/{sweep,w0}). One part per call, or "week sens" in one call. Per part:
# the gate (`e7b --check-start`: refused unless design/ms8/registration.md exists at HEAD, the working tree is clean and
# e7b_analysis.py's sha256 is the registered one; exit 2 when refused), the job list, the manifest, the pool jobs (E7b
# has no 'alone' or MILP jobs), the missing-run rule's rerun (`e7b --retry-list`: once per pool job not 'ok' or with a
# run that raised or failed an invariant, as run_e7h.sh), the manifest again and the summary, then, after part sens,
# the analysis in a 3G scope, then ms3_finish's done line.
# --reduced: e7b.py's reduced job lists (MS8_E7B_REDUCED=1: the development cell bench_e7f 101 with a 2-hour horizon;
# the gate is recorded, not enforced), for smoke runs under a scratch MS3_ROOT, never a result. Environment as
# ms3_lib.sh (MS3_WORKERS, MS3_RESUME, MS3_ROOT, ...; MS3_OUT is set per part here), plus, for tests and smoke runs
# only, E7B_ONLY=<extended regex>: only the jobs whose list line matches run (the summary lists the others as missing),
# E7B_FROZEN=<folder>: the folder holding the frozen summaries that e7b_analysis.py reads (default <MS3_ROOT>/out),
# and E7B_ANALYSIS_MODULE=<module>: the analysis module run after part sens (default sublet.experiments.e7b_analysis).
set -u
for arg in "$@"; do
  case "$arg" in
    --reduced) export MS8_E7B_REDUCED=1 ;;
    *) echo "usage: E7B_PART=<part> $0 [--reduced]" >&2; exit 2 ;;
  esac
done
E7B_PARTS="${E7B_PART:-}"
E7B_PARTS="${E7B_PARTS//,/ }"
if [ -z "${E7B_PARTS// /}" ]; then
  echo "[run_e7b] E7B_PART must name the part(s) to run: week sens" >&2
  exit 2
fi
for part in $E7B_PARTS; do
  case "$part" in
    week | sens) ;;
    *) echo "[run_e7b] unknown part '$part'" >&2; exit 2 ;;
  esac
done
E7B_ONLY="${E7B_ONLY:-}"
if [ -n "$E7B_ONLY" ]; then
  printf '' | grep -Eq -- "$E7B_ONLY" 2> /dev/null
  [ $? -eq 2 ] && { echo "[run_e7b] E7B_ONLY is not a valid extended regex: '$E7B_ONLY'" >&2; exit 2; }
fi
source "$(dirname "$0")/ms3_lib.sh"

e7b_check_start() {   # 0 iff the part's gate lets it start (e7b --check-start in a 3G scope; its lines to the log)
  local -a MS3_PRE
  _ms3_prefix
  "${MS3_PRE[@]}" "$MS3_PY" -m "$MS3_MODULE" --check-start 2>&1 | tee -a "$MS3_LOG"
  return "${PIPESTATUS[0]}"
}

e7b_only() {          # keep the list lines that match E7B_ONLY (tests and smoke runs)
  [ -n "$E7B_ONLY" ] || return 0
  mv "$MS3_OUT/jobs_list.txt" "$MS3_OUT/jobs_list_all.txt"
  grep -E -- "$E7B_ONLY" "$MS3_OUT/jobs_list_all.txt" > "$MS3_OUT/jobs_list.txt"
  _ms3_log "E7B_ONLY='$E7B_ONLY': $(wc -l < "$MS3_OUT/jobs_list.txt") of $(wc -l < "$MS3_OUT/jobs_list_all.txt") jobs"
}

e7b_retry() {         # the missing-run rule's rerun: once per pool job
  local -a MS3_PRE
  _ms3_prefix
  if ! "${MS3_PRE[@]}" "$MS3_PY" -m "$MS3_MODULE" --retry-list --out "$MS3_OUT" > "$MS3_OUT/jobs_retry.txt" \
      2>> "$MS3_LOG"; then
    _ms3_log "could not list the jobs to rerun"
    return 0
  fi
  if [ -n "$E7B_ONLY" ]; then
    grep -E -- "$E7B_ONLY" "$MS3_OUT/jobs_retry.txt" > "$MS3_OUT/jobs_retry_only.txt" || true
    mv "$MS3_OUT/jobs_retry_only.txt" "$MS3_OUT/jobs_retry.txt"
  fi
  _ms3_log "rerun once: $(grep -c '^pool ' "$MS3_OUT/jobs_retry.txt") pool job(s)"
  [ -s "$MS3_OUT/jobs_retry.txt" ] || return 0
  mv "$MS3_OUT/jobs_list.txt" "$MS3_OUT/jobs_list_full.txt"
  cp "$MS3_OUT/jobs_retry.txt" "$MS3_OUT/jobs_list.txt"
  ms3_run_jobs pool
  mv "$MS3_OUT/jobs_list_full.txt" "$MS3_OUT/jobs_list.txt"
}

e7b_analysis() {      # e7b_analysis.py in a 3G scope, its output to the run log
  local -a MS3_PRE
  _ms3_prefix
  local rc
  local -a extra=()
  [ -n "${E7B_FROZEN:-}" ] && extra=(--frozen "$E7B_FROZEN")
  "${MS3_PRE[@]}" "$MS3_PY" -m "${E7B_ANALYSIS_MODULE:-sublet.experiments.e7b_analysis}" --root "$MS3_ROOT" \
    "${extra[@]}" 2>&1 | tee -a "$MS3_LOG"
  rc="${PIPESTATUS[0]}"
  [ "$rc" -eq 0 ] || { _ms3_log "e7b_analysis failed (exit $rc)"; return 1; }
}

for part in $E7B_PARTS; do
  export E7B_PART="$part"
  MS3_OUT="$MS3_ROOT/out/e7b/$part"
  ms3_init e7b
  _ms3_log "part $part"
  if ! e7b_check_start; then
    _ms3_log "refused: part $part does not start (design/ms8/plan.md D4)"
    exit 2
  fi
  ms3_list
  e7b_only
  ms3_manifest
  ms3_run_jobs pool
  e7b_retry
  ms3_manifest
  ms3_summary
  if [ "$part" = "sens" ]; then
    e7b_analysis || exit 1
  fi
  ms3_finish
done
