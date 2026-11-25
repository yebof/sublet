"""Tests of the MS5b additions C41-C44 to MS3-MS5 files (design/sublet_v2.md §11, W7, W8, W12, W13); C45, the pinned
lines of the MS3-MS5 tests that these additions change, is in those tests, each line naming C45.

- C41 (figs/style.py): the 24 MS5b registry keys as built (label, color, marker, fill, line style, group, family),
  Okabe-Ito colors or #4D4D4D, a fill of FILLS and a group of GROUPS; Sublet's emphasis on sublet_v2; labels unique
  among the MS5b keys, written with \\geq and never \\ge; no (color, marker) pair that the MS3 and MS4 tests pin, and a
  triple shared with an earlier key only where the label is that key's too; each key placed after its family's anchor,
  the earlier keys in their order; fig4v2 registered as a main-text figure (W2 x 2.4 in) with the union of W1's panels;
  SUPP_POLICIES_MS5B names the seven figures of W3 and W4 with their sizes, which tests/test_figs_style.py's ink tests
  cover; every MS5b set (and fig4v2's) lies within the registry, passes check_policies, has unique labels and no
  (marker, fill) twice, holds no legacy key, and every MS5b key is in one; RR_RENEW and MARKING fail the color rule in
  sf_fam_v2's set (so they stay in its tables); siloed runs are drawn in the sharing line style.
- C41 (W8): check_legacy() holds on the registry; LEGACY_PENDING names exactly the frozen figures that draw a legacy
  key (Figs. 1, 3, 4 and 5 and the twelve supplementary figures of W8; C47: since the MS6 gate's C46, Figs. 1 and 4
  only), each with its note; a figure that draws an MS5b key with a legacy key, one that draws a legacy key without an
  entry, and an entry for a figure that draws none fail.
- C42 (figs/rebuild.py): the main-text scripts in (N, file name) order whatever the file system's order; the MS5b
  figures listed from MS5B_SCRIPTS while their scripts are missing, in place, and such an entry not run without its
  extract; Table III v2 listed by its file names, and a script under its name with another NAME a list error; the
  float heights keyed 'plain', 'ms4' and 'ms5b'; each hand-set float checked against its own heights record (the v2
  floats against floats_heights_ms5b.json).
- C43 (paper/layout_check/pageplan/floats_heights.py): BUDGETS_MS5B by its rule from the versioned measured heights;
  --ms4 and --ms5b exclude each other; with --ms5b on copies of the frozen floats under the v2 names the measured
  heights equal the frozen records' (skipped without pdflatex).
- C44 (figs/print_sheet.py): main_figures() puts fig4v2 right after fig4 and keeps fig1-fig7 in order.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from fixtures import SIM

import test_ms4_additions as t4
import test_ms5_additions as t5
import test_rebuild as tr

from figs import print_sheet
from figs import rebuild as rb
from figs import style as st

REPO = SIM.parents[1]
PDFLATEX = Path.home() / ".local" / "bin" / "pdflatex"
HEIGHTS_SCRIPT = REPO / "paper" / "layout_check" / "pageplan" / "floats_heights.py"

# ---------------------------------------------------------------- C41: the registry table (W7)
WANT = {   # key: (label, color, marker, fill, line style, group, family); design/sublet_v2.md §11, W7
    "sublet_v2": ("Sublet", "#0072B2", "o", "filled", "-", "sublet", "sublet"),
    "sublet_v2_siloed": ("Sublet, siloed", "#0072B2", "o", "open", "--", "sublet", "sublet"),
    "sublet_v2_lag": ("Sublet, lagged", "#0072B2", "v", "filled", "-", "sublet", "sublet"),
    "sublet_1way": ("Sublet, one-way", "#0072B2", "D", "filled", "-", "guarded", "sublet"),
    "bl1_gp": ("Greedy + guard", "#E69F00", "^", "filled", "-", "guarded", "bl1"),
    "bl1_g1": ("Greedy + one-way guard", "#E69F00", "v", "filled", "-", "guarded", "bl1"),
    "bl5_g1": ("Lagged RetroRenting + one-way guard", "#56B4E9", ">", "filled", "-", "guarded", "bl5"),
    # C59 (RC19(3)): the allowance in words (as built "($B_0=10\%$ BL0a)")
    "sublet_ms4": (r"Lagged RetroRenting + one-way guard ($B_0=10\%$ of the all-fallback bill)", "#56B4E9", "<", "filled",
                   "-", "guarded", "bl5"),
    "a9": ("Critical-ratio renting", "#0072B2", "s", "filled", "-", "ours", "sublet"),
    "cr": ("Critical-ratio planning", "#0072B2", ">", "filled", "-", "ours", "sublet"),
    "a9_nombb": ("Critical-ratio renting, no make-before-break", "#0072B2", "d", "filled", "-", "ours", "sublet"),
    "a9_nocommit": ("Critical-ratio renting, no commitment rule", "#0072B2", "d", "open", "-", "ours", "sublet"),
    "a9_noins": ("Critical-ratio renting, no insurance", "#0072B2", "p", "open", "-", "ours", "sublet"),
    "a9_kstar": (r"Critical-ratio renting, $k^{\ast}$ contract", "#0072B2", "h", "open", "-", "ours", "sublet"),
    "a9_static": ("Critical-ratio renting, no site marking", "#0072B2", "P", "open", "-", "ours", "sublet"),
    "a9_lag": ("Critical-ratio renting, lagged", "#0072B2", "X", "open", "-", "ours", "sublet"),
    "bl1n": ("Greedy + notice layer", "#E69F00", "D", "open", "-", "ours", "bl1"),
    "bl5n": ("RetroRenting + notice layer", "#56B4E9", "X", "filled", "-", "ours", "bl5"),
    "bl5_cur": ("RetroRenting-style", "#56B4E9", "s", "open", "-", "baseline", "bl5"),
    "bl5_tau60": (r"RetroRenting, $\tau\geq1$ h", "#56B4E9", ">", "open", "-", "baseline", "bl5"),
    "bl5_lag": ("RetroRenting-style, lagged", "#56B4E9", "<", "open", "-", "baseline", "bl5"),
    "bl1_bo": ("Greedy, back-off", "#E69F00", "v", "open", "-", "baseline", "bl1"),
    "bl1_lag": ("Greedy renting, lagged", "#E69F00", ">", "filled", "-", "baseline", "bl1"),
    "bl3_0": (r"SpotHedge-style, $N_{\mathrm{Extra}}=0$", "#009E73", "p", "filled", "-", "baseline", "bl3"),
}
ANCHORS = {"sublet_siloed": ("sublet_v2", "sublet_v2_siloed", "sublet_v2_lag"),
           "bl1_guard": ("sublet_1way", "bl1_gp", "bl1_g1", "bl5_g1", "sublet_ms4", "a9", "cr", "a9_nombb",
                         "a9_nocommit", "a9_noins", "a9_kstar", "a9_static", "a9_lag", "bl1n", "bl5n"),
           "bl5": ("bl5_cur", "bl5_tau60", "bl5_lag"), "bl1": ("bl1_bo", "bl1_lag"), "bl3": ("bl3_0",)}
# the earlier key whose label (and so whose triple) a new key takes over (W7)
SUCCESSORS = {"sublet_v2": "sublet", "sublet_v2_siloed": "sublet_siloed", "bl1_gp": "bl1_guard", "bl5_cur": "bl5"}
# (color, marker) pairs that tests/test_ms3_additions.py (a3_rot, cold) and test_ms4_additions.py (C18) pin
PINNED = ("a3_rot", "cold") + tuple(t4.WANT_KEYS)
# W1's panels (a) and (c), with BL0a's reference line and BL0b's arrow of (a)
FIG4V2 = {"sublet_v2", "bl1_bo", "bl1", "bl5_cur", "bl5_tau60", "bl2", "bl3_0", "bl4", "bl1n", "bl1_gp", "bl5n",
          "bl0a", "bl0b"}
MS5B_SIZES = {"sf_e3_v2": ("W2", 2.2), "sf_e7_intensity": ("W2", 2.5), "sf_e7_decomp": ("W2", 2.4),
              "sf_e7_boundary": ("W2", 2.5),                                       # C59: was 2.4 in
              "sf_e7_grid_dev": ("W2", 2.4), "sf_fam_v2": ("W2", 2.2),
              "sf_e7_links": ("W1", 2.2)}
# C47: C46 moves the sets of the other fourteen frozen figures to the configuration keys (design/ms6_spec.md M1, M2, M4;
# W8's sixteen until then: fig1, fig3, fig4, fig5 and the twelve supplementary figures), so only the frozen fig1 and
# fig4, which the manuscript replaces by fig1v2 and fig4v2, still draw a legacy key
LEGACY_FIGURES = {"fig1", "fig4"}


@pytest.fixture()
def registry_without_test_figures(monkeypatch):
    """rebuild.entries() needs a script for every figure of style.FIGURES; the test-only figures that earlier test
    modules register ('test_*') are left out for the test (as tests/test_rebuild.py does)."""
    for k in [k for k in st.FIGURES if k.startswith("test_")]:
        monkeypatch.delitem(st.FIGURES, k)


def test_c41_ms5b_keys_as_built():
    """The 24 keys of W7's table with their labels, colors, markers, fills, line styles, groups and families; Sublet's
    emphasis; labels unique, with \\geq; no pinned (color, marker) pair; a triple shared with an earlier key only by the
    key that takes its label; each key after its anchor, the earlier keys in their order."""
    assert st.MS5B_KEYS == tuple(WANT)
    # C47: C46 adds a7_guard, which a7_g1 supersedes in every figure but the frozen fig4 (design/ms6_spec.md M3)
    assert st.LEGACY_KEYS == ("sublet", "sublet_siloed", "bl5", "bl1_guard", "a7_guard")
    allowed = {c.upper() for c in st.OKABE_ITO} | {"#4D4D4D"}
    # C47: the keys before MS5b; C46's MS6 keys (a7_g1, design/ms6_spec.md M3) come later and are tested in
    # tests/test_ms6_additions_figs.py
    earlier = {k: p for k, p in st.POLICIES.items() if k not in st.MS5B_KEYS and k not in st.MS6_KEYS
               and k not in st.MS7_KEYS                                      # C58 (W-G2): and the MS7 keys
               and k not in st.MS7_SUPP_KEYS                                 # C58 (W-G4): and the supplement's
               and k not in st.MS8_SUPP_KEYS}                                # MS8: and the MS8 supplement's
    for k, (label, color, marker, fill, ls, group, family) in WANT.items():
        p = st.POLICIES[k]
        assert (p.label, p.color, p.marker, p.fill, p.linestyle, p.group, p.family) == \
            (label, color, marker, fill, ls, group, family), k
        assert p.color.upper() in allowed and p.fill in st.FILLS and p.group in st.GROUPS and p.edgecolor is None, k
        assert "\\ge" not in label.replace("\\geq", ""), k
        assert p.note.startswith("MS5b C41"), k
        for q in PINNED:
            assert (p.color.upper(), p.marker) != (st.POLICIES[q].color.upper(), st.POLICIES[q].marker), (k, q)
        same = [q for q, e in earlier.items() if e.triple == p.triple]
        assert same == ([SUCCESSORS[k]] if k in SUCCESSORS else []), (k, same)
        if k in SUCCESSORS:
            assert p.label == earlier[SUCCESSORS[k]].label
    labels = [st.POLICIES[k].label for k in st.MS5B_KEYS]
    assert len(set(labels)) == len(labels)
    s, v = st.POLICIES["sublet"], st.POLICIES["sublet_v2"]
    assert (v.linewidth, v.markersize, v.zorder) == (s.linewidth, s.markersize, s.zorder) == \
        (st.SUBLET_LINE_PT, st.SUBLET_MARKER_PT, st.Z_SUBLET)
    assert v.zorder == max(p.zorder for p in st.POLICIES.values())
    assert st.POLICIES["sublet_v2_siloed"].zorder == st.POLICIES["sublet_siloed"].zorder
    order = list(st.POLICIES)
    for anchor, keys in ANCHORS.items():
        i = order.index(anchor)
        assert tuple(order[i + 1:i + 1 + len(keys)]) == keys, anchor
    assert tuple(earlier) == t5.MS4_POLICY_KEYS


def test_c41_fig4v2_and_ms5b_sets():
    """fig4v2 is a main-text figure (W2 x 2.4 in) with W1's set; SUPP_POLICIES_MS5B names W3's and W4's figures at their
    sizes (registered, covered by the ink tests' sizes, registered again only at the same size); each set lies within
    the registry and passes check_policies, with unique labels and no (marker, fill) twice; no set holds a legacy key;
    every MS5b key is in a set; RR_RENEW or MARKING beside sf_fam_v2's set fails the color rule; a siloed run is
    the sharing line style of the same key."""
    from test_figs_style import _sizes
    spec = st.FIGURES["fig4v2"]
    assert (spec.width, spec.height_in, spec.main) == ("W2", 2.4, True)
    assert set(st.FIGURE_POLICIES["fig4v2"]) == FIG4V2 and len(st.FIGURE_POLICIES["fig4v2"]) == len(FIG4V2)
    assert tuple(st.SUPP_POLICIES_MS5B) == tuple(MS5B_SIZES)
    assert not set(st.SUPP_POLICIES_MS5B) & (set(st.SUPP_POLICIES) | set(st.SUPP_POLICIES_MS4) |
                                             set(st.SUPP_POLICIES_MS5) | set(st.FIGURE_POLICIES))
    for name, (width, height) in MS5B_SIZES.items():
        spec = st.FIGURES[name]
        assert (spec.width, spec.height_in, spec.main) == (width, height, False), name
        assert (width, height) in _sizes(), name
        assert st.register_supplementary(name, width, height) == spec
        with pytest.raises(st.StyleError, match="already registered"):
            st.register_supplementary(name, width, 2.3)
    sets = {**st.SUPP_POLICIES_MS5B, "fig4v2": st.FIGURE_POLICIES["fig4v2"]}
    for name, keys in sets.items():
        assert len(set(keys)) == len(keys) and set(keys) <= set(st.POLICIES), name
        st.check_policies(keys)
        labels = [st.POLICIES[k].label for k in keys]
        assert len(set(labels)) == len(labels), name
        mf = [(st.POLICIES[k].marker, st.POLICIES[k].fill) for k in keys if st.POLICIES[k].marker is not None]
        assert len(set(mf)) == len(mf), (name, mf)
        assert not set(keys) & set(st.LEGACY_KEYS), name
        assert tuple(keys) == tuple(st.legend_order(keys)), name
    assert set(st.MS5B_KEYS) <= {k for keys in sets.values() for k in keys}
    assert set(st.SUPP_POLICIES_MS5B["sf_e7_links"]) == {"sublet_ms4", "bl5_lag", "bl1"}       # W4
    for k in ("rr_renew", "marking"):
        with pytest.raises(st.StyleError, match="share"):
            st.check_policies(st.SUPP_POLICIES_MS5B["sf_fam_v2"] + (k,))
    kw = st.policy_kwargs("sublet_ms4", env=("sharing", "siloed"))
    assert kw["linestyle"] == "--" and kw["marker"] == "<" and kw["label"] == st.POLICIES["sublet_ms4"].label


def test_c41_legacy_pending():
    """check_legacy() holds on every registry map; LEGACY_PENDING names exactly the frozen figures that draw a legacy
    key, each registered, each with a note naming its item; mixing, a missing entry and a stale entry each fail."""
    st.check_legacy()
    sets = st.figure_sets()
    assert set(sets) == (set(st.FIGURE_POLICIES) | set(st.SUPP_POLICIES) | set(st.SUPP_POLICIES_MS4) |
                         set(st.SUPP_POLICIES_MS5) | set(st.SUPP_POLICIES_MS5B)
                         | set(st.SUPP_POLICIES_MS7)                        # C58 (W-G4): the MS7 supplementary sets
                         | set(st.SUPP_POLICIES_MS8))                       # MS8: the MS8 supplementary sets
    drawing = {n for n, ks in sets.items() if set(ks) & set(st.LEGACY_KEYS)}
    assert drawing == set(st.LEGACY_PENDING) == LEGACY_FIGURES
    assert not drawing & (set(st.SUPP_POLICIES_MS5B) | {"fig4v2"})
    import importlib
    import pkgutil

    import figs.supp
    for m in pkgutil.iter_modules(figs.supp.__path__):        # the MS3 scripts register their own sizes
        importlib.import_module(f"figs.supp.{m.name}")
    for name, note in st.LEGACY_PENDING.items():
        assert name in st.FIGURES and isinstance(note, str) and ("W8" in note or "W6" in note), name
    with pytest.raises(st.StyleError, match=r"fig_x draws the MS5b keys \['sublet_v2'\] with the legacy keys"):
        st.check_legacy({"fig_x": ("sublet_v2", "sublet")}, {"fig_x": "pending"})
    with pytest.raises(st.StyleError, match="sf_y draws the legacy keys \\['bl5'\\] without a LEGACY_PENDING entry"):
        st.check_legacy({**sets, "sf_y": ("bl5", "bl1")})
    with pytest.raises(st.StyleError, match="fig4v2 has a LEGACY_PENDING entry but draws no legacy key"):
        st.check_legacy(sets, {**st.LEGACY_PENDING, "fig4v2": "stale"})
    st.check_legacy({"fig4v2": st.FIGURE_POLICIES["fig4v2"]})          # one figure's drawn keys alone


# ---------------------------------------------------------------- C42: the rebuild list
def test_c42_main_scripts_in_number_and_name_order(tmp_path, monkeypatch):
    """figure_scripts() sorts the main-text scripts by N, then by file name: fig4_e7_e3.py before fig4_v2.py, whatever
    order the file system lists them in."""
    sim = tmp_path / "code" / "sim"
    for sub in ("figs", "figs/supp"):
        (sim / sub).mkdir(parents=True)
    for n in ("fig7_e2_e6.py", "fig4_v2.py", "fig10_x.py", "fig4_e7_e3.py", "fig1_guard.py"):
        (sim / "figs" / n).write_text("NAME = 'x'\n")
    (sim / "figs" / "supp" / "sf_e7_links.py").write_text("NAME = 'x'\n")
    monkeypatch.setattr(rb, "SIM", sim)
    monkeypatch.setattr(rb, "REPO", tmp_path)
    got = [s for _, _, s in rb.figure_scripts()]
    assert got == [f"code/sim/figs/{n}" for n in ("fig1_guard.py", "fig4_e7_e3.py", "fig4_v2.py", "fig7_e2_e6.py",
                                                  "fig10_x.py")] + ["code/sim/figs/supp/sf_e7_links.py"]
    assert rb._script_key("main", "fig4_e7_e3.py") < rb._script_key("main", "fig4_v2.py")


def test_c42_ms5b_entries(registry_without_test_figures, tmp_path):
    """The MS5b figures are listed from MS5B_SCRIPTS while their scripts are missing (kind from the registry, module
    from the path, the PDF, extract and preview as outputs), in the place their scripts will take; Table III v2 follows
    Table III; the heights and hand-set entries of C42; an MS5b figure's entry without its extract is not run."""
    ents = rb.entries()
    by = {e.name: e for e in ents}
    names = [e.name for e in ents]
    assert names.index("fig4v2") == names.index("fig4") + 1
    for name, script in rb.MS5B_SCRIPTS.items():
        e = by[name]
        assert (e.kind == "main") == st.FIGURES[name].main and e.script == script, name
        assert e.module == ".".join(Path(script).relative_to("code/sim").with_suffix("").parts), name
        assert e.outputs[:3] == (f"{rb.MAIN_PDF_DIR if e.kind == 'main' else rb.SUPP_PDF_DIR}/{name}.pdf",
                                 f"{rb.EXTRACT_DIR}/{name}.json", f"{rb.EXTRACT_DIR}/{name}.png"), name
        if not (REPO / script).is_file():
            assert e.outputs[3:] == (), name
    supp = [e.script for e in ents if e.kind == "supp"]
    assert supp == sorted(supp)
    assert names.index("table3_v2") == names.index("table3_e7") + 1
    v2 = by["table3_v2"]
    assert (v2.kind, v2.script, v2.module, v2.extract) == ("float", "code/sim/figs/table3_v2.py", "figs.table3_v2",
                                                           "code/sim/out/figs/table3_v2.json")
    assert by["floats_heights_ms5b"].args == ("--ms5b",)
    assert by["floats_heights_ms5b"].outputs == ("code/sim/out/figs/floats_heights_ms5b.json",)
    assert rb.HAND_SET[:4] == ("paper/floats/table1_price_of_revocation.tex", "paper/floats/table2_policies.tex",
                               "paper/floats/alg1_guard.tex", "code/sim/out/figs/print_check.md")
    assert rb.HAND_SET[4:7] == ("paper/floats/table2_policies_v2.tex", "paper/floats/alg1_guard_v2.tex",
                                "paper/supplement/tables/ms5b_deviations.tex")   # C58: MS7's hand-set floats follow
    # an entry whose extract is missing is not run (no child), so it cannot pass
    root, work = tmp_path / "root", tmp_path / "work"
    root.mkdir()
    work.mkdir()
    run = rb.Run(root, work, True, None, True)
    rows = rb.run_entries(run, ents, [by["fig4v2"], by["sf_e7_links"], by["table3_v2"]])
    assert [r["status"] for r in rows] == ["no_extract"] * 3
    assert not (work / "_time").exists()


def test_c42_table3_v2_name_is_checked(registry_without_test_figures, monkeypatch):
    """A Table III v2 script whose NAME is not 'table3_v2' is a list error (here table3_e7.py under that entry)."""
    monkeypatch.setattr(rb, "TABLE3_V2", ("table3_v2", "code/sim/figs/table3_e7.py", "figs.table3_e7"))
    with pytest.raises(rb.RebuildError, match="must have NAME 'table3_v2'"):
        rb.entries()


def test_c42_heights_keys(tmp_path):
    """compare_outputs keys the float-height entries 'plain', 'ms4' and 'ms5b' (the earlier two as before), and since
    C58 'ms7'."""
    root, work = tmp_path / "root", tmp_path / "work"
    hs = [rb.Entry(n, "heights", rb.HEIGHTS_SCRIPT, None, (rel,), args=a) for n, a, rel in rb.HEIGHTS]
    for e in hs:
        for top in (root, work / "heights"):
            p = top / e.outputs[0] if top == root else top / Path(e.outputs[0]).name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps({"floats": {}, "written": "x"}))
    run = rb.Run(root, work, True, None, True)
    _, heights = rb.compare_outputs(run, hs, {})
    assert list(heights) == ["plain", "ms4", "ms5b", "ms7"] and all(h["equal"] for h in heights.values())  # C58: ms7
    assert [h["file"] for h in heights.values()] == [rel for _, _, rel in rb.HEIGHTS]


def test_c42_hand_set_floats_by_their_own_record(registry_without_test_figures, tmp_path):
    """Each hand-set float is checked against its own heights record: the frozen three against floats_heights.json,
    the two v2 floats against floats_heights_ms5b.json; a changed v2 float fails alone, and a v2 float that only the
    frozen record lists does not match."""
    ents = rb.entries()
    root = tr._tree(tmp_path, ents)
    snap = rb.snapshot(root)
    res = {h["path"]: h for h in rb.hand_set_check(root, snap, snap)}
    for rel in rb.HAND_SET:
        want = rb.HAND_SET_HEIGHTS.get(rel, rb.HEIGHTS_RECORD) if rel.startswith("paper/floats/") else None
        assert res[rel]["heights_record"] == want and res[rel]["ok"], rel
    v2_heights = {k: v for k, v in rb.HAND_SET_HEIGHTS.items() if not v.endswith("_ms7.json")}   # C58: and MS7's
    assert v2_heights == {"paper/floats/table2_policies_v2.tex": "code/sim/out/figs/floats_heights_ms5b.json",
                          "paper/floats/alg1_guard_v2.tex": "code/sim/out/figs/floats_heights_ms5b.json"}
    v2 = "paper/floats/alg1_guard_v2.tex"
    (root / v2).write_text("changed\n")
    snap2 = rb.snapshot(root)
    res = {h["path"]: h for h in rb.hand_set_check(root, snap2, snap2)}
    assert [p for p, h in res.items() if not h["ok"]] == [v2] and res[v2]["matches_heights_record"] is False
    rec = json.loads((root / rb.HEIGHTS_RECORD).read_text())          # listed in the frozen record only
    rec["floats"]["alg1_guard_v2"] = {"sha256": rb.sha256(root / v2)}
    (root / rb.HEIGHTS_RECORD).write_text(json.dumps(rec))
    snap3 = rb.snapshot(root)
    res = {h["path"]: h for h in rb.hand_set_check(root, snap3, snap3)}
    assert res[v2]["matches_heights_record"] is False


# ---------------------------------------------------------------- C43: the MS5b float budgets
def _heights():
    sys.path.insert(0, str(HEIGHTS_SCRIPT.parent))
    try:
        import floats_heights
    finally:
        sys.path.remove(str(HEIGHTS_SCRIPT.parent))
    return floats_heights


def test_c43_budgets_by_their_rule():
    """BUDGETS_MS5B: Table III v2 at MS4's measured Table III plus 0.0065 page per row beyond 10 (14 rows), Table II v2
    and Algorithm 1 v2 at the frozen floats' measured heights plus 0.0065 page per further line (10 and 3, W14's
    plan); the earlier maps unchanged; --ms4 and --ms5b exclude each other."""
    fh = _heights()
    frozen = json.loads((SIM / "out/figs/floats_heights.json").read_text())["floats"]
    ms4 = json.loads((SIM / "out/figs/floats_heights_ms4.json").read_text())["floats"]
    assert fh.LINE_PAGES == 0.0065
    assert fh.BUDGETS_MS5B == {
        "table3_v2": round(ms4["table3_e7"]["measured_pages"] + 4 * 0.0065, 4),
        "table2_policies_v2": round(frozen["table2_policies"]["measured_pages"] + 10 * 0.0065, 4),
        "alg1_guard_v2": round(frozen["alg1_guard"]["measured_pages"] + 3 * 0.0065, 4)}
    assert fh.BUDGETS_MS5B == {"table3_v2": 0.172, "table2_policies_v2": 0.4362, "alg1_guard_v2": 0.1913}
    assert fh.BUDGETS == {"table1_price_of_revocation": 0.09, "table2_policies": 0.22, "alg1_guard": 0.129}
    assert fh.BUDGETS_MS4 == {"table3_e7": 0.125}
    assert fh.OUT_MS5B == SIM / "out/figs/floats_heights_ms5b.json"
    r = subprocess.run([sys.executable, str(HEIGHTS_SCRIPT), "--ms4", "--ms5b"], capture_output=True, text=True)
    assert r.returncode == 2 and "not allowed with" in r.stderr


@pytest.mark.skipif(not PDFLATEX.is_file(), reason=f"{PDFLATEX} is not installed")
def test_c43_ms5b_heights_on_copies_of_the_frozen_floats(tmp_path):
    """--ms5b --floats DIR on copies of table3_e7.tex, table2_policies.tex and alg1_guard.tex under the v2 names
    measures the heights of the frozen records (method unchanged), each next to its MS5b budget, into --out only."""
    fh = _heights()
    d = tmp_path / "floats"
    d.mkdir()
    for src, dst in (("table3_e7", "table3_v2"), ("table2_policies", "table2_policies_v2"),
                     ("alg1_guard", "alg1_guard_v2")):
        shutil.copy(REPO / "paper" / "floats" / f"{src}.tex", d / f"{dst}.tex")
    out = tmp_path / "h.json"
    default = SIM / "out/figs/floats_heights_ms5b.json"
    before = default.stat().st_mtime_ns if default.exists() else None
    r = subprocess.run([sys.executable, str(HEIGHTS_SCRIPT), "--ms5b", "--floats", str(d), "--out", str(out)],
                       capture_output=True, text=True, timeout=600)
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]
    rep = json.loads(out.read_text())
    frozen = json.loads((SIM / "out/figs/floats_heights.json").read_text())["floats"]
    ms4 = json.loads((SIM / "out/figs/floats_heights_ms4.json").read_text())["floats"]
    assert list(rep["floats"]) == list(fh.BUDGETS_MS5B)
    for name, src, rec in (("table3_v2", "table3_e7", ms4), ("table2_policies_v2", "table2_policies", frozen),
                           ("alg1_guard_v2", "alg1_guard", frozen)):
        f = rep["floats"][name]
        assert f["measured_pages"] == rec[src]["measured_pages"] and f["sha256"] == rec[src]["sha256"], name
        assert f["budget_pages"] == fh.BUDGETS_MS5B[name], name
    assert (default.stat().st_mtime_ns if default.exists() else None) == before       # only --out was written


# ---------------------------------------------------------------- C44: the print sheet's order
def test_c44_fig4v2_follows_fig4():
    """main_figures() lists fig1-fig7 in order with fig4v2 right after fig4 (C47: and fig1v2 right after fig1); a name
    without the fig<N> form sorts last."""
    # C47: C46 registers fig1v2, the paper's Fig. 1 (design/ms6_spec.md M1), which C44's rule orders after fig1;
    # C58: fig1v3, the paper's Fig. 1 since MS7 (design/ms7/w_spec.md §4 W-G1), after fig1v2
    assert print_sheet.main_figures() == ["fig1", "fig1v2", "fig1v3", "fig2", "fig3", "fig4", "fig4v2", "fig4v3",
                                          "fig5", "fig6", "fig7"]                     # C58: fig1v3; fig4v3 (W-G2)
    assert sorted(["fig10", "fig4v2", "x", "fig4", "fig2"], key=print_sheet._order) == ["fig2", "fig4", "fig4v2",
                                                                                       "fig10", "x"]
