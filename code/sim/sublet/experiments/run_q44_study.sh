#!/usr/bin/env bash
# Q44 study (design/q44_practical_sublet.md §5.5): runs the jobs of the named blocks, by default Tier 1
# (Q0, the checks V1, and Q1-Q6); Tier 2 blocks (T2_vr_rf, T2_ad, T2_stress, T2_guard, T2_e7r, T2_bl8) run
# only when named. Every job (one cell-mode, one family instance-mode, or one lower bound) runs in its own
# 3G scope (MemorySwapMax=0, OMP_NUM_THREADS=1, PYTHONDONTWRITEBYTECODE=1). At most two jobs run at a time;
# the jobs marked 'alone' (every LP and MILP, and the cell-modes with per-run LPs) run afterwards, one at a
# time with no other job. A job killed by the cap (exit 137) is recorded as "oom_at_3G" and not retried at a
# larger cap. Then manifest.json and the summary (q44_summary.py: summary.json, tables.md, fig/).
# Outputs: code/sim/out/q44_study/ (or SUBLET_Q44_DIR, relative to code/sim), with the console log
# run_q44_study.log (per job: wall time and peak RSS) and logs/<job>.log.
# Usage (from any directory; run it alone, with no other heavy job):
#   bash code/sim/sublet/experiments/run_q44_study.sh [BLOCK ...]
#   Q44_WORKERS=1 ... (fewer workers; never more than 2)   Q44_RESUME=1 ... (skip jobs already 'ok')
#   bash code/sim/sublet/experiments/run_q44_study.sh --dry-run [BLOCK ...]
#     lists the processes (pool or alone) with their estimated wall times and the totals for the worker
#     count (q44_study.py --estimate); runs no job and writes nothing.
set -u
cd "$(dirname "$0")/../.."                       # code/sim
PY="$HOME/venv/bin/python"
OUT="${SUBLET_Q44_DIR:-out/q44_study}"
LOG="$OUT/run_q44_study.log"
WORKERS="${Q44_WORKERS:-2}"
if [ "$WORKERS" -gt 2 ]; then WORKERS=2; fi
if [ "$WORKERS" -lt 1 ]; then WORKERS=1; fi
SCOPE=(systemd-run --user --scope -q -p MemoryMax=3G -p MemorySwapMax=0 env OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1)
export OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
DRY=0
if [ "${1:-}" = "--dry-run" ]; then DRY=1; shift; fi
BLOCKS=("$@")
if [ ${#BLOCKS[@]} -eq 0 ]; then BLOCKS=(Q0 Q1 Q2 Q3 Q4 Q5 Q6); fi
if [ "$DRY" -eq 1 ]; then
  echo "[run_q44_study] dry run: blocks ${BLOCKS[*]}, $WORKERS worker(s), out $OUT (nothing is run or written)"
  "${SCOPE[@]}" "$PY" -m sublet.experiments.q44_study --estimate "${BLOCKS[@]}" --workers "$WORKERS"
  exit $?
fi
mkdir -p "$OUT/logs" "$OUT/jobs"

log() { echo "$*" | tee -a "$LOG"; }

job_done() {   # 0 if Q44_RESUME=1 and the job's record says ok
  [ "${Q44_RESUME:-0}" = "1" ] || return 1
  local f="$OUT/jobs/$(echo "$1" | sed -E 's/[^A-Za-z0-9_.-]+/__/g').json"
  [ -s "$f" ] && grep -q '"status": "ok' "$f"
}

run_one() {    # one job in its own scope; its console output in logs/<job>.log, the time line in the main log
  local job="$1"
  local name
  name="$(echo "$job" | sed -E 's/[^A-Za-z0-9_.-]+/__/g')"
  /usr/bin/time -o "$OUT/logs/$name.time" -f "[time] $job peak RSS %M KB, %e s, exit %x" \
    "${SCOPE[@]}" "$PY" -m sublet.experiments.q44_study --job "$job" --out "$OUT" > "$OUT/logs/$name.log" 2>&1
  local rc=$?
  cat "$OUT/logs/$name.time" >> "$LOG"
  if [ "$rc" -ne 0 ]; then
    "$PY" -m sublet.experiments.q44_study --record-failure "$job" --exit-code "$rc" --out "$OUT" >> "$LOG" 2>&1
    if [ "$rc" -eq 137 ]; then
      echo "[run_q44_study] $job: oom_at_3G (exit 137), not retried" >> "$LOG"
    else
      echo "[run_q44_study] $job: failed with exit code $rc (see logs/$name.log)" >> "$LOG"
    fi
  fi
  return 0
}

log "[run_q44_study] start $(date -Is) on $(hostname): blocks ${BLOCKS[*]}, $WORKERS worker(s), out $OUT"
"$PY" -m sublet.experiments.q44_study --manifest "${BLOCKS[@]}" --out "$OUT" 2>&1 | tee -a "$LOG"
if ! "$PY" -m sublet.experiments.q44_study --list "${BLOCKS[@]}" > "$OUT/jobs_list.txt" 2>> "$LOG"; then
  log "[run_q44_study] could not list the jobs of ${BLOCKS[*]}"; exit 1
fi
N_POOL=$(grep -c '^pool ' "$OUT/jobs_list.txt" || true)
N_ALONE=$(grep -c '^alone ' "$OUT/jobs_list.txt" || true)
log "[run_q44_study] $N_POOL pool jobs, $N_ALONE alone jobs"

# pool: at most $WORKERS jobs at a time
running=0
while read -r kind job; do
  [ "$kind" = "pool" ] || continue
  if job_done "$job"; then log "[run_q44_study] $job: done before, skipped"; continue; fi
  if [ "$running" -ge "$WORKERS" ]; then wait -n; running=$((running - 1)); fi
  echo "[run_q44_study] pool $job $(date -Is)" >> "$LOG"
  run_one "$job" < /dev/null &
  running=$((running + 1))
done < "$OUT/jobs_list.txt"
wait
log "[run_q44_study] pool done $(date -Is)"

# alone: one at a time, nothing else running
while read -r kind job; do
  [ "$kind" = "alone" ] || continue
  if job_done "$job"; then log "[run_q44_study] $job: done before, skipped"; continue; fi
  echo "[run_q44_study] alone $job $(date -Is)" >> "$LOG"
  run_one "$job" < /dev/null
done < "$OUT/jobs_list.txt"
log "[run_q44_study] alone done $(date -Is)"

"$PY" -m sublet.experiments.q44_study --manifest "${BLOCKS[@]}" --out "$OUT" 2>&1 | tee -a "$LOG"
/usr/bin/time -f "[time] summary peak RSS %M KB, %e s" "${SCOPE[@]}" "$PY" -m sublet.experiments.q44_summary --out "$OUT" 2>&1 | tee -a "$LOG"
log "[run_q44_study] done $(date -Is)"
