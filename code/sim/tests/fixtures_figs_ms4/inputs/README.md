# Input tree of the MS4 figure, float and claims tests (Fig. 4, the MS4 supplementary panels, Table III, the MS4 claims report)

This folder mirrors the repository layout, so that a figure script run with `SUBLET_FIGS_IN_ROOT` set to it reads
`code/sim/out/e7/main/summary.json` and the other inputs under the same repository-relative names that it records for
the real files (`code/sim/figs/inputs.py`). `code/sim/tests/test_figs_ms4.py`, `test_floats_ms4.py` and
`test_ms4_claims.py` run on it (design/sim_spec_ms4.md §0 item 7, §10).

**These files are reduced-mode outputs of the MS4 drivers, not results.** No number in them may be cited. They were
written by the MS4 run scripts with `--reduced` (smoke runs at alignment 1 and policy seed 0 on short horizons;
design/sim_spec_ms4.md §3.10, §4.7, §5.5, §6.7, §7.8) at commit `939847ca` (the merge of PR #53), which every file
records in `git_revision`, and copied here unchanged: unlike the MS3 tree `tests/fixtures_figs/inputs/`, nothing is
made up or edited by hand, so the files have the drivers' exact shape (key paths, field names, numeric-key format
`ms3_common.num_key`, null forms with their `*_note` siblings, §2.6). Every `summary.json`, `e3/gate.json` and
`e7/table3.json` has `meta.reduced` true (and `table3.json` `meta.sources.<part>.reduced` true), so the claims report
marks every check row read from them `bug` (§1.4 item 2), as `test_ms4_claims.py` expects of a reduced summary.

| File | Content |
|---|---|
| `code/sim/out/e3/summary.json` | E3 (§4.8). Reduced: b in {1, 8}, u = 8, mu / beta~ = 1 and the mu point 2 at b = 8, slow slots [156, 180) of the first day, MILPs under 30 s; the other b (2, 4, 16, 32) and mu (0.2, 0.5) are present in their null forms |
| `code/sim/out/e3/gate.json` | the gate record of `run_e3.sh --reduced --gate` (§4.4; its cell b = 8, u = 8, mu = 1, c = 1) |
| `code/sim/out/e4/summary.json` | E4 (§6.10). Reduced: both panels, the predictions `prev`, `phase30`, `amp1.5`, `del_p90`, `inj3x30`, `empty`, `exact`, mu = 1 and the default point at mu = 2, 2-hour days from slow slot 444, MILPs under 10 s, `e4:repro` at full size; the other six predictions and mu 0.2, 0.5 are present in their null forms, and `eager` and `phat` list alignment 1 only |
| `code/sim/out/e4/lb/eager/panel=<P>/c=1/{lp,lp_core,milp}.json` | the OPT_eager records of the ratio days (§6.7), behind `ratio.<panel>.<pred>.<series>.x_core` of `sf_e4` |
| `code/sim/out/e5/summary.json` | E5 (§5.6). Reduced: the whole grid of levels, menus, tags and mu on one day |
| `code/sim/out/e7/{main,stress,gap,allow}/summary.json` | E7's four parts (§3.10). Reduced: every part and job kind with the whole grid of tags, mu, routing graphs, stress modes and allowances on a 2-hour horizon |
| `code/sim/out/e7/table3.json` | every cell of Table III (§3.10, §9), written by main's summary job from the four part summaries |
| `code/sim/out/e8/summary.json` | E8 (§7.8). Reduced: the first 6 hours at market tightness 0.05, tiers S, M, L, windows 5 and 60 min, mu / beta~ 1 and 2, the Mooncake hour at windows 5 and 60; this summary keys only that grid (`meta.grid`), so window 15 and mu 0.2, 0.5 are absent rather than null |
| `code/sim/out/<folder>/manifest.json`, `<folder>/jobs/*.json` | the job list and the job records of each folder `e3`, `e4`, `e5`, `e7/main`, `e7/stress`, `e7/gap`, `e7/allow`, `e8` (the claims report's jobs block, §1.4 item 2); every record is `ok`; their `argv` and `outputs` name the scratch roots of the run |

Readers: Fig. 4 reads `e7/main/summary.json` and `e3/summary.json` (§8.1); `sf_e3_util` and `sf_e3_mu` `e3/`;
`sf_e4` `e4/`; `sf_e5` `e5/`; `sf_e7_mix` `e7/main/`, `e7/stress/` and `e7/table3.json`; `sf_e7_mu` `e7/main/`;
`sf_e7_allow` `e7/allow/`; `sf_e8` `e8/` (§8.2); Table III's writer `figs/table3_e7.py` `e7/table3.json` (§9); the
claims report `experiments/ms4_claims.py` the `checks` blocks of `e7/main/` (E7-1 to E7-12, combined over the parts),
`e3/`, `e4/`, `e5/` and `e8/`, the gate record and the job records (§1.4).

The tree has no `code/sim/out/figs/floats_heights_ms4.json` (Table III's measured height, written by
`paper/layout_check/pageplan/floats_heights.py --ms4`), no copy records `code/sim/out/ms3_copy_<exp>.json` (written
by `ms3_common --check-copy` against the clone of the runs, which needs the `runs/` folders) and no figure extracts,
so on the tree as it is those blocks of the claims report are `missing`; a test that needs them builds them in its
`tmp_path`, as `test_ms3_claims.py` does for MS3, and leaves this tree unchanged. It has no `runs/`, `logs/`,
`tables.md`, `jobs_list.txt` or run logs, no E3 or E7 `lb/` records and no E4 `repro/` or `repro_check.json`, which
no figure, float or claims row reads. About 2.4 MB in 389 files besides this README.

## How the tree was made, and refreshing it

`code/sim/tests/fixtures_figs_ms4/refresh_inputs.sh` makes it, from any folder:

    code/sim/tests/fixtures_figs_ms4/refresh_inputs.sh SCRATCH                  # run all five, then copy and check
    code/sim/tests/fixtures_figs_ms4/refresh_inputs.sh SCRATCH --only e7 e3     # rerun and recopy these only
    code/sim/tests/fixtures_figs_ms4/refresh_inputs.sh SCRATCH --no-run         # copy and check earlier roots

`SCRATCH` is a folder outside the repository. Each experiment runs in its own fresh root `SCRATCH/<exp>/` (as
`MS3_ROOT`, with `MS3_WORKERS=1` and a copy of `code/sim/out/e11/summary.json` as the stand-in that the slot
semaphore needs), one after another:

    MS3_ROOT=SCRATCH/e3 MS3_WORKERS=1 code/sim/sublet/experiments/run_e3.sh --reduced --gate
    MS3_ROOT=SCRATCH/e3 MS3_WORKERS=1 code/sim/sublet/experiments/run_e3.sh --reduced
    MS3_ROOT=SCRATCH/e4 MS3_WORKERS=1 code/sim/sublet/experiments/run_e4.sh --reduced
    MS3_ROOT=SCRATCH/e5 MS3_WORKERS=1 code/sim/sublet/experiments/run_e5.sh --reduced
    MS3_ROOT=SCRATCH/e7 MS3_WORKERS=1 code/sim/sublet/experiments/run_e7.sh --reduced
    MS3_ROOT=SCRATCH/e8 MS3_WORKERS=1 code/sim/sublet/experiments/run_e8.sh --reduced

(E8 reads the raw Azure 2024 and Mooncake traces under `/mnt/data/datasets`.) The script then replaces
`code/sim/out/<exp>/` of this tree with the files listed above and checks it: every file parses, every summary,
`gate.json` and `table3.json` has `meta.reduced` true, every job of each manifest has a record, `ok` unless it is a
MILP job whose output is a lower bound (`e3:milp:*`, `e4:eager:*`; not E4's P-hat day plans) and whose LB is its LP
under Q39's rule, and no `runs/` or `logs/` folder was copied. Rerun it after a change to
an MS4 driver, then update the commit above (this README is not rewritten by the script) and refresh the MS4 fixture
extracts `code/sim/tests/fixtures_figs_ms4/<name>.json`, which `test_figs_ms4.py` compares with what each figure
script builds from this tree (§10).
