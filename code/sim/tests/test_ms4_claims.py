"""Tests of the MS4 claims report sublet/experiments/ms4_claims.py (design/sim_spec_ms4.md §1.4 items 1, 2 and 5;
§10, row test_ms4_claims.py). Quick: the inputs are the MS4 fixture tree tests/fixtures_figs_ms4/inputs/ (reduced-mode
driver outputs, README there; its values are not results) and copies of its files in tmp_path, with meta.reduced set
false and check entries changed in the drivers' form; for the figure reruns the MS3 fixture tree and extracts
(tests/fixtures_figs/) and, where they exist, the MS4 fixture extracts tests/fixtures_figs_ms4/<name>.json. Every
output goes under pytest's tmp_path (never into paper/ or code/sim/out/).

- the rows cover every check id of the five spec tables (§3.11, §4.9, §5.7, §6.9, §7.9, parsed from the spec)
  exactly once and in order, with the status labels copied from the spec or the design (each part with a status
  word found there; changing one status word is caught) and the kinds of the spec's verdict column;
- the verdict of each summary status (pass by kind, fail, explained (never allowed in MS4), informative, missing,
  pending, an unknown status, an input that is not JSON), on the copies; E3-7 and E4-5 informative unless they fail;
- the fixture tree as it is (every summary reduced): every row a bug; a reduced main, part, other summary or gate
  makes exactly its rows bugs; a part summary rebuilt after main's (a stale combined entry) makes its rows bugs;
- malformed inputs give bug rows and a written report (no crash); missing summaries give missing rows;
- the jobs block on the fixture's job records and with Q39's MILP rule; the floats block from
  floats_heights_ms4.json; the copy block (one clone commit); the caption drafts;
- the figure reruns (the MS4 script list, the mechanism on an MS3 script, the MS4 scripts on their fixture extracts
  where both exist), written only to a temporary folder; the command line writes only under --out-dir.
"""
import json
import os
import re
import shutil
from pathlib import Path

import pytest

from fixtures import SIM
from test_ms3_claims import STATUS_WORD, _label_part_copied, _norm, _split_top

from sublet.experiments import ms3_claims as m3
from sublet.experiments import ms3_common as mc
from sublet.experiments import ms4_claims as mcl

REPO = SIM.parents[1]
FIX4 = Path(__file__).resolve().parent / "fixtures_figs_ms4"
IN_ROOT = FIX4 / "inputs"
FIX3 = Path(__file__).resolve().parent / "fixtures_figs"
SPEC = REPO / "design" / "sim_spec_ms4.md"
SECTIONS = (("3.11", "E7"), ("4.9", "E3"), ("5.7", "E5"), ("6.9", "E4"), ("7.9", "E8"))
OUT = "code/sim/out"
SUMMARIES = ("e7/main/summary.json", "e7/stress/summary.json", "e7/gap/summary.json", "e7/allow/summary.json",
             "e3/summary.json", "e3/gate.json", "e5/summary.json", "e4/summary.json", "e8/summary.json",
             "e7/table3.json")
INFORMATIVE = {"E7-8", "E7-9", "E7-10", "E7-11", "E7-12", "E3-6", "E3-7", "E5-4", "E5-6", "E4-4", "E4-5", "E4-6",
               "E8-4", "E8-5"}


def spec_table_rows() -> list:
    """(check id, content, verdict cell) of the tables of §3.11, §4.9, §5.7, §6.9 and §7.9, in the spec's order."""
    text = SPEC.read_text(encoding="utf-8")
    rows = []
    for sec, _ in SECTIONS:
        start = text.index(f"\n### {sec} ")
        end = text.index("\n#", start + 1)
        for ln in text[start:end].splitlines():
            m = re.match(r"^\| (E\d+-\d+) \| (.*) \|$", ln)
            if m:
                content, verdict = m.group(2).rsplit(" | ", 1)
                rows.append((m.group(1), content, verdict))
    return rows


def _outputs_snapshot() -> dict:
    """{path: mtime} of the report's default outputs and of every file under paper/figures, paper/supplement,
    paper/floats and code/sim/out/figs (none of which a test may write)."""
    snap = {}
    for d in (REPO / "paper" / "figures", REPO / "paper" / "supplement", REPO / "paper" / "floats",
              SIM / "out" / "figs"):
        for p in sorted(d.rglob("*")) if d.is_dir() else []:
            if p.is_file():
                snap[str(p)] = p.stat().st_mtime_ns
    for name in (mcl.OUT_MD, mcl.OUT_JSON):
        p = SIM / "out" / name
        snap[str(p)] = p.stat().st_mtime_ns if p.exists() else None
    return snap


def _set_reduced(root: Path, rel: str, value: bool) -> None:
    p = root / OUT / rel
    d = json.loads(p.read_text())
    d["meta"]["reduced"] = value
    p.write_text(json.dumps(d))


def _tree(tmp_path, reduced: bool = False) -> Path:
    """A copy of the MS4 fixture tree under tmp_path/in, with meta.reduced set to `reduced` in every summary, the
    gate record and table3.json (the drivers' files otherwise unchanged)."""
    root = tmp_path / "in"
    shutil.copytree(IN_ROOT / OUT, root / OUT)
    for rel in SUMMARIES:
        _set_reduced(root, rel, reduced)
    return root


def _load(root: Path, rel: str) -> dict:
    return json.loads((root / OUT / rel).read_text())


def _save(root: Path, rel: str, obj) -> None:
    p = root / OUT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=1))


def _edit(root: Path, rel: str, cid: str, **fields) -> None:
    d = _load(root, rel)
    d["checks"][cid].update(fields)
    _save(root, rel, d)


def _rows(rep) -> dict:
    return {r["id"]: r for r in rep["rows"]}


# ---------------------------------------------------------------------------------------------------------------
def test_rows_cover_every_spec_check_once_in_order():
    """One row per check id of the five spec tables, each exactly once, in the spec's order (E7, E3, E5, E4, E8),
    with the experiment and section of its table and the documented keys."""
    want = [i for i, _, _ in spec_table_rows()]
    assert len(want) == 36 and len(set(want)) == len(want)
    rep = mcl.build(IN_ROOT, figures=False)
    assert [r["id"] for r in rep["rows"]] == want and [s.id for s in mcl.SPECS] == want
    secs = {exp: f"§{sec}" for sec, exp in SECTIONS}
    assert list(dict.fromkeys(r["experiment"] for r in rep["rows"])) == list(secs)
    keys = {"id", "experiment", "section", "kind", "claim", "status_label", "status_label_note", "reference",
            "regenerated", "summary_status", "verdict", "explanation", "note"}
    for r in rep["rows"]:
        assert r["id"].startswith(r["experiment"] + "-") and r["section"] == secs[r["experiment"]]
        assert set(r) == keys | ({"parts"} if r["experiment"] == "E7" else set())
        assert r["kind"] in ("reproduction", "property", "informative") and r["claim"]["spec"]
        assert set(r["reference"]) == {"value", "values", "file"} and set(r["regenerated"]) == {"value", "file"}
        assert (r["status_label"] is None) == (r["status_label_note"] is not None)
        assert r["verdict"] in mcl.VERDICTS and r["regenerated"]["value"]
    assert set(rep) == {"meta", "criterion", "rows", "floats", "figures", "copy_checks", "jobs", "captions"}


def test_kinds_follow_the_spec_verdict_column():
    """A row is informative exactly where its verdict cell in the spec starts with 'informative'; the reproductions
    are E7-7 (the sweep's 10% cells, 'kept as a reproduction check', §3.7(f)) and E4-1 ('reproduced as R7'); no
    MS4 check allows the verdict 'explained'."""
    spec = {i: v for i, _, v in spec_table_rows()}
    kinds = {s.id: s.kind for s in mcl.SPECS}
    assert {i for i, v in spec.items() if v.startswith("informative")} == INFORMATIVE
    assert {i for i, k in kinds.items() if k == "informative"} == INFORMATIVE
    assert {i for i, k in kinds.items() if k == "reproduction"} == {"E7-7", "E4-1"}
    assert spec["E4-1"].startswith("reproduced as R7")
    assert not any(s.explainable for s in mcl.SPECS) and not any("explained" in v for v in spec.values())


def test_status_labels_are_copied_never_upgraded():
    """Every part of a row's status label that carries a status word is copied from the MS4 spec or
    design/Sublet_design.md, normalized to the drivers' ASCII (test_ms3_claims._label_part_copied); an upgraded copy
    is not found there; the labels of the theory rows are those of §3.1, §4.1 and §6.1."""
    src = _norm(SPEC.read_text(encoding="utf-8") + "\n" + (REPO / "design" / "Sublet_design.md").read_text(
        encoding="utf-8"))
    bad = []
    for s in mcl.SPECS:
        if s.label is None:
            assert s.label_note and not STATUS_WORD.search(s.label_note), s.id
            continue
        for part in _split_top(s.label):
            if STATUS_WORD.search(part) and not _label_part_copied(part, src):
                bad.append(f"{s.id}: {part!r}")
    assert not bad, "labels not copied from the spec or the design:\n" + "\n".join(bad)
    lab = {s.id: s.label for s in mcl.SPECS}
    for cid, old, new in (("E7-1", "(CONJECTURE)", "(PROVEN)"), ("E4-1", "PROVEN; numerically", "PROVEN, audited"),
                          ("E3-6", "PROVEN, elementary", "VERIFIED NUMERICALLY"), ("E7-3", "(PROVEN)", "(CONJECTURE)"),
                          ("E4-2", "PROVEN", "VERIFIED NUMERICALLY")):
        up = lab[cid].replace(old, new, 1)
        assert up != lab[cid] and any(STATUS_WORD.search(p) and not _label_part_copied(p, src)
                                      for p in _split_top(up)), (cid, up)
    assert {i for i, x in lab.items() if x == mcl.W_AB} == {"E7-1", "E3-5", "E5-5"}
    assert lab["E3-4"] == "Proposition M4 (PROVEN)" and lab["E4-2"] == "C3-L10 (PROVEN; numerically checked)"
    assert lab["E4-1"] == "C3-T9 (PROVEN; numerically checked); C3-T11 (PROVEN; numerically checked)"
    assert all(lab[f"E8-{i}"] is None for i in range(1, 6))


@pytest.mark.parametrize("kind, status, explainable, want", [
    ("reproduction", "pass", False, "reproduced"), ("property", "pass", False, "holds"),
    ("informative", "pass", False, "informative"), ("informative", "informative", False, "informative"),
    ("property", "informative", False, "bug"), ("property", "fail", False, "bug"),
    ("reproduction", "fail", False, "bug"), ("informative", "fail", False, "bug"),
    ("property", "explained", False, "bug"), ("property", "explained", True, "explained"),
    ("property", "missing", False, "missing"), ("informative", "missing", False, "missing"),
    ("property", "pending", False, "pending"), ("property", "elsewhere", False, "bug"),
    ("property", "done", False, "bug"), ("property", None, False, "bug"),
])
def test_verdict_of_each_status(kind, status, explainable, want):
    v, note = mcl.verdict(kind, status, explainable)
    assert v == want
    if want == "bug" and status != "fail":
        assert note


def test_fixture_tree_rows_are_all_bugs():
    """The fixture tree as it is: every summary, the gate record and table3.json carry meta.reduced true (a smoke
    run), so every row is a bug, its note names the reduced file, and the criterion does not hold; the summaries'
    own statuses are kept (summary_status)."""
    rep = mcl.build(IN_ROOT, figures=False)
    assert [r["verdict"] for r in rep["rows"]] == ["bug"] * 36
    assert all("from a reduced run" in r["note"] for r in rep["rows"])
    R = _rows(rep)
    assert "code/sim/out/e3/gate.json" in R["E3-7"]["note"] and "e7/stress/summary.json" in R["E7-1"]["note"]
    assert R["E7-1"]["summary_status"] == "pass" and R["E7-8"]["summary_status"] == "informative"
    c = rep["criterion"]
    assert c["holds"] is False and c["counts"]["bug"] == 36 and c["bug"] == [s.id for s in mcl.SPECS]


def test_verdicts_on_an_unreduced_copy(tmp_path):
    """On the copy with meta.reduced false every row is reproduced, holds or informative and the criterion holds;
    the informative rows carry the spec's reading; E7's rows show each part's status."""
    rep = mcl.build(_tree(tmp_path), figures=False)
    R = _rows(rep)
    want = {s.id: ("informative" if s.kind == "informative" else "reproduced" if s.kind == "reproduction"
                   else "holds") for s in mcl.SPECS}
    assert {k: r["verdict"] for k, r in R.items()} == want
    assert rep["criterion"]["holds"] is True and rep["criterion"]["text"].startswith("holds: ")
    assert R["E7-1"]["parts"] == {"main": "pass", "stress": "pass", "gap": "pass", "allow": "pass"}
    assert R["E7-7"]["parts"] == {"allow": "pass"} and R["E7-3"]["parts"] == {"gap": "pass"}
    assert "M38" in R["E7-12"]["note"] and "exact core export" in R["E4-5"]["note"]
    v = R["E7-1"]["regenerated"]["value"]
    assert v["sum(parts.*.n_failures)"] == 0 and set(v["parts.*.certificates.held"]) == set(mcl.E7_PARTS)
    main = _load(tmp_path / "in", "e7/main/summary.json")["checks"]
    assert v["sum(parts.*.n_runs)"] == sum(main["E7-1"]["parts"][p]["n_runs"] for p in mcl.E7_PARTS)
    assert R["E7-3"]["reference"]["values"] == {"parts.gap.tolerance": 1e-6}
    assert R["E3-7"]["reference"]["values"]["grid_config_hash"] == R["E3-7"]["regenerated"]["value"]["config_hash"]
    assert "**Criterion of §1.4 item 2: holds.**" in mcl.markdown(rep)


def test_verdicts_from_the_summaries(tmp_path):
    """The verdict of every status as the summaries write it: fail (in a summary and in main's combined E7 entry),
    missing with the entry's or a part's reason, pending, explained (a bug in MS4), informative on a property row,
    pass on an informative row, a status outside §2.6's vocabulary, E3-7 and E4-5 failing, a summary that is not
    JSON."""
    root = _tree(tmp_path)
    _edit(root, "e3/summary.json", "E3-2", status="fail")
    _edit(root, "e3/summary.json", "E3-7", status="fail", config_hash_equal=False)
    _edit(root, "e5/summary.json", "E5-1", status="missing", why="no run of job e5:run:level=sh1 (test)")
    _edit(root, "e5/summary.json", "E5-2", status="pending", pending=["e5:run:x"])
    _edit(root, "e4/summary.json", "E4-3", status="explained", explanation="a text (test)")
    _edit(root, "e4/summary.json", "E4-1", status="informative")
    _edit(root, "e4/summary.json", "E4-4", status="pass")
    _edit(root, "e4/summary.json", "E4-5", status="fail", bugs_on_exact_exports=[{"run": "x"}])
    _edit(root, "e8/summary.json", "E8-1", status="done")
    m = _load(root, "e7/main/summary.json")
    m["checks"]["E7-4"]["status"] = "fail"
    m["checks"]["E7-5"].update(status="missing", parts={**m["checks"]["E7-5"]["parts"], "gap": {
        "status": "missing", "note": "gap/summary.json is missing or has no entry E7-5"}})
    _save(root, "e7/main/summary.json", m)
    R = _rows(mcl.build(root, figures=False))
    want = {"E3-1": "holds", "E3-2": "bug", "E3-7": "bug", "E5-1": "missing", "E5-2": "pending", "E4-3": "bug",
            "E4-1": "bug", "E4-4": "informative", "E4-5": "bug", "E8-1": "bug", "E7-4": "bug", "E7-5": "missing",
            "E7-6": "holds", "E8-4": "informative"}
    assert {k: R[k]["verdict"] for k in want} == want
    assert "no run of job e5:run:level=sh1" in R["E5-1"]["note"] and "pending: 1" in R["E5-2"]["note"]
    assert "allows no explanation" in R["E4-3"]["note"] and R["E4-3"]["explanation"] is None
    assert "pass condition" in R["E4-1"]["note"] and "spec marks the row informative" in R["E4-4"]["note"]
    assert "vocabulary" in R["E8-1"]["note"] and R["E8-1"]["summary_status"] == "done"
    assert "part gap: missing (gap/summary.json is missing" in R["E7-5"]["note"]
    assert R["E3-7"]["regenerated"]["value"]["config_hash_equal"] is False
    assert R["E4-5"]["regenerated"]["value"]["len(bugs_on_exact_exports)"] == 1
    (root / OUT / "e8" / "summary.json").write_text("{not json")
    rep = mcl.build(root, figures=False)
    R = _rows(rep)
    assert all(R[f"E8-{i}"]["verdict"] == "bug" and "invalid JSON" in R[f"E8-{i}"]["note"] for i in range(1, 6))
    assert rep["meta"]["inputs"][f"{OUT}/e8/summary.json"].startswith("invalid JSON")
    c = rep["criterion"]
    assert c["holds"] is False and c["missing"] == ["E7-5", "E5-1"] and c["pending"] == ["E5-2"]


def test_reduced_summaries_make_exactly_their_rows_bugs(tmp_path):
    """A reduced summary (meta.reduced true) makes each of its rows a bug: E5's summary its six rows; the gate record
    E3-7 only; a part summary of E7 the E7 rows whose combined entry used that part (stress: E7-1, E7-2, E7-4,
    E7-6, E7-8, E7-11, §3.11); main's summary every E7 row. The other rows keep their verdicts."""
    root = _tree(tmp_path)
    _set_reduced(root, "e5/summary.json", True)
    _set_reduced(root, "e3/gate.json", True)
    _set_reduced(root, "e7/stress/summary.json", True)
    R = _rows(mcl.build(root, figures=False))
    bug = {k for k, r in R.items() if r["verdict"] == "bug"}
    stress = {"E7-1", "E7-2", "E7-4", "E7-6", "E7-8", "E7-11"}
    assert bug == {f"E5-{i}" for i in range(1, 7)} | {"E3-7"} | stress
    assert all("reduced run" in R[k]["note"] for k in bug)
    assert "e7/stress/summary.json" in R["E7-8"]["note"] and "e3/gate.json" in R["E3-7"]["note"]
    _set_reduced(root, "e7/main/summary.json", True)
    R = _rows(mcl.build(root, figures=False))
    assert all(R[f"E7-{i}"]["verdict"] == "bug" for i in range(1, 13)) and R["E3-1"]["verdict"] == "holds"


def test_stale_combined_e7_entry_is_a_bug(tmp_path):
    """Main's combined entry copies each part's entry; when a part summary's own entry has since another status (the
    part's summary was rebuilt after main's), the rows that used it are bugs and the note says which part; a part
    whose summary main did not use (its entry not copied) is not compared."""
    root = _tree(tmp_path)
    _edit(root, "e7/gap/summary.json", "E7-3", status="fail")
    R = _rows(mcl.build(root, figures=False))
    assert R["E7-3"]["verdict"] == "bug" and "stale" in R["E7-3"]["note"] and "gap (main copied 'pass'" in \
        R["E7-3"]["note"]
    assert R["E7-1"]["verdict"] == "holds"
    m = _load(root, "e7/main/summary.json")
    m["checks"]["E7-3"].update(status="missing", parts={"gap": {"status": "missing", "note": "not used (test)"}},
                               part_status={"gap": "missing"})
    _save(root, "e7/main/summary.json", m)
    r = _rows(mcl.build(root, figures=False))["E7-3"]
    assert r["verdict"] == "missing" and "stale" not in r["note"] and "not used (test)" in r["note"]


def test_malformed_inputs_give_bug_rows_not_a_crash(tmp_path, monkeypatch):
    """Inputs of a shape the drivers never write give 'bug' rows and a written report: a summary that is valid JSON
    but not an object, a checks block that is not an object, an E7 entry whose fields have other types, and a row
    whose reading raises (a 'bug' row naming the error)."""
    root = _tree(tmp_path)
    (root / OUT / "e5" / "summary.json").write_text("[1, 2]")
    d = _load(root, "e8/summary.json")
    d["checks"] = [1, 2]
    _save(root, "e8/summary.json", d)
    m = _load(root, "e7/main/summary.json")
    m["checks"]["E7-1"]["parts"] = [1, 2]
    m["checks"]["E7-2"] = "pass"
    m["meta"] = [1]
    _save(root, "e7/main/summary.json", m)
    p = _load(root, "e7/stress/summary.json")
    p["checks"] = "x"
    _save(root, "e7/stress/summary.json", p)
    rep = mcl.build(root, figures=False)
    R = _rows(rep)
    assert all(R[f"E5-{i}"]["verdict"] == "bug" and "not an object" in R[f"E5-{i}"]["note"] for i in range(1, 7))
    assert all(R[f"E8-{i}"]["verdict"] == "bug" and "checks is not an object" in R[f"E8-{i}"]["note"]
               for i in range(1, 6))
    assert R["E7-1"]["verdict"] == "holds" and R["E7-1"]["parts"] == {}
    assert R["E7-2"]["verdict"] == "missing" and "no entry checks.E7-2" in R["E7-2"]["note"]
    assert R["E7-4"]["verdict"] == "bug" and "stale" in R["E7-4"]["note"]
    assert mcl.markdown(rep).startswith("# MS4 claims report")

    def boom(entry, fields):
        raise TypeError("a shape the drivers never write (test)")
    monkeypatch.setattr(mcl, "_values", boom)
    rep = mcl.build(root, figures=False)
    assert all(r["verdict"] == "bug" and "do not write" in r["note"] for r in rep["rows"])
    pm, pj = mcl.write(rep, tmp_path / "out")
    assert pm.is_file() and json.loads(pj.read_text())["criterion"]["counts"]["bug"] == 36


def test_missing_summaries_give_missing_rows(tmp_path):
    """On an empty input root every row is 'missing' with the absent file named, the blocks say what is absent,
    and the report is written (no crash)."""
    root = tmp_path / "empty"
    root.mkdir()
    rep = mcl.build(root, figures=False)
    assert [r["verdict"] for r in rep["rows"]] == ["missing"] * 36
    assert all(r["note"] and "missing" in r["note"] for r in rep["rows"])
    assert rep["criterion"]["holds"] is False and "36 missing row(s)" in rep["criterion"]["text"]
    assert rep["floats"]["present"] is False and rep["floats"]["rows"] == []
    assert list(rep["copy_checks"]["records"]) == list(mcl.COPY_EXPS) and rep["copy_checks"]["one_commit"] is None
    assert all(not e["present"] for e in rep["copy_checks"]["records"].values())
    assert all(not r["present"] for r in rep["jobs"]["rows"].values()) and \
        rep["jobs"]["note"].startswith("no job list")
    assert rep["captions"]["fig4"]["text"] is None and rep["captions"]["table3"]["certificates"] is None
    pm, pj = mcl.write(rep, tmp_path / "out")
    assert pm.is_file() and json.loads(pj.read_text())["criterion"]["counts"]["missing"] == 36


def test_jobs_block_on_the_fixture_records():
    """The jobs block reads each MS4 folder's job list and records: on the fixture tree every listed job of the
    eight folders (E7's four parts each with their own records) has an 'ok' record, the counts are the manifests'
    and the summaries' meta lists are counted."""
    jb = mcl.build(IN_ROOT, figures=False)["jobs"]
    assert list(jb["rows"]) == list(mcl.JOB_FOLDERS) and jb["n_blocking"] == 0
    for folder, r in jb["rows"].items():
        man = json.loads((IN_ROOT / OUT / folder / "manifest.json").read_text())
        assert r["present"] and r["n_listed"] == len(man["jobs"]) and r["by_status"] == {"ok": r["n_listed"] + 2}
        assert r["n_unlisted_records"] == 0 and r["n_unreadable_records"] == 0 and r["summary_ignored_outputs"] == 0
    assert jb["rows"]["e8"]["summary_outputs_missing"] == 0 and jb["rows"]["e3"]["summary_jobs_missing"] is None
    assert jb["note"].startswith("every listed job has an 'ok' record")


def test_jobs_block_with_q39s_milp_rule(tmp_path):
    """Jobs without an 'ok' record outside Q39's rule are blocking (a failed pool job, a MILP job that failed, a
    listed job without a record, a failed summary record); a MILP job whose output is a lower bound (E3's MILPs, E4's
    OPT_eager) stopped at the wall-clock limit or by the cap is listed apart (LB = LP, §2.5), an E4 P-hat day job so
    stopped is blocking (a plan, not a bound); unlisted and unreadable records are counted; the rows' verdicts do
    not change."""
    root = _tree(tmp_path)
    before = [r["verdict"] for r in mcl.build(root, figures=False)["rows"]]
    jobs = root / OUT / "e3" / "jobs"

    def setst(jid, st):
        p = jobs / mc.job_file_name(jid)
        d = json.loads(p.read_text())
        d["status"] = st
        p.write_text(json.dumps(d))
    setst("e3:milp:b=8:u=8:mu=1:c=1:part=shared", "wall_limit")
    setst("e3:milp:b=8:u=8:mu=1:c=1:part=b01", "oom_at_3G")
    setst("e3:milp:b=8:u=8:mu=1:c=1:part=b02", "failed")
    setst("e3:cell:b=1:u=8:mu=1:c=1", "oom_at_3G")
    setst("e3:summary", "failed")
    (jobs / mc.job_file_name("e3:gate")).unlink()
    (jobs / "e3__old__x__1.json").write_text(json.dumps({"job": "e3:old:x=1", "status": "ok"}))
    (jobs / "broken.json").write_bytes(b"\xff")
    rep = mcl.build(root, figures=False)
    r = rep["jobs"]["rows"]["e3"]
    assert [(x["job"], x["status"]) for x in r["blocking"]] == [
        ("e3:cell:b=1:u=8:mu=1:c=1", "oom_at_3G"), ("e3:milp:b=8:u=8:mu=1:c=1:part=b02", "failed"),
        ("e3:gate", "no record"), ("e3:summary", "failed")]
    assert [x["job"] for x in r["milp_lp_fallback"]] == ["e3:milp:b=8:u=8:mu=1:c=1:part=shared",
                                                         "e3:milp:b=8:u=8:mu=1:c=1:part=b01"]
    assert r["by_status"] == {"failed": 2, "no record": 1, "ok": 20, "oom_at_3G": 2, "wall_limit": 1}
    assert r["n_unlisted_records"] == 1 and r["n_unreadable_records"] == 1
    assert rep["jobs"]["n_blocking"] == 4 and rep["jobs"]["note"].startswith("4 listed job(s) without an 'ok'")
    assert [x["verdict"] for x in rep["rows"]] == before
    md = mcl.markdown(rep)
    assert "- e3: `e3:cell:b=1:u=8:mu=1:c=1` (pool, oom_at_3G); `e3:milp:b=8:u=8:mu=1:c=1:part=b02` (milp, failed)" \
        in md
    # E4: OPT_eager's MILP (a lower bound) falls under Q39's rule; a P-hat day job (kind milp, a plan) does not
    jobs4 = root / OUT / "e4" / "jobs"
    for jid, st in (("e4:eager:panel=azure:c=1", "wall_limit"),
                    ("e4:phat:panel=azure:c=1:mu=1:pred=prev:day=1", "wall_limit")):
        q = jobs4 / mc.job_file_name(jid)
        d = json.loads(q.read_text())
        d["status"] = st
        q.write_text(json.dumps(d))
    r4 = mcl.build(root, figures=False)["jobs"]["rows"]["e4"]
    assert [x["job"] for x in r4["milp_lp_fallback"]] == ["e4:eager:panel=azure:c=1"]
    assert [(x["job"], x["kind"]) for x in r4["blocking"]] == [("e4:phat:panel=azure:c=1:mu=1:pred=prev:day=1", "milp")]


def test_floats_block_reads_floats_heights_ms4(tmp_path):
    """Table III's measured height next to its 0.125-page budget, read from floats_heights_ms4.json (C21): within
    the budget, above it (the note gives M27's order of steps), and a record without table3_e7; absent: noted."""
    root = _tree(tmp_path)
    fl = mcl.build(root, figures=False)["floats"]
    assert fl["present"] is False and "floats_heights.py --ms4" in fl["note"]
    rec = {"source": "paper/floats/table3_e7.tex", "measured_pages": 0.1201, "budget_pages": 0.125,
           "within_budget": True, "difference_pages": -0.0049}
    _save(root, "figs/floats_heights_ms4.json", {"floats": {"table3_e7": rec}, "probes": {}})
    rep = mcl.build(root, figures=False)
    fl = rep["floats"]
    assert fl["rows"] == [{"float": "Table III", "name": "table3_e7", **{k: rec[k] for k in (
        "measured_pages", "budget_pages", "within_budget", "difference_pages", "source")}}]
    assert fl["note"] == "Table III within its budget"
    assert "Floats (§1.4 item 5): Table III 0.1201 page (budget 0.125)" in mcl.markdown(rep)
    _save(root, "figs/floats_heights_ms4.json", {"floats": {"table3_e7": {
        **rec, "measured_pages": 0.144, "within_budget": False, "difference_pages": 0.019}}})
    fl = mcl.build(root, figures=False)["floats"]
    assert "exceeds its budget by 0.019 page" in fl["note"] and "M27" in fl["note"]
    assert "§1.5 item 9" in fl["note"] and "all six data columns stay" in fl["note"]
    assert "excess comes out of the page reserve" in fl["note"]
    assert "steps are done" in fl["note"] and "then merge" not in fl["note"]
    _save(root, "figs/floats_heights_ms4.json", {"floats": {"table2_policies": rec}})
    assert "records no table3_e7" in mcl.build(root, figures=False)["floats"]["note"]


def test_copy_block_reads_the_copy_records(tmp_path):
    """The copy block lists out/ms3_copy_<exp>.json of e3, e4, e5, e7 and e8 (pass, the clone's commit, the failed
    checks, E7's parts); an invalid record is noted; the records name one clone commit or several."""
    root = _tree(tmp_path)
    a, b = "a" * 40, "b" * 40
    ok = {"check": "copy", "pass": True, "clone_commit": a, "time": "2026-12-01T09:00:00",
          "checks": {"same_sha256": True, "run_log_done": True}, "records_by_status": {"ok": 3}}
    _save(root, "ms3_copy_e3.json", {**ok, "exp": "e3", "parts": []})
    _save(root, "ms3_copy_e7.json", {**ok, "exp": "e7", "parts": list(mcl.E7_PARTS)})
    (root / OUT / "ms3_copy_e4.json").write_text("{")
    cp = mcl.build(root, figures=False)["copy_checks"]
    assert cp["records"]["e7"] == {"file": f"{OUT}/ms3_copy_e7.json", "present": True, "pass": True,
                                   "exp_matches": True, "commit": a, "time": "2026-12-01T09:00:00", "failed": [],
                                   "parts": list(mcl.E7_PARTS), "records_by_status": {"ok": 3}}
    assert cp["records"]["e4"]["present"] is False and cp["records"]["e4"]["note"].startswith("invalid JSON")
    assert cp["commits"] == [a] and cp["one_commit"] is True and "every present record passes" in cp["note"]
    _save(root, "ms3_copy_e5.json", {**ok, "exp": "e4", "pass": False, "clone_commit": b,
                                     "checks": {"same_sha256": False, "run_log_done": True}})
    cp = mcl.build(root, figures=False)["copy_checks"]
    e5 = cp["records"]["e5"]
    assert e5["pass"] is False and e5["exp_matches"] is False and e5["failed"] == ["same_sha256"]
    assert cp["commits"] == [a, b] and cp["one_commit"] is False and "failed: e5" in cp["note"]


def test_caption_drafts(tmp_path):
    """Fig. 4's caption draft of §8.1, with every number read from the summaries: own capacity (the median over the
    alignments of meta.own_capacity_usd, whole USD with a separator), the alignments and policy seeds of meta.grids,
    E3's u; at most 3 x 140 characters; drafted by figs.fig4_e7_e3.caption, so that it is the figure extract's
    labels.caption on the same inputs; Table III's certificate line from table3.json's caption; on the reduced
    fixture the notes say so; without the inputs no draft."""
    root = _tree(tmp_path)
    m = _load(root, "e7/main/summary.json")
    m["meta"]["own_capacity_usd"] = {"1": 145715.69, "2": 145000.2, "3": 146000.0, "4": 144000.0}
    m["meta"]["grids"].update(alignments=[1, 2, 3, 4], policy_seeds=[0, 1, 2])
    _save(root, "e7/main/summary.json", m)
    cap = mcl.build(root, figures=False)["captions"]
    f4 = cap["fig4"]
    assert "own capacity, 145,358 USD per week" in f4["text"] and "over 4 alignments × 3 seeds" in f4["text"]
    assert "(u = 8)" in f4["text"] and f4["n_chars"] == len(f4["text"]) == 417 and f4["within_limit"] is True
    assert "Grey: b, the bound on siloed OPT (stars;" in f4["text"]
    assert f4["notes"] == [] and f4["values"]["own_capacity_usd"] == pytest.approx(145357.945)
    t3 = cap["table3"]
    c = _load(root, "e7/table3.json")["caption"]["certificates"]
    assert t3["certificates"] == (f"certificate held in {c['held']} of {c['n']} A8 runs (W(a) "
                                  f"{c['by_case']['W(a)']['runs']}, W(b) {c['by_case']['W(b)']['runs']}, W(c) "
                                  f"{c['by_case']['W(c)']['runs']})")
    assert t3["B0_rule"] == "0.1*BL0a" and t3["notes"] == []
    cap = mcl.build(IN_ROOT, figures=False)["captions"]
    assert cap["fig4"]["text"] and "reduced run" in cap["fig4"]["notes"][0] and "reduced" in cap["table3"]["notes"][0]
    fig4 = json.loads((FIX4 / "fig4.json").read_text())["data"]["labels"]
    assert cap["fig4"]["text"] == fig4["caption"] and "over 1 alignment × 1 seed." in fig4["caption"]


def test_figure_scripts_are_the_ms4_figures():
    """The figure block reruns the nine MS4 scripts: Fig. 4 and the eight supplementary figures of §8.2 (the names
    of style.SUPP_POLICIES_MS4, without sf_e3_u, M41), never an MS3 script; MS3's own list is unchanged (C17)."""
    from figs import style
    got = mcl.figure_scripts()
    names = [n for n, _, _ in got]
    assert names == ["fig4"] + sorted(style.SUPP_POLICIES_MS4) and "fig4" in style.FIGURES
    assert [s for _, _, s in got] == ["figs/fig4_e7_e3.py"] + [f"figs/supp/{n}.py" for n in names[1:]]
    assert all(mod == s[:-3].replace("/", ".") for _, mod, s in got)
    assert not {n for n, _, _ in m3.figure_scripts()} & set(names) and len(m3.figure_scripts()) == 20


def test_figure_reruns_mechanism(tmp_path, monkeypatch):
    """figures_block reruns a script from its extract in this process (here MS3's fig5 on the MS3 fixtures), lists
    its small glyphs (none at C62's scale), lists a figure without an extract as 'missing', a missing script and a
    script that draws another figure as 'error', writes nothing into paper/ or code/sim/out/figs/, removes its temporary
    folder and restores the environment; an unknown name in --only raises."""
    import tempfile
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path / "tmp"))
    (tmp_path / "tmp").mkdir()
    for k in mcl.ENV_FIG_DIRS + (mcl.ENV_IN_ROOT,):
        monkeypatch.delenv(k, raising=False)
    before = _outputs_snapshot()
    fig5 = ("fig5", "figs.fig5_e1_e10", "figs/fig5_e1_e10.py")
    scripts = [fig5, ("fig6", "figs.fig6_e10", "figs/fig6_e10.py"), ("sf_x", "figs.supp.sf_x", "figs/supp/sf_x.py"),
               ("fig4", "figs.fig5_e1_e10", "figs/fig5_e1_e10.py")]
    ext = tmp_path / "ext"
    ext.mkdir()
    shutil.copy(FIX3 / "fig5.json", ext / "fig5.json")
    shutil.copy(FIX3 / "fig5.json", ext / "fig4.json")
    fg = mcl.figures_block(FIX3 / "inputs", ext, scripts=scripts)
    by = {r["figure"]: r for r in fg["rows"]}
    from figs import style                         # C62: tick labels at 7 pt, axis labels and letters at 7.97 pt
    assert by["fig5"]["status"] == "ok" and by["fig5"]["n_small_glyphs"] == 0
    assert set(by["fig5"]["text_pt"]) == {style.TICK_PT, style.LABEL_PT}
    assert by["fig6"]["status"] == "missing" and by["sf_x"]["status"] == "error" and "missing" in by["sf_x"]["error"]
    assert by["fig4"]["status"] == "error" and "draws 'fig5'" in by["fig4"]["error"]
    assert fg["counts"] == {"ok": 1, "missing": 1, "error": 2}
    with pytest.raises(ValueError, match="no figure script"):
        mcl.figures_block(FIX3 / "inputs", ext, ["fig1"])
    assert _outputs_snapshot() == before and list((tmp_path / "tmp").iterdir()) == []
    assert all(k not in os.environ for k in mcl.ENV_FIG_DIRS + (mcl.ENV_IN_ROOT,))
    fg = mcl.figures_block(FIX3 / "inputs", tmp_path / "none", scripts=[fig5])
    assert fg["rows"][0]["status"] == "missing"
    md = mcl.markdown({**mcl.build(IN_ROOT, figures=False), "figures": mcl.figures_block(FIX3 / "inputs", ext,
                                                                                          scripts=[fig5])})
    assert "| fig5 | `figs/fig5_e1_e10.py` | ok | 0 | none |" in md and "1 of 1 redrawn from their extracts" in md


@pytest.mark.parametrize("name", [n for n, _ in mcl.MS4_FIGURE_SCRIPTS])
def test_ms4_figures_redraw_from_their_fixture_extracts(name, tmp_path, monkeypatch):
    """Each MS4 figure script redraws from its fixture extract tests/fixtures_figs_ms4/<name>.json in the figure
    block (finalize() passing; small glyphs listed), outputs only in a temporary folder; skipped while the script
    or its fixture extract does not exist (U25's figure scripts are built beside this module)."""
    script = dict(mcl.MS4_FIGURE_SCRIPTS)[name]
    if not (SIM / script).is_file() or not (FIX4 / f"{name}.json").is_file():
        pytest.skip(f"{script} or tests/fixtures_figs_ms4/{name}.json not there yet")
    import tempfile
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    before = _outputs_snapshot()
    fg = mcl.figures_block(IN_ROOT, FIX4, [name])
    assert fg["rows"][0]["status"] == "ok", fg["rows"][0]["error"]
    assert _outputs_snapshot() == before


def test_command_line_writes_only_under_out_dir(tmp_path, capsys):
    """--root with --out-dir writes ms4_claims.md and ms4_claims.json there (exit 0) and nothing into the
    repository; another root without --out-dir is an error; the JSON has the documented blocks."""
    before = _outputs_snapshot()
    out = tmp_path / "report"
    assert mcl.main(["--root", str(IN_ROOT), "--out-dir", str(out), "--no-figures"]) == 0
    assert sorted(p.name for p in out.iterdir()) == ["ms4_claims.json", "ms4_claims.md"]
    rep = json.loads((out / "ms4_claims.json").read_text())
    assert rep["meta"]["input_root"] == str(IN_ROOT.resolve()) and rep["meta"]["out_dir"] == str(out.resolve())
    assert rep["meta"]["input_root_is_repository"] is False and rep["figures"]["run"] is False
    assert rep["meta"]["module"] == "sublet.experiments.ms4_claims" and rep["meta"]["spec"].startswith(mcl.SPEC_DOC)
    md = (out / "ms4_claims.md").read_text()
    assert md.startswith("# MS4 claims report") and "**Criterion of §1.4 item 2: does not hold.**" in md
    assert "not the repository" in md and "not rerun (--no-figures)" in md and "## Caption drafts" in md
    assert "criterion does not hold" in capsys.readouterr().out
    with pytest.raises(SystemExit) as e:
        mcl.main(["--root", str(IN_ROOT), "--no-figures"])
    assert e.value.code == 2
    assert _outputs_snapshot() == before
