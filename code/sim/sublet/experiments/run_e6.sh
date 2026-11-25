#!/usr/bin/env bash
# E6: contract menu and protection (design/sim_spec_ms3.md §7; deliverable D26). Runs the jobs of
# sublet.experiments.e6 under the MS3 slot semaphore (ms3_lib.sh: one 3G scope per job), part by part:
#   a  E6(a) (§7.1): the cell jobs (INS and WARM runs, BL7 costs, A1's decisions, the E6-2 and E6-3 reruns), the
#      boundary jobs and E6-1, then the summary (out/e6/a/: heatmap.json, boundary.json, summary.json, tables.md).
#      It reads E2's run files, so it runs only after run_e2.sh has finished (out/e2/summary.json exists);
#      otherwise part a is skipped with a message and the script exits 2 after the other parts.
#   b  E6(b) (§7.2): A6 on bench_e7r under four menus, then its summary (out/e6/b/summary.json, tables.md).
# Each part has its own output folder (MS3_OUT = out/e6/<part>: jobs/, logs/, runs/, manifest.json, run_e6.log).
#
#   sublet/experiments/run_e6.sh [--reduced] [a] [b]
#
# Parts: the named ones in the order given, default 'a b' (or E6_PART). --reduced: the reduced job lists of e6.py's
# docstring (MS3_E6_REDUCED=1, which also selects E2's reduced lists); for smoke runs under a scratch MS3_ROOT,
# never a result. Environment as ms3_lib.sh (MS3_WORKERS, MS3_RESUME, MS3_ROOT, ...).
set -u
PARTS=()
for arg in "$@"; do
  case "$arg" in
    --reduced) export MS3_E6_REDUCED=1 ;;
    a | b) PARTS+=("$arg") ;;
    *) echo "usage: $0 [--reduced] [a] [b]" >&2; exit 2 ;;
  esac
done
if [ ${#PARTS[@]} -eq 0 ]; then
  read -r -a PARTS <<< "${E6_PART:-a b}"
fi
source "$(dirname "$0")/ms3_lib.sh"
RC=0
for part in "${PARTS[@]}"; do
  case "$part" in a | b) ;; *) echo "[run_e6] unknown part '$part' (a, b)" >&2; exit 2 ;; esac
  if [ "$part" = a ] && [ ! -s "$MS3_ROOT/out/e2/summary.json" ]; then
    echo "[run_e6] part a skipped: E6(a) reads E2's runs and $MS3_ROOT/out/e2/summary.json is missing" \
      "(run run_e2.sh first)"
    RC=2
    continue
  fi
  export E6_PART="$part"
  MS3_OUT="$MS3_ROOT/out/e6/$part"
  ms3_init e6
  _ms3_log "part $part"
  ms3_list
  ms3_manifest
  ms3_run_jobs pool
  ms3_run_jobs alone
  ms3_run_jobs milp
  ms3_manifest
  ms3_summary
  ms3_finish
done
exit "$RC"
