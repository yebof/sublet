"""Tests of the MS5 claims report sublet/experiments/ms5_claims.py (design/sim_spec_ms5.md §1.4 items 1, 2 and 5, §9;
§10, row test_ms5_claims.py). Quick: the inputs are the MS5 fixture tree tests/fixtures_figs_ms5/inputs/ (reduced-mode
driver outputs, README there; its values are not results) and copies of it in tmp_path, with meta.reduced set false and
check entries changed in the drivers' form, the fixture extracts tests/fixtures_figs_ms5/<name>.json (sf_slack's is
consistent with the tree's npz slice), and synthetic rebuild records in figs/rebuild.py's form. Every output goes under
pytest's tmp_path (never into paper/ or code/sim/out/).

- the rows cover every check id of the five spec tables (§3.10, §4.7, §5.9, §6.3, §8.4, parsed from the spec) exactly
  once and in order, with the kinds of the spec's verdict column and the status labels copied from the spec or the
  design;
- the verdict of each summary status; the fixture tree as it is (every summary reduced): every summary row a bug, SL-1
  and RB-1 missing; a reduced summary makes exactly its rows bugs; missing and malformed inputs;
- SL-1 recomputed from the npz (holds on the fixture extract, fails on a changed value, a changed digest or a missing
  pool, missing without the npz); RB-1 from the rebuild record (holds on a passing exit-run record; each condition of
  §8.4 and a stale record make it a bug);
- the jobs block on the fixture's job records, the copy block, the rebuild block and the caption drafts;
- the figure reruns of the three MS5 scripts on their fixture extracts, written only to a temporary folder; the
  command line writes only under --out-dir.
"""
import copy
import hashlib
import json
import re
import shutil
from pathlib import Path

import numpy as np
import pytest

from fixtures import SIM
from test_ms3_claims import STATUS_WORD, _label_part_copied, _norm, _split_top

from figs import style
from sublet.experiments import ms3_claims as m3
from sublet.experiments import ms3_common as mc
from sublet.experiments import ms5_claims as c5

REPO = SIM.parents[1]
FIX5 = Path(__file__).resolve().parent / "fixtures_figs_ms5"
IN_ROOT = FIX5 / "inputs"
SPEC = REPO / "design" / "sim_spec_ms5.md"
SECTIONS = (("3.10", "S1"), ("4.7", "Q28"), ("5.9", "E9"), ("6.3", "SL"), ("8.4", "RB"))
OUT = "code/sim/out"
SUMMARIES = ("s1/sweep/summary.json", "s1/q28/summary.json", "e9/summary.json")
INFORMATIVE = {"S1-4", "Q28-4", "E9-5"}


def spec_table_rows() -> list:
    """(check id, content, verdict cell) of the tables of §3.10, §4.7, §5.9, §6.3 and §8.4, in the spec's order."""
    text = SPEC.read_text(encoding="utf-8")
    rows = []
    for sec, _ in SECTIONS:
        start = text.index(f"\n### {sec} ")
        end = text.index("\n#", start + 1)
        for ln in text[start:end].splitlines():
            m = re.match(r"^\| ((?:S1|Q28|E9|SL|RB)-\d+) \| (.*) \|$", ln)
            if m:
                content, verdict = m.group(2).rsplit(" | ", 1)
                rows.append((m.group(1), content, verdict))
    return rows


def _tree(tmp_path, reduced: bool = False, slack: bool = True) -> Path:
    """A copy of the MS5 fixture tree under tmp_path/in with meta.reduced set to `reduced` in the three summaries, and
    (`slack`) the fixture extract of sf_slack, built from the tree's npz slice, at code/sim/out/figs/sf_slack.json."""
    root = tmp_path / "in"
    shutil.copytree(IN_ROOT / "code", root / "code")
    for rel in SUMMARIES:
        d = _load(root, rel)
        d["meta"]["reduced"] = reduced
        _save(root, rel, d)
    if slack:
        (root / OUT / "figs").mkdir(parents=True, exist_ok=True)
        shutil.copy(FIX5 / "sf_slack.json", root / OUT / "figs" / "sf_slack.json")
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


def _sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def _record(root: Path) -> dict:
    """A rebuild record of a passing exit run (figs/rebuild.py's fields that RB-1 reads), whose one compared output is
    the tree's sf_slack extract."""
    rel = f"{OUT}/figs/sf_slack.json"
    sha = _sha(root / rel)
    hand = [{"path": p, "ok": True} for p in ("paper/floats/table1_price_of_revocation.tex",
                                              "paper/floats/table2_policies.tex", "paper/floats/alg1_guard.tex",
                                              f"{OUT}/figs/print_check.md")]
    return {"status": "pass", "pass": True, "error": None, "reasons": [],
            "meta": {"module": "figs.rebuild", "mode": "check", "only": None, "root_is_repository": True,
                     "git_revision": "0" * 40, "tracked_files_dirty": False, "written": "2026-11-30T12:00:00",
                     "versions": {"python": "3.12.3"}, "fonts": {"STIXGeneral": {"path": "/x", "sha256": "0" * 64}}},
            "coverage": {"ok": True, "unlisted": [], "missing": [], "errors": []},
            "outputs": [{"path": rel, "entry": "sf_slack", "sha256": sha, "versioned_sha256": sha, "identical": True,
                         "written": True}],
            "heights": {"plain": {"equal": True}, "ms4": {"equal": True}}, "hand_set": hand, "unexpected": [],
            "repo_check": {"changed": []},
            "totals": {"n_scripts": 36, "n_ok": 36, "failed": [], "n_outputs": 1, "n_identical": 1, "different": [],
                       "not_written": [], "heights_equal": {"plain": True, "ms4": True}}}


# ---------------------------------------------------------------------------------------------------------------
def test_rows_cover_every_spec_check_once_in_order():
    """One row per check id of the five spec tables (16, §9), each once, in the spec's order, with the experiment and
    section of its table and the documented keys."""
    want = [i for i, _, _ in spec_table_rows()]
    assert len(want) == 16 and len(set(want)) == len(want)
    rep = c5.build(IN_ROOT, figures=False)
    assert [r["id"] for r in rep["rows"]] == want and [s.id for s in c5.SPECS] == want
    secs = {exp: f"§{sec}" for sec, exp in SECTIONS}
    assert list(dict.fromkeys(r["experiment"] for r in rep["rows"])) == list(secs)
    keys = {"id", "experiment", "section", "kind", "claim", "status_label", "status_label_note", "reference",
            "regenerated", "summary_status", "verdict", "explanation", "note"}
    for r in rep["rows"]:
        assert r["id"].startswith(r["experiment"] + "-") and r["section"] == secs[r["experiment"]]
        assert set(r) == keys and r["kind"] in ("reproduction", "property", "informative") and r["claim"]["spec"]
        assert set(r["reference"]) == {"value", "values", "file"} and set(r["regenerated"]) == {"value", "file"}
        assert (r["status_label"] is None) == (r["status_label_note"] is not None)
        assert r["verdict"] in c5.VERDICTS and r["regenerated"]["value"]
    assert set(rep) == {"meta", "criterion", "rows", "figures", "copy_checks", "jobs", "rebuild", "captions"}


def test_kinds_follow_the_spec_verdict_column():
    """A row is informative exactly where its verdict cell starts with 'informative', the one reproduction is S1-0
    ('reproduced or bug'), and no MS5 check allows the verdict 'explained'."""
    spec = {i: v for i, _, v in spec_table_rows()}
    kinds = {s.id: s.kind for s in c5.SPECS}
    assert {i for i, v in spec.items() if v.startswith("`informative`")} == INFORMATIVE
    assert {i for i, k in kinds.items() if k == "informative"} == INFORMATIVE
    assert {i for i, v in spec.items() if v.startswith("`reproduced`")} == {"S1-0"}
    assert {i for i, k in kinds.items() if k == "reproduction"} == {"S1-0"}
    assert not any(s.explainable for s in c5.SPECS) and not any("explained" in v for v in spec.values())
    assert {s.id for s in c5.SPECS if s.compute is not None} == {"E9-4", "SL-1", "RB-1"}


def test_status_labels_are_copied_never_upgraded():
    """Every part of a status label that carries a status word is copied from the MS5 spec or the design (normalized
    as test_ms3_claims does); the three certificate rows carry Theorem W's label, every other row none; an upgraded
    label is not found."""
    src = _norm(SPEC.read_text(encoding="utf-8") + "\n" + (REPO / "design" / "Sublet_design.md").read_text(
        encoding="utf-8"))
    bad = []
    for s in c5.SPECS:
        if s.label is None:
            assert s.label_note and not STATUS_WORD.search(s.label_note), s.id
            continue
        for part in _split_top(s.label):
            if STATUS_WORD.search(part) and not _label_part_copied(part, src):
                bad.append(f"{s.id}: {part!r}")
    assert not bad, "\n".join(bad)
    assert {s.id for s in c5.SPECS if s.label is not None} == {"S1-2", "Q28-3", "E9-3"}
    assert all(s.label == c5.W_AB for s in c5.SPECS if s.label is not None)
    up = c5.W_AB.replace("(CONJECTURE)", "(PROVEN)")
    assert any(STATUS_WORD.search(p) and not _label_part_copied(p, src) for p in _split_top(up))


@pytest.mark.parametrize("kind, status, want", [
    ("reproduction", "pass", "reproduced"), ("property", "pass", "holds"), ("informative", "pass", "informative"),
    ("informative", "informative", "informative"), ("property", "informative", "bug"), ("property", "fail", "bug"),
    ("reproduction", "fail", "bug"), ("informative", "fail", "bug"), ("property", "explained", "bug"),
    ("property", "missing", "missing"), ("informative", "missing", "missing"), ("property", "pending", "pending"),
    ("property", "elsewhere", "bug"), ("property", None, "bug"), ("property", "bug_input", "bug"),
])
def test_verdict_of_each_status(kind, status, want):
    v, note = c5.verdict(kind, status)
    assert v == want
    if want == "bug" and status not in ("fail", "bug_input"):
        assert note


def test_fixture_tree_rows_are_all_bugs():
    """The fixture tree as it is: the three summaries carry meta.reduced true (a smoke run), so each of their 14 rows
    is a bug whose note names the reduced file; the tree has no slack extract and no rebuild record, so SL-1 and RB-1
    are missing; the criterion does not hold; the summaries' own statuses are kept."""
    rep = c5.build(IN_ROOT, figures=False)
    rows = _rows(rep)
    for s in c5.SPECS:
        r = rows[s.id]
        if s.compute is None or s.id == "E9-4":       # E9-4 is computed from E9's (reduced) summary
            assert r["verdict"] == "bug" and "reduced run" in r["note"] and s.summary in r["note"], s.id
        else:
            assert r["verdict"] == "missing" and "missing" in r["note"], s.id
    assert rows["S1-0"]["summary_status"] == "fail" and rows["S1-1"]["summary_status"] == "pass"
    assert rows["E9-5"]["summary_status"] == "informative"
    c = rep["criterion"]
    assert not c["holds"] and len(c["bug"]) == 14 and c["missing"] == ["SL-1", "RB-1"]


def test_e9_4_lists_gated_lps(tmp_path):
    """E9-4 as amended (§5.9): on an unreduced copy, an LP whose only problem is M18's gate is listed as gated and the
    row holds although the summary's own status is 'fail'; an LP that is not optimal for another reason, a failed LP
    job, a truncated list, and no LP make it a bug or missing; a reduced summary makes it a bug."""
    root = _tree(tmp_path)
    e = _load(root, "e9/summary.json")["checks"]["E9-4"]
    gate = {"job": "e9:lp:pt=e7r_V32_SML:c=2",
            "problems": ["the LP rule's estimate 2838 MB is not under the gate 2800 MB (M18)"]}
    spec = next(s for s in c5.SPECS if s.id == "E9-4")
    base = {**e, "status": "fail", "n_failed": 0, "n_missing": 0, "n_lps": 28}
    for name, change, want in (
            ("gated", dict(not_optimal=[gate], n_not_optimal=1), "holds"),
            ("other", dict(not_optimal=[gate, {"job": "x", "problems": ["status 4 (time limit)"]}],
                           n_not_optimal=2), "bug"),
            ("gate and more", dict(not_optimal=[{**gate, "problems": gate["problems"] + ["peak 3100 MB"]}],
                                   n_not_optimal=1), "bug"),
            ("truncated", dict(not_optimal=[gate], n_not_optimal=3), "bug"),
            ("failed job", dict(not_optimal=[gate], n_not_optimal=1, n_failed=1), "bug"),
            ("no lp", dict(not_optimal=[], n_not_optimal=0, n_lps=0, status="missing"), "missing")):
        _edit(root, "e9/summary.json", "E9-4", **{**base, **change})
        r = c5.build_row(spec, c5.m3._Inputs(root))          # _Inputs reads each file once
        assert r["verdict"] == want, (name, r["note"])
        if name == "gated":
            v = r["regenerated"]["value"]
            assert v["n_gated"] == 1 and v["gated"] == [gate["job"]] and v["summary_status"] == "fail"
            assert "gated" in r["note"] and r["summary_status"] == "pass"
    _edit(root, "e9/summary.json", "E9-4", **{**base, "not_optimal": [gate], "n_not_optimal": 1})
    d = _load(root, "e9/summary.json")
    d["meta"]["reduced"] = True
    _save(root, "e9/summary.json", d)
    r = c5.build_row(spec, c5.m3._Inputs(root))
    assert r["verdict"] == "bug" and "reduced run" in r["note"]


def test_verdicts_on_unreduced_copies(tmp_path):
    """With meta.reduced false: the summaries' statuses give holds for the property checks that pass, informative for
    the three informative rows, bug for S1-0's 'fail' (a 2-hour run against E7's weeks); S1-0 set to pass is
    reproduced; fail, missing, pending, explained, an unknown status and 'informative' on a property row give their
    verdicts; with SL-1 holding and a rebuild record of a passing exit run the criterion holds once S1-0 passes."""
    root = _tree(tmp_path)
    _save(root, "figs/rebuild.json", _record(root))
    rows = _rows(c5.build(root, figures=False))
    for s in c5.SPECS:
        want = "informative" if s.kind == "informative" else ("bug" if s.id == "S1-0" else "holds")
        assert rows[s.id]["verdict"] == want, (s.id, rows[s.id]["note"])
    for cid in INFORMATIVE:
        assert rows[cid]["note"] == next(s.remark for s in c5.SPECS if s.id == cid)
    _edit(root, "s1/sweep/summary.json", "S1-0", status="pass")
    rep = c5.build(root, figures=False)
    assert _rows(rep)["S1-0"]["verdict"] == "reproduced" and rep["criterion"]["holds"], rep["criterion"]["text"]
    for status, want in (("fail", "bug"), ("missing", "missing"), ("pending", "pending"), ("explained", "bug"),
                         ("done", "bug"), ("informative", "bug")):
        _edit(root, "e9/summary.json", "E9-2", status=status)
        r = _rows(c5.build(root, figures=False))["E9-2"]
        assert r["verdict"] == want and r["summary_status"] == status, status
        assert r["note"], status


def test_a_reduced_summary_makes_exactly_its_rows_bugs(tmp_path):
    """One summary with meta.reduced true makes exactly the rows that read it bugs."""
    root = _tree(tmp_path)
    _save(root, "figs/rebuild.json", _record(root))
    _edit(root, "s1/sweep/summary.json", "S1-0", status="pass")
    for rel, exp in (("s1/sweep/summary.json", "S1"), ("s1/q28/summary.json", "Q28"), ("e9/summary.json", "E9")):
        d = _load(root, rel)
        d["meta"]["reduced"] = True
        _save(root, rel, d)
        rows = _rows(c5.build(root, figures=False))
        assert {i for i, r in rows.items() if r["verdict"] == "bug"} == {s.id for s in c5.SPECS if s.exp == exp}
        d["meta"]["reduced"] = False
        _save(root, rel, d)


def test_missing_and_malformed_inputs(tmp_path):
    """A missing summary gives missing rows; a summary that is not a JSON object, or whose checks is not an object, and
    an entry of another shape give bug rows; the report is still written."""
    root = _tree(tmp_path)
    (root / OUT / "e9" / "summary.json").unlink()
    (root / OUT / "s1" / "q28" / "summary.json").write_text("[1, 2]")
    d = _load(root, "s1/sweep/summary.json")
    d["checks"] = ["S1-0"]
    _save(root, "s1/sweep/summary.json", d)
    rep = c5.build(root, figures=False)
    rows = _rows(rep)
    assert all(rows[s.id]["verdict"] == "missing" for s in c5.SPECS if s.exp == "E9")
    assert all(rows[s.id]["verdict"] == "bug" for s in c5.SPECS if s.exp in ("S1", "Q28"))
    assert "not an object" in rows["Q28-1"]["note"] and "checks is not an object" in rows["S1-0"]["note"]
    assert rep["meta"]["inputs"][f"{OUT}/e9/summary.json"] == "missing"
    pm, pj = c5.write(rep, tmp_path / "out")
    assert pm.is_file() and json.loads(pj.read_text())["criterion"]["holds"] is False


def test_sl1(tmp_path, monkeypatch):
    """SL-1 (§6.3) on the fixture extract and the tree's npz slice: holds (every daily series equal within 1e-9, the
    pools, counts and digests equal); a changed daily value beyond 1e-9, a changed digest, a pool missing from the
    extract and a changed slot length each fail, naming what differs; the end rule on synthetic series, and SL-1 on a
    tree whose series have an end (the extract built there holds; a changed day count, day span, last day or end
    length fails); without the npz or the extract the row is missing."""
    root = _tree(tmp_path)
    r = _rows(c5.build(root, figures=False))["SL-1"]
    assert r["verdict"] == "holds", r["note"]
    v = r["regenerated"]["value"]
    assert v["n_pools"] == 6 and v["digests_equal"] is True and v["max_abs_diff"] <= c5.SL1_TOL
    assert v["tail_start_slot"] is None and v["n_kept"] == v["n_slots"] == 4032 and v["n_days"] == 14
    assert r["reference"]["values"] == {"tolerance": c5.SL1_TOL, "slots_per_day": 288, "tail_rise": 0.5}
    ext = root / OUT / "figs" / "sf_slack.json"
    good = json.loads(ext.read_text())
    bad = copy.deepcopy(good)
    bad["data"]["series"]["H800"]["mean"][3] += 2e-9
    ext.write_text(json.dumps(bad))
    r = _rows(c5.build(root, figures=False))["SL-1"]
    assert r["verdict"] == "bug" and "H800.mean" in r["note"]
    bad = copy.deepcopy(good)
    bad["data"]["source_sha256"][c5.SLACK_NPZ] = "0" * 64
    ext.write_text(json.dumps(bad))
    r = _rows(c5.build(root, figures=False))["SL-1"]
    assert r["verdict"] == "bug" and "source digests differ" in r["note"]
    bad = copy.deepcopy(good)
    del bad["data"]["series"]["A10"]
    ext.write_text(json.dumps(bad))
    assert _rows(c5.build(root, figures=False))["SL-1"]["verdict"] == "bug"
    ext.write_text(json.dumps(good))
    a9 = root / c5.SLACK_A9B
    a9_good = a9.read_text()
    d = json.loads(a9_good)
    d["meta"]["slot_min"] = 10
    a9.write_text(json.dumps(d))
    r = _rows(c5.build(root, figures=False))["SL-1"]
    assert r["verdict"] == "bug" and "slots_per_day" in r["note"]
    a9.write_text(a9_good)
    assert c5.daily([1, 2, 3, 4, 5], per_day=2) == {"min": [1, 3, 5], "mean": [1.5, 3.5, 5.0], "max": [2, 4, 5]}
    caps = {"a": 10.0, "b": 4.0}
    series = {"a": [1, 1, 2, 1, 9, 10], "b": [0, 1, 1, 0, 3, 4]}           # both rise by half their capacity at 4
    assert c5.tail_start(series, caps) == (4, [4])
    assert c5.tail_start({"a": [1, 9, 1, 9], "b": [0, 3, 0, 3]}, caps) == (None, [1, 3])
    assert c5.tail_start({"a": [1, 9], "b": [0, 1]}, caps) == (None, [])
    # a series with an end: the slice with one empty slot and 18 slots at capacity appended to every pool (a9b's
    # n_slots to match); sf_slack's extract built on that tree holds, with the end found and left out
    npz = root / c5.SLACK_NPZ
    caps6 = {k: v["capacity_gpus"] for k, v in json.loads((root / c5.SLACK_JSON).read_text()).items()
             if not k.startswith("_")}
    with np.load(npz) as z:
        grown = {k: np.concatenate([z[k], [0.0], np.full(18, float(caps6[k]))]) for k in z.files}
    with open(npz, "wb") as f:
        np.savez(f, **grown)
    n = len(next(iter(grown.values())))
    d = json.loads(a9_good)
    for v in d["lenders"].values():
        v["n_slots"] = n
    a9.write_text(json.dumps(d))
    from figs.inputs import Inputs
    from figs.supp import sf_slack
    monkeypatch.setenv("SUBLET_FIGS_IN_ROOT", str(root))
    data = json.loads(json.dumps(sf_slack.build(Inputs()), allow_nan=False))
    assert data["tail"]["start_slot"] == n - 18 and data["n_kept"] == n - 18 and data["n_days"] == 15
    ext.write_text(json.dumps({**good, "data": style._jsonable(data)}))
    r = _rows(c5.build(root, figures=False))["SL-1"]
    assert r["verdict"] == "holds", r["note"]
    v = r["regenerated"]["value"]
    assert (v["tail_start_slot"], v["n_kept"], v["n_slots"], v["n_days"]) == (n - 18, n - 18, n, 15)
    for k, x in (("n_days", 99), ("days", 1.0), ("last_day_slots", 7)):
        bad = copy.deepcopy(data)
        bad[k] = x
        ext.write_text(json.dumps({**good, "data": bad}))
        r = _rows(c5.build(root, figures=False))["SL-1"]
        assert r["verdict"] == "bug" and k in r["note"], (k, r["note"])
    bad = copy.deepcopy(data)
    bad["tail"]["n_slots"] = 5
    ext.write_text(json.dumps({**good, "data": bad}))
    r = _rows(c5.build(root, figures=False))["SL-1"]
    assert r["verdict"] == "bug" and "length 5" in r["note"]
    ext.write_text(json.dumps(good))
    (root / c5.SLACK_NPZ).unlink()
    r = _rows(c5.build(root, figures=False))["SL-1"]
    assert r["verdict"] == "missing" and c5.SLACK_NPZ in r["note"]
    ext.unlink()
    assert _rows(c5.build(root, figures=False))["SL-1"]["verdict"] == "missing"


def test_rb1(tmp_path):
    """RB-1 (§8.4) holds on the record of a passing exit run (CHECK=1, the full list, a clean clone, every output
    identical, the coverage holding, both float heights equal, the hand-set files unchanged) whose compared files are
    the root's; each condition broken, and a record stale against the root's files, make it a bug with the reason;
    without the record it is missing."""
    root = _tree(tmp_path)
    good = _record(root)
    _save(root, "figs/rebuild.json", good)
    r = _rows(c5.build(root, figures=False))["RB-1"]
    assert r["verdict"] == "holds", r["note"]
    assert r["regenerated"]["value"]["n_identical"] == 1 and r["regenerated"]["value"]["len(problems)"] == 0
    cases = {
        "status": (lambda d: d.update(status="fail", **{"pass": False}, reasons=["x differs"]), "status 'fail'"),
        "mode": (lambda d: d["meta"].update(mode="in_place"), "mode 'in_place'"),
        "only": (lambda d: d["meta"].update(only="^fig6$"), "ONLY"),
        "dirty": (lambda d: d["meta"].update(tracked_files_dirty=True), "not a clean clone"),
        "root": (lambda d: d["meta"].update(root_is_repository=False), "root other than"),
        "coverage": (lambda d: d["coverage"].update(ok=False, missing=["a"]), "coverage"),
        "different": (lambda d: d["totals"].update(different=["paper/figures/fig1.pdf"]), "output(s) differ"),
        "heights": (lambda d: d["heights"]["ms4"].update(equal=False), "float heights"),
        "hand_set": (lambda d: d["hand_set"][0].update(ok=False), "hand-set"),
        "unexpected": (lambda d: d.update(unexpected=["code/sim/out/figs/x.json"]), "unexpected"),
        "stale": (lambda d: d["outputs"][0].update(versioned_sha256="f" * 64), "stale"),
    }
    for name, (change, words) in cases.items():
        d = copy.deepcopy(good)
        change(d)
        _save(root, "figs/rebuild.json", d)
        r = _rows(c5.build(root, figures=False))["RB-1"]
        assert r["verdict"] == "bug" and words in r["note"], (name, r["note"])
    # a record whose compared file was rewritten after the run is stale
    _save(root, "figs/rebuild.json", good)
    ext = root / OUT / "figs" / "sf_slack.json"
    ext.write_text(ext.read_text() + " ")
    r = _rows(c5.build(root, figures=False))["RB-1"]
    assert r["verdict"] == "bug" and "stale" in r["note"]
    (root / OUT / "figs" / "rebuild.json").unlink()
    assert _rows(c5.build(root, figures=False))["RB-1"]["verdict"] == "missing"


def test_jobs_copy_rebuild_and_caption_blocks(tmp_path):
    """The jobs block counts every listed job of s1/sweep, s1/q28 and e9 (all 'ok' in the fixture) with the manifest and
    summary records, and lists a job whose record is missing or failed as blocking; the copy block lists the two
    records with one clone commit, and a failed check by name; the rebuild block reads the record; the caption drafts
    come from the extracts, the reduced ones noted."""
    root = _tree(tmp_path)
    jb = c5.jobs_block(m3._Inputs(root))
    assert list(jb["rows"]) == list(c5.JOB_FOLDERS) and jb["n_blocking"] == 0
    for folder, n in (("s1/sweep", 51), ("s1/q28", 19), ("e9", 39)):
        r = jb["rows"][folder]
        assert r["present"] and r["n_listed"] == n and r["by_status"] == {"ok": n + 2} and r["n_unlisted_records"] == 0
    jobs = root / OUT / "e9" / "jobs"
    (jobs / "e9__lp__pt__e7r_V1_SML__c__1.json").unlink()
    rec = json.loads((jobs / "e9__run__pt__e7f_V1_SML__pol__A6__c__1.json").read_text())
    rec["status"] = "oom_at_3G"
    (jobs / "e9__run__pt__e7f_V1_SML__pol__A6__c__1.json").write_text(json.dumps(rec))
    r = c5.jobs_block(m3._Inputs(root))["rows"]["e9"]
    assert r["n_blocking"] == 2 and {x["status"] for x in r["blocking"]} == {"no record", "oom_at_3G"}
    cp = c5.copy_block(m3._Inputs(root))
    assert set(cp["records"]) == {"s1", "e9"} and cp["one_commit"] is None and "no copy record" in cp["note"]
    for exp in c5.COPY_EXPS:
        _save(root, mc.COPY_RECORD.format(exp=exp), {"exp": exp, "check": "copy", "pass": exp == "e9",
                                                       "clone_commit": "a" * 40, "time": "t", "parts": None,
                                                       "checks": {"same_sha256": exp == "e9"}})
    cp = c5.copy_block(m3._Inputs(root))
    assert cp["one_commit"] is True and cp["records"]["s1"]["failed"] == ["same_sha256"]
    assert cp["records"]["e9"]["pass"] and "failed: s1" in cp["note"]
    rb = c5.rebuild_block(m3._Inputs(root))
    assert not rb["present"] and "missing" in rb["note"]
    _save(root, "figs/rebuild.json", _record(root))
    rb = c5.rebuild_block(m3._Inputs(root))
    assert rb["present"] and rb["pass"] is True and rb["mode"] == "check" and rb["hand_set_ok"] is True
    cap = c5.captions_block(m3._Inputs(root), FIX5)
    assert list(cap) == ["sf_e9", "sf_s1", "sf_slack"]
    for name, e in cap.items():
        ext = json.loads((FIX5 / f"{name}.json").read_text())
        assert e["text"] == ext["data"]["labels"]["caption"] and e["n_chars"] == len(e["text"])
        assert e["reduced"] == (name != "sf_slack")
        assert ("drafted from a reduced run (never a result)" in e["notes"]) == e["reduced"]
    cap = c5.captions_block(m3._Inputs(root), root / OUT / "figs")
    assert cap["sf_s1"]["text"] is None and cap["sf_slack"]["text"]


def test_figure_scripts_are_the_ms5_ones():
    """The figure list is the three MS5 scripts of §2.1, by the names style.SUPP_POLICIES_MS5 registers, in path
    order, each script present and drawing its name."""
    names = [n for n, _, _ in c5.figure_scripts()]
    assert names == sorted(style.SUPP_POLICIES_MS5) == ["sf_e9", "sf_s1", "sf_slack"]
    for name, module, rel in c5.figure_scripts():
        assert (SIM / rel).is_file() and module == rel[:-3].replace("/", ".")
        assert f'NAME = "{name}"' in (SIM / rel).read_text()
        assert not style.FIGURES[name].main


def _outputs_snapshot() -> dict:
    snap = {}
    for d in (REPO / "paper" / "figures", REPO / "paper" / "supplement", REPO / "paper" / "floats",
              SIM / "out" / "figs"):
        for p in sorted(d.rglob("*")) if d.is_dir() else []:
            if p.is_file():
                snap[str(p)] = p.stat().st_mtime_ns
    for name in (c5.OUT_MD, c5.OUT_JSON):
        p = SIM / "out" / name
        snap[str(p)] = p.stat().st_mtime_ns if p.exists() else None
    return snap


def test_figures_rerun_from_the_fixture_extracts(tmp_path, monkeypatch):
    """The three MS5 scripts redraw from their fixture extracts with finalize() passing, each with its glyph list,
    every output in a temporary folder (nothing written into paper/ or code/sim/out/figs/)."""
    import tempfile
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    before = _outputs_snapshot()
    fg = c5.figures_block(IN_ROOT, FIX5)
    assert [r["figure"] for r in fg["rows"]] == ["sf_e9", "sf_s1", "sf_slack"]
    assert all(r["status"] == "ok" for r in fg["rows"]), [r["error"] for r in fg["rows"]]
    assert all(isinstance(r["small_glyphs"], list) and r["text_pt"] for r in fg["rows"])
    assert fg["counts"] == {"ok": 3, "missing": 0, "error": 0}
    assert not list(tmp_path.glob("ms4_claims_figs_*"))          # the temporary folder is removed
    fg = c5.figures_block(IN_ROOT, tmp_path / "none", only=["sf_slack"])
    assert [(r["figure"], r["status"]) for r in fg["rows"]] == [("sf_slack", "missing")]
    with pytest.raises(ValueError):
        c5.figures_block(IN_ROOT, FIX5, only=["sf_e8"])
    assert _outputs_snapshot() == before


def test_command_line_writes_only_under_out_dir(tmp_path):
    """The command line writes ms5_claims.md and .json under --out-dir alone, and requires --out-dir with a root that
    is not the repository; the markdown has one table per experiment and the blocks' sections."""
    root = _tree(tmp_path)
    before = _outputs_snapshot()
    assert c5.main(["--root", str(root), "--out-dir", str(tmp_path / "o"), "--no-figures"]) == 0
    assert sorted(p.name for p in (tmp_path / "o").iterdir()) == ["ms5_claims.json", "ms5_claims.md"]
    md = (tmp_path / "o" / "ms5_claims.md").read_text()
    for head in ("## S1 (§3.10)", "## Q28 (§4.7)", "## E9 (§5.9)", "## SL (§6.3)", "## RB (§8.4)",
                 "## Copy checks (§1.2)", "## Jobs (§2.4)", "## Rebuild record (§8.3)", "## Caption drafts"):
        assert head in md, head
    rep = json.loads((tmp_path / "o" / "ms5_claims.json").read_text())
    assert rep["meta"]["input_root_is_repository"] is False and rep["figures"]["run"] is False
    with pytest.raises(SystemExit):
        c5.main(["--root", str(root), "--no-figures"])
    assert _outputs_snapshot() == before
