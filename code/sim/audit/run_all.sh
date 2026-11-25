#!/bin/bash
# Audit of the full-model guard (design/theory/audit_guard.md, section "Audit of the full-model guard"): the scripts
# X1-X8 of this folder and the identity check of the fixes F1 and F2 on the Q44 study, and the audit addendum of step
# P6 (design/sublet_v2.md §5; design/theory/audit_guard.md, "Audit addendum (P6)"): X9 (x9_prop_p.py, Lemma P.1 and
# Proposition P of the projected guard A8P with the trace of its code-level clause and the C2 negative control), X10
# (x10_g5p_pathwise.py, Lemma G5'(c) pathwise on fuzzed engine runs; needs the raw spot traces), X11
# (x11_g5p_oracle.py, LB'(t), W_k(t) and B(t) of online_lb.py, x10's lb_prime and the prototype against oracles
# written from C3 §9's definition, with the core form on from_core exports, monotonicity and non-anticipation), X12
# (x12_g5p_same_list.py, Lemma G5'(c) on engine runs with Load and Unload of objects created earlier in the same list,
# finding G5P-F7), X13 (x13_core_mode_s.py, Theorem G2 for A8 and A8P on from_core exports with S following R after
# the abort, C3 §9 "A8's mode S on core exports", finding REMARK_R-F1), X14 (x14_prop_p_lp_lb.py, an emulated inexact
# routing LP classified by x9's corrected clause, finding PROP_P-F1, and the float monotonicity of OnlineLB's B with
# the beta < 0 control, PROP_P-F2) and X15 (x15_mutations.py, mutations of ProjectedGuarded against
# tests/test_guard_projection.py, finding REMARK_R-F4); each invocation in its own systemd scope capped at 3G without
# swap, on one worker, one after the other. Outputs in code/sim/out/audit_fm/: x1_out.txt, x2_out.txt (blocks A, B,
# C), x2p_out.txt (F5 probe, block P), x2p_effect_out.txt, x3_out.txt, x4_out.txt, x7_out.txt, x7b_out.txt,
# x8_out.txt, identity.json (and its console, identity_out.txt), x9_out.txt, x10_out.txt, x11_out.txt, x12_out.txt,
# x13_out.txt, x14_out.txt, x15_out.txt; run_all.log records the code state (HEAD, guard.py's sha256, uncommitted
# changes under code/sim) and each step with its wall time, peak memory and exit status. A step exits with status 1
# when its script finds a violation of a checked claim (X1, X2, X3, X4, X7, X7b: a violation count above 0 or a worst
# relative excess above the tolerance; X8: the reserve exceeded or not attained; identity.py: a rerun that differs, or
# a Load or an observation write found by the probe; X9: a failed check, a C2 control that does not produce its abort,
# or an abort classified 'refutation' or 'undecided'; X10: a violation, a failed proof step or engine invariant, or a
# run that raises; X11: a value of online_lb.py, x10's lb_prime or the prototype under (i)-(iii) more than 1e-12
# relative from the oracle, or a failed property (W_k against its formula, B not min{W_k, LB'} bit for bit, a
# decrease, anticipation, the prototype below LB' outside (i)-(iii), the core form, conditions (i)-(iii) against
# online_lb.conditions, the float oracle against the exact one), or an instance that raises; X12: a violation of
# ALG(t) >= LB'(t), an engine invariant failure or a run that raises; X13: a violation of G2(a), G2(b), the mode-S
# step (up to WD_TIE sum max(1, Q(u)) over the adaptive slots and the float tolerance) or soundness, an engine
# invariant failure or a run that raises; X14: x9's clause outputs 'refutation' or 'undecided' on an LP-caused abort,
# an unemulated instance aborts, a power check or monotonicity on the instance class fails, or a negative control does
# not fail; X15: the unmutated copy fails a run, a run ends with an error, or a mutation survives the whole test file
# or both test_remark_r_identity and test_remark_r_coverage, and status 2 if a mutation's code fragment no longer
# occurs exactly once in guard.py) and with a nonzero status when it crashes; "failures" in the log's last line is 1
# if any step did. x2p_effect.py only measures. X15 works in a temporary copy of code/sim and starts each of its
# pytest runs in its own 3G scope. About 45 min for X1-X8 and the identity check, about 20 min for X9 and X10, about
# 10 min for X11-X13, about 3 min for X14 and 15-25 min for X15.
# Usage: run_all.sh [step ...]   steps: x1 x3 x8 x7 x2 x2p x2p_effect x4 x7b identity x9 x10 x11 x12 x13 x14 x15
# (default: all, in this order)
set -u
cd "$(dirname "$0")"
PY=${PY:-$HOME/venv/bin/python}
OUT=../out/audit_fm
mkdir -p "$OUT"
LOG=$OUT/run_all.log
fail=0

step() {   # step <output file> [VAR=value ...] <script> [args...]: stdout appended to <output file>
  local out=$1; shift
  local envs=()
  while [[ $# -gt 0 && $1 == *=* ]]; do envs+=("$1"); shift; done
  echo "== $(date -Is) ${envs[*]} $* >> $out" >> "$LOG"
  systemd-run --user --scope -q -p MemoryMax=3G -p MemorySwapMax=0 \
    /usr/bin/time -a -o "$LOG" -f "   peak RSS %M KB, %e s, exit %x" \
    env OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 "${envs[@]}" "$PY" "$@" >> "$OUT/$out" 2>> "$LOG" || fail=1
}

run() {
  case $1 in
    x1) : > "$OUT/x1_out.txt"; step x1_out.txt x1_load_same_list.py ;;
    x3) : > "$OUT/x3_out.txt"; step x3_out.txt x3_obs_mutation.py ;;
    x8) : > "$OUT/x8_out.txt"; step x8_out.txt x8_reserve_tight.py ;;
    x7) : > "$OUT/x7_out.txt"; step x7_out.txt x7_reclaim_ms.py ;;
    x2) : > "$OUT/x2_out.txt"; for b in A B C; do step x2_out.txt x2_random_search.py "$b" 4; done ;;
    x2p) : > "$OUT/x2p_out.txt"; step x2p_out.txt AUDIT_WC=1 x2_random_search.py P 4 ;;
    x2p_effect) : > "$OUT/x2p_effect_out.txt"; step x2p_effect_out.txt x2p_effect.py ;;
    x4) : > "$OUT/x4_out.txt"; step x4_out.txt x4_natural_aborts.py 2 ;;
    x7b) : > "$OUT/x7b_out.txt"; step x7b_out.txt x7b_reclaim_day.py ;;
    identity) : > "$OUT/identity_out.txt"; step identity_out.txt identity.py 2 ;;
    x9) : > "$OUT/x9_out.txt"; step x9_out.txt x9_prop_p.py ;;
    x10) : > "$OUT/x10_out.txt"; step x10_out.txt x10_g5p_pathwise.py ;;
    x11) : > "$OUT/x11_out.txt"; step x11_out.txt x11_g5p_oracle.py ;;
    x12) : > "$OUT/x12_out.txt"; step x12_out.txt x12_g5p_same_list.py ;;
    x13) : > "$OUT/x13_out.txt"; step x13_out.txt x13_core_mode_s.py ;;
    x14) : > "$OUT/x14_out.txt"; step x14_out.txt x14_prop_p_lp_lb.py ;;
    x15) : > "$OUT/x15_out.txt"; step x15_out.txt x15_mutations.py ;;
    *) echo "unknown step $1" >&2; fail=1 ;;
  esac
}

steps=("$@")
[[ ${#steps[@]} -eq 0 ]] && steps=(x1 x3 x8 x7 x2 x2p x2p_effect x4 x7b identity x9 x10 x11 x12 x13 x14 x15)
{
  echo "# $(date -Is) run_all.sh ${steps[*]} HEAD=$(git -C ../../.. rev-parse --short HEAD)"
  echo "# guard.py sha256 $(sha256sum ../sublet/algos/guard.py | cut -d' ' -f1)"
  git -C ../../.. status --short -- code/sim/sublet code/sim/tests code/sim/audit | sed 's/^/# git status: /'
} >> "$LOG"
for s in "${steps[@]}"; do run "$s"; done
echo "# $(date -Is) done, failures: $fail" >> "$LOG"
exit $fail
