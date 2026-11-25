# Captions of the data files

Each section gives, for one file of this folder, the caption of the table of the paper's supplementary material whose rows it holds (the supplement names the file instead of printing the table), its wording adapted to the file's columns, or, for a data file written by the experiments' programs, a description of its columns. A file converted from a table holds one line per data row of the table, numbers as printed (a dash: no value), and its first columns identify the row: its label; where the table had sections, the section (a column such as Fold, Point or Reference); and where the table gave two rows for one label, a column Statistic or Row that names each. A cell that the table printed on two lines is two columns, named by the table's header and the line's quantity, such as ‘L-tr median’ and ‘L-tr min–max’. Formats within a cell: ‘median (min–max)’ is a median with, in parentheses, the minimum and maximum over the same weeks, cells or runs, and a range [a, b] or a–b is a minimum and a maximum; counts in parentheses after a value, as in ‘0.014 (4/0/12)’, are the sign counts that the caption names (W/T/L: won, tied and lost; or below, at and above zero); a cell that lists several items separates them by ‘; ’. The per-run data files, written by the experiments' programs, have a section that lists their columns. In baseline_study_runs.csv, e7v2_rc_runs.csv, lag_v2_runs.csv, oos_runs.csv and s1v2_runs.csv the policy labels (and in s1v2_runs.csv the assumptions and settings) are LaTeX source; in every per-run data file the column tag is the policy's plain identifier in the code.

## e6a_cells_summary.csv

The cells of the protection heatmaps per lender group, protected load time λ' and μ/β̃. A cell holds the cost of revocable-only leasing over ALG*: the median over (lender, series) pairs, at μ/β̃=1 over (lender, series, alignment) triples, of the layer-summed cost ratio; above 1, ALG*'s insurance pays. Columns: the cells with a value, those above 1, at 1 (down to 0.5% below 1, as the step lines of the heatmaps count them) and below 1, and the range of the ratio. The supplementary data file e6a_cells.csv lists every cell with a value: lender group, λ', μ/β̃, H (min), αp/α, the ratio, its 95% bootstrap interval, the number of pairs and the share of pairs where ALG* insures. The 432 cells without a value (spot cells with data from fewer than two pools; hatched in the supplement's figure of the protection heatmaps) are left out.

## e6a_cells.csv

Every cell with a value of the protection heatmaps, at every μ/β̃: lender_group (MaaS or spot), protected_load_time (λ', the load time at the protected site: measured or 0), mu_over_beta_tilde (μ/β̃), notice_H_min (the notice H, min), price_ratio_alpha_p_over_alpha (αp/α), revocable_only_over_alg_star (the cost of revocable-only leasing over ALG*, the median over (lender, series) pairs, at μ/β̃=1 over (lender, series, alignment) triples, of the layer-summed cost ratio; above 1, ALG*'s insurance pays), ci95_lo and ci95_hi (its 95% bootstrap interval), n (the pairs or triples) and share_insured (the share of them in which ALG* insures). The data file e6a_cells_summary.csv counts these cells per lender group, λ' and μ/β̃.

## e7v2_pareto.csv

Per-week Pareto front of the trace cost r0 and the worst cost W0 (part main, policy seed 0) over the 15 policies of the confirmation that are not ablations of critical-ratio renting in the registered analysis, which counts Greedy + notice layer, run by critical-ratio renting's code with other parameters, as an ablation (Sublet; Critical-ratio renting; Sublet, one-way; Greedy + guard; Lagged RetroRenting + one-way guard (B0=10% of the all-fallback bill); Greedy renting; Greedy, back-off; Per-borrower ski rental; SpotHedge-style, NExtra=0; CoCaR-style; RetroRenting-style; RetroRenting-style, lagged; RetroRenting, τ≥1 h; RetroRenting + notice layer; and Two-timescale PD), each member with its (r0, W0), the members separated by semicolons; whether Sublet is on the front, its values, and the policies that dominate it. Sublet is off the front in weeks 309, 311 and 316. In each of these weeks only Critical-ratio renting, its inner policy, dominates it, by at most 0.004 in r0 and 0.003 in W0.

## e7v2_table3_intervals.csv

The confirmation's cells behind Table IV of the main text, with each policy's gap ALG/LB and first crossing p* (weeks 301–316 of part main, trace lender, policy seed 0; the gap on the days of part second): median; its 95% week-bootstrap interval over the weeks, and for the gap days the range over the days; and the number of values n (descriptive). p*, the least reclaim probability p with a cost above all-fallback (the data file e7v2_crossings.csv), is the lower median over weeks 301–304 (a week without a crossing counted above every p; ‘none’: not reached on the grid up to p=1; >q: not reached up to q, the grid's largest p for that policy); the per-week first crossings, read the same way, stand in place of an interval. Total accounting includes the borrowers' own capacity. All-fallback's saving is 0 and its W0 1 by definition.

## e7v2_rc.csv

Revocation cost RC =r0(M)-r0(L-hon) under every lender mode M, each run paired with the honoring lender's run of the same policy, week and policy seed (2,688 runs; policy seed 0, and seeds 1–2 of part seeds in rows of their own): the number of runs, the median RC and its 95% bootstrap interval over the runs (over n=4 runs, the range of the runs), and the medians of the runs' fallback and stranding totals (USD) and of the fallback share after reclaims that the earlier end-to-end study defined. Part main's modes on every week; part second's (L-vr, L-rf, L-ad, L-tr with the P99.9 buffer, i.i.d. lenders L-iid-p) on its weeks. On weeks 301–304 the runs under L-ad, L-eg and L-iid-1 have equal RC for every policy (each of these lenders announces every revocable lease when its guaranteed period ends): the rows of L-ad and L-iid-1 are equal and repeat L-eg's runs of those weeks. Every run's RC, fallback and stranding totals and share after reclaims (2,688 rows) are in the supplementary data file e7v2_rc_runs.csv.

## e7v2_rc_runs.csv

Every run of e7v2_rc.csv, one line per policy, lender, week and policy seed, each paired with the honoring lender's run of the same policy, week and policy seed. Columns:
- `policy`: the policy's label
- `tag`: the policy's plain identifier in the code
- `lender_mode`: L-tr, L-eg, L-ss, L-co, L-iid-0.05 and L-iid-0.2 on weeks 301–316; on weeks 301–304 also L-vr, L-rf, L-ad, L-b999 (the trace lender with the P99.9 buffer) and L-iid-p at p=0.1, 0.34, 0.5, 0.8 and 1
- `week`: the week (its configuration seed), 301–316
- `policy_seed`: the policy seed (0; 1 and 2 for the policy seeds of part seeds)
- `rc`: RC, r0 under the lender minus r0 under L-hon
- `fallback_usd`: the run's fallback cost over the week (USD)
- `stranding_usd`: the run's stranding cost over the week (USD)
- `fallback_share_after_reclaims`: the fallback load over the demand within 60 min after each capacity drop of an LLM caused by a reclaim, a buffer violation or an announced lease, summed over the LLMs (a fraction; empty where the run had no such drop)

## e7v2_seeds.csv

Policy seeds of part seeds (weeks 301–304): r0 under the seven lender modes, W0 and RC under the trace lender for policy seeds 0, 1, 2 (seed 0 from part main); a column is week/seed, and Metric names the row's quantity: r0 under the lender named, W0, or RC under the trace lender (RC, L-tr). Every value of Sublet at seeds 1 and 2 equals seed 0's: its inner policy draws no random number, and the safe expert, which holds the guard's random draws, followed FB at every slot of all 56 of its runs at these seeds. Largest difference from seed 0: Greedy renting 0.0096; RetroRenting-style 0.0079.

## e7v2_crossings.csv

First crossing of all-fallback on every confirmation week (policy seed 0): the least reclaim probability p of the i.i.d. lender at which the cost exceeds all-fallback (r0>1), parts main and second merged as in the registered analysis. A cell ‘none’ means r0≤1 at every p of the grid up to p=1; a cell >q means r0≤1 at every p measured that week, q the largest (>0.2 on a three-point grid: not reached at p≤0.2); a dash, no run. Grids: 8 points up to p=1 for 12 policies on weeks 301–304; 3 points up to p=0.2 on the other 304 policy-weeks. The lagged-demand policies ran under the trace lender only and have no curve. A cell 0: r0>1 already at p=0, the honoring lender L-hon (no reclaim), the first point of both grids.

## e7v2_boundary.csv

Boundary conditions of part second (weeks 301–304, policy seed 0): cost over all-fallback r0 per week under the trace lender (part main, the reference), L-vr (buffer violations as reclaims without notice), L-rf (purchases on unavailable layers refused), L-ad (every lease announced at the end of its guaranteed period) and the P99.9 buffer, with the median and the range over the weeks. No buffer violation occurred in the 48 L-vr runs, so L-vr's rows equal the trace lender's for every policy. On these weeks L-ad gives the same r0 as the eager lender L-eg and the i.i.d. lender at p=1 for every policy (each announces every revocable lease when its guaranteed period ends).

## e7v2_lag.csv

Lagged demand under the trace lender (weeks 301–304, policy seed 0): r0 of each policy on the revealed slot's demand (part main) and on slot t-1's demand, and their difference, per week, with the median and the range over the weeks. The lagged runs: Sublet, lagged; Critical-ratio renting, lagged; and Greedy renting, lagged from part second; RetroRenting-style, lagged from part main.

## e7v2_e5.csv

The redundancy menus in part second (one week, config seeds 301, 302, 303, 304, policy seed 0): r0 per config seed on the short menu (spot-like contracts with notice up to 2 min, and the protected contract) and the long menu (notice 60–240 min, and the protected contract), under the trace lender and all1 (the correlated lender with every site in one group), with the median and the range over the config seeds.

## fam_v2_instances.csv

The guard study's family instances under the fixed lenders (adaptive for F1, eager for F2 and F3; lender seed 0): per instance the mean ALG/OPT over the policy seeds of every policy that ran there. A policy without random draws (critical-ratio renting, its ablation without insurance and RR-renew) gives one run per instance, and its runs repeat the pilot's runs (not new evidence); reported in full with no criterion. An instance id gives its parameters, e.g. F1_m2_r4: m=2, ρ=4; F3_b2_T48: β=2, horizon T=48. A dash marks a policy that did not run: RR-renew and Marking on F3, since they take the one revocable contract of the single-LLM family and F3's instances offer a revocable and a protected contract.

## e7v2_grid.csv

Part grid, development-exposed (continuity, not a confirmation result): every policy's cost over all-fallback r0 under the trace lender at the alignments 1, 2, 3, 4, under each stress lender at alignment 1, the one with stress runs, with W0, the largest of them (each the median over the policy seeds 0, 1, 2), and the gap days' cost over the merged LP bound (slow grid, reduced menu; the median over the 4 days of the median over the seeds). Six policies ran policy seed 0 only: Critical-ratio renting; Greedy + notice layer; Critical-ratio renting, no make-before-break; Critical-ratio renting, no commitment rule; Critical-ratio renting, no insurance; Critical-ratio renting, k* contract. Equal over the policy seeds in every entry: Sublet; Sublet, one-way. Sublet, one-way aborts in every one of its 39 grid runs (at slot 0 in 33) and then follows all-fallback, hence its r0 and W0 entries of 1.000. The largest range over the policy seeds of any r0 entry is 0.049 (Two-timescale PD).

## e7v2_guard_study.csv

The guard study's held-out cells, development-exposed: per policy and instance the median cost over all-fallback under the trace lender (r0) and W0, the largest median over the instance's stress lenders (the guard study's definitions; in the rows ‘lender of W0’ of column Row, the lender that sets W0), and criterion S (W0≤1.05 on every instance). Part grid's cells per instance: I1 2; I2 7; I3 3; I4 8; the guard study's rows are its medians over its own held-out cells (I1 5; I2 7; I3 3; I4 8), set beside them, not paired. Criterion T is not computable for part grid's rows (a dash): part grid runs no renting baseline (greedy renting, per-borrower ski rental and RetroRenting-style) on these cells; for the guard study's rows its column gives the guard study's own verdict over its cells, D1≤1.1 on at least three of the instances, D1 the cost over the best of these three.

## lag_v2_policies.csv

Every policy on the previous slot's demand, over the 16 confirmation weeks (weeks 301–316, policy seed 0): r0 under the trace lender L-tr, W0 (the largest r0 over the five stress lenders) and the revocation cost RC =r0(L-tr)-r0(L-hon), then each of them lagged minus revealed (Δ, per week, against the same policy with the slot revealed; for RetroRenting-style, lagged, against RetroRenting-style). Statistic: median, the median over the weeks; min–max, the minimum and maximum. The last two columns count the weeks with r0<1 and with W0<1.

## lag_v2_margins.csv

The margin of Sublet, lagged, per week over the 16 confirmation weeks (weeks 301–316, policy seed 0): the least r0 under L-tr (or the least W0; column Metric) over a set of policies minus Sublet's, every policy on the previous slot's demand (positive: Sublet costs less). The primary baselines: Greedy renting, lagged; Greedy, back-off, lagged; Per-borrower ski rental, lagged; SpotHedge-style, NExtra=0, lagged; CoCaR-style, lagged; and RetroRenting-style, lagged. The notice-aware policies: RetroRenting, τ≥1 h, lagged; Greedy + guard, inner lagged; Greedy + notice layer, lagged; and RetroRenting + notice layer, lagged. The weeks compared (Weeks), those with a positive margin (wins), a zero margin (ties) and a negative margin (losses), and the weeks that a missing run decides (lost, a loss); the median, minimum and maximum of the margin over the other weeks; and the policies that are the least of the set, each with the number of weeks in which it is, separated by semicolons.

## lag_v2_modes.csv

The cost over all-fallback, r0, of every policy under each of the 7 lenders with every policy on the previous slot's demand, over the 16 confirmation weeks (weeks 301–316, policy seed 0): the median over the weeks (Statistic median) and the minimum and maximum (Statistic min–max). The guard of Sublet and of greedy renting with the guard tests the realized slot. Every run's r0, lagged and revealed, is in the data file lag_v2_runs.csv.

## lag_v2_runs.csv

Every run with demand one slot late, one line per policy, lender and week (weeks 301–316, policy seed 0), beside the same policy's run with the slot revealed. Columns:
- `policy`: the policy's label (on the previous slot's demand)
- `tag`: the policy's plain identifier in the code
- `revealed_policy`: the label of the same policy with the slot's demand revealed
- `revealed_tag`: its plain identifier (BL5: RetroRenting-style, lagged, which plans on the previous slot as built, so its lagged values are the confirmation's runs)
- `lender_mode`: L-tr, L-hon, L-eg, L-ss, L-co, L-iid-0.05 or L-iid-0.2
- `week`: the week (its configuration seed)
- `policy_seed`: the policy seed (0 in every line)
- `r0_lagged`: r0 with the demand one slot late (for the two guarded policies only the inner policy is lagged; the guard tests the realized slot)
- `r0_revealed`: r0 of the revealed policy in the confirmation's run of the same lender and week
- `projected_slots`: the slots at which the guard ran a projected action list (the two guarded policies only; empty for the others, as in the next three columns)
- `aborted`: 1 where the guard aborted to the safe expert, else 0
- `certificate_held`: 1 where the run's certificate of the guard's bound held, else 0
- `envelope_ok`: 1 where ALG(t)+R(t)≤CS(t)+B(t) at every slot, else 0

## oos_margins.csv

The margin of Sublet over the primary baselines in the out-of-sample folds, per cell: the least r0 over the primary baselines minus Sublet's (positive: Sublet costs less), under each lender and on W0 (the largest r0 over the five stress lenders), per fold and arm over 16 cells (cells 0–15; policy seed 0): the cells with a positive, zero and negative margin and those with a missing run, a loss (W/T/L/M), and the median, minimum and maximum over the cells with a margin. The primary baselines: Greedy renting; Greedy, back-off; Per-borrower ski rental; SpotHedge-style, NExtra=0; CoCaR-style; RetroRenting-style, lagged; and RetroRenting-style. Forward fold: the MaaS lenders calibrated on days 1–4 of the trace week and evaluated on days 5–7; reverse fold: calibrated on days 4–7 and evaluated on days 1–3; in both folds, the spot lenders calibrated on weeks 1–12 of their series and evaluated on a 72-h block after them; in sample: the same cell and demand, with every lender calibrated on its whole series, the evaluated window included.

## oos_policies.csv

Every policy in the out-of-sample folds, over 16 cells (cells 0–15; policy seed 0): out of sample, r0 under the trace lender L-tr and under L-vr (buffer violations as reclaims without notice), W0 (the largest r0 over the five stress lenders) and RC =r0(L-tr)-r0(L-hon); then out of sample minus in sample (Δ) of r0 under L-tr and L-vr and of W0, with the cells below, at and above zero in parentheses. Statistic: median, the median over the cells; min–max, the minimum and maximum. Every value per cell and lender is in the data file oos_runs.csv. Forward fold: the MaaS lenders calibrated on days 1–4 of the trace week and evaluated on days 5–7; reverse fold: calibrated on days 4–7 and evaluated on days 1–3; in both folds, the spot lenders calibrated on weeks 1–12 of their series and evaluated on a 72-h block after them; in sample: the same cell and demand, with every lender calibrated on its whole series, the evaluated window included.

## oos_sources.csv

The lender-source counts of every policy in the out-of-sample folds, summed over 16 cells (cells 0–15; policy seed 0): the slots with a buffer violation of the run's leases, those with a positive attributable deficit, the reclaims and the violation cuts (v/a/r/c), per lender source, fold, arm and lender (L-tr; L-vr, which cuts leases on a buffer violation).

## oos_runs.csv

Every run of the held-out calibration, one line per fold, arm, policy and cell (72-h horizon, overflow accounting, policy seed 0; 15 policies, 16 cells). Columns:
- `fold`: fwd, the forward fold (the MaaS lenders calibrated on days 1–4 of the trace week and evaluated on days 5–7), or rev, the reverse fold (calibrated on days 4–7, evaluated on days 1–3); in both folds the spot lenders are calibrated on weeks 1–12 of their series and evaluated on the cell's 72-h block after them
- `arm`: oos, out of sample (every trace lender calibrated on its calibration window only), or is, in sample (the same cell, demand and Γ, every lender calibrated on its whole series, the evaluated window included)
- `policy`: the policy's label
- `tag`: the policy's plain identifier in the code
- `cell`: the cell, 0–15 (cell k takes the draws of confirmation week 301+k as its configuration and lender seed)
- `policy_seed`: the policy seed (0 in every line)
- `r0_<lender>`: r0, the cost over the cell's all-fallback cost, under the lender L-tr, L-vr, L-eg, L-ss, L-iid-0.05, L-iid-0.2, L-co or L-hon (a fraction)
- `W0`: the largest r0 over the five stress lenders L-eg, L-ss, L-iid-0.05, L-iid-0.2 and L-co
- `W0_lender`: the stress lender that sets W0 (a tie goes to the first in the order of W0's column)
- `r0_minus_confirmation_<lender>`: this run's r0 minus that of the confirmation's one-week run of the same policy and lender at configuration seed 301+k (empty for L-vr, which the confirmation's part main did not run)
- `<lender>_<source>_violation_slots`: for the lender L-tr or L-vr and the source maas or spot: the lender-slots (5 min) with a buffer violation at that source's trace lenders, summed over its lenders
- `<lender>_<source>_violation_slots_attributable`: those of them with a positive deficit attributable to the run's leases
- `<lender>_<source>_reclaims`: the run's leases at that source that ended by a reclaim
- `<lender>_<source>_violation_cuts`: the run's leases there that a buffer violation ended without notice (nonzero under L-vr only)
- `bl0a_usd`: the cell's all-fallback cost over the horizon (USD, overflow accounting)
- `supply_maas_gpus`: the GPUs of the offered layers of the MaaS lenders
- `supply_spot_gpus`: the same for the spot lenders (set by their calibration, so it differs by arm)
- `supply_protected_gpus`: the same for the protected lenders (0: protected capacity is not counted as layer supply)
- `gamma`: Γ, the factor that scales every borrower's overflow series into replica demand, set per cell and the same in both folds and arms
- `c0_from`: where the borrowers' own capacity C0 is fitted (demand_fit: on the fit period's demand, not on the evaluated window)
- `b_median_<source>`: the median over the source's trace lenders of b, the lender's notice buffer over its mean slack in the calibration window (a fraction)
- `n_lenders_<source>`: the source's trace lenders with a value of b
- `n_instance_hashes`: the distinct instances that the 15 policies of the fold, arm and cell ran on (1 in every line: all ran on the same instance)

## s1v2_points.csv

Sensitivity of Sublet per setting on weeks 301–304 (the trace lender, policy seed 0): the saving over each setting's all-fallback cost in overflow accounting, the median over the weeks and, for Sublet, its range; the margin, Greedy, back-off or RetroRenting-style, whichever costs less in the week, minus Sublet in percentage points of the all-fallback cost (positive when Sublet costs less), its median and range over the weeks without a missing run, and the weeks in which it is positive (a missing run counts as not); and the price of the guard, Sublet minus critical-ratio renting (median, percentage points). Default: the assumption's default setting; the columns ‘Default at bar end’ and ‘Setting at bar end’ mark with low and high the settings at the ends of the row's bar in the supplement's figure of Sublet's sensitivity (blank: not at an end), the default point being part of every bar. Rows in the order of the figure's panels, each sorted by span. The buffer quantile 0.999 and the rows L-rf and L-vr are the confirmation's runs. Every per-week value is in the data file s1v2_runs.csv.

## s1v2_w0.csv

Worst case of the sensitivity settings on weeks 301–302: W0, the largest cost over the all-fallback cost under the five stress lenders (overflow accounting, policy seed 0), the median over the weeks and, for Sublet, its range, at the load-scenario and transfer-fee settings and at the default point (the confirmation's runs). Weeks: those in which Sublet's W0 is below 1 and below that of Greedy, back-off, RetroRenting-style and CoCaR-style (a missing run counts as not). Every stress lender's cost is in the data file s1v2_runs.csv.

## s1v2_runs.csv

Every per-run value of Sublet's sensitivity, one line per setting, policy, lender, week and metric (overflow accounting, policy seed 0). Columns:
- `part`: sweep, the settings one at a time on weeks 301–304 (r0 under the trace lender or its variant), or w0, the worst case at the load-scenario and transfer-fee settings and the default point on weeks 301–302 (r0 under each stress lender, and W0)
- `setting_id`: the setting's plain identifier (default: the default point; the others name the assumption and its value, such as alpha02, fee16 or scen_cold_wan_1gbps)
- `assumption`: the assumption varied, as LaTeX source (the rows of s1v2_points.csv)
- `setting`: the setting as the supplement's figure of Sublet's sensitivity prints it, as LaTeX source (empty for the default point)
- `policy`: the policy's label (Sublet, critical-ratio renting, Greedy, back-off, RetroRenting-style, and in part w0 CoCaR-style)
- `tag`: the policy's plain identifier in the code
- `lender`: L-tr (the trace lender; at the buffer quantile 0.999, calibrated at that quantile), L-rf (purchases on unavailable layers refused), L-vr (buffer violations as reclaims without notice), a stress lender (L-eg, L-ss, L-iid-0.05, L-iid-0.2, L-co), or ‘max over the five stress lenders’ on the lines of W0
- `week`: the confirmation week (its configuration seed), 301–304
- `policy_seed`: the policy seed (0 in every line)
- `metric`: r0, the cost over the setting's own all-fallback cost, or W0, the largest r0 over the five stress lenders
- `value`: the metric's value (a fraction)
- `source`: this study; or confirmation, part second (the confirmation's runs, reused for the buffer quantile 0.999, L-rf and L-vr), or confirmation, part main (reused for the default point's stress runs)

## e5v2_costs.csv

Redundancy under correlated reclaims per cell on config seeds 301–304: the saving over the all-fallback cost in overflow accounting, the median over the config seeds and, for Sublet, its range. Lender: the trace lender, correlated reclaims within the lenders' groups at psh, or one group of all lenders at psh=1; the stranding runs at μ≠β̃ are the four policies' with the trace lender and the short-notice menu. †: the confirmation's runs, reused. Every run is in the data file e5v2_runs.csv.

## e5v2_margins.csv

Margins of Sublet per cell on config seeds 301–304, in percentage points of the all-fallback cost (overflow accounting): the cost of Greedy, back-off or RetroRenting-style, whichever is lower in the config seed, minus Sublet's, and the same over every baseline of the cell (with SpotHedge-style at NExtra=0 and 2 where they ran), each with its median, range and the config seeds in which it is positive (a missing run counts as not); the spares' effect, SpotHedge-style at NExtra=2 per pool minus at NExtra=0 (negative when the spares save); and the price of the guard, Sublet minus critical-ratio renting (median).

## e5v2_runs.csv

Every run of redundancy with spares, one line per correlation level, menu, μ/β̃, policy and configuration seed (one week each, overflow accounting, policy seed 0). Columns:
- `level`: trace (the trace lender), sh0.25, sh0.5 or sh1 (correlated reclaims: a reclaim is repeated at each other lender of its group with probability psh), or all1 (one group of all lenders at psh=1)
- `p_sh`: psh, the probability of the repeat (empty at level trace)
- `groups`: own (each lender's correlation group) or all (one group of all lenders); empty at level trace
- `menu`: short (spot-like contracts with notice up to 2 min, and the protected contract) or long (notice 60–240 min, and the protected contract)
- `mu_over_beta`: the stranding price μ/β̃ (1, and 0.2, 0.5 and 2 for the stranding runs at level trace with the short menu)
- `policy`: the policy's label (with SpotHedge-style at NExtra=0 and NExtra=2 spares per pool)
- `tag`: the policy's plain identifier in the code
- `config_seed`: the configuration seed, 301–304 (the confirmation's weeks)
- `r0`: the cost over the all-fallback cost (a fraction)
- `saving_pct`: the saving 100(1-r0) (%; negative where the cost exceeds the all-fallback cost)
- `source`: this study, or confirmation, part second (the confirmation's runs, reused)

## e8v2_tiers.csv

The request-level replay per tier and smoothing window over 4 alignments: Ranked, the alignments in which all four of Sublet, critical-ratio renting, RetroRenting-style and Greedy, back-off have a cost, of 4; Same, those in which their order by fluid cost is their order by replayed cost; First, those in which Sublet costs least of the four, in the fluid model (F) and replayed (R); Below, those in which Sublet costs less than both Greedy, back-off and RetroRenting-style; and the relative cost error E=(Creplay-Cfluid)/Creplay in overflow accounting, the median over the alignments and, for Sublet, its range. Two-timescale PD: the earlier replay study's runs. Every cell is in the data file e8v2_cells.csv.

## e8v2_mooncake.csv

The Mooncake conversation hour (tier M, one alignment), replayed through each policy's placements without and with prefix hits: the cost in overflow accounting (USD) in the fluid model and replayed, of Sublet (S), critical-ratio renting (C), Two-timescale PD (P), RetroRenting-style (R) and Greedy, back-off (G); Same: whether the four policies other than Two-timescale PD have the same order by both costs; Sublet's rank among the four, fluid (F) and replayed (R). The fluid run does not depend on the prefix setting.

## e8v2_cells.csv

Every cell of the request-level replay, one line per part, tier, smoothing window, alignment, prefix setting and policy (overflow accounting). Columns:
- `part`: instance (the request-level instance: one borrower's conversation week, the trace lender, policy seed 0) or mooncake (the Mooncake conversation hour, replayed through each policy's placements in the week's hour with the largest fluid overflow)
- `tier`: the LLM's tier, S, M or L (M for mooncake)
- `window_min`: the demand smoothing window (min): 5, 15 or 60
- `alignment`: the alignment, 1–4 (1 for mooncake)
- `prefix_hits`: for mooncake, off (replayed without prefix hits) or on (with them); empty for instance
- `policy`: the policy's label (Sublet, Critical-ratio renting, Two-timescale PD, RetroRenting-style or Greedy, back-off)
- `tag`: the policy's plain identifier in the code
- `c_fluid_usd`: the fluid model's cost (USD; of the week, or for mooncake of the replayed hour, which does not depend on the prefix setting)
- `c_replay_usd`: the replayed cost (USD)
- `error`: E=(Creplay-Cfluid)/Creplay (a fraction)
- `rank_fluid_of_4`: the policy's rank by fluid cost among Sublet, critical-ratio renting, RetroRenting-style and Greedy, back-off (1: cheapest; ties by tag; empty for Two-timescale PD)
- `rank_replay_of_4`: the same by replayed cost
- `rank_fluid_of_5`: the rank by fluid cost among all five policies
- `rank_replay_of_5`: the same by replayed cost
- `same_order_of_4`: true where the four policies' orders by fluid and by replayed cost agree (per cell)
- `source`: this study, or the earlier replay study's stored runs (Two-timescale PD, read from the earlier request-level replay study on the same instance)

## e9v2_overhead.csv

The scaling study per point, each job alone on the host, over 4 alignments of a day: the act time per slow-loop slot (ms) of Sublet and of critical-ratio renting, its inner policy, with the median and range over the alignments; the guard's overhead, Sublet's time minus critical-ratio renting's in the same alignment (median, range), and their ratio (median); the wall time of the slow and fast loops per simulated hour (s) and the peak memory (MB) of each, medians. A slow-loop slot is 300 s. Every run is in the data file e9v2_runs.csv. The first four columns identify the point: Menu, full (20 revocable contracts and the protected contract) or reduced (3 revocable contracts and the protected contract); V, the most layers that each trace lender offers the platform, Vℓ (default 8; the supplement's grids name its values); LLMs, the tiers served; Sites × LLMs, the instance's sites times its LLMs.

## e9v2_split.csv

The guard's time per slow-loop slot by part (mean, ms), from one instrumented run of Sublet per point (alignment), used where the run equals the uninstrumented one bit for bit (Equal): Sublet's act time, its inner policy's, the guard's (the difference), and the guard's parts: the safe expert's step, the online lower bound, the guard's test (the update of its bound and the slot's first evaluation), the projection (the candidates and the later evaluations) and the rest. The first four columns identify the point: Menu, full (20 revocable contracts and the protected contract) or reduced (3 revocable contracts and the protected contract); V, the most layers that each trace lender offers the platform, Vℓ (default 8; the supplement's grids name its values); LLMs, the tiers served; Sites × LLMs, the instance's sites times its LLMs.

## e9v2_runs.csv

Every timed run of the scaling study, one line per point, policy and alignment (one day, each job alone on the host, policy seed 0). Columns:
- `point`: the point's plain identifier, `<instance>_V<V>_<LLMs>` (e7f: the full menu, e7r: the reduced menu)
- `menu`: full (20 revocable contracts and the protected contract) or reduced (3 revocable contracts and the protected contract)
- `V`: the most layers that each trace lender offers the platform, Vℓ (1, 2, 4, 8, 16, 32 or 64; default 8)
- `llm_set`: the LLM tiers served: SML (S, M and L), ML (M and L) or S
- `sites_x_llms`: the instance's sites times its LLMs
- `policy`: the policy's label (Sublet or Critical-ratio renting)
- `tag`: the policy's plain identifier in the code
- `alignment`: the alignment, 1–4 (the configuration and lender seed)
- `act_s_per_slot`: the mean wall time of the policy's decision per slow-loop slot of 300 s (s)
- `slow_step_s_per_slot`: the mean wall time of the engine's whole slow step per slot (s)
- `slow_loop_s_per_h`: the wall time of the slow loop per simulated hour (s)
- `fast_loop_s_per_h`: the same for the one-minute routing loop, its checks included (s)
- `loops_s_per_h`: their sum (s)
- `peak_rss_mb`: the job's peak resident memory (MB)
- `projected_slots`: the slots in which Sublet's guard ran a projected action list (empty for critical-ratio renting)
- `split_identical`: true where the instrumented run of Sublet equals the uninstrumented one bit for bit; set on Sublet's line of alignment 1 of each point only
- `split_<part>_s_per_slot`: on those lines, the instrumented run's mean time per slow-loop slot (s) of the part act (Sublet's decision), inner_act (critical-ratio renting's inside it), guard (act minus inner_act), safe (the safe expert's step), lb (the online lower bound), test (the guard's bound update and the slot's first evaluation), projection (the candidates and the later evaluations) or other (the rest of the guard)

## e7r_tags.csv

Every policy of the baseline study on weeks 301–316 (16 weeks, policy seed 0): r0 under the trace lender L-tr, W0 (the largest r0 over the five stress lenders of the confirmation), W0+ (over these and the six new ones) and the revocation cost RC under L-tr; median and, in parentheses, min–max over the weeks. The rows hold, in this order, the confirmation's policies, the transplants of the k̄ contract, protected-only renting, the spare variants, MPC at its tuned settings, the settings of rule T, the settings of rule W and the lookahead reference. The confirmation's policies take their runs under its seven lenders from the confirmation. MPC with the oracle forecast, at MPC's as-built setting, ran under L-tr and L-hon only. The runs repeated at this study's code version equal the confirmation's in 18 of 18 pairs of policies with the same rule and settings (576 shared runs; largest difference 0). Protected-only renting holds no revocable lease: its r0 is the same under all 13 lenders in every week. Same setting as rule T: yes where the setting of rule W equals that of rule T (Per-borrower ski rental, tuned (worst case); and MPC, tuned (worst case)); each of these settings ran once. Every run is in the data file baseline_study_runs.csv.

## e7r_margins.csv

Sublet's margin over every policy of the baseline study and over the best member of each comparison set on weeks 301–316 (16 weeks): a policy's value minus Sublet's in the same week (positive: Sublet costs less), on r0 under L-tr, W0 and W0+; weeks won, tied and lost (W/T/L; +m: m weeks without a run, counted as losses), median and min–max over the weeks with a value. The rows hold, in this order, the confirmation's policies, the transplants of the k̄ contract, protected-only renting, the spare variants, MPC at its tuned settings, the settings of rule T, the settings of rule W and the lookahead reference, and the best members of the comparison sets. The best member of a set is, per week and metric, its member of least value (number of distinct settings in parentheses); the sets are the primary baselines as built, the notice-aware policies, the transplants of the k̄ contract, the spare variants, the settings of rules T and W, and all baselines, these sets together with protected-only renting (no set holds Critical-ratio renting; Critical-ratio planning; Critical-ratio renting, k* contract; and MPC, oracle forecast). MPC with the oracle forecast, at MPC's as-built setting, ran under L-tr and L-hon only (not run: W0 and W0+ need the stress lenders).

## e7r_grid.csv

The tuned settings: the 68 configurations of the tuning grids, each family's numbered in grid order from the as-built one, with the median r0 under L-tr and the median W0 over the tuning weeks 113–116 (policy seed 0) and whether every run of the configuration is there (eligible); rule T selects the eligible configuration of least median r0, ties by grid order, and rule W the one of least median W0, ties by the median r0, then grid order. The as-built and the selected configurations ran again on the confirmation weeks 121–124, with their medians there: T holds where its median r0 is at most the as-built setting's, W where its median W0 is. The selection program was registered with the analysis before the runs. The evaluation and confirmation parts recorded the selection that the analysis read (the same file), and the three parts ran at one code version.

## e7r_modes.csv

Every policy of the baseline study under every lender on weeks 301–316 (16 weeks, policy seed 0): the median of r0 over the weeks and its min–max, in the columns `<lender> median` and `<lender> min–max`, under the trace lender L-tr, the honoring lender L-hon, the stress lenders of the confirmation, the i.i.d. lenders by their reclaim probability p per site and slot (the new rates and the confirmation's 0.05 and 0.2), the regional correlated lender by its spreading probability, and the peak-aligned trace lender (peak). The rows hold, in this order, the confirmation's policies, the transplants of the k̄ contract, protected-only renting, the spare variants, MPC at its tuned settings, the settings of rule T, the settings of rule W and the lookahead reference. The confirmation's policies take their runs under its seven lenders from the confirmation; MPC with the oracle forecast, at MPC's as-built setting, ran under L-tr and L-hon only (–: not run). Every run is in the data file baseline_study_runs.csv. Same runs as: for the settings of rule W that equal those of rule T, the row whose runs they share (each of these settings ran once); the row's other cells are blank.

## e7r_stress.csv

The stress regimes per policy on weeks 301–316 (16 weeks): the number of weeks whose least reclaim probability p of the i.i.d. lender with r0>1 is each p of the grid (p=0: the honoring lender; blank: none), or that have r0≤1 at every p (column ‘Weeks with r0≤1 at every p’), and the lenders at which W0+, the largest r0 over the eleven stress lenders, is reached, with their numbers of weeks, separated by semicolons (ties to the first of L-eg, L-ss, L-iid-0.05, L-iid-0.2, L-co and the new lenders). MPC, oracle forecast was not run under the i.i.d. lenders (–). The rows hold, in this order, the confirmation's policies, the transplants of the k̄ contract, protected-only renting, the spare variants, MPC at its tuned settings, the settings of rule T, the settings of rule W and the lookahead reference. The adaptive lender L-ad of Theorem 2(a) of the main text enters W0+ through its equivalence with the eager lender L-eg: on the confirmation's 48 paired runs their r0 are equal.

## baseline_study_runs.csv

Every run of the baseline study with a value, one line per part, policy, lender and week (overflow accounting, policy seed 0). Columns:
- `part`: eval (weeks 301–316 under the 13 lenders), tune (the tuning grids on weeks 113–116 under L-tr and the five stress lenders) or confirm (the as-built and selected settings again on weeks 121–124 under the same lenders)
- `policy`: the policy's label (in part tune `<family>, setting n`, n the configuration's number in its grid, 1 the as-built setting, as in e7r_grid.csv)
- `tag`: the policy's plain identifier in the code; the suffix -c2 marks the transplant of the k̄ contract, -T and -W the settings that rules T and W select, -gNN a configuration of a tuning grid; MPC-oracle is MPC with the oracle forecast
- `lender`: L-tr, L-hon, L-eg, L-ss, L-co, L-iid-p (the i.i.d. lender at the reclaim probability p per site and slot), regional 0.5 and regional 1 (the regional correlated lender at the spreading probability 0.5 or 1) or peak-aligned (the trace lender with each lender's daily slack minimum moved to its region's borrower peak)
- `week`: the week (its configuration seed)
- `policy_seed`: the policy seed (0 in every line)
- `r0`: the cost over the week's all-fallback cost
- `rc`: RC, r0 minus r0 under L-hon for the same policy and week (part eval only; empty under L-hon and in parts tune and confirm, which have no L-hon run)
- `source`: confirmation (the run is the confirmation's: its policies under its seven lenders) or this study

## e8q_costs.csv

The request-level replay with a queue per waiting limit W and tier (each tier over its 3 smoothing windows and 4 alignments; All: every cell): Cells, the cells; each policy's replayed cost over the replayed all-fallback cost at the same W (%), the median over the cells, of Sublet (S); critical-ratio renting (C); RetroRenting-style (R); Greedy, back-off (G); the relative cost error of the fluid model E=(Creplay-Cfluid)/Creplay (%), the median, and that of the all-fallback cost itself (B, no policy); the median of |E|; Margin, the replayed cost of the cheaper of RetroRenting-style and Greedy, back-off minus Sublet's, in percentage points of the all-fallback cost, the median (positive where Sublet costs less); Below, the cells in which Sublet costs less than both, of all the cells (a cell without one of the three runs or the all-fallback run counts as not below); Same, the cells in which the fluid and replayed orders of the four policies agree. Costs in overflow accounting (as in the earlier replay study). Every cell is in the data file e8q_cells.csv.

## e8q_latency_table.csv

Latency of the request-level replay per tier (pooled over its smoothing windows and alignments) and policy, at W=2.5 s per minute class (the minutes in which a lease of the policy is reclaimed, a replica loads, the fluid model sends demand beyond the borrower's own capacity to the platform, or none of these; all: every minute) and, for comparison, at W=0 over every minute: Sublet (S); critical-ratio renting (C); RetroRenting-style (R); Greedy, back-off (G); the all-fallback cost (B: own capacity, then fallback, with the same queue). Slots, the minutes; Copies, the request copies (millions); Fallback, the share (%) of copies served by fallback (at once, after waiting W, or at the end of the horizon); Waited, the share (%) served by a replica after waiting; Interrupted, the share (%) stranded by a reclaim; the time to first token (s) at the percentiles 50, 99 and 99.9 and the attainment of the tier's TTFT objective (S 0.25 s, M 2.5 s, L 4 s; %) for each fallback latency Dfb. A percentile in the last bin of the histogram is printed as a bound at that bin's edge. Classes without copies are left out; every W and class is in the data file e8q_latency.csv. In this file Fallback, Waited, Interrupted and SLO are percentages; in e8q_latency.csv the shares are fractions.

## e8q_latency.csv

Latency of the request-level replay with a queue, one line per tier (S, M, L; pooled over its smoothing windows and alignments), policy (Sublet, critical-ratio renting, RetroRenting-style, Greedy, back-off, and the all-fallback bill: own capacity, then fallback, with the same queue), waiting limit W and minute class: tier, policy, tag (the policy's name in the code), wait_s (W, s: 0, 1, 2.5 or 10), window_class (reclaim: a lease of the policy that carries the LLM is reclaimed; load: a replica of the LLM loads; overflow: the fluid model sends demand beyond the borrower's own capacity to the platform; base: none of these; all: every minute), slots (the minutes), copies (the request copies), fallback_share and fallback_token_share (the shares of copies and of tokens served by fallback: at once, after waiting W, or at the end of the horizon), reneged_share (the share that fell back after waiting W), waited_share (the share served by a replica after waiting), mean_wait_of_waited_s (their mean wait, s), interrupted_share (the share stranded by a reclaim), `p50_s_dfb_<D>`, `p99_s_dfb_<D>` and `p999_s_dfb_<D>` (the time to first token, s, at the percentiles 50, 99 and 99.9, for the fallback latency D = 0.5, 1 and 2 s), `slo_attainment_dfb_<D>` (the share of copies within the tier's TTFT objective), slo_s (that objective, s: S 0.25, M 2.5, L 4) and percentiles_in_last_bin (the percentiles that fall in the last bin of the histogram, a bound at its edge; empty: none). Shares are fractions; an empty cell: no copy in the class (in mean_wait_of_waited_s, none that waited). The data file e8q_latency_table.csv gives the shares and percentiles at W=2.5 s per minute class and at W=0 over every minute.

## e8q_decomp.csv

Why the fluid model's error depends on the policy: per waiting limit W and policy, the medians over the cells of the gap between the replayed and the fluid cost (USD) split into the replayed fallback in minutes in which the fluid demand is zero (Zero), the replayed fallback in minutes with demand minus the fluid fallback (Overflow), the replayed minus the fluid stranding and routing; the gap (USD and % of the replayed all-fallback cost), E (%), the lease spend (lease and loading, USD), the share of all minutes and of the minutes with demand in which the warm capacity exceeds the demand (Headroom, %), and the zero-demand fallback's share of a positive gap (%). Per cell the four parts add up to the gap (largest residual 2×10^-11 USD); the medians need not. Every cell is in the data file e8q_cells.csv.

## e8q_cells.csv

Every cell of the request-level replay with a queue, one line per tier, smoothing window, alignment, waiting limit W and policy, with one line for the all-fallback bill (overflow accounting; shares and E as fractions). Columns:
- `tier`: the LLM's tier, S, M or L
- `window_min`: the demand smoothing window (min): 5, 15 or 60
- `alignment`: the alignment, 1–4 (the configuration, lender and request-copy seed)
- `wait_s`: W (s): 0, 1, 2.5 or 10; a request copy that finds no free replica waits up to W in one FIFO queue before it falls back (W=0: the replay without a queue)
- `policy`: the policy's label (Sublet, Critical-ratio renting, RetroRenting-style, Greedy, back-off, or All-fallback bill)
- `tag`: the policy's plain identifier in the code (BL0a: the all-fallback bill)
- `c_fluid_usd`: the fluid model's cost of the week (USD; it does not depend on W)
- `c_replay_usd`: the replayed cost at W (USD): the fluid run's lease and loading spend plus the replay's routing, fallback and stranding
- `bill_replay_usd`: the replayed all-fallback cost of the cell at the same W (USD)
- `cost_over_bill`: c_replay_usd over bill_replay_usd (1 on the bill's lines)
- `error`: E=(Creplay-Cfluid)/Creplay
- `gap_usd`: Creplay-Cfluid (USD), which the next five columns split
- `fallback_zero_demand_usd`: the replayed fallback in minutes with zero fluid demand (USD)
- `fallback_overflow_usd`: the replayed fallback in minutes with demand minus the fluid fallback (USD)
- `stranding_usd`: the replayed minus the fluid stranding (USD)
- `routing_usd`: the replayed minus the fluid routing (USD)
- `residual_usd`: the gap minus the four parts (USD; round-off)
- `lease_usd`: the fluid run's lease and loading spend (USD)
- `headroom_all`: the share of the week's minutes in which the warm replica capacity exceeds the fluid demand
- `headroom_positive_demand`: the same share over the minutes with demand
- `delta_over_bill`: the cell's margin: the cost over the bill of the cheaper of RetroRenting-style and Greedy, back-off minus Sublet's (a fraction of the bill)
- `sublet_below_both`: true where Sublet's replayed cost is below both of theirs (per cell)
- `same_order_of_4`: true where the four policies' orders by fluid and by replayed cost agree (per cell)
- `rank_fluid_of_4`: the policy's rank among the four by fluid cost (1: cheapest; ties by tag)
- `rank_replay_of_4`: the same by replayed cost at W
On the bill's lines the four parts, the residual, the lease spend, the headroom shares, the margin, the flags and the ranks are empty.

## cap_costs.csv

The naive spend caps on weeks 301–316 (16 weeks, policy seed 0) beside Sublet and the references: the median and, in parentheses, min–max over the weeks of r0 under the trace lender L-tr, of W0 (the largest r0 over the five stress lenders) and of W0+ (over the eleven lenders of the stress and new modes); the runs above the bound CFB(T)+B(T) out of the runs over all 13 lenders; and the largest final excess (ALG(T)-CFB(T)-B(T))/CFB(T) and run-time excess maxt(ALG(t)-CFB(t)-B(t))/CFB(T) over the runs with a value, with (n/N) where only n of the N runs have one. †For the runs read from the earlier studies, the run-time value of a guarded run is the guard's envelope, an upper bound on the run-time excess when the safe expert followed all-fallback; their unguarded runs have none. The rows hold, in this order, Sublet, the caps and the references. Every run is in the data file cap_runs.csv.

## cap_margins.csv

The caps' paired margins on weeks 301–316: a cap's value minus the reference's in the same week (positive: the reference costs less), the reference (column Reference) being Sublet and, for the greedy caps, also Greedy + guard, the same guard around greedy renting, on r0 under L-tr, W0 and W0+: weeks won by the reference (the reference costs less), tied and lost (W/T/L), with +m for the m weeks in which the cap or the reference has no run, counted as the reference's losses; median and min–max over the weeks with a value. Kept: the median over all runs of the share of the inner policy's saving (1-r0)/(1-r0^inner) that the cap keeps (by lender class in the data file cap_binds.csv). Cheaper: the runs, over all lenders, in which the cap's r0 is below Sublet's.

## cap_binds.csv

The caps' binds and the saving they keep (policy seed 0), on the confirmation weeks and at each sensitivity point (column Point): the runs; the slots at which the cap bound, median and min–max over the runs (Binds median, Binds min–max; a blank min–max: the minimum equals the maximum as printed); the runs in which the latched cap latched; and the share of the inner policy's saving (1-r0)/(1-r0^inner) that the cap keeps (critical-ratio renting for the critical-ratio caps, greedy renting for the greedy caps), median and min–max over the runs (Kept `<class>` median and min–max, a blank min–max as above) under the trace lender L-tr, the five stress lenders, the other lenders and all lenders, over the runs in which the inner policy saved something; No saving: the runs in which it saved nothing (r0^inner≥1).

## cap_modes.csv

Every policy of the spend-cap runs under every lender on weeks 301–316 (16 weeks, policy seed 0): the median of r0 over the weeks and its min–max, in the columns `<lender> median` and `<lender> min–max` (–: no run), under the trace lender L-tr, the honoring lender L-hon, the stress lenders of the confirmation, the i.i.d. lenders by their reclaim probability p per site and slot, the regional correlated lender by its spreading probability, and the peak-aligned trace lender (peak). The rows hold Sublet, the caps and the references, in this order; CR: critical-ratio renting; GR: greedy renting. Every run is in the data file cap_runs.csv.

## cap_mode_margins.csv

The caps' paired margins on r0 per lender on weeks 301–316 (the lenders of the data file cap_modes.csv): a cap's r0 minus that of the Reference, Sublet or Greedy + guard, in the same week (positive: the reference costs less); in the column `<lender> W/T/L` the weeks won by the reference (the reference costs less), tied and lost (W/T/L), with +m for the m weeks in which the cap or the reference has no run, counted as the reference's losses, and in the column `<lender> median` the median over the weeks with a value; CR: critical-ratio renting; GR: greedy renting.

## cap_sens.csv

The caps at the sensitivity points (policy seed 0): per point and policy, the median and min–max of r0 under L-tr over the point's trace weeks and of W0 over its weeks with stress runs (weeks 301–304 and 301–302 at every point, column Point), the runs above the bound out of the runs, the largest final and run-time excess over CFB(T) (as in the data file cap_costs.csv), and a cap's margin against the reference in column Reference (Sublet, and for a greedy cap also, in a row of its own, Greedy + guard, the same guard around greedy renting): weeks won by the reference (the reference costs less), tied and lost (W/T/L), with +m for the m weeks in which the cap or the reference has no run, counted as the reference's losses on r0 under L-tr (with the median margin) and on W0. †: for the runs read from the earlier studies, the run-time value of a guarded run is the guard's envelope, an upper bound on the run-time excess when the safe expert followed all-fallback (as in the data file cap_costs.csv).

## cap_runs.csv

Every run record of the spend caps, one line per part, point, lender, week and policy (overflow accounting, policy seed 0). Columns:
- `part`: week (weeks 301–316 under the 13 lenders) or sens (the sensitivity points: L-tr on weeks 301–304, the five stress lenders on weeks 301–302)
- `point`: default (part week) or the sensitivity point: fee4, fee8 or fee16 (the transfer fee ρ=4, 8 or 16), slow1 (a slow-loop slot of 1 min) or scen_cold_wan_1gbps (cold loads over a WAN of 1 Gb/s)
- `lender`: L-tr, L-hon, L-eg, L-ss, L-co, L-iid-p (the i.i.d. lender at the reclaim probability p per site and slot), regional 0.5 and regional 1 (the regional correlated lender at the spreading probability 0.5 or 1) or peak-aligned (the trace lender with each lender's daily slack minimum moved to its region's borrower peak)
- `week`: the week (its configuration seed)
- `policy`: the policy's label
- `tag`: the policy's plain identifier in the code: the caps CR-cap-B, CR-cap-0, CR-cap-5, CR-cap-B-latch and CR-cap-B-slot (critical-ratio renting with the cap at B(t), at 0, at 5% of the fallback cost so far, latched, and with the slot's purchases and rent priced), GR-cap-B and GR-cap-0 (greedy renting with the cap at B(t) or 0), and the references Sublet, A9 (critical-ratio renting), BL1 (greedy renting) and BL1-GP (Greedy + guard)
- `source`: e7b (this study's runs), or the earlier runs it reads: main (the confirmation's), eval (the baseline study's, under its six new lenders), sweep and w0 (Sublet's sensitivity runs under L-tr and under the stress lenders)
- `policy_seed`: the policy seed (0 in every line)
- `r0`: alg_usd over fb_usd
- `alg_usd`: ALG(T), the run's cost over the week (USD)
- `fb_usd`: CFB(T), the week's all-fallback cost (USD)
- `b_usd`: B(T), Sublet's allowance at the horizon (USD; it depends on the instance only)
- `final_excess_usd`: ALG(T)-CFB(T)-B(T) (USD; negative: below the bound)
- `final_excess_rel`: the same over CFB(T)
- `above`: true where the final excess exceeds the numerical tolerance
- `runtime_source`: series (the run-time excess from the run's per-slot series), envelope (for a guarded run read from the earlier studies, the guard's envelope, an upper bound on the run-time excess when the safe expert followed all-fallback) or empty (an unguarded run read from the earlier studies: no run-time value)
- `runtime_excess_usd`: maxt(ALG(t)-CFB(t)-B(t)) (USD; empty as above)
- `runtime_excess_rel`: the same over CFB(T)
- `runtime_above`: true where some slot exceeds the bound (for envelope, where the envelope is violated; empty as above)
- `cap_bind_slots`: the slow-loop slots at which the cap bound (empty for the references)
- `cap_first_bind`: the first of them, a 0-based slot index (empty where the cap never bound)
- `cap_latch_slot`: the slot at which the latched cap latched (CR-cap-B-latch only; empty where it never bound)
- `r3_cell`: true where the run is a cap whose r0 is below Sublet's in the same part, point, lender and week (the cheaper runs of cap_margins.csv)
