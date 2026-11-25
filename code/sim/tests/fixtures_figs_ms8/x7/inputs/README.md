# Input tree of the tests of the X7 supplementary script (MS8, unit F7)

This folder mirrors the repository layout, so that `figs/supp/sf_e8q.py` run with `SUBLET_FIGS_IN_ROOT` set to it
reads its inputs under the repository-relative names it records for the real files (`code/sim/figs/inputs.py`). The
tests `tests/test_figs_ms8_x7.py` run on it (design/ms8/plan.md W), and the fixture extract
`tests/fixtures_figs_ms8/x7/sf_e8q.json` is what the script writes on it.

**These files are a reduced-mode (smoke) output of the X7 driver, trimmed, and the frozen analysis run on it; they are
not results.** No number in them may be cited. They cover E8 v2's reduced instance (6 hours at market tightness 0.05):
tiers S, M, L, smoothing windows 5 and 60 min, alignment 1, the four policies and the bill at W in {0, 1, 2.5, 10} s.

| File | Content |
|---|---|
| `code/sim/out/e8q/summary.json` | `run_e8q.sh --reduced`, trimmed: per cell and tag only the keys that the frozen analysis and `sf_e8q` read (costs, fluid components, lease spend, headroom, window classes, status; per W the costs, E, gap, replay components, fallback split by demand, per-class counters), the checks cut to status, claim and n |
| `code/sim/out/e8q/hist.json` | `run_e8q.sh --reduced`, unchanged (the TTFT histograms, the analysis's Q-2 input; `sf_e8q` does not read it, the stand-ins of the real-scale test do) |
| `code/sim/out/e8q/analysis.json` | `e8q_analysis.run_analysis` on the trimmed summary and hist.json, with E8 v2's reduced summary of the MS7 fixture tree (`tests/fixtures_figs_ms7/g4c/inputs/code/sim/out/e8v2/a/summary.json`, the same reduced grid) as Q-0's reference, so that it records the sha256 of the summary beside it (the script checks it); Q-0 passes on these cells |

Every value kept is copied unchanged; only keys are left out (`../trim_inputs.py`). The analysis records the
registration as matching (the frozen script's sha256) and its input as a reduced run whose gate was not enforced, so
`registered_full_inputs` is false; the script accepts that for reduced inputs only and never writes its outputs into
`paper/` or `code/sim/out/` then.

## How the tree was made, and refreshing it

    code/sim/tests/fixtures_figs_ms8/x7/refresh_inputs.sh SCRATCH [--reuse ROOT]
    python tests/fixtures_figs_ms8/x7/refresh_extracts.py            # from code/sim, then the fixture extract

`refresh_inputs.sh` runs the reduced X7 run in `SCRATCH` as its MS3_ROOT (or, with `--reuse`, takes an earlier reduced
root) and then `trim_inputs.py ROOT`, which writes this tree (`--check` lists a file that would change). The tree was
made on 2026-11-24 from a reduced run of the run commit's driver (`6acedbcd` with this unit's files uncommitted, so the
gate recorded a dirty tree). Rerun it after a change to the X7 driver or the analysis, then refresh the fixture
extract.

The real-scale test uses stand-ins instead (`../standins.py`: made-up numbers at the registered grid, with E8 v2's
stored pairs at W = 0, written to the test's temporary folder only).
