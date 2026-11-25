#!/bin/bash
# Audit of C2 (design/theory/audit_c2.md): reproduces every file in audit/out/, plus out/por_default.{txt,json}
# (Table PoR at the default prices, Q25; script ../por_default.py).  About 1 h 20 min on 4 cores.
# Run from anywhere.  Each command runs in a memory-capped scope (3 GB, no swap) so an out-of-memory
# kill stops only that command; scripts use at most 4 worker processes; commands run one at a time.
# The scripts import ../model.py, ../det_game.py, ../families.py, ../alg_check.py and ../rand_lp.py.
set -e
cd "$(dirname "$0")"
PY="systemd-run --user --scope -q -p MemoryMax=3G -p MemorySwapMax=0 $HOME/venv/bin/python"
run() { local t0=$(date +%s); echo "== $*"; $PY "$@" > /dev/null; echo "   $(( $(date +%s) - t0 )) s"; }
# proof lens
run formula_check.py          # Thm 4 / Cor 5 / Cor 6 algebra on random (C) instances; Cor 5.3 proviso failures
run lb_rigorous.py            # interval-arithmetic F1/F2 lower bound: Table PoR cells and P7
run never_buy.py              # Thm 3 never-buy case; families.lb_react search window (pre- and post-audit)
run alg_star_exact.py         # Lemma 1(b) vs brute-force OPT; ALG* exact at H*; ALG* fails just below H*
run necessity_lb.py           # rigorous F1/F2/F3 lower bound below H* (necessity of Thm 4); Sec. 9 corners
run closed_form_mA.py         # two-family closed form with m_A = mu vs rigorous reactive bound
run xcheck_por_p7.py          # Table PoR and P7 with F1/F2/F3 (second interval implementation)
run alpha_and_tau_scope.py    # Thm 4 at alpha > 1/2; tau > 0 second-lease ('re-buy') schedules
run tau_f2_instance.py        # F2 for tau > H: literal text instance vs the instance families.py uses
run t4_exact.py               # exact game at kappa-binding, L3-binding, lam = s0, alpha = 0 cases
run t4_alpha_gt_half.py       # exact game for alpha in {0.6, 0.75}
# model / solver lens
run model_opt_bruteforce.py   # independent OPT; lam > R corner (pre-/post-fix); second revocable lease when tau > 0
run model_hstar_fine.py       # exact game at H* and just below, dt = 0.05 / 0.025; Sec. 9 corners
run model_grid_check.py       # grid error of the 26 non-tight scan rows; PoR cells at dt = 0.025; scan sample
run model_tau_semantics.py    # F2 text vs code; per-lease and notice-after-commitment semantics
run model_switch_cost.py      # H* when a pre-warm switch costs bw != beta
run model_switch_cost.py --extra   # bw = ap block (appends)
run model_switch_cost_default.py   # H* with switch cost bw at the default calibration (alpha = 0.40, alpha_p = 0.83; Q17, Q25)
run ../por_default.py         # Table PoR at the default prices, switch beta and bw; mu at which up-front insurance binds (Q25)
run switch_cost_crossover.py  # C2-SW formula only: simple-form, regime and cold/pre-warm breakpoints in mu (Q11, Q17)
run model_reversible_ins.py   # protected -> revocable switches allowed
run model_rand_fine.py        # randomized LP at dt = 0.05 beyond the deterministic H*
# re-check of the findings (reads out/model_switch_cost.txt, so it runs last)
run recheck_c2.py             # own implementation of every non-CORRECT finding; part J uses necessity_lb.py
