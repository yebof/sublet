# Input tree of the MS6 figure tests (Fig. 1 v2, `fig1v2`)

This folder mirrors the repository layout, so that a figure script run with `SUBLET_FIGS_IN_ROOT` set to it reads
`code/sim/out/fig1v2/run.json` and `manifest.json` under the same repository-relative names that it records for the
real files (`code/sim/figs/inputs.py`). `code/sim/tests/test_fig1v2.py` runs on it, and the fixture extract
`code/sim/tests/fixtures_figs_ms6/fig1v2.json` is what `figs/fig1_v2.py` writes on it (design/ms6_spec.md §2 U44).

**These files are the output of a reduced run of the driver, not a result.** No number in them may be cited. They were
written by `python -m sublet.experiments.fig1_illustrative --reduced` (Sublet on the first 3 hours, slow slots
[0, 36), of the pilot cell Q44 I2 c1 under the eager stress lender L-eg, policy seed 0; the driver's `WINDOW_REDUCED`)
on the U44 build's working tree on top of commit `0cb4f4af` (the manifest records it, with `tracked_files_dirty`
true), so the files have the driver's exact shape. The manifest has `reduced` true and no pilot check (`checks.pilot`
null); its other checks pass (the logged run equals the unlogged run; the log is consistent with the guard's record).
The run projects 5 slots (0, 2, 3, 10, 11) and does not abort.

| File | Content |
|---|---|
| `code/sim/out/fig1v2/run.json` | the run record: cell, mode, seeds, the tag's and the policy's parameters, the per-slot series (test value, threshold, C_S, B, executed candidate, the inner list's test value at the projected slots, ALG per slot and cumulative), every logged evaluation and the summary |
| `code/sim/out/fig1v2/manifest.json` | git revision and dirty flag, cell, mode, seeds, parameters, wall time, peak RSS, the sha256 of `run.json` and the checks |

## Refreshing it

`code/sim/tests/fixtures_figs_ms6/refresh_inputs.sh` reruns the reduced driver into this tree (about 15 s, in a 3G
scope). Rerun it after a change to the driver, then update the commit above (this README is not rewritten by the
script) and refresh the fixture extract with `python tests/fixtures_figs_ms6/refresh_extracts.py` from `code/sim`,
which `test_fig1v2.py` compares with what the figure script builds from this tree.
