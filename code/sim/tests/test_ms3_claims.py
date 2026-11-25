"""Tests of the MS3 claims report sublet/experiments/ms3_claims.py (design/sim_spec_ms3.md §1.4 items 1, 2 and 5;
§10). Quick: the inputs are the synthetic fixture tree tests/fixtures_figs/inputs/ (README there; its values are not
results), copies of its summaries in tmp_path with check entries changed in the drivers' form, the fixture extracts
tests/fixtures_figs/<name>.json, and for the E11 rows the repository's versioned E11 files (read, never written).
Every output goes under pytest's tmp_path (never into paper/ or code/sim/out/).

- the rows cover every check id of the five spec tables (§3.3, §4.6, §5.5, §6.9, §7.3, parsed from the spec)
  exactly once and in order, with the status labels copied from the spec or the design (each part with a status
  word found there; changing one status word is caught);
- the verdict of each summary status (pass by kind, fail, explained where allowed and elsewhere, informative,
  missing, pending, an unknown status, an input that is not JSON); E1-1's 'elsewhere' resolved from fig2.json; a
  reduced summary's rows and malformed inputs are bugs (no crash); the notes name the reason;
- an 'explained' row carries its text (the summary's explanation field, or E2-5's counterexamples), E2-5 only when
  its MILP records confirm every episode;
- E11-4 compares every number Fig. 3 draws; the jobs block (jobs without an 'ok' record, Q39's MILP rule); the
  needs_ms3_out marker's folder rule;
- the criterion line of §1.4 item 2 (holds; does not hold with bug, missing or pending rows);
- missing summaries give 'missing' rows, not a crash;
- the E11 rows on the versioned E11 files; the floats and copy-check blocks;
- the figure reruns on a few scripts (small glyphs listed, a missing extract listed as missing), written only to a
  temporary folder; the command line writes only under --out-dir.
"""
import json
import os
import re
import shutil
from pathlib import Path

import pytest

from fixtures import SIM

from sublet.experiments import ms3_claims as mcl
from sublet.experiments import ms3_common as mc

REPO = SIM.parents[1]
FIX = Path(__file__).resolve().parent / "fixtures_figs"
IN_ROOT = FIX / "inputs"
SPEC = REPO / "design" / "sim_spec_ms3.md"
SECTIONS = (("3.3", "4. "), ("4.6", "5. "), ("5.5", "6. "), ("6.9", "7. "), ("7.3", "8. "))
OUT = "code/sim/out"


def spec_check_ids() -> list:
    """The check ids of the tables of §3.3, §4.6, §5.5, §6.9 and §7.3, in the spec's order (first column)."""
    text = SPEC.read_text(encoding="utf-8")
    ids = []
    for sec, nxt in SECTIONS:
        start = text.index(f"\n### {sec} ")
        end = text.index(f"\n## {nxt}", start)
        ids += re.findall(r"^\| (E\d+-\d+b?) \|", text[start:end], flags=re.M)
    return ids


def _outputs_snapshot() -> dict:
    """{path: mtime} of the report's default outputs and of every file under paper/figures, paper/supplement and
    code/sim/out/figs (none of which a test may write)."""
    snap = {}
    for d in (REPO / "paper" / "figures", REPO / "paper" / "supplement", SIM / "out" / "figs"):
        for p in sorted(d.rglob("*")) if d.is_dir() else []:
            if p.is_file():
                snap[str(p)] = p.stat().st_mtime_ns
    for name in (mcl.OUT_MD, mcl.OUT_JSON):
        p = SIM / "out" / name
        snap[str(p)] = p.stat().st_mtime_ns if p.exists() else None
    return snap


def _tree(tmp_path) -> Path:
    """A copy of the fixture tree's MS3 summaries (regular files) under tmp_path/in."""
    root = tmp_path / "in"
    shutil.copytree(IN_ROOT / OUT, root / OUT, ignore=shutil.ignore_patterns("ms2_checks"))
    return root


def _edit(root: Path, rel: str, cid: str, **fields) -> None:
    p = root / OUT / rel
    d = json.loads(p.read_text())
    d["checks"][cid].update(fields)
    p.write_text(json.dumps(d, indent=1))


def _write(root: Path, rel: str, obj) -> None:
    p = root / OUT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=1))


def _rows(rep) -> dict:
    return {r["id"]: r for r in rep["rows"]}


def _e6a_summary(status: str = "pass") -> dict:
    """An e6/a summary's checks in the driver's form (e6.CHECK_CLAIMS; the fields of e6.py's docstring)."""
    from sublet.experiments import e6
    ch = {"E6-1": {"a": {"n": 2, "n_fail": 0, "rows": []}, "b": {"n": 2, "n_fail": 0, "rows": [],
                                                                    "a1": {"n": 1, "n_fail": 0, "rows": []}},
                   "pass": True},
          "E6-2": {"reruns": [], "n": 3, "n_fail": 0, "failures": [],
                   "units_across_alignments": {"n": 2, "n_fail": 0, "failures": []}, "tolerance": 1e-9, "pass": True},
          "E6-3": {"rows": [], "n": 2, "n_fail": 0, "tolerance_usd": 1e-9, "n_without_e2_cold": 0, "pass": True},
          "E6-4": {"n_pairs": 4, "max_abs_dev": 0.0, "pass": True},
          "E6-5": {"disagreements": [], "n_disagree": 0, "n_cells": 9, "informative": True}}
    return {"meta": {"exp": "e6", "part": "a"}, "checks": {
        k: {"status": "informative" if k == "E6-5" else status, "claim": e6.CHECK_CLAIMS[k], **v}
        for k, v in ch.items()}}


def _complete_tree(tmp_path) -> Path:
    """The fixture summaries plus an e6/a summary whose checks pass, fig2.json's E1_1 passing, and the repository's
    versioned E11 files (symbolic links) under one root: every row reproduced, holds or informative."""
    root = _tree(tmp_path)
    _write(root, "e6/a/summary.json", _e6a_summary())
    _write(root, "figs/fig2.json", {"figure": "fig2", "data": {"b": {"E1_1": {
        "check": "E1-1", "price_ref": "maas_p99_median", "n": 3, "max_rel_err": 0.0, "tol": 1e-12, "pass": True}}}})
    for rel in ("ms3_e11_0.json", "e11/summary.json", "q44_study/summary.json", "figs/fig1.json", "figs/fig3.json"):
        dst = root / OUT / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        os.symlink(SIM / "out" / rel, dst)
    return root


# ---------------------------------------------------------------------------------------------------------------
def test_rows_cover_every_spec_check_once_in_order():
    """One row per check id of the five spec tables, each exactly once, in the spec's order (E11, E1, E10, E2, E6),
    with the experiment and section of its table; every row has the documented keys."""
    want = spec_check_ids()
    assert len(want) == 37 and len(set(want)) == len(want)
    rep = mcl.build(IN_ROOT, figures=False)
    ids = [r["id"] for r in rep["rows"]]
    assert ids == want and [s.id for s in mcl.SPECS] == want
    secs = {"E11": "§3.3", "E1": "§4.6", "E10": "§5.5", "E2": "§6.9", "E6": "§7.3"}
    assert list(dict.fromkeys(r["experiment"] for r in rep["rows"])) == list(secs)
    keys = {"id", "experiment", "section", "kind", "claim", "status_label", "status_label_note", "reference",
            "regenerated", "summary_status", "verdict", "explanation", "note"}
    for r in rep["rows"]:
        assert r["id"].startswith(r["experiment"] + "-") and r["section"] == secs[r["experiment"]]
        assert keys <= set(r) and set(r) - keys <= {"detail"}
        assert r["kind"] in ("reproduction", "property", "informative") and r["claim"]["spec"]
        assert set(r["reference"]) == {"value", "values", "file"} and set(r["regenerated"]) == {"value", "file"}
        assert (r["status_label"] is None) == (r["status_label_note"] is not None)
        assert r["verdict"] in mcl.VERDICTS
    assert set(rep) == {"meta", "criterion", "rows", "floats", "figures", "copy_checks", "jobs"}


STATUS_WORD = re.compile(r"PROVEN|VERIFIED NUMERICALLY|CONJECTURE")


def _norm(t: str) -> str:
    """The spec's and design's TeX and markdown in the drivers' ASCII ($m\\ge3$ -> 'm >= 3', $\\rho$ -> 'rho',
    C1–C3 -> C1-C3, C′ -> C', H^\\star_\\mu -> H*_mu), without backticks and bold, spaces collapsed."""
    t = t.replace("`", "").replace("**", "").replace("$", "").replace("′", "'").replace("–", "-").replace("—", "-")
    t = t.replace("^\\star", "*")
    t = re.sub(r"\\(ge|le)(?![A-Za-z])", lambda m: ">=" if m.group(1) == "ge" else "<=", t)
    t = re.sub(r"\\(rho|tau|alpha|beta|mu)(?![A-Za-z])", r"\1", t)
    t = re.sub(r"\s*(>=|<=|=)\s*", r" \1 ", t)
    return re.sub(r"\s+", " ", t)


def _split_top(label: str) -> list:
    """The parts of a label separated by '; ' outside parentheses."""
    parts, depth, cur = [], 0, ""
    for i, ch in enumerate(label):
        depth += (ch == "(") - (ch == ")")
        if depth == 0 and label.startswith("; ", i):
            parts.append(cur)
            cur = ""
            continue
        if not (cur == "" and ch == " " and parts):
            cur += ch
    return parts + [cur]


def _paren_bodies(text: str, ident: str) -> list:
    """The texts inside the parentheses that follow each occurrence of 'IDENT (' in `text` (nested ones kept)."""
    out, key = [], ident + " ("
    i = text.find(key)
    while i >= 0:
        j, depth = i + len(key), 1
        while j < len(text) and depth:
            depth += (text[j] == "(") - (text[j] == ")")
            j += 1
        out.append(text[i + len(key):j - 1])
        i = text.find(key, i + 1)
    return out


def _label_part_copied(part: str, src: str) -> bool:
    """A label part with a status word is copied: verbatim in the normalized sources, or 'ID (text)rest' where
    `text` opens the parenthesis that follows ID there (equal, or followed by ';', ',' or ':' in the source) and
    `rest` has no status word."""
    if part in src:
        return True
    m = re.match(r"^(.+?) \(", part)
    if m is None:
        return False
    ident, j, depth = m.group(1), m.end(), 1
    while j < len(part) and depth:
        depth += (part[j] == "(") - (part[j] == ")")
        j += 1
    body, rest = part[m.end():j - 1], part[j:]
    if depth or STATUS_WORD.search(rest):
        return False
    return any(b == body or (b.startswith(body) and b[len(body):len(body) + 1] in ";,:")
               for b in _paren_bodies(src, ident))


def test_status_labels_are_copied_never_upgraded():
    """Every part of a row's status label that carries a status word (PROVEN, VERIFIED NUMERICALLY, CONJECTURE) is
    copied from the spec or design/Sublet_design.md, normalized to the drivers' ASCII (_label_part_copied), so a
    label whose status word is changed (an upgrade) is not found there; the checker itself rejects upgraded copies
    of real labels; the informative and explainable rows are those of §3.3-§7.3."""
    src = _norm(SPEC.read_text(encoding="utf-8") + "\n" + (REPO / "design" / "Sublet_design.md").read_text(
        encoding="utf-8"))
    bad = []
    for s in mcl.SPECS:
        if s.label is None:
            assert s.label_note
            continue
        for part in _split_top(s.label):
            if STATUS_WORD.search(part) and not _label_part_copied(part, src):
                bad.append(f"{s.id}: {part!r}")
    assert not bad, "labels not copied from the spec or the design:\n" + "\n".join(bad)
    lab = {s.id: s.label for s in mcl.SPECS}
    for cid, old, new in (("E2-7", "CONJECTURE", "PROVEN"), ("E10-10", "CONJECTURE", "PROVEN"),
                          ("E10-8", "VERIFIED NUMERICALLY / CONJECTURE", "PROVEN"),
                          ("E11-2", "(CONJECTURE)", "(PROVEN)"), ("E2-1", "CONJECTURE in general", "PROVEN in general"),
                          ("E2-5", "CONJECTURE", "PROVEN")):
        up = lab[cid].replace(old, new)
        assert up != lab[cid] and any(STATUS_WORD.search(p) and not _label_part_copied(p, src)
                                      for p in _split_top(up)), (cid, up)
    assert lab["E10-10"] == "C-O1b (CONJECTURE)" and lab["E2-5"] == "Claim D2 (CONJECTURE)"
    assert lab["E10-8"] == "C-O1a (VERIFIED NUMERICALLY / CONJECTURE)" and "W(c) (CONJECTURE)" in lab["E11-2"]
    assert lab["E2-1"].startswith("C2-P8 (lower bound PROVEN, table values interval-certified")
    informative = {s.id for s in mcl.SPECS if s.kind == "informative"}
    assert informative == {"E11-3", "E11-4", "E1-8", "E10-7", "E10-8", "E10-10", "E2-6", "E2-7", "E6-5"}
    assert {s.id for s in mcl.SPECS if s.explainable} == {"E2-5"}


@pytest.mark.parametrize("kind, status, explainable, want", [
    ("reproduction", "pass", False, "reproduced"), ("property", "pass", False, "holds"),
    ("informative", "pass", False, "informative"), ("informative", "informative", False, "informative"),
    ("property", "informative", False, "bug"), ("property", "fail", False, "bug"),
    ("reproduction", "fail", False, "bug"), ("informative", "fail", False, "bug"),
    ("property", "explained", True, "explained"), ("property", "explained", False, "bug"),
    ("property", "missing", False, "missing"), ("informative", "missing", False, "missing"),
    ("property", "pending", False, "pending"), ("property", "done", False, "bug"), ("property", None, False, "bug"),
])
def test_verdict_of_each_status(kind, status, explainable, want):
    v, note = mcl.verdict(kind, status, explainable)
    assert v == want
    if want == "bug" and status not in ("fail",):
        assert note


def test_verdicts_from_the_summaries(tmp_path):
    """The verdict of every status as the summaries write it: pass (reproduction and property rows), fail, missing
    (with the entry's own reason), pending (with what is outstanding), informative (and pass on an informative
    row), explained where §6.9 allows it and a bug elsewhere, a status outside §2.6's vocabulary, a summary that is
    not JSON; E1-1's 'elsewhere' read from figs/fig2.json (pass: reproduced, fail: bug, absent: missing)."""
    root = _tree(tmp_path)
    _edit(root, "e1/summary.json", "E1-2", status="fail")
    _edit(root, "e1/summary.json", "E1-3", status="missing", why="tight_family.json missing (job e1:tight)")
    _edit(root, "e10/summary.json", "E10-5", status="pending",
          rerun_pending=[{"point": ["safe_site", "16", "8"], "tag": "A2-th"}])
    _edit(root, "e10/summary.json", "E10-7", status="pass")
    _edit(root, "e10/summary.json", "E10-2", status="explained")
    _edit(root, "e2/summary.json", "E2-3", status="informative")
    _edit(root, "e2/summary.json", "E2-4", status="done")
    rep = mcl.build(root, figures=False)
    R = _rows(rep)
    want = {"E1-1": "missing", "E1-2": "bug", "E1-3": "missing", "E1-4": "holds", "E1-7": "reproduced",
            "E1-8": "informative", "E10-1": "reproduced", "E10-2": "bug", "E10-5": "pending", "E10-7": "informative",
            "E10-9": "reproduced", "E2-1": "reproduced", "E2-3": "bug", "E2-4": "bug", "E2-5": "holds",
            "E2-6": "informative", "E6-1": "missing", "E6-6": "holds", "E11-0": "missing", "E11-4": "missing"}
    assert {k: R[k]["verdict"] for k in want} == want
    assert "tight_family.json missing" in R["E1-3"]["note"] and "rerun_pending: 1" in R["E10-5"]["note"]
    assert "allows no explanation" in R["E10-2"]["note"] and "pass condition" in R["E2-3"]["note"]
    assert "vocabulary" in R["E2-4"]["note"] and R["E2-4"]["summary_status"] == "done"
    assert "fig2.json missing" in R["E1-1"]["note"] and "e6/a/summary.json missing" in R["E6-1"]["note"]
    assert R["E1-2"]["regenerated"]["value"]["n_cells"] == 18 and R["E2-1"]["reference"]["values"]["rows[*].CR_ref"]
    assert R["E1-4"]["claim"]["summary"].startswith("C3-L2 (PROVEN)")
    # E1-1: elsewhere, resolved from figs/fig2.json data.b.E1_1
    e11 = {"check": "E1-1", "price_ref": "maas_p99_median", "n": 3, "max_rel_err": 0.0, "tol": 1e-12, "pass": True}
    _write(root, "figs/fig2.json", {"figure": "fig2", "data": {"b": {"E1_1": e11}}})
    R = _rows(mcl.build(root, figures=False))
    assert R["E1-1"]["verdict"] == "reproduced" and R["E1-1"]["summary_status"] == "pass"
    assert R["E1-1"]["regenerated"]["value"]["max_rel_err"] == 0.0 and R["E1-1"]["claim"]["summary"]
    _write(root, "figs/fig2.json", {"figure": "fig2", "data": {"b": {"E1_1": {**e11, "pass": False}}}})
    assert _rows(mcl.build(root, figures=False))["E1-1"]["verdict"] == "bug"
    # a summary that is not JSON: its rows are bugs, named
    (root / OUT / "e10" / "summary.json").write_text("{not json")
    rep = mcl.build(root, figures=False)
    R = _rows(rep)
    assert all(R[f"E10-{i}"]["verdict"] == "bug" and "invalid JSON" in R[f"E10-{i}"]["note"] for i in range(1, 11))
    assert rep["meta"]["inputs"][f"{OUT}/e10/summary.json"].startswith("invalid JSON")


def test_explained_row_carries_its_text(tmp_path):
    """E2-5 'explained' (every episode below 1 - 1e-9 a confirmed counterexample to Claim D2): the row carries the
    summary's explanation field when it has one, else the counterexamples read from the E2-5 MILP records."""
    root = _tree(tmp_path)
    milp = [{"episode": {"job": "e2:cell:lender=a2.c05:H=60:mu=1:c=1", "series": "burstgpt_1", "layer": 3,
                         "f_a": 120, "f_b": 180}, "dp": 10.5, "incumbent": 10.25, "dual_bound": 10.2, "LB": 10.2,
             "rules": [{"rule": "a1", "verdict": "explained: counterexample to Claim D2"}]}]
    _edit(root, "e2/summary.json", "E2-5", status="explained", n_below=1, min_ratio=0.99, milp=milp, n_candidates=1)
    R = _rows(mcl.build(root, figures=False))
    t = R["E2-5"]["explanation"]
    assert R["E2-5"]["verdict"] == "explained" and "counterexample to Claim D2" in t
    assert "e2:cell:lender=a2.c05:H=60:mu=1:c=1" in t and "layer 3" in t and "10.25" in t and "10.5" in t
    _edit(root, "e2/summary.json", "E2-5", explanation="every such episode is a confirmed counterexample (test)")
    rep = mcl.build(root, figures=False)
    assert _rows(rep)["E2-5"]["explanation"] == "every such episode is a confirmed counterexample (test)"
    md = mcl.markdown(rep)
    assert "- E2-5: explained: every such episode is a confirmed counterexample (test)" in md
    assert rep["criterion"]["explained"] == ["E2-5"] and "E2-5" not in rep["criterion"]["unexplained"]


def test_criterion_line(tmp_path):
    """§1.4 item 2: holds when no row is a bug and every other row is reproduced, holds, informative or explained;
    a bug row, a missing row or a pending row makes it not hold, and the head says why."""
    root = _complete_tree(tmp_path)
    rep = mcl.build(root, figures=False)
    c = rep["criterion"]
    assert c["holds"] is True, c
    assert c["counts"]["bug"] == c["counts"]["missing"] == c["counts"]["pending"] == 0 and c["n_rows"] == 37
    assert c["text"].startswith("holds: ")
    md = mcl.markdown(rep)
    assert "**Criterion of §1.4 item 2: holds.**" in md
    milp = [{"episode": {"job": "e2:cell:lender=a2.c05:H=60:mu=1:c=1", "series": "burstgpt_1", "layer": 3,
                         "f_a": 120}, "dp": 10.5, "incumbent": 10.25,
             "rules": [{"rule": "a1", "verdict": "explained: counterexample to Claim D2"}]}]
    _edit(root, "e2/summary.json", "E2-5", status="explained", n_below=1, n_candidates=1, milp=milp,
          explanation="a confirmed counterexample to Claim D2 (test)")
    c = mcl.build(root, figures=False)["criterion"]
    assert c["holds"] is True and c["explained"] == ["E2-5"] and "1 explained" in c["text"]
    p = root / OUT / "e6" / "a" / "summary.json"
    s = _e6a_summary()
    s["checks"]["E6-4"]["status"] = "fail"
    p.write_text(json.dumps(s))
    rep = mcl.build(root, figures=False)
    assert rep["criterion"]["holds"] is False and rep["criterion"]["bug"] == ["E6-4"]
    assert "**Criterion of §1.4 item 2: does not hold.** 1 bug row(s) (E6-4)" in mcl.markdown(rep)
    p.unlink()
    _edit(root, "e10/summary.json", "E10-6", status="pending")
    c = mcl.build(root, figures=False)["criterion"]
    assert c["holds"] is False and c["pending"] == ["E10-6"] and c["missing"] == ["E6-1", "E6-2", "E6-3", "E6-4",
                                                                                   "E6-5"]
    assert "5 missing row(s)" in c["text"] and "1 pending row(s) (E10-6)" in c["text"]
    assert "cannot hold until its output exists" in c["text"]


def test_missing_summaries_give_missing_rows(tmp_path):
    """On an empty input root every row is 'missing' with the absent file named, the blocks say what is absent,
    and the report is written (no crash)."""
    root = tmp_path / "empty"
    root.mkdir()
    rep = mcl.build(root, figures=False)
    assert [r["verdict"] for r in rep["rows"]] == ["missing"] * 37
    assert all(r["note"] and "missing" in r["note"] for r in rep["rows"])
    assert rep["criterion"]["holds"] is False and "37 missing row(s)" in rep["criterion"]["text"]
    assert rep["floats"]["present"] is False and rep["floats"]["rows"] == []
    assert all(e["present"] is False and e["pass"] is None for e in rep["copy_checks"].values())
    assert list(rep["copy_checks"]) == ["e11", "e1", "e10", "e2", "e6"]
    pm, pj = mcl.write(rep, tmp_path / "out")
    assert pm.is_file() and json.loads(pj.read_text())["criterion"]["counts"]["missing"] == 37


def test_e11_rows_and_blocks_on_the_versioned_files(tmp_path):
    """The E11 rows on the repository's versioned E11 files (E11-0 to E11-2 hold, E11-3 and E11-4 informative, with
    E11-4's compared values in `detail`), the floats block from floats_heights.json next to the budgets, and the
    copy block with E11-0's record. Read only; the report goes to tmp_path."""
    rep = mcl.build(REPO, figures=False)
    R = _rows(rep)
    assert [R[f"E11-{i}"]["verdict"] for i in range(5)] == ["holds"] * 3 + ["informative"] * 2
    assert R["E11-0"]["regenerated"]["value"]["n_sha256_mismatch"] == 0 and R["E11-0"]["reference"]["file"]
    assert all(R["E11-1"]["regenerated"]["value"][v] == "pass" for v in mcl.V_CHECKS)
    det = R["E11-4"]["detail"]
    assert det and {d["panel"] for d in det} == {"a", "b", "c"}
    assert R["E11-4"]["regenerated"]["value"]["n_compared"] == sum(1 for d in det if d["abs_diff"] is not None)
    assert {(d["panel"], d["field"]) for d in det} == E11_4_FIELDS
    assert R["E11-4"]["regenerated"]["value"]["n_without_counterpart"] == 0
    fl = rep["floats"]
    heights = json.loads((SIM / "out" / "figs" / "floats_heights.json").read_text())["floats"]
    assert [r["name"] for r in fl["rows"]] == list(heights)
    assert all(r["measured_pages"] == heights[r["name"]]["measured_pages"]
               and r["budget_pages"] == heights[r["name"]]["budget_pages"] for r in fl["rows"])
    assert {r["float"] for r in fl["rows"]} == {"Table I", "Table II", "Algorithm 1"}
    e11_0 = json.loads((SIM / "out" / "ms3_e11_0.json").read_text())
    assert rep["copy_checks"]["e11"]["pass"] is e11_0["pass"] and rep["meta"]["input_root_is_repository"]
    pm, _ = mcl.write(rep, tmp_path)
    md = pm.read_text()
    assert "## Floats (§1.4 item 5)" in md and "Table II" in md and "| E11-2 |" in md


E11_4_FIELDS = ({("a", f) for f in ("x", "y", "x_min", "y_min", "D1", "W0", "x_max", "y_max")}
                | {("b", f) for f in ("x", "median", "ci_lo", "ci_hi", "n", "intensity")}
                | {("c", f) for f in ("mean", "min", "max", "runs", "revocable_only_limit")})


def test_e11_4_compares_every_drawn_value(tmp_path):
    """E11-4 compares every number Fig. 3 draws, not only (a)'s extremes, (b)'s medians and (c)'s means: a change of
    Fig. 3(b)'s CI end, of (c)'s revocable-only limit or of an instance value D1 behind (a) in a copy of fig3.json
    is found, counted per panel and named as the panel's largest difference (the first study's values from the
    versioned q44_study/summary.json; E11's other files linked, read only)."""
    root = tmp_path / "in"
    for rel in ("ms3_e11_0.json", "e11/summary.json", "q44_study/summary.json", "figs/fig1.json"):
        dst = root / OUT / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        os.symlink(SIM / "out" / rel, dst)
    P = json.loads((SIM / "out" / "figs" / "fig3.json").read_text())
    base = _rows(mcl.build(REPO, figures=False))["E11-4"]["regenerated"]["value"]
    d = P["data"]
    mode0 = d["b"]["series"]["bl1"]["modes"][0]
    d["b"]["series"]["bl1"]["ci_hi"][0] += 0.5
    d["c"]["revocable_only_limit"][1] += 0.25
    # C47 (design/ms6_spec.md M2, M4; unit U43a): fig3.json names E11's BL5-G by its configuration key, bl5_g1
    d["a"]["series"]["bl5_g1"]["D1"]["I2"] += 0.125
    _write(root, "figs/fig3.json", P)
    v = _rows(mcl.build(root, figures=False))["E11-4"]["regenerated"]["value"]
    assert v["n_differ"] == base["n_differ"] + 3 and v["n_compared"] == base["n_compared"]
    assert (v["n_differ_a"], v["n_differ_b"], v["n_differ_c"]) == (base["n_differ_a"] + 1, base["n_differ_b"] + 1,
                                                                  base["n_differ_c"] + 1)
    assert v["largest_b"] == f"bl1 ci_hi at {mode0}" and v["max_abs_diff_b"] == pytest.approx(0.5, rel=0.05)
    assert v["largest_c"] == f"revocable_only_limit revocable_only_limit at {d['c']['rho1'][1]}"
    assert v["largest_a"] == "bl5_g1 D1 at I2" and v["max_abs_diff_a"] == pytest.approx(0.125, rel=0.2)    # C47


def test_reduced_summary_rows_are_bugs(tmp_path):
    """A summary whose meta.reduced is true (a smoke run, never a result) makes each of its rows a bug, with the
    note saying so; the other summaries' rows keep their verdicts."""
    root = _tree(tmp_path)
    p = root / OUT / "e10" / "summary.json"
    d = json.loads(p.read_text())
    d["meta"]["reduced"] = True
    p.write_text(json.dumps(d))
    R = _rows(mcl.build(root, figures=False))
    assert all(R[f"E10-{i}"]["verdict"] == "bug" and "reduced run" in R[f"E10-{i}"]["note"] for i in range(1, 11))
    assert R["E1-2"]["verdict"] == "holds" and R["E2-1"]["verdict"] == "reproduced"


def test_malformed_inputs_give_bug_rows_not_a_crash(tmp_path):
    """Inputs of a shape the drivers never write give 'bug' rows and a written report: a summary that is valid JSON
    but not an object, a checks block that is not an object, an E2-5 entry with a MILP list of another type."""
    root = _tree(tmp_path)
    (root / OUT / "e10" / "summary.json").write_text("[1, 2]")
    p = root / OUT / "e2" / "summary.json"
    d = json.loads(p.read_text())
    d["checks"] = [1, 2]
    p.write_text(json.dumps(d))
    _write(root, "figs/fig1.json", {"data": [1]})
    rep = mcl.build(root, figures=False)
    R = _rows(rep)
    assert all(R[f"E10-{i}"]["verdict"] == "bug" and "not an object" in R[f"E10-{i}"]["note"] for i in range(1, 11))
    assert R["E2-1"]["verdict"] == "bug" and "checks is not an object" in R["E2-1"]["note"]
    assert R["E11-3"]["verdict"] == "missing"
    d["checks"] = json.loads((IN_ROOT / OUT / "e2" / "summary.json").read_text())["checks"]
    d["checks"]["E2-5"].update(status="explained", n_below=1, milp="not a list", rules=None)
    p.write_text(json.dumps(d))
    R = _rows(mcl.build(root, figures=False))
    assert R["E2-5"]["verdict"] == "explained" and R["E2-5"]["explanation"] is None and "not explained" in \
        R["E2-5"]["note"]
    assert mcl.markdown(rep).startswith("# MS3 claims report")


def test_notes_name_the_reason(tmp_path):
    """A row's note says why: 'elsewhere' on a row other than E1-1, a missing entry with the driver's 'where' or
    'missing_Hs', and 'the summary gives no reason' where the entry has none."""
    root = _tree(tmp_path)
    _edit(root, "e10/summary.json", "E10-4", status="elsewhere")
    _edit(root, "e1/summary.json", "E1-7", status="missing", where="e10/repro.json (E10-1, job e10:repro)")
    _edit(root, "e2/summary.json", "E2-1", status="missing", missing_Hs=[0.25, 0.5])
    p = root / OUT / "e10" / "summary.json"
    d = json.loads(p.read_text())
    d["checks"]["E10-6"] = {"status": "missing", "claim": "O1-D (test)"}
    p.write_text(json.dumps(d))
    R = _rows(mcl.build(root, figures=False))
    assert R["E10-4"]["verdict"] == "bug" and R["E10-4"]["note"] == "'elsewhere' is allowed only for E1-1 (§4.6)"
    assert R["E1-7"]["verdict"] == "missing" and "where: e10/repro.json (E10-1, job e10:repro)" in R["E1-7"]["note"]
    assert R["E2-1"]["verdict"] == "missing" and "missing_Hs: [0.25, 0.5]" in R["E2-1"]["note"]
    assert R["E10-6"]["verdict"] == "missing" and R["E10-6"]["note"] == "the summary gives no reason"


def test_e2_5_explained_only_with_confirming_milp_records(tmp_path):
    """E2-5 'explained' carries a text only when the E2-5 MILP records confirm every episode below 1 - 1e-9 as a
    counterexample to Claim D2 (incumbent below the DP value, verdict 'explained'); with no record, a record whose
    incumbent is not below the DP value, an unresolved episode or fewer confirmed episodes than candidates the row
    has no text, its note says why, and the criterion does not hold."""
    root = _complete_tree(tmp_path)
    good = {"episode": {"job": "e2:cell:lender=a2.c05:H=60:mu=1:c=1", "series": "burstgpt_1", "layer": 3, "f_a": 120},
            "dp": 10.5, "incumbent": 10.25,
            "rules": [{"rule": "a1", "verdict": "explained: counterexample to Claim D2"}]}
    cases = [({"milp": []}, "no E2-5 MILP record confirms"),
             ({"milp": [{**good, "incumbent": 10.5}]}, "without an incumbent below the DP value"),
             ({"milp": [good], "unresolved": [["e2:cell:x", "s", 1, 2]]}, "unresolved"),
             ({"milp": [good], "n_candidates": 2}, "1 confirmed episode(s) for 2"),
             ({"milp": [{**good, "rules": [{"rule": "a1", "verdict": "bug"}]}]}, "verdict other than 'explained'")]
    for fields, why in cases:
        _edit(root, "e2/summary.json", "E2-5", **{"status": "explained", "n_below": 1, "n_candidates": 1,
                                                  "unresolved": [], **fields})
        rep = mcl.build(root, figures=False)
        r = _rows(rep)["E2-5"]
        assert r["verdict"] == "explained" and r["explanation"] is None and why in r["note"], (fields, r["note"])
        assert rep["criterion"]["holds"] is False and rep["criterion"]["unexplained"] == ["E2-5"]
    _edit(root, "e2/summary.json", "E2-5", status="explained", n_below=1, n_candidates=1, unresolved=[], milp=[good])
    rep = mcl.build(root, figures=False)
    assert "1 episode(s), each a confirmed counterexample" in _rows(rep)["E2-5"]["explanation"]
    assert rep["criterion"]["holds"] is True


def _job_tree(root: Path, recs: dict, listed: list) -> None:
    """e1/manifest.json listing `listed` [(id, kind)] and the job records {id: status} under root (drivers' names)."""
    _write(root, "e1/manifest.json", {"meta": {"exp": "e1", "git_revision": "f" * 40},
                                      "jobs": [{"id": j, "kind": k, "params": {}} for j, k in listed]})
    for jid, st in recs.items():
        _write(root, f"e1/jobs/{mc.job_file_name(jid)}", {"job": jid, "status": st, "git_revision": "f" * 40})


def test_jobs_block_lists_jobs_without_an_ok_record(tmp_path):
    """The jobs block reads each folder's job list (manifest.json) and job records: a pool or alone job without an
    'ok' record (failed, oom_at_3G, or no record), a failed summary record and a MILP job that failed are blocking;
    a MILP job stopped at the wall-clock limit or by the cap is listed apart (LB = LP, Q39); unlisted and unreadable
    records are counted; the head of the report says so, and the rows' verdicts do not change."""
    root = _tree(tmp_path)
    listed = [("e1:tight", "pool"), ("e1:cell:c=1", "pool"), ("e1:alone:x=1", "alone"), ("e1:milp:c=1", "milp"),
              ("e1:milp:c=2", "milp"), ("e1:milp:c=3", "milp")]
    _job_tree(root, {"e1:tight": "ok", "e1:cell:c=1": "oom_at_3G", "e1:milp:c=1": "wall_limit",
                     "e1:milp:c=2": "oom_at_3G", "e1:milp:c=3": "failed", "e1:manifest": "ok", "e1:summary": "failed",
                     "e1:old:c=9": "ok"}, listed)
    (root / OUT / "e1" / "jobs" / "broken.json").write_bytes(b"\xff")
    before = [r["verdict"] for r in mcl.build(root, figures=False)["rows"]]
    rep = mcl.build(root, figures=False)
    r = rep["jobs"]["rows"]["e1"]
    assert r["present"] and r["n_listed"] == 6
    assert r["by_status"] == {"failed": 2, "no record": 1, "ok": 2, "oom_at_3G": 2, "wall_limit": 1}
    assert [x["job"] for x in r["blocking"]] == ["e1:cell:c=1", "e1:alone:x=1", "e1:milp:c=3", "e1:summary"]
    assert [x["status"] for x in r["blocking"]] == ["oom_at_3G", "no record", "failed", "failed"]
    assert [x["job"] for x in r["milp_lp_fallback"]] == ["e1:milp:c=1", "e1:milp:c=2"] and r["n_milp_lp_fallback"] == 2
    assert r["n_unlisted_records"] == 1 and r["n_unreadable_records"] == 1 and r["summary_ignored_outputs"] == 0
    assert rep["jobs"]["n_blocking"] == 4 and rep["jobs"]["note"].startswith("4 listed job(s) without an 'ok'")
    assert all(rep["jobs"]["rows"][k]["present"] is False for k in ("e10", "e2", "e6/a", "e6/b"))
    assert [x["verdict"] for x in rep["rows"]] == before
    md = mcl.markdown(rep)
    assert "Jobs (§2.4): e1 6 listed, failed 2, no record 1, ok 2, oom_at_3G 2, wall_limit 1;" in md
    assert "- e1: `e1:cell:c=1` (pool, oom_at_3G); `e1:alone:x=1` (alone, no record)" in md
    _job_tree(root, {j: "ok" for j, _ in listed}
              | {"e1:manifest": "ok", "e1:summary": "ok", "e1:milp:c=3": "wall_limit"}, listed)
    jb = mcl.build(root, figures=False)["jobs"]
    assert jb["n_blocking"] == 0 and jb["rows"]["e1"]["n_milp_lp_fallback"] == 1
    assert jb["note"].startswith("every listed job has an 'ok' record") and "no job list for e10" in jb["note"]
    assert mcl.build(tmp_path / "nothing", figures=False)["jobs"]["note"].startswith("no job list (manifest.json)")


def test_needs_ms3_out_marker_folder_rule(tmp_path, monkeypatch):
    """conftest's needs_ms3_out (§10, C15): the named files missing under the folder, and the folder itself when a
    marker has no argument (alone or beside markers with files) and the folder is missing or empty."""
    import conftest
    out = tmp_path / "out"
    monkeypatch.setattr(conftest, "MS3_OUT_DIR", out)
    assert conftest._ms3_out_missing([]) == [str(out)]
    assert conftest._ms3_out_missing(["e1/summary.json"]) == ["e1/summary.json"]
    assert conftest._ms3_out_missing(["e1/summary.json"], folder=True) == [str(out), "e1/summary.json"]
    (out / "e1").mkdir(parents=True)
    (out / "e1" / "summary.json").write_text("{}")
    assert conftest._ms3_out_missing(["e1/summary.json"], folder=True) == [] and conftest._ms3_out_missing([]) == []


def test_figure_reruns_on_a_few_scripts(tmp_path, monkeypatch):
    """The figure part reruns the named scripts from the fixture extracts in this process, lists each figure's
    small_glyphs from figs.common.cli's report ([size < SCRIPT_MIN_PT, text]; none at C62's scale, where every
    first-level script is at least 4.9 pt, so the lists are empty here), lists a figure without an extract as
    'missing', writes nothing into paper/ or code/sim/out/figs/, removes its temporary folder and restores the
    environment."""
    import tempfile
    names = [n for n, _, _ in mcl.figure_scripts()]
    assert len(names) == 20 and len(set(names)) == 20
    assert set(names) == {p.stem for p in FIX.glob("*.json")}
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path / "tmp"))
    (tmp_path / "tmp").mkdir()
    for k in mcl.ENV_FIG_DIRS + (mcl.ENV_IN_ROOT,):
        monkeypatch.delenv(k, raising=False)
    before = _outputs_snapshot()
    fg = mcl.figures_block(IN_ROOT, FIX, ["fig5", "sf_e10b", "fig1"])
    assert [r["figure"] for r in fg["rows"]] == ["fig1", "fig5", "sf_e10b"]
    assert all(r["status"] == "ok" and r["error"] is None for r in fg["rows"]), fg["rows"]
    by = {r["figure"]: r for r in fg["rows"]}
    # every first-level script (at least 4.9 pt since C62) is allowed, so these figures list no small glyph
    assert all(r["n_small_glyphs"] == len(r["small_glyphs"]) == 0 for r in fg["rows"]), fg["rows"]
    from figs import style                         # C62: tick labels at 7 pt, axis labels and letters at 7.97 pt
    assert set(by["fig5"]["text_pt"]) == {style.TICK_PT, style.LABEL_PT}
    assert fg["counts"] == {"ok": 3, "missing": 0, "error": 0}
    fg = mcl.figures_block(IN_ROOT, tmp_path / "no_extracts", ["fig6"])
    assert fg["rows"][0]["status"] == "missing" and fg["counts"]["missing"] == 1
    with pytest.raises(ValueError, match="no figure script"):
        mcl.figures_block(IN_ROOT, FIX, ["fig4"])
    assert _outputs_snapshot() == before
    assert list((tmp_path / "tmp").iterdir()) == []
    assert all(k not in os.environ for k in mcl.ENV_FIG_DIRS + (mcl.ENV_IN_ROOT,))
    rep = mcl.build(IN_ROOT, only=["fig6", "sf_e6a"], extracts=FIX)
    md = mcl.markdown(rep)
    assert "| fig6 | `figs/fig6_e10.py` | ok |" in md and "| sf_e6a | `figs/supp/sf_e6a.py` | ok |" in md
    assert "2 of 2 redrawn from their extracts" in md and _outputs_snapshot() == before


def test_command_line_writes_only_under_out_dir(tmp_path, capsys):
    """--root with --out-dir writes ms3_claims.md and ms3_claims.json there (exit 0) and nothing into the
    repository; another root without --out-dir is an error; the JSON has the documented blocks."""
    before = _outputs_snapshot()
    out = tmp_path / "report"
    assert mcl.main(["--root", str(IN_ROOT), "--out-dir", str(out), "--no-figures"]) == 0
    assert sorted(p.name for p in out.iterdir()) == ["ms3_claims.json", "ms3_claims.md"]
    rep = json.loads((out / "ms3_claims.json").read_text())
    assert rep["meta"]["input_root"] == str(IN_ROOT.resolve()) and rep["meta"]["out_dir"] == str(out.resolve())
    assert rep["meta"]["input_root_is_repository"] is False and rep["figures"]["run"] is False
    md = (out / "ms3_claims.md").read_text()
    assert md.startswith("# MS3 claims report") and "**Criterion of §1.4 item 2: does not hold.**" in md
    assert "not the repository" in md and "not rerun (--no-figures)" in md
    assert "criterion does not hold" in capsys.readouterr().out
    with pytest.raises(SystemExit) as e:
        mcl.main(["--root", str(IN_ROOT), "--no-figures"])
    assert e.value.code == 2
    assert _outputs_snapshot() == before


def test_copy_block_reads_the_copy_records(tmp_path):
    """The copy block lists E11-0's record and each experiment's out/ms3_copy_<exp>.json (pass, the clone's commit,
    the failed checks); an invalid record is noted."""
    root = _tree(tmp_path)
    _write(root, "ms3_copy_e1.json", {"check": "copy", "exp": "e1", "pass": False, "clone_commit": "a" * 40,
                                      "time": "2026-10-20T09:00:00",
                                      "checks": {"same_sha256": True, "run_log_done": False}})
    (root / OUT / "ms3_copy_e10.json").write_text("{")
    cp = mcl.build(root, figures=False)["copy_checks"]
    assert cp["e1"] == {"file": f"{OUT}/ms3_copy_e1.json", "present": True, "pass": False, "commit": "a" * 40,
                        "time": "2026-10-20T09:00:00", "failed": ["run_log_done"], "records_by_status": None}
    assert cp["e10"]["present"] is False and cp["e10"]["note"].startswith("invalid JSON")
    assert cp["e2"]["present"] is False and mc.COPY_RECORD.format(exp="e2") in cp["e2"]["file"]
