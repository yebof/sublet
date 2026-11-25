"""Tests of the figure style module code/sim/figs/style.py (design/figure_plan.md §5). Fast, no raw data; every
file is written under pytest's tmp_path (never into paper/ or code/sim/out/)."""
import dataclasses
import json
import math
import re

import matplotlib as mpl
import numpy as np
import pytest
from matplotlib import patheffects

from figs import style as st

# _figure's y label "ALG / OPT$_{\mathrm{eager}}$" (LABEL_PT, 7.97 pt) has a 5.58-pt subscript, a first script level,
# which does not warn (C62: a first-level script of 7-pt text, 4.9 pt, is the smallest glyph allowed);
# test_math_script_glyphs_below_the_first_script_level_warn asserts the warning for a second level, the other tests
# ignore GlyphSizeWarning.
pytestmark = pytest.mark.filterwarnings("ignore::figs.style.GlyphSizeWarning")


def _figure(name, *, legend=None, ratios=None, sharey=None):
    """A small valid figure at the registered size: one row of panels with labels, policies and a theory line."""
    spec = st.figure_spec(name)
    legend = (spec.width == "W2") if legend is None else legend
    ratios = ratios or ((1, 1, 1) if spec.width == "W2" else (1,))
    fig = st.new_figure(name)
    axes = st.panel_row(fig, ratios, legend=legend, sharey=sharey)
    x = np.array([1, 2, 4, 8, 16])
    for ax in axes:
        st.plot_policy(ax, "bl5", x, 1.0 + 0.05 * np.log2(x))
        st.plot_policy(ax, "sublet", x, 1.0 + 0.02 * np.log2(x))
        st.theory_line(ax, x, np.maximum(2, x), "upper", r"$\max(2,\rho)$")
        st.reference_line(ax, y=1.0)
        st.log2_axis(ax, "x")
        ax.set_xlabel(r"$\rho$")
        ax.set_ylabel(r"ALG / OPT$_{\mathrm{eager}}$")
    st.panel_letters(axes)
    if legend:
        st.legend_row(fig, ["bl5", "sublet"])
    else:
        st.corner_legend(axes[0], ["bl5", "sublet"])
    return fig, axes


def _dirs(tmp_path):
    return dict(pdf_dir=tmp_path / "paper_figures", out_dir=tmp_path / "out_figs")


def _written(tmp_path, name):
    d = _dirs(tmp_path)
    return [p for p in (d["pdf_dir"] / f"{name}.pdf", d["out_dir"] / f"{name}.json", d["out_dir"] / f"{name}.png")
            if p.exists()]


# ---------------------------------------------------------------------------------------------------------------
def test_rcparams_and_font():
    assert st.FONT_PATH.endswith("LiberationSans-Regular.ttf")
    rc = mpl.rcParams
    assert rc["font.sans-serif"][:2] == ["Liberation Sans", "Nimbus Sans"]
    assert "DejaVu Sans" not in rc["font.sans-serif"]
    assert rc["pdf.fonttype"] == 42 and rc["mathtext.fontset"] == "custom" and rc["mathtext.fallback"] == "stixsans"
    assert rc["mathtext.rm"] == "Liberation Sans" and rc["mathtext.it"] == "Liberation Sans:italic"
    assert rc["mathtext.bf"] == "Liberation Sans:bold"
    # C62: axis labels and panel titles at the caption size, every other text at 7 pt (style.TICK_PT)
    assert rc["axes.labelsize"] == st.LABEL_PT == st.CAPTION_PT and rc["axes.titlesize"] == st.CAPTION_PT
    assert rc["xtick.labelsize"] == 7 and rc["ytick.labelsize"] == 7 and rc["legend.title_fontsize"] == 7
    assert rc["legend.fontsize"] == 7 and rc["font.size"] == 7 and rc["legend.columnspacing"] == 1.0
    assert rc["lines.linewidth"] == 1.0 and rc["lines.markersize"] == 3.5 and rc["lines.markeredgewidth"] == 0.6
    assert rc["axes.linewidth"] == 0.6 and not rc["axes.spines.top"] and not rc["axes.spines.right"]
    assert not rc["axes.grid"] and rc["xtick.direction"] == "out" and rc["ytick.direction"] == "out"
    assert (rc["xtick.major.size"], rc["xtick.major.width"], rc["xtick.minor.size"], rc["xtick.minor.width"]) == \
        (3.0, 0.6, 1.5, 0.4)
    assert rc["savefig.bbox"] is None and not rc["figure.constrained_layout.use"] and not rc["figure.autolayout"]
    assert rc["errorbar.capsize"] == 0 and not rc["legend.frameon"]
    with pytest.raises(st.StyleError, match="cannot find the font"):
        st.require_font("No Such Font Family Sublet", rebuild=False)


def test_c62_type_scale_and_margins():
    """C62 (2026-11-24): no figure text larger than the caption text, IEEEtran's \\footnotesize at the 10-pt
    body, 8 TeX pt = 8 * 72 / 72.27 bp; the bold letters and axis labels at that size, every other text at 7 pt, the
    smallest glyph a first-level script of 7-pt text (4.9 pt). The margins that hold text are their 9-pt values less
    what the smaller text frees (style.py, at the constants)."""
    assert st.CAPTION_PT == 8 * 72 / 72.27 and abs(st.CAPTION_PT - 7.970) < 0.0005
    assert st.TEXT_MAX_PT == st.CAPTION_PT and st.TEXT_MIN_PT == 7.0 and st.TICK_PT == 7.0
    assert st.LABEL_PT == st.LETTER_PT == st.CAPTION_PT
    assert abs(st.SCRIPT_MIN_PT - 4.9) < 1e-12 and st.SCRIPT_MIN_PT == 0.7 * st.TEXT_MIN_PT
    assert st.CAPTION_PT + st.TEXT_TOL_PT < 8.0 and st.TEXT_TOL_PT > 0
    assert (st.MARGIN_RIGHT, st.MARGIN_BOTTOM, st.MARGIN_TOP, st.LEGEND_ROW, st.LEFT_LABEL, st.LEFT_SHARED) == \
        (0.06, 0.38, 0.12, 0.21, 0.43, 0.11)


def test_sizes_and_registry_heights():
    assert abs(st.W1 * 72 - 251.06) < 0.005 and abs(st.W2 * 72 - 514.07) < 0.005
    assert {k: (s.width, s.height_in) for k, s in st.FIGURES.items() if s.main} == {
        "fig1": ("W1", 2.4), "fig2": ("W1", 2.7), "fig3": ("W2", 2.4), "fig4": ("W2", 2.2), "fig5": ("W2", 2.2),
        "fig6": ("W1", 2.2), "fig7": ("W2", 2.4),
        "fig4v2": ("W2", 2.4),      # C45: C41 registers fig4v2, the paper's Fig. 4 (design/sublet_v2.md §11, W1)
        "fig1v2": ("W1", 2.4),      # C47: C46 registers fig1v2, the paper's Fig. 1, at fig1's size (ms6_spec M1)
        "fig1v3": ("W2", 1.70),     # C58: fig1v3, the paper's Fig. 1 (design/ms7/w_spec.md §4 W-G1); C62: 1.70 in
        "fig4v3": ("W2", 2.4)}      # C58: fig4v3, the paper's Fig. 3 (design/ms7/w_spec.md §4 W-G2)
    spec = st.register_supplementary("test_supp_a", "W1", 1.8)
    assert spec.size_in == (st.W1, 1.8) and not spec.main
    for bad in (1.7, 2.6):
        with pytest.raises(st.StyleError, match="outside"):
            st.register_supplementary("test_supp_b", "W2", bad)
    with pytest.raises(st.StyleError, match="main-text"):
        st.register_supplementary("fig3", "W2", 2.2)
    with pytest.raises(st.StyleError, match="not registered"):
        st.new_figure("fig99")


@pytest.mark.parametrize("name", ["fig6", "fig3"])
def test_w1_and_w2_figures_pass_finalize(tmp_path, name):
    import warnings
    fig, _ = _figure(name)
    with warnings.catch_warnings():
        warnings.simplefilter("error", st.GlyphSizeWarning)      # a first-level subscript (C62) is allowed
        rep = st.save(fig, name, {"x": [1, 2, 4, 8, 16]}, **_dirs(tmp_path))
    spec = st.figure_spec(name)
    assert abs(rep["width_bp"] - spec.width_in * 72) <= 0.5 and abs(rep["height_bp"] - spec.height_in * 72) <= 0.5
    assert rep["pages"] == 1 and rep["text_pt"] == [st.TICK_PT, st.LABEL_PT] == [7.0, st.CAPTION_PT]
    assert rep["min_glyph_pt"] == round(0.7 * st.LABEL_PT, 3) == 5.579 and rep["small_glyphs"] == []
    assert rep["outside_page"] == []
    assert len(_written(tmp_path, name)) == 3
    from PIL import Image
    with Image.open(_dirs(tmp_path)["out_dir"] / f"{name}.png") as im:
        assert abs(im.size[0] - spec.width_in * 300) <= 1 and abs(im.size[1] - spec.height_in * 300) <= 1


def test_stacked_rows_fig1_pass(tmp_path):
    """Fig. 1: a 0.74-in timeline above a 1.12-in trajectory in W1 x 2.4 in (rows placed with left/bottom/top, as
    fig1_guard.py places them; C62: (b) 0.90 in below the top, 1.00 in with a 0.98-in trajectory at 9 pt)."""
    fig = st.new_figure("fig1")
    (a,) = st.panel_row(fig, (1,), left=[0.16], bottom=1.50, top=0.16)
    (b,) = st.panel_row(fig, (1,), bottom=st.MARGIN_BOTTOM, top=0.90)
    a.plot([0, 1], [0, 1])
    a.axis("off")                                        # the timeline draws its own marks
    st.plot_policy(b, "sublet", [0, 1, 2], [0, 1, 3])
    b.set_xlabel("Time of day (h)")
    b.set_ylabel("Cost (USD)")
    st.panel_letters([a, b])
    rep = st.save(fig, "fig1", {"t": [0, 1, 2]}, **_dirs(tmp_path))
    assert abs(rep["height_bp"] - 2.4 * 72) <= 0.5
    assert np.allclose(st.axes_rect_in(a), (0.16, 1.50, st.W1 - 0.16 - st.MARGIN_RIGHT, 0.74), atol=0.01)
    assert np.allclose(st.axes_rect_in(b)[1:4:2], (st.MARGIN_BOTTOM, 2.4 - 0.90 - st.MARGIN_BOTTOM), atol=0.01)
    from figs import fig1_guard
    assert (fig1_guard.A_LEFT, fig1_guard.A_BOTTOM, fig1_guard.A_TOP, fig1_guard.B_TOP) == (0.16, 1.50, 0.16, 0.90)


def test_wrong_width_fails(tmp_path):
    fig, _ = _figure("fig6")
    fig.set_size_inches(3.5, 2.2)          # 252 bp: the 3.5-in width is 0.9 pt wider than \columnwidth
    with pytest.raises(st.FigureCheckError, match="page width 252.00 bp, expected 251.06 bp"):
        st.save(fig, "fig6", {"x": [1]}, **_dirs(tmp_path))
    assert _written(tmp_path, "fig6") == []
    assert not any(_dirs(tmp_path)["pdf_dir"].iterdir())


def test_wrong_height_fails(tmp_path):
    fig, _ = _figure("fig5")
    fig.set_size_inches(st.W2, 2.3)
    with pytest.raises(st.FigureCheckError, match="page height 165.60 bp, expected 158.40 bp"):
        st.save(fig, "fig5", {"x": [1]}, **_dirs(tmp_path))
    assert _written(tmp_path, "fig5") == []


@pytest.mark.parametrize("size", [6.5, 6.99, 8, 9, 11])
def test_text_outside_the_c62_scale_fails(tmp_path, size):
    """C62: a text below 7 pt or larger than the caption (7.970 bp) fails, 8 bp and the former 9 pt included."""
    fig, axes = _figure("fig6")
    axes[0].text(2, 1.5, "annotation", fontsize=size)
    with pytest.raises(st.FigureCheckError,
                       match=re.escape(f"'annotation' at {size:g} pt is outside [7, 7.970] pt")):
        st.save(fig, "fig6", {"x": [1]}, **_dirs(tmp_path))
    assert _written(tmp_path, "fig6") == []


@pytest.mark.parametrize("size", [7.0, 7.5, 8 * 72 / 72.27])
def test_text_at_the_caption_size_passes(tmp_path, size):
    """C62: a text at 7 pt, between, or at exactly the caption size (8 TeX pt = 7.970 bp) passes."""
    fig, axes = _figure("fig6")
    axes[0].text(2, 1.5, "annotation", fontsize=size)
    rep = st.save(fig, "fig6", {"x": [1]}, **_dirs(tmp_path))
    assert size in rep["text_pt"] and max(rep["text_pt"]) <= st.CAPTION_PT


def test_direct_label_colors_read_on_white():
    """Direct labels use Policy.label_color: at least 4.5:1 contrast against white for every policy; the dark colors
    (Sublet's blue) unchanged, the light ones (orange, sky blue) darkened in the same hue, yellow BL3/BL4 black."""
    import matplotlib.colors as mcolors

    def contrast(c):
        lin = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in mcolors.to_rgb(c)]
        return 1.05 / (0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2] + 0.05)
    for k, p in st.POLICIES.items():
        assert contrast(p.label_color) >= 4.5, k
    assert st.policy("sublet").label_color == "#0072B2" and st.policy("bl3").label_color == "#000000"
    for k in ("bl1", "bl5", "a6"):
        c, d = (np.asarray(mcolors.to_rgb(v)) for v in (st.policy(k).color, st.policy(k).label_color))
        assert contrast(st.policy(k).color) < 4.5 and np.allclose(d / d.max(), c / c.max(), atol=0.02), k
    fig, axes = _figure("fig6")
    t = st.direct_label(axes[0], "bl1", 2.0, 1.5)
    assert mcolors.to_hex(t.get_color()) == st.policy("bl1").label_color


def test_ygrid_ends_with_the_x_spine():
    """ygrid draws its lines at the major y ticks inside the y limits and only as far as the bottom spine's bounds,
    so a label column right of the data stays free of grid lines; without bounds it spans the x limits."""
    fig = st.new_figure("fig6")
    (ax,) = st.panel_row(fig, (1,))
    ax.plot([2, 64], [1, 20])
    st.log2_axis(ax, "x")
    st.log_axis(ax, "y", ticks=[1, 2, 5, 10, 20])
    ax.set_xlim(1.8, 200)
    ax.set_ylim(0.9, 25)
    st.ygrid(ax)
    st.ygrid(ax)                                          # once per axes
    (grid,) = [c for c in ax.collections if type(c).__name__ == "_YGrid"]
    fig.canvas.draw()
    segs = grid.get_segments()
    assert [s[0][1] for s in segs] == [1, 2, 5, 10, 20] and {(s[0][0], s[1][0]) for s in segs} == {(1.8, 200)}
    ax.spines["bottom"].set_bounds(2, 64)
    fig.canvas.draw()
    assert {(s[0][0], s[1][0]) for s in grid.get_segments()} == {(2, 64)}
    assert not any(line.get_visible() for line in ax.get_ygridlines())


def test_letters_of_shared_panels_end_left_of_the_spine():
    """A panel that shares its left neighbor's y axis has a 0.11-in reserve, narrower than a bold 7.97-pt "(b)": its
    letter ends LETTER_SPINE_GAP_PT left of its y spine instead of sitting on the spine's top; the row keeps one
    baseline, and a panel with the full reserve keeps its letter at the slot's left edge."""
    fig = st.new_figure("fig5")
    axes = st.panel_row(fig, (1, 1, 1), sharey=(False, True, True))
    letters = st.panel_letters(axes)
    r = fig.canvas.get_renderer()
    assert len({t.get_position()[1] for t in letters}) == 1
    assert abs(letters[0].get_position()[0]) < 1e-9
    for t, ax in zip(letters[1:], axes[1:]):
        assert t.get_window_extent(r).width / fig.dpi > st.LEFT_SHARED          # the case this rule is for
        right_in = t.get_window_extent(r).x1 / fig.dpi
        assert abs(st.axes_rect_in(ax)[0] - st.LETTER_SPINE_GAP_PT / 72 - right_in) < 0.005


def test_theory_labels_read_on_white():
    """Theory lines keep #7F7F7F; their labels use THEORY_LABEL_GREY, the same grey at 4.5:1 against white."""
    import matplotlib.colors as mcolors
    fig, axes = _figure("fig6")
    line, txt = st.theory_line(axes[0], [1, 16], [2, 16], "upper", "bound")
    assert mcolors.to_hex(line.get_color()) == st.THEORY_GREY.lower()
    assert mcolors.to_hex(txt.get_color()) == st.THEORY_LABEL_GREY == st.readable_on_white(st.THEORY_GREY)
    assert st.THEORY_LABEL_GREY != st.THEORY_GREY.lower()


def test_overlapping_texts_fail(tmp_path):
    """Two labels set on top of each other fail finalize (text_overlaps); the same labels apart pass."""
    fig, axes = _figure("fig6")
    axes[0].text(2, 1.5, "first label", fontsize=st.TICK_PT)
    axes[0].text(2.2, 1.5, "second label", fontsize=st.TICK_PT)
    assert st.text_overlaps(fig) == [("first label", "second label")]
    with pytest.raises(st.FigureCheckError, match=re.escape("1 pairs of texts overlap: [('first label', "
                                                            "'second label')]")):
        st.save(fig, "fig6", {"x": [1]}, **_dirs(tmp_path))
    assert _written(tmp_path, "fig6") == []
    fig, axes = _figure("fig6")
    axes[0].text(0.3, 0.7, "first label", fontsize=st.TICK_PT, transform=axes[0].transAxes)
    axes[0].text(0.3, 0.4, "second label", fontsize=st.TICK_PT, transform=axes[0].transAxes)
    assert st.text_overlaps(fig) == []


def test_type3_font_fails(tmp_path):
    fig, _ = _figure("fig6")
    with mpl.rc_context({"pdf.fonttype": 3}):
        with pytest.raises(st.FigureCheckError, match="Type 3 font"):
            st.save(fig, "fig6", {"x": [1]}, **_dirs(tmp_path))
    assert _written(tmp_path, "fig6") == []


@pytest.mark.filterwarnings("ignore:There are no gridspecs with layoutgrids")
def test_layout_engine_and_moved_panels_fail(tmp_path):
    fig, _ = _figure("fig3")
    fig.set_layout_engine("constrained")
    with pytest.raises(st.FigureCheckError, match="layout engine"):
        st.save(fig, "fig3", {"x": [1]}, **_dirs(tmp_path))
    fig, axes = _figure("fig3")
    axes[1].set_position((0.3, 0.2, 0.2, 0.6))
    with pytest.raises(st.FigureCheckError, match="moved"):
        st.save(fig, "fig3", {"x": [1]}, **_dirs(tmp_path))


def test_pdf_embeds_liberation_sans_and_no_dejavu(tmp_path):
    fig, axes = _figure("fig3")
    axes[2].text(0.05, 0.3, r"$\bar{r}$, $\lambda$, $H^\star_\beta$ and $\geq$", fontsize=st.TICK_PT,
                 transform=axes[2].transAxes)
    rep = st.save(fig, "fig3", {"x": [1]}, **_dirs(tmp_path))
    fonts = st.pdf_fonts(_dirs(tmp_path)["pdf_dir"] / "fig3.pdf")
    names = [f["name"] for f in fonts]
    assert names == rep["fonts"]
    assert any(n.split("+")[-1] == "LiberationSans" for n in names)
    assert not any("dejavu" in n.lower() for n in names)
    assert all(f["emb"] == "yes" and "Type 3" not in f["type"] for f in fonts)


def test_pdf_is_deterministic(tmp_path):
    d1, d2 = tmp_path / "one", tmp_path / "two"
    for d in (d1, d2):
        fig, _ = _figure("fig6")
        st.save(fig, "fig6", {"x": [1]}, pdf_dir=d, out_dir=d)
    b1, b2 = (d1 / "fig6.pdf").read_bytes(), (d2 / "fig6.pdf").read_bytes()
    assert b"CreationDate" not in b1 and b1 == b2


# ---------------------------------------------------------------------------------------------------------------
def test_registry_unique_within_documented_figures():
    # C45: C41 adds fig4v2's set (design/sublet_v2.md §11, W1); C47: C46 adds fig1v2's (design/ms6_spec.md M1)
    assert set(st.FIGURE_POLICIES) == {f"fig{i}" for i in range(1, 8)} | {"fig4v2", "fig1v2", "fig1v3",
                                                                          "fig4v3"}     # C58: fig1v3, fig4v3
    for fig, keys in st.FIGURE_POLICIES.items():
        assert set(keys) <= set(st.POLICIES), fig
        st.check_policies(keys)                     # no shared triple; shared colors only within a family
    # decision 11 labels; only A8 around BL5 is "Sublet" in a legend
    assert st.POLICIES["a6"].label == "Two-timescale PD" and st.POLICIES["a7"].label == "PD heuristic"
    assert st.POLICIES["a7_guard"].label == "PD heuristic + guard"
    assert st.POLICIES["a7_g1"].label == "PD heuristic + one-way guard"     # C46 (design/ms6_spec.md M3)
    # C45: C41's sublet_v2 (A8P around A9) is "Sublet" in the MS5b figures, which never draw the legacy sublet (W7)
    assert [k for k, p in st.POLICIES.items() if p.label == "Sublet"] == ["sublet", "sublet_v2"]
    allowed = {c.upper() for c in st.OKABE_ITO} | {"#4D4D4D"}
    for p in st.POLICIES.values():
        assert p.color.upper() in allowed and p.fill in st.FILLS and p.group in st.GROUPS, p.key
        if p.marker is None:
            assert p.fill == "line"
    # §5's color reuse: these pairs share a color and never share a documented figure; C46: and the keys that Figs. 1, 3
    # and 5 draw since the MS6 gate (design/ms6_spec.md M1, M2) beside the other family of their color
    for a, b in [("sublet", "a1"), ("bl5", "prewarm"), ("bl1", "rr_renew"), ("bl1", "marking"), ("bl2", "bl6"),
                 ("a6", "a3"), ("sublet_v2", "a1"), ("bl5_g1", "prewarm"), ("bl5_lag", "prewarm"),
                 ("a7_g1", "bl3_0")]:
        assert st.POLICIES[a].color == st.POLICIES[b].color
        assert not any(a in ks and b in ks for ks in st.FIGURE_POLICIES.values()), (a, b)


def test_check_rejects_a_clash():
    reg = dict(st.POLICIES)
    reg["clone"] = dataclasses.replace(st.POLICIES["bl5"], key="clone", label="Clone")
    with pytest.raises(st.StyleError, match="bl5 and clone share"):
        st.check_unique(["sublet", "bl5", "clone"], reg)
    st.check_unique(["bl5", "bl5", "sublet"])               # one policy at two environment levels is allowed
    with pytest.raises(st.StyleError, match="share"):
        st.check_color_reuse(["sublet", "a1"])                # same color, different families
    with pytest.raises(st.StyleError, match="unknown policy key"):
        st.check_unique(["sublet", "no_such_policy"])
    # the two reference lines differ only by line style, which identifies a line without markers
    assert st.POLICIES["bl0a"].triple != st.POLICIES["bl0b"].triple


def test_policy_styles():
    s = st.policy_kwargs("sublet")
    assert (s["linewidth"], s["markersize"], s["markeredgewidth"]) == (1.5, 4.0, 0.6)
    assert s["zorder"] == max(p.zorder for p in st.POLICIES.values())
    b = st.policy_kwargs("bl5")
    assert (b["linewidth"], b["markersize"], b["markerfacecolor"], b["markeredgecolor"]) == (1.0, 3.5, "white",
                                                                                            "#56B4E9")
    assert st.policy_kwargs("bl4")["markeredgecolor"] == "#000000"
    assert st.policy_kwargs("bl1", env=("lender", "spot"))["linestyle"] == "--"
    assert st.policy_kwargs("bl1", env=("lender", "maas"))["linestyle"] == "-"
    assert st.ENV_LINESTYLES == {"lender": {"maas": "-", "spot": "--"}, "information": {"private": "-", "public": "--"},
                                 "sharing": {"shared": "-", "siloed": "--"},
                                 # C58 (W-G4): X1's demand and X2's calibration window
                                 "demand": {"revealed": "-", "lagged": "--"}, "calibration": {"oos": "-", "is": "--"}}
    assert {f: set(v) for f, v in st.ENV_LABELS.items()} == {f: set(v) for f, v in st.ENV_LINESTYLES.items()}  # C58
    fig = st.new_figure("fig7")
    (ax,) = st.panel_row(fig, (1,))
    st.plot_policy(ax, "a1", [0, 1], [1, 2], env=("lender", "maas"))
    st.plot_policy(ax, "a1", [0, 1], [1, 3], env=("lender", "spot"))
    with pytest.raises(st.StyleError, match="one environment factor per figure"):
        st.plot_policy(ax, "bl6", [0, 1], [1, 2], env=("information", "public"))


def test_legend_order_and_row():
    keys = ["lb", "bl1", "a7", "bl1_guard", "bl0a", "sublet", "a6", "bl5", "a7_guard", "opt"]
    assert st.legend_order(keys) == ["sublet", "a7_guard", "bl1_guard", "a7", "a6", "bl5", "bl1", "bl0a", "opt",
                                     "lb"]
    fig = st.new_figure("fig3")
    st.panel_row(fig, (1, 1, 1), legend=True)
    leg = st.legend_row(fig, ["bl5", "sublet", "a6"], extra=st.env_handles("lender"))
    assert [t.get_text() for t in leg.get_texts()] == ["Sublet", "Two-timescale PD", "RetroRenting-style", "MaaS",
                                                       "Spot"]
    assert not leg.get_frame_on() and leg._ncols == 5
    with pytest.raises(st.StyleError, match="wider than the figure"):
        st.legend_row(fig, list(st.POLICIES))
    assert fig.legends == [leg]                       # a legend row that does not fit is not left on the figure


def test_theory_and_reference_lines():
    fig = st.new_figure("fig5")
    (ax,) = st.panel_row(fig, (1,))
    x = np.array([1.0, 2.0, 4.0])
    want = {"upper": ("--", 0.75), "lower": (":", 0.9), "exact": ("-", 0.75), "limit": ("-", 0.75),
            "unproven": ("-.", 0.75)}
    for kind, (ls, lw) in want.items():
        line, txt = st.theory_line(ax, x, x + 1, kind, f"{kind} Limit")
        assert (line.get_linestyle(), line.get_linewidth(), line.get_color()) == (ls, lw, "#7F7F7F")
        assert txt.get_text() == f"{kind} Limit" and txt.xy == (4.0, 5.0) and txt.get_fontsize() == st.TICK_PT
        assert line.get_label().startswith("_")
        # the line is behind the data, its label above all data (Sublet and bands included) with a white halo
        assert line.get_zorder() < min(p.zorder for p in st.POLICIES.values() if p.group != "reference")
        assert txt.get_zorder() > max(p.zorder for p in st.POLICIES.values())
        (pe,) = txt.get_path_effects()
        assert isinstance(pe, patheffects.withStroke) and pe._gc["foreground"] == "white"
        assert pe._gc["linewidth"] == pytest.approx(2.1)
    with pytest.raises(st.StyleError, match="labeled as such"):
        st.theory_line(ax, x, x, "limit", r"$\rho m/(m+\rho-1)$")
    with pytest.raises(st.StyleError, match="give a label"):
        st.theory_line(ax, x, x, "upper", "")
    line, _ = st.theory_line(ax, x, x, "lower", "LB", on_heatmap=True)
    halos = [ln for ln in ax.lines if getattr(ln, "_sublet_role", "") == "halo"]
    assert len(halos) == 1 and halos[0].get_color() == "white" and halos[0].get_zorder() < line.get_zorder()
    ref = st.reference_line(ax, y=1.0)
    assert (ref.get_linewidth(), ref.get_color(), ref.get_linestyle()) == (0.5, "#BDBDBD", "-")
    st.plot_policy(ax, "sublet", x, x)
    handles, labels = ax.get_legend_handles_labels()
    assert labels == ["Sublet"]


def test_panel_geometry_matches_margins(tmp_path):
    tol = 0.01
    L, S, B, T, R = st.LEFT_LABEL, st.LEFT_SHARED, st.MARGIN_BOTTOM, st.MARGIN_TOP, st.MARGIN_RIGHT
    fig, axes = _figure("fig3")
    w = (st.W2 - 3 * L - R) / 3
    h = st.figure_spec("fig3").height_in - B - T - st.LEGEND_ROW
    for i, ax in enumerate(axes):
        assert np.allclose(st.axes_rect_in(ax), (L * (i + 1) + w * i, B, w, h), atol=tol)
    st.save(fig, "fig3", {"x": [1]}, **_dirs(tmp_path))       # drawing does not move the panels
    for i, ax in enumerate(axes):
        assert np.allclose(st.axes_rect_in(ax), (L * (i + 1) + w * i, B, w, h), atol=tol)
    # Fig. 4 style: ratios 2:1:1, the third panel shares the y axis of the second, no legend row
    fig = st.new_figure("fig4")
    axes = st.panel_row(fig, (2, 1, 1), sharey=(False, False, True))
    avail = st.W2 - (L + L + S) - R
    x0 = [L, L + avail / 2 + L, L + avail / 2 + L + avail / 4 + S]
    for ax, x, r in zip(axes, x0, (2, 1, 1)):
        assert np.allclose(st.axes_rect_in(ax), (x, B, avail * r / 4, 2.2 - B - T), atol=tol)
    assert axes[2].get_shared_y_axes().joined(axes[1], axes[2])
    assert not any(t.get_visible() for t in axes[2].get_yticklabels())
    # a measured reserve for name tick labels
    res = st.ytick_reserve(fig, ["RetroRenting-style", "Sublet"])
    assert 0.8 < res < 1.2
    axes = st.panel_row(st.new_figure("fig4"), (2, 1, 1), left=(res, None, None))
    assert abs(st.axes_rect_in(axes[0])[0] - res) < tol and abs(st.axes_rect_in(axes[1])[0] -
                                                                (res + st.axes_rect_in(axes[0])[2] + L)) < tol
    # panel letters: one baseline per row, at each slot's left edge
    fig, axes = _figure("fig3")
    letters = [t for t in fig.texts if getattr(t, "_sublet_role", "") == "panel_letter"]
    assert [t.get_text() for t in letters] == ["(a)", "(b)", "(c)"]
    assert len({t.get_position()[1] for t in letters}) == 1
    assert all(t.get_fontsize() == st.LETTER_PT and t.get_fontweight() == "bold" for t in letters)
    assert np.allclose([t.get_position()[0] * st.W2 for t in letters], [0.0, L + w, 2 * (L + w)], atol=tol)


def test_json_extract_written(tmp_path):
    fig, _ = _figure("fig6")
    data = {"rho": np.array([1, 2, 4]), "ratio": np.array([1.5, np.nan, 2.25]), "n": np.int64(3),
            "series": {"sublet": [np.float64(1.0), 1.1]}}
    sources = ["code/sim/out/q44_study/summary.json", "code/theory_checks/c3/o1/out/o1_lb.json",
               "code/analysis/out/a11_calibration.json"]
    st.save(fig, "fig6", data, sources=sources, **_dirs(tmp_path))
    got = json.loads((_dirs(tmp_path)["out_dir"] / "fig6.json").read_text())
    assert got["figure"] == "fig6" and got["size_in"] == [round(st.W1, 4), 2.2] and got["sources"] == sources
    assert got["data"] == {"rho": [1, 2, 4], "ratio": [1.5, None, 2.25], "n": 3, "series": {"sublet": [1.0, 1.1]}}
    for bad in ("code/sim/configs/example_1day.json", "/mnt/data/datasets/x.csv", "code/theory_checks/c3/core.py"):
        with pytest.raises(st.StyleError, match="read only"):
            st.check_source(bad)
    with pytest.raises(st.StyleError, match="infinite"):
        st.save(fig, "fig6", {"x": [math.inf]}, **_dirs(tmp_path))
    with pytest.raises(st.StyleError, match="non-empty"):
        st.save(fig, "fig6", {}, **_dirs(tmp_path))


def test_output_roots_default_and_override(tmp_path, monkeypatch):
    monkeypatch.delenv(st.ENV_PDF_DIR, raising=False)
    monkeypatch.delenv(st.ENV_OUT_DIR, raising=False)
    assert st.output_dirs() == (st.REPO / "paper" / "figures", st.REPO / "code" / "sim" / "out" / "figs")
    monkeypatch.setenv(st.ENV_PDF_DIR, str(tmp_path / "p"))
    monkeypatch.setenv(st.ENV_OUT_DIR, str(tmp_path / "o"))
    fig, _ = _figure("fig6")
    rep = st.save(fig, "fig6", {"x": [1]})
    assert rep["pdf"] == str(tmp_path / "p" / "fig6.pdf") and rep["json"] == str(tmp_path / "o" / "fig6.json")
    assert (tmp_path / "o" / "fig6.png").is_file()


def test_rasterize_dense(tmp_path):
    fig, axes = _figure("fig6")
    rng = np.random.default_rng(0)
    dense = axes[0].scatter(rng.uniform(1, 16, 6000), rng.uniform(1, 2, 6000), s=1, color="#7F7F7F")
    (sparse,) = axes[0].plot(np.linspace(1, 16, 100), np.ones(100))
    st.save(fig, "fig6", {"x": [1]}, **_dirs(tmp_path))
    assert dense.get_rasterized() and not sparse.get_rasterized()
    assert b"/Subtype /Image" in (_dirs(tmp_path)["pdf_dir"] / "fig6.pdf").read_bytes()


def test_axis_helpers_and_colors():
    fig = st.new_figure("fig5")
    a, b, c = st.panel_row(fig, (1, 1, 1), legend=True)
    a.plot([1, 64], [1, 2])
    st.log2_axis(a, "x")
    a.set_xlim(1, 64)
    fig.canvas.draw()
    locs = [v for v in a.xaxis.get_majorticklocs() if 1 <= v <= 64]
    assert [a.xaxis.get_major_formatter()(v) for v in locs] == ["1", "2", "4", "8", "16", "32", "64"]
    assert isinstance(a.xaxis.get_minor_locator(), mpl.ticker.NullLocator)
    st.symlog_minutes(b, "x")
    assert b.xaxis.get_transform().linthresh == 1.0
    st.log_axis(c, "y")
    assert st.PLAIN(1000.0) == "1000" and st.PLAIN(0.5) == "0.5" and st.PLAIN(-2.0) == "−2"
    st.ygrid(c)
    norm = st.ratio_norm(0.8, 2.5)
    assert abs(norm(1.0) - 0.5) < 1e-12 and norm.vmax == 2.5 and abs(norm.vmin - 0.4) < 1e-12
    assert st.RATIO_CMAP == "PuOr"
    for kind in ("cividis", "greys"):
        cols = st.ramp(5, kind)
        assert len(set(cols)) == 5
    assert st.ramp(3, "greys")[0] != "#ffffff"


def _h_axis_figure(**kw):
    fig = st.new_figure("fig6")
    (ax,) = st.panel_row(fig, (1,))
    ax.plot([0, 240], [1, 2])
    st.symlog_minutes(ax, "x", **kw)
    ax.set_xlim(0, 240)
    return fig, ax


def _end_alignment(ax):
    """{tick value: horizontal alignment of its label} of the symlog H axis (FixedLocator: tick i is H_TICKS_MIN[i])."""
    ticks = ax.xaxis.get_major_ticks(len(st.H_TICKS_MIN))
    return {v: tk.label1.get_horizontalalignment() for v, tk in zip(st.H_TICKS_MIN, ticks)}


def test_text_outside_page_fails_and_end_label_stays_inside(tmp_path):
    """A centered tick label at the right end of the x axis sticks out of the 0.06-in right margin and is cut off
    at the page edge: save() fails and writes nothing. symlog_minutes right-aligns that label by default."""
    fig, _ = _h_axis_figure(end_inside=False)
    with pytest.raises(st.FigureCheckError, match=re.escape("text partly outside the page: ['240']")):
        st.save(fig, "fig6", {"x": [1]}, **_dirs(tmp_path))
    assert _written(tmp_path, "fig6") == []
    fig, ax = _h_axis_figure()
    rep = st.save(fig, "fig6", {"x": [1]}, **_dirs(tmp_path))
    assert rep["outside_page"] == [] and len(_written(tmp_path, "fig6")) == 3
    al = _end_alignment(ax)
    assert al[240] == "right" and {al[v] for v in st.H_TICKS_MIN if v != 240} == {"center"}
    ax.set_xlim(0, 60)                                    # the alignment follows the x limits
    al = _end_alignment(ax)
    assert al[60] == "right" and al[240] == "center"
    fig, _ = _figure("fig3")
    rep = st.save(fig, "fig3", {"x": [1]}, **_dirs(tmp_path))
    assert rep["outside_page"] == []


def test_font_cache_rebuild_in_user_cache_only(tmp_path):
    """With a matplotlib font cache that lacks Liberation Sans, importing figs.style rebuilds the cache in the
    user-level cache folder (here MPLCONFIGDIR = tmp_path) and finds the font; no system file is touched."""
    import copy
    import os
    import subprocess
    import sys
    from pathlib import Path

    from matplotlib import font_manager as fm
    stale = copy.copy(fm.fontManager)
    stale.ttflist = [f for f in fm.fontManager.ttflist if "Liberation" not in f.name]
    cache = tmp_path / f"fontlist-v{fm.FontManager.__version__}.json"
    fm.json_dump(stale, cache)
    assert "Liberation Sans" not in cache.read_text()
    env = dict(os.environ, MPLCONFIGDIR=str(tmp_path), PYTHONDONTWRITEBYTECODE="1")
    code = ("import matplotlib.font_manager as fm; "
            "assert not any(f.name == 'Liberation Sans' for f in fm.fontManager.ttflist); "
            "from figs import style; print(style.FONT_PATH)")
    r = subprocess.run([sys.executable, "-c", code], cwd=Path(st.__file__).resolve().parents[1], env=env,
                       capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip().endswith("LiberationSans-Regular.ttf")
    assert "Liberation Sans" in cache.read_text()


def test_nimbus_fallback_embeds_and_warns(tmp_path):
    """Text set explicitly in Nimbus Sans (§5's fallback family, which the RC never selects while Liberation Sans is
    installed; a glyph that Liberation Sans lacks is not taken from it, see test_missing_glyph_fails) is embedded
    (OpenType/CFF, not Type 3), so finalize passes, but poppler reports a font-type mismatch, which finalize passes
    on as a FigureWarning."""
    fig, axes = _figure("fig6")
    axes[0].text(2, 1.5, "fallback", family="Nimbus Sans")
    with pytest.warns(st.FigureWarning, match="pdffonts reports"):
        rep = st.save(fig, "fig6", {"x": [1]}, **_dirs(tmp_path))
    assert any("NimbusSans" in n for n in rep["fonts"])


def test_missing_glyph_fails(tmp_path):
    """Liberation Sans lacks U+2713 (check mark). The glyph fallback chain is Liberation Sans alone (font.family
    "sans-serif"; Nimbus Sans is a family fallback only), so matplotlib would draw an empty box; so would mathtext in
    the non-math part of a label with math (its font 'default' has no fallback), and in math for a glyph that neither
    Liberation Sans nor the stixsans fallback has (U+2603, snowman) it would draw a dummy symbol. save() then fails and
    writes nothing. In math, U+2713 comes from the fallback (STIXGeneral) and the figure passes."""
    from pathlib import Path

    from matplotlib.font_manager import FontProperties, fontManager
    chain = fontManager._find_fonts_by_props(FontProperties(family=mpl.rcParams["font.family"]))
    assert [Path(p).name for p in chain] == ["LiberationSans-Regular.ttf"]
    for label, msg in (("Glyph ✓ test", "Glyph 10003 (\\N{CHECK MARK}) missing from font(s) Liberation Sans"),
                       ("x ✓ $\\rho$", "Font 'default' does not have a glyph for '\\u2713'"),
                       ("$☃$", "does not have a glyph for '\\u2603'")):
        fig, axes = _figure("fig6")
        axes[0].set_xlabel(label)
        with pytest.raises(st.FigureCheckError, match=re.escape(msg)):
            st.save(fig, "fig6", {"x": [1]}, **_dirs(tmp_path))
        assert _written(tmp_path, "fig6") == []
    fig, axes = _figure("fig6")
    axes[0].set_xlabel("$✓$")
    rep = st.save(fig, "fig6", {"x": [1]}, **_dirs(tmp_path))
    assert any(n.endswith("+STIXGeneral-Regular") for n in rep["fonts"])


def test_math_script_glyphs_below_the_first_script_level_warn(tmp_path):
    """Mathtext sets a sub- or superscript at 0.7 of the text size per level: the 7-pt label LB_react has 4.9-pt
    glyphs, allowed (SCRIPT_MIN_PT, C62); a second script level (3.43 pt) warns (GlyphSizeWarning). The nominal sizes
    stay at 7 pt and, for the x label, LABEL_PT; finalize reports the smallest glyph."""
    import warnings
    s, s2 = r"LB$_{\mathrm{react}}$", r"$H^{\star}_{\mu_1}$"
    fig = st.new_figure("fig6")
    (ax,) = st.panel_row(fig, (1,))
    ax.plot([0, 1], [1, 2])
    ax.set_xlabel("Notice (min)")
    ax.text(0.1, 1.5, s, fontsize=st.TICK_PT)
    assert [(round(g, 3), t) for g, t in st.math_glyph_sizes(fig)] == [(4.9, s)]
    with warnings.catch_warnings():
        warnings.simplefilter("error", st.GlyphSizeWarning)
        rep = st.save(fig, "fig6", {"x": [1]}, **_dirs(tmp_path))
    assert rep["text_pt"] == [st.TICK_PT, st.LABEL_PT]
    assert rep["min_glyph_pt"] == 4.9 and rep["small_glyphs"] == []
    fig = st.new_figure("fig6")
    (ax,) = st.panel_row(fig, (1,))
    ax.plot([0, 1], [1, 2])
    ax.set_xlabel("Notice (min)")
    ax.text(0.1, 1.5, s2, fontsize=st.TICK_PT)
    with pytest.warns(st.GlyphSizeWarning, match="mu"):
        rep = st.save(fig, "fig6", {"x": [1]}, **_dirs(tmp_path))
    assert rep["min_glyph_pt"] == 3.43 and rep["small_glyphs"] == [[3.43, s2]]


def test_yellow_policies_get_black_uncertainty_bars():
    """BL3 and BL4 (#F0E442 with a black edge): their 0.6-pt bars take the black edge color, and a band (yellow at
    alpha 0.18, almost white) is refused."""
    fig = st.new_figure("fig4")
    (ax,) = st.panel_row(fig, (1,))
    for key, want in (("bl4", "#000000"), ("bl3", "#000000"), ("bl5", "#56b4e9")):
        c = st.errorbars(ax, key, [1, 2], [1, 1], [0.9, 0.9], [1.1, 1.1])
        (bars,) = c.lines[2]
        assert {mpl.colors.to_hex(col) for col in bars.get_colors()} == {want}, key
    with pytest.raises(st.StyleError, match="errorbars"):
        st.band(ax, "bl4", [1, 2], [0.9, 0.9], [1.1, 1.1])
    b = st.band(ax, "bl5", [1, 2], [0.9, 0.9], [1.1, 1.1])
    assert np.allclose(b.get_facecolor()[0], mpl.colors.to_rgba("#56B4E9", 0.18))


def test_legend_row_needs_the_legend_reserve():
    """A legend row over panels placed without the 0.21-in reserve would cover the axes tops and the panel letters."""
    fig = st.new_figure("fig3")
    st.panel_row(fig, (1, 1, 1))
    with pytest.raises(st.StyleError, match=re.escape("panel_row(..., legend=True)")):
        st.legend_row(fig, ["sublet", "bl5"])
    assert fig.legends == []
    with pytest.raises(st.StyleError, match="no panel_row axes"):
        st.legend_row(st.new_figure("fig3"), ["sublet"])
    fig = st.new_figure("fig3")                              # the reserve given through `top` is accepted
    st.panel_row(fig, (1, 1, 1), top=st.MARGIN_TOP + st.LEGEND_ROW)
    assert len(st.legend_row(fig, ["sublet"]).get_texts()) == 1


def test_font_subsets_get_distinct_tags(tmp_path):
    """matplotlib names every subset of a face alike (FRZNSF+LiberationSans in every figure); save() gives each
    subset a tag of its own, which differs between figures and between texts of one figure."""
    tags = {}
    for name, text, d in (("fig6", "AAAA BBBB", "a"), ("fig6", "qqqq zzzz", "b"), ("fig2", "AAAA BBBB", "c")):
        fig = st.new_figure(name)
        (ax,) = st.panel_row(fig, (1,))
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_xlabel(text)
        st.panel_letters([ax])
        rep = st.save(fig, name, {"x": [1]}, pdf_dir=tmp_path / d, out_dir=tmp_path / d)
        names = [f["name"] for f in st.pdf_fonts(tmp_path / d / f"{name}.pdf")]
        assert names == rep["fonts"] and all(re.fullmatch(r"[A-Z]{6}\+[A-Za-z-]+", n) for n in names)
        tag = {n.split("+")[1]: n.split("+")[0] for n in names}
        assert set(tag) == {"LiberationSans", "LiberationSans-Bold"} and len(set(tag.values())) == 2
        tags[d] = tag
    assert tags["a"]["LiberationSans"] != tags["b"]["LiberationSans"]        # one figure, other text
    assert tags["a"]["LiberationSans"] != tags["c"]["LiberationSans"]        # same text, other figure
    assert tags["a"]["LiberationSans-Bold"] != tags["c"]["LiberationSans-Bold"]


# ---------------------------------------------------------------------------------------------------------------
# The ink-outside check at every figure size (C1 of the MS3 fixes): the bordered rendering is often a pixel smaller
# than (W + 0.6) x (H + 0.6) in at the render dpi (e.g. 1547 x 560 px for W2 x 2.2 in at 200 dpi), which once made
# the check skip itself at every size but W1 x 2.2 in; it now reads the image size back.
SUPP_SIZES_IN_USE = (("W1", 2.0), ("W1", 2.2), ("W1", 2.4), ("W2", 2.2), ("W2", 2.5),   # sizes of the sf_* figures
                     ("W2", 2.3),       # C62 (group g1): sf_e10_rho, 2.3 in (2.5 in at 9 pt)
                     ("W2", 1.9))       # C62 (group g2): sf_e6b, 1.9 in (2.2 in at 9 pt; its keys on the letters' line)
EDGES = {"left": dict(x=0.0, y=0.5, ha="center", va="center"), "right": dict(x=1.0, y=0.5, ha="center", va="center"),
         "top": dict(x=0.5, y=1.0, ha="center", va="center"), "bottom": dict(x=0.5, y=0.0, ha="center", va="center")}


def _sizes():
    main = sorted({(s.width, s.height_in) for s in st.FIGURES.values() if s.main})
    return main + [s for s in SUPP_SIZES_IN_USE if s not in main]


def _figure_at(size):
    """A registered figure name at `size` (a main-text figure, else a test supplementary figure)."""
    for k, s in st.FIGURES.items():
        if s.main and (s.width, s.height_in) == size:
            return k
    return st.register_supplementary(f"test_ink_{size[0]}_{size[1]:g}", *size).name


def _plain_figure(name, *, top=None):
    """A clean figure: one row of panels with tick labels, axis labels, panel letters and a corner legend."""
    fig = st.new_figure(name)
    axes = st.panel_row(fig, (1, 1) if st.figure_spec(name).width == "W2" else (1,), top=top)
    for ax in axes:
        st.plot_policy(ax, "sublet", [1, 2, 4], [1.0, 1.1, 1.3])
        ax.set_xlabel("Sites m")
        ax.set_ylabel("Cost / all-fallback")
    letters = st.panel_letters(axes)
    st.corner_legend(axes[0], ["sublet"], loc="lower right")
    return fig, axes, letters


def test_supplementary_sizes_in_use_are_covered():
    """Every registered supplementary figure (all figs.supp scripts imported) has a size the ink tests cover."""
    import importlib
    import pkgutil

    import figs.supp
    for m in pkgutil.iter_modules(figs.supp.__path__):
        importlib.import_module(f"figs.supp.{m.name}")
    used = {(s.width, s.height_in) for k, s in st.FIGURES.items() if not s.main and not k.startswith("test_")}
    assert used and used <= set(_sizes()), used - set(_sizes())


@pytest.mark.parametrize("size", _sizes(), ids=lambda s: f"{s[0]}x{s[1]:g}")
def test_ink_check_at_every_size(tmp_path, size):
    """At each registered size: the bordered rendering's pixel size is read back (not assumed), a clean figure
    passes finalize, and a text half past any one page edge fails it with the text named; nothing is written."""
    import io

    from matplotlib.transforms import Bbox
    from PIL import Image
    name = _figure_at(size)
    fig, _, _ = _plain_figure(name)
    W, H = fig.get_size_inches()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=200, bbox_inches=Bbox([[-0.3, -0.3], [W + 0.3, H + 0.3]]))
    with Image.open(io.BytesIO(buf.getvalue())) as im:
        nx, ny = im.size
    assert abs(nx - (W + 0.6) * 200) <= 1.5 and abs(ny - (H + 0.6) * 200) <= 1.5
    assert st.ink_outside_sides(fig) == {"left": False, "right": False, "top": False, "bottom": False}
    rep = st.save(fig, name, {"x": [1]}, **_dirs(tmp_path))
    assert rep["outside_page"] == [] and len(_written(tmp_path, name)) == 3
    for edge, kw in EDGES.items():
        d = tmp_path / edge
        fig, _, _ = _plain_figure(name)
        fig.text(kw["x"], kw["y"], "past the edge", ha=kw["ha"], va=kw["va"], fontsize=st.TICK_PT)
        assert st.ink_outside_sides(fig)[edge] and sum(st.ink_outside_sides(fig).values()) == 1, edge
        with pytest.raises(st.FigureCheckError, match=re.escape("text partly outside the page: ['past the edge']")):
            st.save(fig, name, {"x": [1]}, pdf_dir=d, out_dir=d)
        assert not d.exists() or not any(p.suffix in (".pdf", ".json", ".png") for p in d.iterdir()), edge


@pytest.mark.parametrize("size", [("W2", 2.2), ("W1", 2.2)], ids=["W2x2.2", "W1x2.2"])
def test_mathtext_accent_clipped_at_the_page_top_fails(tmp_path, size):
    """A mathtext panel title with a tilde (beta~, as in sf_e2_mu_cost) at LABEL_PT on the panel letters' baseline
    0.02 in higher than the default top margin puts it: the tilde rises above the page and the PDF would cut it off,
    so finalize fails (the check renders at 600 dpi; at 200 dpi the thin accent left no pixel darker than the ink
    threshold beyond the tolerance). At the default top margin (0.12 in since C62; at 9 pt the default 0.13 in clipped
    such a title) and with 0.04 in more the figure passes."""
    name = _figure_at(size)
    title = r"$\mu/\tilde{\beta}$ = 0.2"
    for extra, ok in ((-0.02, False), (0.0, True), (0.04, True)):
        fig, axes, letters = _figure_and_title(name, title, top=st.MARGIN_TOP + extra)
        if ok:
            rep = st.save(fig, name, {"x": [1]}, pdf_dir=tmp_path / "ok", out_dir=tmp_path / "ok")
            assert rep["outside_page"] == []
        else:
            assert st.ink_outside_sides(fig)["top"]
            with pytest.raises(st.FigureCheckError, match="outside the page"):
                st.save(fig, name, {"x": [1]}, pdf_dir=tmp_path / "bad", out_dir=tmp_path / "bad")


def _figure_and_title(name, title, *, top):
    fig, axes, letters = _plain_figure(name, top=top)
    r = fig.canvas.get_renderer()
    bb = letters[0].get_window_extent(r)
    fig.text((bb.x1 / fig.dpi + 3.0 / 72.0) / fig.get_size_inches()[0], letters[0].get_position()[1], title,
             ha="left", va="baseline", fontsize=st.LABEL_PT)                    # C62: a panel title at LABEL_PT
    return fig, axes, letters


def test_math_glyph_sizes_parses_multiline_labels_line_by_line(caplog):
    """C2 of the MS3 fixes: a two-line label with mathtext on one line ("LB$_T$\\n(C3-T4)", as in sf_e10_rho) is
    parsed line by line, as matplotlib lays it out: the subscript's size is found and mathtext logs nothing (it used
    to log "Font 'default' does not have a glyph for '\\n'" when handed the whole string)."""
    import logging
    fig = st.new_figure("fig6")
    (ax,) = st.panel_row(fig, (1,))
    ax.plot([0, 1], [1, 2])
    labels = ("LB$_T$\n(C3-T4)", "O1-C\nlimit", "max(2, $\\rho$),\nC3-Cor3 factor")
    for i, s in enumerate(labels):
        ax.text(0.2, 1.2 + 0.2 * i, s, fontsize=7)
    with caplog.at_level(logging.DEBUG, logger="matplotlib.mathtext"):
        got = {t: round(g, 3) for g, t in st.math_glyph_sizes(fig)}
    assert got == {labels[0]: 4.9, labels[2]: 7.0}
    assert not [r for r in caplog.records if "does not have a glyph" in r.getMessage()]
