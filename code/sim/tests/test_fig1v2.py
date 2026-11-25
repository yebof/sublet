"""Tests of Fig. 1 v2 (design/ms6_spec.md §1.1 M1, §2 U44): the driver sublet/experiments/fig1_illustrative.py with its
logging subclass, and the figure script figs/fig1_v2.py.

Quick (no run): the inputs are the input tree tests/fixtures_figs_ms6/inputs/ (a reduced run of the driver, the first 3
hours of the cell; not a result; README there) and the fixture extract tests/fixtures_figs_ms6/fig1v2.json (what the
script writes on that tree; tests/fixtures_figs_ms6/refresh_extracts.py); every file is written under pytest's tmp_path.
- The figure redraws from the fixture extract with finalize() passing at fig1's registered size (W1 x 2.4 in), writes
  the extract it read, and a second redraw from that extract gives the same PDF bytes; the build on the input tree
  opens only result files of the input root and gives the fixture extract; it draws only sublet_v2 (FIGURE_POLICIES
  ["fig1v2"]), (a)'s reactions in sublet_v2's color.
- The extract equals the run record: each plotted series minus C_S, the projected slots and the inner list's test
  values; (a)'s labels carry contract k's subscripts (consistency C-14); no design ID is drawn; the caption draft says
  what M1 requires (illustrative run of Sublet, a pilot cell, the eager stress lender, the projected slots, the
  inner policy's proposals above the threshold and the executed list under it, no abort, and the three results by
  their labels of design/ms6_spec.md §5) within the single-column caption budget.
- collect() refuses a record whose sha256 or checks do not hold, a run that aborted, an executed test value above the
  threshold, an inner test value not above it, and a run without a projected slot.
- The driver's helpers, the identity check's sensitivity, and the logging subclass: outside algos/guard.py, overriding
  reset and _evaluate only, set only on an A8P object.
- The frozen fig1 (figs/fig1_guard.py, whose draw_timeline gained the keyword policy_key, default 'sublet') redraws
  from its versioned extract byte-identical to paper/figures/fig1.pdf (C62: the versioned PDF is the redraw at C62's
  sizes, with (a)'s rows spaced for 7-pt text; its extract, the figure's source, is unchanged).
- figs.rebuild lists fig1v2 right after fig1 (C42's order, C44: the print sheet's), from its script.
With the a12 outputs (needs_a12; the instance's inputs are versioned, no raw trace): the full run of the cell (Q44 I2
c1, L-eg, policy seed 0; about 13 s): the logged run equals an unlogged run (report, per-slot costs, components);
ALG(T) equals the pilot's record (code/sim/out/sublet_v2_pilot/p4/summary.json; 589.0211708550141 USD) within 1e-9,
with 38 projected slots and no abort; the log agrees with the guard's record; the driver's main() writes a run record
and manifest whose checks pass, and the figure builds from them with finalize() passing.
"""
from __future__ import annotations

import builtins
import copy
import hashlib
import inspect
import io
import json
import os
import re
import shutil
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from fixtures import SIM

from figs import fig1_guard, fig1_v2, style
from figs import rebuild as rb
from figs.inputs import Inputs
from sublet.experiments import fig1_illustrative as F

REPO = SIM.parents[1]
FIX = Path(__file__).resolve().parent / "fixtures_figs_ms6"
IN_ROOT = FIX / "inputs"
RUN_DIR = IN_ROOT / "code" / "sim" / "out" / "fig1v2"
STALE = ("tests/fixtures_figs_ms6/fig1v2.json is stale (the script's data changed): refresh it with "
         "`python tests/fixtures_figs_ms6/refresh_extracts.py` from code/sim")
PILOT_ALG = 589.0211708550141           # design/ms6_spec.md M1: the pilot's record of the cell (p4/summary.json)
# drawn design or experiment IDs (design/ms6_spec.md M6, inventory_consistency §4 G-7): policy and baseline IDs,
# experiments, results, cells, lender modes, open choices and units, and the names of the results
DESIGN_ID = re.compile(r"\b(A[1-9]P?|BL\d|E\d{1,2}|G\d|C\d{1,2}|Q\d{1,2}|I\d|W\([abc]\)|M\d{1,2}|U\d{2}|P\.1)\b"
                       r"|L-[a-z]|Theorem|Lemma|Proposition|Remark|Sublet|illustrative")

pytestmark = pytest.mark.filterwarnings("ignore::figs.style.GlyphSizeWarning")


def fixture_payload():
    return json.loads((FIX / "fig1v2.json").read_text())


def fixture_data():
    return fixture_payload()["data"]


@pytest.fixture
def figs_env(tmp_path, monkeypatch):
    monkeypatch.setenv("SUBLET_FIGS_IN_ROOT", str(IN_ROOT))
    monkeypatch.setenv(style.ENV_PDF_DIR, str(tmp_path / "pdf"))
    monkeypatch.setenv(style.ENV_OUT_DIR, str(tmp_path / "out"))
    monkeypatch.setenv("SUBLET_FIGS_TABLES_DIR", str(tmp_path / "tables"))
    return tmp_path


def drawn_keys(fig) -> set:
    return {getattr(a, "_sublet_policy") for ax in fig.axes for a in ax.get_children() if hasattr(a, "_sublet_policy")}


def tree_copy(tmp_path: Path) -> Path:
    """A copy of the input tree under tmp_path/tree."""
    root = tmp_path / "tree"
    shutil.copytree(IN_ROOT, root)
    return root


def rewrite_run(root: Path, edit) -> None:
    """Apply edit(run) to the tree's run record and renew its manifest's sha256 (so that only the edit is tested)."""
    d = root / "code" / "sim" / "out" / "fig1v2"
    run = json.loads((d / "run.json").read_text())
    edit(run)
    (d / "run.json").write_text(json.dumps(run))
    man = json.loads((d / "manifest.json").read_text())
    man["run_sha256"] = hashlib.sha256((d / "run.json").read_bytes()).hexdigest()
    (d / "manifest.json").write_text(json.dumps(man))


# ---------------------------------------------------------------------------------------------------------------
def test_registered_and_drawn_keys():
    """fig1v2's registration is the frozen fig1's size with the set (sublet_v2,), it has no LEGACY_PENDING entry, and
    the figure draws only that key; (a)'s reactions are drawn in its color."""
    assert fig1_v2.NAME == "fig1v2" and fig1_v2.KEY == "sublet_v2"
    spec, old = style.FIGURES["fig1v2"], style.FIGURES["fig1"]
    assert (spec.width, spec.height_in, spec.main) == (old.width, old.height_in, True) == ("W1", 2.4, True)
    assert style.FIGURE_POLICIES["fig1v2"] == (fig1_v2.KEY,) and "fig1v2" not in style.LEGACY_PENDING
    style.check_legacy()
    fig = fig1_v2.draw(fixture_data())
    assert drawn_keys(fig) == {fig1_v2.KEY}
    a = fig.axes[0]
    c = style.policy(fig1_v2.KEY).color
    dashed = [ln for ln in a.lines if ln.get_linestyle() == "--"]
    assert dashed and all(ln.get_color() == c for ln in dashed)            # the pre-warm


def test_from_extract_saves_and_finalize_passes(figs_env):
    """--from-extract on the fixture extract: save() under the temporary folders (finalize() passed), the registered
    page size, 9-10 pt text, the extract written equals the one read, and a redraw from the written extract gives the
    same PDF bytes."""
    rep = fig1_v2.main(["--from-extract", str(FIX / "fig1v2.json")])
    spec = style.figure_spec("fig1v2")
    assert Path(rep["pdf"]) == figs_env / "pdf" / "fig1v2.pdf" and Path(rep["pdf"]).is_file()
    assert abs(rep["width_bp"] - spec.width_in * 72) <= 0.5 and abs(rep["height_bp"] - spec.height_in * 72) <= 0.5
    assert rep["outside_page"] == [] and rep["pages"] == 1
    assert all(style.TEXT_MIN_PT <= s <= style.TEXT_MAX_PT for s in rep["text_pt"])
    assert rep["min_glyph_pt"] >= style.SCRIPT_MIN_PT - 1e-9
    assert not any("dejavu" in f.lower() for f in rep["fonts"])
    written = figs_env / "out" / "fig1v2.json"
    assert json.loads(written.read_text()) == fixture_payload()
    first = Path(rep["pdf"]).read_bytes()
    second = figs_env / "again"
    rep2 = style.save(fig1_v2.draw(json.loads(written.read_text())["data"]), "fig1v2",
                      json.loads(written.read_text())["data"], sources=fixture_payload()["sources"],
                      pdf_dir=second / "pdf", out_dir=second / "out")
    assert Path(rep2["pdf"]).read_bytes() == first
    assert (second / "out" / "fig1v2.json").read_text() == written.read_text()


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

    assert fig1_v2.main.__module__ == fig1_v2.__name__ and fig1_v2.cli is common.cli
    monkeypatch.setattr(inputs.Inputs, "extract", fake_extract)
    with pytest.raises(Stop):
        fig1_v2.main(["--from-extract"])
    monkeypatch.setattr(common, "read_extract", fake_read_extract)
    with pytest.raises(Stop):
        fig1_v2.main(["--from-extract", "some/extract.json"])
    assert calls == [("fig1v2", "Inputs.extract"), ("fig1v2", "some/extract.json")]


def test_build_on_the_input_tree_matches_the_fixture(figs_env, monkeypatch):
    """collect() on the input tree opens no repository file outside the result folders of the input root (patched
    open), records the run record and its manifest as its sources, and gives the fixture extract's data."""
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
    data = fig1_v2.collect(inp)
    monkeypatch.undo()
    for p in opened:
        if style.REPO in p.parents:
            assert IN_ROOT in p.parents, f"fig1v2 opened {p}"
            style.check_source(p.relative_to(IN_ROOT).as_posix())
    assert inp.sources == [fig1_v2.RUN, fig1_v2.MANIFEST] == fixture_payload()["sources"]
    from figs.common import json_number
    data = json.loads(json.dumps(data, allow_nan=False, default=json_number))
    assert data == fixture_data(), STALE


def test_extract_equals_the_run():
    """Every plotted value is the run record's series minus C_S; the projected slots and the inner list's values are
    the record's; the run's facts are copied; (a)'s labels carry contract k's subscripts (C-14)."""
    run = json.loads((RUN_DIR / "run.json").read_text())
    man = json.loads((RUN_DIR / "manifest.json").read_text())
    d, s = fixture_data(), run["series"]
    C_S = np.asarray(s["C_S"])
    assert d["excess"]["test_value"] == (np.asarray(s["test_value"]) - C_S).tolist()
    assert d["excess"]["threshold"] == (np.asarray(s["threshold"]) - C_S).tolist()
    proj = [t for t, p in enumerate(s["projected"]) if p]
    assert d["projected"] == proj and len(proj) == run["summary"]["projected_slots"] == d["projected_slots"] > 0
    assert d["inner_test_value"] == [s["inner_test_value"][t] for t in proj]
    assert d["excess"]["inner"] == [s["inner_test_value"][t] - s["C_S"][t] for t in proj]
    assert all(v is None for t, v in enumerate(s["inner_test_value"]) if t not in proj)
    assert d["t_h"] == s["t_h"] and d["n_slots"] == run["grid"]["T_slow"] and d["hours"] == 3.0
    assert (d["run_sha256"], d["git_revision"], d["reduced"]) == (man["run_sha256"], man["git_revision"], True)
    assert (d["cell"], d["mode"], d["policy_seed"], d["tag"], d["tag_params"]) == \
        (run["cell"], "L-eg", 0, "Sublet", {"inner": "A9", "project": True, "allowance": "lb", "kappa": None})
    assert d["ALG_T"] == run["summary"]["ALG_T"] and d["aborted"] is False
    a = d["labels"]["a"]
    assert (a["tau"], a["H"], a["s_tau"], a["s_D"], a["r_H"]) == (r"$\tau_k$", "$H_k$", r"$s+\tau_k$", "$s+D_k$",
                                                                  "$r+H_k$")
    assert a["window"].endswith(r"$D_k=\tau_k+H_k$")
    assert d["labels"]["b"]["threshold"] == "$C_S+B$" and d["gamma"] == 1.0


def test_threshold_ticks_at_the_projected_slots():
    """C47 (print check of the gate): at each projected slot a short grey tick at that slot's threshold (relative to
    C_S), centered on the slot's middle and fig1_v2.TICK_HALF_PT wide on either side, drawn over the executed line and
    under the circles, so that each circle shows above its own threshold (the threshold's first steps are a few pt
    wide)."""
    d = fixture_data()
    fig = fig1_v2.draw(d)
    ax = fig.axes[1]
    (ticks,) = [c for c in ax.collections if getattr(c, "_sublet_role", "") == "threshold_tick"]
    segs = ticks.get_segments()
    dt = d["slot_min"] / 60.0
    thr = [d["excess"]["threshold"][t] for t in d["projected"]]
    assert len(segs) == len(d["projected"]) == len(thr)
    half = fig1_v2.TICK_HALF_PT / (style.axes_rect_in(ax)[2] * style.BP_PER_IN / d["hours"])
    for (p0, p1), t, y in zip(segs, d["projected"], thr):
        mid = d["t_h"][t] + 0.5 * dt
        assert p0[1] == p1[1] == pytest.approx(y) and (p0[0], p1[0]) == (pytest.approx(mid - half),
                                                                         pytest.approx(mid + half))
    assert all(v > y for v, y in zip(d["excess"]["inner"], thr))
    assert style.mpl.colors.to_hex(ticks.get_colors()[0]) == style.mpl.colors.to_hex(style.THEORY_GREY)
    line = [ln for ln in ax.lines if getattr(ln, "_sublet_policy", "") == fig1_v2.KEY][0]
    assert line.get_zorder() < ticks.get_zorder() < style.POLICIES[fig1_v2.KEY].zorder + 0.05


def test_no_design_id_drawn():
    """No drawn text of the figure carries a design or experiment ID or a result's name: the caption carries them."""
    fig = fig1_v2.draw(fixture_data())
    texts = [t.get_text() for t in style.drawn_texts(fig)]
    assert texts and not [t for t in texts if DESIGN_ID.search(t)], texts
    names = {t.get_text() for t in style.drawn_texts(fig)}
    lab = fixture_data()["labels"]["b"]
    assert {lab["test"], lab["inner"], lab["threshold"], lab["C_S"]} <= names


def test_caption_draft():
    """The caption draft says what M1 requires, cites Theorem W(a), Remark R and Proposition P by their labels of
    design/ms6_spec.md §5, takes its numbers from the run, and fits the budget of a single-column caption."""
    d = fixture_data()
    cap = d["labels"]["caption"]
    # C47 (print check of the gate): the cell named (M1: "with the cell and the lender in the caption"), its span where
    # it is not the whole day; C47 (U46): in the paper's words, "one-day pilot instance, cell 1" (not "instance I2",
    # which reads as the information class I2), the threshold "(grey)" (its dashed line and its ticks), and the
    # conditions of Proposition 15 that the run meets with "no abort"
    for s in ("Illustrative run of Sublet", "eager stress lender", "no abort", "exceed",  # C47
              "stays under", f"the {d['projected_slots']} projected slots", "inner policy's proposals",
              r"\ref{lem:projection}", r"\ref{thm:fullmodel}(a)", r"\ref{prop:noabort}",
              "Sublet (one-day pilot instance, cell 1, first 3 h; eager stress lender)", "$C_S+B$ (grey) and",  # C47
              r"no abort ($S$ on all-fallback, T0g in bound form; Proposition~\ref{prop:noabort})."):         # C47
        assert s in cap, s
    assert d["s_fb_all"] and d["t0g_bound_all"]                                                          # C47
    assert not re.search(r"\bI2\b|development cell|grey ticks", cap), cap                                # C47
    assert [(r["design"], r["label"], r["paper"]) for r in d["labels"]["refs"]] == \
        [("Theorem W(a)", "thm:fullmodel", "Theorem 16"), ("Remark R", "lem:projection", "Lemma 11"),     # C48
         ("Proposition P", "prop:noabort", "Proposition 15")]
    assert d["labels"]["caption_lines_est"] <= fig1_v2.CAPTION_LINES
    full = fig1_v2.caption({**d, "hours": 24.0, "projected_slots": 38})
    assert "Sublet (one-day pilot instance, cell 1; eager stress lender): at the" in full           # C47
    # C47 (U46): a run that does not meet Proposition 15's conditions says "no abort" without citing it
    for k in ("s_fb_all", "t0g_bound_all"):  # C47
        bare = fig1_v2.caption({**d, "hours": 24.0, "projected_slots": 38, k: False})  # C47
        assert bare.endswith("Theorem~\\ref{thm:fullmodel}(a)); no abort.") and "prop:noabort" not in bare     # C47
    assert "the 38 projected slots" in full
    assert fig1_v2.printed_chars(full) <= fig1_v2.CAPTION_LINES * fig1_v2.CAPTION_LINE_CHARS
    assert [x["result"] for x in d["labels"]["status"]] == ["Theorem W(a), W(b)", "Remark R", "Proposition P",
                                                            "Lemma P.1"]
    assert all(x["status"].startswith("PROVEN") for x in d["labels"]["status"])


@pytest.mark.parametrize("case", ["sha", "checks", "aborted", "above", "inner_low", "none_projected"])
def test_collect_refuses(tmp_path, monkeypatch, case):
    """collect() fails on a record that its manifest does not match, on failed checks, on a run that aborted, on an
    executed test value above the threshold, on an inner test value not above it and on a run without a projected
    slot."""
    root = tree_copy(tmp_path)
    d = root / "code" / "sim" / "out" / "fig1v2"
    if case == "sha":
        run = json.loads((d / "run.json").read_text())
        run["summary"]["ALG_T"] += 1.0
        (d / "run.json").write_text(json.dumps(run))
        match = "differs from its manifest"
    elif case == "checks":
        man = json.loads((d / "manifest.json").read_text())
        man["checks"]["pass"] = False
        (d / "manifest.json").write_text(json.dumps(man))
        match = "checks do not pass"
    elif case == "aborted":
        rewrite_run(root, lambda r: r["summary"].update(aborted=True, t_a=20))
        match = "aborted"
    elif case == "above":
        def up(r):
            t = r["series"]["projected"].index(False)
            r["series"]["test_value"][t] = r["series"]["threshold"][t] + 1e-3
        rewrite_run(root, up)
        match = "exceeds the threshold"
    elif case == "inner_low":
        def low(r):
            t = r["series"]["projected"].index(True)
            r["series"]["inner_test_value"][t] = r["series"]["threshold"][t]
        rewrite_run(root, low)
        match = "does not exceed the threshold"
    else:
        def none(r):
            r["series"]["projected"] = [False] * len(r["series"]["projected"])
            r["summary"]["projected_slots"] = 0
        rewrite_run(root, none)
        match = "needs at least one"
    monkeypatch.setenv("SUBLET_FIGS_IN_ROOT", str(root))
    with pytest.raises(style.StyleError, match=match):
        fig1_v2.collect(Inputs())


def test_helpers():
    """The driver's run-length expansion and runs of projected slots; the figure's x ticks and printed-character
    count."""
    assert F._rle_expand([["P1", 0, 1], ["E", 1, 2], ["P0", 3, 1]]) == ["P1", "E", "E", "P0"]
    with pytest.raises(ValueError):
        F._rle_expand([["E", 1, 2]])
    assert F._runs([True, False, True, True, False, True]) == [[0, 0], [2, 3], [5, 5]]
    assert fig1_v2.x_ticks(24.0) == [0, 6, 12, 18, 24] and fig1_v2.x_ticks(3.0) == [0, 1, 2, 3]
    assert fig1_v2.x_ticks(2.0) == [0, 1, 2]
    assert fig1_v2.printed_chars(r"see Lemma~\ref{lem:projection} and $C_S+B$") == len("see Lemma 00 and CS+B")


def test_identical_detects_a_difference():
    """The driver's identity check compares the policy report, every per-slot series and the components bit for
    bit."""
    def res(total, rep=None, comps=None):
        return SimpleNamespace(metrics={"policy": rep or {"t_a": None}}, per_slot={"total": np.asarray(total)},
                               components=comps or {"total": float(sum(total))})
    a = res([1.0, 2.0])
    assert F.identical(a, res([1.0, 2.0]))["ok"]
    assert not F.identical(a, res([1.0, 2.0 + 1e-15]))["per_slot"]
    assert not F.identical(a, res([1.0, 2.0], rep={"t_a": 3}))["report"]
    assert not F.identical(a, res([1.0, 2.0], comps={"total": 3.5}))["components"]


def test_logging_subclass_is_outside_the_guard():
    """LoggedProjectedGuarded lives in the driver, overrides reset and _evaluate only, and is set only on an A8P
    object; algos/guard.py knows nothing of the log."""
    from sublet.algos import guard
    assert F.LoggedProjectedGuarded.__module__ == F.__name__
    assert issubclass(F.LoggedProjectedGuarded, guard.ProjectedGuarded)
    own = {k for k, v in vars(F.LoggedProjectedGuarded).items() if callable(v)}
    assert own == {"reset", "_evaluate"}
    src = Path(guard.__file__).read_text()
    assert "eval_log" not in src and "LoggedProjectedGuarded" not in src and "fig1_illustrative" not in src
    with pytest.raises(TypeError):
        F.logged(guard.Guarded.__new__(guard.Guarded))


def test_frozen_fig1_unchanged(tmp_path):
    """draw_timeline keeps the frozen fig1's key by default, and fig1 redraws from its versioned extract byte-identical
    to paper/figures/fig1.pdf (fig1 stays frozen, M1), and writes that extract unchanged. C62 (2026-11-24): the
    versioned PDF is now fig1's redraw at C62's type scale (7-pt text, 7.97-pt axis labels and letters), with (a)'s
    rows spaced for 7-pt text (fig1_guard.A_AXIS_DROP to A_REACT_DROP; (b)'s axes 1.12 in high, B_TOP 0.90 in), the
    window label and (b)'s peak label on the baselines of their rows; the test pins that redraw, as it pinned the 9-pt
    one, so that the frozen rebuild's fig1 stays exact. The extract (data, labels, sources) is the one of the MS3 runs."""
    assert inspect.signature(fig1_guard.draw_timeline).parameters["policy_key"].default == "sublet"
    ext = REPO / "code" / "sim" / "out" / "figs" / "fig1.json"
    payload = json.loads(ext.read_text())
    data = payload["data"]
    rep = style.save(fig1_guard.draw(data), "fig1", data, sources=payload["sources"], pdf_dir=tmp_path / "pdf",
                     out_dir=tmp_path / "out")
    assert Path(rep["pdf"]).read_bytes() == (REPO / "paper" / "figures" / "fig1.pdf").read_bytes()
    assert (tmp_path / "out" / "fig1.json").read_bytes() == ext.read_bytes()


def test_rebuild_lists_fig1v2_after_fig1(monkeypatch):
    """figs.rebuild lists fig1v2 from its script, right after fig1 (C42's order by N, then file name; C44's order of
    the print sheet), with the PDF, the extract and the preview as its outputs and the extract as its input."""
    for k in [k for k in style.FIGURES if k.startswith("test_")]:     # test-only figures of earlier modules
        monkeypatch.delitem(style.FIGURES, k)
    ents = rb.entries()
    main = [e for e in ents if e.kind == "main"]
    names = [e.name for e in main]
    assert names.index("fig1v2") == names.index("fig1") + 1
    e = main[names.index("fig1v2")]
    assert (e.script, e.module) == ("code/sim/figs/fig1_v2.py", "figs.fig1_v2")
    assert set(e.outputs) == {"paper/figures/fig1v2.pdf", "code/sim/out/figs/fig1v2.json",
                              "code/sim/out/figs/fig1v2.png"}
    assert e.extract == "code/sim/out/figs/fig1v2.json"


# ---------------------------------------------------------------- the full run (needs the a12 outputs)
@pytest.fixture(scope="module")
def full_run():
    """The cell's logged and unlogged runs, and the run record of the logged one (about 13 s)."""
    cell = F.build()
    res_l, pol_l = F.simulate(cell, log=True)
    res_u, pol_u = F.simulate(cell, log=False)
    run, log_check = F.record(res_l, pol_l, cell)
    return SimpleNamespace(cell=cell, res_l=res_l, pol_l=pol_l, res_u=res_u, pol_u=pol_u, run=run, log=log_check)


@pytest.mark.needs_a12
def test_logged_run_equals_unlogged_run(full_run):
    """The logged run (LoggedProjectedGuarded) and the unlogged run (ProjectedGuarded) of the same spec have the same
    policy report, per-slot costs and components, bit for bit."""
    r = full_run
    assert type(r.pol_l) is F.LoggedProjectedGuarded and type(r.pol_u).__name__ == "ProjectedGuarded"
    assert json.dumps(r.res_l.metrics["policy"], sort_keys=True, default=str) == \
        json.dumps(r.res_u.metrics["policy"], sort_keys=True, default=str)
    assert sorted(r.res_l.per_slot) == sorted(r.res_u.per_slot)
    for k in r.res_l.per_slot:
        assert np.array_equal(np.asarray(r.res_l.per_slot[k]), np.asarray(r.res_u.per_slot[k])), k
    assert r.res_l.components == r.res_u.components
    assert F.identical(r.res_l, r.res_u)["ok"]
    assert len(r.pol_l.eval_log) > r.run["grid"]["T_slow"] and not hasattr(r.pol_u, "eval_log")


@pytest.mark.needs_a12
def test_run_reproduces_the_pilot_record(full_run):
    """ALG(T) equals the pilot's record of the cell (tag Sublet, cell I2:c1, mode L-eg, seed 0) within 1e-9, with 38
    projected slots and no abort; the cell is the one-day instance on 288 slow slots."""
    s = full_run.run["summary"]
    assert abs(s["ALG_T"] - PILOT_ALG) <= 1e-9
    assert s["projected_slots"] == 38 and s["aborted"] is False and s["t_a"] is None
    assert full_run.run["grid"]["T_slow"] == 288 and full_run.run["window"] is None
    chk = F.pilot_check(full_run.run)
    assert chk["ok"] and chk["pilot"]["ALG"] == PILOT_ALG and chk["abs_diff"]["ALG"] <= 1e-9, chk


@pytest.mark.needs_a12
def test_log_agrees_with_the_guard(full_run):
    """The log check holds; at every projected slot A_E(t)'s test value is above the threshold and the executed one is
    not; the executed candidates are the report's."""
    run = full_run.run
    assert full_run.log["ok"], full_run.log["problems"]
    s = run["series"]
    proj = [t for t, p in enumerate(s["projected"]) if p]
    assert len(proj) == 38 and all(s["inner_test_value"][t] > s["threshold"][t] for t in proj)
    assert all(v <= h * (1 + 1e-12) for v, h in zip(s["test_value"], s["threshold"]))
    assert F._rle_expand(run["summary"]["candidates"]) == s["candidate"]
    assert run["summary"]["min_margin_usd"] > 0 and run["summary"]["inner_excess_usd"]["min"] > 0


@pytest.mark.needs_a12
def test_driver_main_and_figure_on_the_full_run(tmp_path, monkeypatch, full_run):
    """main() writes run.json (the record of the logged run, deterministic) and a manifest whose checks pass, with the
    run's sha256; the figure builds from them with finalize() passing and 38 projected slots in its extract."""
    out = tmp_path / "tree" / "code" / "sim" / "out" / "fig1v2"
    assert F.main(["--out", str(out)]) == 0
    man = json.loads((out / "manifest.json").read_text())
    assert man["checks"]["pass"] and man["checks"]["identical"]["ok"] and man["checks"]["pilot"]["ok"]
    assert man["run_sha256"] == hashlib.sha256((out / "run.json").read_bytes()).hexdigest()
    assert (man["mode"], man["policy_seed"], man["tag"], man["reduced"]) == ("L-eg", 0, "Sublet", False)
    assert json.loads((out / "run.json").read_text()) == json.loads(json.dumps(copy.deepcopy(full_run.run)))
    monkeypatch.setenv("SUBLET_FIGS_IN_ROOT", str(tmp_path / "tree"))
    monkeypatch.setenv(style.ENV_PDF_DIR, str(tmp_path / "pdf"))
    monkeypatch.setenv(style.ENV_OUT_DIR, str(tmp_path / "out"))
    rep = fig1_v2.main([])
    assert rep["outside_page"] == [] and all(style.TEXT_MIN_PT <= v <= style.TEXT_MAX_PT for v in rep["text_pt"])
    d = json.loads((tmp_path / "out" / "fig1v2.json").read_text())["data"]
    assert d["projected_slots"] == 38 and d["hours"] == 24.0 and d["reduced"] is False
    assert "Sublet (one-day pilot instance, cell 1; eager stress lender)" in d["labels"]["caption"]   # C47
    assert d["labels"]["caption_lines_est"] <= fig1_v2.CAPTION_LINES


# ---------------------------------------------------------------- C62 (2026-11-24): fig1 and fig1v2 at 7 pt
def test_fig1_fig1v2_c62_rows_on_one_baseline():
    """C62: (a) of fig1 and fig1v2 is spaced for 7-pt text (fig1_guard's A_* rows, fig1_v3's minimum gaps; (b) 0.90 in
    below the top) and its texts that share a row print on one baseline (common.printed_baselines_pt, the PDF's
    metrics): the window label on its panel letter's (it is mathtext, which the PDF backend raises by up to 1 pt), the
    five marks' labels on one; in fig1's (b), the test value's label beside t_a's prints on t_a's baseline."""
    from figs.common import printed_baselines_pt
    assert (fig1_guard.A_AXIS_DROP, fig1_guard.A_MARK_DROP, fig1_guard.A_BRACKET_UP, fig1_guard.A_DRAIN_UP,
            fig1_guard.A_REACT_DROP, fig1_guard.B_TOP) == (0.26, 0.125, 0.08, 0.17, 0.235, 0.90)
    fig1_data = json.loads((REPO / "code" / "sim" / "out" / "figs" / "fig1.json").read_text())["data"]
    for name, fig, lab_a in (("fig1", fig1_guard.draw(fig1_data), fig1_data["labels"]["a"]),
                             ("fig1v2", fig1_v2.draw(fixture_data()), fig1_v2.LABELS_A)):
        a, b = fig.axes
        assert style.axes_rect_in(b)[1] + style.axes_rect_in(b)[3] == pytest.approx(2.4 - 0.90, abs=1e-6), name
        letter = next(t for t in fig.texts if t.get_text() == "(a)")
        window = next(t for t in a.texts if t.get_text() == lab_a["window"])
        marks = [next(t for t in a.texts if t.get_text() == lab_a[k]) for k in ("s", "s_tau", "r", "s_D", "r_H")]
        base = printed_baselines_pt(fig, [letter, window, *marks])
        assert abs(base[1] - base[0]) < 0.05, (name, base[:2])
        assert max(base[2:]) - min(base[2:]) < 0.05, (name, base[2:])
        if name == "fig1":
            t_a = next(t for t in b.texts if t.get_text() == fig1_data["labels"]["b"]["t_a"])
            peak = next(t for t in b.texts if t.get_text() == fig1_data["labels"]["b"]["test"])
            assert getattr(peak, "_sublet_baseline_shift_pt", None) is not None
            b_peak, b_t = printed_baselines_pt(fig, [peak, t_a])
            assert abs(b_peak - b_t) < 0.05
