#!/usr/bin/env bash
# E2: the value and price of notice (design/sim_spec_ms3.md §6; deliverable D25). Runs every job of
# sublet.experiments.e2 under the MS3 slot semaphore (ms3_lib.sh: one 3G scope per job): the pool jobs (one per
# cell, mu and alignment: the rule runs, the week DPs and the per-episode runs and DPs), the 'alone' jobs of the
# exact C2 game on the finer H grid (each holds every slot and runs an internal pool of that many processes), the
# MILP jobs under the hard wall-clock limit (the E2-6 joint MILPs and the E2-5 episode MILPs, which read the cell
# jobs' records), the manifest and the summary (code/sim/out/e2/summary.json, game.json, joint_milp.json, tables.md).
#
#   sublet/experiments/run_e2.sh [--reduced]
#
# --reduced: the reduced job list of e2.py's docstring (MS3_E2_REDUCED=1), with MS3_MILP_LIMIT 30 s unless set;
# for smoke runs under a scratch MS3_ROOT, never a result. Environment as ms3_lib.sh (MS3_WORKERS, MS3_RESUME,
# MS3_MILP_LIMIT, MS3_ROOT, MS3_OUT, ...).
set -u
for arg in "$@"; do
  case "$arg" in
    --reduced) export MS3_E2_REDUCED=1; export MS3_MILP_LIMIT="${MS3_MILP_LIMIT:-30}" ;;
    *) echo "usage: $0 [--reduced]" >&2; exit 2 ;;
  esac
done
source "$(dirname "$0")/ms3_lib.sh"
ms3_init e2
ms3_list
ms3_manifest
ms3_run_jobs pool
ms3_run_jobs alone
ms3_run_jobs milp
ms3_manifest
ms3_summary
ms3_finish
