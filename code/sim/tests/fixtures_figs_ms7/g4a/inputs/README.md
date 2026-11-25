# Fixture input tree of the MS7 supplementary figures sf_lag_v2 and sf_oos (not results)

Every file under `code/sim/out/` here is a reduced-mode (smoke) output of the MS7 drivers and their registered
analyses, or a trimmed copy of one: **not results**. Never cite a number from this tree.

- `e7c/analysis.json`, `e7c/lag/summary.json`: the registered X1 analysis (`sublet/experiments/e7c_analysis.py`) on a
  reduced run of `run_e7c.sh` (parts gate and lag: development week 101, two hours), and that run's part lag summary
  trimmed to its meta, table and the runs of the two guarded policies.
- `sublet_v2/main/summary.json`: the MS5b fixture's confirmation summary (`tests/fixtures_figs_ms5b/inputs/`, week
  101) that the reduced X1 run read, trimmed to its meta and the table rows of the revealed counterparts and of the
  lagged RetroRenting-style.
- `e7o/analysis.json`: the registered X2 analysis (`sublet/experiments/e7o_analysis.py`) on a reduced run of
  `run_e7o.sh` (folds fwd and rev, cell 0 at development seed 101, two hours), bridged to the same MS5b summary,
  without each fold's `sublet_vs_h1_summary`.

Remake the tree with `tests/fixtures_figs_ms7/g4a/refresh_inputs.sh SCRATCH` (or its `--reuse-e7c`/`--reuse-e7o`
options) and `trim_inputs.py`; then refresh the fixture extracts with `python tests/fixtures_figs_ms7/g4a/refresh_extracts.py`
from `code/sim`. The tests' full-scale trees (16 weeks, 16 cells per fold) are made from this tree in pytest's
`tmp_path` by `fullscale.py`, which reruns the registered analyses on stand-in summaries; their numbers exist only in
the test.
