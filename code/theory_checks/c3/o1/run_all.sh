#!/bin/bash
# O1 checks (design/theory/o1_oblivious_lender.md). About 5-8 min on 5 cores. Outputs in out/.
set -e
cd "$(dirname "$0")"
PY=${PY:-$HOME/venv/bin/python}
mkdir -p out
for s in o1_lb o1_ub o1_rr_search o1_game; do
  echo "== $s"; $PY $s.py > out/$s.log
done
