# Input tree of the tests of the budget-cap figure (MS8, X6)

This folder mirrors the repository layout, so that `figs/supp/sf_cap.py` run with `SUBLET_FIGS_IN_ROOT` set to it reads
its input under the repository-relative name it records for the real file (`code/sim/figs/inputs.py`). The tests
`tests/test_figs_ms8_x6.py` run on it (design/ms8/plan.md D2, W), and the fixture extract
`tests/fixtures_figs_ms8/x6/sf_cap.json` is what the script writes on it.

**This file is a reduced-mode (smoke) output of the budget-cap driver (`sublet/experiments/e7b.py`, parts week and
sens) and of its registered analysis (`e7b_analysis.py`), trimmed: not a result.** No number in it may be cited. It
covers one development week (`bench_e7f` config seed 101, a two-hour horizon); the analysis was run against reduced
frozen stand-ins of that week (`../assemble_frozen.py`: the MS5b fixture tree's part main, a reduced E7r part eval and
two reduced S1 v2 sweep and w0 summaries, which hold no run at the point fee4).

| File | Content |
|---|---|
| `code/sim/out/e7b/analysis.json` | `python -m sublet.experiments.e7b_analysis --frozen <stand-ins>` on the reduced run, with every key but `identity.rows` (the per-pair rows of the identity check; its counts stay) |

Every value kept is copied unchanged (`../trim_inputs.py`). The analysis's meta records the scratch paths and the
sha256 of the files it read; its registration check reports the working tree of the reduced run.

## How the tree was made, and refreshing it

    python tests/fixtures_figs_ms8/x6/assemble_frozen.py FROZEN --eval ... --sweep ... --w0 ...
    code/sim/tests/fixtures_figs_ms8/x6/refresh_inputs.sh SCRATCH --frozen FROZEN [--reuse-e7b ROOT] [--no-run]
    python tests/fixtures_figs_ms8/x6/refresh_extracts.py        # from code/sim, then the fixture extract

`refresh_inputs.sh` runs the reduced budget-cap runs (or, with `--reuse-e7b`, copies the parts' summaries of an earlier
reduced run), runs the registered analysis against the stand-ins, and then `trim_inputs.py SCRATCH/root` writes this
tree (`--check` lists a stale copy). Rerun it after a change to the driver or the analysis, then refresh the fixture
extract.

`../standin.py` makes, in a test's temporary folder, a stand-in analysis at the scale of the registered runs (16 weeks,
13 lenders, five points) from this one by a seeded perturbation, run through the frozen analysis; its numbers exist only
in the tests.
