"""Tests of Fig. 4 v2, figs/fig4_v2.py (the paper's Fig. 4; design/sublet_v2.md §11, W1, W9, W10, W13, row
test_figs_ms5b.py for this figure). Quick: no raw data, no run outputs. The inputs are the input tree
tests/fixtures_figs_ms5b/inputs/ (reduced-mode outputs of e7h.py's confirmation parts and the analysis on them, one
development week of two hours; README there) and the fixture extract tests/fixtures_figs_ms5b/fig4v2.json (what the
script writes on that tree; tests/fixtures_figs_ms5b/refresh_extracts.py), and every file is written under pytest's
tmp_path. The reduced files carry no real values, so the oracles recompute every plotted number from the fixture
summaries and run files independently of the script (the week bootstrap of §4.5 reimplemented here with the registered
seed and resamples, the margins from the summary's table and W0 rather than from analysis.json).

- --from-extract on the fixture extract saves at the registered size (W2 x 2.4 in, main text) with finalize() passing,
  and writes the extract it read; the command line's --from-extract option is figs.common.cli's.
- build() on the input tree gives the fixture extract's data, opens no repository file outside the input tree's result
  folders (patched open), records only result files as sources, and lists every run file it read with its sha256
  (W10); the stored layout equals a recomputation.
- The keys drawn are exactly FIGURE_POLICIES["fig4v2"] and pass check_policies and check_legacy; the legend row has two
  rows, (c)'s six policies in the first three columns and (b)'s three margins in the last two; at most 6 policies in
  the panel that is not labeled directly; (a)'s bars are named on the y ticks by their registry labels.
- Value oracles: (a)'s medians, intervals, components and segments, BL0a's USD and BL0b's ratio; (b)'s three margins
  and the negative weeks; (c)'s medians and intervals; A9 against Sublet; the caption's numbers and phrases (W1), the
  policies named by their registry labels, never by tags.
- The checks of the script: a run file whose r0 differs from the summary's, an analysis W0 that differs from the
  summary's, an H1 best outside H1's set, and an analysis count (H1's wins, H2's or H2b's weeks below the set) that
  the drawn margins do not give raise; a missing margin leaves its point out with a note and is listed among the
  missing weeks; the caption names H2b's failing weeks where they are not BL5-tau60's, and a week without a run.
- At real scale (a hand-modified extract: 16 weeks, three negative weeks two apart, BL0b far off the axis) the figure
  saves with finalize() passing, marks and labels every negative week once, and labels the weeks at a regular stride;
  a week without a margin is marked and labeled too; (a)'s label column ends at least 6 pt left of (b)'s y label.
- The print-check fixes (U37's print check): (b)'s margins dodged in x (the stored dodge), no two of its markers
  overlapping by more than MAX_MARKER_OVERLAP (and a StyleError where they would), each week's label on its column below
  the column's markers; (a)'s components key parted from BL0a's label and from BL0b's row by empty rows (key_rows),
  BL0b's ratio at the start of the label column with its arrow to the right, BL0a's label above its line's top end where
  a bar passes 1; the interval bars of (a) and (c) in the policies' label colors.
- needs_ms5b_out: on the copied confirmation outputs (where the unversioned run files are present) the extract's
  hypotheses, negative weeks and caption agree with analysis.json.
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
import shutil
import statistics
from pathlib import Path

import numpy as np
import pytest

from figs import style
from figs.common import json_number
from figs.inputs import Inputs

NAME = "fig4v2"
MODULE = "figs.fig4_v2"
FIX = Path(__file__).resolve().parent / "fixtures_figs_ms5b"
IN_ROOT = FIX / "inputs"
OUT = IN_ROOT / "code" / "sim" / "out"
MAIN = OUT / "sublet_v2" / "main" / "summary.json"
ANALYSIS = OUT / "sublet_v2" / "analysis.json"
STALE = ("tests/fixtures_figs_ms5b/fig4v2.json is stale (the script's data changed): refresh it with "
         "`python tests/fixtures_figs_ms5b/refresh_extracts.py --only fig4v2` from code/sim")
# the registered comparison sets and statistic (design/sublet_v2_prereg.md, §4.5, §6), reimplemented for the oracles
H1_SET = ("BL1", "BL1-BO", "BL2", "BL3-0", "BL4", "BL5", "BL5-cur")
BOOT_SEED, BOOT_B = 20261031, 10000
TAGS = {"sublet_v2": "Sublet", "bl1_bo": "BL1-BO", "bl1": "BL1", "bl5_cur": "BL5-cur", "bl5_tau60": "BL5-tau60",
        "bl2": "BL2", "bl3_0": "BL3-0", "bl4": "BL4", "bl1n": "BL1N", "bl5n": "BL5N", "bl1_gp": "BL1-GP"}
BARS = ("sublet_v2", "bl1_bo", "bl1", "bl5_cur", "bl5_tau60", "bl2", "bl3_0", "bl4")          # W1's list
C_KEYS = {"sublet_v2", "bl1", "bl1n", "bl1_gp", "bl5_cur", "bl5n"}                            # W1 (c)

pytestmark = pytest.mark.filterwarnings("ignore::figs.style.GlyphSizeWarning")


def module():
    return importlib.import_module(MODULE)


def fixture_payload():
    return json.loads((FIX / f"{NAME}.json").read_text())


def fixture_data():
    return fixture_payload()["data"]


def tree(p: Path):
    return json.loads(p.read_text())


def boot(values):
    """§4.5's week bootstrap: B resamples of the n values (numpy.random.default_rng(seed).integers((B, n))), the
    median of each, the 2.5 and 97.5 percentiles."""
    v = np.asarray([float(x) for x in values if x is not None])
    idx = np.random.default_rng(BOOT_SEED).integers(0, v.size, size=(BOOT_B, v.size))
    lo, hi = np.percentile(np.median(v[idx], axis=1), [2.5, 97.5])
    return float(np.median(v)), [float(lo), float(hi)]


def weeks_of(summary):
    return sorted(summary["table"]["Sublet"]["L-tr"], key=int)


def close(a, b, tol=1e-12):
    return a is not None and b is not None and abs(float(a) - float(b)) <= tol * max(1.0, abs(float(b)))


@pytest.fixture
def figs_env(tmp_path, monkeypatch):
    monkeypatch.setenv("SUBLET_FIGS_IN_ROOT", str(IN_ROOT))
    monkeypatch.setenv(style.ENV_PDF_DIR, str(tmp_path / "pdf"))
    monkeypatch.setenv(style.ENV_OUT_DIR, str(tmp_path / "out"))
    monkeypatch.setenv("SUBLET_FIGS_TABLES_DIR", str(tmp_path / "tables"))
    return tmp_path


def drawn_keys(fig) -> set:
    return {getattr(a, "_sublet_policy") for ax in fig.axes for a in ax.get_children() if hasattr(a, "_sublet_policy")}


def by_role(ax, role: str) -> list:
    return [t for t in ax.texts if getattr(t, "_sublet_role", "") == role]


# ---------------------------------------------------------------------------------------------------------------
def test_from_extract_saves_and_finalize_passes(figs_env):
    """--from-extract on the fixture extract: save() under the temporary folders (finalize() passed) at the registered
    size, text at C62's sizes, no DejaVu font, nothing outside the page, the extract written equal to the one read,
    no table."""
    rep = module().main(["--from-extract", str(FIX / f"{NAME}.json")])
    spec = style.figure_spec(NAME)
    assert (spec.width, spec.height_in, spec.main) == ("W2", 2.4, True)
    assert Path(rep["pdf"]) == figs_env / "pdf" / f"{NAME}.pdf" and Path(rep["pdf"]).is_file()
    assert abs(rep["width_bp"] - spec.width_in * 72) <= 0.5 and abs(rep["height_bp"] - spec.height_in * 72) <= 0.5
    assert rep["outside_page"] == [] and rep["pages"] == 1
    assert all(style.TEXT_MIN_PT <= s <= style.TEXT_MAX_PT for s in rep["text_pt"])
    assert not any("dejavu" in f.lower() for f in rep["fonts"])
    assert json.loads((figs_env / "out" / f"{NAME}.json").read_text()) == fixture_payload()
    assert (figs_env / "out" / f"{NAME}.png").is_file()
    assert not (figs_env / "tables").exists() and getattr(module(), "TABLES", ()) == ()


def test_from_extract_option_is_the_common_one(monkeypatch):
    """figs.common.cli: --from-extract without an argument reads the figure's own extract through Inputs.extract, with
    a path that file."""
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

    mod = module()
    assert mod.main.__module__ == mod.__name__ and mod.cli is common.cli and mod.NAME == NAME
    monkeypatch.setattr(inputs.Inputs, "extract", fake_extract)
    with pytest.raises(Stop):
        mod.main(["--from-extract"])
    monkeypatch.setattr(common, "read_extract", fake_read_extract)
    with pytest.raises(Stop):
        mod.main(["--from-extract", "some/extract.json"])
    assert calls == [(NAME, "Inputs.extract"), (NAME, "some/extract.json")]


def test_build_on_the_input_tree_matches_the_fixture(figs_env, monkeypatch):
    """build() on the input tree opens no repository file outside the result folders of the input root (patched open),
    records only result files as sources, gives the fixture extract's data, and lists every run file it read, with
    its sha256, among the sources (W10)."""
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
    data = module().build(inp)
    monkeypatch.undo()
    for p in opened:
        if style.REPO in p.parents:
            assert IN_ROOT in p.parents, f"{NAME} opened {p}"
            style.check_source(p.relative_to(IN_ROOT).as_posix())
    assert opened and all(style.check_source(s) == s for s in inp.sources)
    data = json.loads(json.dumps(data, allow_nan=False, default=json_number))
    assert data == fixture_data(), STALE
    assert fixture_payload()["sources"] == inp.sources == data["meta"]["sources"]
    runs = data["runs_files"]
    assert runs and [r["path"] for r in runs] == [s for s in inp.sources if "/runs/" in s]
    for r in runs:
        assert r["path"].startswith("code/sim/out/sublet_v2/main/runs/")
        assert r["sha256"] == hashlib.sha256((IN_ROOT / r["path"]).read_bytes()).hexdigest()
    s = tree(MAIN)
    assert data["meta"]["reduced"] is True is bool(s["meta"]["reduced"])
    assert data["meta"]["git_revision"] == s["meta"]["git_revision"]
    assert data["meta"]["weeks"] == weeks_of(s) == data["scope"]["weeks"]


def test_stored_layout_equals_a_recomputation():
    """The layout that build() stores (left reserves, axes widths, (a)'s x range) is what layout() gives on the stored
    data, so a redraw from the extract draws what the build drew; (b) and (c) are as wide as (a)'s bars' range, and
    (a)'s axes add the label column."""
    d = fixture_data()
    lay = module().layout(d)
    assert lay == d["layout"]
    w_a, w_b, w_c = lay["axes_in"]
    assert w_b == w_c and abs(w_a - w_b - lay["a_column_in"]) <= 2e-4
    assert abs(lay["a_x_max"] / lay["a_x_hi"] - w_a / w_b) <= 1e-3
    assert lay["a_x_hi"] == max([1.0] + [v for k in BARS for v in (d["a"][k]["median"], d["a"][k]["ci_hi"])])
    W = style.FIGURES[NAME].width_in
    assert abs(sum(lay["left_in"]) + sum(lay["axes_in"]) + style.MARGIN_RIGHT - W) <= 1e-3


def test_registry_keys_legend_and_policy_checks():
    """The keys drawn are FIGURE_POLICIES['fig4v2'] (W1's (a) and (c), BL0a's line and BL0b's arrow), pass
    check_policies and check_legacy, and are no legacy key; (a)'s bars are named by their registry labels in W1's
    order; the legend row has (c)'s six policies (at most 6 in the panel that is not labeled directly) in the first
    three columns and (b)'s three margins in the last two, on two rows."""
    mod = module()
    d = fixture_data()
    fig = mod.draw(d)
    keys = drawn_keys(fig)
    assert tuple(mod.KEYS) == style.FIGURE_POLICIES[NAME]
    assert keys == set(style.FIGURE_POLICIES[NAME]), keys
    style.check_policies(keys)
    style.check_legacy({NAME: tuple(keys)})
    assert not keys & set(style.LEGACY_KEYS)
    ax_a, ax_b, ax_c = fig.axes
    assert tuple(d["a"]["order"]) == BARS
    assert [t.get_text() for t in ax_a.get_yticklabels()] == \
        [style.POLICIES[k].label for k in BARS] + [style.POLICIES["bl0b"].label]
    assert set(d["c"]["order"]) == C_KEYS and len(C_KEYS) <= 6
    assert {getattr(a, "_sublet_policy") for a in ax_c.get_children() if hasattr(a, "_sublet_policy")} == C_KEYS
    (leg,) = fig.legends
    texts = [t.get_text() for t in leg.get_texts()]
    assert texts == [style.POLICIES[k].label for k in style.legend_order(C_KEYS)] + \
        [d["labels"]["margins"][k] for k in mod.MARGINS]
    assert leg._ncols == 5 and math.ceil(len(texts) / leg._ncols) == 2
    # filled column by column: the six policies take the first three columns
    assert texts[:6] == [style.POLICIES[k].label for k in style.legend_order(C_KEYS)]
    # (b)'s margins are no policies: black markers whose (marker, fill) no policy of (c) has
    mf = {(style.POLICIES[k].marker, style.POLICIES[k].fill) for k in C_KEYS}
    for k in mod.MARGINS:
        kw = mod.margin_kwargs(k)
        fill = "open" if kw["markerfacecolor"] == "white" else "filled"
        assert kw["color"] == "#000000" and (kw["marker"], fill) not in mf
    assert len({(mod.margin_kwargs(k)["marker"], mod.margin_kwargs(k)["markerfacecolor"]) for k in mod.MARGINS}) == 3


def test_panel_a_values():
    """(a): each bar's median and 95% interval of r0 over the weeks (the summary's table, L-tr, seed 0), its components'
    medians over the weeks (the run files' grouped components over the run's bl0a_usd, lease = prepaid + rent),
    segments that sum to the bar, the zero components left out, BL0a's USD per week from the summary rows and BL0b's
    median ratio from the run files' references."""
    d = fixture_data()["a"]
    s = tree(MAIN)
    weeks = weeks_of(s)
    rows = {(r["tag"], r["mode"], str(r["cell"]), r["seed"]): r for r in s["runs"] if r["kind"] == "week"}
    comps_all, refs = {}, {}
    for key in BARS:
        tag = TAGS[key]
        r0 = [s["table"][tag]["L-tr"][w]["0"] for w in weeks]
        med, ci = boot(r0)
        e = d[key]
        assert e["tag"] == tag and e["r0"] == r0 and e["n"] == len(weeks)
        assert close(e["median"], med) and close(e["ci_lo"], ci[0]) and close(e["ci_hi"], ci[1])
        comps = {}
        for w in weeks:
            job = rows[(tag, "L-tr", w, 0)]["job"]
            rec = tree(OUT / "sublet_v2" / "main" / "runs" / (job.replace(":", "__").replace("=", "__") + ".json"))
            (run,) = [x for x in rec["runs"] if x["mode"] == "L-tr" and x["policy_seed"] == 0]
            assert close(run["accountings"]["overflow_over_bl0a"], s["table"][tag]["L-tr"][w]["0"])
            assert close(run["components"]["lease_prepaid"] + run["components"]["lease_rent"], run["grouped"]["lease"],
                         1e-9)
            for c, v in run["grouped"].items():
                if c != "total":
                    comps.setdefault(c, []).append(v / run["bl0a_usd"])
            refs[w] = rec["instances"]["base"]["references"]
        med_c = {c: statistics.median(v) for c, v in comps.items()}
        assert e["components_median_over_bl0a"].keys() == med_c.keys()
        assert all(close(e["components_median_over_bl0a"][c], med_c[c]) for c in med_c)
        comps_all[key] = med_c
    drawn = [c for c in ("lease", "loading", "routing", "fallback", "stranding")
             if any(comps_all[k].get(c, 0.0) > 0 for k in BARS)]
    assert d["components"]["order"] == drawn
    assert d["zero_components"] == sorted(c for c in set().union(*comps_all.values()) if c not in drawn)
    for key in BARS:
        tot = sum(comps_all[key][c] for c in drawn)
        seg = d[key]["segments"]
        assert list(seg) == drawn and close(sum(seg.values()), d[key]["median"], 1e-9)
        assert all(close(seg[c], d[key]["median"] * comps_all[key][c] / tot, 1e-9) for c in drawn)
    usd = {w: rows[("Sublet", "L-tr", w, 0)]["bl0a_usd"] for w in weeks}
    assert d["bl0a"]["usd_by_week"] == usd and close(d["bl0a"]["usd_median"], statistics.median(usd.values()))
    ratio = statistics.median(refs[w]["bl0b_overflow_usd"] / refs[w]["bl0a_usd"] for w in weeks)
    assert close(d["bl0b"]["overflow_over_bl0a"], ratio)
    assert fixture_data()["labels"]["bl0b_ratio"] == f"{ratio:.1f}"


def test_panel_b_values():
    """(b): per week, H1's margin (the least r0 of H1's set minus Sublet's, from the summary's table), Sublet's W0
    margin under H1's set and under BL5-tau60 (from the summary's W0); the negative weeks with their lowest series; the
    weeks in which BL5-tau60's W0 is below Sublet's."""
    b = fixture_data()["b"]
    s = tree(MAIN)
    weeks = weeks_of(s)
    tab, w0 = s["table"], s["W0"]["0"]
    assert b["weeks"] == weeks and b["x"] == [int(w) for w in weeks] and b["h1_set"] == list(H1_SET)
    neg = []
    for i, w in enumerate(weeks):
        trace = min(tab[t]["L-tr"][w]["0"] for t in H1_SET) - tab["Sublet"]["L-tr"][w]["0"]
        w0s = min(w0[t][w] for t in H1_SET) - w0["Sublet"][w]
        t60 = w0["BL5-tau60"][w] - w0["Sublet"][w]
        assert close(b["trace"][i], trace) and close(b["w0_set"][i], w0s) and close(b["w0_tau60"][i], t60)
        vals = {k: v for k, v in (("trace", trace), ("w0_set", w0s), ("w0_tau60", t60)) if v < 0}
        if vals:
            low = min(vals, key=vals.get)
            neg.append((w, low, sorted(vals)))
    assert [(n["week"], n["lowest"], n["series"]) for n in b["negative"]] == neg
    assert b["tau60_below_sublet_weeks"] == [w for w in weeks if w0["BL5-tau60"][w] < w0["Sublet"][w]]
    assert b["notes"] == []


def test_panel_c_values_and_a9():
    """(c): medians and 95% week-bootstrap intervals of r0 (L-tr) and W0 for the six policies; A9 against Sublet."""
    c = fixture_data()["c"]
    s = tree(MAIN)
    weeks = weeks_of(s)
    for key in C_KEYS:
        tag = TAGS[key]
        for field, vals in (("r0", [s["table"][tag]["L-tr"][w]["0"] for w in weeks]),
                            ("W0", [s["W0"]["0"][tag][w] for w in weeks])):
            med, ci = boot(vals)
            assert close(c[key][field]["median"], med) and all(close(x, y) for x, y in zip(c[key][field]["ci"], ci))
    a9 = {f: boot(v)[0] for f, v in (("r0", [s["table"]["A9"]["L-tr"][w]["0"] for w in weeks]),
                                     ("W0", [s["W0"]["0"]["A9"][w] for w in weeks]))}
    sub = {f: c["sublet_v2"][f]["median"] for f in ("r0", "W0")}
    diff = {f: abs(a9[f] - sub[f]) for f in a9}
    assert all(close(c["a9"]["abs_diff_to_sublet"][f], diff[f]) for f in diff)
    assert c["a9"]["coincides"] is all(v <= module().A9_TOL for v in diff.values())


def test_caption_draft():
    """The caption draft (W1): at most 4 lines of about 140 characters; BL0a's weekly USD, H1's registered margin and
    interval, H2's count, H2b's count with its weeks and verdict, H1's set named, the weeks' dependence, the
    descriptive statistics, A9 against Sublet and the lagged BL5's row in the supplement, each number from the
    inputs; no claim of a lower worst case than every baseline."""
    d = fixture_data()
    cap = d["labels"]["caption"]
    a = tree(ANALYSIS)
    n = len(d["b"]["weeks"])
    assert d["labels"]["caption_chars"] == len(cap) <= 4 * 140 and d["labels"]["caption_lines_est"] <= 4
    m = a["H1"]["median_margin"]
    assert f"median {m['median']:.3f} [{m['ci'][0]:.3f}, {m['ci'][1]:.3f}]" in cap
    assert f"{d['a']['bl0a']['usd_median']:,.0f} USD/week (median)" in cap
    assert f">0 in {a['H2']['weeks_below_set']}/{n}, H2" in cap
    t60 = d["b"]["tau60_below_sublet_weeks"]
    assert f"<0 in {len(t60)}/{n}" in cap                    # the weeks themselves are labeled in (b)
    assert ("H2b holds" if a["H2b"]["pass"] else "H2b fails") in cap
    for phrase in ("H1's set", "rotations of one series", "descriptive", "RetroRenting-style, lagged (H1's set): "
                   "supplement", "critical-ratio renting alone", "overflow accounting", "Medians, 95% intervals",
                   "Segments: component medians, scaled", "Grey: all-fallback", "RetroRenting, τ≥1 h minus Sublet"):
        assert phrase in cap, phrase
    assert f"provision for peak: {d['labels']['bl0b_ratio']}" in cap
    assert "every baseline" not in cap
    # the figure's names, never the tags (print check of U37)
    for tag in ("BL0a", "BL0b", "BL5-tau60", "A9", "BL5 ", "lagged BL5"):
        assert tag not in cap, tag
    assert d["hypotheses"]["H1"]["median_margin"] == m["median"] and d["hypotheses"]["H2b"]["pass"] == a["H2b"]["pass"]
    fail = [str(r["week"]) for r in a["H2b"]["weeks"] if not r["below_all"]]
    assert d["b"]["h2b_failing_weeks"] == d["hypotheses"]["H2b"]["failing_weeks"] == fail
    # the figure states no theory result, so its extract carries no (paraphrased) status label of C3 (W5)
    assert set(d["labels"]["status"]) == {"statistics"}


def test_caption_names_other_h2b_weeks_and_missing_weeks():
    """Where H2b's failing weeks are not BL5-tau60's negative weeks the caption gives them too, and a week without a
    run (the missing-run rule, a loss for Sublet) is named in the caption."""
    mod = module()
    base = {"n_weeks": 16, "bl0a_usd_median": 35010.0, "h1": {"median": 0.052, "ci": [0.038, 0.080]},
            "h2_below_set": 16, "tau60_below_sublet_weeks": ["302"], "h2b_pass": False,
            "h2b_failing_weeks": ["302"], "missing_weeks": [], "a9_coincides": True, "a9": {}}
    cap = mod.caption(base)
    assert "(<0 in 1/16; H2b fails)" in cap and "H2b's set not above" not in cap and "No run" not in cap
    cap = mod.caption({**base, "h2b_failing_weeks": ["302", "311"], "missing_weeks": ["305"]})
    assert "H2b's set not above Sublet in 2/16: 302, 311" in cap and "No run in week 305: a loss" in cap


# ---------------------------------------------------------------------------------------------------------------
# The script's checks
def _copy_tree(tmp_path) -> Path:
    root = tmp_path / "root"
    src = OUT / "sublet_v2"
    dst = root / "code" / "sim" / "out" / "sublet_v2"
    shutil.copytree(src / "main", dst / "main")
    shutil.copy(src / "analysis.json", dst / "analysis.json")
    return root


def test_build_checks_raise(tmp_path, monkeypatch):
    """A run file whose overflow_over_bl0a differs from the summary's r0, and an analysis W0 that differs from the
    summary's, stop the build."""
    mod = module()
    root = _copy_tree(tmp_path)
    monkeypatch.setenv("SUBLET_FIGS_IN_ROOT", str(root))
    run = root / "code/sim/out/sublet_v2/main/runs" / next(p.name for p in sorted(
        (root / "code/sim/out/sublet_v2/main/runs").glob("*__tag__BL4__*.json")))
    rec = json.loads(run.read_text())
    keep = run.read_text()
    for r in rec["runs"]:
        r["accountings"]["overflow_over_bl0a"] += 0.01
    run.write_text(json.dumps(rec))
    with pytest.raises(style.StyleError, match="differs from the summary's r0"):
        mod.build(Inputs())
    run.write_text(keep)
    ana_p = root / "code/sim/out/sublet_v2/analysis.json"
    ana = json.loads(ana_p.read_text())
    ana["H2"]["weeks"][0]["Sublet"] += 0.01
    ana_p.write_text(json.dumps(ana))
    with pytest.raises(style.StyleError, match="the W0 of Sublet"):
        mod.build(Inputs())


def test_margin_series_checks_and_missing_values():
    """margin_series: an H1 best outside H1's set raises; a week without H1's margin or without BL5-tau60's W0 leaves
    those points out (None) with a note."""
    mod = module()
    s, a = tree(MAIN), tree(ANALYSIS)
    weeks = weeks_of(s)
    bad = copy.deepcopy(a)
    bad["H1"]["margins"][weeks[0]]["best"] = "A9"
    with pytest.raises(style.StyleError, match="is not in H1's set"):
        mod.margin_series(bad, s, weeks)
    miss, s2 = copy.deepcopy(a), copy.deepcopy(s)
    miss["H1"]["margins"][weeks[0]]["delta"] = None
    if (a["H1"]["margins"][weeks[0]]["delta"] or 0.0) > 0:      # a missing margin is a loss in H1's count
        miss["H1"]["wins"] -= 1
    miss["H2b"]["weeks"][0]["others"]["BL5-tau60"] = None
    if miss["H2b"]["weeks"][0]["below_all"]:                     # and not below H2b's set
        miss["H2b"]["weeks"][0]["below_all"] = False
        miss["H2b"]["weeks_below_set"] -= 1
    s2["W0"]["0"]["BL5-tau60"][weeks[0]] = None
    b = mod.margin_series(miss, s2, weeks)
    assert b["trace"][0] is None and b["w0_tau60"][0] is None and b["w0_set"][0] is not None
    assert any("H1's margin missing" in t for t in b["notes"]) and any("BL5-tau60" in t for t in b["notes"])
    assert b["missing_weeks"] == [{"week": weeks[0], "x": int(weeks[0]), "series": ["trace", "w0_tau60"]}]
    assert weeks[0] in b["h2b_failing_weeks"]


@pytest.mark.parametrize("path, value, match", [
    (("H1", "wins"), 5, "H1.wins"),
    (("H2", "weeks_below_set"), 7, "H2.weeks_below_set"),
    (("H2b", "weeks_below_set"), 9, "H2b.weeks_below_set"),
])
def test_margin_series_checks_the_analysis_counts(path, value, match):
    """The drawn margins give the analysis's counts: H1's wins, H2's weeks below the set, and H2b's weeks below the set
    against its rows; a count that differs stops the build."""
    mod = module()
    s, a = tree(MAIN), copy.deepcopy(tree(ANALYSIS))
    a[path[0]][path[1]] = value
    with pytest.raises(style.StyleError, match=match):
        mod.margin_series(a, s, weeks_of(s))


# ---------------------------------------------------------------------------------------------------------------
# Real scale
def real_scale(d: dict) -> dict:
    """The fixture extract with real-scale values: 16 weeks with margins like the confirmation's (three negative weeks,
    two of them two weeks apart), the bars below 1, BL0b at 24.3, (c)'s points spread as on the confirmation."""
    mod = module()
    d = copy.deepcopy(d)
    weeks = [str(w) for w in range(1001, 1017)]
    rng = np.random.default_rng(7)
    trace = list(np.round(rng.uniform(0.03, 0.11, 16), 4))
    w0s = list(np.round(rng.uniform(0.24, 0.35, 16), 4))
    t60 = list(np.round(rng.uniform(0.0, 0.29, 16), 4))
    for i, v in ((1, -0.045), (6, -0.049), (8, -0.017)):
        t60[i] = v
    b = d["b"]
    b.update(weeks=weeks, x=[int(w) for w in weeks], trace=trace, w0_set=w0s, w0_tau60=t60,
             best_trace=["BL1-BO"] * 16, best_w0=["BL4"] * 16, notes=[],
             negative=[{"week": weeks[i], "x": int(weeks[i]), "series": ["w0_tau60"], "lowest": "w0_tau60",
                        "y": t60[i]} for i in (1, 6, 8)],
             tau60_below_sublet_weeks=[weeks[i] for i in (1, 6, 8)])
    for key, (m, lo, hi) in zip(BARS, ((0.538, 0.531, 0.547), (0.606, 0.575, 0.640), (0.617, 0.601, 0.670),
                                       (0.629, 0.595, 0.653), (0.755, 0.724, 0.786), (0.646, 0.628, 0.684),
                                       (0.657, 0.632, 0.675), (0.888, 0.862, 0.906))):
        e = d["a"][key]
        tot = sum(e["segments"].values()) or 1.0
        e["segments"] = {c: m * v / tot for c, v in e["segments"].items()}
        e.update(median=m, ci_lo=lo, ci_hi=hi)
    d["a"]["bl0b"]["overflow_over_bl0a"] = 24.345
    d["labels"]["bl0b_ratio"] = "24.3"
    for key, (r, rl, rh, w, wl, wh) in {
            "sublet_v2": (0.538, 0.531, 0.547, 0.770, 0.733, 0.776), "bl1": (0.617, 0.601, 0.670, 1.565, 1.504, 1.912),
            "bl5_cur": (0.629, 0.595, 0.653, 1.138, 1.111, 1.295), "bl1n": (0.616, 0.578, 0.641, 0.929, 0.886, 0.971),
            "bl5n": (0.596, 0.568, 0.635, 0.899, 0.891, 0.911), "bl1_gp": (0.629, 0.604, 0.687, 1.009, 1.007, 1.011),
    }.items():
        d["c"][key]["r0"].update(median=r, ci=[rl, rh])
        d["c"][key]["W0"].update(median=w, ci=[wl, wh])
    d["layout"] = mod.layout(d)
    return d


def test_real_scale_saves_and_marks_every_negative_week(tmp_path):
    """At real scale the figure saves with finalize() passing; each negative week has one shaded column and one label
    with its number, placed nearer its own point than the other negative weeks' points; the weeks are labeled at a
    regular stride that includes the first and the last."""
    from matplotlib.patches import Rectangle
    mod = module()
    d = real_scale(fixture_data())
    fig = mod.draw(d)
    ax_b = fig.axes[1]
    labels = by_role(ax_b, "week_label")
    assert sorted(t.get_text() for t in labels) == sorted(n["week"] for n in d["b"]["negative"])
    shaded = [p for p in ax_b.patches if isinstance(p, Rectangle) and p.get_facecolor()[:3] ==
              tuple(int(style.SHADE_GREY[i:i + 2], 16) / 255 for i in (1, 3, 5))]
    assert sorted(round(p.get_x() + 0.5) for p in shaded) == sorted(n["x"] for n in d["b"]["negative"])
    r = fig.canvas.get_renderer()
    pts = {n["week"]: ax_b.transData.transform((n["x"], n["y"])) for n in d["b"]["negative"]}
    for t in labels:
        bb = t.get_window_extent(r)
        c = np.array([(bb.x0 + bb.x1) / 2, (bb.y0 + bb.y1) / 2])
        dist = {w: np.hypot(*(p - c)) for w, p in pts.items()}
        assert min(dist, key=dist.get) == t.get_text()
    shown = [float(v) for v in ax_b.xaxis.get_majorticklocs()]
    xs = d["b"]["x"]
    assert shown[0] == xs[0] and shown[-1] == xs[-1] and len(set(np.diff(shown))) == 1
    assert (len(xs) - 1) % int(shown[1] - shown[0]) == 0
    rep = style.save(fig, NAME, d, pdf_dir=tmp_path / "pdf", out_dir=tmp_path / "out")
    assert rep["outside_page"] == []
    assert rep["text_pt"] and set(rep["text_pt"]) <= {style.TICK_PT, style.LABEL_PT}


def test_real_scale_missing_week_is_marked(tmp_path):
    """A week without a margin (the missing-run rule: a loss for Sublet) leaves its point out and is marked by a shaded
    column and labeled with its number, like a negative week, so that no failure is hidden; the figure saves."""
    from matplotlib.patches import Rectangle
    mod = module()
    d = real_scale(fixture_data())
    b = d["b"]
    i = 12
    b["trace"][i] = None
    b["missing_weeks"] = [{"week": b["weeks"][i], "x": b["x"][i], "series": ["trace"]}]
    fig = mod.draw(d)
    ax_b = fig.axes[1]
    want = sorted([n["week"] for n in b["negative"]] + [b["weeks"][i]])
    assert sorted(t.get_text() for t in by_role(ax_b, "week_label")) == want
    shaded = sorted(round(p.get_x() + 0.5) for p in ax_b.patches if isinstance(p, Rectangle))
    assert shaded == sorted(int(w) for w in want)
    style.save(fig, NAME, d, pdf_dir=tmp_path / "pdf", out_dir=tmp_path / "out")


def test_label_column_clears_panel_b(tmp_path):
    """(a)'s label column (BL0a's label, the components' key, BL0b's ratio and arrow) ends at least 6 pt left of (b)'s
    y label at real scale (COL_END_PT; 2.6 pt before the review)."""
    mod = module()
    d = real_scale(fixture_data())
    fig = mod.draw(d)
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    to_pt = 72.0 / fig.dpi
    ax_a, ax_b, _ = fig.axes
    texts = list(ax_a.texts)                               # BL0b's arrow is an annotation, with its arrow patch
    assert any(getattr(t, "_sublet_role", "") == "off_scale_arrow" for t in texts)
    right = max(t.get_window_extent(r).x1 for t in texts)
    assert (ax_b.yaxis.label.get_window_extent(r).x0 - right) * to_pt >= 6.0


def test_real_scale_bar_beyond_one_and_no_negative_week(tmp_path):
    """A bar beyond 1 widens x_hi (the BL0a line then crosses it) and a figure without a negative week has no shaded
    column and no week label; both save."""
    mod = module()
    d = real_scale(fixture_data())
    d["a"]["bl4"].update(median=1.21, ci_lo=1.15, ci_hi=1.30)
    d["b"]["w0_tau60"] = [abs(v) for v in d["b"]["w0_tau60"]]
    d["b"]["negative"], d["b"]["tau60_below_sublet_weeks"] = [], []
    d["layout"] = mod.layout(d)
    assert d["layout"]["a_x_hi"] == 1.30
    fig = mod.draw(d)
    assert by_role(fig.axes[1], "week_label") == [] and len(fig.axes[1].patches) == 0
    # BL0a's line now lies inside the bars' range: its label sits above the line's top end, centered on x = 1
    ax_a = fig.axes[0]
    r = fig.canvas.get_renderer()
    (fb,) = [t for t in by_role(ax_a, "direct_label") if t.get_text() == d["labels"]["bl0a"]]
    bb = fb.get_window_extent(r)
    assert bb.y0 >= ax_a.get_window_extent(r).y1
    assert abs((bb.x0 + bb.x1) / 2 - ax_a.transData.transform((1.0, 0.0))[0]) <= 0.5
    rows = sorted(t.get_position()[1] for t in by_role(ax_a, "key"))
    assert rows == mod.key_rows(len(d["a"]["order"]), len(d["a"]["components"]["order"]), True)
    style.save(fig, NAME, d, pdf_dir=tmp_path / "pdf", out_dir=tmp_path / "out")


def test_margins_dodged_and_markers_apart():
    """(b)'s margins are drawn at the week plus the stored dodge (BL5-tau60's W0 margin left, the cost margin right,
    H1's set's on the week; the W0 margins open, the cost margin filled); at real scale no two markers overlap by more
    than MAX_MARKER_OVERLAP of the smaller one; where two would (the cost and BL5-tau60 margins equal and undodged)
    the draw raises (print check of U37: they merged in 6 of 16 weeks)."""
    mod = module()
    d = real_scale(fixture_data())
    assert d["b"]["dodge_weeks"] == mod.DODGE == {"trace": mod.B_DODGE, "w0_set": 0.0, "w0_tau60": -mod.B_DODGE}
    assert [mod.MARGIN_STYLES[k]["markerfacecolor"] for k in mod.MARGINS] == ["#000000", "white", "white"]
    fig = mod.draw(d)
    ax_b = fig.axes[1]
    lines = {ln._sublet_role[7:]: ln for ln in ax_b.lines if getattr(ln, "_sublet_role", "").startswith("margin:")}
    assert set(lines) == set(mod.MARGINS)
    for k, ln in lines.items():
        xs = [x for x, y in zip(d["b"]["x"], d["b"][k]) if y is not None]
        assert np.allclose(ln.get_xdata(), np.asarray(xs, dtype=float) + mod.DODGE[k])
    over = mod.marker_overlaps(ax_b)
    assert not over or over[0]["share"] <= mod.MAX_MARKER_OVERLAP
    bad = copy.deepcopy(d)
    bad["b"]["w0_tau60"] = list(bad["b"]["trace"])
    bad["b"]["dodge_weeks"] = {"trace": 0.0, "w0_set": 0.0, "w0_tau60": 0.0}
    bad["b"]["negative"], bad["b"]["tau60_below_sublet_weeks"] = [], []
    with pytest.raises(style.StyleError, match="markers overlap"):
        mod.draw(bad)


def test_marker_outline_and_overlap_share():
    """The outline of a marker at markersize s with edge e spans the marker's unit path times s + e; two equal squares
    half on each other overlap by a share of one half."""
    mod = module()
    h = mod.marker_outline_pt("h", 3.5, 0.6)
    assert abs(np.ptp(h[:, 1]) - 4.1) < 1e-9 and abs(np.ptp(h[:, 0]) - 4.1 * math.sqrt(3) / 2) < 1e-9
    sq = np.array([[0.0, 0.0], [2.0, 0.0], [2.0, 2.0], [0.0, 2.0]])
    q = mod._clip(sq, sq + [1.0, 0.0])
    assert abs(mod._area(q) / mod._area(sq) - 0.5) < 1e-12 and mod._clip(sq, sq + [3.0, 0.0]) is None


def test_week_labels_on_their_columns():
    """Each week's label has its center within its column (the week +- 0.5) and its top below the lowest marker drawn
    in that column (print check of U37: '307' and '309' sat 7.3 pt beside their columns)."""
    mod = module()
    d = real_scale(fixture_data())
    fig = mod.draw(d)
    ax_b = fig.axes[1]
    r = fig.canvas.get_renderer()
    labels = by_role(ax_b, "week_label")
    assert sorted(t.get_text() for t in labels) == sorted(n["week"] for n in d["b"]["negative"])
    for t in labels:
        bb = t.get_window_extent(r)
        cx, top = ax_b.transData.inverted().transform(((bb.x0 + bb.x1) / 2, bb.y1))
        i = d["b"]["weeks"].index(t.get_text())
        assert abs(cx - d["b"]["x"][i]) <= 0.5 + 1e-9, t.get_text()
        assert top < min(d["b"][k][i] for k in mod.MARGINS if d["b"][k][i] is not None), t.get_text()


def test_panel_a_key_rows_bl0b_arrow_and_whiskers():
    """(a): the components key sits in key_rows' rows, an empty row or more from BL0a's label (row 0) and from BL0b's
    row; BL0b's ratio starts the label column right of x_hi and its arrow runs from right of the ratio to the column's
    end; the interval bars of (a) and (c) are drawn in the policies' label colors."""
    from matplotlib import colors as mcolors
    from matplotlib.collections import LineCollection
    mod = module()
    assert mod.key_rows(8, 4, False) == [3, 4, 5, 6] and mod.key_rows(8, 4, True) == [2, 3, 4, 5]
    with pytest.raises(style.StyleError, match="need more rows"):
        mod.key_rows(5, 4, False)
    d = real_scale(fixture_data())
    fig = mod.draw(d)
    ax_a, _, ax_c = fig.axes
    n_bars, comps = len(d["a"]["order"]), d["a"]["components"]["order"]
    rows = sorted(t.get_position()[1] for t in by_role(ax_a, "key"))
    assert rows == mod.key_rows(n_bars, len(comps), False) and rows[0] >= 2 and rows[-1] <= n_bars - 2
    (fb,) = [t for t in by_role(ax_a, "direct_label") if t.get_text() == d["labels"]["bl0a"]]
    assert fb.get_position()[1] == 0
    (ratio,) = [t for t in by_role(ax_a, "direct_label") if t.get_text() == d["labels"]["bl0b_ratio"]]
    (arr,) = by_role(ax_a, "off_scale_arrow")
    hi = d["layout"]["a_x_hi"]
    r = fig.canvas.get_renderer()
    assert ratio.xy[0] > hi and ratio.xy[1] == n_bars and arr.xy[1] == n_bars
    tail_px = ax_a.transData.transform((arr.xyann[0], n_bars))[0]
    assert tail_px > ratio.get_window_extent(r).x1 and arr.xy[0] > arr.xyann[0]
    for ax, keys in ((ax_a, BARS), (ax_c, C_KEYS)):
        got = {mcolors.to_hex(c.get_colors()[0]) for c in ax.collections if isinstance(c, LineCollection)}
        assert got == {mcolors.to_hex(style.POLICIES[k].label_color) for k in keys}, (got, keys)
    # (a)'s whiskers in a white casing, so that they read over the dark fallback segment in greyscale (second print
    # check of U37)
    whiskers = [c for c in ax_a.collections if isinstance(c, LineCollection)]
    assert len(whiskers) == len(BARS)
    for c in whiskers:
        stroke = c.get_path_effects()[0]
        assert mcolors.to_hex(stroke._gc["foreground"]) == "#ffffff"
        assert abs(stroke._gc["linewidth"] - (style.UNCERTAINTY_PT + mod.WHISKER_CASING_PT)) < 1e-12


# ---------------------------------------------------------------------------------------------------------------
@pytest.mark.needs_ms5b_out("sublet_v2/main/summary.json", "sublet_v2/analysis.json")
def test_confirmation_build_agrees_with_the_analysis():
    """On the copied confirmation outputs (skipped where the unversioned run files are absent): the build is not
    reduced, its weeks are H1's, its hypotheses block, negative weeks and caption agree with analysis.json, and every
    run file it read is listed with its sha256."""
    import conftest
    root = conftest.MS5B_OUT_ROOT
    runs = root / "code/sim/out/sublet_v2/main/runs"
    if not runs.is_dir() or not any(runs.glob("*.json")):
        pytest.skip(f"{runs} holds no run files (not versioned, C40)")
    old = os.environ.get("SUBLET_FIGS_IN_ROOT")
    os.environ["SUBLET_FIGS_IN_ROOT"] = str(root)
    try:
        inp = Inputs()
        d = json.loads(json.dumps(module().build(inp), allow_nan=False, default=json_number))
    finally:
        if old is None:
            os.environ.pop("SUBLET_FIGS_IN_ROOT", None)
        else:
            os.environ["SUBLET_FIGS_IN_ROOT"] = old
    a = json.loads((root / "code/sim/out/sublet_v2/analysis.json").read_text())
    assert d["meta"]["reduced"] is False and d["b"]["weeks"] == [str(w) for w in a["H1"]["weeks"]]
    assert d["hypotheses"]["H1"]["median_margin"] == a["H1"]["median_margin"]["median"]
    assert d["hypotheses"]["H2"]["weeks_below_set"] == a["H2"]["weeks_below_set"]
    below = [r["week"] for r in a["H2b"]["weeks"] if r["others"]["BL5-tau60"] < r["Sublet"]]
    assert d["b"]["tau60_below_sublet_weeks"] == below == [n["week"] for n in d["b"]["negative"]]
    assert len(d["runs_files"]) == len(BARS) * len(a["H1"]["weeks"])
    assert all(r["sha256"] == hashlib.sha256((root / r["path"]).read_bytes()).hexdigest() for r in d["runs_files"])


# ---------------------------------------------------------------- C62 (2026-11-24): fig4v2 at 7 pt
def test_fig4v2_c62_rows_on_one_baseline():
    """C62: the texts that share a row print on one baseline (common.printed_baselines_pt, the PDF's metrics): each
    row of the two-row legend (align_printed_rows moves its mathtext labels, "$W_0$ vs. ...", onto their plain
    neighbors' baseline), and in (a) BL0a's label, each component's name in the key and BL0b's ratio on the bar name of
    their row (va center_baseline, as the y tick labels); the stored layout is measured at the tick size (the rule)."""
    from figs import common
    mod = module()
    for d in (fixture_data(), json.loads((Path(mod.__file__).resolve().parents[1] / "out" / "figs" /
                                          "fig4v2.json").read_text())["data"]):
        fig = mod.draw(d)
        (leg,) = [lg for lg in fig.legends if getattr(lg, "_sublet_role", "") == "legend_row"]
        texts = list(leg.get_texts())
        base = common.printed_baselines_pt(fig, texts)
        rows = sorted(base)
        assert rows[-1] - rows[0] > 5.0                                    # two rows
        for b in base:
            assert all(abs(b - c) < 0.05 for c in base if abs(b - c) < common.ROW_TOL_PT)
        assert any(getattr(t, "_sublet_baseline_shift_pt", 0.0) for t in texts) or \
            not any("$" in t.get_text() for t in texts)
        ax_a = fig.axes[0]
        names = {round(float(tk.get_loc())): tk.label1 for tk in ax_a.yaxis.get_major_ticks()
                 if tk.label1.get_text()}
        col = [t for t in ax_a.texts if getattr(t, "_sublet_role", "") in ("direct_label", "key")]
        assert col and "at 7 pt" in d["layout"]["rule"]
        fig.canvas.draw()
        r = fig.canvas.get_renderer()
        pitch = abs(ax_a.transData.transform((0, 1))[1] - ax_a.transData.transform((0, 0))[1])
        on_rows = 0
        for t in col:                                  # the texts on a bar's row (not BL0a's label above the axes)
            yc = 0.5 * (t.get_window_extent(r).y0 + t.get_window_extent(r).y1)
            n = min(names.values(), key=lambda q: abs(0.5 * (q.get_window_extent(r).y0 + q.get_window_extent(r).y1)
                                                      - yc))
            if abs(0.5 * (n.get_window_extent(r).y0 + n.get_window_extent(r).y1) - yc) > 0.5 * pitch:
                continue
            b_t, b_n = common.printed_baselines_pt(fig, [t, n])
            assert abs(b_t - b_n) < 0.05, (t.get_text(), n.get_text(), b_t, b_n)
            on_rows += 1
        assert on_rows >= 2
