"""pytest setup for the Sublet simulator (design/sim_spec.md §9.1).

Puts code/sim, code/theory_checks/c3, code/theory_checks/c3/o1 and code/analysis on
sys.path, sets OMP_NUM_THREADS=1 if unset, and defines the markers
  slow       the test takes more than 30 s;
  needs_a12  skipped if a12_minute_io.npz or a12_sim_inputs.json is missing in code/analysis/out;
  needs_raw  skipped if /mnt/data/datasets is not readable.
Reference modules are then importable by their names in the check scripts: core,
pd (as ref_pd), fam, check_c4_lower, check_c3_benchmark.

MS2 additions (design/sim_spec_ms2.md §17.1): code/theory_checks/c2 and c2/audit on sys.path
(model, families, alg_check as an oracle, model_switch_cost); sys.dont_write_bytecode = True, so
that no .pyc file under code/theory_checks/ is created or changed; the marker
  needs_ms2_checks(*files)  skipped if a file it reads in code/sim/out/ms2_checks/ is missing
                            (no argument: if that folder is missing or empty).
The folder is MS2_CHECKS_DIR, overridable with the environment variable SUBLET_MS2_CHECKS_DIR
(also the folder to which informative tests write, e.g. pd_order.json).

MS3 addition (design/sim_spec_ms3.md §10): the marker
  needs_ms3_out(*files)     skipped if a named file under code/sim/out/ is missing (names relative to that
                            folder, e.g. "e1/summary.json"; the files of every such marker of a test, e.g. of
                            the test and of its parametrized case, count; a marker without arguments, alone or
                            beside markers with files: also if the folder is missing or empty).
The folder is MS3_OUT_DIR = <MS3_OUT_ROOT>/code/sim/out, with MS3_OUT_ROOT the repository, overridable with the
environment variable SUBLET_MS3_OUT_ROOT (a folder with the repository's layout; tests/test_ms3_out.py reads the
same root). The quick suite runs with -m "not needs_raw and not needs_ms2_checks and not needs_ms3_out".

MS4 addition (design/sim_spec_ms4.md §2.3, C19; §10): the marker
  needs_ms4_out(*files)     defined like needs_ms3_out: skipped if a named file under
                            <MS4_OUT_ROOT>/code/sim/out is missing (the files of every such marker of a test count;
                            a marker without arguments also skips while that folder is missing or empty).
MS4_OUT_ROOT is the repository, overridable with the environment variable SUBLET_MS4_OUT_ROOT. The quick suite
then runs with -m "not needs_raw and not needs_ms2_checks and not needs_ms3_out and not needs_ms4_out".

MS5 addition (design/sim_spec_ms5.md §2.3, C31; §10): the marker
  needs_ms5_out(*files)     defined like needs_ms4_out: skipped if a named file under
                            <MS5_OUT_ROOT>/code/sim/out is missing (the files of every such marker of a test count;
                            a marker without arguments also skips while that folder is missing or empty).
MS5_OUT_ROOT is the repository, overridable with the environment variable SUBLET_MS5_OUT_ROOT. The quick suite
then runs with -m "not needs_raw and not needs_ms2_checks and not needs_ms3_out and not needs_ms4_out and not
needs_ms5_out".

MS5b addition (design/sublet_v2.md §8.3): the marker
  needs_ms5b_out(*files)    defined like needs_ms5_out: skipped if a named file under
                            <MS5B_OUT_ROOT>/code/sim/out is missing (the files of every such marker of a test count;
                            a marker without arguments also skips while that folder is missing or empty).
MS5B_OUT_ROOT is the repository, overridable with the environment variable SUBLET_MS5B_OUT_ROOT. The quick suite then
also leaves out needs_ms5b_out.

Public release: the tests that need files this repository does not include (the manuscript sources, the design notes,
development measurements, prototypes and pilot outputs, the job records of the runs, the history on which the
registered gates check) are listed with the reason in tests/public_release_skips.json and skipped; test_floats_ms7.py
imports the manuscript's tools at module level and is not collected.
"""
import os
import sys
from pathlib import Path

sys.dont_write_bytecode = True       # MS2 §0 rule 5: before any reference module is imported

import pytest

os.environ.setdefault("OMP_NUM_THREADS", "1")

SIM = Path(__file__).resolve().parent
REPO = SIM.parents[1]
C3 = REPO / "code" / "theory_checks" / "c3"
ANALYSIS = REPO / "code" / "analysis"
A12_FILES = ("a12_minute_io.npz", "a12_sim_inputs.json")
DATA = Path("/mnt/data/datasets")

# Moved to the front in reverse, so that the order is code/sim, c3, c3/o1, analysis
# (pytest itself may already have put code/sim on sys.path when importing this file).
for _d in (ANALYSIS, C3 / "o1", C3, SIM):
    while str(_d) in sys.path:
        sys.path.remove(str(_d))
    sys.path.insert(0, str(_d))

# MS2: the C2 reference folders, after the MS1 folders (no module name occurs in both)
C2 = REPO / "code" / "theory_checks" / "c2"
for _d in (C2, C2 / "audit"):
    if str(_d) not in sys.path:
        sys.path.append(str(_d))

MS2_CHECKS_DIR = Path(os.environ.get("SUBLET_MS2_CHECKS_DIR") or (SIM / "out" / "ms2_checks"))
MS3_OUT_ROOT = Path(os.environ.get("SUBLET_MS3_OUT_ROOT") or REPO)
MS3_OUT_DIR = MS3_OUT_ROOT / "code" / "sim" / "out"
MS4_OUT_ROOT = Path(os.environ.get("SUBLET_MS4_OUT_ROOT") or REPO)
MS4_OUT_DIR = MS4_OUT_ROOT / "code" / "sim" / "out"
MS5_OUT_ROOT = Path(os.environ.get("SUBLET_MS5_OUT_ROOT") or REPO)
MS5_OUT_DIR = MS5_OUT_ROOT / "code" / "sim" / "out"
MS5B_OUT_ROOT = Path(os.environ.get("SUBLET_MS5B_OUT_ROOT") or REPO)
MS5B_OUT_DIR = MS5B_OUT_ROOT / "code" / "sim" / "out"


def _ms2_checks_missing(files) -> list[str]:
    if not files:
        ok = MS2_CHECKS_DIR.is_dir() and any(MS2_CHECKS_DIR.iterdir())
        return [] if ok else [str(MS2_CHECKS_DIR)]
    return [f for f in files if not (MS2_CHECKS_DIR / f).is_file()]


def _ms3_out_missing(files, folder: bool = False) -> list[str]:
    """The named files missing under MS3_OUT_DIR, preceded by the folder itself if it is missing or empty and a
    marker has no argument (`folder`, or no file named at all)."""
    miss = []
    if (folder or not files) and not (MS3_OUT_DIR.is_dir() and any(MS3_OUT_DIR.iterdir())):
        miss.append(str(MS3_OUT_DIR))
    return miss + [f for f in files if not (MS3_OUT_DIR / f).is_file()]


def _ms4_out_missing(files, folder: bool = False) -> list[str]:
    """As _ms3_out_missing, under MS4_OUT_DIR (C19)."""
    miss = []
    if (folder or not files) and not (MS4_OUT_DIR.is_dir() and any(MS4_OUT_DIR.iterdir())):
        miss.append(str(MS4_OUT_DIR))
    return miss + [f for f in files if not (MS4_OUT_DIR / f).is_file()]


def _ms5_out_missing(files, folder: bool = False) -> list[str]:
    """As _ms4_out_missing, under MS5_OUT_DIR (C31)."""
    miss = []
    if (folder or not files) and not (MS5_OUT_DIR.is_dir() and any(MS5_OUT_DIR.iterdir())):
        miss.append(str(MS5_OUT_DIR))
    return miss + [f for f in files if not (MS5_OUT_DIR / f).is_file()]


def _ms5b_out_missing(files, folder: bool = False) -> list[str]:
    """As _ms5_out_missing, under MS5B_OUT_DIR (design/sublet_v2.md §8.3)."""
    miss = []
    if (folder or not files) and not (MS5B_OUT_DIR.is_dir() and any(MS5B_OUT_DIR.iterdir())):
        miss.append(str(MS5B_OUT_DIR))
    return miss + [f for f in files if not (MS5B_OUT_DIR / f).is_file()]


def _a12_missing() -> list[str]:
    return [f for f in A12_FILES if not (ANALYSIS / "out" / f).is_file()]


def _raw_readable() -> bool:
    return DATA.is_dir() and os.access(DATA, os.R_OK | os.X_OK)


def pytest_configure(config):
    config.addinivalue_line("markers", "slow: test takes more than 30 s")
    config.addinivalue_line(
        "markers", "needs_a12: needs code/analysis/out/a12_minute_io.npz and a12_sim_inputs.json")
    config.addinivalue_line("markers", "needs_raw: needs readable raw traces in /mnt/data/datasets")
    config.addinivalue_line(
        "markers", "needs_ms2_checks(*files): needs the named files of code/sim/out/ms2_checks/ "
                   "(written by sublet/experiments/run_ms2_checks.sh)")
    config.addinivalue_line(
        "markers", "needs_ms3_out(*files): needs the named files under code/sim/out/ (the MS3 summaries and "
                   "records, written by the run scripts of design/sim_spec_ms3.md §4-§7 and the copy checks)")
    config.addinivalue_line(
        "markers", "needs_ms4_out(*files): needs the named files under code/sim/out/ (the MS4 summaries and "
                   "records, written by the run scripts of design/sim_spec_ms4.md §3-§7 and the copy checks)")
    config.addinivalue_line(
        "markers", "needs_ms5_out(*files): needs the named files under code/sim/out/ (the MS5 summaries and "
                   "records, written by the run scripts of design/sim_spec_ms5.md §3-§8 and the copy checks)")
    config.addinivalue_line(
        "markers", "needs_ms5b_out(*files): needs the named files under code/sim/out/ (the MS5b confirmation's "
                   "summaries and records, written by run_e7h.sh and the copy check; design/sublet_v2.md §8.3)")


def pytest_collection_modifyitems(config, items):
    missing = _a12_missing()
    skip_a12 = pytest.mark.skip(reason=f"missing in code/analysis/out: {', '.join(missing)}") \
        if missing else None
    skip_raw = None if _raw_readable() else pytest.mark.skip(reason=f"{DATA} is not readable")
    for item in items:
        if skip_a12 is not None and item.get_closest_marker("needs_a12"):
            item.add_marker(skip_a12)
        if skip_raw is not None and item.get_closest_marker("needs_raw"):
            item.add_marker(skip_raw)
        mk = item.get_closest_marker("needs_ms2_checks")
        if mk is not None:
            miss = _ms2_checks_missing(mk.args)
            if miss:
                item.add_marker(pytest.mark.skip(
                    reason=f"missing in {MS2_CHECKS_DIR}: {', '.join(miss)} "
                           "(run sublet/experiments/run_ms2_checks.sh)"))
        marks = list(item.iter_markers("needs_ms3_out"))      # a parametrized case may add its own files
        if marks:
            miss = _ms3_out_missing([f for mk in marks for f in mk.args], folder=any(not mk.args for mk in marks))
            if miss:
                item.add_marker(pytest.mark.skip(
                    reason=f"missing in {MS3_OUT_DIR}: {', '.join(miss)} (the MS3 runs, design/sim_spec_ms3.md §1.2)"))
        marks = list(item.iter_markers("needs_ms4_out"))      # MS4 (C19): as needs_ms3_out
        if marks:
            miss = _ms4_out_missing([f for mk in marks for f in mk.args], folder=any(not mk.args for mk in marks))
            if miss:
                item.add_marker(pytest.mark.skip(
                    reason=f"missing in {MS4_OUT_DIR}: {', '.join(miss)} (the MS4 runs, design/sim_spec_ms4.md §1.2)"))
        marks = list(item.iter_markers("needs_ms5_out"))      # MS5 (C31): as needs_ms4_out
        if marks:
            miss = _ms5_out_missing([f for mk in marks for f in mk.args], folder=any(not mk.args for mk in marks))
            if miss:
                item.add_marker(pytest.mark.skip(
                    reason=f"missing in {MS5_OUT_DIR}: {', '.join(miss)} (the MS5 runs, design/sim_spec_ms5.md §1.2)"))
        marks = list(item.iter_markers("needs_ms5b_out"))     # MS5b (design/sublet_v2.md §8.3): as needs_ms5_out
        if marks:
            miss = _ms5b_out_missing([f for mk in marks for f in mk.args], folder=any(not mk.args for mk in marks))
            if miss:
                item.add_marker(pytest.mark.skip(
                    reason=f"missing in {MS5B_OUT_DIR}: {', '.join(miss)} (the MS5b confirmation, design/sublet_v2.md "
                           "§4.3)"))
    _public_release_skips(items)


_PUBLIC_SKIPS = Path(__file__).parent / "tests" / "public_release_skips.json"
_PUBLIC = __import__("json").loads(_PUBLIC_SKIPS.read_text()) if _PUBLIC_SKIPS.is_file() else {"skips": {}, "not_collected": []}
collect_ignore = list(_PUBLIC["not_collected"])


def _public_release_skips(items):
    """Public release: skip the tests listed in tests/public_release_skips.json, with their reason."""
    reasons = {nid: why for why, nids in _PUBLIC["skips"].items() for nid in nids}
    for item in items:
        why = reasons.get(getattr(item, "nodeid", "").split("code/sim/", 1)[-1])
        if why is not None:
            item.add_marker(pytest.mark.skip(reason=why if why.startswith("files edited")
                                             else f"needs {why}, not in the public release"))
