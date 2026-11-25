#!/usr/bin/env bash
# Regenerate the input tree tests/fixtures_figs_ms7/inputs/ of the MS7 figure and table tests (Fig. 3 v3, Tables IV
# and V; design/ms7/w_spec.md §4, unit W-G2; README in inputs/) from reduced (smoke) runs of the MS7 drivers and their
# registered analyses, run against the MS5b fixture tree's confirmation summaries (development week 101, two hours).
# Nothing here is a result.
#
#   code/sim/tests/fixtures_figs_ms7/refresh_inputs.sh SCRATCH [--reuse-e7r ROOT] [--reuse-s1v2 ROOT] [--no-run]
#
# SCRATCH  a folder outside the repository (created if absent), with one MS3_ROOT per experiment, each with a copy of
#          this repository's code/sim/out/e11/summary.json as the stand-in that the slot semaphore needs and
#          MS3_WORKERS=1 unless set (each job in its own 3G scope, by ms3_lib.sh):
#   e7c    SCRATCH/e7c, with the MS5b fixture's main and second summaries in out/sublet_v2/ (part lag's lagged
#          RetroRenting-style rows are main's):
#            E7C_PART="gate lag" MS3_ROOT=SCRATCH/e7c sublet/experiments/run_e7c.sh --reduced     (about 10 min)
#            python -m sublet.experiments.e7c_analysis --root SCRATCH/e7c
#   e7r    SCRATCH/e7r: E7R_PART="tune confirm eval" MS3_ROOT=SCRATCH/e7r sublet/experiments/run_e7r.sh --reduced, or
#          with --reuse-e7r ROOT the parts' summary.json and tune/selection.json copied from ROOT/out/e7r/ (an earlier
#          reduced run, e.g. unit B2's smoke root); then
#            python -m sublet.experiments.e7r_analysis --root SCRATCH/e7r --frozen <MS5b fixture>/out/sublet_v2
#   s1v2   SCRATCH/s1v2: S1V2_PART="sweep w0" MS3_ROOT=SCRATCH/s1v2 sublet/experiments/run_s1v2.sh --reduced, or with
#          --reuse-s1v2 ROOT the parts' summary.json copied from ROOT/out/s1v2/ (e.g. unit B4's smoke root); then
#          ms7_sens_analysis.run_analysis(['s1v2'], root=SCRATCH/s1v2, conf_dir=<MS5b fixture>/out/sublet_v2), whose
#          seed spread is then the fixture's (the command line has no conf_dir option)
# --no-run  skip the runs and analyses; trim from the roots that SCRATCH already holds
# Then `python tests/fixtures_figs_ms7/trim_inputs.py SCRATCH` writes the tree (its docstring lists the files). Refresh
# the fixture extracts afterwards: `python tests/fixtures_figs_ms7/refresh_extracts.py` from code/sim. The analyses run
# in 3G scopes; reduced runs record the registration gate without enforcing it, so a dirty working tree is fine.
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"        # code/sim/tests/fixtures_figs_ms7
SIM="$(cd "$HERE/../.." && pwd)"                            # code/sim
REPO="$(cd "$SIM/../.." && pwd)"
EXP_DIR="$SIM/sublet/experiments"
MS5B_CONF="$SIM/tests/fixtures_figs_ms5b/inputs/code/sim/out/sublet_v2"
PY="${MS3_PY:-$HOME/venv/bin/python}"
SCOPE=(systemd-run --user --scope -q -p MemoryMax=3G -p MemorySwapMax=0 env OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1)
export MS3_WORKERS="${MS3_WORKERS:-1}"

usage() { echo "usage: $0 SCRATCH [--reuse-e7r ROOT] [--reuse-s1v2 ROOT] [--no-run]" >&2; exit 2; }
[ $# -ge 1 ] || usage
SCRATCH="$1"; shift
RUN=1; REUSE_E7R=""; REUSE_S1V2=""
while [ $# -gt 0 ]; do
  case "$1" in
    --no-run) RUN=0 ;;
    --reuse-e7r) shift; [ $# -gt 0 ] || usage; REUSE_E7R="$1" ;;
    --reuse-s1v2) shift; [ $# -gt 0 ] || usage; REUSE_S1V2="$1" ;;
    *) usage ;;
  esac
  shift
done
mkdir -p "$SCRATCH"
SCRATCH="$(cd "$SCRATCH" && pwd)"
case "$SCRATCH/" in "$REPO/"*) echo "SCRATCH must lie outside the repository" >&2; exit 2 ;; esac
log() { echo "[refresh_inputs ms7] $*"; }
fail() { echo "[refresh_inputs ms7] $*" >&2; exit 1; }

root() {              # root NAME: a fresh MS3_ROOT with the semaphore's stand-in
  local r="$SCRATCH/$1"
  mkdir -p "$r/out/e11"
  cp "$SIM/out/e11/summary.json" "$r/out/e11/summary.json"
  echo "$r"
}

if [ "$RUN" = 1 ]; then
  # X1: the causal runs and their analysis
  R="$(root e7c)"
  mkdir -p "$R/out/sublet_v2/main" "$R/out/sublet_v2/second"
  cp "$MS5B_CONF/main/summary.json" "$R/out/sublet_v2/main/summary.json"
  cp "$MS5B_CONF/second/summary.json" "$R/out/sublet_v2/second/summary.json"
  (cd "$SIM" && E7C_PART="gate lag" MS3_ROOT="$R" "$EXP_DIR/run_e7c.sh" --reduced) > "$SCRATCH/e7c.console" 2>&1 \
    || fail "run_e7c.sh failed (see $SCRATCH/e7c.console)"
  (cd "$SIM" && "${SCOPE[@]}" "$PY" -m sublet.experiments.e7c_analysis --root "$R") || fail "e7c_analysis failed"
  # X4: the baseline runs (or an earlier reduced run's summaries) and their analysis
  R="$(root e7r)"
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
  # X3: S1 v2 (or an earlier reduced run's summaries) and its analysis on the fixture's confirmation
  R="$(root s1v2)"
  if [ -n "$REUSE_S1V2" ]; then
    for p in sweep w0; do
      mkdir -p "$R/out/s1v2/$p"
      cp "$REUSE_S1V2/out/s1v2/$p/summary.json" "$R/out/s1v2/$p/summary.json" || fail "no $p summary in $REUSE_S1V2"
    done
  else
    (cd "$SIM" && S1V2_PART="sweep w0" MS3_ROOT="$R" "$EXP_DIR/run_s1v2.sh" --reduced) \
      > "$SCRATCH/s1v2.console" 2>&1 || fail "run_s1v2.sh failed (see $SCRATCH/s1v2.console)"
  fi
  (cd "$SIM" && "${SCOPE[@]}" "$PY" -c "from sublet.experiments import ms7_sens_analysis as M; \
M.run_analysis(['s1v2'], root='$R', conf_dir='$MS5B_CONF')") || fail "ms7_sens_analysis failed"
fi
(cd "$SIM" && "${SCOPE[@]}" "$PY" "$HERE/trim_inputs.py" "$SCRATCH") || fail "trim_inputs.py failed"
log "done; refresh the fixture extracts: python tests/fixtures_figs_ms7/refresh_extracts.py (from code/sim)"
