#!/usr/bin/env bash
# MS7 theory checks (design/ms7/plan.md D8): the independent audits' numerical checks of Supplement S-B.7 and S-D.10,
# each in its own memory-capped scope; outputs in out/. A check prints its violation counts (0 expected).
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p out
PY="systemd-run --user --scope -q -p MemoryMax=3G -p MemorySwapMax=0 env OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 $HOME/venv/bin/python"
$PY check_raises.py 400 > out/check_raises.txt 2>&1
$PY check_tradeoff.py > out/check_tradeoff.txt 2>&1
grep -H "violation" out/*.txt
