"""Tests of the frozen rebuild figs/rebuild.py and code/sim/figs/run_all.sh (design/sim_spec_ms5.md §8; §10, row
test_rebuild.py). Quick; the float-height cases are skipped without pdflatex.

- the list against the versioned PDFs, tables and extracts of this checkout (no file without an entry; the entries
  without a file are at most the MS5 figures and tables, which the integrator writes after the runs), its kinds and
  its failure on an unlisted file, a missing file, a figure without a script and two scripts of one figure;
- run_all.sh with CHECK=1 and ONLY on a temporary tree (a copy of the five folders of this checkout, with a
  placeholder for each listed file that does not exist yet, so that the coverage holds): byte-identical outputs and
  exit 0, then a changed byte reported with its path and exit 1; the record's fields; the work folder left with the
  record and the log alone; nothing written into the repository;
- the in-place mode on a temporary tree (the outputs rewritten where they live, byte-identical);
- the float heights compared on every key but 'written' (unit, and a CHECK=1 run of floats_heights.py on the tree);
- the hand-set files' sha256 check (unit), and its failure on a changed float in a CHECK=1 run;
- DRY_RUN=1 printing the list, and the usage errors.

C45 (design/sublet_v2.md §11, W12): the list now also holds C41's and C42's MS5b entries (fig4v2, the seven MS5b
supplementary figures, Table III v2, floats_heights_ms5b and three hand-set files), whose files the MS5b units write
later (U37-U39 and the MS5b exit run), so the counts, the entries allowed without a file and the placeholders of the
temporary tree change; each changed line names C45. The tests of C42 itself are in tests/test_ms5b_additions_figs.py.

C47 (design/ms6_spec.md M1, §2 U42): the list also holds C46's fig1v2, the paper's Fig. 1, between fig1 and fig2, listed
from rb.MS6_SCRIPTS until unit U44 writes figs/fig1_v2.py and its outputs; each changed line names C47. C47
(design/ms6_spec.md M7, §2 U45): floats_heights.py \\inputs the label stub paper/generated/labels_stub.tex on its mock
pages, so the temporary tree of the float-height case holds it too.

C52 (design/ms7/plan.md D3 and §4, unit T1): sf_e6a writes the data file e6a_cells.csv beside its summary table
e6a_cells.tex (its TABLES), so its entry lists four outputs after the figure's three; each changed line names C52.

C58 (design/ms7/w_spec.md §4, unit W-G4; registration of unit W-G4-0): the list also holds the eight supplementary
figures of the MS7 runs (rb.MS7_SUPP_SCRIPTS), listed from that map until units W-G4 A-C write their scripts and pending
until their run outputs are copied in, so the supplementary count and the scripts' count change; each changed line
names C58. The tests of the W-G4 entries themselves are in tests/test_ms7_supp_registry.py.
"""
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from fixtures import SIM

from figs import rebuild as rb
from figs import style

REPO = SIM.parents[1]
RUN_ALL = SIM / "figs" / "run_all.sh"
PDFLATEX = Path.home() / ".local" / "bin" / "pdflatex"
MS5_FIGURES = ("sf_s1", "sf_e9", "sf_slack")
# C45: the entries of C41 and C42 whose files the MS5b units write later (design/sublet_v2.md §11, W12, W16)
MS5B_ENTRIES = tuple(rb.MS5B_SCRIPTS) + (rb.TABLE3_V2[0], "floats_heights_ms5b", "table2_policies_v2.tex",
                                         "alg1_guard_v2.tex", "ms5b_deviations.tex")
# C47: the entry of C46 whose files unit U44 writes later (design/ms6_spec.md M1); C47 (review of the gate): allowed
# missing only until the run record code/sim/out/fig1v2/run.json is copied in from the clean clone, after which the
# figure's outputs must exist like every other entry's
MS6_ENTRIES = () if (REPO / "code" / "sim" / "out" / "fig1v2" / "run.json").is_file() else tuple(rb.MS6_SCRIPTS)
MODE_VARS = ("CHECK", "ONLY", "DRY_RUN", "KEEP", "WORK", "REBUILD_ROOT")
LAYOUT_FILES = ("paper/layout_check/IEEEtran.cls", "paper/layout_check/pageplan/floats_heights.py",
                "paper/layout_check/pageplan/A_body.tex", "paper/layout_check/pageplan/F_none.tex",
                "paper/layout_check/pageplan/F_tab8.tex", "paper/layout_check/pageplan/F_alg16.tex",
                # C47 (design/ms6_spec.md M7, unit U45): floats_heights.py \inputs the label stub on its mock pages
                "paper/generated/labels_stub.tex")


@pytest.fixture(scope="module", autouse=True)
def registry_without_test_figures():
    """style.FIGURES is process-global, and earlier test modules register test-only figures in it ('test_*', the
    convention that test_figs_style.py's test_supplementary_sizes_in_use_are_covered filters). rebuild.entries()
    treats every key as a figure that needs a script, so this module runs on the registry without them; they are
    restored afterwards."""
    leaked = {k: v for k, v in style.FIGURES.items() if k.startswith("test_")}
    for k in leaked:
        del style.FIGURES[k]
    yield
    style.FIGURES.update(leaked)


@pytest.fixture(scope="module")
def ents(registry_without_test_figures):
    return rb.entries()


def _tree(tmp_path: Path, ents, layout: bool = False) -> Path:
    """A copy of the five folders of this checkout under tmp_path/tree, with a placeholder for every listed file that
    does not exist yet (the MS5 figures until the integrator writes them), so that the coverage holds; with `layout`
    also the files floats_heights.py needs (its script, the class, the fill text and the probes)."""
    root = tmp_path / "tree"
    for d in rb.COVERAGE_DIRS:
        if (REPO / d).is_dir():
            shutil.copytree(REPO / d, root / d)
    placed = set()
    for e in ents:
        for rel in e.outputs:
            if e.kind != "record" and not (root / rel).is_file():
                (root / rel).parent.mkdir(parents=True, exist_ok=True)
                (root / rel).write_bytes(b"placeholder\n")
                placed.add(rel)
    # C45: a placeholder heights record of the MS5b floats (C42, until floats_heights.py --ms5b writes the real one)
    # holds the sha256 of the placeholder v2 floats, so that the hand-set check holds on the tree
    hrec = "code/sim/out/figs/floats_heights_ms5b.json"
    if hrec in placed:
        floats = {Path(rel).stem: {"sha256": rb.sha256(root / rel)} for rel, r in rb.HAND_SET_HEIGHTS.items()
                  if r == hrec}
        (root / hrec).write_text(json.dumps({"floats": floats}, indent=1) + "\n")
    for rel in LAYOUT_FILES if layout else ():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO / rel, root / rel)
    return root


def run_all(**env_extra) -> subprocess.CompletedProcess:
    """code/sim/figs/run_all.sh with the given mode variables, the figure variables of the test process removed."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("SUBLET_FIGS_") and k not in MODE_VARS}
    env.update({k: str(v) for k, v in env_extra.items()})
    return subprocess.run([str(RUN_ALL)], env=env, capture_output=True, text=True, timeout=900)


@pytest.fixture()
def repo_unchanged():
    """The repository's five folders are not written by the test (sha256 and mtime of every file)."""
    before = rb.snapshot(REPO)
    yield
    assert rb.snapshot(REPO) == before, "the test wrote into the repository's figure folders"


# ---------------------------------------------------------------------------------------------------------------
def test_list_covers_the_versioned_files(ents):
    """The list holds every main-text and supplementary figure of style.FIGURES (each with its script, the supplementary
    tables of its TABLES or TABLE), Table III, the print sheet, the two float-height measurements, the four hand-set
    files and the record; names and outputs are unique; no file of the five folders of this checkout lacks an entry,
    and the entries without a file are at most the MS5 figures' outputs."""
    kinds = {}
    for e in ents:
        kinds.setdefault(e.kind, []).append(e)
    n_supp = len(list((SIM / "figs" / "supp").glob("sf_*.py")))
    # C45: C41 and C42 add fig4v2, the seven MS5b supplementary figures (listed from rb.MS5B_SCRIPTS until their
    # scripts exist), Table III v2, the --ms5b heights and three hand-set files
    # C47: and C46's fig1v2 (main 9); C58: and fig1v3 (main 10); C58 (W-G2): fig4v3 (main 11), Tables IV and V
    # C58 (W-G4): and the eight MS7 supplementary figures (rb.MS7_SUPP_SCRIPTS)
    # MS8: and the MS8 supplementary figures (rb.MS8_SUPP_SCRIPTS, one block per writer unit)
    assert {k: len(v) for k, v in kinds.items()} == {"main": 11, "supp": 25 + 7 + 8 + len(rb.MS8_SUPP_SCRIPTS),
                                                    "float": 4, "print_sheet": 1, "heights": 4, "hand_set": 12,
                                                    "record": 1}
    # C58: the --ms7 heights and five hand-set files (four MS7 floats and the supplement's Algorithm S1)
    n_ms5b = sum((REPO / s).is_file() for n, s in rb.MS5B_SCRIPTS.items() if n != "fig4v2")
    n_ms7 = sum((REPO / s).is_file() for s in rb.MS7_SUPP_SCRIPTS.values())          # C58 (W-G4): those written
    n_ms8 = sum((REPO / s).is_file() for s in rb.MS8_SUPP_SCRIPTS.values())          # MS8: those written
    assert n_supp == 25 + n_ms5b + n_ms7 + n_ms8
    assert [e.name for e in kinds["main"]] == ["fig1", "fig1v2", "fig1v3", "fig2", "fig3", "fig4", "fig4v2", "fig4v3",
                                               "fig5", "fig6", "fig7"]  # C47: fig1v2 after fig1; C58: fig1v3, fig4v3
    assert (kinds["main"][1].script, kinds["main"][1].module) == ("code/sim/figs/fig1_v2.py", "figs.fig1_v2")  # C47
    assert {e.name for e in kinds["main"] + kinds["supp"]} == set(style.FIGURES)
    assert all(style.FIGURES[e.name].main == (e.kind == "main") for e in kinds["main"] + kinds["supp"])
    names = [e.name for e in ents]
    outs = [p for e in ents for p in e.outputs]
    assert len(set(names)) == len(names) and len(set(outs)) == len(outs)
    by = {e.name: e for e in ents}
    assert by["sf_e7_mix"].outputs[3:] == tuple(f"paper/supplement/tables/{t}" for t in (
        "table3_intervals.tex", "e7_total_accounting.tex", "e7_stress_aborts.tex"))
    assert by["sf_e6a"].outputs[3:] == ("paper/supplement/tables/e6a_cells.tex",
                                         "paper/supplement/tables/e6a_cells.csv")                       # C52
    assert by["sf_s1"].outputs[3:] == ("paper/supplement/tables/s1_points.tex", "paper/supplement/tables/s1_q28.tex")
    assert by["sf_e9"].outputs[3:] == ("paper/supplement/tables/e9_steps.tex",)
    assert by["table3_e7"].outputs == ("paper/floats/table3_e7.tex", "code/sim/out/figs/table3_e7.json")
    assert by["table3_v2"].outputs == ("paper/floats/table3_v2.tex", "code/sim/out/figs/table3_v2.json")    # C45
    assert by["print_check"].outputs == ("code/sim/out/figs/print_check.pdf",)
    assert {e.outputs[0] for e in kinds["hand_set"]} == set(rb.HAND_SET)
    assert [e.args for e in kinds["heights"]] == [(), ("--ms4",), ("--ms5b",),          # C45: C42's --ms5b
                                                  ("--ms7", "--allow-missing")]           # C58
    cov = rb.coverage(REPO, ents)
    assert cov["unlisted"] == [], cov["unlisted"]
    # C45: and MS5b's; C47: and C46's fig1v2 until U44 writes it
    ms5 = {p for e in ents if e.name in MS5_FIGURES + MS5B_ENTRIES + MS6_ENTRIES for p in e.outputs}
    assert set(cov["missing"]) <= ms5, sorted(set(cov["missing"]) - ms5)
    assert [e.name for e in rb.select(ents, None)] == [e.name for e in ents if e.runs]
    assert [e.name for e in rb.select(ents, r"^fig6$|sf_e6a")] == ["fig6", "sf_e6a"]
    assert [e.name for e in rb.select(ents, "floats_heights")] == ["floats_heights", "floats_heights_ms4",
                                                                   "floats_heights_ms5b",       # C45: C42
                                                                   "floats_heights_ms7"]        # C58


def test_list_fails_on_an_unlisted_file_and_a_missing_file(tmp_path, ents):
    """In a temporary tree the coverage holds; a file without an entry in any of the five folders and a listed file
    that is missing make it fail, each named."""
    root = _tree(tmp_path, ents)
    assert rb.coverage(root, ents)["ok"]
    extra = ["paper/supplement/figures/sf_extra.pdf", "paper/supplement/tables/extra.tex", "paper/floats/extra.tex",
             "code/sim/out/figs/stray.json", "paper/figures/sub/fig9.pdf"]
    for rel in extra:
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text("x")
    (root / "code/sim/out/figs/sf_e8.png").unlink()
    cov = rb.coverage(root, ents)
    assert not cov["ok"] and cov["unlisted"] == sorted(extra) and cov["missing"] == ["code/sim/out/figs/sf_e8.png"]
    # the record need not exist (the first rebuild writes it; after the exit run the checkout versions one)
    (root / rb.RECORD).unlink(missing_ok=True)
    assert rb.RECORD not in rb.coverage(root, ents)["missing"]


def test_list_errors(monkeypatch):
    """A registered figure that no script draws, and two scripts that draw one figure, are list errors."""
    monkeypatch.setitem(style.FIGURES, "sf_ghost", style.FigureSpec("sf_ghost", "W1", 2.2, main=False))
    with pytest.raises(rb.RebuildError, match="sf_ghost"):
        rb.entries()
    monkeypatch.delitem(style.FIGURES, "sf_ghost")
    scripts = rb.figure_scripts()
    twice = scripts + [s for s in scripts if s[1] == "figs.supp.sf_e6a"]
    monkeypatch.setattr(rb, "figure_scripts", lambda: twice)
    with pytest.raises(rb.RebuildError, match="both draw 'sf_e6a'"):
        rb.entries()


def test_check_only_identical_then_a_changed_byte(tmp_path, ents, repo_unchanged):
    """CHECK=1 ONLY=<two scripts> on a temporary tree: a main-text figure and a supplementary figure with its table
    rebuilt byte-identical, exit 0, the record with the fields of §8.3, the work folder left with the record and the
    log alone; then one changed byte of the versioned fig6.pdf and a changed hand-set float: exit 1, the PDF named
    with its first differing byte, the float named."""
    root = _tree(tmp_path, ents)
    work = tmp_path / "w1"
    r = run_all(CHECK=1, ONLY=r"^(fig6|sf_e6a)$", REBUILD_ROOT=root, WORK=work)
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-2000:]
    assert sorted(p.name for p in work.iterdir()) == ["rebuild.json", "rebuild.log"]
    rec = json.loads((work / "rebuild.json").read_text())
    assert rec["status"] == "pass" and rec["pass"] is True and rec["meta"]["mode"] == "check"
    assert rec["meta"]["root"] == str(root.resolve()) and rec["meta"]["root_is_repository"] is False
    assert [s["name"] for s in rec["scripts"]] == ["fig6", "sf_e6a"]
    assert all(s["status"] == "ok" for s in rec["scripts"])
    assert all(isinstance(s["wall_s"], float) and s["peak_rss_kb"] > 0 for s in rec["scripts"])
    want = [p for e in ents if e.name in ("fig6", "sf_e6a") for p in e.outputs]
    assert [o["path"] for o in rec["outputs"]] == want and len(want) == 8                     # C52: e6a_cells.csv
    assert all(o["identical"] and o["sha256"] == o["versioned_sha256"] and len(o["sha256"]) == 64
               for o in rec["outputs"])
    assert set(rec["meta"]["versions"]) == {"python", "numpy", "scipy", "matplotlib", "pymupdf", "pillow", "poppler",
                                            "ghostscript", "pdflatex"}
    assert set(rec["meta"]["fonts"]) == {"Liberation Sans regular", "Liberation Sans bold", "Liberation Sans italic",
                                         "STIXGeneral"}
    assert all(len(v["sha256"] or "") == 64 for v in rec["meta"]["fonts"].values())
    assert rec["coverage"]["ok"] and rec["unexpected"] == [] and rec["repo_check"]["changed"] == []
    assert rec["heights"] == {} and all(h["ok"] for h in rec["hand_set"])
    assert [e["name"] for e in rec["entries"] if e["run"]] == ["fig6", "sf_e6a"]
    # one changed byte of a versioned PDF, and a hand-set float changed since its height was measured
    pdf = root / "paper/figures/fig6.pdf"
    b = bytearray(pdf.read_bytes())
    b[-10] ^= 0x01
    pdf.write_bytes(bytes(b))
    t1 = root / "paper/floats/table1_price_of_revocation.tex"
    t1.write_text(t1.read_text() + "% changed\n")
    work2 = tmp_path / "w2"
    r = run_all(CHECK=1, ONLY=r"^fig6$", REBUILD_ROOT=root, WORK=work2, KEEP=1)
    assert r.returncode == 1
    assert "paper/figures/fig6.pdf" in r.stdout and "table1_price_of_revocation.tex" in r.stdout
    rec = json.loads((work2 / "rebuild.json").read_text())
    assert rec["status"] == "fail" and rec["totals"]["different"] == ["paper/figures/fig6.pdf"]
    o = next(x for x in rec["outputs"] if x["path"] == "paper/figures/fig6.pdf")
    assert not o["identical"] and o["first_diff_offset"] == len(b) - 10
    h = next(x for x in rec["hand_set"] if x["path"].endswith("table1_price_of_revocation.tex"))
    assert h["unchanged"] and h["matches_heights_record"] is False and not h["ok"]
    assert (work2 / "paper/figures/fig6.pdf").is_file()          # KEEP=1 keeps the rebuilt files


def test_in_place_mode_rewrites_where_the_files_live(tmp_path, ents, repo_unchanged):
    """In place on a temporary tree: the outputs are rewritten in the tree (new mtimes), byte-identical, the record
    goes to the tree's code/sim/out/figs/rebuild.json, and no other file of the five folders changes."""
    root = _tree(tmp_path, ents)
    before = rb.snapshot(root)
    r = run_all(ONLY=r"^fig6$", REBUILD_ROOT=root, WORK=tmp_path / "w")
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-2000:]
    rec = json.loads((root / rb.RECORD).read_text())
    assert rec["status"] == "pass" and rec["meta"]["mode"] == "in_place" and rec["repo_check"] is None
    assert all(o["written"] and o["identical"] for o in rec["outputs"]) and len(rec["outputs"]) == 3
    after = rb.snapshot(root)
    changed = sorted(p for p in set(before) | set(after) if before.get(p) != after.get(p))
    assert changed == sorted(["paper/figures/fig6.pdf", "code/sim/out/figs/fig6.json", "code/sim/out/figs/fig6.png",
                              rb.RECORD])
    assert all(before[p][0] == after[p][0] for p in changed if p != rb.RECORD)


def test_heights_compared_on_every_key_but_written():
    """M31: two float-height records equal but for 'written' compare equal; any other difference is named."""
    a = json.loads((REPO / "code/sim/out/figs/floats_heights.json").read_text())
    b = json.loads(json.dumps(a))
    b["written"] = "2000-01-01T00:00:00"
    assert rb.heights_diff(b, a) == []
    c = json.loads(json.dumps(b))
    c["floats"]["alg1_guard"]["measured_pages"] += 0.001
    del c["probes"]["tab8"]
    c["pdflatex"] = "another"
    assert rb.heights_diff(c, a) == ["floats.alg1_guard.measured_pages", "pdflatex", "probes.tab8 (only versioned)"]
    d = json.loads(json.dumps(a))
    d["floats"]["alg1_guard"]["written"] = "x"            # only the top-level 'written' is ignored
    assert rb.heights_diff(d, a) == ["floats.alg1_guard.written (only rebuilt)"]


@pytest.mark.skipif(not PDFLATEX.is_file(), reason=f"{PDFLATEX} is not installed")
def test_heights_rebuilt_on_a_tree(tmp_path, ents, repo_unchanged):
    """floats_heights.py (plain) re-measured under CHECK=1 on a temporary tree equals the versioned
    floats_heights.json on every key but 'written'; in place it leaves the versioned file as it is; a changed measured
    value in the versioned file makes the CHECK run fail."""
    root = _tree(tmp_path, ents, layout=True)
    r = run_all(CHECK=1, ONLY=r"^floats_heights$", REBUILD_ROOT=root, WORK=tmp_path / "w1")
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-2000:]
    h = json.loads((tmp_path / "w1" / "rebuild.json").read_text())["heights"]
    assert list(h) == ["plain"] and h["plain"]["equal"] and h["plain"]["differing_keys"] == []
    ver = root / "code/sim/out/figs/floats_heights.json"
    st = ver.stat().st_mtime_ns
    r = run_all(ONLY=r"^floats_heights$", REBUILD_ROOT=root, WORK=tmp_path / "w2")
    assert r.returncode == 0, r.stdout[-3000:]
    assert ver.stat().st_mtime_ns == st and not json.loads((root / rb.RECORD).read_text())["heights"]["plain"][
        "moved_into_place"]
    d = json.loads(ver.read_text())
    d["floats"]["table2_policies"]["measured_pages"] = 0.5
    ver.write_text(json.dumps(d, indent=1) + "\n")
    r = run_all(CHECK=1, ONLY=r"^floats_heights$", REBUILD_ROOT=root, WORK=tmp_path / "w3")
    assert r.returncode == 1
    h = json.loads((tmp_path / "w3" / "rebuild.json").read_text())["heights"]["plain"]
    assert not h["equal"] and h["differing_keys"] == ["floats.table2_policies.measured_pages"]


def test_hand_set_check(tmp_path, ents):
    """M32: each hand-set file unchanged by the run and, for the floats, the one floats_heights.json measured; a file
    changed during the run, a float changed since it was measured, a changed print-check record and a missing file
    each fail."""
    root = _tree(tmp_path, ents)
    snap = rb.snapshot(root)
    res = rb.hand_set_check(root, snap, snap)
    assert [h["path"] for h in res] == list(rb.HAND_SET) and all(h["ok"] for h in res)
    # C45: C42's two v2 floats (checked against floats_heights_ms5b.json) and ms5b_deviations.tex (no record)
    # C58: the four MS7 floats (floats_heights_ms7.json) and alg_s1_guard.tex (supplement table, no record)
    assert [h["matches_heights_record"] for h in res] == [True, True, True, None, True, True, None,
                                                          True, True, True, True, None]
    md = "code/sim/out/figs/print_check.md"
    (root / md).write_text((root / md).read_text() + "x")
    after = rb.snapshot(root)
    res = {h["path"]: h for h in rb.hand_set_check(root, snap, after)}
    assert not res[md]["unchanged"] and not res[md]["ok"]
    alg = "paper/floats/alg1_guard.tex"
    (root / alg).write_text("changed\n")
    snap2 = rb.snapshot(root)
    res = {h["path"]: h for h in rb.hand_set_check(root, snap2, snap2)}
    assert res[alg]["unchanged"] and res[alg]["matches_heights_record"] is False and not res[alg]["ok"]
    (root / "paper/floats/table2_policies.tex").unlink()
    snap3 = rb.snapshot(root)
    res = {h["path"]: h for h in rb.hand_set_check(root, snap3, snap3)}
    assert not res["paper/floats/table2_policies.tex"]["exists"] and not res["paper/floats/table2_policies.tex"]["ok"]


def test_dry_run_prints_the_list(ents, repo_unchanged, tmp_path):
    """DRY_RUN=1 prints one line per entry (those that would run marked '*') and the coverage, writes no record and
    exits 0; a mode variable other than 0 or 1 and an invalid ONLY are usage errors (exit 2)."""
    r = run_all(DRY_RUN=1, ONLY=r"^fig6$")
    assert r.returncode == 0, r.stderr
    lines = r.stdout.splitlines()
    assert lines[0].startswith(f"[rebuild] {len(ents)} entries") and "1 to run" in lines[0]
    for e in ents:
        row = [ln for ln in lines if ln[2:].split()[:2] == [e.kind, e.name]]
        assert len(row) == 1, e.name
        assert row[0].startswith("*" if e.name == "fig6" else " ") and e.outputs[0] in row[0]
    assert any(ln.startswith("[rebuild] coverage: ") for ln in lines)
    assert run_all(CHECK=2).returncode == 2
    assert run_all(DRY_RUN=1, ONLY="(").returncode == 2
    (tmp_path / "busy").mkdir()
    (tmp_path / "busy" / "x").write_text("x")
    assert run_all(CHECK=1, ONLY=r"^fig6$", WORK=tmp_path / "busy").returncode == 2
