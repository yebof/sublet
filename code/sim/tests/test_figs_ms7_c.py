"""Tests of the supplementary figures and tables of X3, Sublet's own sensitivity and fidelity studies
(design/ms7/registration.md §2-§3; design/ms7/w_spec.md §4, unit W-G4, writer C; change C58): figs/supp/sf_s1_v2.py,
sf_e5_v2.py, sf_e8_v2.py and sf_e9_v2.py with their shared helpers figs/supp/ms7_x3_lib.py.

Quick. The inputs are the input tree tests/fixtures_figs_ms7/g4c/inputs/ (reduced-mode outputs of the X3 drivers,
trimmed, and the frozen analysis run on them; README there) and the fixture extracts tests/fixtures_figs_ms7/g4c/
<name>.json (what each script writes on that tree; refresh_extracts.py there); every file is written under pytest's
tmp_path. The real-scale tests run on stand-ins (tests/fixtures_figs_ms7/g4c/standins.py: made-up numbers at the
registered grids, in tmp_path only) through the frozen analysis.

- Registration (writer C's block of figs/style.py): each figure's size and set, the script's KEYS, RUN_INPUTS (MS7 run
  outputs only, the analysis first) and TABLES (the tables and one CSV data file); the rebuild entry of each script
  (its tables and data file among the outputs, its RUN_INPUTS as run inputs, pending in a tree without them).
- Each script on the fixtures: build() gives the fixture extract's data and records only its RUN_INPUTS as sources;
  --from-extract rewrites the extract, the tables and the data file byte for byte (and the build from the inputs writes
  the same tables), a second redraw gives the same PDF bytes, finalize() passes at C62's text sizes; a missing input
  exits 2 with the file named; reduced input is never written into paper/ or code/sim/out/; a non-reduced analysis that
  is not the registered one on full runs, a summary that the analysis did not read and an analysis that records no input
  are refused.
- Reported in full: every point, setting, cell, policy, lender, week, config seed and alignment of the inputs appears
  in the tables or the data file; the plotted and tabulated values are the analysis's (value oracles, with medians
  recomputed by statistics.median; on the fixtures and, in the real-scale test, on the stand-ins' four weeks, config
  seeds and alignments, where a median differs from a minimum).
- Printed text: registry labels only, no design ID or tag in the captions, the tables or the figure's texts.
- Real scale (stand-ins): each script saves with finalize() passing on a non-reduced, registered analysis, and its
  tables compile in the supplement's class without an overfull box or an error.
"""
from __future__ import annotations

import csv
import importlib
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

NAMES = ("sf_s1_v2", "sf_e5_v2", "sf_e8_v2", "sf_e9_v2")
FIX = Path(__file__).resolve().parent / "fixtures_figs_ms7" / "g4c"
IN_ROOT = FIX / "inputs"
OUT = IN_ROOT / "code" / "sim" / "out"
REPO = style.REPO
PDFLATEX = Path.home() / ".local" / "bin" / "pdflatex"
# C62: sf_e8_v2 at 2.5 in (2.2 as built at 9 pt), for nearly square scatter panels
SIZES = {"sf_s1_v2": ("W2", 2.5), "sf_e5_v2": ("W2", 2.5), "sf_e8_v2": ("W2", 2.5), "sf_e9_v2": ("W2", 2.2)}
EXP = {"sf_s1_v2": "s1v2", "sf_e5_v2": "e5v2", "sf_e8_v2": "e8v2", "sf_e9_v2": "e9v2"}
STALE = ("tests/fixtures_figs_ms7/g4c/{name}.json is stale (the script's data changed): refresh it with "
         "`python tests/fixtures_figs_ms7/g4c/refresh_extracts.py --only {name}` from code/sim")
# design IDs and tags that the printed text never carries (lender names such as L-tr, L-rf are the paper's)
DESIGN = re.compile(r"\b(BL\d|A\d\b|A9|A6|X\d|H\d|MS\d|S1\b|E5\b|E8\b|E9\b|T0)|Sublet-|\bc2\b|-(T|W)\b|kstar|BO\b|"
                    r"\bcur\b|e7[fr]_|_V\d")

pytestmark = pytest.mark.filterwarnings("ignore::figs.style.GlyphSizeWarning")


def mod(name: str):
    return importlib.import_module(f"figs.supp.{name}")


def jl(p: Path):
    return json.loads(Path(p).read_text())


def fixture_payload(name: str) -> dict:
    return jl(FIX / f"{name}.json")


def standins():
    sys.path.insert(0, str(FIX))
    try:
        return importlib.import_module("standins")
    finally:
        sys.path.remove(str(FIX))


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
@pytest.mark.parametrize("name", NAMES)
def test_registration(name):
    m = mod(name)
    spec = style.FIGURES[name]
    assert (spec.width, spec.height_in, spec.main) == (*SIZES[name], False)
    assert tuple(m.KEYS) == style.SUPP_POLICIES_MS7[name]
    style.check_policies(m.KEYS)
    mf = [(style.POLICIES[k].marker, style.POLICIES[k].fill) for k in m.KEYS]
    assert len(set(mf)) == len(mf)
    assert m.NAME == name and m.INPUTS == m.RUN_INPUTS and m.RUN_INPUTS[0] == f"code/sim/out/{EXP[name]}/analysis.json"
    assert all(p.startswith(f"code/sim/out/{EXP[name]}/") for p in m.RUN_INPUTS)
    assert all(p.startswith(rb.MS7_RUN_DIRS) for p in m.RUN_INPUTS)
    assert [t.rsplit(".", 1)[1] for t in m.TABLES] == ["tex"] * (len(m.TABLES) - 1) + ["csv"]
    for k in m.KEYS:                                     # every drawn key is a registry key with a label
        assert style.POLICIES[k].label and not DESIGN.search(style.POLICIES[k].label), k


@pytest.mark.parametrize("name", NAMES)
def test_rebuild_entry_pending_until_the_runs(name, registry_without_test_figures, tmp_path):
    m = mod(name)
    e = {x.name: x for x in rb.entries()}[name]
    assert (e.kind, e.script, e.module) == ("supp", f"code/sim/figs/supp/{name}.py", f"figs.supp.{name}")
    assert e.outputs == (f"paper/supplement/figures/{name}.pdf", f"code/sim/out/figs/{name}.json",
                         f"code/sim/out/figs/{name}.png") + tuple(f"paper/supplement/tables/{t}" for t in m.TABLES)
    assert e.run_inputs == tuple(m.RUN_INPUTS) and rb.pending_inputs(e) == tuple(m.RUN_INPUTS)
    root = tmp_path / "root"
    root.mkdir()
    assert rb.is_pending(root, e) and rb.coverage(root, [e])["pending"] == [name]
    for rel in m.RUN_INPUTS[:-1]:
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text("{}")
    assert rb.is_pending(root, e)                         # one run input still missing
    (root / m.RUN_INPUTS[-1]).parent.mkdir(parents=True, exist_ok=True)
    (root / m.RUN_INPUTS[-1]).write_text("{}")
    assert not rb.is_pending(root, e) and rb.coverage(root, [e])["missing"] == sorted(e.outputs)


# ---------------------------------------------------------------------------------------------------------------
# The scripts on the fixtures
@pytest.mark.parametrize("name", NAMES)
def test_build_matches_fixture(name, env):
    m = mod(name)
    inp = Inputs()
    data = json.loads(json.dumps(m.build(inp), allow_nan=False))
    assert data == fixture_payload(name)["data"], STALE.format(name=name)
    assert sorted(inp.sources) == sorted(m.RUN_INPUTS)
    assert data["meta"]["reduced"] is True and data["meta"]["analysis"]["registered_full_inputs"] is False
    assert data["headline"] == jl(OUT / EXP[name] / "analysis.json")["headline"]
    assert data["labels"]["caption"] and data["labels"]["values"]


@pytest.mark.parametrize("name", NAMES)
def test_from_extract_rewrites_every_output_byte_for_byte(name, env):
    m = mod(name)
    rep = m.main(["--from-extract", str(FIX / f"{name}.json")])
    spec = style.figure_spec(name)
    assert abs(rep["width_bp"] - spec.width_in * 72) <= 0.5 and abs(rep["height_bp"] - spec.height_in * 72) <= 0.5
    assert rep["pages"] == 1 and rep["outside_page"] == []
    assert rep["text_pt"] and set(rep["text_pt"]) <= {style.TICK_PT, style.LABEL_PT}
    assert rep["min_glyph_pt"] >= style.SCRIPT_MIN_PT - 1e-6
    assert not any("dejavu" in f.lower() for f in rep["fonts"])
    assert jl(env / "out" / f"{name}.json") == fixture_payload(name)
    first = {t: (env / "tables" / t).read_bytes() for t in m.TABLES}
    pdf1 = Path(rep["pdf"]).read_bytes()
    # a redraw from the written extract: the same PDF, extract and tables
    for t in m.TABLES:
        (env / "tables" / t).unlink()
    rep2 = m.main(["--from-extract", str(env / "out" / f"{name}.json")])
    assert Path(rep2["pdf"]).read_bytes() == pdf1
    assert {t: (env / "tables" / t).read_bytes() for t in m.TABLES} == first
    # the build from the inputs writes the same tables and data file
    for t in m.TABLES:
        (env / "tables" / t).unlink()
    m.main([])
    assert {t: (env / "tables" / t).read_bytes() for t in m.TABLES} == first
    csv_entry = next(v for v in fixture_payload(name)["data"]["tables"].values()
                     if isinstance(v, dict) and v.get("file") == m.TABLES[-1])
    assert __import__("hashlib").sha256(first[m.TABLES[-1]]).hexdigest() == csv_entry["sha256"]
    for t in m.TABLES[:-1]:
        text = first[t].decode()
        assert text.startswith(f"% Written by code/sim/figs/supp/{name}.py") and r"\begin{longtable}" in text


def _copy_tree(tmp_path: Path) -> Path:
    root = tmp_path / "tree"
    shutil.copytree(IN_ROOT, root)
    return root


@pytest.mark.parametrize("name,i", [(n, i) for n in NAMES for i in range(len(mod(n).RUN_INPUTS))])
def test_missing_input_exits_2(name, i, tmp_path, monkeypatch, capsys):
    m = mod(name)
    root = _copy_tree(tmp_path)
    (root / m.RUN_INPUTS[i]).unlink()
    monkeypatch.setenv("SUBLET_FIGS_IN_ROOT", str(root))
    monkeypatch.setenv(style.ENV_PDF_DIR, str(tmp_path / "pdf"))
    monkeypatch.setenv(style.ENV_OUT_DIR, str(tmp_path / "out"))
    with pytest.raises(SystemExit) as e:
        m.main([])
    assert e.value.code == 2
    err = capsys.readouterr().err
    assert m.RUN_INPUTS[i] in err and "MS7 run output" in err
    assert not (tmp_path / "pdf").exists() and not (tmp_path / "out").exists()


@pytest.mark.parametrize("name", NAMES)
def test_reduced_input_is_never_written_into_versioned_folders(name, tmp_path, monkeypatch):
    m = mod(name)
    watched = [REPO / "paper" / "supplement" / "figures", REPO / "paper" / "supplement" / "tables",
               style.DEFAULT_OUT_DIR]
    before = {d: sorted((p.name, p.stat().st_mtime_ns) for p in d.iterdir()) for d in watched}
    monkeypatch.setenv("SUBLET_FIGS_IN_ROOT", str(IN_ROOT))
    for k in (style.ENV_PDF_DIR, style.ENV_OUT_DIR, "SUBLET_FIGS_TABLES_DIR"):
        monkeypatch.delenv(k, raising=False)
    for argv in ([], ["--from-extract", str(FIX / f"{name}.json")]):
        with pytest.raises(SystemExit, match="reduced"):
            m.main(argv)
    # the PDF and the tables redirected, the extract not: still refused (stage 3's review: one folder is not enough)
    monkeypatch.setenv(style.ENV_PDF_DIR, str(tmp_path / "pdf"))
    with pytest.raises(SystemExit, match="reduced"):
        m.main(["--from-extract", str(FIX / f"{name}.json")])
    # a scratch folder inside code/sim/out/ is refused too
    monkeypatch.setenv(style.ENV_OUT_DIR, str(REPO / "code" / "sim" / "out" / "scratch_g4c"))
    with pytest.raises(SystemExit, match="reduced"):
        m.main(["--from-extract", str(FIX / f"{name}.json")])
    assert not (REPO / "code" / "sim" / "out" / "scratch_g4c").exists() and not (tmp_path / "pdf").exists()
    assert {d: sorted((p.name, p.stat().st_mtime_ns) for p in d.iterdir()) for d in watched} == before


@pytest.mark.parametrize("name", NAMES)
def test_unregistered_or_inconsistent_analysis_is_refused(name, tmp_path, monkeypatch):
    m = mod(name)
    monkeypatch.setenv(style.ENV_PDF_DIR, str(tmp_path / "pdf"))
    monkeypatch.setenv(style.ENV_OUT_DIR, str(tmp_path / "out"))
    root = _copy_tree(tmp_path)
    monkeypatch.setenv("SUBLET_FIGS_IN_ROOT", str(root))
    ap = root / m.RUN_INPUTS[0]
    a = jl(ap)
    # a full analysis that is not the registered one on full runs
    full = json.loads(json.dumps(a))
    full["meta"]["reduced"] = False
    for x in full["meta"]["input_records"]:
        x["reduced"] = False
    ap.write_text(json.dumps(full))
    with pytest.raises(style.StyleError, match="not a registered analysis"):
        m.build(Inputs())
    # a summary that the analysis did not read
    ap.write_text(json.dumps(a))
    s = root / m.RUN_INPUTS[1]
    s.write_text(s.read_text() + " ")
    with pytest.raises(style.StyleError, match="not the summary that the analysis read"):
        m.build(Inputs())
    # review: an analysis that records no input summary at all (so none that the script reads)
    s.write_text(s.read_text()[:-1])
    none = json.loads(json.dumps(a))
    none["meta"]["input_records"] = []
    ap.write_text(json.dumps(none))
    with pytest.raises(style.StyleError, match="records no sha256"):
        m.build(Inputs())


# ---------------------------------------------------------------------------------------------------------------
# Reported in full, and the values (each check runs on the fixture extract and, in test_real_scale, on the stand-ins'
# build, whose four weeks, config seeds and alignments tell a median from a minimum)
def _csv_rows(name: str, d: dict | None = None) -> list[dict]:
    m = mod(name)
    d = fixture_payload(name)["data"] if d is None else d
    e = next(v for v in d["tables"].values() if isinstance(v, dict) and v.get("file") == m.TABLES[-1])
    text = m.X.csv_text(e["columns"], e["rows"])
    return list(csv.DictReader(io.StringIO(text)))


def test_s1v2_reported_in_full_and_values():
    check_s1v2(fixture_payload("sf_s1_v2")["data"], OUT)


def check_s1v2(d: dict, out: Path) -> None:
    m = mod("sf_s1_v2")
    a = jl(out / "s1v2" / "analysis.json")
    w0s = jl(out / "s1v2" / "w0" / "summary.json")
    rows = _csv_rows("sf_s1_v2", d)
    # every setting and policy of every week, as the analysis has them
    got = {(r["setting_id"], r["tag"], r["week"], r["metric"], r["lender"]) for r in rows}
    for n, e in a["points"].items():
        for t in m.TAGS4:
            for w in e["by_tag"][t]["r0"]:
                assert (n, t, w, "r0", m._lender_of(n, a)) in got, (n, t, w)
    for t, by_m in w0s["table"].items():
        for md, by_p in by_m.items():
            for n, by_w in by_p.items():
                for w in by_w:
                    assert (n, t, w, "r0", md) in got, (t, md, n, w)
    for n, e in a["w0"]["points"].items():
        for t in m.W0_TAGS:
            for w in e["W0"][t]:
                assert any(r["setting_id"] == n and r["tag"] == t and r["week"] == w and r["metric"] == "W0"
                           for r in rows), (n, t, w)
    assert {r["point"] for r in d["tables"]["points"]} == set(a["points"])
    assert [r["point"] for r in d["tables"]["w0"]["rows"]] == ["default"] + [n for n in a["w0"]["points"]
                                                                             if n != "default"]
    assert {r["tag"] for r in d["tables"]["seeds"]["rows"]} == set(a["seed_spread"]["by_tag"])
    # every register row is drawn, in its panel, with the analysis's bar ends and its settings' medians
    assert sorted(i for p in m.PANELS for i in d["panels"][p]) == sorted(a["rows"])
    for rid, r in d["rows"].items():
        assert (r["lo"], r["hi"], r["span"]) == (a["rows"][rid].get("lo"), a["rows"][rid].get("hi"),
                                                 a["rows"][rid].get("span")), rid
        for q in r["points"]:
            e = a["points"][q["name"]]
            assert q["median"] == e["by_tag"]["Sublet"]["median_saving_pct"]
            assert q["holds"] == (e["vs_pair"]["weeks_hold"] == e["vs_pair"]["n_weeks"] > 0)
    assert d["default_saving_pct"] == a["points"]["default"]["by_tag"]["Sublet"]["median_saving_pct"]
    for t in d["tables"]["points"]:
        e = a["points"][t["point"]]
        assert t["delta_median"] == e["vs_pair"]["delta_median"] and t["weeks_hold"] == e["vs_pair"]["weeks_hold"]
        assert t["guard_r0"] == e["sublet_minus_a9_r0"]["median"]
        sv = [v for v in e["by_tag"]["Sublet"]["saving_pct"].values() if v is not None]
        assert (t["sublet_lo"], t["sublet_hi"]) == ((min(sv), max(sv)) if sv else (None, None))
    # the W0 table: each tag's median W0 over the weeks (an independent median)
    for r in d["tables"]["w0"]["rows"]:
        e = a["w0"]["points"][r["point"]]
        for t in m.W0_TAGS:
            v = [x for x in e["W0"][t].values() if x is not None]
            assert r["median"][t] == (statistics.median(v) if v else None), (r["point"], t)
        assert r["weeks_hold"] == e["weeks_hold"]


def test_s1v2_price_defaults_at_three_decimals():
    """C59 (RC18(1)): the points table prints the defaults of alpha and alpha_p at three decimals, as Section V and the
    supplement's register table do: the prices of the week instance's config (a11_calibration.json inputs.alpha and
    inputs.alpha_p) rounded, where the driver's register types them at two decimals."""
    m = mod("sf_s1_v2")
    cal = jl(REPO / "code" / "analysis" / "out" / "a11_calibration.json")["inputs"]
    assert m.DEFAULT_TEXT == {"alpha": format(cal["alpha"], ".3f"), "alpha_p": format(cal["alpha_p"], ".3f")}
    d = fixture_payload("sf_s1_v2")["data"]
    for rid, txt in m.DEFAULT_TEXT.items():
        if rid in d["rows"]:
            assert d["rows"][rid]["default"]["label"] == txt
            assert all(t["default_setting"] == txt for t in d["tables"]["points"] if t["row"] == rid)


def test_e8v2_ranked_caption_counts_the_alignments():
    """C59 (RC18(5)): the tiers table's caption says what the Ranked column counts, of how many alignments."""
    m = mod("sf_e8_v2")
    d = fixture_payload("sf_e8_v2")["data"]
    n = len(d["grid"].get("alignments") or [])
    tex = m.tiers_tex(d["tables"]["tiers"], d)
    assert (f"Ranked, the alignments in which all four of Sublet, critical-ratio renting, RetroRenting-style and "
            f"Greedy, back-off have a cost, of {n};") in tex


def test_e5v2_reported_in_full_and_values():
    check_e5v2(fixture_payload("sf_e5_v2")["data"], OUT)


def check_e5v2(d: dict, out: Path) -> None:
    m = mod("sf_e5_v2")
    a = jl(out / "e5v2" / "analysis.json")
    rows = _csv_rows("sf_e5_v2", d)
    cells = {(lv, mn, mk) for lv, x in a["cells"].items() for mn, y in x.items() for mk in y}
    assert {(r["level"], r["menu"], r["mu"]) for r in d["tables"]["cells"]} == cells
    got = {(r["level"], r["menu"], float(r["mu_over_beta"]), r["tag"], r["config_seed"]) for r in rows}
    for lv, mn, mk in cells:
        for t, b in a["cells"][lv][mn][mk]["by_tag"].items():
            for c in b["r0"]:
                assert (lv, mn, float(mk), t, c) in got
    for p, mn in (("a", "short"), ("b", "long")):
        for t, s in d["panels"][p]["series"].items():
            for i, lv in enumerate(m.LEVELS):
                b = (a["cells"].get(lv, {}).get(mn, {}).get("1", {}).get("by_tag") or {}).get(t) or {}
                assert s["median"][i] == b.get("median_r0")
                vals = [v for v in (b.get("r0") or {}).values() if v is not None]
                assert (s["lo"][i], s["hi"][i]) == ((min(vals), max(vals)) if vals else (None, None))
    # the tables: each cell's savings, margins and the spares' effect as the analysis has them
    for r in d["tables"]["cells"]:
        e = a["cells"][r["level"]][r["menu"]][r["mu"]]
        assert r["saving"] == {t: (e["by_tag"].get(t) or {}).get("median_saving_pct") for t in m.TAGS}
        assert r["pair"]["delta_median"] == e["vs_pair"]["delta_median"]
        assert r["all"]["weeks_hold"] == e["vs_baselines"]["weeks_hold"]
        sp = e.get("bl3_spares_r0")
        assert (r["spares"] or {}).get("median") == (sp or {}).get("median")
        sv = [v for v in ((e["by_tag"].get("Sublet") or {}).get("saving_pct") or {}).values() if v is not None]
        assert (r["sublet_lo"], r["sublet_hi"]) == ((min(sv), max(sv)) if sv else (None, None))


def test_e8v2_reported_in_full_and_values():
    check_e8v2(fixture_payload("sf_e8_v2")["data"], OUT)


def check_e8v2(d: dict, out: Path) -> None:
    m = mod("sf_e8_v2")
    a = jl(out / "e8v2" / "analysis.json")
    rows = _csv_rows("sf_e8_v2", d)
    assert {(r["tier"], r["window"]) for r in d["tables"]["tiers"]} == \
        {(t, w) for t, x in a["by_tier_window"].items() for w in x}
    assert {(r["window"], r["prefix"]) for r in d["tables"]["mooncake"]} == \
        {(w, pf) for w, x in a["mooncake"].items() for pf in x}
    n_inst = sum(len(z) for x in a["cells"].values() for z in x.values())
    n_mc = sum(len(x) for x in a["mooncake"].values())
    assert len(rows) == (n_inst + n_mc) * len(m.TAGS) and {r["tag"] for r in rows} == set(m.TAGS)
    for tier, x in a["cells"].items():
        for w, y in x.items():
            for c, e in y.items():
                for t in m.OTHERS:
                    pts = [q for q in d["panels"]["a"]["points"][t] if (q["tier"], q["window"], q["alignment"])
                           == (tier, w, c)]
                    fl, rp = e["fluid"], e["replay"]
                    if None in (fl.get(t), fl.get("Sublet"), rp.get(t), rp.get("Sublet")):
                        assert not pts
                        continue
                    (q,) = pts
                    assert q["x"] == fl[t] / fl["Sublet"] and q["y"] == rp[t] / rp["Sublet"]
    for r in d["tables"]["tiers"]:
        x = a["by_tier_window"][r["tier"]][r["window"]]
        assert (r["n"], r["same_order"], r["sublet_beats_pair_replay"]) == (x["n"], x["same_order"],
                                                                           x["sublet_beats_pair_replay"])
        assert r["E_median"] == {t: x["E_median"].get(t) for t in m.TAGS}


def test_e9v2_reported_in_full_and_values():
    check_e9v2(fixture_payload("sf_e9_v2")["data"], OUT)


def check_e9v2(d: dict, out: Path) -> None:
    m = mod("sf_e9_v2")
    a = jl(out / "e9v2" / "analysis.json")
    rows = _csv_rows("sf_e9_v2", d)
    assert {r["point"] for r in d["tables"]["overhead"]} == set(a["points"])
    assert {r["point"] for r in d["tables"]["split"]} == {p for p, e in a["points"].items() if e.get("split")}
    want = {(p, c, t) for p, e in a["points"].items() for c in e["by_alignment"] for t in m.TAGS}
    assert {(r["point"], r["alignment"], r["tag"]) for r in rows} == want
    for p in ("a", "b"):
        s = d["panels"][p]
        for i, pt in enumerate(s["points"]):
            by = a["points"][pt]["by_alignment"]
            for t in m.TAGS:
                vals = sorted(v["act_s_per_slot"][t] for v in by.values() if v["act_s_per_slot"][t] is not None)
                assert s["series"][t]["median"][i] == (statistics.median(vals) if vals else None)
                assert (s["series"][t]["lo"][i], s["series"][t]["hi"][i]) == ((vals[0], vals[-1]) if vals
                                                                              else (None, None))
    for r in d["tables"]["overhead"]:
        e = a["points"][r["point"]]
        assert r["overhead"]["median"] == e["act_overhead_s_per_slot_median"] and r["ratio_median"] == \
            e["act_ratio_median"]
        for t in m.TAGS:
            vals = [v["act_s_per_slot"][t] for v in e["by_alignment"].values() if v["act_s_per_slot"][t] is not None]
            assert r["act"][t]["median"] == (statistics.median(vals) if vals else None), (r["point"], t)
    for i, pt in enumerate(d["panels"]["c"]["points"]):
        sp = a["points"][pt]["split"]
        assert sp["identical"] is True
        assert {k: d["panels"]["c"]["parts"][k][i] for k in m.PARTS} == {k: sp["per_slot_mean_s"][k] for k in m.PARTS}


# ---------------------------------------------------------------------------------------------------------------
# Printed text
@pytest.mark.parametrize("name", NAMES)
def test_printed_text_has_no_design_names(name, env):
    m = mod(name)
    d = fixture_payload(name)["data"]
    assert not DESIGN.search(d["labels"]["caption"]), d["labels"]["caption"]
    m.main(["--from-extract", str(FIX / f"{name}.json")])
    for t in m.TABLES[:-1]:
        body = "\n".join(ln for ln in (env / "tables" / t).read_text().splitlines() if not ln.startswith("%"))
        hit = DESIGN.search(body.replace(r"\label{", "").replace("tab:s-", "").replace("fig:s-", ""))
        assert not hit, (t, hit.group(0), body[max(0, hit.start() - 80):hit.end() + 40])
    fig = m.draw(d)
    texts = [t.get_text() for t in style.drawn_texts(fig)]
    assert not [t for t in texts if DESIGN.search(t)], texts
    labels = {style.POLICIES[k].label for k in m.KEYS}
    leg = [t.get_text() for lg in fig.legends + [ax.get_legend() for ax in fig.axes if ax.get_legend()]
           for t in lg.get_texts()]
    assert not [x for x in leg if x not in labels and name != "sf_s1_v2"], leg


# ---------------------------------------------------------------------------------------------------------------
# Real scale (stand-ins in tmp_path only)
@pytest.fixture(scope="module")
def real_root(tmp_path_factory):
    return standins().standin_tree(tmp_path_factory.mktemp("g4c_real"))


CHECKS = {"sf_s1_v2": check_s1v2, "sf_e5_v2": check_e5v2, "sf_e8_v2": check_e8v2, "sf_e9_v2": check_e9v2}
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


@pytest.mark.parametrize("name", NAMES)
def test_real_scale(name, real_root, tmp_path, monkeypatch):
    m = mod(name)
    monkeypatch.setenv("SUBLET_FIGS_IN_ROOT", str(real_root))
    monkeypatch.setenv(style.ENV_PDF_DIR, str(tmp_path / "pdf"))
    monkeypatch.setenv(style.ENV_OUT_DIR, str(tmp_path / "out"))
    monkeypatch.setenv("SUBLET_FIGS_TABLES_DIR", str(tmp_path / "tables"))
    rep = m.main([])
    assert rep["outside_page"] == []
    assert rep["text_pt"] and set(rep["text_pt"]) <= {style.TICK_PT, style.LABEL_PT}
    d = jl(tmp_path / "out" / f"{name}.json")["data"]
    assert d["meta"]["reduced"] is False and d["meta"]["analysis"]["registered_full_inputs"] is True
    if name == "sf_s1_v2":
        assert d["layout"]["legend"]["mode"] == "panel" and len(d["weeks"]) == 4
        assert sum(len(v) for v in d["panels"].values()) == len(d["rows"]) == 28
    if name == "sf_e9_v2":
        assert len(d["panels"]["a"]["points"]) == len(d["panels"]["b"]["points"]) == 7
    # review: the value checks at four weeks, config seeds or alignments, where a median differs from a minimum
    CHECKS[name](d, real_root / "code" / "sim" / "out")
    if not PDFLATEX.is_file():
        pytest.skip(f"{PDFLATEX} is not installed")
    shutil.copy(REPO / "paper" / "IEEEtran.cls", tmp_path / "tables" / "IEEEtran.cls")
    doc = PREAMBLE + "".join(f"\\input{{{t}}}\n" for t in m.TABLES[:-1]) + "\\end{document}\n"
    (tmp_path / "tables" / "doc.tex").write_text(doc)
    r = subprocess.run([str(PDFLATEX), "-interaction=nonstopmode", "-halt-on-error", "doc.tex"],
                       cwd=tmp_path / "tables", capture_output=True, text=True, timeout=300,
                       env=dict(os.environ, TEXINPUTS=f"{tmp_path / 'tables'}:"))
    log = (tmp_path / "tables" / "doc.log").read_text(errors="replace")
    assert r.returncode == 0, log[-2000:]
    assert "Overfull" not in log and "LaTeX Error" not in log, [ln for ln in log.splitlines() if "Overfull" in ln]
