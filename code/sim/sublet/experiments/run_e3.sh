#!/usr/bin/env bash
# E3: shared replicas (design/sim_spec_ms4.md §4; deliverable D32, unit U21). Runs the jobs of sublet.experiments.e3
# under the MS3 slot semaphore (ms3_lib.sh: one 3G scope per job) in filtered passes (§2.4: jobs_list.txt is moved
# aside, the matching lines become the list, ms3_run_jobs runs them, and the full list is put back).
#
#   sublet/experiments/run_e3.sh [--reduced] --gate     the gate (§1.2 item 6, §4.4): first in the clean clone of the
#                                                       runs, before any other MS4 run there
#   sublet/experiments/run_e3.sh [--reduced]            the full grid, once out/e3/gate.json exists
#
# --gate: three passes on the gate cell (b, u, mu, c) = (8, 8, 1, 1): its cell job (pool), its 9 MILP jobs (milp),
# then e3:gate (pool), which reads the cell's MILP records and writes out/e3/gate.json. These jobs are jobs of the
# grid, which the full run resumes.
# Full run: refuses to start (exit 2) unless `python -m sublet.experiments.e3 --check-gate` passes (gate.json exists,
# the job record of e3:gate is ok, gate.json records the config hash of the grid's instances and its MILPs ran under
# the current MS3_MILP_LIMIT); runs with MS3_RESUME=1 (the gate's jobs are not run again): the manifest, the cell
# jobs (pool), every MILP job except the part=b00 jobs at b = 1, then those 4 jobs (each copies its cell's shared
# record, which the first pass finished, and fails if that job is not ok, so that the next run repeats both; §4.7),
# the manifest and the summary (out/e3/summary.json, tables.md).
# --reduced: the reduced job list of e3.py's docstring (MS3_E3_REDUCED=1: b 1 and 8, u 8, the mu point 2,
# alignment 1, policy seed 0, a 2-h window), with MS3_MILP_LIMIT 30 s unless set; for smoke runs under a scratch
# MS3_ROOT, never a result. Environment as ms3_lib.sh (MS3_WORKERS, MS3_MILP_LIMIT, MS3_ROOT, MS3_OUT, ...).
set -u
GATE=0
for arg in "$@"; do
  case "$arg" in
    --reduced) export MS3_E3_REDUCED=1; export MS3_MILP_LIMIT="${MS3_MILP_LIMIT:-30}" ;;
    --gate) GATE=1 ;;
    *) echo "usage: $0 [--reduced] [--gate]" >&2; exit 2 ;;
  esac
done
# the filters of the passes (extended regular expressions on the lines '<kind> <job id>' of jobs_list.txt)
GATE_CELL_RE='^pool e3:cell:b=8:u=8:mu=1:c=1$'
GATE_MILP_RE='^milp e3:milp:b=8:u=8:mu=1:c=1:part=[a-z0-9]+$'
GATE_JOB_RE='^pool e3:gate$'
B00_RE='^milp e3:milp:b=1:u=[0-9]+:mu=[0-9.]+:c=[0-9]+:part=b00$'
[ "$GATE" = "1" ] || export MS3_RESUME=1
source "$(dirname "$0")/ms3_lib.sh"

e3_pass() {           # e3_pass KIND REGEX [-v]: run the jobs of KIND whose list lines match REGEX (with -v: do not)
  local kind="$1" re="$2" inv="${3:-}" n
  mv "$MS3_OUT/jobs_list.txt" "$MS3_OUT/jobs_list_full.txt"
  if [ "$inv" = "-v" ]; then
    grep -v -E "$re" "$MS3_OUT/jobs_list_full.txt" > "$MS3_OUT/jobs_list.txt"
  else
    grep -E "$re" "$MS3_OUT/jobs_list_full.txt" > "$MS3_OUT/jobs_list.txt"
  fi
  n="$(grep -c "^$kind " "$MS3_OUT/jobs_list.txt")"
  _ms3_log "pass: $n $kind job(s) ${inv:+not }matching '$re'"
  ms3_run_jobs "$kind"
  mv "$MS3_OUT/jobs_list_full.txt" "$MS3_OUT/jobs_list.txt"
}

e3_check_gate() {     # 0 iff the gate allows the full grid (e3.py --check-gate in a 3G scope; its line to the log)
  local -a MS3_PRE
  _ms3_prefix
  "${MS3_PRE[@]}" "$MS3_PY" -m "$MS3_MODULE" --check-gate --out "$MS3_OUT" 2>&1 | tee -a "$MS3_LOG"
  return "${PIPESTATUS[0]}"
}

ms3_init e3
if [ "$GATE" = "1" ]; then
  _ms3_log "gate: the cell, its MILP jobs and e3:gate of (b, u, mu, c) = (8, 8, 1, 1)"
  ms3_list
  e3_pass pool "$GATE_CELL_RE"
  e3_pass milp "$GATE_MILP_RE"
  e3_pass pool "$GATE_JOB_RE"
  if e3_check_gate; then
    _ms3_log "gate written: $MS3_OUT/gate.json"
    ms3_finish
    exit 0
  fi
  _ms3_log "the gate failed: no valid $MS3_OUT/gate.json (see logs/)"
  exit 1
fi
if ! e3_check_gate; then
  _ms3_log "refused: the gate does not allow the full grid; run $0 --gate first (design/sim_spec_ms4.md §4.4)"
  exit 2
fi
ms3_list
ms3_manifest
e3_pass pool "$GATE_JOB_RE" -v
ms3_run_jobs alone
e3_pass milp "$B00_RE" -v
e3_pass milp "$B00_RE"
ms3_manifest
ms3_summary
ms3_finish
