#!/usr/bin/env bash
# Regenerate the input tree tests/fixtures_figs_ms8/x7/inputs/ of the tests of the X7 supplementary script sf_e8q
# (tests/test_figs_ms8_x7.py; design/ms8/plan.md W; README in inputs/) from a reduced (smoke) run of the X7 driver.
# Nothing here is a result.
#
#   code/sim/tests/fixtures_figs_ms8/x7/refresh_inputs.sh SCRATCH [--reuse ROOT]
#
# SCRATCH  a folder outside the repository (created if absent), used as the MS3_ROOT of the reduced run, with a copy
#          of this repository's code/sim/out/e11/summary.json as the stand-in that the slot semaphore needs and
#          MS3_WORKERS=2 unless set (each job in its own 3G scope, by ms3_lib.sh):
#            sublet/experiments/run_e8q.sh --reduced          (E8 v2's reduced instance: 6 cells, 6 hours)
# --reuse ROOT  skip the run and trim from ROOT/out/e8q/ (an earlier reduced root)
# Then `python tests/fixtures_figs_ms8/x7/trim_inputs.py ROOT` (in a 3G scope) writes the tree: the trimmed summary,
# hist.json and the frozen analysis run on them (its docstring). Refresh the fixture extract afterwards:
# `python tests/fixtures_figs_ms8/x7/refresh_extracts.py` from code/sim. Reduced runs record the registration gate
# without enforcing it, so a dirty working tree is fine.
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"        # code/sim/tests/fixtures_figs_ms8/x7
SIM="$(cd "$HERE/../../.." && pwd)"                         # code/sim
REPO="$(cd "$SIM/../.." && pwd)"
EXP_DIR="$SIM/sublet/experiments"
PY="${MS3_PY:-$HOME/venv/bin/python}"
SCOPE=(systemd-run --user --scope -q -p MemoryMax=3G -p MemorySwapMax=0 env OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1)
export MS3_WORKERS="${MS3_WORKERS:-2}"

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
log() { echo "[refresh_inputs x7] $*"; }
fail() { echo "[refresh_inputs x7] $*" >&2; exit 1; }

if [ -n "$REUSE" ]; then
  ROOT="$(cd "$REUSE" && pwd)"
else
  mkdir -p "$SCRATCH"
  ROOT="$(cd "$SCRATCH" && pwd)"
  case "$ROOT/" in "$REPO/"*) echo "SCRATCH must lie outside the repository" >&2; exit 2 ;; esac
  mkdir -p "$ROOT/out/e11"
  cp "$SIM/out/e11/summary.json" "$ROOT/out/e11/summary.json"
  (cd "$SIM" && MS3_ROOT="$ROOT" "$EXP_DIR/run_e8q.sh" --reduced) > "$ROOT/e8q.console" 2>&1 \
    || fail "run_e8q.sh failed (see $ROOT/e8q.console)"
fi
(cd "$SIM" && "${SCOPE[@]}" "$PY" "$HERE/trim_inputs.py" "$ROOT") || fail "trim_inputs.py failed"
log "done; refresh the fixture extract: python tests/fixtures_figs_ms8/x7/refresh_extracts.py (from code/sim)"
