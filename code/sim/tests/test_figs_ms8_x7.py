"""Tests of the supplementary figure and tables of X7, the request-level replay with a queue (design/ms8/plan.md D1, W;
design/ms8/registration.md §2-§3): figs/supp/sf_e8q.py.

Quick. The inputs are the input tree tests/fixtures_figs_ms8/x7/inputs/ (a reduced-mode output of the X7 driver,
trimmed, and the frozen analysis run on it; README there) and the fixture extract tests/fixtures_figs_ms8/x7/
sf_e8q.json (what the script writes on that tree; refresh_extracts.py there); every file is written under pytest's
tmp_path. The real-scale test runs on stand-ins (tests/fixtures_figs_ms8/x7/standins.py: made-up numbers at the
registered grid, in tmp_path only) through the frozen analysis.

- Registration: the figure's size and set (figs/style.py's MS8 unit F7 block), the script's KEYS, RUN_INPUTS (MS8 run
  outputs only, the analysis first) and TABLES (three tables, two CSV data files); the rebuild entry (its tables and
  data files among the outputs, its RUN_INPUTS as run inputs, pending in a tree without them).
- On the fixture: build() gives the fixture extract's data and records only its RUN_INPUTS as sources; --from-extract
  rewrites the extract, the tables and the data files byte for byte (and the build from the inputs writes the same
  tables), a second redraw gives the same PDF bytes, finalize() passes at C62's text sizes; a missing input exits 2
  with the file named; reduced input is never written into paper/ or code/sim/out/; a non-reduced analysis that is not
  the registered one on full runs, a summary that the analysis did not read, an analysis that records no input and an
  analysis whose summary blocks disagree with its cells are refused.
- Reported in full, and the values: every cell, policy and W in the cells data file, every tier, policy, W and class of
  Q-2 in the latency data file and every W in the tables; the plotted and tabulated values are the analysis's (value
  oracles with statistics.median), the four parts of each gap add up to it.
- Printed text: registry labels only, no design ID or tag in the caption, the tables or the figure's texts.
- Real scale (stand-ins): the script saves with finalize() passing on a non-reduced, registered analysis (Q-0 'pass'
  against E8 v2's stored pairs), the value checks hold, every window class is drawn in (c), a percentile in the last
  bin is printed as a bound at its edge, and the tables compile in the supplement's class without an overfull box or
  an error; with runs removed from a copy, the wins count of all 36 cells (a missing run is a loss, registration §3)
  and the caption names the missing runs.
- Small rules: the copies' three significant figures, the last bin's edge from the analysis's note, the quartiles;
  the tables' group rules.
"""
from __future__ import annotations

import csv
import hashlib
import importlib
import importlib.util
import importlib.util
import io
import json
import os
import re
import shutil
import statistics
import subprocess
import sys
from pathlib import Path

import pytest

from figs import rebuild as rb
from figs import style
from figs.inputs import Inputs

NAME = "sf_e8q"
FIX = Path(__file__).resolve().parent / "fixtures_figs_ms8" / "x7"
IN_ROOT = FIX / "inputs"
OUT = IN_ROOT / "code" / "sim" / "out"
REPO = style.REPO
PDFLATEX = Path.home() / ".local" / "bin" / "pdflatex"
STALE = ("tests/fixtures_figs_ms8/x7/sf_e8q.json is stale (the script's data changed): refresh it with "
         "`python tests/fixtures_figs_ms8/x7/refresh_extracts.py` from code/sim")
# design IDs and tags that the printed text never carries
DESIGN = re.compile(r"\b(BL\d|A\d\b|A9|A6|X\d|H\d|MS\d|E8\b|T0)|Sublet-|\bc2\b|-(T|W)\b|kstar|BO\b|\bcur\b|e8q|"
                    r"_V\d")
WAITS = ("0", "1", "2.5", "10")

pytestmark = pytest.mark.filterwarnings("ignore::figs.style.GlyphSizeWarning")


def mod():
    return importlib.import_module(f"figs.supp.{NAME}")


def jl(p: Path):
    return json.loads(Path(p).read_text())


def fixture_payload() -> dict:
    return jl(FIX / f"{NAME}.json")


def standins():
    """The X7 stand-ins, loaded from their file under a name of their own: test_figs_ms7_c.py imports another
    fixture folder's standins.py as 'standins', which a plain import here would reuse from sys.modules."""
    name = "fixtures_figs_ms8_x7_standins"
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, FIX / "standins.py")
        m_ = importlib.util.module_from_spec(spec)
        sys.modules[name] = m_
        spec.loader.exec_module(m_)
    return sys.modules[name]


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("SUBLET_FIGS_IN_ROOT", str(IN_ROOT))
    monkeypatch.setenv(style.ENV_PDF_DIR, str(tmp_path / "pdf"))
    monkeypatch.setenv(style.ENV_OUT_DIR, str(tmp_path / "out"))
    monkeypatch.setenv("SUBLET_FIGS_TABLES_DIR", str(tmp_path / "tables"))
    return tmp_path


@pytest.fixture
def registry_without_test_figures():
    leaked = {k: v for k, v in style.FIGURES.items() if k.startswith("test_")}
    for k in leaked:
        del style.FIGURES[k]
    yield
    style.FIGURES.update(leaked)


# ---------------------------------------------------------------------------------------------------------------
# Registration
def test_registration():
    m = mod()
    spec = style.FIGURES[NAME]
    assert (spec.width, spec.height_in, spec.main) == ("W2", 2.5, False)
    assert tuple(m.KEYS) == style.SUPP_POLICIES_MS8[NAME] == ("sublet_v2", "a9", "bl5_cur", "bl1_bo", "bl0a")
    assert NAME in style.figure_sets()
    style.check_policies(m.KEYS)
    assert tuple(m.KEYS) == tuple(style.legend_order(m.KEYS))
    mf = [(style.POLICIES[k].marker, style.POLICIES[k].fill) for k in m.KEYS if style.POLICIES[k].marker]
    assert len(set(mf)) == len(mf)
    assert m.NAME == NAME and m.INPUTS == m.RUN_INPUTS == ("code/sim/out/e8q/analysis.json",
                                                          "code/sim/out/e8q/summary.json")
    assert all(p.startswith(rb.MS8_RUN_DIRS) for p in m.RUN_INPUTS)
    assert [t.rsplit(".", 1)[1] for t in m.TABLES] == ["tex"] * 3 + ["csv"] * 2
    for k in m.KEYS:
        assert style.POLICIES[k].label and not DESIGN.search(style.POLICIES[k].label), k
    # the frozen analysis's constants, which the script repeats
    from sublet.experiments import e8q_analysis as A
    assert (m.TAGS[0], set(m.TAGS)) == ("Sublet", set(A.TAGS)) and m.PAIR == A.PAIR and m.BILL == A.BILL
    assert m.WAITS == A.WAITS and (m.W0, m.W_STAR) == (A.W0, A.W_STAR) and m.CLASSES == A.CLASSES
    assert m.PARTS == A.PARTS and m.QUANT == tuple(A.QUANTILES)
    from sublet.experiments.ms3_common import num_key
    assert m.D_FB == tuple(num_key(x) for x in A.D_FB)


def test_rebuild_entry_pending_until_the_runs(registry_without_test_figures, tmp_path):
    m = mod()
    assert rb.MS8_SUPP_SCRIPTS[NAME] == f"code/sim/figs/supp/{NAME}.py"
    assert rb.MS8_SUPP_RUN_INPUTS[NAME] == tuple(m.RUN_INPUTS)
    e = {x.name: x for x in rb.entries()}[NAME]
    assert (e.kind, e.script, e.module) == ("supp", f"code/sim/figs/supp/{NAME}.py", f"figs.supp.{NAME}")
    assert e.outputs == (f"paper/supplement/figures/{NAME}.pdf", f"code/sim/out/figs/{NAME}.json",
                         f"code/sim/out/figs/{NAME}.png") + tuple(f"paper/supplement/tables/{t}" for t in m.TABLES)
    assert e.run_inputs == tuple(m.RUN_INPUTS) and rb.pending_inputs(e) == tuple(m.RUN_INPUTS)
    # in this checkout: pending until the X7 outputs are copied in
    want = not any((REPO / p).is_file() for p in e.outputs) and any(not (REPO / p).is_file() for p in e.run_inputs)
    assert rb.is_pending(REPO, e) == want
    root = tmp_path / "root"
    root.mkdir()
    assert rb.is_pending(root, e) and rb.coverage(root, [e])["pending"] == [NAME]
    (root / m.RUN_INPUTS[0]).parent.mkdir(parents=True, exist_ok=True)
    (root / m.RUN_INPUTS[0]).write_text("{}")
    assert rb.is_pending(root, e)                         # the summary still missing
    (root / m.RUN_INPUTS[1]).write_text("{}")
    assert not rb.is_pending(root, e) and rb.coverage(root, [e])["missing"] == sorted(e.outputs)
    # a reduced extract in the tree is a list error
    (root / e.extract).parent.mkdir(parents=True, exist_ok=True)
    (root / e.extract).write_text(json.dumps({"meta": {"reduced": True}}))
    assert rb.reduced_extracts(root, [e]) and not rb.coverage(root, [e])["ok"]


@pytest.mark.parametrize("attrs,match", [
    (dict(), "declares no RUN_INPUTS"),
    (dict(RUN_INPUTS=("code/sim/out/e8v2/analysis.json",)), "no file in an MS8 run folder"),
    (dict(RUN_INPUTS=("paper/values/evaluation.json",)), "not run outputs"),
])
def test_rebuild_list_errors_of_the_script(registry_without_test_figures, monkeypatch, attrs, match):
    import types
    module, script = f"figs.supp.{NAME}", f"code/sim/figs/supp/{NAME}.py"
    fake = types.SimpleNamespace(NAME=NAME, **attrs)
    real = [s for s in rb.figure_scripts() if s[1] != module]
    monkeypatch.setattr(rb, "figure_scripts", lambda: real + [("supp", module, script)])
    imp = rb._import
    monkeypatch.setattr(rb, "_import", lambda mm: fake if mm == module else imp(mm))
    with pytest.raises(rb.RebuildError, match=match):
        rb.entries()


# ---------------------------------------------------------------------------------------------------------------
# The script on the fixture
def test_build_matches_fixture(env):
    m = mod()
    inp = Inputs()
    data = json.loads(json.dumps(m.build(inp), allow_nan=False))
    assert data == fixture_payload()["data"], STALE
    assert sorted(inp.sources) == sorted(m.RUN_INPUTS)
    assert data["meta"]["reduced"] is True and data["meta"]["analysis"]["registered_full_inputs"] is False
    assert data["headline"] == jl(OUT / "e8q" / "analysis.json")["headline"]
    assert data["labels"]["caption"] and data["labels"]["values"]


def test_from_extract_rewrites_every_output_byte_for_byte(env):
    m = mod()
    rep = m.main(["--from-extract", str(FIX / f"{NAME}.json")])
    spec = style.figure_spec(NAME)
    assert abs(rep["width_bp"] - spec.width_in * 72) <= 0.5 and abs(rep["height_bp"] - spec.height_in * 72) <= 0.5
    assert rep["pages"] == 1 and rep["outside_page"] == []
    assert rep["text_pt"] and set(rep["text_pt"]) <= {style.TICK_PT, style.LABEL_PT}
    assert rep["min_glyph_pt"] >= style.SCRIPT_MIN_PT - 1e-6
    assert not any("dejavu" in f.lower() for f in rep["fonts"])
    assert jl(env / "out" / f"{NAME}.json") == fixture_payload()
    first = {t: (env / "tables" / t).read_bytes() for t in m.TABLES}
    pdf1 = Path(rep["pdf"]).read_bytes()
    for t in m.TABLES:
        (env / "tables" / t).unlink()
    rep2 = m.main(["--from-extract", str(env / "out" / f"{NAME}.json")])
    assert Path(rep2["pdf"]).read_bytes() == pdf1
    assert {t: (env / "tables" / t).read_bytes() for t in m.TABLES} == first
    for t in m.TABLES:
        (env / "tables" / t).unlink()
    m.main([])
    assert {t: (env / "tables" / t).read_bytes() for t in m.TABLES} == first
    d = fixture_payload()["data"]["tables"]
    for t, key in ((m.CELLS_CSV, "e8q_cells"), (m.LATENCY_CSV, "e8q_latency")):
        assert hashlib.sha256(first[t]).hexdigest() == d[key]["sha256"]
    for t in m.TABLES[:3]:
        text = first[t].decode()
        assert text.startswith(f"% Written by code/sim/figs/supp/{NAME}.py") and r"\begin{longtable}" in text


def _copy_tree(tmp_path: Path) -> Path:
    root = tmp_path / "tree"
    shutil.copytree(IN_ROOT, root)
    return root


@pytest.mark.parametrize("i", [0, 1])
def test_missing_input_exits_2(i, tmp_path, monkeypatch, capsys):
    m = mod()
    root = _copy_tree(tmp_path)
    (root / m.RUN_INPUTS[i]).unlink()
    monkeypatch.setenv("SUBLET_FIGS_IN_ROOT", str(root))
    monkeypatch.setenv(style.ENV_PDF_DIR, str(tmp_path / "pdf"))
    monkeypatch.setenv(style.ENV_OUT_DIR, str(tmp_path / "out"))
    with pytest.raises(SystemExit) as e:
        m.main([])
    assert e.value.code == 2
    err = capsys.readouterr().err
    assert m.RUN_INPUTS[i] in err and "MS8 run output" in err
    assert not (tmp_path / "pdf").exists() and not (tmp_path / "out").exists()


def test_reduced_input_is_never_written_into_versioned_folders(tmp_path, monkeypatch):
    m = mod()
    watched = [REPO / "paper" / "supplement" / "figures", REPO / "paper" / "supplement" / "tables",
               style.DEFAULT_OUT_DIR]
    before = {d: sorted((p.name, p.stat().st_mtime_ns) for p in d.iterdir()) for d in watched}
    monkeypatch.setenv("SUBLET_FIGS_IN_ROOT", str(IN_ROOT))
    for k in (style.ENV_PDF_DIR, style.ENV_OUT_DIR, "SUBLET_FIGS_TABLES_DIR"):
        monkeypatch.delenv(k, raising=False)
    for argv in ([], ["--from-extract", str(FIX / f"{NAME}.json")]):
        with pytest.raises(SystemExit, match="reduced"):
            m.main(argv)
    monkeypatch.setenv(style.ENV_PDF_DIR, str(tmp_path / "pdf"))
    with pytest.raises(SystemExit, match="reduced"):
        m.main(["--from-extract", str(FIX / f"{NAME}.json")])
    monkeypatch.setenv(style.ENV_OUT_DIR, str(REPO / "code" / "sim" / "out" / "scratch_x7"))
    with pytest.raises(SystemExit, match="reduced"):
        m.main(["--from-extract", str(FIX / f"{NAME}.json")])
    assert not (REPO / "code" / "sim" / "out" / "scratch_x7").exists() and not (tmp_path / "pdf").exists()
    assert {d: sorted((p.name, p.stat().st_mtime_ns) for p in d.iterdir()) for d in watched} == before


def test_unregistered_or_inconsistent_analysis_is_refused(tmp_path, monkeypatch):
    m = mod()
    monkeypatch.setenv(style.ENV_PDF_DIR, str(tmp_path / "pdf"))
    monkeypatch.setenv(style.ENV_OUT_DIR, str(tmp_path / "out"))
    root = _copy_tree(tmp_path)
    monkeypatch.setenv("SUBLET_FIGS_IN_ROOT", str(root))
    ap = root / m.RUN_INPUTS[0]
    a = jl(ap)
    full = json.loads(json.dumps(a))
    full["meta"]["reduced"] = False
    for x in full["meta"]["input_records"]:
        x["reduced"] = False
    ap.write_text(json.dumps(full))
    with pytest.raises(style.StyleError, match="not a registered analysis"):
        m.build(Inputs())
    ap.write_text(json.dumps(a))
    s = root / m.RUN_INPUTS[1]
    s.write_text(s.read_text() + " ")
    with pytest.raises(style.StyleError, match="not the summary that the analysis read"):
        m.build(Inputs())
    s.write_text(s.read_text()[:-1])
    none = json.loads(json.dumps(a))
    none["meta"]["input_records"] = []
    ap.write_text(json.dumps(none))
    with pytest.raises(style.StyleError, match="records no sha256"):
        m.build(Inputs())
    # an analysis whose summary blocks disagree with its own cells (edited after the run)
    bad = json.loads(json.dumps(a))
    bad["q1"]["overall"]["2.5"]["E_abs_median"]["Sublet"] += 0.01
    ap.write_text(json.dumps(bad))
    with pytest.raises(style.StyleError, match="stale or edited"):
        m.build(Inputs())


# ---------------------------------------------------------------------------------------------------------------
# Reported in full, and the values (on the fixture extract and, in test_real_scale, on the stand-ins)
def _csv(d: dict, key: str) -> list[dict]:
    m = mod()
    e = d["tables"][key]
    return list(csv.DictReader(io.StringIO(m.X.csv_text(e["columns"], e["rows"]))))


def _f(s: str):
    return None if s == "" else float(s)


def check_values(d: dict, out: Path) -> None:
    m = mod()
    a = jl(out / "e8q" / "analysis.json")
    s = jl(out / "e8q" / "summary.json")
    q1, q2, q3 = a["q1"], a["q2"], a["q3"]
    cells = [(t, w, c) for t, x in s["cells"].items() for w, y in x.items() for c in y]
    # the cells data file: every cell, tag (and the bill) and W, the analysis's values
    rows = _csv(d, "e8q_cells")
    assert len(rows) == len(cells) * len(WAITS) * 5
    by = {(r["tier"], r["window_min"], r["alignment"], r["wait_s"], r["tag"]): r for r in rows}
    for W in WAITS:
        for t, w, c in cells:
            e = q1["cells"][W][t][w][c]
            for tg in m.TAGS:
                r = by[(t, w, c, format(float(W), ".9g"), tg)]
                y = e["tags"][tg]
                for col, v in (("c_replay_usd", y["C_replay"]), ("error", y["E"]), ("cost_over_bill", y["r"]),
                               ("gap_usd", y["gap_usd"]), ("delta_over_bill", e["delta"])):
                    assert _f(r[col]) == pytest.approx(v, rel=1e-8, abs=1e-12), (t, w, c, W, tg, col)
                assert r["sublet_below_both"] == ("true" if e["win"] else "false")
                parts = sum(_f(r[f"{p}_usd"]) for p in m.PARTS)
                assert parts == pytest.approx(_f(r["gap_usd"]), rel=1e-6, abs=1e-6)
            b = by[(t, w, c, format(float(W), ".9g"), "BL0a")]
            assert _f(b["c_replay_usd"]) == pytest.approx(e["bill"], rel=1e-8)
    # (a): the signed E per tag (and the bill) and W: the analysis's median and count below 0, the quartiles and the
    # range over the cells
    for tg in m.TAGS + ("BL0a",):
        for r in d["panels"]["a"]["series"][tg]:
            o = q1["overall"][r["W"]]
            es = [q1["cells"][r["W"]][t][w][c]["bill_E" if tg == "BL0a" else "tags"] for t, w, c in cells]
            es = es if tg == "BL0a" else [x[tg]["E"] for x in es]
            want = o["bill_E_median"] if tg == "BL0a" else o["E_median"][tg]
            neg = o["bill_n_E_negative"] if tg == "BL0a" else o["n_E_negative"][tg]
            assert r["median"] == pytest.approx(100 * want, rel=1e-9, abs=1e-12)
            assert r["median"] == pytest.approx(100 * statistics.median(es), rel=1e-9, abs=1e-12)
            assert r["n_negative"] == neg == sum(1 for x in es if x < 0)
            q = statistics.quantiles(es, n=4, method="inclusive")
            assert (r["q25"], r["q75"]) == (pytest.approx(100 * q[0]), pytest.approx(100 * q[2]))
            assert (r["min"], r["max"]) == (pytest.approx(100 * min(es)), pytest.approx(100 * max(es)))
    # the registered rule's |E| in the values (caption)
    for W in WAITS:
        es = [abs(q1["cells"][W][t][w][c]["tags"]["Sublet"]["E"]) for t, w, c in cells]
        assert d["labels"]["values"]["sublet_abs_E_median_pct"][W] == \
            pytest.approx(100 * a["q1"]["overall"][W]["E_abs_median"]["Sublet"]) == pytest.approx(
                100 * statistics.median(es))
    # (b): the ratios and the wins
    for tg in m.OTHERS:
        for r in d["panels"]["b"]["series"][tg]:
            v = [q1["cells"][r["W"]][t][w][c]["tags"][tg]["C_replay"]
                 / q1["cells"][r["W"]][t][w][c]["tags"]["Sublet"]["C_replay"] for t, w, c in cells]
            assert r["median"] == pytest.approx(statistics.median(v), rel=1e-9) and r["n"] == len(cells)
    assert [w["wins"] for w in d["panels"]["b"]["wins"]] == [q1["overall"][W]["wins"] for W in WAITS]
    assert [w["n_cells"] for w in d["panels"]["b"]["wins"]] == [len(cells)] * len(WAITS)    # a missing run: a loss
    # (c): the fallback share per class at W = 0 and W*, per tier the analysis's, pooled by copies
    for tg in m.TAGS + ("BL0a",):
        for r in d["panels"]["c"]["series"][tg]:
            for W in (m.W0, m.W_STAR):
                zs = {t: q2["by_tier"][t][tg][W][r["class"]] for t in q2["by_tier"]}
                zs = {t: z for t, z in zs.items() if z["copies"]}
                assert r[W]["tiers"] == {t: pytest.approx(100 * z["fallback_share"]) for t, z in zs.items()}
                n = sum(z["copies"] for z in zs.values())
                assert r[W]["copies"] == n
                if n:
                    assert r[W]["pooled"] == pytest.approx(
                        100 * sum(z["fallback_share"] * z["copies"] for z in zs.values()) / n)
                else:
                    assert r[W]["pooled"] is None
    # the latency data file: the whole of Q-2
    lat = _csv(d, "e8q_latency")
    n = sum(1 for t, x in q2["by_tier"].items() for tg, y in x.items() for W, z in y.items() for cn in z)
    assert len(lat) == n
    for r in lat:
        z = q2["by_tier"][r["tier"]][r["tag"]][{float(W): W for W in WAITS}[float(r["wait_s"])]][r["window_class"]]
        assert int(r["copies"]) == z["copies"] and _f(r["fallback_share"]) == pytest.approx(z["fallback_share"]) \
            if z["fallback_share"] is not None else r["fallback_share"] == ""
        for dfb in m.D_FB:
            v = z["ttft"][dfb]["p99"]
            assert (_f(r[f"p99_s_dfb_{dfb}"]) == pytest.approx(v)) if v is not None else r[f"p99_s_dfb_{dfb}"] == ""
    # the tables: every W, tiers and 'all'; Q-3 the analysis's medians
    assert [(r["W"], r["tier"]) for r in d["tables"]["costs"]] == \
        [(W, t) for W in WAITS for t in list(s["cells"]) + ["all"]]
    for r in d["tables"]["decomp"]:
        x = q3["overall"][r["W"]][r["tag"]]
        assert {k: r[k] for k in m.Q3_KEYS} == {k: x[k] for k in m.Q3_KEYS}
    assert {(r["W"], r["class"]) for r in d["tables"]["latency"]} <= \
        {(m.W0, "all")} | {(m.W_STAR, cn) for cn in m.CLASSES + ("all",)}
    assert {r["W"] for r in d["tables"]["latency"]} == {m.W0, m.W_STAR}


def test_reported_in_full_and_values():
    check_values(fixture_payload()["data"], OUT)


def test_decompose_is_the_analysis_rule():
    from sublet.experiments import e8q_analysis as A
    m = mod()
    s = jl(OUT / "e8q" / "summary.json")
    for t, x in s["cells"].items():
        for w, y in x.items():
            for c, z in y.items():
                for tg in m.TAGS:
                    for W in WAITS:
                        assert m.decompose(z[tg], W) == A.decompose(z[tg], W)


# ---------------------------------------------------------------------------------------------------------------
# Printed text
def test_printed_text_has_no_design_names(env):
    m = mod()
    d = fixture_payload()["data"]
    assert not DESIGN.search(d["labels"]["caption"]), d["labels"]["caption"]
    m.main(["--from-extract", str(FIX / f"{NAME}.json")])
    for t in m.TABLES[:3]:
        body = "\n".join(ln for ln in (env / "tables" / t).read_text().splitlines() if not ln.startswith("%"))
        hit = DESIGN.search(body.replace(r"\label{", "").replace("tab:s-e8q-", "").replace("e8q\\_", ""))
        assert not hit, (t, hit.group(0), body[max(0, hit.start() - 80):hit.end() + 40])
    fig = m.draw(d)
    texts = [t.get_text() for t in style.drawn_texts(fig)]
    assert not [t for t in texts if DESIGN.search(t)], texts
    labels = {style.POLICIES[k].label for k in m.KEYS}
    leg = [t.get_text() for lg in fig.legends for t in lg.get_texts()]
    assert sorted(leg) == sorted(labels)


# ---------------------------------------------------------------------------------------------------------------
# Real scale (stand-ins in tmp_path only)
@pytest.fixture(scope="module")
def real_root(tmp_path_factory):
    return standins().standin_tree(tmp_path_factory.mktemp("x7_real"))


PREAMBLE = r"""\documentclass[lettersize,journal,onecolumn]{IEEEtran}
\usepackage{amsmath}\usepackage{amssymb}\usepackage{graphicx}\usepackage{booktabs}\usepackage{array}
\usepackage{longtable}
\makeatletter
\setlength{\LTcapwidth}{\textwidth}
\def\LT@makecaption#1#2#3{\LT@mcol\LT@cols c{\hbox to\z@{\hss\parbox[t]\LTcapwidth{\centering\footnotesize
  #1{\MakeUppercase{#2}\\[2pt]}{\scshape #3}\endgraf\vskip\baselineskip}\hss}}}
\makeatother
\renewcommand{\thetable}{S\arabic{table}}
\hyphenation{Retro-Rent-ing}
\begin{document}
"""


def test_real_scale(real_root, tmp_path, monkeypatch):
    m = mod()
    monkeypatch.setenv("SUBLET_FIGS_IN_ROOT", str(real_root))
    monkeypatch.setenv(style.ENV_PDF_DIR, str(tmp_path / "pdf"))
    monkeypatch.setenv(style.ENV_OUT_DIR, str(tmp_path / "out"))
    monkeypatch.setenv("SUBLET_FIGS_TABLES_DIR", str(tmp_path / "tables"))
    rep = m.main([])
    assert rep["outside_page"] == []
    assert rep["text_pt"] and set(rep["text_pt"]) <= {style.TICK_PT, style.LABEL_PT}
    d = jl(tmp_path / "out" / f"{NAME}.json")["data"]
    assert d["meta"]["reduced"] is False and d["meta"]["analysis"]["registered_full_inputs"] is True
    assert d["q0"]["status"] == "pass" and d["q0"]["n"] == 36 * 4
    assert d["labels"]["values"]["n_cells"] == 36 and len(d["tables"]["e8q_cells"]["rows"]) == 36 * 4 * 5
    check_values(d, real_root / "code" / "sim" / "out")
    # every window class drawn in (c); the stand-ins' tail in the last bin printed as a bound at the bin's edge
    assert d["layout"]["c"]["classes"] == list(m.CLASSES)
    lat = (tmp_path / "tables" / m.TABLES[1]).read_text()
    assert r"$\geq$20 &" in lat and " & reclaim & " in lat
    t, tg, cn = standins().CAPPED
    row = [r for r in d["tables"]["latency"] if (r["tier"], r["tag"], r["W"], r["class"]) == (t, tg, m.W_STAR, cn)]
    assert row and row[0]["ttft"]["1"]["capped"] == ["p99", "p999"] and row[0]["ttft"]["1"]["cap_s"]["p99"] == 20.0
    assert any(r["percentiles_in_last_bin"] for r in _csv(d, "e8q_latency"))
    if not PDFLATEX.is_file():
        pytest.skip(f"{PDFLATEX} is not installed")
    shutil.copy(REPO / "paper" / "IEEEtran.cls", tmp_path / "tables" / "IEEEtran.cls")
    doc = PREAMBLE + "".join(f"\\input{{{t}}}\n" for t in m.TABLES[:3]) + "\\end{document}\n"
    (tmp_path / "tables" / "doc.tex").write_text(doc)
    r = subprocess.run([str(PDFLATEX), "-interaction=nonstopmode", "-halt-on-error", "doc.tex"],
                       cwd=tmp_path / "tables", capture_output=True, text=True, timeout=300,
                       env=dict(os.environ, TEXINPUTS=f"{tmp_path / 'tables'}:"))
    log = (tmp_path / "tables" / "doc.log").read_text(errors="replace")
    assert r.returncode == 0, log[-2000:]
    assert "Overfull" not in log and "LaTeX Error" not in log, [ln for ln in log.splitlines() if "Overfull" in ln]


def test_missing_runs_count_as_losses(real_root, tmp_path, monkeypatch):
    """Registration §3: a missing run counts as a loss, so (b) and the costs table count wins of all 36 cells and
    the caption names the missing runs (one whole cell and a lone run of the bill removed from a stand-in copy)."""
    m = mod()
    root = tmp_path / "miss"
    shutil.copytree(real_root, root)
    sp = root / "code" / "sim" / "out" / "e8q" / "summary.json"
    s = jl(sp)
    miss = []
    for tg in list(s["cells"]["M"]["15"]["2"]):
        s["cells"]["M"]["15"]["2"][tg] = None
        miss.append({"job": "M-15-2", "tag": tg, "why": "run missing"})
    s["cells"]["S"]["5"]["1"]["BL0a"] = None
    miss.append({"job": "S-5-1", "tag": "BL0a", "why": "run missing"})
    s["missing"] = miss
    sp.write_text(json.dumps(s))
    from sublet.experiments import e8q_analysis as A
    a = A.run_analysis(root=root / "code" / "sim")
    assert all(a["q1"]["overall"][W]["n_with_delta"] == 34 for W in WAITS)
    monkeypatch.setenv("SUBLET_FIGS_IN_ROOT", str(root))
    monkeypatch.setenv(style.ENV_PDF_DIR, str(tmp_path / "pdf"))
    monkeypatch.setenv(style.ENV_OUT_DIR, str(tmp_path / "out"))
    monkeypatch.setenv("SUBLET_FIGS_TABLES_DIR", str(tmp_path / "tables"))
    m.main([])
    d = jl(tmp_path / "out" / f"{NAME}.json")["data"]
    assert [w["n_cells"] for w in d["panels"]["b"]["wins"]] == [36] * 4
    fig = m.draw(d)
    counts = [t.get_text() for t in style.drawn_texts(fig) if getattr(t, "_sublet_role", None) == "win_count"]
    assert counts and all(c.endswith("/36") for c in counts), counts
    costs = (tmp_path / "tables" / m.TABLES[0]).read_text()
    below = re.findall(r"& (\d+)/(\d+) & (\d+)/(\d+) \\tabularnewline", costs)
    assert len(below) == 4 * 4 and {(b[1], b[3]) for b in below} == {("12", "12"), ("36", "36")}
    v = d["labels"]["values"]
    assert v["n_missing"] == 6 and v["missing_by_tag"] == {"Sublet": 1, "A9": 1, "BL1-BO": 1, "BL5-cur": 1, "BL0a": 2}
    assert "Missing runs: 6 (" in d["labels"]["caption"] and "counts as a loss" in d["labels"]["caption"]
    assert not DESIGN.search(d["labels"]["caption"])


def test_small_rules():
    m = mod()
    assert [m._sig3(x) for x in (0, 0.0452, 0.000045, 1.234, 12.34, 123.4, 12345.6)] == \
        ["0", "0.0452", "0.0000450", "1.23", "12.3", "123", "12,346"]
    assert m._cap_edge("in the last bin (>= 20 s)") == 20.0 and m._cap_edge("in the last bin (>= 7.5 s)") == 7.5
    with pytest.raises(style.StyleError):
        m._cap_edge("somewhere")
    assert m.quartiles([3.0]) == {"q25": 3.0, "q75": 3.0} and m.quartiles([]) == {"q25": None, "q75": None}
    assert m.quartiles([1, 2, 3, 4, 5]) == {"q25": 2.0, "q75": 4.0}


def test_table_headers(env):
    """The decomposition's group rules: Gap over its two columns, E outside it; the latency table's W column."""
    m = mod()
    m.main(["--from-extract", str(FIX / f"{NAME}.json")])
    dec = (env / "tables" / m.TABLES[2]).read_text()
    assert r"\cmidrule(lr){7-8}" in dec and r"\multicolumn{2}{c}{Gap}" in dec and "{7-9}" not in dec
    lat = (env / "tables" / m.TABLES[1]).read_text()
    assert r"\cmidrule(lr){10-13}" in lat and " & 0 & all & " in lat
    costs = (env / "tables" / m.TABLES[0]).read_text()
    assert "Greedy, back-off (G)" in costs and "; Greedy, back-off (G)" in costs
    assert "overflow accounting (as in the earlier replay study)" in costs
