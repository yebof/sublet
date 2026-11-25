#!/bin/bash
# Runs the C3 audit checks. Outputs in out/. Run under a memory cap if desired (each needs < 0.2 GB).
# a1-a4: audit of C3-C5 (design/theory/audit_c3_c4_c5.md), a few seconds in total.
# a5-a7: audit of the guard, C3 §9 (design/theory/audit_guard.md); a5 writes one file per part
# (out/a5_guard_independent_<part>.txt), a6 and a7 write their own files. About 3.5 min on one worker,
# of which a5 part A takes about 3 min (env GUARD_WORKERS, default 1).
set -e
cd "$(dirname "$0")"
PY=${PY:-$HOME/venv/bin/python}
mkdir -p out
for s in a1_lemma2_tight_small_rho a2_P_equiv_and_termination a3_prop_hypotheses a4_combiner_stress; do
  echo "== $s"; OMP_NUM_THREADS=1 $PY $s.py | tee out/$s.txt
done
for part in A A1 C E F H; do
  echo "== a5_guard_independent $part"; OMP_NUM_THREADS=1 $PY a5_guard_independent.py $part
done
for s in a6_t0_twin a7_g4_switch0; do
  echo "== $s"; OMP_NUM_THREADS=1 $PY $s.py
done
