"""Tests of the supplementary items of the MS8 budget-cap runs (design/ms8/plan.md D2, W; design/ms8/registration.md
§3, X6): figs/supp/sf_cap.py (figure, tables cap_runs, cap_sens and cap_checks, data file cap_runs.csv), its registry
keys in figs/style.py's MS8 unit F6 block and its entry in figs/rebuild.py's MS8 block X6.

Quick. The inputs are the input tree tests/fixtures_figs_ms8/x6/inputs/ (a reduced-mode output of the budget-cap runs'
registered analysis, development week 101; README there, not results) and the fixture extract
tests/fixtures_figs_ms8/x6/sf_cap.json (what the script writes on that tree; refresh_extracts.py there). Every file is
written under pytest's tmp_path. The oracles recompute the printed numbers from the analysis independently of the
script, on a fresh build() of the input tree (fixture `fresh`), not only on the fixture extract.

- Registration: the seven keys as built (label, color, marker, fill, group, family; note naming the tag), each triple
  and label no other key's, no pinned (color, marker) pair, no design name in a label, appended after the MS7 keys;
  MS8_KEY_OF_TAG covers e7b's cap tags; the set in legend order passing check_policies and check_legacy with no (marker,
  fill) twice; W2 x 2.5 in; the rebuild entry (outputs with TABLES, run inputs RUN_INPUTS, pending in a tree without the
  run output, ordinary with it).
- --from-extract on the fixture extract saves at the registered size with finalize() passing, writes the extract it
  read and every table, and a second redraw is byte for byte the same.
- build() on the input tree gives the fixture extract's data and reads only its run output.
- Reported in full: every run of the analysis is a line of the data file with its values; every tag of part week, every
  point and tag of part sens, every cap and reference of the margins, and every check and reading appear in the tables
  with the analysis's numbers; the figure's numbers are the analysis's.
- The figure draws the registered keys, names policies by registry labels and prints no design name.
- A missing run output exits 2 and names the file; reduced input is never written into paper/ or code/sim/out/figs/.
- At real scale (a stand-in analysis of 16 weeks made in tmp_path by fixtures_figs_ms8/x6/standin.py; its numbers exist
  only in the test) the figure saves with finalize() passing and the tables compile in the supplement's class without
  an overfull box (pdflatex, if installed).
- The review of unit F6 (findings 1-12), on mutated copies of the input tree under tmp_path and at real scale: the
  caption's statement on Sublet follows the reading; the points' r0 and W0 weeks are named apart; R1 per tag, R2 per
  mode, the greedy caps against Greedy + guard at the points, every tag and cap per lender (cap_modes), the binds and
  kept shares (tab:cap-binds) are printed; the run-time column marks a subset; W/T/L names the winner; (a) draws six
  series with bars in W0 and W0+ only; markers clear the spines; (b) has a glyph per column; no run at the points and a
  cap without any run still render; the stand-in with the repository's real frozen summaries renders (identity holds).
"""
from __future__ import annotations

import builtins
import csv
import importlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from figs import rebuild as rb
from figs import style
from figs.inputs import Inputs

FIX = Path(__file__).resolve().parent / "fixtures_figs_ms8" / "x6"
IN_ROOT = FIX / "inputs"
ANALYSIS = IN_ROOT / "code" / "sim" / "out" / "e7b" / "analysis.json"
REPO = style.REPO
NAME = "sf_cap"
MODULE = "figs.supp.sf_cap"
TABLES = ("cap_runs.tex", "cap_modes.tex", "cap_sens.tex", "cap_checks.tex", "cap_runs.csv")
RUN_INPUTS = ("code/sim/out/e7b/analysis.json",)
STALE = ("tests/fixtures_figs_ms8/x6/sf_cap.json is stale (the script's data changed): refresh it with "
         "`python tests/fixtures_figs_ms8/x6/refresh_extracts.py` from code/sim")
PDFLATEX = Path.home() / ".local/bin/pdflatex"
DESIGN = re.compile(r"\b(BL\d|A\d\b|A9|X\d\b|H\d\b|MS\d|e7b\b|e7r\b)|\bCR-cap|\bGR-cap|-cap-")
PU, OR = "#CC79A7", "#E69F00"
WANT = {   # key: (label, color, marker, fill, group, family, tag)
    "cap_cr_b": (r"Critical-ratio renting, cap $B(t)$", PU, ">", "filled", "baseline", "cap_cr", "CR-cap-B"),
    "cap_cr_0": ("Critical-ratio renting, cap 0", PU, ">", "open", "baseline", "cap_cr", "CR-cap-0"),
    "cap_cr_5": ("Critical-ratio renting, cap 5%", PU, "o", "open", "baseline", "cap_cr", "CR-cap-5"),
    "cap_cr_latch": (r"Critical-ratio renting, latched cap $B(t)$", PU, "H", "filled", "baseline", "cap_cr",
                     "CR-cap-B-latch"),
    "cap_cr_slot": (r"Critical-ratio renting, slot-count cap $B(t)$", PU, "X", "filled", "baseline", "cap_cr",
                    "CR-cap-B-slot"),
    "cap_gr_b": (r"Greedy renting, cap $B(t)$", OR, "P", "filled", "baseline", "bl1", "GR-cap-B"),
    "cap_gr_0": ("Greedy renting, cap 0", OR, "s", "open", "baseline", "bl1", "GR-cap-0"),
}
PINNED = ("a3_rot", "cold", "psi_01", "psi_03", "psi_05", "a6_red_off", "a6_always2", "bl3_n0", "bl3_n1")

pytestmark = pytest.mark.filterwarnings("ignore::figs.style.GlyphSizeWarning")


def module():
    return importlib.import_module(MODULE)


def payload():
    return json.loads((FIX / f"{NAME}.json").read_text())


def data():
    return payload()["data"]


def analysis():
    return json.loads(ANALYSIS.read_text())


def build_on(root: Path) -> dict:
    from figs.common import json_number
    old = os.environ.get("SUBLET_FIGS_IN_ROOT")
    os.environ["SUBLET_FIGS_IN_ROOT"] = str(root)
    try:
        d = module().build(Inputs())
    finally:
        if old is None:
            os.environ.pop("SUBLET_FIGS_IN_ROOT", None)
        else:
            os.environ["SUBLET_FIGS_IN_ROOT"] = old
    return json.loads(json.dumps(d, allow_nan=False, default=json_number))


@pytest.fixture(scope="module")
def fresh():
    return build_on(IN_ROOT)


@pytest.fixture
def figs_env(tmp_path, monkeypatch):
    monkeypatch.setenv("SUBLET_FIGS_IN_ROOT", str(IN_ROOT))
    monkeypatch.setenv(style.ENV_PDF_DIR, str(tmp_path / "pdf"))
    monkeypatch.setenv(style.ENV_OUT_DIR, str(tmp_path / "out"))
    monkeypatch.setenv("SUBLET_FIGS_TABLES_DIR", str(tmp_path / "tables"))
    return tmp_path


def tex_of(table: str, d=None) -> str:
    """The text of a table file that the after hook writes from the data `d` (default: the fixture extract), without
    its comment line."""
    mod = module()
    d = data() if d is None else d
    t = d["tables"]
    if table == "cap_runs.csv":
        from figs.supp import ms7_x3_lib as X
        e = t["cap_runs_csv"]
        return X.csv_text(e["columns"], e["rows"])
    if table == "cap_runs.tex":
        return (mod.runs_tex(t["cap_runs"], d) + "\n" + mod.margins_tex(t["cap_margins"], d) + "\n"
                + mod.binds_tex(t["cap_binds"], d))
    if table == "cap_modes.tex":
        return mod.modes_tex(t["cap_modes"], d)
    if table == "cap_sens.tex":
        return mod.sens_tex(t["cap_sens"], d)
    return mod.checks_tex(t["cap_checks"], d)


def drawn_keys(fig) -> set:
    return {getattr(a, "_sublet_policy") for ax in fig.axes for a in ax.get_children() if hasattr(a, "_sublet_policy")}


def fig_texts(fig) -> list[str]:
    out = [t.get_text() for t in fig.texts]
    for leg in fig.legends:
        out += [t.get_text() for t in leg.get_texts()]
    for ax in fig.axes:
        out += [t.get_text() for t in ax.texts] + [ax.get_xlabel(), ax.get_ylabel()]
        out += [t.get_text() for t in ax.get_yticklabels() + ax.get_xticklabels()]
    return [s for s in out if s]


# ---------------------------------------------------------------------------------------------------------------
# registration
def test_keys_as_built():
    assert style.MS8_SUPP_KEYS[:len(WANT)] == tuple(WANT)
    order = list(style.POLICIES)
    i = order.index(style.MS7_SUPP_KEYS[-1])
    assert tuple(order[i + 1:i + 1 + len(WANT)]) == tuple(WANT)
    for k, (lab, color, marker, fill, group, family, tag) in WANT.items():
        p = style.POLICIES[k]
        assert (p.label, p.color, p.marker, p.fill, p.group, p.family, p.edgecolor, p.linestyle) == \
            (lab, color, marker, fill, group, family, None, "-"), k
        assert (p.linewidth, p.markersize, p.zorder) == (style.LINE_PT, style.MARKER_PT, style.Z_DATA), k
        assert p.note.startswith("MS8 unit F6") and f"tag {tag} of e7b" in p.note, k
        others = [q for q in style.POLICIES.values() if q.key != k]
        assert p.triple not in {q.triple for q in others}, k
        assert p.label not in {q.label for q in others}, k
        for q in PINNED:
            assert (p.color.upper(), p.marker) != (style.POLICIES[q].color.upper(), style.POLICIES[q].marker), (k, q)
        assert not DESIGN.search(lab), (k, lab)
        assert style.MS8_KEY_OF_TAG[tag] == k
    from sublet.experiments import e7b_tags as bt
    assert set(bt.CAP_TAGS) <= set(style.MS8_KEY_OF_TAG)


def test_registered():
    mod = module()
    spec = style.FIGURES[NAME]
    assert (spec.width, spec.height_in, spec.main) == ("W2", 2.5, False)
    assert tuple(mod.KEYS) == style.SUPP_POLICIES_MS8[NAME] == ("sublet_v2",) + tuple(WANT)
    assert tuple(mod.TABLES) == TABLES and tuple(mod.RUN_INPUTS) == RUN_INPUTS and mod.NAME == NAME
    style.check_policies(mod.KEYS)
    style.check_legacy({NAME: mod.KEYS})
    style.check_legacy()
    assert tuple(mod.KEYS) == tuple(style.legend_order(mod.KEYS))
    mf = [(style.POLICIES[k].marker, style.POLICIES[k].fill) for k in mod.KEYS]
    assert len(mf) == len(set(mf))
    assert style.figure_sets()[NAME] == mod.KEYS
    assert rb.MS8_SUPP_SCRIPTS[NAME] == "code/sim/figs/supp/sf_cap.py"
    assert rb.MS8_SUPP_RUN_INPUTS[NAME] == RUN_INPUTS


@pytest.fixture
def registry_without_test_figures(monkeypatch):
    for k in [k for k in style.FIGURES if k.startswith("test_")]:
        monkeypatch.delitem(style.FIGURES, k)


def test_rebuild_entry_and_pending(registry_without_test_figures, tmp_path):
    ents = {e.name: e for e in rb.entries()}
    e = ents[NAME]
    assert (e.kind, e.script, e.module) == ("supp", "code/sim/figs/supp/sf_cap.py", MODULE)
    assert e.outputs == (f"paper/supplement/figures/{NAME}.pdf", f"code/sim/out/figs/{NAME}.json",
                         f"code/sim/out/figs/{NAME}.png") + tuple(f"paper/supplement/tables/{t}" for t in TABLES)
    assert e.run_inputs == RUN_INPUTS and rb.pending_inputs(e) == RUN_INPUTS
    assert rb.is_pending(tmp_path, e)
    p = tmp_path / RUN_INPUTS[0]
    p.parent.mkdir(parents=True)
    p.write_text("{}")
    assert not rb.is_pending(tmp_path, e)
    outs = [o for x in ents.values() for o in x.outputs]
    assert len(outs) == len(set(outs))
    # the repository holds no run output yet: the entry is pending there until the runs are copied in
    if not (REPO / RUN_INPUTS[0]).is_file():
        assert rb.is_pending(REPO, e)


def test_reduced_extract_is_a_list_error(registry_without_test_figures, tmp_path):
    ents = [e for e in rb.entries() if e.name == NAME]
    p = tmp_path / ents[0].extract
    p.parent.mkdir(parents=True)
    p.write_text(json.dumps({"meta": {"reduced": True}}))       # the shape rebuild.reduced_extracts reads
    errs = rb.reduced_extracts(tmp_path, ents)
    assert len(errs) == 1 and "reduced" in errs[0]
    assert payload()["data"]["meta"]["reduced"] is True        # the fixture extract records it (under "data")
    # the layout style.save writes (meta under "data"; review of unit F6, finding 11): caught as well
    p.write_text(json.dumps(payload()))
    assert len(rb.reduced_extracts(tmp_path, ents)) == 1
    full = payload()
    full["data"]["meta"]["reduced"] = False
    p.write_text(json.dumps(full))
    assert rb.reduced_extracts(tmp_path, ents) == []
    full["data"]["meta"]["reduced"] = {"week": False, "sens": True}
    p.write_text(json.dumps(full))
    assert len(rb.reduced_extracts(tmp_path, ents)) == 1
    full["data"]["meta"]["reduced"] = {"week": False, "sens": False}
    p.write_text(json.dumps(full))
    assert rb.reduced_extracts(tmp_path, ents) == []


# ---------------------------------------------------------------------------------------------------------------
# the script on the fixtures
def test_from_extract_saves_and_is_byte_stable(figs_env):
    mod = module()
    rep = mod.main(["--from-extract", str(FIX / f"{NAME}.json")])
    spec = style.figure_spec(NAME)
    assert Path(rep["pdf"]) == figs_env / "pdf" / f"{NAME}.pdf"
    assert abs(rep["width_bp"] - spec.width_in * 72) <= 0.5 and abs(rep["height_bp"] - spec.height_in * 72) <= 0.5
    assert rep["pages"] == 1 and rep["outside_page"] == []
    assert rep["text_pt"] and set(rep["text_pt"]) <= {style.TICK_PT, style.LABEL_PT}
    assert rep["min_glyph_pt"] >= style.SCRIPT_MIN_PT - 1e-6
    assert not any("dejavu" in f.lower() for f in rep["fonts"])
    assert json.loads((figs_env / "out" / f"{NAME}.json").read_text()) == payload()
    tables = figs_env / "tables"
    assert sorted(p.name for p in tables.iterdir()) == sorted(TABLES)
    first = {p.name: p.read_bytes() for p in tables.iterdir()}
    pdf = Path(rep["pdf"]).read_bytes()
    for t in TABLES:
        text = (tables / t).read_text()
        if t.endswith(".tex"):
            assert text.startswith(f"% Written by code/sim/figs/supp/{NAME}.py from ")
            assert text.split("\n", 1)[1] == tex_of(t)
        else:
            assert text == tex_of(t)
    rep2 = mod.main(["--from-extract", str(figs_env / "out" / f"{NAME}.json")])
    assert Path(rep2["pdf"]).read_bytes() == pdf
    assert {p.name: p.read_bytes() for p in tables.iterdir()} == first


def test_build_on_the_input_tree_matches_the_fixture(figs_env, monkeypatch):
    mod = module()
    opened = []
    real_open, real_io_open = builtins.open, io.open

    def spy(file, *a, **k):
        if isinstance(file, (str, os.PathLike)):
            opened.append(Path(os.path.abspath(os.fspath(file))))
        return real_open(file, *a, **k)

    def spy_io(file, *a, **k):
        if isinstance(file, (str, os.PathLike)):
            opened.append(Path(os.path.abspath(os.fspath(file))))
        return real_io_open(file, *a, **k)

    monkeypatch.setattr(builtins, "open", spy)
    monkeypatch.setattr(io, "open", spy_io)
    d = mod.build(Inputs())
    monkeypatch.undo()
    for p in opened:
        if IN_ROOT in p.parents:
            assert p.relative_to(IN_ROOT).as_posix() in RUN_INPUTS, p
        else:
            assert "/out/" not in p.as_posix(), p
    from figs.common import json_number
    d = json.loads(json.dumps(d, allow_nan=False, default=json_number))
    assert d == data(), STALE
    assert d["meta"]["reduced"] is True and d["meta"]["sources"] == list(RUN_INPUTS)


# ---------------------------------------------------------------------------------------------------------------
# reported in full (oracles on the analysis)
def test_data_file_holds_every_run(fresh):
    an = analysis()
    rows = list(csv.DictReader(io.StringIO(tex_of("cap_runs.csv", fresh))))
    assert len(rows) == len(an["runs"]) == fresh["tables"]["cap_runs_csv"]["n_rows"]
    r3 = {(c["part"], c["point"], c["mode"], str(c["week"]), c["tag"]) for c in an["readings"]["R3"]["cells"]}
    for r, x in zip(rows, an["runs"]):
        assert (r["part"], r["point"], r["tag"], r["week"]) == (x["part"], x["point"], x["tag"], str(x["week"]))
        for col, f in (("r0", "r0"), ("fb_usd", "FB"), ("b_usd", "B"), ("final_excess_rel", "final_rel"),
                       ("runtime_excess_rel", "runtime_rel")):
            assert (r[col] == "") == (x[f] is None), (col, x)
            if x[f] is not None:
                assert float(r[col]) == pytest.approx(x[f], rel=1e-8, abs=1e-12), (col, x)
        assert r["above"] == ("" if x["above"] is None else str(x["above"]).lower())
        assert r["r3_cell"] == str((x["part"], x["point"], x["mode"], str(x["week"]), x["tag"]) in r3).lower()
        assert not DESIGN.search(r["policy"]) or r["policy"] == r["tag"], r["policy"]


def test_runs_table_reports_every_tag_of_part_week(fresh):
    an = analysis()
    pt = an["per_tag"]["week"]["default"]
    rows = {r["tag"]: r for r in fresh["tables"]["cap_runs"]["rows"]}
    want = set(pt) | {"Sublet"} | set(an["meta"]["cap_tags"])
    assert want <= set(rows), want - set(rows)
    for t, by_m in pt.items():
        r = rows[t]
        assert r["runs"] == sum(x["runs"] for x in by_m.values())
        assert r["above"] == sum(x["above"] for x in by_m.values())
        if "L-tr" in by_m:
            assert r["r0_tr"]["median"] == by_m["L-tr"]["r0"]["median"]
        w = an["W"]["week"]["default"].get(t) or {}
        assert (r["W0"] or {}).get("median") == (w.get("W0_stats") or {}).get("median")
        assert (r["W0plus"] or {}).get("median") == (w.get("W0plus_stats") or {}).get("median")
    tex = tex_of("cap_runs.tex", fresh)
    for t in rows:
        assert module().name_cell(module().label(t)) in tex, t     # a cap's name breaks only after its comma


def test_margins_table_reports_every_cap_and_reference(fresh):
    an = analysis()
    mg = an["margins"]["week"]["default"]
    rows = fresh["tables"]["cap_margins"]["rows"]
    pairs = {(r["tag"], r["reference"]) for r in rows}
    want = {(c, ref) for c in an["meta"]["cap_tags"] for ref in an["meta"]["references"][c]}
    assert pairs == want
    for r in rows:
        for m in ("r0_tr", "W0", "W0plus"):
            src = mg[r["tag"]][r["reference"]][m]
            for f in ("wins", "ties", "losses", "missing", "median"):
                assert r[m][f] == src[f], (r["tag"], r["reference"], m, f)
    r3 = [c for c in an["readings"]["R3"]["cells"] if c["part"] == "week"]
    for r in rows:
        if r["reference"] == "Sublet":
            assert r["r3_cells"] == sum(1 for c in r3 if c["tag"] == r["tag"])


def test_sens_table_reports_every_point_and_tag(fresh):
    an = analysis()
    pt = an["per_tag"].get("sens") or {}
    blocks = {b["point"]: b for b in fresh["tables"]["cap_sens"]["blocks"]}
    assert set(blocks) == set(an["meta"]["cells"].get("sens") or {})
    for p, by_t in pt.items():
        rows = {r["tag"]: r for r in blocks[p]["rows"]}
        assert set(by_t) <= set(rows), (p, set(by_t) - set(rows))
        for t, by_m in by_t.items():
            assert rows[t]["runs"] == sum(x["runs"] for x in by_m.values())
            assert rows[t]["above"] == sum(x["above"] for x in by_m.values())
    tex = tex_of("cap_sens.tex", fresh)
    for p in blocks:
        assert module()._cap1(module().POINT_TEX[p]) in tex


def test_checks_table_reports_every_check_and_reading(fresh):
    an = analysis()
    t = fresh["tables"]["cap_checks"]
    assert t["checks"] == an["checks"] and t["sublet"] == an["sublet"]
    assert t["identity"]["n_pairs"] == an["identity"]["n_pairs"] and t["identity"]["holds"] == an["identity"]["holds"]
    for k in ("R1", "R2", "R3"):
        assert t[k]["holds" if k != "R3" else "n_cells"] == an["readings"][k]["holds" if k != "R3" else "n_cells"]
    tex = tex_of("cap_checks.tex", fresh)
    for part, c in an["checks"].items():
        assert f"Part {part}" in tex and f"{c['runs']:,}" in tex
    assert "R1" in tex and "R2" in tex and "R3" in tex


def test_figure_numbers_are_the_analysis(fresh):
    an = analysis()
    mod = module()
    pt = an["per_tag"]["week"]["default"]
    for k, s in fresh["a"]["series"].items():
        t = mod.TAG_OF_KEY[k]
        for m, st in s["modes"].items():
            src = ((pt.get(t) or {}).get(m) or {}).get("r0")
            assert (st or {}).get("median") == (src or {}).get("median"), (t, m)
    for k, s in fresh["b"].items():
        t = mod.TAG_OF_KEY[k]
        assert s["values"] == [r["runtime_rel"] for r in an["runs"] if r["tag"] == t]
        assert s["above"] == sum(1 for r in an["runs"] if r["tag"] == t and r["runtime_above"])
    for row in fresh["cd"]["rows"]:
        for k, s in row["series"].items():
            t = mod.TAG_OF_KEY[k]
            src = ((an["per_tag"]["sens"].get(row["point"]) or {}).get(t) or {}).get("L-tr") or {}
            assert (s["r0_tr"] or {}).get("median") == (src.get("r0") or {}).get("median")
    assert set(fresh["cd"]["keys"]) == {"sublet_v2"} | {mod.KEY_OF_TAG[t] for t in an["meta"]["b_caps"]}


def test_figure_keys_labels_and_no_design_names():
    mod = module()
    fig = mod.draw(data())
    assert drawn_keys(fig) == set(mod.KEYS)
    texts = fig_texts(fig)
    labels = {style.POLICIES[k].label for k in mod.KEYS}
    leg = [t.get_text() for t in fig.legends[0].get_texts()]
    assert set(leg) == labels and len(leg) == len(labels)
    for s in texts:
        assert not DESIGN.search(s), s
    for s in (data()["labels"]["caption"],):
        assert not DESIGN.search(s), s


def test_legend_reads_row_by_row_in_legend_order():
    mod = module()
    pairs = mod.legend_pairs(mod.KEYS)
    labels = [lab for _h, lab in pairs]
    ncol = -(-len(labels) // 2)
    rows = [labels[i::2] for i in range(2)]                  # legend_row fills the columns first
    want = [style.POLICIES[k].label for k in style.legend_order(mod.KEYS)]
    assert rows[0] + rows[1] == want and len(rows[0]) == ncol


# ---------------------------------------------------------------------------------------------------------------
# failure modes
def test_missing_input_exits_2(tmp_path, monkeypatch, capsys):
    root = tmp_path / "tree"
    shutil.copytree(IN_ROOT, root)
    (root / RUN_INPUTS[0]).unlink()
    monkeypatch.setenv("SUBLET_FIGS_IN_ROOT", str(root))
    monkeypatch.setenv(style.ENV_PDF_DIR, str(tmp_path / "pdf"))
    monkeypatch.setenv(style.ENV_OUT_DIR, str(tmp_path / "out"))
    monkeypatch.setenv("SUBLET_FIGS_TABLES_DIR", str(tmp_path / "tables"))
    with pytest.raises(SystemExit) as e:
        module().main([])
    assert e.value.code == 2 and RUN_INPUTS[0] in capsys.readouterr().err
    assert not (tmp_path / "pdf").exists() and not (tmp_path / "out").exists() and not (tmp_path / "tables").exists()


def _listing(*dirs):
    return {str(d): sorted(p.name for p in Path(d).iterdir()) if Path(d).is_dir() else None for d in dirs}


def test_reduced_input_is_never_written_into_versioned_folders(monkeypatch, tmp_path):
    supp_fig, supp_tab = REPO / "paper" / "supplement" / "figures", REPO / "paper" / "supplement" / "tables"
    before = _listing(supp_fig, supp_tab, style.DEFAULT_OUT_DIR)
    monkeypatch.setenv("SUBLET_FIGS_IN_ROOT", str(IN_ROOT))
    cases = [(None, tmp_path / "o1", tmp_path / "t1"), (tmp_path / "p2", None, tmp_path / "t2"),
             (tmp_path / "p3", tmp_path / "o3", supp_tab)]
    for pdf, out, tab in cases:
        for env, v in ((style.ENV_PDF_DIR, pdf), (style.ENV_OUT_DIR, out), ("SUBLET_FIGS_TABLES_DIR", tab)):
            if v is None:
                monkeypatch.delenv(env, raising=False)
            else:
                monkeypatch.setenv(env, str(v))
        for argv in ([], ["--from-extract", str(FIX / f"{NAME}.json")]):
            with pytest.raises(SystemExit) as e:
                module().main(argv)
            assert "reduced" in str(e.value.code), (pdf, out, tab, argv)
    assert _listing(supp_fig, supp_tab, style.DEFAULT_OUT_DIR) == before
    assert not any((tmp_path / p).exists() for p in ("p2", "p3", "o1", "o3", "t1", "t2"))


def test_reduced_flag_per_part():
    """The analysis records meta.reduced per part (a dict, truthy even when every part is a full run): the extract's
    meta.reduced is true iff some part is reduced."""
    mod = module()
    assert mod.meta_of({"meta": {"reduced": {"week": False, "sens": False}}})["reduced"] is False
    assert mod.meta_of({"meta": {"reduced": {"week": False, "sens": True}}})["reduced"] is True


# ---------------------------------------------------------------------------------------------------------------
# real scale
@pytest.fixture(scope="module")
def real_scale(tmp_path_factory):
    sys.path.insert(0, str(FIX))
    try:
        import standin
    finally:
        sys.path.remove(str(FIX))
    tmp = tmp_path_factory.mktemp("x6_real")
    root = standin.standin_root(tmp / "tree")
    env = {"SUBLET_FIGS_IN_ROOT": str(root), style.ENV_PDF_DIR: str(tmp / "pdf"), style.ENV_OUT_DIR: str(tmp / "out"),
           "SUBLET_FIGS_TABLES_DIR": str(tmp / "tables")}
    old = {k: os.environ.get(k) for k in env}
    os.environ.update(env)
    try:
        rep = module().main([])
    finally:
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
    return tmp, rep


def test_real_scale_figure(real_scale):
    tmp, rep = real_scale
    assert rep["outside_page"] == [] and set(rep["text_pt"]) <= {style.TICK_PT, style.LABEL_PT}
    d = json.loads((tmp / "out" / f"{NAME}.json").read_text())["data"]
    assert len(d["weeks"]) == 16 and d["meta"]["reduced"] is False
    assert len(d["a"]["modes"]) == 13 and len(d["cd"]["rows"]) == 5
    assert d["b"]["sublet_v2"]["above"] == 0 and any(d["b"][k]["above"] for k in d["keys"][1:])
    fig = module().draw(d)
    r = fig.canvas.get_renderer()
    for ax in fig._sublet_axes:                 # tick labels inside the figure and not over the next panel
        for t in ax.get_xticklabels():
            if t.get_text():
                tb = t.get_window_extent(r)
                assert tb.y0 >= -0.5, t.get_text()


@pytest.mark.skipif(not PDFLATEX.is_file(), reason="pdflatex is not installed")
def test_tables_compile_without_overfull_boxes(real_scale, tmp_path):
    tmp, _ = real_scale
    inputs = []
    for t in TABLES:
        if not t.endswith(".tex"):
            continue
        (tmp_path / f"fix_{t}").write_text(tex_of(t))
        shutil.copy(tmp / "tables" / t, tmp_path / f"real_{t}")
        inputs += [f"\\input{{fix_{t}}}", f"\\input{{real_{t}}}"]
    (tmp_path / "doc.tex").write_text(
        "\\documentclass[lettersize,journal,onecolumn]{IEEEtran}\n\\usepackage{amsmath}\\usepackage{amssymb}"
        "\\usepackage{booktabs}\\usepackage{array}\\usepackage{longtable}\n\\begin{document}\nText.\n"
        + "\n".join(inputs) + "\n\\end{document}\n")
    env = dict(os.environ, TEXINPUTS=f".:{REPO / 'paper'}:")
    res = subprocess.run([str(PDFLATEX), "-interaction=nonstopmode", "-halt-on-error", "doc.tex"], cwd=tmp_path,
                         capture_output=True, text=True, env=env, timeout=300)
    log = (tmp_path / "doc.log").read_text(errors="replace")
    assert res.returncode == 0 and "LaTeX Error" not in log, log[-2000:]
    assert "Overfull" not in log, [ln for ln in log.splitlines() if "Overfull" in ln]


# ---------------------------------------------------------------------------------------------------------------
# the review of unit F6 (findings 1-12): mutated copies of the fixture analysis, written under tmp_path
def mutated_root(tmp_path: Path, mutate) -> Path:
    an = analysis()
    mutate(an)
    root = tmp_path / "mut"
    p = root / RUN_INPUTS[0]
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(an))
    return root


def run_main(root: Path, out: Path, argv=()) -> dict:
    env = {"SUBLET_FIGS_IN_ROOT": str(root), style.ENV_PDF_DIR: str(out / "pdf"), style.ENV_OUT_DIR: str(out / "out"),
           "SUBLET_FIGS_TABLES_DIR": str(out / "tables")}
    old = {k: os.environ.get(k) for k in env}
    os.environ.update(env)
    try:
        return module().main(list(argv))
    finally:
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def test_caption_states_sublet_from_the_reading(tmp_path, fresh):
    """Finding 1: the caption's statement on Sublet follows readings.R1.sublet_violations, whatever its count."""
    an = analysis()
    ns = an["readings"]["R1"]["sublet_runs"]
    assert not an["readings"]["R1"]["sublet_violations"]
    assert f"none of Sublet's {ns:,} runs is above the bound" in fresh["labels"]["caption"]

    def bad(a):
        a["readings"]["R1"]["sublet_violations"] = [["week", "default", "L-eg", "101", "Sublet"]] * 2
        a["readings"]["R1"]["holds"] = False
    d = build_on(mutated_root(tmp_path, bad))
    cap = d["labels"]["caption"]
    assert f"two of Sublet's {ns:,} runs are above the bound" in cap and "none of Sublet" not in cap


def test_sens_weeks_are_named_per_metric(real_scale):
    """Finding 2: the r0 weeks (L-tr) and the W0 weeks (stress runs) of the points are named apart, in the caption and
    in the block heads of cap_sens."""
    tmp, _ = real_scale
    d = json.loads((tmp / "out" / f"{NAME}.json").read_text())["data"]
    assert set(map(tuple, d["sens_weeks_r0_tr"].values())) == {("301", "302", "303", "304")}
    assert set(map(tuple, d["sens_weeks_W0"].values())) == {("301", "302")}
    cap = d["labels"]["caption"]
    assert "trace lender over weeks 301--304 and the median $W_0$ over weeks 301--302" in cap
    tex = (tmp / "tables" / "cap_sens.tex").read_text()
    assert tex.count(r"}, $r_0$: weeks 301--304, $W_0$: weeks 301--302}") == 5
    assert "week 101" in data()["labels"]["caption"]               # one week: singular


def test_checks_report_r1_per_tag_and_r2_per_mode(fresh):
    """Finding 3(a)."""
    an = analysis()
    tex = tex_of("cap_checks.tex", fresh)
    mod = module()
    for t, v in an["readings"]["R1"]["by_tag"].items():
        row = [ln for ln in tex.splitlines() if (r"\quad " + mod.label(t).replace("%", r"\%")) in ln]
        assert len(row) == 1, t
        assert f"{v['above_with_runtime']} of {v['runs_in_scope']} runs in scope" in row[0]
        assert mod._excess(v["final_rel_max"]) in row[0] and mod._excess(v["runtime_rel_max"]) in row[0]
    from figs.supp import ms7_e7r_lib as E
    for m, v in an["readings"]["R2"]["per_mode"].items():
        row = [ln for ln in tex.splitlines() if (r"\quad under " + E.mode_text(m) + " &") in ln]
        assert len(row) == 1 and f"{E.num(v['cap'])} against {E.num(v['sublet'])}" in row[0], m


def test_sens_reports_greedy_caps_against_both_references(fresh):
    """Finding 3(b): at every point each greedy cap's margins against BL1-GP as well as Sublet."""
    an = analysis()
    from figs.supp import ms7_e7r_lib as E
    tex = tex_of("cap_sens.tex", fresh)
    for b in fresh["tables"]["cap_sens"]["blocks"]:
        for r in b["rows"]:
            if r["tag"] not in an["meta"]["cap_tags"]:
                assert r["vs"] is None
                continue
            assert list(r["vs"]) == an["meta"]["references"][r["tag"]], r["tag"]
            for ref, m in r["vs"].items():
                src = an["margins"]["sens"][b["point"]][r["tag"]][ref]
                for k in ("r0_tr", "W0"):
                    for f in ("wins", "ties", "losses", "missing", "median"):
                        assert m[k][f] == src[k][f], (b["point"], r["tag"], ref, k, f)
    assert tex.count(r"\quad against Greedy + guard") == len(fresh["tables"]["cap_sens"]["blocks"]) * 2
    assert E.wtl(an["margins"]["sens"]["fee4"]["GR-cap-B"]["BL1-GP"]["W0"]) in tex


def test_modes_table_reports_every_tag_and_cap_per_lender(fresh):
    """Finding 3(c): tab:cap-modes (every tag under every lender) and tab:cap-mode-margins (every cap and reference)."""
    an = analysis()
    pt = an["per_tag"]["week"]["default"]
    t = fresh["tables"]["cap_modes"]
    modes = [c["mode"] for c in t["columns"]]
    assert set(modes) == {m for x in pt.values() for m in x} and len(modes) == 13
    assert [r["tag"] for r in t["rows"]] == list(module().FIG_TAGS) + list(module().REFERENCE_TAGS)
    for r in t["rows"]:
        for m in modes:
            src = ((pt.get(r["tag"]) or {}).get(m) or {}).get("r0")
            assert (r["r0"][m] or {}).get("median") == (src or {}).get("median"), (r["tag"], m)
    mg = an["margins"]["week"]["default"]
    assert {(r["tag"], r["reference"]) for r in t["margins"]} == {
        (c, ref) for c in an["meta"]["cap_tags"] for ref in an["meta"]["references"][c]}
    for r in t["margins"]:
        for m in modes:
            src = mg[r["tag"]][r["reference"]][f"r0:{m}"]
            assert {f: r["r0"][m][f] for f in ("wins", "ties", "losses", "missing", "median")} == \
                {f: src[f] for f in ("wins", "ties", "losses", "missing", "median")}
    tex = tex_of("cap_modes.tex", fresh)
    assert r"\label{tab:cap-modes}" in tex and r"\label{tab:cap-mode-margins}" in tex
    assert "peak" in tex and r"i.i.d., $p=$" in tex


def test_binds_table_reports_binds_latches_and_kept_shares(fresh):
    """Finding 3(d): per part and point and cap the binds, the latched runs, the kept share per mode class and the
    runs whose inner policy saved nothing."""
    an = analysis()
    blocks = fresh["tables"]["cap_binds"]["blocks"]
    assert [(b["part"], b["point"]) for b in blocks] == [("week", "default")] + [
        ("sens", p) for p in module().point_order(an["meta"]["cells"]["sens"])]
    for b in blocks:
        pt = an["per_tag"][b["part"]][b["point"]]
        inner = an["inner"][b["part"]][b["point"]]
        for r in b["rows"]:
            by_m = pt.get(r["tag"]) or {}
            assert r["latched_runs"] == sum(x.get("latched_runs", 0) for x in by_m.values())
            assert r["runs"] == sum(x["runs"] for x in by_m.values())
            binds = [x["cap"]["bind_slots"] for x in an["runs"] if (x["part"], x["point"], x["tag"]) ==
                     (b["part"], b["point"], r["tag"]) and x.get("cap")]
            assert r["bind_slots"]["n"] == len(binds) and r["bind_slots"]["max"] == max(binds)
            for c in ("trace", "stress", "other", "all"):
                src = ((inner.get(r["tag"]) or {}).get(c) or {}).get("kept_share")
                assert (r["kept_share"][c] or {}).get("median") == (src or {}).get("median"), (r["tag"], c)
            assert r["n_inner_saving_nonpositive"] == \
                ((inner.get(r["tag"]) or {}).get("all") or {}).get("n_inner_saving_nonpositive")
    assert r"\label{tab:cap-binds}" in tex_of("cap_runs.tex", fresh)


def test_runtime_column_marks_a_subset(fresh):
    """Finding 4: the run-time maximum names the runs with a value when they are fewer than the runs."""
    rows = {r["tag"]: r for r in fresh["tables"]["cap_runs"]["rows"]}
    a9 = rows["A9"]
    assert 0 < a9["runtime_n"] < a9["runs"]
    tex = tex_of("cap_runs.tex", fresh)
    assert f"({a9['runtime_n']}/{a9['runs']})" in tex
    for t, r in rows.items():
        if r["runtime_n"] == r["runs"]:
            assert module()._runtime(r).count("(") == 0, t
    assert "read from the earlier studies" in tex and "from the confirmation, the run-time" not in tex


def test_wtl_names_the_winner_and_the_missing_weeks(fresh):
    """Finding 5."""
    for t in ("cap_runs.tex", "cap_modes.tex", "cap_sens.tex"):
        tex = tex_of(t, fresh)
        assert "weeks won by the reference (the reference costs less)" in tex, t
        assert "counted as the reference's losses" in tex, t


def test_panel_a_draws_fewer_series_and_bars_only_for_the_worst_cases(real_scale):
    """Finding 6: (a) leaves out the latched and slot-count caps and draws min-max bars only in W0 and W0+ (at real
    scale: the fixture's one week has no range)."""
    mod = module()
    tmp, _ = real_scale
    fresh = json.loads((tmp / "out" / f"{NAME}.json").read_text())["data"]
    assert fresh["a"]["keys"] == [k for k in mod.KEYS if mod.TAG_OF_KEY[k] not in mod.A_DROP]
    fig = mod.draw(fresh)
    ax = fig._sublet_axes[0]
    assert {getattr(a, "_sublet_policy") for a in ax.get_children() if hasattr(a, "_sublet_policy")} == \
        set(fresh["a"]["keys"])
    xs, cols, _g = mod.column_positions(fresh["a"]["modes"], fresh["modes"]["stress"])
    first_summary = xs[cols.index("W0")] - 0.5
    bars = [c for c in ax.containers]
    assert bars
    for c in bars:
        for seg in c.lines[2][0].get_segments():
            assert min(p[0] for p in seg) >= first_summary, seg


def _marker_clearance_pt(fig, ax, horizontal: bool) -> float:
    r = fig.canvas.get_renderer()
    bb = ax.get_window_extent(r)
    out = []
    for ln in ax.lines:
        if getattr(ln, "_sublet_role", None) != "median":
            continue
        for x, y in ax.transData.transform(ln.get_xydata()):
            out += [x - bb.x0, bb.x1 - x] if horizontal else [y - bb.y0, bb.y1 - y]
    return min(out) * 72.0 / fig.dpi


def test_markers_clear_the_spines_and_c_has_a_tick_below_the_data(real_scale):
    """Finding 7: in (a), (c) and (d) every median marker clears the axis ends by its radius and MARKER_PAD_PT; (c)
    has a tick at or below its smallest value."""
    tmp, _ = real_scale
    mod = module()
    d = json.loads((tmp / "out" / f"{NAME}.json").read_text())["data"]
    fig = mod.draw(d)
    axes = fig._sublet_axes
    need_pt = style.MARKER_PT / 2.0 + mod.MARKER_PAD_PT - 0.3
    assert _marker_clearance_pt(fig, axes[0], False) >= need_pt
    for ax in axes[2:]:
        assert _marker_clearance_pt(fig, ax, True) >= need_pt
    xs = [x for ln in axes[2].lines if getattr(ln, "_sublet_role", None) == "median" for x in ln.get_xdata()]
    assert min(axes[2].get_xticks()) <= min(xs) + 1e-9 and len(axes[2].get_xticks()) >= 3


def test_nice_axis():
    mod = module()
    assert mod.nice_axis(0.6, 2.0) == (0.5, [0.5, 1.0, 1.5, 2.0])
    lo, t = mod.nice_axis(0.95, 2.8)
    assert lo == 0.95 and t[0] >= 0.95 and 2 <= len(t) <= 4


def test_panel_b_glyphs_and_the_common_bound(fresh):
    """Finding 8: a full-size legend glyph over each column of (b), and the caption says the bound is Sublet's for
    every column."""
    mod = module()
    fig = mod.draw(fresh)
    ax = fig._sublet_axes[1]
    g = [a for a in ax.lines if getattr(a, "_sublet_role", None) == "column_glyph"]
    assert [a._sublet_policy for a in g] == list(mod.KEYS)
    assert all(a.get_markersize() == style.policy(a._sublet_policy).markersize for a in g)
    sh = [a for a in ax.patches if getattr(a, "_sublet_role", None) == "above_region"]
    assert len(sh) == 1
    assert "the same for every column whatever the cap's own limit $X$" in fresh["labels"]["caption"]


def test_no_sens_runs_draws(tmp_path):
    """Finding 9: an analysis without any run of part sens draws and saves (finalize passing)."""
    def no_sens(a):
        for k in ("per_tag", "W", "margins", "inner"):
            (a.get(k) or {}).pop("sens", None)
        a["meta"]["cells"]["sens"] = {}
        a["runs"] = [r for r in a["runs"] if r["part"] != "sens"]
    rep = run_main(mutated_root(tmp_path, no_sens), tmp_path / "o")
    assert rep["outside_page"] == []
    d = json.loads((tmp_path / "o" / "out" / f"{NAME}.json").read_text())["data"]
    assert d["cd"]["rows"] == [] and "No run at the sensitivity points" in d["labels"]["caption"]


def test_cap_without_runs_counts_every_week_missing(tmp_path):
    """Finding 10: a cap with no run at all keeps its margin rows, every week missing."""
    def drop(a):
        for k in ("per_tag", "W", "margins", "inner"):
            for part in (a.get(k) or {}).values():
                for pt in part.values():
                    pt.pop("GR-cap-0", None)
        a["runs"] = [r for r in a["runs"] if r["tag"] != "GR-cap-0"]
    root = mutated_root(tmp_path, drop)
    d = build_on(root)
    n_w = len(d["weeks"])
    rows = [r for r in d["tables"]["cap_margins"]["rows"] if r["tag"] == "GR-cap-0"]
    assert len(rows) == 2 and all(r["no_runs"] for r in rows)
    for r in rows:
        assert all((r[m]["missing"], r[m]["wins"], r[m]["median"]) == (n_w, 0, None) for m in ("r0_tr", "W0"))
    tex = tex_of("cap_runs.tex", d)
    assert f"0/0/0+{n_w}" in tex
    for b in d["tables"]["cap_sens"]["blocks"]:
        assert "GR-cap-0" in [r["tag"] for r in b["rows"]]
    run_main(root, tmp_path / "o")


# ---------------------------------------------------------------------------------------------------------------
# finding 12: the stand-in with the repository's real frozen summaries (the earlier studies' runs of Sublet, A9, BL1
# and BL1-GP) and made-up runs of the caps
FROZEN = REPO / "code" / "sim" / "out"
FROZEN_FILES = ("sublet_v2/main/summary.json", "e7r/eval/summary.json", "s1v2/sweep/summary.json",
                "s1v2/w0/summary.json")


@pytest.mark.skipif(not all((FROZEN / f).is_file() for f in FROZEN_FILES), reason="frozen summaries not present")
def test_real_frozen_standin(tmp_path):
    sys.path.insert(0, str(FIX))
    try:
        import standin
    finally:
        sys.path.remove(str(FIX))
    root = standin.standin_root(tmp_path / "tree", frozen=FROZEN)
    an = json.loads((root / RUN_INPUTS[0]).read_text())
    assert an["identity"]["holds"] is True
    sub = [r for r in an["runs"] if r["tag"] == "Sublet"]
    assert all(r["source"] in ("main", "eval", "sweep", "w0", "e7b") for r in sub)
    assert any(r["runtime_label"] == "envelope" for r in sub)
    rep = run_main(root, tmp_path / "o")
    assert rep["outside_page"] == [] and set(rep["text_pt"]) <= {style.TICK_PT, style.LABEL_PT}
    d = json.loads((tmp_path / "o" / "out" / f"{NAME}.json").read_text())["data"]
    b = d["b"]["sublet_v2"]
    assert b["above"] == 0 and b["runs"] == len(sub)
    assert max(v for v in b["values"] if v is not None) <= 0.0 + 1e-9      # envelopes at or below the bound
    for t in TABLES:
        assert (tmp_path / "o" / "tables" / t).is_file()
