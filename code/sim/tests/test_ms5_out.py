"""Tests of the MS5 outputs (design/sim_spec_ms5.md §10, row test_ms5_out.py; marker needs_ms5_out, C31): every check
of §3.10, §4.7 and §5.9, read from the copied summaries of S1's two parts and E9 (none from a reduced run), has a
status the spec allows, and the claims report gives it an allowed verdict; the claims report on these inputs lists no
bug (written to tmp_path), SL-1 and RB-1 included; every listed job has an 'ok' record; the copy records
out/ms3_copy_s1.json and ms3_copy_e9.json pass, still match the copy (tree digests) and name one clone commit, the one
§11.2 records; the three MS5 figures redraw from their extracts, and each extract is what its script builds from the
copied summaries (sf_slack: from the analysis outputs); the rebuild record code/sim/out/figs/rebuild.json says every
output identical, covers today's rebuild list and is current.

Each test is skipped while a file it reads under code/sim/out/ is missing, i.e. until the run scripts of §3-§5 have
written their outputs in the clean clone of the MS5 runs, the outputs have been copied into the repository and the
copy checks have run (§1.2), and, for the rebuild record, until the exit run of §1.4 item 5 has been copied. The input
root is the repository, or SUBLET_MS5_OUT_ROOT (conftest.py), a folder with the repository's layout. On a root that
holds the reduced fixture tree tests/fixtures_figs_ms5/inputs/ the tests that run fail where the tree is reduced
(meta.reduced true), as they must.
"""
import importlib
import json
import os
from pathlib import Path

import pytest

from fixtures import SIM

from sublet.experiments import ms3_common as mc
from sublet.experiments import ms5_claims as c5

ROOT = Path(os.environ.get("SUBLET_MS5_OUT_ROOT") or SIM.parents[1])
OUT = ROOT / "code" / "sim" / "out"

# the files under code/sim/out/ that each experiment's rows read
FILES = {"S1": ("s1/sweep/summary.json",), "Q28": ("s1/q28/summary.json",), "E9": ("e9/summary.json",)}
SUMMARIES = tuple(f for fs in FILES.values() for f in fs)
EXTRACTS = tuple(f"figs/{n}.json" for n, _, _ in c5.figure_scripts())
REBUILD = "figs/rebuild.json"
COPIED = {"s1": ("s1/sweep/summary.json", "s1/q28/summary.json"), "e9": ("e9/summary.json",)}


def _read(rel: str) -> dict:
    d = mc.read_json(OUT / rel)
    assert d is not None, f"{OUT / rel} is not a JSON object"
    return d


def _allowed(spec) -> tuple[set, set]:
    """(summary statuses, verdicts) the spec allows for a check: pass for a reproduction or a property check,
    informative for the rows §3.10-§5.9 mark informative (no MS5 check allows 'explained'); for E9-4, whose summary
    status counts an LP above M18's gate as a failure, pass or fail with the report's row holding (§5.9 as amended)."""
    if spec.kind == "informative":
        return {"informative"}, {"informative"}
    if spec.id == "E9-4":       # §5.9 as amended: the summary's own status counts a gated LP as a failure
        return {"pass", "fail"}, {"holds"}
    return {"pass"}, {"reproduced" if spec.kind == "reproduction" else "holds"}


@pytest.mark.parametrize("exp", [pytest.param(e, marks=pytest.mark.needs_ms5_out(*fs)) for e, fs in FILES.items()])
def test_checks_from_the_summaries(exp):
    """Every check of the experiment: its summary is not reduced, its status is one the spec allows, and the claims
    report's row for it is reproduced, holds or informative, never bug, missing or pending."""
    inp = c5.m3._Inputs(ROOT)
    specs = [s for s in c5.SPECS if s.exp == exp]
    assert specs
    bad = []
    for rel in FILES[exp]:
        meta = _read(rel).get("meta") or {}
        if meta.get("reduced") is not False:
            bad.append(f"{rel}: meta.reduced {meta.get('reduced')!r}, not false (a reduced run is never a result)")
    for s in specs:
        statuses, verdicts = _allowed(s)
        S, prob = inp.load(s.summary)
        assert S is not None, f"{s.summary}: {prob}"
        e = (S.get("checks") or {}).get(s.id) or {}
        if e.get("status") not in statuses:
            bad.append(f"{s.id}: summary status {e.get('status')!r}, the spec allows {sorted(statuses)}")
        row = c5.build_row(s, inp)
        if row["verdict"] not in verdicts:
            bad.append(f"{s.id}: verdict {row['verdict']!r} ({row['note']})")
    assert not bad, "\n".join(bad)


@pytest.mark.needs_ms5_out(*SUMMARIES, "figs/sf_slack.json", REBUILD)
def test_claims_report_lists_no_bug(tmp_path):
    """ms5_claims on the inputs writes a report (to tmp_path) whose 16 rows are the spec's, none a bug, missing or
    pending, so that the criterion of §1.4 item 2 holds; the caption drafts of the three figures have their text and
    none is from a reduced run."""
    rep = c5.build(ROOT, figures=False)
    assert [r["id"] for r in rep["rows"]] == [s.id for s in c5.SPECS] and len(rep["rows"]) == 16
    bad = [f"{r['id']}: {r['verdict']} ({r['note']})" for r in rep["rows"] if r["verdict"] not in c5.OK_VERDICTS]
    assert not bad, "\n".join(bad)
    assert rep["criterion"]["holds"], rep["criterion"]["text"]
    for name, cap in rep["captions"].items():
        assert cap["text"] and not cap["reduced"] and not cap["notes"], (name, cap["notes"])
    pm, pj = c5.write(rep, tmp_path)
    assert "**bug**" not in pm.read_text() and pj.is_file()


@pytest.mark.needs_ms5_out("figs/sf_slack.json")
def test_sl1_on_the_versioned_files():
    """SL-1 (§6.3): the versioned slack extract's daily series, without the series' end, equal the report's
    recomputation from code/analysis/out/a1_slack_series.npz within 1e-9, and its source digests are those of the
    versioned files."""
    row = c5.build_row(next(s for s in c5.SPECS if s.id == "SL-1"), c5.m3._Inputs(ROOT))
    assert row["verdict"] == "holds", row["note"]
    assert row["regenerated"]["value"]["n_pools"] == 6 and row["regenerated"]["value"]["digests_equal"] is True


@pytest.mark.needs_ms5_out(*EXTRACTS)
def test_figures_redraw_from_their_extracts(tmp_path, monkeypatch):
    """The three MS5 figure scripts redraw from their extracts with finalize() passing (§1.4 item 1), in a temporary
    folder."""
    import tempfile
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    fg = c5.figures_block(ROOT, OUT / "figs")
    errs = [f"{r['figure']}: {r['status']} {r['error']}" for r in fg["rows"] if r["status"] != "ok"]
    assert len(fg["rows"]) == 3 and not errs, "\n".join(errs)


@pytest.mark.parametrize("name, module", [pytest.param(n, m, marks=pytest.mark.needs_ms5_out(f"figs/{n}.json"))
                                          for n, m, _ in c5.figure_scripts()])
def test_figure_extracts_are_current(name, module, monkeypatch):
    """Each MS5 figure's extract code/sim/out/figs/<name>.json holds what its script builds from the copied summaries
    (sf_slack: from the analysis outputs), data and sources, so that a figure drawn before a rerun, or from partial or
    reduced outputs, fails."""
    from figs.common import json_number
    from figs.inputs import Inputs
    monkeypatch.setenv("SUBLET_FIGS_IN_ROOT", str(ROOT))
    inp = Inputs()
    data = json.loads(json.dumps(importlib.import_module(module).build(inp), allow_nan=False, default=json_number))
    ext = _read(f"figs/{name}.json")
    assert data == ext["data"], f"code/sim/out/figs/{name}.json is not current: rerun python -m {module}"
    assert ext["sources"] == inp.sources
    assert (data.get("meta") or {}).get("reduced") is not True, f"{name} is drawn from a reduced run"


@pytest.mark.parametrize("folder", [pytest.param(f, marks=pytest.mark.needs_ms5_out(f"{f}/manifest.json"))
                                    for f in c5.JOB_FOLDERS])
def test_every_listed_job_ok(folder):
    """Every job of the folder's job list, and its '<exp>:manifest' and '<exp>:summary' records, has an 'ok' record
    (§2.4: only 'ok' counts as done; MS5 has no MILP job)."""
    r = c5.jobs_block(c5.m3._Inputs(ROOT))["rows"][folder]
    assert r["present"] and r["n_listed"] > 0, r.get("note")
    assert r["n_blocking"] == 0 and r["n_unreadable_records"] == 0, r["blocking"]


@pytest.mark.parametrize("exp", [pytest.param(e, marks=pytest.mark.needs_ms5_out(mc.COPY_RECORD.format(exp=e)))
                                 for e in c5.COPY_EXPS])
def test_copy_check_passed(exp):
    """The copy check of §1.2 (python -m sublet.experiments.ms3_common --check-copy EXP CLONE; S1's two parts through
    C30) passed: equal files and sha256, no symbolic link, every JSON file recording the clone's commit, the summaries
    present with 'ok' summary and manifest records, no 'running' record, each part's run log with its done line; the
    copy is unchanged since (tree digests: over the versioned files, and over all files where the run files runs/ are
    present) and holds the experiment's summaries."""
    rec = mc.read_json(OUT / mc.COPY_RECORD.format(exp=exp))
    assert rec is not None and rec["exp"] == exp and rec["check"] == "copy"
    assert rec["pass"] is True and all(rec["checks"].values()), {k: v for k, v in rec["checks"].items() if not v}
    want = {"same_file_list", "same_sha256", "no_symlinks", "json_readable", "revisions", "revisions_recorded",
            "manifest_revision", "summary_ok", "no_running_records", "record_statuses_known", "run_log_done"}
    assert set(rec["checks"]) == want
    assert len(rec["clone_commit"]) == 40 and set(rec["revisions_found"]) == {rec["clone_commit"]}
    assert rec["n_running"] == 0 and all(x["done"] for x in rec["run_logs"].values())
    assert rec["parts"] == list(mc.COPY_PARTS.get(exp, ()))
    assert rec["tree_sha256_versioned"] == mc.tree_digest(OUT / exp, exp), f"out/{exp} changed after its copy check"
    runs = [OUT / exp / p / "runs" for p in mc.COPY_PARTS.get(exp, ("",))]
    if any(r.is_dir() for r in runs):
        assert rec["tree_sha256"] == mc.tree_digest(OUT / exp), f"out/{exp} changed after its copy check: rerun it"
    missing = [f for f in COPIED[exp] if not (OUT / f).is_file()]
    assert not missing, f"files missing in the copy: {missing}"


@pytest.mark.needs_ms5_out(*(mc.COPY_RECORD.format(exp=e) for e in c5.COPY_EXPS))
def test_copy_checks_share_one_commit():
    """S1 and E9 ran in one clean clone at one commit (§1.2), the commit that §11.2 of design/sim_spec_ms5.md records
    for the clone of the MS5 runs."""
    commits = {e: (mc.read_json(OUT / mc.COPY_RECORD.format(exp=e)) or {}).get("clone_commit") for e in c5.COPY_EXPS}
    assert len(set(commits.values())) == 1 and None not in commits.values(), commits
    spec = (SIM.parents[1] / "design" / "sim_spec_ms5.md").read_text(encoding="utf-8")
    assert commits["s1"] in spec, f"the clone commit {commits['s1']} is not the one design/sim_spec_ms5.md §11.2 names"


@pytest.mark.needs_ms5_out(REBUILD)
def test_rebuild_record_every_output_identical():
    """The record of the exit run (§1.4 item 5, §8.4): RB-1 holds (CHECK=1, the full list, a clean clone, every output
    identical, the coverage holding, both float heights equal, the hand-set files unchanged, the record current
    against the versioned files); its entries are today's rebuild list (figs/rebuild.py), so that a figure added
    after the exit run fails; it names the tools and the four font files with their sha256."""
    from figs import rebuild as rb
    row = c5.build_row(next(s for s in c5.SPECS if s.id == "RB-1"), c5.m3._Inputs(ROOT))
    assert row["verdict"] == "holds", row["note"]
    rec = _read(REBUILD)
    assert rec["outputs"] and all(o["identical"] for o in rec["outputs"])
    from figs import style
    leaked = {k: style.FIGURES.pop(k) for k in [k for k in style.FIGURES if k.startswith("test_")]}
    try:                                    # test-only registrations of earlier modules (test_rebuild.py's fixture)
        now = [(e.name, e.kind, list(e.outputs)) for e in rb.entries()]
    finally:
        style.FIGURES.update(leaked)
    assert [(e["name"], e["kind"], e["outputs"]) for e in rec["entries"]] == now, "rerun the exit rebuild (§8.4)"
    assert all(e["run"] for e in rec["entries"] if e["kind"] not in ("hand_set", "record"))
    assert {"python", "numpy", "matplotlib", "pymupdf", "pillow", "poppler", "ghostscript", "pdflatex"} <= \
        set(rec["meta"]["versions"])
    assert len(rec["meta"]["fonts"]) == 4 and all(len(v["sha256"] or "") == 64 for v in rec["meta"]["fonts"].values())
