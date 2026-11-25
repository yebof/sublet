#!/usr/bin/env bash
# E8 v2 part (a): the request-level replay for Sublet itself, A9, BL1-BO and BL5-cur (design/ms7/plan.md X3; change
# C56). Runs the jobs of sublet.experiments.e8v2 under the MS3 slot semaphore (ms3_lib.sh: one 3G scope per job) with
# the output folder MS3_OUT = out/e8v2/a (ms3_common.COPY_PARTS['e8v2']), as run_e8.sh runs E8's: the gate (`e8v2
# --check-start`: a full run refuses to start unless design/ms7/registration.md exists at HEAD with the sha256 of
# experiments/ms7_sens_analysis.py and the working tree is clean; exit 2 when refused), the job list, the manifest,
# then three filtered passes: e8v2:requests, the request cache that every other job reads (rerun when its record is ok
# but its files are missing); the first e8v2:pair job alone (the job with the most copies), which is timed; the
# remaining e8v2:pair and e8v2:mooncake jobs. The replay passes do not run without an ok e8v2:requests and its cache
# files. Then the manifest again, the summary (out/e8v2/a/summary.json, tables.md) and ms3_finish's done line. The
# analysis (python -m sublet.experiments.ms7_sens_analysis --exp e8v2) runs after this script, in the same clone.
#
#   sublet/experiments/run_e8v2.sh [--reduced]
#
# --reduced: the reduced job list of e8v2.py's docstring (MS3_E8V2_REDUCED=1: 6 hours at market tightness 0.05; the
# gate is recorded, not enforced); for smoke runs under a scratch MS3_ROOT, never a result. Environment as ms3_lib.sh
# (MS3_WORKERS, MS3_RESUME, MS3_ROOT, ...; MS3_OUT is set here), plus, for tests and smoke runs only,
# E8V2_ONLY=<extended regex>: only the replay jobs whose list line matches run.
set -u
for arg in "$@"; do
  case "$arg" in
    --reduced) export MS3_E8V2_REDUCED=1 ;;
    *) echo "usage: $0 [--reduced]" >&2; exit 2 ;;
  esac
done
E8V2_ONLY="${E8V2_ONLY:-}"
if [ -n "$E8V2_ONLY" ]; then
  printf '' | grep -Eq -- "$E8V2_ONLY" 2> /dev/null
  [ $? -eq 2 ] && { echo "[run_e8v2] E8V2_ONLY is not a valid extended regex: '$E8V2_ONLY'" >&2; exit 2; }
fi
source "$(dirname "$0")/ms3_lib.sh"
MS3_OUT="$MS3_ROOT/out/e8v2/a"
ms3_init e8v2

e8v2_check_start() {  # 0 iff the gate lets the run start (e8v2 --check-start in a 3G scope; its lines to the log)
  local -a MS3_PRE
  _ms3_prefix
  "${MS3_PRE[@]}" "$MS3_PY" -m "$MS3_MODULE" --check-start 2>&1 | tee -a "$MS3_LOG"
  return "${PIPESTATUS[0]}"
}

_e8v2_cache_ok() {    # the request cache's record and arrays exist (replay.requests.cache_paths of azure2024_conv)
  local f
  for f in azure2024_conv.json azure2024_conv_t_s.npy azure2024_conv_inp.npy azure2024_conv_out.npy; do
    [ -s "$MS3_OUT/runs/requests/$f" ] || return 1
  done
}

if ! e8v2_check_start; then
  _ms3_log "refused: E8 v2 does not start (design/ms7/plan.md D6)"
  exit 2
fi
ms3_list
ms3_manifest
E8V2_FULL="$MS3_OUT/jobs_list_full.txt"
mv "$MS3_OUT/jobs_list.txt" "$E8V2_FULL"

# pass 1: the request cache (rerun, also under MS3_RESUME=1, when its files are missing)
grep -x -F 'pool e8v2:requests' "$E8V2_FULL" > "$MS3_OUT/jobs_list.txt"
if ms3_done e8v2:requests && ! _e8v2_cache_ok; then
  _ms3_log "e8v2:requests: ok before, but the request cache in runs/requests/ is incomplete: rerun"
  MS3_RESUME=0 ms3_run_jobs pool
else
  ms3_run_jobs pool
fi
if _ms3_record_ok e8v2:requests && _e8v2_cache_ok; then
  grep -v -x -F 'pool e8v2:requests' "$E8V2_FULL" > "$MS3_OUT/jobs_replay.txt"
  if [ -n "$E8V2_ONLY" ]; then
    grep -E -- "$E8V2_ONLY" "$MS3_OUT/jobs_replay.txt" > "$MS3_OUT/jobs_replay_only.txt" || true
    mv "$MS3_OUT/jobs_replay_only.txt" "$MS3_OUT/jobs_replay.txt"
    _ms3_log "E8V2_ONLY='$E8V2_ONLY': $(wc -l < "$MS3_OUT/jobs_replay.txt") replay job(s)"
  fi
  # pass 2: the first e8v2:pair job alone, timed
  E8V2_FIRST="$(grep -m 1 '^pool e8v2:pair:' "$MS3_OUT/jobs_replay.txt")"
  if [ -n "$E8V2_FIRST" ]; then
    printf '%s\n' "$E8V2_FIRST" > "$MS3_OUT/jobs_list.txt"
    if ms3_done "${E8V2_FIRST#pool }"; then
      ms3_run_jobs pool
      _ms3_log "first e8v2:pair job ${E8V2_FIRST#pool }: ok before, not timed"
    else
      E8V2_T0=$SECONDS
      ms3_run_jobs pool
      _ms3_log "first e8v2:pair job ${E8V2_FIRST#pool } timed alone: $((SECONDS - E8V2_T0)) s"
    fi
  fi
  # pass 3: the remaining e8v2:pair and e8v2:mooncake jobs
  grep -v -x -F -e "${E8V2_FIRST:-pool e8v2:none}" "$MS3_OUT/jobs_replay.txt" > "$MS3_OUT/jobs_list.txt"
  _ms3_log "$(grep -c '^pool ' "$MS3_OUT/jobs_list.txt") remaining e8v2:pair and e8v2:mooncake job(s)"
  ms3_run_jobs pool
else
  _ms3_log "e8v2:requests has no ok record or its cache files in runs/requests/ are missing (see" \
    "logs/$(ms3_job_name e8v2:requests).log): the replay jobs are not run"
fi
mv "$E8V2_FULL" "$MS3_OUT/jobs_list.txt"
ms3_manifest
ms3_summary
ms3_finish
