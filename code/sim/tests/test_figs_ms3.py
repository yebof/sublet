"""Tests of the MS3 figure scripts of unit U17a (design/sim_spec_ms3.md §10, row test_figs_ms3.py, for Figs. 1, 2, 3,
the supplementary sf_e11_inst, sf_e11_fam and sf_e11_guard, and the print sheet). Quick: every file is written under
pytest's tmp_path; the fixture extracts and the Fig. 1(b) selection-rule folder are in tests/fixtures_figs/.

- Each script redraws its figure with --from-extract from a fixture extract (tests/fixtures_figs/<name>.json, read
  through SUBLET_FIGS_IN_ROOT) and saves under temporary SUBLET_FIGS_*_DIR with finalize() passing, which includes
  the check that no ink lies outside the page (style.texts_outside_page, at every figure size; its own tests are in
  test_figs_style.py); the extract it writes equals the one it read; sf_e11_guard's table goes to
  SUBLET_FIGS_TABLES_DIR (figs.common.tables_dir).
- The registry keys each figure draws are within FIGURE_POLICIES (main text) or SUPP_POLICIES (C13), and
  check_policies passes on them.
- Fig. 1(b)'s selection rule (§8.1, M51) picks the first held-out aborted run with fb_after_t_a and W_S(t_a) = 0 in
  sorted path order and fails when none qualifies; collect() on a synthetic one-day run gives the series of §8.1.
- Every 'limit' theory label says "limit" or T→∞; Fig. 3(a) has its shaded criteria region; Fig. 3(c)'s G3(b) is
  Corollary G3(b) at the run's inputs; Fig. 2's check E1-1 passes on the versioned a11 file.
- No script opens a path outside the allowed roots (patched open).
- MS6 (design/ms6_spec.md §1.1 M2-M6, unit U43a; C47 for each changed pin): Fig. 3's arrows join the configuration
  keys; no drawn text of Figs. 3, 5, 6 and 7 holds a design or experiment ID or the name Sublet (M6, M17); Fig. 3 and
  sf_e11_inst draw M5's paired legend and no legacy key, sf_e11_inst dodges each guarded configuration right of its
  inner policy, sf_e11_fam's keys pair two samples with a short text and keep the names for the caption, and
  sf_e11_guard's legend is a row over its panels.

C50 (design/ms6_spec.md §7.2, the D5 review; §7.1 D4's script items): e11_scope.tex's caption leaves the definitions
of r_best and r_0 to the supplement's text, so that the float fits its page without an \\arraystretch override. Each
changed line names C50.

C62 (2026-11-24: the type scale of the caption; figures high-end, informative, readable): Fig. 2's layout for
the smaller text (test_fig2_c62_layout_keys_and_clearances): (a)'s pool key on the letter's baseline, the MaaS label
in its band, the named 100% line, no minor ticks on its log y axis; (b)'s tier key inside the panel, each entry a
marker on its own min-max bar, the bars apart, the scenario bar placed from its labels; the guards that keep labels and
keys off the data; the layout at 2.5 in.
"""
from __future__ import annotations

import builtins
import importlib
import io
import json
import math
import re
import shutil
from pathlib import Path

import numpy as np
import pytest
from matplotlib.patches import Rectangle

from figs import style
from figs import common as figs_common
from figs import inputs as figs_inputs

pytestmark = pytest.mark.filterwarnings("ignore::figs.style.FigureWarning")

FIX = Path(__file__).resolve().parent / "fixtures_figs"
REPO = style.REPO
SCRIPTS = {   # figure name: (module, main text)
    "fig1": ("figs.fig1_guard", True),
    "fig2": ("figs.fig2_e1a", True),
    "fig3": ("figs.fig3_e11", True),
    "sf_e11_inst": ("figs.supp.sf_e11_inst", False),
    "sf_e11_fam": ("figs.supp.sf_e11_fam", False),
    "sf_e11_guard": ("figs.supp.sf_e11_guard", False),
}
ALLOWED_IN = ("code/analysis/out/", "code/sim/out/")


def _module(name):
    return importlib.import_module(SCRIPTS[name][0])


def _fixture(name) -> dict:
    return json.loads((FIX / f"{name}.json").read_text())


def _env(monkeypatch, tmp_path) -> dict:
    d = {"in": tmp_path / "in", "pdf": tmp_path / "pdf", "out": tmp_path / "out", "tab": tmp_path / "tab"}
    for v in d.values():
        v.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv(figs_inputs.ENV_IN_ROOT, str(d["in"]))
    monkeypatch.setenv(style.ENV_PDF_DIR, str(d["pdf"]))
    monkeypatch.setenv(style.ENV_OUT_DIR, str(d["out"]))
    monkeypatch.setenv(figs_common.ENV_TABLES_DIR, str(d["tab"]))
    return d


def _place_extract(d, name):
    tgt = d["in"] / "code/sim/out/figs" / f"{name}.json"
    tgt.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(FIX / f"{name}.json", tgt)


def _drawn_keys(fig) -> list:
    return sorted({getattr(a, "_sublet_policy") for ax in fig.axes for a in ax.get_children()
                   if hasattr(a, "_sublet_policy")})


class _OpenLog:
    """Records every path opened through builtins.open and io.open while installed."""

    def __init__(self):
        self.paths = []
        self._open = builtins.open

    def __call__(self, file, *a, **k):
        if isinstance(file, (str, Path)):
            self.paths.append(Path(file).resolve())
        return self._open(file, *a, **k)


def _check_paths(paths, d):
    """Paths in the repository or the temporary folders must lie under an allowed root."""
    in_root = d["in"].resolve()
    outs = [d[k].resolve() for k in ("pdf", "out", "tab")]
    bad = []
    for p in paths:
        if any(p.is_relative_to(o) for o in outs):
            continue
        for root in (in_root, REPO):
            if p.is_relative_to(root):
                rel = p.relative_to(root).as_posix()
                ok = rel.startswith(ALLOWED_IN) or (rel.startswith("code/theory_checks/") and
                                                    "out" in Path(rel).parts[2:-1])
                if not ok and not (root == REPO and rel.startswith("code/sim/figs/")):
                    bad.append(str(p))
                break
    return bad


# ---------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("name", list(SCRIPTS))
def test_from_extract_redraws_and_passes_finalize(name, monkeypatch, tmp_path):
    d = _env(monkeypatch, tmp_path)
    _place_extract(d, name)
    mod = _module(name)
    log = _OpenLog()
    monkeypatch.setattr(builtins, "open", log)
    monkeypatch.setattr(io, "open", log)
    rep = mod.main(["--from-extract"])
    monkeypatch.undo()
    assert _check_paths(log.paths, d) == []
    spec = style.figure_spec(name)
    assert abs(rep["width_bp"] - spec.width_in * 72) <= 0.5 and abs(rep["height_bp"] - spec.height_in * 72) <= 0.5
    assert rep["outside_page"] == [] and rep["pages"] == 1
    assert all(style.TEXT_MIN_PT <= s <= style.TEXT_MAX_PT for s in rep["text_pt"])
    assert not any("dejavu" in f.lower() for f in rep["fonts"])
    pdf = Path(rep["pdf"])
    assert pdf.parent == d["pdf"] and pdf.is_file()
    got = json.loads((d["out"] / f"{name}.json").read_text())
    want = _fixture(name)
    assert got["data"] == want["data"] and got["sources"] == want["sources"]
    if name == "sf_e11_guard":
        tex = (d["tab"] / "e11_scope.tex").read_text()
        assert tex.startswith(r"\begin{table*}") and r"\toprule" in tex and tex.rstrip().endswith(r"\end{table*}")
        # C50 (D5 review; D4's script items): r_best and r_0 are defined in the text before the table (s_f1.tex)
        cap = tex[tex.index(r"\caption{"):tex.index(r"\label{tab:e11-scope}")]                             # C50
        assert r"is the cost over the cheapest" not in cap and "Paired columns" in cap                      # C50


@pytest.mark.parametrize("name,inputs", [("fig2", ("code/analysis/out/a9b_notice_buffer_24h.json",
                                                    "code/analysis/out/a11_calibration.json")),
                                         ("sf_e11_inst", ("code/sim/out/e11/summary.json",))])
def test_normal_mode_on_the_versioned_inputs(name, inputs, monkeypatch, tmp_path):
    """The scripts whose inputs are versioned run from them: they open nothing outside the allowed roots, record
    exactly those inputs as sources, and write the extract of the fixture (the real extract)."""
    if not all((REPO / p).is_file() for p in inputs):
        pytest.skip(f"missing {inputs}")
    d = _env(monkeypatch, tmp_path)
    monkeypatch.delenv(figs_inputs.ENV_IN_ROOT)                 # read the repository's files
    mod = _module(name)
    log = _OpenLog()
    monkeypatch.setattr(builtins, "open", log)
    monkeypatch.setattr(io, "open", log)
    mod.main([])
    monkeypatch.undo()
    assert _check_paths(log.paths, d) == []
    assert {REPO / p for p in inputs} <= set(log.paths)
    got = json.loads((d["out"] / f"{name}.json").read_text())
    assert got["sources"] == list(inputs)
    assert got["data"] == _fixture(name)["data"], (
        f"tests/fixtures_figs/{name}.json differs from the extract built on the versioned inputs: rerun the script on "
        f"the real inputs (code/sim/out/figs/{name}.json), then `python tests/fixtures_figs/refresh_extracts.py` from "
        "code/sim")


@pytest.mark.parametrize("name", list(SCRIPTS))
def test_registry_keys_and_policy_checks(name):
    mod = _module(name)
    fig = mod.draw(_fixture(name)["data"])
    drawn = _drawn_keys(fig)
    allowed = style.FIGURE_POLICIES[name] if SCRIPTS[name][1] else style.SUPP_POLICIES[name]
    assert set(drawn) <= set(allowed), (name, drawn)
    assert set(getattr(mod, "KEYS")) <= set(allowed)
    style.check_policies(drawn)
    if SCRIPTS[name][1]:
        assert not set(drawn) & set(style.SUPP_ONLY_KEYS)
    for leg in fig.legends + [ax.get_legend() for ax in fig.axes if ax.get_legend() is not None]:
        labels = [t.get_text() for t in leg.get_texts()]
        assert all(lab for lab in labels)


@pytest.mark.parametrize("name", list(SCRIPTS))
def test_limit_labels_say_limit(name):
    fig = _module(name).draw(_fixture(name)["data"])
    for ax in fig.axes:
        for t in ax.texts:
            if getattr(t, "_sublet_role", "") == "theory_label:limit":
                s = t.get_text()
                assert "limit" in s.lower() or "T→∞" in s or "\\infty" in s, s


# ---------------------------------------------------------------------------------------------------------------
def test_fig1_selection_rule_picks_first_qualifying(monkeypatch, tmp_path):
    from figs import fig1_guard as f1
    monkeypatch.setenv(figs_inputs.ENV_IN_ROOT, str(FIX / "fig1_rule"))
    inp = figs_inputs.Inputs()
    name, run = f1.select_run(inp)
    assert name == "code/sim/out/e11/runs/Q1/I2/1min/L-eg/BL5-G_c2_l2_p2.json"
    assert f1.qualifies(run)
    # the files read to evaluate the rule are recorded as sources, in path order, up to the chosen one
    assert inp.sources[-1] == name and inp.sources == sorted(inp.sources)
    # none qualifies: the script fails
    root = tmp_path / "rule"
    sub = "code/sim/out/e11/runs/Q1/I2/1min/L-eg"
    (root / sub).mkdir(parents=True)
    for n in ("BL5-G_c1_l1_p0.json", "BL5-G_c2_l2_p0.json", "BL5-G_c2_l2_p1.json", "BL5-G_c3_l3_p1.json"):
        shutil.copy(FIX / "fig1_rule" / sub / n, root / sub / n)
    monkeypatch.setenv(figs_inputs.ENV_IN_ROOT, str(root))
    with pytest.raises(f1.SelectionError, match="no run file"):
        f1.select_run(figs_inputs.Inputs())


def _synthetic_run(t_a=100, slots=288, gamma=1.0, B0=10.0):
    rng = np.random.default_rng(0)
    q = np.r_[0.0, rng.uniform(0, 3, slots - 1)]
    C_S = np.cumsum(q)
    B = np.minimum(B0, 10 * np.cumsum(q > 0) * 0.2)
    a_hat = C_S[: t_a + 1] + np.linspace(0, 0.8 * B0, t_a + 1)
    a_hat[-1] = gamma * C_S[t_a] + B[t_a] + 1.0                      # the abort
    alg = np.r_[a_hat[:t_a], C_S[t_a:] + ((a_hat[t_a - 1] - C_S[t_a - 1]) if t_a else 0.0)]
    flags = dict(aborted=True, fb_after_t_a=True, held=True, proven_case=True, core_bound_ok=True, e_mode_ok=True)
    return {
        "meta": {"git_revision": "f" * 40},
        "metrics": {"policy": {
            "guard": {"t_a": t_a, "gamma": gamma, "B0": B0, "slots": list(range(t_a + 1)), "a_hat": a_hat.tolist(),
                      "reserve": [0.0] * (t_a + 1), "rhs": (gamma * C_S[: t_a + 1] + B[: t_a + 1]).tolist()},
            "safe": {"C_S_curve": C_S.tolist(), "B_curve": B.tolist()}}},
        "q44": {"tuning": False, "instance": "I2", "mode": "L-eg", "tag": "BL5-G",
                "seeds": {"config": 2, "lender": 2, "policy": 0},
                "certificate": dict(flags, W_S_t_a=0.0, t_a=t_a, ALG_T=float(alg[-1]), ALG_per_slot=alg.tolist(),
                                    core_bound_rhs=float(C_S[-1] + (gamma - 1.0) * (C_S[t_a - 1] if t_a else 0.0)
                                                         + (B[t_a - 1] if t_a else 0.0)))},
    }


def test_fig1_collect_on_a_synthetic_run(monkeypatch, tmp_path):
    from figs import fig1_guard as f1
    d = _env(monkeypatch, tmp_path)
    run = _synthetic_run()
    p = d["in"] / "code/sim/out/e11/runs/Q1/I2/1min/L-eg/BL5-G_c2_l2_p0.json"
    p.parent.mkdir(parents=True)
    p.write_text(json.dumps(run))
    data = json.loads(json.dumps(f1.collect(figs_inputs.Inputs())))
    assert data["t_a"] == 100 and data["slot_min"] == 5.0 and len(data["t_h"]) == 288
    assert data["t_h"][12] == 1.0 and data["tuning"] is False and data["same_as_first_study"] is None
    C_S = np.asarray(run["metrics"]["policy"]["safe"]["C_S_curve"])
    np.testing.assert_allclose(data["excess"]["threshold"],
                               np.asarray(data["threshold"]) - C_S, rtol=0, atol=1e-12)
    np.testing.assert_allclose(data["test_value"], run["metrics"]["policy"]["guard"]["a_hat"], atol=1e-12)
    assert len(data["ALG_after"]) == 288 - 100 and data["excess"]["test_value"][-1] > data["excess"]["threshold"][100]
    rep = style.save(f1.draw(data), "fig1", data)
    assert rep["outside_page"] == []
    # a guard record whose threshold is not gamma C_S + B is rejected
    run["metrics"]["policy"]["guard"]["rhs"][5] += 1.0
    p.write_text(json.dumps(run))
    with pytest.raises(style.StyleError, match="rhs"):
        f1.collect(figs_inputs.Inputs())
    # a run that is not one day long is rejected
    run = _synthetic_run(slots=200)
    p.write_text(json.dumps(run))
    with pytest.raises(style.StyleError, match="one day"):
        f1.collect(figs_inputs.Inputs())
    # an abort at slot 0: C_S(t_a - 1) and B(t_a - 1) are 0 (q44_study.certificate's convention), so Theorem W(b)'s
    # bound is C_S(T); a bound that differs from the certificate's core_bound_rhs is rejected
    run = _synthetic_run(t_a=0)
    p.write_text(json.dumps(run))
    data = json.loads(json.dumps(f1.collect(figs_inputs.Inputs())))
    assert data["t_a"] == 0 and data["bound_W_b"] == pytest.approx(
        run["metrics"]["policy"]["safe"]["C_S_curve"][-1], rel=1e-15)
    assert style.save(f1.draw(data), "fig1", data)["outside_page"] == []
    run["q44"]["certificate"]["core_bound_rhs"] += 1.0
    p.write_text(json.dumps(run))
    with pytest.raises(style.StyleError, match="core_bound_rhs"):
        f1.collect(figs_inputs.Inputs())


# ---------------------------------------------------------------------------------------------------------------
def test_fig2_rho_formula_and_check_e1_1():
    from figs import fig2_e1a as f2
    # a11's formula rho = 1 + (1 + phi / alpha) lambda / (60 D_pd) with alpha = a0 * multiplier / q_GPU
    assert f2.rho(60.0, 5.0, 2.0, 1.0, 4.0, 1.0) == pytest.approx(1.0 + 3.0 * 60.0 / 300.0)
    a11 = REPO / "code/analysis/out/a11_calibration.json"
    if not a11.is_file():
        pytest.skip("code/analysis/out/a11_calibration.json is missing")
    b = f2.collect_b(figs_inputs.Inputs())
    assert b["E1_1"]["pass"] and b["E1_1"]["max_rel_err"] <= 1e-12
    sh = b["shares_rho_le_2"]
    assert 0 < sh["default_scenarios"]["n"] < sh["all"]["n"] and 0 <= sh["all"]["share"] <= 1
    assert sum(p["n"] for p in b["points"]) == sh["all"]["n"]
    assert all(p["min"] <= p["median"] <= p["max"] for p in b["points"])


def _log_interp(x, xs, ys):                                                                                    # C62
    return 10 ** np.interp(np.log10(x), np.log10(xs), np.log10(ys))                                          # C62


def test_fig2_c62_layout_keys_and_clearances(monkeypatch, tmp_path):                                         # C62
    """C62: (a)'s spot-pool key is one row above the axes whose text shares the panel letter's baseline, its right end
    at the axes' right end, one entry per pool in the extract's order; the MaaS label lies inside the band, above the
    median line and below the band's top, over its whole span; the 100% line and rho = 2 are named by labels.a_ref and
    labels.b_ref in the reference-label grey. (b)'s tier key lies inside the axes and left of the scenario bar, titled
    labels.b_range, one entry per tier; the bar has no outline, its labels are the scenarios' short names and end at
    the axes' right end, and it is CBAR_CLEAR_IN clear of the rightmost marker. Each entry of the tier key is a marker
    on its own min-max bar: the bars are centered on their markers, show at least KEY_STEM_PT beyond them, lie
    KEY_BAR_GAP_PT apart and below the title's baseline (the first C62 build joined them into one line). (a)'s log y
    axis has no minor ticks; (b)'s markers are B_MARKER_PT; the label of rho = 2 ends REF_LABEL_PT[0] short of its
    line. Moving the tier key or the MaaS label onto the data, packing the key's rows too tightly for the bars, or
    asking for more room before the bar than the labels leave, fails the script. At 2.5 in (should the page budget
    force it; the figure is registered at 2.7 in) the figure passes finalize() with no warning."""
    import warnings
    from matplotlib.font_manager import FontProperties
    from matplotlib.lines import Line2D
    from figs import fig2_e1a as f2
    data = _fixture("fig2")["data"]
    lab = data["labels"]
    fig = f2.draw(data)
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    pt = fig.dpi / style.BP_PER_IN
    a, b = fig.axes[0], fig.axes[1]
    ae, be = a.get_window_extent(r), b.get_window_extent(r)
    letters = [t for t in fig.texts if getattr(t, "_sublet_role", "") == "panel_letter"]
    assert [t.get_text() for t in letters] == ["(a)", "(b)"]
    # (a): the pool key on the letter's baseline, right-aligned with the axes
    la = a.get_legend()
    assert [t.get_text() for t in la.get_texts()] == [v["label"] for v in data["a"]["pools"].values()]
    ea = la.get_window_extent(r)
    _, _, descent = r.get_text_width_height_descent("lp", FontProperties(size=style.TICK_PT), ismath=False)
    base = letters[0].get_transform().transform(letters[0].get_position())[1]
    assert all(abs(t.get_window_extent(r).y0 + descent - base) <= 0.5 * pt for t in la.get_texts())
    assert ea.y0 >= ae.y1 - 0.5 * pt and abs(ea.x1 - ae.x1) <= 0.5 * pt
    assert ea.x0 > letters[0].get_window_extent(r).x1
    # (a): the MaaS label inside its band, above the median line, over its whole span
    (maas,) = [t for t in a.texts if t.get_text() == lab["a_maas"]]
    mb = maas.get_window_extent(r)
    inv = a.transData.inverted()
    (x0, y0), (x1, y1) = inv.transform((mb.x0, mb.y0)), inv.transform((mb.x1, mb.y1))
    W, m = data["a"]["windows_min"], data["a"]["maas"]
    span = np.geomspace(x0, x1, 50)
    assert y0 > 100 * _log_interp(span, W, m["median"]).max() and y1 < 100 * _log_interp(span, W, m["max"]).min()
    # the reference lines' labels
    grey = style.THEORY_LABEL_GREY
    for ax, want in ((a, lab["a_ref"]), (b, lab["b_ref"])):
        refs = [t for t in ax.texts if getattr(t, "_sublet_role", "") == "reference_label"]
        assert [t.get_text() for t in refs] == [want] and refs[0].get_color() == grey
    assert lab["a_ref"] == "Mean capacity"
    # (b): the tier key inside the axes, left of the scenario bar
    lb = b.get_legend()
    assert lb.get_title().get_text() == lab["b_range"]
    assert [t.get_text() for t in lb.get_texts()] == [lab["b_tiers"][t] for t in data["b"]["tiers"]]
    eb = lb.get_window_extent(r)
    (cax,) = b.child_axes
    ce = cax.get_window_extent(r)
    assert be.x0 < eb.x0 and eb.x1 < ce.x0 and be.y0 < eb.y0 and eb.y1 <= be.y1 + 0.5 * pt
    # (b): the scenario bar, its labels, no outline, clear of the rightmost marker
    assert [t.get_text() for t in cax.get_yticklabels()] == data["b"]["scenario_short"]
    assert max(t.get_window_extent(r).x1 for t in cax.get_yticklabels()) <= be.x1 + 0.5 * pt
    assert not cax.spines["outline"].get_visible()
    xs = [p["D_pd"] * d for p in data["b"]["points"] for t, d in zip(data["b"]["tiers"], data["b"]["dodge"])
          if p["tier"] == t]
    right = b.transData.transform((max(xs), 1.0))[0] + f2.b_marker_half_pt() * pt
    assert ce.x0 - right >= f2.CBAR_CLEAR_IN * fig.dpi - 1e-6
    # (b)'s tier key: each tier marker on its own min-max bar, the bars apart and below the title's baseline
    bars = [l for l in lb.legend_handles]
    dots = [c for c in lb.findobj(Line2D) if c.get_marker() not in ("None", None, "")]
    assert [d.get_marker() for d in dots] == [f2.TIER_MARKERS[t] for t in data["b"]["tiers"]]
    assert all(d.get_markersize() == f2.B_MARKER_PT for d in dots)
    bx = [bb.get_window_extent(r) for bb in bars]
    for e, d in zip(bx, dots):
        cy = d.get_transform().transform(d.get_xydata())[0, 1]
        assert abs(0.5 * (e.y0 + e.y1) - cy) <= 0.05 * pt
        assert 0.5 * (e.y1 - e.y0) >= (f2.marker_half_pt(d.get_marker()) + f2.KEY_STEM_PT) * pt - 1e-6
    assert all(bx[i].y0 - bx[i + 1].y1 >= f2.KEY_BAR_GAP_PT * pt - 1e-6 for i in range(len(bx) - 1))
    assert lb.get_title().get_window_extent(r).y0 + descent - bx[0].y1 >= f2.KEY_BAR_GAP_PT * pt - 1e-6
    # (b)'s medians at B_MARKER_PT; (a)'s log y axis without minor ticks; rho = 2's label short of its line's end
    meds = [l for l in b.lines if l.get_marker() in f2.TIER_MARKERS.values()]
    assert len(meds) == len(data["b"]["points"]) and {l.get_markersize() for l in meds} == {f2.B_MARKER_PT}
    assert len(a.yaxis.get_minorticklocs()) == 0
    (ref_b,) = [t for t in b.texts if getattr(t, "_sublet_role", "") == "reference_label"]
    line_end = max(l.get_window_extent(r).x1 for l in b.lines if l.get_marker() in ("None", None, "")
                   and len(l.get_ydata()) == 2 and l.get_ydata()[0] == l.get_ydata()[1] == 2.0)
    assert line_end - ref_b.get_window_extent(r).x1 >= f2.REF_LABEL_PT[0] * pt - 0.5
    # the guards: a key, a label or the bar moved onto the data fails the script
    for attr, value, match in (("KEY_X", 6.0, "tier key"), ("MAAS_LABEL_X", 5.0, "MaaS label"),
                               ("CBAR_CLEAR_IN", 1.0, "scenario bar"), ("KEY_ROW_EM", 0.0, "tier key's rows")):
        with monkeypatch.context() as mp:
            mp.setattr(f2, attr, value)
            with pytest.raises(style.StyleError, match=match):
                f2.draw(data)
    # the layout at 2.5 in
    d = _env(monkeypatch, tmp_path)
    monkeypatch.setitem(style.FIGURES, "fig2", style.FigureSpec("fig2", "W1", 2.5))
    with warnings.catch_warnings():
        warnings.simplefilter("error", style.FigureWarning)
        rep = style.save(f2.draw(data), "fig2", data)
    assert abs(rep["height_bp"] - 2.5 * 72) <= 0.5 and rep["outside_page"] == []
    assert Path(rep["pdf"]).parent == d["pdf"]


def test_fig3_shaded_region_and_g3b():
    from figs import fig3_e11 as f3
    data = _fixture("fig3")["data"]
    fig = f3.draw(data)
    ax = fig.axes[0]
    rects = [p for p in ax.patches if isinstance(p, Rectangle) and
             np.allclose(p.get_facecolor()[:3], np.array([0xEF, 0xEF, 0xEF]) / 255.0)]
    assert len(rects) == 1
    r = rects[0]
    cr = data["a"]["criteria"]
    assert r.get_x() == pytest.approx(ax.get_xlim()[0]) and r.get_y() == pytest.approx(ax.get_ylim()[0])
    assert r.get_x() + r.get_width() == pytest.approx(1.0 + cr["x_T"])
    assert r.get_y() + r.get_height() == pytest.approx(1.0 + cr["y_S"])
    # Corollary G3(b) at the defaults: (1 + gamma) c(gamma') + kappa = 2 (3 + 2 sqrt 2) + 10 (design Table 2.10)
    assert f3.c_gamma(1 + 1 / math.sqrt(2)) == pytest.approx(3 + 2 * math.sqrt(2), rel=1e-14)
    assert f3.g3b(1e9, 1.0, 192, 1, 2, 1.0, 1 + 1 / math.sqrt(2), 10.0) == pytest.approx(
        (16 + 4 * math.sqrt(2)) * (4 * math.ceil(2 * math.log(192)) * math.log(4) + 1), rel=1e-14)
    assert f3.g3b(5.0, 1.0, 192, 1, 2, 1.0, 1 + 1 / math.sqrt(2), 10.0) == pytest.approx(
        5.0 * (16 + 4 * math.sqrt(2)), rel=1e-14)
    assert f3.parse_mK("check_c4_lower.single(192, [(1, 1), (192, 0)], 2, [1.0, 1.3])") == (1, 2)
    with pytest.raises(style.StyleError):
        f3.parse_mK("fam.build(8, 16)")
    for row, v in zip(data["c"]["G3b_inputs"], data["c"]["G3b"]):
        assert v == pytest.approx(f3.g3b(row["q_sigma"], row["OPT_eager"], row["N"], row["m"], row["K"],
                                         row["gamma"], row["gamma_T11"], row["kappa"]), rel=1e-12)
    # the arrows run from each inner policy to its guarded version
    # C47 (design/ms6_spec.md M2-M4): the configuration keys of Algorithm 1's defaults in place of the legacy keys
    assert data["a"]["arrows"] == [["bl5_lag", "bl5_g1"], ["a7", "a7_g1"], ["bl1", "bl1_g1"]]


def test_mode_labels_and_scope_table():
    from figs.supp import sf_e11_guard as g
    assert g.mode_label("L-iid-0.05") == "i.i.d. 0.05" and g.mode_label("L-tr") == "trace"   # C47: the table's name
    assert g.mode_label("L-co") == "correlated"                                               # C47: was "corr."
    data = _fixture("sf_e11_guard")["data"]
    tex = g.scope_table(data["scope"])
    # C47 (design/ms6_spec.md M2, M5): a guarded configuration's column (tag "<inner>-G") stands beside its inner
    # policy's under the inner policy's name, headed "+ one-way guard" (with the configurations' names as headers the
    # table was wider than the page); every other policy is named by its registry label
    tags = data["scope"]["tags"]
    for t, lab in zip(tags, data["scope"]["tag_labels"]):
        if not (t.endswith("-G") and t[:-2] in tags):
            assert all(w in tex for w in lab.split()), lab
    guarded = sum(t.endswith("-G") and t[:-2] in tags for t in tags)
    assert guarded == 3 and tex.count(r"\shortstack{+ one-way\\guard}") == guarded
    assert tex.count(r"\shortstack{inner\\policy}") == guarded and tex.count(r"\cmidrule") == guarded
    assert tex.count(r"\\") >= len(data["scope"]["rows"]) + len(data["scope"]["headroom"])
    # every (mode, metric) that D6 compares is a row (the i.i.d. lender's r_0 too); a headroom mode without an LB
    # is listed in the extract, not as a row of dashes
    assert {(r["mode"], r["metric"]) for r in data["scope"]["rows"]} == set(g.SCOPE_METRICS)
    assert r"i.i.d.\ 0.05, $r_0$" in tex and "L-ad" not in tex
    assert data["scope"]["headroom_without_lb"] and all(h["h"] is not None for h in data["scope"]["headroom"])
    assert not any(set(l.split("&")[3:]) <= {" -- ", " -- \\\\"} for l in tex.splitlines() if l.count("&") > 3)
    # the A8 run files counted are the summary's (full model and core)
    c = data["certificates"]
    assert c["matches_summary"] and c["full"] == c["summary_full_model"]["runs"]
    assert c["core"] == c["summary_core"]["runs"] and c["held"] == c["runs"]


def test_print_sheet(monkeypatch, tmp_path):
    import fitz
    from figs import print_sheet
    _env(monkeypatch, tmp_path)
    for name in ("fig1", "fig3"):
        style.save(_module(name).draw(_fixture(name)["data"]), name, {"x": [1]})
    rep = print_sheet.main([])
    assert [r["figure"] for r in rep["included"]] == ["fig1", "fig3"]
    # C45: C41 registers fig4v2 and C44 orders it after fig4 (design/sublet_v2.md §11, W1, W12); C47: C46 registers
    # fig1v2, ordered after fig1 (design/ms6_spec.md M1)
    assert rep["skipped"] == ["fig1v2", "fig1v3", "fig2", "fig4", "fig4v2", "fig4v3", "fig5", "fig6",
                              "fig7"]                                           # C58: fig1v3, fig4v3 (W-G2)
    with fitz.open(rep["pdf"]) as doc:
        assert doc.page_count == 3
        assert all(abs(p.rect.width - 612) < 0.01 and abs(p.rect.height - 792) < 0.01 for p in doc)
        assert "fig7: skipped" in doc[0].get_text()
        # 100%: the placed figures keep their size
        imgs = doc[2].get_text("dict")
        assert "fig3 (color, 100%" in doc[2].get_text() and "fig3 (greyscale, 100%" in doc[2].get_text()
        assert imgs["width"] == 612
        # C62 integration: each greyscale copy prints without color (the sheet keeps every source open until its save,
        # since show_pdf_page's graft map is keyed on id(src) and a closed color copy's id could be reused)
        if any("ghostscript" in r["greyscale"] for r in rep["included"]):
            import numpy as np
            for page in doc[1:]:
                (y,) = [b[1] for b in page.get_text("blocks") if "(greyscale, 100%" in b[4]]
                pix = page.get_pixmap(dpi=40, clip=fitz.Rect(0, y, page.rect.width, page.rect.height))
                px = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n).astype(int)
                assert (px.max(axis=2) - px.min(axis=2)).max() <= 2


@pytest.mark.skipif(not (Path.home() / ".local/bin/pdflatex").is_file(), reason="pdflatex is not installed")
def test_scope_table_compiles(tmp_path):
    import os
    import subprocess
    from figs.supp import sf_e11_guard as g
    (tmp_path / "e11_scope.tex").write_text(g.scope_table(_fixture("sf_e11_guard")["data"]["scope"]))
    (tmp_path / "doc.tex").write_text("\\documentclass[journal]{IEEEtran}\\usepackage{booktabs}\n\\begin{document}\n"
                                      "\\input{e11_scope.tex}\nText.\n\\end{document}\n")
    env = dict(os.environ, TEXINPUTS=f"{REPO / 'paper' / 'layout_check'}:")
    r = subprocess.run([str(Path.home() / ".local/bin/pdflatex"), "-interaction=nonstopmode", "-halt-on-error",
                        "doc.tex"], cwd=tmp_path, capture_output=True, text=True, env=env, timeout=300)
    log = (tmp_path / "doc.log").read_text(errors="replace")
    assert r.returncode == 0 and "LaTeX Error" not in log, log[-2000:]
    assert "Overfull" not in log, [l for l in log.splitlines() if "Overfull" in l]


# ---------------------------------------------------------------------------------------------------------------
# MS6 (design/ms6_spec.md §1.1 M2-M6, unit U43a)
def _marked(leg) -> list:
    """The drawn samples of a legend with a marker (HandlerLine2D draws one marker per sample)."""
    from matplotlib.lines import Line2D
    leg.figure.canvas.draw()
    return [ln for ln in leg.findobj(Line2D) if ln.get_marker() not in (None, "None", "none", "")]


# design IDs (contributions C1-C7 and their results, O1's, the guard's G1-G6, experiments E1-E11, policies A1-A9 but the
# names A2 and A3, A8P, BL0-BL8) and the name Sublet, which these figures no longer use for any configuration
ID_PATTERN = re.compile(r"\b(?:C[1-7]\b|O1-|G[1-6]\b|E(?:1[01]?|[2-9])\b|BL\d|A(?:[14-9]|8P)\b)|Sublet")
MAIN_M6 = {"fig3": "figs.fig3_e11", "fig5": "figs.fig5_e1_e10", "fig6": "figs.fig6_e10", "fig7": "figs.fig7_e2_e6"}


def test_c46_id_pattern_catches_the_frozen_labels():
    """The pattern of the next test finds every design ID that the frozen figures drew (inventory_consistency §1.3)
    and none of the names that stay (A2, A3, the instance and family names, the trace lender)."""
    for old in ("G3(b), Sublet", "max(2, ρ),\nC3-Cor3 factor", "LB$_T$ (C3-T4)", "O1-B", "trace (E1)", "LB$_A$, O1-A",
                "O1-C\nlimit, T→∞", "O1-D", "LB$_{\\mathrm{react}}$, C2-T3", "exact CR*(H), C2 core", "Sublet"):
        assert ID_PATTERN.search(old), old
    for ok in ("A2, theory $\\bar{r}$", "A3", "A2 fractional", "I1", "F3", "trace", "core ratio bound",
               "RR-renew bound", "marking bound", "LB$_T$\n(adaptive)", "Lagged RetroRenting + one-way guard"):
        assert not ID_PATTERN.search(ok), ok


@pytest.mark.parametrize("name", sorted(MAIN_M6))
def test_c46_main_figures_draw_no_design_id(name):
    """M6, M17: no drawn text of Figs. 3, 5, 6 and 7 (labels, legends, keys, ticks) holds a design or experiment ID
    or the name Sublet; the extract keeps its status labels, which are data. Fig. 3 (c)'s G3(b) line is "core ratio
    bound", whose owner (Lagged RetroRenting + one-way guard) the extract names for the caption."""
    data = _fixture(name)["data"]
    fig = importlib.import_module(MAIN_M6[name]).draw(data)
    drawn = [t.get_text() for t in style.drawn_texts(fig)]
    assert drawn and [t for t in drawn if ID_PATTERN.search(t)] == []
    if name == "fig3":
        assert data["labels"]["g3b"] == "core ratio bound" and "core ratio bound" in drawn
        assert data["labels"]["g3b_of"] == style.POLICIES["bl5_g1"].label
        assert "status" in data and data["status"]["G2_G3b"] == "PROVEN, audited"
    # C47 (print check of the gate): Fig. 5(c)'s "RR-renew bound" on one line, level with its line (no leader); C47
    # (U46): the symbols of Fig. 5's drawn labels in math, italic as on its axes, and Fig. 7's notice H likewise
    # C62: Fig. 5(a)'s trace squares carry M6's "trace instances" (at 9 pt only "trace" fit) and "random core" stands on
    # two lines above its dots
    want = {"fig5": (r"$\max(2,\rho)$", "RR-renew bound", "LB$_T$\n(adaptive)", "trace instances", r"$\rho<2$",  # C62
                     "$T=3000$", "$T=60$", "$\\rho m/(m+\\rho-1)$,\n$m=8$, limit", "random\ncore"),          # C47, C62
            "fig6": ("RR-renew bound", "marking bound", "LB$_A$ (private)"),
            "fig7": ("LB$_{\\mathrm{react}}$", "Notice $H$ (min)", "exact\nCR*($H$)")}.get(name, ())       # C47
    assert set(want) <= set(drawn), set(want) - set(drawn)
    # C47 (U46): no symbol drawn upright where the figure sets it in math (Fig. 5: rho, T, m; Fig. 7: H), and the
    # limits' arrow is \longrightarrow (STIX's full-height arrow), not \to or U+2192 (Liberation Sans' small one)
    upright = {"fig5": re.compile(r"ρ|\bT = |\bm = "), "fig7": re.compile(r"Notice H\b|CR\*\(H\)")}.get(name)  # C47
    assert upright is None or not [t for t in drawn if upright.search(t)], drawn                         # C47
    assert not [t for t in drawn if "\\to\\infty" in t or "→" in t], drawn                                 # C47
    if name == "fig6":
        assert any(t.startswith("LB$_C$ limit\n(public), $T\\longrightarrow\\infty$") for t in drawn)     # C47


@pytest.mark.parametrize("name", ["fig3", "sf_e11_inst"])
def test_c46_fig3_paired_legend(name):
    """M5: Fig. 3 and sf_e11_inst have one legend, in two rows over the panels: the three (inner, guarded) pairs
    under the inner policies' names, Two-timescale PD, per-borrower ski rental and the note; each pair's handle is a
    MarkerPair of the inner policy's open sample and its configuration's filled one. No legacy key is drawn, and the
    drawn keys are the figure's set."""
    from figs import fig3_e11 as f3
    fig = _module(name).draw(_fixture(name)["data"])
    assert len(fig.legends) == 1
    leg = fig.legends[0]
    texts = [t.get_text() for t in leg.get_texts()]
    assert texts == ["RetroRenting-style, lagged", "PD heuristic", "Greedy renting", "Two-timescale PD",
                     "Per-borrower ski rental", style.GUARD_PAIR_NOTE]
    assert f3.PAIRS == (("bl5_lag", "bl5_g1"), ("a7", "a7_g1"), ("bl1", "bl1_g1"))
    handles = [h for h, _ in f3.legend_entries()]
    assert [isinstance(h, style.MarkerPair) for h in handles] == [True] * 3 + [False] * 3
    assert len(_marked(leg)) == 2 * 3 + 2                        # the pairs' six samples, Two-timescale PD, BL2
    for h, (inner, guarded) in zip(handles, f3.PAIRS):
        assert [ln.get_marker() for ln in h] == [style.POLICIES[k].marker for k in (inner, guarded)]
        assert h[0].get_markerfacecolor() == "white" and h[1].get_markerfacecolor() == style.POLICIES[guarded].color
    assert _fixture(name)["data"]["labels"]["legend"] == texts
    drawn = _drawn_keys(fig)
    assert not set(drawn) & set(style.LEGACY_KEYS)
    assert set(drawn) == set(style.FIGURE_POLICIES["fig3"])          # sf_e11_inst's set is Fig. 3's


def test_c47_fig3_b_draws_the_agreeing_pair_once_with_a_key():
    """C47 (print check of the gate): in Fig. 3(b) the lagged RetroRenting-style rule and its guarded configuration
    agree within fig3_e11.B_AGREE_PCT percent at every point (medians; their open < and filled > overprinted into bow
    ties), so (b) draws the guarded configuration only, and a key shows the pair's two samples side by side, as the
    legend does, with "agree within p%"; the key lies above every drawn value of (b) (C62: on (b)'s letter line above
    the axes, test_c62_fig3_letter_keys_ticks_and_baselines; in (b)'s upper left corner before)."""
    from figs import fig3_e11 as f3
    from figs.common import agreement
    data = _fixture("fig3")["data"]
    b = data["b"]
    ag = agreement(b["series"]["bl5_lag"]["median"], b["series"]["bl5_g1"]["median"])
    assert b["agree"]["pair"] == ["bl5_lag", "bl5_g1"] and b["agree"]["drawn"] == "bl5_g1"
    assert b["agree"]["within_pct"] == ag["within_pct"] <= f3.B_AGREE_PCT
    assert b["agree"]["key"] == f"agree within {ag['within_pct']}%"
    fig = f3.draw(data)
    ax_b = fig.axes[1]
    drawn = {getattr(ln, "_sublet_policy", None) for ln in ax_b.lines} - {None}
    assert "bl5_g1" in drawn and "bl5_lag" not in drawn
    keys = [a for a in ax_b.artists if getattr(a, "_sublet_role", "") == "key"]
    assert len(keys) == 1 and [t.get_text() for t in keys[0].get_texts()] == [b["agree"]["key"]]
    assert len(_marked(keys[0])) == 2                                    # the pair's two samples
    r = fig.canvas.get_renderer()
    y_key = keys[0].get_window_extent(r).y0
    tops = [ax_b.transData.transform((x, y))[1] for k in drawn if k in b["series"]
            for x, y in zip(b["series"][k]["x"], b["series"][k]["ci_hi"]) if y is not None]
    assert max(tops) < y_key


def test_c47_fig3_a_cases_the_guarded_lagged_marker():  # C47
    """C47 (print check of the gate, U46): in Fig. 3(a) the x-whiskers of Greedy + one-way guard and PD heuristic +
    one-way guard run at the height of the lagged RetroRenting rule's guarded marker (y 1.024 against 1.018) and
    seemed to start at its tip; that marker is drawn above every other series of (a) on a white casing of
    fig3_e11.CASING_PT outside its edge, with its own whiskers above the casing."""
    from matplotlib.collections import LineCollection  # C47
    from matplotlib.colors import to_rgba  # C47
    from figs import fig3_e11 as f3  # C47
    data = _fixture("fig3")["data"]  # C47
    ax = f3.draw(data).axes[0]  # C47
    casing = [ln for ln in ax.lines if getattr(ln, "_sublet_role", "") == "casing"]  # C47
    assert len(casing) == 1  # C47
    c = casing[0]  # C47
    s = data["a"]["series"][f3.A_CASED]  # C47
    assert (list(c.get_xdata()), list(c.get_ydata())) == ([s["x"]], [s["y"]])  # C47
    assert c.get_marker() == style.POLICIES[f3.A_CASED].marker and c.get_linestyle() == "None"  # C47
    assert c.get_markerfacecolor() == c.get_markeredgecolor() == "white"  # C47
    assert c.get_markeredgewidth() == pytest.approx(style.MARKER_EDGE_PT + 2.0 * f3.CASING_PT)  # C47
    above = [a for a in ax.lines + ax.collections if a is not c and a.get_zorder() > c.get_zorder()]  # C47
    own = [a for a in above if getattr(a, "_sublet_policy", None) == f3.A_CASED]  # C47
    bars = [a for a in above if isinstance(a, LineCollection)]  # C47
    assert len(own) == 1 and len(bars) == 2 and len(above) == 3, above      # C47: its marker and whiskers only
    assert own[0].get_zorder() > max(b.get_zorder() for b in bars)  # C47
    want = to_rgba(style.policy(f3.A_CASED).text_color)  # C47
    assert all(np.allclose(b.get_colors()[0], want) for b in bars)  # C47


def test_c46_sf_e11_inst_dodge_order_and_lines():
    """sf_e11_inst dodges (a) and (b) in the legend's order, each guarded configuration just right of its inner
    policy, so that Greedy + one-way guard (after Greedy renting's open triangle) and per-borrower ski rental (last),
    which share a filled down triangle in greyscale, are told apart by place; (c) draws bl5_g1 only, its three
    instance lines in its filled marker and three line styles, with a y label that names no policy."""
    from figs.supp import sf_e11_inst as si
    assert si.DODGE_ORDER == ("bl5_lag", "bl5_g1", "a7", "a7_g1", "bl1", "bl1_g1", "a6", "bl2")
    data = _fixture("sf_e11_inst")["data"]
    fig = si.draw(data)
    ax_a, _, ax_c = fig.axes[:3]
    first = {}
    for ln in ax_a.lines:
        k = getattr(ln, "_sublet_policy", None)
        if k is not None and ln.get_marker() not in (None, "None", "none", ""):
            first.setdefault(k, float(np.asarray(ln.get_xdata(), dtype=float)[0]))
    order = sorted(first, key=first.get)
    assert order == list(si.DODGE_ORDER)
    lines = [ln for ln in ax_c.lines if getattr(ln, "_sublet_policy", None) is not None
             and ln.get_linestyle() not in ("None", "none", "")]
    assert {ln._sublet_policy for ln in lines} == {"bl5_g1"} and len(lines) == 3
    assert sorted(ln.get_linestyle() for ln in lines) == ["-", "--", ":"] and \
        {ln.get_marker() for ln in lines} == {style.POLICIES["bl5_g1"].marker}
    assert data["labels"]["c_y"] == "Cost / all-fallback"
    assert data["labels"]["c_policy"] == style.POLICIES["bl5_g1"].label


def test_c46_sf_e11_fam_keys_and_sf_e11_guard_legend():
    """sf_e11_fam: every pair drawn once and every near pair is in a key (none beside the panel letters), whose
    handle shows the pair's two samples side by side and whose text is "equal" or "agree within p%"; the texts with
    the policies' names are in the extract for the caption; the off-scale label keeps the name on its first line.
    sf_e11_guard: one legend row with the three guarded configurations, over panels of the registered size."""
    from figs.supp import sf_e11_fam as fam, sf_e11_guard as g
    data = _fixture("sf_e11_fam")["data"]
    lab = data["labels"]
    assert set(lab["coincide"].values()) == {"equal"} and set(lab["coincide_names"]) == set(lab["coincide"])
    assert lab["coincide_names"]["a7_g1|a7"] == "PD heuristic + one-way guard = PD heuristic"
    for p in "abc":
        assert all(t == "equal" or re.fullmatch(r"agree within \d+%", t) for t in lab["near"][p].values())
    # C47 (print check of the gate): the envelope as Fig. 3(c) names the same bound, no design ID
    assert lab["envelope"] == "core ratio bound" and lab["envelope_of"] == style.POLICIES["bl5_g1"].label
    h = fam._pair_handle("a7_g1", "a7")
    assert isinstance(h, style.MarkerPair) and [ln.get_marker() for ln in h] == ["D", "d"]      # inner first
    fig = fam.draw(data)
    keys = [a for ax in fig.axes for a in ax.artists if type(a).__name__ == "Legend"]
    assert keys
    for k in keys:
        assert all(t.get_text() == "equal" or t.get_text().startswith("agree within") for t in k.get_texts())
        assert len(_marked(k)) == 2 * len(k.get_texts())        # two samples per entry
    n = sum(len(data[p]["coincide"]) for p in "abc")
    assert sum(t.get_text() == "equal" for k in keys for t in k.get_texts()) >= n
    off = [t.get_text() for ax in fig.axes for t in ax.texts if "off scale" in t.get_text()]
    assert off and all(t.split("\n")[0].startswith("RetroRenting-style, lagged,") for t in off)
    fig = g.draw(_fixture("sf_e11_guard")["data"])
    # C47 (print check of the gate): the legend in the order (a) and (b) draw the guards (GUARDED's), not the registry's
    assert len(fig.legends) == 1 and [t.get_text() for t in fig.legends[0].get_texts()] == \
        [style.POLICIES[k].label for k in g.KEYS] and g.KEYS == ("bl5_g1", "a7_g1", "bl1_g1")
    assert style.figure_spec("sf_e11_guard").height_in == 2.5


def _gap_pt(P, Q) -> float:  # C47
    """The distance (pt) between two convex polygons (n x 2, any vertex order), -1 if they overlap."""  # C47
    def ccw(A):  # C47
        c = A.mean(axis=0)  # C47
        return A[np.argsort(np.arctan2(A[:, 1] - c[1], A[:, 0] - c[0]))]  # C47
    P, Q = ccw(np.asarray(P, float)), ccw(np.asarray(Q, float))  # C47
    for A, B in ((P, Q), (Q, P)):                       # C47: a separating axis among the edge normals
        for i in range(len(A)):  # C47
            e = A[(i + 1) % len(A)] - A[i]  # C47
            n = np.array([e[1], -e[0]]) / np.hypot(*e)  # C47
            if (B @ n).min() >= (A @ n).max():  # C47
                break  # C47
        else:  # C47
            continue  # C47
        break  # C47
    else:  # C47
        return -1.0  # C47

    def seg(p, a, b):  # C47
        t = np.clip(np.dot(p - a, b - a) / max(np.dot(b - a, b - a), 1e-12), 0.0, 1.0)  # C47
        return float(np.hypot(*(p - a - t * (b - a))))  # C47
    return min(seg(p, B[i], B[(i + 1) % len(B)]) for A, B in ((P, Q), (Q, P)) for p in A for i in range(len(B)))  # C47


def test_c47_sf_e11_inst_markers_and_bars_keep_clear():  # C47
    """C47 (print check of the gate, U46): in sf_e11_inst (a) and (b) no marker or interval bar of one policy comes
    within sf_e11_inst.CLEAR_PT of another policy's (the uniform slots, 3.6 pt apart, let equal pairs overprint), every
    instance keeps the legend's order inside +-DODGE, and the pairs that are equal are in labels.equal and the caption.
    (c)'s bars took each line's dash pattern until C62's fix round (now solid: test_c62_fix_sf_e11_inst_c_bars)."""
    from figs.supp import sf_e11_inst as si  # C47
    data = _fixture("sf_e11_inst")["data"]  # C47
    fig = si.draw(data)  # C47
    fig.canvas.draw()  # C47
    to_pt = 72.0 / fig.dpi  # C47
    for p, ax in zip("ab", fig.axes[:2]):  # C47
        marks = []                                   # C47: (instance, x data, key, outline pt)
        for ln in ax.lines:  # C47
            k = getattr(ln, "_sublet_policy", None)  # C47
            if k is None or ln.get_marker() in (None, "None", "none", ""):  # C47
                continue  # C47
            for x, y in ln.get_xydata():  # C47
                if np.isfinite(y):  # C47
                    c = ln.get_transform().transform((x, y)) * to_pt  # C47
                    marks.append((int(round(x)), float(x), k, si._outline_pt(k) + c))  # C47
        for i in range(len(data["instances"])):  # C47
            row = sorted((m for m in marks if m[0] == i), key=lambda m: m[1])  # C47
            assert [m[2] for m in row] == [k for k in si.DODGE_ORDER if k in [m[2] for m in row]]  # C47
            assert all(abs(m[1] - i) <= si.DODGE + 1e-9 for m in row)  # C47
        w = 0.5 * style.UNCERTAINTY_PT  # C47
        shapes = [(m[0], m[1], m[3]) for m in marks]  # C47
        for coll in ax.collections:                  # C47: the interval bars, each at its marker's x
            for s in coll.get_segments():  # C47
                (x0, y0), (_, y1) = ax.transData.transform(s) * to_pt  # C47
                xd = float(s[0][0])  # C47
                if abs(y1 - y0) > 0.2:  # C47
                    shapes.append((int(round(xd)), xd, np.array([[x0 - w, y0], [x0 + w, y0], [x0 + w, y1],  # C47
                                                                 [x0 - w, y1]])))  # C47
        for a in range(len(shapes)):  # C47
            for b in range(a + 1, len(shapes)):  # C47
                (ia, xa, A), (ib, xb, B) = shapes[a], shapes[b]  # C47
                if ia == ib and abs(xa - xb) > 1e-9:     # C47: one instance, two policies (a bar sits on its marker)
                    assert _gap_pt(A, B) >= si.CLEAR_PT - 0.1, (p, ia, xa, xb)  # C47
    eq = data["labels"]["equal"]  # C47
    for p, f in (("a", "median"), ("b", "W0")):  # C47
        for pair, at in eq[p].items():  # C47
            inner, guarded = pair.split("|")  # C47
            assert (inner, guarded) in si.f3.PAIRS  # C47
            for I in at:  # C47
                i = data["instances"].index(I)  # C47
                assert data[p][inner][f][i] == pytest.approx(data[p][guarded][f][i], rel=1e-12)  # C47
                assert style.POLICIES[inner].label in data["labels"]["caption"]  # C47
    assert data["labels"]["caption"] == si.caption(data)  # C47
    cap = data["labels"]["caption"]  # C47
    assert "\\ref{fig:guard}(b)" in cap and data["labels"]["c_policy"] in cap and not ID_PATTERN.search(cap)  # C47


def test_c47_sf_e11_guard_labels_markers_caption_and_scope_table():  # C47
    """C47 (print check of the gate, U46): sf_e11_guard (a) says what it plots and names the lenders as the table does;
    (c) puts no ECDF marker at a ratio of ECDF_MARK_BELOW or more (the runs within 1% of the bound, whose markers stood
    in one column at 1); the caption draft gives those shares and the certificates' counts by \\ref; the scope table
    names no contract tag and no experiment ID, defines the 5-min-notice variant and names Fig. 3 by \\ref."""
    from figs.supp import sf_e11_guard as g  # C47
    data = _fixture("sf_e11_guard")["data"]  # C47
    lab = data["labels"]  # C47
    assert lab["a_x"] == "Share of runs that abort"  # C47
    assert "i.i.d. 0.05" in data["mode_labels"] and "correlated" in data["mode_labels"]  # C47
    assert not [m for m in data["mode_labels"] if m.startswith("iid") or m == "corr."]  # C47
    assert g.ECDF_MARK_BELOW == 0.99  # C47
    fig = g.draw(data)  # C47
    n_marks = 0  # C47
    for ln in fig.axes[2].lines:  # C47
        every = ln.get_markevery()  # C47
        if getattr(ln, "_sublet_policy", None) is None or not every:  # C47
            continue  # C47
        x = np.asarray(ln.get_xdata(), dtype=float)  # C47
        assert all(x[i] < 0.99 for i in every)       # C47: none within 1% of the bound
        n_marks += len(every)  # C47
    assert n_marks > 0  # C47
    cap = lab["caption"]                             # C47: built on every run file (the fixture keeps every 25th ratio)
    assert set(lab["at_bound"]) == set(g.KEYS) and all(0.0 <= v <= 1.0 for v in lab["at_bound"].values())  # C47
    for k, v in lab["at_bound"].items():  # C47
        assert f"{100 * v:.0f}\\% ({style.POLICIES[k].label})" in cap  # C47
    for ref in ("fig:guard", "thm:fullmodel", "thm:envelope"):  # C47
        assert f"\\ref{{{ref}}}" in cap  # C47
    assert f"{data['certificates']['held']:,}" in cap and not ID_PATTERN.search(cap)  # C47
    tex = g.scope_table(data["scope"])  # C47
    assert "5-min notice &" in tex and "s5\\_tau5" not in tex and "E11" not in tex  # C47
    assert "Fig.~\\ref{fig:guard}" in tex and "$(\\tau,H)=(5,2)$" in tex  # C47
    assert "the headroom $h$, LB over all-fallback (median; 95\\% interval below)" in tex  # C47


def test_c47_sf_e11_fam_caption_and_limit_arrow():  # C47
    """C47 (print check of the gate, U46): sf_e11_fam's caption draft names F1-F3 by their results (\\ref), says whose
    bound the core ratio bound is and that it bounds no other policy, names each key's pairs by the policies' names
    (escaped for LaTeX), and is the text draw() writes; the limit's arrow is \\longrightarrow, as Fig. 3(c)'s."""
    from figs.supp import sf_e11_fam as fam  # C47
    data = _fixture("sf_e11_fam")["data"]  # C47
    lab = data["labels"]  # C47
    cap = lab["caption"]  # C47
    fam.draw(data)  # C47
    assert data["labels"]["caption"] == cap  # C47
    for ref in ("fig:guard", "thm:lower", "thm:public", "prop:insurance", "thm:envelope"):  # C47
        assert f"\\ref{{{ref}}}" in cap  # C47
    assert f"core ratio bound in (a) and (b) is that of {lab['envelope_of']}" in cap  # C47
    assert "it does not bound the other policies" in cap  # C47
    for a, b in (pair for p in "abc" for pair in data[p]["coincide"]):  # C47
        assert lab["coincide_names"][f"{a}|{b}"] + " (drawn once)" in cap  # C47
    assert not re.search(r"(?<!\\)%", cap) and "≈" not in cap and "–" not in cap  # C47
    assert lab["limit"] == r"revocable-only limit, $T\longrightarrow\infty$"  # C47


# ---------------------------------------------------------------------------------------------------------------
# C62 (2026-11-24: the caption's type scale; figures high-end, informative, readable): the guard study's
# figures fig3, sf_e11_inst, sf_e11_fam and sf_e11_guard
def _c62_pdf_spans(pdf) -> list:
    """(text, size, baseline y, x0, x1) of every horizontal text span of a figure PDF (pt, y down; PyMuPDF)."""
    import fitz
    out = []
    with fitz.open(pdf) as doc:
        for block in doc[0].get_text("rawdict")["blocks"]:
            for ln in block.get("lines", []):
                if tuple(round(v) for v in ln["dir"]) != (1, 0):
                    continue
                for sp in ln["spans"]:
                    if sp["chars"]:
                        out.append(("".join(c["c"] for c in sp["chars"]), sp["size"], sp["chars"][0]["origin"][1],
                                    sp["bbox"][0], sp["bbox"][2]))
    return out


def _c62_span(spans, text) -> tuple:
    hits = [s for s in spans if s[0] == text]
    assert len(hits) == 1, (text, hits)
    return hits[0]


def test_c62_fig3_letter_keys_ticks_and_baselines(monkeypatch, tmp_path):
    """C62: Fig. 3's keys of (b) (the agreeing pair, C47) and (c) (BL1 = PS) stand on their panels' letter line, right
    of the letter, as the paper's Fig. 4 sets its keys: their labels on the letter's baseline as printed (PyMuPDF,
    0.05 pt), each key's box fig3_e11.LETTER_KEY_CLEAR_PT above its axes (0.25 pt), within its panel's slot, (c)'s
    on one line; the row's x labels on one baseline as printed ((c)'s mathtext rho_1 sat 1.0 pt high before); (a)'s
    y label centered (2.5 pt low at 9 pt); no minor ticks on (b)'s log x axis or (c)'s log y axis; the legend in two
    rows, since one row with M5's note is still wider than the page at 7 pt."""
    from figs import fig3_e11 as f3
    _env(monkeypatch, tmp_path)
    data = _fixture("fig3")["data"]
    fig = f3.draw(data)
    rep = style.save(fig, "fig3", data)
    spans = _c62_pdf_spans(rep["pdf"])
    letters = {p: _c62_span(spans, f"({p})") for p in "abc"}
    texts = {"b": data["b"]["agree"]["key"], "c": data["labels"]["bl1_eq_a7"]}
    assert "\n" not in texts["c"]
    for p, t in texts.items():
        s = _c62_span(spans, t)
        assert abs(s[2] - letters[p][2]) <= 0.05 and s[3] > letters[p][4], (p, s, letters[p])
    xl = [_c62_span(spans, data["labels"][k]) for k in ("a_x", "b_x")] + [_c62_span(spans, "ρ")]
    assert max(s[2] for s in xl) - min(s[2] for s in xl) <= 0.05, xl
    r = fig.canvas.get_renderer()
    k_pt = 72.0 / fig.dpi
    keys = {p: [a for a in ax.artists if getattr(a, "_sublet_role", "") == "key"]
            for p, ax in zip("abc", fig.axes[:3])}
    assert [len(keys[p]) for p in "abc"] == [0, 1, 1]
    W = float(fig.get_size_inches()[0])
    right = [ax._sublet_rect_in[0] - style.LEFT_LABEL for ax in fig.axes[2:3]] + [W - style.MARGIN_RIGHT]
    for (p, ax), lim in zip(zip("bc", fig.axes[1:3]), right):
        kb, ab = keys[p][0].get_window_extent(r), ax.get_window_extent(r)
        assert (kb.y0 - ab.y1) * k_pt >= f3.LETTER_KEY_CLEAR_PT - 0.25, p
        assert kb.x1 / fig.dpi <= lim + 1e-6, p
    assert fig.axes[0].yaxis.label.get_position()[1] == pytest.approx(0.5)
    assert len(fig.axes[1].xaxis.get_minorticklocs()) == 0 and len(fig.axes[2].yaxis.get_minorticklocs()) == 0
    # the legend: two rows of three columns; one row of its six entries is wider than the page less its right margin
    leg = fig.legends[0]
    assert leg._ncols == 3 and len(leg.get_texts()) == 6
    handles, labels = zip(*f3.legend_entries())
    one = fig.legend(list(handles), list(labels), ncol=len(labels), frameon=False, borderpad=0.0,
                     handler_map=dict(style.PAIR_HANDLER_MAP))
    assert one.get_window_extent(r).width / fig.dpi > W - style.MARGIN_RIGHT
    one.remove()


def test_c62_sf_e11_inst_c_ticks():
    """C62: sf_e11_inst (c) has no minor ticks on its log x axis (labeled at 3, 10, 30, ...) and y ticks 0.1 apart
    (eight labels 0.05 apart at MaxNLocator's default); its extract (the fixture, the real one) is unchanged."""
    from figs.supp import sf_e11_inst as si
    fig = si.draw(_fixture("sf_e11_inst")["data"])
    ax = fig.axes[2]
    assert len(ax.xaxis.get_minorticklocs()) == 0
    lo, hi = ax.get_ylim()
    locs = [v for v in ax.yaxis.get_majorticklocs() if lo <= v <= hi]
    assert len(locs) >= 3 and np.allclose(np.diff(locs), 0.1)


def test_c62_sf_e11_fam_minor_ticks_and_marker_keys():
    """C62: sf_e11_fam's decade-labeled log y axes have unlabeled minor ticks at 2 and 5 times the decades only (eight
    per decade before), an axis labeled at 1, 2 and 5 times the decades none; the keys' handles are the pairs' markers
    without line stubs (the legend row shows the lines)."""
    from matplotlib.lines import Line2D
    from figs.supp import sf_e11_fam as fam
    fig = fam.draw(_fixture("sf_e11_fam")["data"])
    for ax in fig.axes[:3]:
        lo, hi = ax.get_ylim()
        major = [v for v in ax.yaxis.get_majorticklocs() if lo <= v <= hi]
        minor = list(ax.yaxis.get_minorticklocs())
        mant = {round(v / 10.0 ** math.floor(math.log10(v) + 1e-9), 6) for v in major}
        want = {2.0, 5.0} if mant == {1.0} else set()
        assert {round(v / 10.0 ** math.floor(math.log10(v) + 1e-9), 6) for v in minor} <= want, (major, minor)
        assert all(min(major) <= v <= max(major) for v in minor)
    assert any(len(ax.yaxis.get_minorticklocs()) for ax in fig.axes[:3])
    keys = [a for ax in fig.axes for a in ax.artists if type(a).__name__ == "Legend"]
    assert keys
    for k in keys:
        fig.canvas.draw()
        samples = [ln for ln in k.findobj(Line2D) if ln.get_marker() not in (None, "None", "none", "")]
        assert len(samples) == 2 * len(k.get_texts())
        assert all(ln.get_linestyle() in ("None", "none", "") for ln in k.findobj(Line2D)), k
    assert all(ln.get_linestyle() == "None" for ln in fam._pair_handle("bl5_g1", "bl5_lag"))


def test_c62_sf_e11_guard_grid_separators_and_ecdf_marks():
    """C62: sf_e11_guard (a) has light vertical grid lines at every GRID_STEP up to 1 behind its bars; (b) light
    separators between the instances and y ticks 0.2 apart; (c) the ECDFs' markers (ecdf_marks) spaced along the
    curves, none stacked (consecutive markers of a curve at least 6 pt apart; the 5%-of-runs rule set them 1-2 pt
    apart on the steep rises), none at a ratio of ECDF_MARK_BELOW or more and none within ECDF_MARK_FLOOR_PT of the x
    axis."""
    from figs.supp import sf_e11_guard as g
    fig = g.draw(_fixture("sf_e11_guard")["data"])
    ax_a, ax_b, ax_c = fig.axes[:3]
    grey = [ln for ln in ax_a.lines if ln.get_color() == style.GRID_GREY]
    assert sorted(round(float(ln.get_xdata()[0]), 6) for ln in grey) == [0.25, 0.5, 0.75, 1.0]
    bars = [p for p in ax_a.patches if isinstance(p, Rectangle)]
    assert bars and all(ln.get_zorder() < min(b.get_zorder() for b in bars) for ln in grey)
    seps = [ln for ln in ax_b.lines if ln.get_color() == style.GRID_GREY]
    assert sorted(float(ln.get_xdata()[0]) for ln in seps) == [0.5, 1.5, 2.5]
    lo, hi = ax_b.get_ylim()
    locs = [v for v in ax_b.yaxis.get_majorticklocs() if lo <= v <= hi]
    assert len(locs) >= 3 and np.allclose(np.diff(locs), 0.2)
    k_pt = 72.0 / fig.dpi
    floor = ax_c.transData.transform((0.0, 0.0))[1] * k_pt
    n = 0
    for ln in ax_c.lines:
        every = ln.get_markevery()
        if getattr(ln, "_sublet_policy", None) is None or not every:
            continue
        xy = np.column_stack([ln.get_xdata(), ln.get_ydata()])[every]
        P = ax_c.transData.transform(xy) * k_pt
        assert (xy[:, 0] < g.ECDF_MARK_BELOW).all() and (P[:, 1] - floor >= g.ECDF_MARK_FLOOR_PT - 1e-9).all()
        assert np.hypot(*np.diff(P, axis=0).T).min() >= 6.0, ln._sublet_policy
        n += 1
    assert n == len(g.KEYS)


# ---------------------------------------------------------------------------------------------------------------
# C62 fix round (the supplement's critic): sf_e11_inst (c)'s interval bars, sf_e11_guard (c)'s math label, and the
# baselines of both figures' rows
def test_c62_fix_sf_e11_inst_c_bars():
    """C62 fix round: sf_e11_inst (c)'s interval bars are solid, UNCERTAINTY_PT wide, in the series color (I2's dashed
    and I3's dotted bars read as reference lines), the dashes and dots only on the three connecting lines; two lines'
    bars that show beyond their markers and overlap in height stand at least BAR_SEP_PT apart (I2 and I3 near 14
    announcements per site-day stood 1.0 pt apart at their points' x), each at most BAR_SHIFT_MAX_PT from its point;
    the caption draft no longer gives the intervals the lines' style."""
    from matplotlib.colors import to_hex
    from figs.supp import sf_e11_inst as si
    data = _fixture("sf_e11_inst")["data"]
    fig = si.draw(data)
    fig.canvas.draw()
    ax = fig.axes[2]
    k_pt = 72.0 / fig.dpi
    p = style.policy(si.C_KEY)
    lines = [ln for ln in ax.lines if getattr(ln, "_sublet_policy", None) == si.C_KEY]
    assert sorted(ln.get_linestyle() for ln in lines) == ["-", "--", ":"]
    C = list(data["c"].values())
    assert len(ax.collections) == len(C)             # one set of bars per instance, in data["c"]'s order
    reach = float(np.abs(si._outline_pt(si.C_KEY)[:, 1]).max())
    bars = []                                        # (instance, x pt of the bar, lo pt, hi pt, shows beyond marker)
    shifts = []
    for j, (coll, s) in enumerate(zip(ax.collections, C)):
        assert all(d is None for _, d in coll.get_linestyle())                  # solid
        assert {to_hex(c) for c in coll.get_colors()} == {to_hex(p.text_color)}
        assert np.allclose(coll.get_linewidths(), style.UNCERTAINTY_PT)
        segs = coll.get_segments()
        assert len(segs) == len(s["x"])
        for seg, x, y in zip(segs, s["x"], s["median"]):
            (xb, y0), (_, y1) = ax.transData.transform(seg) * k_pt
            xp, yp = ax.transData.transform((x, y)) * k_pt
            shifts.append(abs(xb - xp))
            lo, hi = min(y0, y1), max(y0, y1)
            bars.append((j, xb, lo, hi, max(hi - yp, yp - lo) > reach + si.CLEAR_PT))
    assert max(shifts) <= si.BAR_SHIFT_MAX_PT + 1e-6
    assert max(shifts) > 0.1                         # the real fixture has the pair near 14 (I2, I3), set apart
    for a in range(len(bars)):
        for b in range(a + 1, len(bars)):
            A, B = bars[a], bars[b]
            if A[0] != B[0] and A[4] and B[4] and min(A[3], B[3]) > max(A[2], B[2]) - si.CLEAR_PT:
                assert abs(A[1] - B[1]) >= si.BAR_SEP_PT - 1e-6, (A, B)
    assert "line's style" not in data["labels"]["caption"] and data["labels"]["caption"] == si.caption(data)


def _c62_fix_fonts(pdf, text) -> set:
    """The font names of the PDF's spans whose text is `text`."""
    import fitz
    with fitz.open(pdf) as doc:
        return {sp["font"] for block in doc[0].get_text("rawdict")["blocks"] for ln in block.get("lines", [])
                for sp in ln["spans"] if "".join(c["c"] for c in sp["chars"]) == text}


def test_c62_fix_sf_e11_guard_math_label_and_row_baselines(monkeypatch, tmp_path):
    """C62 fix round: sf_e11_guard (c)'s x label sets T in math italic, $\\mathrm{ALG}(T)$ as the caption's $\\ALG(T)$
    ("ALG(T)" set it upright); as the PDF prints them (PyMuPDF, 0.05 pt) the row's x labels share one baseline ((c)'s
    mathtext by common.align_baselines) and so do its x tick labels ((b)'s instance names, without ticks, sat
    one tick length, 3 pt, high, and its x label with them); the same for sf_e11_inst's (a) and (b) against (c)."""
    from figs.supp import sf_e11_guard as g, sf_e11_inst as si
    _env(monkeypatch, tmp_path)
    data = _fixture("sf_e11_guard")["data"]
    assert data["labels"]["c_x"] == g.C_X_LABEL == r"$\mathrm{ALG}(T)$ / certificate bound"
    rep = style.save(g.draw(data), "sf_e11_guard", data)
    spans = _c62_pdf_spans(rep["pdf"])
    assert {f.split("+")[-1] for f in _c62_fix_fonts(rep["pdf"], "T")} == {"LiberationSans-Italic"}
    xl = [_c62_span(spans, t) for t in (data["labels"]["a_x"], data["labels"]["b_x"], "ALG(")]
    assert max(s[2] for s in xl) - min(s[2] for s in xl) <= 0.05, xl
    ticks = [_c62_span(spans, "0.25"), _c62_span(spans, "I1"), max((s for s in spans if s[0] == "0.2"),
                                                                     key=lambda s: s[2])]
    assert max(s[2] for s in ticks) - min(s[2] for s in ticks) <= 0.05, ticks
    data = _fixture("sf_e11_inst")["data"]
    rep = style.save(si.draw(data), "sf_e11_inst", data)
    spans = _c62_pdf_spans(rep["pdf"])
    xl = [s for s in spans if s[0] == data["labels"]["a_x"]] + [_c62_span(spans, data["labels"]["c_x"])]
    ticks = [s for s in spans if s[0] == "I4"] + [_c62_span(spans, "10")]
    assert len(xl) == 3 and len(ticks) == 3
    for row in (xl, ticks):
        assert max(s[2] for s in row) - min(s[2] for s in row) <= 0.05, row
