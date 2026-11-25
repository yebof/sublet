#!/usr/bin/env bash
# Regenerate the input tree tests/fixtures_figs_ms7/g4a/inputs/ of the tests of figs/supp/sf_lag_v2.py and sf_oos.py
# (tests/test_figs_ms7_a.py; design/ms7/w_spec.md §4, unit W-G4, writer A; README in inputs/) from reduced (smoke)
# runs of the X1 and X2 drivers and their registered analyses, run against the MS5b fixture tree's confirmation summary
# (development week 101, two hours). Nothing here is a result.
#
#   code/sim/tests/fixtures_figs_ms7/g4a/refresh_inputs.sh SCRATCH [--reuse-e7c ROOT] [--reuse-e7o ROOT] [--no-run]
#
# SCRATCH  a folder outside the repository (created if absent), with one MS3_ROOT per experiment, each with a copy of
#          this repository's code/sim/out/e11/summary.json as the stand-in that the slot semaphore needs, the MS5b
#          fixture's main (and, for X1, second) summary in out/sublet_v2/, and MS3_WORKERS=1 unless set (each job in
#          its own 3G scope, by ms3_lib.sh):
#   e7c    SCRATCH/e7c: E7C_PART="gate lag" MS3_ROOT=SCRATCH/e7c sublet/experiments/run_e7c.sh --reduced, or with
#          --reuse-e7c ROOT the parts' summary.json copied from ROOT/out/e7c/ (an earlier reduced run against the
#          same MS5b summaries, e.g. stage 3's smoke root); then python -m sublet.experiments.e7c_analysis --root
#   e7o    SCRATCH/e7o: E7O_PART="fwd rev" MS3_ROOT=SCRATCH/e7o sublet/experiments/run_e7o.sh --reduced, or with
#          --reuse-e7o ROOT the parts' summary.json copied from ROOT/out/e7o/ (e.g. unit B3's smoke root); then
#          python -m sublet.experiments.e7o_analysis --root (its bridge reads the MS5b fixture's week 101)
# --no-run  skip the runs and analyses; trim from the roots that SCRATCH already holds
# Then `python tests/fixtures_figs_ms7/g4a/trim_inputs.py SCRATCH` writes the tree (its docstring lists the files).
# Refresh the fixture extracts afterwards: `python tests/fixtures_figs_ms7/g4a/refresh_extracts.py` from code/sim.
# The analyses run in 3G scopes; reduced runs record the registration gate without enforcing it.
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"        # code/sim/tests/fixtures_figs_ms7/g4a
SIM="$(cd "$HERE/../../.." && pwd)"                         # code/sim
REPO="$(cd "$SIM/../.." && pwd)"
EXP_DIR="$SIM/sublet/experiments"
MS5B_CONF="$SIM/tests/fixtures_figs_ms5b/inputs/code/sim/out/sublet_v2"
PY="${MS3_PY:-$HOME/venv/bin/python}"
SCOPE=(systemd-run --user --scope -q -p MemoryMax=3G -p MemorySwapMax=0 env OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1)
export MS3_WORKERS="${MS3_WORKERS:-1}"

usage() { echo "usage: $0 SCRATCH [--reuse-e7c ROOT] [--reuse-e7o ROOT] [--no-run]" >&2; exit 2; }
[ $# -ge 1 ] || usage
SCRATCH="$1"; shift
RUN=1; REUSE_E7C=""; REUSE_E7O=""
while [ $# -gt 0 ]; do
  case "$1" in
    --no-run) RUN=0 ;;
    --reuse-e7c) shift; [ $# -gt 0 ] || usage; REUSE_E7C="$1" ;;
    --reuse-e7o) shift; [ $# -gt 0 ] || usage; REUSE_E7O="$1" ;;
    *) usage ;;
  esac
  shift
done
mkdir -p "$SCRATCH"
SCRATCH="$(cd "$SCRATCH" && pwd)"
case "$SCRATCH/" in "$REPO/"*) echo "SCRATCH must lie outside the repository" >&2; exit 2 ;; esac
log() { echo "[refresh_inputs g4a] $*"; }
fail() { echo "[refresh_inputs g4a] $*" >&2; exit 1; }

root() {              # root NAME: a fresh MS3_ROOT with the semaphore's stand-in and the MS5b fixture's summaries
  local r="$SCRATCH/$1"
  mkdir -p "$r/out/e11" "$r/out/sublet_v2/main" "$r/out/sublet_v2/second"
  cp "$SIM/out/e11/summary.json" "$r/out/e11/summary.json"
  cp "$MS5B_CONF/main/summary.json" "$r/out/sublet_v2/main/summary.json"
  cp "$MS5B_CONF/second/summary.json" "$r/out/sublet_v2/second/summary.json"
  echo "$r"
}

if [ "$RUN" = 1 ]; then
  # X1: the causal runs (or an earlier reduced run's summaries) and their analysis
  R="$(root e7c)"
  if [ -n "$REUSE_E7C" ]; then
    for p in gate lag; do
      mkdir -p "$R/out/e7c/$p"
      cp "$REUSE_E7C/out/e7c/$p/summary.json" "$R/out/e7c/$p/summary.json" || fail "no $p summary in $REUSE_E7C"
    done
  else
    (cd "$SIM" && E7C_PART="gate lag" MS3_ROOT="$R" "$EXP_DIR/run_e7c.sh" --reduced) > "$SCRATCH/e7c.console" 2>&1 \
      || fail "run_e7c.sh failed (see $SCRATCH/e7c.console)"
  fi
  (cd "$SIM" && "${SCOPE[@]}" "$PY" -m sublet.experiments.e7c_analysis --root "$R") || fail "e7c_analysis failed"
  # X2: the out-of-sample folds (or an earlier reduced run's summaries) and their analysis
  R="$(root e7o)"
  if [ -n "$REUSE_E7O" ]; then
    for p in fwd rev; do
      mkdir -p "$R/out/e7o/$p"
      cp "$REUSE_E7O/out/e7o/$p/summary.json" "$R/out/e7o/$p/summary.json" || fail "no $p summary in $REUSE_E7O"
    done
  else
    (cd "$SIM" && E7O_PART="fwd rev" MS3_ROOT="$R" "$EXP_DIR/run_e7o.sh" --reduced) > "$SCRATCH/e7o.console" 2>&1 \
      || fail "run_e7o.sh failed (see $SCRATCH/e7o.console)"
  fi
  (cd "$SIM" && "${SCOPE[@]}" "$PY" -m sublet.experiments.e7o_analysis --root "$R") || fail "e7o_analysis failed"
fi
(cd "$SIM" && "${SCOPE[@]}" "$PY" "$HERE/trim_inputs.py" "$SCRATCH") || fail "trim_inputs.py failed"
log "done; refresh the fixture extracts: python tests/fixtures_figs_ms7/g4a/refresh_extracts.py (from code/sim)"
