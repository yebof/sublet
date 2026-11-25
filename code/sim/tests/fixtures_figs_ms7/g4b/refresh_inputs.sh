#!/usr/bin/env bash
# Regenerate the input tree tests/fixtures_figs_ms7/g4b/inputs/ of the tests of the MS7 baseline and stress figures
# (figs/supp/sf_bl_ms7.py, sf_stress_ms7.py; design/ms7/w_spec.md §4, unit W-G4 B; README in inputs/) from a reduced
# (smoke) run of the baseline study and its registered analysis, run against the MS5b fixture tree's confirmation
# summaries (development week 101, two hours). Nothing here is a result.
#
#   code/sim/tests/fixtures_figs_ms7/g4b/refresh_inputs.sh SCRATCH [--reuse-e7r ROOT] [--no-run]
#
# SCRATCH   a folder outside the repository (created if absent); SCRATCH/e7r is the MS3_ROOT of the run, with a copy of
#           this repository's code/sim/out/e11/summary.json as the stand-in that the slot semaphore needs and
#           MS3_WORKERS=1 unless set (each job in its own 3G scope, by ms3_lib.sh):
#             E7R_PART="tune confirm eval" MS3_ROOT=SCRATCH/e7r sublet/experiments/run_e7r.sh --reduced
#           or, with --reuse-e7r ROOT, the parts' summary.json and tune/selection.json copied from ROOT/out/e7r/ (an
#           earlier reduced run, e.g. unit B2's smoke root); then
#             python -m sublet.experiments.e7r_analysis --root SCRATCH/e7r --frozen <MS5b fixture>/out/sublet_v2
# --no-run  skip the run and the analysis; trim from SCRATCH/e7r as it is
# Then `python tests/fixtures_figs_ms7/g4b/trim_inputs.py SCRATCH/e7r` writes the tree (its docstring lists the files).
# Refresh the fixture extracts afterwards: `python tests/fixtures_figs_ms7/g4b/refresh_extracts.py` from code/sim. The
# analysis runs in a 3G scope; a reduced run records the registration gate without enforcing it, so a dirty working
# tree is fine. The tree of 2026-11-09 was made with --reuse-e7r from the root that unit W-G2 made for
# tests/fixtures_figs_ms7/ (unit B2's reduced runs at 56b847be, analysed against the MS5b fixture).
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"        # code/sim/tests/fixtures_figs_ms7/g4b
SIM="$(cd "$HERE/../../.." && pwd)"                         # code/sim
REPO="$(cd "$SIM/../.." && pwd)"
EXP_DIR="$SIM/sublet/experiments"
MS5B_CONF="$SIM/tests/fixtures_figs_ms5b/inputs/code/sim/out/sublet_v2"
PY="${MS3_PY:-$HOME/venv/bin/python}"
SCOPE=(systemd-run --user --scope -q -p MemoryMax=3G -p MemorySwapMax=0 env OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1)
export MS3_WORKERS="${MS3_WORKERS:-1}"

usage() { echo "usage: $0 SCRATCH [--reuse-e7r ROOT] [--no-run]" >&2; exit 2; }
[ $# -ge 1 ] || usage
SCRATCH="$1"; shift
RUN=1; REUSE_E7R=""
while [ $# -gt 0 ]; do
  case "$1" in
    --no-run) RUN=0 ;;
    --reuse-e7r) shift; [ $# -gt 0 ] || usage; REUSE_E7R="$1" ;;
    *) usage ;;
  esac
  shift
done
mkdir -p "$SCRATCH"
SCRATCH="$(cd "$SCRATCH" && pwd)"
case "$SCRATCH/" in "$REPO/"*) echo "SCRATCH must lie outside the repository" >&2; exit 2 ;; esac
log() { echo "[refresh_inputs g4b] $*"; }
fail() { echo "[refresh_inputs g4b] $*" >&2; exit 1; }

R="$SCRATCH/e7r"
if [ "$RUN" = 1 ]; then
  mkdir -p "$R/out/e11"
  cp "$SIM/out/e11/summary.json" "$R/out/e11/summary.json"
  if [ -n "$REUSE_E7R" ]; then
    for p in tune confirm eval; do
      mkdir -p "$R/out/e7r/$p"
      cp "$REUSE_E7R/out/e7r/$p/summary.json" "$R/out/e7r/$p/summary.json" || fail "no $p summary in $REUSE_E7R"
    done
    cp "$REUSE_E7R/out/e7r/tune/selection.json" "$R/out/e7r/tune/selection.json" || fail "no selection in $REUSE_E7R"
  else
    (cd "$SIM" && E7R_PART="tune confirm eval" MS3_ROOT="$R" "$EXP_DIR/run_e7r.sh" --reduced) \
      > "$SCRATCH/e7r.console" 2>&1 || fail "run_e7r.sh failed (see $SCRATCH/e7r.console)"
  fi
  (cd "$SIM" && "${SCOPE[@]}" "$PY" -m sublet.experiments.e7r_analysis --root "$R" --frozen "$MS5B_CONF") \
    || fail "e7r_analysis failed"
fi
(cd "$SIM" && "${SCOPE[@]}" "$PY" "$HERE/trim_inputs.py" "$R") || fail "trim_inputs.py failed"
log "done; refresh the fixture extracts: python tests/fixtures_figs_ms7/g4b/refresh_extracts.py (from code/sim)"
