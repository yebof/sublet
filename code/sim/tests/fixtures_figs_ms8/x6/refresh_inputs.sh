#!/usr/bin/env bash
# Regenerate the input tree tests/fixtures_figs_ms8/x6/inputs/ of the tests of the budget-cap figure
# (figs/supp/sf_cap.py; design/ms8/plan.md D2, W; README in inputs/) from a reduced (smoke) run of the budget-cap
# driver and its registered analysis, run against reduced frozen stand-ins of development week 101 (two hours).
# Nothing here is a result.
#
#   code/sim/tests/fixtures_figs_ms8/x6/refresh_inputs.sh SCRATCH --frozen DIR [--reuse-e7b ROOT] [--no-run]
#
# SCRATCH      a folder outside the repository (created if absent); SCRATCH/root is the MS3_ROOT of the run, with a
#              copy of this repository's code/sim/out/e11/summary.json as the stand-in that the slot semaphore needs and
#              MS3_WORKERS=1 unless set (each job in its own 3G scope, by ms3_lib.sh):
#                E7B_PART="week sens" MS3_ROOT=SCRATCH/root E7B_FROZEN=DIR sublet/experiments/run_e7b.sh --reduced
#              which runs e7b_analysis.py after part sens (a reduced run records the registration gate without
#              enforcing it, so a dirty working tree is fine);
# --frozen DIR the frozen stand-ins (DIR/sublet_v2/main, DIR/e7r/eval, DIR/s1v2/sweep, DIR/s1v2/w0, each summary.json,
#              reduced runs of week 101), made by assemble_frozen.py (its docstring names the sources of the tree);
# --reuse-e7b ROOT  copy the parts' summary.json from ROOT/out/e7b/ (an earlier reduced run) instead of running, then
#              run the analysis against DIR;
# --no-run     skip the run and the analysis; trim from SCRATCH/root as it is.
# Then `python tests/fixtures_figs_ms8/x6/trim_inputs.py SCRATCH/root` writes the tree. Refresh the fixture extract
# afterwards: `python tests/fixtures_figs_ms8/x6/refresh_extracts.py` from code/sim. The tree of 2026-11-24 was made
# by this script with MS3_WORKERS=2 at the MS8 run commit's working tree (the figure scripts' edits only).
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"        # code/sim/tests/fixtures_figs_ms8/x6
SIM="$(cd "$HERE/../../.." && pwd)"                         # code/sim
REPO="$(cd "$SIM/../.." && pwd)"
EXP_DIR="$SIM/sublet/experiments"
PY="${MS3_PY:-$HOME/venv/bin/python}"
SCOPE=(systemd-run --user --scope -q -p MemoryMax=3G -p MemorySwapMax=0 env OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1)
export MS3_WORKERS="${MS3_WORKERS:-1}"

usage() { echo "usage: $0 SCRATCH --frozen DIR [--reuse-e7b ROOT] [--no-run]" >&2; exit 2; }
[ $# -ge 1 ] || usage
SCRATCH="$1"; shift
RUN=1; REUSE=""; FROZEN=""
while [ $# -gt 0 ]; do
  case "$1" in
    --no-run) RUN=0 ;;
    --frozen) shift; [ $# -gt 0 ] || usage; FROZEN="$1" ;;
    --reuse-e7b) shift; [ $# -gt 0 ] || usage; REUSE="$1" ;;
    *) usage ;;
  esac
  shift
done
mkdir -p "$SCRATCH"
SCRATCH="$(cd "$SCRATCH" && pwd)"
case "$SCRATCH/" in "$REPO/"*) echo "SCRATCH must lie outside the repository" >&2; exit 2 ;; esac
log() { echo "[refresh_inputs x6] $*"; }
fail() { echo "[refresh_inputs x6] $*" >&2; exit 1; }

R="$SCRATCH/root"
if [ "$RUN" = 1 ]; then
  [ -n "$FROZEN" ] || usage
  FROZEN="$(cd "$FROZEN" && pwd)" || fail "no folder $FROZEN"
  for f in sublet_v2/main e7r/eval s1v2/sweep s1v2/w0; do
    [ -f "$FROZEN/$f/summary.json" ] || fail "no $FROZEN/$f/summary.json (assemble_frozen.py)"
  done
  mkdir -p "$R/out/e11"
  cp "$SIM/out/e11/summary.json" "$R/out/e11/summary.json"
  if [ -n "$REUSE" ]; then
    for p in week sens; do
      mkdir -p "$R/out/e7b/$p"
      cp "$REUSE/out/e7b/$p/summary.json" "$R/out/e7b/$p/summary.json" || fail "no $p summary in $REUSE"
    done
    (cd "$SIM" && "${SCOPE[@]}" "$PY" -m sublet.experiments.e7b_analysis --root "$R" --frozen "$FROZEN") \
      || fail "e7b_analysis failed"
  else
    (cd "$SIM" && E7B_PART="week sens" MS3_ROOT="$R" E7B_FROZEN="$FROZEN" MS3_PY="$PY" \
      "$EXP_DIR/run_e7b.sh" --reduced) > "$SCRATCH/run_e7b.console" 2>&1 \
      || fail "run_e7b.sh failed (see $SCRATCH/run_e7b.console)"
  fi
fi
[ -f "$R/out/e7b/analysis.json" ] || fail "no $R/out/e7b/analysis.json"
(cd "$SIM" && "${SCOPE[@]}" "$PY" "$HERE/trim_inputs.py" "$R") || fail "trim_inputs.py failed"
log "done; refresh the fixture extract: python tests/fixtures_figs_ms8/x6/refresh_extracts.py (from code/sim)"
