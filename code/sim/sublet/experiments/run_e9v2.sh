#!/usr/bin/env bash
# E9 v2: scalability of Sublet itself and the guard's per-slot overhead over A9 (design/ms7/plan.md X3; change C56).
# Runs every job of sublet.experiments.e9v2 alone, as run_e9.sh runs E9's: each job holds every slot of ms3_lib.sh's
# host-wide semaphore, runs in its own 3G scope and under its own limit,
#   /usr/bin/time ... systemd-run --user --scope -q -p MemoryMax=3G -p MemorySwapMax=0
#       env OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 timeout --foreground -k 30 $((LIMIT + 60)) $PY -m ... --job ID
# and a job that exits nonzero or leaves no 'ok' record is classified by `ms3_common --record-failure ... --limit
# LIMIT` (exit 124, or 137 at LIMIT + 60 s or later: wall_limit; other 137: oom_at_3G; never retried at a larger cap).
# Order: the gate (`e9v2 --check-start`: a full run refuses to start unless design/ms7/registration.md exists at HEAD
# with the sha256 of experiments/ms7_sens_analysis.py and the working tree is clean; exit 2 when refused), the job
# list, the limits, the manifest; pass 1, the first job (e9v2.FIRST_JOB: e7f_V64_SML, Sublet, c 1) alone under
# FIRST_LIMIT_S, timed; then the limits again (`e9v2 --limits --out`: now scaled by the first job's wall time over its
# estimate, never below the static limits); pass 2, every other job in the order of jobs_list.txt; the manifest again,
# the summary (out/e9v2/summary.json, tables.md) and ms3_finish's done line. Run it last, after run_s1v2.sh, with
# nothing else on the host; every job records the load average at its start, and the run log warns when it exceeds
# E9_LOAD_WARN (default 1.5). The analysis (python -m sublet.experiments.ms7_sens_analysis --exp e9v2) runs after it.
#
#   sublet/experiments/run_e9v2.sh [--reduced]
#
# --reduced: the reduced job list of e9v2.py's docstring (MS3_E9V2_REDUCED=1: every point and kind, alignment 1, a
# 2-hour horizon; the gate is recorded, not enforced); for smoke runs under a scratch MS3_ROOT, never a result.
# Environment as ms3_lib.sh, plus, for tests and smoke runs only: E9V2_ONLY=<extended regex> runs only the jobs whose
# id matches, and MS3_E9V2_TEST_GRACE_S replaces the 60-s grace of the timeout.
set -u
for arg in "$@"; do
  case "$arg" in
    --reduced) export MS3_E9V2_REDUCED=1 ;;
    *) echo "usage: $0 [--reduced]" >&2; exit 2 ;;
  esac
done
source "$(dirname "$0")/ms3_lib.sh"
E9V2_GRACE_S="${MS3_E9V2_TEST_GRACE_S:-$MS3_WALL_GRACE_S}"
E9_LOAD_WARN="${E9_LOAD_WARN:-1.5}"
E9V2_ONLY="${E9V2_ONLY:-}"
if [ -n "$E9V2_ONLY" ]; then
  printf '' | grep -Eq -- "$E9V2_ONLY" 2> /dev/null
  [ $? -eq 2 ] && { echo "[run_e9v2] E9V2_ONLY is not a valid extended regex: '$E9V2_ONLY'" >&2; exit 2; }
fi

e9v2_check_start() {  # 0 iff the gate lets the run start (e9v2 --check-start in a 3G scope; its lines to the log)
  local -a MS3_PRE
  _ms3_prefix
  "${MS3_PRE[@]}" "$MS3_PY" -m "$MS3_MODULE" --check-start 2>&1 | tee -a "$MS3_LOG"
  return "${PIPESTATUS[0]}"
}

e9v2_limits() {       # the job limits '<limit s> <job id>' into $MS3_OUT/jobs_limits.txt (3G scope, no slot)
  local -a MS3_PRE
  _ms3_prefix
  if ! "${MS3_PRE[@]}" "$MS3_PY" -m "$MS3_MODULE" --limits --out "$MS3_OUT" > "$MS3_OUT/jobs_limits.txt" \
      2>> "$MS3_LOG"; then
    _ms3_log "could not list the job limits of $MS3_EXP"
    exit 1
  fi
}

_e9v2_launch_body() { # _e9v2_launch_body JOB LIMIT: ms3_lib.sh's _ms3_launch_body for an 'alone' job under its limit
  local job="$1" limit="$2"
  local name tf rc kb="" el="" load
  name="$(ms3_job_name "$job")"
  cd "$MS3_CODE" || exit 1
  mkdir -p "$MS3_SLOT_DIR" "$MS3_OUT/logs" "$MS3_OUT/jobs"
  _ms3_acquire alone
  export MS3_SLOTS
  local -a MS3_PRE
  _ms3_prefix
  MS3_PRE+=(timeout --foreground -k "$MS3_KILL_AFTER_S" "$((limit + E9V2_GRACE_S))")
  tf="$MS3_OUT/logs/$name.time"
  load="$(cut -d' ' -f1-3 /proc/loadavg 2> /dev/null)"
  echo "[$MS3_TAG] alone $job holds $MS3_SLOTS, limit $limit s, load $load $(date -Is)" >> "$MS3_LOG"
  if awk -v l="${load%% *}" -v w="$E9_LOAD_WARN" 'BEGIN { exit !(l + 0 > w + 0) }'; then
    echo "[$MS3_TAG] warning: $job must run alone, but the load average is ${load%% *} (> $E9_LOAD_WARN)" >> "$MS3_LOG"
  fi
  /usr/bin/time -o "$tf" -f "%M %e" "${MS3_PRE[@]}" "$MS3_PY" -m "$MS3_MODULE" --job "$job" --out "$MS3_OUT" \
    > "$MS3_OUT/logs/$name.log" 2>&1 < /dev/null
  rc=$?
  read -r kb el < <(tail -n 1 "$tf" 2> /dev/null) || true
  case "$kb" in '' | *[!0-9]*) kb="" ;; esac
  case "$el" in '' | *[!0-9.]*) el="" ;; esac
  echo "[time] $job peak RSS ${kb:-?} KB, ${el:-?} s, exit $rc" >> "$MS3_LOG"
  if [ "$rc" -ne 0 ] || ! _ms3_record_ok "$job"; then
    local -a args=(--record-failure "$job" --out "$MS3_OUT" --exit-code "$rc" --slots "$MS3_SLOTS" --limit "$limit")
    [ -n "$el" ] && args+=(--elapsed "$el")
    [ -n "$kb" ] && args+=(--peak-kb "$kb")
    "$MS3_PY" -m sublet.experiments.ms3_common "${args[@]}" >> "$MS3_LOG" 2>&1
  fi
  exit 0              # the locks are released here
}

e9v2_run_jobs() {     # e9v2_run_jobs WHICH: 'first' (only FIRST, the list's first line) or 'rest', one at a time
  local which="$1" kind job limit n=0 first t0
  first="$(awk 'NR == 1 { print $2; exit }' "$MS3_OUT/jobs_list.txt")"
  [ -n "$E9V2_ONLY" ] && _ms3_log "E9V2_ONLY='$E9V2_ONLY': only the matching jobs run"
  while read -r kind job; do
    [ "$kind" = alone ] || continue
    if [ "$which" = first ] && [ "$job" != "$first" ]; then continue; fi
    if [ "$which" = rest ] && [ "$job" = "$first" ]; then continue; fi
    if [ -n "$E9V2_ONLY" ] && ! printf '%s\n' "$job" | grep -Eq -- "$E9V2_ONLY"; then continue; fi
    if ms3_done "$job"; then _ms3_log "$job: ok before, skipped"; continue; fi
    limit="$(awk -v j="$job" '$2 == j { print $1; exit }' "$MS3_OUT/jobs_limits.txt")"
    case "$limit" in
      '' | *[!0-9]*) _ms3_log "$job: no limit in jobs_limits.txt, not run"; continue ;;
    esac
    t0=$SECONDS
    (_e9v2_launch_body "$job" "$limit") < /dev/null &
    MS3_LAST_PID=$!
    wait "$MS3_LAST_PID"
    n=$((n + 1))
    [ "$which" = first ] && _ms3_log "first job $job timed alone: $((SECONDS - t0)) s"
  done < "$MS3_OUT/jobs_list.txt"
  _ms3_log "alone jobs ($which) done ($n run) $(date -Is)"
}

ms3_init e9v2
if ! e9v2_check_start; then
  _ms3_log "refused: E9 v2 does not start (design/ms7/plan.md D6)"
  exit 2
fi
ms3_list
e9v2_limits
ms3_manifest
e9v2_run_jobs first
e9v2_limits
_ms3_log "limits after the first job: $(awk '{print $1}' "$MS3_OUT/jobs_limits.txt" | sort -n | uniq | tr '\n' ' ')s"
e9v2_run_jobs rest
ms3_manifest
ms3_summary
ms3_finish
