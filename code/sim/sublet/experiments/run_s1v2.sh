#!/usr/bin/env bash
# S1 v2: Sublet's own sensitivity with A9 and the two strongest baselines (design/ms7/plan.md X3; change C56). Runs the
# jobs of sublet.experiments.s1v2 under the slot semaphore shared with MS3-MS5b (ms3_lib.sh: one 3G scope per job, at
# most 4 jobs on the host), one part after another, each part with its own output folder (MS3_OUT =
# out/s1v2/<part>: jobs/, logs/, runs/, manifest.json, summary.json, tables.md, run_s1v2.log;
# ms3_common.COPY_PARTS['s1v2']):
#   pass 1, the jobs of each part of S1V2_PART (default "sweep w0", in that order): the gate (`s1v2 --check-start`: a
#           full run refuses to start unless design/ms7/registration.md exists at HEAD with the sha256 of
#           experiments/ms7_sens_analysis.py and the working tree is clean; exit 2 when refused), the job list, the job
#           limits, the manifest, then the pool jobs, each with its limit LIMIT from `--limits` (three times its
#           estimate, at least 1,800 s);
#   pass 2, the summaries of the same parts: the manifest again and the summary, then ms3_finish's done line.
# Each pool job runs as run_s1.sh runs its jobs (_s1v2_launch_body below): `timeout --foreground -k 30 $((LIMIT + 60))`
# inside its 3G scope, and a job that exits nonzero or leaves no 'ok' record is classified by `ms3_common
# --record-failure ... --limit LIMIT` (exit 124, or 137 at LIMIT + 60 s or later: wall_limit; other 137: oom_at_3G;
# never retried at a larger cap). The analysis (python -m sublet.experiments.ms7_sens_analysis --exp s1v2) runs after
# this script, in the same clone, before the copy.
#
#   S1V2_PART="sweep w0" sublet/experiments/run_s1v2.sh [--reduced]
#
# --reduced: the reduced job lists of s1v2.py's docstring (MS3_S1V2_REDUCED=1: development week 101, policy seed 0, a
# 2-hour horizon; the gate is recorded, not enforced); for smoke runs under a scratch MS3_ROOT, never a result.
# Environment as ms3_lib.sh (MS3_WORKERS, MS3_RESUME, MS3_ROOT, ...; MS3_OUT is set per part here), plus, for tests and
# smoke runs only: S1V2_ONLY=<extended regex> runs only the jobs whose id matches (the summaries list the others as
# missing), and MS3_S1V2_TEST_GRACE_S replaces the 60-s grace of the timeout.
set -u
for arg in "$@"; do
  case "$arg" in
    --reduced) export MS3_S1V2_REDUCED=1 ;;
    *) echo "usage: S1V2_PART=<parts> $0 [--reduced]" >&2; exit 2 ;;
  esac
done
S1V2_PARTS="${S1V2_PART:-sweep w0}"
S1V2_PARTS="${S1V2_PARTS//,/ }"
for part in $S1V2_PARTS; do
  case "$part" in
    sweep | w0) ;;
    *) echo "[run_s1v2] unknown part '$part' (sweep, w0)" >&2; exit 2 ;;
  esac
done
source "$(dirname "$0")/ms3_lib.sh"
S1V2_GRACE_S="${MS3_S1V2_TEST_GRACE_S:-$MS3_WALL_GRACE_S}"
S1V2_ONLY="${S1V2_ONLY:-}"
if [ -n "$S1V2_ONLY" ]; then
  printf '' | grep -Eq -- "$S1V2_ONLY" 2> /dev/null
  [ $? -eq 2 ] && { echo "[run_s1v2] S1V2_ONLY is not a valid extended regex: '$S1V2_ONLY'" >&2; exit 2; }
fi

s1v2_check_start() {  # 0 iff the gate lets the part start (s1v2 --check-start in a 3G scope; its lines to the log)
  local -a MS3_PRE
  _ms3_prefix
  "${MS3_PRE[@]}" "$MS3_PY" -m "$MS3_MODULE" --check-start 2>&1 | tee -a "$MS3_LOG"
  return "${PIPESTATUS[0]}"
}

s1v2_limits() {       # '<kind> <limit_s> <job id>' per job into $MS3_OUT/jobs_limits.txt (3G scope, as ms3_list)
  local -a MS3_PRE
  _ms3_prefix
  if ! "${MS3_PRE[@]}" "$MS3_PY" -m "$MS3_MODULE" --limits > "$MS3_OUT/jobs_limits.txt" 2>> "$MS3_LOG"; then
    _ms3_log "could not list the job limits of $MS3_EXP"
    exit 1
  fi
  _ms3_log "$(grep -c '^pool ' "$MS3_OUT/jobs_limits.txt") pool jobs with limits" \
    "$(awk '{print $2}' "$MS3_OUT/jobs_limits.txt" | sort -n | uniq | tr '\n' ' ')s"
}

_s1v2_launch_body() { # _s1v2_launch_body JOB LIMIT: ms3_lib.sh's _ms3_launch_body for a pool job under its limit
  local job="$1" limit="$2"
  local name tf rc kb="" el=""
  name="$(ms3_job_name "$job")"
  cd "$MS3_CODE" || exit 1
  mkdir -p "$MS3_SLOT_DIR" "$MS3_OUT/logs" "$MS3_OUT/jobs"
  _ms3_acquire pool
  export MS3_SLOTS
  local -a MS3_PRE
  _ms3_prefix
  MS3_PRE+=(timeout --foreground -k "$MS3_KILL_AFTER_S" "$((limit + S1V2_GRACE_S))")
  tf="$MS3_OUT/logs/$name.time"
  echo "[$MS3_TAG] pool $job holds $MS3_SLOTS, limit $limit s $(date -Is)" >> "$MS3_LOG"
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

s1v2_run_jobs() {     # every pool job of jobs_limits.txt under its limit, as ms3_run_jobs pool, then wait
  local kind limit job running=0
  [ -n "$S1V2_ONLY" ] && _ms3_log "S1V2_ONLY='$S1V2_ONLY': only the matching jobs run"
  while read -r kind limit job; do
    [ "$kind" = pool ] || continue
    if [ -n "$S1V2_ONLY" ] && ! printf '%s\n' "$job" | grep -Eq -- "$S1V2_ONLY"; then continue; fi
    if ms3_done "$job"; then _ms3_log "$job: ok before, skipped"; continue; fi
    case "$limit" in
      '' | *[!0-9]*) _ms3_log "$job: no limit in jobs_limits.txt, not run"; continue ;;
    esac
    while [ "$running" -ge "$MS3_N_SLOTS" ]; do
      wait -n
      running=$((running - 1))
    done
    (_s1v2_launch_body "$job" "$limit") < /dev/null &
    MS3_LAST_PID=$!
    running=$((running + 1))
  done < "$MS3_OUT/jobs_limits.txt"
  wait
  _ms3_log "pool jobs done $(date -Is)"
}

for part in $S1V2_PARTS; do
  export S1V2_PART="$part"
  MS3_OUT="$MS3_ROOT/out/s1v2/$part"
  ms3_init s1v2
  _ms3_log "pass 1 (jobs), part $part"
  if ! s1v2_check_start; then
    _ms3_log "refused: part $part does not start (design/ms7/plan.md D6)"
    exit 2
  fi
  ms3_list
  s1v2_limits
  ms3_manifest
  s1v2_run_jobs
done
for part in $S1V2_PARTS; do
  export S1V2_PART="$part"
  MS3_OUT="$MS3_ROOT/out/s1v2/$part"
  ms3_init s1v2
  _ms3_log "pass 2 (summary), part $part"
  ms3_manifest
  ms3_summary
  ms3_finish
done
