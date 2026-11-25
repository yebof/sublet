#!/usr/bin/env bash
# E7: end-to-end savings (design/sim_spec_ms4.md §3; deliverable D31). Runs the jobs of sublet.experiments.e7 under
# the slot semaphore shared with MS3 (ms3_lib.sh: one 3G scope per job) in two passes over the parts (§3.10), each part
# with its own output folder (MS3_OUT = out/e7/<part>: jobs/, logs/, runs/, manifest.json, summary.json, tables.md,
# run_e7.log; ms3_common.COPY_PARTS['e7']):
#   pass 1, the jobs, parts gap, stress, main, allow: the job list, the manifest, the pool jobs, then the 'alone'
#           jobs (gap's merged LPs, e7:gap_lp:c=C, each holding every slot);
#   pass 2, the summaries, parts gap, stress, allow, main: the manifest again and the summary, then ms3_finish's done
#           line. allow's summary reads main's and stress's run files (check E7-7) and stress's summary, and main's
#           summary, written last, reads the other three and writes out/e7/table3.json.
#
#   sublet/experiments/run_e7.sh [--reduced]
#
# --reduced: the reduced job list of e7.py's docstring (MS3_E7_REDUCED=1: alignment 1, policy seed 0, a 2-hour horizon,
# every part and job kind); for smoke runs under a scratch MS3_ROOT, never a result. Environment as ms3_lib.sh
# (MS3_WORKERS, MS3_RESUME, MS3_ROOT, ...; MS3_OUT is set per part here).
set -u
for arg in "$@"; do
  case "$arg" in
    --reduced) export MS3_E7_REDUCED=1 ;;
    *) echo "usage: $0 [--reduced]" >&2; exit 2 ;;
  esac
done
source "$(dirname "$0")/ms3_lib.sh"
for part in gap stress main allow; do
  export E7_PART="$part"
  MS3_OUT="$MS3_ROOT/out/e7/$part"
  ms3_init e7
  _ms3_log "pass 1 (jobs), part $part"
  ms3_list
  ms3_manifest
  ms3_run_jobs pool
  ms3_run_jobs alone
done
for part in gap stress allow main; do
  export E7_PART="$part"
  MS3_OUT="$MS3_ROOT/out/e7/$part"
  ms3_init e7
  _ms3_log "pass 2 (summary), part $part"
  ms3_manifest
  ms3_summary
  ms3_finish
done
