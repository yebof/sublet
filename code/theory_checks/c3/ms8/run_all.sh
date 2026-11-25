#!/usr/bin/env bash
# MS8 theory checks (design/ms8/plan.md D3, D2): Proposition A, the additive price on phase-predictable
# demand (check_additive.py), the two-contract composition game (check_k2_composition.py), and, if present,
# the naive spend-cap examples of unit U2 (check_naive_cap.py). Theory note: design/theory/core_additive.md.
# Each step runs alone in its own memory-capped scope; outputs and logs in out/. A step exits nonzero on a
# violation, and this script then stops (set -e). Workers of check_additive.py: env ADD_WORKERS (default 3).
# Measured on the 12-thread server (2026-11-24): check_k2_composition.py about 10 min, check_additive.py about
# 7 min with 3 workers (21 min of CPU), check_naive_cap.py under 1 min.
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p out
PY="systemd-run --user --scope -q -p MemoryMax=3G -p MemorySwapMax=0 env OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 $HOME/venv/bin/python"
echo "== check_k2_composition"; $PY check_k2_composition.py > out/check_k2_composition.log 2>&1
echo "== check_additive"; $PY check_additive.py --workers "${ADD_WORKERS:-3}" > out/check_additive.log 2>&1
if [ -f check_naive_cap.py ]; then
  echo "== check_naive_cap"; $PY check_naive_cap.py > out/check_naive_cap.txt 2>&1
fi
grep -H -i "violations" out/check_k2_composition.log out/check_additive.log || true
