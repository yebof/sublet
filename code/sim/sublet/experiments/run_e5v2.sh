#!/usr/bin/env bash
# E5 v2: redundancy under correlated reclaims for Sublet itself (design/ms7/plan.md X3; change C56). Runs every job of
# sublet.experiments.e5v2 under the host-wide slot semaphore (ms3_lib.sh: one 3G scope per job, at most 4 jobs on
# the host): the gate (`e5v2 --check-start`: a full run refuses to start unless design/ms7/registration.md exists at
# HEAD with the sha256 of experiments/ms7_sens_analysis.py and the working tree is clean; exit 2 when refused), the job
# list, the manifest, the pool jobs e5v2:cell:... and e5v2:mu:... (each builds its own instance, so the jobs have no
# order), the manifest again and the summary (out/e5v2/summary.json, tables.md), then ms3_finish's done line. The
# analysis (python -m sublet.experiments.ms7_sens_analysis --exp e5v2) runs after this script, in the same clone.
#
#   sublet/experiments/run_e5v2.sh [--reduced]
#
# --reduced: the reduced job list of e5v2.py's docstring (MS3_E5V2_REDUCED=1: development E5 config seed 101, a 2-hour
# horizon; the gate is recorded, not enforced); for smoke runs under a scratch MS3_ROOT, never a result. Environment as
# ms3_lib.sh (MS3_WORKERS, MS3_RESUME, MS3_ROOT, MS3_OUT, ...), plus, for tests and smoke runs only,
# E5V2_ONLY=<extended regex>: only the jobs whose list line matches run (the summary lists the others as missing).
set -u
for arg in "$@"; do
  case "$arg" in
    --reduced) export MS3_E5V2_REDUCED=1 ;;
    *) echo "usage: $0 [--reduced]" >&2; exit 2 ;;
  esac
done
E5V2_ONLY="${E5V2_ONLY:-}"
if [ -n "$E5V2_ONLY" ]; then
  printf '' | grep -Eq -- "$E5V2_ONLY" 2> /dev/null
  [ $? -eq 2 ] && { echo "[run_e5v2] E5V2_ONLY is not a valid extended regex: '$E5V2_ONLY'" >&2; exit 2; }
fi
source "$(dirname "$0")/ms3_lib.sh"

e5v2_check_start() {  # 0 iff the gate lets the run start (e5v2 --check-start in a 3G scope; its lines to the log)
  local -a MS3_PRE
  _ms3_prefix
  "${MS3_PRE[@]}" "$MS3_PY" -m "$MS3_MODULE" --check-start 2>&1 | tee -a "$MS3_LOG"
  return "${PIPESTATUS[0]}"
}

e5v2_only() {         # keep the list lines that match E5V2_ONLY (tests and smoke runs)
  [ -n "$E5V2_ONLY" ] || return 0
  mv "$MS3_OUT/jobs_list.txt" "$MS3_OUT/jobs_list_all.txt"
  grep -E -- "$E5V2_ONLY" "$MS3_OUT/jobs_list_all.txt" > "$MS3_OUT/jobs_list.txt"
  _ms3_log "E5V2_ONLY='$E5V2_ONLY': $(wc -l < "$MS3_OUT/jobs_list.txt") of $(wc -l < "$MS3_OUT/jobs_list_all.txt") jobs"
}

ms3_init e5v2
if ! e5v2_check_start; then
  _ms3_log "refused: E5 v2 does not start (design/ms7/plan.md D6)"
  exit 2
fi
ms3_list
e5v2_only
ms3_manifest
ms3_run_jobs pool
ms3_manifest
ms3_summary
ms3_finish
