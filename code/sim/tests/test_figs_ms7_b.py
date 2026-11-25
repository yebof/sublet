"""Tests of the supplementary items of the MS7 baseline and stress study (design/ms7/w_spec.md §4, unit W-G4 B; change
C58): figs/supp/sf_bl_ms7.py (X4, stronger baselines: figure, tables e7r_tags, e7r_margins and e7r_grid, data file
baseline_study_runs.csv), figs/supp/sf_stress_ms7.py (X5, stress regimes: figure, tables e7r_modes and e7r_stress) and
their helper figs/supp/ms7_e7r_lib.py.

Quick. The inputs are the input tree tests/fixtures_figs_ms7/g4b/inputs/ (reduced-mode outputs of the baseline study
and its registered analysis, one development week; README there, not results) and the fixture extracts
tests/fixtures_figs_ms7/g4b/<name>.json (what each script writes on that tree; refresh_extracts.py there). Every file is
written under pytest's tmp_path. The oracles recompute the printed numbers from the input files independently of the
scripts.

- Registration (C58 block B): sizes, sets, check_policies and check_legacy, the rebuild entries (outputs with TABLES,
  run inputs RUN_INPUTS, pending in a tree without the run outputs).
- --from-extract on the fixture extract saves at the registered size with finalize() passing (C62's text sizes, no
  overlap, no ink outside the page), writes the extract it read and every table, and a second redraw is byte for byte
  the same (PDF, tables, data file).
- build() on the input tree gives the fixture extract's data and reads only the run outputs it names.
- Reported in full: every tag, lender mode and cell of the analysis (and every configuration of the selection, every run
  of the parts) appears in the tables or the data file, with the analysis's numbers. These oracles check a fresh build()
  on the input tree (fixture `fresh`), not only the fixture extract, so that a wrong build fails them even after the
  fixtures were refreshed from it (review of W-G4 B).
- Review of W-G4 B: MPC and the oracle forecast share a row only where the oracle is rule T's setting with another
  forecast; the margins caption names the policies that no comparison set holds; a policy not run under every i.i.d.
  lender has no crossing counts; the T and W holds follow the confirm block; Sublet's label in every panel of the
  stress figure is clear of the other series.
- The figures draw the registered keys, name policies by registry labels and print no design name.
- A missing run output exits 2 and names the file; reduced input is never written into paper/ or code/sim/out/figs/.
- At real scale (a stand-in tree of 16 weeks made in tmp_path by fixtures_figs_ms7/g4b/standin.py; its numbers exist
  only in the test) both figures save with finalize() passing and their tables compile in the supplement's class
  without an overfull box (pdflatex, if installed).
"""
from __future__ import annotations

import builtins
import csv
import hashlib
import importlib
import importlib.util
import io
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from figs import rebuild as rb
from figs import style
from figs.inputs import Inputs

FIX = Path(__file__).resolve().parent / "fixtures_figs_ms7" / "g4b"
IN_ROOT = FIX / "inputs"
E7R = IN_ROOT / "code" / "sim" / "out" / "e7r"
REPO = style.REPO
SCRIPTS = {"sf_bl_ms7": "figs.supp.sf_bl_ms7", "sf_stress_ms7": "figs.supp.sf_stress_ms7"}
NAMES = sorted(SCRIPTS)
TABLES = {"sf_bl_ms7": ("e7r_tags.tex", "e7r_margins.tex", "e7r_grid.tex", "baseline_study_runs.csv"),
          "sf_stress_ms7": ("e7r_modes.tex", "e7r_stress.tex")}
RUN_INPUTS = {"sf_bl_ms7": ("code/sim/out/e7r/analysis.json", "code/sim/out/e7r/tune/selection.json",
                            "code/sim/out/e7r/tune/summary.json", "code/sim/out/e7r/confirm/summary.json"),
              "sf_stress_ms7": ("code/sim/out/e7r/analysis.json",)}
SIZES = {"sf_bl_ms7": ("W2", 2.5), "sf_stress_ms7": ("W2", 2.5)}
STALE = ("tests/fixtures_figs_ms7/g4b/{}.json is stale (the script's data changed): refresh it with "
         "`python tests/fixtures_figs_ms7/g4b/refresh_extracts.py --only {}` from code/sim")
PDFLATEX = Path.home() / ".local/bin/pdflatex"
# design names that no printed text may carry (tags, experiment IDs, hypothesis and milestone names)
DESIGN = re.compile(r"\b(BL\d|A\d\b|A9|X\d\b|H\d\b|H2b|MS\d|e7r\b|e7c\b|e7o\b|T0\b)|-c2\b|-g\d\d\b|\b(?:BL\d|MPC)-[TW]\b")

pytestmark = pytest.mark.filterwarnings("ignore::figs.style.GlyphSizeWarning")


def module(name):
    return importlib.import_module(SCRIPTS[name])


def payload(name):
    return json.loads((FIX / f"{name}.json").read_text())


def data(name):
    return payload(name)["data"]


def jl(p):
    return json.loads(Path(p).read_text())


def analysis():
    return jl(E7R / "analysis.json")


def build_on(root: Path, name: str) -> dict:
    """`name`'s build() on the input tree `root`, as the extract stores it (review of W-G4 B: the oracles below check a
    fresh build, not the fixture extract alone, so that a wrong build fails them even after a refresh of the
    fixtures)."""
    from figs.common import json_number
    old = os.environ.get("SUBLET_FIGS_IN_ROOT")
    os.environ["SUBLET_FIGS_IN_ROOT"] = str(root)
    try:
        d = module(name).build(Inputs())
    finally:
        if old is None:
            os.environ.pop("SUBLET_FIGS_IN_ROOT", None)
        else:
            os.environ["SUBLET_FIGS_IN_ROOT"] = old
    return json.loads(json.dumps(d, allow_nan=False, default=json_number))


@pytest.fixture(scope="module")
def fresh():
    """{name: data}: each script's build() on the fixture input tree."""
    return {n: build_on(IN_ROOT, n) for n in NAMES}


@pytest.fixture
def figs_env(tmp_path, monkeypatch):
    monkeypatch.setenv("SUBLET_FIGS_IN_ROOT", str(IN_ROOT))
    monkeypatch.setenv(style.ENV_PDF_DIR, str(tmp_path / "pdf"))
    monkeypatch.setenv(style.ENV_OUT_DIR, str(tmp_path / "out"))
    monkeypatch.setenv("SUBLET_FIGS_TABLES_DIR", str(tmp_path / "tables"))
    return tmp_path


def tex_of(name: str, table: str, d=None) -> str:
    """The text of a table file that `name`'s after hook writes from the data `d` (default: its fixture extract)."""
    mod = module(name)
    d = data(name) if d is None else d
    t = d["tables"]
    if table == "baseline_study_runs.csv":
        return mod.runs_csv(t["baseline_study_runs"])
    stem = table[:-4]
    fn = {"e7r_tags": mod.__dict__.get("tags_tex"), "e7r_margins": mod.__dict__.get("margins_tex"),
          "e7r_grid": mod.__dict__.get("grid_tex"), "e7r_modes": mod.__dict__.get("modes_tex"),
          "e7r_stress": mod.__dict__.get("stress_tex")}[stem]
    return fn(t[stem], d)


def drawn_keys(fig) -> set:
    return {getattr(a, "_sublet_policy") for ax in fig.axes for a in ax.get_children() if hasattr(a, "_sublet_policy")}


def fig_texts(fig) -> list[str]:
    out = [t.get_text() for t in fig.texts]
    for ax in fig.axes:
        out += [t.get_text() for t in ax.texts] + [ax.get_xlabel(), ax.get_ylabel()]
        out += [t.get_text() for t in ax.get_yticklabels() + ax.get_xticklabels()]
        leg = ax.get_legend()
        if leg is not None:
            out += [t.get_text() for t in leg.get_texts()]
    return [s for s in out if s]


# ---------------------------------------------------------------------------------------------------------------
# registration (C58, block B) and the rebuild entries
def test_registered():
    for name in NAMES:
        mod = module(name)
        spec = style.FIGURES[name]
        assert (spec.width, spec.height_in, spec.main) == (*SIZES[name], False)
        assert tuple(mod.KEYS) == style.SUPP_POLICIES_MS7[name] and mod.NAME == name
        assert tuple(mod.TABLES) == TABLES[name] and tuple(mod.RUN_INPUTS) == RUN_INPUTS[name]
        style.check_policies(mod.KEYS)
        style.check_legacy({name: mod.KEYS})
        assert tuple(mod.KEYS) == tuple(style.legend_order(mod.KEYS))
    # every new key of X4 is drawn by sf_bl_ms7 (tests/test_ms7_supp_registry.py: drawn by a set or a tuned setting)
    want = {"bl5_cur_c2", "bl1_c2", "bl2_c2", "bl3_0_c2", "bl4_c2", "bl3_1", "bl3_2", "bl3_1_llm", "bl3_2_llm",
            "mpc_oracle", "a9p", "mpc"}
    assert want <= set(style.SUPP_POLICIES_MS7["sf_bl_ms7"])


@pytest.fixture
def registry_without_test_figures(monkeypatch):
    for k in [k for k in style.FIGURES if k.startswith("test_")]:
        monkeypatch.delitem(style.FIGURES, k)


def test_rebuild_entries_and_pending(registry_without_test_figures, tmp_path):
    ents = {e.name: e for e in rb.entries()}
    for name in NAMES:
        e = ents[name]
        assert (e.kind, e.script, e.module) == ("supp", f"code/sim/figs/supp/{name}.py", f"figs.supp.{name}")
        assert e.outputs == (f"paper/supplement/figures/{name}.pdf", f"code/sim/out/figs/{name}.json",
                             f"code/sim/out/figs/{name}.png") + tuple(f"paper/supplement/tables/{t}"
                                                                      for t in TABLES[name])
        assert e.run_inputs == RUN_INPUTS[name] and rb.pending_inputs(e) == RUN_INPUTS[name]
        root = tmp_path / name
        root.mkdir()
        assert rb.is_pending(root, e)
        for rel in RUN_INPUTS[name]:
            (root / rel).parent.mkdir(parents=True, exist_ok=True)
            (root / rel).write_text("{}")
        assert not rb.is_pending(root, e)
    # the tables of the two scripts are distinct files
    outs = [o for n in NAMES for o in ents[n].outputs]
    assert len(outs) == len(set(outs))


# ---------------------------------------------------------------------------------------------------------------
# the scripts on the fixtures
@pytest.mark.parametrize("name", NAMES)
def test_from_extract_saves_and_is_byte_stable(figs_env, name):
    mod = module(name)
    rep = mod.main(["--from-extract", str(FIX / f"{name}.json")])
    spec = style.figure_spec(name)
    assert Path(rep["pdf"]) == figs_env / "pdf" / f"{name}.pdf"
    assert abs(rep["width_bp"] - spec.width_in * 72) <= 0.5 and abs(rep["height_bp"] - spec.height_in * 72) <= 0.5
    assert rep["pages"] == 1 and rep["outside_page"] == []
    assert rep["text_pt"] and set(rep["text_pt"]) <= {style.TICK_PT, style.LABEL_PT}
    assert rep["min_glyph_pt"] >= style.SCRIPT_MIN_PT - 1e-6
    assert not any("dejavu" in f.lower() for f in rep["fonts"])
    assert jl(figs_env / "out" / f"{name}.json") == payload(name)
    tables = figs_env / "tables"
    assert sorted(p.name for p in tables.iterdir()) == sorted(TABLES[name])
    first = {p.name: p.read_bytes() for p in tables.iterdir()}
    pdf = Path(rep["pdf"]).read_bytes()
    for t in TABLES[name]:
        text = (tables / t).read_text()
        if t.endswith(".tex"):
            assert text.startswith(f"% Written by code/sim/figs/supp/{name}.py from ")
            assert text.split("\n", 1)[1] == tex_of(name, t)
        else:
            assert text == tex_of(name, t)
    rep2 = mod.main(["--from-extract", str(figs_env / "out" / f"{name}.json")])
    assert Path(rep2["pdf"]).read_bytes() == pdf
    assert {p.name: p.read_bytes() for p in tables.iterdir()} == first


@pytest.mark.parametrize("name", NAMES)
def test_build_on_the_input_tree_matches_the_fixture(figs_env, monkeypatch, name):
    """build() reads only its run outputs (patched open: no other repository file, no run file) and gives the fixture
    extract's data."""
    mod = module(name)
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
    inp = Inputs()
    d = mod.build(inp)
    monkeypatch.undo()
    for p in opened:
        if IN_ROOT in p.parents:
            assert p.relative_to(IN_ROOT).as_posix() in RUN_INPUTS[name], p
        else:
            assert "/out/" not in p.as_posix() or "/runs/" not in p.as_posix(), p
    from figs.common import json_number
    d = json.loads(json.dumps(d, allow_nan=False, default=json_number))
    assert d == data(name), STALE.format(name, name)
    assert inp.sources == list(RUN_INPUTS[name]) == payload(name)["sources"] == d["meta"]["sources"]
    assert d["meta"]["reduced"] is True


# ---------------------------------------------------------------------------------------------------------------
# reported in full, with the analysis's numbers
def test_bl_tables_report_every_tag_set_and_configuration(fresh):
    a = analysis()
    sel = jl(E7R / "tune" / "selection.json")
    d = fresh["sf_bl_ms7"]
    t = d["tables"]
    # e7r_tags: every tag, with the analysis's statistics
    rows = {r["tag"]: r for r in t["e7r_tags"]["rows"]}
    assert set(rows) == set(a["tags"]) and len(rows) == len(t["e7r_tags"]["rows"])
    for tag, x in a["tags"].items():
        for k, src in (("r0_tr", x["r0_tr"]), ("W0", x["W0"]), ("W0plus", x["W0plus"]),
                       ("RC_tr", (x.get("RC") or {}).get("L-tr"))):
            for f in ("median", "min", "max"):
                assert (rows[tag][k] or {}).get(f) == (src or {}).get(f), (tag, k, f)
    # e7r_margins: every tag but Sublet, every comparison set, with the analysis's margins
    mrows = {r["tag"]: r for r in t["e7r_margins"]["rows"]}
    assert set(mrows) == set(a["tags"]) - {"Sublet"} == set(a["margins"])
    for tag, mg in a["margins"].items():
        for m in ("r0_tr", "W0", "W0plus"):
            for f in ("wins", "ties", "losses", "missing", "median", "min", "max"):
                assert mrows[tag][m][f] == mg[m][f], (tag, m, f)
    sets = {s["set"]: s for s in t["e7r_margins"]["sets"]}
    assert set(sets) == set(a["best_of"])
    for name, b in a["best_of"].items():
        assert sets[name]["members"] == b["members"]
        for m in ("r0_tr", "W0", "W0plus"):
            assert sets[name][m]["median"] == b["margins"][m]["median"]
    # e7r_grid: every configuration with the selection's medians and choices, the confirmation's medians
    g = {r["config"]: r for r in t["e7r_grid"]["rows"]}
    allc = {c: (fam, x) for fam, f in sel["families"].items() for c, x in f["configs"].items()}
    assert set(g) == set(allc)
    for c, (fam, x) in allc.items():
        f = sel["families"][fam]
        assert (g[c]["median_r0_tr"], g[c]["median_W0"], g[c]["eligible"]) == \
            (x["median_r0_tr"], x["median_W0"], x["eligible"])
        assert (g[c]["T"], g[c]["W"], g[c]["as_built"]) == (c == f["T"], c == f["W"], c == f["default"])
        cf = a["confirm"]["families"][fam]
        if c == f["default"]:
            assert g[c]["conf_r0_tr"] == cf["median_r0_tr"][cf["as_built"]]
        if c == f["T"]:
            assert g[c]["conf_W0"] == cf["median_W0"][f"{fam}-T"] and g[c]["holds"]["T"] == cf["T_holds"]
        if c == f["W"]:
            assert g[c]["holds"]["W"] == cf["W_holds"]


def test_bl_runs_file_holds_every_run(fresh):
    a = analysis()
    sel = jl(E7R / "tune" / "selection.json")
    tune = jl(E7R / "tune" / "summary.json")
    conf = jl(E7R / "confirm" / "summary.json")
    d = fresh["sf_bl_ms7"]
    block = d["tables"]["baseline_study_runs"]
    text = module("sf_bl_ms7").runs_csv(block)
    assert hashlib.sha256(text.encode()).hexdigest() == block["sha256"]
    rows = list(csv.DictReader(io.StringIO(text)))
    assert len(rows) == block["n_rows"] and list(rows[0]) == block["columns"]
    got = {(r["part"], r["tag"], r["lender"], r["week"]): float(r["r0"]) for r in rows}
    assert len(got) == len(rows)
    from figs.supp import ms7_e7r_lib as E
    want = {}
    for tag, x in a["tags"].items():
        if tag in sel["aliases"]:
            continue
        for w, pw in x["per_week"].items():
            for m, v in pw["r0"].items():
                if v is not None:
                    want[("eval", tag, E.mode_plain(m), w)] = v
    for part, s in (("tune", tune), ("confirm", conf)):
        for tag, by_m in s["table"].items():
            for m, by_w in by_m.items():
                for w, by_s in by_w.items():
                    if by_s.get("0") is not None:
                        want[(part, tag, m, w)] = by_s["0"]
    assert set(got) == set(want)
    assert all(abs(got[k] - want[k]) <= 5e-7 for k in want)
    # RC of an eval run: r0 minus r0 under L-hon of the same policy and week
    for r in rows:
        if r["part"] == "eval" and r["lender"] != "L-hon" and r["rc"]:
            h = got[("eval", r["tag"], "L-hon", r["week"])]
            assert abs(float(r["rc"]) - (float(r["r0"]) - h)) <= 2e-6
    # every policy name is a registry label (plain) or a tuning configuration of a family
    labels = {style.POLICIES[k].label.replace("$", "") for k in style.POLICIES}
    for r in rows:
        assert r["policy"] in labels or (r["part"] == "tune" and ", setting " in r["policy"]), r["policy"]


def test_bl_figure_rows_are_the_analysis_margins(fresh):
    a = analysis()
    d = fresh["sf_bl_ms7"]
    seen = set()
    for r in d["rows"]:
        for m in r["members"]:
            seen.add(m["tag"])
            for k in ("r0_tr", "W0", "W0plus"):
                assert m[k]["median"] == a["margins"][m["tag"]][k]["median"], (m["tag"], k)
                assert (m[k]["min"], m[k]["max"]) == (a["margins"][m["tag"]][k]["min"], a["margins"][m["tag"]][k]["max"])
    pairs = {(p["as_built"], p["c2"]) for p in a["as_built_vs_c2"]}
    assert pairs <= {tuple(m["tag"] for m in r["members"]) for r in d["rows"]}
    assert {"BL3-1", "BL3-2", "BL3-1-llm", "BL3-2-llm", "MPC-T", "MPC-oracle", "A9-P"} <= seen
    # each row label is its registry labels: the base's, an arrow (C62 fix round: STIX's, in mathtext), the part of
    # the variant's that differs
    arrow = module("sf_bl_ms7").ARROW
    assert arrow == r" $\!\mathbb{\rightarrow}\!$ "
    for r in d["rows"]:
        labs = [style.POLICIES[m["key"]].label for m in r["members"]]
        if len(labs) == 1:
            assert r["label"] == labs[0]
        else:
            base, rest = r["label"].split(arrow)
            assert base == labs[0] and labs[1].endswith(rest) and labs[1] != labs[0]


def test_stress_tables_report_every_tag_mode_and_week(fresh):
    a = analysis()
    d = fresh["sf_stress_ms7"]
    t = d["tables"]
    rows = {r["tag"]: r for r in t["e7r_modes"]["rows"]}
    assert set(rows) == set(a["tags"])
    have = {m for x in a["tags"].values() for m in x["r0"]}
    assert set(c["mode"] for c in t["e7r_modes"]["columns"]) == have
    assert len(have) == 13 or a["meta"].get("reduced")
    for tag, x in a["tags"].items():
        for m, st in x["r0"].items():
            for f in ("median", "min", "max"):
                assert rows[tag]["r0"][m][f] == st[f], (tag, m, f)
    # crossings: per tag the weeks by first p with r0 > 1, recomputed from the analysis's per-week curves
    srows = {r["tag"]: r for r in t["e7r_stress"]["rows"]}
    assert set(srows) == set(a["tags"])
    w0p = a["meta"]["w0plus_modes"]
    grid_modes = [m for _p, m in a["meta"]["intensity_points"]]
    for tag, x in a["tags"].items():
        it = x.get("intensity")
        c = srows[tag]["crossings"]
        if not it or [m for _p, m in it["points"]] != grid_modes:     # not run under every lender of the grid
            assert c is None, tag
            continue
        n = {}
        for w, pw in it["per_week"].items():
            f = pw["first_p_above_1"]
            k = "none" if f is None else format(float(f), "g")
            n[k] = n.get(k, 0) + 1
        assert {k: v for k, v in c["counts"].items() if v} == n
        # the lender of W0+ per week, independently: the largest r0 over the W0+ modes, ties to the first
        att = {}
        for w, pw in x["per_week"].items():
            vals = [(pw["r0"].get(m), -i, m) for i, m in enumerate(w0p)]
            if any(v is None for v, _, _ in vals):
                continue
            m = max(vals)[2]
            att[m] = att.get(m, 0) + 1
        assert srows[tag]["w0plus_lender"] == att
    assert srows["MPC-oracle"]["crossings"] is None                   # L-tr and L-hon only: no curve, no count
    from figs.supp import ms5b_e7_lib as L
    tex = module("sf_stress_ms7").stress_tex(t["e7r_stress"], d)
    assert L.tex(style.POLICIES["mpc_oracle"].label) + " was not run under the i.i.d.\\ lenders (--)." in tex
    # the figure's series are the analysis's intensity points
    for key, s in d["series"].items():
        it = a["tags"][s["tag"]]["intensity"]
        assert s["p"] == [float(p) for p, _ in it["points"]]
        assert s["median"] == [it["by_p"][m]["median"] for _, m in it["points"]]


@pytest.mark.parametrize("name,table", [(n, t) for n in NAMES for t in TABLES[n] if t.endswith(".tex")])
def test_tables_name_every_policy_and_print_no_design_name(fresh, name, table):
    from figs.supp import ms5b_e7_lib as L
    d = fresh[name]
    tex = tex_of(name, table, d)
    t = d["tables"][table[:-4]]
    assert tex.startswith(L.ONE_COLUMN) and r"\begin{longtable}" in tex and r"\label{tab:" in tex
    assert tex.count(r"{Table~\thetable, continued}") == tex.count(r"\begin{longtable}")
    for tag in t["scope"].get("tags", []):
        assert L.tex(style.POLICIES[module(name).E.KEY_OF_TAG[tag]].label) in tex, (table, tag)
    printed = re.sub(r"\\(label|ref)\{[^}]*\}", "", tex.split("\n", 1)[1])
    printed = printed.replace("baseline_study_runs", "")
    assert not DESIGN.search(printed), DESIGN.search(printed)
    for w in d["weeks"] if table != "e7r_grid.tex" else t["weeks"]:
        assert str(w) in tex


@pytest.mark.parametrize("name", NAMES)
def test_figure_keys_labels_and_no_design_names(name):
    mod = module(name)
    fig = mod.draw(data(name))
    keys = drawn_keys(fig)
    assert keys == set(style.SUPP_POLICIES_MS7[name]), keys
    texts = fig_texts(fig)
    assert not [s for s in texts if DESIGN.search(s)], [s for s in texts if DESIGN.search(s)]
    labels = {style.POLICIES[k].label for k in keys}
    for ax in fig.axes:
        leg = ax.get_legend()
        if leg is not None:
            assert all(x.get_text().replace("\n", " ") in labels for x in leg.get_texts())
    cap = re.sub(r"\\(label|ref)\{[^}]*\}", "", data(name)["labels"]["caption"])
    assert not DESIGN.search(cap.replace("baseline_study_runs", "")), cap


# ---------------------------------------------------------------------------------------------------------------
# the checks
def copy_tree(tmp_path: Path) -> Path:
    root = tmp_path / "tree"
    shutil.copytree(IN_ROOT, root)
    return root


@pytest.mark.parametrize("name,missing", [(n, r) for n in NAMES for r in RUN_INPUTS[n]])
def test_missing_input_exits_2(tmp_path, monkeypatch, capsys, name, missing):
    root = copy_tree(tmp_path)
    (root / missing).unlink()
    monkeypatch.setenv("SUBLET_FIGS_IN_ROOT", str(root))
    monkeypatch.setenv(style.ENV_PDF_DIR, str(tmp_path / "pdf"))
    monkeypatch.setenv(style.ENV_OUT_DIR, str(tmp_path / "out"))
    monkeypatch.setenv("SUBLET_FIGS_TABLES_DIR", str(tmp_path / "tables"))
    with pytest.raises(SystemExit) as e:
        module(name).main([])
    assert e.value.code == 2 and missing in capsys.readouterr().err
    assert not (tmp_path / "pdf").exists() and not (tmp_path / "out").exists() and not (tmp_path / "tables").exists()


def _listing(*dirs):
    return {str(d): sorted(p.name for p in Path(d).iterdir()) if Path(d).is_dir() else None for d in dirs}


@pytest.mark.parametrize("name", NAMES)
def test_reduced_input_is_never_written_into_versioned_folders(monkeypatch, tmp_path, name):
    supp_fig, supp_tab = REPO / "paper" / "supplement" / "figures", REPO / "paper" / "supplement" / "tables"
    before = _listing(supp_fig, supp_tab, style.DEFAULT_OUT_DIR)
    monkeypatch.setenv("SUBLET_FIGS_IN_ROOT", str(IN_ROOT))
    cases = [  # (PDF dir, extract dir, tables dir); None: unset
        (None, tmp_path / "o1", tmp_path / "t1"),
        (tmp_path / "p2", None, tmp_path / "t2"),
        (tmp_path / "p3", tmp_path / "o3", supp_tab),
    ]
    for pdf, out, tab in cases:
        for env, v in ((style.ENV_PDF_DIR, pdf), (style.ENV_OUT_DIR, out), ("SUBLET_FIGS_TABLES_DIR", tab)):
            if v is None:
                monkeypatch.delenv(env, raising=False)
            else:
                monkeypatch.setenv(env, str(v))
        for argv in ([], ["--from-extract", str(FIX / f"{name}.json")]):
            with pytest.raises(SystemExit) as e:
                module(name).main(argv)
            assert "reduced" in str(e.value.code), (pdf, out, tab, argv)
    assert _listing(supp_fig, supp_tab, style.DEFAULT_OUT_DIR) == before
    assert not any((tmp_path / p).exists() for p in ("p2", "p3", "o1", "o3", "t1", "t2"))


def test_absent_tuned_tag_keeps_the_figure(tmp_path, monkeypatch):
    """A family without an eligible tuning configuration has no tuned tags in the analysis (e7r_select.py): the figure
    keeps its other rows, names a row of one rule by that rule's registry label and lists the absent tag."""
    root = copy_tree(tmp_path)
    f = root / "code/sim/out/e7r/analysis.json"
    a = jl(f)
    for t in ("MPC-T", "MPC-W"):
        a["tags"].pop(t, None)
        a["margins"].pop(t, None)
    f.write_text(json.dumps(a))
    monkeypatch.setenv("SUBLET_FIGS_IN_ROOT", str(root))
    monkeypatch.setenv(style.ENV_PDF_DIR, str(tmp_path / "pdf"))
    monkeypatch.setenv(style.ENV_OUT_DIR, str(tmp_path / "out"))
    monkeypatch.setenv("SUBLET_FIGS_TABLES_DIR", str(tmp_path / "tables"))
    rep = module("sf_bl_ms7").main([])
    assert rep["outside_page"] == []
    d = jl(tmp_path / "out" / "sf_bl_ms7.json")["data"]
    assert d["absent"] == ["MPC-T"]
    row = next(r for r in d["rows"] if r["group"] == "mpc")
    assert [m["tag"] for m in row["members"]] == ["MPC-oracle"] and row["label"] == style.POLICIES["mpc_oracle"].label
    assert "Not in the analysis: MPC." in d["labels"]["caption"]


# ---------------------------------------------------------------------------------------------------------------
# review of W-G4 B
def _settings_but_forecast(info):
    p = info.get("params")
    return None if not isinstance(p, dict) else (info.get("policy_id"), {k: v for k, v in p.items() if k != "forecast"})


def test_mpc_and_oracle_share_a_row_only_when_the_oracle_is_rule_t(fresh, tmp_path, monkeypatch):
    """The oracle forecast is MPC's as-built setting with the realized demand (ms7_baselines.MS7_TAGS): it is drawn as
    the variant of rule T's MPC, in one row with an arrow, only where rule T's setting differs from it in the forecast
    alone; otherwise the two are rows of their own and the caption says that the oracle is the as-built setting."""
    a = analysis()
    t, o = a["tags"]["MPC-T"], a["tags"]["MPC-oracle"]
    want = _settings_but_forecast(t) == _settings_but_forecast(o)
    d = fresh["sf_bl_ms7"]
    assert d["mpc_oracle_paired"] is want
    mpc = [r for r in d["rows"] if r["group"] == "mpc"]
    cap = d["labels"]["caption"]
    if not want:                                    # the reduced tree: rule T took the kbar contract
        assert [[m["tag"] for m in r["members"]] for r in mpc] == [["MPC-T"], ["MPC-oracle"]]
        assert [r["label"] for r in mpc] == [style.POLICIES["mpc"].label, style.POLICIES["mpc_oracle"].label]
        assert "in its own row, the oracle forecast at MPC's as-built setting" in cap
        assert "to the same setting with the oracle forecast" not in cap
    # rule T at the as-built setting: the oracle is its variant
    root = copy_tree(tmp_path)
    f = root / "code/sim/out/e7r/analysis.json"
    a2 = jl(f)
    a2["tags"]["MPC-T"]["params"] = {k: v for k, v in o["params"].items() if k != "forecast"}
    f.write_text(json.dumps(a2))
    monkeypatch.setenv("SUBLET_FIGS_IN_ROOT", str(root))
    monkeypatch.setenv(style.ENV_PDF_DIR, str(tmp_path / "pdf"))
    monkeypatch.setenv(style.ENV_OUT_DIR, str(tmp_path / "out"))
    monkeypatch.setenv("SUBLET_FIGS_TABLES_DIR", str(tmp_path / "tables"))
    rep = module("sf_bl_ms7").main([])
    assert rep["outside_page"] == []
    d2 = jl(tmp_path / "out" / "sf_bl_ms7.json")["data"]
    assert d2["mpc_oracle_paired"] is True
    mpc = [r for r in d2["rows"] if r["group"] == "mpc"]
    assert len(mpc) == 1 and [m["tag"] for m in mpc[0]["members"]] == ["MPC-T", "MPC-oracle"]
    assert mpc[0]["label"] == r"MPC $\!\mathbb{\rightarrow}\!$ oracle forecast"
    assert "to the same setting with the oracle forecast" in d2["labels"]["caption"]
    assert "in its own row" not in d2["labels"]["caption"]


def test_margins_caption_names_the_policies_no_comparison_set_holds(fresh):
    """The set of all baselines holds every set's members and protected-only renting: the caption names exactly the
    other tags (aliases read as their targets), recomputed from the analysis's best_of members and the selection."""
    a = analysis()
    sel = jl(E7R / "tune" / "selection.json")
    held = {m for b in a["best_of"].values() for m in b["members"]}
    assert set(a["best_of"]["all_online"]["members"]) == held
    want = [t for t in a["margins"] if sel["aliases"].get(t, t) not in held]
    d = fresh["sf_bl_ms7"]
    t = d["tables"]["e7r_margins"]
    assert sorted(t["left_out"]) == sorted(want) and "MPC-oracle" in want and "Sublet" not in want
    from figs.supp import ms5b_e7_lib as L
    cap = tex_of("sf_bl_ms7", "e7r_margins.tex", d).split(r"\label{tab:e7r-margins}")[0]
    for x in want:
        assert L.tex(style.POLICIES[module("sf_bl_ms7").E.KEY_OF_TAG[x]].label) in cap, x
    assert "every online policy" not in tex_of("sf_bl_ms7", "e7r_margins.tex", d)


def test_grid_holds_follow_the_confirm_block(tmp_path):
    """Whether T and W hold on the confirmation weeks is printed from the analysis's confirm block for the row of each
    rule's configuration, on a tree whose confirm block has T holding and W failing where T and W differ."""
    root = copy_tree(tmp_path)
    f = root / "code/sim/out/e7r/analysis.json"
    a = jl(f)
    sel = jl(E7R / "tune" / "selection.json")
    fams = [k for k, x in sel["families"].items() if x["T"] != x["W"]]
    assert fams
    for k in fams:
        a["confirm"]["families"][k]["T_holds"], a["confirm"]["families"][k]["W_holds"] = True, False
    f.write_text(json.dumps(a))
    d = build_on(root, "sf_bl_ms7")
    g = {r["config"]: r for r in d["tables"]["e7r_grid"]["rows"]}
    for k in fams:
        x = sel["families"][k]
        assert g[x["T"]]["holds"] == {"T": True} and g[x["W"]]["holds"] == {"W": False}
    tex = tex_of("sf_bl_ms7", "e7r_grid.tex", d)
    assert "T yes" in tex and "W no" in tex


def _sublet_label_clear(fig) -> list:
    """Per panel of sf_stress_ms7: Sublet's label and whether its box is clear of every other series, text, legend and
    reference line (common._occupancy without the label, its leader, Sublet's line and its dotted link to p = 0)."""
    from figs.common import GRID_RES_PT, _occupancy
    out = []
    for ax in fig._sublet_axes:
        labs = [t for t in ax.texts if getattr(t, "_sublet_role", "") == "direct_label"]
        assert len(labs) == 1 and labs[0].get_text() == "Sublet"
        t = labs[0]
        own = tuple(ln for ln in ax.lines if getattr(ln, "_sublet_role", "") == "leader"
                    or (getattr(ln, "_sublet_policy", None) == "sublet_v2"
                        and getattr(ln, "_sublet_role", "") in ("line", "zero_link")))
        taken, x0, y0 = _occupancy(ax, skip=(t,) + own)
        to_pt, tol = 72.0 / fig.dpi, 0.25           # tol: rounding of the box to the 0.5-pt grid (KEY_PAD_PT is 1.5)
        bb = t.get_window_extent(fig.canvas.get_renderer())
        i0, i1 = int((bb.x0 * to_pt + tol - x0) // GRID_RES_PT), int(-(-(bb.x1 * to_pt - tol - x0) // GRID_RES_PT))
        j0, j1 = int((bb.y0 * to_pt + tol - y0) // GRID_RES_PT), int(-(-(bb.y1 * to_pt - tol - y0) // GRID_RES_PT))
        inside = 0 <= i0 and i1 <= taken.shape[1] and 0 <= j0 and j1 <= taken.shape[0]
        out.append(inside and not taken[max(j0, 0):j1, max(i0, 0):i1].any())
    return out


def test_stress_sublet_label_clear_of_the_other_series(real_scale):
    """Sublet's direct label in every panel lies on free space (or on its own line), never over another series, a
    legend or the reference line, on the fixture tree and on the real-scale stand-in (review of W-G4 B: a label set at
    the last point overlapped other series' lines in crowded panels)."""
    tmp, _ = real_scale
    mod = module("sf_stress_ms7")
    for d in (data("sf_stress_ms7"), jl(tmp / "out" / "sf_stress_ms7.json")["data"]):
        fig = mod.draw(d)
        assert all(_sublet_label_clear(fig)), _sublet_label_clear(fig)


def _row_name_gaps_pt(fig) -> float:
    """The least vertical gap (pt) between the boxes of neighboring row names of sf_bl_ms7 (negative: they overlap)."""
    ax = fig._sublet_axes[0]
    r = fig.canvas.get_renderer()
    bbs = [t.get_window_extent(r) for t in ax.get_yticklabels() if t.get_text()]
    return min((bbs[i].y0 - bbs[i + 1].y1) * 72.0 / fig.dpi for i in range(len(bbs) - 1))


def test_bl_row_names_do_not_overlap(real_scale, tmp_path):
    """The row names of sf_bl_ms7 stand apart with nine rows (MPC and its oracle in one row) and with ten (apart), on
    the fixture and at real scale (review of W-G4 B: ten rows at GROUP_GAP 0.25 overlapped by 0.19 pt)."""
    tmp, _ = real_scale
    mod = module("sf_bl_ms7")
    ds = [data("sf_bl_ms7"), jl(tmp / "out" / "sf_bl_ms7.json")["data"]]
    root = copy_tree(tmp_path)
    f = root / "code/sim/out/e7r/analysis.json"
    a = jl(f)
    a["tags"]["MPC-T"]["params"] = {k: v for k, v in a["tags"]["MPC-oracle"]["params"].items() if k != "forecast"}
    f.write_text(json.dumps(a))
    ds.append(build_on(root, "sf_bl_ms7"))
    assert sorted(len(d["rows"]) for d in ds) == [9, 10, 10]
    for d in ds:
        assert _row_name_gaps_pt(mod.draw(d)) > 0.0, len(d["rows"])


def test_bl_row_name_arrow_is_stix_and_names_end_together(real_scale):
    """C62 fix round: the arrow of a row name of two rules is STIX's right arrow (Liberation Sans's U+2192, as built,
    was small and low next to 7-pt lower case; mathtext's plain \\rightarrow is that glyph too), and every name with
    math is moved right by the PDF's rounding of its width (common.align_right_math), so that it ends where the plain
    names do; on the fixture and at real scale."""
    import math
    from matplotlib.mathtext import MathTextParser
    tmp, _ = real_scale
    mod = module("sf_bl_ms7")
    parser = MathTextParser("path")
    for d in (data("sf_bl_ms7"), jl(tmp / "out" / "sf_bl_ms7.json")["data"]):
        fig = mod.draw(d)
        names = [t for t in fig._sublet_axes[0].get_yticklabels() if t.get_text()]
        two = [t for t in names if mod.ARROW in t.get_text()]
        assert len(two) == sum(1 for r in d["rows"] if len(r["members"]) == 2) > 0
        for t in two:
            glyphs = parser.parse(t.get_text(), 72, t.get_fontproperties()).glyphs
            fonts = {g[0].family_name for g in glyphs if g[2] == 0x2192}
            assert fonts == {"STIXGeneral"}, (t.get_text(), fonts)
        for t in names:
            s, prop = t.get_text(), t.get_fontproperties()
            if "$" not in s:
                assert not hasattr(t, "_sublet_right_shift_pt")
                continue
            fine = parser.parse(s, 7200, prop).width / 100.0
            want = math.ceil(fine - 1e-9) - fine
            assert abs(getattr(t, "_sublet_right_shift_pt", 0.0) - want) < 0.02, (s, want)


def test_stress_gap_mark_on_the_policy():
    """A week with a missing point before its crossing marks the policy's name, not the 'not reached' count."""
    d = json.loads(json.dumps(data("sf_stress_ms7")))
    r = d["tables"]["e7r_stress"]["rows"][0]
    assert r["crossings"] is not None
    r["crossings"]["weeks_with_gap"] = 1
    tex = module("sf_stress_ms7").stress_tex(d["tables"]["e7r_stress"], d)
    from figs.supp import ms5b_e7_lib as L
    line = next(ln for ln in tex.splitlines() if ln.startswith(L.rag(L.tex(r["label"]))))
    assert line.startswith(L.rag(L.tex(r["label"]) + r"$^{\dagger}$"))
    assert line.count(r"\dagger") == 1
    assert "in a week of the policy" in tex             # the caption defines the dagger that a row carries


def test_stress_caption_without_gap_has_no_dagger():
    """Integration review of X5: the caption defines the dagger only when a row carries it."""
    d = json.loads(json.dumps(data("sf_stress_ms7")))
    for r in d["tables"]["e7r_stress"]["rows"]:
        if r["crossings"] is not None:
            r["crossings"]["weeks_with_gap"] = 0
    tex = module("sf_stress_ms7").stress_tex(d["tables"]["e7r_stress"], d)
    assert r"\dagger" not in tex and "in a week of the policy" not in tex


def test_margins_best_of_counts_distinct_settings():
    """Integration review of X4: a best-of row counts the distinct settings of its set (same registry id and the
    same parameters are one setting), not the tags: the set of all baselines holds 31 tags and 25 settings."""
    mod = module("sf_bl_ms7")
    tags = {"A": {"policy_id": "p", "params": {"k": 1, "c": "x"}},
            "B": {"policy_id": "p", "params": {"c": "x", "k": 1}},
            "C": {"policy_id": "p", "params": {"k": 2}}, "D": {"policy_id": "q", "params": {"k": 1}}, "E": {}}
    assert mod._n_settings(tags, ["A", "B", "C", "D", "E"]) == 4
    d = data("sf_bl_ms7")
    sets = d["tables"]["e7r_margins"]["sets"]
    assert sets and all(1 <= s["n_settings"] <= len(s["members"]) for s in sets)
    tex = mod.margins_tex(d["tables"]["e7r_margins"], d)
    assert "number of distinct settings in parentheses" in tex and "members run" not in tex
    for s in sets:
        assert f"Best of {mod.SET_TEXT[s['set']]} ({s['n_settings']})" in tex


# ---------------------------------------------------------------------------------------------------------------
# helpers
def test_lib_cells_and_order():
    from figs.supp import ms7_e7r_lib as E
    assert E.num(-0.0001) == "0.000" and E.num(-0.25) == "$-$0.250" and E.num(None) == "--"
    assert E.med_range({"median": 0.5, "min": 0.4, "max": 0.6}) == "0.500 (0.400--0.600)"
    assert E.med_range({"median": 0.5, "min": 0.5, "max": 0.5}) == "0.500" and E.med_range(None) == "--"
    assert E.wtl({"wins": 3, "ties": 1, "losses": 2, "missing": 0}) == "3/1/2"
    assert E.wtl({"wins": 3, "ties": 1, "losses": 2, "missing": 4}) == "3/1/2+4"
    assert E.count(5) == "five" and E.count(13) == "13"
    a = analysis()
    order = E.tag_order(a["tags"])
    assert sorted(order) == sorted(a["tags"]) and order[0] == "Sublet"
    groups = [E.group_of(t, a["tags"][t]) for t in order]
    assert groups == sorted(groups, key=E.GROUP_ORDER.index)
    st = module("sf_stress_ms7")
    cols = [c["mode"] for c in st.mode_columns({m for x in a["tags"].values() for m in x["r0"]})]
    assert cols[:2] == ["L-tr", "L-hon"] and cols[-1] == "L-pk"
    iid = [c for c in cols if c.startswith("L-iid-")]
    assert iid == sorted(iid, key=lambda m: float(m[6:]))


def test_every_tuning_configuration_has_its_own_words():
    """setting_text describes every configuration of the registered grids in words (no knob=value fallback), and two
    configurations of one family never read the same."""
    from sublet.experiments import ms7_baselines as mb
    mod = module("sf_bl_ms7")
    defaults = mod._knob_defaults()
    for fam in mb.FAMILIES:
        texts = [mod.setting_text(fam, pid, p, defaults) for pid, p in mb.grid(fam).values()]
        assert not [x for x in texts if "=" in re.sub(r"\$[^$]*\$", "", x)], texts
        assert len(set(texts)) == len(texts), fam


# ---------------------------------------------------------------------------------------------------------------
# real scale (a stand-in tree in tmp_path; its numbers exist only in the test)
def _standin(tmp_path: Path) -> Path:
    spec = importlib.util.spec_from_file_location("g4b_standin", FIX / "standin.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m.standin_root(tmp_path / "standin")


@pytest.fixture(scope="module")
def real_scale(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("g4b_real")
    root = _standin(tmp)
    env = {"SUBLET_FIGS_IN_ROOT": str(root), style.ENV_PDF_DIR: str(tmp / "pdf"), style.ENV_OUT_DIR: str(tmp / "out"),
           "SUBLET_FIGS_TABLES_DIR": str(tmp / "tables")}
    old = {k: os.environ.get(k) for k in env}
    os.environ.update(env)
    try:
        reps = {n: module(n).main([]) for n in NAMES}
    finally:
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
    return tmp, reps


def test_real_scale_figures(real_scale):
    tmp, reps = real_scale
    for name, rep in reps.items():
        assert rep["outside_page"] == [], name
        assert rep["text_pt"] and set(rep["text_pt"]) <= {style.TICK_PT, style.LABEL_PT}, name
        d = jl(tmp / "out" / f"{name}.json")["data"]
        assert len(d["weeks"]) == 16 and d["meta"]["reduced"] is False
    d = jl(tmp / "out" / "sf_bl_ms7.json")["data"]
    fig = module("sf_bl_ms7").draw(d)
    r = fig.canvas.get_renderer()
    for ax in fig._sublet_axes:                 # tick labels inside their panel
        bb = ax.get_window_extent(r)
        for t in ax.get_xticklabels():
            if t.get_text():
                tb = t.get_window_extent(r)
                assert bb.x0 - 0.5 <= tb.x0 and tb.x1 <= bb.x1 + 0.5, t.get_text()
    for ax in fig._sublet_axes:                 # an arrow joins the two medians of its own row
        for c in ax.texts:
            if getattr(c, "_sublet_role", "") == "arrow":
                assert c._sublet_pair[0] != c._sublet_pair[1]
    d2 = jl(tmp / "out" / "sf_stress_ms7.json")["data"]
    fig2 = module("sf_stress_ms7").draw(d2)
    labs = [t for ax in fig2._sublet_axes for t in ax.texts if getattr(t, "_sublet_role", "") == "direct_label"]
    assert len(labs) == len(d2["groups"]) and all(t.get_text() == "Sublet" for t in labs)


@pytest.mark.skipif(not PDFLATEX.is_file(), reason="pdflatex is not installed")
def test_tables_compile_without_overfull_boxes(real_scale, tmp_path):
    """The five tables of the fixture extracts and of the real-scale stand-in compile in the supplement's class
    (IEEEtran, one column, as paper/supplement/supplement.tex) with no overfull box."""
    tmp, _ = real_scale
    inputs = []
    for n in NAMES:
        for t in TABLES[n]:
            if not t.endswith(".tex"):
                continue
            (tmp_path / f"fix_{t}").write_text(tex_of(n, t))
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
