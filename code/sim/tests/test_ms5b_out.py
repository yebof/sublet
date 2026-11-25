"""Tests of the MS5b outputs (design/sublet_v2.md §11, W13 row test_ms5b_out.py and W15; marker needs_ms5b_out): the
claims report sublet/experiments/ms5b_claims.py on the copied confirmation outputs lists no bug and its criterion
holds; the gate, copy, job and run rows hold and the analysis is reproduced; each MS5b figure's and Table III v2's
extract is what its script builds from the copied outputs, with the runs/ files it lists unchanged; every listed job
has an 'ok' record; the copy check of out/sublet_v2/ passed and the copy is unchanged since; the rebuild record
code/sim/out/figs/rebuild.json is that of the MS5b exit run and current.

Each test is skipped while a file it reads under code/sim/out/ is missing: the summaries, analysis.json and the copy
record exist once the confirmation is copied in (§4.3); the extracts once units U37-U39 have run on the copy; the
float heights and the MS5b rebuild record once the exit run of W15 item 5 is copied in. The input root is the
repository, or SUBLET_MS5B_OUT_ROOT (conftest.py), a folder with the repository's layout; the F rows need the run
files runs/, which only the checkout the confirmation was copied into holds: a test that rebuilds an extract listing
runs/ files is skipped where they are absent (a clean clone; the MS6 gate's test record, U47). On a root that holds
the reduced fixture tree tests/fixtures_figs_ms5b/inputs/ the tests that run fail, as they must.
"""
import json
import os
from pathlib import Path

import pytest

from fixtures import SIM

from sublet.experiments import ms5b_claims as cb

ROOT = Path(os.environ.get("SUBLET_MS5B_OUT_ROOT") or SIM.parents[1])
PARTS = cb.PARTS
SUMMARIES = tuple(f"sublet_v2/{p}/summary.json" for p in PARTS)
ANALYSIS = "sublet_v2/analysis.json"
COPY = "ms3_copy_sublet_v2.json"
EXTRACTS = tuple(f"figs/{n}.json" for n, _, _ in cb.F_ENTRIES)
HEIGHTS, REBUILD = "figs/floats_heights_ms5b.json", "figs/rebuild.json"


def _row(cid: str) -> dict:
    return cb._Inputs(ROOT).row(cid)


def _skip_without_runs(names) -> None:
    """Skip when a runs/ file that one of the named extracts lists (W10) is absent under the root: runs/ is not
    versioned, so these F rows rebuild only in the checkout the confirmation was copied into."""
    for n in names:
        p = ROOT / "code/sim/out/figs" / f"{n}.json"
        listed = cb.runs_listed(json.loads(p.read_text())) if p.is_file() else {}
        absent = [r for r in listed if not (ROOT / r).is_file()]
        if absent:
            pytest.skip(f"{len(absent)} runs/ file(s) that {n}.json lists are absent under {ROOT} (runs/ is not "
                        f"versioned; present in the checkout of the copy), e.g. {absent[0]}")


@pytest.mark.needs_ms5b_out(*SUMMARIES, ANALYSIS, COPY, *EXTRACTS, HEIGHTS, REBUILD)
def test_claims_report_lists_no_bug(tmp_path):
    """ms5b_claims on the inputs writes a report (to tmp_path) whose rows are W11's, none a bug, missing or pending,
    every failed hypothesis explained with its registered consequence applied, so that W11's criterion holds; the
    caption drafts of Fig. 4 v2 and Table III v2 have their text and none is from a reduced run."""
    _skip_without_runs(n for n, _, _ in cb.F_ENTRIES)
    rep = cb.build(ROOT, figures=False)
    assert [r["id"] for r in rep["rows"]] == [s.id for s in cb.SPECS]
    bad = [f"{r['id']}: {r['verdict']} ({r['note']})" for r in rep["rows"]
           if r["verdict"] not in cb.OK_VERDICTS + ("explained",)]
    assert not bad, "\n".join(bad)
    assert all(r["explanation"] for r in rep["rows"] if r["verdict"] == "explained")
    assert rep["criterion"]["holds"], rep["criterion"]["text"]
    for name in ("fig4v2", "table3_v2"):
        cap = rep["captions"][name]
        assert cap["text"] and not cap["reduced"] and not cap["notes"], (name, cap["notes"])
    pm, pj = cb.write(rep, tmp_path)
    assert "**bug**" not in pm.read_text() and pj.is_file()


@pytest.mark.needs_ms5b_out(*SUMMARIES, ANALYSIS, COPY)
def test_gates_and_analysis_hold():
    """G-1 to G-5 hold on the copied outputs (the gate at the freeze commit with the pre-registration and the
    analysis script unchanged since, no reduced part and one commit, the copy check, every job and run ok) and A-1 is
    reproduced (analysis.json is what the frozen script computes from the summaries), A-2 holds (the registered
    CONFIG)."""
    bad = []
    for cid in ("G-1", "G-2", "G-3", "G-4", "G-5", "A-1", "A-2"):
        r = _row(cid)
        if r["verdict"] not in ("holds", "reproduced"):
            bad.append(f"{cid}: {r['verdict']} ({r['note']})")
    assert not bad, "\n".join(bad)


@pytest.mark.parametrize("name, cid", [pytest.param(n, f"F-{i}", marks=pytest.mark.needs_ms5b_out(f"figs/{n}.json"))
                                       for i, (n, _, _) in enumerate(cb.F_ENTRIES, 1)])
def test_extracts_are_current(name, cid):
    """The extract code/sim/out/figs/<name>.json is what its script builds from the copied outputs (data and sources),
    every runs/ file it read is listed with its sha256, and each still has it (the F row is reproduced)."""
    _skip_without_runs([name])
    r = _row(cid)
    assert r["regenerated"]["value"] is not None
    assert r["verdict"] == "reproduced", f"{name}: {r['verdict']} ({r['note']}); rerun its script"


@pytest.mark.parametrize("part", [pytest.param(p, marks=pytest.mark.needs_ms5b_out(f"sublet_v2/{p}/manifest.json"))
                                  for p in PARTS])
def test_every_listed_job_ok(part):
    """Every job of the part's job list, and its 'e7h:manifest' and 'e7h:summary' records, has an 'ok' record (an e3
    MILP job stopped at the wall-clock limit or by the cap is allowed under Q39's rule)."""
    r = cb.jobs_block(cb._Inputs(ROOT))["rows"][part]
    assert r["present"] and r["n_listed"] > 0, r.get("note")
    assert r["n_blocking"] == 0 and r["n_unreadable_records"] == 0 and r["n_unlisted_records"] == 0, r["blocking"]


@pytest.mark.needs_ms5b_out(COPY, *SUMMARIES)
def test_copy_check_passed():
    """The copy check of out/sublet_v2/ (python -m sublet.experiments.ms5b_common --check-copy CLONE) passed against
    the clean clone of the summaries' commit, and the copy is unchanged since (G-3)."""
    r = _row("G-3")
    assert r["verdict"] == "holds", r["note"]
    assert r["regenerated"]["value"]["versioned_current"] is True


@pytest.mark.needs_ms5b_out(REBUILD, HEIGHTS)
def test_rebuild_record_is_current():
    """The record of the MS5b exit run (W15 item 5): CHECK=1 in a clean clone, every output identical, the three
    float-height measurements equal, every hand-set file checked, the record current and its entries today's list
    (RB-1)."""
    r = _row("RB-1")
    assert r["verdict"] == "holds", r["note"]
