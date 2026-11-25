#!/usr/bin/env bash
# E7c: the causal-demand rerun of MS7 (design/ms7/plan.md X1, D6; change C53). Runs the jobs of sublet.experiments.e7c
# under the slot semaphore shared with MS3-MS5b (ms3_lib.sh: one 3G scope per job, at most 4 jobs on the host), one part
# at a time, each part with its own output folder (MS3_OUT = out/e7c/<part>: jobs/, logs/, runs/, retry/,
# manifest.json, summary.json, tables.md, run_e7c.log).
#
#   E7C_PART="gate" sublet/experiments/run_e7c.sh [--reduced]      then
#   E7C_PART="lag"  sublet/experiments/run_e7c.sh [--reduced]
#
# Run gate first and lag after it, both in the clean clone of the registration commit (D6), one part per call or
# "gate lag" in one call. Per part: the gate (`e7c --check-start`: refused unless design/ms7/registration.md exists at
# HEAD, the working tree is clean and e7c_analysis.py's sha256 is the registered one; part lag also unless part gate's
# summary at that commit passed every identity check; exit 2 when refused), the job list, the manifest, the pool jobs
# (E7c has no 'alone' or MILP jobs), the missing-run rule's rerun (`e7c --retry-list`: once per pool job not 'ok' or
# with a run that raised or failed an invariant, as run_e7h.sh), the manifest again and the summary, then ms3_finish's
# done line. Part lag is not started after a part gate of the same call that did not pass (its own gate refuses it).
# --reduced: e7c.py's reduced job lists (MS3_E7C_REDUCED=1: development week 101, a 2-hour horizon), for smoke runs
# under a scratch MS3_ROOT, never a result. Environment as ms3_lib.sh (MS3_WORKERS, MS3_RESUME, MS3_ROOT, ...; MS3_OUT
# is set per part here), plus, for tests and smoke runs only, E7C_ONLY=<extended regex>: only the jobs whose list line
# matches run (the summary lists the others as missing).
set -u
for arg in "$@"; do
  case "$arg" in
    --reduced) export MS3_E7C_REDUCED=1 ;;
    *) echo "usage: E7C_PART=<part> $0 [--reduced]" >&2; exit 2 ;;
  esac
done
E7C_PARTS="${E7C_PART:-}"
E7C_PARTS="${E7C_PARTS//,/ }"
if [ -z "${E7C_PARTS// /}" ]; then
  echo "[run_e7c] E7C_PART must name the part(s) to run: gate lag" >&2
  exit 2
fi
for part in $E7C_PARTS; do
  case "$part" in
    gate | lag) ;;
    *) echo "[run_e7c] unknown part '$part'" >&2; exit 2 ;;
  esac
done
E7C_ONLY="${E7C_ONLY:-}"
if [ -n "$E7C_ONLY" ]; then
  printf '' | grep -Eq -- "$E7C_ONLY" 2> /dev/null
  [ $? -eq 2 ] && { echo "[run_e7c] E7C_ONLY is not a valid extended regex: '$E7C_ONLY'" >&2; exit 2; }
fi
source "$(dirname "$0")/ms3_lib.sh"

e7c_check_start() {   # 0 iff the part's gate lets it start (e7c --check-start in a 3G scope; its lines to the log)
  local -a MS3_PRE
  _ms3_prefix
  "${MS3_PRE[@]}" "$MS3_PY" -m "$MS3_MODULE" --check-start 2>&1 | tee -a "$MS3_LOG"
  return "${PIPESTATUS[0]}"
}

e7c_only() {          # keep the list lines that match E7C_ONLY (tests and smoke runs)
  [ -n "$E7C_ONLY" ] || return 0
  mv "$MS3_OUT/jobs_list.txt" "$MS3_OUT/jobs_list_all.txt"
  grep -E -- "$E7C_ONLY" "$MS3_OUT/jobs_list_all.txt" > "$MS3_OUT/jobs_list.txt"
  _ms3_log "E7C_ONLY='$E7C_ONLY': $(wc -l < "$MS3_OUT/jobs_list.txt") of $(wc -l < "$MS3_OUT/jobs_list_all.txt") jobs"
}

e7c_retry() {         # the missing-run rule's rerun: once per pool job
  local -a MS3_PRE
  _ms3_prefix
  if ! "${MS3_PRE[@]}" "$MS3_PY" -m "$MS3_MODULE" --retry-list --out "$MS3_OUT" > "$MS3_OUT/jobs_retry.txt" \
      2>> "$MS3_LOG"; then
    _ms3_log "could not list the jobs to rerun"
    return 0
  fi
  if [ -n "$E7C_ONLY" ]; then
    grep -E -- "$E7C_ONLY" "$MS3_OUT/jobs_retry.txt" > "$MS3_OUT/jobs_retry_only.txt" || true
    mv "$MS3_OUT/jobs_retry_only.txt" "$MS3_OUT/jobs_retry.txt"
  fi
  _ms3_log "rerun once (design/sublet_v2.md §4.5): $(grep -c '^pool ' "$MS3_OUT/jobs_retry.txt") pool job(s)"
  [ -s "$MS3_OUT/jobs_retry.txt" ] || return 0
  mv "$MS3_OUT/jobs_list.txt" "$MS3_OUT/jobs_list_full.txt"
  cp "$MS3_OUT/jobs_retry.txt" "$MS3_OUT/jobs_list.txt"
  ms3_run_jobs pool
  mv "$MS3_OUT/jobs_list_full.txt" "$MS3_OUT/jobs_list.txt"
}

for part in $E7C_PARTS; do
  export E7C_PART="$part"
  MS3_OUT="$MS3_ROOT/out/e7c/$part"
  ms3_init e7c
  _ms3_log "part $part"
  if ! e7c_check_start; then
    _ms3_log "refused: part $part does not start (design/ms7/plan.md D6)"
    exit 2
  fi
  ms3_list
  e7c_only
  ms3_manifest
  ms3_run_jobs pool
  e7c_retry
  ms3_manifest
  ms3_summary
  ms3_finish
done
