# Input tree of the MS5 figure tests (sf_s1, sf_e9, sf_slack and their tables)

This folder mirrors the repository layout, so that a figure script run with `SUBLET_FIGS_IN_ROOT` set to it reads
`code/sim/out/s1/sweep/summary.json` and the other inputs under the same repository-relative names that it records for
the real files (`code/sim/figs/inputs.py`). `code/sim/tests/test_figs_ms5.py` runs on it, and the fixture extracts
`code/sim/tests/fixtures_figs_ms5/<name>.json` are what each MS5 figure script writes on it (design/sim_spec_ms5.md
§0 item 7, §10).

**These files are reduced-mode outputs of the MS5 drivers and a slice of an analysis output, not results.** No number
in them may be cited. The S1 and E9 files were written by the MS5 run scripts with `--reduced` (smoke runs at
alignment 1 and policy seed 0 on a 2-hour horizon; design/sim_spec_ms5.md §2.4) on the MS5 build's working tree on top
of commit `c82fa05f` (every summary records it in `git_revision`), and copied here unchanged, so the files have the
drivers' exact shape (key paths, field names, null forms with their `*_note` siblings). Every S1 and E9 `summary.json`
has `meta.reduced` true. In these 2-hour runs most Sublet runs abort (certificate case W(b)), S1-0 fails by
construction (2-hour runs against E7's weeks) and the per-hour times of E9 are not representative.

| File | Content |
|---|---|
| `code/sim/out/s1/sweep/summary.json` | S1's part `sweep` (§3.8): all 51 points (the default and the 50 of §3.4) at alignment 1, policy seed 0, 2 hours; the rows with `lo`, `hi`, `span`, the mu row read from E7's versioned summary, `not_run` and S1-0 … S1-4 |
| `code/sim/out/s1/q28/summary.json` | S1's part `q28` (§4.6): the nine policies under L-rf and L-vr and BL3 under the default lender, the rows `q28_rf` and `q28_vr`, Q28-1 … Q28-4 |
| `code/sim/out/e9/summary.json` | E9 (§5.7): all 16 run points with Sublet and A6 and all 7 LP points at alignment 1 on a 2-hour horizon |
| `code/sim/out/<folder>/manifest.json`, `<folder>/jobs/*.json` | the job list and the job records of `s1/sweep`, `s1/q28` and `e9`; every listed job is `ok`; their `argv` and `outputs` name the scratch roots of the runs |
| `code/sim/out/e7/main/summary.json` | a copy of the repository's versioned E7 main summary (written at `939847ca`; a result, not reduced): S1's mu row quotes it, and `sf_s1` reads it for the mu row of `s1_points.tex`; its sha256 equals the sweep summary's `meta.e7_summary.sha256` |
| `code/analysis/out/a1_lender_spotgpu.json` | a copy of the versioned analysis output (pools, capacities, lease levels) |
| `code/analysis/out/a1_slack_series.npz` | the first 4,032 slots (two weeks of 5-min slots) of each of the six pools of the versioned `a1_slack_series.npz`, written with fixed zip timestamps (reproducible bytes); the full series (50,993 slots) would make a fixture extract of about 1 MB. Check SL-1 runs on the versioned files instead (`test_figs_ms5.py`) |
| `code/analysis/out/a9b_notice_buffer_24h.json` | a trimmed copy of the versioned analysis output with the keys `sf_slack` reads: `meta.slot_min` (the slot length of the slack series) and, per a1 pool, `source` and `n_slots`, the latter set to the slice's 4,032 slots; it has a `meta.note` saying so. The slice has no end of the trace, so the fixture extract drops no slot (the versioned series drops its last 18, §6.2) |

Readers: `sf_s1` reads `s1/sweep/`, `s1/q28/` and `e7/main/summary.json`; `sf_e9` reads `e9/`; `sf_slack` reads the
three analysis files (§7). The tree has no `runs/`, `logs/`, `tables.md`, job lists or run logs, which no figure reads.
About 1.7 MB in 125 files besides this README.

## How the tree was made, and refreshing it

`code/sim/tests/fixtures_figs_ms5/refresh_inputs.sh` makes it, from any folder:

    code/sim/tests/fixtures_figs_ms5/refresh_inputs.sh SCRATCH                  # run s1 and e9, then copy and check
    code/sim/tests/fixtures_figs_ms5/refresh_inputs.sh SCRATCH --only e9        # rerun and recopy E9 only
    code/sim/tests/fixtures_figs_ms5/refresh_inputs.sh SCRATCH --no-run         # copy and check earlier roots

`SCRATCH` is a folder outside the repository. Each experiment runs in its own fresh root `SCRATCH/<exp>/` (as
`MS3_ROOT`, with `MS3_WORKERS=1` unless set and a copy of `code/sim/out/e11/summary.json` as the stand-in that the
slot semaphore needs), one after another:

    MS3_ROOT=SCRATCH/s1 MS3_WORKERS=1 code/sim/sublet/experiments/run_s1.sh --reduced
    MS3_ROOT=SCRATCH/e9 MS3_WORKERS=1 code/sim/sublet/experiments/run_e9.sh --reduced

The E9 files were copied with `--no-run` from the reduced root of the U28 build (`SCRATCH/e9` a symbolic link to it),
which ran the second command. The S1 files were rewritten on 2026-10-29 with `refresh_inputs.sh SCRATCH --only s1` (the
first command, run with `--no-copy` and then copied with `--no-run`), after the integrator's change to Q28-2, on the
same working tree. The script then replaces the folders listed above, writes the slack slice and the trimmed a9b file,
and checks the tree: every JSON file parses, every S1 and E9 summary has `meta.reduced` true, every job of each manifest
has an `ok` record, the E7 copy has the recorded sha256, and the slice holds the JSON's pools. Rerun it after a change
to an MS5 driver, then update the commit above (this README is not rewritten by the script) and refresh the fixture
extracts with `python tests/fixtures_figs_ms5/refresh_extracts.py` from `code/sim`, which `test_figs_ms5.py` compares
with what each figure script builds from this tree (§10).
