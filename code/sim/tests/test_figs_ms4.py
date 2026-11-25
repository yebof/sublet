"""Tests of the MS4 figure scripts: Fig. 4 (figs/fig4_e7_e3.py) and the MS4 supplementary figures of
design/sim_spec_ms4.md §8.2 (figs/supp/sf_e3_util.py, sf_e3_mu.py, sf_e4.py, sf_e5.py, sf_e7_mix.py, sf_e7_mu.py,
sf_e7_allow.py, sf_e8.py); §10, row test_figs_ms4.py. Quick: no raw data, no run outputs. The inputs are the input
tree tests/fixtures_figs_ms4/inputs/ (reduced-mode outputs of the MS4 drivers, README there) and the fixture extracts
tests/fixtures_figs_ms4/<name>.json (what each script writes on that tree; tests/fixtures_figs_ms4/refresh_extracts.py),
and every file is written under pytest's tmp_path (never into paper/ or code/sim/out/).

- Each script redraws with --from-extract from its fixture extract under temporary SUBLET_FIGS_*_DIR, with finalize()
  passing, and writes the extract it read; sf_e7_mix's after hook writes its three tables.
- Each script builds from the input tree (SUBLET_FIGS_IN_ROOT) the data of its fixture extract and opens no file
  outside the allowed roots (patched open).
- The keys drawn lie within FIGURE_POLICIES["fig4"] or SUPP_POLICIES_MS4 and pass check_policies.
- Fig. 4(c) labels b as the bound on siloed OPT over shared OPT (the copy argument) and draws no min(b, u) line (M41).
- sf_e7_mu's two legend rows (legend_row); sf_e7_allow's lines, axes and the theory default; sf_e5's zero or null
  shares on the x spine and coinciding A6 modes; sf_e8's off-scale values; sf_e4's cost models and bounds; every
  supplementary script on hand-modified extracts with real-scale extremes.

C50 (design/ms6_spec.md §7.2, the D5 review; §7.1 D4's script items): table3_intervals.tex opens its head on the
later pages with "Table <n>, continued". Each changed line names C50.

C52 (design/ms7/plan.md §4, unit T1, glossary G5): sf_e7_allow labels the open marker "Per-LLM allowance", Section VI's
name of min{B0, kappa B_on}, and its note names it so. Each changed line names C52.
"""
from __future__ import annotations

import builtins
import copy
import importlib
import io
import json
import os
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pytest

from figs import style
from figs.inputs import Inputs

FIX = Path(__file__).resolve().parent / "fixtures_figs_ms4"
IN_ROOT = FIX / "inputs"
SCRIPTS = {"fig4": "figs.fig4_e7_e3", "sf_e3_util": "figs.supp.sf_e3_util", "sf_e3_mu": "figs.supp.sf_e3_mu",
           "sf_e4": "figs.supp.sf_e4", "sf_e5": "figs.supp.sf_e5", "sf_e7_mix": "figs.supp.sf_e7_mix",
           "sf_e7_mu": "figs.supp.sf_e7_mu", "sf_e7_allow": "figs.supp.sf_e7_allow", "sf_e8": "figs.supp.sf_e8"}
NAMES = sorted(SCRIPTS)
SUPP = sorted(n for n in SCRIPTS if n != "fig4")
STALE = ("tests/fixtures_figs_ms4/{}.json is stale (the script's data changed): refresh it with "
         "`python tests/fixtures_figs_ms4/refresh_extracts.py --only {}` from code/sim")

# first-level mathtext subscripts (B_0, W_0, p_sh, N_Extra) are 4.9 pt at 7 pt (C62) and do not warn; save() would warn
# only below that (GlyphSizeWarning), which these tests do not check
pytestmark = pytest.mark.filterwarnings("ignore::figs.style.GlyphSizeWarning")


def module(name):
    return importlib.import_module(SCRIPTS[name])


def fixture_payload(name):
    return json.loads((FIX / f"{name}.json").read_text())


def fixture_data(name):
    return fixture_payload(name)["data"]


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


def texts(fig) -> list:
    return [t for t in fig.findobj(lambda a: hasattr(a, "get_text")) if t.get_text().strip()]


# ---------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("name", NAMES)
def test_from_extract_saves_and_finalize_passes(figs_env, name):
    """--from-extract on the fixture extract: save() under the temporary folders (finalize() passed), the registered
    page size, 9-10 pt text, and the extract written equals the one read (the MS5 rebuild is exact)."""
    rep = module(name).main(["--from-extract", str(FIX / f"{name}.json")])
    spec = style.figure_spec(name)
    assert Path(rep["pdf"]) == figs_env / "pdf" / f"{name}.pdf" and Path(rep["pdf"]).is_file()
    assert abs(rep["width_bp"] - spec.width_in * 72) <= 0.5 and abs(rep["height_bp"] - spec.height_in * 72) <= 0.5
    assert rep["outside_page"] == [] and rep["pages"] == 1
    assert all(style.TEXT_MIN_PT <= s <= style.TEXT_MAX_PT for s in rep["text_pt"])
    assert not any("dejavu" in f.lower() for f in rep["fonts"])
    assert json.loads((figs_env / "out" / f"{name}.json").read_text()) == fixture_payload(name)
    if name == "sf_e7_mix":
        from figs.supp.sf_e7_mix import TABLES
        for t in TABLES:
            assert (figs_env / "tables" / t).is_file(), t
    assert spec.main == (name == "fig4")


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
    """The keys drawn lie within the figure's set (FIGURE_POLICIES["fig4"], SUPP_POLICIES_MS4) and pass
    check_policies; Fig. 4 draws no supplementary-only key; every legend entry has a label."""
    mod = module(name)
    fig = mod.draw(fixture_data(name))
    keys = drawn_keys(fig)
    allowed = style.FIGURE_POLICIES[name] if name == "fig4" else style.SUPP_POLICIES_MS4[name]
    assert keys <= set(allowed), keys - set(allowed)
    style.check_policies(keys)
    if name == "fig4":
        assert not keys & (set(style.SUPP_ONLY_KEYS) | set(style.SUPP_ONLY_KEYS_MS4))
    else:
        assert tuple(mod.KEYS) == style.SUPP_POLICIES_MS4[name]
    for leg in fig.legends + [ax.get_legend() for ax in fig.axes if ax.get_legend() is not None]:
        assert all(t.get_text() for t in leg.get_texts())
    for ax in fig.axes:
        for t in ax.texts:
            if getattr(t, "_sublet_role", "") == "theory_label:limit":
                assert "limit" in t.get_text().lower() or "T→∞" in t.get_text()


def test_supplementary_scripts_register_their_sizes():
    """Each sf_* script registers the size of §8.2 (the registry of C18) and writes to paper/supplement/figures/
    unless SUBLET_FIGS_PDF_DIR is set (figs.common.supp_pdf_dir)."""
    sizes = {"sf_e3_util": ("W2", 2.2), "sf_e3_mu": ("W1", 2.4),        # C59: sf_e3_mu was 2.2 in
             "sf_e4": ("W1", 2.2), "sf_e5": ("W2", 2.5),
             "sf_e7_mix": ("W2", 2.2), "sf_e7_mu": ("W2", 2.5), "sf_e7_allow": ("W1", 2.2), "sf_e8": ("W1", 2.2)}
    # C47 (review of the gate): sf_e7_mu 2.5 in high (2.2 in §8.2), for the third legend row of the two guards
    assert set(sizes) == set(SUPP) == set(style.SUPP_POLICIES_MS4)
    for name, (w, h) in sizes.items():
        module(name)
        spec = style.figure_spec(name)
        assert (spec.width, spec.height_in, spec.main) == (w, h, False)


# ---------------------------------------------------------------------------------------------------------------
# C47 (design/ms6_spec.md M2, M4, §2 U43b): the relabeled MS4 supplementary figures
RELABELED = ("sf_e3_util", "sf_e3_mu", "sf_e5", "sf_e7_mix", "sf_e7_mu", "sf_e7_allow")


def _strings(x):
    if isinstance(x, str):
        yield x
    elif isinstance(x, dict):
        for v in x.values():
            yield from _strings(v)
    elif isinstance(x, list):
        for v in x:
            yield from _strings(v)


@pytest.mark.parametrize("name", RELABELED)
def test_c47_relabeled_figures_draw_configuration_keys_and_never_say_sublet(name):
    """C47: each relabeled figure draws no legacy key (style.LEGACY_KEYS) and the configuration key of its
    configuration (MS4's allowance: sublet_ms4; sf_e7_allow, whose axis sweeps B0: bl5_g1); no drawn text and no
    string of its extract's labels (the legend, notes and captions) says "Sublet", the paper's A8P around A9, while the
    extract keeps the summaries' tags (data, not text)."""
    data = fixture_data(name)
    fig = module(name).draw(data)
    keys = drawn_keys(fig) if name != "sf_e7_mix" else set(data["keys"])     # sf_e7_mix's bars carry no key
    assert not keys & set(style.LEGACY_KEYS), keys
    assert ("bl5_g1" if name == "sf_e7_allow" else "sublet_ms4") in keys
    assert not [t.get_text() for t in texts(fig) if "Sublet" in t.get_text()]
    assert not [t for t in _strings(data["labels"]) if "Sublet" in t]
    if "tags" in data:
        assert "Sublet" in data["tags"].values()


def test_c47_sf_e3_mu_legend_rows_above_the_panel():
    """C47: sf_e3_mu's legend (sublet_ms4's label alone is wider than the panel) stands in rows above the panel,
    each filled in order as far as the width allows, within the page width less the right margin and above the
    panel's top margin; the y axis has no legend headroom (its spine runs to the axes top). C47 (print check of the
    gate): the rows fill the reserve of sf_e3_mu.LEGEND_RESERVE column-aligned rows, no more (as relabeled, a reserve
    of three left 0.25 in of white between the legend and the axes). C62: two rows in a reserve of two."""
    from figs.supp import ms4_lib, sf_e3_mu
    fig = sf_e3_mu.draw(fixture_data("sf_e3_mu"))
    legs = [lg for lg in fig.legends if getattr(lg, "_sublet_role", "") == "legend_row"]
    got = [[t.get_text() for t in leg.get_texts()] for leg in legs]
    # C59 (RC19(3)): the guard's label in words on two lines (ms4_lib.wrap_wide), in the reserve of three rows
    two = "\n".join(ms4_lib.label_lines(style.POLICIES["sublet_ms4"].label))
    want = [two if k == "sublet_ms4" else style.POLICIES[k].label for k in style.legend_order(sf_e3_mu.LEGEND_KEYS)] + \
        [sf_e3_mu.LABELS["opt"]] + [t for _, t in style.env_handles("sharing")]
    # C62 (7-pt text): two rows, the guard's two-line label beside Two-timescale PD, then the other four entries, in the
    # reserve of two rows (C59 at 9 pt: three rows in a reserve of three, the guard alone in the first)
    assert len(legs) == sf_e3_mu.LEGEND_ROWS == 2 and [t for row in got for t in row] == want
    assert got[0] == [two, style.POLICIES["a6"].label]
    r = fig.canvas.get_renderer()
    ax = fig.axes[0]
    top_in = style.axes_rect_in(ax)[1] + style.axes_rect_in(ax)[3]
    assert sf_e3_mu.LEGEND_RESERVE == 2                                       # C62 (C59: 3; C47: 2)
    assert fig.get_size_inches()[1] - top_in == pytest.approx(ms4_lib.legend_reserve_top(2))
    for leg in legs:
        bb = leg.get_window_extent(r)
        assert bb.width / fig.dpi <= style.W1 - style.MARGIN_RIGHT + 1e-6 and bb.y0 / fig.dpi > top_in
    assert ax.spines["left"].get_bounds() is None


def test_c47_ms4_lib_keys_lines_and_legend_rows():
    """C47: ms4_lib maps the summaries' recorded style keys to the drawn configuration keys (tag_of(..., drawn=...);
    a missing key still raises), splits a long label into its lines, reads the allowance share of a B0 rule, and
    legend_rows_above refuses rows that need more than the reserve."""
    from figs.common import MissingKey
    from figs.supp import ms4_lib
    tags = {"Sublet": {"style_key": "sublet"}, "BL5": {"style_key": "bl5"}, "A6": {"style_key": "a6"}}
    assert ms4_lib.tag_of(tags, ("sublet_ms4", "bl5_lag", "a6"), "t", drawn=ms4_lib.DRAWN_KEY) == \
        {"sublet_ms4": "Sublet", "bl5_lag": "BL5", "a6": "A6"}
    with pytest.raises(MissingKey):
        ms4_lib.tag_of(tags, ("sublet_ms4",), "t")
    lab = style.POLICIES["sublet_ms4"].label
    # C59 (RC19(3)): the allowance in words (as built "($B_0=10\%$ BL0a)")
    assert ms4_lib.label_lines(lab) == ["Lagged RetroRenting + one-way guard", r"($B_0=10\%$ of the all-fallback bill)"]
    assert ms4_lib.label_lines(lab, plus=True) == ["Lagged RetroRenting", "+ one-way guard",
                                                   r"($B_0=10\%$ of the all-fallback bill)"]
    # C59: a legend label wider than LABEL_WRAP_IN with a parenthesis on two lines, every other label unchanged
    fig = style.new_figure("sf_e3_mu")
    h = object()
    assert ms4_lib.wrap_wide(fig, [(h, lab), (h, "Greedy renting"), (h, "SpotHedge-style, $N_{\\mathrm{Extra}}=0$")]) \
        == [(h, "\n".join(ms4_lib.label_lines(lab))), (h, "Greedy renting"), (h, "SpotHedge-style, $N_{\\mathrm{Extra}}=0$")]
    assert ms4_lib.label_lines("Greedy renting", plus=True) == ["Greedy renting"]
    assert ms4_lib.tex_label(lab) == lab and ms4_lib.tex_label("a_b & 5%") == r"a\_b \& 5\%"
    assert (ms4_lib.b0_share_text("0.1*BL0a"), ms4_lib.b0_share_text("0.1*BL0a", tex=True)) == ("10%", r"10\%")
    assert ms4_lib.b0_share_text(None) is None and ms4_lib.series_key("sublet_ms4:siloed") == "sublet_ms4"
    fig = style.new_figure("sf_e7_mu")
    style.panel_row(fig, (1, 1), legend=True)
    pairs = style.policy_handles(style.SUPP_POLICIES_MS4["sf_e7_mu"])
    rows = ms4_lib.split_rows(fig, pairs, max_rows=3)    # C47 (C46: a7_ms4's label too; the rows need three)
    with pytest.raises(style.StyleError, match="do not fit above the panels"):
        ms4_lib.legend_rows_above(fig, rows, n_rows=1)
    with pytest.raises(style.StyleError, match="more than 1"):
        ms4_lib.split_rows(fig, pairs, max_rows=1)


# ---------------------------------------------------------------------------------------------------------------
def test_c47_u46_print_check_of_the_ms4_supplement():
    """C47 (U46, the print check of the gate): sf_e5's legend closes its second row with the menus' black samples;
    sf_e3_util draws b = 1 once per policy where each siloed form equals its shared form, and its short agreement key
    sets the pair's markers on one solid line; sf_e7_allow names the original allowance; the caption drafts carry no
    build, milestone or experiment names; table3_intervals.tex at footnotesize, with W0 of all-fallback by
    definition."""
    import re
    from matplotlib.lines import Line2D
    from figs.supp import sf_e3_util, sf_e5, sf_e7_mix
    d5 = fixture_data("sf_e5")
    legs = [lg for lg in sf_e5.draw(d5).legends if getattr(lg, "_sublet_role", "") == "legend_row"]       # C47
    assert len(legs) == 2 and [t.get_text() for t in legs[1].get_texts()][-2:] == \
        [d5["labels"]["menu"]["short"], d5["labels"]["menu"]["long"]] == ["Short-notice menu", "Long-notice menu"]  # C47
    faces = [h.get_markerfacecolor() for h in legs[1].legend_handles[-2:]]                              # C47
    assert faces == ["black", "white"] and all(h.get_marker() == sf_e5.MENU_MARKER for h in legs[1].legend_handles[-2:])
    assert sf_e5.MENU_MARKER not in {style.policy(k).marker for k in sf_e5.KEYS}                       # C47
    assert "filled: short-notice menu (leases with a 5-min guaranteed period and 0, 1 or 2 min notice, plus " \
        "protected capacity), open: long-notice menu (leases with a 5-min guaranteed period and 60, 120 or 240 min " \
        "notice, plus protected capacity)" in d5["labels"]["note"]                                     # C47
    assert sf_e5.menu_text(None) == "" and sf_e5.menu_text({"contracts": [{"tau_min": None}]}) == ""     # C47
    for name in ("sf_e3_util", "sf_e3_mu", "sf_e5", "sf_e7_mix", "sf_e7_mu", "sf_e7_allow"):
        note = fixture_data(name)["labels"]["note"]
        assert not re.search(r"\(M\d+\)|ratio_LB|Q39|zero_or_null|s5_tau5|MS4's|e7r", note), name     # C47
    # sf_e3_util: at b = 1 the four series left, evenly spread; the siloed lines start at their shared forms' markers
    d3 = copy.deepcopy(fixture_data("sf_e3_util"))
    assert d3["single_b1"]["every_pair"] and "only the shared forms are drawn there" in d3["labels"]["note"]  # C47
    for p in ("a", "b", "c"):
        d3[p]["bl5_lag"] = copy.deepcopy(d3[p]["sublet_ms4"])                 # C47: the pair of the agreement key
    d3["agree"] = sf_e3_util.identity_entry(d3)
    fig = sf_e3_util.draw(d3)
    for ax in fig.axes[:3]:
        at1 = []
        for ln in (x for x in ax.lines if getattr(x, "_sublet_role", "") == "markers"):
            x, y = np.asarray(ln.get_xdata(), float), np.asarray(ln.get_ydata(), float)
            at1 += [(ln._sublet_series, float(np.log2(v))) for v in x[(np.abs(np.log2(x)) < 0.5) & np.isfinite(y)]]
        assert [k for k, _ in sorted(at1, key=lambda q: q[1])] == ["bl5_lag", "a6", "sublet_ms4", "bl2"]   # C47
        assert np.diff(sorted(o for _, o in at1)) == pytest.approx([0.2] * 3)                              # C47
        shared_x = dict(at1)
        for ser, shared in d3["single_b1"]["pairs"]:
            (ln,) = [x for x in ax.lines if getattr(x, "_sublet_series", "") == ser and x.get_linestyle() == "--"]
            assert np.log2(ln.get_xdata()[0]) == pytest.approx(shared_x[shared])                           # C47
    (key,) = [a for ax in fig.axes for a in ax.get_children() if getattr(a, "_sublet_agree", "") == "short"]  # C47
    drawn = [ln for ln in key.findobj(Line2D) if ln.get_marker() not in (None, "None", "none", "")]
    assert sorted(ln.get_markerfacecolor() for ln in drawn) == sorted([style.policy("sublet_ms4").color, "white"])
    assert all(ln.get_linestyle() == "-" for ln in key.findobj(Line2D) if ln.get_xydata().size)          # C47
    # table3_intervals.tex: footnotesize, the caption names its scope, BL0a's W0 by definition
    t = fixture_data("sf_e7_mix")["tables"]["table3_intervals"]
    tex = sf_e7_mix.table3_intervals_tex(t)
    assert tex.startswith(r"{\footnotesize") and tex.rstrip().endswith(r"\end{longtable}}")                  # C47
    assert r"\caption{E7 on its main week (" in tex and "main-week table" not in tex                         # C47
    assert r"\multicolumn{5}{@{}l}{Table~\thetable, continued}" in tex.split(r"\endfirsthead")[1]          # C50
    assert " & 1 (by definition) & -- & 0 " in tex and sf_e7_mix.defined_text({"median": 1.0, "n": 4,
                                                                                "note": "1 by definition"}) is None


def test_fig4_c_labels_b_as_the_copy_bound():
    """Fig. 4(c): the grey dashed line y = b (an upper bound: siloed OPT <= b * shared OPT, the copy argument,
    attained on C3-P7's instance) labeled as the bound on siloed OPT ("b, bound on siloed OPT" or "b, bound on OPT",
    whichever form fits; print check 2026-10-27), and no min(b, u) line (M41)."""
    data = fixture_data("fig4")
    fig = module("fig4").draw(data)
    ax_c = fig.axes[2]
    th = [ln for ln in ax_c.lines if getattr(ln, "_sublet_role", "") == "theory:upper"]
    assert len(th) == 1
    x, y = np.asarray(th[0].get_xdata(), float), np.asarray(th[0].get_ydata(), float)
    np.testing.assert_allclose(y, x, rtol=0, atol=0)
    np.testing.assert_allclose(x, data["c"]["theory"]["b"])
    assert data["c"]["theory"]["upper_b"] == data["c"]["theory"]["b"]
    labels = [t.get_text() for t in ax_c.texts if getattr(t, "_sublet_role", "") == "theory_label:upper"]
    forms = [" ".join(s.split()) for s in module("fig4").LABELS["theory_forms"]]
    assert all("bound on" in f and "OPT" in f for f in forms)
    assert len(labels) == 1 and " ".join(labels[0].split()) in forms
    assert th[0].get_linestyle() == "--" and th[0].get_color() == style.THEORY_GREY
    assert not [t for t in texts(fig) if "min(" in t.get_text()]
    assert not any(ln for ax in fig.axes for ln in ax.lines if getattr(ln, "_sublet_role", "").startswith("theory")
                   and ln is not th[0])
    assert ax_c.get_xscale() == "log" and ax_c.get_yscale() == "log"


def test_fig4_c_y_range_from_the_data_and_stars_named():
    """Fig. 4(c): the y axis spans the data and brackets (at least up to C3_TOP_MIN), not the bound's b = 32, which
    leaves through the top with its label placed on the drawn part; the OPT legend entry is a star alone (the brackets
    are unjoined) and the caption names the stars siloed OPT; (a): BL0a's line above the bars in a white casing."""
    from figs import fig4_e7_e3 as f4
    data = fixture_data("fig4")
    fig = f4.draw(data)
    ax_a, ax_c = fig.axes[0], fig.axes[2]
    c = data["c"]
    vals = [v for k in f4.C_KEYS for f in ("median", "ci_lo", "ci_hi") for v in c[k][f] if v is not None]
    vals += [v for f in ("point", "lo", "hi") for v in c["opt"][f] if v is not None]
    top = ax_c.get_ylim()[1]
    assert max(vals) < top < 2 * max(max(vals), f4.C_TOP_MIN) and top < max(c["theory"]["b"])
    (lab,) = [t for t in ax_c.texts if getattr(t, "_sublet_role", "") == "theory_label:upper"]
    assert lab.xy[1] <= top
    (leg,) = [lg for lg in fig.legends if getattr(lg, "_sublet_role", "") == "legend_row"]
    opt = [h for h, t in zip(leg.legend_handles, leg.get_texts()) if t.get_text() == style.POLICIES["opt"].label]
    assert len(opt) == 1 and opt[0].get_linestyle() in ("None", "none") and opt[0].get_marker() == "*"
    assert "Grey: b, the bound on siloed OPT (stars;" in data["labels"]["caption"]
    assert data["labels"]["caption_chars"] <= 3 * 140
    (bl0a,) = [ln for ln in ax_a.lines if getattr(ln, "_sublet_policy", "") == "bl0a"]
    bars = [pt for pt in ax_a.patches]
    assert bl0a.get_zorder() > max(pt.get_zorder() for pt in bars)
    assert any(type(pe).__name__ == "Stroke" for pe in bl0a.get_path_effects())
    # at a six-digit own capacity over 4 alignments x 3 seeds, the caption is 417 characters (§8.1)
    assert len(f4.caption(145715.69, 4, 3, 8.0)) == 417


def test_sf_e3_mu_opt_bracket_has_its_own_slot():
    """sf_e3_mu: the siloed/shared OPT bracket is dodged into a slot of its own, apart from every series' x (as built
    it sat on A6's marker and bar at the undodged mu)."""
    fig = module("sf_e3_mu").draw(fixture_data("sf_e3_mu"))
    ax = fig.axes[0]
    opt = [ln for ln in ax.lines if getattr(ln, "_sublet_policy", "") == "opt"]
    xs_opt = {round(float(x), 9) for ln in opt for x in ln.get_xdata()}
    xs_ser = {round(float(x), 9) for ln in ax.lines if getattr(ln, "_sublet_policy", "") not in ("", "opt")
              for x in ln.get_xdata()}
    assert xs_opt and not xs_opt & xs_ser


def test_sf_e7_mu_two_legend_rows():
    """sf_e7_mu: the eight keys in two legend rows above the panels (one row does not fit at 9 pt), within the
    page width less the right margin, in the registry's legend order.

    C47 (design/ms6_spec.md M2, M3, M4): with sublet_ms4's label legend_row's two column-aligned rows are 8.38 in
    wide, so the entries stand side by side in two legend rows of their own (ms4_lib.legend_rows_above), the first
    row filled as far as the width allows; together they hold the eight keys in the legend order. C47 (C46, review of
    the gate): with a7_ms4's label the entries take three rows, the two guards in the first and the other six halved
    over the next two (the figure 2.5 in high)."""
    from figs.supp import ms4_lib
    fig = module("sf_e7_mu").draw(fixture_data("sf_e7_mu"))
    legs = [lg for lg in fig.legends if getattr(lg, "_sublet_role", "") == "legend_row"]
    assert len(legs) == module("sf_e7_mu").LEGEND_ROWS == 3                  # C47: one legend per row, three rows
    keys = style.SUPP_POLICIES_MS4["sf_e7_mu"]
    # C59 (RC19(3)): the guards' labels in words on two lines each (ms4_lib.wrap_wide)
    two = {k: "\n".join(ms4_lib.label_lines(style.POLICIES[k].label)) for k in ("a7_ms4", "sublet_ms4")}
    assert [t.get_text() for leg in legs for t in leg.get_texts()] == \
        [two.get(k, style.POLICIES[k].label) for k in style.legend_order(keys)]
    assert [len(leg.get_texts()) for leg in legs] == [2, 3, 3]              # C47: the guards, then halves
    assert [t.get_text() for t in legs[0].get_texts()] == [two[k] for k in ("a7_ms4", "sublet_ms4")]
    r = fig.canvas.get_renderer()
    boxes = [leg.get_window_extent(r) for leg in legs]
    assert all(b.width / fig.dpi <= style.W2 - style.MARGIN_RIGHT + 1e-6 for b in boxes)
    assert (boxes[0].y1 - boxes[-1].y0) / fig.dpi <= 3 * style.LEGEND_ROW + 1e-6               # C47: three rows
    assert all(b.y1 <= a.y0 for a, b in zip(boxes, boxes[1:]))
    ax_top = max(style.axes_rect_in(ax)[1] + style.axes_rect_in(ax)[3] for ax in fig.axes[:2])
    assert boxes[-1].y0 / fig.dpi > ax_top + style.MARGIN_TOP - 1e-6
    with pytest.raises(style.StyleError, match="wider than the figure"):
        f2 = style.new_figure("sf_e7_mu")
        style.panel_row(f2, (1, 1), legend=True, sharey=(False, True))
        style.legend_row(f2, keys)
    with pytest.raises(style.StyleError, match="wider than the figure"):     # C47: nor in two aligned rows
        f2 = style.new_figure("sf_e7_mu")
        style.panel_row(f2, (1, 1), legend=2, sharey=(False, True))
        style.legend_row(f2, keys, rows=2)
    assert ms4_lib.LEGEND_HANDLE_SHORT == 1.4
    # BL4's yellow line in a black casing, in the panel and in its legend sample (it printed lighter than the
    # reference line in greyscale)
    from figs.supp.ms4_lib import CASING_PT
    ax_b = fig.axes[1]
    case = [ln for ln in ax_b.lines if getattr(ln, "_sublet_role", "") == "casing"]
    (bl4,) = [ln for ln in ax_b.lines if getattr(ln, "_sublet_policy", "") == "bl4"]
    assert len(case) == 1 and case[0].get_color() == "#000000" and case[0].get_zorder() < bl4.get_zorder()
    assert case[0].get_linewidth() == pytest.approx(bl4.get_linewidth() + CASING_PT)
    np.testing.assert_allclose(case[0].get_xdata(), bl4.get_xdata())
    assert not [ln for ax in fig.axes for ln in ax.lines if getattr(ln, "_sublet_role", "") == "casing"
                and ln is not case[0]]


def test_ms4_lib_log_ticks_at_least_three():
    """ms4_lib.log_ticks gives at least LOG_MIN_TICKS ticks where a ladder does (as built, 2 ticks over 2-3
    decades, since 1, 2, 5 gave too many): 1, 3 per decade there, the earlier ladders unchanged elsewhere."""
    from figs.supp.ms4_lib import LOG_MAX_TICKS, LOG_MIN_TICKS, log_ticks
    assert log_ticks(0.0035, 0.69) == [0.01, 0.03, 0.1, 0.3]
    assert log_ticks(0.03, 9) == [0.03, 0.1, 0.3, 1.0, 3.0]
    assert log_ticks(0.6, 21) == [1.0, 2.0, 5.0, 10.0, 20.0] and log_ticks(0.01, 1) == [0.01, 0.1, 1.0]
    for lo in (0.001, 0.002, 0.004, 0.007):
        for hi in (0.3, 0.6, 2.0, 9.0):
            t = log_ticks(lo, hi)
            assert LOG_MIN_TICKS <= len(t), (lo, hi, t)
            assert len(t) <= LOG_MAX_TICKS or hi / lo > 1e3, (lo, hi, t)


def test_sf_e7_allow_draws_a_share_only_where_its_b0_matches(tmp_path, monkeypatch):
    """sf_e7_allow: a cell whose B0_usd is not its share x meta.bl0a_usd is not drawn at the share (null with a
    note, and a warning); the y labels name the quantities."""
    root = tmp_path / "in"
    shutil.copytree(IN_ROOT / "code/sim/out/e7/allow", root / "code/sim/out/e7/allow")
    f = root / "code/sim/out/e7/allow/summary.json"
    s = json.loads(f.read_text())
    s["cells"]["0.05"]["L-tr"]["B0_usd"] *= 1.5
    f.write_text(json.dumps(s))
    monkeypatch.setenv("SUBLET_FIGS_IN_ROOT", str(root))
    from figs.supp import sf_e7_allow
    with pytest.warns(UserWarning, match="not drawn at the share"):
        data = json.loads(json.dumps(sf_e7_allow.build(Inputs())))
    i = data["a"]["share_pct"].index(5.0)
    assert data["a"]["median"][i] is None and "not 0.05 x meta.bl0a_usd" in data["a"]["note"][i]
    assert data["b"]["value"][i] is None and data["b"]["note"][i] == data["a"]["note"][i]
    assert sum(v is None for v in data["a"]["median"]) == 1
    # C62: (b)'s y label in one line, as (a)'s (C47, at 9 pt: in two lines, since the two legend rows left axes shorter
    # than the label in one line; at 7.97 pt it is 1.15 in along 1.49-in axes)
    assert (data["labels"]["a_y"], data["labels"]["b_y"]) == ("Cost / all-fallback", "Worst cost / all-fallback")


def test_sf_e7_allow_lines_axes_and_default():
    """sf_e7_allow: Sublet's runs against B0 / BL0a on a log x axis over the sweep's shares, the unguarded BL5 as a
    horizontal line at its value, Algorithm 1's default as an open marker at its share b0_auto_usd / BL0a, one panel of
    cost / BL0a under L-tr and one of W0.

    C47 (design/ms6_spec.md M2, M4): the swept guard drawn as bl5_g1 (its axis sweeps B0), the unguarded lagged BL5 as
    bl5_lag; the two in two legend rows of one column, and the default named by a direct label next to its marker.
    C62: the two side by side in one legend row (3.27 in at 7 pt in W1's 3.43 in), the panels taking the freed row;
    the default's label, where it needs a leader, in the form nearer to its marker (sf_e7_allow.default_label)."""
    data = fixture_data("sf_e7_allow")
    fig = module("sf_e7_allow").draw(data)
    ax_a, ax_b = fig.axes[:2]
    share = 100.0 * data["meta"]["b0_auto_usd"] / data["meta"]["bl0a_usd"]
    assert data["default"]["share_pct"] == pytest.approx(share, rel=1e-12)
    assert sorted(data["a"]["share_pct"]) == pytest.approx([0.5, 1.0, 2.0, 5.0, 10.0, 20.0])
    for ax, ys, bl5, dflt in ((ax_a, data["a"]["median"], data["bl5"]["L-tr"], data["default"]["a"]["median"]),
                              (ax_b, data["b"]["value"], data["bl5"]["W0"], data["default"]["b"]["value"])):
        assert ax.get_xscale() == "log"
        lo, hi = ax.get_xlim()
        assert lo < min(data["a"]["share_pct"] + [share]) and hi > max(data["a"]["share_pct"])
        bl5_lines = [ln for ln in ax.lines if getattr(ln, "_sublet_policy", "") == "bl5_lag"]          # C47
        assert len(bl5_lines) == 1 and list(bl5_lines[0].get_ydata()) == [bl5, bl5]
        sub = [ln for ln in ax.lines if getattr(ln, "_sublet_policy", "") == "bl5_g1"]                 # C47
        series = [ln for ln in sub if ln.get_linestyle() != "None"]
        opened = [ln for ln in sub if ln.get_linestyle() == "None" and ln.get_markerfacecolor() == "white"]
        assert len(series) == 1 and list(series[0].get_ydata()) == pytest.approx(ys)
        assert len(opened) == 1 and list(opened[0].get_xdata()) == [pytest.approx(share)]
        assert list(opened[0].get_ydata()) == [dflt]
        refs = [ln for ln in ax.lines if getattr(ln, "_sublet_role", "") == "reference"]
        assert any(list(ln.get_ydata()) == [1.0, 1.0] for ln in refs)
    assert ax_a.get_ylabel() == data["labels"]["a_y"] and ax_b.get_ylabel() == data["labels"]["b_y"]
    assert data["meta"]["kappa10_cap_usd"] is not None
    # C62: the legend's two policies side by side in one row (C47, at 9 pt: one above the other); the default's direct
    # label in its guard's label color
    (leg,) = [lg for lg in fig.legends if getattr(lg, "_sublet_role", "") == "legend_row"]
    assert [t.get_text() for t in leg.get_texts()] == [style.POLICIES[k].label for k in ("bl5_g1", "bl5_lag")]
    assert leg._ncols == 2 and module("sf_e7_allow").LEGEND_ROWS == 1                                 # C62
    fig.canvas.draw()                                    # places the legend's texts
    r = fig.canvas.get_renderer()
    boxes = [t.get_window_extent(r) for t in leg.get_texts()]
    assert abs(boxes[0].y0 - boxes[1].y0) < 0.5 and boxes[0].x1 < boxes[1].x0                        # C62: one row
    assert style.axes_rect_in(ax_a)[3] == pytest.approx(
        style.FIGURES["sf_e7_allow"].height_in - style.MARGIN_BOTTOM - style.MARGIN_TOP - style.LEGEND_ROW)
    lab = [t for ax in (ax_a, ax_b) for t in ax.texts if getattr(t, "_sublet_role", "") == "direct_label:default"]
    # C47 (U46 print check): the original allowance labeled in each panel, not "Algorithm 1 default" (Algorithm 1 v2's
    # default allowance is Sublet's min{W_k, LB'}); C52 (design/ms7/plan.md §4, T1 glossary G5): by the paper's name,
    # "Per-LLM allowance" (as built "Original allowance")
    assert [t.axes for t in lab] == [ax_a, ax_b]                                                       # C47
    assert all(" ".join(t.get_text().split()) == data["labels"]["default"] == "Per-LLM allowance" for t in lab)  # C52
    assert all(t.get_color() == style.policy("bl5_g1").label_color for t in lab)                      # C47
    assert "the per-LLM allowance min{B0, kappa B_on} (B0 auto" in data["labels"]["note"]              # C52
    assert "original allowance" not in data["labels"]["note"].lower()                                  # C52


def test_sf_e7_mix_tables():
    """sf_e7_mix's tables: every Table III row and column with its interval, the total accounting with the own
    capacity per alignment, the aborts of the A8 rows per stress mode."""
    from figs.supp import ms4_lib
    from figs.supp import sf_e7_mix as m
    data = fixture_data("sf_e7_mix")
    t = data["tables"]
    t3 = json.loads((IN_ROOT / "code/sim/out/e7/table3.json").read_text())
    tex = m.table3_intervals_tex(t["table3_intervals"])
    assert [r["tag"] for r in t["table3_intervals"]["rows"]] == t3["order"]
    for r in t["table3_intervals"]["rows"]:
        # C47 (design/ms6_spec.md U43b): the registry label of the key drawn for the recorded style key, not the
        # recorded label, in lines on the block's first rows (ms4_lib.label_lines)
        assert r["key"] == ms4_lib.DRAWN_KEY.get(r["style_key"], r["style_key"])
        assert r["label"] == style.POLICIES[r["key"]].label and r["recorded_label"] == t3["rows"][r["tag"]]["label"]
        assert all(ln in tex for ln in m._tex_lines(r["label"], plus=True))
        assert set(r["cells"]) == {c for c, _ in m.T3_COLUMNS}
    assert t["table3_intervals"]["rows"][0]["label"] != t3["rows"][t3["order"][0]]["label"]   # C47: not "Sublet"
    # C47 (U46 print check): every row of a policy's block but its last ends in \\* (no page break inside a block)
    assert tex.count(r"\\" + "\n") + tex.count(r"\\*" + "\n") >= len(t3["order"]) * len(m.T3_COLUMNS)    # C47
    assert tex.count(r"\\*" + "\n") == len(t3["order"]) * (len(m.T3_COLUMNS) - 1)                        # C47
    assert "e7r" not in tex and "(slow grid, reduced menu)" in tex and r"{\footnotesize" in tex          # C47
    assert r"\begin{longtable}" in tex and r"\end{longtable}" in tex
    sub = t3["rows"]["Sublet"]["usd"]["overflow"]
    assert t["table3_intervals"]["rows"][0]["cells"]["usd.overflow"]["median"] == sub["median"]
    tot = m.total_accounting_tex(t["total_accounting"])
    main = json.loads((IN_ROOT / "code/sim/out/e7/main/summary.json").read_text())
    assert t["total_accounting"]["own_capacity_usd"] == main["meta"]["own_capacity_usd"]
    order = [ms4_lib.DRAWN_KEY.get(t3["rows"][tag]["style_key"], t3["rows"][tag]["style_key"])
             for tag in t3["order"]]                                       # Table III's order (C47: drawn keys)
    assert [r["key"] for r in t["total_accounting"]["rows"]] == [k for k in order if k in m.KEYS] + ["bl0b", "bl0a"]
    assert data["keys"] == [k for k in order if k in m.KEYS] and set(data["keys"]) == set(m.KEYS)
    # every count, scope and slot length of the captions is read (here 1 alignment x 1 seed, 120 min, 5-min slots)
    g, sg = t["total_accounting"]["grid"], t["stress_aborts"]["grid"]
    assert (g["n_alignments"], g["n_policy_seeds"]) == (len(main["meta"]["grids"]["alignments"]),
                                                        len(main["meta"]["grids"]["policy_seeds"]))
    assert f"over {g['n_alignments']} alignment" in tot and "4 alignments" not in tot and "3 policy seeds" not in tot
    (al, own), = main["meta"]["own_capacity_usd"].items()
    assert f"Own capacity costs {own:,.0f} USD per week (alignment {al})" in tot
    t3i = m.table3_intervals_tex(t["table3_intervals"])
    assert "(120 min, full menu, trace lender" in t3i and "one week" not in t3i
    bl0a = [r for r in t["total_accounting"]["rows"] if r["key"] == "bl0a"][0]
    assert bl0a["saving_pct"]["median"] == 0.0
    assert r"\begin{table}" in tot and "Own capacity costs" in tot
    ab = t["stress_aborts"]
    assert {r["key"] for r in ab["rows"]} == set(m.A8_KEYS) and len(ab["rows"]) == len(m.A8_KEYS) * len(ab["modes"])
    tex_ab = m.stress_aborts_tex(ab)
    assert tex_ab.count(r"\\") >= len(ab["rows"]) + 1
    stress = json.loads((IN_ROOT / "code/sim/out/e7/stress/summary.json").read_text())["meta"]
    inst = main["meta"]["instances"][f"mu={stress['mu']:g}:c={stress['alignment']}"]
    assert sg == {"alignment": stress["alignment"], "n_policy_seeds": len(stress["grids"]["policy_seeds"]),
                  "slow_min": inst["slow_min"]} == {"alignment": 1, "n_policy_seeds": 1, "slow_min": 5}
    assert "(alignment 1, 1 policy seed per mode)" in tex_ab and "$t_a$ (5-min slots)" in tex_ab
    many = {**t["total_accounting"], "own_capacity_usd": {"1": 145726.0, "2": 145736.0},
            "own_capacity_median": 145731.0, "grid": {"n_alignments": 2, "n_policy_seeds": 3}}
    tm = m.total_accounting_tex(many)
    assert "over 2 alignments $\\times$ 3 policy seeds" in tm
    assert "145,731 USD per week, the median over the alignments (by alignment: 1: 145,726; 2: 145,736)" in tm


def test_sf_e5_zero_or_null_on_the_spine_and_coinciding_modes(tmp_path, monkeypatch):
    """sf_e5: a null or zero share is listed in zero_or_null and drawn on the x spine (outside the clip box); where
    the three A6 modes give one point only A6's default is drawn there; the panels share y."""
    root = tmp_path / "in"
    shutil.copytree(IN_ROOT / "code/sim/out/e5", root / "code/sim/out/e5")
    s = json.loads((root / "code/sim/out/e5/summary.json").read_text())
    fb = s["cells"]["sh1"]["long"]["1"]["Sublet"]["fallback_share_after_reclaims"]
    fb.update(median=None, median_note="no run with a reclaim-caused capacity drop", median_ci95=[None, None])
    s["cells"]["sh0.5"]["short"]["1"]["BL3-2"]["fallback_share_after_reclaims"].update(median=0.0)
    (root / "code/sim/out/e5/summary.json").write_text(json.dumps(s))
    monkeypatch.setenv("SUBLET_FIGS_IN_ROOT", str(root))
    from figs.supp import sf_e5
    data = json.loads(json.dumps(sf_e5.build(Inputs())))
    z = {(r["level"], r["menu"], r["key"]) for r in data["zero_or_null"]}
    assert ("sh1", "long", "sublet_ms4") in z and ("sh0.5", "short", "bl3") in z        # C47: the tag Sublet drawn
    fig = sf_e5.draw(data)
    axes = fig.axes[:5]
    y0 = axes[0].get_ylim()[0]
    assert all(ax.get_ylim() == axes[0].get_ylim() for ax in axes)
    ax_d = axes[sf_e5.LEVELS.index("sh1")]
    on_spine = [ln for ln in ax_d.lines if getattr(ln, "_sublet_policy", "") == "sublet_ms4"           # C47
                and list(ln.get_ydata()) == [y0]]
    assert len(on_spine) == 1 and on_spine[0].get_clip_on() is False
    assert on_spine[0].get_markerfacecolor() == "white"            # the long menu: open
    for lv, ax in zip(sf_e5.LEVELS, axes):
        for menu in sf_e5.MENUS:
            n_a6 = sum(1 for ln in ax.lines if getattr(ln, "_sublet_policy", "") in sf_e5.A6_KEYS
                       and (ln.get_markerfacecolor() == "white") == (menu == "long"))
            assert n_a6 == (1 if data["a6_coincide"][lv][menu]["drawn_as_one"] else 3), (lv, menu)
    style.save(fig, "sf_e5", data, pdf_dir=tmp_path / "pdf", out_dir=tmp_path / "out")


def test_sf_e5_legend_lists_the_keys_drawn():
    """sf_e5's legend lists only keys drawn in some panel; where A6's other modes coincide with its default in every
    cell (the fixture), they are left out and A6's entry reads 'all modes'; with one cell apart, all three are
    listed under their registry labels. BL3 with N_Extra = 0 is a pentagon, whose fill shows (filled: short menu)."""
    from figs.supp import sf_e5
    data = fixture_data("sf_e5")
    assert all(f["drawn_as_one"] for lv in data["levels"] for f in data["a6_coincide"][lv].values())

    def legend_texts(d):
        # C47: with A6's three modes listed the entries need two legend rows of their own (ms4_lib.legend_rows_above),
        # so the texts of every legend row, in order
        fig = sf_e5.draw(d)
        legs = [lg for lg in fig.legends if getattr(lg, "_sublet_role", "") == "legend_row"]
        assert len(legs) in (1, 2)
        return [t.get_text() for leg in legs for t in leg.get_texts()]
    got = legend_texts(data)
    assert data["labels"]["a6_all_modes"] in got and style.POLICIES["a6"].label not in got
    assert not {style.POLICIES[k].label for k in ("a6_red_off", "a6_always2")} & set(got)
    # C62 (7-pt text): the guard's label on one line, the rows by family (the guard and Two-timescale PD; SpotHedge-style
    # in N_Extra's order, then the menus' samples)
    assert got == [style.POLICIES["sublet_ms4"].label, data["labels"]["a6_all_modes"]] + \
        [style.POLICIES[k].label for k in sf_e5.BL3_KEYS] + [data["labels"]["menu"][m] for m in ("short", "long")]
    d = copy.deepcopy(data)
    d["a6_coincide"]["trace"]["short"]["drawn_as_one"] = False
    got = legend_texts(d)
    assert [style.POLICIES[k].label for k in ("a6", "a6_red_off", "a6_always2")] == \
        [t for t in got if t.startswith("Two-timescale")]
    # C47: the guard first, in the legend; C59: its label in words on two lines (ms4_lib.wrap_wide), which C62 keeps
    # where A6's three modes share the guard's row
    from figs.supp import ms4_lib
    assert got[0] == "\n".join(ms4_lib.label_lines(style.POLICIES["sublet_ms4"].label))
    assert style.POLICIES["bl3_n0"].marker == "p" and data["labels"]["y"] == "Fallback share"


def test_sf_e8_off_scale_values(tmp_path, monkeypatch):
    """sf_e8: a value of E below the floor (-1) is listed in off_scale, drawn as an arrow to the axis floor with its
    value printed, and the axis is not stretched to it; windows absent from a reduced summary have no point."""
    root = tmp_path / "in"
    shutil.copytree(IN_ROOT / "code/sim/out/e8", root / "code/sim/out/e8")
    s = json.loads((root / "code/sim/out/e8/summary.json").read_text())
    s["mooncake"]["60"]["on"]["error"] = -5.3
    (root / "code/sim/out/e8/summary.json").write_text(json.dumps(s))
    monkeypatch.setenv("SUBLET_FIGS_IN_ROOT", str(root))
    from figs.supp import sf_e8
    data = json.loads(json.dumps(sf_e8.build(Inputs())))
    assert data["off_scale"] == [{"panel": "b", "prefix": "on", "win": 60.0, "error": -5.3}]
    assert data["windows"] == sorted(float(w) for w in s["meta"]["grid"]["windows"])
    fig = sf_e8.draw(data)
    ax_b = fig.axes[1]
    arrows = [t for t in ax_b.texts if getattr(t, "_sublet_role", "") == "off_scale_arrow"]
    labels = [t.get_text() for t in ax_b.texts if getattr(t, "_sublet_role", "") == "off_scale_label"]
    assert len(arrows) == 1 and labels == ["−5.3"]
    assert ax_b.get_ylim()[0] > -1.5 and arrows[0].xy[1] == sf_e8.FLOOR
    style.save(fig, "sf_e8", data, pdf_dir=tmp_path / "pdf", out_dir=tmp_path / "out")
    assert "off_scale" in data["labels"]


def test_sf_e8_tier_colors_and_bars_cut_at_the_floor(tmp_path):
    """sf_e8 (a): the tiers in the three darker of four cividis shades (the lightest of three printed at the
    reference line's grey); a min-max bar whose minimum lies below the floor ends there in an arrowhead and the
    minimum is in off_scale."""
    from matplotlib.colors import to_rgb
    from figs.supp import sf_e8
    data = copy.deepcopy(fixture_data("sf_e8"))
    t = data["a"]["M"]
    t["min"][0] = -1.4
    t["median"][0] = max(t["median"][0], -0.6)
    data["off_scale"] = [{"panel": "a", "tier": "M", "win": t["win"][0], "value": -1.4, "field": "min"}]
    fig = sf_e8.draw(data)
    ax_a = fig.axes[0]
    grey = lambda c: 0.299 * to_rgb(c)[0] + 0.587 * to_rgb(c)[1] + 0.114 * to_rgb(c)[2]
    tiers = [ln for ln in ax_a.lines if ln.get_label().startswith("Tier")]
    assert [ln.get_color() for ln in tiers] == style.ramp(4, "cividis")[:3]
    assert all(abs(grey(ln.get_color()) - grey(style.REFERENCE_GREY)) > 0.15 for ln in tiers)
    cut = [a for a in ax_a.texts if getattr(a, "_sublet_role", "") == "bar_cut_arrow"]
    assert len(cut) == 1 and cut[0].xy[1] == sf_e8.FLOOR
    assert data["labels"]["y"] == r"Relative cost error $E$"
    style.save(fig, "sf_e8", data, pdf_dir=tmp_path / "pdf", out_dir=tmp_path / "out")


def test_sf_e4_cost_models_and_bounds():
    """sf_e4: the fractional series against LP_core (x_core, core_median), the combiner's run against OPT_eager
    (x, median); the bounds 1 + x and the combiner factor (1 + x) drawn where the extract says, grey dashed."""
    from figs.supp import sf_e4
    data = fixture_data("sf_e4")
    e4 = json.loads((IN_ROOT / "code/sim/out/e4/summary.json").read_text())
    for p, panel in sf_e4.PANELS:
        for key in sf_e4.KEYS:
            s = data[p][key]
            assert s["x_field"] == ("x" if key == "a5" else "x_core")
            assert s["x"] == sorted(s["x"])
            for pred, x, y in zip(s["pred"], s["x"], s["y"]):
                ent = e4["ratio"][panel][pred][key]
                assert (x, y) == ((ent["x"], ent["median"]) if key == "a5" else (ent["x_core"], ent["core_median"]))
    assert data["bounds"]["factor_t11"] == e4["meta"]["combiner_bound"]
    fig = sf_e4.draw(data)
    n_drawn = sum(b["drawn"] for b in data["bounds"]["lines"])
    marks = [b for b in data["bounds"]["lines"] if b["mark_at_zero"]]
    assert not any(b["drawn"] and b["mark_at_zero"] for b in data["bounds"]["lines"])
    for ax in fig.axes[:2]:
        th = [ln for ln in ax.lines if getattr(ln, "_sublet_role", "") == "theory:upper"]
        assert len(th) == n_drawn
        for ln, b in zip(th, [b for b in data["bounds"]["lines"] if b["drawn"]]):
            np.testing.assert_allclose(ln.get_ydata(), b["factor"] * (1.0 + np.asarray(ln.get_xdata())))
        # a bound too short to carry its label on a line is drawn as a dashed stub from x = 0 to where it leaves the
        # y range (print check of 2026-10-27; as built, a solid tick at its value at x = 0 read as a legend sample)
        mk = [ln for ln in ax.lines if getattr(ln, "_sublet_role", "") == "theory_mark:upper"]
        assert len(mk) == len(marks)
        for ln, b in zip(mk, marks):
            x = np.asarray(ln.get_xdata(), dtype=float)
            assert x[0] == 0.0 and x[-1] == pytest.approx(b["stub_to"])
            np.testing.assert_allclose(ln.get_ydata(), b["factor"] * (1.0 + x))
            assert ln.get_linestyle() == "--"
        assert len([t for t in ax.texts if getattr(t, "_sublet_role", "") == "theory_label:upper"]) == \
            n_drawn + len(marks)
        # markers only: the predictions are different kinds of error, not a sequence
        pol = [ln for ln in ax.lines if hasattr(ln, "_sublet_policy")]
        assert pol and all(ln.get_linestyle() == "None" for ln in pol)
        assert ax.get_xscale() == "symlog" and ax.get_yscale() == "log"
        # symlog_u is matplotlib's own transform of the axis
        tr = ax.xaxis.get_transform()
        for v in (-0.12, 0.5, 1.0, 10.0, 63.3):
            assert sf_e4.symlog_u(v) == pytest.approx(float(tr.transform(v)), rel=1e-12)
    assert "1 + x bounds c(P-hat)" in data["labels"]["note"]


def _e4_scaled(data: dict, top: float) -> dict:
    """sf_e4's extract with BurstGPT's psi = 0.1 scaled so that its largest value is `top`, the axes and bounds
    recomputed as build() does (the bound 5.83 (1 + x) is drawn once the y range reaches about 7.1)."""
    from figs.supp import sf_e4
    d = copy.deepcopy(data)
    s = d["b"]["psi_01"]
    m = max(s["y"])
    s["y"] = [y * top / m if y > 4 else y for y in s["y"]]
    d["axes"] = sf_e4.axis_ranges(d)
    d["bounds"]["lines"] = sf_e4.bounds_inside(d["bounds"]["factor_t11"], d["axes"])
    return d


@pytest.mark.parametrize("top", [5.5, 7.2, 8.0, 9.0, 10.0, 14.0])
def test_sf_e4_bounds_drawn_or_marked_at_real_scale(tmp_path, top):
    """sf_e4 with ratios up to `top`: 5.83 (1 + x) marked at x = 0 or drawn as a line, each label on the free space
    next to its bound and joined by a leader where set apart; save() passes (as built, the drawn line's label fell
    onto the y label above about 7.1 and finalize() failed)."""
    d = _e4_scaled(fixture_data("sf_e4"), top)
    t11 = d["bounds"]["lines"][1]
    assert t11["drawn"] or t11["mark_at_zero"]
    fig = module("sf_e4").draw(d)
    for ax in fig.axes[:2]:
        assert len([t for t in ax.texts if getattr(t, "_sublet_role", "") == "theory_label:upper"]) == 2
    rep = save("sf_e4", d, tmp_path)
    assert rep["outside_page"] == []


def test_e3_figures_draw_siloed_series_dashed_and_keep_null_points():
    """sf_e3_util and sf_e3_mu: the siloed variants dashed (env sharing), the shared solid; a b without runs in the
    reduced tree stays in the series with its note (a gap).

    C47 (design/ms6_spec.md M2, M4): the siloed form of sublet_ms4 is that key in the sharing line style with its
    own filled markers (no siloed registry key, as sf_e3_v2), A6's its registry key a6_siloed (open hexagons); each
    is dashed, each shared form solid, and both forms of sublet_ms4 are drawn."""
    from figs.supp.sf_e3_util import SILOED, SUBLET_SILOED
    for name in ("sf_e3_util", "sf_e3_mu"):
        data = fixture_data(name)
        fig = module(name).draw(data)
        series = {}
        for ln in fig.axes[0].lines:
            k = getattr(ln, "_sublet_policy", "")
            # C47 (M2, M4): sublet_ms4 in place of the frozen sublet and sublet_siloed (one key, two line styles)
            if k not in ("sublet_ms4", "a6", "a6_siloed") or ln.get_linestyle() in ("None", "none"):
                continue                                       # the markers-only lines and the other policies
            series.setdefault(k, set()).add(ln.get_linestyle())
            if k == "a6_siloed":
                assert ln.get_linestyle() == "--" and ln.get_markerfacecolor() == "white"
            elif k == "a6":                                    # C47: a6 is checked alone (sublet_ms4 has two styles)
                assert ln.get_linestyle() == "-"
        # C47 (M2, M4): both forms of sublet_ms4, its shared form solid and its siloed form dashed
        assert series["sublet_ms4"] == {"-", "--"} and series["a6_siloed"] == {"--"}
        assert SUBLET_SILOED in SILOED and data["tags"][SUBLET_SILOED] == "Sublet-siloed"   # the summary's tag
    mk = [ln for ln in module("sf_e3_util").draw(fixture_data("sf_e3_util")).axes[0].lines
          if getattr(ln, "_sublet_series", "") == SUBLET_SILOED and getattr(ln, "_sublet_role", "") == "markers"]
    assert mk and all(ln.get_markerfacecolor() == style.policy("sublet_ms4").color for ln in mk)   # its own fill
    d = fixture_data("sf_e3_util")
    s = d["c"]["sublet_ms4"]                                   # C47 (M2, M4): the guard's series under its key
    i = s["b"].index(2.0)
    assert s["median"][i] is None and s["note"][i]
    assert d["u"] == 8.0 and d["mu"] == 1.0


# ---------------------------------------------------------------------------------------------------------------
def _extreme(name: str, data: dict) -> dict:
    """A hand-modified copy of a fixture extract at the real-scale extremes the unit builds reported: E5's BL3 at
    10-21 x BL0a under one group and a null share, E8's prefix-hit error far below -1, E3's siloed loads per day in the
    thousands, E4's x up to hundreds, E7's default allowance far below the sweep's shares and many contract classes."""
    d = copy.deepcopy(data)
    if name == "sf_e5":
        for key, v in (("bl3_n0", 10.2), ("bl3_n1", 17.5), ("bl3", 21.3)):
            d["all1"]["long"][key]["cost"].update(median=v, ci_lo=v * 0.9, ci_hi=v * 1.1)
        d["sh1"]["long"]["sublet_ms4"]["fallback"].update(median=None, ci_lo=None, ci_hi=None, note="null")   # C47
    elif name == "sf_e8":
        for w, v in zip(d["b"]["on"]["win"], (-0.4, -5.3)):
            d["b"]["on"]["error"][d["b"]["on"]["win"].index(w)] = v
    elif name == "sf_e3_util":
        for k in ("sublet_ms4:siloed", "a6_siloed", "bl2"):                   # C47: sublet_ms4's siloed form
            s = d["b"][k]
            s["median"] = [None if v is None else v * 30 for v in s["median"]]
            s["ci_hi"] = [None if v is None else v * 33 for v in s["ci_hi"]]
            s["ci_lo"] = [None if v is None else v * 27 for v in s["ci_lo"]]
    elif name == "sf_e4":
        from figs.supp import sf_e4
        for p in ("a", "b"):
            for key in ("psi_01", "psi_03", "psi_05", "a2_frac"):
                d[p][key]["x"] = [x * 10 for x in d[p][key]["x"]]
        d = _e4_scaled(d, 9.0)                         # y up to 9 too: 5.83 (1 + x) inside the y range
        t11 = d["bounds"]["lines"][1]
        assert (t11["drawn"] or t11["mark_at_zero"]) and sf_e4.axis_ranges(d)["x_max"] == d["axes"]["x_max"]
    elif name == "sf_e7_allow":
        d["default"]["share_pct"] = 0.12
    elif name == "sf_e7_mix":
        d["a"]["a7"] = {"spot-like": 0.002, "AEP-82-like": 0.3, "general": 0.69, "GFS-like": 0.005, "protected": 0.003}
        d["a"]["sublet_ms4"] = {"spot-like": 0.97, "AEP-82-like": 0.02, "protected": 0.01}            # C47
        d["b"]["bl2"] = {}
    elif name == "sf_e7_mu":
        for p in ("a", "b"):
            for s in d[p].values():
                s["median"] = [None if v is None else v * 1.3 for v in s["median"]]
    elif name == "sf_e3_mu":
        d["opt"]["open"] = [True] * len(d["opt"]["open"])
    return d


@pytest.mark.parametrize("name", SUPP)
def test_supplementary_scripts_on_real_scale_extremes(tmp_path, name):
    """Every supplementary script draws a hand-modified extract at real-scale extremes and save() passes (no text
    overlap, no ink outside the page, 9-10 pt)."""
    rep = save(name, _extreme(name, fixture_data(name)), tmp_path)
    assert rep["outside_page"] == [] and all(style.TEXT_MIN_PT <= s <= style.TEXT_MAX_PT for s in rep["text_pt"])


@pytest.mark.skipif(not (Path.home() / ".local/bin/pdflatex").is_file(), reason="pdflatex is not installed")
def test_sf_e7_mix_tables_compile(tmp_path):
    """The three tables compile with booktabs and longtable in a one-column IEEEtran page (longtable, as sf_e6a's
    e6a_cells.tex, needs one-column mode), with no overfull box."""
    from figs.supp import sf_e7_mix as m
    t = fixture_data("sf_e7_mix")["tables"]
    (tmp_path / "a.tex").write_text(m.table3_intervals_tex(t["table3_intervals"]))
    (tmp_path / "b.tex").write_text(m.total_accounting_tex(t["total_accounting"]))
    (tmp_path / "c.tex").write_text(m.stress_aborts_tex(t["stress_aborts"]))
    (tmp_path / "doc.tex").write_text("\\documentclass[journal,onecolumn]{IEEEtran}\\usepackage{booktabs}"
                                      "\\usepackage{longtable}\n"
                                      "\\begin{document}\n\\input{a.tex}\n\\input{b.tex}\n\\input{c.tex}\nText.\n"
                                      "\\end{document}\n")
    env = dict(os.environ, TEXINPUTS=f"{style.REPO / 'paper' / 'layout_check'}:")
    r = subprocess.run([str(Path.home() / ".local/bin/pdflatex"), "-interaction=nonstopmode", "-halt-on-error",
                        "doc.tex"], cwd=tmp_path, capture_output=True, text=True, env=env, timeout=300)
    log = (tmp_path / "doc.log").read_text(errors="replace")
    assert r.returncode == 0 and "LaTeX Error" not in log, log[-2000:]
    assert "Overfull" not in log, [ln for ln in log.splitlines() if "Overfull" in ln]


# ---------------------------------------------------------------- C62 (2026-11-24): the MS4 figures of g8
def test_fig4_c62_labels_on_their_rows():
    """C62 (fig4): BL0b's ratio prints on the baseline of its row's name ("Provision for peak", va center_baseline as
    the y tick labels; centered, it printed 0.7 pt above it) and "All-fallback" on the printed baseline of the
    components key's last row (moved there, _sublet_baseline_shift_pt; centered on the row, 0.3 pt above it), measured
    with the PDF's metrics (common.printed_baselines_pt); the bars keep their height as built (BAR_H 0.62)."""
    from figs import fig4_e7_e3 as f4
    from figs.common import printed_baselines_pt
    assert (f4.BAR_H, f4.BAR_EDGE_PT) == (0.62, 0.8)
    data = fixture_data("fig4")
    fig = f4.draw(data)
    ax_a = fig.axes[0]
    ratio = next(t for t in ax_a.texts if t.get_text() == data["labels"]["bl0b_ratio"])
    name = next(tk.label1 for tk in ax_a.yaxis.get_major_ticks() if tk.label1.get_text() == data["labels"]["bl0b"])
    label = next(t for t in ax_a.texts if t.get_text() == data["labels"]["bl0a"])
    key = next(lg for lg in ax_a.get_children() if type(lg).__name__ == "Legend")
    base = printed_baselines_pt(fig, [ratio, name, label, *key.get_texts()])
    assert abs(base[0] - base[1]) < 0.05
    assert getattr(label, "_sublet_baseline_shift_pt", None) is not None and abs(base[2] - min(base[3:])) < 0.05


def test_sf_e7_mix_c62_titles_and_rows():
    """C62 (sf_e7_mix): the panel titles at the caption size (style.LABEL_PT, as C62 sets panel titles; at TICK_PT as
    built) on their letters' baseline, the row names on the rows' pitch as printed (common.align_baselines moves the
    names with mathtext, which the PDF set up to 1 pt off), and the top row's stem one line (LINE_STEP_PT) above its
    second line."""
    from figs.common import LINE_STEP_PT
    from figs.common import printed_baselines_pt
    data = fixture_data("sf_e7_mix")
    fig = module("sf_e7_mix").draw(data)
    ax_a = fig.axes[0]
    letters = [t for t in fig.texts if t.get_text() in ("(a)", "(b)")]
    titles = [t for t in fig.texts if t not in letters and t.get_text().strip()]
    assert len(letters) == 2 and titles and all(t.get_fontsize() == pytest.approx(style.LABEL_PT) for t in titles)
    base = printed_baselines_pt(fig, letters + titles)
    assert max(base) - min(base) < 0.05
    names = [tk.label1 for tk in ax_a.yaxis.get_major_ticks() if tk.label1.get_text()]
    rows = printed_baselines_pt(fig, names)
    assert np.allclose(np.diff(rows), np.diff(rows)[0], atol=0.05)
    stem = [t for t in ax_a.texts if getattr(t, "_sublet_role", "") == "row_label:stem"]
    if stem:
        (b_stem,) = printed_baselines_pt(fig, stem)
        assert b_stem - rows[0] == pytest.approx(LINE_STEP_PT, abs=0.05)


def _pdf_spans(pdf) -> list[dict]:
    """The horizontal text spans of a figure PDF (PyMuPDF): text, size, font, baseline (origin y, pt from the top)."""
    import fitz
    out = []
    for b in fitz.open(str(pdf))[0].get_text("dict")["blocks"]:
        for ln in b.get("lines", []):
            if tuple(round(v, 3) for v in ln["dir"]) != (1.0, 0.0):
                continue
            out += [{"text": s["text"], "size": s["size"], "font": s["font"], "y": s["origin"][1], "x0": s["bbox"][0],
                     "x1": s["bbox"][2]} for s in ln["spans"] if s["text"].strip()]
    return out


@pytest.mark.parametrize("name, n_panels", [("sf_e4", 2), ("sf_e5", 5), ("sf_e8", 2)])
def test_c62_fix_panel_titles_at_caption_size_on_letter_baselines(figs_env, name, n_panels):
    """C62 fix round (group g4): the panel titles of sf_e4, sf_e5 and sf_e8 at the caption size (style.LABEL_PT; at
    TICK_PT as first restyled) on their letters' baseline, as the model of the PDF prints them (printed_baselines_pt)
    and in the PDF itself (PyMuPDF; sf_e5's titles with p_sh are mathtext, moved by common.align_baselines), within
    0.05 pt; each title ends left of the next panel's letter (sf_e8: at least TITLE_GAP_PT)."""
    import re
    from figs.common import printed_baselines_pt
    data = fixture_data(name)
    fig = module(name).draw(data)
    letters = [t for t in fig.texts if getattr(t, "_sublet_role", "") == "panel_letter"]
    y_l = letters[0].get_position()[1]
    titles = [t for t in fig.texts if t not in letters and t.get_text().strip() and t.get_position()[1] == y_l]
    assert len(letters) == len(titles) == n_panels
    assert all(t.get_fontsize() == pytest.approx(style.LABEL_PT) for t in letters + titles)
    base = printed_baselines_pt(fig, letters + titles)
    assert max(base) - min(base) < 0.05
    r = fig.canvas.get_renderer()
    to_pt = style.BP_PER_IN / fig.dpi
    gap = TITLE_GAP_MIN.get(name, 0.0)
    for t, nxt in zip(titles, letters[1:]):
        assert (nxt.get_window_extent(r).x0 - t.get_window_extent(r).x1) * to_pt >= gap
    rep = module(name).main(["--from-extract", str(FIX / f"{name}.json")])
    spans = _pdf_spans(rep["pdf"])
    heads = [s for s in spans if re.fullmatch(r"\([a-z]\)", s["text"]) and "Bold" in s["font"]]
    assert len(heads) == n_panels
    y0 = heads[0]["y"]
    row = [s for s in spans if abs(s["y"] - y0) < 1.0 and abs(s["size"] - style.LABEL_PT) < 0.01]
    assert len(row) > n_panels and all(abs(s["y"] - y0) < 0.05 for s in row)


TITLE_GAP_MIN = {"sf_e8": 4.0}                 # sf_e8.TITLE_GAP_PT, checked above against the module's own value


def test_c62_fix_sf_e8_title_gap_constant():
    """sf_e8's TITLE_GAP_PT is the gap the title test asks for, and title_clear raises where a title ends closer."""
    from figs.supp import sf_e8
    assert sf_e8.TITLE_GAP_PT == TITLE_GAP_MIN["sf_e8"]
    fig = sf_e8.draw(fixture_data("sf_e8"))
    letters = [t for t in fig.texts if getattr(t, "_sublet_role", "") == "panel_letter"]
    titles = [t for t in fig.texts if t not in letters and t.get_text().strip()
              and t.get_position()[1] == letters[0].get_position()[1]]
    titles[0].set_text(titles[0].get_text() + " and more words")
    with pytest.raises(style.StyleError, match="next letter"):
        sf_e8.title_clear(letters, titles)


def test_c62_fix_sf_e4_bound_formula_in_math():
    """C62 fix round (sf_e4): the stub label of the combiner's bound gives its formula in math, $5.83\\,(1+x)$ with an
    italic x as on the x axis and in the caption (as built "5.83 (1 + x)" in plain text), over "A5, C3-T11", the tag the
    caption quotes; 1 + x's stub form likewise; the extract's bounds keep their plain names. On the versioned extract
    both panels draw the formula form."""
    from figs.supp import sf_e4
    for d in (fixture_data("sf_e4"), json.loads((style.REPO / "code/sim/out/figs/sf_e4.json").read_text())["data"]):
        f = d["bounds"]["factor_t11"]
        assert d["labels"]["bound_t11_stub"] == f"${f:g}\\,(1+x)$\nA5, C3-T11"
        assert d["labels"]["bound_1x_stub"].startswith("$1+x$\n")
        assert [b["line"] for b in d["bounds"]["lines"]] == ["1 + x", f"{f:g} (1 + x)"]
    fig = sf_e4.draw(d)                                   # the versioned extract
    for ax in fig.axes[:2]:
        lab = [t.get_text() for t in ax.texts if getattr(t, "_sublet_role", "") == "theory_label:upper"]
        assert d["labels"]["bound_t11_stub"] in lab


def test_c62_fix_sf_e3_util_x_label_names_b_per_llm(figs_env):
    """C62 fix round (sf_e3_util): every panel's x label is "Borrowers per LLM, $b$" (the design's name of b, borrowers
    per LLM; the caption's b co-located borrowers of one LLM), as its MS5b sister sf_e3_v2 labels it, in the fixture and
    the versioned extract, and the PDF prints b in the italic face."""
    from figs.supp import sf_e3_util as m
    from figs.supp import sf_e3_v2
    assert m.LABELS["x"] == sf_e3_v2.LABELS["x"] == "Borrowers per LLM, $b$"
    for d in (fixture_data("sf_e3_util"),
              json.loads((style.REPO / "code/sim/out/figs/sf_e3_util.json").read_text())["data"]):
        assert d["labels"]["x"] == m.LABELS["x"]
        fig = m.draw(d)
        assert [ax.get_xlabel() for ax in fig.axes if hasattr(ax, "_sublet_rect_in")] == [m.LABELS["x"]] * 3
    spans = _pdf_spans(m.main(["--from-extract", str(FIX / "sf_e3_util.json")])["pdf"])
    heads = [i for i, s in enumerate(spans) if s["text"] == "Borrowers per LLM, "]
    assert len(heads) == 3
    for i in heads:
        assert spans[i + 1]["text"] == "b" and "Italic" in spans[i + 1]["font"] and "Italic" not in spans[i]["font"]
