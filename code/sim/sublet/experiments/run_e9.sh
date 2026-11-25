#!/usr/bin/env bash
# E9: scalability (design/sim_spec_ms5.md §5; deliverable D41, unit U28). Runs every job of sublet.experiments.e9 alone
# (§0 item 3, M24): each job holds every slot of ms3_lib.sh's host-wide semaphore (its turnstile serves a waiting
# 'alone' job first), runs in its own 3G scope, and runs under its own limit (§5.7):
#   /usr/bin/time ... systemd-run --user --scope -q -p MemoryMax=3G -p MemorySwapMax=0
#       env OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 timeout --foreground -k 30 $((LIMIT + 60)) $PY -m ... --job ID
# with LIMIT the job's limit from `python -m sublet.experiments.e9 --limits` ($MS3_OUT/jobs_limits.txt: measurement 4's
# case limits for the runs, 900 s by default, and 1800 s for the LPs), as ms3_lib.sh runs a MILP job; a job that exits
# nonzero or leaves no 'ok' record is classified by `ms3_common --record-failure ... --limit LIMIT` (exit 124, or 137 at
# LIMIT + 60 s or later: wall_limit; other 137: oom_at_3G; never retried at a larger cap). The jobs run one at a time
# in the order of jobs_list.txt (the runs in the order of the points, then the LPs), between the job list, the
# manifest (twice) and the summary (code/sim/out/e9/summary.json, tables.md), then ms3_finish's done line.
# Run it after run_s1.sh has finished, with nothing else on the host (§1.2 item 4); every job records the load average
# at its start, and the run log warns when it exceeds E9_LOAD_WARN (default 1.5) at a job's start.
#
#   sublet/experiments/run_e9.sh [--reduced]
#
# --reduced: the reduced job list of e9.py's docstring (MS3_E9_REDUCED=1: every point and job kind, alignment 1, policy
# seed 0, a 2-hour horizon); for smoke runs under a scratch MS3_ROOT, never a result. Environment as ms3_lib.sh
# (MS3_WORKERS, MS3_RESUME, MS3_ROOT, MS3_OUT, MS3_PY, MS3_MODULE, MS3_SCOPE, ...), plus, for tests and smoke runs
# only: E9_ONLY=<extended regex> runs only the jobs whose id matches (the summary lists the others as missing), and
# MS3_E9_TEST_GRACE_S replaces the 60-s grace of the timeout (LIMIT + grace; the classification keeps LIMIT).
set -u
for arg in "$@"; do
  case "$arg" in
    --reduced) export MS3_E9_REDUCED=1 ;;
    *) echo "usage: $0 [--reduced]" >&2; exit 2 ;;
  esac
done
source "$(dirname "$0")/ms3_lib.sh"
E9_GRACE_S="${MS3_E9_TEST_GRACE_S:-$MS3_WALL_GRACE_S}"
E9_LOAD_WARN="${E9_LOAD_WARN:-1.5}"
E9_ONLY="${E9_ONLY:-}"
if [ -n "$E9_ONLY" ]; then
  printf '' | grep -Eq -- "$E9_ONLY" 2> /dev/null
  [ $? -eq 2 ] && { echo "[run_e9] E9_ONLY is not a valid extended regex: '$E9_ONLY'" >&2; exit 2; }
fi

e9_limits() {         # the job limits '<limit s> <job id>' into $MS3_OUT/jobs_limits.txt (3G scope, no slot)
  local -a MS3_PRE
  _ms3_prefix
  if ! "${MS3_PRE[@]}" "$MS3_PY" -m "$MS3_MODULE" --limits > "$MS3_OUT/jobs_limits.txt" 2>> "$MS3_LOG"; then
    _ms3_log "could not list the job limits of $MS3_EXP"
    exit 1
  fi
}

_e9_launch_body() {   # _e9_launch_body JOB LIMIT: ms3_lib.sh's _ms3_launch_body for an 'alone' job under its limit
  local job="$1" limit="$2"
  local name tf rc kb="" el="" load
  name="$(ms3_job_name "$job")"
  cd "$MS3_CODE" || exit 1
  mkdir -p "$MS3_SLOT_DIR" "$MS3_OUT/logs" "$MS3_OUT/jobs"
  _ms3_acquire alone
  export MS3_SLOTS
  local -a MS3_PRE
  _ms3_prefix
  MS3_PRE+=(timeout --foreground -k "$MS3_KILL_AFTER_S" "$((limit + E9_GRACE_S))")
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

e9_run_jobs() {       # every 'alone' job of jobs_list.txt in its order, one at a time, each under its limit
  local kind job limit n=0
  [ -n "$E9_ONLY" ] && _ms3_log "E9_ONLY='$E9_ONLY': only the matching jobs run"
  while read -r kind job; do
    [ "$kind" = alone ] || continue
    if [ -n "$E9_ONLY" ] && ! printf '%s\n' "$job" | grep -Eq -- "$E9_ONLY"; then continue; fi
    if ms3_done "$job"; then _ms3_log "$job: ok before, skipped"; continue; fi
    limit="$(awk -v j="$job" '$2 == j { print $1; exit }' "$MS3_OUT/jobs_limits.txt")"
    case "$limit" in
      '' | *[!0-9]*) _ms3_log "$job: no limit in jobs_limits.txt, not run"; continue ;;
    esac
    (_e9_launch_body "$job" "$limit") < /dev/null &
    MS3_LAST_PID=$!
    wait "$MS3_LAST_PID"
    n=$((n + 1))
  done < "$MS3_OUT/jobs_list.txt"
  _ms3_log "alone jobs done ($n run) $(date -Is)"
}

ms3_init e9
ms3_list
e9_limits
ms3_manifest
e9_run_jobs
ms3_manifest
ms3_summary
ms3_finish
