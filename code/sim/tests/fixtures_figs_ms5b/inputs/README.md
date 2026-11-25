# Input tree of the MS5b figure, float and claims tests (Fig. 4 v2, Table III v2, the supplementary MS5b figures)

This folder mirrors the repository layout, so that a figure or float script run with `SUBLET_FIGS_IN_ROOT` set to it
reads `code/sim/out/sublet_v2/main/summary.json` and the other inputs under the same repository-relative names that it
records for the real files (`code/sim/figs/inputs.py`). The MS5b figure, float and claims tests run on it
(design/sublet_v2.md §11, W13), and the fixture extracts `code/sim/tests/fixtures_figs_ms5b/<name>.json` are what each
MS5b figure script writes on it.

**These files are reduced-mode outputs of the confirmation parts of `e7h.py` and the analysis script run on them, not
results.** No number in them may be cited. They were written by `run_e7h.sh --reduced` (development cells only:
`bench_e7f` config seed 101 on a 2-hour horizon, E3 and E5 config seed 101, E3 at b in {1, 8}, the first Q6 family
instances, the Q44 tuning cell I2 c1; e7h.py's docstring) on commit `5c7d3328` with U36's working tree (every summary
records the commit in `meta.git_revision`; the working tree held U36's uncommitted changes to the figure layer, none in
`sublet/`), and copied here unchanged, so the files have the driver's exact shape (key paths, field names, null forms).
Every part's `summary.json` has `meta.reduced` true. In reduced mode the confirmation gate is recorded, not enforced:
each summary's `meta.confirmation_gate` and each run file's `meta.gate` say so (`enforced` false; the gate itself
reports the dirty working tree). `analysis.json` has no `reduced` flag; a script takes it from the summaries. Its
pass/fail values on these two-hour development runs mean nothing.

| File | Content |
|---|---|
| `code/sim/out/sublet_v2/main/` | part `main`: the 22 tags of §3 on week 101 (development cell, 2 hours) under L-tr, the five stress modes and L-hon, policy seed 0; 22 jobs, 154 runs |
| `code/sim/out/sublet_v2/seeds/` | part `seeds`: Sublet, BL1 and BL5-cur on week 101 under the seven modes at policy seed 1; 3 jobs, 21 runs |
| `code/sim/out/sublet_v2/second/` | part `second`: the 12 tags of §4.4(b) on week 101 under L-vr, L-rf, L-ad, L-b999 and the iid_step grid, the lag tags under L-tr, the E5 menus and the gap day; 40 jobs, 147 runs, one merged gap LP in `lb/` |
| `code/sim/out/sublet_v2/e3/` | part `e3`: E3 config seed 101 at b in {1, 8}, u 8, mu 1: Sublet, A9, BL1, BL5-cur and Sublet-MS4, shared and siloed, with the LP and MILP bound files in `lb/`; 13 jobs, 20 runs |
| `code/sim/out/sublet_v2/fam/` | part `fam`: the first instance of each Q6 family under its first mode (F1 under F-ad, F2 under F-ss, F3 under F-eg) at policy seed 0 for the 8 family tags; 3 jobs, 22 runs |
| `code/sim/out/sublet_v2/grid/` | part `grid`: the 22 tags on week 101 under L-tr and the five stress modes at policy seed 0, the gap reruns of that week with their merged LP in `lb/`, and the Q44 tuning cell I2 c1 under L-tr for Sublet, A9 and BL1-GP (so criterion S has no stress runs to read); 46 jobs, 157 runs |
| `code/sim/out/sublet_v2/<part>/` files | `summary.json`, `manifest.json`, `jobs/*.json` (every listed job has an `ok` record; their `argv` and `outputs` name the scratch roots of the runs), `tables.md`, `runs/` (every run file of the part, `e3`'s cell files in `runs/cells/`; 114 files, 2.2 MB, the unversioned files that W10's figures read for cost components, the total accounting, BL0b and own capacity) and `lb/` where the part writes one |
| `code/sim/out/sublet_v2/analysis.json`, `analysis.md` | `python -m sublet.experiments.ms5b_analysis --root <merged tree>` on the six parts above (H1-H6, H2b and the reported items) |

Not in the tree: the copy record `code/sim/out/ms3_copy_sublet_v2.json` (a check of the real copy, not a driver
output). No `logs/`, `retry/`, job lists or run logs. About 3.7 MB in 296 files besides this README and the two
trimmed copies below.

Two trimmed copies of other experiments' summaries, which some MS5b figures put beside the confirmation (unit U39b),
written by `python tests/fixtures_figs_ms5b/trim_inputs.py` from `code/sim` (`--check` lists a stale copy; rerun it
after either source changes). Every value kept is copied unchanged; only keys are left out (the script's docstring
names the keys kept):

| File | Content |
|---|---|
| `code/sim/out/e11/summary.json` | for `sf_e7_grid_dev`: E11's versioned summary (`code/sim/out/e11/summary.json`, a result at E11's commit `29919ea`, its `meta.git_revision`; not a reduced output) trimmed to its provenance, `D2` (per instance the stress modes, the W0 rows and the per-mode medians with their cell counts) for E11's tags BL1-G, BL5-G and BL5, `D4.thresholds`, and `D4.criteria` T and S of those tags (E11's own verdicts, which `e7v2_q44.tex` prints); 21 KB |
| `code/sim/out/e7/main/summary.json` | for `sf_e7_links`: the MS4 fixture tree's reduced E7 main summary (`tests/fixtures_figs_ms4/inputs/code/sim/out/e7/main/summary.json`, reduced mode at `939847ca`, not a result) trimmed to its provenance, grid, tag and links keys and the `saving_pct` of Sublet, BL5 and BL1 in `runs.1` and `links`; 8 KB |

## How the tree was made, and refreshing it

`code/sim/tests/fixtures_figs_ms5b/refresh_inputs.sh` makes it, from any folder:

    code/sim/tests/fixtures_figs_ms5b/refresh_inputs.sh SCRATCH                       # run the six parts, analyse, copy, check
    PARTS_AT_ONCE=2 MS3_WORKERS=2 code/sim/tests/fixtures_figs_ms5b/refresh_inputs.sh SCRATCH
    code/sim/tests/fixtures_figs_ms5b/refresh_inputs.sh SCRATCH --only e3 fam          # rerun and recopy two parts
    code/sim/tests/fixtures_figs_ms5b/refresh_inputs.sh SCRATCH --no-run               # analyse, copy and check earlier roots

`SCRATCH` is a folder outside the repository. Each part runs in its own fresh root `SCRATCH/<part>/` (as `MS3_ROOT`,
with `MS3_WORKERS=1` unless set and a copy of `code/sim/out/e11/summary.json` as the stand-in that the slot semaphore
needs):

    E7H_PART=<part> MS3_ROOT=SCRATCH/<part> MS3_WORKERS=1 code/sim/sublet/experiments/run_e7h.sh --reduced

and `SCRATCH/merged/out/sublet_v2/<part>` links to each part's folder for the analysis. This tree was made on
2026-11-03 with `PARTS_AT_ONCE=2 MS3_WORKERS=2` and the parts in the order main, second, grid, seeds, e3, fam (`--only`
in that order, then `--no-run` for the copy): main 566 s, second 762 s, grid 712 s, seeds 147 s, e3 73 s, fam 16 s
of wall time, about 30 min in all. The script then replaces the folders listed above and checks the tree: every JSON
file parses, every part's summary has `meta.reduced` true and its own part name, every job of each manifest has an
`ok` record, every run file records the confirmation gate as not enforced, and `analysis.json` holds H1-H6 and H2b.
Rerun it after a change to `e7h.py`, `ms5b_common.py` or `ms5b_analysis.py`, then update the commit above (this README
is not rewritten by the script) and refresh the fixture extracts with
`python tests/fixtures_figs_ms5b/refresh_extracts.py` from `code/sim`.
