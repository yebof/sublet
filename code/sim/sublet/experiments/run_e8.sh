#!/usr/bin/env bash
# E8: fluid-model fidelity (design/sim_spec_ms4.md §7; deliverable D35). Runs the jobs of sublet.experiments.e8 under
# the MS3 slot semaphore (ms3_lib.sh: one 3G scope per job) in three filtered passes (§2.4, §7.8; the pattern of
# run_e10.sh): e8:requests, the request cache that every other job reads; then the first e8:pair job alone (the job
# with the most copies), which is timed (its time sets the budget of §11); then the remaining e8:pair and e8:mooncake
# jobs. Then the manifest and the summary (code/sim/out/e8/summary.json, tables.md). The replay jobs are not run while
# e8:requests has no ok record or its cache files are missing; e8:requests is rerun when its record is ok but the
# cache files are missing (MS3_RESUME=1 in a tree without the unversioned runs/).
#
#   sublet/experiments/run_e8.sh [--reduced]
#
# --reduced: the reduced job list of e8.py's docstring (MS3_E8_REDUCED=1: 6 hours at market tightness 0.05); for smoke
# runs under a scratch MS3_ROOT, never a result. Environment as ms3_lib.sh (MS3_WORKERS, MS3_RESUME, MS3_ROOT, MS3_OUT,
# ...).
set -u
for arg in "$@"; do
  case "$arg" in
    --reduced) export MS3_E8_REDUCED=1 ;;
    *) echo "usage: $0 [--reduced]" >&2; exit 2 ;;
  esac
done
source "$(dirname "$0")/ms3_lib.sh"
ms3_init e8
ms3_list
ms3_manifest
E8_FULL="$MS3_OUT/jobs_list_full.txt"
mv "$MS3_OUT/jobs_list.txt" "$E8_FULL"

_e8_cache_ok() {      # the request cache's record and arrays exist (replay.requests.cache_paths of azure2024_conv)
  local f
  for f in azure2024_conv.json azure2024_conv_t_s.npy azure2024_conv_inp.npy azure2024_conv_out.npy; do
    [ -s "$MS3_OUT/runs/requests/$f" ] || return 1
  done
}

# pass 1: the request cache (rerun, also under MS3_RESUME=1, when its files are missing)
grep -x -F 'pool e8:requests' "$E8_FULL" > "$MS3_OUT/jobs_list.txt"
if ms3_done e8:requests && ! _e8_cache_ok; then
  _ms3_log "e8:requests: ok before, but the request cache in runs/requests/ is incomplete: rerun"
  MS3_RESUME=0 ms3_run_jobs pool
else
  ms3_run_jobs pool
fi
if _ms3_record_ok e8:requests && _e8_cache_ok; then
  # pass 2: the first e8:pair job alone, timed
  E8_FIRST="$(grep -m 1 '^pool e8:pair:' "$E8_FULL")"
  printf '%s\n' "$E8_FIRST" > "$MS3_OUT/jobs_list.txt"
  if ms3_done "${E8_FIRST#pool }"; then
    ms3_run_jobs pool
    _ms3_log "first e8:pair job ${E8_FIRST#pool }: ok before, not timed"
  else
    E8_T0=$SECONDS
    ms3_run_jobs pool
    _ms3_log "first e8:pair job ${E8_FIRST#pool } timed alone: $((SECONDS - E8_T0)) s"
  fi
  # pass 3: the remaining e8:pair and e8:mooncake jobs
  grep -v -x -F -e 'pool e8:requests' -e "$E8_FIRST" "$E8_FULL" > "$MS3_OUT/jobs_list.txt"
  _ms3_log "$(grep -c '^pool ' "$MS3_OUT/jobs_list.txt") remaining e8:pair and e8:mooncake job(s)"
  ms3_run_jobs pool
else
  _ms3_log "e8:requests has no ok record or its cache files in runs/requests/ are missing (see" \
    "logs/$(ms3_job_name e8:requests).log): the replay jobs are not run"
fi
mv "$E8_FULL" "$MS3_OUT/jobs_list.txt"
ms3_run_jobs alone
ms3_run_jobs milp
ms3_manifest
ms3_summary
ms3_finish
