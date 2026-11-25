#!/usr/bin/env bash
# E9 smoke run of design/sim_spec_ms2.md §18. Every case runs alone in its own 3G scope (MemorySwapMax=0,
# OMP_NUM_THREADS=1, PYTHONDONTWRITEBYTECODE=1), one at a time. A case killed by the cap (exit 137) or
# without an output file is recorded as "oom_at_3G" (or "failed") and not retried at a larger cap. Then
# summary.json lists every case, the targets P1-P4 with the measured values and the git revision.
# Outputs: code/sim/out/e9_smoke/<id>.json, summary.json and e9_smoke.log.
# Run it alone (no other heavy job), from any directory: bash code/sim/sublet/experiments/run_e9_smoke.sh
# The config-based cases need the a12 outputs (as MS1's needs_a12 tests); pd_bench and fam_m8 do not.
set -u
cd "$(dirname "$0")/../.."                       # code/sim
PY="$HOME/venv/bin/python"
OUT=out/e9_smoke
LOG="$OUT/e9_smoke.log"
SCOPE=(systemd-run --user --scope -q -p MemoryMax=3G -p MemorySwapMax=0 env OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1)
export OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
mkdir -p "$OUT"

echo "[run_e9_smoke] start $(date -Is) on $(hostname)" | tee -a "$LOG"
for id in $("$PY" -m sublet.experiments.e9_smoke --list); do
  rm -f "$OUT/$id.json"
  echo "[run_e9_smoke] case $id $(date -Is)" | tee -a "$LOG"
  /usr/bin/time -f "[time] $id peak RSS %M KB, %e s" "${SCOPE[@]}" "$PY" -m sublet.experiments.e9_smoke --case "$id" 2>&1 | tee -a "$LOG"
  rc=${PIPESTATUS[0]}
  if [ "$rc" -eq 137 ] || [ ! -s "$OUT/$id.json" ]; then
    "$PY" -m sublet.experiments.e9_smoke --record-failure "$id" --exit-code "$rc" 2>&1 | tee -a "$LOG"
  fi
done
"${SCOPE[@]}" "$PY" -m sublet.experiments.e9_smoke --summary 2>&1 | tee -a "$LOG"
echo "[run_e9_smoke] done $(date -Is)" | tee -a "$LOG"
