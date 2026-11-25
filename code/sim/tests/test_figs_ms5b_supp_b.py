"""Tests of the MS5b supplementary figure scripts of unit U39b (design/sublet_v2.md §11, W3, W4, W7, W9, W10, W13):
figs/supp/sf_e3_v2.py, sf_e7_grid_dev.py, sf_fam_v2.py and sf_e7_links.py with their tables e3_v2.tex, e7v2_grid.tex,
e7v2_q44.tex, fam_v2_pairs.tex, fam_v2_f3.tex and fam_v2_q6.tex. Quick: no raw data, no run outputs. The inputs are the
input tree tests/fixtures_figs_ms5b/inputs/ (reduced-mode outputs of the confirmation parts, and the two trimmed copies
of E11's summary and MS4's E7 main summary that tests/fixtures_figs_ms5b/trim_inputs.py writes; README there) and the
fixture extracts tests/fixtures_figs_ms5b/<name>.json (refresh_extracts.py); every file is written under pytest's
tmp_path (never into paper/ or code/sim/out/). The reduced summaries carry no real values, so the oracles recompute
each plotted or tabled value from the summaries by another path than the scripts take.

- Each script redraws with --from-extract from its fixture extract under temporary SUBLET_FIGS_*_DIR, finalize()
  passing at its registered size (C41), writes the extract it read and its tables; the common --from-extract option.
- Each script builds from the input tree the data of its fixture extract, opens nothing outside the input root's result
  folders (patched open), records only result files as sources and reads no runs/ file (meta.runs_files empty, W10);
  meta.reduced comes from the summaries; every table of TABLES has its entry with its file and scope in `tables`.
- The keys drawn are the figure's set in style.SUPP_POLICIES_MS5B (sf_e7_grid_dev's set changed by U39b to the seven
  keys it draws), pass check_policies, and include no legacy key (check_legacy).
- Value oracles: sf_e3_v2 against e3.<cell>.ratios, the brackets and analysis.json's H5; sf_e7_grid_dev against the
  grid summary's `table` and `W0` blocks and E11's D2; sf_fam_v2 against total / opt of the runs, fam.pairs and
  analysis.json's H4; sf_e7_links against MS4's links and runs.1.
- The tables hold every row and column of their scope, and compile with booktabs and array in an IEEEtran page with no
  overfull box (pdflatex, if installed), at the fixture's width and widened to the confirmation's grid.

C50 (design/ms6_spec.md §7.2, the D5 review; §7.1 D4's script items): the captions print the paper's words for the
project names (the pilot's runs, the single-LLM family, the reduced menu), and e3_v2's says that the main text claims
no measured sharing gain for any policy. Each changed line names C50.
"""
from __future__ import annotations

import builtins
import copy
import importlib
import io
import json
import os
import statistics
import subprocess
from pathlib import Path

import numpy as np
import pytest

from figs import style
from figs.inputs import Inputs

FIX = Path(__file__).resolve().parent / "fixtures_figs_ms5b"
IN_ROOT = FIX / "inputs"
OUT = IN_ROOT / "code" / "sim" / "out"
SCRIPTS = {"sf_e3_v2": "figs.supp.sf_e3_v2", "sf_e7_grid_dev": "figs.supp.sf_e7_grid_dev",
           "sf_fam_v2": "figs.supp.sf_fam_v2", "sf_e7_links": "figs.supp.sf_e7_links"}
NAMES = sorted(SCRIPTS)
SIZES = {"sf_e3_v2": ("W2", 2.2), "sf_e7_grid_dev": ("W2", 2.4), "sf_fam_v2": ("W2", 2.2), "sf_e7_links": ("W1", 2.2)}
TABLES = {"sf_e3_v2": ("e3_v2.tex",), "sf_e7_grid_dev": ("e7v2_grid.tex", "e7v2_q44.tex"),
          "sf_fam_v2": ("fam_v2_pairs.tex", "fam_v2_f3.tex", "fam_v2_q6.tex"), "sf_e7_links": ()}
STALE = ("tests/fixtures_figs_ms5b/{}.json is stale (the script's data changed): refresh it with "
         "`python tests/fixtures_figs_ms5b/refresh_extracts.py --only {}` from code/sim")
PDFLATEX = Path.home() / ".local/bin/pdflatex"
GRID_KEYS = ("sublet_v2", "bl1_gp", "bl1_g1", "bl5_g1", "a9", "bl5_lag", "bl1")      # U39b's set of sf_e7_grid_dev
STRESS = {"L-eg", "L-ss", "L-iid-0.05", "L-iid-0.2", "L-co"}                       # q44_study.MODES' stress modes

pytestmark = pytest.mark.filterwarnings("ignore::figs.style.GlyphSizeWarning")


def module(name):
    return importlib.import_module(SCRIPTS[name])


def payload(name):
    return json.loads((FIX / f"{name}.json").read_text())


def fdata(name):
    return payload(name)["data"]


def tree(rel: str):
    return json.loads((OUT / rel).read_text())


def drawn_keys(fig) -> set:
    return {getattr(a, "_sublet_policy") for ax in fig.axes for a in ax.get_children() if hasattr(a, "_sublet_policy")}


@pytest.fixture
def figs_env(tmp_path, monkeypatch):
    monkeypatch.setenv("SUBLET_FIGS_IN_ROOT", str(IN_ROOT))
    monkeypatch.setenv(style.ENV_PDF_DIR, str(tmp_path / "pdf"))
    monkeypatch.setenv(style.ENV_OUT_DIR, str(tmp_path / "out"))
    monkeypatch.setenv("SUBLET_FIGS_TABLES_DIR", str(tmp_path / "tables"))
    return tmp_path


# ---------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("name", NAMES)
def test_from_extract_saves_and_finalize_passes(figs_env, name):
    """--from-extract on the fixture extract: save() under the temporary folders (finalize() passed), the registered
    size, 9-10 pt text, no DejaVu font, the extract written equals the one read, and the figure's tables written."""
    rep = module(name).main(["--from-extract", str(FIX / f"{name}.json")])
    spec = style.figure_spec(name)
    assert (spec.width, spec.height_in, spec.main) == (*SIZES[name], False)
    assert Path(rep["pdf"]) == figs_env / "pdf" / f"{name}.pdf" and Path(rep["pdf"]).is_file()
    assert abs(rep["width_bp"] - spec.width_in * 72) <= 0.5 and abs(rep["height_bp"] - spec.height_in * 72) <= 0.5
    assert rep["outside_page"] == [] and rep["pages"] == 1
    assert all(style.TEXT_MIN_PT <= s <= style.TEXT_MAX_PT for s in rep["text_pt"])
    assert not any("dejavu" in f.lower() for f in rep["fonts"])
    assert json.loads((figs_env / "out" / f"{name}.json").read_text()) == payload(name)
    tables = figs_env / "tables"
    written = sorted(p.name for p in tables.iterdir()) if tables.is_dir() else []
    assert written == sorted(TABLES[name])
    assert tuple(module(name).TABLES if TABLES[name] else ()) == TABLES[name]


@pytest.mark.parametrize("name", NAMES)
def test_every_script_has_the_common_from_extract_option(name, monkeypatch):
    """figs.common.cli: --from-extract without an argument reads the figure's own extract through Inputs.extract,
    with a path that file."""
    from figs import common, inputs

    class Stop(Exception):
        pass

    calls = []

    def fake_read_extract(n, path=None):
        calls.append((n, path))
        raise Stop

    def fake_extract(self, n):
        calls.append((n, "Inputs.extract"))
        raise Stop

    mod = module(name)
    assert mod.main.__module__ == mod.__name__ and mod.cli is common.cli and mod.NAME == name
    monkeypatch.setattr(inputs.Inputs, "extract", fake_extract)
    with pytest.raises(Stop):
        mod.main(["--from-extract"])
    monkeypatch.setattr(common, "read_extract", fake_read_extract)
    with pytest.raises(Stop):
        mod.main(["--from-extract", "some/extract.json"])
    assert calls == [(name, "Inputs.extract"), (name, "some/extract.json")]


@pytest.mark.parametrize("name", NAMES)
def test_build_on_the_input_tree_matches_the_fixture(figs_env, monkeypatch, name):
    """build() on the input tree opens no repository file outside the result folders of the input root (patched open)
    and no runs/ file, records only result files as sources, takes meta.reduced from the summaries, lists every table
    with its file and scope, and gives the fixture extract's data."""
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
    data = module(name).build(inp)
    monkeypatch.undo()
    for p in opened:
        if style.REPO in p.parents:
            assert IN_ROOT in p.parents, f"{name} opened {p}"
            rel = p.relative_to(IN_ROOT).as_posix()
            style.check_source(rel)
            assert "/runs/" not in rel, f"{name} read the run file {rel} (W10: list it with its sha256)"
    assert opened and all(style.check_source(s) == s for s in inp.sources)
    from figs.common import json_number
    data = json.loads(json.dumps(data, allow_nan=False, default=json_number))
    assert data == fdata(name), STALE.format(name, name)
    assert payload(name)["sources"] == inp.sources == data["meta"]["sources"]
    assert data["meta"]["runs_files"] == [] and data["meta"]["reduced"] is True
    assert isinstance(data["labels"]["caption"], str) and data["labels"]["caption"]
    for f in TABLES[name]:
        ent = data["tables"][f.removesuffix(".tex")]
        assert ent["file"] == f and isinstance(ent["scope"], dict) and ent["scope"], (name, f)


@pytest.mark.parametrize("name", NAMES)
def test_registry_keys_and_policy_checks(name):
    """The keys drawn are the figure's set (C41; sf_e7_grid_dev's as U39b changed it) and its KEYS, pass
    check_policies, and include no legacy key; every legend entry has a label."""
    mod = module(name)
    fig = mod.draw(fdata(name))
    keys = drawn_keys(fig)
    assert tuple(mod.KEYS) == style.SUPP_POLICIES_MS5B[name]
    assert keys == set(style.SUPP_POLICIES_MS5B[name]), keys
    style.check_policies(keys)
    assert not keys & set(style.LEGACY_KEYS) and keys <= set(style.MS5B_KEYS) | {"opt", "bl1"}
    style.check_legacy({name: tuple(keys)})
    for leg in fig.legends + [ax.get_legend() for ax in fig.axes if ax.get_legend() is not None]:
        assert all(t.get_text() for t in leg.get_texts())


def test_grid_dev_set_is_the_seven_keys_drawn():
    """U39b's change of C41's set: the seven keys in legend order, no (marker, fill) twice, E11's guarded rows in."""
    keys = style.SUPP_POLICIES_MS5B["sf_e7_grid_dev"]
    assert keys == GRID_KEYS == tuple(style.legend_order(keys))
    mf = [(style.POLICIES[k].marker, style.POLICIES[k].fill) for k in keys]
    assert len(set(mf)) == len(mf)
    assert {"bl1_g1", "bl5_g1", "bl5_lag"} <= set(keys) and not {"a7", "a7_guard"} & set(keys)


# ---------------------------------------------------------------------------------------------------------------
# value oracles
def test_e3_values_against_the_summary_and_h5():
    """Every point is the median over the seeds of e3.<cell>.ratios.<tag>:<mode> with its interval around it; the
    brackets the median point with the extreme ends; H5's rows equal analysis.json's (clause (ii) untested at b = 1);
    u and mu from the manifest; Sublet siloed drawn with its registry key, the others in the sharing line style."""
    from figs.supp import sf_e3_v2 as m
    d = fdata("sf_e3_v2")
    e3, an = tree("sublet_v2/e3/summary.json"), tree("sublet_v2/analysis.json")
    cells = e3["e3"]
    bs = sorted({int(c.split(":")[0][1:]) for c in cells})
    seeds = sorted({int(c.split(":")[1][1:]) for c in cells})
    assert d["grid"]["b"] == bs and d["grid"]["seeds"] == seeds
    jobs = [j["params"] for j in tree("sublet_v2/e3/manifest.json")["jobs"] if j["params"].get("kind") == "e3cell"]
    assert {(j["u"], j["mu"]) for j in jobs} == {(d["grid"]["u"], d["grid"]["mu"])}
    for mode in m.MODES:
        for tag, key in m.TAG_KEY.items():
            s = d["panels"][mode][key]
            for i, b in enumerate(bs):
                vals = [cells[f"b{b}:c{c}"]["ratios"][f"{tag}:{mode}"] for c in seeds]
                assert s["median"][i] == pytest.approx(statistics.median(vals), rel=1e-12)
                assert s["ci_lo"][i] <= s["median"][i] <= s["ci_hi"][i]
                assert min(vals) <= s["ci_lo"][i] and s["ci_hi"][i] <= max(vals)
    for i, b in enumerate(bs):
        br = [cells[f"b{b}:c{c}"]["bracket"] for c in seeds]
        assert d["opt"]["point"][i] == pytest.approx(statistics.median([x["point"] for x in br]))
        assert d["opt"]["lo"][i] == min(x["lo"] for x in br) and d["opt"]["hi"][i] == max(x["hi"] for x in br)
    rows = {r["b"]: r for r in an["H5"]["b"]}
    for r in d["h5"]["rows"]:
        assert r["le_MS4"] == rows[r["b"]]["le_MS4"]
        assert r["shared_below_siloed"] == (None if r["b"] < 2 else rows[r["b"]]["shared_below_siloed"])
        assert r["Sublet_shared"] == pytest.approx(d["panels"]["shared"]["sublet_v2"]["median"][bs.index(r["b"])])
    assert d["h5"]["pass"] == an["H5"]["pass"] and d["h5"]["kind"] == an["H5"]["kind"]
    assert m.key_of("sublet_v2", "siloed") == ("sublet_v2_siloed", ("sharing", "siloed"))
    assert m.key_of("bl1", "siloed") == ("bl1", ("sharing", "siloed")) and m.key_of("bl1", "shared") == ("bl1", None)
    fig = m.draw(d)
    ax_b = fig.axes[1]
    dashed = {getattr(ln, "_sublet_policy") for ln in ax_b.lines
              if hasattr(ln, "_sublet_policy") and ln.get_linestyle() == "--"}
    assert dashed == {"sublet_v2_siloed", "sublet_ms4", "a9", "bl5_cur", "bl1"}
    assert any(getattr(t, "_sublet_role", "").startswith("theory_label") for t in ax_b.texts)


def test_grid_dev_values_against_the_table_block_and_e11():
    """(a) the median over the seeds of the summary's table.<tag>.L-tr.<alignment> with the seeds' range; the grid
    table's W0 the median of W0.<seed>.<tag>.<alignment>; Q44 by Q44's definitions recomputed from the table block
    (seed means, medians over the cells, the largest over the stress modes); E11's rows equal its D2; criteria S and
    T as stated."""
    from figs.supp import sf_e7_grid_dev as m
    d = fdata("sf_e7_grid_dev")
    s, e11 = tree("sublet_v2/grid/summary.json"), tree("e11/summary.json")
    tab = s["table"]
    als = d["a"]["alignments"]
    assert als == sorted({r["cell"] for r in s["runs"] if r["kind"] == "week"})
    for tag in m.A_TAGS:
        ser = d["a"]["series"][m.GRID_KEY[tag]]
        for i, c in enumerate(als):
            v = list(tab[tag]["L-tr"][c].values())
            assert ser["median"][i] == pytest.approx(float(np.median(v))) and (ser["lo"][i], ser["hi"][i]) == \
                (min(v), max(v))
    gt = d["tables"]["e7v2_grid"]
    rows = gt["rows"]
    assert list(rows) == [t for t in m.GRID_KEY if t in s["meta"]["tags"]] == gt["scope"]["tags"]
    stress = [mo for mo in ("L-eg", "L-ss", "L-iid-0.05", "L-iid-0.2", "L-co")
              if any(r["kind"] == "week" and r["mode"] == mo for r in s["runs"])]
    assert gt["stress_modes"] == stress
    spread = []
    for tag, r in rows.items():
        for c, w in r["W0"].items():
            vals = [by[tag][c] for by in s["W0"].values() if tag in by and by[tag].get(c) is not None]
            assert w["median"] == (pytest.approx(float(np.median(vals))) if vals else None)
            per = {mo: list(tab[tag][mo][c].values()) for mo in stress if c in tab[tag].get(mo, {})}
            for mo in stress:
                got = r["stress"][c][mo]
                assert got["median"] == (pytest.approx(float(np.median(per[mo]))) if mo in per else None)
            if len(per) == len(stress):        # W0 is the largest stress r0 of each seed (summary W0 block)
                for seed, by in s["W0"].items():
                    if by.get(tag, {}).get(c) is not None:
                        assert by[tag][c] == pytest.approx(max(tab[tag][mo][c][seed] for mo in stress))
        for c, p in r["r0"].items():
            if p["n"] > 1:
                spread.append(p["hi"] - p["lo"])
        spread += [q["hi"] - q["lo"] for by in r["stress"].values() for q in by.values() if q["n"] > 1]
    assert gt["seed_range"]["max"] == (pytest.approx(max(spread)) if spread else None)
    gap_cells = sorted({r["cell"] for r in s["runs"] if r["kind"] == "gap"})
    assert sorted(gt["scope"]["gap_cells"]) == gap_cells and set(gap_cells) <= set(gt["scope"]["cells"])
    q = d["q44"]
    y = e11["D4"]["thresholds"]["y_S"]
    assert q["y_S"] == y
    for tag in m.Q_GRID_TAGS:
        ser = q["series"][m.GRID_KEY[tag]]
        for i, inst in enumerate(q["instances"]):
            by_mode = {}
            for mode, cells in tab[tag].items():
                vals = [statistics.fmean(v.values()) for c, v in cells.items() if c.startswith(inst + ":")]
                if vals:
                    by_mode[mode] = statistics.median(vals)
            assert ser["r0_tr"][i] == pytest.approx(by_mode["L-tr"])
            w = [v for mo, v in by_mode.items() if mo in STRESS]
            assert ser["W0"][i] == (pytest.approx(max(w)) if w else None)
        w0s = ser["W0"]
        assert ser["S"] == (None if any(v is None for v in w0s) else all(v <= 1 + y for v in w0s))
    for tag, key in m.E11_KEY.items():
        ser = q["series"][key]
        assert ser["source"] == "e11"
        for i, inst in enumerate(q["instances"]):
            assert ser["r0_tr"][i] == e11["D2"][inst]["modes"]["L-tr"]["r0"][tag]["median"]
            assert ser["W0"][i] == e11["D2"][inst]["W0"][tag]["W0"]
    assert "not computable" in q["criterion_T"] and "Criterion T is not computable" in d["labels"]["caption"]
    assert "development-exposed" in d["labels"]["caption"]


def test_fam_values_against_the_runs_pairs_and_h4():
    """Instance values the mean of total / opt over the seeds; (a)'s groups the families F1, F2 by lender; the pairs
    table equals fam.pairs grouped, its counted total analysis.json's; F3's overall means analysis.json's; the Q6
    table the Q6 instances under F-ad and F-eg; equal pairs only where every instance agrees."""
    from figs.supp import sf_fam_v2 as m
    d = fdata("sf_fam_v2")
    fam, an = tree("sublet_v2/fam/summary.json"), tree("sublet_v2/analysis.json")
    runs = [r for r in fam["runs"] if r["kind"] == "fam"]
    mean = {}
    for r in runs:
        mean.setdefault((r["fam"], r["inst"], r["mode"], r["tag"]), []).append(r["total"] / r["opt"])
    groups = [(g["fam"], g["mode"]) for g in d["a"]["groups"]]
    assert groups == sorted({(f, mo) for f, _, mo, _ in mean if f in ("F1", "F2")},
                            key=lambda g: (g[0], m.LENDERS.index(g[1])))
    for tag, key in m.TAG_KEY.items():
        for i, (f, mo) in enumerate(groups):
            vals = [statistics.fmean(v) for (ff, _, mm, t), v in mean.items() if (ff, mm, t) == (f, mo, tag)]
            got = d["a"]["series"][key]
            assert got["median"][i] == (pytest.approx(statistics.median(vals)) if vals else None)
            assert got["n"][i] == len(vals)
    pt = d["tables"]["fam_v2_pairs"]
    assert sum(r["pairs"] for r in pt["rows"]) == len(fam["fam"]["pairs"])
    assert pt["counted_pairs"] == an["H4"]["n_counted_pairs"] and pt["pass"] == an["H4"]["pass"]
    f3 = d["tables"]["fam_v2_f3"]
    for t, o in f3["overall"].items():
        assert o["mean"] == pytest.approx(an["H4"]["f3_ratio_opt"][t]["mean"]) and o["n"] == \
            an["H4"]["f3_ratio_opt"][t]["n"]
    q6 = d["tables"]["fam_v2_q6"]
    assert {r["inst"] for r in q6["rows"]} == {r["inst"] for r in runs if r["src"].startswith("F")
                                               and r["mode"] in ("F-ad", "F-eg")}
    ran = {r["tag"] for r in runs if r["src"].startswith("F") and r["mode"] in ("F-ad", "F-eg")}
    assert set(q6["tags"]) == ran & set(m.TABLE_TAGS) and {"RR_RENEW", "MARKING"} & ran <= set(q6["tags"])
    assert not {"rr_renew", "marking"} & set(m.KEYS)              # tables only (C41's color rule)
    for p, pairs in d["equal"].items():
        for a, b in pairs:
            ia, ib = d[p]["series"][a]["instances"], d[p]["series"][b]["instances"]
            assert all(x.get(n) == pytest.approx(y.get(n), rel=1e-12) for x, y in zip(ia, ib) for n in x)
    assert m.equal_classes([["a9", "a9_noins"], ["sublet_v2", "a9"], ["bl1_gp", "bl1_g1"]]) == \
        [["sublet_v2", "a9", "a9_noins"], ["bl1_gp", "bl1_g1"]]


def test_links_values_against_ms4_and_the_tag_check(figs_env, tmp_path, monkeypatch):
    """Each point is MS4's saving_pct median with its interval (links.<n>, runs.1 for the main grid's n); the MS5b
    keys are checked against MS4's legacy style keys and B0 rule, so a summary whose tags or allowance differ raises."""
    from figs.common import MissingKey
    from figs.supp import sf_e7_links as m
    d = fdata("sf_e7_links")
    e7 = tree("e7/main/summary.json")
    for key, (tag, _) in m.TAGS.items():
        s = d["series"][key]
        for i, n in enumerate(s["links"]):
            nk = format(float(n), "g")
            blk = e7["links"][nk][tag] if nk in e7["links"] else e7["runs"]["1"][tag]
            assert s["median"][i] == blk["saving_pct"]["median"]
            assert [s["ci_lo"][i], s["ci_hi"][i]] == blk["saving_pct"]["median_ci95"]
    assert m.short_label("sublet_ms4") + " (" in style.POLICIES["sublet_ms4"].label and "(" not in \
        m.short_label("sublet_ms4") and m.short_label("bl1") == style.POLICIES["bl1"].label
    root = tmp_path / "in"
    (root / "code/sim/out/e7/main").mkdir(parents=True)
    bad = copy.deepcopy(e7)
    bad["meta"]["tags"]["BL5"]["style_key"] = "bl5_cur"
    (root / "code/sim/out/e7/main/summary.json").write_text(json.dumps(bad))
    monkeypatch.setenv("SUBLET_FIGS_IN_ROOT", str(root))
    with pytest.raises(MissingKey, match="style_key"):
        m.build(Inputs())
    bad = copy.deepcopy(e7)
    bad["meta"]["B0_rule"] = "auto"
    (root / "code/sim/out/e7/main/summary.json").write_text(json.dumps(bad))
    with pytest.raises(style.StyleError, match="B0_rule"):
        m.build(Inputs())


def _listed(scope: dict, keys) -> set:
    """The values a scope lists under `keys` (lists, and a mapping's keys and values), as strings."""
    out = set()

    def walk(x):
        if isinstance(x, dict):
            for k, v in x.items():
                out.add(str(k))
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
        else:
            out.add(str(x))
    for k in keys:
        walk(scope.get(k, []))
    return out


def test_table_scopes_cover_the_summaries_runs():
    """Each table's scope lists what the claims report (W11, R rows) checks it against, read here from the summaries'
    runs: E3's tags, modes and cells b<b>:c<c>; the grid's week and gap runs' tags, modes, cells and seeds; the Q44
    runs' tags and cells; the Q6 runs under F-ad and F-eg with their seeds; F3's tags and instances; the pairs'
    families and lenders."""
    def runs_of(part, pred):
        return [r for r in tree(f"sublet_v2/{part}/summary.json")["runs"] if pred(r)]

    def need(runs, sc, dims):
        for dim, (field, keys) in dims.items():
            want = {str(r[field]) for r in runs}
            assert want and want <= _listed(sc, keys), (dim, sorted(want - _listed(sc, keys)))

    e3 = fdata("sf_e3_v2")["tables"]["e3_v2"]["scope"]
    need(runs_of("e3", lambda r: r.get("kind") == "e3cell"), e3,
         {"tags": ("tag", ["tags"]), "modes": ("mode", ["modes"]), "cells": ("cell", ["cells"])})
    g = fdata("sf_e7_grid_dev")["tables"]
    need(runs_of("grid", lambda r: r.get("kind") in ("week", "gap")), g["e7v2_grid"]["scope"],
         {"tags": ("tag", ["tags"]), "modes": ("mode", ["modes"]), "cells": ("cell", ["cells"]),
          "seeds": ("seed", ["seeds"])})
    need(runs_of("grid", lambda r: r.get("kind") == "q44"), g["e7v2_q44"]["scope"],
         {"tags": ("tag", ["tags"]), "cells": ("cell", ["cells"])})
    f = fdata("sf_fam_v2")["tables"]
    q6 = runs_of("fam", lambda r: r.get("kind") == "fam" and r["src"].startswith("F") and r["mode"] in ("F-ad", "F-eg"))
    need(q6, f["fam_v2_q6"]["scope"], {"tags": ("tag", ["tags"]), "modes": ("mode", ["modes"]),
                                       "instances": ("inst", ["instances"]), "seeds": ("seed", ["seeds"])})
    need(runs_of("fam", lambda r: r.get("kind") == "fam" and r["fam"] == "F3"), f["fam_v2_f3"]["scope"],
         {"tags": ("tag", ["tags"]), "instances": ("inst", ["instances"]), "modes": ("mode", ["modes"])})
    pairs = tree("sublet_v2/fam/summary.json")["fam"]["pairs"]
    need(pairs, f["fam_v2_pairs"]["scope"], {"families": ("fam", ["families"]), "modes": ("mode", ["modes"])})


# ---------------------------------------------------------------------------------------------------------------
# the print check's fixes (2026-11-03)
def test_e3_interval_is_called_the_range_only_where_it_is_and_opt_is_labeled_directly():
    """bootstrap.ci_equals_range is true iff every interval is the seeds' range; the caption and the table name the
    second number by it; no caption says 'Sublet-MS4'; the stars carry the direct label 'Siloed / shared OPT' and the
    legend row no OPT entry; the caption copies the copy bound's scope and status."""
    from figs.supp import sf_e3_v2 as m
    d = fdata("sf_e3_v2")
    cells = [(s["ci_lo"][i], s["ci_hi"][i], s["values"][i]) for p in d["panels"].values() for s in p.values()
             for i in range(len(d["grid"]["b"])) if s["values"][i]]
    assert d["bootstrap"]["ci_equals_range"] == all(lo == min(v) and hi == max(v) for lo, hi, v in cells)
    cap = d["labels"]["caption"]
    assert m.interval_text(d) in cap and "Sublet-MS4" not in cap and "attained on C3-P7's instance" in cap
    assert f"({m.COPY_STATUS})" in cap and "every one is in Table e3_v2" in cap
    other = copy.deepcopy(d)
    other["bootstrap"]["ci_equals_range"] = False
    assert "range" not in m.interval_text(other) and "95% interval" in m.interval_text(other)
    assert m.split_label("A (b)") == ("A", "(b)") and m.split_label("A") == ("A", "")
    fig = m.draw(d)
    leg = fig.legends[0]
    assert "OPT" not in " ".join(t.get_text() for t in leg.get_texts())
    assert [t.get_text() for t in fig.axes[1].texts if getattr(t, "_sublet_role", "") == "direct_label"] == \
        [m.LABELS["opt"]]


def test_grid_dev_dodge_order_seeds_aborts_and_t_column(tmp_path, monkeypatch):
    """The dodge slots follow the legend's order; the grid table's caption names the tags with other seed sets, the
    tags whose seeds agree everywhere and the tags that abort in every run, from the extract (no fixed 'seed 0 only'
    sentence), and a dash sentence only where a cell is '--'; e7v2_q44.tex has a T column with E11's own verdicts for
    E11's rows and a dash for part grid's."""
    from figs.supp import sf_e7_grid_dev as m
    assert list(m.A_SLOTS) == style.legend_order(m.A_SLOTS) and list(m.Q_SLOTS) == style.legend_order(m.Q_SLOTS)
    g = fdata("sf_e7_grid_dev")
    e11 = tree("e11/summary.json")
    for tag, key in m.E11_KEY.items():
        assert g["q44"]["series"][key]["T_e11"] == e11["D4"]["criteria"][tag]["T"]
    tt = _tables_of("sf_e7_grid_dev", g, tmp_path, monkeypatch)
    q44 = tt["e7v2_q44.tex"]
    for key, s in g["q44"]["series"].items():
        t_cell = m._s_text(s["T_e11"]) if s["source"] == "e11" else "--"
        assert f" & {m._s_text(s['S'])} & {t_cell} \\\\" in q44, key
    grid = tt["e7v2_grid.tex"]
    assert "without random draws" not in grid and ("A dash marks" in grid) == (" & -- " in grid)
    t = g["tables"]["e7v2_grid"]
    name = {tag: m.tex_label(style.POLICIES[t["rows"][tag]["key"]].label) for tag in t["tags"]}
    for tag, a in t["aborts"].items():
        if a["runs"] and a["aborted"] == a["runs"]:
            assert f"{name[tag]} aborts in every one of its {a['runs']} grid runs" in grid
    # seed sets: a synthetic table with three seeds, two tags on seed 0 only, one tag equal over its seeds
    syn = copy.deepcopy(t)
    tags = list(syn["tags"])[:4]
    syn["tags"], syn["seeds"] = tags, [0, 1, 2]
    syn["seed_sets"] = {tags[0]: [0, 1, 2], tags[1]: [0], tags[2]: [0], tags[3]: [0, 1, 2]}
    for tag in tags:
        for c, p in syn["rows"][tag]["r0"].items():
            same = tag == tags[0]
            syn["rows"][tag]["r0"][c] = {"median": 1.0, "lo": 1.0, "hi": 1.0 if same else 1.1,
                                         "n": 3 if tag in (tags[0], tags[3]) else 1}
        syn["rows"][tag]["stress"] = {}
    txt = m.seeds_text(syn, name)
    assert f"Two tags ran policy seed 0 only: {name[tags[1]]}; {name[tags[2]]}." in txt
    assert f"Equal over the policy seeds in every entry: {name[tags[0]]}." in txt and name[tags[3]] not in txt
    # the figure caption names (a)'s tags with fewer policy seeds (re-review of 2026-11-03), and only those
    gg = copy.deepcopy(g)
    gt = gg["tables"]["e7v2_grid"]
    gt["seeds"] = [0, 1, 2]
    gt["seed_sets"] = {tag: ([0] if tag == "A9" else [0, 1, 2]) for tag in m.A_TAGS}
    cap = m.caption(gg)
    assert f"; {style.POLICIES['a9'].label} ran policy seed 0 only." in cap
    gt["seed_sets"]["A9"] = [0, 1, 2]
    assert "only." not in m.caption(gg).split(" (b), (c)")[0]


def test_fam_dodge_order_captions_and_tables(tmp_path, monkeypatch):
    """The dodge slots follow the legend's order; the caption gives the guarded policies' F3 aborts; the pairs table
    centers its Counted column; the F3 table names no file in its caption; the Q6 table decodes the instance ids and
    explains a dash only where a cell has none."""
    from figs.supp import sf_fam_v2 as m
    assert list(m.SLOTS) == style.legend_order(m.SLOTS) and m.DRAW == tuple(reversed(m.SLOTS))
    f = fdata("sf_fam_v2")
    ov = f["tables"]["fam_v2_f3"]["overall"]
    for t, o in ov.items():
        if o.get("aborts") is not None:
            assert f"{style.POLICIES[m.TAG_KEY[t]].label} " in f["labels"]["caption"]
            assert f"{o['aborts']} of " in f["labels"]["caption"]
    ft = _tables_of("sf_fam_v2", f, tmp_path, monkeypatch)
    assert r"\begin{tabular}{@{}lllrrrcr@{}}" in ft["fam_v2_pairs.tex"]
    assert "analysis.json" not in ft["fam_v2_f3.tex"].split("\n", 1)[1]
    q6 = ft["fam_v2_q6.tex"]
    has_dash = any(c is None for r in f["tables"]["fam_v2_q6"]["rows"] for c in r["cells"].values())
    assert ("A dash marks a policy that did not run" in q6) == has_dash
    assert "An instance id gives its parameters" in q6
    # C50 (D5 review; D4's script items): the paper's words for P3 and the T4/O1 family in the captions
    assert "P3" not in ft["fam_v2_pairs.tex"] + q6 and "T4/O1" not in q6                               # C50
    assert "repeat the pilot's runs" in q6                                                            # C50
    q6t = copy.deepcopy(f["tables"]["fam_v2_q6"])                                                     # C50
    q6t["rows"] = [{**r, "fam": "F3", "cells": {tg: (None if tg in m.ONE_CONTRACT else {"mean": 1.0, "n": 1})
                                                for tg in r["cells"]}} for r in q6t["rows"][:1]]        # C50
    if any(tg in m.ONE_CONTRACT for tg in q6t["tags"]):                                                 # C50
        assert "the one revocable contract of the single-LLM family" in m.q6_dashes(q6t)               # C50
    # the ids in the caption are set upright, not in the caption's small capitals (re-review of 2026-11-03)
    assert r"e.g. \textnormal{" in m.q6_ids(f["tables"]["fam_v2_q6"])
    rows = copy.deepcopy(f["tables"]["fam_v2_q6"])
    for r in rows["rows"]:
        r["cells"] = {tg: (c or {"mean": 1.0, "n": 1}) for tg, c in r["cells"].items()}
    assert m.q6_dashes(rows) == ""


def test_links_direct_labels_without_key(monkeypatch):
    """No key on the panel: the series are labeled directly, one label for sublet_ms4 and the lagged BL5 where they
    agree and one each where they do not, with the provenance label; the y range is not given headroom for a key."""
    from figs.supp import sf_e7_links as m
    d = fdata("sf_e7_links")
    for agree in (None, {"pair": ["sublet_ms4", "bl5_lag"], "within_pct": 0, "max_rel_diff": 0.0, "key": "k"}):
        dd = copy.deepcopy(d)
        dd["agree"] = agree
        specs = m.label_specs(dd)
        assert len(specs) == (2 if agree else 3)
        fig = m.draw(dd)
        (ax,) = fig.axes
        assert ax.get_legend() is None and not fig.legends
        got = [t.get_text() for t in ax.texts if getattr(t, "_sublet_role", "") == "direct_label"]
        assert got == [s for s, _ in specs] + [m.LABELS["key_title"]]
    assert "Sublet-MS4" not in d["labels"]["caption"]
    dd = copy.deepcopy(d)
    dd["agree"] = {"pair": ["sublet_ms4", "bl5_lag"], "within_pct": 0, "max_rel_diff": 0.0, "key": "k"}
    assert m.caption(dd).endswith(" Their medians are equal at every number of cross-region links.")
    assert "every n." not in m.caption(dd)


# ---------------------------------------------------------------------------------------------------------------
# tables
def _tables_of(name: str, data: dict, tmp_path: Path, monkeypatch) -> dict:
    """{file: text} of the tables that `name`'s after hook writes from `data` (under tmp_path)."""
    d = tmp_path / name
    d.mkdir(exist_ok=True)
    with monkeypatch.context() as mp:
        mp.setenv("SUBLET_FIGS_TABLES_DIR", str(d))
        module(name).write_tables(data, {})
    return {p.name: p.read_text() for p in d.iterdir()}


def test_tables_hold_every_row_of_their_scope(tmp_path, monkeypatch):
    """Every tag, mode, b, alignment, instance and group of a table's scope has its row or column, with the extract's
    values; each table starts with its provenance line."""
    from figs.supp import sf_e3_v2 as e3m
    from figs.supp import sf_e7_grid_dev as gm
    from figs.supp import sf_fam_v2 as fm
    from figs.supp.sf_e3_v2 import tex_f, tex_label
    d = fdata("sf_e3_v2")
    t = _tables_of("sf_e3_v2", d, tmp_path, monkeypatch)["e3_v2.tex"]
    sc = d["tables"]["e3_v2"]["scope"]
    assert t.startswith("% Written by code/sim/figs/supp/sf_e3_v2.py")
    # C50 (D5 review): the caption says what the main text claims (Section VII-C states Proposition 5's sharing bound)
    if "H5 failed" in t:                                                                                   # C50
        assert "the main text claims no measured sharing gain for any policy" in t                         # C50
    assert "no sharing claim enters the main text" not in t                                               # C50
    for b in sc["b"]:
        assert f"$b={b}$" in t
    for tag in sc["tags"]:
        stem, rest = e3m.split_label(style.POLICIES[e3m.TAG_KEY[tag]].label)
        assert f"\n{tex_label(stem)} & shared & " in t and (not rest or f"\n{tex_label(rest)} &  & [" in t)
        for mode in sc["modes"]:
            for v in d["panels"][mode][e3m.TAG_KEY[tag]]["median"]:
                assert tex_f(v) in t
    assert "H5 (i), reported as measured" in t and "H5 (ii), reported as measured" in t
    g = fdata("sf_e7_grid_dev")
    tt = _tables_of("sf_e7_grid_dev", g, tmp_path, monkeypatch)
    grid, q44 = tt["e7v2_grid.tex"], tt["e7v2_q44.tex"]
    for tag in g["tables"]["e7v2_grid"]["scope"]["tags"]:
        line = next(ln for ln in grid.splitlines() if ln.startswith(tex_label(style.POLICIES[gm.GRID_KEY[tag]].label)
                                                                    + " & "))
        row = g["tables"]["e7v2_grid"]["rows"][tag]
        want = [row["r0"][c]["median"] for c in g["a"]["alignments"]]
        for c in g["tables"]["e7v2_grid"]["stress_alignments"]:
            want += [row["stress"][c][mo]["median"] for mo in g["tables"]["e7v2_grid"]["stress_modes"]]
            want.append(row["W0"][c]["median"])
        want.append(row["gap"]["median"])
        assert line.removesuffix(r" \\").split(" & ")[1:] == [tex_f(v) for v in want], (tag, line)
    for inst in g["tables"]["e7v2_q44"]["scope"]["instances"]:
        assert r"\multicolumn{2}{c}{" + inst + "}" in q44
    for key, s in g["q44"]["series"].items():
        # C59 (RC19(3)): the guard study's rows by its name (as built "E11")
        assert tex_label(style.POLICIES[key].label) + (" & part grid & " if s["source"] == "grid" else
                                                       " & guard study & ") in q44
    assert "development-exposed" in grid and "development-exposed" in q44 and "Criterion T is not computable" in q44
    f = fdata("sf_fam_v2")
    ft = _tables_of("sf_fam_v2", f, tmp_path, monkeypatch)
    for r in f["tables"]["fam_v2_pairs"]["rows"]:
        assert f"{r['fam']} & {fm.SET_TEXT[r['set']]} & {fm.LENDER_NAME[r['mode']]} & {r['instances']} & " \
               f"{r['pairs']} & " \
               f"{r['equal']} & " in ft["fam_v2_pairs.tex"]
    for r in f["tables"]["fam_v2_f3"]["rows"]:
        assert f"$\\beta={r['beta']}$, $T={r['T']}$ & {fm.SET_TEXT[r['set']]} & " in ft["fam_v2_f3.tex"]  # C59
    for r in f["tables"]["fam_v2_q6"]["rows"]:
        assert r["inst"].replace("_", r"\_") + " & " in ft["fam_v2_q6.tex"]
    for tag in f["tables"]["fam_v2_q6"]["tags"]:
        assert fm._label(tag) in ft["fam_v2_q6.tex"]


def _widened(name: str) -> dict:
    """The fixture's data widened to the confirmation's grid (six b, four alignments, four instances), with values of
    the confirmation's size, so that the tables' widths are tested at full size."""
    d = copy.deepcopy(fdata(name))
    if name == "sf_e3_v2":
        bs = [1, 2, 4, 8, 16, 32]
        d["grid"]["b"] = bs
        for mode, panel in d["panels"].items():
            for s in panel.values():
                for f, v in (("median", 2.758), ("ci_lo", 2.715), ("ci_hi", 2.758)):
                    s[f] = [v] * len(bs)
        for f, v in (("point", 1.497), ("lo", 1.491), ("hi", 1.514)):
            d["opt"][f] = [v] * len(bs)
        d["h5"]["rows"] = [{"b": b, "le_MS4": b > 1, "shared_below_siloed": None if b < 2 else True} for b in bs]
        d["h5"]["failed_b"] = [1]
    if name == "sf_e7_grid_dev":
        g = d["tables"]["e7v2_grid"]
        c0 = g["alignments"][0]
        g["alignments"] = ["1", "2", "3", "4"]
        g["stress_alignments"] = ["1"]
        assert len(g["stress_modes"]) == 5
        for r in g["rows"].values():
            r["r0"] = {c: {**r["r0"][c0], "median": 1.106} for c in g["alignments"]}
            r["stress"] = {"1": {m: {"median": 2.028, "lo": None, "hi": None, "n": 3} for m in g["stress_modes"]}}
            r["W0"] = {"1": {"median": 2.028, "lo": None, "hi": None, "n": 3}}
            r["gap"]["median"] = 2.217
        q = d["q44"]
        q["instances"] = ["I1", "I2", "I3", "I4"]
        for s in q["series"].values():
            s["r0_tr"], s["W0"], s["W0_mode"] = [1.041] * 4, [1.141] * 4, ["L-iid-0.2"] * 4
        q["grid_cells"] = {i: ["c"] * 8 for i in q["instances"]}
        q["e11_cells"] = {i: 8 for i in q["instances"]}
    return d


@pytest.mark.skipif(not PDFLATEX.is_file(), reason="pdflatex is not installed")
@pytest.mark.parametrize("wide", [False, True], ids=["fixture", "full_width"])
def test_tables_compile(tmp_path, monkeypatch, wide):
    """The six tables compile with booktabs and array in a two-column IEEEtran page, with no overfull box, from the
    fixture extracts and widened to the confirmation's grid."""
    texts = {}
    for name in ("sf_e3_v2", "sf_e7_grid_dev", "sf_fam_v2"):
        data = _widened(name) if wide else fdata(name)
        texts.update(_tables_of(name, data, tmp_path, monkeypatch))
    assert sorted(texts) == sorted(f for n in TABLES.values() for f in n)
    for f, t in texts.items():
        (tmp_path / f).write_text(t)
    body = "".join(f"\\input{{{f}}}\n" for f in sorted(texts))
    (tmp_path / "doc.tex").write_text("\\documentclass[lettersize,journal]{IEEEtran}\\usepackage{booktabs}"
                                      "\\usepackage{array}\n\\begin{document}\n" + body + "Text.\n\\end{document}\n")
    env = dict(os.environ, TEXINPUTS=f"{style.REPO / 'paper' / 'layout_check'}:")
    r = subprocess.run([str(PDFLATEX), "-interaction=nonstopmode", "-halt-on-error", "doc.tex"], cwd=tmp_path,
                       capture_output=True, text=True, env=env, timeout=300)
    log = (tmp_path / "doc.log").read_text(errors="replace")
    assert r.returncode == 0 and "LaTeX Error" not in log, log[-2000:]
    assert "Overfull" not in log, [ln for ln in log.splitlines() if "Overfull" in ln]


# ---------------------------------------------------------------------------------------------------------------
# C62 (group g5-ms5b: the type scale of the caption and the redrawn layouts of sf_e3_v2, sf_fam_v2 and sf_e7_grid_dev)
def _pdf_spans_c62(pdf) -> list:
    """(baseline y, x, size, text) of every text span of a one-page PDF (PyMuPDF), baselines from the top in bp."""
    import fitz
    out = []
    for b in fitz.open(str(pdf))[0].get_text("rawdict")["blocks"]:
        for ln in b.get("lines", []):
            for s in ln["spans"]:
                txt = "".join(c["c"] for c in s["chars"])
                if txt.strip():
                    out.append((s["chars"][0]["origin"][1], s["chars"][0]["origin"][0], s["size"], txt))
    return out


@pytest.mark.parametrize("name", ["sf_e3_v2", "sf_fam_v2", "sf_e7_grid_dev"])
def test_c62_sf_e3_v2_fam_v2_grid_dev_titles_on_the_letters_baseline(figs_env, name):
    """C62: every panel title is at the caption size (style.LABEL_PT) and, in the PDF, on its panel letter's baseline
    (within 0.05 bp; sf_e7_grid_dev's (c) has a mathtext W0)."""
    rep = module(name).main(["--from-extract", str(FIX / f"{name}.json")])
    fig = module(name).draw(fdata(name))
    titles = [t for t in fig.texts if getattr(t, "_sublet_role", "") == "panel_title"]
    letters = [t for t in fig.texts if getattr(t, "_sublet_role", "") == "panel_letter"]
    assert len(titles) == len(letters) > 0 and all(t.get_fontsize() == pytest.approx(style.LABEL_PT) for t in titles)
    spans = _pdf_spans_c62(rep["pdf"])
    base = [y for y, _, _, txt in spans if txt.startswith("(") and txt.endswith(")") and len(txt) == 3]
    assert len(base) == len(letters)
    for t in titles:
        head = t.get_text().split("$")[0].strip()
        ys = [y for y, _, s, txt in spans if txt.strip().startswith(head) and abs(s - style.LABEL_PT) < 0.01]
        assert ys and min(abs(ys[0] - b) for b in base) < 0.05, (name, t.get_text())


def test_c62_sf_e3_v2_key_in_a_clear_of_the_data_and_stars_at_b():
    """C62 (sf_e3_v2): the key is one figure legend inside (a), its labels the registry labels (sublet_ms4's on two
    lines), above every marker and bar of (a) by KEY_CLEAR_PT, on a white box without an edge; no legend row above the
    panels; the stars sit at b itself."""
    from figs.supp import sf_e3_v2 as m
    d = fdata("sf_e3_v2")
    fig = m.draw(d)
    (leg,) = fig.legends
    assert leg._sublet_role == "key"
    keys = [k for k in m.KEYS if k != "opt"]
    assert sorted(t.get_text().replace("\n", " ") for t in leg.get_texts()) == sorted(
        style.POLICIES[k].label for k in keys)
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    ax_a, ax_b = [ax for ax in fig.axes if hasattr(ax, "_sublet_rect_in")]
    bb, ab = leg.get_window_extent(r), ax_a.get_window_extent(r)
    assert ab.x0 <= bb.x0 and bb.x1 <= ab.x1 and ab.y0 <= bb.y0 and bb.y1 <= ab.y1
    assert leg.get_frame().get_edgecolor()[3] == 0.0 and leg.get_frame().get_facecolor()[:3] == (1.0, 1.0, 1.0)
    px = fig.dpi / 72.0
    for ln in ax_a.lines:
        if getattr(ln, "_sublet_role", "") == "markers":
            for x, y in ln.get_xydata():
                pxl, pyl = ax_a.transData.transform((x, y))
                if pxl <= bb.x1:
                    assert pyl + 0.5 * (ln.get_markersize() + ln.get_markeredgewidth()) * px + m.KEY_CLEAR_PT * px \
                        <= bb.y0 + 0.5, (x, y)
    stars = [ln for ln in ax_b.lines if getattr(ln, "_sublet_policy", "") == "opt"]
    assert stars and all(list(ln.get_xdata()) == pytest.approx([float(b) for b in d["opt"]["b"]][:len(
        ln.get_xdata())]) or set(ln.get_xdata()) <= {float(b) for b in d["opt"]["b"]} for ln in stars)


def test_c62_sf_e3_v2_x_label_names_b_in_math_italic(figs_env):
    """C62 fix round (sf_e3_v2): both panels' x label is "Borrowers per LLM, $b$", the caption's wording with the
    paper's italic b, in the fixture and in the versioned extract, and the PDF prints that b in the italic face."""
    from figs.supp import sf_e3_v2 as m
    assert m.LABELS["x"] == "Borrowers per LLM, $b$"
    for d in (fdata("sf_e3_v2"), json.loads((style.REPO / "code/sim/out/figs/sf_e3_v2.json").read_text())["data"]):
        assert d["labels"]["x"] == m.LABELS["x"]
        fig = m.draw(d)
        assert [ax.get_xlabel() for ax in fig.axes if hasattr(ax, "_sublet_rect_in")] == [m.LABELS["x"]] * 2
    import fitz
    rep = m.main(["--from-extract", str(FIX / "sf_e3_v2.json")])
    spans = [s for b in fitz.open(str(rep["pdf"]))[0].get_text("dict")["blocks"] for ln in b.get("lines", [])
             for s in ln["spans"]]
    heads = [i for i, s in enumerate(spans) if s["text"] == "Borrowers per LLM, "]
    assert len(heads) == 2
    for i in heads:
        assert spans[i + 1]["text"] == "b" and "Italic" in spans[i + 1]["font"] and "Italic" not in spans[i]["font"]


def test_c62_sf_fam_v2_categories_minor_ticks_and_x_labels(figs_env):
    """C62 (sf_fam_v2): (a)'s categories on one line under its own x label, which shares its PDF baseline with (b)'s
    mathtext label (within 0.05 bp); the log y axis has no minor ticks."""
    from figs.supp import sf_fam_v2 as m
    d = fdata("sf_fam_v2")
    fig = m.draw(d)
    ax_a, ax_b = [ax for ax in fig.axes if hasattr(ax, "_sublet_rect_in")]
    assert all("\n" not in t.get_text() for t in ax_a.get_xticklabels())
    assert ax_a.get_xlabel() == m.LABELS["a_x"] and not len(ax_a.yaxis.get_minorticklocs())
    rep = m.main(["--from-extract", str(FIX / "sf_fam_v2.json")])
    spans = _pdf_spans_c62(rep["pdf"])
    ya = [y for y, _, s, txt in spans if txt.startswith(m.LABELS["a_x"])]
    yb = [y for y, _, s, txt in spans if "eager lender)" in txt and abs(s - style.LABEL_PT) < 0.01]
    assert ya and yb and abs(ya[0] - yb[0]) < 0.05
