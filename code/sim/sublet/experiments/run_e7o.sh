#!/usr/bin/env bash
# E7o: the out-of-sample folds of MS7's X2 (design/ms7/plan.md §3 X2; design/ms7/feasibility/oos.md §3, §4 item 6;
# change C55). Runs the jobs of sublet.experiments.e7o under the slot semaphore shared with MS3-MS7 (ms3_lib.sh: one 3G
# scope per job, at most 4 jobs on the host), one fold at a time, each with its own output folder MS3_OUT =
# out/e7o/<part> (jobs/, logs/, runs/, retry/, manifest.json, summary.json, tables.md, run_e7o.log;
# ms3_common.COPY_PARTS['e7o']), then the frozen analysis into out/e7o/analysis.json and analysis.md.
#
#   E7O_PART="fwd [rev]" sublet/experiments/run_e7o.sh [--reduced]
#
# Per part: the gate (`e7o --check-start`: a full run refuses to start unless design/ms7/registration.md exists at HEAD
# and records e7o_analysis.py's sha256, and the working tree is clean; exit 2 when refused), the job list, the
# manifest, the pool jobs, the missing-run rule's rerun (`e7o --retry-list`, once per job, as run_e7h.sh), the
# manifest again and the summary, then ms3_finish's done line. After the last part: e7o_analysis (3G scope), which
# reads every part's summary.json that exists. The forward fold is 480 jobs, about 30 CPU-h, 7.6 h on 4 slots
# (`e7o --estimate`; oos.md §5); the reverse fold the same.
# --reduced: the reduced job lists of e7o.py's docstring (MS3_E7O_REDUCED=1: cell 0 at development seed 101, a 2-hour
# horizon), for smoke runs under a scratch MS3_ROOT, never a result. Environment as ms3_lib.sh (MS3_WORKERS,
# MS3_RESUME, MS3_ROOT, ...; MS3_OUT is set per part here), plus, for tests and smoke runs only,
# E7O_ONLY=<extended regex>: only the jobs whose list line matches run (the summary lists the others as missing).
set -u
for arg in "$@"; do
  case "$arg" in
    --reduced) export MS3_E7O_REDUCED=1 ;;
    *) echo "usage: E7O_PART=<part> $0 [--reduced]" >&2; exit 2 ;;
  esac
done
E7O_PARTS="${E7O_PART:-}"
E7O_PARTS="${E7O_PARTS//,/ }"
if [ -z "${E7O_PARTS// /}" ]; then
  echo "[run_e7o] E7O_PART must name the part(s) to run: fwd rev" >&2
  exit 2
fi
for part in $E7O_PARTS; do
  case "$part" in
    fwd | rev) ;;
    *) echo "[run_e7o] unknown part '$part'" >&2; exit 2 ;;
  esac
done
E7O_ONLY="${E7O_ONLY:-}"
if [ -n "$E7O_ONLY" ]; then
  printf '' | grep -Eq -- "$E7O_ONLY" 2> /dev/null
  [ $? -eq 2 ] && { echo "[run_e7o] E7O_ONLY is not a valid extended regex: '$E7O_ONLY'" >&2; exit 2; }
fi
source "$(dirname "$0")/ms3_lib.sh"

e7o_check_start() {   # 0 iff the gate lets the part start (e7o --check-start in a 3G scope; its lines to the log)
  local -a MS3_PRE
  _ms3_prefix
  "${MS3_PRE[@]}" "$MS3_PY" -m "$MS3_MODULE" --check-start 2>&1 | tee -a "$MS3_LOG"
  return "${PIPESTATUS[0]}"
}

e7o_only() {          # keep the list lines that match E7O_ONLY (tests and smoke runs)
  [ -n "$E7O_ONLY" ] || return 0
  mv "$MS3_OUT/jobs_list.txt" "$MS3_OUT/jobs_list_all.txt"
  grep -E -- "$E7O_ONLY" "$MS3_OUT/jobs_list_all.txt" > "$MS3_OUT/jobs_list.txt"
  _ms3_log "E7O_ONLY='$E7O_ONLY': $(wc -l < "$MS3_OUT/jobs_list.txt") of $(wc -l < "$MS3_OUT/jobs_list_all.txt") jobs"
}

e7o_retry() {         # the missing-run rule's rerun (design/sublet_v2.md §4.5): once per pool job
  local -a MS3_PRE
  _ms3_prefix
  if ! "${MS3_PRE[@]}" "$MS3_PY" -m "$MS3_MODULE" --retry-list --out "$MS3_OUT" > "$MS3_OUT/jobs_retry.txt" \
      2>> "$MS3_LOG"; then
    _ms3_log "could not list the jobs to rerun"
    return 0
  fi
  if [ -n "$E7O_ONLY" ]; then
    grep -E -- "$E7O_ONLY" "$MS3_OUT/jobs_retry.txt" > "$MS3_OUT/jobs_retry_only.txt" || true
    mv "$MS3_OUT/jobs_retry_only.txt" "$MS3_OUT/jobs_retry.txt"
  fi
  _ms3_log "rerun once (§4.5): $(grep -c '^pool ' "$MS3_OUT/jobs_retry.txt") pool job(s)"
  [ -s "$MS3_OUT/jobs_retry.txt" ] || return 0
  mv "$MS3_OUT/jobs_list.txt" "$MS3_OUT/jobs_list_full.txt"
  cp "$MS3_OUT/jobs_retry.txt" "$MS3_OUT/jobs_list.txt"
  ms3_run_jobs pool
  mv "$MS3_OUT/jobs_list_full.txt" "$MS3_OUT/jobs_list.txt"
}

for part in $E7O_PARTS; do
  export E7O_PART="$part"
  MS3_OUT="$MS3_ROOT/out/e7o/$part"
  ms3_init e7o
  _ms3_log "part $part"
  if ! e7o_check_start; then
    _ms3_log "refused: part $part does not start (design/ms7/plan.md D6)"
    exit 2
  fi
  ms3_list
  e7o_only
  ms3_manifest
  ms3_run_jobs pool
  e7o_retry
  ms3_manifest
  ms3_summary
  ms3_finish
done
# the analysis logs to out/e7o/analysis.log, so that every part's run log still ends with its done line (copy check)
ANALYSIS_MODULE="${E7O_ANALYSIS_MODULE:-sublet.experiments.e7o_analysis}"
ALOG="$MS3_ROOT/out/e7o/analysis.log"
declare -a MS3_PRE
_ms3_prefix
if "${MS3_PRE[@]}" "$MS3_PY" -m "$ANALYSIS_MODULE" --root "$MS3_ROOT" > "$ALOG" 2>&1; then
  echo "[run_e7o] analysis written: $MS3_ROOT/out/e7o/analysis.json, analysis.md (log $ALOG)"
else
  echo "[run_e7o] analysis failed (see $ALOG)" >&2
  exit 1
fi
