#!/usr/bin/env bash
# Memory benchmark of design/sim_spec.md §9.3. Every case runs alone in its own 3G scope, one at a
# time, on at most 4 cores (mem_bench.py sets the affinity). A case killed by the cap (exit 137) or
# without an output file is recorded as "oom_at_3G" and is not retried at a larger cap. Then the 7-day
# model sizes of the LP/MILP families are counted (estimate_size, no solve) and the summary is written
# to ../out/mem_bench/summary.json. Console log: ../out/mem_bench/mem_bench.log.
# Run it alone (no other heavy job), from any directory: bash code/sim/bench/run_mem_bench.sh
set -u
cd "$(dirname "$0")"
PY="$HOME/venv/bin/python"
OUT=../out/mem_bench
LOG="$OUT/mem_bench.log"
SCOPE=(systemd-run --user --scope -q -p MemoryMax=3G -p MemorySwapMax=0)
export OMP_NUM_THREADS=1
mkdir -p "$OUT"

echo "[run_mem_bench] start $(date -Is) on $(hostname)" | tee -a "$LOG"
for id in $("$PY" mem_bench.py --list); do
  rm -f "$OUT/$id.json"
  echo "[run_mem_bench] case $id $(date -Is)" | tee -a "$LOG"
  /usr/bin/time -f "[time] $id peak RSS %M KB, %e s" "${SCOPE[@]}" "$PY" mem_bench.py --case "$id" 2>&1 | tee -a "$LOG"
  rc=${PIPESTATUS[0]}
  if [ "$rc" -eq 137 ] || [ ! -s "$OUT/$id.json" ]; then
    "$PY" mem_bench.py --record-failure "$id" --exit-code "$rc" 2>&1 | tee -a "$LOG"
  fi
done
for fam in $("$PY" mem_bench.py --list-families); do
  echo "[run_mem_bench] 7-day size estimate $fam $(date -Is)" | tee -a "$LOG"
  /usr/bin/time -f "[time] estimate $fam peak RSS %M KB, %e s" "${SCOPE[@]}" "$PY" mem_bench.py --estimate "$fam" --days 7 2>&1 | tee -a "$LOG"
done
"${SCOPE[@]}" "$PY" mem_bench.py --summary 2>&1 | tee -a "$LOG"
echo "[run_mem_bench] done $(date -Is)" | tee -a "$LOG"
