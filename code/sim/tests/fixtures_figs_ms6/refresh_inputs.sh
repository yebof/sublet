#!/usr/bin/env bash
# Regenerate the input tree tests/fixtures_figs_ms6/inputs/ of the MS6 figure tests (design/ms6_spec.md §2 U44; README
# in inputs/) from a reduced run of the driver of Fig. 1 v2.
#
#   code/sim/tests/fixtures_figs_ms6/refresh_inputs.sh
#
# Runs `python -m sublet.experiments.fig1_illustrative --reduced --out <tree>/code/sim/out/fig1v2` from code/sim in a
# 3G scope: Sublet on the first 3 hours of the pilot cell Q44 I2 c1 under L-eg, policy seed 0 (the driver's
# WINDOW_REDUCED), with the logged and the unlogged run compared. It writes run.json and manifest.json there, and exits
# nonzero if the driver's checks fail (the driver's exit status). Run from anywhere; about 15 s. README.md is written by
# hand: update its commit line after a refresh, then refresh the fixture extracts (refresh_extracts.py).
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"        # code/sim/tests/fixtures_figs_ms6
SIM="$(cd "$HERE/../.." && pwd)"                            # code/sim
PY="${MS3_PY:-$HOME/venv/bin/python}"
DEST="$HERE/inputs/code/sim/out/fig1v2"
cd "$SIM" || exit 1
systemd-run --user --scope -q -p MemoryMax=3G -p MemorySwapMax=0 env OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 \
  "$PY" -m sublet.experiments.fig1_illustrative --reduced --out "$DEST"
rc=$?
echo "[refresh_inputs ms6] driver exit $rc; commit $(git -C "$SIM" rev-parse HEAD); $(ls "$DEST" | tr '\n' ' ')"
exit "$rc"
