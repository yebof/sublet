#!/usr/bin/env bash
# Regenerate the input tree tests/fixtures_figs_ms7/g4c/inputs/ of the tests of the X3 supplementary scripts sf_s1_v2,
# sf_e5_v2, sf_e8_v2 and sf_e9_v2 (tests/test_figs_ms7_c.py; design/ms7/w_spec.md §4, unit W-G4, writer C; README in
# inputs/) from reduced (smoke) runs of the X3 drivers. Nothing here is a result.
#
#   code/sim/tests/fixtures_figs_ms7/g4c/refresh_inputs.sh SCRATCH [--reuse ROOT]
#
# SCRATCH  a folder outside the repository (created if absent), used as the MS3_ROOT of the reduced runs, with a copy
#          of this repository's code/sim/out/e11/summary.json as the stand-in that the slot semaphore needs and
#          MS3_WORKERS=1 unless set (each job in its own 3G scope, by ms3_lib.sh):
#            S1V2_PART="sweep w0" sublet/experiments/run_s1v2.sh --reduced
#            sublet/experiments/run_e5v2.sh --reduced
#            sublet/experiments/run_e8v2.sh --reduced
#            sublet/experiments/run_e9v2.sh --reduced          (alone; it takes every slot)
# --reuse ROOT  skip the runs and trim from ROOT/out/ (an earlier reduced root, e.g. unit B4's smoke root)
# Then `python tests/fixtures_figs_ms7/g4c/trim_inputs.py ROOT` (in a 3G scope) writes the tree: the trimmed summaries
# and the frozen analysis run on them (its docstring). Refresh the fixture extracts afterwards:
# `python tests/fixtures_figs_ms7/g4c/refresh_extracts.py` from code/sim. Reduced runs record the registration gate
# without enforcing it, so a dirty working tree is fine.
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"        # code/sim/tests/fixtures_figs_ms7/g4c
SIM="$(cd "$HERE/../../.." && pwd)"                         # code/sim
REPO="$(cd "$SIM/../.." && pwd)"
EXP_DIR="$SIM/sublet/experiments"
PY="${MS3_PY:-$HOME/venv/bin/python}"
SCOPE=(systemd-run --user --scope -q -p MemoryMax=3G -p MemorySwapMax=0 env OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1)
export MS3_WORKERS="${MS3_WORKERS:-1}"

usage() { echo "usage: $0 SCRATCH [--reuse ROOT]" >&2; exit 2; }
[ $# -ge 1 ] || usage
SCRATCH="$1"; shift
REUSE=""
while [ $# -gt 0 ]; do
  case "$1" in
    --reuse) shift; [ $# -gt 0 ] || usage; REUSE="$1" ;;
    *) usage ;;
  esac
  shift
done
log() { echo "[refresh_inputs g4c] $*"; }
fail() { echo "[refresh_inputs g4c] $*" >&2; exit 1; }

if [ -n "$REUSE" ]; then
  ROOT="$(cd "$REUSE" && pwd)"
else
  mkdir -p "$SCRATCH"
  ROOT="$(cd "$SCRATCH" && pwd)"
  case "$ROOT/" in "$REPO/"*) echo "SCRATCH must lie outside the repository" >&2; exit 2 ;; esac
  mkdir -p "$ROOT/out/e11"
  cp "$SIM/out/e11/summary.json" "$ROOT/out/e11/summary.json"
  (cd "$SIM" && S1V2_PART="sweep w0" MS3_ROOT="$ROOT" "$EXP_DIR/run_s1v2.sh" --reduced) > "$ROOT/s1v2.console" 2>&1 \
    || fail "run_s1v2.sh failed (see $ROOT/s1v2.console)"
  for exp in e5v2 e8v2 e9v2; do
    (cd "$SIM" && MS3_ROOT="$ROOT" "$EXP_DIR/run_$exp.sh" --reduced) > "$ROOT/$exp.console" 2>&1 \
      || fail "run_$exp.sh failed (see $ROOT/$exp.console)"
  done
fi
(cd "$SIM" && "${SCOPE[@]}" "$PY" "$HERE/trim_inputs.py" "$ROOT") || fail "trim_inputs.py failed"
log "done; refresh the fixture extracts: python tests/fixtures_figs_ms7/g4c/refresh_extracts.py (from code/sim)"
