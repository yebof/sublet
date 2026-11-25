# shellcheck shell=bash
# MS3 run-script library (design/sim_spec_ms3.md §2.4, §2.5, §0 items 2-3; M3, M43, M44). Sourced, never run,
# by every sublet/experiments/run_<exp>.sh, which follows run_q44_study.sh:
#
#   #!/usr/bin/env bash
#   set -u
#   source "$(dirname "$0")/ms3_lib.sh"
#   ms3_init e1                # cd code/sim; exits 2 with "E11 has not finished (§3.2)" while N = 0
#   ms3_list                   # $MS3_OUT/jobs_list.txt from 'python -m sublet.experiments.e1 --list' (3G scope)
#   ms3_manifest               # '--manifest' in its own 3G scope, holding one slot (it builds the instances)
#   ms3_run_jobs pool          # every pool job (at most 4 launches of this script waiting or running)
#   ms3_run_jobs alone         # one at a time, each holding every slot
#   ms3_run_jobs milp          # each under the hard wall-clock limit (at most 2 launches of this script)
#   ms3_manifest
#   ms3_summary                # '--summary' in its own 3G scope, holding one slot
#   ms3_finish
#
# Slot semaphore (§2.4, M44). Lock files $MS3_ROOT/out/.ms3_slots/slot0 ... slot3 and milp0, milp1, taken
# with flock by the background subshell of `launch` and released when that subshell exits, also when the job
# is killed (the job inherits the descriptors, so a slot stays taken while its job runs). N is
# `python -m sublet.experiments.ms3_common --max-workers` = min(MS3_WORKERS, 4), or 0 while this repository's
# code/sim/out/e11/summary.json is missing; `launch` re-reads it every MS3_POLL_S seconds (default 10) until it
# holds one of slot0 ... slot<N-1> (with flock -n) and, for a milp job, also one of milp0, milp1 (it gives
# the slot back if no MILP lock is free, so a waiting MILP blocks no other job). A job of kind 'alone' takes
# slot0 ... slot<N-1> in index order and keeps what it holds, which cannot deadlock against single-slot jobs
# (they never wait while holding a lock). So the host never runs more than 4 MS3 jobs nor more than 2 MILP
# jobs, whatever the number of run scripts. A run script is never edited while it runs (§0 item 3).
#
# Turnstile (throughput only). A waiting 'alone' job first takes the lock file gate exclusively (flock -n -x)
# and collects slots only while it holds it; it gives the gate back once it holds every slot, before its job
# starts. A pool or milp launch tries the slots only under a shared lock on gate (flock -n -s), released right
# after the try, and sleeps while the gate is taken. So every slot freed while an 'alone' job waits goes to that
# job instead of to the next pool job of another run script, and the slots it already holds do not stay idle
# for more than the longest job then running. A running job holds no lock on gate, so this adds no waiting
# between jobs that hold slots, and the order of the slots is unchanged, so no deadlock.
#
# Jobs (§0 item 2, §2.5). Every job runs as
#   /usr/bin/time ... systemd-run --user --scope -q -p MemoryMax=3G -p MemorySwapMax=0
#       env OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 [timeout --foreground -k 30 $((LIMIT + 60))] $PY -m ... --job ID
# with `timeout` for milp jobs only (LIMIT = MS3_MILP_LIMIT, default 300 s, HiGHS's own time_limit_s, M3).
# --foreground: timeout signals only the job (a MILP job is one process) and reaps it also after its SIGKILL,
# so /usr/bin/time's %M is the job's peak RSS (without it timeout kills its own process group, itself included,
# before it reaps the job, and %M is timeout's own RSS); the exit codes stay 124 (SIGTERM) and 137 (SIGKILL).
# The job list (--list) runs in the same 3G scope (no slot); the manifest (--manifest), which builds the
# experiment's instances for their hashes, runs through `launch` like a pool job (record <exp>:manifest).
# The cap is never raised. The console output goes to logs/<job>.log, the line
#   [time] <job> peak RSS <KB>, <s> s, exit <code>
# to $MS3_OUT/run_<exp>.log; a job that exits nonzero or leaves no 'ok' record is classified by
# `ms3_common --record-failure` (exit 124 or 137 at LIMIT + 60 s or later: wall_limit; other 137: oom_at_3G,
# not retried). With MS3_RESUME=1 a job whose record says 'ok' is skipped (M43). Processes are killed only by
# PID, never with pkill -f or pgrep -f.
#
# Variables (environment, before sourcing): MS3_HOST_SLOTS (MS7 C57: the host's slots, 1..6, default 4; every
# run script on the host must see the same value), MS3_WORKERS (default and at most MS3_HOST_SLOTS), MS3_RESUME,
# MS3_MILP_LIMIT,
# MS3_POLL_S, MS3_PY (default ~/venv/bin/python), MS3_OUT (default $MS3_ROOT/out/<exp>; relative to code/sim);
# for tests only: MS3_ROOT (a folder used in place of this repository's code/sim for out/, so also for the lock
# files and e11/summary.json), MS3_MODULE (the driver module, default sublet.experiments.<exp>) and MS3_SCOPE=0
# (no systemd scope, for hosts without a user manager).

MS3_CODE="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"          # code/sim (the package)
MS3_ROOT="$(cd "${MS3_ROOT:-$MS3_CODE}" && pwd)"
MS3_PY="${MS3_PY:-$HOME/venv/bin/python}"
MS3_SLOT_DIR="$MS3_ROOT/out/.ms3_slots"
MS3_N_SLOTS="${MS3_HOST_SLOTS:-4}"   # MS7 addition C57: MS3_HOST_SLOTS in 1..6 (ms3_common.host_slots), default 4
case "$MS3_N_SLOTS" in [1-6]) ;; *) echo "ms3_lib: MS3_HOST_SLOTS must be in 1..6, got $MS3_N_SLOTS" >&2; exit 2 ;; esac
export MS3_HOST_SLOTS="$MS3_N_SLOTS"
MS3_N_MILP=2
MS3_MILP_LIMIT="${MS3_MILP_LIMIT:-300}"
MS3_WALL_GRACE_S=60
MS3_KILL_AFTER_S=30
MS3_POLL_S="${MS3_POLL_S:-10}"
MS3_SCOPE_CMD=(systemd-run --user --scope -q -p MemoryMax=3G -p MemorySwapMax=0
               env OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1)
MS3_LAST_PID=""
export OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 MS3_ROOT MS3_MILP_LIMIT

ms3_max_workers() {   # print N (fails if the helper cannot run)
  (cd "$MS3_CODE" && "$MS3_PY" -m sublet.experiments.ms3_common --max-workers --root "$MS3_ROOT")
}

ms3_job_name() {      # the record's file stem: q44_study.job_file_name's rule
  printf '%s' "$1" | LC_ALL=C sed -E 's/[^A-Za-z0-9_.-]+/__/g'
}

_ms3_log() {          # a line to the console and the run log
  echo "[${MS3_TAG:-ms3}] $*" | tee -a "$MS3_LOG"
}

ms3_init() {          # ms3_init EXP: output folders, the run log; exit 2 while N = 0
  MS3_EXP="$1"
  MS3_TAG="run_$MS3_EXP"
  MS3_MODULE="${MS3_MODULE:-sublet.experiments.$MS3_EXP}"
  cd "$MS3_CODE" || exit 1
  MS3_OUT="$(realpath -m "${MS3_OUT:-$MS3_ROOT/out/$MS3_EXP}")"
  MS3_LOG="$MS3_OUT/run_$MS3_EXP.log"
  local n
  if ! n="$(ms3_max_workers)"; then
    echo "[$MS3_TAG] could not read the slot count (python -m sublet.experiments.ms3_common --max-workers)" >&2
    exit 1
  fi
  if [ "$n" -eq 0 ]; then
    echo "[$MS3_TAG] E11 has not finished (§3.2): no $MS3_ROOT/out/e11/summary.json, so no MS3 job runs"
    exit 2
  fi
  mkdir -p "$MS3_OUT/jobs" "$MS3_OUT/logs" "$MS3_SLOT_DIR"
  export MS3_OUT
  _ms3_log "start $(date -Is) on $(hostname): $n slot(s) now, out $MS3_OUT"
}

_ms3_prefix() {       # MS3_PRE=(the 3G scope command), or the environment only with MS3_SCOPE=0 (tests)
  if [ "${MS3_SCOPE:-1}" = "0" ]; then
    MS3_PRE=(env OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1)
  else
    MS3_PRE=("${MS3_SCOPE_CMD[@]}")
  fi
}

ms3_list() {          # the job list '<kind> <id>' of the experiment into $MS3_OUT/jobs_list.txt (3G scope)
  local -a MS3_PRE
  _ms3_prefix
  if ! "${MS3_PRE[@]}" "$MS3_PY" -m "$MS3_MODULE" --list > "$MS3_OUT/jobs_list.txt" 2>> "$MS3_LOG"; then
    _ms3_log "could not list the jobs of $MS3_EXP"
    exit 1
  fi
  _ms3_log "$(grep -c '^pool ' "$MS3_OUT/jobs_list.txt") pool, $(grep -c '^alone ' "$MS3_OUT/jobs_list.txt") alone," \
    "$(grep -c '^milp ' "$MS3_OUT/jobs_list.txt") milp jobs"
}

ms3_manifest() {      # manifest.json in its own 3G scope, holding one slot like any job (record <exp>:manifest)
  launch pool "$MS3_EXP:manifest" "$MS3_PY" -m "$MS3_MODULE" --manifest --out "$MS3_OUT"
  wait "$MS3_LAST_PID"
  _ms3_record_ok "$MS3_EXP:manifest" \
    || _ms3_log "manifest failed (see logs/$(ms3_job_name "$MS3_EXP:manifest").log)"
}

ms3_done() {          # 0 iff MS3_RESUME=1 and the job's record says ok
  [ "${MS3_RESUME:-0}" = "1" ] || return 1
  _ms3_record_ok "$1"
}

_ms3_record_ok() {    # the record's top-level status (indent 1, as ms3_common.dump_json writes it) is ok
  local f
  f="$MS3_OUT/jobs/$(ms3_job_name "$1").json"
  [ -s "$f" ] && grep -qE '^ "status": "ok",?$' "$f"
}

_ms3_acquire() {      # _ms3_acquire KIND: wait until the locks are held; sets MS3_SLOTS (in this subshell)
  local kind="$1" n i j fd mfd gfd="" all ok
  local -a held=()
  while :; do
    n="$(ms3_max_workers 2> /dev/null)" || n=0
    case "$n" in '' | *[!0-9]*) n=0 ;; esac
    [ "$n" -gt "$MS3_N_SLOTS" ] && n=$MS3_N_SLOTS
    if [ "$n" -gt 0 ]; then
      if [ "$kind" = alone ]; then
        if [ -z "$gfd" ]; then        # the turnstile, held from the first slot to the last
          exec {gfd}>> "$MS3_SLOT_DIR/gate"
          if ! flock -n -x "$gfd"; then exec {gfd}>&-; gfd=""; fi
        fi
        if [ -n "$gfd" ]; then
          ok=1
          for ((i = 0; i < n; i++)); do
            [ -n "${held[$i]:-}" ] && continue
            exec {fd}>> "$MS3_SLOT_DIR/slot$i"
            if flock -n "$fd"; then held[$i]=$fd; else exec {fd}>&-; ok=0; break; fi
          done
          if [ "$ok" -eq 1 ]; then
            exec {gfd}>&-             # every slot held: the gate opens before the job starts
            all=""
            for i in "${!held[@]}"; do all="${all:+$all,}slot$i"; done
            MS3_SLOTS="$all"
            return 0
          fi
        fi
      else
        exec {gfd}>> "$MS3_SLOT_DIR/gate"
        if flock -n -s "$gfd"; then   # no 'alone' job is collecting slots
          for ((i = 0; i < n; i++)); do
            exec {fd}>> "$MS3_SLOT_DIR/slot$i"
            if flock -n "$fd"; then
              if [ "$kind" != milp ]; then exec {gfd}>&-; MS3_SLOTS="slot$i"; return 0; fi
              for ((j = 0; j < MS3_N_MILP; j++)); do
                exec {mfd}>> "$MS3_SLOT_DIR/milp$j"
                if flock -n "$mfd"; then exec {gfd}>&-; MS3_SLOTS="slot$i,milp$j"; return 0; fi
                exec {mfd}>&-
              done
              exec {fd}>&-            # no MILP lock free: give the slot back and wait
              break
            fi
            exec {fd}>&-
          done
        fi
        exec {gfd}>&-                 # the shared lock on the gate is never kept while waiting or running
      fi
    fi
    sleep "$MS3_POLL_S"
  done
}

_ms3_launch_body() {  # runs in the background subshell of `launch`
  local kind="$1" job="$2"
  shift 2
  local name tf rc kb="" el="" limit=""
  name="$(ms3_job_name "$job")"
  cd "$MS3_CODE" || exit 1
  mkdir -p "$MS3_SLOT_DIR" "$MS3_OUT/logs" "$MS3_OUT/jobs"
  _ms3_acquire "$kind"
  export MS3_SLOTS
  local -a MS3_PRE
  _ms3_prefix
  if [ "$kind" = milp ]; then
    limit="$MS3_MILP_LIMIT"
    MS3_PRE+=(timeout --foreground -k "$MS3_KILL_AFTER_S" "$((MS3_MILP_LIMIT + MS3_WALL_GRACE_S))")
  fi
  tf="$MS3_OUT/logs/$name.time"
  echo "[$MS3_TAG] $kind $job holds $MS3_SLOTS $(date -Is)" >> "$MS3_LOG"
  /usr/bin/time -o "$tf" -f "%M %e" "${MS3_PRE[@]}" "$@" > "$MS3_OUT/logs/$name.log" 2>&1 < /dev/null
  rc=$?
  read -r kb el < <(tail -n 1 "$tf" 2> /dev/null) || true
  case "$kb" in '' | *[!0-9]*) kb="" ;; esac
  case "$el" in '' | *[!0-9.]*) el="" ;; esac
  echo "[time] $job peak RSS ${kb:-?} KB, ${el:-?} s, exit $rc" >> "$MS3_LOG"
  if [ "$rc" -ne 0 ] || ! _ms3_record_ok "$job"; then
    local -a args=(--record-failure "$job" --out "$MS3_OUT" --exit-code "$rc" --slots "$MS3_SLOTS")
    [ -n "$el" ] && args+=(--elapsed "$el")
    [ -n "$kb" ] && args+=(--peak-kb "$kb")
    [ -n "$limit" ] && args+=(--limit "$limit")
    "$MS3_PY" -m sublet.experiments.ms3_common "${args[@]}" >> "$MS3_LOG" 2>&1
  fi
  exit 0              # the locks are released here
}

launch() {            # launch KIND JOB [CMD ...]: run one job in a background subshell under the semaphore
  local kind="$1" job="$2"
  shift 2
  case "$kind" in
    pool | alone | milp) ;;
    *) echo "[ms3_lib] launch: unknown kind '$kind' (pool, alone, milp)" >&2; return 2 ;;
  esac
  if [ "$#" -eq 0 ]; then
    set -- "$MS3_PY" -m "$MS3_MODULE" --job "$job" --out "$MS3_OUT"
  fi
  (_ms3_launch_body "$kind" "$job" "$@") < /dev/null &
  MS3_LAST_PID=$!
}

ms3_run_jobs() {      # ms3_run_jobs KIND: every job of that kind in $MS3_OUT/jobs_list.txt, then wait
  local want="$1" kind job cap running=0
  case "$want" in
    pool) cap=$MS3_N_SLOTS ;;
    milp) cap=$MS3_N_MILP ;;
    alone) cap=1 ;;
    *) echo "[ms3_lib] ms3_run_jobs: unknown kind '$want'" >&2; return 2 ;;
  esac
  while read -r kind job; do
    [ "$kind" = "$want" ] || continue
    if ms3_done "$job"; then _ms3_log "$job: ok before, skipped"; continue; fi
    while [ "$running" -ge "$cap" ]; do
      wait -n
      running=$((running - 1))
    done
    launch "$kind" "$job"
    running=$((running + 1))
  done < "$MS3_OUT/jobs_list.txt"
  wait
  _ms3_log "$want jobs done $(date -Is)"
}

ms3_summary() {       # the summary in its own 3G scope, holding one slot like any job
  launch pool "$MS3_EXP:summary" "$MS3_PY" -m "$MS3_MODULE" --summary --out "$MS3_OUT"
  wait "$MS3_LAST_PID"
}

ms3_finish() {
  _ms3_log "done $(date -Is)"
}
