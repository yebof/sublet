"""Tests of the MS5b claims report sublet/experiments/ms5b_claims.py (design/sublet_v2.md §11, W11 and W13, row
test_ms5b_claims.py). Quick: the inputs are the MS5b fixture tree tests/fixtures_figs_ms5b/inputs/ (reduced-mode
outputs of e7h's confirmation parts and the analysis on them, README there; its values are not results) and copies of
it in tmp_path with the three design documents the report reads, made unreduced and given a confirmation gate and a
copy record in the drivers' form, plus synthetic extracts, tables, float heights and rebuild records in the forms the
MS5b scripts and figs/rebuild.py write. Every output goes under pytest's tmp_path (never into paper/ or
code/sim/out/).

- the rows are W11's list in its order (parsed from the note), with the R rows covering every item of §6's
  "Reported in full" sentence and the supplementary tables of W4, and the F rows the MS5b figures of
  figs.rebuild.MS5B_SCRIPTS and Table III v2; the kinds, and H3's status labels copied, never upgraded;
- the verdict of each status; the fixture tree as it is (every summary reduced): every row that reads the summaries a
  bug, the others missing; malformed and missing inputs;
- the gate, copy, job and run rows and the recomputed analysis on a valid tree, each detecting a changed value; G-1's
  read-only check of the freeze commit in git (stubbed);
- the H rows' consequence rule: a failed hypothesis is explained only when its consequence rows hold, with the
  registered consequence quoted from the note, else a bug; the caption forms that C-H2b reads;
- the R rows against scopes recomputed independently from the fixture summaries, in the canonical shape and in the
  shapes the U39 scripts write; D-1 against the pre-registration's §7; the F rows on a stand-in figure module (build
  equal to the extract, the runs/ files' sha256); FL-1; RB-1;
- the jobs, copy, rebuild and caption blocks, the figure reruns, and the command line, which writes only under
  --out-dir.
"""
import copy
import hashlib
import json
import re
import shutil
import textwrap
from pathlib import Path
from types import SimpleNamespace

import pytest

from fixtures import SIM
from test_ms3_claims import STATUS_WORD, _label_part_copied, _norm, _split_top

from figs import rebuild as rb
from figs import style
from sublet.experiments import ms5b_claims as cb

REPO = SIM.parents[1]
FIX = Path(__file__).resolve().parent / "fixtures_figs_ms5b"
IN_ROOT = FIX / "inputs"
NOTE, PREREG, DESIGN = (REPO / "design" / "sublet_v2.md", REPO / "design" / "sublet_v2_prereg.md",
                        REPO / "design" / "Sublet_design.md")
OUT = "code/sim/out"
PARTS = ("main", "seeds", "second", "e3", "fam", "grid")
HYP = ("H1", "H2", "H2b", "H3", "H4", "H5", "H6")
# the supplementary tables of W4 with the script that writes each (their file names fixed for the claims report)
TABLES = {"e7v2_crossings.tex": "sf_e7_intensity", "e7v2_weeks.tex": "sf_e7_decomp",
          "e7v2_pareto.tex": "sf_e7_decomp", "e7v2_rc.tex": "sf_e7_decomp", "e7v2_seeds.tex": "sf_e7_decomp",
          "e7v2_table3_intervals.tex": "sf_e7_decomp", "e7v2_h3.tex": "sf_e7_decomp",
          "ms5b_outcomes.tex": "sf_e7_decomp", "e7v2_boundary.tex": "sf_e7_boundary", "e7v2_lag.tex": "sf_e7_boundary",
          "e7v2_e5.tex": "sf_e7_boundary", "e7v2_gap.tex": "sf_e7_boundary", "e7v2_grid.tex": "sf_e7_grid_dev",
          "e7v2_q44.tex": "sf_e7_grid_dev", "fam_v2_pairs.tex": "sf_fam_v2", "fam_v2_f3.tex": "sf_fam_v2",
          "fam_v2_q6.tex": "sf_fam_v2", "e3_v2.tex": "sf_e3_v2"}


# ---------------------------------------------------------------------------------------------------------------
def _p(root: Path, rel: str) -> Path:
    return root / OUT / rel


def _load(root: Path, rel: str):
    return json.loads(_p(root, rel).read_text())


def _save(root: Path, rel: str, obj) -> None:
    p = _p(root, rel)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=1))


def _sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def _rows(rep) -> dict:
    return {r["id"]: r for r in rep["rows"]}


def _row(root: Path, cid: str) -> dict:
    """One row computed on a fresh read of the tree."""
    return cb._Inputs(root).row(cid)


def _tree(tmp_path, reduced: bool = True, docs: bool = True) -> Path:
    """A copy of the fixture tree under tmp_path/in with meta.reduced set to `reduced` in the six summaries and, with
    `docs`, the note, the pre-registration and design/Sublet_design.md copied into its design/."""
    root = tmp_path / "in"
    shutil.copytree(IN_ROOT / "code", root / "code")
    for p in PARTS:
        d = _load(root, f"sublet_v2/{p}/summary.json")
        d["meta"]["reduced"] = reduced
        _save(root, f"sublet_v2/{p}/summary.json", d)
    if docs:
        (root / "design").mkdir()
        for f in (NOTE, PREREG, DESIGN):
            shutil.copy(f, root / "design" / f.name)
    return root


def _tree_digests(top: Path) -> tuple[str, str]:
    """(versioned, full) digest of the six part folders: sha256 over the sorted lines '<path>\\t<sha256>' of their
    files, without runs/ for the versioned one (this test's own computation of the copy check's digests)."""
    files = [p for p in top.rglob("*") if p.is_file() and p.relative_to(top).parts[0] in PARTS]
    lines = sorted((p.relative_to(top).as_posix(), _sha(p)) for p in files)

    def dig(ls):
        h = hashlib.sha256()
        for a, b in ls:
            h.update(f"{a}\t{b}\n".encode())
        return h.hexdigest()
    return dig([x for x in lines if "/runs/" not in f"/{x[0]}"]), dig(lines)


def _copy_record(root: Path) -> None:
    """A passing copy record of the tree as it is now (ms5b_common.check_copy's fields)."""
    commit = _load(root, "sublet_v2/main/summary.json")["meta"]["git_revision"]
    ver, full = _tree_digests(root / OUT / "sublet_v2")
    checks = {k: True for k in ("same_file_list", "same_sha256", "no_symlinks", "json_readable", "revisions",
                                "revisions_recorded", "manifest_revision", "summary_ok", "no_running_records",
                                "run_log_done")}
    _save(root, "ms3_copy_sublet_v2.json", {"check": "copy", "exp": "sublet_v2", "driver": "e7h", "pass": True,
                                            "checks": checks, "clone_commit": commit, "parts": list(PARTS),
                                            "tree_sha256": full, "tree_sha256_versioned": ver, "n_files_copy": 1,
                                            "time": "2026-11-03T12:00:00"})


def _valid(tmp_path) -> Path:
    """An unreduced copy whose gate records are those of a passing confirmation gate at the summaries' commit (the
    pre-registration and the analysis hash of the copied documents), with a matching copy record."""
    root = _tree(tmp_path, reduced=False)
    pre = (root / "design" / PREREG.name).read_text()
    line = re.search(r"^analysis_sha256:\s*([0-9a-f]{64})\s*$", pre, re.M).group(1)
    for p in PARTS:
        d = _load(root, f"sublet_v2/{p}/summary.json")
        commit = d["meta"]["git_revision"]
        d["meta"]["confirmation_gate"] = {
            "ok": True, "reason": "pre-registration at HEAD, clean tree, analysis sha256 as recorded",
            "record": {"head": commit, "prereg": "design/sublet_v2_prereg.md", "prereg_at_head": True,
                       "prereg_sha256": _sha(root / "design" / PREREG.name), "analysis_sha256_prereg": line,
                       "analysis_sha256_head": line, "analysis_sha256_disk": line, "dirty_paths": [],
                       "pilot": {"anchor_is_ancestor": True, "sections_changed_since_anchor": []}}}
        _save(root, f"sublet_v2/{p}/summary.json", d)
    _copy_record(root)
    return root


def _summaries(root: Path) -> dict:
    return {p: _load(root, f"sublet_v2/{p}/summary.json") for p in PARTS}


# ---------------------------------------------------------------------------------------------------------------
def _w11() -> str:
    text = NOTE.read_text(encoding="utf-8")
    return next(ln for ln in text.splitlines() if ln.startswith("| W11 |"))


def test_rows_follow_w11_in_order():
    """The fixed rows are W11's, once each and in its order (G-1 ... A-2, the H rows H1-H6 and H2b, C-H5, C-H2b, the R
    rows, D-1, the F rows, FL-1, RB-1); the H rows are the hypotheses of §6; the F rows are the MS5b figures of
    figs.rebuild.MS5B_SCRIPTS and Table III v2; every row has the documented keys."""
    w = _w11()
    fixed = list(dict.fromkeys(re.findall(r"\b(G-\d|A-\d|C-H\d+b?|D-\d|FL-\d|RB-\d)\b", w)))
    assert fixed == ["G-1", "G-2", "G-3", "G-4", "G-5", "A-1", "A-2", "C-H5", "C-H2b", "D-1", "FL-1", "RB-1"]
    assert "H1–H6 and H2b" in w and "R-1…" in w and "F-1…" in w
    ids = [s.id for s in cb.SPECS]
    assert len(ids) == len(set(ids))
    want = (fixed[:7] + list(HYP) + fixed[7:9] + [f"R-{i}" for i in range(1, len(cb.R_ITEMS) + 1)] + ["D-1"]
            + [f"F-{i}" for i in range(1, len(cb.F_ENTRIES) + 1)] + ["FL-1", "RB-1"])
    assert ids == want
    assert [n for n, _, _ in cb.F_ENTRIES] == list(rb.MS5B_SCRIPTS) + ["table3_v2"]
    assert [s for _, s, _ in cb.F_ENTRIES][:-1] == list(rb.MS5B_SCRIPTS.values())
    assert cb.F_ENTRIES[-1] == tuple(rb.TABLE3_V2)
    rep = cb.build(IN_ROOT, figures=False)
    assert [r["id"] for r in rep["rows"]] == ids
    keys = {"id", "group", "section", "kind", "claim", "status_label", "status_label_note", "reference",
            "regenerated", "summary_status", "verdict", "explanation", "note"}
    for r in rep["rows"]:
        assert set(r) == keys and r["verdict"] in cb.VERDICTS and r["claim"]["spec"]
        assert (r["status_label"] is None) == (r["status_label_note"] is not None)
        assert set(r["reference"]) == {"value", "values", "file"} and set(r["regenerated"]) == {"value", "file"}
    assert set(rep) == {"meta", "criterion", "rows", "figures", "copy_checks", "jobs", "rebuild", "captions"}


def test_r_rows_cover_section_6_and_w4():
    """One R row per item of §6's "Reported in full" sentence (each item named by a key phrase that one R row's item
    carries), the further R rows for the items §6 reports in H3, H4 and H5's consequence, W2's intervals and the
    outcomes; every supplementary table of W4 (with its script) mapped to exactly one R row."""
    note = NOTE.read_text(encoding="utf-8")
    sec6 = note[note.index("\n## 6. "):note.index("\n## 7. ")]
    sent = next(ln for ln in sec6.splitlines() if ln.startswith("Reported in full with no threshold:"))
    items = [x.strip(" .") for x in sent.split(":", 1)[1].split(";")]
    key = {"transplants": "R-1", "Pareto front": "R-2", "stress-intensity curve": "R-3", "RC under every mode": "R-4",
           "Q44 criteria T and S": "R-9", "policy seeds 1–2": "R-10", "development-exposed E7 grid": "R-11",
           "Q6 family runs under F-ad and F-eg": "R-12", "gap-day ALG/LB": "R-8"}
    boundary = {"L-vr, L-rf, L-ad, the p99.9 buffer": "R-5", "the E5 menus": "R-6", "lagged demand": "R-7"}
    by_id = {it.id: it for it in cb.R_ITEMS}
    for it in items:
        hits = [r for k, r in {**key, **boundary}.items() if k in it]
        assert hits, f"§6 item without an R row: {it!r}"
        for r in hits:
            assert by_id[r].source.startswith("§6, reported in full")
    assert {it.table: it.figure for it in cb.R_ITEMS} == TABLES
    assert len({it.table for it in cb.R_ITEMS}) == len(cb.R_ITEMS) == 18
    assert set(TABLES.values()) <= set(style.SUPP_POLICIES_MS5B) and set(TABLES.values()) <= set(rb.MS5B_SCRIPTS)


def test_kinds_and_labels():
    """A-1 and the F rows are reproductions, FL-1 informative, the H rows hypotheses (the only explainable rows), the
    C rows consequences; only H3 carries a status label, each part copied from the note, the pre-registration or the
    design (normalized as test_ms3_claims does), and an upgraded label is not found there."""
    kinds = {s.id: s.kind for s in cb.SPECS}
    assert {i for i, k in kinds.items() if k == "reproduction"} == {"A-1"} | {f"F-{i}" for i in range(1, 10)}
    assert {i for i, k in kinds.items() if k == "informative"} == {"FL-1"}
    assert {i for i, k in kinds.items() if k == "hypothesis"} == set(HYP)
    assert {s.id for s in cb.SPECS if s.explainable} == set(HYP)
    assert {i for i, k in kinds.items() if k == "consequence"} == {"C-H5", "C-H2b"}
    src = _norm("\n".join(p.read_text(encoding="utf-8") for p in (NOTE, PREREG, DESIGN)))
    labelled = [s for s in cb.SPECS if s.label is not None]
    assert [s.id for s in labelled] == ["H3"]
    bad = [p for s in labelled for p in _split_top(s.label) if STATUS_WORD.search(p) and not _label_part_copied(p, src)]
    assert not bad, bad
    for s in cb.SPECS:
        if s.label is None:
            assert s.label_note and not STATUS_WORD.search(s.label_note), s.id
    up = cb.PROP_P.replace("(d) under its three float hypotheses", "(d) PROVEN")
    assert not _label_part_copied(up, src)


@pytest.mark.parametrize("kind, status, explainable, want", [
    ("reproduction", "pass", False, "reproduced"), ("property", "pass", False, "holds"),
    ("hypothesis", "pass", True, "holds"), ("consequence", "pass", False, "holds"),
    ("informative", "pass", False, "informative"), ("informative", "informative", False, "informative"),
    ("consequence", "informative", False, "informative"), ("hypothesis", "informative", True, "informative"),
    ("property", "informative", False, "bug"), ("property", "fail", False, "bug"), ("hypothesis", "fail", True, "bug"),
    ("hypothesis", "explained", True, "explained"), ("property", "explained", False, "bug"),
    ("property", "missing", False, "missing"), ("property", "pending", False, "pending"),
    ("property", "bug_input", False, "bug"), ("property", None, False, "bug"), ("property", "done", False, "bug"),
])
def test_verdict_of_each_status(kind, status, explainable, want):
    v, note = cb.verdict(kind, status, explainable)
    assert v == want
    if want == "bug" and status not in ("fail", "bug_input"):
        assert note


def test_fixture_tree_as_is():
    """The fixture tree (every summary reduced): each row that reads the summaries or analysis.json (G, A, H, C, R) is
    a bug whose note names the reduced summaries; D-1, the F rows, FL-1 and RB-1 are missing (no pre-registration, no
    script, extract, heights or rebuild record there); the criterion does not hold."""
    rep = cb.build(IN_ROOT, figures=False)
    for r in rep["rows"]:
        if r["group"] in ("G", "A", "H", "C", "R"):
            assert r["verdict"] == "bug" and "reduced run" in r["note"], (r["id"], r["note"])
            assert f"{OUT}/sublet_v2/main/summary.json" in r["note"]
        elif r["group"] == "F" and (REPO / cb.F_ENTRIES[int(r["id"][2:]) - 1][1]).is_file():
            assert r["verdict"] in ("missing", "bug"), r["id"]          # a script landed: its extract is not there
        else:
            assert r["verdict"] == "missing", (r["id"], r["note"])
    c = rep["criterion"]
    assert not c["holds"] and set(c["bug"]) >= {"G-1", "A-1", "H1", "C-H5", "R-1"}


def test_valid_tree_gates_and_analysis(tmp_path):
    """On an unreduced copy with a passing gate and copy record: G-1 to G-5 hold, A-1 is reproduced (analysis.json
    equals the recomputation, the hashes agree) and A-2 holds."""
    root = _valid(tmp_path)
    rows = _rows(cb.build(root, figures=False))
    for cid in ("G-1", "G-2", "G-3", "G-4", "G-5", "A-2"):
        assert rows[cid]["verdict"] == "holds", (cid, rows[cid]["note"])
    assert rows["A-1"]["verdict"] == "reproduced", rows["A-1"]["note"]
    v = rows["A-1"]["regenerated"]["value"]
    assert v["equal"] is True and v["n_differences"] == 0
    assert v["sha256"] == v["analysis_sha256_prereg"] == v["analysis_sha256_module"]
    g1 = rows["G-1"]["regenerated"]["value"]
    assert g1["freeze_commit"] == _load(root, "sublet_v2/main/summary.json")["meta"]["git_revision"]
    assert g1["prereg_sha256"] == _sha(PREREG)
    assert rows["G-5"]["regenerated"]["value"]["n_runs"] == sum(len(S["runs"]) for S in _summaries(root).values())
    assert rows["A-2"]["reference"]["values"]["registered"] == {"H4_wording": "deployed", "H5_status": "primary",
                                                               "H6_threshold": 0.01}


def _edited(tmp_path, name, change):
    """A fresh valid tree in tmp_path/<name> with `change(root)` applied."""
    d = tmp_path / name
    d.mkdir()
    root = _valid(d)
    change(root)
    return root


def _set(rel, fn):
    def change(root):
        d = _load(root, rel)
        fn(d)
        _save(root, rel, d)
    return change


def test_computed_rows_detect_changes(tmp_path):
    """Each G and A row turns into a bug (or missing) when its input changes: the pre-registration edited (G-1, A-2
    keep their own), a dirty gate, a second commit, a versioned file changed after the copy check and no copy record,
    a job record removed and a job not ok, a run not ok and an invariant failure, a value of analysis.json changed,
    the config changed."""
    def prereg_edit(root):
        p = root / "design" / PREREG.name
        p.write_text(p.read_text() + "\nA line added after the freeze.\n")
    cases = [
        ("prereg", prereg_edit, "G-1", "bug", "sha256 now"),
        ("dirty", _set("sublet_v2/seeds/summary.json",
                       lambda d: d["meta"]["confirmation_gate"]["record"].update(dirty_paths=[" M x"])), "G-1", "bug",
         "dirty paths"),
        ("gate", _set("sublet_v2/e3/summary.json", lambda d: d["meta"]["confirmation_gate"].update(ok=False)), "G-1",
         "bug", "gate ok False"),
        ("commit", _set("sublet_v2/fam/summary.json", lambda d: d["meta"].update(git_revision="f" * 40)), "G-2",
         "bug", "git revisions"),
        ("copy_changed", lambda r: (_p(r, "sublet_v2/main/tables.md").write_text("changed\n")), "G-3", "bug",
         "changed since the copy check"),
        ("copy_missing", lambda r: _p(r, "ms3_copy_sublet_v2.json").unlink(), "G-3", "missing", "missing"),
        ("record_gone", lambda r: next(iter(sorted(_p(r, "sublet_v2/grid/jobs").glob("e7h__grid__*.json")))).unlink(),
         "G-4", "bug", "without an 'ok' record"),
        ("not_ok", _set("sublet_v2/main/summary.json", lambda d: d["meta"].update(jobs_not_ok={"x": "failed"})),
         "G-4", "bug", "jobs_not_ok"),
        ("run_status", _set("sublet_v2/second/summary.json", lambda d: d["runs"][0].update(status="crashed")),
         "G-5", "bug", "not ok"),
        ("invariant", _set("sublet_v2/fam/summary.json", lambda d: d["runs"][3].update(n_invariant_failures=2)),
         "G-5", "bug", "invariant"),
        ("analysis", _set("sublet_v2/analysis.json", lambda d: d["H1"].update(wins=d["H1"]["wins"] + 1)), "A-1",
         "bug", "$.H1.wins"),
        ("analysis_meta", _set("sublet_v2/analysis.json", lambda d: d["meta"].update(pilot_dry_run=True)), "A-1",
         "bug", "pilot_dry_run"),
        ("config", _set("sublet_v2/analysis.json", lambda d: d["config"].update(H6_threshold=0.02)), "A-2", "bug",
         "not the registered"),
    ]
    for name, change, cid, want, words in cases:
        root = _edited(tmp_path, name, change)
        r = _row(root, cid)
        assert r["verdict"] == want and words in (r["note"] or ""), (name, r["verdict"], r["note"])


def test_reduced_and_malformed_inputs(tmp_path):
    """One reduced summary makes every G, A, H, C and R row a bug and leaves the D, F, FL and RB rows alone; a summary
    that is not a JSON object, or an analysis.json that is a list, makes its rows bugs; a missing analysis.json makes
    the A, H and C rows missing; the report is still written."""
    root = _valid(tmp_path)
    d = _load(root, "sublet_v2/grid/summary.json")
    d["meta"]["reduced"] = True
    _save(root, "sublet_v2/grid/summary.json", d)
    rows = _rows(cb.build(root, figures=False))
    assert {i for i, r in rows.items() if r["verdict"] == "bug"} == \
        {s.id for s in cb.SPECS if s.group in ("G", "A", "H", "C", "R")}
    assert all("sublet_v2/grid/summary.json from a reduced run" in rows[i]["note"] for i in ("G-5", "H1", "R-3"))
    d["meta"]["reduced"] = False
    _save(root, "sublet_v2/grid/summary.json", d)
    seeds = _p(root, "sublet_v2/seeds/summary.json")
    keep = seeds.read_text()
    seeds.write_text("[1, 2]")
    rows = _rows(cb.build(root, figures=False))
    for cid in ("G-1", "G-2", "G-4", "G-5", "A-1"):
        assert rows[cid]["verdict"] == "bug" and "not an object" in rows[cid]["note"], cid
    seeds.write_text(keep)
    _p(root, "sublet_v2/analysis.json").write_text("[1]")
    rows = _rows(cb.build(root, figures=False))
    assert all(rows[i]["verdict"] == "bug" and "not an object" in rows[i]["note"]
               for i in ("A-1", "A-2", "H1", "C-H5"))
    _p(root, "sublet_v2/analysis.json").unlink()
    rep = cb.build(root, figures=False)
    rows = _rows(rep)
    assert all(rows[i]["verdict"] == "missing" for i in ("A-1", "A-2", *HYP, "C-H5", "C-H2b"))
    assert rep["meta"]["inputs"][f"{OUT}/sublet_v2/analysis.json"] == "missing"
    pm, pj = cb.write(rep, tmp_path / "out")
    assert pm.is_file() and json.loads(pj.read_text())["criterion"]["holds"] is False


# ---------------------------------------------------------------- R rows: scopes recomputed here
def _dims(runs, keys):
    f = {"tags": "tag", "modes": "mode", "cells": "cell", "seeds": "seed"}
    return {k: sorted({str(r[f[k]]) for r in runs}) for k in keys}


IID = ("L-hon", "L-iid-0.05", "L-iid-0.1", "L-iid-0.2", "L-iid-0.34", "L-iid-0.5", "L-iid-0.8", "L-iid-1")


def oracle_scopes(root: Path) -> dict:
    """{table: scope} recomputed by this test from the summaries (analysis.json only for the hypotheses' names), by
    the rules of §4.5 and §6, independently of the report's code."""
    S = _summaries(root)
    week = {p: [r for r in S[p]["runs"] if r["kind"] == "week"] for p in ("main", "seeds", "second", "grid")}
    main0 = [r for r in week["main"] if r["seed"] == 0]
    out = {"e7v2_weeks.tex": _dims(main0, ("tags", "cells"))}
    abl = {"BL1N", "CR"} | {t for t in {r["tag"] for r in main0} if t.startswith("A9-")}
    out["e7v2_pareto.tex"] = {"cells": sorted({r["cell"] for r in main0}),
                              "tags": sorted({r["tag"] for r in main0} - abl)}
    pts: dict = {}
    for r in week["main"] + week["second"]:
        if r["seed"] == 0 and r["mode"] in IID:
            pts.setdefault((r["tag"], r["cell"]), set()).add(r["mode"])
    cur = [k for k, v in pts.items() if len(v) > 1]
    out["e7v2_crossings.tex"] = {"tags": sorted({t for t, _ in cur}), "cells": sorted({c for _, c in cur})}
    hon = {(r["tag"], r["cell"], r["seed"]) for p in ("main", "seeds") for r in week[p] if r["mode"] == "L-hon"}
    rc = [r for p in ("main", "seeds", "second") for r in week[p]
          if r["mode"] != "L-hon" and (r["tag"], r["cell"], r["seed"]) in hon]
    out["e7v2_rc.tex"] = _dims(rc, ("tags", "modes", "cells", "seeds"))
    out["e7v2_boundary.tex"] = _dims([r for r in week["second"] if r["mode"] in ("L-vr", "L-rf", "L-ad", "L-b999")],
                                     ("tags", "modes", "cells"))
    out["e7v2_e5.tex"] = _dims([r for r in S["second"]["runs"] if r["kind"] == "e5"], ("tags", "modes", "cells"))
    out["e7v2_lag.tex"] = _dims([r for r in week["second"] if r["tag"].endswith("-lag")], ("tags", "cells"))
    out["e7v2_gap.tex"] = _dims([r for r in S["second"]["runs"] if r["kind"] == "gap"], ("tags", "cells"))
    out["e7v2_q44.tex"] = _dims([r for r in S["grid"]["runs"] if r["kind"] == "q44"], ("tags", "cells"))
    out["e7v2_seeds.tex"] = _dims(week["seeds"], ("tags", "modes", "cells", "seeds"))
    out["e7v2_grid.tex"] = _dims([r for r in S["grid"]["runs"] if r["kind"] in ("week", "gap")],
                                 ("tags", "modes", "cells", "seeds"))
    fam = [r for r in S["fam"]["runs"] if r["kind"] == "fam"]
    out["fam_v2_q6.tex"] = _dims([r for r in fam if not r["src"].startswith("C") and r["mode"] in ("F-ad", "F-eg")],
                                 ("tags", "modes", "cells", "seeds"))
    out["e7v2_h3.tex"] = {"parts": sorted(p for p in PARTS if S[p]["guarded"]),
                          "tags": sorted({g["tag"] for p in PARTS for g in S[p]["guarded"]})}
    out["fam_v2_f3.tex"] = _dims([r for r in fam if r["fam"] == "F3"], ("tags", "cells"))
    pairs = S["fam"]["fam"]["pairs"]
    out["fam_v2_pairs.tex"] = {"families": sorted({x["fam"] for x in pairs}),           # W4: by family and lender
                               "modes": sorted({x["mode"] for x in pairs})}
    out["e3_v2.tex"] = _dims([r for r in S["e3"]["runs"] if r["kind"] == "e3cell"], ("tags", "modes", "cells"))
    t3 = {"Sublet", "Sublet-1way", "BL1-GP", "BL1N", "BL5N", "BL1", "BL1-BO", "BL5-cur", "BL5-tau60", "BL2", "BL3-0",
          "BL4", "A6"}
    gap3 = [r for r in S["second"]["runs"] if r["kind"] == "gap" and r["tag"] in t3]
    out["e7v2_table3_intervals.tex"] = _dims([r for r in main0 if r["tag"] in t3] + gap3, ("tags", "cells"))
    a = _load(root, "sublet_v2/analysis.json")
    out["ms5b_outcomes.tex"] = {"hypotheses": [h for h in HYP if h in a]}
    return out


RC_RUNS = "policy,tag,lender_mode,week,policy_seed,rc\nSublet,Sublet,L-tr,301,0,0.0\nSublet,Sublet,L-ad,301,0,0.1\n"


def _write_tables(root: Path, scopes: dict, reduced: bool = False) -> None:
    """The supplementary tables (a one-line stand-in each), R-4's data file e7v2_rc_runs.csv (a stand-in of two
    data rows) and each script's extract with its tables block, which records the data file's sha256 and rows."""
    by_fig: dict = {}
    for table, fig in TABLES.items():
        p = root / "paper" / "supplement" / "tables" / table
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(f"% stand-in for {table}\n")
        by_fig.setdefault(fig, {})[table] = {"scope": scopes[table], "rows": 1}
    (root / "paper" / "supplement" / "tables" / "e7v2_rc_runs.csv").write_text(RC_RUNS)
    by_fig["sf_e7_decomp"]["e7v2_rc_runs"] = {"file": "e7v2_rc_runs.csv", "n_rows": 2,
                                              "sha256": hashlib.sha256(RC_RUNS.encode()).hexdigest()}
    for fig, tables in by_fig.items():
        _save(root, f"figs/{fig}.json", {"figure": fig, "size_in": [7.08, 2.4], "sources": [],
                                         "data": {"tables": tables, "meta": {"reduced": reduced},
                                                  "labels": {"caption": f"{fig} draft."}}})


def test_r_rows_against_recomputed_scopes(tmp_path):
    """The report's required scope of each R row equals this test's recomputation from the summaries; with every
    table present and its extract's scope equal to that recomputation, every R row holds; a value left out of a
    scope, a dimension left out, the table file absent, the extract absent or its tables block without the table
    make the row missing, naming what lacks; a scope keyed by the file's stem is read; a reduced extract makes it a
    bug."""
    root = _valid(tmp_path)
    scopes = oracle_scopes(root)
    rows = _rows(cb.build(root, figures=False))
    for it in cb.R_ITEMS:
        assert rows[it.id]["verdict"] == "missing", it.id
        assert rows[it.id]["regenerated"]["value"]["required"] == {k: len(v) for k, v in scopes[it.table].items()}, \
            it.id
    _write_tables(root, scopes)
    rows = _rows(cb.build(root, figures=False))
    for it in cb.R_ITEMS:
        assert rows[it.id]["verdict"] == "holds", (it.id, rows[it.id]["note"])
    ext = _load(root, "figs/sf_e7_decomp.json")
    good = copy.deepcopy(ext)
    rc = ext["data"]["tables"]["e7v2_rc.tex"]["scope"]
    dropped = rc["seeds"].pop()
    _save(root, "figs/sf_e7_decomp.json", ext)
    r = _row(root, "R-4")
    assert r["verdict"] == "missing" and f"seeds ['{dropped}']" in r["note"]
    del ext["data"]["tables"]["e7v2_rc.tex"]["scope"]["modes"]
    _save(root, "figs/sf_e7_decomp.json", ext)
    assert "modes ['<absent>'" in _row(root, "R-4")["note"]
    ext = copy.deepcopy(good)
    ext["data"]["tables"]["e7v2_weeks"] = ext["data"]["tables"].pop("e7v2_weeks.tex")
    _save(root, "figs/sf_e7_decomp.json", ext)
    assert _row(root, "R-1")["verdict"] == "holds"
    del ext["data"]["tables"]["e7v2_weeks"]
    _save(root, "figs/sf_e7_decomp.json", ext)
    r = _row(root, "R-1")
    assert r["verdict"] == "missing" and "no tables.e7v2_weeks.tex" in r["note"]
    _save(root, "figs/sf_e7_decomp.json", good)
    (root / "paper" / "supplement" / "tables" / "e7v2_pareto.tex").unlink()
    r = _row(root, "R-2")
    assert r["verdict"] == "missing" and "e7v2_pareto.tex absent" in r["note"]
    _p(root, "figs/sf_fam_v2.json").unlink()
    r = _row(root, "R-12")
    assert r["verdict"] == "missing" and "sf_fam_v2.json missing" in r["note"]
    csv = root / "paper" / "supplement" / "tables" / "e7v2_rc_runs.csv"
    r = _row(root, "R-4")
    assert r["verdict"] == "holds" and r["regenerated"]["value"]["data_rows"] == 2
    csv.write_text(RC_RUNS + "Sublet,Sublet,L-eg,301,0,0.2\n")
    r = _row(root, "R-4")
    assert r["verdict"] == "bug" and "sha256 unlike" in r["note"] and "3 data rows" in r["note"]
    csv.unlink()
    r = _row(root, "R-4")
    assert r["verdict"] == "missing" and "e7v2_rc_runs.csv absent" in r["note"]
    csv.write_text(RC_RUNS)
    bad = copy.deepcopy(good)
    del bad["data"]["tables"]["e7v2_rc_runs"]
    _save(root, "figs/sf_e7_decomp.json", bad)
    r = _row(root, "R-4")
    assert r["verdict"] == "missing" and "no tables.e7v2_rc_runs" in r["note"]
    bad = copy.deepcopy(good)
    bad["data"]["meta"]["reduced"] = True
    _save(root, "figs/sf_e7_decomp.json", bad)
    r = _row(root, "R-4")
    assert r["verdict"] == "bug" and "reduced run" in r["note"]


def u39_style(table: str, sc: dict) -> dict:
    """The oracle scope `sc` of `table` in the shapes the U39 scripts write (W4 leaves the keys to them): week cells
    under 'weeks', gap days under 'days', RC's weeks per row, E5's cells split into menus and config seeds with the
    modes as 'levels', E3's into b and config seeds, the families' into instances and modes, Q44's cells by instance,
    the grid's into alignments and gap days, seeds as numbers, and scalar entries (n_runs, u)."""
    sc = copy.deepcopy(sc)
    cells = sc.pop("cells", None)
    if "seeds" in sc:
        sc["seeds"] = [int(x) for x in sc["seeds"]]
    if table == "e7v2_e5.tex":
        sc.update(menus=sorted({c.split(":")[0] for c in cells}), cells=sorted({c.split(":")[1] for c in cells}),
                  levels=sc.pop("modes"))
    elif table == "e3_v2.tex":
        sc.update(b=sorted({int(c.split(":")[0][1:]) for c in cells}), seeds=sorted({c.split(":")[1] for c in cells}),
                  u=8.0, mu=1.0)
    elif table in ("fam_v2_q6.tex", "fam_v2_f3.tex"):
        sc.update(instances=sorted({c.split(":")[0] for c in cells}),
                  modes=sorted(set(sc.get("modes", [])) | {c.split(":")[1] for c in cells}))
    elif table == "e7v2_q44.tex":
        by: dict = {}
        for c in cells:
            by.setdefault(c.split(":")[0], []).append(c)
        sc["cells"] = by
    elif table == "e7v2_grid.tex":
        sc.update(alignments=[c for c in cells if ":" not in c], gap_days=[c for c in cells if ":" in c])
    elif table == "e7v2_gap.tex":
        sc["days"] = cells
    elif table == "e7v2_rc.tex":
        sc.update(weeks_by_row={"Sublet|L-tr|0": cells}, n_runs=3)
    elif cells is not None:
        sc["weeks"] = cells
    if table == "e7v2_h3.tex":
        sc["n_runs"] = 5
    if table == "fam_v2_pairs.tex":
        sc["sets"] = ["Q6", "fresh"]
    return sc


def test_r_rows_accept_the_scripts_shapes(tmp_path):
    """The scopes in the shapes the U39 scripts write (aliases of the cell and mode keys, composite cells split into
    their parts, config seeds as 'c301' or 301, mapping and scalar entries) cover the same required values: every R
    row holds. A value left out of such a scope (a b of E3, the grid's gap days) or a cell key the report does not
    know still makes the row missing, naming the cells."""
    root = _valid(tmp_path)
    scopes = oracle_scopes(root)
    styled = {t: u39_style(t, sc) for t, sc in scopes.items()}
    _write_tables(root, styled)
    rows = _rows(cb.build(root, figures=False))
    for it in cb.R_ITEMS:
        assert rows[it.id]["verdict"] == "holds", (it.id, rows[it.id]["note"], styled[it.table])
    b1 = min(styled["e3_v2.tex"]["b"])
    for table, cid, change, word in (
            ("e3_v2.tex", "R-16", lambda sc: sc["b"].remove(b1), f"b{b1}:"),
            ("e7v2_grid.tex", "R-11", lambda sc: sc.pop("gap_days"), "gap:"),
            ("e7v2_weeks.tex", "R-1", lambda sc: sc.update(periods=sc.pop("weeks")), "<absent>")):
        bad = copy.deepcopy(styled)
        change(bad[table])
        _write_tables(root, bad)
        r = _row(root, cid)
        assert r["verdict"] == "missing" and word in r["note"], (table, r["note"])
    _write_tables(root, styled)
    assert cb.uncovered({"cells": ["b8:c301"], "seeds": ["0"]}, {"b": [8.0], "seeds": ["c301", 0]}) == {}
    assert cb.uncovered({"cells": ["301", "gap:c301"]}, {"weeks": ["c301"], "tags": ["gap"]}) == {}
    assert cb.uncovered({"cells": ["gap:c1"]}, {"alignments": ["1"]}) == {"cells": ["gap:c1"]}
    assert cb.uncovered({"modes": ["L-tr"]}, {"tags": ["L-tr"]}) == {"modes": ["<absent>", "L-tr"]}


def test_g1_verifies_the_freeze_commit_in_git(tmp_path, monkeypatch):
    """Where the root is the top of a git work tree, G-1 reads the pre-registration and the analysis script at the
    gate's head (read-only git; stubbed here): equal sha256 hold (freeze_in_git true), another pre-registration at the
    head is a bug, a history without the commit is a note; a tree without git leaves freeze_in_git null."""
    root = _valid(tmp_path)
    head = _load(root, "sublet_v2/main/summary.json")["meta"]["git_revision"]
    pre = (root / "design" / PREREG.name).read_bytes()
    ana = (SIM / "sublet" / "experiments" / "ms5b_analysis.py").read_bytes()
    assert _row(root, "G-1")["regenerated"]["value"]["freeze_in_git"] is None
    state = {"pre": pre, "has": True}

    def fake(cmd, **kw):
        assert cmd[:3] == ["git", "-C", str(root)], cmd
        if cmd[3] == "rev-parse":
            return SimpleNamespace(returncode=0, stdout=f"{root}\n".encode())
        if cmd[3] == "cat-file":
            return SimpleNamespace(returncode=0 if state["has"] else 1, stdout=b"")
        assert cmd[3] == "show" and cmd[4].startswith(f"{head}:"), cmd
        return SimpleNamespace(returncode=0, stdout=state["pre"] if cmd[4].endswith(PREREG.name) else ana)
    monkeypatch.setattr(cb.subprocess, "run", fake)
    r = _row(root, "G-1")
    assert r["verdict"] == "holds" and r["regenerated"]["value"]["freeze_in_git"] is True, r["note"]
    state["pre"] = pre + b"\nedited\n"
    r = _row(root, "G-1")
    assert r["verdict"] == "bug" and "at the freeze commit" in r["note"], r["note"]
    state.update(pre=pre, has=False)
    r = _row(root, "G-1")
    assert r["verdict"] == "holds" and "lacks the freeze commit" in r["note"]


def test_caption_forms():
    """H2b's count as 'k of n', 'k of the n', 'k out of n' or 'k/n' (not inside a longer number); H1's set named by the
    phrase or by every policy, a registry label found through LaTeX wrappers (\\mbox, braces)."""
    assert cb.states_count("below in 3/16: 302", 3, 16) and cb.states_count("in 3 of the 16 weeks", 3, 16)
    assert cb.states_count("3 out of 16", 3, 16) and not cb.states_count("13 of 16", 3, 16)
    assert not cb.states_count("3 of 160", 3, 16)
    assert cb.names_policy(r"SpotHedge-style, \mbox{$N_{\mathrm{Extra}}=0$}; CoCaR-style", "BL3-0")
    assert cb.names_h1_set("the least of H1's set minus Sublet") == (True, list(cb.m5.H1_SET))
    named, unnamed = cb.names_h1_set("Greedy renting and CoCaR-style")
    assert not named and "BL2" in unnamed and "BL1" not in unnamed


# ---------------------------------------------------------------- H rows and their consequence rows
def _consequences(note: str) -> dict:
    """{hypothesis: [the sentences of §6's *Consequences.* paragraph whose lead names it]} (this test's parse)."""
    sec6 = note[note.index("\n## 6. "):note.index("\n## 7. ")]
    para = next(ln for ln in sec6.splitlines() if ln.startswith("*Consequences.*"))[len("*Consequences.* "):]
    out: dict = {}
    for s in re.split(r"(?<=\.) (?=H\d)", para):
        for h in re.findall(r"\bH\d+b?\b", s.split(":")[0]):
            out.setdefault(h, []).append(s)
    return out


def _failing_analysis(root: Path) -> None:
    """analysis.json with H1-H4 and H6 passing and H2b and H5 failing as at the confirmation (a week in which
    BL5-tau60's W0 is below Sublet's; Sublet above Sublet-MS4 at b = 1)."""
    def fn(a):
        for h in ("H1", "H2", "H3", "H4", "H6"):
            a[h]["pass"] = True
        a["H2b"]["pass"] = False
        w = a["H2b"]["weeks"][0]
        w.update(below_all=False)
        w["others"]["BL5-tau60"] = w["Sublet"] - 0.01
        a["H2b"]["weeks_below_set"] = 0
        a["H5"]["pass"] = False
        a["H5"]["b"][0].update(le_MS4=False, Sublet_MS4_shared=a["H5"]["b"][0]["Sublet_shared"] - 0.004)
    _set("sublet_v2/analysis.json", fn)(root)


def _main_text_extracts(root: Path, caption: str, extra_sources=()) -> None:
    _save(root, "figs/fig4v2.json", {"figure": "fig4v2", "size_in": [7.08, 2.4],
                                     "sources": [f"{OUT}/sublet_v2/main/summary.json", *extra_sources],
                                     "data": {"labels": {"caption": caption}, "meta": {"reduced": False}}})
    _save(root, "figs/table3_v2.json", {"table": "table3_v2", "sources": [f"{OUT}/sublet_v2/main/summary.json"],
                                        "data": {"labels": {"caption": caption}, "meta": {"reduced": False}}})


H1_NAMES = ("Greedy renting, Greedy, back-off, Per-borrower ski rental, SpotHedge-style, $N_{\\mathrm{Extra}}=0$, "
            "CoCaR-style, RetroRenting-style, lagged, and RetroRenting-style")


def test_h_rows_and_the_consequence_rule(tmp_path):
    """A passing hypothesis holds. A failed one is explained only when every consequence row holds: without the
    main-text extracts and the tables its H row is a bug naming the missing consequence rows; with captions that state
    H2b's count and name H1's set, extracts without E3 data, design §2.7's sharing item and the outcome and E3 tables,
    C-H5, C-H2b, R-16 and R-18 hold and H2b and H5 are explained, the text giving the measured failure and quoting the
    registered consequence of the note's §6 (the frozen fig4.json, replaced under W6, may hold E3 data); the drafts'
    own forms (a count 'k/n', "H1's set" by name, labels in \\mbox) are read; a caption saying 'every baseline', a
    caption without the count or without H1's set, an E3 source or an H5 key in fig4v2's extract, an E3 source in a
    frozen main-text extract (fig7), or design §2.7 without the item make the consequence row, and so the H row, a
    bug; a failed H1 (no consequence row) is a bug; H6 without a threshold is informative."""
    root = _valid(tmp_path)
    _failing_analysis(root)
    rows = _rows(cb.build(root, figures=False))
    for h in ("H1", "H2", "H3", "H4", "H6"):
        assert rows[h]["verdict"] == "holds", (h, rows[h]["note"])
    reg = {h: s for h, s in cb.registered_statements(PREREG.read_text()).items()}
    assert rows["H1"]["claim"]["summary"] == f"H1 ({reg['H1'][0]}): {reg['H1'][1]}"
    for h, cons in (("H2b", ("C-H2b", "R-18")), ("H5", ("C-H5", "R-16"))):
        assert rows[h]["verdict"] == "bug" and all(f"{c} missing" in rows[h]["note"] for c in cons), rows[h]["note"]
    n = _load(root, "sublet_v2/analysis.json")["H2b"]["n_weeks"]
    cap = f"BL5-tau60's $W_0$ is below Sublet's in {n} of {n} weeks (H2b); H1's set: {H1_NAMES}."
    _main_text_extracts(root, cap)
    _write_tables(root, oracle_scopes(root))
    # the frozen Fig. 4 (E7 and E3), which W6 replaces by fig4v2, is not a main-text extract
    _save(root, "figs/fig4.json", {"figure": "fig4", "sources": [f"{OUT}/e3/summary.json"], "data": {"e3": {}}})
    rows = _rows(cb.build(root, figures=False))
    for c in ("C-H5", "C-H2b", "R-16", "R-18"):
        assert rows[c]["verdict"] == "holds", (c, rows[c]["note"])
    quotes = _consequences(NOTE.read_text(encoding="utf-8"))
    for h in ("H2b", "H5"):
        r = rows[h]
        assert r["verdict"] == "explained" and r["explanation"], (h, r["note"])
        assert all(q in r["explanation"] for q in quotes[h]), r["explanation"]
    assert "BL5-tau60" in rows["H2b"]["explanation"] and "b = 1" in rows["H5"]["explanation"]
    assert '"The paper says that Sublet has a lower worst case than every baseline only if H2 and H2b both hold; ' \
        'with H2 alone it names H1\'s set."' in rows["H2b"]["explanation"]
    # every other row passes but A-1 (analysis.json was edited here) and the rows whose files this test does not make
    assert rep_holds_but(cb.build(root, figures=False),
                         {"A-1", "D-1", "FL-1", "RB-1"} | {f"F-{i}" for i in range(1, 10)})
    # the drafts' own forms: Fig. 4's caption gives the count as k/n and refers to "H1's set" by name (W1); Table
    # III's lists the set with LaTeX wrappers around a label (W2) and, since C51, need not state H2b's count
    _save(root, "figs/fig4v2.json", {"figure": "fig4v2", "sources": [], "data": {"labels": {"caption": (
        f"(b) Per week, the least of H1's set minus Sublet; BL5-tau60's W0 minus Sublet's (<0 in {n}/{n}; H2b "
        "fails).")}, "meta": {"reduced": False}}})
    _save(root, "figs/table3_v2.json", {"table": "table3_v2", "sources": [], "data": {"labels": {"caption": (
        "Greedy renting; Greedy, back-off; RetroRenting-style; Per-borrower ski rental; SpotHedge-style, "
        r"\mbox{$N_{\mathrm{Extra}}=0$}; CoCaR-style; and RetroRenting-style, lagged (supplement).")},
        "meta": {"reduced": False}}})
    rows = _rows(cb.build(root, figures=False))
    assert rows["C-H2b"]["verdict"] == "holds" and rows["H2b"]["verdict"] == "explained", rows["C-H2b"]["note"]
    # a consequence row that fails turns its hypothesis into a bug
    for name, change, cid in (
            ("every", lambda r: _main_text_extracts(r, cap + " Sublet beats every baseline."), "C-H2b"),
            ("count", lambda r: _main_text_extracts(r, cap.replace(f"{n} of {n}", "most")), "C-H2b"),
            ("set", lambda r: _main_text_extracts(r, cap.replace("CoCaR-style, ", "").replace("H1's set", "the set")),
             "C-H2b"),
            ("e3", lambda r: _main_text_extracts(r, cap, [f"{OUT}/sublet_v2/e3/summary.json"]), "C-H5"),
            ("h5_key", lambda r: _set("figs/fig4v2.json", lambda d: d["data"].update(H5={"pass": False}))(r), "C-H5"),
            ("frozen", lambda r: _save(r, "figs/fig7.json", {"figure": "fig7", "sources": [f"{OUT}/e3/summary.json"],
                                                             "data": {}}), "C-H5"),
            ("design", lambda r: (r / "design" / DESIGN.name).write_text("# design\n\n### 2.7 Theory storyline\n\n"
                                                                         "- nothing\n\n### 2.8 x\n"), "C-H5")):
        d = tmp_path / f"c_{name}"
        d.mkdir()
        r2 = _valid(d)
        _failing_analysis(r2)
        _main_text_extracts(r2, cap)
        _write_tables(r2, oracle_scopes(r2))
        change(r2)
        rows = _rows(cb.build(r2, figures=False))
        hid = "H2b" if cid == "C-H2b" else "H5"
        assert rows[cid]["verdict"] == "bug" and rows[hid]["verdict"] == "bug", (name, rows[cid]["note"])
        assert f"{cid} bug" in rows[hid]["note"]
    # H1 failing has no consequence row; H2b holding leaves C-H2b informative; H6 without a threshold
    _set("sublet_v2/analysis.json", lambda a: (a["H1"].update({"pass": False}), a["H2b"].update({"pass": True}),
                                               a["H6"].update({"pass": None, "threshold": None})))(root)
    rows = _rows(cb.build(root, figures=False))
    assert rows["H1"]["verdict"] == "bug" and "no consequence row" in rows["H1"]["note"]
    assert rows["H2b"]["verdict"] == "holds" and rows["C-H2b"]["verdict"] == "informative"
    assert rows["H6"]["verdict"] == "informative"


def rep_holds_but(rep, allowed: set) -> bool:
    """Every row not in `allowed` is reproduced, holds, informative or explained (G-3 included)."""
    bad = [(r["id"], r["verdict"], r["note"]) for r in rep["rows"] if r["id"] not in allowed
           and r["verdict"] not in ("reproduced", "holds", "informative", "explained")]
    assert not bad, bad
    return True


def test_names_policy_and_h1_names():
    """A policy of H1's set is named by its tag as a whole token or by its registry label where no longer label of
    the registry starts; BL5's label is that of the lagged build."""
    assert cb.names_policy("rows BL1, BL2", "BL1") and not cb.names_policy("BL1-GP and BL1N", "BL1")
    assert not cb.names_policy("BL5-cur, BL5-tau60, BL5N", "BL5") and cb.names_policy("BL5 (lagged)", "BL5")
    assert cb.names_policy("RetroRenting-style, lagged", "BL5")
    assert not cb.names_policy("RetroRenting-style, lagged", "BL5-cur")
    assert cb.names_policy("RetroRenting-style and more", "BL5-cur")
    for tag, key in cb.H1_KEYS.items():
        assert cb.names_policy(style.POLICIES[key].label, tag), tag


# ---------------------------------------------------------------- D-1
def _md_to_tex(s: str) -> str:
    s = re.sub(r"`([^`]*)`", lambda m: r"\texttt{" + m.group(1).replace("_", r"\_") + "}", s)
    s = re.sub(r"\*([^*]+)\*", r"\\emph{\1}", s)
    return s.replace("§", r"\S{}").replace("%", r"\%")


def _prereg_items() -> dict:
    """{item: text} of the pre-registration's §7 (this test's parse)."""
    text = PREREG.read_text(encoding="utf-8")
    sec = text[text.index("\n## 7. "):text.index("\n## 8. ")]
    out, letter = {}, None
    for ln in sec.splitlines():
        m = re.match(r"^\*([A-E])\. ", ln)
        if m:
            letter = m.group(1)
        m = re.match(r"^(\d+)\. (.*)$", ln)
        if m and letter:
            out[f"{letter}{m.group(1)}"] = m.group(2).strip()
    return out


DEVS = ("B1", "B2", "B3", "B5", "B12", "B13", "C2")


def _deviations_tex(items: dict, ids=DEVS, form: str = "tabular") -> str:
    if form == "list":
        body = "\n".join(rf"\item[{k}] {_md_to_tex(items[k])}" for k in ids)
        return "\\begin{description}\n" + body + "\n\\end{description}\n"
    rows = "\n".join(rf"{k} & {_md_to_tex(items[k])} \\" for k in ids)
    return ("\\begin{table*}\n\\caption{Deviations}\\label{tab:dev}\n\\begin{tabular}{@{}lp{15cm}@{}}\n\\toprule\n"
            "Item & Change and reason \\\\\n\\midrule\n" + rows + "\n\\bottomrule\n\\end{tabular}\n\\end{table*}\n")


def test_d1(tmp_path):
    """D-1 holds when ms5b_deviations.tex lists exactly B1, B2, B3, B5, B12, B13 and C2 with their texts (a tabular,
    or a description list; the texts in LaTeX, a 'Recorded:' sentence left out); it is a bug with an item missing or
    added, a word changed or an item text swapped, and missing without the file."""
    root = _tree(tmp_path, reduced=True)
    items = _prereg_items()
    assert cb.prereg_deviations(PREREG.read_text()) == list(DEVS)
    assert cb.prereg_items(PREREG.read_text()) == items
    p = root / "paper" / "supplement" / "tables" / "ms5b_deviations.tex"
    assert _row(root, "D-1")["verdict"] == "missing"
    p.parent.mkdir(parents=True)
    p.write_text(_deviations_tex(items))
    r = _row(root, "D-1")
    assert r["verdict"] == "holds", r["note"]
    assert r["regenerated"]["value"]["listed"] == list(DEVS)
    p.write_text(_deviations_tex(items, form="list"))
    assert _row(root, "D-1")["verdict"] == "holds"
    short = {**items, "B12": items["B12"][:items["B12"].rindex("Recorded:")]}
    p.write_text(_deviations_tex(short))
    assert _row(root, "D-1")["verdict"] == "holds"
    for name, tex, words in (
            ("missing", _deviations_tex(items, ids=DEVS[:-1]), "registered but not listed ['C2']"),
            ("extra", _deviations_tex(items, ids=DEVS + ("B4",)), "listed but not registered ['B4']"),
            ("word", _deviations_tex({**items, "B5": items["B5"].replace("BL1-GP is Sublet's guard",
                                                                         "BL1-GP is a guard")}),
             "B5 (first difference"),
            ("swap", _deviations_tex({**items, "B2": items["B3"]}), "B2 (first difference")):
        p.write_text(tex)
        r = _row(root, "D-1")
        assert r["verdict"] == "bug" and words in r["note"], (name, r["note"])



def test_d1_c58_titled_rows(tmp_path):
    """C58: D-1 also holds for the table in the paper's names (rows titled by DEVIATION_TITLES, in §7's order, each
    with at least 20 words and no design ID); a missing title, a short row or a design ID is a bug."""
    root = _tree(tmp_path, reduced=True)
    p = root / "paper" / "supplement" / "tables" / "ms5b_deviations.tex"
    p.parent.mkdir(parents=True)
    text = " ".join(["the registered rule changes here for a stated reason"] * 3)

    def table(titles, body=text):
        rows = "\n".join(rf"{ti} & {body} \\ \addlinespace" for ti in titles)
        return ("\\begin{table*}[t]\n\\caption{Deviations}\\label{tab:dev}\n\\begin{tabular}{@{}lp{15cm}@{}}\n"
                "\\toprule\nItem & Deviation \\\\\n\\midrule\n" + rows + "\n\\bottomrule\n\\end{tabular}\n"
                "\\end{table*}\n")
    titles = list(cb.DEVIATION_TITLES.values())
    p.write_text(table(titles))
    r = _row(root, "D-1")
    assert r["verdict"] == "holds", r["note"]
    assert r["regenerated"]["value"]["listed"] == list(DEVS)
    for name, tex, words in (("missing", table(titles[:-1]), "registered but not listed ['C2']"),
                             ("short", table(titles, "too short"), "fewer than 20 words or a design ID"),
                             ("design id", table(titles, text + " A8P"), "fewer than 20 words or a design ID")):
        p.write_text(tex)
        r = _row(root, "D-1")
        assert r["verdict"] == "bug" and words in r["note"], (name, r["note"])

# ---------------------------------------------------------------- F rows on a stand-in figure module
FAKE = '''
"""Stand-in figure script for tests/test_ms5b_claims.py (not a figure)."""
import hashlib

NAME = "u40_fake"
SUM = "code/sim/out/sublet_v2/main/summary.json"
RUNS = {runs!r}


def build(inp):
    s = inp.json(SUM)
    sha = {{}}
    for rel in RUNS:
        sha[rel] = hashlib.sha256(inp.path(rel).read_bytes()).hexdigest()
    return {{"n_runs": len(s["runs"]), "runs_sha256": sha, "meta": {{"reduced": False}}}}
'''


def test_f_rows(tmp_path, monkeypatch):
    """An F row is reproduced when the script's build on the root equals the extract, its sources equal and every
    runs/ source listed with its sha256 (W10); a changed value, a recorded sha256 that differs, a runs/ source not
    listed, a reduced extract and an extract of another figure make it a bug; an absent runs/ file, extract or script
    makes it missing."""
    root = _valid(tmp_path)
    runs = sorted(p.relative_to(root).as_posix() for p in _p(root, "sublet_v2/main/runs").glob("*.json"))[:2]
    mod_dir = tmp_path / "mods"
    mod_dir.mkdir()
    (mod_dir / "u40_fake.py").write_text(textwrap.dedent(FAKE.format(runs=runs)))
    monkeypatch.syspath_prepend(str(mod_dir))
    script = str(mod_dir / "u40_fake.py")
    spec = cb.Spec("F-0", "F", "W10", "reproduction", claim="stand-in", label=None, label_note="test",
                   fields=cb.SPEC_BY_ID["F-1"].fields, compute=lambda inp: cb._f(inp, "u40_fake", script, "u40_fake"))

    def row():
        return cb.build_row(spec, cb._Inputs(root))
    data, sources = cb.build_figure(root, "u40_fake")
    assert len(data["runs_sha256"]) == 2 and all("/runs/" in s for s in list(data["runs_sha256"]))
    assert sources[0] == f"{OUT}/sublet_v2/main/summary.json" and len(sources) == 3
    good = {"figure": "u40_fake", "size_in": [3.5, 2.0], "sources": sources, "data": data}
    _save(root, "figs/u40_fake.json", good)
    r = row()
    assert r["verdict"] == "reproduced", r["note"]
    v = r["regenerated"]["value"]
    assert v["equal"] and v["sources_equal"] and v["n_runs_listed"] == v["n_runs_sources"] == 2
    for name, change, want, words in (
            ("value", lambda d: d["data"].update(n_runs=d["data"]["n_runs"] + 1), "bug", "$.data.n_runs"),
            ("sha", lambda d: d["data"]["runs_sha256"].update({sources[1]: "0" * 64}), "bug", "not the recorded"),
            ("unlisted", lambda d: d["data"]["runs_sha256"].pop(sources[2]), "bug", "without a sha256"),
            ("reduced", lambda d: d["data"]["meta"].update(reduced=True), "bug", "reduced run"),
            ("other", lambda d: d.update(figure="sf_e9"), "bug", "the extract of 'sf_e9'")):
        d = copy.deepcopy(good)
        change(d)
        _save(root, "figs/u40_fake.json", d)
        r = row()
        assert r["verdict"] == want and words in r["note"], (name, r["note"])
    _save(root, "figs/u40_fake.json", good)
    (root / sources[1]).unlink()
    r = row()
    assert r["verdict"] == "missing" and "absent under the root" in r["note"]
    _p(root, "figs/u40_fake.json").unlink()
    assert row()["verdict"] == "missing"
    spec2 = cb.Spec("F-0", "F", "W10", "reproduction", claim="stand-in", label=None, label_note="test",
                    compute=lambda inp: cb._f(inp, "u40_fake", str(mod_dir / "absent.py"), "absent"))
    r = cb.build_row(spec2, cb._Inputs(root))
    assert r["verdict"] == "missing" and "absent" in r["note"]
    assert cb.runs_listed({"a": [{"path": "code/sim/out/x/runs/a.json", "sha256": "1" * 64}],
                           "b": {"code/sim/out/y/runs/b.json": "2" * 64, "c": "3" * 64}}) == \
        {"code/sim/out/x/runs/a.json": "1" * 64, "code/sim/out/y/runs/b.json": "2" * 64}


# ---------------------------------------------------------------- FL-1, RB-1
def _heights(root: Path) -> dict:
    floats = {}
    for k in cb.FLOAT_NAMES_MS5B:
        p = root / "paper" / "floats" / f"{k}.tex"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(f"% {k}\n")
        floats[k] = {"measured_pages": 0.17, "budget_pages": 0.172, "within_budget": True,
                     "difference_pages": -0.002, "source": f"paper/floats/{k}.tex", "sha256": _sha(p)}
    return {"floats": floats, "written": "2026-11-04T10:00:00"}


def test_fl1(tmp_path):
    """FL-1 is informative with the three v2 floats measured and each record current; a float changed after its
    measurement is a bug (stale), a float not measured or no heights file is missing."""
    root = _tree(tmp_path)
    assert _row(root, "FL-1")["verdict"] == "missing"
    h = _heights(root)
    _save(root, "figs/floats_heights_ms5b.json", h)
    r = _row(root, "FL-1")
    assert r["verdict"] == "informative" and "Table III v2 0.17 page (budget 0.172)" in r["note"]
    (root / "paper" / "floats" / "alg1_guard_v2.tex").write_text("% changed\n")
    r = _row(root, "FL-1")
    assert r["verdict"] == "bug" and "stale" in r["note"]
    del h["floats"]["table2_policies_v2"]
    _save(root, "figs/floats_heights_ms5b.json", h)
    (root / "paper" / "floats" / "alg1_guard_v2.tex").write_text("% alg1_guard_v2\n")
    assert _row(root, "FL-1")["verdict"] == "missing"


def _rb_record(root: Path) -> dict:
    """A rebuild record of a passing MS5b exit run (figs/rebuild.py's fields that RB-1 reads), whose one compared
    output is a file of the tree, with today's entries and every hand-set file checked."""
    rel = f"{OUT}/sublet_v2/analysis.md"
    sha = _sha(root / rel)
    return {"status": "pass", "pass": True, "error": None, "reasons": [],
            "meta": {"module": "figs.rebuild", "mode": "check", "only": None, "root_is_repository": True,
                     "git_revision": "0" * 40, "tracked_files_dirty": False, "written": "2026-11-05T12:00:00",
                     "versions": {"python": "3.12.3"}, "fonts": {}},
            "coverage": {"ok": True, "unlisted": [], "missing": [], "errors": []},
            "outputs": [{"path": rel, "entry": "x", "sha256": sha, "versioned_sha256": sha, "identical": True,
                         "written": True}],
            "entries": [{"name": n, "kind": k, "outputs": o, "run": True} for n, k, o in cb._rebuild_entries()],
            "heights": {"plain": {"equal": True}, "ms4": {"equal": True}, "ms5b": {"equal": True}},
            "hand_set": [{"path": p, "ok": True} for p in rb.HAND_SET], "unexpected": [],
            "totals": {"n_scripts": 1, "n_ok": 1, "failed": [], "n_outputs": 1, "n_identical": 1, "different": [],
                       "not_written": [], "heights_equal": {"plain": True, "ms4": True, "ms5b": True}}}


def test_rb1(tmp_path):
    """RB-1 holds on the record of a passing MS5b exit run; a record without the 'ms5b' heights (MS5's exit run) is
    missing; unequal ms5b heights, a hand-set file of figs.rebuild.HAND_SET unchecked, entries other than today's
    list, and ms5_claims' conditions (here a stale output and the mode) make it a bug; no record is missing."""
    root = _tree(tmp_path)
    assert _row(root, "RB-1")["verdict"] == "missing"
    good = _rb_record(root)
    _save(root, "figs/rebuild.json", good)
    r = _row(root, "RB-1")
    assert r["verdict"] == "holds", r["note"]
    for name, change, want, words in (
            ("ms5", lambda d: d["heights"].pop("ms5b"), "missing", "earlier milestone"),
            ("heights", lambda d: d["heights"]["ms5b"].update(equal=False), "bug", "ms5b equal False"),
            ("hand", lambda d: d["hand_set"].pop(), "bug", "not checked"),
            ("entries", lambda d: d["entries"].pop(), "bug", "today's rebuild list"),
            ("stale", lambda d: d["outputs"][0].update(versioned_sha256="f" * 64), "bug", "stale"),
            ("mode", lambda d: d["meta"].update(mode="in_place"), "bug", "mode 'in_place'")):
        d = copy.deepcopy(good)
        change(d)
        _save(root, "figs/rebuild.json", d)
        r = _row(root, "RB-1")
        assert r["verdict"] == want and words in r["note"], (name, r["note"])


# ---------------------------------------------------------------- blocks, figures, command line
def test_jobs_copy_rebuild_and_caption_blocks(tmp_path):
    """The jobs block lists every job of the six manifests with the two e7h records (all 'ok' in the fixture); a
    removed record is blocking and an e3 MILP job stopped at the wall-clock limit is not (Q39), so G-4 still holds;
    the copy block reads the sublet_v2 record; the rebuild block the record; the caption drafts come from the
    extracts of the MS5b figures and Table III v2, a reduced one noted."""
    root = _valid(tmp_path)
    jb = cb.jobs_block(cb._Inputs(root))
    assert list(jb["rows"]) == list(PARTS) and jb["n_blocking"] == 0
    for p in PARTS:
        n = len(_load(root, f"sublet_v2/{p}/manifest.json")["jobs"])
        r = jb["rows"][p]
        assert r["present"] and r["n_listed"] == n and r["by_status"] == {"ok": n + 2} and r["n_unlisted_records"] == 0
    jobs = _p(root, "sublet_v2/e3/jobs")
    milp = next(p for p in sorted(jobs.glob("e3__milp__*.json")))
    rec = json.loads(milp.read_text())
    rec["status"] = "wall_limit"
    milp.write_text(json.dumps(rec))
    week = next(p for p in sorted(_p(root, "sublet_v2/main/jobs").glob("e7h__main__*.json")))
    week.unlink()
    jb = cb.jobs_block(cb._Inputs(root))
    assert jb["rows"]["e3"]["n_blocking"] == 0 and jb["rows"]["e3"]["n_milp_lp_fallback"] == 1
    assert jb["rows"]["main"]["n_blocking"] == 1 and jb["rows"]["main"]["blocking"][0]["status"] == "no record"
    g4 = _row(root, "G-4")
    assert g4["verdict"] == "bug" and "main: " in g4["note"] and "e3: " not in g4["note"]
    cp = cb.copy_block(cb._Inputs(root))
    assert list(cp["records"]) == ["sublet_v2"] and cp["records"]["sublet_v2"]["pass"] is True
    assert cp["one_commit"] is True
    assert not cb.rebuild_block(cb._Inputs(root))["present"]
    _save(root, "figs/fig4v2.json", {"figure": "fig4v2", "data": {"labels": {"caption": "Draft."},
                                                                 "meta": {"reduced": True}}, "sources": []})
    _save(root, "figs/table3_v2.json", {"table": "table3_v2", "data": {"caption": "Table draft."}, "sources": []})
    cap = cb.captions_block(cb._Inputs(root), root / OUT / "figs")
    assert list(cap) == [n for n, _, _ in cb.F_ENTRIES]
    assert cap["fig4v2"]["text"] == "Draft." and cap["fig4v2"]["reduced"]
    assert "drafted from a reduced run (never a result)" in cap["fig4v2"]["notes"]
    assert cap["table3_v2"]["text"] == "Table draft." and cap["table3_v2"]["n_chars"] == 12
    assert cap["sf_e3_v2"]["text"] is None and "missing" in cap["sf_e3_v2"]["notes"][0]


def _outputs_snapshot() -> dict:
    snap = {}
    for d in (REPO / "paper" / "figures", REPO / "paper" / "supplement", REPO / "paper" / "floats",
              SIM / "out" / "figs"):
        for p in sorted(d.rglob("*")) if d.is_dir() else []:
            if p.is_file():
                snap[str(p)] = p.stat().st_mtime_ns
    for name in (cb.OUT_MD, cb.OUT_JSON):
        p = SIM / "out" / name
        snap[str(p)] = p.stat().st_mtime_ns if p.exists() else None
    return snap


def test_figures_block(tmp_path, monkeypatch):
    """The figure reruns cover the eight MS5b figures (not Table III v2, a float), in MS5B_SCRIPTS' order: a script
    not yet written is an error row, one written redraws from its fixture extract with finalize() passing; nothing is
    written into paper/ or code/sim/out/figs/, and the temporary folder is removed."""
    import tempfile
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    before = _outputs_snapshot()
    fg = cb.figures_block(IN_ROOT, FIX)
    assert [r["figure"] for r in fg["rows"]] == list(rb.MS5B_SCRIPTS)
    for r, (name, script) in zip(fg["rows"], rb.MS5B_SCRIPTS.items()):
        if not (REPO / script).is_file():
            assert r["status"] == "error" and "missing" in r["error"], name
        elif (FIX / f"{name}.json").is_file():
            assert r["status"] == "ok", (name, r["error"])
    assert not list(tmp_path.glob("ms4_claims_figs_*"))
    with pytest.raises(ValueError):
        cb.figures_block(IN_ROOT, FIX, only=["sf_e9"])
    assert _outputs_snapshot() == before


def test_command_line_writes_only_under_out_dir(tmp_path):
    """The command line writes ms5b_claims.md and .json under --out-dir alone and requires --out-dir with a root that
    is not the repository; the markdown has a table per group of rows and the blocks' sections."""
    root = _valid(tmp_path)
    before = _outputs_snapshot()
    assert cb.main(["--root", str(root), "--out-dir", str(tmp_path / "o"), "--no-figures"]) == 0
    assert sorted(p.name for p in (tmp_path / "o").iterdir()) == ["ms5b_claims.json", "ms5b_claims.md"]
    md = (tmp_path / "o" / "ms5b_claims.md").read_text()
    for head in ("## G: Gates and provenance", "## A: The analysis", "## H: Hypotheses", "## C: Consequences",
                 "## R: Reported in full", "## D: Deviations", "## F: Figures and floats", "## FL: Float heights",
                 "## RB: Rebuild", "## Copy check (§4.3)", "## Jobs (§4.5; Q39)", "## Rebuild record",
                 "## Caption drafts"):
        assert head in md, head
    rep = json.loads((tmp_path / "o" / "ms5b_claims.json").read_text())
    assert rep["meta"]["input_root_is_repository"] is False and rep["figures"]["run"] is False
    assert [r["id"] for r in rep["rows"]] == [s.id for s in cb.SPECS]
    with pytest.raises(SystemExit):
        cb.main(["--root", str(root), "--no-figures"])
    assert _outputs_snapshot() == before
