"""Tests of the registrations of the MS7 supplementary figures (design/ms7/w_spec.md §4, unit W-G4; registration of
unit W-G4-0; change C58): figs/style.py's MS7_SUPP_KEYS, MS7_KEY_OF_TAG, SUPP_POLICIES_MS7 with its writer blocks and
the environment factors 'demand' and 'calibration', and figs/rebuild.py's entries of MS7_SUPP_SCRIPTS. Quick; every
file is written under pytest's tmp_path.

- Keys: the 32 keys as built (label, color, marker, fill, group, family, edge color), each note naming C58 and its tag;
  each triple and each label no other key's; no (color, marker) pair that tests/test_ms3_additions.py or
  test_ms4_additions.py pins; appended after MS7_KEYS in this order; no design name in a label; every label sets at
  TICK_PT with the registry's fonts (style.save passes: no missing glyph, no overlap).
- MS7_KEY_OF_TAG: each tag maps to its own key; with figs/supp/ms5b_e7_lib.KEY_OF_TAG every tag that the registration's
  parts run (e7c's gate and lag tags, e7o's fifteen, e7r's MS7, existing, grid-free tuned tags, X3's tags) has a key.
- Sets: the eight figures in block order, each supplementary at a size that the ink tests cover (registered again only
  at the same size), named by no other map; each set within the registry, in legend order, passing
  check_policies with unique labels and no (marker, fill) twice, without a legacy key; figure_sets() holds the map and
  check_legacy() passes; the tuned settings beside the as-built baselines and Sublet have no (marker, fill) twice; each
  writer block of style.py holds the lines of its own figures only.
- Rebuild: the eight entries listed from MS7_SUPP_SCRIPTS while their scripts are missing (supplementary, module from
  the path; PDF, extract and preview; run inputs MS7_SUPP_RUN_INPUTS), pending in a tree without the run outputs (not
  missing, not run, not failed; a rebuild run compares nothing), ordinary once the run outputs are there and once an
  output exists; a script at its path gives the entry its TABLES and RUN_INPUTS; a script away from its path, without
  RUN_INPUTS, or with run inputs that are no MS7 run output is a list error.
"""
from __future__ import annotations

import re
import types
from pathlib import Path

import pytest

from fixtures import SIM

from figs import rebuild as rb
from figs import style as st

REPO = SIM.parents[1]
O, SK, VM, G, Y, K = "#E69F00", "#56B4E9", "#D55E00", "#009E73", "#F0E442", "#000000"
# key: (label, color, marker, fill, group, family, edge color), in registry order
WANT = {
    "bl1_gp_lag": ("Greedy + guard, inner lagged", O, "s", "filled", "guarded", "bl1", None),
    "bl1n_lag": ("Greedy + notice layer, lagged", O, "D", "filled", "ours", "bl1", None),
    "bl5n_lag": ("RetroRenting + notice layer, lagged", SK, "D", "open", "ours", "bl5", None),
    "bl5_tau60_lag": (r"RetroRenting, $\tau\geq1$ h, lagged", SK, "^", "open", "baseline", "bl5", None),
    "bl1_bo_lag": ("Greedy, back-off, lagged", O, "<", "filled", "baseline", "bl1", None),
    "bl2_lag": ("Per-borrower ski rental, lagged", VM, "v", "open", "baseline", "bl2", None),
    "bl3_0_lag": (r"SpotHedge-style, $N_{\mathrm{Extra}}=0$, lagged", G, "p", "open", "baseline", "bl3", None),
    "bl4_lag": ("CoCaR-style, lagged", Y, "P", "open", "baseline", "bl4", K),
    "bl5_cur_c2": (r"RetroRenting-style, $\bar{k}$ contract", SK, "p", "open", "baseline", "bl5", None),
    "bl1_c2": (r"Greedy renting, $\bar{k}$ contract", O, "<", "open", "baseline", "bl1", None),
    "bl2_c2": (r"Per-borrower ski rental, $\bar{k}$ contract", VM, "s", "filled", "baseline", "bl2", None),
    "bl3_0_c2": (r"SpotHedge-style, $N_{\mathrm{Extra}}=0$, $\bar{k}$ contract", G, "^", "filled", "baseline", "bl3",
                 None),
    "bl4_c2": (r"CoCaR-style, $\bar{k}$ contract", Y, "v", "open", "baseline", "bl4", K),
    "bl3_1": (r"SpotHedge-style, $N_{\mathrm{Extra}}=1$ per pool", G, ">", "filled", "baseline", "bl3", None),
    "bl3_2": (r"SpotHedge-style, $N_{\mathrm{Extra}}=2$ per pool", G, ">", "open", "baseline", "bl3", None),
    "bl3_1_llm": (r"SpotHedge-style, $N_{\mathrm{Extra}}=1$ per LLM", G, "h", "filled", "baseline", "bl3", None),
    "bl3_2_llm": (r"SpotHedge-style, $N_{\mathrm{Extra}}=2$ per LLM", G, "h", "open", "baseline", "bl3", None),
    "bl5_t": ("RetroRenting-style, tuned (trace)", SK, "^", "filled", "baseline", "bl5", None),
    "bl5_w": ("RetroRenting-style, tuned (worst case)", SK, "v", "open", "baseline", "bl5", None),
    "bl1_t": ("Greedy renting, tuned (trace)", O, "d", "filled", "baseline", "bl1", None),
    "bl1_w": ("Greedy renting, tuned (worst case)", O, "d", "open", "baseline", "bl1", None),
    "bl2_t": ("Per-borrower ski rental, tuned (trace)", VM, ">", "filled", "baseline", "bl2", None),
    "bl2_w": ("Per-borrower ski rental, tuned (worst case)", VM, ">", "open", "baseline", "bl2", None),
    "bl3_t": ("SpotHedge-style, tuned (trace)", G, "<", "filled", "baseline", "bl3", None),
    "bl3_w": ("SpotHedge-style, tuned (worst case)", G, "<", "open", "baseline", "bl3", None),
    "bl4_t": ("CoCaR-style, tuned (trace)", Y, "h", "filled", "baseline", "bl4", K),
    "bl4_w": ("CoCaR-style, tuned (worst case)", Y, "h", "open", "baseline", "bl4", K),
    "mpc_built": ("MPC, as built", Y, "s", "filled", "baseline", "bl4", K),
    "mpc_w": ("MPC, tuned (worst case)", Y, "D", "open", "baseline", "bl4", K),
    "mpc_oracle": ("MPC, oracle forecast", K, "d", "filled", "benchmark", "benchmarks", None),
}
# the (color, marker) pairs that tests/test_ms3_additions.py and test_ms4_additions.py pin (C41's PINNED)
PINNED = ("a3_rot", "cold", "psi_01", "psi_03", "psi_05", "a6_red_off", "a6_always2", "bl3_n0", "bl3_n1")
FIGURES = {"sf_lag_v2": ("W2", 2.4), "sf_oos": ("W2", 2.4), "sf_bl_ms7": ("W2", 2.4), "sf_stress_ms7": ("W2", 2.5),
           "sf_s1_v2": ("W2", 2.5), "sf_e5_v2": ("W2", 2.5), "sf_e8_v2": ("W1", 2.2), "sf_e9_v2": ("W2", 2.2)}
BLOCKS = {"A": ("sf_lag_v2", "sf_oos"), "B": ("sf_bl_ms7", "sf_stress_ms7"),
          "C": ("sf_s1_v2", "sf_e5_v2", "sf_e8_v2", "sf_e9_v2")}
# the tuned settings of X4 beside the as-built baselines and Sublet (a set that block B may draw in place of its own)
TUNED = ("sublet_v2", "bl5_cur", "bl1", "bl2", "bl3_0", "bl4", "mpc", "bl5_t", "bl5_w", "bl1_t", "bl1_w", "bl2_t",
         "bl2_w", "bl3_t", "bl3_w", "bl4_t", "bl4_w", "mpc_built", "mpc_w")
DESIGN_NAME = re.compile(r"\b(BL\d|A\d|X\d|H\d|L-[a-z]|MS\d|T0)|\bc2\b|-(T|W)\b")


@pytest.fixture()
def registry_without_test_figures(monkeypatch):
    """rebuild.entries() needs a script for every figure of style.FIGURES; the test-only figures that earlier test
    modules register ('test_*') are left out for the test (as tests/test_rebuild.py does)."""
    for k in [k for k in st.FIGURES if k.startswith("test_")]:
        monkeypatch.delitem(st.FIGURES, k)


def _mf(keys):
    return [(st.POLICIES[k].marker, st.POLICIES[k].fill) for k in keys if st.POLICIES[k].marker is not None]


# ---------------------------------------------------------------- keys
def test_keys_as_built():
    assert st.MS7_SUPP_KEYS == tuple(WANT)
    n = len(WANT)
    order = list(st.POLICIES)
    i = order.index("a9p")                       # MS8: the MS8 keys (st.MS8_SUPP_KEYS) follow these
    assert tuple(order[i + 2:i + 2 + n]) == tuple(WANT) and tuple(order[i:i + 2]) == st.MS7_KEYS == ("a9p", "mpc")
    assert tuple(order[i + 2 + n:]) == st.MS8_SUPP_KEYS
    allowed = {c.upper() for c in st.OKABE_ITO}
    for k, (label, color, marker, fill, group, family, edge) in WANT.items():
        p = st.POLICIES[k]
        assert (p.label, p.color, p.marker, p.fill, p.group, p.family, p.edgecolor, p.linestyle) == \
            (label, color, marker, fill, group, family, edge, "-"), k
        assert (p.linewidth, p.markersize, p.zorder) == (st.LINE_PT, st.MARKER_PT, st.Z_DATA), k
        assert p.color.upper() in allowed and p.fill in st.FILLS and p.group in st.GROUPS, k
        assert p.note.startswith("MS7 C58") and re.search(r"tag \S+ of e7[cr]", p.note), k
        others = [q for q in st.POLICIES.values() if q.key != k]
        assert p.triple not in {q.triple for q in others}, k
        assert p.label not in {q.label for q in others}, k
        for q in PINNED:
            assert (p.color.upper(), p.marker) != (st.POLICIES[q].color.upper(), st.POLICIES[q].marker), (k, q)
        assert not DESIGN_NAME.search(label), (k, label)
        assert "\\ge" not in label.replace("\\geq", ""), k
        # a family's color: the color of the family's as-built key (BL3's MS5b green, the benchmarks' black)
        anchor = {"bl1": "bl1", "bl2": "bl2", "bl3": "bl3_0", "bl4": "bl4", "bl5": "bl5_cur", "benchmarks": "opt"}
        assert p.color == st.POLICIES[anchor[family]].color, k
        if p.color.upper() == Y.upper():
            assert p.edgecolor == K, k                     # yellow markers have a black edge


def test_labels_set_at_nine_points(tmp_path):
    """Every new label, set as a TICK_PT (7-pt) text with the registry's fonts, passes style.save (no missing glyph,
    sizes within [TEXT_MIN_PT, TEXT_MAX_PT] = [7, 7.970] pt, no overlap)."""
    name = "test_ms7_supp_labels"
    st.register_supplementary(name, "W2", 2.5)
    keys = list(WANT)
    for i in range(0, len(keys), 11):
        fig = st.new_figure(name)
        for j, k in enumerate(keys[i:i + 11]):
            fig.text(0.02, 0.95 - 0.085 * j, st.POLICIES[k].label, fontsize=st.TICK_PT, va="top")
        rep = st.save(fig, name, {"keys": keys[i:i + 11]}, pdf_dir=tmp_path / f"p{i}", out_dir=tmp_path / f"o{i}")
        assert (tmp_path / f"p{i}" / f"{name}.pdf").is_file() and rep["outside_page"] == []


def test_key_of_tag_covers_every_tag():
    from sublet.experiments import e5v2, e7c, e7c_tags, e7o, e7r_analysis, e8v2, e9v2, ms7_baselines, s1v2

    from figs.supp.ms5b_e7_lib import KEY_OF_TAG
    m = st.MS7_KEY_OF_TAG
    assert len(set(m.values())) == len(m) and set(m.values()) <= set(st.POLICIES)
    assert set(m.values()) == set(WANT) | {"a9p", "mpc"}
    assert not set(m) & set(KEY_OF_TAG) and not set(m.values()) & set(KEY_OF_TAG.values())
    both = {**KEY_OF_TAG, **m}
    tags = (set(e7c_tags.LAG_TAGS) | set(e7c.GATE_DEFAULT_TAGS) | set(e7c.GATE_LAG_TAGS) | set(e7o.TAGS)
            | set(ms7_baselines.MS7_TAGS) | set(ms7_baselines.EXISTING_EVAL_TAGS) | set(e7r_analysis.TUNED_T)
            | set(e7r_analysis.TUNED_W) | set(s1v2.LOCAL_TAGS) | set(s1v2.W0_TAGS) | set(e5v2.TAGS) | set(e8v2.TAGS)
            | {e8v2.IDENTITY_TAG} | set(e9v2.TAGS))
    assert tags <= set(both), sorted(tags - set(both))
    assert set(e7c_tags.LAG_TAGS) - set(KEY_OF_TAG) == {t for t in m if t.endswith("-lag")}
    for t in m:                                          # every MS7 tag is a tag the registration runs
        assert t in tags, t


# ---------------------------------------------------------------- sets
def test_sets_and_sizes():
    from test_figs_style import _sizes
    assert tuple(st.SUPP_POLICIES_MS7) == tuple(FIGURES)
    assert not set(st.SUPP_POLICIES_MS7) & (set(st.FIGURE_POLICIES) | set(st.SUPP_POLICIES) | set(st.SUPP_POLICIES_MS4)
                                            | set(st.SUPP_POLICIES_MS5) | set(st.SUPP_POLICIES_MS5B))
    for name in FIGURES:            # FIGURES holds the sizes as registered by W-G4-0; a writer may change its own
        spec = st.FIGURES[name]     # (within the sizes that the ink tests cover)
        assert spec.width in st.WIDTHS and not spec.main, name
        assert (spec.width, spec.height_in) in _sizes(), name
        assert st.register_supplementary(name, spec.width, spec.height_in) == spec
        with pytest.raises(st.StyleError, match="already registered"):
            st.register_supplementary(name, spec.width, 2.3)
    for name, keys in {**st.SUPP_POLICIES_MS7, "tuned": TUNED}.items():
        assert len(set(keys)) == len(keys) and set(keys) <= set(st.POLICIES), name
        st.check_policies(keys)
        labels = [st.POLICIES[k].label for k in keys]
        assert len(set(labels)) == len(labels), name
        mf = _mf(keys)
        assert len(set(mf)) == len(mf), (name, mf)
        assert not set(keys) & set(st.LEGACY_KEYS), name
        assert tuple(keys) == tuple(st.legend_order(keys)), name
    assert set(st.figure_sets()) >= set(st.SUPP_POLICIES_MS7)
    st.check_legacy()
    # every new key is drawn by a set or is a tuned setting (TUNED)
    drawn = {k for ks in st.SUPP_POLICIES_MS7.values() for k in ks}
    assert set(WANT) <= drawn | set(TUNED)


def test_environment_factors():
    assert st.env_linestyle("demand", "lagged") == "--" and st.env_linestyle("demand", "revealed") == "-"
    assert st.env_linestyle("calibration", "is") == "--" and st.env_linestyle("calibration", "oos") == "-"
    assert st.ENV_LABELS["demand"] == {"revealed": "Revealed slot", "lagged": "Lagged one slot"}
    assert st.ENV_LABELS["calibration"] == {"oos": "Out of sample", "is": "In sample"}
    kw = st.policy_kwargs("sublet_v2", env=("demand", "lagged"))
    assert kw["linestyle"] == "--" and kw["label"] == "Sublet"


def test_writer_blocks():
    """Each writer block ('# W-G4 block X (names)' ... '# end W-G4 block X') sets and sizes its own figures only, and no
    line outside the blocks sets a figure of SUPP_POLICIES_MS7; MS8: likewise each MS8 writer unit's block of
    SUPP_POLICIES_MS8 ('# MS8 unit <U> block (<name>; ...)' ... '# end MS8 unit <U> block')."""
    src = (SIM / "figs" / "style.py").read_text(encoding="utf-8")
    found = {}
    for m in re.finditer(r"^# W-G4 block ([A-Z]) \(([^)]*)\)\n(.*?)^# end W-G4 block \1\n", src, re.MULTILINE | re.DOTALL):
        names = tuple(s.strip() for s in m.group(2).split(","))
        body = m.group(3)
        found[m.group(1)] = names
        assert set(re.findall(r'SUPP_POLICIES_MS7\["(\w+)"\]', body)) == set(names), m.group(1)
        assert set(re.findall(r'register_supplementary\("(\w+)"', body)) == set(names), m.group(1)
        src = src.replace(m.group(0), "")
    assert found == BLOCKS
    # MS8 (design/ms8/plan.md W): the writer units' blocks of SUPP_POLICIES_MS8 ('# MS8 unit <U> block (<name>; ...)'
    # ... '# end MS8 unit <U> block'), each setting and sizing its own figure only
    for m in re.finditer(r"^# MS8 unit (\w+) block \((\w+)[;)][^\n]*\n(.*?)^# end MS8 unit \1 block\n", src,
                         re.MULTILINE | re.DOTALL):
        body = m.group(3)
        assert set(re.findall(r'SUPP_POLICIES_MS8\["(\w+)"\]', body)) == {m.group(2)}, m.group(1)
        assert set(re.findall(r'register_supplementary\("(\w+)"', body)) == {m.group(2)}, m.group(1)
        assert not re.search(r'SUPP_POLICIES_MS7\["', body), m.group(1)
        src = src.replace(m.group(0), "")
    assert not re.search(r'SUPP_POLICIES_MS7\["', src) and not re.search(r'register_supplementary\("sf_', src)
    assert not re.search(r'SUPP_POLICIES_MS8\["', src)


# ---------------------------------------------------------------- rebuild
def test_rebuild_lists_the_supplementary_figures_pending(registry_without_test_figures, tmp_path):
    ents = rb.entries()
    by = {e.name: e for e in ents}
    assert set(rb.MS7_SUPP_SCRIPTS) == set(FIGURES) == set(rb.MS7_SUPP_RUN_INPUTS)
    supp = [e.script for e in ents if e.kind == "supp"]
    assert supp == sorted(supp)
    for name, script in rb.MS7_SUPP_SCRIPTS.items():
        e = by[name]
        assert script == f"code/sim/figs/supp/{name}.py" and e.script == script, name
        assert (e.kind, e.module, e.extract) == ("supp", f"figs.supp.{name}", f"code/sim/out/figs/{name}.json"), name
        assert e.outputs[:3] == (f"paper/supplement/figures/{name}.pdf", f"code/sim/out/figs/{name}.json",
                                 f"code/sim/out/figs/{name}.png"), name
        if not (REPO / script).is_file():
            assert e.outputs[3:] == () and e.run_inputs == rb.MS7_SUPP_RUN_INPUTS[name], name
        else:
            mod = rb._import(e.module)
            assert e.run_inputs == tuple(mod.RUN_INPUTS), name
            assert e.outputs[3:] == tuple(f"paper/supplement/tables/{t}" for t in rb._tables_of(mod)), name
        assert rb.pending_inputs(e) == e.run_inputs and any(p.startswith(rb.MS7_RUN_DIRS) for p in e.run_inputs)
        # in this checkout: pending while its run outputs are missing and none of its outputs exists
        want = not any((REPO / p).is_file() for p in e.outputs) and \
            any(not (REPO / p).is_file() for p in e.run_inputs)
        assert rb.is_pending(REPO, e) == want, name
    ours = [by[n] for n in FIGURES]
    # a tree without the MS7 run outputs: pending, not missing, not run, not a failure
    root, work = tmp_path / "root", tmp_path / "work"
    root.mkdir()
    work.mkdir()
    cov = rb.coverage(root, ours)
    assert cov["pending"] == list(FIGURES) and cov["missing"] == []
    rows = rb.run_entries(rb.Run(root, work, True, None, True), ents, ours)
    assert [r["status"] for r in rows] == ["pending"] * len(ours) and not (work / "_time").exists()
    assert all(r["note"].startswith("pending: the MS7 run outputs code/sim/out/") for r in rows)
    t = rb.totals(rows, [], {})
    assert t["failed"] == [] and t["pending"] == list(FIGURES)
    # once the run outputs are in the tree, ordinary entries: their outputs are missing until the final render
    for e in ours:
        for rel in e.run_inputs:
            (root / rel).parent.mkdir(parents=True, exist_ok=True)
            (root / rel).write_text("{}")
    assert not any(rb.is_pending(root, e) for e in ours)
    assert rb.coverage(root, ours)["missing"] == sorted(p for e in ours for p in e.outputs)
    # an output that exists (a final render) ends the pending state, whatever the run outputs
    root2 = tmp_path / "root2"
    (root2 / "paper/supplement/figures").mkdir(parents=True)
    (root2 / "paper/supplement/figures/sf_oos.pdf").write_bytes(b"x")
    assert not rb.is_pending(root2, by["sf_oos"]) and rb.is_pending(root2, by["sf_lag_v2"])
    # a rebuild run: the pending entries are neither run nor compared (no output 'not written')
    rec_root, rec_work = tmp_path / "rroot", tmp_path / "rwork"
    rec_root.mkdir()
    code, rec, _ = rb.rebuild(rec_root, rec_work, check=True, only=r"^sf_(lag_v2|e9_v2)$", keep=False)
    assert [s["status"] for s in rec["scripts"]] == ["pending", "pending"] and rec["outputs"] == []
    assert rec["totals"]["not_written"] == [] and sorted(rec["totals"]["pending"]) == ["sf_e9_v2", "sf_lag_v2"]
    assert all(x["pending"] for x in rec["entries"] if x["name"] in ("sf_lag_v2", "sf_e9_v2"))


def test_rebuild_refuses_a_reduced_extract(registry_without_test_figures, tmp_path):
    """C58 (review of W-G4): an MS7 entry's extract that records meta.reduced is a list error of the coverage, whether
    or not the run outputs are in the tree; a full-run extract and the frozen entries are not affected."""
    import json
    ents = rb.entries()
    by = {e.name: e for e in ents}
    ours = [by[n] for n in FIGURES] + [by[n] for n in rb.MS7_PENDING if n in by]
    root = tmp_path / "root"
    for e, reduced in ((by["sf_lag_v2"], True), (by["sf_oos"], False)):
        (root / e.extract).parent.mkdir(parents=True, exist_ok=True)
        (root / e.extract).write_text(json.dumps({"meta": {"reduced": reduced}}))
    cov = rb.coverage(root, ours)
    assert len(cov["errors"]) == 1 and not cov["ok"]
    assert cov["errors"][0].startswith("code/sim/out/figs/sf_lag_v2.json: the extract of a reduced (smoke) run")
    assert rb.reduced_extracts(root, [e for e in ents if not rb.pending_inputs(e)]) == []
    ok, why = rb.verdict({"coverage": cov, "totals": rb.totals([], [], {}), "heights": {}, "hand_set": [],
                          "unexpected": []})
    assert not ok and why[0].startswith("list errors:")


def _with_script(monkeypatch, module: str, script: str, **attrs):
    """rebuild's list with one more supplementary script `script` (module `module`, attributes `attrs`), any real
    script of that NAME left out."""
    fake = types.SimpleNamespace(**attrs)
    real = [s for s in rb.figure_scripts() if s[1] != module and Path(s[2]).stem != attrs.get("NAME")]
    monkeypatch.setattr(rb, "figure_scripts", lambda: real + [("supp", module, script)])
    imp = rb._import
    monkeypatch.setattr(rb, "_import", lambda m: fake if m == module else imp(m))


def test_rebuild_reads_the_script_once_it_exists(registry_without_test_figures, monkeypatch, tmp_path):
    ri = ("code/sim/out/e7c/analysis.json", "code/sim/out/sublet_v2/main/summary.json")
    _with_script(monkeypatch, "figs.supp.sf_lag_v2", "code/sim/figs/supp/sf_lag_v2.py", NAME="sf_lag_v2",
                 TABLES=("e7c_lag_weeks.tex", "e7c_lag_runs.csv"), RUN_INPUTS=ri)
    e = {x.name: x for x in rb.entries()}["sf_lag_v2"]
    assert e.run_inputs == ri and rb.pending_inputs(e) == ri
    assert e.outputs[3:] == ("paper/supplement/tables/e7c_lag_weeks.tex", "paper/supplement/tables/e7c_lag_runs.csv")
    assert rb.is_pending(tmp_path, e)
    (tmp_path / ri[0]).parent.mkdir(parents=True)
    (tmp_path / ri[0]).write_text("{}")
    assert rb.is_pending(tmp_path, e)                      # the confirmation's summary is still missing in the tree
    (tmp_path / ri[1]).parent.mkdir(parents=True)
    (tmp_path / ri[1]).write_text("{}")
    assert not rb.is_pending(tmp_path, e)


@pytest.mark.parametrize("script,attrs,match", [
    ("code/sim/figs/supp/sf_lag_other.py", dict(RUN_INPUTS=("code/sim/out/e7c/analysis.json",)), "whose script is"),
    ("code/sim/figs/supp/sf_lag_v2.py", dict(), "declares no RUN_INPUTS"),
    ("code/sim/figs/supp/sf_lag_v2.py", dict(RUN_INPUTS=()), "declares no RUN_INPUTS"),
    ("code/sim/figs/supp/sf_lag_v2.py", dict(RUN_INPUTS=("code/sim/out/sublet_v2/main/summary.json",)),
     "no file in an MS7 run folder"),
    ("code/sim/figs/supp/sf_lag_v2.py", dict(RUN_INPUTS=("code/sim/out/figs/fig4v3.json",)), "not run outputs"),
    ("code/sim/figs/supp/sf_lag_v2.py", dict(RUN_INPUTS=("paper/values/evaluation.json",)), "not run outputs"),
])
def test_rebuild_list_errors_of_a_script(registry_without_test_figures, monkeypatch, script, attrs, match):
    module = ".".join(Path(script).relative_to("code/sim").with_suffix("").parts)
    _with_script(monkeypatch, module, script, NAME="sf_lag_v2", **attrs)
    with pytest.raises(rb.RebuildError, match=match):
        rb.entries()
