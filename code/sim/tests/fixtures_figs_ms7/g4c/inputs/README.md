# Input tree of the tests of the X3 supplementary scripts (writer C of unit W-G4)

This folder mirrors the repository layout, so that `figs/supp/sf_s1_v2.py`, `sf_e5_v2.py`, `sf_e8_v2.py` and
`sf_e9_v2.py` run with `SUBLET_FIGS_IN_ROOT` set to it read their inputs under the repository-relative names they record
for the real files (`code/sim/figs/inputs.py`). The tests `tests/test_figs_ms7_c.py` run on it (design/ms7/w_spec.md
§4, unit W-G4), and the fixture extracts `tests/fixtures_figs_ms7/g4c/<name>.json` are what each script writes on it.

**These files are reduced-mode (smoke) outputs of the X3 drivers, trimmed, and the frozen analysis run on them; they
are not results.** No number in them may be cited. They cover one development week or config seed (101) at a short
horizon and alignment 1, with most jobs of S1 v2 and E9 v2 left out by the reduced job lists; E8 v2's two-timescale PD
is absent, since the reduced runs are not at E8's scale.

| File | Content |
|---|---|
| `code/sim/out/s1v2/sweep/summary.json`, `w0/summary.json` | `S1V2_PART="sweep w0" run_s1v2.sh --reduced` (unit B4's smoke root), trimmed: the sweep's runs, missing list and instances left out, its points cut to their row, value, label, mu and gamma_row, the checks to their status and claim |
| `code/sim/out/e5v2/summary.json` | `run_e5v2.sh --reduced`, trimmed: runs and missing list left out, checks to status and claim |
| `code/sim/out/e8v2/a/summary.json` | `run_e8v2.sh --reduced`, the missing list left out, checks to status and claim |
| `code/sim/out/e9v2/summary.json` | `run_e9v2.sh --reduced`, trimmed: per point its sizes, split and per policy the run fields that the analysis and the script read |
| `code/sim/out/<exp>/analysis.json` | `ms7_sens_analysis.run_analysis(['s1v2', 'e5v2', 'e8v2', 'e9v2'], root=<this tree's code/sim>, conf_dir=<tests/fixtures_figs_ms5b's sublet_v2>)` on the trimmed summaries, so that each records the sha256 of the summary beside it (the scripts check it) and S1 v2's seed spread is the MS5b fixture's (week 101) |

Every value kept is copied unchanged; only keys and rows are left out (`../trim_inputs.py`). The analyses record the
registration as matching (the frozen script's sha256) and their inputs as reduced runs whose gate was not enforced, so
`registered_full_inputs` is false; the scripts accept that for reduced inputs only and never write their outputs into
`paper/` or `code/sim/out/` then.

## How the tree was made, and refreshing it

    code/sim/tests/fixtures_figs_ms7/g4c/refresh_inputs.sh SCRATCH [--reuse ROOT]
    python tests/fixtures_figs_ms7/g4c/refresh_extracts.py            # from code/sim, then the fixture extracts

`refresh_inputs.sh` runs the four reduced X3 runs in `SCRATCH` as their MS3_ROOT (or, with `--reuse`, takes an earlier
reduced root) and then `trim_inputs.py ROOT`, which writes this tree (`--check` lists a file that would change). The
tree was made on 2026-11-09 with `--reuse` of unit B4's reduced runs (at `56b847be`), the analysis at `c1f4dc18`. Rerun
it after a change to the X3 drivers or the analysis, then refresh the fixture extracts.

The real-scale tests use stand-ins instead (`../standins.py`: made-up numbers at the registered grids, written to the
test's temporary folder only).
