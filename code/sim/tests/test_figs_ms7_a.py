"""Tests of the MS7 supplementary figures of writer unit W-G4 A (design/ms7/w_spec.md §4, unit W-G4; change C58):
figs/supp/sf_lag_v2.py (the causal-demand runs, X1 of design/ms7/registration.md) and figs/supp/sf_oos.py (the
out-of-sample folds, X2), their helper figs/supp/ms7_a_lib.py, their tables and data files, their registration in
figs/style.py (block A) and their rebuild entries in figs/rebuild.py.

Quick: no raw data. The inputs are the input tree tests/fixtures_figs_ms7/g4a/inputs/ (reduced-mode outputs of the X1
and X2 drivers and their registered analyses: one development week, one cell per fold; README there) and the fixture
extracts tests/fixtures_figs_ms7/g4a/<name>.json (what each script writes on that tree; refresh_extracts.py). The
full-scale tests build a stand-in tree in tmp_path (tests/fixtures_figs_ms7/g4a/fullscale.py: the registered analyses
rerun on summaries of 16 weeks and 16 cells per fold scaled from the fixture; their numbers exist only in the test).
Every output goes under pytest's tmp_path. The oracles recompute the printed numbers from the input files by other
code paths.

- Registration (block A): both figures at W2 x 2.5 in, their sets in legend order with no (marker, fill) twice, the
  scripts' KEYS, TABLES and RUN_INPUTS (run outputs of the MS7 run folders).
- --from-extract on each fixture extract: style.save at the registered size with finalize() passing (C62's text sizes,
  no overlap, nothing outside the page), the extract written equals the one read, the tables and the data file are the
  writers' text of the extract, and a second redraw writes the same bytes (PDF, extract, tables, data file).
- build() on the input tree gives the fixture's data and records only its inputs; the value oracles (X1: the margins,
  the rows, the lender table, the guard counts and the data file against the analysis and the summaries; X2: the
  margins recomputed from the per-cell r0, OOS minus IS, the rules, the source sums and the data file); every tag,
  lender and week or cell of the input appears in the tables or the data file.
- The checks: a missing input exits 2 and names the file (nothing written); reduced data is refused for each versioned
  folder (PDF, extract, tables); a stale analysis (a value that its summary or per-cell r0 does not give) is refused.
- The printed text names policies by their registry labels and holds no design name or tag.
- The tables compile in the supplement's class (one column, the template's IEEEtran.cls) with no overfull box, on the
  fixture and at full scale (pdflatex, if installed).
- Full scale: each figure saves with finalize() passing, panel (a)'s markers overlap by at most a third of a marker,
  the shaded columns are those with a negative or missing margin, the missing run is named in the caption draft, and
  the rows panels name every row once.
- figs/rebuild.py: each entry lists its tables and data file and is pending until its RUN_INPUTS exist.
- Review of W-G4 A: oracles of the policy tables (X1: r0, W0, RC and lagged minus revealed from the summaries; X2:
  every column from the per-cell r0, with the columns pinned to what the head prints) and of the rules table (the
  confirmation's thresholds applied to the per-cell r0 by another path), on the fixture and at full scale; a median
  over fewer weeks or cells carries the mark and its caption note, and only then; inputs from full runs must be the
  registered X1 analysis on the confirmation weeks and X2's full design (16 cells, 15 tags); the X2 captions describe
  the arms as built (the in-sample twin calibrates every lender on its whole series; the spot lenders' weeks).
"""
from __future__ import annotations

import hashlib
import importlib
import json
import os
import re
import shutil
import statistics
import subprocess
import sys
from pathlib import Path

import pytest

from figs import style
from figs import rebuild as rb
from figs.inputs import Inputs

FIX = Path(__file__).resolve().parent / "fixtures_figs_ms7" / "g4a"
IN_ROOT = FIX / "inputs"
OUT = IN_ROOT / "code" / "sim" / "out"
REPO = style.REPO
SCRIPTS = {"sf_lag_v2": "figs.supp.sf_lag_v2", "sf_oos": "figs.supp.sf_oos"}
NAMES = sorted(SCRIPTS)
TABLES = {"sf_lag_v2": ("lag_v2_modes.tex", "lag_v2_policies.tex", "lag_v2_margins.tex", "lag_v2_guard.tex",
                        "lag_v2_runs.csv"),
          "sf_oos": ("oos_margins.tex", "oos_rules.tex", "oos_policies.tex", "oos_sources.tex", "oos_runs.csv")}
TEX_FN = {"lag_v2_modes": "modes_tex", "lag_v2_policies": "policies_tex", "lag_v2_margins": "margins_tex",
          "lag_v2_guard": "guard_tex", "oos_margins": "margins_tex", "oos_rules": "rules_tex",
          "oos_policies": "policies_tex", "oos_sources": "sources_tex"}
STALE = ("tests/fixtures_figs_ms7/g4a/{}.json is stale (the script's data changed): refresh it with "
         "`python tests/fixtures_figs_ms7/g4a/refresh_extracts.py --only {}` from code/sim")
PDFLATEX = Path.home() / ".local/bin/pdflatex"
STRESS = ("L-eg", "L-ss", "L-iid-0.05", "L-iid-0.2", "L-co")
# design names and tags that no printed text may hold (registry labels and lender names such as L-tr are allowed)
DESIGN = re.compile(r"\b(BL\d|A\d|X\d|H\d|MS\d|e7[a-z]|S1|E\d)\b|Sublet-lag|A9-lag|-lag\b|\bc2\b|kstar|H2b")

pytestmark = pytest.mark.filterwarnings("ignore::figs.style.GlyphSizeWarning")


def module(name):
    return importlib.import_module(SCRIPTS[name])


def payload(name):
    return json.loads((FIX / f"{name}.json").read_text())


def data(name):
    return payload(name)["data"]


def jl(p):
    return json.loads(Path(p).read_text())


def tex_of(name: str, d: dict, table: str) -> str:
    stem = table[:-4]
    return getattr(module(name), TEX_FN[stem])(d["tables"][stem], d)


def set_env(monkeypatch, root: Path, tmp: Path) -> None:
    monkeypatch.setenv("SUBLET_FIGS_IN_ROOT", str(root))
    monkeypatch.setenv(style.ENV_PDF_DIR, str(tmp / "pdf"))
    monkeypatch.setenv(style.ENV_OUT_DIR, str(tmp / "out"))
    monkeypatch.setenv("SUBLET_FIGS_TABLES_DIR", str(tmp / "tables"))


@pytest.fixture
def figs_env(tmp_path, monkeypatch):
    set_env(monkeypatch, IN_ROOT, tmp_path)
    return tmp_path


@pytest.fixture(scope="module")
def full_root(tmp_path_factory):
    """The full-scale stand-in tree (fullscale.py), made once per module."""
    sys.path.insert(0, str(FIX))
    try:
        import fullscale
    finally:
        sys.path.remove(str(FIX))
    return fullscale.write_tree(tmp_path_factory.mktemp("g4a_full"))


@pytest.fixture(scope="module")
def full_out(full_root, tmp_path_factory):
    """Both scripts run on the full-scale tree: {name: (report, extract data, output folder)}."""
    out = {}
    mp = pytest.MonkeyPatch()
    try:
        for name in NAMES:
            t = tmp_path_factory.mktemp(f"g4a_full_{name}")
            set_env(mp, full_root, t)
            rep = module(name).main([])
            out[name] = (rep, jl(t / "out" / f"{name}.json")["data"], t)
    finally:
        mp.undo()
    return out


def copy_tree(tmp_path: Path) -> Path:
    root = tmp_path / "tree"
    shutil.copytree(IN_ROOT, root)
    return root


# ---------------------------------------------------------------------------------------------------------------
# registration
@pytest.mark.parametrize("name", NAMES)
def test_registered(name):
    mod = module(name)
    spec = style.FIGURES[name]
    assert (spec.width, spec.height_in, spec.main) == ("W2", 2.5, False)
    keys = style.SUPP_POLICIES_MS7[name]
    assert tuple(mod.KEYS) == keys == tuple(style.legend_order(keys))
    style.check_policies(keys)
    style.check_legacy({name: keys})
    mf = [(style.POLICIES[k].marker, style.POLICIES[k].fill) for k in keys]
    assert len(set(mf)) == len(mf)
    assert tuple(mod.TABLES) == TABLES[name] and mod.NAME == name
    assert mod.RUN_INPUTS and all(p.startswith(rb.MS7_RUN_DIRS) for p in mod.RUN_INPUTS)
    assert set(mod.RUN_INPUTS) <= set(mod.INPUTS)


def test_sets_cover_the_runs():
    """sf_lag_v2 draws every lagged policy of X1's analysis; sf_oos's rows are Sublet, critical-ratio renting and the
    seven primary baselines (the tables print every tag)."""
    from figs.supp import ms5b_e7_lib as L
    from sublet.experiments import e7c_tags, ms5b_common as m5
    lag = {**L.KEY_OF_TAG, **style.MS7_KEY_OF_TAG}
    tags = list(e7c_tags.LAG_TAGS) + list(e7c_tags.LAGGED_FROM_MAIN)
    assert sorted(lag[t] for t in tags) == sorted(style.SUPP_POLICIES_MS7["sf_lag_v2"])
    assert sorted(L.KEY_OF_TAG[t] for t in ("Sublet", "A9") + tuple(m5.H1_SET)) == \
        sorted(style.SUPP_POLICIES_MS7["sf_oos"])


# ---------------------------------------------------------------------------------------------------------------
# the scripts on the fixtures
def _outputs(t: Path, name: str) -> dict:
    files = [t / "pdf" / f"{name}.pdf", t / "out" / f"{name}.json"] + [t / "tables" / x for x in TABLES[name]]
    return {f.name: f.read_bytes() for f in files}


@pytest.mark.parametrize("name", NAMES)
def test_from_extract_saves_and_is_byte_stable(figs_env, name):
    mod = module(name)
    rep = mod.main(["--from-extract", str(FIX / f"{name}.json")])
    spec = style.figure_spec(name)
    assert abs(rep["width_bp"] - spec.width_in * 72) <= 0.5 and abs(rep["height_bp"] - spec.height_in * 72) <= 0.5
    assert rep["pages"] == 1 and rep["outside_page"] == []
    assert rep["text_pt"] and set(rep["text_pt"]) <= {style.TICK_PT, style.LABEL_PT}
    assert rep["min_glyph_pt"] >= style.SCRIPT_MIN_PT - 1e-6
    assert not any("dejavu" in f.lower() for f in rep["fonts"])
    assert jl(figs_env / "out" / f"{name}.json") == payload(name)
    d = data(name)
    tables = figs_env / "tables"
    assert sorted(p.name for p in tables.iterdir()) == sorted(TABLES[name])
    for t in TABLES[name]:
        text = (tables / t).read_text()
        if t.endswith(".tex"):
            assert text.startswith(f"% Written by code/sim/figs/supp/{name}.py from ")
            assert text.split("\n", 1)[1] == tex_of(name, d, t)
        else:
            entry = d["tables"][t[:-4]]
            assert hashlib.sha256(text.encode()).hexdigest() == entry["sha256"]
            assert text.splitlines()[1:] == entry["lines"] and len(entry["lines"]) == entry["n_rows"]
    first = _outputs(figs_env, name)
    mod.main(["--from-extract", str(figs_env / "out" / f"{name}.json")])
    assert _outputs(figs_env, name) == first


@pytest.mark.parametrize("name", NAMES)
def test_build_on_the_input_tree_matches_the_fixture(figs_env, name):
    mod = module(name)
    inp = Inputs()
    d = json.loads(json.dumps(mod.build(inp), allow_nan=False))
    assert d == data(name), STALE.format(name, name)
    assert set(inp.sources) == set(mod.INPUTS) and all(style.check_source(s) == s for s in inp.sources)
    assert not any("/runs/" in s for s in inp.sources)
    assert payload(name)["sources"] == inp.sources == d["meta"]["sources"]
    assert d["meta"]["reduced"] is True


def test_data_file_writer_refuses_another_sha256():
    from figs.supp import ms7_a_lib as A
    e = A.csv_entry("x.csv", ["a", "b"], [[1, 2.5], [None, "c,d"]], {"tags": []})
    assert A.csv_from_entry(e) == 'a,b\n1,2.5\n,"c,d"\n'
    bad = dict(e, lines=["1,2.6", ',"c,d"'])
    with pytest.raises(style.StyleError, match="sha256"):
        A.csv_from_entry(bad)


# ---------------------------------------------------------------------------------------------------------------
# value oracles: sf_lag_v2
def _val(table, tag, mode, week):
    return (((table.get(tag) or {}).get(mode) or {}).get(str(week)) or {}).get("0")


def _x1_tables(root: Path):
    out = root / "code" / "sim" / "out"
    return jl(out / "e7c" / "analysis.json"), jl(out / "e7c" / "lag" / "summary.json"), \
        jl(out / "sublet_v2" / "main" / "summary.json")


def check_lag_values(d: dict, root: Path) -> None:
    an, lag, main = _x1_tables(root)
    weeks = [str(w) for w in an["meta"]["weeks"]]
    assert d["a"]["weeks"] == weeks
    for s in ("h1", "notice"):
        for k in ("r0", "W0"):
            assert d["a"][f"{s}_{k}"] == [an["margins"][s][k]["weeks"][w]["delta"] for w in weeks]
    tags = d["tags"]
    assert sorted(tags) == sorted(an["policies"])
    src = {t: (main if an["lag_minus_revealed"][t]["lagged_from"] == "main" else lag)["table"] for t in tags}
    for panel, k in (("b", "r0"), ("c", "W0")):
        for row, t in zip(d[panel], tags):
            vals = [an["per_policy"][t][k]["weeks"][w] for w in weeks]
            ok = [v for v in vals if v is not None]
            assert row["lagged"]["median"] == statistics.median(ok) and row["lagged"]["min"] == min(ok)
            rv = [an["lag_minus_revealed"][t][k]["revealed"]["weeks"][w] for w in weeks]
            assert row["revealed"]["median"] == statistics.median([v for v in rv if v is not None])
    # the lender table from the summaries (part lag's table, main's for the lagged RetroRenting-style)
    mt = d["tables"]["lag_v2_modes"]
    assert mt["modes"] == ["L-tr", "L-eg", "L-ss", "L-iid-0.05", "L-iid-0.2", "L-co", "L-hon"]
    for r in mt["rows"]:
        for m in mt["modes"]:
            v = [_val(src[r["tag"]], r["tag"], m, w) for w in weeks]
            ok = [x for x in v if x is not None]
            st = r["stats"][m]
            assert (st["median"], st["min"], st["max"], st["n_missing"]) == \
                (statistics.median(ok) if ok else None, min(ok, default=None), max(ok, default=None),
                 v.count(None)), (r["tag"], m)
    # W0 against the stress lenders (another path than the analysis)
    for t in tags:
        for w in weeks:
            ws = [_val(src[t], t, m, w) for m in STRESS]
            want = None if None in ws else max(ws)
            assert an["per_policy"][t]["W0"]["weeks"][w] == want
    # the guard counts
    g = d["tables"]["lag_v2_guard"]
    for r in g["rows"]:
        g_t = an["guard"]
        want = g_t["by_tag"][r["tag"]] if r["mode"] == "all" else g_t["by_tag_mode"][r["tag"]][r["mode"]]
        assert all(r[k] == int(want[k]) for k in ("runs", "runs_projected", "projected_slots", "aborts", "held"))
    # the data file: every run of every lagged policy, lender and week, with its r0
    e = d["tables"]["lag_v2_runs"]
    rows = list(__import__("csv").reader(e["lines"]))
    assert len(rows) == len(tags) * len(mt["modes"]) * len(weeks) == e["n_rows"]
    for r in rows:
        t, rt, m, w = r[1], r[3], r[4], r[5]
        lv, rv = _val(src[t], t, m, w), _val(main["table"], rt, m, w)
        assert r[7] == ("" if lv is None else f"{lv:.6f}") and r[8] == ("" if rv is None else f"{rv:.6f}")
        assert rt == an["lag_minus_revealed"][t]["revealed"]


def test_lag_value_oracles():
    check_lag_values(data("sf_lag_v2"), IN_ROOT)


def test_lag_margins_table_and_caption():
    d = data("sf_lag_v2")
    an = _x1_tables(IN_ROOT)[0]
    for r in d["tables"]["lag_v2_margins"]["rows"]:
        g = an["margins"][r["set"]][r["metric"]]
        assert (r["n_wins"], r["n_ties"], r["n_losses"], r["n_lost_missing"], r["median"]) == \
            (g["n_wins"], g["n_ties"], g["n_losses"], g["n_lost_missing"], g["median"])
        assert sum(n for _, _, n in r["best"]) == sum(1 for w in g["weeks"].values() if w["best"] is not None)
    cap = d["labels"]["caption"]
    wins = an["margins"]["h1"]["r0"]["n_wins"]
    assert f"in {wins} of {len(d['a']['weeks'])} week" in cap and not DESIGN.search(cap)


# ---------------------------------------------------------------------------------------------------------------
# value oracles: sf_oos
def check_oos_values(d: dict, root: Path) -> None:
    an = jl(root / "code" / "sim" / "out" / "e7o" / "analysis.json")
    h1 = an["h1_set"]
    cells = d["a"]["cells"]
    for f in ("fwd", "rev"):
        x = an["folds"][f]
        pc = x["per_cell"]

        def r0(arm, t, c, k):
            e = pc[arm][t][c]
            return e["W0"] if k == "W0" else e["r0"][k]

        # (a): the least primary baseline minus Sublet, out of sample, recomputed from the per-cell r0
        for key, k in ((f"{f}_r0", "L-tr"), (f"{f}_W0", "W0")):
            for c, v in zip(cells, d["a"][key]):
                s, hv = r0("oos", "Sublet", c, k), [r0("oos", t, c, k) for t in h1]
                assert v == (None if s is None or None in hv else min(hv) - s), (f, k, c)
        # (b), (c): OOS minus IS per tag
        for panel, k in (("b", "L-tr"), ("c", "W0")):
            for row in d[panel]:
                diffs = [None if r0("oos", row["tag"], c, k) is None or r0("is", row["tag"], c, k) is None else
                         r0("oos", row["tag"], c, k) - r0("is", row["tag"], c, k) for c in [str(c) for c in x["cells"]]]
                ok = [v for v in diffs if v is not None]
                assert row[f]["median"] == statistics.median(ok) and row[f]["max"] == max(ok)
                assert row[f]["n_neg"] == sum(v < 0 for v in ok)
        # the margins table: counts and statistics over the cells, every lender and W0, both arms
        for col in [c for c in d["tables"]["oos_margins"]["columns"] if c["fold"] == f]:
            for k, s in col["by"].items():
                ms = [None if r0(col["arm"], "Sublet", c, k) is None or
                      any(r0(col["arm"], t, c, k) is None for t in h1) else
                      min(r0(col["arm"], t, c, k) for t in h1) - r0(col["arm"], "Sublet", c, k)
                      for c in [str(c) for c in x["cells"]]]
                ok = [v for v in ms if v is not None]
                assert (s["wins"], s["losses"], s["lost"]) == (sum(v > 0 for v in ok), sum(v < 0 for v in ok),
                                                                ms.count(None))
                assert s["median"] == (statistics.median(ok) if ok else None)
        # the rules: as the analysis applies them
        for col in [c for c in d["tables"]["oos_rules"]["columns"] if c["fold"] == f]:
            cr = x["criteria"][col["arm"]]
            assert col["cost"]["L-tr"]["wins"] == cr["H1"]["L-tr"]["wins"]
            assert col["worst"]["cells_below_set"] == cr["H2"]["cells_below_set"]
            assert col["notice"]["cells_below_set"] == cr["H2b"]["cells_below_set"]
        # the source sums
        for r in d["tables"]["oos_sources"]["rows"]:
            for arm in ("oos", "is"):
                for m in ("L-tr", "L-vr"):
                    cell = r["cells"][f"{f}|{arm}|{m}"]
                    for s in ("maas", "spot"):
                        want = [sum(int(pc[arm][r["tag"]][str(c)]["sources"][m][s][fld] or 0)
                                    for c in x["cells"] if pc[arm][r["tag"]][str(c)]["sources"][m][s][fld] is not None)
                                for fld in ("violation_slots", "violation_slots_attributable", "reclaims",
                                            "violation_cuts")]
                        assert cell[s] == want, (f, r["tag"], arm, m, s)
    # the data file: one line per fold, arm, tag and cell, with every lender's r0
    e = d["tables"]["oos_runs"]
    rows = list(__import__("csv").reader(e["lines"]))
    modes = an["modes"]
    n = sum(2 * len(x["tags"]) * len(x["cells"]) for x in an["folds"].values())
    assert len(rows) == n == e["n_rows"]
    for r in rows:
        f, arm, t, c = r[0], r[1], r[3], r[4]
        v = an["folds"][f]["per_cell"][arm][t][c]["r0"]
        assert r[6:6 + len(modes)] == ["" if v[m] is None else f"{v[m]:.6f}" for m in modes]


def test_oos_value_oracles():
    check_oos_values(data("sf_oos"), IN_ROOT)


# ---------------------------------------------------------------------------------------------------------------
# every tag, lender and week or cell appears; no design names
def _printed(name: str, d: dict) -> str:
    return "\n".join(tex_of(name, d, t) for t in TABLES[name] if t.endswith(".tex"))


def label_in(text: str, label: str) -> bool:
    """`label` printed whole, or split once at a word break (after ', ' or ' + ', or before ' (') with both parts
    printed (a name over two rows of a table)."""
    if label in text:
        return True
    for sep in (", ", " + ", " ("):
        for m in re.finditer(re.escape(sep), label):
            a, b = label[:m.start() + len(sep)].rstrip(), label[m.end():]
            if sep == " (":
                a, b = label[:m.start()], label[m.start() + 1:]
            if a in text and b in text:
                return True
    return False


def check_full_report(name: str, d: dict) -> None:
    from figs.supp import ms5b_e7_lib as L
    tex = _printed(name, d)
    lines = [ln for t in TABLES[name] if t.endswith(".csv") for ln in d["tables"][t[:-4]]["lines"]]
    rows = list(__import__("csv").reader(lines))
    scopes = [t["scope"] for t in d["tables"].values()]
    tags = {x for s in scopes for x in s.get("tags", [])}
    labels = {L.tex(style.POLICIES[module(name).key_of(t)].label) for t in tags}
    flat = tex.replace("\\raggedright ", "").replace("\\quad ", "")
    for lab in labels:
        assert label_in(flat, lab), lab
    for m in {x for s in scopes for x in s.get("modes", [])}:
        assert m in tex, m
    col = 5 if name == "sf_lag_v2" else 4              # the week (X1) or cell (X2) column of the data file
    want = set(d["a"]["weeks"] if name == "sf_lag_v2" else d["a"]["cells"])
    assert {r[col] for r in rows} == want
    assert {r[1 if name == "sf_lag_v2" else 3] for r in rows} == set(d["tags"])
    printed = re.sub(r"\\label\{[^}]*\}", "", "\n".join(ln for ln in tex.splitlines() if not ln.startswith("%")))
    printed = printed.replace("K0", "")
    assert not DESIGN.search(printed), DESIGN.search(printed)


@pytest.mark.parametrize("name", NAMES)
def test_every_tag_lender_and_column_appears(name):
    check_full_report(name, data(name))


@pytest.mark.parametrize("name", NAMES)
def test_figure_text_is_registry_labels_without_design_names(name):
    """The rows are named by registry labels: sf_oos's by the drawn policy's, sf_lag_v2's (C62) by the policy's with the
    slot revealed, since each row draws the policy lagged and revealed (as built, the lagged policy's label, ", lagged"
    on every row). sf_oos keys its folds in a legend row; sf_lag_v2 (C62) keys (a) and (b) on their letters' baseline,
    no legend row, each key the extract's legend entries of its panel."""
    from figs.supp import ms5b_e7_lib as L
    mod = module(name)
    d = data(name)
    fig = mod.draw(d)
    texts = [t.get_text() for t in style.drawn_texts(fig)]
    assert not any(DESIGN.search(t) for t in texts), texts
    ax = fig._sublet_panels["b"]
    names = [t.get_text() for t in ax.get_yticklabels()]
    if name == "sf_lag_v2":
        rev = {r["tag"]: r["revealed_tag"] for r in d["tables"]["lag_v2_policies"]["rows"]}
        assert names == d["labels"]["rows"] == [style.POLICIES[L.KEY_OF_TAG[rev[t]]].label for t in d["tags"]]
        assert not fig.legends
        keys: dict = {}
        for t in fig.texts:
            if getattr(t, "_sublet_role", "") == "key":
                keys.setdefault(t._sublet_key_of, []).append(t.get_text())
        assert keys == {"(a)": [e[1] for e in d["legend"]["a"]], "(b)": [e[1] for e in d["legend"]["b"]]}
    else:
        assert names == [style.POLICIES[k].label for k in d["rows"]]
        (leg,) = fig.legends
        assert [t.get_text() for t in leg.get_texts()] == [e[1] for e in d["legend"]]
    assert not DESIGN.search(d["labels"]["caption"])


def _rows_panel(values: list[float]):
    """A rows panel of sf_lag_v2's size with one row per value (both series at the value, bars 0.05 to each side) and
    the grey line at 1, drawn by ms7_a_lib.draw_rows; (figure, axes)."""
    from figs.supp import ms7_a_lib as A
    module("sf_lag_v2")                                 # registers the figure's size
    fig = style.new_figure("sf_lag_v2")
    ax = fig.add_axes((0.4, 0.15, 0.3, 0.75))
    rows = [{"key": f"r{i}", **{s: {"median": v, "min": v - 0.05, "max": v + 0.05} for s in ("lagged", "revealed")}}
            for i, v in enumerate(values)]
    ax.set_xlim(0.4, 1.6)
    A.draw_rows(ax, rows, ("lagged", "revealed"), {"lagged": "c", "revealed": "d"}, ref=1.0, xlabel="Cost",
                names=[f"Row {i}" for i in range(len(values))], separators=[])
    return fig, ax


def test_line_label_inside_caps_its_line_clear_of_the_data():
    """C62 fix round (ms7_a_lib.line_label_inside): sf_lag_v2's 'All-fallback' stood above (b) on its key row, right of
    'Revealed slot', and read as a key entry without a sample. It stands inside the rows panel: centered on the grey
    line at its top end, on the first row's name baseline, the line stopping LINE_LABEL_GAP_PT below its ink; where
    data come near, beside the line or at its bottom end; nowhere (the line whole) where every place is taken; always
    LINE_LABEL_CLEAR_PT clear of every median and bar."""
    from figs.supp import ms7_a_lib as A
    for values, place in (([0.6] * 6, ("top", "center")), ([0.9] + [0.6] * 5, ("top", "right")),
                          ([1.0] + [0.6] * 5, ("bottom", "center")), ([1.0] * 6, None)):
        fig, ax = _rows_panel(values)
        t = A.line_label_inside(ax, 1.0, "All-fallback")
        (line,) = [ln for ln in ax.lines if getattr(ln, "_sublet_role", "") == "reference"]
        if place is None:
            assert t is None and list(line.get_ydata()) == [0, 1] and not ax.texts
            continue
        assert t._sublet_place == place and t._sublet_role == "reference_label"
        assert t.get_color() == style.THEORY_LABEL_GREY and t.get_fontsize() == style.TICK_PT
        r = fig.canvas.get_renderer()
        px = fig.dpi / style.BP_PER_IN
        bb, box = t.get_window_extent(r), ax.get_window_extent(r)
        assert box.x0 < bb.x0 and bb.x1 < box.x1 and box.y0 < bb.y0 and bb.y1 < box.y1
        line_x = ax.transData.transform((1.0, 0.0))[0]
        if place[1] == "right":                         # beside the line's end, the line whole
            assert line_x < bb.x0 < line_x + 3.0 * px and list(line.get_ydata()) == [0, 1]
            continue
        assert abs(0.5 * (bb.x0 + bb.x1) - line_x) < 0.5                   # centered on the line
        name = ax.get_yticklabels()[0 if place[0] == "top" else -1]
        assert abs(name.get_window_extent(r).y0 - bb.y0) < 1e-6           # on the row's name baseline (both plain)
        _, _, lp_d = r.get_text_width_height_descent("lp", t.get_fontproperties(), ismath=False)
        lo, hi = A._glyph_span_pt(t.get_text())
        base = bb.y0 + lp_d                                                # the label's baseline
        ink = (bb.x0, base + lo * px, bb.x1, base + hi * px)
        ys = [box.y0 + v * box.height for v in line.get_ydata()]
        gap = A.LINE_LABEL_GAP_PT * px
        if place[0] == "top":
            assert ys[0] == box.y0 and abs(ys[1] - (ink[1] - gap)) < 0.5   # the line stops below the label
        else:
            assert ys[1] == box.y1 and abs(ys[0] - (ink[3] + gap)) < 0.5   # the line starts above the label
        clear = A.LINE_LABEL_CLEAR_PT * px
        for d in A._data_boxes_px(ax):
            assert not (ink[0] - clear < d[2] and d[0] < ink[2] + clear and ink[1] - clear < d[3]
                        and d[1] < ink[3] + clear), d


def test_lag_fallback_label_is_not_on_the_key_row():
    """sf_lag_v2 (C62 fix round): no text on (b)'s key row but the key; the grey line's name, where drawn, is inside
    (b) (ms7_a_lib.line_label_inside), on the fixture."""
    d = data("sf_lag_v2")
    fig = module("sf_lag_v2").draw(d)
    assert not [t for t in fig.texts if t.get_text() == d["labels"]["fallback"]]
    ax = fig._sublet_panels["b"]
    labs = [t for t in ax.texts if t.get_text() == d["labels"]["fallback"]]
    assert all(getattr(t, "_sublet_role", "") == "reference_label" for t in labs) and len(labs) <= 1


# ---------------------------------------------------------------------------------------------------------------
# the checks
@pytest.mark.parametrize("name,missing", [(n, p) for n in NAMES for p in importlib.import_module(SCRIPTS[n]).INPUTS])
def test_missing_input_exits_2(tmp_path, monkeypatch, capsys, name, missing):
    root = copy_tree(tmp_path)
    (root / missing).unlink()
    set_env(monkeypatch, root, tmp_path)
    with pytest.raises(SystemExit) as e:
        module(name).main([])
    assert e.value.code == 2 and missing in capsys.readouterr().err
    assert not (tmp_path / "pdf").exists() and not (tmp_path / "tables").exists()


@pytest.mark.parametrize("name", NAMES)
@pytest.mark.parametrize("unset", ["SUBLET_FIGS_PDF_DIR", "SUBLET_FIGS_OUT_DIR", "SUBLET_FIGS_TABLES_DIR"])
def test_reduced_input_is_never_written_into_the_versioned_folders(tmp_path, monkeypatch, name, unset):
    """Each of the three output folders at its versioned folder: the PDF and extract folders by leaving their variable
    unset, the tables' folder (whose default is SUBLET_FIGS_PDF_DIR while that is set) by setting it there; nothing
    is written, on the build and the --from-extract path."""
    from figs import common
    set_env(monkeypatch, IN_ROOT, tmp_path)
    monkeypatch.delenv(unset)
    if unset == "SUBLET_FIGS_TABLES_DIR":
        monkeypatch.setenv("SUBLET_FIGS_TABLES_DIR", str(common.TABLES_DIR))
    watched = [common.SUPP_PDF_DIR, common.TABLES_DIR, style.DEFAULT_OUT_DIR]
    before = {p: sorted(x.name for x in p.iterdir()) if p.is_dir() else None for p in watched}
    for argv in ([], ["--from-extract", str(FIX / f"{name}.json")]):
        with pytest.raises(SystemExit) as e:
            module(name).main(argv)
        assert "reduced" in str(e.value.code)
    assert {p: sorted(x.name for x in p.iterdir()) if p.is_dir() else None for p in watched} == before
    assert not (tmp_path / "pdf").exists() and not (tmp_path / "out").exists()


def test_stale_inputs_are_refused(tmp_path, monkeypatch):
    root = copy_tree(tmp_path)
    monkeypatch.setenv("SUBLET_FIGS_IN_ROOT", str(root))
    f = root / "code/sim/out/e7c/analysis.json"
    a = jl(f)
    w = a["meta"]["weeks"][0]
    a["per_policy"]["BL2-lag"]["r0"]["weeks"][w] += 0.01
    f.write_text(json.dumps(a))
    with pytest.raises(style.StyleError, match="stale"):
        module("sf_lag_v2").build(Inputs())
    g = root / "code/sim/out/e7o/analysis.json"
    b = jl(g)
    x = b["folds"]["fwd"]
    c = str(x["cells"][0])
    x["oos_minus_is"]["BL1"]["L-tr"][c] += 0.01
    g.write_text(json.dumps(b))
    with pytest.raises(style.StyleError, match="stale"):
        module("sf_oos").build(Inputs())


def test_a_missing_fold_is_named(tmp_path, monkeypatch):
    from figs.common import MissingKey
    root = copy_tree(tmp_path)
    monkeypatch.setenv("SUBLET_FIGS_IN_ROOT", str(root))
    g = root / "code/sim/out/e7o/analysis.json"
    b = jl(g)
    b["folds_found"] = ["fwd"]
    g.write_text(json.dumps(b))
    with pytest.raises(MissingKey, match="rev"):
        module("sf_oos").build(Inputs())


# ---------------------------------------------------------------------------------------------------------------
# the tables compile
def compile_tables(tmp: Path, texts: dict) -> str:
    for n, t in texts.items():
        (tmp / n).write_text(t)
    body = "\n".join(f"\\input{{{n}}}" for n in texts)
    (tmp / "doc.tex").write_text("\\documentclass[lettersize,journal,onecolumn]{IEEEtran}\\usepackage{amsmath}"
                                 "\\usepackage{booktabs}\\usepackage{array}\\usepackage{longtable}\n"
                                 "\\begin{document}\nText.\n" + body + "\n\\end{document}\n")
    env = dict(os.environ, TEXINPUTS=f"{REPO / 'paper'}:")
    for _ in range(3):                                   # longtable settles its column widths over the runs
        r = subprocess.run([str(PDFLATEX), "-interaction=nonstopmode", "-halt-on-error", "doc.tex"], cwd=tmp,
                           capture_output=True, text=True, env=env, timeout=300)
    log = (tmp / "doc.log").read_text(errors="replace")
    assert r.returncode == 0 and "LaTeX Error" not in log, log[-2000:]
    assert "Overfull" not in log, [ln for ln in log.splitlines() if "Overfull" in ln]
    assert "Underfull \\hbox" not in log, [ln for ln in log.splitlines() if "Underfull" in ln]
    return log


@pytest.mark.skipif(not PDFLATEX.is_file(), reason="pdflatex is not installed")
def test_tables_compile_on_the_fixture(tmp_path):
    texts = {t: tex_of(n, data(n), t) for n in NAMES for t in TABLES[n] if t.endswith(".tex")}
    compile_tables(tmp_path, texts)


@pytest.mark.skipif(not PDFLATEX.is_file(), reason="pdflatex is not installed")
def test_tables_compile_at_full_scale(tmp_path, full_out):
    texts = {}
    for n in NAMES:
        _, d, t = full_out[n]
        for x in TABLES[n]:
            if x.endswith(".tex"):
                texts[x] = (t / "tables" / x).read_text()
                assert texts[x].split("\n", 1)[1] == tex_of(n, d, x)
    compile_tables(tmp_path, texts)


# ---------------------------------------------------------------------------------------------------------------
# full scale
@pytest.mark.parametrize("name", NAMES)
def test_full_scale_figure(full_out, full_root, name):
    from figs import fig4_v2 as v2
    rep, d, _ = full_out[name]
    assert rep["outside_page"] == []
    assert rep["text_pt"] and set(rep["text_pt"]) <= {style.TICK_PT, style.LABEL_PT}
    assert d["meta"]["reduced"] is False
    n = 16
    assert len(d["a"]["x"]) == n
    fig = module(name).draw(d)
    for ax, (sub, keys) in zip(fig._sublet_panels["a"], d["a"]["subpanels"]):
        worst = v2.marker_overlaps(ax)
        assert not worst or worst[0]["share"] <= v2.MAX_MARKER_OVERLAP
        shades = sorted(int(p._sublet_column) for p in ax.patches if getattr(p, "_sublet_role", "") == "shade")
        want = sorted(x for i, x in enumerate(d["a"]["x"]) if any(d["a"][k][i] is None or d["a"][k][i] < 0
                                                                   for k in keys))
        assert shades == want == sorted(d["a"]["shaded"][sub]), sub
    missing = sorted({c for v in d["a"]["missing"].values() for c in v}, key=int)
    assert missing and all(c in d["labels"]["caption"] for c in missing)
    rows = [ln._sublet_row for ln in fig._sublet_panels["b"].lines if str(getattr(ln, "_sublet_role", "")).startswith(
        "median:")]
    assert sorted(set(rows)) == sorted(d["rows"])
    assert style.text_overlaps(fig) == []
    if name == "sf_lag_v2":
        check_lag_values(d, full_root)
    else:
        check_oos_values(d, full_root)
    check_full_report(name, d)


def test_full_scale_identity_and_gate_in_the_guard_caption(full_out):
    _, d, t = full_out["sf_lag_v2"]
    g = d["tables"]["lag_v2_guard"]
    assert g["identity"]["n_pairs"] > 0 and g["identity"]["holds"] is True and g["gate"]["pass"] is True
    text = (t / "tables" / "lag_v2_guard.tex").read_text()
    assert f"On the {g['identity']['n_pairs']} runs" in text and f"exactly in {g['identity']['n_exact']}" in text
    assert f"{g['gate']['n_equal']} of {g['gate']['n_checks']} reruns" in text


# ---------------------------------------------------------------------------------------------------------------
# helpers
def test_lib_prose_and_longtable():
    from figs.supp import ms7_a_lib as A
    assert [A.prose(x) for x in ("Greedy renting", "Critical-ratio renting, lagged", "Sublet, lagged",
                                 "RetroRenting-style", "SpotHedge-style", "CoCaR-style", "Per-borrower ski rental",
                                 "MPC")] == ["greedy renting", "critical-ratio renting, lagged", "Sublet, lagged",
                                             "RetroRenting-style", "SpotHedge-style", "CoCaR-style",
                                             "per-borrower ski rental", "MPC"]
    t = A.longtable("ll", "cap", "tab:x", ["a", "b"], [["1", "2"], ["3", "4"], ["5", "6"]], rules=[2],
                    together=[[0, 1]])
    assert "1 & 2 \\tabularnewline*\n3 & 4 \\tabularnewline\n\\midrule\n5 & 6 \\tabularnewline\n" in t
    assert t.count("Table~\\thetable, continued") == 1 and "\\label{tab:x}" in t


# ---------------------------------------------------------------------------------------------------------------
# the rebuild entries (C58)
@pytest.fixture
def registry_without_test_figures(monkeypatch):
    for k in [k for k in style.FIGURES if k.startswith("test_")]:
        monkeypatch.delitem(style.FIGURES, k)


@pytest.mark.parametrize("name", NAMES)
def test_rebuild_entry(registry_without_test_figures, tmp_path, name):
    mod = module(name)
    e = {x.name: x for x in rb.entries()}[name]
    assert e.kind == "supp" and e.script == f"code/sim/figs/supp/{name}.py"
    assert e.outputs == (f"paper/supplement/figures/{name}.pdf", f"code/sim/out/figs/{name}.json",
                         f"code/sim/out/figs/{name}.png") + tuple(f"paper/supplement/tables/{t}" for t in TABLES[name])
    assert e.run_inputs == tuple(mod.RUN_INPUTS) == rb.pending_inputs(e)
    root = tmp_path / "root"
    root.mkdir()
    assert rb.is_pending(root, e)
    for rel in mod.RUN_INPUTS:
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text("{}")
    assert not rb.is_pending(root, e)


# ---------------------------------------------------------------------------------------------------------------
# review of W-G4 A: oracles of the policy and rule tables, the missing-run marks, the registration check and the
# description of the folds' arms
def _desc(vals: list) -> tuple:
    ok = [v for v in vals if v is not None]
    return (statistics.median(ok) if ok else None, min(ok, default=None), max(ok, default=None), vals.count(None))


def _st(s: dict) -> tuple:
    return (s["median"], s["min"], s["max"], s["n_missing"])


def check_lag_policies(d: dict, root: Path) -> None:
    """lag_v2_policies against the summaries by another path than the analysis: r0 under L-tr, W0 over the five
    stress lenders, RC (L-tr minus L-hon), each lagged minus revealed, and the weeks below 1."""
    an, lag, main = _x1_tables(root)
    weeks = [str(w) for w in an["meta"]["weeks"]]
    tabs = {t: (main if an["lag_minus_revealed"][t]["lagged_from"] == "main" else lag)["table"] for t in d["tags"]}

    def metric(table, tag, w, k):
        if k == "r0":
            return _val(table, tag, "L-tr", w)
        if k == "W0":
            ws = [_val(table, tag, m, w) for m in STRESS]
            return None if None in ws else max(ws)
        a, h = _val(table, tag, "L-tr", w), _val(table, tag, "L-hon", w)
        return None if a is None or h is None else a - h

    rows = d["tables"]["lag_v2_policies"]["rows"]
    assert [r["tag"] for r in rows] == d["tags"]
    for r in rows:
        t, rt = r["tag"], r["revealed_tag"]
        assert rt == ({"BL5": "BL5-cur"}.get(t) or t.replace("-lag", "")), t
        for k in ("r0", "W0", "RC"):
            lagged = [metric(tabs[t], t, w, k) for w in weeks]
            revealed = [metric(main["table"], rt, w, k) for w in weeks]
            delta = [None if a is None or b is None else a - b for a, b in zip(lagged, revealed)]
            assert _st(r[k]) == _desc(lagged), (t, k)
            assert _st(r[f"d_{k}"]) == _desc(delta), (t, k)
        for k in ("r0", "W0"):
            vals = [metric(tabs[t], t, w, k) for w in weeks]
            assert r[f"n_{k}_below_1"] == sum(1 for v in vals if v is not None and v < 1), (t, k)


def check_oos_policies_and_rules(d: dict, root: Path) -> None:
    """oos_policies and oos_rules recomputed from the analysis's per-cell r0 (another path than its summaries and
    criteria): every column of every tag per fold, and the confirmation's three rules with ms5b_analysis's thresholds
    (H1: 12 of 16 cells won and a median margin of 0.02, a missing run below every margin; H2: W0 below 1 and below
    every primary baseline in every cell with a median of at most 0.85; H2b: below each notice-aware policy)."""
    an = jl(root / "code" / "sim" / "out" / "e7o" / "analysis.json")
    h1 = an["h1_set"]
    t = d["tables"]["oos_policies"]
    assert t["columns"] == [["r0", "oos", "L-tr"], ["r0", "oos", "L-vr"], ["r0", "oos", "W0"], ["rc", "oos", "L-tr"],
                            ["d", None, "L-tr"], ["d", None, "L-vr"], ["d", None, "W0"]]     # as the head prints them
    assert [b["fold"] for b in t["blocks"]] == ["fwd", "rev"]
    for b in t["blocks"]:
        x = an["folds"][b["fold"]]
        pc, cells = x["per_cell"], [str(c) for c in x["cells"]]

        def r0(arm, tag, c, k):
            e = pc[arm][tag][c]
            return e["W0"] if k == "W0" else e["r0"][k]

        assert sorted(r["tag"] for r in b["rows"]) == sorted(x["tags"]) and b["n_cells"] == len(cells)
        for row in b["rows"]:
            g = row["tag"]
            for (kind, arm, k), st in zip(t["columns"], row["cells"]):
                if kind == "r0":
                    vals = [r0(arm, g, c, k) for c in cells]
                elif kind == "rc":
                    vals = [None if r0(arm, g, c, k) is None or r0(arm, g, c, "L-hon") is None else
                            r0(arm, g, c, k) - r0(arm, g, c, "L-hon") for c in cells]
                else:
                    vals = [None if r0("oos", g, c, k) is None or r0("is", g, c, k) is None else
                            r0("oos", g, c, k) - r0("is", g, c, k) for c in cells]
                    ok = [v for v in vals if v is not None]
                    assert (st["n_neg"], st["n_zero"], st["n_pos"]) == (sum(v < 0 for v in ok), sum(v == 0 for v in ok),
                                                                        sum(v > 0 for v in ok)), (g, kind, k)
                assert _st(st) == _desc(vals), (b["fold"], g, kind, arm, k)
    rules = d["tables"]["oos_rules"]
    th = rules["thresholds"]
    assert (th["H1_wins"], th["H1_median_margin"], th["H2_median_W0"], th["n_cells"]) == (12, 0.02, 0.85, 16)
    for col in rules["columns"]:
        x = an["folds"][col["fold"]]
        pc, cells, arm = x["per_cell"], [str(c) for c in x["cells"]], col["arm"]
        n = len(cells)

        def r0(tag, c, k):
            e = pc[arm][tag][c]
            return e["W0"] if k == "W0" else e["r0"][k]

        for m in ("L-tr", "L-vr"):
            ms = [None if r0("Sublet", c, m) is None or any(r0(h, c, m) is None for h in h1) else
                  min(r0(h, c, m) for h in h1) - r0("Sublet", c, m) for c in cells]
            ok = [v for v in ms if v is not None]
            med = statistics.median([-1e9 if v is None else v for v in ms])
            med = None if abs(med) >= 1e8 else med
            got = col["cost"][m]
            assert (got["wins"], got["n_loss_cells"], got["min_margin"], got["max_margin"], got["median_margin"]) == \
                (sum(v > 0 for v in ok), ms.count(None), min(ok, default=None), max(ok, default=None), med), m
            assert got["holds"] == ((sum(v > 0 for v in ok) >= 12 and med is not None and med >= 0.02) if n == 16
                                    else None)
        w = {c: r0("Sublet", c, "W0") for c in cells}
        below1 = sum(1 for c in cells if w[c] is not None and w[c] < 1)
        below = sum(1 for c in cells if w[c] is not None and all(r0(h, c, "W0") is not None and w[c] < r0(h, c, "W0")
                                                                for h in h1))
        assert (col["worst"]["cells_below_1"], col["worst"]["cells_below_set"]) == (below1, below)
        per = [[g, sum(1 for c in cells if w[c] is not None and r0(g, c, "W0") is not None and w[c] < r0(g, c, "W0"))]
               for g in rules["notice_set"]]
        assert col["notice"]["per_tag"] == per


def test_policy_and_rule_oracles_on_the_fixture():
    check_lag_policies(data("sf_lag_v2"), IN_ROOT)
    check_oos_policies_and_rules(data("sf_oos"), IN_ROOT)


def test_policy_and_rule_oracles_at_full_scale(full_out, full_root):
    check_lag_policies(full_out["sf_lag_v2"][1], full_root)
    check_oos_policies_and_rules(full_out["sf_oos"][1], full_root)


def _marks(tex: str) -> int:
    from figs.supp import ms7_a_lib as A
    body = [ln for ln in tex.splitlines() if not ln.startswith(("%", "\\caption"))]
    return sum(ln.count(A.FEWER_MARK) for ln in body)


def _n_fewer(stats) -> int:
    return sum(1 for s in stats if s.get("median") is not None and (s.get("n_missing") or 0) > 0)


@pytest.mark.parametrize("scale", ["fixture", "full"])
def test_a_median_over_fewer_weeks_or_cells_is_marked(request, scale):
    """Every median that leaves out a missing run carries the mark, and the caption explains it, only then."""
    from figs.supp import ms7_a_lib as A
    if scale == "full":
        out = request.getfixturevalue("full_out")
        dl, do = out["sf_lag_v2"][1], out["sf_oos"][1]
    else:
        dl, do = data("sf_lag_v2"), data("sf_oos")
    want = {"lag_v2_modes": _n_fewer([r["stats"][m] for r in dl["tables"]["lag_v2_modes"]["rows"]
                                      for m in dl["tables"]["lag_v2_modes"]["modes"]]),
            "lag_v2_policies": _n_fewer([r[k] for r in dl["tables"]["lag_v2_policies"]["rows"]
                                         for k in ("r0", "W0", "RC", "d_r0", "d_W0", "d_RC")]),
            "oos_policies": _n_fewer([s for b in do["tables"]["oos_policies"]["blocks"] for r in b["rows"]
                                      for s in r["cells"]])}
    for table, n in want.items():
        name, d = ("sf_lag_v2", dl) if table.startswith("lag") else ("sf_oos", do)
        tex = tex_of(name, d, f"{table}.tex")
        cap = next(ln for ln in tex.splitlines() if ln.startswith("\\caption"))
        assert _marks(tex) == n, table
        assert (A.FEWER_MARK in cap) == (n > 0), table
    if scale == "full":                 # the stand-ins' missing runs: CoCaR-style, lagged, and CoCaR-style, under L-co
        assert all(n > 0 for n in want.values())


def test_full_runs_must_be_the_registered_analysis(full_root, tmp_path, monkeypatch):
    """sf_lag_v2 refuses an analysis of full runs whose sha256 is not the registered one or whose weeks are not the
    confirmation weeks; reduced inputs (the fixture tree) pass."""
    for key, value in (("registration", {"matches": False, "registered_sha256": "0" * 64}),
                       ("weeks_are_confirmation_weeks", False)):
        root = tmp_path / key
        shutil.copytree(full_root, root)
        f = root / "code/sim/out/e7c/analysis.json"
        a = jl(f)
        a["meta"][key] = value if key != "registration" else {**a["meta"]["registration"], **value}
        f.write_text(json.dumps(a))
        monkeypatch.setenv("SUBLET_FIGS_IN_ROOT", str(root))
        with pytest.raises(style.StyleError, match="registered analysis"):
            module("sf_lag_v2").build(Inputs())
    monkeypatch.setenv("SUBLET_FIGS_IN_ROOT", str(IN_ROOT))
    assert module("sf_lag_v2").build(Inputs())["meta"]["reduced"] is True


def test_full_runs_must_be_the_full_design(full_root, tmp_path, monkeypatch):
    """sf_oos refuses folds of full runs without the design's 16 cells or 15 tags; reduced folds pass."""
    for what in ("cells", "tags"):
        root = tmp_path / what
        shutil.copytree(full_root, root)
        f = root / "code/sim/out/e7o/analysis.json"
        a = jl(f)
        x = a["folds"]["rev"]
        x[what] = x[what][:-1]
        f.write_text(json.dumps(a))
        monkeypatch.setenv("SUBLET_FIGS_IN_ROOT", str(root))
        with pytest.raises(style.StyleError, match="full design"):
            module("sf_oos").build(Inputs())
    monkeypatch.setenv("SUBLET_FIGS_IN_ROOT", str(IN_ROOT))
    assert module("sf_oos").build(Inputs())["meta"]["reduced"] is True


def test_the_captions_describe_the_arms_as_built():
    """The in-sample twin calibrates every lender on its whole series (sublet.experiments.e7o: arm 'is' sets no
    calib_slots), and the out-of-sample arm calibrates the spot lenders on the first weeks of their series
    (e7o.SPOT_CALIB) in both folds; no caption says the in-sample lenders are calibrated on the evaluated window."""
    from sublet.experiments import e7o
    mod = module("sf_oos")
    w = e7o.SLACK_SLOTS_PER_WEEK
    assert mod.spot_window() == {"calib_weeks": f"{e7o.SPOT_CALIB[0] // w + 1}–{e7o.SPOT_CALIB[1] // w}",
                                 "block_h": round(e7o.SPOT_BLOCK_SLOTS * 7 * 24 / w)} == \
        {"calib_weeks": "1–12", "block_h": 72}
    d = data("sf_oos")
    texts = [d["labels"]["caption"]] + [tex_of("sf_oos", d, f"{t}.tex") for t in ("oos_margins", "oos_policies")]
    for text in texts:
        assert "calibrated on its whole series, the evaluated window included" in text
        assert "spot lenders calibrated on weeks 1" in text
        assert "calibrated on the evaluated window" not in text
