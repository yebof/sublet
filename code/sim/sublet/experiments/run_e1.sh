#!/usr/bin/env bash
# E1: revocation exposure and the benchmark gap (design/sim_spec_ms3.md §4; deliverable D23). Runs every job of
# sublet.experiments.e1 under the MS3 slot semaphore (ms3_lib.sh: one 3G scope per job; pool jobs, then MILP jobs
# under the hard wall-clock limit), then the manifest and the summary (code/sim/out/e1/summary.json, tables.md).
#
#   sublet/experiments/run_e1.sh [--reduced]
#
# --reduced: the reduced job list of e1.py's docstring (MS3_E1_REDUCED=1: alignment 1, policy seed 0, 2-h
# instances), with MS3_MILP_LIMIT 30 s unless set; for smoke runs under a scratch MS3_ROOT, never a result.
# Environment as ms3_lib.sh (MS3_WORKERS, MS3_RESUME, MS3_MILP_LIMIT, MS3_ROOT, MS3_OUT, ...).
set -u
for arg in "$@"; do
  case "$arg" in
    --reduced) export MS3_E1_REDUCED=1; export MS3_MILP_LIMIT="${MS3_MILP_LIMIT:-30}" ;;
    *) echo "usage: $0 [--reduced]" >&2; exit 2 ;;
  esac
done
source "$(dirname "$0")/ms3_lib.sh"
ms3_init e1
ms3_list
ms3_manifest
ms3_run_jobs pool
ms3_run_jobs alone
ms3_run_jobs milp
ms3_manifest
ms3_summary
ms3_finish
