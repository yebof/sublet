#!/usr/bin/env bash
# Audit R3 of design/theory/core_additive.md (Proposition A, Proposition B, the two-contract composition game):
# the auditor's independent checks. Report: design/theory/audit_core_additive.md. Each step runs alone in its own
# memory-capped scope; outputs and logs in out/. A step exits nonzero on a violation, and this script then stops.
# Measured on the 12-thread server (2026-11-24): audit_k2_game.py about 6 min, audit_additive.py about 3 min with
# 4 workers. Both take --reduced for a smoke run (a few seconds).
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p out
PY="systemd-run --user --scope -q -p MemoryMax=3G -p MemorySwapMax=0 env OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 $HOME/venv/bin/python"
echo "== audit_k2_game"; $PY audit_k2_game.py > out/audit_k2_game.log 2>&1
echo "== audit_additive"; $PY audit_additive.py --workers "${AUDIT_WORKERS:-4}" > out/audit_additive.log 2>&1
grep -H "violations" out/audit_k2_game.txt out/audit_additive.txt
