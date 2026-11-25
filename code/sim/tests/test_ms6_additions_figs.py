"""Tests of the MS6 addition C46 to figs/style.py (design/ms6_spec.md §1.1 M1-M5, §2 U42; the entry gate, MS5b's W8);
C47, the pinned lines of the MS3-MS5b tests that C46 changes, is in those tests, each line naming C47.

- M3: the key a7_g1 "PD heuristic + one-way guard" as built (label, color, marker, fill, line style, group, family, the
  note of its tag), placed right after a7_guard and listed with the guarded policies; its triple and its (color, marker)
  pair are no other key's; its label and the labels of the other configuration keys are the names that Table II v2
  prints. M3, M4 (review of the gate): the key a7_ms4, the same guard at MS4's allowance (E7's and S1's tag A7G), with
  sublet_ms4's allowance suffix and its own triple, placed right after a7_g1; MS6_KEYS is the two.
- M2, M4: the fourteen frozen figures' sets moved to the configuration keys, each the frozen set under M4's rule
  (Algorithm 1's defaults: bl5_g1 and a7_g1; MS4's allowance: sublet_ms4 and a7_ms4; bl5 -> bl5_lag, bl1_guard ->
  bl1_g1, sublet_siloed left out) and within the registry, with unique keys and labels, passing check_policies; the
  (marker, fill) pairs drawn twice are exactly the recorded two (GREY_SHARED); the legacy entries keep their labels
  and triples, a7_guard is a legacy key, and the frozen fig1 and fig4 keep their sets.
- check_legacy: no figure outside LEGACY_PENDING draws a legacy key, LEGACY_PENDING is fig1 and fig4 with W8's and
  W6's notes, a7_g1 and a7_ms4 never share a figure with a7_guard, and a figure that draws an MS6 key with a legacy
  key fails.
- M1: fig1v2 registered as a main-text figure at the frozen fig1's size with the set (sublet_v2,), listed right after
  fig1 by the print sheet's order.
- M5: guard_pair_handles gives one entry per (inner, guarded) pair with the inner policy's registry label and the
  explanatory entry GUARD_PAIR_NOTE; each pair's handle holds the inner policy's open sample and the guarded key's
  filled sample in their registry styles; it rejects a pair that is not an open inner policy beside a filled guarded
  key of its family and color, a repeated key and an empty list; legend_row (two rows over Fig. 3's panels) and
  corner_legend draw the two samples of a pair side by side, inner first, and the figure passes finalize().
"""
from __future__ import annotations

import matplotlib.colors as mcolors
import pytest
from matplotlib.legend_handler import HandlerTuple
from matplotlib.lines import Line2D

from fixtures import SIM

from figs import print_sheet
from figs import style as st

REPO = SIM.parents[1]
TABLE2_V2 = REPO / "paper" / "floats" / "table2_policies_v2.tex"

pytestmark = pytest.mark.filterwarnings("ignore::figs.style.GlyphSizeWarning")

# ---------------------------------------------------------------- M2, M4: the sets before and after the gate
# the sets of the fourteen frozen figures that W8 lists, as they were before C46 (commit e17bf449)
FROZEN = {
    "fig3": ("sublet", "a7_guard", "bl1_guard", "a7", "a6", "bl5", "bl1", "bl2"),
    "fig5": ("sublet", "a2_frac", "a2_r1", "a2_theory", "a3", "rr_renew"),
    "sf_e1_sched": ("sublet", "a2_frac", "a2_r1", "a2_theory", "a3"),
    "sf_e11_inst": ("sublet", "a7_guard", "bl1_guard", "a7", "a6", "bl5", "bl1", "bl2"),
    "sf_e11_fam": ("sublet", "bl5", "a7", "a7_guard", "a2_theory", "a3", "rr_renew", "marking"),
    "sf_e11_guard": ("sublet", "a7_guard", "bl1_guard"),
    "sf_e3_util": ("sublet", "sublet_siloed", "a6", "a6_siloed", "bl2", "bl5"),
    "sf_e3_mu": ("sublet", "sublet_siloed", "a6", "a6_siloed", "bl2", "opt"),
    "sf_e5": ("sublet", "a6_red_off", "a6", "a6_always2", "bl3_n0", "bl3_n1", "bl3"),
    "sf_e7_mix": ("sublet", "a7_guard", "a7", "a6", "bl5", "bl1", "bl2", "bl4"),
    "sf_e7_mu": ("sublet", "a7_guard", "a7", "a6", "bl5", "bl1", "bl2", "bl4"),
    "sf_e7_allow": ("sublet", "bl5"),
    "sf_s1": ("sublet",),
    "sf_e9": ("sublet", "a6", "lb"),
}
# M4: the figures of Algorithm 1's defaults (E1(b), E11, and sf_e7_allow, whose axis sweeps B0) and of MS4's allowance
ALG1_DEFAULTS = ("fig3", "fig5", "sf_e1_sched", "sf_e11_inst", "sf_e11_fam", "sf_e11_guard", "sf_e7_allow")
MS4_ALLOWANCE = ("sf_e3_util", "sf_e3_mu", "sf_e5", "sf_e7_mix", "sf_e7_mu", "sf_s1", "sf_e9")
MOVE = {"bl5": "bl5_lag", "bl1_guard": "bl1_g1", "sublet_siloed": None}
# C46 (review of the gate): a7_guard by its allowance, as the frozen sublet (M4)
A7_GUARD = {"alg1": "a7_g1", "ms4": "a7_ms4"}
# (marker, fill) pairs drawn twice in a moved set: both keys' triples are fixed (bl1_g1 and sublet_ms4 by C41, bl2 and
# bl3 by the frozen registry); as built, Fig. 3 labels bl1_g1 directly in (a), sf_e11_inst tells bl1_g1 and bl2 apart
# by their dodge places, and sf_e5 keeps sublet_ms4 and bl3 in its legend rows, told apart by BL3's black edge and
# lighter fill (the print check judges both in greyscale)
GREY_SHARED = {"fig3": {("v", "filled"): ["bl1_g1", "bl2"]}, "sf_e11_inst": {("v", "filled"): ["bl1_g1", "bl2"]},
               "sf_e5": {("<", "filled"): ["sublet_ms4", "bl3"]}}
# the legacy entries as they stay (M2): label and (color, marker, fill)
LEGACY = {"sublet": ("Sublet", ("#0072B2", "o", "filled")),
          "sublet_siloed": ("Sublet, siloed", ("#0072B2", "o", "open")),
          "bl5": ("RetroRenting-style", ("#56B4E9", "s", "open")),
          "bl1_guard": ("Greedy + guard", ("#E69F00", "^", "filled")),
          "a7_guard": ("PD heuristic + guard", ("#009E73", "D", "filled"))}
FIG3_PAIRS = (("bl5_lag", "bl5_g1"), ("a7", "a7_g1"), ("bl1", "bl1_g1"))


def _moved(name: str) -> tuple[str, ...]:
    """M4's rule on a frozen set: the frozen sublet becomes its figure's configuration key, the other legacy keys their
    configuration keys, and the siloed form leaves the set."""
    cfg = "bl5_g1" if name in ALG1_DEFAULTS else "sublet_ms4"
    a7 = A7_GUARD["alg1" if name in ALG1_DEFAULTS else "ms4"]
    out = []
    for k in FROZEN[name]:
        k = cfg if k == "sublet" else a7 if k == "a7_guard" else MOVE.get(k, k)
        if k is not None:
            out.append(k)
    return tuple(out)


def _grey_twice(keys) -> dict:
    mf: dict = {}
    for k in keys:
        p = st.POLICIES[k]
        if p.marker is not None:
            mf.setdefault((p.marker, p.fill), []).append(k)
    return {m: ks for m, ks in mf.items() if len(ks) > 1}


# ---------------------------------------------------------------- M3: a7_g1
def test_c46_a7_g1_as_built():
    """a7_g1 with its label, A7's green, a filled thin diamond, the solid line, group guarded, family a7 and the note of
    tag A7G; right after a7_guard; MS6_KEYS; its triple and (color, marker) pair are no other key's; legend_order lists
    it with the guarded policies; the configuration keys' labels are Table II v2's names."""
    p = st.POLICIES["a7_g1"]
    assert (p.label, p.color, p.marker, p.fill, p.linestyle, p.group, p.family, p.edgecolor) == \
        ("PD heuristic + one-way guard", "#009E73", "d", "filled", "-", "guarded", "a7", None)
    assert (p.linewidth, p.markersize, p.zorder) == (st.LINE_PT, st.MARKER_PT, st.Z_DATA)
    assert p.note.startswith("MS6 C46") and "PS-G" in p.note and "defaults" in p.note
    assert p.color == st.POLICIES["a7"].color and p.family == st.POLICIES["a7"].family
    # C46 (review of the gate): a7_ms4 follows it in MS6_KEYS and in the registry order
    assert st.MS6_KEYS == ("a7_g1", "a7_ms4") and not set(st.MS6_KEYS) & (set(st.MS5B_KEYS) | set(st.LEGACY_KEYS))
    order = list(st.POLICIES)
    assert order[order.index("a7_guard") + 1] == "a7_g1" and order[order.index("a7_g1") + 1] == "a7_ms4"
    assert order[order.index("a7_ms4") + 1] == "bl1_guard"
    others = [q for q in st.POLICIES.values() if q.key != "a7_g1"]
    assert p.triple not in {q.triple for q in others}
    assert (p.color.upper(), p.marker) not in {(q.color.upper(), q.marker) for q in others}
    assert p.triple != st.POLICIES["a7_guard"].triple and p.label != st.POLICIES["a7_guard"].label
    assert st.legend_order(["a7", "bl2", "a7_g1", "a6"]) == ["a7_g1", "a7", "a6", "bl2"]
    table2 = TABLE2_V2.read_text(encoding="utf-8")
    for k in ("a7_g1", "bl5_g1", "bl1_g1"):
        assert st.POLICIES[k].label in table2, k


def test_c46_a7_ms4_as_built():
    """C46 (review of the gate; M3, M4): a7_ms4 is the guard around A7 at MS4's allowance, E7's and S1's tag A7G: A7's
    green and family, group guarded, a filled X, the solid line, its label a7_g1's with sublet_ms4's allowance suffix,
    its note naming the tag and the allowance; its triple and (color, marker) pair are no other key's, and its (marker,
    fill) no other key's of the sets that draw it (sf_e7_mix, sf_e7_mu); it never shares a figure with a7_g1 or
    a7_guard."""
    p, g1, ms4 = st.POLICIES["a7_ms4"], st.POLICIES["a7_g1"], st.POLICIES["sublet_ms4"]
    assert (p.color, p.marker, p.fill, p.linestyle, p.group, p.family, p.edgecolor) == \
        ("#009E73", "X", "filled", "-", "guarded", "a7", None)
    assert (p.linewidth, p.markersize, p.zorder) == (st.LINE_PT, st.MARKER_PT, st.Z_DATA)
    suffix = ms4.label[len(st.POLICIES["bl5_g1"].label):]
    assert suffix == r" ($B_0=10\%$ of the all-fallback bill)" and p.label == g1.label + suffix             # C59
    assert p.note.startswith("MS6 C46") and "A7G" in p.note and "0.1 BL0a" in p.note
    others = [q for q in st.POLICIES.values() if q.key != "a7_ms4"]
    assert p.triple not in {q.triple for q in others}
    assert (p.color.upper(), p.marker) not in {(q.color.upper(), q.marker) for q in others}
    sets = st.figure_sets()
    assert {n for n, ks in sets.items() if "a7_ms4" in ks} == {"sf_e7_mix", "sf_e7_mu"}
    for n in ("sf_e7_mix", "sf_e7_mu"):
        assert [k for k in sets[n] if (st.POLICIES[k].marker, st.POLICIES[k].fill) == ("X", "filled")] == ["a7_ms4"]
    assert not any({"a7_g1", "a7_ms4"} <= set(ks) or {"a7_ms4", "a7_guard"} <= set(ks) for ks in sets.values())


# ---------------------------------------------------------------- M2, M4: the moved sets
def test_c46_moved_sets():
    """Each of the fourteen figures draws its frozen set under M4's rule; Algorithm 1's defaults draw bl5_g1 and never
    sublet_ms4, MS4's allowance the reverse; every set lies within the registry with unique keys and labels and passes
    check_policies; only GREY_SHARED's (marker, fill) pairs occur twice; the frozen fig1 and fig4 keep their sets and
    the legacy entries their labels and triples."""
    sets = st.figure_sets()
    assert set(FROZEN) == set(ALG1_DEFAULTS) | set(MS4_ALLOWANCE) and not set(ALG1_DEFAULTS) & set(MS4_ALLOWANCE)
    for name in FROZEN:
        keys = sets[name]
        assert keys == _moved(name), name
        assert len(set(keys)) == len(keys) and set(keys) <= set(st.POLICIES), name
        st.check_policies(keys)
        labels = [st.POLICIES[k].label for k in keys]
        assert len(set(labels)) == len(labels), name
        assert not set(keys) & set(st.LEGACY_KEYS), name
        cfg, other = ("bl5_g1", "sublet_ms4") if name in ALG1_DEFAULTS else ("sublet_ms4", "bl5_g1")
        assert cfg in keys and other not in keys, name
        assert ("a7_ms4" if name in ALG1_DEFAULTS else "a7_g1") not in keys, name       # C46: the allowance's key
        assert _grey_twice(keys) == GREY_SHARED.get(name, {}), name
    assert st.SUPP_POLICIES["sf_e11_inst"] == st.FIGURE_POLICIES["fig3"]
    assert st.FIGURE_POLICIES["fig1"] == ("sublet",)
    assert st.FIGURE_POLICIES["fig4"] == ("sublet", "sublet_siloed", "a7_guard", "a7", "a6", "a6_siloed", "bl5", "bl1",
                                          "bl2", "bl4", "bl0a", "bl0b", "opt")
    for k, (label, triple) in LEGACY.items():
        assert (st.POLICIES[k].label, st.POLICIES[k].triple) == (label, triple), k
    # a siloed run is the same key in the sharing line style (as sf_e3_v2 draws it)
    kw = st.policy_kwargs("sublet_ms4", env=("sharing", "siloed"))
    assert kw["linestyle"] == "--" and kw["label"] == st.POLICIES["sublet_ms4"].label
    for name, keys in sets.items():
        st.check_policies(keys)


# ---------------------------------------------------------------- check_legacy
def test_c46_legacy_keys_only_in_the_frozen_figures():
    """check_legacy() holds; no figure outside LEGACY_PENDING draws a legacy key; LEGACY_PENDING is fig1 and fig4, each
    registered with its W8 or W6 note; a7_guard is a legacy key and never shares a figure with a7_g1; a figure that
    draws an MS6 key with a legacy key fails, naming both."""
    st.check_legacy()
    sets = st.figure_sets()
    assert set(st.LEGACY_PENDING) == {"fig1", "fig4"}
    assert "W8" in st.LEGACY_PENDING["fig1"] and "fig1v2" in st.LEGACY_PENDING["fig1"]
    assert "W6" in st.LEGACY_PENDING["fig4"]
    assert all(st.FIGURES[n].main for n in st.LEGACY_PENDING)
    for name, keys in sets.items():
        if name not in st.LEGACY_PENDING:
            assert not set(keys) & set(st.LEGACY_KEYS), name
    assert "a7_guard" in st.LEGACY_KEYS
    assert not any({"a7_g1", "a7_guard"} <= set(keys) or {"a7_ms4", "a7_guard"} <= set(keys) for keys in sets.values())
    assert {n for n, ks in sets.items() if "a7_guard" in ks} == {"fig4"}
    with pytest.raises(st.StyleError, match=r"fig_x draws the MS6 keys \['a7_g1'\] with the legacy keys "
                                            r"\['a7_guard'\]"):
        st.check_legacy({"fig_x": ("a7_g1", "a7_guard", "a7")}, {"fig_x": "pending"})
    with pytest.raises(st.StyleError, match=r"sf_z draws the legacy keys \['a7_guard'\] without a LEGACY_PENDING"):
        st.check_legacy({**sets, "sf_z": ("a7_guard", "a7")})


# ---------------------------------------------------------------- M1: fig1v2
def test_c46_fig1v2_registered():
    """fig1v2 is a main-text figure at the frozen fig1's size (W1 x 2.4 in) with the set (sublet_v2,), which passes
    check_policies and check_legacy; the print sheet lists it right after fig1."""
    spec, old = st.FIGURES["fig1v2"], st.FIGURES["fig1"]
    assert (spec.name, spec.width, spec.height_in, spec.main) == ("fig1v2", "W1", 2.4, True)
    assert (spec.width, spec.height_in) == (old.width, old.height_in)
    assert st.FIGURE_POLICIES["fig1v2"] == ("sublet_v2",)
    st.check_policies(st.FIGURE_POLICIES["fig1v2"])
    st.check_legacy({"fig1v2": st.FIGURE_POLICIES["fig1v2"]}, {})
    names = print_sheet.main_figures()
    assert names.index("fig1v2") == names.index("fig1") + 1
    fig = st.new_figure("fig1v2")
    assert tuple(round(v, 6) for v in fig.get_size_inches()) == (round(st.W1, 6), 2.4)


# ---------------------------------------------------------------- M5: the paired legend
def test_c46_guard_pair_handles_entries():
    """One entry per pair in the given order, labeled with the inner policy's registry label, then GUARD_PAIR_NOTE with
    an empty handle; a pair's handle is a MarkerPair of the inner policy's open sample and the guarded key's filled
    sample, markers only by default and with the registry line if lines=True; note=False leaves the note out."""
    out = st.guard_pair_handles(FIG3_PAIRS)
    # C46 (review of the gate): "paired, filled", since unpaired entries with filled markers share Fig. 3's legend
    assert [lab for _, lab in out] == ["RetroRenting-style, lagged", "PD heuristic", "Greedy renting",
                                       "paired, filled: + one-way guard (Algorithm 1 without projection)"]
    assert out[-1][1] == st.GUARD_PAIR_NOTE
    for (handle, label), (inner, guarded) in zip(out, FIG3_PAIRS):
        assert isinstance(handle, st.MarkerPair) and len(handle) == 2 and label == st.POLICIES[inner].label
        for sample, key in zip(handle, (inner, guarded)):
            p = st.POLICIES[key]
            assert isinstance(sample, Line2D)
            assert (sample.get_marker(), sample.get_color(), sample.get_markeredgecolor()) == (p.marker, p.color,
                                                                                             p.color)
            assert sample.get_markerfacecolor() == ("white" if key == inner else p.color)
            assert sample.get_linestyle() == "None" and sample.get_markersize() == p.markersize
    blank = out[-1][0]
    assert isinstance(blank, Line2D) and blank.get_marker() == "None" and blank.get_linestyle() == "None"
    with_lines = st.guard_pair_handles(FIG3_PAIRS[:1], lines=True, note=False)
    assert len(with_lines) == 1 and [s.get_linestyle() for s in with_lines[0][0]] == ["-", "-"]


@pytest.mark.parametrize("pairs, match", [
    ([("bl5_g1", "bl5_lag")], "bl5_g1 is not an inner policy"),
    ([("a6", "a7_g1")], "not an inner policy with an open marker"),
    ([("bl5_lag", "bl5")], "bl5 is not a guarded policy"),
    ([("bl5_lag", "bl1_g1")], "bl5_lag and bl1_g1 are not one family in one color"),
    ([("a7", "a7_g1"), ("a7", "bl1_g1")], "a7 is in two pairs"),
    ([("a7", "no_such_key")], "unknown policy key"),
    ([("a7",)], "is not an \\(inner, guarded\\) pair"),
    ([], "at least one"),
])
def test_c46_guard_pair_handles_rejects(pairs, match):
    with pytest.raises(st.StyleError, match=match):
        st.guard_pair_handles(pairs)


def _sample_centers(leg, fig) -> dict:
    """{(marker, face color): (x, y) of the marker in display units} of the legend's drawn samples (HandlerLine2D
    draws one marker at the middle of a 3-point line)."""
    fig.canvas.draw()
    out = {}
    for ln in leg.findobj(Line2D):
        xy = ln.get_xydata()
        if ln.get_marker() not in (None, "None", "none", "") and len(xy):
            key = (ln.get_marker(), mcolors.to_hex(ln.get_markerfacecolor()))
            assert key not in out, key
            out[key] = tuple(ln.get_transform().transform(xy[len(xy) // 2]))
    return out


def _center(pos: dict, key: str) -> tuple:
    p = st.POLICIES[key]
    return pos[(p.marker, mcolors.to_hex("white" if p.fill == "open" else p.color))]


def test_c46_guard_pairs_drawn_side_by_side(tmp_path):
    """legend_row draws Fig. 3's three pairs, the unpaired Two-timescale PD and per-borrower ski rental and the note in
    two rows over Fig. 3's panels: each pair's handler is HandlerTuple with ndivide None, its two samples on one
    baseline with the inner policy's left of the guarded key's; the labels are those of the entries; the figure passes
    finalize() (C62's text sizes, nothing outside the page, no overlap). corner_legend does the same and keeps a
    handler_map it is given."""
    extra = st.guard_pair_handles(FIG3_PAIRS, note=False) + st.policy_handles(["a6", "bl2"]) + \
        st.guard_pair_handles(FIG3_PAIRS[:1])[-1:]
    fig = st.new_figure("fig3")
    axes = st.panel_row(fig, (1, 1, 1), legend=2)
    for ax in axes:
        ax.plot([0, 1], [0, 1], color="#000000")
        ax.set_xlabel("Trace cost")
        ax.set_ylabel("Worst case")
    st.panel_letters(axes)
    leg = st.legend_row(fig, [], extra=extra, rows=2)
    assert [t.get_text() for t in leg.get_texts()] == [lab for _, lab in extra]
    hmap = leg.get_legend_handler_map()
    for handle, _ in extra[:3]:
        h = leg.get_legend_handler(hmap, handle)
        assert isinstance(h, HandlerTuple) and h._ndivide is None
    pos = _sample_centers(leg, fig)
    assert len(pos) == 2 * len(FIG3_PAIRS) + 2                      # the pairs' six samples, Two-timescale PD, BL2
    for inner, guarded in FIG3_PAIRS:
        a, b = _center(pos, inner), _center(pos, guarded)
        assert a[0] < b[0] - 2.0 and abs(a[1] - b[1]) < 0.5, (inner, guarded)
    rep = st.save(fig, "fig3", {"pairs": [list(p) for p in FIG3_PAIRS]}, pdf_dir=tmp_path, out_dir=tmp_path)
    assert rep["text_pt"] == [st.TICK_PT, st.LABEL_PT]
    assert rep["outside_page"] == [] and (tmp_path / "fig3.pdf").is_file()
    # a corner legend in a single-column panel, with a handler_map of the caller's kept beside the pairs'
    fig = st.new_figure("fig6")
    (ax,) = st.panel_row(fig, (1,))

    class Custom:
        pass
    pairs = st.guard_pair_handles(FIG3_PAIRS[1:2])
    leg = st.corner_legend(ax, ["a6"], extra=pairs, loc="upper left", handler_map={Custom: HandlerTuple()})
    hmap = leg.get_legend_handler_map()
    assert Custom in hmap and leg.get_legend_handler(hmap, pairs[0][0]) is st.PAIR_HANDLER_MAP[st.MarkerPair]
    assert [t.get_text() for t in leg.get_texts()] == ["Two-timescale PD", "PD heuristic", st.GUARD_PAIR_NOTE]
    pos = _sample_centers(leg, fig)
    a, b = _center(pos, "a7"), _center(pos, "a7_g1")
    assert a[0] < b[0] - 2.0 and abs(a[1] - b[1]) < 0.5
