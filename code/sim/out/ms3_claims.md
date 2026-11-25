# MS3 claims report (design/sim_spec_ms3.md §1.4)

Written 2026-11-25T06:40:55 by `sublet.experiments.ms3_claims` at revision 992823b93d06ab079b469b16d32b1b9309e79b35; inputs under the repository.

**Criterion of §1.4 item 2: holds.** No row is a bug, and every row is reproduced, holds, informative or explained (0 explained).

Rows: 37; reproduced 6, holds 22, informative 9, explained 0, bug 0, missing 0, pending 0.

Figures (§1.4 item 1): 20 of 20 redrawn from their extracts with finalize() passing, 0 extract(s) missing, 0 error(s); 0 figure(s) with mathtext glyphs below 4.9 pt, i.e. below a first-level script of 7-pt text (listed below; plan §5 allows first-level scripts).

Floats (§1.4 item 5): Table I 0.1374 page (budget 0.09); Table II 0.3712 page (budget 0.22); Algorithm 1 0.1718 page (budget 0.129) (3 of 3 floats exceed their budget (Table I, Table II, Algorithm 1); recorded, no float trimmed (decision of 2026-10-20, §9)).

Copy checks: e11 pass; e1 pass; e10 pass; e2 pass; e6 pass.

Jobs (§2.4): e1 570 listed, ok 572; e10 183 listed, ok 185; e2 1531 listed, ok 1533; e6/a 877 listed, ok 879; e6/b 28 listed, ok 30 (every listed job has an 'ok' record, or is a MILP job whose LB is the LP under Q39's rule).

## E11 (§3.3)

| Check | Claim | Status label | Reference (file) | Regenerated (file) | Verdict |
|---|---|---|---|---|---|
| E11-0 | the copy of §3.2 step 1: manifest.json meta.git_revision is E11's commit; every run file that records a git revision records it; the file list and the sha256 of every file equal the clone's | none: the provenance of the copy (no claim of the design) | the clone's files and their sha256; revision 29919ea0a0cb0be883ceb60b86c1f1ddd1dcfa3c (§3.1); `/work/e11c/code/sim/out/e11` | pass true; n_files_copy 23403; n_files_clone 23403; n_sha256_mismatch 0; n_only_in_copy 0; n_only_in_clone 0; manifest_git_revision 29919ea0a0cb0be883ceb60b86c1f1ddd1dcfa3c; n_run_revision_differs 0; n_runs_no_revision_other 0; n_runs_unreadable 0; `code/sim/out/ms3_e11_0.json` | **holds** |
| E11-1 | e11/summary.json checks.V1-V7 each pass; V3 is computed from T2_ad (it was 'not run' in the first study, q44_study/summary.json checks.V3.why) | none: the Q44 study's checks V1-V7 (design/q44_practical_sublet.md §8.2) | each pass (V1 against the values of its reference_file, V5 against c4_lower.json) (V1_reference_file code/sim/out/ms2_checks/pd_cost_diag.json; V5_reference_file code/theory_checks/c3/out/c4_lower.json); `code/sim/out/e11/summary.json (checks.V1.reference_file, checks.V5.reference_file)` | V1 pass; V2 pass; V3 pass; V4 pass; V5 pass; V6 pass; V7 pass; V3_pairs 504; `code/sim/out/e11/summary.json checks.V1-V7` | **holds** |
| E11-2 | certificate_full_model.all_held and the certificate of every core-export run (D5.certificate) true; a run in Theorem W's proven cases whose ALG(T) exceeds its bound plus the tolerance is a bug | Theorem W(a)(b) (PROVEN for the engine as implemented under C1-C3, audited); W(c) (CONJECTURE) | every certificate held (all_held true, no failure listed); `code/sim/sublet/algos/guard.py (Theorem W, module docstring); design/Sublet_design.md §2.9` | full_model_all_held true; full_model_held 4020; full_model_runs 4020; full_model_failures 0; core_all_held true; core_held 2120; core_runs 2120; core_failures 0; `code/sim/out/e11/summary.json certificate_full_model, D5.certificate` | **holds** |
| E11-3 | identity of the Fig. 1(b) run (§8.1's rule) with the first study's file of the same path (t_a, ALG_T, the guard record), and whether the rule picks the same path in both (informative, M42) | none: the identity of one run between the two studies (M42) | the first study's run file of the same path (t_a 107; ALG_T 732.695); `code/sim/out/q44_study/runs/Q1/I2/1min/L-eg/BL5-G_c2_l2_p0.json` | run_file code/sim/out/e11/runs/Q1/I2/1min/L-eg/BL5-G_c2_l2_p0.json; same_as_first_study true; t_a 107; ALG_T 732.695; identical true; `code/sim/out/figs/fig1.json data` | **informative** |
| E11-4 | Fig. 3's numbers versus the first study's: fig3.json carries E11's values; the first study's come from fig3_e11.collect_a and collect_b on q44_study/summary.json and (c)'s series from its D5; (c)'s G3(b) line is not compared (informative; changes under L-co are expected from S11) | none: measurements (Fig. 3's values), no pass condition | the first study's Fig. 3 values (collect_a, collect_b, D5); `code/sim/out/q44_study/summary.json` | n_compared 383; n_differ 14; n_differ_a 1; n_differ_b 13; n_differ_c 0; max_abs_diff_a 0.0224874; max_abs_diff_b 0.3; max_abs_diff_c 0; largest_a a6 W0 at I1; largest_b a6 x at L-co; largest_c all equal; n_without_counterpart 0; e11_revision 29919ea0a0cb0be883ceb60b86c1f1ddd1dcfa3c; `code/sim/out/figs/fig3.json data.a, data.b, data.c` | **informative** |

- E11-3: the rule picks the same path in both studies and the run is identical (t_a, ALG_T and every guard series)
- E11-4: 14 of 383 compared values differ: (a) 1 of 98 (W0); (b) 13 of 217 (ci_hi, ci_lo, intensity, x); (c) 0 of 68; the figure and the text use E11's values (changes under L-co are expected from S11, §3.3)

## E1 (§4.6)

| Check | Claim | Status label | Reference (file) | Regenerated (file) | Verdict |
|---|---|---|---|---|---|
| E1-1 | Fig. 2(b)'s rho at maas_p99_median equals a11's rows.*.rho (computed by the Fig. 2 script into figs/fig2.json data.b.E1_1; e1/summary.json gives it the status 'elsewhere'); 1e-12 relative | none: the calibration formula of a11 (field_sources.rho) | rows.maas_a10.<t>.<s>.by_contract.<k>.rho; `code/analysis/out/a11_calibration.json` | n 480; max_rel_err 0; tol 1e-12; price_ref maas_p99_median; `code/sim/out/figs/fig2.json data.b.E1_1` | **reproduced** |
| E1-2 | instance_rho after beta_for_rho equals rho* for both LLMs, every config seed (1e-9) | none: the construction of the per-LLM fee (C12) | rho* in {1.5, 2, 4, 8, 16} (the target); `code/sim/out/e1/summary.json meta.fees` | n_cells 72; max_abs_diff 1.77636e-15; len(failures) 0; `code/sim/out/e1/summary.json checks.E1-2` | **holds** |
| E1-3 | tight family at T = 60 equals c3/out/c3_benchmark.json a[*] (OPT_eager, OPT_none, OPTeager_over_OPTnone); at every T the MILP values equal the closed forms (1e-9, status 0, gap 0) | C3-L2 (PROVEN, pathwise, tight for every rho); core.opt_omega and core.opt_eager (Proposition M1, Corollary M2, PROVEN) | c3_benchmark.json a[*] at T = 60; the closed forms of §4.4; `code/theory_checks/c3/out/c3_benchmark.json` | n_rows 20; n_T60_compared 5; max_abs_diff_T60_vs_reference 0; max_rel_diff_closed_form 0; len(not_optimal_or_gap) 0; len(above_max2rho) 0; `code/sim/out/e1/tight_family.json check_E1_3` | **reproduced** |
| E1-4 | on every instance with an exact core export, OPT_eager / OPT(sigma, omega) <= max(2, rho) (C3-L2); the tight family and c3_benchmark.json b (re-solved, reproduced to 1e-9, at most 1.513) are exact; on the trace instances the bracket is a diagnostic | C3-L2 (PROVEN, pathwise, tight for every rho) | max(2, rho); c3_benchmark.json b[*].per_rate[*].eager_over_omega; `code/theory_checks/c3/out/c3_benchmark.json` | core_b_n 50; core_b_max_eager_over_omega 1.51342; core_b_max_abs_diff 0; core_b_reproduced true; core_b_all_within_bound true; len(tight_family_above_max2rho) 0; trace_exports.n_exact 0; trace_brackets_diagnostic.n_lo_above_max2rho 0; `code/sim/out/e1/core_b.json, tight_family.json; code/sim/out/e1/summary.json checks.E1-4` | **holds** |
| E1-5 | every Sublet run's certificate held in Theorem W's proven cases; W(c) runs reported | Theorem W(a)(b) (PROVEN for the engine as implemented under C1-C3, audited); W(c) (CONJECTURE) | ALG(T) within Theorem W's bound in every proven case; `code/sim/sublet/algos/guard.py` | runs 216; n_failures 0; n_w_c 0; by_case {W(a): {runs: 180, held: 180}, W(b): {runs: 36, held: 36}, W(c): {runs: 0, held: 0}, unavailable: {runs: 0, held: 0}}; `code/sim/out/e1/summary.json checks.E1-5` | **holds** |
| E1-6 | every E1(b) run: invariant_failures empty, gpu_only_lease_slots 0, ratio_validity None; plan class P1 runs have ratio_LB >= 1 - 1e-6 (LB <= OPT_P1 <= ALG) | Proposition M4 (PROVEN) | no failure; ratio_LB >= 1 - 1e-6 for P1 runs; `design/Sublet_design.md §5.2.4 (Proposition M4)` | n_runs 924; len(invariant_failures) 0; len(gpu_only_lease_slots) 0; len(ratio_validity_not_none) 0; n_p1 924; len(p1_below) 0; min_ratio_LB_p1 1; `code/sim/out/e1/summary.json checks.E1-6` | **holds** |
| E1-7 | A3 in reference mode with rbar = 1 and with the theory rbar reproduces c3/out/c4_lower.json a (pd_r1, pd_r1_min, pd_rth, pd_rth_min) through E10-1 | C3-T4 (PROVEN) | c4_lower.json a (pd_r1, pd_r1_min, pd_rth, pd_rth_min); `code/theory_checks/c3/out/c4_lower.json` | n_points 16; max_abs_diff_pd_columns 0; `code/sim/out/e10/repro.json (E10-1); code/sim/out/e1/summary.json checks.E1-7` | **reproduced** |
| E1-8 | ratios above max(2, rho) on trace instances are not bugs (plan §7); counted and reported | C3-Cor3 (PROVEN); trace instances leave the ORML core, so their ratios are diagnostics | max(2, rho*); `code/sim/out/e1/summary.json ratios.*.max2rho` | n_runs_above 261; len(by_point) 29; `code/sim/out/e1/summary.json checks.E1-8` | **informative** |

- E1-1: the summary's claim: Fig. 2(b)'s rho equals a11's rows.*.rho
- E1-3: the summary's claim: C3-L1(c) tight family: T = 60 equals c3_benchmark.json a; MILP values equal the closed forms (1e-9, status 0, gap 0)
- E1-4: the summary's claim: C3-L2 (PROVEN): OPT_eager / OPT(sigma, omega) <= max(2, rho) on exact core exports
- E1-5: the summary's claim: Theorem W: every Sublet certificate held in the proven cases; W(c) runs reported
- E1-6: the summary's claim: every run: no invariant failure, no GPU-only lease slot, ratio_validity None; P1 runs ratio_LB >= 1 - 1e-6 (Proposition M4)
- E1-7: the summary's claim: A3 reference mode with rbar = 1 and theory reproduces c4_lower.json a
- E1-8: the summary's claim: ratios ALG/LB above max(2, rho*) on trace instances are not bugs (plan §7)

## E10 (§5.5)

| Check | Claim | Status label | Reference (file) | Regenerated (file) | Verdict |
|---|---|---|---|---|---|
| E10-1 | at T = 48, m in {2, 3, 4, 6}, rho in {2, 4, 8, 16}, RR-renew, stay and A3's reference mode (rbar = 1 and theory), seeds 0-3, under 'adaptive', reproduce c4_lower.json a (rr, stay, pd_r1, pd_r1_min, pd_rth, pd_rth_min, LB_T); exact to 1e-9 | C3-T4 (PROVEN) | c4_lower.json a (rr, stay, pd_r1, pd_r1_min, pd_rth, pd_rth_min, LB_T); `code/theory_checks/c3/out/c4_lower.json` | n_points 16; max_abs_diff 0; len(failures) 0; `code/sim/out/e10/repro.json; code/sim/out/e10/summary.json checks.E10-1` | **reproduced** |
| E10-2 | C3-T4: every run under 'adaptive' has ALG/OPT >= LB_T - 1e-9 | C3-T4 (PROVEN, pathwise for deterministic algorithms against the adaptive-offline lender) | LB_T = (A0 beta + a T) / ((A0/m + 1) beta + a (T + D)); `code/sim/out/e10/summary.json bounds` | n_runs 1638; min_ratio_over_LB_T 1.00373; len(failures) 0; `code/sim/out/e10/summary.json checks.E10-2` | **holds** |
| E10-3 | O1-B: every RR-renew run, under every lender, has ALG <= min{rho (1 + D/T) OPT, 2 m OPT + a D} (1 + 1e-9) | O1-B (PROVEN, any lender) | min{rho (1 + D/T) OPT, 2 m OPT + a D}; `code/sim/out/e10/summary.json checks.E10-3 (per run)` | n_runs 1098; max_alg_over_bound 0.954292; len(failures) 0; `code/sim/out/e10/summary.json checks.E10-3` | **holds** |
| E10-4 | under safe_site, OPT = Phi beta + a T on every schedule (1e-9) | O1-A (PROVEN for m >= 3 under one-notice I1 and the assumptions of design §1.8.3); the check tests its Claim 1 (design/theory/o1_oblivious_lender.md) | Phi beta + a T; `code/sim/out/e10/summary.json a.safe_site.*` | n_runs 1620; max_rel_diff 0; `code/sim/out/e10/summary.json checks.E10-4` | **holds** |
| E10-5 | O1-A: at m >= 3 the upper end of the 95% interval of E[ALG]/OPT under safe_site at k* is at least LB_A(k*) - 1e-9; a point below is rerun with seeds 30-129 (pending until then), still below is a bug | O1-A (PROVEN for m >= 3 under one-notice I1 and the assumptions of design §1.8.3) | LB_A(k*); `code/sim/out/e10/summary.json bounds.<rho>.<m>.LB_A; code/theory_checks/c3/o1/out/o1_lb.json A` | n_points 15; len(flagged) 0; len(still_flagged_after_rerun) 0; len(rerun_pending) 0; `code/sim/out/e10/summary.json checks.E10-5` | **holds** |
| E10-6 | O1-D: the lower end of the 95% interval of marking's ratio is at most 2 h_m + 1 (reruns as E10-5) | O1-D (PROVEN) | 2 h_m + 1; `code/sim/out/e10/summary.json bounds.<rho>.<m>.two_h_m_plus_1` | n_points 36; len(flagged) 0; len(still_flagged_after_rerun) 0; len(rerun_pending) 0; `code/sim/out/e10/summary.json checks.E10-6` | **holds** |
| E10-7 | O1-C: marking's ratio under iid_step at p* against max_p LB_C (a limit; finite runs may lie below) | O1-C (PROVEN with tau >= 1); a T -> infinity limit that bounds no finite run | max_p LB_C; `code/sim/out/e10/summary.json bounds.<rho>.<m>.LB_C_max` | len(points) 18; min(points[*].ratio_minus_LB_C) -0.0253572; max(points[*].ratio_minus_LB_C) 0.0302585; `code/sim/out/e10/summary.json checks.E10-7` | **informative** |
| E10-8 | C-O1a: RR-renew's ratio under 'adaptive' against rho m / (m + rho - 1) | C-O1a (VERIFIED NUMERICALLY / CONJECTURE) | rho m / (m + rho - 1); `code/sim/out/e10/summary.json bounds.<rho>.<m>.limit` | len(points) 18; min(points[*].ratio_over_limit) 1; max(points[*].ratio_over_limit) 1; `code/sim/out/e10/summary.json checks.E10-8` | **informative** |
| E10-9 | o1_lb.lb_A, lb_C through import_ref reproduce o1_lb.json A at every listed (rho, m), and summary.json bounds equals them there (exact) | O1-A (PROVEN for m >= 3 under one-notice I1 and the assumptions of design §1.8.3); O1-C (PROVEN with tau >= 1): the values of LB_A and LB_C | o1_lb.json A (k, LB_A, p, LB_C); `code/theory_checks/c3/o1/out/o1_lb.json` | n_listed 56; recompute_pass true; len(bounds_mismatch) 0; `code/sim/out/e10/repro.json o1_lb; code/sim/out/e10/summary.json bounds` | **reproduced** |
| E10-10 | E10(b): ratios growing faster than min(rho, m) in m at fixed rho (informative evidence against C-O1b; the entry lists stale_milp_records) | C-O1b (CONJECTURE) | min(rho, m) and min(rho, 1 + log2 m), orders up to polylog factors; `code/sim/out/e10/summary.json checks.E10-10.series` | n_runs 320; n_empty_instances 64; len(series) 8; len(stale_milp_records) 0; `code/sim/out/e10/summary.json checks.E10-10` | **informative** |

- E10-1: the summary's claim: R2 reproduction of c4_lower.json a (rr, stay, pd_r1, pd_r1_min, pd_rth, pd_rth_min, LB_T) to 1e-9
- E10-2: the summary's claim: C3-T4 (PROVEN): every adaptive run has ALG/OPT >= LB_T - 1e-9
- E10-3: the summary's claim: O1-B (PROVEN): RR-renew ALG <= min{rho (1 + D/T) OPT, 2 m OPT + a D} (1 + 1e-9)
- E10-4: the summary's claim: under safe_site OPT = Phi beta + a T on every schedule (1e-9)
- E10-5: the summary's claim: O1-A (PROVEN, m >= 3): upper end of the 95% interval of E[ALG]/OPT under safe_site at k* >= LB_A(k*) - 1e-9 (private tags)
- E10-6: the summary's claim: O1-D (PROVEN): lower end of the 95% interval of marking's ratio <= 2 h_m + 1
- E10-7: the summary's claim: O1-C (PROVEN with tau >= 1; a T -> infinity limit that bounds no finite run): marking's ratio under iid_step at p* against max_p LB_C
- E10-8: the summary's claim: C-O1a (VERIFIED NUMERICALLY / CONJECTURE): RR-renew's adaptive ratio against rho m / (m + rho - 1)
- E10-9: the summary's claim: o1_lb.lb_A, lb_C through import_ref reproduce o1_lb.json A at every listed (rho, m); bounds equal them there
- E10-10: the summary's claim: C-O1b (CONJECTURE): E10(b) ratios against min(rho, m) in m

## E2 (§6.9)

| Check | Claim | Status label | Reference (file) | Regenerated (file) | Verdict |
|---|---|---|---|---|---|
| E2-1 | the finer-grid game reproduces por_default.json table_por_switch_beta at mu = 1, lambda = inputs.lambda_default, Hs = H_BASE (the same floats); exact to 1e-12 | C2-P8 (lower bound PROVEN, table values interval-certified, equality VERIFIED NUMERICALLY at alpha = 0.3, CONJECTURE in general) | table_por_switch_beta CR at Hs in H_BASE (rows[*].CR_ref [1.77077, 1.72454, 1.67357, 1.6228, 1.6014, 1.6014, 1.6014, 1.6014]); `code/theory_checks/c2/out/por_default.json` | max_abs_diff 0; tolerance 1e-12; len(missing_Hs) 0; rows[*].CR [1.77077, 1.72454, 1.67357, 1.6228, 1.6014, 1.6014, 1.6014, 1.6014]; `code/sim/out/e2/game.json; code/sim/out/e2/summary.json checks.E2-1` | **reproduced** |
| E2-2 | (a) the cell kinds, A1's insurance decision and its reaction per mu, recomputed by c2rule at each e2_reactions.json row's units, equal the row's (exact); (b) A1's units of the run against the row's (informative, differences listed) | every per-lender H*_mu at a lender's IR price is the C2-SW formula, CONJECTURE (code/sim/out/ms2_checks/e2_reactions.json, field status) | e2_reactions.json rows (kind, insure_up_front, reaction, units); `code/sim/out/ms2_checks/e2_reactions.json` | a.n_rows 860; len(a.mismatches) 0; len(a.alpha_kind_mismatches) 0; b.n_cells 1505; b.n_differences 0; `code/sim/out/e2/summary.json checks.E2-2` | **holds** |
| E2-3 | Q42 (a): at mu = 1 on every cell, A1 and 'always cold' give identical ledgers where A1 does not insure; all three rules identical where it insures (1e-9 USD) | none: the coincidence of the rules (Q42 (a)), a property of the build | A1's ledgers (1e-9 USD); `code/sim/out/e2/summary.json checks.E2-3` | n_cells 860; n_compared 932598; max_abs_diff_a1_cold 0; max_abs_diff_insured 0; len(violations) 0; `code/sim/out/e2/summary.json checks.E2-3` | **holds** |
| E2-3b | band-less layers: every band-less DP value at most the layer's fallback cost (1e-9 USD) | none: the band-less layers (M48) | the layer's fallback cost; `code/sim/out/e2/summary.json bandless` | n_bandless 1645; max_dp_minus_fallback 0; n_dp_missing 0; len(violations) 0; `code/sim/out/e2/summary.json checks.E2-3b` | **holds** |
| E2-4 | every run: invariant_failures empty, gpu_only_lease_slots 0; every DP within its domain (status optimal) | none: the engine's invariants and the DP's domain | no failure; `code/sim/out/e2/summary.json checks.E2-4` | n_runs 5593782; n_invariant_failures 0; n_gpu_only_lease_slots 0; n_dp 1628713; n_dp_not_optimal 0; n_dp_domain_error 0; `code/sim/out/e2/summary.json checks.E2-4` | **holds** |
| E2-5 | per-episode ratio at least 1 - 1e-9 (the DP is OPT on the episode's domain); below it a bug unless opt.milp.solve_opt on that episode returns an incumbent below the DP value (a confirmed counterexample to Claim D2: explained); pending while such an episode's MILP job has not run; ALG below the MILP's lower bound is a bug in any case | Claim D2 (CONJECTURE) | 1 - 1e-9; `code/sim/out/e2/summary.json checks.E2-5` | n_episodes 1534113; min_ratio 1; n_below 0; n_candidates 0; len(unresolved) 0; len(ep_milp_stale) 0; len(milp) 0; `code/sim/out/e2/summary.json checks.E2-5` | **holds** |
| E2-6 | the sum of the layers' DPs against the joint MILP's lower bound on 1-day instances | none: open (MS1 spec §7.6): whether the sum of the layers' DPs equals the joint optimum | LB_joint = max(LP, dual bound); `code/sim/out/e2/joint_milp.json` | len(rows) 8; min(rows[*].ratio_sum_dp_over_LB) 1.00119; max(rows[*].ratio_sum_dp_over_LB) 1.03048; `code/sim/out/e2/summary.json checks.E2-6` | **informative** |
| E2-7 | a ratio above 2 - alpha at H >= H*_mu is not a bug on trace episodes (the bug test on C2-core instances is the harness's, MS2 spec §16) | C2-T4 (PROVEN under (C'), tau = 0); every per-lender H*_mu at a lender's IR price is the C2-SW formula, CONJECTURE (code/sim/out/ms2_checks/e2_reactions.json, field status) | 2 - alpha_k at H >= H*_mu of the cell's e2_reactions.json row; `code/sim/out/ms2_checks/e2_reactions.json` | by_group.maas {n_at_or_above_hstar: 1147300, n_above_2_minus_alpha: 342640}; by_group.spot {n_at_or_above_hstar: 46279, n_above_2_minus_alpha: 4378}; `code/sim/out/e2/summary.json checks.E2-7` | **informative** |

- E2-1: the summary's claim: the exact C2 game on the finer H grid (det_game.solve_det, switch cost beta~) reproduces por_default.json table_por_switch_beta at mu = 1, lambda = inputs.lambda_default, Hs in H_BASE (exact to 1e-12)
- E2-2: the summary's claim: (a) the cell kinds, A1's insurance decision and its reaction per mu, recomputed by c2rule at each e2_reactions.json row's units, equal the row's (exact); (b) A1's units of the run against the row's (informative)
- E2-3: the summary's claim: Q42 (a) at mu = 1 on every cell: A1 and 'always cold' give identical ledgers where A1 does not insure, all three rules where it insures (1e-9 USD)
- E2-3b: the summary's claim: band-less layers (M48): every band-less DP value at most the layer's fallback cost (1e-9 USD)
- E2-5: the summary's claim: per-episode ratio at least 1 - 1e-9 (the DP is OPT on the episode's domain, Claim D2 CONJECTURE); below it a bug unless opt.milp.solve_opt returns an incumbent below the DP value (a counterexample to Claim D2: explained)
- E2-6: the summary's claim: the sum of the layers' DPs against the joint MILP's lower bound on 1-day instances (M46; whether the sum equals the joint optimum is open, MS1 spec §7.6; informative)
- E2-7: the summary's claim: per-episode ratios above 2 - alpha at H >= H*_mu are not bugs on trace episodes (C2-T4 PROVEN under (C'), tau = 0; the per-lender H*_mu is the C2-SW formula, CONJECTURE; informative)

## E6 (§7.3)

| Check | Claim | Status label | Reference (file) | Regenerated (file) | Verdict |
|---|---|---|---|---|---|
| E6-1 | C2-T2 in the harness and A1's insurance rule: (a) the harness's INS worst ratio within [CR_ins (1 - 1e-3), CR_ins + 1e-9], (b) insure_up_front equals the direct formula and A1 reports it (exact) | C2-T2 (PROVEN for insurance held to the end of the demand) | CR_ins = max(2 - alpha, alpha_p / alpha); the direct formula with families.lb_react; `code/theory_checks/c2/out/por_default.json (inputs)` | a.n 64; a.n_fail 0; b.n 512; b.n_fail 0; b.a1.n 128; b.a1.n_fail 0; `code/sim/out/e6/a/runs/c2t2.json (job e6:a_c2t2); code/sim/out/e6/a/summary.json checks.E6-1` | **holds** |
| E6-2 | linearity in a_p and in mu: INS and WARM reruns at r = 3, mu = 1 and WARM at r = 1.1, mu = 2 give A + a_p G + mu_fb W with the reference run's plan; A1's C2 units at c in {2, 3, 4} equal those at c = 1 (1e-9 relative) | none: the linearity of E6(a)'s evaluation (M28) | A + a_p(r) G + mu_fb(mu) W of the reference run; `code/sim/out/e6/a/summary.json checks.E6-2` | n 510; n_fail 0; units_across_alignments.n 100380; units_across_alignments.n_fail 0; `code/sim/out/e6/a/summary.json checks.E6-2` | **holds** |
| E6-3 | BL7 equals E2's cold, non-insured run of the same key (alignment 1, mu = 1, every 10th MaaS key; identical totals to 1e-9 USD) | none: the identity of BL7 with E2's cold runs | E2's cold, non-insured run of the same key; `code/sim/out/e2/runs/cells/ (E2's run files)` | n 800; n_fail 0; n_without_e2_cold 0; `code/sim/out/e6/a/summary.json checks.E6-3` | **holds** |
| E6-4 | where A1 neither insures nor pre-warms, the cell value is exactly 1 | none: a property of the heatmap value (M29) | 1; `code/sim/out/e6/a/heatmap.json` | n_pairs 39735; max_abs_dev 0; `code/sim/out/e6/a/summary.json checks.E6-4` | **holds** |
| E6-5 | the cells where insuring pays on the traces (react_over_ins above 1) and the boundary's insuring region r < r*(H) differ, listed with their inputs (the experiment's question) | C2-T3 (PROVEN for tau = 0): LB_react(H) <= CR_react(H), the boundary's certified bound | r*(H) of the certified bound; `code/sim/out/e6/a/boundary.json` | n_cells 1008; n_disagree 275; `code/sim/out/e6/a/summary.json checks.E6-5` | **informative** |
| E6-6 | E6(b) runs: no invariant failure, no GPU-only lease slot | none: the engine's invariants | no failure; `code/sim/out/e6/b/summary.json checks.E6-6` | n_runs 84; n_invariant_failures 0; n_gpu_only_lease_slots 0; `code/sim/out/e6/b/summary.json checks.E6-6` | **holds** |

- E6-1: the summary's claim: C2-T2 (PROVEN for insurance held to the end of the demand): (a) the harness's INS worst ratio lies in [CR_ins (1 - 1e-3), CR_ins + 1e-9], CR_ins = max(2 - alpha, alpha_p / alpha); (b) c2rule.insure_up_front(units, 'lb_react') equals the direct formula with families.lb_react, and A1 built at the row's protected price reports the same `insured` (exact)
- E6-2: the summary's claim: linearity in a_p and in mu (M28): INS and WARM rerun at r = 3, mu / beta~ = 1 and WARM at r = 1.1, mu / beta~ = 2 give A + a_p G + mu_fb W with the reference run's plan; A1's C2 units at c in {2, 3, 4} equal those at c = 1 (1e-9 relative)
- E6-3: the summary's claim: BL7 equals E2's cold, non-insured run of the same key (alignment 1, mu = 1, every 10th MaaS key; 1e-9 USD)
- E6-5: the summary's claim: the cells where insuring pays on the traces (react_over_ins above 1) and the boundary r < r*(H) (certified LB_react, C2-T3 PROVEN for tau = 0) disagree (informative)

## Floats (§1.4 item 5)

| Float | Measured (page) | Budget (page) | Within budget | Difference (page) | Source |
|---|---|---|---|---|---|
| Table I | 0.1374 | 0.09 | false | 0.0474 | `paper/floats/table1_price_of_revocation.tex` |
| Table II | 0.3712 | 0.22 | false | 0.1512 | `paper/floats/table2_policies.tex` |
| Algorithm 1 | 0.1718 | 0.129 | false | 0.0428 | `paper/floats/alg1_guard.tex` |

From `code/sim/out/figs/floats_heights.json`; 3 of 3 floats exceed their budget (Table I, Table II, Algorithm 1); recorded, no float trimmed (decision of 2026-10-20, §9).

## Figures: small glyphs (§1.4 item 1)

| Figure | Script | Status | Small glyphs | Glyphs below 4.9 pt (size, text) |
|---|---|---|---|---|
| fig1 | `figs/fig1_guard.py` | ok | 0 | none |
| fig2 | `figs/fig2_e1a.py` | ok | 0 | none |
| fig3 | `figs/fig3_e11.py` | ok | 0 | none |
| fig5 | `figs/fig5_e1_e10.py` | ok | 0 | none |
| fig6 | `figs/fig6_e10.py` | ok | 0 | none |
| fig7 | `figs/fig7_e2_e6.py` | ok | 0 | none |
| sf_e10_cross | `figs/supp/sf_e10_cross.py` | ok | 0 | none |
| sf_e10_rho | `figs/supp/sf_e10_rho.py` | ok | 0 | none |
| sf_e10b | `figs/supp/sf_e10b.py` | ok | 0 | none |
| sf_e11_fam | `figs/supp/sf_e11_fam.py` | ok | 0 | none |
| sf_e11_guard | `figs/supp/sf_e11_guard.py` | ok | 0 | none |
| sf_e11_inst | `figs/supp/sf_e11_inst.py` | ok | 0 | none |
| sf_e1_rotation | `figs/supp/sf_e1_rotation.py` | ok | 0 | none |
| sf_e1_sched | `figs/supp/sf_e1_sched.py` | ok | 0 | none |
| sf_e2_mu_cost | `figs/supp/sf_e2_mu_cost.py` | ok | 0 | none |
| sf_e2_mu_ep | `figs/supp/sf_e2_mu_ep.py` | ok | 0 | none |
| sf_e2_pool | `figs/supp/sf_e2_pool.py` | ok | 0 | none |
| sf_e2_por | `figs/supp/sf_e2_por.py` | ok | 0 | none |
| sf_e6a | `figs/supp/sf_e6a.py` | ok | 0 | none |
| sf_e6b | `figs/supp/sf_e6b.py` | ok | 0 | none |

20 figure script(s) rerun with --from-extract into a temporary folder (removed); extracts from `/work/sublet/code/sim/out/figs`.

## Copy checks (§1.2, §3.2 step 1)

| Experiment | Record | Present | Pass | Commit | Time | Failed checks |
|---|---|---|---|---|---|---|
| e11 | `code/sim/out/ms3_e11_0.json` | true | true | 29919ea0a0cb0be883ceb60b86c1f1ddd1dcfa3c | 2026-10-19T23:59:24 | – |
| e1 | `code/sim/out/ms3_copy_e1.json` | true | true | f10237bb39ab101b9831afcee79121d0fa4e1979 | 2026-10-20T18:42:43 | – |
| e10 | `code/sim/out/ms3_copy_e10.json` | true | true | f10237bb39ab101b9831afcee79121d0fa4e1979 | 2026-10-20T15:22:06 | – |
| e2 | `code/sim/out/ms3_copy_e2.json` | true | true | f10237bb39ab101b9831afcee79121d0fa4e1979 | 2026-10-22T01:50:21 | – |
| e6 | `code/sim/out/ms3_copy_e6.json` | true | true | f10237bb39ab101b9831afcee79121d0fa4e1979 | 2026-10-22T17:26:50 | – |

## Jobs (§2.4, §2.5)

| Folder | Job list | Listed | Records by status | Without 'ok' (blocking) | MILP, LB = LP (Q39) | Summary: jobs_missing, ignored_outputs |
|---|---|---|---|---|---|---|
| e1 | `code/sim/out/e1/manifest.json` | 570 | {ok: 572} | 0 | 0 | null, 0 |
| e10 | `code/sim/out/e10/manifest.json` | 183 | {ok: 185} | 0 | 0 | null, 0 |
| e2 | `code/sim/out/e2/manifest.json` | 1531 | {ok: 1533} | 0 | 0 | 0, null |
| e6/a | `code/sim/out/e6/a/manifest.json` | 877 | {ok: 879} | 0 | 0 | 0, null |
| e6/b | `code/sim/out/e6/b/manifest.json` | 28 | {ok: 30} | 0 | 0 | 0, null |

Every listed job has an 'ok' record, or is a MILP job whose LB is the LP under Q39's rule. The jobs without an 'ok' record outside Q39's MILP rule are listed below, at most 50 per folder; a MILP job stopped at the wall-clock limit or by the cap leaves the LP as its LB (§2.5).
