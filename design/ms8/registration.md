# Registration of the runs X6 and X7

*Public copy: process notes and references to internal design documents were removed; every registered rule, parameter, cell and hash is unchanged from the version frozen at the registration commit. (The frozen version, whose sha256 `4efe023be0d2f586ae1efd0a7977ca44e494cce30feb2aa890bbb23128172c72` the run records in `code/sim/out/e8q/` and `code/sim/out/e7b/` carry as `registration_sha256`, therefore differs from this file; the two `_sha256` lines of §1 are identical in both.)*

*Registered on 2026-11-24, before any registered run. The commit that merges this file into `main` is the **run commit**; in the development repository it is `467b2181` (the merge of the registration commit `157d5083`). Every part below runs once, in a clean clone of the run commit, and its outputs are copied into `code/sim/out/` with a copy check (`python -m sublet.experiments.ms3_common --check-copy <exp> <clone>`), as for the runs of `design/ms7/registration.md`. These runs are exploratory: they are reported in full whatever their outcome; they are not confirmations.*

## 1. Frozen scripts

The drivers read these lines (each at the start of a line, `<name>_sha256: <64 hex>`):

```
e8q_analysis_sha256: 68b7f7a3d2ac57863662385322b9fad1e1463ed5fc528967c79273b3cfd1c728
e7b_analysis_sha256: 530151bfa0c506ceab5c5b9ec367424bab275edcc150fb78a2242f36aabe8704
```

| Line | Script (under `code/sim/sublet/experiments/`) | Read by |
|---|---|---|
| `e8q_analysis_sha256` | `e8q_analysis.py` | `e8q.py` (X7) |
| `e7b_analysis_sha256` | `e7b_analysis.py` | `e7b.py` (X6) |

The policies, drivers and options are those of the run commit: `sublet/replay/queue.py`, `sublet/algos/budget_cap.py` (registry table MS8), `experiments/e8q.py`, `e7b.py`, `e7b_tags.py` and their run scripts, each reviewed independently before this registration. No frozen module changed; `registry.py` gains a table read after MS7's, and `ms3_common.COPY_PARTS` gains the entries of `e8q` and `e7b`.

## 2. What runs

| Exp. | Driver, parts | Cells | Policies | Lender modes | Jobs |
|---|---|---|---|---|---|
| X7, replay with a queue | `e8q.py` (no parts) | E8 v2's grid: tiers S, M, L x smoothing windows 5, 15, 60 min x alignments 1-4, mu = beta-tilde, policy seed 0 | Sublet, A9, BL1-BO, BL5-cur, each replayed at W in {0, 1, 2.5, 10} s in lockstep, with BL0a's zero placement for the replayed bill at each W | L-tr | 37 (the request cache and 36 cells) |
| X6, budget caps | `e7b.py`: `week`, then `sens` | `week`: the confirmation weeks 301-316; `sens`: the S1 v2 points fee4, fee8, fee16, slow1 and scen_cold_wan_1gbps on weeks 301-304 (L-tr) and 301-302 (the five stress modes) | the cap tags CR-cap-B, CR-cap-0, CR-cap-5, CR-cap-B-latch, CR-cap-B-slot (inner A9) and GR-cap-B, GR-cap-0 (inner BL1); in `week` also Sublet and A9 under L-tr as an identity rerun against `out/sublet_v2/main`; in `sens` also BL1-GP as the reference of the GR caps | `week`: the 13 modes of E7r's part eval; `sens`: as above | 144 (`week`); 188 (`sens`) |

No parameter is chosen on these cells: X is Sublet's allowance B(t) (`'lb'`), 0, or 5% of the fallback cost so far, and every other setting is as built.

## 3. What each analysis reports

No analysis prints a p-value (the weeks are rotations of one series). Margins follow the confirmation's convention: baseline minus Sublet, positive when Sublet costs less, with a missing run counted as a loss.

- **X7** (`e8q_analysis.py`): Q-0, the identity at W = 0 with E8 v2's fluid and replayed costs (`out/e8v2/a/summary.json`) to 1e-9 in every tag and cell. Q-1, per W: each tag's replayed cost, the fluid model's error E and its median |E|, Sublet's margin over the cheaper of BL1-BO and BL5-cur, wins out of 36 and the agreement of the fluid and replayed orders. **Q-1 holds** iff Sublet's median |E| at W* = 2.5 s is below its median |E| at W = 0 and Sublet's wins at W* are at least its wins at W = 0. Q-2 (descriptive): per tier, tag, W and window class (reclaim, load, overflow, base), the fallback share, the share served after waiting, the interrupted share, TTFT percentiles P50, P99 and P99.9 at D_fb in {0.5, 1, 2} s and the attainment of TTFT SLOs of 0.25, 2.5 and 4.0 s by tier, each with its slot and copy counts. Q-3: the gap between replayed and fluid cost split into fallback in zero-demand slots, fallback in overflow slots, stranding and routing, and each policy's headroom.
- **X6** (`e7b_analysis.py`): per run r0, W0 and W0+, the final excess (ALG(T) - FB(T) - B(T))/FB(T) and the largest run-time excess over the run; the run checks (FB(T) equals BL0a's bill, X(T) equals Sublet's B(T) for the X = B(t) caps); the paired margins of each cap against Sublet and of the GR caps against BL1-GP, with wins, ties, losses (missing counted) and median and min-max. The readings, each reported whatever its sign: **R1** whether some X = B(t) cap ends or runs above the bound FB + B in some run while Sublet never does; **R2** whether CR-cap-0's median r0 under the stress modes is at least 0.95 while Sublet's is at most 0.79; **R3** every cell in which a cap costs less than Sublet.

## 4. Order and host

From `code/sim` in the clean clone of the run commit, with `MS3_HOST_SLOTS=6` for every run script (the value sets only how many jobs run at once):

1. `E7B_PART=week sublet/experiments/run_e7b.sh`, then `E7B_PART=sens sublet/experiments/run_e7b.sh` (which runs the analysis);
2. in parallel with 1: `sublet/experiments/run_e8q.sh` (which runs the analysis).

Every job runs in its own 3 GB scope.

## 5. Runs made before this registration (disclosed)

None of these is a registered result, and none is copied into `code/sim/out/`:

- prototype runs: for X7, Sublet and BL1-BO on cell (M, 15, 1) at W in {0, 1, 2, 5, 10} s; for X6, naive caps around A9 and BL1 on weeks 301-302 at the default point and at fee16 and slow1 under L-tr, L-eg and L-iid-0.2 or L-iid-0.05;
- measurements of the built X7 code with the gate bypassed on cells (S, 60, 1), (M, 15, 1) and (L, 5, 1), and the code review's cell (L, 5, 2), all before the fix to the load window (`queue.window_classes`);
- the reduced smoke runs of both drivers in the tests.

## 6. Checks at the run commit

Before the runs, in the clean clone: the new tests (`tests/test_replay_queue.py`, `test_e8q.py`, `test_budget_cap.py`, `test_e7b.py`) and the existing tests of the replay, E8 v2, the guard, the registry and E7r. After the runs: the copy checks, then the quick suite of the merge that copies the outputs in.
