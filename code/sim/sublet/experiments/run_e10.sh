#!/usr/bin/env bash
# E10: the value of public reclaim information (design/sim_spec_ms3.md §5; deliverable D24). Runs every job of
# sublet.experiments.e10 under the MS3 slot semaphore (ms3_lib.sh: one 3G scope per job): the pool jobs (e10:repro,
# E10(a), E10(b) runs), then a second listing that adds the e10:rerun jobs of the points that E10-5 or E10-6 flags
# (seeds 30-129, M14) and runs them, then the E10(b) MILP jobs under the hard wall-clock limit, the manifest and
# the summary (code/sim/out/e10/summary.json, tables.md).
#
#   sublet/experiments/run_e10.sh [--reduced]
#
# --reduced: the reduced job list of e10.py's docstring (MS3_E10_REDUCED=1), with MS3_MILP_LIMIT 30 s unless set;
# for smoke runs under a scratch MS3_ROOT, never a result. Environment as ms3_lib.sh (MS3_WORKERS, MS3_RESUME,
# MS3_MILP_LIMIT, MS3_ROOT, MS3_OUT, ...).
set -u
for arg in "$@"; do
  case "$arg" in
    --reduced) export MS3_E10_REDUCED=1; export MS3_MILP_LIMIT="${MS3_MILP_LIMIT:-30}" ;;
    *) echo "usage: $0 [--reduced]" >&2; exit 2 ;;
  esac
done
source "$(dirname "$0")/ms3_lib.sh"
ms3_init e10
ms3_list
ms3_manifest
ms3_run_jobs pool
# reruns of flagged points (E10-5, E10-6): the job list now names them; run only those (ms3_run_jobs reads
# jobs_list.txt, so it gets the rerun lines alone and the full list is put back afterwards)
ms3_list
if grep -q '^pool e10:rerun:' "$MS3_OUT/jobs_list.txt"; then
  mv "$MS3_OUT/jobs_list.txt" "$MS3_OUT/jobs_list_full.txt"
  grep '^pool e10:rerun:' "$MS3_OUT/jobs_list_full.txt" > "$MS3_OUT/jobs_list.txt"
  _ms3_log "$(wc -l < "$MS3_OUT/jobs_list.txt") e10:rerun job(s) flagged by E10-5 or E10-6"
  ms3_run_jobs pool
  mv "$MS3_OUT/jobs_list_full.txt" "$MS3_OUT/jobs_list.txt"
fi
ms3_run_jobs alone
ms3_run_jobs milp
ms3_manifest
ms3_summary
ms3_finish
