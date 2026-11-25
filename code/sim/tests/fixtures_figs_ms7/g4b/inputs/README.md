# Input tree of the tests of the MS7 baseline and stress figures (unit W-G4 B)

This folder mirrors the repository layout, so that `figs/supp/sf_bl_ms7.py` and `figs/supp/sf_stress_ms7.py` run with
`SUBLET_FIGS_IN_ROOT` set to it read their inputs under the repository-relative names they record for the real files
(`code/sim/figs/inputs.py`). The tests `tests/test_figs_ms7_b.py` run on it (design/ms7/w_spec.md §4, unit W-G4 B),
and the fixture extracts `tests/fixtures_figs_ms7/g4b/<name>.json` are what each script writes on it.

**These files are reduced-mode (smoke) outputs of the baseline study's driver (`sublet/experiments/e7r.py`, parts
tune, confirm and eval) and of its registered analysis (`e7r_analysis.py`), trimmed: not results.** No number in them
may be cited. They cover one development week (`bench_e7f` config seed 101, a two-hour horizon); the analysis was run
against the MS5b fixture tree's confirmation summaries of that week (`tests/fixtures_figs_ms5b/inputs/code/sim/out/
sublet_v2/`), so the confirmation's tags take their seven lenders from that fixture's part main.

| File | Content |
|---|---|
| `code/sim/out/e7r/analysis.json` | `python -m sublet.experiments.e7r_analysis --frozen <the MS5b fixture's sublet_v2>` on the reduced run, trimmed to weeks, tags (every tag, every field), margins (r0_tr, W0, W0plus), the names of the as_built_vs_c2 pairs, tuned, best_of, confirm, checks (identity_summary, a9p_invariance, adaptive_equivalence, provenance) and meta |
| `code/sim/out/e7r/tune/selection.json` | the selection of `e7r_select.py` on the reduced tune part, unchanged |
| `code/sim/out/e7r/tune/summary.json` | the reduced tune part's summary, trimmed to meta (exp, part, spec, git_revision, written, reduced, weeks, modes, tags, reduced_note) and table |
| `code/sim/out/e7r/confirm/summary.json` | the reduced confirm part's summary, trimmed likewise (with selection and aliases) |

Every value kept is copied unchanged; only keys are left out (`../trim_inputs.py`). The analysis's meta records the
scratch paths and the sha256 of the files it read; its registration and gate checks report reduced runs.

## How the tree was made, and refreshing it

    code/sim/tests/fixtures_figs_ms7/g4b/refresh_inputs.sh SCRATCH [--reuse-e7r ROOT] [--no-run]
    python tests/fixtures_figs_ms7/g4b/refresh_extracts.py        # from code/sim, then the fixture extracts

`refresh_inputs.sh` runs the reduced baseline study (or, with `--reuse-e7r`, copies the parts' summaries and the
selection of an earlier reduced run), runs the registered analysis against the MS5b fixture tree, and then
`trim_inputs.py SCRATCH/e7r` writes this tree (`--check` lists a stale copy). The tree was made on 2026-11-09 from the
root that unit W-G2 made for `tests/fixtures_figs_ms7/` (unit B2's reduced runs at `56b847be`, analysed against the
MS5b fixture tree). Rerun it after a change to the baseline study's driver or analysis, or to the MS5b fixture tree,
then refresh the fixture extracts.

`../standin.py` makes, in a test's temporary folder, a stand-in tree at the scale of the real runs (16 evaluation
weeks, every tag) from this one by a seeded perturbation, run through the frozen selection rules and analysis; its
numbers exist only in the tests.
