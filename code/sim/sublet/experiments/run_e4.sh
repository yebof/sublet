#!/usr/bin/env bash
# E4: predictions (design/sim_spec_ms4.md §6; deliverable D34). Runs every job of sublet.experiments.e4 under the
# MS3 slot semaphore (ms3_lib.sh: one 3G scope per job) in the order of §6.7: the MILP jobs under the hard wall-clock
# limit (e4:phat, the P-hat days, and e4:eager, OPT_eager of the ratio days), then a filtered pool pass of the
# e4:pcols jobs, which assemble each P-hat from its day jobs into runs/pcols/, then the complementary pool pass
# (e4:week and e4:ratio, which read runs/pcols/, and e4:repro), the manifest and the summary
# (code/sim/out/e4/summary.json, tables.md). E4 has no 'alone' job.
#
#   sublet/experiments/run_e4.sh [--reduced]
#
# --reduced: the reduced job list of e4.py's docstring (MS3_E4_REDUCED=1), with MS3_MILP_LIMIT 10 s unless set; for
# smoke runs under a scratch MS3_ROOT, never a result. Environment as ms3_lib.sh (MS3_WORKERS, MS3_RESUME,
# MS3_MILP_LIMIT, MS3_ROOT, MS3_OUT, ...).
set -u
for arg in "$@"; do
  case "$arg" in
    --reduced) export MS3_E4_REDUCED=1; export MS3_MILP_LIMIT="${MS3_MILP_LIMIT:-10}" ;;
    *) echo "usage: $0 [--reduced]" >&2; exit 2 ;;
  esac
done
source "$(dirname "$0")/ms3_lib.sh"
ms3_init e4
ms3_list
ms3_manifest
ms3_run_jobs milp
# filtered passes (§2.4, the pattern of run_e10.sh): ms3_run_jobs reads jobs_list.txt, so the e4:pcols lines alone
# become the list, then every other line; the full list is put back afterwards
mv "$MS3_OUT/jobs_list.txt" "$MS3_OUT/jobs_list_full.txt"
grep '^pool e4:pcols:' "$MS3_OUT/jobs_list_full.txt" > "$MS3_OUT/jobs_list.txt"
_ms3_log "$(wc -l < "$MS3_OUT/jobs_list.txt") e4:pcols job(s)"
ms3_run_jobs pool
grep -v '^pool e4:pcols:' "$MS3_OUT/jobs_list_full.txt" > "$MS3_OUT/jobs_list.txt"
_ms3_log "$(grep -c '^pool ' "$MS3_OUT/jobs_list.txt") other pool job(s) (e4:week, e4:ratio, e4:repro)"
ms3_run_jobs pool
mv "$MS3_OUT/jobs_list_full.txt" "$MS3_OUT/jobs_list.txt"
ms3_manifest
ms3_summary
ms3_finish
