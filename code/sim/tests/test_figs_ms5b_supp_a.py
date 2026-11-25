"""Tests of the MS5b supplementary E7 scripts of unit U39a (figs/supp/sf_e7_intensity.py, sf_e7_decomp.py,
sf_e7_boundary.py, their helper figs/supp/ms5b_e7_lib.py) and their thirteen tables (design/sublet_v2.md §11, W4, W9,
W10, W13). Quick: no raw data. The inputs are the input tree tests/fixtures_figs_ms5b/inputs/ (reduced-mode outputs of
the confirmation parts of e7h.py and the analysis on them, with a set of main/runs/ files; its README) and the fixture
extracts tests/fixtures_figs_ms5b/<name>.json (what each script writes on that tree;
tests/fixtures_figs_ms5b/refresh_extracts.py --only NAME). Every file is written under pytest's tmp_path. The reduced
summaries carry no real values, so the oracles are recomputed from the fixture summaries by other code paths: every
point, row and table cell equal to its source.

- Each script redraws with --from-extract from its fixture extract under temporary SUBLET_FIGS_*_DIR, with finalize()
  passing at its registered size (C41), writes the extract it read and its tables (TABLES).
- Each script builds from the input tree the data of its fixture extract and opens no file outside the result folders
  of the input root (patched open); the extract's meta block has each part's git revision, `reduced` from the
  summaries and the sources; sf_e7_decomp lists each run file it read with its sha256 (W10).
- The keys drawn are SUPP_POLICIES_MS5B's set, pass check_policies and check_legacy, and include no legacy key.
- Value oracles: the intensity curves and every crossing against main's and second's tables; the decomposition's
  paired differences, W0 against the stress modes' maximum, the Pareto front recomputed, RC against the L-hon runs,
  the seeds, Table III v2's cells (overflow USD as r0 x bl0a_usd, the total accounting from the run files, the gap
  from the gap rows), H3's counts against analysis.json and the outcomes; the boundary rows, the lagged pairs, the E5
  menus and the gap days against part second's rows.
- Each table holds every row of its scope (the extract's tables.<name>.scope) and compiles, between \\onecolumn and
  \\twocolumn of a two-column IEEEtran document (longtable needs one-column mode), with no overfull box (pdflatex, if
  installed); sf_e7_decomp's data file e7v2_rc_runs.csv holds every run of e7v2_rc with the recorded sha256.
- The print-check fixes of 2026-11-03: sf_e7_decomp's symlog (a), shared names of coinciding points, the count of a
  clipped point's weeks beyond the drawn range, leaders clear of other points' bars, a clipped Delta r0 bar's arrow
  pointing at its own name (round 2); sf_e7_intensity's square-root
  axis and its caption's overlaps; sf_e7_boundary's L-vr violation count, the L-ad, L-eg and L-iid-1 check and the
  x ranges; 'none' crossings, H3's zero columns, H6's exact zero.
- The helpers: label wrapping at word breaks only, run file names, week spans, column blocks, the longtable (groups
  kept on one page, the one-column comment, a spanning head), the name cells.

C50 (design/ms6_spec.md §7.2, the D5 review; §7.1 D4's script items): every longtable's head on its later pages opens
with "Table <n>, continued" (ms5b_e7_lib.cont_head), and no table prints the project names MS4's, P3's, T4/O1 or e7r.
Each changed line names C50.
"""
from __future__ import annotations

import builtins
import copy
import hashlib
import importlib
import io
import json
import math
import os
import re
import statistics
import subprocess
from pathlib import Path

import pytest

from figs import style
from figs.inputs import Inputs

FIX = Path(__file__).resolve().parent / "fixtures_figs_ms5b"
IN_ROOT = FIX / "inputs"
CONF = IN_ROOT / "code" / "sim" / "out" / "sublet_v2"
SCRIPTS = {"sf_e7_intensity": "figs.supp.sf_e7_intensity", "sf_e7_decomp": "figs.supp.sf_e7_decomp",
           "sf_e7_boundary": "figs.supp.sf_e7_boundary"}
NAMES = sorted(SCRIPTS)
SIZES = {"sf_e7_intensity": ("W2", 2.5), "sf_e7_decomp": ("W2", 2.4), "sf_e7_boundary": ("W2", 2.5)}     # C41, W4;
# C59: sf_e7_boundary 2.5 in (was 2.4 in), for the guard's name in words on three lines
TABLES = {"sf_e7_intensity": ("e7v2_crossings.tex",),
          "sf_e7_decomp": ("e7v2_weeks.tex", "e7v2_pareto.tex", "e7v2_rc.tex", "e7v2_seeds.tex",
                           "e7v2_table3_intervals.tex", "e7v2_h3.tex", "ms5b_outcomes.tex", "e7v2_rc_runs.csv"),
          "sf_e7_boundary": ("e7v2_boundary.tex", "e7v2_lag.tex", "e7v2_e5.tex", "e7v2_gap.tex")}
TEX = {n: tuple(t for t in ts if t.endswith(".tex")) for n, ts in TABLES.items()}      # the LaTeX tables
STALE = ("tests/fixtures_figs_ms5b/{}.json is stale (the script's data changed): refresh it with "
         "`python tests/fixtures_figs_ms5b/refresh_extracts.py --only {}` from code/sim")
PDFLATEX = Path.home() / ".local/bin/pdflatex"
STRESS = ("L-eg", "L-ss", "L-iid-0.05", "L-iid-0.2", "L-co")

pytestmark = pytest.mark.filterwarnings("ignore::figs.style.GlyphSizeWarning")


def module(name):
    return importlib.import_module(SCRIPTS[name])


def payload(name):
    return json.loads((FIX / f"{name}.json").read_text())


def data(name):
    return payload(name)["data"]


def part(p: str) -> dict:
    return json.loads((CONF / p / "summary.json").read_text())


def analysis() -> dict:
    return json.loads((CONF / "analysis.json").read_text())


def val(table, tag, mode, cell, seed=0):
    return (((table.get(tag) or {}).get(mode) or {}).get(str(cell)) or {}).get(str(seed))


@pytest.fixture
def figs_env(tmp_path, monkeypatch):
    monkeypatch.setenv("SUBLET_FIGS_IN_ROOT", str(IN_ROOT))
    monkeypatch.setenv(style.ENV_PDF_DIR, str(tmp_path / "pdf"))
    monkeypatch.setenv(style.ENV_OUT_DIR, str(tmp_path / "out"))
    monkeypatch.setenv("SUBLET_FIGS_TABLES_DIR", str(tmp_path / "tables"))
    return tmp_path


def drawn_keys(fig) -> set:
    return {getattr(a, "_sublet_policy") for ax in fig.axes for a in ax.get_children() if hasattr(a, "_sublet_policy")}


def tex_of(name: str, table: str) -> str:
    """The table file that `name`'s after hook writes from its fixture extract."""
    mod = module(name)
    d = data(name)
    stem = table[:-4]
    fn = {"e7v2_crossings": lambda: mod.crossings_tex(d["tables"][stem], d),
          "e7v2_weeks": lambda: mod.weeks_tex(d["tables"][stem], d),
          "e7v2_pareto": lambda: mod.pareto_tex(d["tables"][stem], d),
          "e7v2_rc": lambda: mod.rc_tex(d["tables"][stem], d),
          "e7v2_seeds": lambda: mod.seeds_tex(d["tables"][stem], d),
          "e7v2_table3_intervals": lambda: mod.t3_tex(d["tables"][stem], d),
          "e7v2_h3": lambda: mod.h3_tex(d["tables"][stem], d),
          "ms5b_outcomes": lambda: mod.outcomes_tex(d["tables"][stem], d),
          "e7v2_boundary": lambda: mod.boundary_tex(d["tables"][stem], d),
          "e7v2_lag": lambda: mod.lag_tex(d["tables"][stem], d),
          "e7v2_e5": lambda: mod.e5_tex(d["tables"][stem], d),
          "e7v2_gap": lambda: mod.gap_tex(d["tables"][stem], d)}[stem]
    return fn()


def body_rows(tex: str) -> int:
    return tex.count(r"\tabularnewline")


# ---------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("name", NAMES)
def test_from_extract_saves_and_finalize_passes(figs_env, name):
    """--from-extract on the fixture extract: save() under the temporary folders (finalize() passed), the registered
    page size, 9-10 pt text, the extract written equals the one read, and the after hook wrote the tables."""
    rep = module(name).main(["--from-extract", str(FIX / f"{name}.json")])
    spec = style.figure_spec(name)
    assert Path(rep["pdf"]) == figs_env / "pdf" / f"{name}.pdf" and Path(rep["pdf"]).is_file()
    assert (spec.width, spec.height_in, spec.main) == (*SIZES[name], False)
    assert abs(rep["width_bp"] - spec.width_in * 72) <= 0.5 and abs(rep["height_bp"] - spec.height_in * 72) <= 0.5
    assert rep["outside_page"] == [] and rep["pages"] == 1
    assert all(style.TEXT_MIN_PT <= s <= style.TEXT_MAX_PT for s in rep["text_pt"])
    assert not any("dejavu" in f.lower() for f in rep["fonts"])
    assert json.loads((figs_env / "out" / f"{name}.json").read_text()) == payload(name)
    tables = figs_env / "tables"
    assert sorted(p.name for p in tables.iterdir()) == sorted(TABLES[name])
    assert tuple(module(name).TABLES) == TABLES[name]
    for t in TEX[name]:
        text = (tables / t).read_text()
        assert text.startswith(f"% Written by code/sim/figs/supp/{name}.py from ") and text.rstrip().endswith(
            r"\endgroup")
        assert text.split("\n", 1)[1] == tex_of(name, t)
    if name == "sf_e7_decomp":
        d = data(name)
        text = (tables / "e7v2_rc_runs.csv").read_text()
        assert text == module(name).rc_runs_csv(d["tables"]["e7v2_rc"])
        assert hashlib.sha256(text.encode()).hexdigest() == d["tables"]["e7v2_rc_runs"]["sha256"]


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
    """build() on the input tree opens no repository file outside the result folders of the input root (patched
    open), records only result files as sources, and gives the fixture extract's data."""
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
        if style.REPO in p.parents:
            assert IN_ROOT in p.parents, f"{name} opened {p}"
            style.check_source(p.relative_to(IN_ROOT).as_posix())
    assert opened and all(style.check_source(s) == s for s in inp.sources)
    from figs.common import json_number
    d = json.loads(json.dumps(d, allow_nan=False, default=json_number))
    assert d == data(name), STALE.format(name, name)
    assert payload(name)["sources"] == inp.sources == d["meta"]["sources"]


@pytest.mark.parametrize("name", NAMES)
def test_registry_keys_and_policy_checks(name):
    """The keys drawn are the figure's set of SUPP_POLICIES_MS5B (C41; the fixture has every one), pass
    check_policies and check_legacy, and hold no legacy key; every drawn text names a policy by its registry label
    (or, in sf_e7_decomp's panel (a), by the label less the prefix that the panel title carries)."""
    mod = module(name)
    fig = mod.draw(data(name))
    keys = drawn_keys(fig)
    assert tuple(mod.KEYS) == style.SUPP_POLICIES_MS5B[name]
    assert keys == set(style.SUPP_POLICIES_MS5B[name]), keys
    style.check_policies(keys)
    style.check_legacy({name: keys})
    assert not keys & set(style.LEGACY_KEYS)
    for leg in [ax.get_legend() for ax in fig.axes if ax.get_legend() is not None]:
        labels = {style.POLICIES[k].label for k in keys}
        assert all(t.get_text().replace("\n", " ") in labels for t in leg.get_texts())


@pytest.mark.parametrize("name", NAMES)
def test_meta_and_scopes(name):
    """meta: each part's git revision, `reduced` true on the reduced tree (from the summaries' meta.reduced), the
    sources; every table of TABLES has a `scope` in the extract's tables block."""
    d = data(name)
    m = d["meta"]
    assert m["reduced"] is True and isinstance(m["git_revision"], dict) and m["git_revision"]
    for p, rev in m["git_revision"].items():
        src = analysis() if p == "analysis" else part(p)
        assert rev == src["meta"]["git_revision"]
    assert m["sources"] == payload(name)["sources"]
    assert sorted(d["tables"]) == sorted(t[:-4] for t in TABLES[name])
    assert all(isinstance(t.get("scope"), dict) and t["scope"] for t in d["tables"].values())
    assert d["labels"]["caption"] and "{" not in d["labels"]["caption"].replace("\\{", "").replace(
        "\\}", "").replace("{tab:", "").split("\\ref")[0]


# ---------------------------------------------------------------------------------------------------------------
# sf_e7_intensity
def merged_r0(tag: str, p: float, week: str):
    """r0 of `tag` at the i.i.d. lender's p on `week`: main's runs at 0 (L-hon), 0.05 and 0.2, second's at the other
    points (the registered merge, by another path)."""
    mode = "L-hon" if p == 0 else f"L-iid-{format(p, 'g')}"
    for s in (part("main"), part("second")):
        v = val(s["table"], tag, mode, week)
        if v is not None:
            return v
    return None


def test_intensity_series_and_crossings_equal_the_tables():
    """Every point of every curve equals main's or second's r0 at its p and week; medians are the medians of the
    weeks; every crossing cell is the first p with r0 > 1 over the points measured that week."""
    from figs.supp import ms5b_e7_lib as L
    from figs.supp import sf_e7_intensity as M
    d = data("sf_e7_intensity")
    grid = d["grid"]
    assert grid == sorted(grid) and grid[0] == 0.0 and d["weeks"]
    for key, s in d["series"].items():
        tag = L.TAG_OF_KEY[key]
        for w in d["weeks"]:
            assert s["per_week"][w] == [merged_r0(tag, p, w) for p in grid], (key, w)
        for i in range(len(grid)):
            assert s["median"][i] == statistics.median(s["per_week"][w][i] for w in d["weeks"])
            assert s["lo"][i] <= s["median"][i] <= s["hi"][i]
    t = d["tables"]["e7v2_crossings"]
    assert t["scope"]["tags"] == [r["tag"] for r in t["rows"]] and set(t["scope"]["weeks"]) == set(t["weeks"])
    for r in t["rows"]:
        for w, c in r["cells"].items():
            if c is None:
                continue
            pts = [(p, merged_r0(r["tag"], p, w)) for p in grid]
            pts = [(p, v) for p, v in pts if v is not None]
            assert c["n_points"] == len(pts) and c["p_max"] == max(p for p, _ in pts)
            assert c["first"] == next((p for p, v in pts if v > 1.0), None), (r["tag"], w)
            want = (format(c["first"], "g") if c["first"] is not None else
                    "none" if c["p_max"] >= t["grid_top"] else "$>$")
            assert M.cell_text(c, t["grid_top"]).startswith(want)
    assert t["grid_top"] == max(grid)


def test_intensity_panels_legends_and_reference():
    """Each panel draws Sublet and its group, its legend lists the group in legend order (Sublet labeled directly),
    the grey line marks 1, and no legend lies over the data under it."""
    from figs.supp import sf_e7_intensity as M
    d = data("sf_e7_intensity")
    fig = M.draw(d)
    axes = [ax for ax in fig.axes if hasattr(ax, "_sublet_rect_in")]
    assert len(axes) == len(M.GROUPS)
    r = fig.canvas.get_renderer()
    for ax, (letter, title, keys) in zip(axes, M.GROUPS):
        drawn = {getattr(a, "_sublet_policy") for a in ax.lines if hasattr(a, "_sublet_policy")}
        assert drawn == {M.REF, *keys}
        leg = ax.get_legend()
        want = [style.POLICIES[k].label for k in style.legend_order(keys)]
        assert [t.get_text().replace("\n", " ") for t in leg.get_texts()] == want
        assert [t.get_text() for t in ax.texts if getattr(t, "_sublet_role", "") == "direct_label"] == ["Sublet"]
        bb = leg.get_window_extent(r)
        for ln in ax.lines:
            if getattr(ln, "_sublet_role", "") != "markers":
                continue
            for x, y in ln.get_xydata():
                px, py = ax.transData.transform((x, y))
                assert not (bb.x0 <= px <= bb.x1 and bb.y0 <= py <= bb.y1), (letter, x, y)


# ---------------------------------------------------------------------------------------------------------------
# sf_e7_decomp
def test_decomp_points_are_paired_differences():
    """Each point: per week r0 under L-tr and W0 (the largest r0 over the five stress modes) minus Sublet's, and their
    medians; main's W0 block equals the stress modes' maximum."""
    from figs.supp import ms5b_e7_lib as L
    main = part("main")
    t = main["table"]
    d = data("sf_e7_decomp")
    for w in d["weeks"]:
        for tag in t:
            assert main["W0"]["0"][tag][w] == max(val(t, tag, m, w) for m in STRESS)
    for key, p in d["points"].items():
        tag = L.TAG_OF_KEY[key]
        for w in d["weeks"]:
            dr = val(t, tag, "L-tr", w) - val(t, "Sublet", "L-tr", w)
            dw = max(val(t, tag, m, w) for m in STRESS) - max(val(t, "Sublet", m, w) for m in STRESS)
            assert p["per_week"][w] == pytest.approx([dr, dw], abs=1e-12)
        assert p["dr"]["median"] == pytest.approx(statistics.median(x for x, _ in p["per_week"].values()), abs=1e-12)
    assert d["arrows"] == [["bl1", "bl1n"], ["bl1", "bl1_gp"], ["bl5_cur", "bl5n"]]


def test_decomp_figure_names_leaders_and_arrows():
    """Every point is named once in its panel, beside its point or in the column (C62: as built until then, every
    name in the column), each column name with a leader (but one at its point's clip arrow) and no other name with
    one; three arrows in (b); a clipped
    interval (an extract whose Sublet one-way interval reaches far) gets an arrowhead and its end value, and the
    caption names it."""
    from figs.supp import sf_e7_decomp as M
    d = copy.deepcopy(data("sf_e7_decomp"))
    fig = M.draw(d)
    axes = [ax for ax in fig.axes if hasattr(ax, "_sublet_rect_in")]
    for ax, (_, _, keys) in zip(axes, M.PANELS):
        names = [t for t in ax.texts if getattr(t, "_sublet_role", "") == "name"]
        # one name per group of coinciding points: the first point's name, the others' after M.SAME on lines of
        # their own; every point named once
        assert sorted(k for t in names for k in t._sublet_keys) == sorted([M.REF, *keys])
        for t in names:
            lines = t.get_text().split("\n")
            assert lines[:len(t._sublet_keys)] == [M.name_of(t._sublet_keys[0])] + [
                M.SAME + M.name_of(k) for k in t._sublet_keys[1:]]
        assert [list(t._sublet_keys) for t in names] == M.name_groups(d, keys)
        # C62 (sf_e7_decomp): a name beside its point has no leader, a name in the column one, unless its point's
        # clip arrow points at it
        assert all(t._sublet_place in (*M.PLACES, M.COLUMN) for t in names)
        assert sum(getattr(t, "_sublet_role", "") == "leader" for t in ax.texts) == sum(
            t._sublet_place == M.COLUMN and not t._sublet_at_arrow for t in names)
    assert sum(getattr(t, "_sublet_role", "") == "arrow" for t in axes[1].texts) == 3
    p = d["points"]["sublet_1way"]["dr"]
    p.update(median=0.0, lo=0.0, hi=50.0)
    d["points"]["sublet_1way"]["per_week"] = {w: [40.0, 0.5] for w in d["weeks"]}
    d["clipped"] = M.clipped(d)
    d["beyond"] = M.beyond(d)
    assert {"key": "sublet_1way", "axis": "dr", "end": "hi", "value": 50.0} in d["clipped"]
    assert "Sublet, one-way's interval on $\\Delta r_0$ reaches 50.00" in M.caption(d)
    (b,) = d["beyond"]
    assert b["key"] == "sublet_1way" and b["weeks"] == d["weeks"] and b["dr"] == [40.0, 40.0]
    fig = M.draw(d)
    assert any(getattr(t, "_sublet_role", "") == "clip_arrow" for ax in fig.axes for t in ax.texts)
    names = [t.get_text() for ax in fig.axes for t in ax.texts if getattr(t, "_sublet_role", "") == "name"
             and "sublet_1way" in t._sublet_keys]
    assert names == [f"Sublet, one-way\n{len(d['weeks'])} of {len(d['weeks'])} weeks at $\\Delta r_0$ 40.00"]


def test_decomp_clip_arrow_points_at_its_own_name():
    """A Delta r0 bar clipped at the spine's end points with its arrowhead into the name column: at the arrow's height
    lies its own point's name and no other, also where its median is Sublet's origin (as Sublet one-way's on the
    confirmation weeks; print check 2026-11-03, round 2)."""
    from figs.supp import sf_e7_decomp as M
    d = copy.deepcopy(data("sf_e7_decomp"))
    p = d["points"]["sublet_1way"]
    p["dr"].update(median=0.0, lo=0.0, hi=50.0)
    p["dw"].update(median=0.0, lo=0.0, hi=0.0)
    p["per_week"] = {w: ([40.0, 0.5] if i % 2 == 0 else [0.0, 0.0]) for i, w in enumerate(d["weeks"])}
    d["clipped"] = M.clipped(d)
    d["beyond"] = M.beyond(d)
    fig = M.draw(d)
    rend = fig.canvas.get_renderer()
    ax = [a for a in fig.axes if hasattr(a, "_sublet_rect_in")][1]
    (arrow,) = [t for t in ax.texts if getattr(t, "_sublet_role", "") == "clip_arrow"]
    y_tip = ax.transData.transform(arrow.xy)[1]
    names = [t for t in ax.texts if getattr(t, "_sublet_role", "") == "name"]
    hit = [t._sublet_keys for t in names
           if t.get_window_extent(rend).y0 <= y_tip <= t.get_window_extent(rend).y1]
    assert hit == [("sublet_1way",)]


def test_decomp_tables_weeks_pareto_rc_seeds():
    """e7v2_weeks: every tag of main with its r0 and W0 per week; e7v2_pareto: the front recomputed from main's table
    equals the analysis's, with Sublet's dominators; e7v2_rc: every RC = r0(M) - r0(L-hon) of the same tag, week and
    seed, with the run's fallback and stranding totals; e7v2_seeds: seeds 1-2 from part seeds, 0 from main."""
    from sublet.experiments import ms5b_analysis as MA
    main, seeds, second, an = part("main"), part("seeds"), part("second"), analysis()
    t = main["table"]
    d = data("sf_e7_decomp")["tables"]
    wk = d["e7v2_weeks"]
    assert sorted(r["tag"] for r in wk["rows"]) == sorted(t) == sorted(wk["scope"]["tags"])
    for r in wk["rows"]:
        assert r["r0"]["values"] == [val(t, r["tag"], "L-tr", w) for w in wk["weeks"]]
        assert r["W0"]["values"] == [main["W0"]["0"][r["tag"]][w] for w in wk["weeks"]]
    pa = d["e7v2_pareto"]
    for r in pa["rows"]:
        w = r["week"]
        pts = {x: (val(t, x, "L-tr", w), max(val(t, x, m, w) for m in STRESS)) for x in MA.PARETO_TAGS}
        front = sorted(x for x, (a, b) in pts.items() if not any(
            c <= a and e <= b and (c < a or e < b) for y, (c, e) in pts.items() if y != x))
        assert sorted(m["tag"] for m in r["front"]) == front == sorted(an["reported"]["pareto_front"][w])
        assert r["sublet_on_front"] == ("Sublet" in front)
        assert bool(r["dominated_by"]) == (not r["sublet_on_front"])
    assert pa["scope"]["tags"] == [x for x in MA.PARETO_TAGS if x in t]      # the claims report's key (R-2)
    ptex = tex_of("sf_e7_decomp", "e7v2_pareto.tex")
    for r in pa["rows"]:                                                     # four decimals: a dominance shows
        for m in r["front"]:
            assert f"({format(m['r0'], '.4f')}, {format(m['W0'], '.4f')})" in ptex
    runs = {(x["tag"], x["mode"], str(x["cell"]), x["seed"]): x for p in (main, seeds, second) for x in p["runs"]
            if x["kind"] == "week"}
    rc = d["e7v2_rc"]
    n = 0
    for r in rc["rows"]:
        for w, s, v, fb, st, sh in r["runs"]:
            hon_t = (main if s == 0 else seeds)["table"]
            src = (main if r["mode"] in ("L-tr", *STRESS) else second)["table"] if s == 0 else seeds["table"]
            assert v == pytest.approx(val(src, r["tag"], r["mode"], w, s) - val(hon_t, r["tag"], "L-hon", w, s),
                                      abs=1e-12)
            x = runs[(r["tag"], r["mode"], w, s)]
            assert (fb, st, sh) == (x["fallback_usd"], x["stranding_usd"], x["fallback_share_after_reclaims"])
            n += 1
    assert n == rc["scope"]["n_runs"] == sum(len(by_s) for by_m in an["reported"]["RC"].values()
                                             for by_w in by_m.values() for by_s in by_w.values())
    se = d["e7v2_seeds"]
    assert se["seeds"][0] == 0 and set(se["seeds"][1:]) == {int(s) for s in seeds["W0"]}
    # the caption's reason for equal seeds is what the data support: never "Sublet draws no random number" (the
    # guard's safe expert draws, ms5b_common.seed_free), but its seed-free inner and its runs' s_fb_all
    stex = tex_of("sf_e7_decomp", "e7v2_seeds.tex")
    assert "Sublet draws no random number" not in stex
    for r in se["rows"]:
        g = [x for x in seeds["guarded"] if x["tag"] == r["tag"]]
        assert (r["draws"]["runs"], r["draws"]["s_fb_all"]) == (len(g), sum(x["s_fb_all"] is True for x in g))
        if r["max_diff"] == 0.0 and r["draws"]["guarded"] and r["draws"]["s_fb_all"] == len(g) > 0:
            assert f"followed FB at every slot of all {len(g):,} of its runs" in stex
    for r in se["rows"]:
        for ln in r["lines"]:
            if ln["what"] not in ("W0", "RC L-tr"):
                for w, by_s in ln["values"].items():
                    for s, v in by_s.items():
                        assert v == val((main if s == "0" else seeds)["table"], r["tag"], ln["what"], w, s)


def test_decomp_table3_intervals_against_runs_and_rows():
    """Table III v2's cells: the 14 rows of W2; overflow USD = median of r0 x bl0a_usd; total USD from the run files
    (each listed with its sha256); the saving 100 (1 - r0); the gap from second's gap_ratio; RC and W0 from main;
    p* from the curves; BL0a from bl0a_usd and the runs' references."""
    from figs.supp import sf_e7_decomp as M
    main, second = part("main"), part("second")
    d = data("sf_e7_decomp")
    t3 = d["tables"]["e7v2_table3_intervals"]
    assert [r["tag"] for r in t3["rows"]] == list(M.T3_TAGS) == t3["scope"]["tags"]
    assert [c["key"] for c in t3["columns"]] == [k for k, _, _ in M.T3_COLUMNS]
    rows = {(x["tag"], x["cell"]): x for x in main["runs"] if x["mode"] == "L-tr" and x["seed"] == 0}
    files = {f["path"]: f["sha256"] for f in d["meta"]["runs_files"]}
    assert files and all(p in d["meta"]["sources"] for p in files)
    for p, h in files.items():
        assert hashlib.sha256((IN_ROOT / p).read_bytes()).hexdigest() == h
    curves = analysis()["reported"]["intensity_curves"]
    top = max(p for by_w in curves.values() for c in by_w.values() for p, v in c["points"] if v is not None)
    bl0a = {(x["cell"], x["mode"]): x["bl0a_usd"] for x in main["runs"]}
    for r in t3["rows"]:
        c = r["cells"]
        if r["tag"] == "BL0a":
            assert c["usd_overflow"]["median"] == pytest.approx(statistics.median(
                rows[("Sublet", w)]["bl0a_usd"] / 1e3 for w in t3["weeks"]))
            assert c["saving_pct"]["median"] == 0.0
            assert c["w0"]["median"] == pytest.approx(statistics.median(
                max(bl0a[(w, m)] for m in STRESS) / bl0a[(w, "L-tr")] for w in t3["weeks"]))
            assert c["p_star"]["median"] is None and c["rc"]["median"] is None
            continue
        # p*: Table III v2's lower median over part second's weeks (a week without a crossing above every p), read
        # 'none' when every week's curve reaches the grid's top, else '>q'
        firsts = [curves[r["tag"]][w].get("first_p_above_1") for w in t3["p_weeks"]]
        ranked = sorted(firsts, key=lambda x: math.inf if x is None else x)
        low = ranked[(len(ranked) + 1) // 2 - 1]
        reach = min(max(p for p, v in curves[r["tag"]][w]["points"] if v is not None) for w in t3["p_weeks"])
        ps = c["p_star"]
        assert ps["median"] == low and [x["first"] for x in ps["per_week"]] == firsts
        assert ps["reading"] == (None if low is not None else "none" if reach >= top else f">{format(reach, 'g')}")
        assert c["usd_overflow"]["median"] == pytest.approx(statistics.median(
            rows[(r["tag"], w)]["r0"] * rows[(r["tag"], w)]["bl0a_usd"] / 1e3 for w in t3["weeks"]))
        tot = []
        for w in t3["weeks"]:
            job = rows[(r["tag"], w)]["job"]
            f = "code/sim/out/sublet_v2/main/runs/" + re.sub(r"[:=]", "__", job) + ".json"
            assert f in files
            pl = json.loads((IN_ROOT / f).read_text())
            (rec,) = [x for x in pl["runs"] if x["mode"] == "L-tr" and x["policy_seed"] == 0]
            tot.append(rec["accountings"]["total_usd"] / 1e3)
        assert c["usd_total"]["median"] == pytest.approx(statistics.median(tot))
        assert c["saving_pct"]["median"] == pytest.approx(statistics.median(
            100 * (1 - val(main["table"], r["tag"], "L-tr", w)) for w in t3["weeks"]))
        gaps = [second["gap_ratio"].get(f"{r['tag']}:{x}:0") for x in t3["gap_days"]]
        if any(v is not None for v in gaps):
            assert c["gap"]["median"] == pytest.approx(statistics.median(v for v in gaps if v is not None))
        else:
            assert c["gap"]["median"] is None
        assert c["w0"]["median"] == pytest.approx(statistics.median(main["W0"]["0"][r["tag"]][w] for w in t3["weeks"]))


def test_decomp_h3_counts_and_outcomes_equal_the_analysis():
    """H3's counts: the rows sum to the totals, which equal analysis.json's H3 (runs, aborts, one-way aborts by
    project, switches, robust slots, projected slots, K0, dropped Buys) and every part's guard_summary; the outcomes
    table has H1-H6 and H2b with analysis.json's kind and pass."""
    an = analysis()
    d = data("sf_e7_decomp")["tables"]
    h3 = d["e7v2_h3"]
    tot = h3["total"]
    a = an["H3"]
    assert (tot["runs"], tot["aborts"], tot["projected_slots"], tot["K0"], tot["dropped_buys"], tot["switch_runs"],
            tot["robust_runs"], tot["aborts_prop_p"], tot["runs"] - tot["held"], tot["env_violations"]) == \
        (a["n_runs"], a["aborts"], a["projected_slots"], a["K0"], a["dropped_buys"], a["runs_with_switches"],
         a["runs_with_robust_slots"], a["n_aborts_s_fb_bound_form"], a["n_not_held"], a["n_envelope_violations"])
    for p in ("main", "seeds", "second", "e3", "fam", "grid"):
        gs = part(p)["guard_summary"]
        rows = [r for r in h3["rows"] if r["part"] == p]
        assert sum(r["runs"] for r in rows) == gs["n_runs"] and sum(r["aborts"] for r in rows) == gs["aborts"]
    g = [x for p in ("main", "seeds", "second", "e3", "fam", "grid") for x in part(p)["guarded"]]
    assert tot["switches"] == sum(int(x.get("switches") or 0) for x in g)          # switches of S (§6, H3)
    assert tot["robust_slots"] == sum(int(x.get("robust_slots") or 0) for x in g)  # robust-form slots
    out = d["ms5b_outcomes"]
    assert [r["id"] for r in out["rows"]] == ["H1", "H2", "H2b", "H3", "H4", "H5", "H6"] == out["scope"]["hypotheses"]
    for r in out["rows"]:
        assert (r["kind"], r["pass"]) == (an[r["id"]]["kind"], an[r["id"]]["pass"])
    # the criteria as registered: 16 weeks (ms5b_common.CONF_WEEKS), whatever the input; each label of H1's set
    # whole, the list separated by semicolons where a label holds a comma
    from figs.supp import ms5b_e7_lib as L
    from sublet.experiments import ms5b_common as m5
    crit = {r["id"]: r["criterion"] for r in out["rows"]}
    k = len(m5.CONF_WEEKS)
    assert f"in at least {an['H1']['threshold']['wins']} of {k} weeks" in crit["H1"]
    assert f"in {k} of {k} weeks" in crit["H2"] and f"in {k} of {k} weeks" in crit["H2b"]
    assert L.join_labels([L.tex(L.label(t)) for t in an["H2"]["set"]]) in crit["H1"]
    tex = tex_of("sf_e7_decomp", "ms5b_outcomes.tex")
    assert body_rows(tex) == 7
    for r in out["rows"]:
        assert {True: "holds", False: "fails"}.get(r["pass"], "not decided") in tex


# ---------------------------------------------------------------------------------------------------------------
# sf_e7_boundary
def test_boundary_rows_lags_e5_and_gap_equal_part_second():
    """Every row: r0 under each condition from second's table, the L-tr reference from main's; the lagged variants
    (second's lag tags, main's lagged BL5); the E5 cells; the gap days: each ratio ALG / gap_lp of the day's gap row,
    BL0a's bl0a_usd / gap_lp."""
    from figs.supp import sf_e7_boundary as M
    main, second = part("main"), part("second")
    d = data("sf_e7_boundary")
    assert [r["tag"] for r in d["rows"]] == list(M.ROW_TAGS)
    for r in d["rows"]:
        assert r["ref"]["values"] == [val(main["table"], r["tag"], "L-tr", w) for w in d["weeks"]]
        for m, s in r["modes"].items():
            assert s["values"] == [val(second["table"], r["tag"], m, w) for w in d["weeks"]]
        if r["tag"] in M.LAG:
            lt, p = M.LAG[r["tag"]]
            src = second if p == "second" else main
            assert r["lag"]["values"] == [val(src["table"], lt, "L-tr", w) for w in d["weeks"]]
    lag = d["tables"]["e7v2_lag"]
    assert [p["tag"] for p in lag["pairs"]] == [t for t in M.ROW_TAGS if t in M.LAG]
    for p in lag["pairs"]:
        assert p["diff"]["values"] == pytest.approx([b - a for a, b in zip(p["base"]["values"],
                                                                          p["lagged"]["values"])])
    e5 = d["tables"]["e7v2_e5"]
    assert len(e5["rows"]) == len(M.E5_MENUS) * len(M.E5_LEVELS) * len(M.E5_TAGS)
    for r in e5["rows"]:
        assert r["values"] == [val(second["table"], r["tag"], r["level"], f"{r['menu']}:{c}") for c in e5["cells"]]
    gap = d["tables"]["e7v2_gap"]
    gr = {(x["tag"], x["cell"]): x for x in second["runs"] if x["kind"] == "gap"}
    for r in gap["rows"]:
        for day, v in zip(gap["days"], r["values"]):
            if r["tag"] == "BL0a":
                assert v == pytest.approx(gr[("Sublet", day)]["bl0a_usd"] / second["gap_lp"][day])
            else:
                assert v == pytest.approx(gr[(r["tag"], day)]["ALG"] / second["gap_lp"][day])
    assert gap["lp_usd"] == [second["gap_lp"][x] for x in gap["days"]]


def test_boundary_row_layout_and_ticks():
    """The rows are placed by their names' heights with one gap at least ROW_GAP_MIN_PT between neighbors (the
    wrapped Sublet-MS4 name on two lines); every panel draws a grey L-tr tick per row that has one; panel (e) draws
    only the lagged variants."""
    from figs.supp import sf_e7_boundary as M
    d = data("sf_e7_boundary")
    fig = M.draw(d)
    axes = [ax for ax in fig.axes if hasattr(ax, "_sublet_rect_in")]
    names = [t.get_text() for t in axes[0].get_yticklabels()]
    assert [n.replace("\n", " ") for n in names] == [r["label"] for r in d["rows"]]
    assert sum("\n" in n for n in names) == 1
    r = fig.canvas.get_renderer()
    fig.canvas.draw()
    boxes = sorted((t.get_window_extent(r) for t in axes[0].get_yticklabels()), key=lambda b: -b.y1)
    gaps = [(a.y0 - b.y1) * 72.0 / fig.dpi for a, b in zip(boxes, boxes[1:])]
    assert min(gaps) >= M.ROW_GAP_MIN_PT - 0.05
    for ax, p in zip(axes, d["panels"]):
        ticks = [ln for ln in ax.lines if getattr(ln, "_sublet_role", "") == "reference_tick"]
        keys = {getattr(ln, "_sublet_policy") for ln in ax.lines if hasattr(ln, "_sublet_policy")}
        if p["mode"] == "lag":
            assert len(ticks) == len(M.LAG) and keys == {style.POLICIES[k].key for k in
                                                         ("sublet_v2_lag", "a9_lag", "bl1_lag", "bl5_lag")}
        else:
            assert len(ticks) == len(d["rows"]) and len(keys) == len(d["rows"])


# ---------------------------------------------------------------------------------------------------------------
# the tables
def label_in(tex: str, lab: str) -> bool:
    """Whether a table prints a registry label: whole, or split over a group's first two rows (name_cells)."""
    from figs.supp import ms5b_e7_lib as L
    if L.tex(lab) in tex:
        return True
    for w in (1.1, 1.45, 2.0):
        a, b = L.name_cells(L.tex(lab), 2, w)
        if b and a in tex and b in tex:
            return True
    return False


@pytest.mark.parametrize("name,table", [(n, t) for n in NAMES for t in TEX[n]])
def test_tables_hold_every_row_of_their_scope(name, table):
    """Each table names every policy of its scope's tags (registry labels) and has the expected number of body rows;
    it opens with the one-column comment (longtable)."""
    from figs.supp import ms5b_e7_lib as L
    d = data(name)
    t = d["tables"][table[:-4]]
    tex = tex_of(name, table)
    assert r"\begin{longtable}" in tex and r"\label{tab:" in tex and tex.startswith(L.ONE_COLUMN)
    # C50 (D5 review; D4's script items): every longtable's head opens with "Table <n>, continued"; no project name
    assert tex.count(r"{Table~\thetable, continued}") == tex.count(r"\begin{longtable}")                # C50
    assert not re.search(r"\bMS4's|\bP3's|T4/O1|\be7r\b", tex)                                         # C50
    for tag in t["scope"].get("tags", []):
        lab = style.POLICIES["bl0a"].label if tag == "BL0a" else L.label(tag)
        assert label_in(tex, lab), (table, tag)
    weeks = t["scope"].get("weeks")
    for w in weeks if isinstance(weeks, list) else []:
        assert w in tex, (table, w)
    n = body_rows(tex)
    stem = table[:-4]
    want = {"e7v2_crossings": lambda: len(t["rows"]) * len(L.chunks(t["weeks"], 16)),
            "e7v2_weeks": lambda: 2 * len(t["rows"]) * len(L.chunks(t["weeks"], 8)),
            "e7v2_pareto": lambda: len(t["rows"]),
            "e7v2_rc": lambda: len(t["rows"]),
            "e7v2_seeds": lambda: sum(len(r["lines"]) for r in t["rows"]),
            "e7v2_table3_intervals": lambda: len(t["rows"]) * len(t["columns"]),
            "e7v2_h3": lambda: len(t["rows"]) + 1,
            "ms5b_outcomes": lambda: len(t["rows"]),
            "e7v2_boundary": lambda: len(t["rows"]) * len(t["modes"]),
            "e7v2_lag": lambda: 3 * len(t["pairs"]),
            "e7v2_e5": lambda: len(t["rows"]),
            "e7v2_gap": lambda: len(t["rows"]) + 1}[stem]()
    assert n == want, (table, n, want)


@pytest.mark.skipif(not PDFLATEX.is_file(), reason="pdflatex is not installed")
def test_tables_compile(tmp_path):
    """The twelve tables, from the fixture extracts, compile with booktabs and longtable between \\onecolumn and
    \\twocolumn of a two-column IEEEtran document (longtable needs one-column mode; the supplement sets them so, as
    the MS4 and MS5 longtables), with no overfull box."""
    inputs = []
    for name in NAMES:
        for table in TEX[name]:
            (tmp_path / table).write_text(tex_of(name, table))
            inputs.append(f"\\input{{{table}}}")
    (tmp_path / "doc.tex").write_text("\\documentclass[journal]{IEEEtran}\\usepackage{booktabs}"
                                      "\\usepackage{longtable}\n\\begin{document}\nText.\n\\onecolumn\n"
                                      + "\n".join(inputs) + "\n\\twocolumn\nText.\n\\end{document}\n")
    env = dict(os.environ, TEXINPUTS=f"{style.REPO / 'paper' / 'layout_check'}:")
    r = subprocess.run([str(PDFLATEX), "-interaction=nonstopmode", "-halt-on-error", "doc.tex"], cwd=tmp_path,
                       capture_output=True, text=True, env=env, timeout=300)
    log = (tmp_path / "doc.log").read_text(errors="replace")
    assert r.returncode == 0 and "LaTeX Error" not in log, log[-2000:]
    assert "Overfull" not in log, [ln for ln in log.splitlines() if "Overfull" in ln]


# ---------------------------------------------------------------------------------------------------------------
# helpers
def test_lib_helpers():
    """wrap splits once at a word break outside math and keeps the words; run_file maps a job id to its file;
    week_span, chunks and med_ci (the registered bootstrap) behave as documented; every confirmation tag of
    ms5b_common.E7_TAGS has a registry key."""
    from figs.supp import ms5b_e7_lib as L
    from sublet.experiments import ms5b_common as m5
    fig = style.new_figure("sf_e7_boundary")
    lab = style.POLICIES["sublet_ms4"].label
    w = L.wrap(fig, lab, 1.6)
    assert w.count("\n") == 1 and w.replace("\n", " ") == lab and "$" not in w.split("\n")[0][-2:]
    assert L.wrap(fig, "Sublet", 1.6) == "Sublet"
    assert L.run_file("main", "e7h:main:k=week:tag=BL1:c=301") == \
        "code/sim/out/sublet_v2/main/runs/e7h__main__k__week__tag__BL1__c__301.json"
    assert L.week_span(["301", "302", "303"]) == "301--303" and L.week_span(["101"]) == "101"
    assert L.chunks(list(range(16)), 8) == [list(range(8)), list(range(8, 16))] and L.chunks([], 8) == [[]]
    assert [len(c) for c in L.chunks(list(range(9)), 8)] == [5, 4]
    s = L.med_ci([1.0, 2.0, 3.0, 4.0])
    b = m5.bootstrap_median_ci([1.0, 2.0, 3.0, 4.0])
    assert (s["median"], s["lo"], s["hi"], s["n"]) == (b["median"], *b["ci"], 4) and b["seed"] == 20261031
    assert L.med_ci([None]) == {"median": None, "lo": None, "hi": None, "n": 0}
    assert set(m5.E7_TAGS) <= set(L.KEY_OF_TAG) and all(k in style.POLICIES for k in L.KEY_OF_TAG.values())
    assert L.tex(r"$a_b$ 10% x_y") == r"$a_b$ 10\% x\_y"
    assert L.num(-0.5, ".1f") == "$-$0.5" and L.num(None) == "--" and L.num(math.inf) == "--"


def test_lib_lists_and_continuation_blocks():
    """join_labels keeps every label whole (semicolons where a label holds a comma); a continuation block of a
    longtable steps the table counter back, so that the next table keeps its number."""
    from figs.supp import ms5b_e7_lib as L
    assert L.join_labels(["A", "B", "C"]) == "A, B and C" and L.join_labels(["A"]) == "A"
    assert L.join_labels(["Greedy renting", "Greedy, back-off"]) == "Greedy renting; and Greedy, back-off"
    first = L.longtable("lr", "Cap.", "tab:x", ["a", "b"], [["1", "2"]])
    cont = L.longtable("lr", "Continued.", "tab:x", ["a", "b"], [["1", "2"]], cont=False)
    assert r"\addtocounter{table}{-1}" not in first and r"\caption{Cap.}\label{tab:x}" in first
    assert cont.index(r"\addtocounter{table}{-1}") < cont.index(r"\begin{longtable}") and r"\caption" not in cont
    # C50 (D5 review; D4's script items): the head on the later pages, also of a continuation block, opens with
    # "Table <n>, continued", after the first head and before the repeated header
    for t in (first, cont):                                                                                # C50
        assert t.index(r"\endfirsthead") < t.index(L.cont_head(2)) < t.index(r"\endhead")                 # C50
    assert L.cont_head(2) == r"\multicolumn{2}{@{}l}{Table~\thetable, continued}\\[2pt]"                  # C50


def test_intensity_caption_bound():
    """The caption's A9-Sublet distance is an upper bound at one significant digit, never rounded down to 0."""
    from figs.supp import sf_e7_intensity as M
    assert M.bound_text(9.836e-05) == "0.0001" and M.bound_text(0.0012) == "0.002" and M.bound_text(0.0) == "0"
    assert M.bound_text(0.003) == "0.003"
    d = copy.deepcopy(data("sf_e7_intensity"))
    d["a9_sublet_max_gap"] = 9.836e-05
    assert "medians lie within 0.0001 of Sublet's" in M.caption(d)
    d["a9_sublet_max_gap"] = 0.0
    assert "medians equal Sublet's" in M.caption(d)
    d["a9_sublet_max_gap"] = 0.05
    assert "Critical-ratio renting" not in M.caption(d)


def test_table3_intervals_equal_table3_v2_cells(monkeypatch):
    """Where figs/table3_v2.py (U38, Table III v2) is present, every cell that both compute agrees on the input tree:
    the medians of USD (overflow, total), saving, gap, RC, W0, p* with its reading, and the intervals of USD and
    W0, so that the supplement's Table III with intervals never contradicts Table III."""
    T = pytest.importorskip("figs.table3_v2")
    monkeypatch.setenv("SUBLET_FIGS_IN_ROOT", str(IN_ROOT))
    u = T.build(Inputs())["rows"]
    mine = data("sf_e7_decomp")["tables"]["e7v2_table3_intervals"]
    assert [r["tag"] for r in mine["rows"]] == list(u)

    def eq(a, b):
        return (a is None and b is None) or (a is not None and b is not None and math.isclose(a, b, rel_tol=1e-9,
                                                                                             abs_tol=1e-12))
    for r in mine["rows"]:
        c, v = r["cells"], u[r["tag"]]["cells"]
        tot = c["usd_total"]["median"]
        assert eq(c["usd_overflow"]["median"] * 1e3, v["usd"]["overflow"]["median"]), r["tag"]
        assert eq(None if tot is None else tot * 1e3, v["usd"]["total"]["median"]), r["tag"]
        for mk, vk in (("saving_pct", "saving_pct"), ("gap", "gap"), ("rc", "RC"), ("w0", "W0"),
                       ("p_star", "p_star")):
            assert eq(c[mk]["median"], v[vk]["value"]), (r["tag"], mk)
        assert c["p_star"].get("reading") == v["p_star"].get("reading"), r["tag"]
        if c["usd_overflow"]["lo"] is not None and v["usd"]["overflow"].get("ci"):
            assert eq(c["usd_overflow"]["lo"] * 1e3, v["usd"]["overflow"]["ci"][0])
            assert eq(c["usd_overflow"]["hi"] * 1e3, v["usd"]["overflow"]["ci"][1])
        if c["w0"]["lo"] is not None and v["W0"].get("ci"):
            assert eq(c["w0"]["lo"], v["W0"]["ci"][0]) and eq(c["w0"]["hi"], v["W0"]["ci"][1])


# ---------------------------------------------------------------------------------------------------------------
# the print-check fixes (2026-11-03)
def test_decomp_axes_names_and_caption():
    """sf_e7_decomp: (a)'s Delta W0 axis is symlog at SYMLOG['a'], (b)'s linear, each panel with its own y ticks
    (symlog ticks at least Y_TICK_GAP_PT apart); the extract's coinciding groups are name_groups' groups of two or
    more; the caption names the scale, the coinciding points and every ablation whose Delta W0 interval lies below 0;
    no leader crosses another point's bar where a shift within LEADER_SHIFT_PT clears it."""
    from figs.supp import sf_e7_decomp as M
    d = data("sf_e7_decomp")
    fig = M.draw(d)
    axes = [ax for ax in fig.axes if hasattr(ax, "_sublet_rect_in")]
    assert [p["symlog"] for p in d["panels"]] == [M.SYMLOG.get(p["letter"]) for p in d["panels"]]
    assert axes[0].get_yscale() == "symlog" and axes[1].get_yscale() == "linear"
    assert axes[0].yaxis.get_transform().linthresh == M.SYMLOG["a"]
    r = fig.canvas.get_renderer()
    pos = sorted(axes[0].transData.transform((0.0, v))[1] * 72.0 / fig.dpi for v in axes[0].get_yticks())
    assert all(b - a >= M.Y_TICK_GAP_PT - 1e-6 for a, b in zip(pos, pos[1:])) and r is not None
    assert d["coincide"] == [g for p in d["panels"] for g in M.name_groups(d, p["keys"]) if len(g) > 1]
    cap = d["labels"]["caption"]
    assert "linear within $\\pm" + format(M.SYMLOG["a"], "g") + "$" in cap
    for k in [k for p in d["panels"] for k in p["keys"]]:
        dw = d["points"][k]["dw"]
        if dw["median"] is not None and (dw["hi"] or 0.0) < 0.0:
            assert M.name_of(k) in cap, k
    assert M._crosses((0, 0), (2, 2), (0, 2), (2, 0)) and not M._crosses((0, 0), (1, 0), (0, 1), (1, 1))
    assert M._near((0, 0), (10, 0), (5, 1), 1.5) and not M._near((0, 0), (10, 0), (5, 3), 1.5)


def test_decomp_coinciding_points_share_a_name():
    """Points whose medians and interval ends agree within COINCIDE_TOL share one name (the first point's, the
    others after SAME) and one leader; the caption says they have Sublet's medians and intervals."""
    from figs.supp import sf_e7_decomp as M
    d = copy.deepcopy(data("sf_e7_decomp"))
    zero = {"median": 0.0, "lo": 0.0, "hi": 0.0, "n": 1}
    for k in ("a9", "a9_noins"):
        d["points"][k]["dr"] = dict(zero)
        d["points"][k]["dw"] = {**zero, "lo": -0.5 * M.COINCIDE_TOL}
    groups = M.name_groups(d, d["panels"][0]["keys"])
    assert groups[0][0] == M.REF and sorted(groups[0][1:]) == ["a9", "a9_noins"]
    d["coincide"] = [g for p in d["panels"] for g in M.name_groups(d, p["keys"]) if len(g) > 1]
    assert "Critical-ratio renting and its ablation ``no insurance'' have Sublet's medians" in M.caption(d)
    assert M.group_text(d, groups[0], "a") == "\n".join([M.name_of(M.REF)] + [M.SAME + M.name_of(k)
                                                                              for k in groups[0][1:]])


def test_decomp_rc_runs_file_and_same_modes():
    """e7v2_rc_runs.csv: a header and one line per run of e7v2_rc (scope n_runs), its sha256 and columns in the
    extract; same_modes agrees with RC recomputed across L-ad, L-eg and L-iid-1 on their common weeks."""
    import csv as _csv
    from figs.supp import sf_e7_decomp as M
    d = data("sf_e7_decomp")["tables"]
    text = M.rc_runs_csv(d["e7v2_rc"])
    rows = list(_csv.reader(io.StringIO(text)))
    assert tuple(rows[0]) == M.RC_RUNS_COLUMNS == tuple(d["e7v2_rc_runs"]["columns"])
    assert len(rows) - 1 == d["e7v2_rc"]["scope"]["n_runs"] == d["e7v2_rc_runs"]["n_rows"]
    assert d["e7v2_rc_runs"]["sha256"] == hashlib.sha256(text.encode()).hexdigest()
    assert d["e7v2_rc_runs"]["scope"] == d["e7v2_rc"]["scope"]
    rc = analysis()["reported"]["RC"]
    sm = d["e7v2_rc"]["same_modes"]
    tags = [t for t in rc if all(m in rc[t] for m in M.SAME_MODES)]
    if sm is None:
        assert not tags
    else:
        eq = all(abs(rc[t][m][w]["0"] - rc[t]["L-ad"][w]["0"]) <= 1e-12 for t in tags for m in M.SAME_MODES
                 for w in sm["weeks"])
        assert sm["equal"] == eq and sm["n_tags"] == len(tags)


def test_decomp_h3_zero_columns_and_h6_text():
    """e7v2_h3.tex leaves out a column that is 0 in every row and names it in the caption; H6's measured value reads
    '0 (exactly; ...)' where the median price is exactly 0 (C59: as built '0 BL0a (exactly; ...)'), and H1's and
    H6's thresholds name the all-fallback bill (C59: as built 'BL0a')."""
    from figs.supp import sf_e7_decomp as M
    d = copy.deepcopy(data("sf_e7_decomp"))
    t = d["tables"]["e7v2_h3"]
    for r in t["rows"]:
        r["robust_slots"] = 0
    t["total"]["robust_slots"] = 0
    tex = M.h3_tex(t, d)
    assert "Robust" not in tex.split("\\toprule", 1)[1] and "a robust-form slot" in tex and r"\footnotesize" in tex
    an = copy.deepcopy(analysis())
    an["H6"]["median_price"] = 0.0
    h6 = M.outcomes_table(an)["rows"][-1]
    assert h6["id"] == "H6" and h6["measured"].startswith("0 (exactly")                                  # C59
    rows = M.outcomes_table(an)["rows"]
    assert all("BL0a" not in r["criterion"] + r["measured"] for r in rows)                               # C59
    assert h6["criterion"].endswith(" of the all-fallback bill") and "On the sharing instances (config seeds" in \
        rows[5]["criterion"]                                                                                # C59


def test_intensity_sqrt_axis_and_overlaps():
    """sf_e7_intensity draws each series at sqrt(p) plus its dodge, with labeled ticks at sqrt(X_TICKS) and minor
    ticks at the grid's other points; overlaps() finds equal medians at a p and pairs within NEAR_TOL at the grid's
    last NEAR_RUN points, which the caption names."""
    import numpy as np
    from figs.supp import sf_e7_intensity as M
    d = data("sf_e7_intensity")
    fig = M.draw(d)
    axes = [ax for ax in fig.axes if hasattr(ax, "_sublet_rect_in")]
    for ax in axes:
        assert list(ax.get_xticks()) == pytest.approx([math.sqrt(p) for p in M.X_TICKS if p <= max(d["grid"])])
        assert [t.get_text() for t in ax.get_xticklabels()] == [style.PLAIN(p) for p in M.X_TICKS
                                                                if p <= max(d["grid"])]
        for ln in ax.lines:
            if getattr(ln, "_sublet_role", "") == "markers":
                x = ln.get_xdata()
                off = x - np.sqrt(np.asarray(d["grid"]))
                assert np.allclose(off, off[0]) and abs(off[0]) < 0.05
    g = [0.0, 0.5, 1.0, 2.0]
    s = {k: {"median": [1.0, 1.0, 1.0, 1.0]} for k in style.SUPP_POLICIES_MS5B["sf_e7_intensity"]}
    s["bl1"] = {"median": [1.0, 2.0, 3.0, 4.0]}
    s["bl1_bo"] = {"median": [5.0, 2.01, 3.01, 4.02]}
    ov = M.overlaps(s, g)
    assert {"panel": "a", "p": 0.0, "value": 1.0, "keys": [k for k in style.legend_order(
        [M.REF, *M.GROUPS[0][2]]) if k != "bl1_bo"]} in ov["equal"]
    tails = [(t["panel"], t["p"], sorted(t["keys"])) for t in ov["tail"]]
    assert ("a", 0.5, ["bl1", "bl1_bo"]) in tails
    assert all({M.REF, "a9"} != set(t["keys"]) for t in ov["tail"])
    dd = copy.deepcopy(d)
    dd["overlaps"] = ov
    assert "differ by at most 0.02" in M.caption(dd) and "share the median 1.000" in M.caption(dd)


def test_boundary_violations_same_modes_and_ranges(monkeypatch):
    """sf_e7_boundary: the L-vr violation count read from part second's run files (each listed with its sha256)
    equals a count by another path; (a)'s title and the captions say 'no violation' where it is 0; same_modes equals
    the check of L-ad, L-eg and L-iid-1 on the tables; every panel but those with own ranges shares one x range,
    which holds its data and 1."""
    from figs.supp import sf_e7_boundary as M
    d = data("sf_e7_boundary")
    second, main = part("second"), part("main")
    files = {f["path"]: f["sha256"] for f in d["meta"]["runs_files"]}
    n = c = 0
    for r in second["runs"]:
        if r["kind"] == "week" and r["mode"] == "L-vr" and r["tag"] in M.ROW_TAGS and r["seed"] == 0 \
                and r["cell"] in d["weeks"]:
            f = "code/sim/out/sublet_v2/second/runs/" + re.sub(r"[:=]", "__", r["job"]) + ".json"
            assert hashlib.sha256((IN_ROOT / f).read_bytes()).hexdigest() == files[f]
            (rec,) = [x for x in json.loads((IN_ROOT / f).read_text())["runs"] if x["mode"] == "L-vr"
                      and x["policy_seed"] == 0]
            n, c = n + 1, c + rec["buffer_violations"]["count"]
    assert (d["violations"]["runs"], d["violations"]["count"]) == (n, c) and len(files) == n
    title = d["panels"][0]["title"]
    assert (title == "L-vr: no violation") == (n > 0 and c == 0)
    if n and c == 0:
        assert f"no buffer violation occurred in its {n} runs" in d["labels"]["caption"]
        assert f"No buffer violation occurred in the {n} L-vr runs" in tex_of("sf_e7_boundary", "e7v2_boundary.tex")
    eq = all(len({val(second["table"], t, "L-ad", w), val(main["table"], t, "L-eg", w),
                  val(second["table"], t, "L-iid-1", w)}) == 1 for t in M.ROW_TAGS for w in d["weeks"])
    assert d["same_modes"]["equal"] == eq
    xr = d["x_ranges"]
    shared = [x for x in xr if not x["own"]]
    assert shared and all((x["lo"], x["hi"]) == (shared[0]["lo"], shared[0]["hi"]) for x in shared)
    assert all(x["lo"] < 1.0 < x["hi"] for x in xr)
    fig = M.draw(d)
    axes = [ax for ax in fig.axes if hasattr(ax, "_sublet_rect_in")]
    assert [ax.get_xlim() for ax in axes] == [pytest.approx((x["lo"], x["hi"])) for x in xr]


def test_lib_longtable_groups_head_and_name_cells():
    """longtable: the one-column comment first, rows of a group of at most `keep` rows but its last end with
    \\tabularnewline* (no page break), none without groups; head_top above the header; name_cells splits a long name
    over a group's first two rows at a word break outside math, never a short one or a one-row group's."""
    from figs.supp import ms5b_e7_lib as L
    rows = [[str(i), "x"] for i in range(5)]
    t = L.longtable("lr", "Cap.", "tab:x", ["a", "b"], rows, groups=[0, 3], head_top=r"\multicolumn{2}{c}{H} \\")
    assert t.startswith(L.ONE_COLUMN + "\n")
    body = [ln for ln in t.split("\n") if ln.endswith("tabularnewline") or ln.endswith("tabularnewline*")]
    assert [ln.endswith("*") for ln in body] == [True, True, False, True, False]
    assert t.index(r"\multicolumn{2}{c}{H} \\") < t.index("a & b")
    assert not any(ln.endswith("*") for ln in L.longtable("lr", "C", "tab:y", ["a", "b"], rows).split("\n"))
    long = L.tex(style.POLICIES["sublet_ms4"].label)
    a, b = L.name_cells(long, 2, 2.0)
    assert a == L.rag("Lagged RetroRenting + one-way guard") and \
        b == L.rag(r"\quad ($B_0=10\%$ of the all-fallback bill)")                                         # C59
    assert L.name_cells(long, 1, 2.0) == [L.rag(long)] and L.name_cells("Sublet", 3, 2.0) == [L.rag("Sublet"), "", ""]
    assert L.bound_text(0.0037) == "0.004"
    assert L.plain_label(long) == "Lagged RetroRenting + one-way guard (B_0=10% of the all-fallback bill)"   # C59


# ---------------------------------------------------------------------------------------------------------------
# C62 (group g5-ms5b: the type scale of the caption and the redrawn layouts of sf_e7_intensity, sf_e7_decomp and
# sf_e7_boundary)
def _pdf_spans(pdf) -> list:
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


@pytest.mark.parametrize("name", NAMES)
def test_c62_sf_e7_intensity_decomp_boundary_titles_on_the_letters_baseline(figs_env, name):
    """C62: every panel title is at the caption size (style.LABEL_PT) and, in the PDF, on its panel letter's
    baseline (within 0.05 bp, mathtext titles included)."""
    rep = module(name).main(["--from-extract", str(FIX / f"{name}.json")])
    fig = module(name).draw(data(name))
    titles = [t for t in fig.texts if getattr(t, "_sublet_role", "") == "panel_title"]
    letters = [t for t in fig.texts if getattr(t, "_sublet_role", "") == "panel_letter"]
    assert len(titles) == len(letters) > 0 and all(t.get_fontsize() == pytest.approx(style.LABEL_PT) for t in titles)
    spans = _pdf_spans(rep["pdf"])
    base = {txt: y for y, _, _, txt in spans if txt.startswith("(") and txt.endswith(")") and len(txt) == 3}
    assert len(base) == len(letters)
    for t in titles:
        head = t.get_text().split("$")[0].strip()
        ys = [y for y, _, s, txt in spans if txt.strip().startswith(head) and abs(s - style.LABEL_PT) < 0.01]
        assert ys and min(abs(ys[0] - b) for b in base.values()) < 0.05, (name, t.get_text())


def test_c62_sf_e7_decomp_names_beside_points_keep_clear():
    """C62 (sf_e7_decomp): a name beside its point keeps NAME_CLEAR_PT from every mark of another point (markers,
    bars, arrows, the zero lines; within 0.1 pt of the Agg layout) and stays inside its axes (a column name reaches at
    most COLUMN_BELOW_PT below them), no two names meet, a name in the column has its leader (but one at its point's
    clip arrow), and each panel's y axis has its label."""
    from figs.supp import sf_e7_decomp as M
    for d in (data("sf_e7_decomp"), json.loads((style.REPO / "code/sim/out/figs/sf_e7_decomp.json").read_text())[
            "data"]):
        fig = M.draw(d)
        fig.canvas.draw()
        r = fig.canvas.get_renderer()
        px = fig.dpi / 72.0
        axes = [ax for ax in fig.axes if hasattr(ax, "_sublet_rect_in")]
        for ax, p, rg in zip(axes, d["panels"], M.ranges(d)):
            assert ax.get_ylabel() == d["labels"]["y"]
            groups = M.name_groups(d, p["keys"])
            marks = M._marks(ax, d, p, rg, groups)
            names = [t for t in ax.texts if getattr(t, "_sublet_role", "") == "name"]
            boxes = [tuple(t.get_window_extent(r).extents) for t in names]
            bb = ax.get_window_extent(r)
            for t, box in zip(names, boxes):
                below = M.COLUMN_BELOW_PT if t._sublet_place == M.COLUMN else 0.0     # the column reaches below
                assert bb.x0 <= box[0] and box[2] <= bb.x1 + 0.5 * px and bb.y0 - (below + 0.5) * px <= box[1] \
                    and box[3] <= bb.y1 + 0.5 * px, t.get_text()
                if t._sublet_place != M.COLUMN:
                    assert M._box_free(box, marks, (M.NAME_CLEAR_PT - 0.1) * px), t.get_text()
            for a, b in zip(boxes, boxes[1:]):
                assert not M._boxes_meet(a, b, 0.0)
            assert sum(getattr(t, "_sublet_role", "") == "leader" for t in ax.texts) == sum(
                t._sublet_place == M.COLUMN and not t._sublet_at_arrow for t in names)


def test_c62_sf_e7_boundary_row_bands_and_one_pitch():
    """C62 (sf_e7_boundary): a band behind every other row from the name column through the last panel (figure
    rectangles in figure fractions below the axes, whose faces are hidden), each between the midpoints of its row's
    neighbors; the one-line rows share one pitch; the names with a mathtext part sit on the plain names' baseline
    offset from their rows' centers (common.align_baselines)."""
    from figs.supp import sf_e7_boundary as M
    d = data("sf_e7_boundary")
    fig = M.draw(d)
    axes = [ax for ax in fig.axes if hasattr(ax, "_sublet_rect_in")]
    bands = [a for a in fig.artists if getattr(a, "_sublet_role", "") == "row_band"]
    assert len(bands) == (len(d["rows"]) + 1) // 2
    assert all(b.get_data_transform() is fig.transFigure and b.get_zorder() < 0 for b in bands)
    assert not any(ax.patch.get_visible() for ax in axes)
    centers = list(axes[0].get_yticks())
    names = [t.get_text() for t in axes[0].get_yticklabels()]
    pitch = {round(b - a, 6) for (a, na), (b, nb) in zip(zip(centers, names), zip(centers[1:], names[1:]))
             if "\n" not in na and "\n" not in nb}
    assert len(pitch) == 1
    math_rows = [t for t in axes[0].get_yticklabels() if "$" in t.get_text() and "\n" not in t.get_text()]
    assert math_rows and all(hasattr(t, "_sublet_baseline_shift_pt") for t in math_rows)


LOWER_PERCENTILE = re.compile(r"(?<![A-Za-z$\\])p\d+(\.\d+)?\b")   # 'p99.9', not 'P99.9', '$p$' or 'L-iid-0.05'


@pytest.mark.parametrize("name", NAMES)
def test_c62_percentiles_in_upper_case(name):
    """C62 fix round: a percentile is written in upper case (P99.9), as every other figure and the captions write it;
    sf_e7_boundary's (d) is titled "P99.9 buffer" in its fixture and in the versioned extract, whose caption draft
    says so too, and so do the tables of sf_e7_boundary and sf_e7_decomp (MODE_TEX)."""
    import matplotlib.text as mtext
    payloads = [data(name), json.loads((style.REPO / f"code/sim/out/figs/{name}.json").read_text())["data"]]
    for d in payloads:
        fig = module(name).draw(d)
        texts = [t.get_text() for t in fig.findobj(mtext.Text)]
        assert not [t for t in texts if LOWER_PERCENTILE.search(t)], name
        if name == "sf_e7_boundary":
            (title,) = [p["title"] for p in d["panels"] if p["mode"] == "L-b999"]
            assert title == "P99.9 buffer" and "P99.9 lease buffer" in d["labels"]["caption"]
            assert "P99.9 buffer" in texts
    from figs.supp import sf_e7_boundary, sf_e7_decomp
    assert sf_e7_boundary.MODE_TEX["L-b999"] == "P99.9 buffer" and sf_e7_decomp.MODE_TEX["L-b999"] == "L-tr, P99.9"


def test_c62_sf_e7_intensity_sublet_label_at_its_mid_point():
    """C62 (sf_e7_intensity): Sublet's direct label is centered on its curve's point nearest REF_LABEL_P, below it
    where Sublet is the lowest series there."""
    from figs.supp import sf_e7_intensity as M
    d = data("sf_e7_intensity")
    fig = M.draw(d)
    s = d["series"][M.REF]
    i = min((j for j, v in enumerate(s["median"]) if v is not None),
            key=lambda j: (abs(s["p"][j] - M.REF_LABEL_P), -j))
    for ax in [a for a in fig.axes if hasattr(a, "_sublet_rect_in")]:
        (t,) = [t for t in ax.texts if getattr(t, "_sublet_role", "") == "direct_label"]
        assert t.xy == pytest.approx((math.sqrt(s["p"][i]), s["median"][i])) and t.get_horizontalalignment() == "center"
