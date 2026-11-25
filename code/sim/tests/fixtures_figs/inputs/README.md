# Fixture input tree of the figure tests (Figs. 5-7 and the E1, E2, E6, E10 supplementary panels)

This folder mirrors the repository layout, so that a figure script run with `SUBLET_FIGS_IN_ROOT` set to it reads
`code/sim/out/e1/summary.json` and the other inputs under the same repository-relative names that it records for the
real files (`code/sim/figs/inputs.py`). `code/sim/tests/test_figs_ms3_exp.py` runs on it.

**The MS3 summaries here are synthetic.** They are not results of any run and no number in them may be cited. They
have the shape the MS3 drivers write (`code/sim/sublet/experiments/e1.py`, `e10.py`, `e2.py`, `e6.py`;
design/sim_spec_ms3.md §4-§7): the same key paths, field names, types, numeric-key format (`format(float(x), "g")`)
and null forms (a missing value is `null` with its `*_note` sibling, §2.6; the null entries are built by the
drivers' own helpers `e2._null`, `e2._totals_null`, `e2._best_H_null`, `e6._cell_null`, `e6._b_null`,
`e10._null_entry` and `e10.b_entry`). Their values are made up, of plausible magnitude (taken from
`code/sim/out/ms3spec/`, `code/sim/out/ms2_checks/` and the theory outputs), except where a driver function gives
them: the E10 `bounds` are `e10.bounds_entry` (with the fixture's RR-renew OPT for O1-B), and the `meta`, `checks`,
`certificates` and `milp` blocks are in the drivers' form with values from a reduced driver run.

| File | Content |
|---|---|
| `code/sim/out/e1/summary.json` | `ratios.<sched>.<rho>.<mu>.<tag>`, `brackets.trace.<rho>.<c>` (with the `eager` and `omega` records), `meta`, `certificates`, `milp`, `tight_family`, `checks` |
| `code/sim/out/e1/tight_family.json` | the output of job `e1:tight` (§4.4; not reduced, so these are the family's exact values) |
| `code/sim/out/e10/summary.json` | `a`, `b`, `bounds`, `value_public`, `meta`, `checks` |
| `code/sim/out/e2/summary.json` | `episodes`, `totals`, `best_H`, `coincide`, `cold_equals_a1`, `bandless`, `meta` (groups, quartiles and spot pools only), `checks`; kept small: the pool and quartile groups only at mu = 1 for A1 (what `sf_e2_pool` reads), complete totals only for A1, `by_alignment` only where a figure reads it, no `coincide_detail` |
| `code/sim/out/e2/game.json` | `rows` on the grids of §6.6 with CR interpolated from `por_default.json` Table PoR, and `meta.hstar` from its `Hstar_formula` |
| `code/sim/out/e6/a/heatmap.json`, `boundary.json` | the cells of every (group, lambda', mu, H, row) and the boundary columns; kept small: a cell with a value has only the fields the figures read (value, ci95, n_pairs, share_insured) |
| `code/sim/out/e6/b/summary.json` | `menus.<menu>.<mu>` (without `cost_R_over_cost_bl0a` and `bl0a_by_alignment`), `meta` (subset), `checks` |

`code/sim/tests/test_ms3_claims.py` also reads this tree (the claims report, design/sim_spec_ms3.md §1.4): the
`checks` blocks of the summaries above. The tree has no `code/sim/out/e6/a/summary.json` (E6-1 to E6-5), no E11 files
(`e11/summary.json`, `ms3_e11_0.json`, `q44_study/summary.json`) and no `figs/` extracts, so on the tree as it is those
rows are `missing`; the test builds the other cases in its `tmp_path` (an e6/a `checks` block in the driver's form,
links to the repository's versioned E11 files, job lists and job records for the report's jobs block) and leaves this
tree unchanged.

The files under `code/theory_checks/**/out/`, `code/analysis/out/a11_calibration.json` and
`code/sim/out/ms2_checks/a3_rotation_c4a.json` are relative symbolic links to the real files of the repository.

The fixture extracts `code/sim/tests/fixtures_figs/<name>.json` (`fig5`, `fig6`, `fig7`, `sf_e1_*`, `sf_e2_*`,
`sf_e6a`, `sf_e6b`, `sf_e10*`) are what the figure scripts write when run on this tree, and are therefore synthetic
too; `sf_e6a.json` keeps one block of its cell table (MaaS, lambda' = a5, mu = 1) to stay small.

## Refreshing the fixture extracts

After any change to a figure script, refresh the fixture extracts with
`code/sim/tests/fixtures_figs/refresh_extracts.py`, run from `code/sim` in the 3G scope:

    python tests/fixtures_figs/refresh_extracts.py            # rewrite every stale fixture extract
    python tests/fixtures_figs/refresh_extracts.py --check    # list the stale ones, write nothing (exit 1 if any)
    python tests/fixtures_figs/refresh_extracts.py --only fig7 sf_e6a

It refreshes two groups, each the way it was made:

- `fig5`, `fig6`, `fig7`, `sf_e1_*`, `sf_e2_*`, `sf_e6a`, `sf_e6b`, `sf_e10*` (read by `test_figs_ms3_exp.py`): it runs
  each script on this tree with its outputs in a temporary folder (finalize() runs on each) and keeps the extract,
  with `sf_e6a`'s cell table cut to the MaaS, lambda' = a5, mu = 1 block. Synthetic, like the tree.
- `fig1`, `fig2`, `fig3`, `sf_e11_inst`, `sf_e11_fam`, `sf_e11_guard` (read by `test_figs_ms3.py`): copies of the real
  extracts in `code/sim/out/figs/` (rerun those scripts on the real inputs first), with `sf_e11_fam`'s `all_modes`
  cut to `F1_m2_r16` and `sf_e11_guard`'s certificate ratios thinned to every 25th sorted value plus the last, each
  with a `fixture_note`.

`test_figs_ms3_exp.py::test_build_reads_only_result_files_and_matches_the_extract` and
`test_figs_ms3.py::test_normal_mode_on_the_versioned_inputs` fail on a stale fixture extract and name the script.
The synthetic summaries of this tree are not regenerated by it; they are edited by hand in the drivers' form.
