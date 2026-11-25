#!/usr/bin/env bash
# E5: redundancy under correlated reclaims (design/sim_spec_ms4.md §5; deliverable D33). Runs every job of
# sublet.experiments.e5 under the host-wide slot semaphore (ms3_lib.sh: one 3G scope per job): the pool jobs
# e5:run:level=L:menu=M:pol=P:mu=U:c=C (the 3 policy seeds of one tag; each job builds its own instances, so the
# jobs have no order and need no filtered pass), then the manifest and the summary (code/sim/out/e5/summary.json,
# tables.md).
#
#   sublet/experiments/run_e5.sh [--reduced]
#
# --reduced: the reduced job list of e5.py's docstring (MS3_E5_REDUCED=1: alignment 1, policy seed 0, one-day
# instances); for smoke runs under a scratch MS3_ROOT, never a result. Environment as ms3_lib.sh (MS3_WORKERS,
# MS3_RESUME, MS3_ROOT, MS3_OUT, ...).
set -u
for arg in "$@"; do
  case "$arg" in
    --reduced) export MS3_E5_REDUCED=1 ;;
    *) echo "usage: $0 [--reduced]" >&2; exit 2 ;;
  esac
done
source "$(dirname "$0")/ms3_lib.sh"
ms3_init e5
ms3_list
ms3_manifest
ms3_run_jobs pool
ms3_run_jobs alone
ms3_run_jobs milp
ms3_manifest
ms3_summary
ms3_finish
