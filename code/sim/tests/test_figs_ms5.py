"""Tests of the MS5 supplementary figure scripts (figs/supp/sf_s1.py, sf_e9.py, sf_slack.py) and their tables
(s1_points.tex, s1_q28.tex, e9_steps.tex); design/sim_spec_ms5.md §6, §7, §10, row test_figs_ms5.py. Quick: no raw
data, no run outputs. The inputs are the input tree tests/fixtures_figs_ms5/inputs/ (reduced-mode outputs of the MS5
drivers, a copy of E7's versioned main summary and a slice of the slack series; README there) and the fixture extracts
tests/fixtures_figs_ms5/<name>.json (what each script writes on that tree; tests/fixtures_figs_ms5/refresh_extracts.py),
and every file is written under pytest's tmp_path (never into paper/ or code/sim/out/). The reduced summaries carry no
real values, so the oracles are structural: every point, row and series present, every value equal to its source.

- Each script redraws with --from-extract from its fixture extract under temporary SUBLET_FIGS_*_DIR, with finalize()
  passing at its registered size, and writes the extract it read; the after hooks write the three tables.
- Each script builds from the input tree (SUBLET_FIGS_IN_ROOT) the data of its fixture extract and opens no file
  outside the allowed roots (patched open); the stored layouts equal a recomputation.
- The keys drawn lie within SUPP_POLICIES_MS5 and pass check_policies.
- The three tables hold every row of their source with the source's values, and compile (pdflatex, if installed).
- sf_s1: every register row and Q28 row, its bar from lo to hi, its points, the order by span, the end labels where
  the layout draws them, the default's reference line; sf_e9: every series equal to the summary, the loops' styles,
  the reference lines, the direct labels or their move to the caption; sf_slack: SL-1 (the extract's daily series
  against a recomputation from the versioned npz within 1e-9, and the source digests), drawn at full size.
- Every script on hand-modified extracts at real-scale values.

C50 (design/ms6_spec.md §7.2, the D5 review; §7.1 D4's script items): the longtables of s1_points.tex and
e9_steps.tex open their head on the later pages with "Table <n>, continued", and e9_steps.tex's uncaptioned LP
longtable steps the table counter back itself. Each changed line names C50.
"""
from __future__ import annotations

import builtins
import copy
import hashlib
import importlib
import io
import json
import os
import subprocess
from pathlib import Path

import numpy as np
import pytest

from figs import style
from figs.common import MissingKey
from figs.inputs import Inputs

FIX = Path(__file__).resolve().parent / "fixtures_figs_ms5"
IN_ROOT = FIX / "inputs"
OUT = IN_ROOT / "code" / "sim" / "out"
SCRIPTS = {"sf_s1": "figs.supp.sf_s1", "sf_e9": "figs.supp.sf_e9", "sf_slack": "figs.supp.sf_slack"}
NAMES = sorted(SCRIPTS)
SIZES = {"sf_s1": ("W2", 2.5), "sf_e9": ("W2", 2.2), "sf_slack": ("W2", 2.5)}        # §7.1-§7.3 (C29)
TABLES = {"sf_s1": ("s1_points.tex", "s1_q28.tex"), "sf_e9": ("e9_steps.tex",), "sf_slack": ()}
STALE = ("tests/fixtures_figs_ms5/{}.json is stale (the script's data changed): refresh it with "
         "`python tests/fixtures_figs_ms5/refresh_extracts.py --only {}` from code/sim")
PDFLATEX = Path.home() / ".local/bin/pdflatex"

# first-level mathtext subscripts (alpha_p, s_S, delta_1, V_ell) are 4.9 pt at 7 pt (C62) and do not warn
pytestmark = pytest.mark.filterwarnings("ignore::figs.style.GlyphSizeWarning")


def module(name):
    return importlib.import_module(SCRIPTS[name])


def fixture_payload(name):
    return json.loads((FIX / f"{name}.json").read_text())


def fixture_data(name):
    return fixture_payload(name)["data"]


def tree(rel: str):
    return json.loads((OUT / rel).read_text())


@pytest.fixture
def figs_env(tmp_path, monkeypatch):
    monkeypatch.setenv("SUBLET_FIGS_IN_ROOT", str(IN_ROOT))
    monkeypatch.setenv(style.ENV_PDF_DIR, str(tmp_path / "pdf"))
    monkeypatch.setenv(style.ENV_OUT_DIR, str(tmp_path / "out"))
    monkeypatch.setenv("SUBLET_FIGS_TABLES_DIR", str(tmp_path / "tables"))
    return tmp_path


def save(name, data, tmp_path):
    """style.save of a figure drawn from `data` under tmp_path (finalize() runs)."""
    fig = module(name).draw(data)
    return style.save(fig, name, data, pdf_dir=tmp_path / "pdf", out_dir=tmp_path / "out")


def drawn_keys(fig) -> set:
    return {getattr(a, "_sublet_policy") for ax in fig.axes for a in ax.get_children() if hasattr(a, "_sublet_policy")}


def by_role(ax, role: str) -> list:
    return [t for t in ax.texts if getattr(t, "_sublet_role", "") == role]


# ---------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("name", NAMES)
def test_from_extract_saves_and_finalize_passes(figs_env, name):
    """--from-extract on the fixture extract: save() under the temporary folders (finalize() passed), the registered
    page size, 9-10 pt text, the extract written equals the one read (the MS5 rebuild is exact), and the after hook
    wrote the figure's tables."""
    rep = module(name).main(["--from-extract", str(FIX / f"{name}.json")])
    spec = style.figure_spec(name)
    assert Path(rep["pdf"]) == figs_env / "pdf" / f"{name}.pdf" and Path(rep["pdf"]).is_file()
    assert (spec.width, spec.height_in, spec.main) == (*SIZES[name], False)
    assert abs(rep["width_bp"] - spec.width_in * 72) <= 0.5 and abs(rep["height_bp"] - spec.height_in * 72) <= 0.5
    assert rep["outside_page"] == [] and rep["pages"] == 1
    assert all(style.TEXT_MIN_PT <= s <= style.TEXT_MAX_PT for s in rep["text_pt"])
    assert not any("dejavu" in f.lower() for f in rep["fonts"])
    assert json.loads((figs_env / "out" / f"{name}.json").read_text()) == fixture_payload(name)
    tables = figs_env / "tables"
    written = sorted(p.name for p in tables.iterdir()) if tables.is_dir() else []
    assert written == sorted(TABLES[name])


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
            style.check_source(p.relative_to(IN_ROOT).as_posix())
    assert opened and all(style.check_source(s) == s for s in inp.sources)
    from figs.common import json_number
    data = json.loads(json.dumps(data, allow_nan=False, default=json_number))
    assert data == fixture_data(name), STALE.format(name, name)
    assert fixture_payload(name)["sources"] == inp.sources


@pytest.mark.parametrize("name", NAMES)
def test_registry_keys_and_policy_checks(name):
    """The keys drawn lie within SUPP_POLICIES_MS5 (C29), pass check_policies, and are the script's KEYS; no
    supplementary-only key of MS3 or MS4 is drawn; every legend entry has a label."""
    mod = module(name)
    fig = mod.draw(fixture_data(name))
    keys = drawn_keys(fig)
    assert tuple(mod.KEYS) == style.SUPP_POLICIES_MS5[name]
    assert keys == set(style.SUPP_POLICIES_MS5[name]), keys
    style.check_policies(keys)
    assert not keys & (set(style.SUPP_ONLY_KEYS) | set(style.SUPP_ONLY_KEYS_MS4))
    for leg in fig.legends + [ax.get_legend() for ax in fig.axes if ax.get_legend() is not None]:
        assert all(t.get_text() for t in leg.get_texts())


def test_stored_layouts_equal_a_recomputation():
    """The layouts that build() stores in the extracts (sf_s1's x range and end labels, sf_e9's moved direct labels)
    are what layout() gives on the stored data, so a redraw from the extract draws what the build drew."""
    from figs.supp import sf_e9, sf_s1
    d = fixture_data("sf_s1")
    assert sf_s1.layout(d) == d["layout"]
    e = fixture_data("sf_e9")
    assert sf_e9.layout(e) == e["layout"]["moved"]
    fig = sf_e9.draw(e)
    assert fig._sublet_moved == [] and set(e["layout"]["moved"]) <= set(sf_e9.DIRECT)


@pytest.mark.parametrize("name", ["sf_s1", "sf_e9"])
def test_c47_relabeled_figures_draw_sublet_ms4_and_never_say_sublet(name):
    """C47 (design/ms6_spec.md M2, M4, §2 U43b): sf_s1 and sf_e9 draw S1's and E9's guard as sublet_ms4 and no legacy
    key; no drawn text and no string of the extract's labels (legend, caption, notes) or table labels says "Sublet",
    the paper's A8P around A9; sf_e9's caption no longer calls a line thicker; the tables name the guards' allowance."""
    d = fixture_data(name)
    fig = module(name).draw(d)
    keys = drawn_keys(fig)
    assert "sublet_ms4" in keys and not keys & set(style.LEGACY_KEYS)
    assert not [t.get_text() for t in fig.findobj(lambda a: hasattr(a, "get_text")) if "Sublet" in t.get_text()]
    labels = [d["labels"]] + ([d["tables"]["q28"]["rows"]] if name == "sf_s1" else [d["table"]["runs"]])

    def strings(x):
        if isinstance(x, str):
            yield x
        elif isinstance(x, dict):
            for k, v in x.items():
                if k not in ("tag", "default_source"):           # the summaries' tags and sources are data
                    yield from strings(v)
        elif isinstance(x, list):
            for v in x:
                yield from strings(v)
    assert not [t for t in strings(labels) if "Sublet" in t]
    if name == "sf_e9":
        assert "thicker" not in d["labels"]["caption"]
    else:
        from figs.supp import sf_s1
        assert "Both one-way guards run at $B_0$ = 10\\%" in sf_s1.q28_tex(d["tables"]["q28"], d)
        assert d["labels"]["caption"].startswith("The saving over all-fallback of " + style.POLICIES[sf_s1.KEY].label)


# ---------------------------------------------------------------------------------------------------------------
# sf_s1
def test_sf_s1_rows_bars_points_and_order():
    """Every register row of the sweep (meta.rows_order) and Q28's two rows is drawn once in its panel (the driver's
    rows.<row>.panel), sorted by span (largest at the top; ties in the register's order), with its bar from lo to hi
    and a marker at each point's median, both equal to the summaries; the default's median saving is a reference line
    in every panel, and the three panels share one x range, the layout's."""
    from figs.supp import sf_s1
    d = fixture_data("sf_s1")
    sweep, q28 = tree("s1/sweep/summary.json"), tree("s1/q28/summary.json")
    order = sweep["meta"]["rows_order"] + list(sf_s1.Q28_ROWS)
    assert list(d["rows"]) == order and sorted(i for p in sf_s1.PANELS for i in d["panels"][p]) == sorted(order)
    for rid in order:
        src = (q28 if rid in sf_s1.Q28_ROWS else sweep)["rows"][rid]
        r = d["rows"][rid]
        assert (r["lo"], r["hi"], r["span"], r["panel"]) == (src["lo"], src["hi"], src["span"], src["panel"])
        assert [p["name"] for p in r["points"]] == list(src["points"])
        assert [p["median"] for p in r["points"]] == [v["saving_pct_median"] for v in src["points"].values()]
        assert rid in d["panels"][src["panel"]]
    for p in sf_s1.PANELS:
        spans = [d["rows"][i]["span"] for i in d["panels"][p]]
        assert spans == sorted(spans, reverse=True)
    assert d["default_saving_pct"] == sweep["points"]["default"]["saving_pct"]["median"]
    assert {p: len(v) for p, v in d["panels"].items()} == {"a": 9, "b": 10, "c": 8}       # §7.1: 27 rows
    fig = sf_s1.draw(d)
    axes = fig.axes[:3]
    assert len({ax.get_xlim() for ax in axes}) == 1
    assert list(axes[0].get_xlim()) == pytest.approx(d["layout"]["x_range"])
    for ax, p in zip(axes, sf_s1.PANELS):
        ids = d["panels"][p]
        assert [t.get_text() for t in ax.get_yticklabels()] == [d["rows"][i]["label"] for i in ids]
        refs = [ln for ln in ax.lines if getattr(ln, "_sublet_role", "") == "reference"]
        assert len(refs) == 1 and list(refs[0].get_xdata()) == [d["default_saving_pct"]] * 2
        for y, rid in enumerate(ids):
            r = d["rows"][rid]
            (bar,) = [pa for pa in ax.patches if getattr(pa, "_sublet_row", None) == rid]
            assert bar.get_x() == pytest.approx(r["lo"]) and bar.get_width() == pytest.approx(r["hi"] - r["lo"])
            assert bar.get_y() + 0.5 * bar.get_height() == pytest.approx(y)
            (mk,) = [ln for ln in ax.lines if getattr(ln, "_sublet_row", None) == rid]
            assert list(mk.get_xdata()) == [pt["median"] for pt in r["points"] if pt["median"] is not None]
            # C47 (design/ms6_spec.md M2, M4): S1's policy is drawn as its configuration key sublet_ms4 (sf_s1.KEY)
            assert getattr(mk, "_sublet_policy") == sf_s1.KEY == "sublet_ms4" and mk.get_linestyle() == "None"
            ends = [t for t in ax.texts if getattr(t, "_sublet_row", None) == rid]
            if d["layout"]["end_labels"][rid]:
                want = [r["hi_text"]] if r["zero_span"] else [r["lo_text"], r["hi_text"]]
                assert sorted(t.get_text() for t in ends) == sorted(want)
            else:
                assert ends == [] and rid in d["layout"]["moved"]


def test_sf_s1_end_texts_and_layout_rule():
    """The end labels name the points at each bar end (the default's label where the default is the end; ties
    joined), Q28's lender modes read off and on, a row without a span says "no change"; every drawn end label lies
    inside its panel, outside its bar, clear of the y spine, and the moved rows are named in the caption."""
    from figs.supp import sf_s1
    d = fixture_data("sf_s1")
    for r in d["rows"].values():
        texts = {"default": sf_s1.end_text(r["default"]["label"]), **{p["name"]: p["end_text"] for p in r["points"]}}
        if r["zero_span"]:
            assert r["lo_text"] is None and r["hi_text"] == (sf_s1.LABELS["no_violation"] if r.get("no_violation")
                                                             else sf_s1.LABELS["no_change"])
        else:
            assert r["lo_text"] == ", ".join(texts[n] for n in r["lo_points"])
            assert r["hi_text"] == ", ".join(texts[n] for n in r["hi_points"])
    assert sf_s1.end_text("L-tr") == "off" and sf_s1.end_text("L-rf") == "on" and sf_s1.end_text("L-vr") == "on"
    assert sf_s1.end_text("x0.5") == r"$\times$0.5" and sf_s1.end_text("rho = 4") == r"$\rho$ = 4"
    assert sf_s1.end_text("P90") == "P90"
    fig = sf_s1.draw(d)
    r_ = fig.canvas.get_renderer()
    to_pt = 72.0 / fig.dpi
    for ax in fig.axes[:3]:
        bb = ax.get_window_extent(r_)
        for t in [t for t in ax.texts if getattr(t, "_sublet_role", "").startswith("end_label")]:
            tb = t.get_window_extent(r_)
            assert tb.x0 >= bb.x0 + (sf_s1.EDGE_CLEAR_PT - 0.6) / to_pt and tb.x1 <= bb.x1 + 0.5 / to_pt
            r = d["rows"][t._sublet_row]
            x_lo, x_hi = (ax.transData.transform((v, 0))[0] for v in (r["lo"], r["hi"]))
            assert tb.x1 <= x_lo + 0.1 or tb.x0 >= x_hi - 0.1
    for rid in d["layout"]["moved"]:
        assert d["rows"][rid]["label"] in d["labels"]["caption"]
    assert d["layout"]["all_fit"] == (not d["layout"]["moved"])


def test_s1_points_table_has_every_point(tmp_path):
    """s1_points.tex: the default, every point of the sweep's rows (all of meta.points), the mu row's points from
    E7's summary and Q28's two Sublet variants, with the saving medians, intervals and BL0a of their sources; the bar
    ends marked as the rows' lo_points and hi_points; a longtable."""
    from figs.supp import sf_s1
    d = fixture_data("sf_s1")
    sweep, q28, e7 = tree("s1/sweep/summary.json"), tree("s1/q28/summary.json"), tree("e7/main/summary.json")
    rows = d["tables"]["points"]
    names = [r["point"] for r in rows]
    assert names[0] == "default" and sorted(set(sweep["meta"]["points"])) == sorted(
        n for n in names if n in sweep["meta"]["points"])
    mu_pts = list(sweep["rows"]["mu"]["points"])
    assert [n for n in names if n in mu_pts] == mu_pts and [n for n in names if n in sf_s1.Q28_ROWS] == list(
        sf_s1.Q28_ROWS)
    assert len(rows) == 1 + sum(len(r["points"]) for r in d["rows"].values())
    for r in rows:
        if r["source"] == "s1_sweep":
            src = sweep["points"][r["point"]]
            assert r["bl0a_usd"] == src["bl0a_usd"][r["alignment"]]
        elif r["source"] == "e7":
            src = e7["runs"][r["point"][2:]]["Sublet"]
            assert r["bl0a_usd"] == e7["meta"]["bl0a_usd"][r["alignment"]]
        else:
            src = q28["runs"][sf_s1.Q28_VARIANTS[r["point"]]]["Sublet"]
        assert r["saving"]["median"] == src["saving_pct"]["median"]
        assert [r["saving"]["lo"], r["saving"]["hi"]] == src["saving_pct"]["median_ci95"]
        assert r["saving_total"]["median"] == src["saving_pct_total"]["median"]
        if r["row"] != "default":
            row = d["rows"][r["row"]]
            assert ("low" in r["ends"]) == (r["point"] in row["lo_points"])
            assert ("high" in r["ends"]) == (r["point"] in row["hi_points"])
    tex = sf_s1.points_tex(rows, d)
    assert r"\begin{longtable}" in tex and r"\end{longtable}" in tex
    body = tex.split(r"\endlastfoot")[1]
    assert body.count("\\\\\n") + body.count("\\\\*\n") == len(rows)
    # C50 (D5 review; D4's script items): the head on the later pages opens with "Table <n>, continued"
    head = tex.split(r"\endfirsthead")[1].split(r"\endhead")[0]                                         # C50
    assert head.lstrip().startswith(r"\multicolumn{9}{@{}l}{Table~\thetable, continued}")              # C50
    # C47 (U46 re-review): a page breaks only between assumptions' blocks: \\* ends every row but a block's last
    lasts = sum(1 for i, r in enumerate(rows) if i + 1 == len(rows) or rows[i + 1]["row"] != r["row"])
    assert body.count("\\\\\n") == lasts and body.count("\\\\*\n") == len(rows) - lasts > 0
    for r in rows[1:]:
        assert sf_s1._num(r["saving"]["median"], 2) in body
    # C47 (U46 print check): no analysis-step or design name in the settings and the head ("a5 tiers", "a5 pair",
    # "BL0a (USD)"), the drawn end texts included
    assert "All-fallback (USD)" in tex and "BL0a" not in tex.split(r"\toprule")[1] and "a5 " not in tex      # C47
    ends = [t for row in d["rows"].values() for t in (row["lo_text"], row["hi_text"], row["default"]["label"]) if t]
    assert ends and not [t for t in ends if "a5" in t]                                                   # C47
    assert d["rows"]["catalog"]["default"]["label"] == "MaaS" and sf_s1.setting_text("catalog", "a5 tiers") == \
        "Llama" and sf_s1.setting_text("load_scenario", "a5 pair") == "10 and 2 GB/s"                     # C47


def test_s1_q28_table_has_every_policy():
    """s1_q28.tex: one row per policy of part q28 (E7's eight and BL3, runs.rf's order) with the reference, both
    variants' median cost over BL0a, the refusals by reason and the violation victims, equal to the summary."""
    from figs.supp import sf_s1
    q28 = tree("s1/q28/summary.json")
    t = fixture_data("sf_s1")["tables"]["q28"]["rows"]
    assert [r["tag"] for r in t] == [k for k in q28["runs"]["rf"] if not k.endswith("_note")]
    # C47 (design/ms6_spec.md M2, M3, M4): the recorded keys sublet, a7_guard and bl5 as the configuration keys drawn
    # (a7_guard as a7_ms4, the guard around A7 at MS4's allowance: C46, review of the gate)
    assert len(t) == 9 and {r["key"] for r in t} == {"sublet_ms4", "a7_ms4", "a7", "a6", "bl5_lag", "bl1", "bl2",
                                                       "bl4", "bl3"}
    for r in t:
        rf, vr = q28["runs"]["rf"][r["tag"]], q28["runs"]["vr"][r["tag"]]
        assert r["rf"] == rf["overflow_over_bl0a"]["median"] and r["vr"] == vr["overflow_over_bl0a"]["median"]
        assert r["default"] == rf["reference"]["overflow_over_bl0a_median"]
        assert r["refused_unavailable"] == rf["refusals"]["unavailable"]["median"]
        assert r["refused_capacity"] == rf["refusals"]["capacity"]["median"]
        assert r["victims"] == vr["violation_victims"]["median"]
        assert r["label"] == style.POLICIES[r["key"]].label
    tex = sf_s1.q28_tex(fixture_data("sf_s1")["tables"]["q28"], fixture_data("sf_s1"))
    body = tex.split(r"\midrule")[1]
    # C47: a label split into lines (ms4_lib.label_lines: sublet_ms4's and a7_ms4's into three), the lines after
    # the first on rows of their own, so the body has a row per line, and every line is in it
    from figs.supp.ms4_lib import label_lines
    lines = {r["key"]: label_lines(r["label"], plus=True) for r in t}
    assert len(lines["sublet_ms4"]) == 3 and len(lines["a7_ms4"]) == 3                       # C47 (C46: a7_ms4)
    assert body.count("\\\\") == sum(len(v) for v in lines.values())
    assert all(sf_s1._tex(ln) in body for v in lines.values() for ln in v)


# ---------------------------------------------------------------------------------------------------------------
# sf_e9
def test_sf_e9_series_equal_the_summary():
    """sf_e9: (a) and (c) draw the e7f SML points, (b) the e7r SML points, ordered by sites x LLMs; every value (median,
    min, max) equals the summary's; (b)'s LP bound equals lp.<pt>.*.s_per_h at the LP points; the LLM-axis points
    are in the table only."""
    from figs.supp import sf_e9
    d = fixture_data("sf_e9")
    e9 = tree("e9/summary.json")
    tags = d["tags"]
    for p, base, sset in sf_e9.PANELS:
        pts = [pt for pt in e9["meta"]["grid"]["run_points"] if e9["points"][pt]["base"] == base
               and e9["points"][pt]["llm_set"] == sset]
        assert sorted(d[p]["points"]) == sorted(pts) and len(pts) == 7
        xs = [e9["points"][pt]["sites_x_llms"] for pt in d[p]["points"]]
        assert xs == sorted(xs)
        for key in sf_e9.RUN_KEYS:
            for field, s in d[p]["series"][key].items():
                assert s["x"] == xs
                for st in ("median", "min", "max"):
                    assert s[st] == [e9["points"][pt]["policies"][tags[key]][st][field] for pt in d[p]["points"]]
    lp = d["b"]["lp"]
    assert lp["point"] == [pt for pt in d["b"]["points"] if pt in e9["meta"]["grid"]["lp_points"]]
    for st in ("median", "min", "max"):
        assert lp[st] == [e9["lp"][pt][st]["s_per_h"] for pt in lp["point"]]
    assert sorted(d["grid"]["llm_axis_points"]) == ["e7f_V8_ML", "e7f_V8_S"]
    assert not {pt for p, _, _ in sf_e9.PANELS for pt in d[p]["points"]} & set(d["grid"]["llm_axis_points"])
    assert d["real_time_s_per_h"] == e9["meta"]["real_time_s_per_h"] and d["slow_slot_s"] == e9["meta"]["slow_slot_s"]


def test_sf_e9_styles_reference_lines_and_labels():
    """sf_e9: the slow loops in the registry styles with markers, the fast loops in the policy's color and width
    with its markers small (C47, print check of the gate: without markers the two fast loops printed as one grey), the
    LP bound as the registry's lower bound (black, dashed); real time and the slow slot as
    reference lines with their labels; the direct labels placed unless the layout moves them to the caption; log-log
    axes over ranges that hold every value; the legend: the guard's configuration key sublet_ms4 (C47) and A6."""
    from figs.supp import sf_e9
    d = fixture_data("sf_e9")
    fig = sf_e9.draw(d)
    ax_a, ax_b, ax_c = fig.axes[:3]
    for ax, p in ((ax_a, "a"), (ax_b, "b")):
        for key in sf_e9.RUN_KEYS:
            pol = style.POLICIES[key]
            lines = {getattr(ln, "_sublet_loop", None): ln for ln in ax.lines
                     if getattr(ln, "_sublet_policy", "") == key}
            slow, fast = lines["slow_loop_s_per_h"], lines["fast_loop_s_per_h"]
            # C47 (print check of the gate): the fast loop with the policy's marker at FAST_MARKER_SCALE of its size
            assert slow.get_marker() == pol.marker and fast.get_marker() == pol.marker
            assert slow.get_markersize() == pol.markersize
            assert fast.get_markersize() == pytest.approx(pol.markersize * sf_e9.FAST_MARKER_SCALE)
            assert slow.get_linewidth() == fast.get_linewidth() == pol.linewidth
            assert slow.get_color() == fast.get_color() == pol.color
            np.testing.assert_allclose(fast.get_ydata(), d[p]["series"][key]["fast_loop_s_per_h"]["median"])
        refs = [ln for ln in ax.lines if getattr(ln, "_sublet_role", "") == "reference"]
        assert [list(ln.get_ydata()) for ln in refs] == [[d["real_time_s_per_h"]] * 2]
        assert ax.get_xscale() == ax.get_yscale() == "log"
        assert list(ax.get_xlim()) == d["axes"]["x"]
    (lp,) = [ln for ln in ax_b.lines if getattr(ln, "_sublet_policy", "") == "lb"]
    assert lp.get_color() == "#000000" and lp.get_linestyle() == "--"
    refs = [ln for ln in ax_c.lines if getattr(ln, "_sublet_role", "") == "reference"]
    assert [list(ln.get_ydata()) for ln in refs] == [[d["slow_slot_s"]] * 2]
    assert [t.get_text() for t in by_role(ax_a, "reference_label")] == [d["labels"]["real_time"]]
    assert [t.get_text() for t in by_role(ax_c, "reference_label")] == [d["labels"]["slot"]] == ["5-min slot"]
    placed = {t.get_text() for ax in (ax_a, ax_b) for t in by_role(ax, "direct_label")}
    for k in sf_e9.DIRECT:
        assert (d["labels"][k] in placed) == (k not in d["layout"]["moved"])
    lo, hi = d["axes"]["y_ab"]
    vals = [v for p in ("a", "b") for k in sf_e9.RUN_KEYS for s in d[p]["series"][k].values()
            for st in ("median", "min", "max") for v in s[st] if v is not None]
    assert lo <= min(vals) and max(vals + [d["real_time_s_per_h"]]) <= hi
    assert ax_a.get_ylim()[0] == lo and ax_a.get_ylim()[1] >= hi and ax_b.get_ylim() == ax_a.get_ylim()
    (leg,) = [lg for lg in fig.legends if getattr(lg, "_sublet_role", "") == "legend_row"]
    # C47 (design/ms6_spec.md M2, M4): E9's guard drawn as sublet_ms4, under its registry label
    assert [t.get_text() for t in leg.get_texts()] == [style.POLICIES["sublet_ms4"].label, "Two-timescale PD"]


def test_sf_e9_moves_a_label_that_fits_nowhere(tmp_path):
    """sf_e9 with the LP bound on Sublet's fast loop (its label then fits nowhere nearer to it than to the loops):
    layout() moves it, the caption names the black dashed line, draw() leaves it out and save() passes; a layout
    that does not move a label which fits nowhere is refused."""
    from figs.supp import sf_e9
    d = copy.deepcopy(fixture_data("sf_e9"))
    s = d["b"]["series"][sf_e9.GUARD]["fast_loop_s_per_h"]           # C47: the guard's key, sublet_ms4
    lp = d["b"]["lp"]
    for st in ("median", "min", "max"):
        lp[st] = [v for v, x in zip(s[st], s["x"]) if x in lp["x"]]
    moved = sf_e9.layout(d)
    assert "lp" in moved
    d["layout"]["moved"] = moved
    d["labels"]["caption"] = sf_e9.caption(d)
    assert sf_e9.LABELS["moved"]["lp"].lower() in d["labels"]["caption"].lower()
    fig = sf_e9.draw(d)
    assert sf_e9.LABELS["lp"] not in {t.get_text() for ax in fig.axes for t in ax.texts}
    style.save(fig, "sf_e9", d, pdf_dir=tmp_path / "pdf", out_dir=tmp_path / "out")
    d["layout"]["moved"] = [k for k in moved if k != "lp"]
    with pytest.raises(style.StyleError, match="fits nowhere"):
        sf_e9.draw(d)


def test_e9_steps_table_has_every_run_and_lp():
    """e9_steps.tex: one row per run point (meta.grid.run_points, the LLM-axis points included) and policy with the
    medians of the summary, then one row per LP point; two longtables at footnotesize, the LP block with its own
    head."""
    from figs.supp import sf_e9
    d = fixture_data("sf_e9")
    e9 = tree("e9/summary.json")
    t = d["table"]
    pts = e9["meta"]["grid"]["run_points"]
    # C47 (design/ms6_spec.md M2, M4): E9's guard drawn as sublet_ms4
    assert [(r["point"], r["key"]) for r in t["runs"]] == [(pt, k) for pt in pts for k in ("sublet_ms4", "a6")]
    for r in t["runs"]:
        med = e9["points"][r["point"]]["policies"][d["tags"][r["key"]]]["median"]
        assert all(r[f] == med[f] for f in sf_e9.TABLE_RUN_FIELDS)
        assert r["n_units"] == e9["points"][r["point"]]["n_units"]["median"]
    assert [r["point"] for r in t["lp"]] == e9["meta"]["grid"]["lp_points"]
    for r in t["lp"]:
        assert all(r[f] == e9["lp"][r["point"]]["median"][f] for f in sf_e9.TABLE_LP_FIELDS)
    tex = sf_e9.steps_tex(t, d["grid"])
    assert tex.count(r"\begin{longtable}") == 2 and tex.count(r"\end{longtable}") == 2
    # C50 (D5 review; D4's script items): each head on the later pages opens with "Table <n>, continued", and the
    # uncaptioned LP longtable steps the table counter back first (s_f1.tex no longer does it after the \input)
    assert tex.count(r"{Table~\thetable, continued}") == 2 and tex.count(r"\addtocounter{table}{-1}") == 1  # C50
    second = tex.split(r"\end{longtable}")[1]                                                              # C50
    assert second.index(r"\addtocounter{table}{-1}") < second.index(r"\begin{longtable}")                  # C50
    runs_body = tex.split(r"\endlastfoot")[1].split(r"\end{longtable}")[0]
    lp_body = tex.split(r"\endlastfoot")[2].split(r"\end{longtable}")[0]
    # C47: sublet_ms4's label in three lines (ms4_lib.label_lines), the two after the first on rows of their own; C59:
    # in four, the allowance in words also split after " of the"
    from figs.supp.ms4_lib import label_lines, tex_label
    first, *more = label_lines(style.POLICIES["sublet_ms4"].label, plus=True, of=True)
    assert len(more) == 3                                                                                  # C59
    # C47 (U46 print check): every row of a point's block but its last ends in \\* (no page break inside a name or
    # between a point's policies), so each point's block ends in one \\
    assert runs_body.count("\\\\\n") + runs_body.count("\\\\*\n") == len(t["runs"]) + len(more) * len(pts) and \
        lp_body.count("\\\\\n") == len(t["lp"])                                                      # C47
    assert runs_body.count("\\\\\n") == len(pts)                                                     # C47
    assert runs_body.count(f" & {first} & ") == len(pts) and lp_body.count("LP bound") == 0
    assert all(runs_body.count(r"\quad " + tex_label(m)) == len(pts) for m in more)


# ---------------------------------------------------------------------------------------------------------------
# sf_slack
VERSIONED = {"npz": style.REPO / "code/analysis/out/a1_slack_series.npz",
             "json": style.REPO / "code/analysis/out/a1_lender_spotgpu.json",
             "a9b": style.REPO / "code/analysis/out/a9b_notice_buffer_24h.json"}


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sl1(data: dict, npz_path: Path, json_path: Path, a9b_path: Path) -> None:
    """Check SL-1 (§6.3): the extract's daily minimum, mean and maximum equal a recomputation from the npz without the
    trace's end within 1e-9 (days of 1440 / slot_min slots, the slot length from a9b's meta), its source digests
    equal the files', the end is the one slot at which every pool rises by half its capacity, in the last day, and
    the levels, capacities and zero shares equal their sources."""
    from figs.supp import sf_slack
    meta = json.loads(json_path.read_text())
    slot = json.loads(a9b_path.read_text())["meta"]["slot_min"]
    per_day = 1440 // slot
    with np.load(npz_path) as z:
        series = {k: np.asarray(z[k], dtype=float) for k in z.files}
    assert data["pools"] == list(series)
    assert data["source_sha256"] == {sf_slack.NPZ: _sha(npz_path), sf_slack.JSON: _sha(json_path),
                                     sf_slack.A9B: _sha(a9b_path)}
    assert data["slot_min"] == slot and data["slots_per_day"] == per_day
    n = len(next(iter(series.values())))
    t = data["tail"]["start_slot"]
    n_kept = n if t is None else t
    assert data["n_slots"] == n and data["n_kept"] == n_kept == n - data["tail"]["n_slots"]
    rises = np.vstack([np.diff(s) / meta[p]["capacity_gpus"] for p, s in series.items()]) >= sf_slack.TAIL_RISE
    assert (np.flatnonzero(rises.all(axis=0)) + 1).tolist() == ([] if t is None else [t])
    assert t is None or n - t <= per_day
    for pool, s in series.items():
        e = data["series"][pool]
        k = s[:n_kept]
        n_d = -(-k.size // per_day)
        assert len(e["min"]) == len(e["mean"]) == len(e["max"]) == n_d == data["n_days"]
        assert data["last_day_slots"] == k.size - (n_d - 1) * per_day
        for d in (0, n_d // 2, n_d - 1):
            blk = k[d * per_day:(d + 1) * per_day]
            assert (e["min"][d], e["max"][d]) == (blk.min(), blk.max()) and abs(e["mean"][d] - blk.mean()) <= 1e-9
        pad = np.full(n_d * per_day, np.nan)
        pad[:k.size] = k
        b = pad.reshape(n_d, per_day)
        for f, v in (("min", np.nanmin(b, 1)), ("mean", np.nanmean(b, 1)), ("max", np.nanmax(b, 1))):
            np.testing.assert_allclose(e[f], v, rtol=0, atol=1e-9)
        assert e["capacity_gpus"] == meta[pool]["capacity_gpus"] and e["zero_share"] == float(np.mean(k == 0))
        for q in sf_slack.LEVELS:
            lv = ((meta[pool]["leases"].get(q) or {}).get("window") or {}).get("L")
            assert e["levels"][q] == lv and ((q + "_note") in e["levels"]) == (lv is None)
    assert data["days"] == pytest.approx(n_kept * slot / 1440)


def test_sf_slack_sl1_on_the_versioned_files(tmp_path, monkeypatch):
    """SL-1 on the versioned analysis outputs (input root the repository): the extract's daily series against a
    recomputation from the npz without the trace's end within 1e-9 and the source digests; the end is the last 18
    slots, from the one slot at which every pool rises by half its capacity (§6.2); the figure drawn from the full
    series at its registered size passes finalize(); the A10 pool (no level above 0) says so in place of the P25
    label; the caption names the dropped end."""
    from figs.supp import sf_slack
    monkeypatch.delenv("SUBLET_FIGS_IN_ROOT", raising=False)
    inp = Inputs()
    data = json.loads(json.dumps(sf_slack.build(inp), allow_nan=False))
    assert inp.sources == [sf_slack.JSON, sf_slack.A9B, sf_slack.NPZ]
    sl1(data, VERSIONED["npz"], VERSIONED["json"], VERSIONED["a9b"])
    assert data["n_slots"] == 50993 and data["slot_min"] == 5                      # §6.1
    assert data["tail"]["start_slot"] == 50975 and data["tail"]["n_slots"] == 18    # §6.2
    assert data["n_days"] == 177 and data["last_day_slots"] == 287
    assert min(data["tail"]["rise_share"].values()) >= 0.5
    assert "last 18 slots (90 min)" in data["labels"]["caption"]
    assert data["no_level"] == ["A10"] and data["series"]["A10"]["zero_share"] > 0.9
    rep = save("sf_slack", data, tmp_path)
    assert rep["outside_page"] == []
    fig = sf_slack.draw(data)
    for ax, pool in zip(fig.axes[:6], data["pools"]):
        labels = [t.get_text() for t in by_role(ax, "reference_label")]
        refs = [ln for ln in ax.lines if getattr(ln, "_sublet_role", "") == "reference"]
        lv = data["series"][pool]["levels"]["p25"]
        assert labels == ([data["labels"]["no_level"]] if lv is None else [data["labels"]["level"]])
        assert [list(ln.get_ydata()) for ln in refs] == ([] if lv is None else [[lv, lv]])
        assert ax.get_ylim() == (0.0, float(data["series"][pool]["capacity_gpus"]))


def test_sf_slack_fixture_extract_against_its_slice():
    """The fixture extract is SL-1-consistent with the slice in the input tree (and the slice is the first slots of
    the versioned series); the panels are in the npz's order, two rows of three sharing x per column."""
    from figs.supp import sf_slack
    d = fixture_data("sf_slack")
    an = IN_ROOT / "code/analysis/out"
    sl1(d, an / "a1_slack_series.npz", an / "a1_lender_spotgpu.json", an / "a9b_notice_buffer_24h.json")
    assert d["tail"]["start_slot"] is None and d["n_kept"] == d["n_slots"]       # the slice has no end of the trace
    with np.load(an / "a1_slack_series.npz") as z, np.load(VERSIONED["npz"]) as full:
        for k in z.files:
            np.testing.assert_array_equal(z[k], full[k][:z[k].size])
    assert (an / "a1_lender_spotgpu.json").read_bytes() == VERSIONED["json"].read_bytes()
    a9b, a9b_full = (json.loads(f.read_text()) for f in (an / "a9b_notice_buffer_24h.json", VERSIONED["a9b"]))
    assert a9b["meta"] == {"slot_min": a9b_full["meta"]["slot_min"], "note": a9b["meta"]["note"]}
    assert {k: v["source"] for k, v in a9b["lenders"].items()} == \
        {f"a1:{p}": a9b_full["lenders"][f"a1:{p}"]["source"] for p in d["pools"]}
    fig = sf_slack.draw(d)
    axes = fig.axes[:6]
    assert len({ax.get_xlim() for ax in axes}) == 1
    fig.canvas.draw()
    drawn = {id(t) for t in style.drawn_texts(fig)}
    assert not [t for ax in axes[:3] for t in ax.get_xticklabels() if id(t) in drawn]       # x shared per column
    assert all([t for t in ax.get_xticklabels() if id(t) in drawn] for ax in axes[3:])
    for c in range(3):
        assert style.axes_rect_in(axes[c])[0] == pytest.approx(style.axes_rect_in(axes[c + 3])[0])
    assert sf_slack.daily(np.arange(25.0), 12) == {"min": [0.0, 12.0, 24.0], "mean": [5.5, 17.5, 24.0],
                                                    "max": [11.0, 23.0, 24.0]}
    np.testing.assert_allclose(sf_slack.day_centers(25, 12, 5), np.array([6.0, 18.0, 24.5]) * 5 / 1440)


def test_sf_slack_censored_tail_and_slot_length():
    """The trace's end (§6.2): the one slot at which every pool's slack rises by at least half its capacity at once,
    in the series' last day; none without such a slot; two such slots, or one before the last day, are errors. The
    slot length comes from a9b's meta, whose a1 entries must name the npz and hold its series lengths."""
    from figs.supp import sf_slack
    caps = {"a": 10.0, "b": 4.0}
    t = sf_slack.censored_tail({"a": np.array([1, 1, 2, 1, 9, 10.]), "b": np.array([0, 1, 1, 0, 3, 4.])}, caps, 4)
    assert (t["start_slot"], t["n_slots"]) == (4, 2) and t["rise_share"] == {"a": 0.8, "b": 0.75}
    assert t["min_share_after"] == {"a": 0.9, "b": 0.75}
    t = sf_slack.censored_tail({"a": np.array([1, 9, 9.]), "b": np.array([0, 1, 1.])}, caps, 4)
    assert (t["start_slot"], t["n_slots"]) == (None, 0)
    with pytest.raises(style.StyleError, match="expected one such slot"):
        sf_slack.censored_tail({"a": np.array([1, 9, 1, 9.]), "b": np.array([0, 3, 0, 3.])}, caps, 4)
    with pytest.raises(style.StyleError, match="expected one such slot"):       # mid-series: data, not the end
        sf_slack.censored_tail({"a": np.array([1, 9, 9, 9, 9, 9.]), "b": np.array([0, 3, 3, 3, 3, 3.])}, caps, 2)
    a9b = {"meta": {"slot_min": 5}, "lenders": {"a1:a": {"source": "x (a1_slack_series.npz)", "n_slots": 6}}}
    assert sf_slack.slot_minutes(a9b, {"a": 6}) == 5
    with pytest.raises(MissingKey, match="does not describe"):
        sf_slack.slot_minutes(a9b, {"a": 7})
    with pytest.raises(MissingKey, match="not a positive divisor"):
        sf_slack.slot_minutes({**a9b, "meta": {"slot_min": 7}}, {"a": 6})


@pytest.mark.parametrize("source", ["fixture", "versioned"])
def test_c62_fix_sf_slack_titles_at_caption_size_and_row_gap(figs_env, source):
    """C62 fix round (sf_slack): the six panel titles at the caption size (style.LABEL_PT; at TICK_PT as first
    restyled) on their letters' baseline, as the model of the PDF prints them (printed_baselines_pt) and in the PDF
    (PyMuPDF), within 0.05 pt; with ROW_GAP_IN = 0.22 in the bottom row's letters and titles end at least 4 pt below the
    top row's 3-pt x ticks (common.text_ink in the PDF draw)."""
    import fitz
    from figs.common import in_pdf, printed_baselines_pt, text_ink
    from figs.supp import sf_slack
    path = FIX / "sf_slack.json" if source == "fixture" else style.REPO / "code/sim/out/figs/sf_slack.json"
    d = json.loads(path.read_text())["data"]
    fig = sf_slack.draw(d)
    letters = [t for t in fig.texts if getattr(t, "_sublet_role", "") == "panel_letter"]
    titles = [t for t in fig.texts if t not in letters and t.get_text().strip()
              and any(t.get_position()[1] == lt.get_position()[1] for lt in letters)]
    assert len(letters) == len(titles) == 6
    assert all(t.get_fontsize() == pytest.approx(style.LABEL_PT) for t in letters + titles)
    for row in (slice(0, 3), slice(3, 6)):
        base = printed_baselines_pt(fig, letters[row] + titles[row])
        assert max(base) - min(base) < 0.05
    axes = [ax for ax in fig.axes if hasattr(ax, "_sublet_rect_in")]
    assert sf_slack.ROW_GAP_IN == 0.22

    def measure(r):
        tick_end = min(ax.get_window_extent(r).y0 for ax in axes[:3]) - \
            axes[0].xaxis.get_major_ticks()[0].tick1line.get_markersize()
        return tick_end - max(text_ink(t, r)[1] for t in letters[3:] + titles[3:])
    assert in_pdf(fig, measure) >= 4.0
    rep = sf_slack.main(["--from-extract", str(path)])
    spans = [s for b in fitz.open(str(rep["pdf"]))[0].get_text("dict")["blocks"] for ln in b.get("lines", [])
             if tuple(round(v, 3) for v in ln["dir"]) == (1.0, 0.0) for s in ln["spans"] if s["text"].strip()]
    for y0 in sorted({round(s["origin"][1], 1) for s in spans if "Bold" in s["font"]}):
        row = [s for s in spans if abs(s["origin"][1] - y0) < 1.0 and abs(s["size"] - style.LABEL_PT) < 0.01]
        assert len(row) == 6 and max(s["origin"][1] for s in row) - min(s["origin"][1] for s in row) < 0.05


# ---------------------------------------------------------------------------------------------------------------
# real-scale extremes
def _s1_real_scale(d: dict, seed: int) -> dict:
    """sf_s1's extract with the savings moved to the scale of the E7 week (default 28.4%, -1 to 54% across the rows,
    measurement 1 of the spec's §3.2), each row's lo, hi, span and end texts recomputed as the driver does, and the
    panels and layout recomputed as build() does."""
    from figs.supp import sf_s1
    d = copy.deepcopy(d)
    rng = np.random.default_rng(seed)
    big = {"alpha": (54.0, 10.0), "load_scenario": (-0.77, 35.0), "tightness": (20.0, 33.0)}
    dflt = 28.41
    d["default_saving_pct"] = dflt
    for rid, r in d["rows"].items():
        r["default"]["median"] = dflt
        for p in r["points"]:
            p["median"] = dflt if r["zero_span"] else float(dflt + rng.normal(0.0, 3.0))
        if rid in big and len(r["points"]) >= 2:
            r["points"][0]["median"], r["points"][-1]["median"] = big[rid]
        vals = [(p["median"], p["name"]) for p in r["points"]] + [(dflt, "default")]
        (lo, ln), (hi, hn) = min(vals), max(vals)
        texts = {"default": sf_s1.end_text(r["default"]["label"]), **{p["name"]: p["end_text"] for p in r["points"]}}
        r.update(lo=lo, hi=hi, span=hi - lo, lo_points=[ln], hi_points=[hn])
        if not r["zero_span"]:
            r.update(lo_text=texts[ln], hi_text=texts[hn])
    d["panels"] = sf_s1.panel_order(list(d["rows"].values()))
    d["layout"] = sf_s1.layout(d)
    d["labels"]["caption"] = sf_s1.caption(d)
    return d


def _e9_real_scale(d: dict) -> dict:
    """sf_e9's extract at the scale of the spec's measurement 4 (§5.2): Sublet's slow loop up to about 56 s per
    simulated hour, the LP bound up to about 16 s, ranges of -20% and +25% over the alignments."""
    from figs.supp import sf_e9
    d = copy.deepcopy(d)
    for p in ("a", "b", "c"):
        for key, ser in d[p]["series"].items():
            for field, s in ser.items():
                g = key == sf_e9.GUARD                    # C47: the guard (the frozen key sublet) as sublet_ms4
                top = {"slow_loop_s_per_h": 56.4 if g else 3.9, "fast_loop_s_per_h": 0.12,
                       "slow_step_p99_s": 44.4 if g else 2.3}[field]
                m = max(v for v in s["median"] if v is not None)
                s["median"] = [None if v is None else v * top / m for v in s["median"]]
                s["min"] = [None if v is None else 0.8 * v for v in s["median"]]
                s["max"] = [None if v is None else 1.25 * v for v in s["median"]]
    lp = d["b"]["lp"]
    lp["median"] = list(np.geomspace(0.54, 16.4, len(lp["median"])))
    lp["min"] = [0.9 * v for v in lp["median"]]
    lp["max"] = [1.1 * v for v in lp["median"]]
    vals = [v for p in ("a", "b") for ser in d[p]["series"].values() for s in ser.values()
            for st in ("median", "min", "max") for v in s[st] if v is not None]
    vals += lp["min"] + lp["max"]
    d["axes"]["y_ab"] = sf_e9.y_range(vals + [d["real_time_s_per_h"]])
    d["axes"]["y_c"] = sf_e9.y_range([v for s in (d["c"]["series"][k]["slow_step_p99_s"] for k in sf_e9.RUN_KEYS)
                                      for st in ("median", "min", "max") for v in s[st] if v is not None]
                                     + [d["slow_slot_s"]])
    d["layout"] = {**d["layout"], "moved": sf_e9.layout(d)}
    d["labels"]["caption"] = sf_e9.caption(d)
    return d


@pytest.mark.parametrize("seed", [0, 1, 2])
def test_sf_s1_on_real_scale_values(tmp_path, seed):
    """sf_s1 at the E7 week's scale: the layout keeps the data on at least FIT_MIN_SHARE of the axes, draws most
    rows' end labels, and save() passes (no text overlap, no ink outside the page, 9-10 pt)."""
    from figs.supp import sf_s1
    d = _s1_real_scale(fixture_data("sf_s1"), seed)
    a, b = d["layout"]["x_range"]
    lo, hi = sf_s1.data_extent(d)
    assert (hi - lo) / (b - a) >= sf_s1.FIT_MIN_SHARE - 1e-9 and a < lo and hi < b
    assert len(d["layout"]["moved"]) <= len(d["rows"]) // 3
    rep = save("sf_s1", d, tmp_path)
    assert rep["outside_page"] == [] and all(style.TEXT_MIN_PT <= s <= style.TEXT_MAX_PT for s in rep["text_pt"])


def test_sf_e9_completes_gated_lps_from_measurement_9(tmp_path, monkeypatch):
    """§5.9 as amended: an LP that E9's gate skipped (null values at one alignment) and that measurement 9 solved
    (out/ms5spec/e9_lp_gated.json, made for this summary, on E9's instance and schedule) enters the LP bound's median,
    minimum and maximum in (b) and the table, and the caption and the table say so; without the file nothing changes;
    a file made for another summary, or an LP on another instance, raises."""
    import hashlib
    import shutil
    from figs.supp import sf_e9
    root = tmp_path / "in"
    shutil.copytree(IN_ROOT / "code", root / "code")
    rel = "code/sim/out/e9/summary.json"
    e9 = json.loads((root / rel).read_text())
    pt = e9["meta"]["grid"]["lp_points"][-1]
    by = e9["lp"][pt]["by_alignment"]
    c = sorted(by)[0]
    for f in sf_e9.TABLE_LP_FIELDS:
        by[c][f] = None
    (root / rel).write_text(json.dumps(e9))
    monkeypatch.setenv("SUBLET_FIGS_IN_ROOT", str(root))
    plain = sf_e9.build(Inputs())
    assert plain["lp_completed"] == {} and "solved separately" not in plain["labels"]["caption"]
    vals = {"n_vars": 10, "nnz": 20, "n_sites_merged": 3, "solve_s": 7.0, "s_per_h": 1234.5, "peak_rss_mb": 99.0,
            "objective_over_bl0a": 0.5}
    job = {"point": pt, "c": int(c), "status": 0, "highs_model_status": 7, "same_instance_as_e9": True,
           "same_schedule_as_e9": True, **vals}
    g = {"meta": {"e9_summary_sha256": hashlib.sha256((root / rel).read_bytes()).hexdigest()},
         "code": {"lp_code_equal_to_e9": True}, "jobs": {f"e9:lp:pt={pt}:c={c}": job}}
    gp = root / sf_e9.GATED
    gp.parent.mkdir(parents=True, exist_ok=True)
    gp.write_text(json.dumps(g))
    inp = Inputs()
    d = sf_e9.build(inp)
    assert sf_e9.GATED in inp.sources and d["lp_completed"] == {pt: {"V": e9["points"][pt]["V"],
                                                                     "alignments": [int(c)]}}
    want = [float(e[f]) if c2 != c else 1234.5 for c2, e in by.items()
            for f in ("s_per_h",) if c2 == c or isinstance(e.get(f), (int, float))]
    i = d["b"]["lp"]["point"].index(pt)
    assert d["b"]["lp"]["median"][i] == pytest.approx(float(np.median(want)))
    assert d["b"]["lp"]["max"][i] == max(want) and d["b"]["lp"]["min"][i] == min(want)
    row = next(r for r in d["table"]["lp"] if r["point"] == pt)
    assert row["s_per_h"] == pytest.approx(float(np.median(want)))
    assert "not solved in E9's run" in d["labels"]["caption"] and "solved separately on the same instance" in \
        d["labels"]["caption"]
    assert "solved separately" in sf_e9.steps_tex(d["table"], d["grid"], d["lp_completed"])
    for bad in ({**g, "meta": {"e9_summary_sha256": "0" * 64}},
                {**g, "code": {"lp_code_equal_to_e9": False}},
                {**g, "jobs": {k: {**v, "same_instance_as_e9": False} for k, v in g["jobs"].items()}}):
        gp.write_text(json.dumps(bad))
        with pytest.raises(style.StyleError):
            sf_e9.build(Inputs())


def test_sf_e9_on_real_scale_values(tmp_path):
    """sf_e9 at the scale of measurement 4 with ranges over the alignments: the range bars drawn (0.6 pt, no caps),
    the y range from 0.01 to 10,000 s as §7.2 states for those values, and save() passes."""
    d = _e9_real_scale(fixture_data("sf_e9"))
    assert d["axes"]["y_ab"] == [0.01, 10000.0] and d["axes"]["y_c"] == [0.01, 1000.0]
    fig = module("sf_e9").draw(d)
    bars = [c for ax in fig.axes[:3] for c in ax.collections if type(c).__name__ == "LineCollection"
            and c.get_linewidths()[0] == pytest.approx(style.UNCERTAINTY_PT)]
    assert len(bars) >= 2 * 2 + 1 + 2 + 2
    rep = save("sf_e9", d, tmp_path)
    assert rep["outside_page"] == []


def test_e9_x_range_and_y_range_rules():
    """x_range: the 1-2-5 values around the points (50 and 5,000 for E9's 84-3,885); y_range: whole decades."""
    from figs.supp import sf_e9
    assert sf_e9.x_range([84, 3855, 3885]) == [50.0, 5000.0]
    assert sf_e9.x_range([28, 507]) == [20.0, 1000.0]
    assert sf_e9.y_range([0.025, 56.4, 3600.0]) == [0.01, 10000.0]
    assert sf_e9.y_range([0.11, 44.4, 300.0]) == [0.01, 1000.0]


@pytest.mark.skipif(not PDFLATEX.is_file(), reason="pdflatex is not installed")
def test_tables_compile(tmp_path):
    """The three tables, from the fixture extracts, compile with booktabs and longtable in a one-column IEEEtran page
    (longtable needs one-column mode), with no overfull box."""
    from figs.supp import sf_e9, sf_s1
    s1, e9 = fixture_data("sf_s1"), fixture_data("sf_e9")
    (tmp_path / "a.tex").write_text(sf_s1.points_tex(s1["tables"]["points"], s1))
    (tmp_path / "b.tex").write_text(sf_s1.q28_tex(s1["tables"]["q28"], s1))
    (tmp_path / "c.tex").write_text(sf_e9.steps_tex(e9["table"], e9["grid"]))
    (tmp_path / "doc.tex").write_text("\\documentclass[journal,onecolumn]{IEEEtran}\\usepackage{booktabs}"
                                      "\\usepackage{longtable}\n"
                                      "\\begin{document}\n\\input{a.tex}\n\\input{b.tex}\n\\input{c.tex}\nText.\n"
                                      "\\end{document}\n")
    env = dict(os.environ, TEXINPUTS=f"{style.REPO / 'paper' / 'layout_check'}:")
    r = subprocess.run([str(PDFLATEX), "-interaction=nonstopmode", "-halt-on-error", "doc.tex"], cwd=tmp_path,
                       capture_output=True, text=True, env=env, timeout=300)
    log = (tmp_path / "doc.log").read_text(errors="replace")
    assert r.returncode == 0 and "LaTeX Error" not in log, log[-2000:]
    assert "Overfull" not in log, [ln for ln in log.splitlines() if "Overfull" in ln]
