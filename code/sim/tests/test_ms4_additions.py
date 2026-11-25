"""Tests of the MS4 additions C17-C26 to MS1-MS3 files (design/sim_spec_ms4.md §2.3, §10).

- C17 (experiments/ms3_claims.py): figure_scripts() returns exactly the 20 MS3 figure scripts of MS3_FIGURE_SCRIPTS,
  also in a copy of the figure tree that holds figs/fig4_e7_e3.py and the MS4 figs/supp/sf_*.py, and their names
  equal the stems of tests/fixtures_figs/*.json.
- C18 (figs/style.py): the seven MS4 keys as built (label, color, marker, fill, family, group); their colors are
  Okabe-Ito colors, their (color, marker, fill) triples and (color, marker) pairs differ from every other key's, no
  FIGURE_POLICIES set uses them; the legend order lists the variants in parameter order (A6's default first); every
  SUPP_POLICIES_MS4 set (the eight figures of §8.2) passes check_policies; SUPP_POLICIES and SUPP_ONLY_KEYS keep their
  MS3 values; the MS4 figures are registered at their §8.2 sizes, and sf_e3_u, dropped with M41, is not; the new labels
  render in a saved figure with finalize() passing; sf_e5's seven keys fit legend_row's two rows, and with the two menu
  entries they do not (tests/test_figs_style.py and tests/test_ms3_additions.py are unchanged and run separately).
  C47 (design/ms6_spec.md M2, M4): the MS6 gate's C46 moves four MS3 and six MS4 sets to the configuration keys; with
  sublet_ms4 in Sublet's place, sf_e5's seven keys no longer fit two rows and its six other keys do.
- C19 (conftest.py): needs_ms4_out on a temporary root, as a helper and in a pytest run of probe tests in a
  subprocess: a test whose file is missing is skipped, one whose file is present runs, a marker without arguments
  skips on an empty folder.
- C20 (experiments/ms3_common.py): check_copy("e7") on a fake clone with the parts main, stress, gap and allow in the
  drivers' shape passes with its tree digests and fails, with the path named, when one part lacks summary.json or
  its run log lacks ms3_finish's done line; check_copy("e4") passes with revision-free JSON files under repro/ and
  fails, with the path named, for one elsewhere.
- C21 (paper/layout_check/pageplan/floats_heights.py): measure() with BUDGETS_MS4 on a temporary floats folder that
  holds a minimal booktabs table3_e7.tex records it with budget 0.125 and the probes' plan values; --ms4 writes a
  temporary output; code/sim/out/figs/floats_heights.json is unchanged (skipped without pdflatex).
- C22 (figs/print_sheet.py, unchanged): with a fig4 PDF in temporary SUBLET_FIGS_* folders, the sheet includes fig4
  at 100% in color and greyscale.
- C23 (.gitignore): the eight runs/ lines of the MS4 experiments.
- C24 (config.py, instance.py): borrowers.normalize "none" and an absent key give the same resolved config,
  config_hash and instance_hash on the series configs of E2 (with the instance hash that out/e2/manifest.json
  records from the MS3 runs), E10(b) and E3's b = 8 (shared and siloed; the overrides of measurement 4); "mean" on
  two series borrowers of different sizes gives clients whose overflow means agree to 1e-9 (relative) with merge
  false and, with merge true, one client equal to their sum, with Gamma solved once on the sum (oracle:
  recomputation from the series); a borrower without overflow is dropped with the builder's note; the regional and
  explicit models reject the key (needs_a12 where a series borrower is built).
- C25 (metrics.py): _git_revision, and ms3_common.git_revision through it, read HEAD from a .git folder and from a
  git worktree's .git file (its gitdir and commondir), with the branch as a loose ref or in packed-refs and with a
  detached HEAD; in this checkout it equals `git rev-parse HEAD` (skipped without git).
- C26 (algos/redundancy.py, M40): on hand-made observations on configs/toy.json with two clients, the X3 pool of a slot
  at L0 is (L0,), one correlation group, and the pool search has no site; 'always2' then buys the spare at the
  wider-set site L1 (another group, non-exposed 'long'), counted in buys and buys_wide; with no wider-set site (none
  feasible, only the majority group, or can_buy false) no spare and no_site 1; where the pool search succeeds or no
  spare is needed ('always2', 'rule' at 33 and 32 exposed, 'off') the actions and counts of tests/test_redundancy.py,
  the wider set never computed, and the report has the MS2 keys plus buys_wide 0.
"""
from __future__ import annotations

import copy
import hashlib
import importlib
import inspect
import json
import os
import shutil
import subprocess
import sys
import warnings
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
import pytest

from fixtures import CONFIGS, SIM, load_json, toy_config

from sublet.config import ConfigError, config_hash, load_config
from sublet.experiments import ms3_common as mc
from sublet.experiments.q44_study import instance_hash
from sublet.instance import build_instance

REPO = SIM.parents[1]
OUT = SIM / "out"
FIX = SIM / "tests" / "fixtures_figs"
LAYOUT = REPO / "paper" / "layout_check"
PDFLATEX = Path.home() / ".local" / "bin" / "pdflatex"
OKABE_ITO = {"#0072B2", "#E69F00", "#009E73", "#D55E00", "#CC79A7", "#56B4E9", "#F0E442", "#000000"}


# ---------------------------------------------------------------- C17: the frozen MS3 figure scripts
MS3_SCRIPTS = (
    ("fig1", "figs.fig1_guard", "figs/fig1_guard.py"), ("fig2", "figs.fig2_e1a", "figs/fig2_e1a.py"),
    ("fig3", "figs.fig3_e11", "figs/fig3_e11.py"), ("fig5", "figs.fig5_e1_e10", "figs/fig5_e1_e10.py"),
    ("fig6", "figs.fig6_e10", "figs/fig6_e10.py"), ("fig7", "figs.fig7_e2_e6", "figs/fig7_e2_e6.py"),
    ("sf_e10_cross", "figs.supp.sf_e10_cross", "figs/supp/sf_e10_cross.py"),
    ("sf_e10_rho", "figs.supp.sf_e10_rho", "figs/supp/sf_e10_rho.py"),
    ("sf_e10b", "figs.supp.sf_e10b", "figs/supp/sf_e10b.py"),
    ("sf_e11_fam", "figs.supp.sf_e11_fam", "figs/supp/sf_e11_fam.py"),
    ("sf_e11_guard", "figs.supp.sf_e11_guard", "figs/supp/sf_e11_guard.py"),
    ("sf_e11_inst", "figs.supp.sf_e11_inst", "figs/supp/sf_e11_inst.py"),
    ("sf_e1_rotation", "figs.supp.sf_e1_rotation", "figs/supp/sf_e1_rotation.py"),
    ("sf_e1_sched", "figs.supp.sf_e1_sched", "figs/supp/sf_e1_sched.py"),
    ("sf_e2_mu_cost", "figs.supp.sf_e2_mu_cost", "figs/supp/sf_e2_mu_cost.py"),
    ("sf_e2_mu_ep", "figs.supp.sf_e2_mu_ep", "figs/supp/sf_e2_mu_ep.py"),
    ("sf_e2_pool", "figs.supp.sf_e2_pool", "figs/supp/sf_e2_pool.py"),
    ("sf_e2_por", "figs.supp.sf_e2_por", "figs/supp/sf_e2_por.py"),
    ("sf_e6a", "figs.supp.sf_e6a", "figs/supp/sf_e6a.py"), ("sf_e6b", "figs.supp.sf_e6b", "figs/supp/sf_e6b.py"))
# the MS4 supplementary figures of §8.2; sf_e3_u, E3's u sweep, was dropped with M41
MS4_SUPP = ("sf_e3_util", "sf_e3_mu", "sf_e4", "sf_e5", "sf_e7_mix", "sf_e7_mu", "sf_e7_allow", "sf_e8")


# C58 (design/ms7/w_spec.md §4, W-G4): the supplementary figure scripts of the MS7 runs X1-X5 (figs/rebuild.py's
# MS7_SUPP_SCRIPTS), counted where present like the MS5, MS5b and MS6 scripts
MS7_SUPP = ("sf_lag_v2", "sf_oos", "sf_bl_ms7", "sf_stress_ms7", "sf_s1_v2", "sf_e5_v2", "sf_e8_v2", "sf_e9_v2")
# MS8 (design/ms8/plan.md W): and the supplementary figure scripts of the MS8 runs X6 and X7 (figs/rebuild.py's
# MS8_SUPP_SCRIPTS, one block per writer unit), counted where present
MS8_SUPP = tuple(__import__("figs.rebuild", fromlist=["MS8_SUPP_SCRIPTS"]).MS8_SUPP_SCRIPTS)


def test_c17_figure_scripts_are_the_20_ms3_scripts(tmp_path, monkeypatch):
    """figure_scripts() lists the 20 MS3 scripts in today's order (main-text figures first, each group by path),
    their names are the stems of the MS3 fixture extracts, and a figure tree that also holds figs/fig4_e7_e3.py,
    figs/table3_e7.py and the eight MS4 figs/supp/sf_*.py gives the same 20, where the former glob found 29."""
    from sublet.experiments import ms3_claims as mcl
    assert tuple(mcl.figure_scripts()) == MS3_SCRIPTS
    assert mcl.MS3_FIGURE_SCRIPTS == tuple(s for _, _, s in MS3_SCRIPTS)
    assert {n for n, _, _ in MS3_SCRIPTS} == {p.stem for p in FIX.glob("*.json")}
    sim = tmp_path / "sim"
    for sub in ("figs", "figs/supp"):
        (sim / sub).mkdir(parents=True)
        for p in (SIM / sub).glob("*.py"):
            shutil.copy(p, sim / sub / p.name)
    (sim / "figs" / "fig4_e7_e3.py").write_text('NAME = "fig4"\n')
    (sim / "figs" / "table3_e7.py").write_text('"""Table III."""\n')
    for n in MS4_SUPP:
        (sim / "figs" / "supp" / f"{n}.py").write_text(f'NAME = "{n}"\n')
    n5 = sum((sim / "figs" / "supp" / f"{n}.py").is_file() for n in ("sf_s1", "sf_e9", "sf_slack"))  # MS5 C33
    # C45: and the MS5b figure scripts present (design/sublet_v2.md §11, W1, W3, W4; units U37 and U39)
    n5b = sum((sim / "figs" / p).is_file() for p in ("fig4_v2.py", "supp/sf_e3_v2.py", "supp/sf_e7_intensity.py",
                                                      "supp/sf_e7_decomp.py", "supp/sf_e7_boundary.py",
                                                      "supp/sf_e7_grid_dev.py", "supp/sf_fam_v2.py",
                                                      "supp/sf_e7_links.py"))
    # C47 (design/ms6_spec.md M1, §2 U44): and the MS6 script of fig1v2, the paper's Fig. 1, where present
    n6 = int((sim / "figs" / "fig1_v2.py").is_file())
    n7 = int((sim / "figs" / "fig1_v3.py").is_file()) + int((sim / "figs" / "fig4_v3.py").is_file())   # C58
    n7 += sum((sim / "figs" / "supp" / f"{n}.py").is_file() for n in MS7_SUPP)   # C58 (W-G4): the X1-X5 figures
    n7 += sum((sim / "figs" / "supp" / f"{n}.py").is_file() for n in MS8_SUPP)   # MS8: the X6 and X7 figures
    assert len(list((sim / "figs").glob("fig*.py"))) + len(list((sim / "figs" / "supp").glob("sf_*.py"))) == \
        29 + n5 + n5b + n6 + n7
    monkeypatch.setattr(mcl.paths, "SIM", sim)
    assert tuple(mcl.figure_scripts()) == MS3_SCRIPTS
    with pytest.raises(ValueError, match="no figure script"):
        mcl.figures_block(tmp_path, tmp_path, ["fig4"])


# ---------------------------------------------------------------- C18: the MS4 supplementary registry keys
WANT_KEYS = {   # key: (label, color, marker, fill, family, group, edge color); design/sim_spec_ms4.md §8.2
    "psi_01": (r"$\psi$-PD, $\psi=0.1$", "#CC79A7", "<", "open", "pd", "ours", None),
    "psi_03": (r"$\psi$-PD, $\psi=0.3$", "#CC79A7", "D", "open", "pd", "ours", None),
    "psi_05": (r"$\psi$-PD, $\psi=0.5$", "#CC79A7", "p", "open", "pd", "ours", None),
    "a6_red_off": ("Two-timescale PD, no spare", "#CC79A7", "s", "filled", "a6", "ours", None),
    "a6_always2": ("Two-timescale PD, spare always", "#CC79A7", "P", "filled", "a6", "ours", None),
    "bl3_n0": (r"SpotHedge-style, $N_{\mathrm{Extra}}=0$", "#F0E442", "p", "filled", "bl3", "baseline", "#000000"),
    "bl3_n1": (r"SpotHedge-style, $N_{\mathrm{Extra}}=1$", "#F0E442", "d", "filled", "bl3", "baseline", "#000000"),
}
# design/sim_spec_ms4.md §8.2, column "Registry keys"; C47: with C46's configuration keys in place of the legacy keys
# (design/ms6_spec.md M2, M4: sublet -> sublet_ms4 at MS4's allowance, bl5_g1 in sf_e7_allow, whose axis sweeps B0;
# bl5 -> bl5_lag; a7_guard -> a7_ms4, the guard around A7 at MS4's allowance (C46, review of the gate); sublet_siloed
# leaves the sets, its runs drawn in the sharing line style)
SPEC_SETS = {
    "sf_e3_util": {"sublet_ms4", "a6", "a6_siloed", "bl2", "bl5_lag"},            # C47 (M2, M4)
    "sf_e3_mu": {"sublet_ms4", "a6", "a6_siloed", "bl2", "opt"},                  # C47 (M2, M4)
    "sf_e4": {"psi_01", "psi_03", "psi_05", "a2_frac", "a5"},
    "sf_e5": {"sublet_ms4", "a6_red_off", "a6", "a6_always2", "bl3_n0", "bl3_n1", "bl3"},       # C47 (M2, M4)
    "sf_e7_mix": {"sublet_ms4", "a7_ms4", "a7", "a6", "bl5_lag", "bl1", "bl2", "bl4"},         # C47 (M2, M3, M4)
    "sf_e7_mu": {"sublet_ms4", "a7_ms4", "a7", "a6", "bl5_lag", "bl1", "bl2", "bl4"},          # C47 (M2, M3, M4)
    "sf_e7_allow": {"bl5_g1", "bl5_lag"},                                         # C47 (M2, M4)
    "sf_e8": set(),
}
SPEC_SIZES = {"sf_e3_util": ("W2", 2.2), "sf_e3_mu": ("W1", 2.4),      # C59: sf_e3_mu was 2.2 in
              "sf_e4": ("W1", 2.2), "sf_e5": ("W2", 2.5),
              "sf_e7_mix": ("W2", 2.2), "sf_e7_mu": ("W2", 2.5), "sf_e7_allow": ("W1", 2.2), "sf_e8": ("W1", 2.2)}
# C47 (review of the gate): sf_e7_mu 2.5 in high (2.2 in §8.2), for the third legend row that the two guards at MS4's
# allowance (sublet_ms4, a7_ms4) take
# C47: sf_e1_sched and the sf_e11 figures with C46's configuration keys of Algorithm 1's defaults in place of the legacy
# keys (design/ms6_spec.md M2, M3, M4: sublet -> bl5_g1, bl5 -> bl5_lag, bl1_guard -> bl1_g1, a7_guard -> a7_g1)
MS3_SUPP_POLICIES = {
    "sf_e1_sched": ("bl5_g1", "a2_frac", "a2_r1", "a2_theory", "a3"), "sf_e1_rotation": ("a3", "a3_rot"),    # C47
    "sf_e2_por": (), "sf_e2_mu_ep": ("a1", "prewarm", "cold", "bl6"), "sf_e2_mu_cost": ("a1",),
    "sf_e2_pool": ("a1",), "sf_e6a": (), "sf_e6b": ("a6",), "sf_e10_rho": ("rr_renew", "a2_theory", "a3", "marking"),
    "sf_e10_cross": ("rr_renew", "a2_theory", "marking"), "sf_e10b": ("a3", "a4"),
    "sf_e11_inst": ("bl5_g1", "a7_g1", "bl1_g1", "a7", "a6", "bl5_lag", "bl1", "bl2"),                       # C47
    "sf_e11_fam": ("bl5_g1", "bl5_lag", "a7", "a7_g1", "a2_theory", "a3", "rr_renew", "marking"),           # C47
    "sf_e11_guard": ("bl5_g1", "a7_g1", "bl1_g1")}                                                          # C47


def test_c18_ms4_keys_and_sets():
    """The seven keys as built; Okabe-Ito colors, a fill of FILLS and a group of GROUPS; triples and (color, marker)
    pairs unlike any other key's; used by no FIGURE_POLICIES set and no MS3 supplementary set; each placed next to its
    family's key so that the legends list the variants in parameter order (psi = 0.1, 0.3, 0.5 before A2 fractional,
    psi = 1; N_Extra = 0, 1 before BL3's default 2), A6's default 'rule' first; SUPP_POLICIES_MS4 names the eight §8.2
    figures with their sets, each passing check_policies; the MS3 maps keep their values; the eight figures are
    registered at their §8.2 sizes, and sf_e3_u (E3's u sweep, dropped with M41) is not registered."""
    from figs import style as st
    assert st.SUPP_ONLY_KEYS_MS4 == tuple(WANT_KEYS)
    order = list(st.POLICIES)
    for k, (label, color, marker, fill, family, group, edge) in WANT_KEYS.items():
        p = st.POLICIES[k]
        assert (p.label, p.color, p.marker, p.fill, p.family, p.group, p.edgecolor) == \
            (label, color, marker, fill, family, group, edge), k
        assert p.color.upper() in OKABE_ITO and p.fill in st.FILLS and p.group in st.GROUPS, k
        others = [q for q in st.POLICIES.values() if q.key != k]
        assert p.triple not in {q.triple for q in others}, k
        assert (p.color.upper(), p.marker) not in {(q.color.upper(), q.marker) for q in others}, k
        assert not any(k in keys for keys in st.FIGURE_POLICIES.values()), k
        assert not any(k in keys for keys in st.SUPP_POLICIES.values()), k
    assert order[order.index("a2_frac") - 3:order.index("a2_frac")] == ["psi_01", "psi_03", "psi_05"]
    assert order[order.index("a6_siloed") + 1:order.index("a6_siloed") + 3] == ["a6_red_off", "a6_always2"]
    assert order[order.index("bl3") - 2:order.index("bl3")] == ["bl3_n0", "bl3_n1"]
    # C47: sublet_ms4, a guarded key, in the frozen sublet's place (design/ms6_spec.md M2, M4)
    assert st.legend_order(st.SUPP_POLICIES_MS4["sf_e5"]) == ["sublet_ms4", "a6", "a6_red_off", "a6_always2", "bl3_n0",
                                                              "bl3_n1", "bl3"]
    assert st.legend_order(st.SUPP_POLICIES_MS4["sf_e4"]) == ["psi_01", "psi_03", "psi_05", "a2_frac", "a5"]
    # the sets of §8.2, each within the registry and passing check_policies; every new key is used
    assert tuple(st.SUPP_POLICIES_MS4) == MS4_SUPP
    assert {n: set(v) for n, v in st.SUPP_POLICIES_MS4.items()} == SPEC_SETS
    for name, keys in st.SUPP_POLICIES_MS4.items():
        assert len(set(keys)) == len(keys) and set(keys) <= set(st.POLICIES), name
        st.check_policies(keys)
    assert set(WANT_KEYS) <= {k for keys in st.SUPP_POLICIES_MS4.values() for k in keys}
    # the color is shared only within a family: the A6 and PD variants, and the BL3 and BL4 yellows, never mix
    for a, b in (("a6_red_off", "psi_01"), ("a6_always2", "a5"), ("bl3_n0", "bl4")):
        with pytest.raises(st.StyleError, match="share"):
            st.check_color_reuse([a, b])
    # the MS3 maps are unchanged (tests/test_ms3_additions.py:293 and :301 fix them); C47: but for C46's configuration
    # keys in four sets (MS3_SUPP_POLICIES above; design/ms6_spec.md M2, M4)
    assert st.SUPP_ONLY_KEYS == ("a3_rot", "cold") and st.SUPP_POLICIES == MS3_SUPP_POLICIES
    for name, (width, height) in SPEC_SIZES.items():
        spec = st.FIGURES[name]
        assert (spec.width, spec.height_in, spec.main) == (width, height, False), name
        assert st.register_supplementary(name, width, height) == spec       # a script registers it again
        with pytest.raises(st.StyleError, match="already registered"):
            st.register_supplementary(name, width, 2.4 if height != 2.4 else 2.3)
    assert {k: (s.width, s.height_in) for k, s in st.FIGURES.items() if s.main}["fig4"] == ("W2", 2.2)
    assert "sf_e3_u" not in st.FIGURES and "sf_e3_u" not in st.SUPP_POLICIES_MS4         # M41


def test_c18_new_labels_render(tmp_path):
    """Every new key's label, with its family's, is drawn in two corner legends of a W2 x 2.5-in figure that
    style.save writes with finalize() passing: every glyph is in the figure fonts, every text at a size of C62's
    scale, no mathtext glyph below SCRIPT_MIN_PT."""
    from figs import style as st
    name = st.register_supplementary("test_ms4_c18_labels", "W2", 2.5).name
    fig = st.new_figure(name)
    axes = st.panel_row(fig, (1, 1))
    # C47: sf_e5's set without C46's sublet_ms4 (design/ms6_spec.md M2, M4), whose label is wider than a W2 panel's
    # corner holds (the MS5b figure tests draw it); the C18 keys keep their families
    sets = (st.SUPP_POLICIES_MS4["sf_e4"], tuple(k for k in st.SUPP_POLICIES_MS4["sf_e5"] if k != "sublet_ms4"))
    for ax, keys in zip(axes, sets):
        for i, k in enumerate(keys):
            st.plot_policy(ax, k, [1, 2, 4], [0.1 * i + 1.0, 0.1 * i + 1.05, 0.1 * i + 1.1])
        ax.set_xlim(0.8, 12)
        ax.set_ylim(0.9, 3.2)
        ax.set_xlabel("Day")
        ax.set_ylabel("Cost / all-fallback")
        st.corner_legend(ax, keys, loc="upper right")
    st.panel_letters(axes)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        rep = st.save(fig, name, {"keys": [list(s) for s in sets]}, pdf_dir=tmp_path, out_dir=tmp_path)
    assert not [w for w in caught if issubclass(w.category, st.GlyphSizeWarning)]
    texts = [t.get_text() for ax in axes for t in ax.get_legend().get_texts()]
    assert set(texts) == {st.POLICIES[k].label for s in sets for k in s}
    assert set(rep["text_pt"]) == {st.TICK_PT, st.LABEL_PT} and rep["outside_page"] == [] and \
        (tmp_path / f"{name}.pdf").is_file()


def test_c18_sf_e5_legend_fits_two_rows():
    """sf_e5's legend (§8.2): its seven keys fill legend_row's two rows over the five panels of the registered
    W2 x 2.5-in figure, within the page width less the right margin, in the order Sublet, A6 ('rule', 'off',
    'always2'), BL3 (N_Extra 0, 1, 2); with the entries 'short notice' and 'long notice' the rows do not fit, so the
    caption names the filled (short-notice menu) and open (long-notice menu) markers.

    C47 (design/ms6_spec.md M2, M4): with C46's sublet_ms4 in Sublet's place the seven entries no longer fit two rows
    (sublet_ms4 shares (<, filled) with BL3: tests/test_ms6_additions_figs.py, GREY_SHARED); the six other keys fit in
    the C18 order. As built, sf_e5 (unit U43b) keeps sublet_ms4 in its legend rows, which hold the five keys it draws
    on E5 (A6's modes merged), or side by side in two rows of their own where more are drawn, and BL3's black edge and
    lighter fill tell the two triangles apart; the menu entries are not in the rows (with sublet_ms4's label they need
    a third row), so the caption names the filled and open markers, as before."""
    from figs import style as st
    seven = st.SUPP_POLICIES_MS4["sf_e5"]
    keys = tuple(k for k in seven if k != "sublet_ms4")                 # C47: the six keys other than sublet_ms4

    def legend(ks):
        fig = st.new_figure("sf_e5")
        st.panel_row(fig, (1, 1, 1, 1, 1), legend=2, sharey=(False, True, True, True, True))
        return fig, st.legend_row(fig, ks, rows=2)
    with pytest.raises(st.StyleError, match="wider than the figure"):  # C47: sublet_ms4's label (C46)
        legend(seven)
    fig, leg = legend(keys)
    assert leg.get_window_extent(fig.canvas.get_renderer()).width / fig.dpi <= st.W2 - st.MARGIN_RIGHT
    assert [t.get_text() for t in leg.get_texts()] == [st.POLICIES[k].label for k in st.legend_order(keys)]
    assert st.legend_order(keys)[0:3] == ["a6", "a6_red_off", "a6_always2"]     # C47: [1:4] with Sublet first


# ---------------------------------------------------------------- C19: the marker needs_ms4_out
def test_c19_needs_ms4_out_helper(tmp_path, monkeypatch):
    """conftest._ms4_out_missing (as _ms3_out_missing, C15): the named files missing under MS4_OUT_DIR, and the folder
    itself when a marker has no argument (alone or beside markers with files) and the folder is missing or empty."""
    import conftest
    out = tmp_path / "code" / "sim" / "out"
    monkeypatch.setattr(conftest, "MS4_OUT_DIR", out)
    assert conftest._ms4_out_missing([]) == [str(out)]
    assert conftest._ms4_out_missing(["e7/main/summary.json"]) == ["e7/main/summary.json"]
    out.mkdir(parents=True)
    assert conftest._ms4_out_missing([]) == [str(out)]
    assert conftest._ms4_out_missing(["e3/summary.json"], folder=True) == [str(out), "e3/summary.json"]
    (out / "e3").mkdir()
    (out / "e3" / "summary.json").write_text("{}")
    assert conftest._ms4_out_missing(["e3/summary.json"], folder=True) == [] and conftest._ms4_out_missing([]) == []
    assert conftest.MS3_OUT_DIR != out                    # the MS3 marker keeps its own root


PROBE_TESTS = '''
import pytest


@pytest.mark.needs_ms4_out("e7/main/summary.json")
def test_present():
    pass


@pytest.mark.needs_ms4_out("e3/summary.json")
def test_missing():
    pass


@pytest.mark.needs_ms4_out()
def test_folder():
    pass


@pytest.mark.needs_ms4_out("e7/main/summary.json")
@pytest.mark.parametrize("case", [pytest.param("e4", marks=pytest.mark.needs_ms4_out("e4/summary.json")), "e7"])
def test_case(case):
    pass
'''


def _probe_run(tmp_path: Path, root: Path, *args) -> dict:
    """Run the probe tests in a pytest subprocess with code/sim/conftest.py as plugin and SUBLET_MS4_OUT_ROOT=root;
    {test id: 'passed' | 'skipped' | 'failed'} from its JUnit XML (deselected tests are absent)."""
    probe = tmp_path / "probe" / "test_probe.py"
    probe.parent.mkdir(exist_ok=True)
    probe.write_text(PROBE_TESTS)
    xml = tmp_path / "probe" / f"report_{len(list(probe.parent.glob('report_*.xml')))}.xml"
    env = dict(os.environ, PYTHONPATH=str(SIM), SUBLET_MS4_OUT_ROOT=str(root), PYTHONDONTWRITEBYTECODE="1")
    r = subprocess.run([sys.executable, "-m", "pytest", "-p", "no:cacheprovider", "-p", "conftest", "-q",
                        f"--rootdir={probe.parent}", "-c", os.devnull, f"--junitxml={xml}", *args, str(probe)],
                       cwd=str(probe.parent), env=env, capture_output=True, text=True, timeout=120)
    assert r.returncode in (0, 5), r.stdout + r.stderr                # 5: every test deselected
    out = {}
    for tc in ET.parse(xml).getroot().iter("testcase"):
        kind = "skipped" if tc.find("skipped") is not None else \
            "failed" if tc.find("failure") is not None or tc.find("error") is not None else "passed"
        out[tc.get("name")] = kind
    return out


def test_c19_needs_ms4_out_in_a_pytest_run(tmp_path):
    """On a temporary root (SUBLET_MS4_OUT_ROOT): with an empty out folder every probe test is skipped (the marker
    without arguments too); with e7/main/summary.json present the tests that need only it run, the ones that need
    e3/summary.json or e4/summary.json (a parametrized case's own marker) are skipped; the quick suite's expression
    deselects them all."""
    root = tmp_path / "root"
    out = root / "code" / "sim" / "out"
    out.mkdir(parents=True)
    names = ("test_present", "test_missing", "test_folder", "test_case[e4]", "test_case[e7]")
    assert _probe_run(tmp_path, root) == {n: "skipped" for n in names}
    (out / "e7" / "main").mkdir(parents=True)
    (out / "e7" / "main" / "summary.json").write_text("{}")
    assert _probe_run(tmp_path, root) == {"test_present": "passed", "test_missing": "skipped",
                                          "test_folder": "passed", "test_case[e4]": "skipped",
                                          "test_case[e7]": "passed"}
    quick = "not needs_raw and not needs_ms2_checks and not needs_ms3_out and not needs_ms4_out"
    assert _probe_run(tmp_path, root, "-m", quick) == {}


# ---------------------------------------------------------------- C20: the copy checks of E7's parts and E4's repro/
COMMIT = "0123456789abcdef0123456789abcdef01234567"
E7_PARTS = ("main", "stress", "gap", "allow")


def _part_files(exp: str, part: str) -> dict:
    """One experiment folder (or part) in the drivers' shape (as tests/test_ms3_common.py builds it): manifest and
    summary with meta.git_revision, job records with a top-level git_revision (a failure record without one, with
    its rule), a run file and an LB record."""
    jid = mc.job_id(exp, part or "cell", c=1)
    milp = mc.job_id(exp, "milp", c=1)
    return {
        "manifest.json": {"meta": {"exp": exp, "git_revision": COMMIT}, "jobs": []},
        "summary.json": {"meta": {"exp": exp, "git_revision": COMMIT, "reduced": False}, "checks": {}},
        f"jobs/{mc.job_file_name(jid)}": {"job": jid, "status": "ok", "git_revision": COMMIT},
        f"jobs/{mc.job_file_name(milp)}": {"job": milp, "status": "failed", "exit_code": 3, "rule": "exit 3"},
        f"jobs/{mc.job_file_name(mc.job_id(exp, 'summary'))}": {"job": mc.job_id(exp, "summary"), "status": "ok",
                                                                 "git_revision": COMMIT},
        f"jobs/{mc.job_file_name(mc.job_id(exp, 'manifest'))}": {"job": mc.job_id(exp, "manifest"), "status": "ok",
                                                                  "git_revision": COMMIT},
        "runs/c=1/Sublet_p0.json": {"meta": {"git_revision": COMMIT}, "components": {}},
        "lb/lp_c1.json": {"job": jid, "git_revision": COMMIT, "status": 0},
    }


def _write_part(top: Path, exp: str, part: str, done: bool = True) -> None:
    for rel, obj in _part_files(exp, part).items():
        p = top / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(obj, indent=1) + "\n")
    (top / "logs").mkdir(exist_ok=True)
    (top / "logs" / "cell.log").write_text("run one\n")
    (top / "tables.md").write_text("# tables\n")
    lines = [f"[run_{exp}] start 2026-11-02T07:35:00+08:00 on host: 4 slot(s) now",
             f"[run_{exp}] pool jobs done 2026-11-02"]
    if done:
        lines.append(f"[run_{exp}] done 2026-11-02T08:00:00+08:00")
    (top / f"run_{exp}.log").write_text("\n".join(lines) + "\n")


def _clone_with(tmp_path: Path, exp: str, build) -> tuple[Path, Path]:
    """(root, clone): a fake clone (a .git/HEAD at COMMIT) whose code/sim/out/<exp> is filled by build(top), and a
    temporary root whose out/<exp> is an exact copy of it."""
    clone = tmp_path / "clone"
    (clone / ".git").mkdir(parents=True)
    (clone / ".git" / "HEAD").write_text(COMMIT + "\n")
    top = clone / "code" / "sim" / "out" / exp
    build(top)
    root = tmp_path / "root"
    shutil.copytree(top, root / "out" / exp)
    return root, clone


def _both(root: Path, clone: Path, exp: str, fn) -> None:
    for top in (root / "out" / exp, clone / "code" / "sim" / "out" / exp):
        fn(top)


def test_c20_check_copy_e7_parts(tmp_path):
    """E7's folder with the parts main, stress, gap and allow (each with its manifest, job records, run log and
    summary) and table3.json at its top passes, with tree_sha256 = tree_digest of the copy and the clone, and
    tree_sha256_versioned leaving out every part's runs/; a part without summary.json, or whose run log lacks the
    done line, fails with that part's path named. The MS3 entries are unchanged."""
    def build(top):
        for part in E7_PARTS:
            _write_part(top / part, "e7", part)
        (top / "table3.json").write_text(json.dumps({"meta": {"git_revision": COMMIT}, "rows": []}))
    root, clone = _clone_with(tmp_path, "e7", build)
    copy_dir = root / "out" / "e7"
    res = mc.check_copy("e7", clone, root)
    assert res["pass"] is True and all(res["checks"].values()), res["checks"]
    assert res["parts"] == list(E7_PARTS) and res["n_files_copy"] == 4 * (len(_part_files("e7", "main")) + 3) + 1
    assert set(res["run_logs"]) == set(E7_PARTS) and res["run_logs"]["gap"]["file"] == "gap/run_e7.log"
    assert res["manifest_git_revision"] == {p: COMMIT for p in E7_PARTS}
    assert {p: s["file"] for p, s in res["summaries"].items()} == {p: f"{p}/summary.json" for p in E7_PARTS}
    assert res["no_revision_by_kind"] == {f"{p}/jobs": 1 for p in E7_PARTS}
    assert res["tree_sha256"] == mc.tree_digest(copy_dir) == mc.tree_digest(clone / "code" / "sim" / "out" / "e7")
    assert res["tree_sha256_versioned"] == mc.tree_digest(copy_dir, "e7") != res["tree_sha256"]
    assert mc._unversioned("e7", "allow/runs/c=1/x.json") and not mc._unversioned("e7", "allow/jobs/x.json")
    assert not mc._unversioned("e7", "table3.json")
    versioned = res["tree_sha256_versioned"]
    # a part without summary.json fails summary_ok with that part's file named
    _both(root, clone, "e7", lambda top: (top / "allow" / "summary.json").unlink())
    res = mc.check_copy("e7", clone, root)
    assert res["pass"] is False and [k for k, v in res["checks"].items() if not v] == ["summary_ok"]
    assert res["summaries"]["allow"]["file"] == "allow/summary.json" and res["summaries"]["allow"]["exists"] is False
    assert all(res["summaries"][p]["ok"] for p in ("main", "stress", "gap"))
    _both(root, clone, "e7", lambda top: (top / "allow" / "summary.json").write_text(
        json.dumps(_part_files("e7", "allow")["summary.json"], indent=1) + "\n"))
    assert mc.check_copy("e7", clone, root)["pass"] is True
    # a part whose run log lacks ms3_finish's done line fails run_log_done with that log named
    _both(root, clone, "e7", lambda top: _write_part(top / "gap", "e7", "gap", done=False))
    res = mc.check_copy("e7", clone, root)
    assert res["pass"] is False and [k for k, v in res["checks"].items() if not v] == ["run_log_done"]
    assert res["run_logs"]["gap"] == {"file": "gap/run_e7.log", "exists": True,
                                      "last_line": "[run_e7] pool jobs done 2026-11-02", "done": False}
    assert all(res["run_logs"][p]["done"] for p in ("main", "stress", "allow"))
    # a checkout without the run files recomputes the versioned digest
    _both(root, clone, "e7", lambda top: _write_part(top / "gap", "e7", "gap"))
    for part in E7_PARTS:
        shutil.rmtree(copy_dir / part / "runs")
    assert mc.tree_digest(copy_dir, "e7") == versioned
    assert {k: mc.COPY_PARTS[k] for k in ("e6", "e7")} == {"e6": ("a", "b"), "e7": E7_PARTS}      # MS5 C33


def test_c20_check_copy_e4_repro(tmp_path):
    """E4's repro/ files (repro_c5_la's outputs, whose meta records no git revision) pass revisions_recorded; a
    revision-free JSON file elsewhere, also one in a folder named repro below another, fails with its path named.
    E2's MS3 entry is unchanged."""
    files = ("repro/c5_la_repro.json", "repro/c5_la_nearest_repro.json")

    def build(top):
        _write_part(top, "e4", "")
        for rel in files:
            (top / rel).parent.mkdir(parents=True, exist_ok=True)
            (top / rel).write_text(json.dumps({"meta": {"script": "repro_c5_la"}, "rows": []}))
    root, clone = _clone_with(tmp_path, "e4", build)
    res = mc.check_copy("e4", clone, root)
    assert res["pass"] is True and all(res["checks"].values()), res["checks"]
    assert res["no_revision_allowed_under"] == ["repro/"] and res["parts"] == []
    assert res["no_revision_by_kind"] == {"jobs": 1, "repro": 2} and res["n_no_revision_unexpected"] == 0
    for rel in ("runs/c=1/extra.json", "runs/repro/c5_la_repro.json"):
        def put(top, rel=rel):
            (top / rel).parent.mkdir(parents=True, exist_ok=True)
            (top / rel).write_text(json.dumps({"rows": []}))
        _both(root, clone, "e4", put)
        res = mc.check_copy("e4", clone, root)
        assert res["pass"] is False and [k for k, v in res["checks"].items() if not v] == ["revisions_recorded"]
        assert res["no_revision_unexpected"] == [rel]
        _both(root, clone, "e4", lambda top, rel=rel: (top / rel).unlink())
    assert mc.COPY_NO_REVISION == {"e2": ("runs/joint/", "runs/ep_milp/"), "e4": ("repro/",)}


# ---------------------------------------------------------------- C21: Table III's measured height
TABLE_PROBE = r"""\begin{table}[!t]
\caption{A minimal probe float}
\label{tab:probe}
\centering
\footnotesize
\begin{tabular}{lrr}
\toprule
Policy & USD & Saving (\%) \\
\midrule
Sublet & 13.9 & 31.7 \\
All-fallback & 20.4 & 0.0 \\
\bottomrule
\end{tabular}
\end{table}
"""


def _floats_heights():
    sys.path.insert(0, str(LAYOUT / "pageplan"))
    try:
        return importlib.import_module("floats_heights")
    finally:
        sys.path.remove(str(LAYOUT / "pageplan"))


def _sha(p: Path):
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None


@pytest.mark.skipif(not PDFLATEX.is_file(), reason=f"{PDFLATEX} is not installed")
def test_c21_floats_heights_ms4(tmp_path):
    """measure() with BUDGETS_MS4 and a temporary floats folder holding a minimal booktabs table3_e7.tex records
    table3_e7 with budget 0.125, its source and sha256, and the probes at the plan's values; --ms4 with --floats and
    --out writes the same floats into a temporary file; the default budgets, floats folder and output are MS3's, and
    neither floats_heights.json nor floats_heights_ms4.json in code/sim/out/figs changes."""
    fh = _floats_heights()
    fixed = OUT / "figs" / "floats_heights.json"
    ms4_out = OUT / "figs" / "floats_heights_ms4.json"
    before = (_sha(fixed), _sha(ms4_out))
    assert fh.BUDGETS == {"table1_price_of_revocation": 0.09, "table2_policies": 0.22, "alg1_guard": 0.129}
    assert fh.BUDGETS_MS4 == {"table3_e7": 0.125} and fh.OUT_MS4 == ms4_out and fh.OUT == fixed
    sig = inspect.signature(fh.measure).parameters
    assert sig["budgets"].default is fh.BUDGETS and sig["floats_dir"].default == fh.FLOATS == REPO / "paper" / "floats"
    floats = tmp_path / "floats"
    floats.mkdir()
    (floats / "table3_e7.tex").write_text(TABLE_PROBE, encoding="utf-8")
    (tmp_path / "wd").mkdir()
    rep = fh.measure(fh.BUDGETS_MS4, workdir=tmp_path / "wd", floats_dir=floats)
    assert set(rep["floats"]) == {"table3_e7"}
    v = rep["floats"]["table3_e7"]
    assert v["budget_pages"] == 0.125 and 0 < v["measured_pages"] < 0.125 and v["within_budget"] is True
    assert v["source"] == str((floats / "table3_e7.tex").resolve())
    assert v["sha256"] == hashlib.sha256(TABLE_PROBE.encode()).hexdigest()
    for k, p in rep["probes"].items():           # the plan's constants of the mock pages (figure_plan §3.1)
        assert abs(p["measured_pages"] - p["plan_value_pages"]) <= 0.001, (k, p)
    out = tmp_path / "heights_ms4.json"
    rep2 = fh.main(["--ms4", "--floats", str(floats), "--out", str(out)])
    disk = json.loads(out.read_text())
    assert set(disk["floats"]) == {"table3_e7"} and disk["floats"]["table3_e7"]["budget_pages"] == 0.125
    assert disk["floats"]["table3_e7"]["measured_pages"] == v["measured_pages"] == rep2["floats"]["table3_e7"][
        "measured_pages"]
    assert (_sha(fixed), _sha(ms4_out)) == before


# ---------------------------------------------------------------- C22: the print sheet with Fig. 4
def test_c22_print_sheet_includes_fig4(tmp_path, monkeypatch):
    """A fig4 PDF at its registered size (W2 x 2.2 in) in a temporary SUBLET_FIGS_PDF_DIR: the sheet, written in a
    temporary SUBLET_FIGS_OUT_DIR, includes fig4 on its own page, in color and in greyscale, each at 100% (the
    figure's 9-pt probe text keeps its size and width), and lists the other main-text figures as skipped."""
    import fitz
    from figs import print_sheet, style as st
    pdf_dir, out_dir = tmp_path / "pdf", tmp_path / "out"
    pdf_dir.mkdir()
    monkeypatch.setenv(st.ENV_PDF_DIR, str(pdf_dir))
    monkeypatch.setenv(st.ENV_OUT_DIR, str(out_dir))
    w, h = st.W2 * st.BP_PER_IN, 2.2 * st.BP_PER_IN
    doc = fitz.open()
    page = doc.new_page(width=w, height=h)
    page.insert_text(fitz.Point(40, 60), "fig4 probe", fontname="helv", fontsize=9)
    doc.save(pdf_dir / "fig4.pdf")
    doc.close()
    with fitz.open(pdf_dir / "fig4.pdf") as src:
        width0 = [s["bbox"][2] - s["bbox"][0] for b in src[0].get_text("dict")["blocks"] for ln in b.get("lines", ())
                  for s in ln["spans"] if s["text"] == "fig4 probe"]
    # C45: C41 registers fig4v2 and C44 orders it after fig4 (design/sublet_v2.md §11, W1, W12); C47: C46 registers
    # fig1v2 (design/ms6_spec.md M1), which C44's rule orders after fig1
    assert print_sheet.main_figures() == ["fig1", "fig1v2", "fig1v3", "fig2", "fig3", "fig4", "fig4v2", "fig4v3",
                                          "fig5", "fig6", "fig7"]                     # C58: fig1v3; fig4v3 (W-G2)
    rep = print_sheet.main([])
    assert [r["figure"] for r in rep["included"]] == ["fig4"]
    assert rep["skipped"] == ["fig1", "fig1v2", "fig1v3", "fig2", "fig3", "fig4v2", "fig4v3", "fig5", "fig6",
                              "fig7"]                                                     # C47 (M1), C58
    assert Path(rep["pdf"]) == out_dir / "print_check.pdf"
    with fitz.open(rep["pdf"]) as sheet:
        assert sheet.page_count == 2
        assert "fig4: included" in sheet[0].get_text() and "fig7: skipped" in sheet[0].get_text()
        txt = sheet[1].get_text()
        for mode in ("color", "greyscale"):
            assert f"fig4 ({mode}, 100%, {w:.2f} x {h:.2f} bp)" in txt, mode
        spans = [s for b in sheet[1].get_text("dict")["blocks"] for ln in b.get("lines", ()) for s in ln["spans"]
                 if s["text"] == "fig4 probe"]
    n = 2 if rep["included"][0]["greyscale"].startswith("ghostscript") else 1     # a raster greyscale has no text
    assert len(spans) == n and all(abs(s["size"] - 9.0) < 1e-6 for s in spans)
    assert all(abs((s["bbox"][2] - s["bbox"][0]) - width0[0]) < 0.01 for s in spans)


# ---------------------------------------------------------------- C23: .gitignore
def test_c23_gitignore_lines():
    """The eight runs/ folders of the MS4 experiments are ignored, each by its own line."""
    lines = {ln.strip() for ln in (REPO / ".gitignore").read_text().splitlines()}
    want = ["code/sim/out/e3/runs/", "code/sim/out/e4/runs/", "code/sim/out/e5/runs/", "code/sim/out/e7/main/runs/",
            "code/sim/out/e7/stress/runs/", "code/sim/out/e7/gap/runs/", "code/sim/out/e7/allow/runs/",
            "code/sim/out/e8/runs/"]
    assert [w for w in want if w not in lines] == []


# ---------------------------------------------------------------- C24: borrowers.normalize of the series model
E3_SIZES = OUT / "ms4spec" / "e3_sizing_b8_sizes.json"     # measurement 4: E3's b = 8 overrides (shared, siloed)
E3_SLICES = (("azure2024_conv", 0), ("azure2024_code", 0), ("burstgpt_1__ChatGPT__conv", 0),
             ("burstgpt_1__ChatGPT__api", 0), ("burstgpt_2__ChatGPT__conv", 0), ("burstgpt_2__ChatGPT__api", 0),
             ("burstgpt_3__ChatGPT__conv", 0), ("burstgpt_3__ChatGPT__api", 0))    # the first 8 of §4.4's order


def _e3_config(slices, merge: bool, normalize=None, c: int = 1) -> dict:
    """E3's raw instance config (bench_e1 with the overrides of measurement 4, design/sim_spec_ms4.md §4.3) for the
    borrowers `slices` (index into E3_SLICES: borrower id b<ii>) at alignment c."""
    from sublet.drivers.run import instance_config
    from sublet.experiments.e1 import MENU
    ov = copy.deepcopy(MENU)
    bor = {"model": "series", "list": [{"id": f"b{i:02d}", "series": E3_SLICES[i][0], "week_index": E3_SLICES[i][1],
                                        "tier": "M", "region": "europe"} for i in slices],
           "own_capacity_quantile": 75, "smoothing_min": 15, "market_tightness": 0.5, "merge": bool(merge)}
    if normalize is not None:
        bor["normalize"] = normalize
    ov.update({"time.horizon_min": 1440, "regions.list": ["europe"], "regions.adjacency": [],
               "llms": [{"id": "M", "catalog": "maas_a10", "entry": "M", "kappa_mult": 1.0}], "units.per_replica": 8,
               "borrowers": bor})
    cfg = instance_config({"instance": "bench_e1.json", "overrides": ov})
    cfg["seed"] = int(c)
    return cfg


def _e2_config(series: str) -> dict:
    from sublet.drivers.run import instance_config
    from sublet.experiments import e2
    cfg = instance_config(e2.run_spec("a1:A100-SXM4-80GB", series, 0, 1.0, 1))
    cfg["seed"] = 1
    return cfg


def _e10b_config(series: str) -> dict:
    from sublet.experiments import e10
    return e10.base_config(series)


def _with_none(cfg: dict) -> dict:
    cfg = copy.deepcopy(cfg)
    cfg["borrowers"]["normalize"] = "none"
    return cfg


SERIES_CONFIGS = {"e2_azure2024_conv": lambda: _e2_config("azure2024_conv"),
                  "e2_burstgpt_1": lambda: _e2_config("burstgpt_1"),
                  "e10b_azure2024_code": lambda: _e10b_config("azure2024_code"),
                  "e3_b8_shared": lambda: _e3_config(range(8), True),
                  "e3_b8_siloed": lambda: _e3_config(range(8), False)}


@pytest.mark.needs_a12
@pytest.mark.parametrize("case", list(SERIES_CONFIGS))
def test_c24_none_leaves_the_series_configs_unchanged(case):
    """"none" and an absent key: the same resolved config (without the key), config_hash and instance_hash; E3's
    config is the one of measurement 4 (its recorded overrides), and E2's base instance has the hash that
    out/e2/manifest.json records from the MS3 runs at commit f10237b."""
    cfg = SERIES_CONFIGS[case]()
    assert cfg["borrowers"]["model"] == "series" and "normalize" not in cfg["borrowers"]
    a, b = load_config(cfg), load_config(_with_none(cfg))
    assert a == b and "normalize" not in a["borrowers"] and config_hash(a) == config_hash(b)
    ia, ib = build_instance(cfg), build_instance(_with_none(cfg))
    assert instance_hash(ia) == instance_hash(ib) and config_hash(ia.config) == config_hash(ib.config)
    assert all(set(v) == {"llm", "C0_loads", "peak_loads"} for v in ia.borrower_stats.values())
    if case.startswith("e3_"):
        rec = json.loads(E3_SIZES.read_text())["overrides"]["shared" if case.endswith("shared") else "siloed"]
        assert rec["borrowers"] == cfg["borrowers"] and rec["units.per_replica"] == 8
    if case.startswith("e2_"):
        man = json.loads((OUT / "e2" / "manifest.json").read_text())
        series = case[len("e2_"):]
        assert instance_hash(ia) == man["instance_hashes"]["e2:cell:lender=a1.A100-SXM4-80GB:H=0:mu=1:c=1"][series]


def _raw_overflow(inst, bid: str):
    """(overflow per minute in replica loads before Gamma, C0, peak of the smoothed series, LLM index) of a series
    borrower, recomputed from the series as tests/test_ms1_additions.py::test_borrower_stats does."""
    from sublet.traces import borrowers as tb
    b = inst.config["borrowers"]
    x = next(v for v in b["list"] if v["id"] == bid)
    sm, q = b["smoothing_min"], b["own_capacity_quantile"]
    i = np.arange(-(sm - 1), inst.grid.horizon_min, dtype=np.int64)
    j = {L.tier: k for k, L in enumerate(inst.llms)}[x["tier"]]
    L = inst.llms[j]
    w = tb.weighted(tb.load_series(x["series"]), L.w_in)
    xs = np.lib.stride_tricks.sliding_window_view(w[((x["week_index"] or 0) * 10080 + i) % len(w)], sm).mean(axis=1)
    C0 = float(np.percentile(xs, q))
    return np.maximum(xs - C0, 0.0) / L.kappa_wtok_per_min, C0, float(xs.max()), j


@pytest.mark.needs_a12
def test_c24_mean_equalizes_the_borrowers():
    """"mean" on E3's Azure conversation and code slices (raw overflow means apart by more than 1.5x): with merge
    false two clients whose demand means agree to 1e-9 (relative), each Gamma; with merge true one client equal to
    their sum (1e-12), with one Gamma, the same in both builds, solved on the sum of the normalized overflows
    (recomputed from the series); borrower_stats record the factor 1 / mean and scale C0 and the peak by it."""
    cfg_s, cfg_m = _e3_config((0, 1), False, "mean"), _e3_config((0, 1), True, "mean")
    assert load_config(cfg_s)["borrowers"]["normalize"] == "mean"
    split, merged, raw = build_instance(cfg_s), build_instance(cfg_m), build_instance(_e3_config((0, 1), False))
    assert split.clients.borrowers == (("b00",), ("b01",)) and merged.clients.borrowers == (("b00", "b01"),)
    m_raw = [float(np.mean(d)) for d in raw.clients.demand]
    assert max(m_raw) > 1.5 * min(m_raw)                                     # two borrowers of different sizes
    gam = [[n for n in x.notes if "Gamma =" in n] for x in (split, merged)]
    assert len(gam[0]) == 1 and gam[0] == gam[1], gam
    # the oracle: Gamma = tightness x supply / peak of the summed GPU overflow, each overflow scaled to mean 1
    supply = float(sum(s.capacity_gpus for s in split.sites if s.kind == "layer"))
    rec = {bid: _raw_overflow(split, bid) for bid in ("b00", "b01")}
    norm = {bid: y / y.mean() for bid, (y, _, _, _) in rec.items()}
    g = split.llms[0].g
    G = split.config["borrowers"]["market_tightness"] * supply / float((g * sum(norm.values())).max())
    fast = split.grid.fast_min
    for c, bid in enumerate(("b00", "b01")):
        want = (G * norm[bid]).reshape(-1, fast).mean(axis=1)
        np.testing.assert_allclose(split.clients.demand[c], want, rtol=1e-12, atol=1e-12 * G)
        y, C0, peak, j = rec[bid]
        st = split.borrower_stats[bid]
        kap = split.llms[j].kappa_wtok_per_min
        assert st["normalize_factor"] == pytest.approx(1.0 / y.mean(), rel=1e-12)
        assert st["C0_loads"] == pytest.approx(st["normalize_factor"] * G * C0 / kap, rel=1e-12)
        assert st["peak_loads"] == pytest.approx(st["normalize_factor"] * G * peak / kap, rel=1e-12)
        assert merged.borrower_stats[bid] == pytest.approx(st, rel=1e-12)
    means = [float(np.mean(d)) for d in split.clients.demand]
    assert abs(means[0] - means[1]) <= 1e-9 * max(means) and means[0] == pytest.approx(G, rel=1e-9)
    np.testing.assert_allclose(merged.clients.demand[0], split.clients.demand[0] + split.clients.demand[1],
                               rtol=1e-12, atol=1e-12 * G)
    assert instance_hash(split) != instance_hash(raw)


@pytest.mark.needs_a12
@pytest.mark.parametrize("merge", [False, True])
def test_c24_borrower_without_overflow(merge):
    """b03 (burstgpt_1 ChatGPT api, week 0) has no overflow on the day: under "mean" it keeps zero; siloed, its
    client is dropped with the builder's note, as without the key; merged, the client of b00 and b03 equals b00's
    normalized overflow (mean Gamma). Its borrower_stats entry has normalize_factor None and the raw C0 and peak."""
    inst = build_instance(_e3_config((0, 3), merge, "mean"))
    none = build_instance(_e3_config((0, 3), merge))
    drop = "client ['b03'] has no overflow and is dropped"
    assert (drop in inst.notes) == (drop in none.notes) == (not merge)
    assert any("borrowers without overflow: ['b03']" in n for n in inst.notes)
    assert inst.clients.borrowers == ((("b00",),) if not merge else (("b00", "b03"),))
    G = float(np.mean(inst.clients.demand[0]))                      # b00's normalized overflow has mean 1
    gam = [n for n in inst.notes if "Gamma =" in n]
    assert len(gam) == 1 and float(gam[0].split("Gamma = ")[1].split()[0]) == pytest.approx(G, rel=1e-5)
    st, st0 = inst.borrower_stats["b03"], none.borrower_stats["b03"]
    assert st["normalize_factor"] is None and (st["C0_loads"], st["peak_loads"]) == (st0["C0_loads"],
                                                                                      st0["peak_loads"])
    assert inst.borrower_stats["b00"]["normalize_factor"] > 0


def test_c24_other_borrower_models_reject_the_key():
    """The key belongs to the series model: the explicit and the regional model raise ConfigError on it (as on any
    unknown key)."""
    cfg = toy_config()
    assert cfg["borrowers"]["model"] == "explicit"
    cfg["borrowers"]["normalize"] = "none"
    with pytest.raises(ConfigError, match=r"borrowers: unknown key\(s\) \['normalize'\]"):
        load_config(cfg)
    cfg = toy_config()
    cfg["borrowers"] = {"model": "regional", "normalize": "mean"}
    with pytest.raises(ConfigError, match=r"borrowers: unknown key\(s\) \['normalize'\]"):
        load_config(cfg)


@pytest.mark.needs_a12
def test_c24_series_model_values():
    """The series model takes "none" and "mean" only."""
    for bad in ("Mean", "max", None, 1):
        cfg = _e3_config((0, 1), True)
        cfg["borrowers"]["normalize"] = bad
        with pytest.raises(ConfigError, match="borrowers.normalize"):
            load_config(cfg)
    regional = load_json(CONFIGS / "example_1day.json")
    assert regional["borrowers"]["model"] == "regional"
    regional["borrowers"]["normalize"] = "mean"
    with pytest.raises(ConfigError, match="unknown key"):
        load_config(regional)


# ---------------------------------------------------------------- C25
SHA = "0123456789abcdef0123456789abcdef01234567"


def _fake_git(tmp, worktree: bool, packed: bool, detached: bool = False) -> Path:
    """A repository folder whose .git is a folder or, for a worktree, a file naming its gitdir; returns the folder."""
    repo = tmp / "repo"
    common = tmp / "main" / ".git" if worktree else repo / ".git"
    (common / "refs" / "heads").mkdir(parents=True)
    if packed:
        (common / "packed-refs").write_text(f"# pack-refs with: peeled fully-peeled sorted\n{SHA} refs/heads/b\n")
    else:
        (common / "refs" / "heads" / "b").write_text(SHA + "\n")
    head = SHA + "\n" if detached else "ref: refs/heads/b\n"
    if worktree:
        gd = common / "worktrees" / "b"
        gd.mkdir(parents=True)
        (gd / "HEAD").write_text(head)
        (gd / "commondir").write_text("../..\n")
        repo.mkdir()
        (repo / ".git").write_text(f"gitdir: {gd}\n")
    else:
        (common / "HEAD").write_text(head)
    return repo


@pytest.mark.parametrize("worktree", [False, True])
@pytest.mark.parametrize("packed", [False, True])
def test_c25_git_revision_folder_and_worktree(tmp_path, monkeypatch, worktree, packed):
    import sublet.paths
    from sublet.metrics import _git_revision
    monkeypatch.setattr(sublet.paths, "REPO", _fake_git(tmp_path, worktree, packed))
    assert _git_revision() == SHA
    assert mc.git_revision() == SHA


def test_c25_git_revision_detached_and_broken(tmp_path, monkeypatch):
    import sublet.paths
    from sublet.metrics import _git_revision
    monkeypatch.setattr(sublet.paths, "REPO", _fake_git(tmp_path / "a", True, False, detached=True))
    assert _git_revision() == SHA
    bad = tmp_path / "b"
    bad.mkdir()
    (bad / ".git").write_text("not a gitdir line\n")
    monkeypatch.setattr(sublet.paths, "REPO", bad)
    assert _git_revision() is None


def test_c25_git_revision_of_this_checkout():
    from sublet.metrics import _git_revision
    from sublet.paths import REPO
    if shutil.which("git") is None:
        pytest.skip("git not available")
    head = subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"], capture_output=True, text=True)
    if head.returncode != 0:
        pytest.skip("not a git checkout")
    assert _git_revision() == head.stdout.strip()


# ---------------------------------------------------------------- C26: the redundancy rule's wider set
# Hand-made observations on configs/toy.json (as tests/test_redundancy.py): 'short' with H = 2 min, load times 300 s at
# L0 (group g0) and L1 (g1), 600 s at P, so lambda_min = 300 s and a 'short' lease past tau is exposed. The view's
# clients are replaced by two clients of the LLM with a hand-made delta, so that the X3 pool of a slot at L0 is the
# intersection of their feasible sites (the pool of E5's L columns at a2:c06, sim_spec_ms4 §2.3 C26).
INF_C26 = float("inf")


def _c26_setup(delta, overrides=None):
    import dataclasses
    from fixtures import site_index, toy_instance
    from sublet.instance import public_view
    ov = {"contracts.0.H_min": 2, "lenders.0.lam_s": 300.0, "lenders.1.lam_s": 300.0, "lenders.2.lam_s": 600.0,
          **(overrides or {})}
    inst = toy_instance(ov)
    view = public_view(inst, "I1")
    d = np.asarray(delta, dtype=np.float64)
    view = dataclasses.replace(view, client_llm=np.zeros(len(d), dtype=np.int64), client_region=("r0",) * len(d),
                               client_delta_usd_per_h=d)
    ids = [c.id for c in inst.contracts]
    sites = (site_index(inst, "L0"), site_index(inst, "L1"), site_index(inst, "P"))
    assert sites == (0, 1, 2) and d.shape == (2, inst.m)        # delta's columns are L0, L1, P
    return (inst, view, *sites, ids.index("short"), ids.index("long"))


def _c26_lease(lid, site, k, start=0):
    from sublet.types import LeaseView
    return LeaseView(id=lid, site=site, contract=k, gpus=1, start_slot=start, start_min=start * 5,
                     prepaid_end_min=start * 5 + 10, announce_slot=None, death_min=None, replicas=(lid * 10,))


def _c26_step(rule, inst, view, t, leases, slots):
    from sublet.algos.common import LeaseBook
    from sublet.types import ReplicaView, SlowObs
    n = len(view.client_llm)
    reps = [ReplicaView(id=L.id * 10, lease_id=L.id, llm=0, state="warm", load_start_min=0, warm_fast=0,
                        admission=1.0, drain_min=None) for L in leases]
    obs = SlowObs(t=t, minute=t * 5, demand=np.ones((n, inst.grid.phi)), leases={L.id: L for L in leases},
                  replicas={r.id: r for r in reps}, notices=[], ended=[], results=[], site_announced=None,
                  served_prev=np.zeros((inst.J, inst.m)), fallback_prev=np.zeros(n), cost_so_far=0.0)
    book = LeaseBook()
    rule.on_results(book.begin(obs))
    rule.step(obs, book, slots)
    return [a for a in book.assemble(obs, view) if getattr(a, "tag", None) == "spare"]


def _c26_slot(l0, k, pool, lid=100, iota=0):
    from types import SimpleNamespace
    return SimpleNamespace(key=(l0, 0, k, iota), lease=lid, ptr=l0, pool=tuple(pool))


def test_c26_one_group_pool_spare_from_the_wider_set():
    """C26 (algos/redundancy.py, M40): client 0 is feasible at L0 and L1, client 1 at L0 only; both are on, so the X3
    pool of a 'short' slot at L0 is (L0,), one correlation group, and the MS2 search (choose_spare over the pool) has
    no site. The wider set of the stranded clients {0, 1} outside the pool is (L1,) (P has no finite delta), in group
    g1: 'always2' buys the spare there with the non-exposed 'long' (60 H = 600 s >= 300 s), counted in buys and
    buys_wide; no_site stays 0."""
    from sublet.algos.redundancy import RedundancyRule, choose_spare, stranded_clients, wide_sites, x3_pool
    from sublet.types import Buy
    inst, view, l0, l1, lp, short, long_ = _c26_setup([[0.0, 0.0, INF_C26], [0.0, INF_C26, INF_C26]])
    rule = RedundancyRule(view, mode="always2")
    key = (l0, 0, short, 0)
    D = np.ones(2)
    pool = x3_pool(view, key, D, zeta=2.0, site_perm=rule.pi, ptr=l0, L=rule.L)
    assert pool == (l0,) and len({view.sites[l].group for l in pool}) == 1
    assert stranded_clients(view, key, D) == [0, 1] and stranded_clients(view, key, np.array([0.0, 1.0])) == [1]
    assert stranded_clients(view, key, np.zeros(2)) == [0, 1]           # none on: all candidates (x3_pool's rule)
    assert wide_sites(view, [0, 1], rule.pi, exclude=pool) == (l1,) and wide_sites(view, [1], rule.pi, pool) == ()
    assert choose_spare(view, 0, pool, view.sites[l0].group, 300.0, rule.L, rule.C, rule.pi) is None
    spares = _c26_step(rule, inst, view, 3, [_c26_lease(100, l0, short)], [_c26_slot(l0, short, pool)])
    assert spares == [Buy(l1, long_, 0, 1, tag="spare", admission=1.0)]
    rep = rule.report()
    assert (rep["buys"], rep["buys_wide"], rep["no_site"], rep["n_exp"][3]) == (1, 1, 0, 1)
    assert rule.spare[(0, (l0,))]["site"] == l1


@pytest.mark.parametrize("case", ["empty", "same_group", "capacity"])
def test_c26_no_site_when_the_wider_set_has_none(case):
    """C26: no spare and no_site 1 when the wider set has no site either: no stranded client is feasible outside the
    pool ('empty'); the only wider-set site is in the majority group (L1 moved to g0, 'same_group'); or it fails
    can_buy (L1's 4 GPUs held by own leases outside the slots, 'capacity'). buys and buys_wide stay 0."""
    from sublet.algos.redundancy import RedundancyRule
    delta = [[0.0, 0.0, INF_C26], [0.0, INF_C26, INF_C26]]
    if case == "empty":
        delta = [[0.0, INF_C26, INF_C26], [0.0, INF_C26, INF_C26]]
    inst, view, l0, l1, lp, short, long_ = _c26_setup(delta, {"lenders.1.group": "g0"} if case == "same_group"
                                                       else None)
    assert (view.sites[l1].group == view.sites[l0].group) == (case == "same_group")
    rule = RedundancyRule(view, mode="always2")
    leases = [_c26_lease(100, l0, short)]
    if case == "capacity":
        leases += [_c26_lease(200 + i, l1, short) for i in range(int(view.sites[l1].capacity_gpus))]
    spares = _c26_step(rule, inst, view, 3, leases, [_c26_slot(l0, short, (l0,))])
    assert spares == []
    rep = rule.report()
    assert (rep["buys"], rep["buys_wide"], rep["no_site"], rep["n_exp"][3]) == (0, 0, 1, 1)


@pytest.mark.parametrize("mode,n,want", [("always2", 1, 1), ("rule", 33, 1), ("rule", 32, 0), ("off", 33, 0)])
def test_c26_pool_search_unchanged(monkeypatch, mode, n, want):
    """C26 is a no-op where the pool search succeeds or no spare is needed: on the toy's own client (feasible
    everywhere) with the pool (L0, L1) of tests/test_redundancy.py, the spare goes to L1 with 'long' through the pool
    (the actions and counts of test_modes and test_spare_threshold), the wider set is never computed (its helpers
    raise if called), and the report has the MS2 keys plus buys_wide = 0."""
    import sublet.algos.redundancy as R
    from fixtures import site_index, toy_instance
    from sublet.instance import public_view
    from sublet.types import Buy

    def boom(*a, **k):
        raise AssertionError("C26's wider set computed although the pool search succeeded or no spare was needed")
    monkeypatch.setattr(R, "stranded_clients", boom)
    monkeypatch.setattr(R, "wide_sites", boom)
    inst = toy_instance({"contracts.0.H_min": 2, "lenders.0.lam_s": 300.0, "lenders.1.lam_s": 300.0,
                         "lenders.2.lam_s": 600.0})
    view = public_view(inst, "I1")
    ids = [c.id for c in inst.contracts]
    l0, l1, short, long_ = site_index(inst, "L0"), site_index(inst, "L1"), ids.index("short"), ids.index("long")
    rule = R.RedundancyRule(view, mode=mode)
    leases = [_c26_lease(100 + i, l0, short) for i in range(n)]
    slots = [_c26_slot(l0, short, (l0, l1), lid=100 + i, iota=i) for i in range(n)]
    spares = _c26_step(rule, inst, view, 3, leases, slots)
    assert spares == [Buy(l1, long_, 0, 1, tag="spare", admission=1.0)] * want
    rep = rule.report()
    ms2_keys = {"mode", "nu_per_day", "zeta", "buys", "releases", "refused", "deaths", "no_site", "n_exp_total",
                "n_exp_max", "spare_slot_groups", "groups_with_spare", "n_exp", "n_groups"}
    assert set(rep) == ms2_keys | {"buys_wide"}
    assert (rep["buys"], rep["buys_wide"], rep["no_site"], rep["n_exp"][3]) == (want, 0, 0, n)
