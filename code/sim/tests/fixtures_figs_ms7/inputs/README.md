# Input tree of the MS7 figure and table tests (Fig. 3 v3, Tables IV and V)

This folder mirrors the repository layout, so that `figs/fig4_v3.py`, `figs/table3_v3.py` and `figs/table5_alglb.py`
run with `SUBLET_FIGS_IN_ROOT` set to it read their inputs under the repository-relative names they record for the
real files (`code/sim/figs/inputs.py`). The tests `tests/test_figs_ms7_fig4.py` and `tests/test_tables_ms7.py` run on
it (design/ms7/w_spec.md §4, unit W-G2), and the fixture extracts `tests/fixtures_figs_ms7/<name>.json` are what each
script writes on it.

**These files are reduced-mode (smoke) outputs of the MS7 drivers and of their registered analyses, or copies of the
MS5b fixture tree's reduced outputs, not results.** No number in them may be cited. They cover one development week
(`bench_e7f` config seed 101, a two-hour horizon), in every file: each MS7 analysis was run against the MS5b fixture
tree's confirmation summaries of that week, so the tree is consistent (the scripts check that the weeks agree, that
Table III v2's BL0a bill is the e7r runs' bl0a_usd, and that the S1 v2 analysis read this tree's main and seeds
summaries).

| File | Content |
|---|---|
| `code/sim/out/sublet_v2/` | copies of `tests/fixtures_figs_ms5b/inputs/code/sim/out/sublet_v2/` main, second (with `lb/`) and seeds `summary.json` and `analysis.json` (reduced runs of `e7h.py`'s confirmation parts on week 101; that tree's README) |
| `code/sim/out/figs/fig4v2.json`, `table3_v2.json` | copies of the MS5b fixture extracts `tests/fixtures_figs_ms5b/fig4v2.json` and `table3_v2.json`, in place of the versioned extracts that Fig. 3 v3 ((a)) and Table IV (the confirmation's rows) read |
| `code/sim/out/e7c/analysis.json` | `python -m sublet.experiments.e7c_analysis` on a reduced run of `E7C_PART="gate lag" run_e7c.sh --reduced` (X1, 11 lag tags under the seven lender modes), unchanged |
| `code/sim/out/e7r/analysis.json` | `python -m sublet.experiments.e7r_analysis --frozen <the MS5b fixture's sublet_v2>` on a reduced run of `run_e7r.sh` (X4, parts tune, confirm and eval; unit B2's smoke root), trimmed to weeks, meta, the tags A9-P, MPC-T and the `-c2` transplants (per_week and role), `as_built_vs_c2` and `checks.identity_summary` |
| `code/sim/out/e7r/eval/summary.json` | that run's part eval summary, trimmed to meta and the week runs of A9-P and MPC-T |
| `code/sim/out/s1v2/analysis.json` | `ms7_sens_analysis.run_analysis(['s1v2'], conf_dir=<the MS5b fixture's sublet_v2>)` on a reduced run of `S1V2_PART="sweep w0" run_s1v2.sh` (X3; unit B4's smoke root), trimmed to meta and `seed_spread` |

Every value kept is copied unchanged; only keys and rows are left out (`trim_inputs.py`). The analyses' meta records
the scratch paths and the sha256 of the files they read; their registration and gate checks report reduced runs.

## How the tree was made, and refreshing it

    code/sim/tests/fixtures_figs_ms7/refresh_inputs.sh SCRATCH [--reuse-e7r ROOT] [--reuse-s1v2 ROOT] [--no-run]
    python tests/fixtures_figs_ms7/refresh_extracts.py            # from code/sim, then the fixture extracts

`refresh_inputs.sh` runs the reduced X1 runs and the three analyses in roots under `SCRATCH` (each run script starts its
own 3G scopes; `MS3_WORKERS=1` unless set), with `--reuse-e7r` and `--reuse-s1v2` copying the parts' summaries from
earlier reduced runs instead of running X4 and X3 again, and then `trim_inputs.py SCRATCH` writes this tree (its
docstring lists the files; `--check` lists a stale copy). The tree was made on 2026-11-09 from the working tree of unit
W-G2 on `6a96bce8`, with the reduced X1 run made then (about 10 min at one worker) and the reduced X4 and X3 runs of
units B2 and B4 (at `56b847be`) reused. Rerun it after a change to the MS7 drivers or analyses, or to the MS5b fixture
tree, then refresh the fixture extracts.
