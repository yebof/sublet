#!/usr/bin/env bash
# E8q (X7): E8 v2's request-level replay with a FIFO queue and a waiting limit W (design/ms8/plan.md D1). Runs the jobs
# of sublet.experiments.e8q under the MS3 slot semaphore (ms3_lib.sh: one 3G scope per job) with the output folder
# MS3_OUT = out/e8q, as run_e8v2.sh runs E8 v2's: the gate (`e8q --check-start`: a full run refuses to start unless
# design/ms8/registration.md exists at HEAD with the sha256 of experiments/e8q_analysis.py and the working tree is
# clean; exit 2 when refused), the job list, the manifest, then three filtered passes: e8q:requests, the request cache
# that every cell job reads (rerun when its record is ok but its files are missing); the first e8q:cell job alone (the
# job with the most copies), which is timed; the remaining e8q:cell jobs. The cell passes do not run without an ok
# e8q:requests and its cache files. Then the manifest again, the summary (out/e8q/summary.json, hist.json, tables.md)
# and ms3_finish's done line. The analysis (python -m sublet.experiments.e8q_analysis) runs after this script, in the
# same clone.
#
#   sublet/experiments/run_e8q.sh [--reduced]
#
# --reduced: the reduced job list of e8q.py's docstring (MS3_E8Q_REDUCED=1 and MS3_E8V2_REDUCED=1: 6 hours at market
# tightness 0.05; the gate is recorded, not enforced); for smoke runs under a scratch MS3_ROOT, never a result.
# Environment as ms3_lib.sh (MS3_WORKERS, MS3_RESUME, MS3_ROOT, ...; MS3_OUT is set here), plus, for tests and smoke
# runs only, E8Q_ONLY=<extended regex>: only the cell jobs whose list line matches run.
set -u
for arg in "$@"; do
  case "$arg" in
    --reduced) export MS3_E8Q_REDUCED=1 MS3_E8V2_REDUCED=1 ;;
    *) echo "usage: $0 [--reduced]" >&2; exit 2 ;;
  esac
done
if [ "${MS3_E8Q_REDUCED:-0}" != "${MS3_E8V2_REDUCED:-0}" ]; then
  echo "[run_e8q] MS3_E8Q_REDUCED and MS3_E8V2_REDUCED must agree" >&2; exit 2
fi
E8Q_ONLY="${E8Q_ONLY:-}"
if [ -n "$E8Q_ONLY" ]; then
  printf '' | grep -Eq -- "$E8Q_ONLY" 2> /dev/null
  [ $? -eq 2 ] && { echo "[run_e8q] E8Q_ONLY is not a valid extended regex: '$E8Q_ONLY'" >&2; exit 2; }
fi
source "$(dirname "$0")/ms3_lib.sh"
MS3_OUT="$MS3_ROOT/out/e8q"
ms3_init e8q

e8q_check_start() {  # 0 iff the gate lets the run start (e8q --check-start in a 3G scope; its lines to the log)
  local -a MS3_PRE
  _ms3_prefix
  "${MS3_PRE[@]}" "$MS3_PY" -m "$MS3_MODULE" --check-start 2>&1 | tee -a "$MS3_LOG"
  return "${PIPESTATUS[0]}"
}

_e8q_cache_ok() {    # the request cache's record and arrays exist (replay.requests.cache_paths of azure2024_conv)
  local f
  for f in azure2024_conv.json azure2024_conv_t_s.npy azure2024_conv_inp.npy azure2024_conv_out.npy; do
    [ -s "$MS3_OUT/runs/requests/$f" ] || return 1
  done
}

if ! e8q_check_start; then
  _ms3_log "refused: E8q does not start (design/ms8/plan.md D4)"
  exit 2
fi
ms3_list
ms3_manifest
E8Q_FULL="$MS3_OUT/jobs_list_full.txt"
mv "$MS3_OUT/jobs_list.txt" "$E8Q_FULL"

# pass 1: the request cache (rerun, also under MS3_RESUME=1, when its files are missing)
grep -x -F 'pool e8q:requests' "$E8Q_FULL" > "$MS3_OUT/jobs_list.txt"
if ms3_done e8q:requests && ! _e8q_cache_ok; then
  _ms3_log "e8q:requests: ok before, but the request cache in runs/requests/ is incomplete: rerun"
  MS3_RESUME=0 ms3_run_jobs pool
else
  ms3_run_jobs pool
fi
if _ms3_record_ok e8q:requests && _e8q_cache_ok; then
  grep -v -x -F 'pool e8q:requests' "$E8Q_FULL" > "$MS3_OUT/jobs_cells.txt"
  if [ -n "$E8Q_ONLY" ]; then
    grep -E -- "$E8Q_ONLY" "$MS3_OUT/jobs_cells.txt" > "$MS3_OUT/jobs_cells_only.txt" || true
    mv "$MS3_OUT/jobs_cells_only.txt" "$MS3_OUT/jobs_cells.txt"
    _ms3_log "E8Q_ONLY='$E8Q_ONLY': $(wc -l < "$MS3_OUT/jobs_cells.txt") cell job(s)"
  fi
  # pass 2: the first e8q:cell job alone, timed
  E8Q_FIRST="$(grep -m 1 '^pool e8q:cell:' "$MS3_OUT/jobs_cells.txt")"
  if [ -n "$E8Q_FIRST" ]; then
    printf '%s\n' "$E8Q_FIRST" > "$MS3_OUT/jobs_list.txt"
    if ms3_done "${E8Q_FIRST#pool }"; then
      ms3_run_jobs pool
      _ms3_log "first e8q:cell job ${E8Q_FIRST#pool }: ok before, not timed"
    else
      E8Q_T0=$SECONDS
      ms3_run_jobs pool
      _ms3_log "first e8q:cell job ${E8Q_FIRST#pool } timed alone: $((SECONDS - E8Q_T0)) s"
    fi
  fi
  # pass 3: the remaining e8q:cell jobs
  grep -v -x -F -e "${E8Q_FIRST:-pool e8q:none}" "$MS3_OUT/jobs_cells.txt" > "$MS3_OUT/jobs_list.txt"
  _ms3_log "$(grep -c '^pool ' "$MS3_OUT/jobs_list.txt") remaining e8q:cell job(s)"
  ms3_run_jobs pool
else
  _ms3_log "e8q:requests has no ok record or its cache files in runs/requests/ are missing (see" \
    "logs/$(ms3_job_name e8q:requests).log): the cell jobs are not run"
fi
mv "$E8Q_FULL" "$MS3_OUT/jobs_list.txt"
ms3_manifest
ms3_summary
ms3_finish
