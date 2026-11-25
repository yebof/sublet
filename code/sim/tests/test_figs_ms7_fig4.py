"""Tests of Fig. 3 v3, figs/fig4_v3.py (figure name fig4v3; the paper's Fig. 3 after cut K1), its registration in
figs/style.py and its rebuild entry in figs/rebuild.py (design/ms7/w_spec.md §2.8 and §4, unit W-G2; change C58).

Quick. The inputs are the input tree tests/fixtures_figs_ms7/inputs/ (reduced-mode outputs of the MS7 drivers and their
registered analyses, and copies of the MS5b fixture tree: one development week of two hours; README there) and the
fixture extract tests/fixtures_figs_ms7/fig4v3.json (what the script writes on that tree;
tests/fixtures_figs_ms7/refresh_extracts.py); every file is written under pytest's tmp_path. The oracles recompute the
plotted numbers from the input files independently of the script.

- C58 registration: fig4v3 at fig4v2's size (W2 x 2.4 in, main text) with its set; the new keys a9p and mpc appended
  to the registry (C58, unit W-G4: then the MS7 supplementary keys); check_policies and check_legacy; no two drawn markers of the set share a (marker, fill), and (b)'s margin
  markers take none of theirs; the print sheet orders fig4v3 after fig4v2.
- --from-extract on the fixture extract saves at the registered size with finalize() passing, writes the extract it
  read, and a second redraw gives the same PDF bytes.
- build() on the input tree gives the fixture extract's data, records only result files as sources, reads no
  unversioned run file.
- Value oracles: (a) is fig4v2.json's (a) without its bootstrap interval, each bar's whisker the range of main's
  per-week r0 (min, max, n; C10) and the caption saying so; (b)'s four margins from
  analysis.json, main's W0 and the e7c analysis; (c)'s medians from main/summary.json and the e7r analysis; the names of
  (c) are the registry labels without the prefix.
- C19: (a)'s components drawn in fills distinct in greyscale (each pair apart in lightness or texture), its key in the
  same fills; each panel its own key, no shared legend row: (b)'s two keys each above its sub-panel (nearer to it than
  to the other) and (c)'s above (c), each clear of every axes and within its panel's slot, the first rows level with
  the panel letters; the figure at its registered height. In the PDF as printed (rendered with PyMuPDF, independent of
  the script's measurements; review of W-G2): each key's ink ends KEY_AXES_GAP_PT above the axes it keys, and (b)'s
  lower key's ink lies at least twice as far from the upper sub-panel's ink as from its own sub-panel. (b)'s markers
  stay MARKER_CLEAR_PT inside their sub-panel's frame (review of W-G2: the top marker of the W0 sub-panel was
  clipped); a hatched segment narrower than HAIRLINE_PT is named in the caption draft with its largest value.
- C62 (2026-11-24): every key one row (its entries on one baseline); Sublet's name beside its point in (c), in
  its label color, nearer to Sublet's point than to any other point of (c), and named in the caption draft;
  the names of one shared name each on lines of their own; (c)'s arrows under its markers; the texts at TICK_PT or
  LABEL_PT (finalize: [7, 7.970] pt). After the review of C62's first render, in the PDF as printed (PyMuPDF's glyph
  origins): each key's labels, (b)'s two y labels and BL0b's ratio with its name on one baseline, (a)'s names and the
  components' names on the rows' pitch (all within BASELINE_TOL_PT); in (c) one marker for a shared name, a small copy
  of the base's marker at each transplant's point, the arrows in a tint of the base's color under the markers; in (a)
  a minor tick under each grid line without a major one and BL0b's off-scale bar with its break; at real scale (c)'s
  names and letter at least NAME_LEFT_GAP_PT right of (b)'s axes.
- The checks: a stale fig4v2.json, another week list in the e7c or e7r analysis, and a missing input (exit 2, the file
  named); reduced input is never written into paper/figures/.
- At real scale (the versioned confirmation files of this repository with stand-in e7c and e7r analyses written to
  tmp_path; the stand-ins' numbers exist only in the test) the figure saves with finalize() passing, (b)'s markers
  overlap by at most MAX_MARKER_OVERLAP, every flagged week is labeled once, each sub-panel of (b) shades only the
  weeks with a negative margin of its own series, (a)'s key markers sit between the names and the bars, (c)'s names
  stay in their slot and each leader ends nearest a point of its own name, and (c)'s confirmation medians are those
  of sf_e7_decomp.json, which Section VII cites (review of W-G2).
- figs/rebuild.py (C58): fig4v3 listed as a main entry after fig4v2; pending in a tree without the MS7 run outputs (not
  missing, not run, not failed), an ordinary entry once they are there.
"""
from __future__ import annotations

import json
import shutil
import statistics
from pathlib import Path

import numpy as np
import pytest

from figs import print_sheet, style
from figs import rebuild as rb
from figs.inputs import Inputs

NAME = "fig4v3"
FIX = Path(__file__).resolve().parent / "fixtures_figs_ms7"
IN_ROOT = FIX / "inputs"
OUT = IN_ROOT / "code" / "sim" / "out"
REPO = style.REPO
STALE = ("tests/fixtures_figs_ms7/fig4v3.json is stale (the script's data changed): refresh it with "
         "`python tests/fixtures_figs_ms7/refresh_extracts.py --only fig4v3` from code/sim")

pytestmark = pytest.mark.filterwarnings("ignore::figs.style.GlyphSizeWarning")


def module():
    from figs import fig4_v3
    return fig4_v3


def fixture_payload():
    return json.loads((FIX / f"{NAME}.json").read_text())


def jl(p: Path):
    return json.loads(Path(p).read_text())


@pytest.fixture
def figs_env(tmp_path, monkeypatch):
    monkeypatch.setenv("SUBLET_FIGS_IN_ROOT", str(IN_ROOT))
    monkeypatch.setenv(style.ENV_PDF_DIR, str(tmp_path / "pdf"))
    monkeypatch.setenv(style.ENV_OUT_DIR, str(tmp_path / "out"))
    return tmp_path


def copy_tree(tmp_path: Path) -> Path:
    root = tmp_path / "tree"
    shutil.copytree(IN_ROOT, root)
    return root


# ---------------------------------------------------------------------------------------------------------------
# Registration (C58)
def test_registered():
    spec = style.FIGURES[NAME]
    assert (spec.width, spec.height_in, spec.main) == ("W2", 2.4, True)
    assert style.FIGURES["fig4v2"].size_in == spec.size_in
    keys = style.FIGURE_POLICIES[NAME]
    assert tuple(module().KEYS) == keys and NAME not in style.LEGACY_PENDING
    style.check_policies(keys)
    style.check_legacy()
    assert not set(keys) & set(style.LEGACY_KEYS)
    assert style.MS7_KEYS == ("a9p", "mpc")
    # appended (the C41 anchors keep their successors); C58 (W-G4): followed by the MS7 supplementary keys, appended too
    # MS8: the MS8 supplementary keys (style.MS8_SUPP_KEYS) follow them
    n, m = len(style.MS7_SUPP_KEYS), len(style.MS8_SUPP_KEYS)
    order = tuple(style.POLICIES)[:len(style.POLICIES) - m]
    assert tuple(style.POLICIES)[len(style.POLICIES) - m:] == style.MS8_SUPP_KEYS
    assert order[len(order) - n - 2:len(order) - n] == ("a9p", "mpc")
    assert order[len(order) - n:] == style.MS7_SUPP_KEYS
    assert style.POLICIES["a9p"].label == "Protected-only renting"     # C61
    assert style.POLICIES["mpc"].label == "MPC"
    assert {k for ks in style.TABLE_POLICIES_MS7.values() for k in ks} <= set(style.POLICIES)
    main = print_sheet.main_figures()
    assert main.index(NAME) == main.index("fig4v2") + 1


def test_greyscale_markers_are_distinct():
    """No two keys whose markers the figure draws share a (marker, fill) (C41's greyscale rule), and (b)'s margin
    markers take none of them (black markers keyed in (b)'s keys)."""
    mod = module()
    drawn = [k for k in style.FIGURE_POLICIES[NAME] if k not in ("bl1n", "bl5n") and style.POLICIES[k].marker]
    pairs = [(style.POLICIES[k].marker, style.POLICIES[k].fill) for k in drawn]
    assert len(pairs) == len(set(pairs)), pairs
    margins = {(v["marker"], "open" if v["markerfacecolor"] == "white" else "filled")
               for v in mod.MARGIN_STYLES.values()}
    assert len(margins) == len(mod.MARGINS) and not margins & set(pairs)


# ---------------------------------------------------------------------------------------------------------------
# The script on the fixtures
def test_from_extract_saves_and_is_byte_stable(figs_env):
    mod = module()
    rep = mod.main(["--from-extract", str(FIX / f"{NAME}.json")])
    spec = style.figure_spec(NAME)
    assert abs(rep["width_bp"] - spec.width_in * 72) <= 0.5 and abs(rep["height_bp"] - spec.height_in * 72) <= 0.5
    assert rep["pages"] == 1 and rep["outside_page"] == []
    assert rep["text_pt"] and set(rep["text_pt"]) <= {style.TICK_PT, style.LABEL_PT}
    assert not any("dejavu" in f.lower() for f in rep["fonts"])
    assert jl(figs_env / "out" / f"{NAME}.json") == fixture_payload()
    assert_keys_ink_in_pdf(rep["pdf"], fixture_payload()["data"])
    assert_baselines_in_pdf(rep["pdf"], fixture_payload()["data"])
    first = Path(rep["pdf"]).read_bytes()
    rep2 = mod.main(["--from-extract", str(figs_env / "out" / f"{NAME}.json")])
    assert Path(rep2["pdf"]).read_bytes() == first


def test_build_on_the_input_tree_matches_the_fixture(figs_env):
    mod = module()
    inp = Inputs()
    data = json.loads(json.dumps(mod.build(inp), allow_nan=False))
    assert data == fixture_payload()["data"], STALE
    assert all(style.check_source(s) == s for s in inp.sources)
    assert not any("/runs/" in s for s in inp.sources)
    assert set(inp.sources) == set(mod.INPUTS)
    assert data["meta"]["reduced"] is True and data["meta"]["inputs_sha256"] == {
        n: __import__("hashlib").sha256((IN_ROOT / n).read_bytes()).hexdigest() for n in mod.INPUTS}
    assert mod.layout(data) == data["layout"]


def test_value_oracles():
    mod = module()
    d = fixture_payload()["data"]
    main = jl(OUT / "sublet_v2" / "main" / "summary.json")
    ana = jl(OUT / "sublet_v2" / "analysis.json")
    e7c = jl(OUT / "e7c" / "analysis.json")
    e7r = jl(OUT / "e7r" / "analysis.json")
    v2 = jl(OUT / "figs" / "fig4v2.json")["data"]
    weeks = sorted(main["table"]["Sublet"]["L-tr"], key=int)
    # (a): fig4v2's (a) with its source recorded, each bar's whisker the range of main's per-week r0 (C10), not fig4v2's
    # week-bootstrap interval
    a = {k: v for k, v in d["a"].items() if k not in ("source", "whiskers")}
    want = json.loads(json.dumps(v2["a"]))
    for key in mod.BARS:
        r0 = [main["table"][mod.v2.TAGS[key]]["L-tr"][w]["0"] for w in weeks]
        assert a[key].pop("range") == {"min": min(r0), "max": max(r0), "n": len(weeks)}, key
        assert "ci_lo" not in a[key] and "ci_hi" not in a[key]
        want[key].pop("ci_lo")
        want[key].pop("ci_hi")
    assert a == want and d["a"]["source"]["extract"] == mod.FIG4V2 and "range over the weeks" in d["a"]["whiskers"]
    # (b)
    W0 = main["W0"]["0"]
    h1_set = ana["H2"]["set"]
    for i, w in enumerate(weeks):
        assert d["b"]["trace"][i] == ana["H1"]["margins"][w]["delta"]
        assert d["b"]["trace_lag"][i] == e7c["margins"]["h1"]["r0"]["weeks"][w]["delta"]
        best = min(W0[t][w] for t in h1_set)
        assert abs(d["b"]["w0_set"][i] - (best - W0["Sublet"][w])) <= 1e-12
        assert abs(d["b"]["w0_tau60"][i] - (W0["BL5-tau60"][w] - W0["Sublet"][w])) <= 1e-12
    assert d["b"]["subpanels"] == [["cost", ["trace", "trace_lag"]], ["w0", ["w0_set", "w0_tau60"]]]
    assert d["b"]["dodge_weeks"] == {"trace": -mod.B_DODGE, "trace_lag": mod.B_DODGE, "w0_set": -mod.B_DODGE,
                                     "w0_tau60": mod.B_DODGE}
    neg = {n["week"] for n in d["b"]["negative"]}
    assert neg == {w for i, w in enumerate(weeks) if any((d["b"][k][i] or 0) < 0 for k in mod.MARGINS)}
    # (c)
    for key, tag in mod.C_MAIN.items():
        r0 = [main["table"][tag]["L-tr"][w]["0"] for w in weeks]
        w0 = [W0[tag][w] for w in weeks]
        assert d["c"][key]["r0"]["median"] == statistics.median(r0) and d["c"][key]["W0"]["median"] == \
            statistics.median(w0), key
    pw = e7r["tags"]["A9-P"]["per_week"]
    assert d["c"]["a9p"]["r0"]["median"] == statistics.median(pw[w]["r0_tr"] for w in weeks)
    assert d["c"]["a9p"]["W0"]["median"] == statistics.median(pw[w]["W0"] for w in weeks)
    prefix = style.POLICIES["a9"].label + ", "
    for k in mod.NAMED:
        lab = style.POLICIES[k].label
        assert d["c"]["names"][k] == (lab[len(prefix):] if lab.startswith(prefix) else lab)
        assert " ".join(d["layout"]["c_name_lines"][k]).replace("- ", "-") == d["c"]["names"][k].replace("- ", "-")
    cap = d["labels"]["caption"]
    assert "H2b" not in cap and "BL" not in cap and "A9" not in cap and d["labels"]["caption_lines_est"] <= 5
    n = len(weeks)
    assert f"whiskers: range over the {n} week{'s' if n != 1 else ''}" in cap and "bootstrap" not in cap
    assert_hairline_caption(d)


def test_drawn_keys_legend_and_names():
    mod = module()
    d = fixture_payload()["data"]
    fig = mod.draw(d)
    keys = {getattr(a, "_sublet_policy") for ax in fig.axes for a in ax.get_children() if hasattr(a, "_sublet_policy")}
    keys |= {k for ax in fig.axes for a in ax.get_children() for k in getattr(a, "_sublet_policies", ())}
    assert keys == set(style.FIGURE_POLICIES[NAME]), keys
    pan = fig._sublet_panels
    ax_a, ax_c = pan["a"], pan["c"]
    assert [t.get_text() for t in ax_a.get_yticklabels()] == \
        [style.POLICIES[k].label for k in mod.BARS] + [style.POLICIES["bl0b"].label]
    # C19: no shared legend row; a key per sub-panel of (b) and one for (c), each with its own entries
    keys = {getattr(leg, "_sublet_role", ""): leg for leg in fig.legends}
    assert sorted(keys) == ["key:c", "key:cost", "key:w0"] and len(fig.legends) == 3
    for name, ks in mod.B_SUBPANELS:
        assert [t.get_text() for t in keys[f"key:{name}"].get_texts()] == [mod.MARGIN_LABELS[k] for k in ks]
    assert [t.get_text().replace("\n", " ") for t in keys["key:c"].get_texts()] == [style.POLICIES["a9p"].label]
    assert_keys_sit_with_their_panels(fig, d)
    assert_markers_inside(fig)
    assert_fills(fig, d)
    names = [t for t in ax_c.texts if getattr(t, "_sublet_role", "") == "direct_label"]
    flat = [k for t in names for k in t._sublet_policies]
    assert sorted(flat) == sorted(mod.NAMED) and len(flat) == len(set(flat))
    for t in names:                       # one name per group of coinciding points (review of W-G2), else the layout's
        if len(t._sublet_policies) == 1:
            assert t.get_text() == "\n".join(d["layout"]["c_name_lines"][t._sublet_policy])
        else:
            assert t.get_text().replace("\n", " ").replace("- ", "-") == \
                mod.NAME_JOIN.join(d["c"]["names"][k] for k in t._sublet_policies).replace("- ", "-")
    assert_leaders_reach_their_points(fig)
    assert_a_keys_between_names_and_bars(fig, d)
    assert_c62_keys_and_sublet_name(fig, d)
    assert_c62_review_a(fig, d)
    assert ax_c.yaxis.get_label_position() == "right"


def _marker_centers(ax) -> dict:
    """{policy key: display (x, y)} of the markers drawn in (c) (one point each)."""
    out = {}
    for ln in ax.get_lines():
        k = getattr(ln, "_sublet_policy", None)
        if k is not None and ln.get_marker() not in (None, "None", "", " ") and len(ln.get_xydata()) == 1:
            out[k] = ln.get_transform().transform(ln.get_xydata())[0]
    return out


def assert_leaders_reach_their_points(fig):
    """Each of (c)'s leaders ends nearer to a point of its own name than to any other point of (c) (review of W-G2:
    a leader that reached past another policy's marker read as naming it)."""
    ax_c = fig._sublet_panels["c"]
    pts = _marker_centers(ax_c)
    names = [t for t in ax_c.texts if getattr(t, "_sublet_role", "") == "direct_label"]
    leaders = [ln for ln in ax_c.get_lines() if getattr(ln, "_sublet_role", "") == "leader"]
    assert len(names) == len(leaders)
    for t, ln in zip(names, leaders):
        end = ln.get_transform().transform(ln.get_xydata())[-1]
        near = min(pts, key=lambda k: float(np.hypot(*(pts[k] - end))))
        assert near in t._sublet_policies, (t.get_text(), near)


def assert_c62_keys_and_sublet_name(fig, d):
    """C62: each key one row (its labels left to right in its entries' order, on one baseline as printed:
    assert_baselines_in_pdf); Sublet's name beside
    its marker in (c) (one point label, the registry label in Sublet's label color, its box within SUBLET_DX_MAX_PT of
    the place next to the marker, its edge facing the marker at least SUBLET_OWN_PT nearer to Sublet's point than to
    any other point or arrow head of (c), or, where no place beside it is free, a leader pointing at it; and the
    caption draft naming Sublet in (c)); each name of a shared name on lines of its own; (c)'s
    arrows under its markers."""
    from matplotlib.colors import to_hex
    mod = module()
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    for leg in fig.legends:                # one row: the boxes overlap across, left to right
        boxes = [t.get_window_extent(r) for t in leg.get_texts()]
        assert max(b.y0 for b in boxes) < min(b.y1 for b in boxes), leg._sublet_role
        assert [b.x0 for b in boxes] == sorted(b.x0 for b in boxes), leg._sublet_role
    ax_c = fig._sublet_panels["c"]
    pts = _marker_centers(ax_c)
    (lab,) = [t for t in ax_c.texts if getattr(t, "_sublet_role", "") == "point_label"]
    assert lab.get_text() == style.POLICIES["sublet_v2"].label and lab._sublet_policy == "sublet_v2"
    assert to_hex(lab.get_color()) == to_hex(style.policy("sublet_v2").label_color)
    bb = lab.get_window_extent(r)

    def box_dist(p):                       # display units: from the label's box to a point
        return float(np.hypot(max(bb.x0 - p[0], 0.0, p[0] - bb.x1), max(bb.y0 - p[1], 0.0, p[1] - bb.y1)))
    heads = [ax_c.transData.transform((d["c"][t]["r0"]["median"], d["c"][t]["W0"]["median"])) for _, t in mod.ARROWS]
    own = box_dist(pts["sublet_v2"])
    if lab._sublet_side == "leader":       # no place beside the point (the fixture, where CoCaR-style's marker touches
        # Sublet's): a leader from the name's box points at Sublet's center and ends LEADER_END_PT off its marker
        a0, a1 = lab._sublet_leader.get_transform().transform(lab._sublet_leader.get_xydata())
        u, q = a1 - a0, pts["sublet_v2"] - a0
        pt = fig.dpi / 72.0
        assert abs(u[0] * q[1] - u[1] * q[0]) / np.hypot(*u) <= 0.5 * pt and float(np.dot(u, q)) > 0
        assert abs(np.hypot(*(pts["sublet_v2"] - a1)) - (mod._marker_radius_pt("sublet_v2") + mod.LEADER_END_PT) * pt) \
            <= 0.5 * pt
        assert box_dist(a0) <= 0.5 * pt                     # it starts on the name's box
    else:                                  # beside it, at most SUBLET_DX_MAX_PT off the marker's edge, the box's edge
        # facing it SUBLET_OWN_PT nearer to it than to any other point or arrow head
        ref = mod.side_anchor(lab._sublet_side, bb.x0, bb.y0, bb.width, bb.height)
        near = [float(np.hypot(*(q - ref))) for k, q in pts.items() if k != "sublet_v2"] + \
            [float(np.hypot(*(q - ref))) for q in heads]
        assert float(np.hypot(*(pts["sublet_v2"] - ref))) + mod.SUBLET_OWN_PT * fig.dpi / 72.0 <= min(near) + 1e-6
        assert own <= (mod._marker_radius_pt("sublet_v2") + mod.SUBLET_GAP_PT + mod.SUBLET_DX_MAX_PT + 0.5) * \
            fig.dpi / 72.0
    assert "named in blue: Sublet," in d["labels"]["caption"]
    for t in ax_c.texts:
        if getattr(t, "_sublet_role", "") == "direct_label" and len(t._sublet_policies) > 1:
            lines = t.get_text().split("\n")
            names = [d["c"]["names"][k] for k in t._sublet_policies]
            # the lines split into consecutive runs, one per name (each name's lines joined give the name)
            i = 0
            for j, n in enumerate(names):
                want = n + (mod.NAME_JOIN.rstrip() if j < len(names) - 1 else "")
                run = []
                while i < len(lines) and " ".join(run).replace("- ", "-") != want.replace("- ", "-"):
                    run.append(lines[i])
                    i += 1
                assert " ".join(run).replace("- ", "-") == want.replace("- ", "-"), (lines, names)
            assert i == len(lines)
    z_marks = min(ln.get_zorder() for ln in ax_c.get_lines() if getattr(ln, "_sublet_policy", None) in pts)
    arrows = [t for t in ax_c.texts if getattr(t, "_sublet_role", "") == "transplant_arrow"]
    assert len(arrows) == len(mod.ARROWS) and all(a.get_zorder() < z_marks for a in arrows)
    assert_c62_review_c(fig, d)


def assert_c62_review_c(fig, d):
    """C62 review, (c): a shared name has one marker, the first's, which carries every key of the name, and no other
    marker of its keys is drawn; each transplant's point has a small copy of its base's marker (marker, fill and color
    of the registry, GHOST_PT < the base's size) and the arrow from the base ends at it, the arrow (shaft and head) in a
    tint of the base's color lighter than the base's label color, under every marker."""
    from matplotlib.colors import to_rgb
    mod = module()
    ax_c = fig._sublet_panels["c"]
    names = [t for t in ax_c.texts if getattr(t, "_sublet_role", "") == "direct_label"]
    markers = [ln for ln in ax_c.get_lines() if getattr(ln, "_sublet_policy", None) in mod.C_ORDER]
    drawn = [ln._sublet_policy for ln in markers]
    assert len(drawn) == len(set(drawn))
    for t in names:
        g = t._sublet_policies
        assert g[0] in drawn and not set(g[1:]) & set(drawn), (g, drawn)
        if len(g) > 1:
            (ln,) = [m for m in markers if m._sublet_policy == g[0]]
            assert ln._sublet_policies == list(g) and ln.get_marker() == style.POLICIES[g[0]].marker
    assert set(drawn) == set(mod.C_ORDER) - {k for t in names for k in t._sublet_policies[1:]}
    ends = {ln._sublet_policy: ln for ln in ax_c.get_lines() if getattr(ln, "_sublet_role", "") == "transplant_end"}
    arrows = {a._sublet_policy: a for a in ax_c.texts if getattr(a, "_sublet_role", "") == "transplant_arrow"}
    z_marks = min(ln.get_zorder() for ln in markers + list(ends.values()))
    for base, head in mod.ARROWS:
        e, p = ends[head], style.POLICIES[base]
        assert e._sublet_base == base and e.get_marker() == p.marker and e.get_markersize() == mod.GHOST_PT < \
            p.markersize
        assert to_rgb(e.get_markeredgecolor()) == to_rgb(p.color) and \
            to_rgb(e.get_markerfacecolor()) == to_rgb("white" if p.fill == "open" else p.color)
        assert tuple(e.get_xydata()[0]) == (d["c"][head]["r0"]["median"], d["c"][head]["W0"]["median"])
        a = arrows[head]
        assert a.xy == tuple(e.get_xydata()[0]) and a.get_zorder() < z_marks
        shaft = to_rgb(a.arrow_patch.get_edgecolor())
        assert all(sv >= cv - 1e-9 for sv, cv in zip(shaft, to_rgb(p.color))) and \
            sum(shaft) > sum(to_rgb(p.label_color)), (base, shaft)
        assert a.arrow_patch.get_linewidth() == mod.ARROW_PT


def assert_c62_review_a(fig, d):
    """C62 review, (a): a minor x tick under each grid line that has no major tick; BL0b's row (where it has a ratio)
    with its off-scale bar from 0 to the spine's end, edged in BL0b's color and cut by a break mark inside it, and its
    ratio set like the names (center_baseline)."""
    from matplotlib.colors import to_rgb
    mod = module()
    ax = fig._sublet_panels["a"]
    lay = d["layout"]
    hi = float(lay["a_x_hi"])
    grid = [g for g in np.arange(mod.A_GRID_STEP, hi, mod.A_GRID_STEP) if abs(g - 1.0) > 1e-9]
    major = list(ax.xaxis.get_majorticklocs())
    assert sorted(ax.xaxis.get_minorticklocs()) == [g for g in grid if min(abs(g - t) for t in major) > 1e-9]
    assert ax.xaxis.get_minorticklocs().size
    if d["a"]["bl0b"].get("overflow_over_bl0a") is None:
        return
    row = len(d["a"]["order"])
    (bar,) = [p for p in ax.patches if getattr(p, "_sublet_role", "") == "offscale_bar"]
    assert bar._sublet_policy == "bl0b" and abs(bar.get_x()) < 1e-12 and abs(bar.get_width() - hi) < 1e-12
    assert abs(bar.get_y() + 0.5 * bar.get_height() - row) < 1e-9
    edge = [ln for ln in ax.get_lines() if getattr(ln, "_sublet_role", "") == "offscale_bar"]
    assert len(edge) == 1 and to_rgb(edge[0].get_color()) == to_rgb(style.policy("bl0b").text_color)
    brk = [ln for ln in ax.get_lines() if getattr(ln, "_sublet_role", "") == "offscale_break"]
    assert len(brk) == 2 and all(0.0 < x < hi for ln in brk for x in ln.get_xdata())
    (ratio,) = [t for t in ax.texts if t.get_text() == d["labels"]["bl0b_ratio"]]
    assert ratio.get_verticalalignment() == "center_baseline" == ax.get_yticklabels()[row].get_verticalalignment()


BASELINE_TOL_PT = 0.05


def _pdf_spans(pdf):
    """The text spans of the first page of `pdf` (PyMuPDF): (text, size, direction, origin x, origin y, x0, x1), origin
    (the first glyph's) and extent (the glyphs') in pt from the page's top left corner. Spaces are left out: PyMuPDF
    puts a space it infers between mathtext glyphs at the previous glyph's origin (after a subscript, on the
    subscript's baseline)."""
    import fitz
    out = []
    with fitz.open(pdf) as doc:
        for b in doc[0].get_text("rawdict")["blocks"]:
            for ln in b.get("lines", []):
                for sp in ln["spans"]:
                    ch = [c for c in sp["chars"] if c["c"].strip()]
                    if ch:
                        out.append(("".join(c["c"] for c in sp["chars"]), round(sp["size"], 2), tuple(ln["dir"]),
                                    ch[0]["origin"][0], ch[0]["origin"][1], ch[0]["bbox"][0], ch[-1]["bbox"][2]))
    return out


def assert_baselines_in_pdf(pdf, d):
    """C62 review, in the PDF as printed (glyph origins, independent of the script's metrics): the labels of each key
    on one baseline (a mathtext label sat 0.9 pt above its plain neighbor); (a)'s names on one pitch (two names with
    math sat 0.45 pt off it), each component's name on the baseline of the bar name in its row, BL0b's ratio on its
    name's baseline (0.7 pt above it); (b)'s two y labels on one baseline (0.75 pt apart); all within
    BASELINE_TOL_PT. First-level scripts (smaller spans) are left out."""
    lay, lab = d["layout"], d["labels"]
    H = style.figure_spec(NAME).height_in * 72.0
    spans = [s for s in _pdf_spans(pdf) if s[1] >= style.TICK_PT - 1e-6 and s[0].strip()]
    flat = [s for s in spans if s[2] == (1.0, 0.0)]
    for n, k in lay["keys"].items():
        corner = H - k["y_in"] * 72.0
        top, bottom = (corner, corner + k["h_in"] * 72.0) if k["loc"] == "upper left" else \
            (corner - k["h_in"] * 72.0, corner)
        x0, x1 = k["x_in"] * 72.0, (k["x_in"] + k["w_in"]) * 72.0
        ys = [s[4] for s in flat if x0 - 0.5 <= s[5] and s[6] <= x1 + 0.5 and top - 1.0 <= s[4] <= bottom + 1.0]
        assert len(ys) >= len(k["entries"]) and max(ys) - min(ys) <= BASELINE_TOL_PT, (n, ys)
    # (a): the names (TICK_PT) left of the bars; rows by baseline
    x_bars = lay["left_in"][0] * 72.0
    names = sorted({round(s[4], 3) for s in flat if abs(s[1] - style.TICK_PT) < 0.01 and s[6] <= x_bars - 1.0})
    rows = []
    for y in names:
        if rows and y - rows[-1][-1] < 3.0:
            rows[-1].append(y)
        else:
            rows.append([y])
    assert all(max(r) - min(r) <= BASELINE_TOL_PT for r in rows), rows
    base = [r[0] for r in rows]
    n_rows = len(d["a"]["order"]) + 1
    assert len(base) == n_rows, base
    pitch = np.diff(base)
    assert float(pitch.max() - pitch.min()) <= BASELINE_TOL_PT, pitch
    by_text = {s[0].strip(): s for s in flat}
    for comp in d["a"]["components"]["order"]:
        s = by_text[lab["components"][comp]]
        assert min(abs(s[4] - y) for y in base) <= BASELINE_TOL_PT, (comp, s[4], base)
    if d["a"]["bl0b"].get("overflow_over_bl0a") is not None:
        assert abs(by_text[lab["bl0b_ratio"]][4] - base[-1]) <= BASELINE_TOL_PT
    # (b): the y labels (rotated, LABEL_PT) left of (b)'s upper sub-panel: one baseline (origin x)
    bx = lay["b_rects_in"][0][0] * 72.0
    ylab = [s[3] for s in spans if s[2] == (0.0, -1.0) and abs(s[1] - round(style.LABEL_PT, 2)) < 0.01
            and bx - 40.0 < s[3] < bx]
    assert len(ylab) >= 2 and max(ylab) - min(ylab) <= BASELINE_TOL_PT, ylab


def assert_a_keys_between_names_and_bars(fig, d):
    """(a)'s key markers: one per bar with a median, in its row, right of its name and left of the bars' start."""
    ax_a = fig._sublet_panels["a"]
    r = fig.canvas.get_renderer()
    keys = [ln for ln in ax_a.get_lines() if getattr(ln, "_sublet_role", "") == "name_key"]
    assert [ln._sublet_policy for ln in keys] == d["layout"]["a_key"]["keys"] == \
        [k for k in d["a"]["order"] if d["a"][k].get("median") is not None]
    x_bars = ax_a.get_window_extent(r).x0
    ticks = {t.get_text(): t.get_window_extent(r) for t in ax_a.get_yticklabels()}
    for ln in keys:
        bb = ln.get_window_extent(r)
        name = ticks[style.POLICIES[ln._sublet_policy].label]
        assert name.x1 < bb.x0 and bb.x1 < x_bars, ln._sublet_policy
        row = ax_a.transData.transform((0.0, d["a"]["order"].index(ln._sublet_policy)))[1]
        assert abs(0.5 * (bb.y0 + bb.y1) - row) < 0.5 and name.y0 < row < name.y1, ln._sublet_policy


def _overlap(a, b, tol=0.0) -> bool:
    return min(a.x1, b.x1) - max(a.x0, b.x0) > tol and min(a.y1, b.y1) - max(a.y0, b.y0) > tol


def assert_keys_sit_with_their_panels(fig, d):
    """C19, on the canvas (Agg at 100 dpi, whose boxes overstate a mathtext row; the ink gaps as printed are
    assert_keys_ink_in_pdf's): each key above the axes it keys (its box's bottom within a few pt of their top, nearer to
    them than to any other axes), clear of every axes and every other key, within its panel's slot across; (b)'s upper
    key and (c)'s key start level with their panel letters (their first text rows' tops within 1 pt of the letters');
    (b)'s lower key set on its bottom, at (b)'s upper key's x; no key spans two slots."""
    mod = module()
    fig.canvas.draw()                                   # the keys' texts are placed at drawing
    r = fig.canvas.get_renderer()
    pt = fig.dpi / 72.0
    pan = fig._sublet_panels
    keys = {getattr(leg, "_sublet_role", "")[4:]: leg for leg in fig.legends}
    boxes = {n: leg.get_window_extent(r) for n, leg in keys.items()}
    axes = {"a": pan["a"], "cost": pan["b"][0], "w0": pan["b"][1], "c": pan["c"]}
    ab = {n: ax.get_window_extent(r) for n, ax in axes.items()}
    slot = {p: ax._sublet_slot_left_in * fig.dpi for p, ax in (("b", pan["b"][0]), ("c", pan["c"]))}
    W = fig.get_size_inches()[0] * fig.dpi
    for n, bb in boxes.items():
        assert not any(_overlap(bb, a, 0.5 * pt) for a in ab.values()), n
        assert not any(_overlap(bb, o, 0.5 * pt) for m, o in boxes.items() if m != n), n
        own = ab[n]
        gap = bb.y0 - own.y1                        # above its own axes, nearer to them than to any other axes
        # (b)'s upper sub-panel and (c) start at one height, below the deeper of their two keys: the shallower key
        # (since C61 (c)'s, one line) ends higher by the difference of the keys' depths
        lift = max(boxes["cost"].height, boxes["c"].height) - bb.height if n in ("cost", "c") else 0.0
        assert 0.0 <= gap <= (mod.KEY_AXES_GAP_PT + 3.0) * pt + lift, (n, gap / pt, lift / pt)
        others = [bb.y0 - a.y1 if a.y1 <= bb.y0 else a.y0 - bb.y1 for m, a in ab.items() if m != n
                  and min(bb.x1, a.x1) > max(bb.x0, a.x0)]
        assert all(o > gap for o in others if o >= 0), (n, gap / pt, [o / pt for o in others])
        lo, hi = (slot["c"], W - style.MARGIN_RIGHT * fig.dpi) if n == "c" else (slot["b"], slot["c"])
        assert lo - 0.5 * pt <= bb.x0 and bb.x1 <= hi + 0.5 * pt, n
    letters = {t.get_text(): t.get_window_extent(r) for t in fig.texts if getattr(t, "_sublet_role", "") ==
               "panel_letter"}
    assert len({round(b.y0, 3) for b in letters.values()}) == 1      # the letters on one line
    for n, letter in (("cost", "(b)"), ("c", "(c)")):
        first = keys[n].get_texts()[0].get_window_extent(r)
        assert abs(first.y1 - letters[letter].y1) <= 1.0 * pt and first.x0 > letters[letter].x1, n
    assert d["layout"]["keys"]["cost"]["x_in"] == d["layout"]["keys"]["w0"]["x_in"]
    assert [d["layout"]["keys"][n]["loc"] for n in ("cost", "w0", "c")] == ["upper left", "lower left", "upper left"]


def assert_hairline_caption(d):
    """(a): each hatched component whose widest segment is narrower than HAIRLINE_PT on the page (its width over (a)'s
    bars, which span [0, a_x_hi] over the axes less the label column) is named in the caption draft with that segment
    rounded up to 4 decimals, and no other is (review of W-G2: routing showed as a white hairline, not as its hatch)."""
    mod = module()
    lay, a, cap = d["layout"], d["a"], d["labels"]["caption"]
    bars_pt = (lay["axes_in"][0] - lay["a_column_in"]) * 72.0
    thin = []
    for comp in a["components"]["order"]:
        widest = max((a[k]["segments"].get(comp, 0.0) for k in a["order"] if a[k].get("median") is not None),
                     default=0.0)
        if mod.COMPONENT_FILLS[comp]["hatch"] and 0 < widest * bars_pt / lay["a_x_hi"] < mod.HAIRLINE_PT:
            thin.append(comp)
            bound = f"{np.ceil(widest * 1e4) / 1e4:.4f}"
            assert f"{a['components']['labels'][comp].lower()}: white hairline (at most {bound})" in cap, (comp, cap)
            assert float(bound) >= widest
    assert [t["component"] for t in lay["a_thin"]] == thin
    assert cap.count("hairline") == len(thin)


def pdf_ink_rows(pdf, x0_in: float, x1_in: float, dpi: int = 720) -> np.ndarray:
    """The pixel rows (pt from the page's top, each row's top) with ink (a pixel darker than 200 of 255) between x0_in
    and x1_in inches on the first page of `pdf`, rendered in grey by PyMuPDF."""
    import fitz
    with fitz.open(pdf) as doc:
        pix = doc[0].get_pixmap(dpi=dpi, colorspace=fitz.csGRAY, alpha=False)
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.stride)[:, :pix.width]
    a, b = int(round(x0_in * dpi)), int(round(x1_in * dpi))
    return np.where((img[:, a:b] < 200).any(axis=1))[0] * 72.0 / dpi


def assert_keys_ink_in_pdf(pdf, d):
    """Review of W-G2: the keys as the PDF prints them (rendered at 720 dpi; independent of the script's own ink
    measurements, which the layout records). Each key's ink, the rows inked across its width within its box (the
    layout's corner and PDF height; 0.5 pt below it, 1 pt above it), ends at least KEY_AXES_GAP_PT above the axes it
    keys, (b)'s lower key's and the deeper of the other two keys' that far (within 0.3 pt; (b)'s upper sub-panel and
    (c) start at one height); (b)'s lower key lies at least twice as far below the upper sub-panel's ink (its tick
    marks, the rows inked across the key's width below that sub-panel) as above its own sub-panel (as built at real
    scale: 3.0 pt below its ink and 7.9 pt above it; before, with the key placed by its box on the canvas, 7.5 pt
    below and 7.1 pt above)."""
    mod = module()
    lay = d["layout"]
    H = style.figure_spec(NAME).height_in * 72.0
    px = 72.0 / 720
    (bx, by, bw, bh), (_, ly, _, lh) = lay["b_rects_in"]
    tops = {"cost": H - (by + bh) * 72.0, "w0": H - (ly + lh) * 72.0, "c": H - sum(lay["c_rect_in"][1::2]) * 72.0}
    ink = {}
    for n, k in lay["keys"].items():
        corner = H - k["y_in"] * 72.0
        top, bottom = (corner, corner + k["h_in"] * 72.0) if k["loc"] == "upper left" else \
            (corner - k["h_in"] * 72.0, corner)
        rows = pdf_ink_rows(pdf, k["x_in"], k["x_in"] + k["w_in"])
        own = rows[(rows >= top - 1.0) & (rows <= bottom + 0.5)]
        assert own.size, n
        ink[n] = (float(own.min()), float(own.max()) + px)
        gap = tops[n] - ink[n][1]
        assert gap >= mod.KEY_AXES_GAP_PT - 0.3, (n, gap)
        if n == "w0":
            assert gap <= mod.KEY_AXES_GAP_PT + 0.3, gap
            upper = H - by * 72.0                                   # the upper sub-panel's frame bottom
            above = rows[(rows > upper - 0.5) & (rows < top - 1.0)]
            assert above.size                                       # its tick marks
            gap_above = ink[n][0] - (float(above.max()) + px)
            assert gap_above >= 2.0 * gap, (gap_above, gap)
    # (b)'s upper sub-panel and (c) start at one height, KEY_AXES_GAP_PT below the deeper of their keys' ink
    assert abs(min(tops[n] - ink[n][1] for n in ("cost", "c")) - mod.KEY_AXES_GAP_PT) <= 0.3
    return ink


def assert_markers_inside(fig):
    """(b): each margin marker's edge at least MARKER_CLEAR_PT inside its sub-panel's top and bottom (within 0.05 pt;
    review of W-G2: the W0 sub-panel's top marker sat 1.1 pt below the top, its upper half clipped)."""
    from figs import fig4_v2 as v2
    mod = module()
    r = fig.canvas.get_renderer()
    pt = fig.dpi / 72.0
    for ax in fig._sublet_panels["b"]:
        ab = ax.get_window_extent(r)
        for ln in ax.get_lines():
            role = getattr(ln, "_sublet_role", "")
            if not role.startswith("margin:"):
                continue
            assert ln.get_clip_on()
            kw = mod.margin_kwargs(role[len("margin:"):])
            outline = v2.marker_outline_pt(kw["marker"], kw["markersize"], kw["markeredgewidth"])
            half = 0.5 * float(np.ptp(outline[:, 1]))
            ys = ax.transData.transform(ln.get_xydata())[:, 1]
            assert (ab.y1 - ys.max()) / pt - half >= mod.MARKER_CLEAR_PT - 0.05, (role, (ab.y1 - ys.max()) / pt - half)
            assert (ys.min() - ab.y0) / pt - half >= mod.MARKER_CLEAR_PT - 0.05, (role, (ys.min() - ab.y0) / pt - half)


def _grey(color) -> float:
    """Relative luminance of a color (WCAG; 0 black, 1 white)."""
    from matplotlib.colors import to_rgb

    def lin(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    rr, gg, bb = (lin(c) for c in to_rgb(color))
    return 0.2126 * rr + 0.7152 * gg + 0.0722 * bb


def assert_fills(fig, d):
    """C19: each component's segments in one fill (face, hatch) of COMPONENT_FILLS, the components' fills pairwise
    distinct, neighbors along a bar apart in lightness (at least 0.15 in luminance) or in texture (another hatch, or
    none), the key patches in the same fills, the segments in the components' order along each bar."""
    from matplotlib.colors import to_hex
    mod = module()
    ax = fig._sublet_panels["a"]
    seen: dict = {}
    for role in ("segment", "key_patch"):
        fills = {}
        for p in ax.patches:
            if getattr(p, "_sublet_role", "") == role:
                f = (to_hex(p.get_facecolor()), p.get_hatch())
                fills.setdefault(p._sublet_component, set()).add(f)
        assert all(len(v) == 1 for v in fills.values()), (role, fills)
        seen[role] = {c: v.pop() for c, v in fills.items()}
    assert seen["key_patch"] == {c: (mod.COMPONENT_FILLS[c]["facecolor"].lower(), mod.COMPONENT_FILLS[c]["hatch"])
                                 for c in d["a"]["components"]["order"]}
    assert all(seen["segment"][c] == seen["key_patch"][c] for c in seen["segment"])
    comps = d["a"]["components"]["order"]
    fills = [seen["key_patch"][c] for c in comps]
    assert len(set(fills)) == len(fills)
    for (fa, ha), (fb, hb) in zip(fills, fills[1:]):
        assert ha != hb or abs(_grey(fa) - _grey(fb)) >= 0.15, (fa, ha, fb, hb)
    for row in range(len(d["a"]["order"])):                             # left to right in the components' order
        segs = sorted((p.get_x(), comps.index(p._sublet_component)) for p in ax.patches
                      if getattr(p, "_sublet_role", "") == "segment"
                      and abs(p.get_y() + 0.5 * p.get_height() - row) < 1e-9)
        assert [i for _, i in segs] == sorted(i for _, i in segs)


def assert_whiskers_are_ranges(fig, d):
    """C10: each bar's whisker runs from the least to the largest per-week r0 (the extract's range, n weeks)."""
    ax = fig._sublet_panels["a"]
    got = {}
    for c in ax.collections:
        if getattr(c, "_sublet_role", "") == "whisker":
            (seg,) = c.get_segments()
            got[c._sublet_whisker] = (float(min(seg[:, 0])), float(max(seg[:, 0])))
    want = {k: (d["a"][k]["range"]["min"], d["a"][k]["range"]["max"]) for k in d["a"]["order"]
            if d["a"][k].get("median") is not None}
    assert set(got) == set(want) and all(np.allclose(got[k], want[k], rtol=0, atol=1e-12) for k in want), (got, want)


# ---------------------------------------------------------------------------------------------------------------
# The checks
def test_missing_input_exits_2(tmp_path, monkeypatch, capsys):
    root = copy_tree(tmp_path)
    (root / "code/sim/out/e7c/analysis.json").unlink()
    monkeypatch.setenv("SUBLET_FIGS_IN_ROOT", str(root))
    monkeypatch.setenv(style.ENV_PDF_DIR, str(tmp_path / "pdf"))
    monkeypatch.setenv(style.ENV_OUT_DIR, str(tmp_path / "out"))
    with pytest.raises(SystemExit) as e:
        module().main([])
    assert e.value.code == 2 and "code/sim/out/e7c/analysis.json" in capsys.readouterr().err
    assert not (tmp_path / "pdf").exists()


def test_stale_inputs_are_refused(tmp_path, monkeypatch):
    mod = module()
    root = copy_tree(tmp_path)
    monkeypatch.setenv("SUBLET_FIGS_IN_ROOT", str(root))
    f = root / "code/sim/out/figs/fig4v2.json"
    good = f.read_text()
    p = json.loads(good)
    p["data"]["a"]["sublet_v2"]["median"] += 0.01
    f.write_text(json.dumps(p))
    with pytest.raises(style.StyleError, match="stale fig4v2.json"):
        mod.build(Inputs())
    f.write_text(good)
    for name, path in (("e7c", "code/sim/out/e7c/analysis.json"), ("e7r", "code/sim/out/e7r/analysis.json")):
        g = root / path
        old = g.read_text()
        q = json.loads(old)
        if name == "e7c":
            q["meta"]["weeks"] = ["999"]
        else:
            q["weeks"] = ["999"]
        g.write_text(json.dumps(q))
        with pytest.raises(style.StyleError, match="weeks"):
            mod.build(Inputs())
        g.write_text(old)


def test_reduced_input_is_not_written_into_paper(monkeypatch, tmp_path):
    monkeypatch.setenv("SUBLET_FIGS_IN_ROOT", str(IN_ROOT))
    monkeypatch.delenv(style.ENV_PDF_DIR, raising=False)
    monkeypatch.setenv(style.ENV_OUT_DIR, str(tmp_path / "out"))
    before = sorted(p.name for p in (REPO / "paper" / "figures").iterdir())
    with pytest.raises(SystemExit) as e:
        module().main(["--from-extract", str(FIX / f"{NAME}.json")])
    assert "reduced" in str(e.value.code)
    assert sorted(p.name for p in (REPO / "paper" / "figures").iterdir()) == before
    # nor into code/sim/out/figs/ (review of W-G2: SUBLET_FIGS_PDF_DIR alone does not suffice)
    monkeypatch.setenv(style.ENV_PDF_DIR, str(tmp_path / "pdf"))
    monkeypatch.delenv(style.ENV_OUT_DIR, raising=False)
    had = (style.DEFAULT_OUT_DIR / f"{NAME}.json").is_file()
    with pytest.raises(SystemExit) as e:
        module().main(["--from-extract", str(FIX / f"{NAME}.json")])
    assert "reduced" in str(e.value.code) and (style.DEFAULT_OUT_DIR / f"{NAME}.json").is_file() == had
    assert not (tmp_path / "pdf").exists()


# ---------------------------------------------------------------------------------------------------------------
# Real scale (stand-in run analyses in tmp_path only)
def real_scale_tree(tmp_path: Path) -> Path:
    """The repository's versioned confirmation files and Fig. 4 v2's extract, with stand-in e7c and e7r analyses on its
    16 weeks (the lagged margin a fixed shift of the revealed one with a negative week, A9-P a shift of Sublet's
    values); these numbers exist only in the test."""
    root = tmp_path / "real"
    out = root / "code" / "sim" / "out"
    for rel in ("sublet_v2/main/summary.json", "sublet_v2/analysis.json", "figs/fig4v2.json"):
        (out / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(REPO / "code" / "sim" / "out" / rel, out / rel)
    ana = jl(out / "sublet_v2/analysis.json")
    main = jl(out / "sublet_v2/main/summary.json")
    weeks = [str(w) for w in ana["H1"]["weeks"]]
    rows = {w: {"delta": ana["H1"]["margins"][w]["delta"] - 0.01 * (1 + i % 3) - (0.08 if i == 5 else 0.0),
                "best": "BL1-lag", "missing": []} for i, w in enumerate(weeks)}
    ds = [r["delta"] for r in rows.values()]
    e7c = {"meta": {"weeks": weeks}, "margins": {"h1": {"r0": {
        "weeks": rows, "set": ["BL1-lag"], "n_weeks": len(weeks), "n_wins": sum(v > 0 for v in ds), "n_ties": 0,
        "n_losses": sum(v < 0 for v in ds), "n_lost_missing": 0, "median": statistics.median(ds), "min": min(ds),
        "max": max(ds)}}}}
    T = main["table"]["Sublet"]["L-tr"]
    e7r = {"weeks": weeks, "tags": {"A9-P": {"per_week": {w: {"r0_tr": T[w]["0"] + 0.17, "W0": T[w]["0"] + 0.18}
                                                          for w in weeks}}}}
    for rel, obj in (("e7c/analysis.json", e7c), ("e7r/analysis.json", e7r)):
        (out / rel).parent.mkdir(parents=True, exist_ok=True)
        (out / rel).write_text(json.dumps(obj))
    return root


def test_real_scale_layout(tmp_path, monkeypatch):
    mod = module()
    root = real_scale_tree(tmp_path)
    monkeypatch.setenv("SUBLET_FIGS_IN_ROOT", str(root))
    monkeypatch.setenv(style.ENV_PDF_DIR, str(tmp_path / "pdf"))
    monkeypatch.setenv(style.ENV_OUT_DIR, str(tmp_path / "out"))
    rep = mod.main([])
    assert rep["outside_page"] == []
    assert rep["text_pt"] and set(rep["text_pt"]) <= {style.TICK_PT, style.LABEL_PT}
    d = jl(tmp_path / "out" / f"{NAME}.json")["data"]
    assert len(d["b"]["weeks"]) == 16 and d["b"]["negative"]
    fig = mod.draw(d)
    from figs import fig4_v2 as v2
    pan = fig._sublet_panels
    (ax_bc, ax_bw), ax_c = pan["b"], pan["c"]
    for ax in (ax_bc, ax_bw):
        worst = v2.marker_overlaps(ax)
        assert not worst or worst[0]["share"] <= mod.MAX_MARKER_OVERLAP
    labels = [t.get_text() for ax in (ax_bc, ax_bw) for t in ax.texts if getattr(t, "_sublet_role", "") ==
              "week_label"]
    flagged = {n["week"] for n in d["b"]["negative"]} | {m["week"] for m in d["b"]["missing_weeks"]}
    assert sorted(labels) == sorted(flagged)
    # each sub-panel shades the weeks with a negative margin of its own series: the stand-in's lagged loss (week 306)
    # in the cost sub-panel only, the weeks with RetroRenting, tau >= 1 h, below Sublet in W0 only (review of W-G2)
    for ax, (name, keys) in zip((ax_bc, ax_bw), d["b"]["subpanels"]):
        shades = sorted((p._sublet_week for p in ax.patches if getattr(p, "_sublet_role", "") == "shade"), key=int)
        want = sorted({d["b"]["weeks"][i] for i in range(16) for k in keys
                       if d["b"][k][i] is None or d["b"][k][i] < 0}, key=int)
        assert shades == want == d["b"]["shaded"][name], name
    assert "306" in d["b"]["shaded"]["cost"] and "306" not in d["b"]["shaded"]["w0"]
    assert d["b"]["shaded"]["w0"] == sorted((w for i, w in enumerate(d["b"]["weeks"]) if d["b"]["w0_tau60"][i] < 0),
                                            key=int)
    assert_leaders_reach_their_points(fig)
    assert_a_keys_between_names_and_bars(fig, d)
    assert_c62_keys_and_sublet_name(fig, d)
    assert_keys_sit_with_their_panels(fig, d)
    assert_keys_ink_in_pdf(rep["pdf"], d)
    assert_baselines_in_pdf(rep["pdf"], d)
    assert_c62_review_a(fig, d)
    assert_markers_inside(fig)
    assert_fills(fig, d)
    assert_whiskers_are_ranges(fig, d)                  # 16 weeks: the whiskers have length (the fixture has one week)
    assert_hairline_caption(d)
    assert [t["component"] for t in d["layout"]["a_thin"]] == ["routing"]     # about 0.7 pt on the confirmation
    main = jl(root / "code/sim/out/sublet_v2/main/summary.json")
    for key in mod.BARS:
        r0 = [main["table"][mod.v2.TAGS[key]]["L-tr"][w]["0"] for w in d["b"]["weeks"]]
        assert d["a"][key]["range"] == {"min": min(r0), "max": max(r0), "n": 16}, key
    assert "whiskers: range over the 16 weeks" in d["labels"]["caption"]
    # the legend row's height went to the panels: (a) from the bottom margin to the letters' line (less BL0a's label
    # room), (b)'s sub-panels at least 0.5 in high
    H = style.figure_spec(NAME).height_in
    assert d["layout"]["a_top_in"] >= H - style.MARGIN_TOP - 0.05
    assert all(rect[3] >= 0.5 for rect in d["layout"]["b_rects_in"])
    # (c)'s confirmation medians are those Section VII cites (sf_e7_decomp.json's week table; review of W-G2)
    rows = {r["tag"]: r for r in jl(REPO / "code/sim/out/figs/sf_e7_decomp.json")["data"]["tables"]["e7v2_weeks"]
            ["rows"]}
    for key, tag in mod.C_MAIN.items():
        assert (d["c"][key]["r0"]["median"], d["c"][key]["W0"]["median"]) == \
            (rows[tag]["r0"]["median"], rows[tag]["W0"]["median"]), key
    r = fig.canvas.get_renderer()
    slot = ax_c._sublet_slot_left_in * fig.dpi
    right_b = ax_bw.get_window_extent(r).x1
    pt = fig.dpi / 72.0
    # C62 review: (c)'s slot, its letter and its names at least NAME_LEFT_GAP_PT right of (b)'s axes (a gutter as wide
    # as the one before (b)), the widest name at the slot's start
    assert abs(slot - right_b - mod.NAME_LEFT_GAP_PT * pt) <= 0.5 * pt
    (letter,) = [t for t in fig.texts if getattr(t, "_sublet_role", "") == "panel_letter" and t.get_text() == "(c)"]
    assert abs(letter.get_window_extent(r).x0 - slot) <= 0.5 * pt
    x0s = []
    for t in ax_c.texts:
        if getattr(t, "_sublet_role", "") == "direct_label":
            bb = t.get_window_extent(r)
            x0s.append(bb.x0)
            assert bb.x0 >= right_b + (mod.NAME_LEFT_GAP_PT - 0.5) * pt and bb.x1 <= ax_c.get_window_extent(r).x0
    assert abs(min(x0s) - slot) <= 1.0 * pt


# ---------------------------------------------------------------------------------------------------------------
# The rebuild entry (C58)
@pytest.fixture
def registry_without_test_figures():
    leaked = {k: v for k, v in style.FIGURES.items() if k.startswith("test_")}
    for k in leaked:
        del style.FIGURES[k]
    yield
    style.FIGURES.update(leaked)


def test_rebuild_lists_fig4v3_and_keeps_it_pending(registry_without_test_figures, tmp_path):
    ents = rb.entries()
    by = {e.name: e for e in ents}
    names = [e.name for e in ents]
    e = by[NAME]
    assert e.kind == "main" and names.index(NAME) == names.index("fig4v2") + 1
    assert (e.script, e.module) == ("code/sim/figs/fig4_v3.py", "figs.fig4_v3")
    assert e.outputs == ("paper/figures/fig4v3.pdf", "code/sim/out/figs/fig4v3.json", "code/sim/out/figs/fig4v3.png")
    assert rb.MS7_SCRIPTS == {"fig1v3": "code/sim/figs/fig1_v3.py", "fig4v3": "code/sim/figs/fig4_v3.py"}
    assert rb.MS7_PENDING[NAME] == module().RUN_INPUTS
    # a tree without the MS7 run outputs: pending, not missing, not run, not a failure
    root, work = tmp_path / "root", tmp_path / "work"
    root.mkdir()
    work.mkdir()
    assert rb.is_pending(root, e)
    cov = rb.coverage(root, [e])
    assert cov["pending"] == [NAME] and cov["missing"] == []
    rows = rb.run_entries(rb.Run(root, work, True, None, True), ents, [e])
    assert [r["status"] for r in rows] == ["pending"] and not (work / "_time").exists()
    assert rb.totals(rows, [], {})["failed"] == [] and rb.totals(rows, [], {})["pending"] == [NAME]
    # once the run outputs are in the tree, an ordinary entry: its outputs are missing until the final render
    for rel in rb.MS7_PENDING[NAME]:
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text("{}")
    assert not rb.is_pending(root, e)
    assert rb.coverage(root, [e])["missing"] == sorted(e.outputs)
    # a rebuild run: the pending entry is neither run nor compared (no output 'not written')
    rec_root, rec_work = tmp_path / "rroot", tmp_path / "rwork"
    rec_root.mkdir()
    code, rec, _ = rb.rebuild(rec_root, rec_work, check=True, only=rf"^{NAME}$", keep=False)
    assert [s["status"] for s in rec["scripts"]] == ["pending"] and rec["outputs"] == []
    assert rec["totals"]["not_written"] == [] and rec["totals"]["pending"] == [NAME]
    assert next(x for x in rec["entries"] if x["name"] == NAME)["pending"] is True
    # an output that exists (a final render) ends the pending state, whatever the run outputs
    root2 = tmp_path / "root2"
    (root2 / "paper/figures").mkdir(parents=True)
    (root2 / "paper/figures/fig4v3.pdf").write_bytes(b"x")
    assert not rb.is_pending(root2, e)
