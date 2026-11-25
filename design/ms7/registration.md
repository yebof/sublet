# Registration of the further runs X1-X5

*Public copy: process notes and references to internal design documents were removed; every registered rule, parameter, cell and hash is unchanged from the version frozen at the registration commit. (The frozen version, the file at the run commit `44d1b4e4` of the development repository, has sha256 `163ff03578ced770f5ded225c058281e32093b613cf2aed29b6e40b6ef094ec8`, which the summaries and manifests in `code/sim/out/e7c/`, `e7o/`, `e7r/`, `s1v2/`, `e5v2/`, `e8v2/` and `e9v2/` carry as `registration_sha256`; it therefore differs from this file, and the five `_sha256` lines of §1 are identical in both. The frozen version ends with the heading and first paragraph of §6; the dated entries of §6 were appended after the run commit, during and after the runs, as that paragraph provides.)*

*Registered on 2026-11-08, before any full run. The commit that merges this file into `main` is the **run commit**. Every part below runs once, in a clean clone of the run commit, and its outputs are copied into `code/sim/out/` with a copy check (`python -m sublet.experiments.ms3_common --check-copy <exp> <clone>`), as for the confirmation of `design/sublet_v2_prereg.md`. These runs are exploratory: they come after the confirmation's freeze (`eb76b160`, `design/sublet_v2_prereg.md`) and change neither its hypotheses, nor its analysis `ms5b_analysis.py`, nor its outcomes. What makes them pre-specified is this file: each analysis script is fixed by its sha256 below, and every full part refuses to start unless this file exists at HEAD, the working tree is clean, and the script on disk and at HEAD has the registered sha256. Reduced (smoke) runs on development cells record the gate without enforcing it; they are not results.*

## 1. Frozen scripts

The drivers read these lines (each at the start of a line, `<name>_sha256: <64 hex>`):

```
e7c_analysis_sha256: 47637395ca47519982603a180c4b54f9fe5ad036b58917de69ae9630216c9f04
e7r_select_sha256: 44dca0ba8ea5e1882c9f69dac6056783228db5362d46ec7484704f888ec2b7da
e7r_analysis_sha256: 1f1dbf42d2ab74fc85aa5763802e2c7fa2c814f0db8b690a67ad4d9ab69f3fbb
e7o_analysis_sha256: 94432921674bcec43df2b8df16c8086c71755a4a251ad51b4baa0cbf29e2398b
ms7_sens_analysis_sha256: 6d9772304fe30b20d0d500c2c56b867ccecc97dc99e672c63bdfcd66912e4a2d
```

| Line | Script (under `code/sim/sublet/experiments/`) | Read by |
|---|---|---|
| `e7c_analysis_sha256` | `e7c_analysis.py` | `e7c.py` (X1) |
| `e7r_select_sha256` | `e7r_select.py`, the tuning selection | `e7r.py` (X4, X5) |
| `e7r_analysis_sha256` | `e7r_analysis.py` | `e7r.py` |
| `e7o_analysis_sha256` | `e7o_analysis.py` | `e7o.py` (X2) |
| `ms7_sens_analysis_sha256` | `ms7_sens_analysis.py` | `s1v2.py`, `e5v2.py`, `e8v2.py`, `e9v2.py` (X3) |

The drivers, policies, baselines and options these runs use are those of the run commit, with their tests there. Every option added for these runs defaults to the frozen behaviour; the frozen run digests that those tests pin are reproduced at the run commit by the quick suite (§5).

## 2. What runs

| Exp. | Driver, parts | Cells | Policies | Lender modes | Jobs |
|---|---|---|---|---|---|
| X1, causal demand | `e7c.py`: `gate`, then `lag` | `gate`: weeks 301-302 (7 modes) and 301-304 (L-tr); `lag`: the 16 confirmation weeks 301-316 | `gate`: BL1, BL2, BL3-0, BL4, BL5, A9 at their defaults and the three lagged tags of part second; `lag`: 11 lagged tags (`e7c_tags.py`) | the confirmation's 7 | 24; 176 |
| X2, out of sample | `e7o.py`: `fwd`, then `rev` | 16 cells per fold (config seeds 301-316, held-out WildChat weeks 37-72, held-out BurstGPT weeks), arms `oos` and `is` | 15 tags: Sublet, A9, the seven primary baselines, the four notice-aware baselines, CR and A9-kstar | L-tr, L-vr, the five stress modes, L-hon | 480 per fold |
| X4, X5, baselines and stress regimes | `e7r.py`: `tune`, `confirm`, `eval` | `tune`: development weeks 113-116; `confirm`: 121-124; `eval`: 301-316 | the c2 transplants, A9-P, the spares tags of BL3, MPC (with the oracle forecast as a labeled reference), the tuned settings (rules T and W of `e7r_select.py` over 68 configurations), and the confirmation's 15 tags under the new modes and L-tr | the confirmation's 7 and L-iid-0.0005, L-iid-0.002, L-iid-0.0124, L-co-reg-0.5, L-co-reg-1, L-pk (constructed) | 272; 48-72; 512-608 |
| X3, Sublet's sensitivity and fidelity | `s1v2.py` (`sweep`, `w0`), `e5v2.py`, `e8v2.py` (part a), `e9v2.py` | weeks 301-304 (W0 on 301-302), E5 seeds 301-304, E8 and E9 alignments 1-4 | Sublet, A9, BL1-BO, BL5-cur (S1 v2, E8 v2, with BL4 in `w0`); with BL3-0 and BL3-2 (E5 v2); Sublet and A9 (E9 v2) | L-tr (S1 v2 sweep, E5 v2, E8 v2, E9 v2); the five stress modes (`w0`) | 250; 96; 43; 144 |

No parameter of a policy is chosen on the weeks 301-316: the tuned settings are selected on weeks 113-116 by the frozen `e7r_select.py` and confirmed on 121-124, and every other setting is the as-built one. Weeks 113-116 and 121-124 were never used in the development, pilot or confirmation runs of Sublet v2. No arm has lookahead except the oracle MPC, a labeled reference that no comparison set contains.

## 3. What each analysis reports

All analyses report sign counts, medians and min-max over weeks or cells; none prints a p-value (the weeks are rotations of one series). Margins follow the confirmation's convention (`ms5b_common.paired_margins`): baseline minus Sublet, positive when Sublet costs less, with a missing run counted as a loss. Every tag, mode and cell is reported in full in the supplement, whatever the sign.

- **X1** (`e7c_analysis.py`): per week and median, the lagged L-tr r0, W0 and RC; the cheapest lagged primary baseline minus Sublet-lag per week, on r0 and W0, with wins, ties, losses and min-max; the same against the notice-aware lagged set; lagged minus revealed per policy; Sublet-lag's projected slots and aborts; the identity r0(Sublet-lag) = r0(A9-lag) in runs without projection; the gate's identities with the confirmation (part `lag` needs a passed `gate` at the same commit).
- **X2** (`e7o_analysis.py`): per fold and cell, r0, W0, RC and the lender-source counts; OOS minus IS per tag; Sublet minus the cheapest primary baseline per cell; the confirmation's H1, H2 and H2b rules applied to the cells descriptively, with the thresholds of `ms5b_analysis.py`.
- **X4, X5** (`e7r_analysis.py`): per week and median, r0, W0, W0+ and RC; margins against each tag, as built against c2, against the best member of each comparison set (as built, notice-aware, c2, spares, tuned T, tuned W, all online) and against the tuned settings; the i.i.d. intensity curve at p in {0, 0.0005, 0.002, 0.0124, 0.05, 0.2}; the confirmation of the tuned settings on weeks 121-124; the identity of the confirmation tags' L-tr runs with part main, A9-P's lender invariance, the L-ad/L-eg equivalence and the provenance of the selection.
- **X3** (`ms7_sens_analysis.py`): S1 v2's savings, Delta = min(BL1-BO, BL5-cur) - Sublet in r0, the weeks in which the ordering holds, Sublet - A9, the row spans, W0 against {BL1-BO, BL5-cur, BL4} and the seed spread from the confirmation; E5 v2 per (level, menu, mu), with BL3-2 - BL3-0; E8 v2's fluid and replayed costs and rankings; E9 v2's per-slot overhead of the guard (Sublet - A9) and its split; each with a headline block and the provenance of its inputs (`registered_full_inputs`).

## 4. Order and host

From `code/sim` in the clean clone of the run commit:

1. `E7C_PART=gate sublet/experiments/run_e7c.sh`, then `E7C_PART=lag sublet/experiments/run_e7c.sh`;
2. in parallel with 1: `E7O_PART=fwd sublet/experiments/run_e7o.sh`, then `E7O_PART=rev`;
3. in parallel with 1 and 2: `E7R_PART=tune sublet/experiments/run_e7r.sh`, then `confirm`, then `eval`;
4. after 1: `S1V2_PART="sweep w0" sublet/experiments/run_s1v2.sh`, `sublet/experiments/run_e5v2.sh`, `sublet/experiments/run_e8v2.sh`, then `python -m sublet.experiments.ms7_sens_analysis --exp s1v2 e5v2 e8v2`;
5. last and alone on the host: `sublet/experiments/run_e9v2.sh`, then `python -m sublet.experiments.ms7_sens_analysis --exp e9v2`.

Every job runs in its own 3 GB scope. The host-wide semaphore of `ms3_lib.sh` runs at most `MS3_HOST_SLOTS` jobs at once (1-6, default 4; these runs use 6, the host's physical cores, set identically for every run script). The value sets only how many jobs run at once: a run's ledger does not depend on it, and E9 v2's timed jobs take every slot.

## 5. Checks at the run commit

Before the runs, the quick suite runs in a clean clone of the run commit (`code/sim/out/tests/`), with the frozen run digests of `test_ms7_lag.py`, `test_ms7_baselines.py` and `test_ms5b_additions.py` and the gate tests of every driver. After the runs, the copy check of each experiment, each analysis's own record of its sha256 against this file, and the identity rows of §3 are reported with the results.

## 6. Deviations

Any departure from this file during the runs is appended here, dated, below this line, with its reason; the sections above are not edited after the run commit.

*2026-11-09, run order (§4).* The runs started in §4's order with 6 host slots. The semaphore of `ms3_lib.sh` gives a freed slot to whichever waiting launch polls first, and a run script launches its next job as soon as one of its own ends, so a script that already holds slots keeps them and a script that starts later waits until an earlier one ends; part `lag` of X1 started no job in 1.5 h. At 00:48 the main shells of `run_e7o.sh` and `run_e7r.sh` were stopped by PID (their running jobs finished and were recorded), and the parts run one script at a time in this priority: X1 (`gate` done, then `lag`), X2 (`fwd`, `rev`, resumed with `MS3_RESUME=1`, which skips every job whose record is ok), X3 (S1 v2, E5 v2, E8 v2), X4 and X5 (`tune`, `confirm`, `eval`, resumed), then E9 v2 alone. Only the order and timing change; every job runs the same code at the run commit, and a run's ledger does not depend on when it runs.

*2026-11-09, wall limit of the e7r jobs.* Four jobs of part `tune` (RetroRenting-style's grid configurations 1, 3, 5 and 7 on week 113, those that re-fetch at once after a reclaim) ran more than 5.3 h each against their estimate of 100 s (`est_s` of the part's manifest, from `ms7_baselines.EST_RUN_S`): one run under L-eg took about 2,900 s, where the same configuration with re-fetch by the rule took 13 s, and the next stress run did not end in 4.5 h. No other finished job of these runs had taken more than 3.4 times its estimate. From 05:45 every e7r job that runs longer than ten times its estimate is stopped by PID (SIGTERM) by a watchdog outside the clone, and `ms3_lib.sh` records it failed (exit 143); its rerun under the missing-run rule has the same limit. The four jobs were stopped at once. By the missing-run rule of the frozen `e7r_select.py` a configuration with a failed run is ineligible, so rules T and W select among the configurations whose runs finish; the stopped jobs are listed with the tuning grid in the supplement. On week 113 the four configurations cost more than their twins with re-fetch by the rule under L-tr ($r_0$ 0.709 and 0.787 against 0.669 and 0.744) and under L-eg (10.09 against 1.35 and 1.26), so neither rule would have selected them there. The analysis scripts, the grids, the rules and every other job are unchanged. The watchdog's log of every stop is copied in with the e7r outputs.

*2026-11-10, the e7r runs and the watchdog's stops.* Parts `tune` (272 jobs), `confirm` (64) and `eval` (576) ended on 2026-11-10 at 20:06; the frozen `e7r_select.py` and `e7r_analysis.py` (sha256 as registered) wrote `tune/selection.json` and `analysis.json`. The watchdog of the deviation above stopped 37 job runs, all in part `tune`: RetroRenting-style's configurations 1, 3, 5 and 7 (re-fetch at once) on each of the weeks 113-116, on the run and on its rerun under the missing-run rule (16 jobs, recorded failed; on week 113 also once in the first launch, before the reorder), and configuration 13 on week 113 once (stopped at 1,020 s; its rerun ended ok in 927 s). No job of `confirm` or `eval` was stopped, and every one ended ok. By the frozen missing-run rule the four configurations are ineligible, so rules T and W chose among 14 of RetroRenting-style's 18 configurations. The watchdog's log of every stop and the script are copied in as `code/sim/out/ms7/e7r_watchdog.log` and `e7r_watchdog.py` (the log is not part of this public copy). The copy check of `out/e7r/` reads the revision of a retried job's first record from its retry wrapper (`ms3_common.py`; before this change, the check counted the 17 wrappers as files without a revision).

*2026-11-11, E9 v2 and the host load.* `run_e9v2.sh` (144 jobs, each alone and holding every host slot) ran from 2026-11-10 20:06 to 2026-11-11 05:02 after every other run of this registration had ended, and `ms7_sens_analysis.py --exp e9v2` (sha256 as registered) wrote `analysis.json`; every job ended ok and the check of each split run's ledger against its unsplit run passed. No other simulator job ran beside it, but light editing, build and test work in another checkout did at times: the 1-min load average at a job's start was 1.02-3.86 (median 1.45; the job itself and the host's background services account for about 1), above `run_e9v2.sh`'s warning threshold of 1.5 at 65 of the 144 starts. A busier host lengthens a measured time rather than shortening it, so where the load mattered the reported per-slot times overstate those of an idle host; the guard's split (its time within one run) is measured inside each run. The scripts, the points, the alignments and the analysis are unchanged.
