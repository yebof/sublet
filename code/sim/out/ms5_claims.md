# MS5 claims report (design/sim_spec_ms5.md §1.4, §9)

Written 2026-11-25T06:41:09 by `sublet.experiments.ms5_claims` at revision 992823b93d06ab079b469b16d32b1b9309e79b35; inputs under the repository.

**Criterion of §1.4 item 2: holds.** No row is a bug, and every row is reproduced, holds, informative or explained (0 explained).

Rows: 16; reproduced 1, holds 12, informative 3, explained 0, bug 0, missing 0, pending 0.

Figures (§1.4 item 1): 3 of 3 redrawn from their extracts with finalize() passing, 0 extract(s) missing, 0 error(s); 0 figure(s) with mathtext glyphs below 4.9 pt, i.e. below a first-level script of 7-pt text (listed below; plan §5 allows first-level scripts).

Copy checks: s1 pass; e9 pass (2 of 2 records present; every present record passes; one clone commit).

Jobs (§2.4): s1/sweep 204 listed, ok 206; s1/q28 76 listed, ok 78; e9 156 listed, ok 158 (every listed job has an 'ok' record).

Rebuild (§1.4 item 5): 235 of 235 outputs identical in mode 'check' at 992823b93d06ab079b469b16d32b1b9309e79b35; pass true.

## S1 (§3.10)

| Check | Claim | Status label | Reference (file) | Regenerated (file) | Verdict |
|---|---|---|---|---|---|
| S1-0 | the default point's twelve runs equal E7's (out/e7/main/summary.json runs.1.Sublet: median, p95, max and mean of overflow_usd within 1e-9 relative, and the instance hashes of meta.instances equal) | none: the identity of S1's default point with E7's runs (M1) | E7's runs.1.Sublet overflow_usd (median, p95, max, mean) within 1e-9 relative; the instance hashes of meta.instances (tolerance 1e-09; overflow_usd.median.e7 23785.5); `code/sim/out/e7/main/summary.json` | n_runs {s1: 12, e7: 12}; n_runs_equal true; max(overflow_usd.*.rel_diff) 0; stats_differ []; hashes_differ []; hashes_missing []; `code/sim/out/s1/sweep/summary.json checks.S1-0` | **reproduced** |
| S1-1 | every point is built as §3.4 states: its instance hash differs from the default's, the demand, compared client by client, and BL0a equal the default's exactly on the rows without Gamma, the points with g^lay 16 have every LLM on a fitting site, and every LLM but S at sS0 has clients | none: the build of the points (§3.4, M3) | the default build of the same alignment; `design/sim_spec_ms5.md §3.4` | n_instances 200; n_failures 0; len(g16_fits) 12; len(rows_without_gamma) 10; `code/sim/out/s1/sweep/summary.json checks.S1-1` | **holds** |
| S1-2 | every A8 run has its certificate, and it holds (Theorem W(a)(b)) | Theorem W(a)(b) (PROVEN for the engine as implemented under C1-C3, audited); W(c) (CONJECTURE) | held in every proven-case run; W(c) runs counted; `code/sim/sublet/algos/guard.py (Theorem W, module docstring); design/Sublet_design.md §2.9` | n_runs 612; certificates.n 612; certificates.held 612; n_unavailable 0; n_failures 0; n_w_c 0; n_run_errors 0; `code/sim/out/s1/sweep/summary.json checks.S1-2` | **holds** |
| S1-3 | no run has an invariant failure | none: the engine's invariants | no invariant failure; `design/Sublet_design.md §5.2` | n_runs 612; n_invariant_failures 0; n_runs_with_gpu_only_lease_slots 0; `code/sim/out/s1/sweep/summary.json checks.S1-3` | **holds** |
| S1-4 | the saving per point and the span per row (informative); with the rows whose span exceeds 10 percentage points named | none: a sensitivity study with no theory claim (design §5.5, S1) | the default point's median saving over BL0a (threshold_pp 10; saving_pct_median.default 28.4149); `code/sim/out/s1/sweep/summary.json rows.<row>.default` | len(saving_pct_median) 51; min(saving_pct_median) -1.39391; max(saving_pct_median) 51.7478; max(span) 42.1175; rows_span_above_threshold [load_scenario, alpha, smoothing, own_capacity, mu_split, xi]; rows_incomplete []; `code/sim/out/s1/sweep/summary.json checks.S1-4` | **informative** |

- S1-0: the summary's claim: the default point's twelve runs equal E7's (code/sim/out/e7/main/summary.json runs.1.Sublet: median, p95, max and mean of overflow_usd within 1e-9 relative, and the instance hashes of meta.instances equal)
- S1-1: the summary's claim: every point is built as §3.4 states: its instance hash differs from the default's; on the rows without Gamma the demand, compared client by client, and BL0a equal the default's exactly; the points with g^lay 16 (every point, checked) have every LLM on a fitting layer site; every LLM but S at sS0 has clients
- S1-2: the summary's claim: every A8 run has its certificate (available true), and in Theorem W's proven cases (W(a), W(b); PROVEN for the engine as implemented under C1-C3, audited) it holds; W(c) runs (CONJECTURE) are counted and listed
- S1-4: reported as measured; S1 is a sensitivity study in the supplement with no claim (§3.1). the summary's claim: the saving per point and the span per row (informative), with the rows whose span exceeds 10 percentage points named

## Q28 (§4.7)

| Check | Claim | Status label | Reference (file) | Regenerated (file) | Verdict |
|---|---|---|---|---|---|
| Q28-1 | every run of every policy under both variants finishes with no invariant failure and handles every refusal and every violation death (no error record) | none: the policies' handling of refused purchases and violation deaths (MS2 spec §20 item 23) | no invariant failure, no error record; `design/Sublet_design.md §5.2.2, §7.5` | n_runs 228; n_sub_runs 360; n_invariant_failures 0; n_run_errors 0; n_job_failures 0; refusals_unavailable_total 76217; violation_deaths_total 3; `code/sim/out/s1/q28/summary.json checks.Q28-1` | **holds** |
| Q28-2 | every L-vr run reports no ratio (ratio_validity non-null) and every L-rf run on the trace schedule keeps its ratio validity as under the default lender; every stress run file records its variant's lender model | none: the ratio rule of design §5.2.4 under the stress variants | ratio_validity non-null under L-vr; under L-rf as under the default lender; `code/sim/sublet/drivers/run.py (ratio_validity); design/Sublet_design.md §5.2.4` | grids [fast, slow_lb, slow]; n_vr 108; n_vr_with_a_ratio 0; n_rf 108; n_rf_changed 0; n_files_checked 72; n_wrong_lender_model 0; `code/sim/out/s1/q28/summary.json checks.Q28-2` | **holds** |
| Q28-3 | every A8 run under both variants has its certificate, and it holds | Theorem W(a)(b) (PROVEN for the engine as implemented under C1-C3, audited); W(c) (CONJECTURE) | held in every proven-case run; W(c) runs counted; `code/sim/sublet/algos/guard.py (Theorem W, module docstring); design/Sublet_design.md §2.9` | n_runs 48; certificates.n 48; certificates.held 48; n_unavailable 0; n_failures 0; n_w_c 0; n_run_errors 0; `code/sim/out/s1/q28/summary.json checks.Q28-3` | **holds** |
| Q28-4 | the change of each policy's median cost over BL0a against its reference, the refusals and the violation victims (informative) | none: Q28's stress variants (design §7.5), a measurement | E7's runs.1.<tag> (BL3: part q28's default jobs; Sublet also S1's default point); `code/sim/out/e7/main/summary.json; code/sim/out/s1/sweep/summary.json` | delta_overflow_over_bl0a.rf {Sublet: -0.00809213, A7G: -0.0268389, A7: -0.0268389, A6: -0.00814054, BL5: -0.00809213, BL1: -0.0315424, BL2: -0.0270663, BL4: -0.00271234, BL3: -0.0102976}; delta_overflow_over_bl0a.vr {Sublet: 0, A7G: 0, A7: 0, A6: 0, BL5: 0, BL1: 0, BL2: 0, BL4: 0, BL3: 0}; delta_overflow_over_bl0a_s1_default {rf: -0.00809213, vr: 0}; refusals_unavailable_median.rf {Sublet: 368, A7G: 610.5, A7: 610.5, A6: 201, BL5: 368, BL1: 639, BL2: 474.5, BL4: 36.5, BL3: 404.5}; violation_victims_median.vr {Sublet: 0, A7G: 0, A7: 0, A6: 0, BL5: 0, BL1: 0, BL2: 0, BL4: 0, BL3: 0}; saving_rises {rf: [A6, A7, A7G, BL1, BL2, BL3, BL4, BL5, ...], vr: []}; `code/sim/out/s1/q28/summary.json checks.Q28-4` | **informative** |

- Q28-1: the summary's claim: every run of every policy under both variants (and BL3's reference runs under the default lender) finishes with no invariant failure and handles every refusal and every violation death (no error record)
- Q28-2: the summary's claim: every L-vr run reports no ratio (ratio_validity non-null for every grid) and every L-rf run on the trace schedule keeps its ratio validity as under the default lender (the same reason for every grid); every stress run file records its variant's lender model (the L-rf half holds by construction once the lender model is L-rf's)
- Q28-3: the summary's claim: every A8 run under both variants has its certificate (available true), and in Theorem W's proven cases (W(a), W(b); PROVEN for the engine as implemented under C1-C3, audited) it holds; W(c) runs (CONJECTURE) are counted and listed
- Q28-4: reported as measured against each policy's reference under the default lender (§4.4). the summary's claim: the change of each policy's median cost over BL0a against its reference, the refusals and the violation victims (informative)

## E9 (§5.9)

| Check | Claim | Status label | Reference (file) | Regenerated (file) | Verdict |
|---|---|---|---|---|---|
| E9-1 | every run job finished with status ok inside the 3 GB cap, with no invariant failure | none: the job records and the engine's invariants | status ok, no failure (cap_mb 3072); `design/sim_spec_ms5.md §0 item 2` | n_jobs 128; jobs_by_status {ok: 128}; n_failed 0; n_missing 0; n_runs 128; n_runs_with_invariant_failures 0; n_over_cap 0; `code/sim/out/e9/summary.json checks.E9-1` | **holds** |
| E9-2 | per run, C27's counts equal the grid (n_slow_steps = 288, n_fast_steps = 1,440), and slow_step_s_sum + fast_step_s_sum + reset_s + finish_s does not exceed wall_s by more than 1e-6 s | none: the engine's loop times (C27) | the grid's step counts; the sums at most wall_s + 1e-6 s (tolerance_s 1e-06); `code/sim/sublet/engine.py (RunResult.runtime, C27)` | n_runs 128; grids [[288, 1440]]; n_failures 0; max_excess_s -0.0052849; `code/sim/out/e9/summary.json checks.E9-2` | **holds** |
| E9-3 | every A8 run has its certificate, and it holds (Theorem W(a)(b)) | Theorem W(a)(b) (PROVEN for the engine as implemented under C1-C3, audited); W(c) (CONJECTURE) | held in every proven-case run; W(c) runs counted; `code/sim/sublet/algos/guard.py (Theorem W, module docstring); design/Sublet_design.md §2.9` | n_runs 64; certificates.n 64; certificates.held 64; n_unavailable 0; n_failures 0; n_w_c 0; `code/sim/out/e9/summary.json checks.E9-3` | **holds** |
| E9-4 | every LP job ended ok, and every LP under M18's gate was solved to optimality (linprog status 0, HiGHS's model status 7, 'Optimal') inside the 3 GB cap; an LP whose estimate is not under the gate is not solved and is listed as gated (amended on 2026-10-30) | none: the LP bound's solves (M17, M18) | linprog status 0, HiGHS model status 7; gated LPs listed (gate_mb 2800; time_limit_s 1500); `code/sim/sublet/opt/milp.py (solve_lp); design/sim_spec_ms5.md §5.9` | n_jobs 28; jobs_by_status {ok: 28}; n_lps 28; n_not_optimal 2; n_gated 2; gated [e9:lp:pt=e7r_V32_SML:c=2, e9:lp:pt=e7r_V64_SML:c=2]; n_failed 0; n_missing 0; summary_status fail; `code/sim/out/e9/summary.json checks.E9-4 (recomputed by this report, §5.9 as amended)` | **holds** |
| E9-5 | per point and policy, the loops per simulated hour against real time, the slow-step P99 and maximum against the 300-s slot, the fast-step P99 against the 60-s slot, the setup, the peak memory and the LP's time (informative); the ratio to real time of the largest point of each menu named | none: a system measurement with no claim (design §5.5, E9) | real time 3,600 s per simulated hour; slots of 300 s and 60 s (real_time_s_per_h 3600; slow_slot_s 300; fast_slot_s 60); `design/sim_spec_ms5.md §5.6` | largest_point_by_menu.*.point {full: e7f_V64_SML, reduced: e7r_V64_SML}; largest_point_by_menu.*.sites_x_llms {full: 3855, reduced: 3885}; largest_point_by_menu.*.policies.Sublet.real_time_over_loops {full: 34.0955, reduced: 135.559}; largest_point_by_menu.*.policies.A6.real_time_over_loops {full: 590.927, reduced: 438.275}; flags.slow_step_max_over_slot []; flags.fast_step_p99_over_slot []; flags.loops_over_real_time []; `code/sim/out/e9/summary.json checks.E9-5` | **informative** |

- E9-2: the summary's claim: per run, C27's counts equal the grid (n_slow_steps = T_slow, n_fast_steps = T_fast: 288 and 1,440 for one day) and slow_step_s_sum + fast_step_s_sum + reset_s + finish_s does not exceed wall_s by more than 1e-6 s
- E9-3: the summary's claim: every A8 run has its certificate, and it holds in every run of Theorem W's proven cases (W(a), W(b); PROVEN for the engine as implemented under C1-C3, audited); W(c) runs (CONJECTURE) are counted and listed with their t_a
- E9-4: 2 LP(s) above M18's gate not solved (gated, §5.9 as amended): e9:lp:pt=e7r_V32_SML:c=2, e9:lp:pt=e7r_V64_SML:c=2. the summary's claim: every LP job was solved to optimality (linprog status 0, HiGHS's model status 7, 'Optimal') inside the 3 GB cap
- E9-5: reported as measured; E9 has no claim (§5.1). the summary's claim: per point and policy, the loops per simulated hour against real time, the slow-step P99 and maximum against the 300-s slot, the fast-step P99 against the 60-s slot, the setup, the peak memory and the LP's time; the ratio to real time of the largest point of each menu named (informative)

## SL (§6.3)

| Check | Claim | Status label | Reference (file) | Regenerated (file) | Verdict |
|---|---|---|---|---|---|
| SL-1 | the extract's daily series equal a recomputation from the npz without the trace's end (minimum, mean and maximum per day within 1e-9), and its source digests equal the versioned files' | none: the slack extract against its analysis outputs (§6) | the npz's daily minimum, mean and maximum without the trace's end (within 1e-9); the sha256 of the npz and the two JSON files (tolerance 1e-09; slots_per_day 288; tail_rise 0.5); `code/analysis/out/a1_slack_series.npz; code/analysis/out/a1_lender_spotgpu.json; code/analysis/out/a9b_notice_buffer_24h.json` | n_pools 6; n_days 177; n_slots 50993; n_kept 50975; tail_start_slot 50975; max_abs_diff 0; digests_equal true; len(failures) 0; `code/sim/out/figs/sf_slack.json (recomputed by this report)` | **holds** |

## RB (§8.4)

| Check | Claim | Status label | Reference (file) | Regenerated (file) | Verdict |
|---|---|---|---|---|---|
| RB-1 | the exit run of run_all.sh with CHECK=1 in a clean clone: every output identical, no file without its entry, the float heights equal | none: the frozen rebuild (design §5.2.6, M30) | every output byte-identical with its versioned file; the float heights equal on every key but 'written'; no file without its entry; `code/sim/figs/rebuild.py` | mode check; only null; git_revision 992823b93d06ab079b469b16d32b1b9309e79b35; tracked_files_dirty false; n_outputs 235; n_identical 235; len(different) 0; len(unlisted) 0; len(missing) 0; heights_equal {plain: true, ms4: true}; hand_set_ok true; len(stale) 0; len(problems) 0; `code/sim/out/figs/rebuild.json (read by this report)` | **holds** |

## Figures: small glyphs (§1.4 item 1)

| Figure | Script | Status | Small glyphs | Glyphs below 4.9 pt (size, text) |
|---|---|---|---|---|
| sf_e9 | `figs/supp/sf_e9.py` | ok | 0 | none |
| sf_s1 | `figs/supp/sf_s1.py` | ok | 0 | none |
| sf_slack | `figs/supp/sf_slack.py` | ok | 0 | none |

3 figure script(s) rerun with --from-extract into a temporary folder (removed); extracts from `/work/sublet/code/sim/out/figs`.

## Copy checks (§1.2)

| Experiment | Record | Present | Pass | Commit | Time | Failed checks |
|---|---|---|---|---|---|---|
| s1 | `code/sim/out/ms3_copy_s1.json` | true | true | 622cf450266ed08609c0958193131e62070450e2 | 2026-10-30T18:42:11 | – |
| e9 | `code/sim/out/ms3_copy_e9.json` | true | true | 622cf450266ed08609c0958193131e62070450e2 | 2026-10-30T18:42:12 | – |

2 of 2 records present; every present record passes; one clone commit.

## Jobs (§2.4)

| Folder | Job list | Listed | Records by status | Without 'ok' (blocking) | Summary: jobs_missing, ignored_outputs |
|---|---|---|---|---|---|
| s1/sweep | `code/sim/out/s1/sweep/manifest.json` | 204 | {ok: 206} | 0 | 0, 0 |
| s1/q28 | `code/sim/out/s1/q28/manifest.json` | 76 | {ok: 78} | 0 | 0, 0 |
| e9 | `code/sim/out/e9/manifest.json` | 156 | {ok: 158} | 0 | 0, 0 |

Every listed job has an 'ok' record.

## Rebuild record (§8.3)

`code/sim/out/figs/rebuild.json`: status pass, mode check, ONLY null, revision 992823b93d06ab079b469b16d32b1b9309e79b35 (tracked files dirty: false), written 2026-11-25T06:39:59; 235 of 235 outputs identical over 62 scripts; differ: none; not written: none; without an entry: none; listed but missing: none; float heights equal {plain: true, ms4: true, ms5b: true, ms7: true}; hand-set files unchanged true.

Tools: {python: 3.12.3, numpy: 2.4.4, scipy: 1.17.1, matplotlib: 3.10.8, pymupdf: 1.27.2.3, pillow: 12.2.0, poppler: pdffonts version 24.02.0, ghostscript: 10.02.1, pdflatex: pdfTeX 3.141592653-2.6-1.40.29 (TeX Live 2026)}.

Fonts: Liberation Sans regular `/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf` sha256 4659bc0c58c5028dd488ec928d41d9265db43d9b669fc14ca8b0832daca7b144; Liberation Sans bold `/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf` sha256 3973aa5054fb467dd5627245d3dc82e37bf16fe075756156a570455871351582; Liberation Sans italic `/usr/share/fonts/truetype/liberation/LiberationSans-Italic.ttf` sha256 830c5fa600505fb4c1a271b4271c53c44bae43f492b2a240d0e98a3a7a380121; STIXGeneral `/opt/venv/lib/python3.12/site-packages/matplotlib/mpl-data/fonts/ttf/STIXGeneral.ttf` sha256 167378031e2dddc6216d67819c9260e9a06ffc4c478e4e23cb98a6fd44b183c2.

## Caption drafts (§1.4 item 2)

sf_e9 (1491 characters): Wall time per simulated hour against sites × LLMs (one day per run; medians over 4 alignments at policy seed 0, with the range over the alignments as bars and, for the LP, as a grey band; invariant checks on; the host's 1-min load average at a job's start: median 1.42, at most 4.00). The points are, from left to right, $V$ = 1, 2, 4, 8, 16, 32 and 64 layers per trace lender. (a) The full menu of E7 (20 revocable contracts) and (b) the reduced menu (3): the slow loop (lines with markers) and the fast loop (lines with small markers) of each policy; the setup per run (build, inputs, construction and reset) is left out and given in Table~\ref{tab:e9-steps}. (b) also gives the time to build and solve the LP bound over the day, divided by its simulated hours (black dashed; the merged relaxation on the slow grid). (a) has no LP bound: on the full menu the LP's estimated memory, at least 4.8 GB, exceeds the 3 GB cap of a job. (c) The slow-step P99 on the full menu. Grey: real time (3,600 s per simulated hour) and the 5-min slow slot. The two fast loops cross between $V$ = 16 and 32 and differ by at most 31% from $V$ = 16 on; where they meet, the line of Lagged RetroRenting + one-way guard ($B_0=10\%$ of the all-fallback bill), drawn last, covers the other. At $V$ = 32 and 64 the LP of alignment 2 was not solved in E9's run, since its estimated memory exceeded the LP runs' gate of 2,800 MB; it was solved separately on the same instance and is included in the median and range.

sf_s1 (1779 characters): The saving over all-fallback of Lagged RetroRenting + one-way guard ($B_0=10\%$ of the all-fallback bill) in overflow accounting per assumption on E7's main week (one week; medians over 4 alignments × 3 policy seeds; each setting's saving over its own all-fallback cost). A bar runs from the lowest to the highest median over the row's settings (markers) and the default (grey line, 28.4%), labeled with the settings at its ends; rows sorted by span. $\Gamma$ is re-solved to keep the market tightness at its default 0.5 (in its own row, at the row's values) in every row of (b) and in the lease quantile, offered layers $V_\ell$, layer GPUs and buffer quantile rows of (c). Its allowance $B_0$ is 10\% of each run's all-fallback cost. The $\alpha_p$ and protected term rows change nothing: the policy leases no protected capacity at their settings. L-rf refuses purchases on unavailable layers, L-vr turns buffer violations into reclaims without notice (off: the default lender; on: the variant); no buffer violation occurred in its L-vr runs, so they equal the default lender's. The $\mu/\tilde{\beta}$ row reuses E7's runs. Bar ends not labeled: Load scenario from WAN 1 Gb/s to warm peer (Table~\ref{tab:s1-points}). Not run: the warm-peer and SSD load-rate scaling, the client unit $1/u$ and the pool width $\zeta$ (no sweep in the register); the tier map (its sweep is the default); a per-tier tokens-per-conversation factor and a clock alignment at local midnight (no source); a non-causal smoothing window and a load scenario per region pair (not built); $V_\ell$ as the whole block below the lease quantile (beyond the evaluation's memory budget); $V_\ell$ as a share of the mean lendable capacity (not defined); a uniform $\kappa$ multiplier (identical to the default).

sf_slack (996 characters): Lendable slack (capacity minus the high-priority jobs' occupancy, at least 0) of the six GPU pools of Alibaba's cluster-trace-v2026-spot-gpu [duan2026gfs] at 5-min slots: daily minimum to maximum (band) and daily mean (line) over 177 days from the end of the trace's first week, which the analysis drops; each y axis runs from 0 to the pool's capacity (title). The trace's last 18 slots (90 min), in which every pool's slack jumps at once to at least 82% of its capacity, are left out. Thin light line: P25, the 25th percentile of the pool's slack over the whole series (the slack reaches it in at least 75% of the slots). At its default lease-size quantile (P25) the simulator takes this quantile of the slack left after the lender's notice buffer and rounds it down to whole layers, so the top of the block a spot lender offers lies at or below this line. (a) A10: P25 = 0; its slack is zero in 94.0% of the slots, in every slot until day 166, and its daily mean is 92–126 GPUs from day 167 on.
