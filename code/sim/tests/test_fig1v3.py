"""Tests of Fig. 1 v3 (design/ms7/w_spec.md §2.2 items 57-76, §4 unit W-G1; change C58): the figure script
figs/fig1_v3.py and its registration in figs/style.py.

Quick (no input file: the figure is a schematic; every file is written under pytest's tmp_path):
- C58: fig1v3 is a main-text figure at W2 (\\textwidth) with the set (sublet_v2,), outside
  LEGACY_PENDING; the print sheet and the rebuild's script list order it right after fig1v2. The build draws at the
  registered height, 1.70 in since C62 (the spec's 1.9 in before), and its rows fit every height from
  fig1_v3.MIN_HEIGHT_IN up.
- The build reads no file (empty sources), saves with finalize() passing at the registered page size, with every text at
  C62's sizes (7 pt, the letters 7.97 pt), and is byte-stable: a second build and a redraw from the written extract give
  the same PDF bytes and the same extract. The versioned extract code/sim/out/figs/fig1v3.json is the build's (not
  stale), and the versioned PDF paper/figures/fig1v3.pdf is its redraw byte for byte.
- (a) draws fig1_v2's labels of contract k (only "cold" differs), the five marks in their order on one baseline, the
  shaded window from s to s + D_k, and the reactions in Sublet's color on two rows, the pre-warm dashed and ending at
  the mark r + H_k, the cold re-buy solid and starting there (C62: drawn by fig1_v3.draw_lease at 7-pt spacing, no
  longer by fig1_guard.draw_timeline, whose rows are spaced for 9-pt text).
- No design or experiment ID, no result name and not the name Sublet is drawn; the paper's names are ("critical-ratio
  renting", "safe expert", "Algorithm 1", P1, P0, K0); the glyph gamma is never drawn (the test is at gamma = 1).
- (c) draws the ladder A_E(t), P1, P0, K0 left to right, then the two outcomes; (b) draws the two components, the safe
  expert and the three parts of the data plane.
- Layout: (b) ends above (c)'s first row, with more space between the panels than inside (c); every "passes" arrow
  lands on the execute bar's straight top edge; (a)'s last text ends on (b)'s data plane's bottom edge; the ladder's
  boxes share one width; at 1.70 in and at the registered height alike.
- The review of C62's restyle: (b)'s arrow-row labels ("list", C_S(t)) and (c)'s test print on one baseline with their
  neighbors (the letter, for the test); (b)'s pairs end on, and start from, the platform's light outline, their labels
  one line apart and centered in the span; nothing is drawn in the bottom reserve (about 6 pt under the ink, as Figs.
  2-4 leave), at 1.70 in and at the registered height.
- The caption draft fits the double-column caption budget and names Sublet, critical-ratio renting, Algorithm 1 and
  the safe expert, without design IDs.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from fixtures import SIM

from figs import fig1_v2, fig1_v3, print_sheet, style
from figs import rebuild as rb
from figs.inputs import Inputs

REPO = SIM.parents[1]
EXTRACT = REPO / "code" / "sim" / "out" / "figs" / "fig1v3.json"
PDF = REPO / "paper" / "figures" / "fig1v3.pdf"
STALE = ("code/sim/out/figs/fig1v3.json is stale (the script's labels changed): rerun `python -m figs.fig1_v3` from "
         "code/sim")
# drawn design or experiment IDs (as tests/test_fig1v2.py's, with the test and guard names of the design): policy and
# baseline IDs, experiments, results, cells, lender modes, open choices and units, the names of results, and Sublet
DESIGN_ID = re.compile(r"\b(A[1-9]P?|BL\d|E\d{1,2}|G\d|C\d{1,2}|Q\d{1,2}|I\d|W\([abc]\)|M\d{1,2}|U\d{2}|P\.1|T0g?|T1|"
                       r"H\d|ORML|FB|PD)\b|L-[a-z]|Theorem|Lemma|Proposition|Remark|Corollary|Sublet|illustrative")
GAMMA_GLYPH = re.compile(r"\\gamma|γ")

pytestmark = pytest.mark.filterwarnings("ignore::figs.style.GlyphSizeWarning")


@pytest.fixture
def figs_env(tmp_path, monkeypatch):
    monkeypatch.delenv("SUBLET_FIGS_IN_ROOT", raising=False)
    monkeypatch.setenv(style.ENV_PDF_DIR, str(tmp_path / "pdf"))
    monkeypatch.setenv(style.ENV_OUT_DIR, str(tmp_path / "out"))
    return tmp_path


def data():
    return json.loads(json.dumps(fig1_v3.collect(Inputs())))


def drawn(fig) -> list[str]:
    return [t.get_text() for t in style.drawn_texts(fig)]


# ---------------------------------------------------------------------------------------------------------------
def test_registered():
    """C58: fig1v3 at W2 x 1.70 in (C62; 1.9 in before), a main-text figure, with the set (sublet_v2,); no LEGACY_PENDING entry; the
    registry checks pass; the print sheet orders it after fig1v2 (C44's rule)."""
    spec = style.FIGURES["fig1v3"]
    assert (spec.width, spec.height_in, spec.main) == ("W2", 1.70, True) and fig1_v3.NAME == "fig1v3"
    assert abs(spec.width_in * style.TEX_PT_PER_IN - 516) < 1e-9                     # \textwidth
    assert style.FIGURE_POLICIES["fig1v3"] == (fig1_v3.KEY,) == ("sublet_v2",)
    assert "fig1v3" not in style.LEGACY_PENDING
    style.check_policies(style.FIGURE_POLICIES["fig1v3"])
    style.check_legacy()
    main = print_sheet.main_figures()
    assert main.index("fig1v3") == main.index("fig1v2") + 1


def test_rebuild_lists_the_script_after_fig1v2():
    """figs.rebuild finds the script by its glob (no list entry needed), right after fig1_v2.py (C42's order)."""
    scripts = rb.figure_scripts()
    paths = [p for _, _, p in scripts]
    i = paths.index("code/sim/figs/fig1_v3.py")
    assert scripts[i][:2] == ("main", "figs.fig1_v3") and paths[i - 1] == "code/sim/figs/fig1_v2.py"


def test_builds_at_final_size_and_is_byte_stable(figs_env):
    """The build (no input file) saves with finalize() passing: one page of the registered size within 0.5 bp, every
    text at 7 pt and the letters at 7.97 pt (C62), no glyph below a first-level script, embedded fonts without
    DejaVu, no ink outside the page. A second build and a redraw from the written extract give the same PDF bytes,
    extract and preview."""
    rep = fig1_v3.main([])
    spec = style.figure_spec("fig1v3")
    assert Path(rep["pdf"]) == figs_env / "pdf" / "fig1v3.pdf"
    assert rep["pages"] == 1 and abs(rep["width_bp"] - spec.width_in * 72) <= 0.5
    assert abs(rep["height_bp"] - spec.height_in * 72) <= 0.5
    assert rep["text_pt"] == [style.TICK_PT, style.LETTER_PT] == [7.0, style.CAPTION_PT]
    assert rep["outside_page"] == []
    assert rep["min_glyph_pt"] >= style.SCRIPT_MIN_PT - 1e-9
    assert len(rep["fonts"]) >= 2 and not any("dejavu" in f.lower() for f in rep["fonts"])
    assert all(r["emb"] == "yes" and "Type 3" not in r["type"] for r in style.pdf_fonts(rep["pdf"]))
    written = figs_env / "out" / "fig1v3.json"
    payload = json.loads(written.read_text())
    assert payload["figure"] == "fig1v3" and payload["sources"] == [] and payload["data"] == data()
    files = (("pdf", "fig1v3.pdf"), ("out", "fig1v3.json"), ("out", "fig1v3.png"))
    first = {n: (figs_env / d / n).read_bytes() for d, n in files}
    for argv in ([], ["--from-extract", str(written)]):          # a second build; a redraw from the written extract
        fig1_v3.main(argv)
        assert {n: (figs_env / d / n).read_bytes() for d, n in files} == first, argv


def test_from_extract_option(monkeypatch):
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

    assert fig1_v3.main.__module__ == fig1_v3.__name__ and fig1_v3.cli is common.cli
    monkeypatch.setattr(inputs.Inputs, "extract", fake_extract)
    with pytest.raises(Stop):
        fig1_v3.main(["--from-extract"])
    monkeypatch.setattr(common, "read_extract", fake_read_extract)
    with pytest.raises(Stop):
        fig1_v3.main(["--from-extract", "some/extract.json"])
    assert calls == [("fig1v3", "Inputs.extract"), ("fig1v3", "some/extract.json")]


def test_versioned_outputs_are_current(tmp_path):
    """The versioned extract is the build's (sources empty), and the versioned PDF is its redraw byte for byte."""
    inp = Inputs()
    built = fig1_v3.collect(inp)
    assert inp.sources == []
    payload = json.loads(EXTRACT.read_text())
    assert payload["figure"] == "fig1v3" and payload["sources"] == []
    assert payload["size_in"] == [round(style.W2, 4), style.figure_spec("fig1v3").height_in]
    assert payload["data"] == json.loads(json.dumps(built)), STALE
    rep = style.save(fig1_v3.draw(payload["data"]), "fig1v3", payload["data"], sources=payload["sources"],
                     pdf_dir=tmp_path / "pdf", out_dir=tmp_path / "out")
    assert Path(rep["pdf"]).read_bytes() == PDF.read_bytes()
    assert (tmp_path / "out" / "fig1v3.json").read_bytes() == EXTRACT.read_bytes()


def test_panel_a_timeline():
    """(a) draws fig1_v2's labels of contract k (only "cold" differs), each once ("lambda" once per reaction): the five
    marks s, s + tau_k, r, s + D_k, r + H_k left to right on one baseline (within the PDF backend's mathtext raise),
    the window shaded from s to s + D_k with its label inside, and the reactions in Sublet's color: the pre-warm dashed
    on the upper row, ending at the mark r + H_k and starting right of s + D_k, the cold re-buy solid on the lower row,
    starting at r + H_k. The three letters are bold (a), (b), (c) at LETTER_PT, with (a) and (b) on one baseline."""
    lab = data()["labels"]["a"]
    assert {k: v for k, v in lab.items() if k != "cold"} == {k: v for k, v in fig1_v2.LABELS_A.items() if k != "cold"}
    assert lab["cold"] == "cold" and lab["window"] == r"guaranteed window $D_k=\tau_k+H_k$"
    fig = fig1_v3.draw(data())
    a = fig.axes[0]
    texts = sorted(t.get_text() for t in a.texts if t.get_visible() and t.get_text())
    assert texts == sorted(list(lab.values()) + [lab["lam"]])
    marks = sorted((t for t in a.texts if getattr(t, "_sublet_role", "") == "mark"), key=lambda t: t.get_position()[0])
    assert [t.get_text() for t in marks] == [lab[k] for k in ("s", "s_tau", "r", "s_D", "r_H")]
    ys = [t.get_position()[1] for t in marks]
    assert max(ys) - min(ys) < 0.02                                   # one baseline, less the mathtext raise
    x_mark = {k: t.get_position()[0] for k, t in zip(("s", "s_tau", "r", "s_D", "r_H"), marks)}
    (win,) = [p for p in a.patches if getattr(p, "_sublet_role", "") == "window"]
    assert win.get_x() == x_mark["s"] and abs(win.get_x() + win.get_width() - x_mark["s_D"]) < 1e-9
    blue = style.mpl.colors.to_rgba(style.policy("sublet_v2").color)
    (pre,) = [ln for ln in a.lines if getattr(ln, "_sublet_role", "") == "prewarm"]
    (cold,) = [ln for ln in a.lines if getattr(ln, "_sublet_role", "") == "cold"]
    assert pre.get_linestyle() == "--" and cold.get_linestyle() == "-"
    assert style.mpl.colors.to_rgba(pre.get_color()) == style.mpl.colors.to_rgba(cold.get_color()) == blue
    (px0, px1), (cx0, cx1) = pre.get_xdata(), cold.get_xdata()
    assert abs(px1 - x_mark["r_H"]) < 1e-9 and abs(cx0 - x_mark["r_H"]) < 1e-9 and px0 > x_mark["s_D"]
    assert abs((px1 - px0) - (cx1 - cx0)) < 1e-9                        # one load time lambda
    assert pre.get_ydata()[0] > cold.get_ydata()[0]
    letters = [t for t in fig.texts if getattr(t, "_sublet_role", "") == "panel_letter"]
    assert [t.get_text() for t in letters] == ["(a)", "(b)", "(c)"]
    assert all(t.get_fontweight() == "bold" and t.get_fontsize() == style.LETTER_PT for t in letters)
    assert letters[0].get_position()[1] == letters[1].get_position()[1] > letters[2].get_position()[1]


def test_no_design_id_and_the_papers_names():
    """No drawn text carries a design or experiment ID, a result's name or the name Sublet, nor the glyph gamma; the
    drawn names are the paper's."""
    texts = drawn(fig1_v3.draw(data()))
    assert texts and not [t for t in texts if DESIGN_ID.search(t)], [t for t in texts if DESIGN_ID.search(t)]
    assert not [t for t in texts if GAMMA_GLYPH.search(t)]
    for name in ("critical-ratio renting", "safe expert", "Algorithm 1", "fallback capacity", "borrowers",
                 "lender sites", "menus, notices", "demand", "routing per interval", "contracts, replicas, reactions",
                 "abort: follow the safe expert"):
        assert name in texts, name
    assert sorted(t.split(":")[0] for t in texts if re.match(r"(P1|P0|K0|\$A_E\(t\)\$):", t)) == \
        ["$A_E(t)$", "K0", "P0", "P1"]


def test_every_text_at_the_c62_scale():
    """Every visible text, the box texts and the labels included, is at style.TICK_PT (7 pt), and the bold panel
    letters at style.LETTER_PT (7.97 pt, the caption size; C62)."""
    fig = fig1_v3.draw(data())
    sizes = style.text_sizes(fig)
    letters = {"(a)", "(b)", "(c)"}
    assert sizes and {s for s, t in sizes if t not in letters} == {style.TICK_PT} == {7.0}
    assert sorted((t, s) for s, t in sizes if t in letters) == [(t, style.LETTER_PT) for t in sorted(letters)]
    assert style.text_overlaps(fig) == []


def test_ladder_and_control_plane():
    """(c): the test at gamma = 1, the four lists left to right in the ladder's order, their boxes in Sublet's color,
    the execute bar under them and the abort box right of the bar; (b): the inner policy and Algorithm 1 in Sublet's
    color, the safe expert in grey, the data plane's three boxes on one row under the platform."""
    fig = fig1_v3.draw(data())
    b, c = fig.axes[1], fig.axes[2]
    blue = style.mpl.colors.to_rgba(style.policy("sublet_v2").color)

    def boxes(ax, role):
        return sorted((p for p in ax.patches if getattr(p, "_sublet_role", "") == role), key=lambda p: p.get_x())

    def texts(ax, role):
        return [t.get_text() for t in sorted((t for t in ax.texts if getattr(t, "_sublet_role", "") == role),
                                             key=lambda t: t.get_position()[0])]

    lab = data()["labels"]["c"]
    assert texts(c, "candidate") == lab["lists"]
    assert lab["test"] == r"list $Y$ passes if $\hat a_Y+R_Y\leq C_S(t)+B(t)$" == fig1_v3.test_label(1.0)
    assert "1.5" in fig1_v3.test_label(1.5) and r"\gamma" not in fig1_v3.test_label(1.5)
    cand = boxes(c, "candidate")
    assert len(cand) == 4 and all(p.get_edgecolor() == blue for p in cand)
    assert all(p.get_y() == cand[0].get_y() for p in cand)
    assert all(abs(p.get_width() - cand[0].get_width()) < 1e-12 for p in cand)       # the ladder's boxes, one width
    assert all(q.get_x() > p.get_x() + p.get_width() for p, q in zip(cand, cand[1:]))
    (ex,), (ab,) = boxes(c, "execute"), boxes(c, "abort")
    assert ex.get_y() + ex.get_height() < cand[0].get_y() and ab.get_y() == ex.get_y()
    assert ex.get_x() + ex.get_width() < ab.get_x() and ex.get_x() + ex.get_width() > cand[-1].get_x()
    assert texts(c, "execute") == [lab["execute"]] and texts(c, "abort") == [lab["abort"]]
    (inner,), (guard,), (safe,) = boxes(b, "inner"), boxes(b, "guard"), boxes(b, "safe")
    assert inner.get_edgecolor() == guard.get_edgecolor() == blue != safe.get_edgecolor()
    assert inner.get_x() < guard.get_x() < safe.get_x()
    plane = boxes(b, "fallback") + boxes(b, "borrowers") + boxes(b, "sites")
    assert len(plane) == 3 and len({p.get_y() for p in plane}) == 1
    assert all(p.get_y() + p.get_height() < inner.get_y() for p in plane)
    assert [p.get_x() for p in plane] == sorted(p.get_x() for p in plane)          # fallback, borrowers, lender sites
    (shade,) = boxes(b, "platform")
    assert shade.get_y() < inner.get_y() and shade.get_y() > plane[0].get_y() + plane[0].get_height()


@pytest.mark.parametrize("height", [None, 1.70])
def test_panels_read_as_groups(height, monkeypatch):
    """Layout (review of W-G1), at the registered height and at the 1.70 in that C62's restyle wants: (b) ends above
    (c)'s first row (its lowest box above the top of (c)'s letter and test), and the space between (b)'s data plane
    and (c)'s ladder exceeds the space inside (c) between the ladder and the outcomes, so that each panel reads as one
    group; every "passes" arrow lands on the execute bar's straight top edge, at least 0.08 in inside its ends (clear
    of the rounded corners); (a)'s lowest text ends within 0.01 in of the bottom edge of (b)'s data plane (the top row
    ends on one line); no two texts overlap and no ink leaves the page."""
    if height is not None:
        monkeypatch.setitem(style.FIGURES, "fig1v3", style.FigureSpec("fig1v3", "W2", height))
    fig = fig1_v3.draw(data())
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    a, b, c = fig.axes

    def ys(artist) -> tuple[float, float]:
        bb = artist.get_window_extent(r)
        return bb.y0 / fig.dpi, bb.y1 / fig.dpi

    def patches(ax, role):
        return [p for p in ax.patches if getattr(p, "_sublet_role", "") == role]

    plane = patches(b, "fallback") + patches(b, "borrowers") + patches(b, "sites")
    cand = patches(c, "candidate")
    (ex,) = patches(c, "execute")
    (test,) = [t for t in c.texts if t.get_text() == data()["labels"]["c"]["test"]]
    (letter,) = [t for t in fig.texts if t.get_text() == "(c)"]
    assert len(plane) == 3 and len(cand) == 4
    plane_bottom = min(ys(p)[0] for p in plane)
    assert plane_bottom > max(ys(test)[1], ys(letter)[1])
    ladder_top, ladder_bottom = max(ys(p)[1] for p in cand), min(ys(p)[0] for p in cand)
    assert plane_bottom - ladder_top > ladder_bottom - ys(ex)[1] + 0.05
    plane_edge = style.axes_rect_in(b)[1] + plane[0].get_y()        # the boxes' bottom edge (in), without the stroke
    # (a)'s lowest text is the cold re-buy's lambda, which has no descender: its baseline (as printed, with the PDF
    # backend's mathtext raise added back) is its ink's bottom; its layout box reaches a font descent lower
    low = min((t for t in a.texts if t.get_visible() and t.get_text()), key=lambda t: ys(t)[0])
    assert low.get_text() == data()["labels"]["a"]["lam"]
    a_bottom = style.axes_rect_in(a)[1] + low.get_position()[1] + fig1_v3._pdf_math_raise_in(
        low.get_text(), low.get_fontproperties())
    assert abs(a_bottom - plane_edge) < 0.005, (a_bottom, plane_edge)
    passes = [x for x in c.get_children() if getattr(x, "_sublet_role", "") == "passes"]
    assert len(passes) == 4
    for x in passes:                                 # the data units of (c)'s axes are inches
        assert ex.get_x() + 0.08 <= x.xy[0] <= ex.get_x() + ex.get_width() - 0.08, x.xy
        assert abs(x.xy[1] - (ex.get_y() + ex.get_height())) < 1e-9
    assert style.text_overlaps(fig) == [] and style.texts_outside_page(fig) == []


@pytest.mark.parametrize("height", [None, 1.70])
def test_baselines_outline_and_bottom_reserve(height, monkeypatch):
    """The review of C62's restyle, at the registered height and at 1.70 in. (b): "list" and C_S(t) print on one
    baseline (the position less the PDF backend's mathtext raise), above the arrows; the platform's shading has a light
    0.4-pt outline (lighter than the boxes' edges), on which every input arrow ends and from which every decision
    arrow starts; a pair's labels sit one line (1.2 x 7 pt) apart, the input's above, with their ink centered in the
    span and at least 0.04 in clear of its ends. (c): the test prints on the letter's baseline. Bottom: no patch or
    text reaches into the bottom reserve BOTTOM_PAD (at least 0.08 in; with the 0.6-pt edge about 6 pt of the page
    stay empty under the ink, as Figs. 2-4 leave under their x labels)."""
    if height is not None:
        monkeypatch.setitem(style.FIGURES, "fig1v3", style.FigureSpec("fig1v3", "W2", height))
    fig = fig1_v3.draw(data())
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    H = fig.get_size_inches()[1]
    a, b, c = fig.axes
    lab = data()["labels"]

    def printed(ax, t) -> float:                     # a text's printed baseline (in from the page's bottom)
        return style.axes_rect_in(ax)[1] + t.get_position()[1] + fig1_v3._pdf_math_raise_in(t.get_text(),
                                                                                            t.get_fontproperties())

    def role(ax, name, kind="texts"):
        return [x for x in getattr(ax, kind) if getattr(x, "_sublet_role", "") == name]

    # (b)'s arrow row
    al = sorted(role(b, "arrow_label"), key=lambda t: t.get_position()[0])
    assert [t.get_text() for t in al] == [lab["b"]["list"], lab["b"]["cost"]]
    assert abs(printed(b, al[0]) - printed(b, al[1])) < 1e-9
    (inner,) = role(b, "inner", "patches")
    ym = inner.get_y() + inner.get_height() / 2
    assert all(t.get_position()[1] + fig1_v3._pdf_math_raise_in(t.get_text(), t.get_fontproperties()) > ym + 0.03
               for t in al)
    # the platform's outline and the arrows on it
    (shade,) = role(b, "platform", "patches")
    assert shade.get_linewidth() == fig1_v3.PLATFORM_EDGE_PT == 0.4
    edge, ink = style.mpl.colors.to_rgb(shade.get_edgecolor()), style.mpl.colors.to_rgb(fig1_v3.INK)
    assert sum(edge) > sum(ink) and sum(edge) < 3 * 0.9          # lighter than the boxes' edges, not white
    f0 = shade.get_y()
    arrows = [x for x in b.get_children() if getattr(x, "_sublet_role", "") in ("input", "decision")]
    assert sorted(getattr(x, "_sublet_role") for x in arrows) == ["decision"] * 2 + ["input"] * 2
    for x in arrows:
        end = x.xy if x._sublet_role == "input" else x.xyann            # the input's tip; the decision's start
        assert abs(end[1] - f0) < 1e-12, (x._sublet_role, end, f0)
    # a pair's labels: one line apart, the input above, the two lines' ink centered in the span
    ups, downs = role(b, "input_label"), role(b, "decision_label")
    assert [t.get_text() for t in ups] == [lab["b"]["demand"], lab["b"]["menus"]]
    assert [t.get_text() for t in downs] == [lab["b"]["route"], lab["b"]["decide"]]
    y_up, y_dn = {t.get_position()[1] for t in ups}, {t.get_position()[1] for t in downs}
    assert len(y_up) == len(y_dn) == 1
    (y_up,), (y_dn,) = y_up, y_dn
    assert abs(y_up - y_dn - 1.2 * style.TICK_PT / style.BP_PER_IN) < 1e-12
    plane = role(b, "borrowers", "patches")[0]
    top_gap = f0 - (y_up + max(fig1_v3._ink_in(t.get_text())[1] for t in ups))
    bottom_gap = (y_dn + min(fig1_v3._ink_in(t.get_text())[0] for t in downs)) - (plane.get_y() + plane.get_height())
    assert abs(top_gap - bottom_gap) < 1e-9 and top_gap >= 0.04, (top_gap, bottom_gap)
    # (c)'s test on its letter's baseline, as printed
    (test,) = role(c, "test")
    (letter,) = [t for t in fig.texts if t.get_text() == "(c)"]
    assert abs(printed(c, test) - letter.get_position()[1] * H) < 1e-9
    # the bottom reserve: no patch (its path; the 0.6-pt edge reaches 0.3 pt lower) and no text layout box in it
    assert fig1_v3.BOTTOM_PAD >= 0.08
    lowest = min(min(p.get_window_extent(r).y0 for ax in fig.axes for p in ax.patches),
                 min(t.get_window_extent(r).y0 for t in style.drawn_texts(fig)))
    assert lowest / fig.dpi >= fig1_v3.BOTTOM_PAD - 1e-6, lowest / fig.dpi
    assert style.text_overlaps(fig) == [] and style.texts_outside_page(fig) == []


def test_rows():
    """rows(): the minimum gaps need less than MIN_HEIGHT_IN (1.70 in, the height C62's restyle wants), so every
    height from there to the registered one fits, with the slack in STRETCH's shares; a smaller height is refused."""
    lo = fig1_v3.rows(fig1_v3.MIN_HEIGHT_IN)
    assert lo["need_in"] <= fig1_v3.MIN_HEIGHT_IN and lo["slack"] >= 0
    assert abs(sum(fig1_v3.STRETCH.values()) - 1.0) < 1e-12 and abs(sum(fig1_v3.A_STRETCH) - 1.0) < 1e-12
    hi = fig1_v3.rows(style.figure_spec("fig1v3").height_in)
    assert hi["span"] >= lo["span"] and hi["gap"] >= lo["gap"] and hi["pass"] >= lo["pass"]
    with pytest.raises(style.StyleError, match="below the height"):
        fig1_v3.rows(fig1_v3.MIN_HEIGHT_IN - 0.05)


def test_caption_draft(monkeypatch):
    """The caption draft fits the double-column budget (at most 5 lines of about 140 characters), names Sublet as
    critical-ratio renting inside Algorithm 1, the safe expert, the allowance and gamma = 1, cites no design ID."""
    lab = data()["labels"]
    cap = lab["caption"]
    assert lab["caption_printed_chars"] == fig1_v2.printed_chars(cap)
    assert lab["caption_lines_est"] <= fig1_v3.CAPTION_LINES == 5 and fig1_v3.CAPTION_LINE_CHARS == 140
    assert cap.startswith("(a)~Contract $k$") and "(b)~The platform's control plane" in cap and "(c)~One slot" in cap
    for s in ("Sublet, critical-ratio renting inside Algorithm~1", "safe expert", "allowance", r"$\gamma=1$",
              r"$r\ge s+\tau_k$", r"$D_k=\tau_k+H_k$", r"$r+H_k-\lambda$"):
        assert s in cap, s
    assert not re.search(r"\b(A[1-9]P?|BL\d|E\d{1,2}|T0g|Theorem W|Remark R)\b", cap)
    monkeypatch.setattr(fig1_v3, "CAPTION_LINE_CHARS", 50)
    with pytest.raises(style.StyleError, match="caption"):
        fig1_v3.collect()
