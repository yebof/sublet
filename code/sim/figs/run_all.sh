#!/usr/bin/env bash
# The frozen rebuild (design/sim_spec_ms5.md §8; deliverable D43, unit U30; M29-M33): every figure of the paper and
# the supplement (the main-text figs/fig*.py and the figs/supp/sf_*.py, from style.FIGURES and the supplementary
# registrations), every extract-based table and Table III rebuilt from the versioned JSON extracts, the print sheet
# (C28) rebuilt from the main-text PDFs, and the float heights re-measured (floats_heights.py plain and --ms4); each
# script in its own 3 GB scope, one after another; every output compared byte for byte with its versioned file, the
# float heights on every key but 'written', the hand-set floats and the print-check record by sha256. The list, the
# comparison and the record are figs/rebuild.py's (its docstring: python -m figs.rebuild --help).
#
#   code/sim/figs/run_all.sh                 in place: the outputs are rewritten where they live, and `git status`
#                                            shows no change but the record code/sim/out/figs/rebuild.json when the
#                                            rebuild is exact
#   CHECK=1 code/sim/figs/run_all.sh         the outputs go to a temporary folder (SUBLET_FIGS_PDF_DIR,
#                                            SUBLET_FIGS_OUT_DIR, SUBLET_FIGS_TABLES_DIR, table3_e7.py --out) and are
#                                            compared byte for byte with the versioned files; the record goes to
#                                            <folder>/rebuild.json (copied into code/sim/out/figs/ by the integrator
#                                            after the exit run in a clean clone, §8.4); without KEEP=1 the rebuilt
#                                            files are removed and the folder keeps rebuild.json and rebuild.log
#   ONLY=<regex>                             only the scripts whose name (fig1, sf_e6a, table3_e7, print_check,
#                                            floats_heights, floats_heights_ms4) or module matches; the coverage and
#                                            the hand-set checks still cover the whole list
#   DRY_RUN=1                                print the list and the coverage, run nothing
#   KEEP=1                                   keep the rebuilt files
#   WORK=<dir>                               the temporary folder (new or empty; default a new folder under TMPDIR)
#   REBUILD_ROOT=<dir>                       for tests: a folder with the repository's layout in place of the
#                                            repository (its extracts are read, its files compared)
#
# Exit 0 iff every output is identical, every listed file exists, no versioned figure, table or extract lacks its
# entry, the float heights are equal and the hand-set files are unchanged (figs/rebuild.py); 1 otherwise; 2 on a usage
# error. The orchestrator runs in its own 3 GB scope and starts one scope per script. Never edit this script while it
# runs.
set -u
SIM="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"          # code/sim
PY="$HOME/venv/bin/python"

flag() {              # flag NAME VALUE: 0 or empty is off, 1 is on, anything else is a usage error
  case "$2" in
    ""|0) return 1 ;;
    1) return 0 ;;
    *) echo "run_all.sh: $1 must be 0 or 1, not '$2'" >&2; exit 2 ;;
  esac
}

args=()
if flag CHECK "${CHECK:-}"; then args+=(--check); fi
if flag KEEP "${KEEP:-}"; then args+=(--keep); fi
if flag DRY_RUN "${DRY_RUN:-}"; then args+=(--dry-run); fi
if [ -n "${ONLY:-}" ]; then args+=(--only "$ONLY"); fi
if [ -n "${WORK:-}" ]; then args+=(--work "$WORK"); fi
if [ -n "${REBUILD_ROOT:-}" ]; then args+=(--root "$REBUILD_ROOT"); fi

cd "$SIM" || exit 2
exec systemd-run --user --scope -q -p MemoryMax=3G -p MemorySwapMax=0 \
  env OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 "$PY" -m figs.rebuild "${args[@]}"
