#!/usr/bin/env bash
# Reproductions R1-R8 and the informative scripts of design/sim_spec_ms2.md §16.4 and §17.3. Every script
# runs alone in its own 3G scope (MemorySwapMax=0, OMP_NUM_THREADS=1, PYTHONDONTWRITEBYTECODE=1), one at
# a time, with at most 4 worker processes inside; outputs go to code/sim/out/ms2_checks/ (or
# SUBLET_MS2_CHECKS_DIR). A script killed by the cap (exit 137) is logged as "oom_at_3G" and not retried at
# a larger cap. Console log: code/sim/out/ms2_checks/run_ms2_checks.log. Then run
#   pytest -q -p no:cacheprovider -m needs_ms2_checks tests      (from code/sim, under the 3G cap)
# Run it alone (no other heavy job), from any directory: bash code/sim/sublet/experiments/run_ms2_checks.sh
# The order puts the quick scripts first; repro_e2_reactions.py needs the a12 outputs.
set -u
cd "$(dirname "$0")/../.."                       # code/sim
PY="$HOME/venv/bin/python"
OUT="${SUBLET_MS2_CHECKS_DIR:-out/ms2_checks}"
LOG="$OUT/run_ms2_checks.log"
SCOPE=(systemd-run --user --scope -q -p MemoryMax=3G -p MemorySwapMax=0 env OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1)
export OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
mkdir -p "$OUT"
SCRIPTS=(repro_c2sw_scan repro_c2_below_hstar repro_c3_upper repro_c4_lower repro_c3_benchmark repro_c5_la
         repro_e2_reactions repro_o1_ub)

echo "[run_ms2_checks] start $(date -Is) on $(hostname)" | tee -a "$LOG"
for s in "${SCRIPTS[@]}"; do
  echo "[run_ms2_checks] $s $(date -Is)" | tee -a "$LOG"
  /usr/bin/time -f "[time] $s peak RSS %M KB, %e s" "${SCOPE[@]}" "$PY" -m "sublet.experiments.$s" --workers 4 2>&1 | tee -a "$LOG"
  rc=${PIPESTATUS[0]}
  if [ "$rc" -eq 137 ]; then
    echo "[run_ms2_checks] $s: oom_at_3G (exit 137), not retried" | tee -a "$LOG"
  elif [ "$rc" -ne 0 ]; then
    echo "[run_ms2_checks] $s: failed with exit code $rc" | tee -a "$LOG"
  fi
done
echo "[run_ms2_checks] done $(date -Is)" | tee -a "$LOG"
