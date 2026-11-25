#!/bin/bash
# Runs all C3/C4/C5 numerical checks (about 1-2 min on 5 cores) and the guard check check_guard.py
# (C3 §9, Lemma G1 - Proposition G6, and the K0 check of Proposition P; audit design/theory/audit_guard.md; about
# 18 min on 2 workers, env GUARD_WORKERS), then check_g5p.py (Lemma G5', C3 §9; needs the raw traces and the a12
# outputs for its E3 instances, G5P_SKIP_E3=1 skips them; about 9 min on 2 workers, env G5P_WORKERS). Outputs in out/.
# O1 checks: o1/run_all.sh; audit checks: audit/.
set -e
cd "$(dirname "$0")"
PY=${PY:-$HOME/venv/bin/python}
mkdir -p out
for s in check_c3_upper check_c3_benchmark check_c4_lower check_c5_la check_c5_la_nearest check_guard; do
  echo "== $s"; $PY $s.py | tee out/$s.log
done
echo "== check_g5p"; $PY check_g5p.py | tee out/check_g5p.log
