"""Tests of the figure scripts of Figs. 5, 6, 7 and the E1, E2, E6 and E10 supplementary panels (design/sim_spec_ms3.md
§8.4-§8.7; §10, row test_figs_ms3.py, for these figures). Quick: no raw data, no run outputs; the inputs are the
synthetic fixture tree tests/fixtures_figs/inputs/ (README there) and the fixture extracts
tests/fixtures_figs/<name>.json, and every file is written under pytest's tmp_path (never into paper/ or
code/sim/out/).

C50 (design/ms6_spec.md §7.2, the D5 review; §7.1 D4's script items): sf_e6a's cell table keeps the cells with a value,
counts the others in its caption, and is one longtable per block whose head repeats "Table <n>, continued" and the
block's label; its caption uses the paper's names (revocable-only leasing over ALG*). Each changed line names C50.

C52 (design/ms7/plan.md D3 and §4, unit T1): sf_e6a's cell list becomes the data file e6a_cells.csv (one line per cell
with a value), and e6a_cells.tex a one-page summary of it, one row per block with the counts above, at and below 1 and
the range, whose caption names the data file and counts the cells left out. Each changed line names C52."""
import builtins
import csv
import importlib
import io
import json
import math
import os
import re
from pathlib import Path

import pytest
from matplotlib.lines import Line2D

from figs import style
from figs.inputs import Inputs

FIX = Path(__file__).resolve().parent / "fixtures_figs"
IN_ROOT = FIX / "inputs"
SCRIPTS = {"fig5": "figs.fig5_e1_e10", "fig6": "figs.fig6_e10", "fig7": "figs.fig7_e2_e6",
           "sf_e1_sched": "figs.supp.sf_e1_sched", "sf_e1_rotation": "figs.supp.sf_e1_rotation",
           "sf_e2_por": "figs.supp.sf_e2_por", "sf_e2_mu_ep": "figs.supp.sf_e2_mu_ep",
           "sf_e2_mu_cost": "figs.supp.sf_e2_mu_cost", "sf_e2_pool": "figs.supp.sf_e2_pool",
           "sf_e6a": "figs.supp.sf_e6a", "sf_e6b": "figs.supp.sf_e6b", "sf_e10_rho": "figs.supp.sf_e10_rho",
           "sf_e10_cross": "figs.supp.sf_e10_cross", "sf_e10b": "figs.supp.sf_e10b"}
NAMES = sorted(SCRIPTS)

# The labels of §1 (LB_T, OPT_eager, H*_mu, ...) have first-level mathtext subscripts (4.9 pt at 7 pt), which do not
# warn; save() would warn only below that (GlyphSizeWarning), which these tests do not check.
pytestmark = pytest.mark.filterwarnings("ignore::figs.style.GlyphSizeWarning")


def module(name):
    return importlib.import_module(SCRIPTS[name])


def fixture_payload(name):
    return json.loads((FIX / f"{name}.json").read_text())


@pytest.fixture
def figs_env(tmp_path, monkeypatch):
    monkeypatch.setenv("SUBLET_FIGS_IN_ROOT", str(IN_ROOT))
    monkeypatch.setenv(style.ENV_PDF_DIR, str(tmp_path / "pdf"))
    monkeypatch.setenv(style.ENV_OUT_DIR, str(tmp_path / "out"))
    monkeypatch.setenv("SUBLET_FIGS_TABLES_DIR", str(tmp_path / "tables"))
    return tmp_path


# ---------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("name", NAMES)
def test_from_extract_saves_and_finalize_passes(figs_env, name):
    """--from-extract on the fixture extract: save() under the temporary output folders (finalize() passed), the
    registered page size, and the rewritten extract equals the one read (the MS5 rebuild is exact)."""
    rep = module(name).main(["--from-extract", str(FIX / f"{name}.json")])
    spec = style.figure_spec(name)
    assert Path(rep["pdf"]) == figs_env / "pdf" / f"{name}.pdf" and Path(rep["pdf"]).is_file()
    assert abs(rep["width_bp"] - spec.width_in * 72) <= 0.5 and abs(rep["height_bp"] - spec.height_in * 72) <= 0.5
    assert rep["outside_page"] == [] and set(rep["text_pt"]) <= {style.TICK_PT, style.LABEL_PT}
    assert json.loads((figs_env / "out" / f"{name}.json").read_text()) == fixture_payload(name)
    if name == "sf_e6a":
        tex = (figs_env / "tables" / "e6a_cells.tex").read_text()
        mod = module(name)
        assert mod.TABLES == ("e6a_cells.tex", "e6a_cells.csv")                                       # C52
        # C52 (design/ms7/plan.md D3, T1): the summary, one row per block of cells with a value, counted
        # independently here (above 1, at 1 within the heatmaps' tolerance below it, below), in one longtable whose
        # caption names the data file; the paper's names in the caption (C50)
        table = fixture_payload(name)["data"]["table"]                                                # C50
        rows = [ln for ln in tex.splitlines() if re.match(r"^[^\\%$].* & .*\\\\$", ln)]               # C52
        rows = [ln for ln in rows if not ln.startswith("Lenders")]                                    # C52: heads
        kept = [r for r in table if r["value"] is not None]                                           # C52
        blocks = list(dict.fromkeys((r["group"], r["lam"], r["mu"]) for r in kept))      # C52: in the table's order
        assert len(rows) == len(blocks)                                                               # C52
        tol = mod.CONTOUR_TOL                                                                         # C52
        for (g, lam, mu), ln in zip(blocks, rows):                                                    # C52
            v = [r["value"] for r in kept if (r["group"], r["lam"], r["mu"]) == (g, lam, mu)]         # C52
            cells = [c.strip() for c in ln[:-2].split("&")]                                          # C52
            want = [str(len(v)), str(sum(x > 1 for x in v)), str(sum(1 - tol <= x <= 1 for x in v)),
                    str(sum(x < 1 - tol for x in v)), f"{min(v):.3f}--{max(v):.3f}"]                  # C52
            assert cells[3:] == want and cells[2] == f"{mu:g}", (cells, want)                        # C52
        assert tex.count(r"\begin{longtable}") == tex.count(r"\end{longtable}") == 1                  # C52
        assert tex.count(r"\label{tab:e6a_cells}") == 1 and "e6a\\_cells.csv" in tex                   # C52
        assert "ALG$^\\ast$" in tex and "BL7" not in tex and "A1" not in tex                           # C50
        assert len(tex.splitlines()) < 60                                                             # C52: a page
        # C52: the data file, one line per cell with a value, in the table's order, CELLS_COLUMNS
        lines = list(csv.reader(io.StringIO((figs_env / "tables" / "e6a_cells.csv").read_text())))   # C52
        assert tuple(lines[0]) == mod.CELLS_COLUMNS and len(lines) - 1 == len(kept)                   # C52
        for r, ln in zip(kept, lines[1:]):                                                            # C52
            assert float(ln[5]) == pytest.approx(r["value"], abs=5e-7) and float(ln[3]) == r["H_min"]  # C52
            assert float(ln[4]) == r["r"] and float(ln[2]) == r["mu"]                                 # C52
            assert ln[0] == {"maas": "MaaS", "spot": "spot"}[r["group"]]                             # C52
            assert ln[1] == {"a5": "measured", "0": "0"}[r["lam"]]                                    # C52
        assert (figs_env / "tables" / "e6a_cells.csv").read_text() == mod.cells_csv(table)          # C52
        miss = {**table[0], "group": "spot", "value": None, "note": "fewer than two spot pools with data"}  # C50
        one = mod.cells_tex(table + [miss])                                                           # C50
        assert "The one cell without a value (spot cells" in one                                       # C50; C52
        assert "The 2 cells without a value (spot cells" in mod.cells_tex(table + [miss, miss])        # C50
        assert mod.cells_csv(table + [miss]) == mod.cells_csv(table)                    # C52: no line without a value
        assert "without a value" not in tex                                       # C50: the fixture has none


ALL_SCRIPTS = {**SCRIPTS, "fig1": "figs.fig1_guard", "fig2": "figs.fig2_e1a", "fig3": "figs.fig3_e11",
               "sf_e11_inst": "figs.supp.sf_e11_inst", "sf_e11_fam": "figs.supp.sf_e11_fam",
               "sf_e11_guard": "figs.supp.sf_e11_guard"}


@pytest.mark.parametrize("name", sorted(ALL_SCRIPTS))
def test_every_script_has_the_common_from_extract_option(name, monkeypatch):
    """One command line for every MS3 figure script (figs.common.cli): --from-extract without an argument reads the
    figure's own extract through Inputs.extract (under the input root), with a path it reads that file."""
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

    mod = importlib.import_module(ALL_SCRIPTS[name])
    assert mod.main.__module__ == mod.__name__ and mod.cli is common.cli
    monkeypatch.setattr(inputs.Inputs, "extract", fake_extract)
    with pytest.raises(Stop):
        mod.main(["--from-extract"])
    monkeypatch.setattr(common, "read_extract", fake_read_extract)
    with pytest.raises(Stop):
        mod.main(["--from-extract", "some/extract.json"])
    assert calls == [(name, "Inputs.extract"), (name, "some/extract.json")]


def test_inputs_extract_reads_under_the_input_root(tmp_path, monkeypatch):
    p = tmp_path / "code/sim/out/figs/fig6.json"
    p.parent.mkdir(parents=True)
    p.write_text(json.dumps({"figure": "fig6", "data": {"x": 1}}))
    monkeypatch.setenv("SUBLET_FIGS_IN_ROOT", str(tmp_path))
    inp = Inputs()
    assert inp.extract("fig6") == {"figure": "fig6", "data": {"x": 1}}
    assert inp.sources == ["code/sim/out/figs/fig6.json"]


def test_from_extract_default_reads_the_extract_under_the_input_root(tmp_path, monkeypatch):
    """Without a path, --from-extract reads code/sim/out/figs/<name>.json under the input root (figs.inputs)."""
    root = tmp_path / "root"
    (root / "code/sim/out/figs").mkdir(parents=True)
    (root / "code/sim/out/figs/fig6.json").write_text((FIX / "fig6.json").read_text())
    monkeypatch.setenv("SUBLET_FIGS_IN_ROOT", str(root))
    monkeypatch.setenv(style.ENV_PDF_DIR, str(tmp_path / "pdf"))
    monkeypatch.setenv(style.ENV_OUT_DIR, str(tmp_path / "out"))
    module("fig6").main(["--from-extract"])
    assert json.loads((tmp_path / "out/fig6.json").read_text()) == fixture_payload("fig6")


@pytest.mark.parametrize("name", NAMES)
def test_build_reads_only_result_files_and_matches_the_extract(figs_env, monkeypatch, name):
    """build() on the fixture tree opens no file of the repository outside the result folders of the input root
    (patched open), records only result files as sources, and gives the fixture extract's data."""
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
    data = module(name).build(inp)
    monkeypatch.undo()
    for p in opened:
        if style.REPO in p.parents:
            assert IN_ROOT in p.parents, f"{name} opened {p}"
            style.check_source(p.relative_to(IN_ROOT).as_posix())
    assert opened and all(style.check_source(s) == s for s in inp.sources)
    from figs.common import json_number
    data = json.loads(json.dumps(data, allow_nan=False, default=json_number))
    want = fixture_payload(name)["data"]
    stale = (f"tests/fixtures_figs/{name}.json is stale (the script's data changed): refresh the fixture extracts "
             "with `python tests/fixtures_figs/refresh_extracts.py` from code/sim (README in "
             "tests/fixtures_figs/inputs)")
    if name == "sf_e6a":              # the fixture extract keeps one block of the cell table (README)
        assert all(row in data["table"] for row in want["table"]), stale
        data, want = ({k: v for k, v in d.items() if k != "table"} for d in (data, want))
    assert data == want, stale


@pytest.mark.parametrize("name", NAMES)
def test_registry_keys_and_theory_lines(name):
    """The policies drawn are within the figure's set (FIGURE_POLICIES for Figs. 5-7, SUPP_POLICIES for sf_*) and
    pass check_policies; every limit line is labeled as a limit; every theory label is drawn."""
    fig = module(name).draw(fixture_payload(name)["data"])
    keys = {getattr(a, "_sublet_policy") for a in fig.findobj(Line2D) if hasattr(a, "_sublet_policy")}
    allowed = style.FIGURE_POLICIES[name] if name.startswith("fig") else style.SUPP_POLICIES[name]
    assert keys <= set(allowed), keys - set(allowed)
    style.check_policies(keys)
    if name.startswith("fig"):
        assert not keys & set(style.SUPP_ONLY_KEYS)      # C13: a3_rot and cold only in supplementary figures
    for t in fig.texts + [t for ax in fig.axes for t in ax.texts]:
        role = getattr(t, "_sublet_role", "")
        if role == "theory_label:limit":
            assert "limit" in t.get_text().lower() or "T→∞" in t.get_text(), t.get_text()


def test_fig7_level_one_reference_and_heatmap_halo():
    """Fig. 7(b) draws the level 1 (all-fallback) with reference_line, not as BL0a; Fig. 7(c) has the boundary
    as a dotted theory line with a white halo."""
    fig = module("fig7").draw(fixture_payload("fig7")["data"])
    ax_a, ax_b, ax_c = fig.axes[:3]
    refs = [ln for ln in ax_b.lines if getattr(ln, "_sublet_role", "") == "reference"]
    assert any(list(ln.get_ydata()) == [1.0, 1.0] for ln in refs)
    assert not any(getattr(ln, "_sublet_policy", "") == "bl0a" for ln in ax_b.lines)
    assert any(getattr(ln, "_sublet_role", "") == "halo" for ln in ax_c.lines)
    assert any(getattr(ln, "_sublet_role", "") == "theory:lower" and ln.get_linestyle() == ":" for ln in ax_c.lines)


def test_fig7_c62_header_cues_and_direct_labels():  # C62
    """C62 (Fig. 7's drawing only): one header row, the legend centered over (a) and (b), whose series it keys, and
    (c)'s colorbar on the legend's center line, right-aligned with the heatmap, its label clear of the legend and its
    tick labels clear of the axes, so that (c)'s cells fill the axes (no headroom); in (c) the cues "< 1", "= 1" and
    "> 1" each over a cell of its own region (here with a cell below 1 added), clear of the boundary's line; (a)'s
    "P95" above the MaaS band's top edge; (b)'s lines labeled with the lender names. The shared drawers keep the
    defaults that sf_e2_* and sf_e6a draw with."""
    import inspect
    import numpy as np
    from figs import fig7_e2_e6 as f7
    for fn, arg, want in ((f7.draw_heat_panel, "cbar_at", "top"), (f7.draw_heat_panel, "cues", "sign"),
                          (f7.draw_heat_panel, "h_gap_pt", 5.0), (f7.draw_episode_panel, "h_gap_pt", 5.0),
                          (f7.draw_totals_panel, "h_gap_pt", 5.0), (f7.h_axis, "gap_pt", 5.0),
                          (f7.thin_x_ticks, "gap_pt", 5.0)):
        assert inspect.signature(fn).parameters[arg].default == want, (fn.__name__, arg)
    data = fixture_payload("fig7")["data"]
    data["c"]["values"][0][0] = 0.5                 # a cell below 1, so that all three regions have cells
    data["c"]["contour"] = f7.ratio_contour(data["c"]["values"], data["c"]["x_edges"], data["c"]["y_edges"])
    fig = f7.draw(data)
    r = fig.canvas.get_renderer()
    to_in, to_pt = 1.0 / fig.dpi, 72.0 / fig.dpi
    ax_a, ax_b, ax_c = fig.axes[:3]
    H = fig.get_size_inches()[1]
    yc = H - 0.5 * style.LEGEND_ROW                  # legend_row's center line
    lb = fig.legends[0].get_window_extent(r)
    ra, rb = style.axes_rect_in(ax_a), style.axes_rect_in(ax_b)
    assert abs(0.5 * (lb.x0 + lb.x1) * to_in - 0.5 * (ra[0] + rb[0] + rb[2])) < 0.01
    assert abs(0.5 * (lb.y0 + lb.y1) * to_in - yc) < 0.005
    (cax,) = ax_c.child_axes
    cb, axb = cax.get_window_extent(r), ax_c.get_window_extent(r)
    assert abs(0.5 * (cb.y0 + cb.y1) * to_in - yc) < 0.005 and abs(cb.x1 - axb.x1) * to_pt < 0.5
    (lab,) = [t for t in ax_c.texts if getattr(t, "_sublet_role", "") == "colorbar_label"]
    assert lab.get_text() == data["labels"]["colorbar"] and lab.get_fontsize() == style.TICK_PT
    assert lb.x1 * to_in + f7.LEGEND_CLEAR_IN <= lab.get_window_extent(r).x0 * to_in
    low = min(t.get_window_extent(r).y0 for t in cax.xaxis.get_ticklabels() if t.get_text())
    assert (low - axb.y1) * to_pt >= f7.CBAR_CLEAR_PT
    assert ax_c.get_ylim() == pytest.approx((data["c"]["y_edges"][0], data["c"]["y_edges"][-1]))
    # (c): each cue's center over a cell of its region, clear of the boundary's line
    vals = np.array([[np.nan if v is None else v for v in row] for row in data["c"]["values"]], dtype=float)
    level, tol = data["c"]["contour"]["level"], data["c"]["contour"]["tol"]
    below, above = vals < level * (1 - tol), vals > level * (1 + 1e-9)
    regions = {data["labels"]["below"]: below, data["labels"]["above"]: above,
               f"= {style.PLAIN(level)}": np.isfinite(vals) & ~below & ~above}
    cues = {t.get_text(): t for t in ax_c.texts if getattr(t, "_sublet_role", "") == "sign_cue"}
    assert set(cues) == {k for k, m in regions.items() if m.any()} == {"< 1", "= 1", "> 1"}
    bound = [ln for ln in ax_c.lines if getattr(ln, "_sublet_role", "") == "theory:lower"][0]
    P = ax_c.transData.transform(np.column_stack([bound.get_xdata(), bound.get_ydata()]).astype(float))
    for text, t in cues.items():
        bb = t.get_window_extent(r)
        x, y = ax_c.transData.inverted().transform((0.5 * (bb.x0 + bb.x1), 0.5 * (bb.y0 + bb.y1)))
        j = int(np.searchsorted(data["c"]["x_edges"], x)) - 1
        i = int(np.searchsorted(data["c"]["y_edges"], y)) - 1
        assert regions[text][i, j], (text, i, j)
        P_in = P[(P[:, 0] >= bb.x0) & (P[:, 0] <= bb.x1)]
        assert not ((P_in[:, 1] >= bb.y0) & (P_in[:, 1] <= bb.y1)).any(), text
    # (a): "P95" above the band's top edge where it spans; (b): the lender names
    (p95,) = [t for t in ax_a.texts if t.get_text() == f7.P95_LABEL]
    s = data["a"]["a1"]["maas"]
    edge = ax_a.transData.transform([(h, p) for h, p in zip(s["H_min"], s["p95"]) if p is not None])
    bb = p95.get_window_extent(r)
    xs = np.linspace(bb.x0, bb.x1, 20)
    assert (np.interp(xs, edge[:, 0], edge[:, 1]) < bb.y0).all() and bb.y1 <= ax_a.get_window_extent(r).y1
    assert sorted(t.get_text() for t in ax_b.texts if getattr(t, "_sublet_role", "") == "direct_label") == \
        sorted(style.ENV_LABELS["lender"][g] for g in f7.GROUPS)


def test_fig7_c62_review_frame_halo_ticks_and_dashes():  # C62, review of the redesign
    """After the review of C62's redesign (Fig. 7's drawing only): (c) framed, its four spines alike, at the cell
    area's edges; the boundary's halo HEAT_HALO_PT (thinner than style.HALO_PT) on each side of the line and of its
    label; (c)'s H ticks label a column beside every vertical step of the step line (here cells below 1 up to the
    30-min column, as in the paper's data: 30 labeled, 60 a minor tick) and keep H_TICK_GAP_PT between labels; the
    legend's dashed sample shows only whole dashes, centered (no sliver at either end). The shared drawers keep the
    defaults that sf_e2_* and sf_e6a draw with."""
    import inspect
    import matplotlib as mpl
    import numpy as np
    from figs import fig7_e2_e6 as f7
    for fn, arg, want in ((f7.draw_heat_panel, "h_priority", None), (f7.draw_heat_panel, "halo_pt", None),
                          (f7.draw_heat_panel, "frame", False), (f7.thin_x_ticks, "priority", f7.H_TICK_PRIORITY)):
        assert inspect.signature(fn).parameters[arg].default == want, (fn.__name__, arg)
    data = fixture_payload("fig7")["data"]
    c = data["c"]
    hs = [float(h) for h in c["H_min"]]
    for i in range(3):                                  # the rows 1.1-1.5 below 1 up to 30 min
        for j, h in enumerate(hs):
            if h <= 30.0:
                c["values"][i][j] = 0.8
    c["contour"] = f7.ratio_contour(c["values"], c["x_edges"], c["y_edges"])
    fig = f7.draw(data)
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    to_pt = 72.0 / fig.dpi
    ax_c = fig.axes[2]
    sides = ("left", "bottom", "top", "right")
    assert all(ax_c.spines[s].get_visible() for s in sides)
    assert len({ax_c.spines[s].get_linewidth() for s in sides}) == 1
    assert ax_c.get_xlim() == pytest.approx((c["x_edges"][0], c["x_edges"][-1]))
    assert ax_c.get_ylim() == pytest.approx((c["y_edges"][0], c["y_edges"][-1]))
    (bound,) = [ln for ln in ax_c.lines if getattr(ln, "_sublet_role", "") == "theory:lower"]
    halos = [ln for ln in ax_c.lines if getattr(ln, "_sublet_role", "") == "halo"]
    assert f7.HEAT_HALO_PT < style.HALO_PT
    assert [h.get_linewidth() for h in halos] == pytest.approx([bound.get_linewidth() + 2 * f7.HEAT_HALO_PT])
    (blab,) = [t for t in ax_c.texts if getattr(t, "_sublet_role", "") == "theory_label:lower"]
    assert [pe._gc["linewidth"] for pe in blab.get_path_effects()] == pytest.approx([2 * f7.HEAT_HALO_PT])
    major = [float(t) for t in ax_c.xaxis.get_majorticklocs()]
    assert 30.0 in major and 60.0 in [float(t) for t in ax_c.xaxis.get_minorticklocs()]
    steps = {x0 for ln in c["contour"]["lines"] for x0, x1 in zip(ln["H_min"], ln["H_min"][1:]) if x0 == x1}
    assert steps
    for e in steps:                                     # a labeled column on one side of every vertical step
        k = int(np.searchsorted(c["x_edges"], e))
        assert hs[k - 1] in major or hs[k] in major, e
    boxes = sorted((t.get_window_extent(r).x0, t.get_window_extent(r).x1) for t in ax_c.xaxis.get_ticklabels()
                   if t.get_text())
    assert len(boxes) == len(major)
    assert all((b[0] - a[1]) * to_pt >= f7.H_TICK_GAP_PT - 0.05 for a, b in zip(boxes, boxes[1:]))
    # the legend's dashed sample: whole dashes only, the free ends alike
    length = mpl.rcParams["legend.handlelength"] * style.TICK_PT
    dashed = [h for h in fig.legends[0].legend_handles if getattr(h, "_unscaled_dash_pattern", (0, None))[1]]
    assert len(dashed) == 1 and dashed[0].get_dash_capstyle() == "butt"          # Spot, the one dashed sample
    off, (on, gap) = dashed[0]._unscaled_dash_pattern
    period = on + gap
    starts = [k * period - off for k in range(-2, int(length // period) + 3)]      # where each dash would start
    pieces = [(max(a, 0.0), min(a + on, length)) for a in starts if min(a + on, length) > max(a, 0.0) + 1e-9]
    assert len(pieces) >= 2 and all(b - a == pytest.approx(on) for a, b in pieces)
    assert pieces[0][0] == pytest.approx(length - pieces[-1][1])


def test_heatmap_ratio_one_contour():
    """Fig. 7(c) and sf_e6a: the step line at ratio 1 runs along the cell edges between a cell below 1 - tol (0.5%)
    and a neighbor that is not, skips edges to missing cells, is chained into polylines (corners only), and is drawn
    thin solid black above the cells and the boundary line with its halo, below the boundary's label; the extract
    names it (labels.contour) and keeps its tolerance (contour.tol)."""
    from matplotlib.colors import to_hex
    from figs.fig7_e2_e6 import ratio_contour
    xe, ye = [0.0, 1.0, 2.0, 3.0], [10.0, 20.0, 30.0]
    vals = [[0.9, 0.95, 1.2],                       # rows by r: the two cells < 1 at the lower left
            [1.0, None, 1.1]]                       # a missing cell: its edges are skipped
    c = ratio_contour(vals, xe, ye)
    assert c["level"] == 1.0 and c["tol"] == 0.005
    assert sorted((ln["H_min"], ln["r"]) for ln in c["lines"]) == [([0.0, 1.0], [20.0, 20.0]),
                                                                   ([2.0, 2.0], [10.0, 20.0])]
    assert ratio_contour([[1.0 - 1e-15, 1.0]], [0.0, 1.0, 2.0], [1.0, 2.0])["lines"] == []   # float noise of a tie
    assert ratio_contour([[0.996, 1.2]], [0.0, 1.0, 2.0], [1.0, 2.0])["lines"] == []         # within 0.5%: 1
    assert len(ratio_contour([[0.994, 1.2]], [0.0, 1.0, 2.0], [1.0, 2.0])["lines"]) == 1
    data = fixture_payload("fig7")["data"]
    assert data["labels"]["contour"] and data["c"]["contour"]["level"] == 1.0
    assert data["c"]["contour"]["tol"] == 0.005 and "0.5%" in data["labels"]["contour"]
    data["c"]["values"][0][0] = 0.5                 # at least one cell < 1 next to cells >= 1
    data["c"]["values"][0][1] = 1.5
    data["c"]["contour"] = ratio_contour(data["c"]["values"], data["c"]["x_edges"], data["c"]["y_edges"])
    ax_c = module("fig7").draw(data).axes[2]
    lines = [ln for ln in ax_c.lines if getattr(ln, "_sublet_role", "") == "contour"]
    below = max(ln.get_zorder() for ln in ax_c.lines if getattr(ln, "_sublet_role", "") in ("halo", "theory:lower"))
    label = min(t.get_zorder() for t in ax_c.texts if getattr(t, "_sublet_role", "") == "theory_label:lower")
    assert lines and all(to_hex(ln.get_color()) == "#000000" and ln.get_linestyle() == "-" for ln in lines)
    assert all(ax_c.collections[0].get_zorder() < below < ln.get_zorder() < label for ln in lines)


def test_heatmap_edges_follow_the_spec():
    """§8.6: x edges at -0.5, 0.5, sqrt 2, sqrt 10, sqrt 50, sqrt 150, sqrt 450, sqrt 1800, sqrt 7200, sqrt 28800,
    240 sqrt 2 on the H grid; y edges at the geometric means of neighboring rows, outer edges by the same ratio."""
    from figs.fig7_e2_e6 import h_edges, r_edges
    want = [-0.5, 0.5] + [math.sqrt(v) for v in (2, 10, 50, 150, 450, 1800, 7200, 28800)] + [240 * math.sqrt(2)]
    assert h_edges([0, 1, 2, 5, 10, 15, 30, 60, 120, 240]) == pytest.approx(want, rel=1e-12)
    ye = r_edges([1.1, 1.25, 1.5])
    assert ye[1] == pytest.approx(math.sqrt(1.1 * 1.25)) and ye[0] / 1.1 == pytest.approx(1.1 / ye[1])
    assert ye[-1] / 1.5 == pytest.approx(1.5 / ye[-2])


def test_summary_readers_follow_the_driver_forms():
    """The forms e2.py and e6.py write (§6.7, §7.1): coincide and cold_equals_a1 as booleans (null with a note where
    nothing is compared), boundary rows as parallel columns; other forms are rejected. E6(b) components without
    double counting."""
    from figs.common import MissingKey
    from figs.fig7_e2_e6 import boundary_records, coincides
    from figs.supp.sf_e6b import component_groups
    e2 = {"coincide": {"maas": {"5": {"1": False, "2": None, "2_note": "nothing compared"}}},
          "cold_equals_a1": {"maas": {"5": {"1": True}}}}
    assert coincides(e2, "prewarm", "maas", "5", 1) == (False, None)
    assert coincides(e2, "cold", "maas", "5", 1) == (True, None)
    assert coincides(e2, "prewarm", "maas", "5", 2) == (None, "nothing compared")
    with pytest.raises(MissingKey):
        coincides({"coincide": {"maas": {"5": {"1": {"prewarm_equals_a1": True}}}}}, "prewarm", "maas", "5", 1)
    cols = {"H": [5, 0], "H_min": [5, 0], "r_star": [1.6, 1.76], "H_skipped": [{"H": 30}]}
    assert [r["r_star"] for r in boundary_records(cols)] == [1.76, 1.6]
    with pytest.raises(MissingKey):
        boundary_records([{"H_min": 5, "r_star": 1.6}])
    comp = {"lease_prepaid": 1.0, "lease_rent": 2.0, "lease": 3.0, "loading": 1.0, "routing": 0.0,
            "stranding": 0.5, "stranding_fb": 0.5, "total": 4.5}
    assert component_groups(comp) == {"lease": 3.0, "loading": 1.0, "routing": 0.0, "stranding": 0.5}
    assert component_groups({"lease_prepaid": 1.0, "lease_rent": 2.0, "stranding_fb": 0.5}) == \
        {"lease": 3.0, "stranding": 0.5}


def test_supplementary_outputs_go_to_the_supplement_unless_overridden(monkeypatch, tmp_path):
    """M39: supplementary PDFs to paper/supplement/figures/ and sf_e6a's table to paper/supplement/tables/, unless
    the test folders are set (the table then follows SUBLET_FIGS_TABLES_DIR, else SUBLET_FIGS_PDF_DIR)."""
    from figs.common import supp_pdf_dir, tables_dir
    monkeypatch.delenv(style.ENV_PDF_DIR, raising=False)
    monkeypatch.delenv("SUBLET_FIGS_TABLES_DIR", raising=False)
    assert supp_pdf_dir() == style.REPO / "paper/supplement/figures"
    assert tables_dir() == style.REPO / "paper/supplement/tables"
    monkeypatch.setenv(style.ENV_PDF_DIR, str(tmp_path / "pdf"))
    assert supp_pdf_dir() == tmp_path / "pdf" and tables_dir() == tmp_path / "pdf"
    monkeypatch.setenv("SUBLET_FIGS_TABLES_DIR", str(tmp_path / "tables"))
    assert tables_dir() == tmp_path / "tables"


def _fixture_input(rel):
    return json.loads((IN_ROOT / rel).read_text())


def test_sf_e2_mu_ep_hstar_mu_is_the_core_game_threshold():
    """M66: in every panel of sf_e2_mu_ep the H*_mu vertical drawn is the threshold of the core game that the drawn
    CR*(H) belongs to (game.json meta.hstar.<mu>.<lambda_default>.H_min), not a11's full-model C2-SW value, which
    the extract keeps beside it (H_star_mu_full_model_min) and does not draw; H*_beta stays a11's (M25), and
    Fig. 7(a) keeps a11's H*_mu (M25)."""
    game = _fixture_input("code/sim/out/e2/game.json")
    por = _fixture_input("code/theory_checks/c2/out/por_default.json")
    a11 = _fixture_input("code/analysis/out/a11_calibration.json")
    tier = a11["table_3_8_by_tier"]["values"]["maas_a10"]["M"]["a5_2GBps"]
    lam = format(float(por["inputs"]["lambda_default"]), "g")
    data = fixture_payload("sf_e2_mu_ep")["data"]
    assert [p["mu"] for p in data["panels"]] == [0.2, 0.5, 2.0]
    fig = module("sf_e2_mu_ep").draw(data)
    for ax, p in zip(fig.axes, data["panels"]):
        game_h = game["meta"]["hstar"][format(p["mu"], "g")][lam]["H_min"]
        full_h = tier["H_star_mu_s"][str(float(p["mu"]))] / 60.0
        assert p["verticals"] == {"H_star_mu_min": game_h, "H_star_beta_min": tier["H_star_beta_s"] / 60.0}
        assert p["hstar_H_min"] == game_h and p["H_star_mu_full_model_min"] == full_h
        assert set(p["verticals_source"]) == {"H_star_mu_min", "H_star_beta_min", "H_star_mu_full_model_min"}
        assert "game.json meta.hstar" in p["verticals_source"]["H_star_mu_min"]
        assert "a11_calibration.json" in p["verticals_source"]["H_star_mu_full_model_min"]
        xs = sorted(ln.get_xdata()[0] for ln in ax.lines if getattr(ln, "_sublet_role", "") == "reference"
                    and ln.get_xdata()[0] == ln.get_xdata()[1])
        assert xs == sorted(p["verticals"].values())
    assert abs(data["panels"][2]["H_star_mu_full_model_min"] / data["panels"][2]["verticals"]["H_star_mu_min"]
               - 1.0) > 0.5                                    # mu = 2: the two thresholds differ
    assert fixture_payload("fig7")["data"]["a"]["verticals"]["H_star_mu_min"] == tier["H_star_mu_s"]["1.0"] / 60.0


def test_missing_values_keep_their_notes_and_do_not_break_the_figures():
    """§2.6 and §8.7: a null value with its '*_note' is drawn as missing and kept in the extract with the note. A
    null best_H (e2.py: "no H with a value") gives no minimizer marker; a menu without runs (e6.py) an empty row; an
    E10 point that is null stays in the series (a gap in its line); BL6 is drawn only where it ran (§6.4: not at H = 0,
    where e2.py gives it A1's values with ran false)."""
    from figs.common import e10_series
    from figs.fig7_e2_e6 import episode_block, totals_block
    from figs.supp import sf_e6b
    from sublet.experiments import e2 as e2d, e6 as e6d, e10 as e10d       # the drivers' null forms
    e2 = _fixture_input("code/sim/out/e2/summary.json")
    e2["best_H"]["spot"]["1"]["trace"]["a1"] = e2d._best_H_null("no H with a value")
    b = totals_block(e2, 1)
    assert b["minimizer"]["spot"] == {"H_min": None, "value": None, "note": "no H with a value"}
    data = fixture_payload("fig7")["data"]
    data["b"]["minimizer"]["spot"] = b["minimizer"]["spot"]
    ax_b = module("fig7").draw(data).axes[1]
    marks = [ln for ln in ax_b.lines if getattr(ln, "_sublet_policy", "") == "a1" and ln.get_linestyle() == "None"]
    assert len(marks) == 1                                   # the MaaS minimizer only
    ep = episode_block(e2, 1, ("a1", "bl6"))
    h0 = ep["bl6"]["maas"]["H_min"].index(0.0)
    assert e2["episodes"]["maas"]["0"]["1"]["bl6"]["ran"] is False
    assert ep["bl6"]["maas"]["median"][h0] is None and ep["bl6"]["maas"]["note"][h0]
    assert ep["a1"]["maas"]["median"][h0] is not None
    e6b = _fixture_input("code/sim/out/e6/b/summary.json")
    e6b["menus"]["R+P+1h"]["1"] = e6d._menu_null("no run with data")
    ent = sf_e6b.menu_entry(e6b, "R+P+1h", 1)
    assert ent["total"] is None and ent["note"] == "no run with data" and ent["shares"] == {}
    d6 = fixture_payload("sf_e6b")["data"]
    d6["a"]["R+P+1h"], d6["b"]["R+P+1h"] = ent, {}
    sf_e6b.draw(d6)
    e10 = _fixture_input("code/sim/out/e10/summary.json")
    e10["a"]["adaptive"]["16"]["32"]["A2-th"] = e10d._null_entry("job failed", {"T": 1536})
    s = e10_series(e10, "adaptive", 16, ["a2_theory"])["a2_theory"]
    i = s["m"].index(32.0)
    assert s["ratio"][i] is None and s["note"][i] == "job failed" and s["ratio"][i + 1] is not None


def test_agreement_needs_the_same_points():
    """A coincidence key ("A = B", "A ≈ B (within p%)") is stated only for series given at the same points: a point
    that one series draws and the other lacks gives no key; zeros compare as equal only to zeros; the tolerance is
    rounded up."""
    from figs import common
    assert common.agree_entry("a3", "a4", [1.0, 1.5, None], [1.0, 1.5, 2.6], 5) is None
    assert common.agree_entry("a3", "a4", [None, 1.5], [None, 1.5], 5)["key"] == "A3 = A4"
    assert common.agreement([0.0, 1.0], [0.0, 1.0])["within_pct"] == 0
    assert common.agreement([0.0, 1.0], [0.001, 1.0]) is None
    assert common.agreement([1.0, 2.0], [1.0, 2.0, 3.0]) is None
    ag = common.agreement([1.0, 2.0], [1.0, 2.021])
    assert ag["within_pct"] == 2 and abs(ag["max_rel_diff"] - 0.0105) < 1e-12
    assert common.agree_entry("a3", "a4", [1.0, 2.0], [1.0, 2.021], 5)["key"] == "A3 ≈ A4 (within 2%)"


def test_pool_median_axis_writes_every_tick_exactly():
    """sf_e2_pool's linear median axis writes each tick with the decimals it needs (a step of 0.025 needs three)."""
    from figs.supp import sf_e2_pool
    scale, lim, ticks, fmt = sf_e2_pool.median_axis(1.0, 1.075)
    assert scale == "linear"
    assert all(abs(float(fmt(t)) - t) < 1e-12 for t in ticks)



def test_c47_sf_e1_sched_bound_label_in_math():  # C47
    """C47 (print check of the gate, U46): sf_e1_sched draws its bound's label in math, max(2, rho) with an italic rho
    as on its x axes and as Fig. 5(b) draws the same label; no theory label sets rho upright. C62: the panel title's
    rho is in math too (C47 kept it upright, "ρ = 4", since mathtext lifted its baseline off the panel letter's), and
    the title sits on its letter's baseline as printed (common.align_baselines; checked on the PDF in
    test_c62_g1_titles_and_legends_on_one_baseline)."""
    from figs.supp import sf_e1_sched  # C47
    data = fixture_payload("sf_e1_sched")["data"]  # C47
    assert data["labels"]["bound"] == sf_e1_sched.LABELS["bound"] == r"$\max(2,\rho)$"  # C47
    fig = sf_e1_sched.draw(data)  # C47
    theory = [t.get_text() for ax in fig.axes for t in ax.texts  # C47
              if getattr(t, "_sublet_role", "").startswith("theory_label")]  # C47
    assert theory and all(t == r"$\max(2,\rho)$" for t in theory) and not [t for t in theory if "ρ" in t]  # C47
    assert data["labels"]["c"] == "Adaptive lender, $\\rho=4$"  # C62 (C47: "Adaptive lender, ρ = 4", upright)


# ---------------------------------------------------------------------------------------------------------------
# C62 (2026-11-24; no figure text larger than the caption), group g1: Figs. 5 and 6 (Supplement Figs.
# fig:loss and fig:public) and the E1 and E10 supplementary panels at the C62 type scale.
G1_NAMES = ("fig5", "fig6", "sf_e1_sched", "sf_e1_rotation", "sf_e10_rho", "sf_e10_cross", "sf_e10b")
G1_TITLED = ("sf_e1_sched", "sf_e1_rotation", "sf_e10_rho", "sf_e10_cross", "sf_e10b")


def _g1_pdf_spans(pdf):
    """Text spans of a figure PDF: x, y of the first glyph's origin (the baseline; y down from the page top), size,
    font, text."""
    import fitz
    out = []
    with fitz.open(pdf) as doc:
        for block in doc[0].get_text("rawdict")["blocks"]:
            for line in block.get("lines", []):
                for s in line["spans"]:
                    text = "".join(c["c"] for c in s["chars"])
                    if text.strip():
                        x, y = s["chars"][0]["origin"]
                        out.append({"x": x, "y": y, "size": s["size"], "font": s["font"], "text": text})
    return out


@pytest.mark.parametrize("name", G1_NAMES)
def test_c62_g1_fig5_fig6_sf_e1_sf_e10_titles_and_legends_on_one_baseline(figs_env, name):
    """C62 (group g1): the panel titles of sf_e1_sched, sf_e1_rotation, sf_e10_rho, sf_e10_cross and sf_e10b are at
    the caption size (style.LABEL_PT), their rho in math, and each prints on its bold letter's baseline (within 0.1
    pt: a mathtext title sat up to 1 pt high before common.align_baselines); every one-row legend of the seven
    figures prints its labels on one baseline (A2's r-bar labels sat 0.9 pt above their plain neighbors)."""
    mod = module(name)
    rep = mod.main(["--from-extract", str(FIX / f"{name}.json")])
    spans = _g1_pdf_spans(rep["pdf"])
    fig = mod.draw(fixture_payload(name)["data"])
    to_pt, H = 72.0 / fig.dpi, fig.get_size_inches()[1] * 72.0
    r = fig.canvas.get_renderer()
    rows = [leg for leg in fig.legends if leg._ncols == len(leg.get_texts()) > 1]
    assert rows or name in ("sf_e1_rotation",), name                 # sf_e1_rotation: a two-row corner legend
    for leg in rows:
        bb = leg.get_window_extent(r)
        ys = [s["y"] for s in spans if abs(s["size"] - style.TICK_PT) < 0.01
              and bb.x0 * to_pt - 1 <= s["x"] <= bb.x1 * to_pt + 1 and H - bb.y1 * to_pt - 1 <= s["y"] <= H - bb.y0 * to_pt + 1]
        assert len(ys) >= len(leg.get_texts()) and max(ys) - min(ys) <= 0.1, (name, ys)
    letters = [t for t in fig.texts if getattr(t, "_sublet_role", "") == "panel_letter"]
    titles = [t for t in fig.texts if t.get_text() and t not in letters and t.get_fontsize() == style.LABEL_PT]
    if name not in G1_TITLED:
        assert titles == []
        return
    assert len(titles) == len(letters) == len(fig.axes) and all("ρ" not in t.get_text() for t in titles)
    bold = [s for s in spans if "Bold" in s["font"] and s["text"].startswith("(")]
    assert len(bold) == len(letters)
    for b in bold:
        mine = [s for s in spans if "Bold" not in s["font"] and abs(s["size"] - style.LABEL_PT) < 0.01
                and abs(s["y"] - b["y"]) < 2.0 and s["x"] > b["x"]]
        assert mine and max(abs(s["y"] - b["y"]) for s in mine) <= 0.1, (name, b, mine)


@pytest.mark.parametrize("name", ("fig6", "sf_e10_rho", "sf_e10_cross"))
def test_c62_g1_fig6_sf_e10_rho_sf_e10_cross_legend_samples_as_drawn(name):
    """C62 (group g1; C52 for Fig. 6): each policy's legend sample is drawn in its series' line style, Marking's dashed
    (public information) and the others solid, in sf_e10_rho and sf_e10_cross as in Fig. 6 (as built their samples
    were all solid); the dashed samples have their pattern centered (fig7_e2_e6.centered_dashes)."""
    fig = module(name).draw(fixture_payload(name)["data"])
    style_of = {}
    for leg in fig.legends:
        for h, t in zip(leg.legend_handles, leg.get_texts()):
            style_of[t.get_text()] = h
    want_dashed = {style.POLICIES["marking"].label, "Public information"}
    assert want_dashed <= set(style_of), set(style_of)
    for text, h in style_of.items():
        dashed = h.get_linestyle() == "--"
        assert dashed == (text in want_dashed), (name, text, h.get_linestyle())
        if dashed:
            offset, pattern = h._unscaled_dash_pattern
            assert offset > 0 and list(pattern) == [float(v) for v in mpl_rc("lines.dashed_pattern")]


def mpl_rc(key):
    import matplotlib as mpl
    return mpl.rcParams[key]


def test_c62_g1_fig6_label_column_measured_heights():
    """C62 (group g1): a mathtext label line is taller than the 1.2 em (common.LINE_STEP_PT) that right_theory_lines
    allows by default, so Fig. 6's three-line limit label overlapped "LB$_A$ (private)" at 7 pt; with measured=True the
    column is stacked on the labels' own heights (common.text_height_pt), and Fig. 6 passes the overlap check."""
    from figs import common
    fig = style.new_figure("fig6")
    lab = module("fig6").MAIN_LABELS
    assert common.text_height_pt(fig, lab["LB_A"]) > common.LINE_STEP_PT
    three = "LB$_C$ limit\n(public), $T\\longrightarrow\\infty$\n≈ Marking"
    assert common.text_height_pt(fig, three) > 3 * common.LINE_STEP_PT
    data = fixture_payload("fig6")["data"]
    fig = module("fig6").draw(data)
    assert style.text_overlaps(fig) == []
    texts = {t.get_text(): t for t in fig.axes[0].texts if getattr(t, "_sublet_role", "").startswith("theory_label")}
    assert set(texts) == {data["labels"][k] for k in ("O1B", "O1D", "LB_A", "LB_C_max")}
    # the y label centered on the spine (the data), below the legend's headroom
    ax = fig.axes[0]
    r = fig.canvas.get_renderer()
    lo, hi = (ax.transData.transform((1.0, v))[1] for v in ax.spines["left"].get_bounds())
    bb = ax.yaxis.label.get_window_extent(r)
    assert abs(0.5 * (bb.y0 + bb.y1) - 0.5 * (lo + hi)) * 72.0 / fig.dpi < 0.5


def test_c62_g1_fig5_b_labels_rho_one_and_a_half_and_log_axes_without_minor_ticks():
    """C62 (group g1): at 7 pt Fig. 5(b)'s data area labels rho = 1.5 beside 2 (PANEL_RATIOS 0.95 : 1.1 : 0.95; at
    9 pt 1.5 was an unlabeled tick), and the log y axes of Fig. 5(b) and sf_e1_sched have no minor ticks between their
    labeled 1, 2, 5, 10, 20 (as Fig. 7)."""
    fig = module("fig5").draw(fixture_payload("fig5")["data"])
    ax_b = fig.axes[1]
    fig.canvas.draw()
    lo, hi = ax_b.get_xlim()
    shown = [t.get_text() for t in ax_b.get_xticklabels() if t.get_text() and lo <= t.get_position()[0] <= hi]
    assert shown[:2] == ["1.5", "2"], shown
    assert list(ax_b.yaxis.get_minorticklocs()) == []
    fig = module("sf_e1_sched").draw(fixture_payload("sf_e1_sched")["data"])
    assert all(list(ax.yaxis.get_minorticklocs()) == [] for ax in fig.axes)


def test_c62_g1_sf_e10b_sf_e10_rho_labels_and_height():
    """C62 (group g1): sf_e10b's order labels in math, min(rho, m) and min(rho, 1 + log_2 m) as plotted (as built
    "log m", upright rho), and no order label within 2 pt of the axes top (label_room), clear of the caption-size
    titles; sf_e10_rho is 2.3 in high (2.5 in at 9 pt), its titles name the lenders, and (b)-(d) keep a gutter between
    the label column on their left and their tick labels."""
    from figs.supp import sf_e10b, sf_e10_rho
    lab = fixture_payload("sf_e10b")["data"]["labels"]
    assert lab["order_m"].startswith("$\\min(\\rho,m)$") and "\\log_2m" in lab["order_log"] and "ρ" not in lab["panel"]
    fig = sf_e10b.draw(fixture_payload("sf_e10b")["data"])
    r = fig.canvas.get_renderer()
    for ax in fig.axes:
        top = ax.get_window_extent(r).y1
        for t in ax.texts:
            if getattr(t, "_sublet_role", "").startswith("theory_label"):
                assert (top - t.get_window_extent(r).y1) * 72.0 / fig.dpi >= sf_e10b.TITLE_CLEAR_PT - 0.01
    assert style.figure_spec("sf_e10_rho").height_in == 2.3
    data = fixture_payload("sf_e10_rho")["data"]
    assert data["labels"]["panel_a"].startswith("Adaptive lender, $\\rho=")
    assert data["labels"]["panel_o"].startswith("Oblivious lenders, $\\rho=")
    fig = sf_e10_rho.draw(data)
    r = fig.canvas.get_renderer()
    for left, right in zip(fig.axes[:-1], fig.axes[1:]):
        ends = [t.get_window_extent(r).x1 for t in left.texts if t.get_text()]
        starts = [tk.label1.get_window_extent(r).x0 for tk in right.yaxis.get_major_ticks()
                  if tk.label1.get_visible() and tk.label1.get_text()]
        assert (min(starts) - max(ends)) * 72.0 / fig.dpi >= 4.0


# C62 fix round (group g1, the supplement's critic): the layouts on the fixture extracts and on the versioned extracts
# of code/sim/out/figs/ (read only), where the critic's cases arise
G1_REAL = Path(__file__).resolve().parents[1] / "out" / "figs"


def _g1_data(name, source):
    if source == "fixture":
        return fixture_payload(name)["data"]
    return json.loads((G1_REAL / f"{name}.json").read_text())["data"]


@pytest.mark.parametrize("source", ("fixture", "versioned"))
@pytest.mark.parametrize("name", ("sf_e10b", "sf_e10_rho"))
def test_c62_g1_fix_one_data_width_and_equal_gutters(name, source):
    """C62 fix round: the four panels of sf_e10b and of sf_e10_rho plot one quantity against the same m, so their data
    areas are equally wide (as built 1.20, 0.95, 1.20, 0.95 in and 0.82, 0.82, 0.91, 0.99 in: the label columns took
    the width), each axes widened by its own label column (sf_e10b.equal_data_ratios); the gutters between a label
    column's widest text and the next panel's tick labels (sf_e10_rho, each panel reserving its own; the next spine in
    sf_e10b, whose panels share the y axis) are equal and at least 4 pt."""
    from figs.supp.sf_e10b import data_width_in
    fig = module(name).draw(_g1_data(name, source))
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    widths = [data_width_in(ax) for ax in fig.axes]
    assert len(widths) == 4 and max(widths) - min(widths) < 0.002, widths
    gutters = []
    for left, right in zip(fig.axes[:-1], fig.axes[1:]):
        end = max(t.get_window_extent(r).x1 for t in left.texts
                  if getattr(t, "_sublet_role", "").startswith("theory_label"))
        lo, hi = sorted(right.get_ylim())
        ticks = [t.get_window_extent(r).x0 for t in right.get_yticklabels()
                 if t.get_visible() and t.get_text() and lo <= t.get_position()[1] <= hi]
        start = min(ticks) if ticks else right.get_window_extent(r).x0
        gutters.append((start - end) * 72.0 / fig.dpi)
    assert max(gutters) - min(gutters) < 0.05 and min(gutters) >= 4.0, gutters


@pytest.mark.parametrize("source", ("fixture", "versioned"))
@pytest.mark.parametrize("name", ("fig5", "sf_e1_sched", "sf_e10b"))
def test_c62_g1_fix_keys_and_direct_labels_clear_of_the_spine(name, source):
    """C62 fix round: every coincidence key and direct label starts at least fig5_e1_e10.SPINE_CLEAR_PT (4 pt) right of
    its panel's y spine (as built sf_e1_sched (c)'s key started 1.5 pt and Fig. 5(a)'s "rho < 2" 2.5 pt from it);
    sf_e1_sched (c)'s key is on two lines and centered over its panel; sf_e10b's keys keep TEXT_GAP_PT (1 em) beside
    a text level with them (with (d)'s wider data area its key came 4 pt before "min(rho, m)")."""
    from figs.fig5_e1_e10 import SPINE_CLEAR_PT, TEXT_GAP_PT, spine_gap_pt, text_gap_pt
    fig = module(name).draw(_g1_data(name, source))
    fig.canvas.draw()
    placed = [(ax, a) for ax in fig.axes for a in list(ax.texts) + list(ax.artists)
              if getattr(a, "_sublet_role", "") in ("key", "direct_label")]
    assert placed or (source, name) == ("fixture", "sf_e10b")       # the synthetic sf_e10b has no agreeing pair
    for ax, a in placed:
        assert spine_gap_pt(ax, a) >= SPINE_CLEAR_PT - 0.05, (name, ax.get_label(), spine_gap_pt(ax, a))
        if name == "sf_e10b":
            assert text_gap_pt(ax, a) >= TEXT_GAP_PT - 0.05, (name, text_gap_pt(ax, a))
    if name == "sf_e1_sched" and source == "versioned":
        r = fig.canvas.get_renderer()
        ax = fig.axes[2]
        (key,) = [a for a in ax.artists if getattr(a, "_sublet_role", "") == "key"]
        assert "\n(within" in key.get_texts()[0].get_text()
        bb, ab = key.get_window_extent(r), ax.get_window_extent(r)
        assert abs(0.5 * (bb.x0 + bb.x1) - 0.5 * (ab.x0 + ab.x1)) * 72.0 / fig.dpi < 1.0


# ---------------------------------------------------------------------------------------------------------------
# C62 (group g2): sf_e2_por, sf_e2_mu_ep, sf_e2_mu_cost, sf_e2_pool, sf_e6a, sf_e6b
G2_NAMES = ("sf_e2_por", "sf_e2_mu_ep", "sf_e2_mu_cost", "sf_e2_pool", "sf_e6a", "sf_e6b")
G2_TITLED = ("sf_e2_por", "sf_e2_mu_ep", "sf_e2_mu_cost", "sf_e2_pool", "sf_e6a")   # sf_e2_pool: C62 fix round


def _g2_accent(text):
    import unicodedata
    return all(unicodedata.combining(c) for c in text.strip())


def test_c62_g2_sf_e2_sf_e6_shared_drawers_keep_their_defaults():
    """C62 (group g2): the keywords that sf_e2_* and sf_e6a pass to fig7_e2_e6's shared drawers are off by default, so
    that Fig. 7 draws as before (its PDF is compared byte for byte by the frozen rebuild); sf_e6b's small_shares, which
    sf_e7_mix imports, keeps its defaults (end_gap_pt SMALL_GAP_PT, va 'center')."""
    import inspect
    from figs import fig7_e2_e6 as f7
    from figs.supp import sf_e6b
    assert inspect.signature(f7.draw_episode_panel).parameters["cr_clear_bands"].default is False
    assert inspect.signature(f7.cr_label_end).parameters["avoid_lines"].default == ()
    p = inspect.signature(sf_e6b.small_shares).parameters
    assert p["end_gap_pt"].default == sf_e6b.SMALL_GAP_PT == 2.0 and p["va"].default == "center"


@pytest.mark.parametrize("name", G2_NAMES)
def test_c62_g2_sf_e2_sf_e6_titles_and_keys_on_one_baseline(figs_env, name):
    """C62 (group g2), in the PDF: the panel titles of sf_e2_por, sf_e2_mu_ep, sf_e2_mu_cost, sf_e2_pool (since the fix
    round) and sf_e6a at the caption size (style.LABEL_PT), each on its bold letter's baseline within 0.05 pt
    (fig7_e2_e6.panel_titles; a mathtext title sat up to 0.2 pt off; 0.1 pt before the fix round); every key row prints
    its title and labels on one baseline within 0.1 pt (fig7_e2_e6.key_row:
    as built, sf_e2_por's two-row legend set its second row 2.3 pt lower under its mathtext entries, and
    sf_e2_mu_cost's "Minimum over $H$" sat 1 pt above "ALG*"); sf_e6b's keys on their letters' baselines."""
    mod = module(name)
    rep = mod.main(["--from-extract", str(FIX / f"{name}.json")])
    spans = [s for s in _g1_pdf_spans(rep["pdf"]) if not _g2_accent(s["text"])]
    fig = mod.draw(fixture_payload(name)["data"])
    to_pt, H = 72.0 / fig.dpi, fig.get_size_inches()[1] * 72.0
    r = fig.canvas.get_renderer()
    legs = [leg for leg in list(fig.legends) + [ax.get_legend() for ax in fig.axes if ax.get_legend()]
            if leg._ncols == len(leg.get_texts()) > 1]
    assert legs or name in ("sf_e2_pool", "sf_e6a"), name     # corner keys of one column; a colorbar
    bold = [s for s in spans if "Bold" in s["font"] and s["text"].startswith("(")]
    assert len(bold) == len(fig.axes)
    for leg in legs:
        bb = leg.get_window_extent(r)
        ys = [s["y"] for s in spans if abs(s["size"] - style.TICK_PT) < 0.01
              and bb.x0 * to_pt - 1 <= s["x"] <= bb.x1 * to_pt + 1
              and H - bb.y1 * to_pt - 1 <= s["y"] <= H - bb.y0 * to_pt + 1]
        assert len(ys) >= len(leg.get_texts()) and max(ys) - min(ys) <= 0.1, (name, ys)
        if name == "sf_e6b":                                              # letter_key: on the letter's line
            assert min(abs(ys[0] - b["y"]) for b in bold) <= 0.1, (ys, bold)
    if name not in G2_TITLED:
        return
    for b in bold:
        mine = [s for s in spans if "Bold" not in s["font"] and abs(s["size"] - style.LABEL_PT) < 0.01
                and abs(s["y"] - b["y"]) < 2.0 and s["x"] > b["x"]]
        assert mine and max(abs(s["y"] - b["y"]) for s in mine) <= 0.05, (name, b, mine)


def test_c62_g2_sf_e2_por_key_rows_and_gutter():
    """C62 (group g2): sf_e2_por's key is two rows (key_row) centered over the axes, KEY_ROW_IN apart, the first led by
    "mu/beta~ =" and the four values darkest first, the second the C2-SW circles and the Table PoR crosses; (b)'s
    letter starts right of (a)'s axes (SHARED_GUTTER_IN); the y grid behind both panels."""
    from figs import fig7_e2_e6 as f7
    data = fixture_payload("sf_e2_por")["data"]
    fig = module("sf_e2_por").draw(data)
    r = fig.canvas.get_renderer()
    rows = [leg for leg in fig.legends if getattr(leg, "_sublet_role", "") == "key_row"]
    assert [[t.get_text() for t in leg.get_texts()] for leg in rows] == [
        [data["labels"]["mu_title"]] + [data["labels"]["mu"].format(m) for m in sorted(data["mus"], reverse=True)],
        [data["labels"]["c2sw"], data["labels"]["plus"]]]
    ra, rb = style.axes_rect_in(fig.axes[0]), style.axes_rect_in(fig.axes[1])
    centers = [leg.get_window_extent(r) for leg in rows]
    for bb in centers:
        assert abs(0.5 * (bb.x0 + bb.x1) / fig.dpi - 0.5 * (ra[0] + rb[0] + rb[2])) < 0.01
    assert abs((0.5 * (centers[0].y0 + centers[0].y1) - 0.5 * (centers[1].y0 + centers[1].y1)) / fig.dpi
               - f7.KEY_ROW_IN) < 0.005
    letters = [t for t in fig.texts if getattr(t, "_sublet_role", "") == "panel_letter"]
    assert letters[1].get_window_extent(r).x0 / fig.dpi >= ra[0] + ra[2] - 1e-6
    assert abs(rb[0] - (ra[0] + ra[2]) - f7.SHARED_GUTTER_IN) < 1e-6


def test_c62_g2_sf_e2_mu_ep_mu_cost_shared_axes_and_labels():
    """C62 (group g2): sf_e2_mu_ep and sf_e2_mu_cost share one y axis over their three panels (tick labels and y label
    on (a) only, SHARED_GUTTER_IN between the panels); sf_e2_mu_ep labels each MaaS band's top edge "P95" and keeps the
    exact curve's label clear of the spot band's dashed outline (cr_clear_bands); sf_e2_mu_cost names the lender
    lines in every panel and keys ALG* and the minimizer in one row."""
    import numpy as np
    from figs import fig7_e2_e6 as f7
    from figs.common import finite
    for name in ("sf_e2_mu_ep", "sf_e2_mu_cost"):
        data = fixture_payload(name)["data"]
        fig = module(name).draw(data)
        r = fig.canvas.get_renderer()
        axes = fig.axes[:3]
        assert all(ax.get_shared_y_axes().joined(axes[0], ax) for ax in axes[1:])
        assert axes[0].get_ylabel() and not any(ax.get_ylabel() for ax in axes[1:])
        assert not any(t.get_visible() and t.get_text() for ax in axes[1:] for t in ax.get_yticklabels())
        for a, b in zip(axes[:-1], axes[1:]):
            ra, rb = style.axes_rect_in(a), style.axes_rect_in(b)
            assert abs(rb[0] - (ra[0] + ra[2]) - f7.SHARED_GUTTER_IN) < 1e-6
        if name == "sf_e2_mu_ep":
            for ax, p in zip(axes, data["panels"]):
                assert [t.get_text() for t in ax.texts if t.get_text() == f7.P95_LABEL] == [f7.P95_LABEL]
                (cr,) = [t for t in ax.texts if getattr(t, "_sublet_role", "") == "theory_label:exact"]
                bb = cr.get_window_extent(r)
                s = p["a1"]["spot"]
                x, y, q = finite(s["H_min"]), finite(s["median"]), finite(s["p95"])
                ok = np.isfinite(x) & np.isfinite(y) & np.isfinite(q)
                P = ax.transData.transform(np.column_stack([np.r_[x[ok], x[ok][::-1]], np.r_[y[ok], q[ok][::-1]]]))
                P = f7._dense(np.vstack([P, P[:1]]), step=0.5 * fig.dpi / 72.0)
                inside = (P[:, 0] > bb.x0) & (P[:, 0] < bb.x1) & (P[:, 1] > bb.y0) & (P[:, 1] < bb.y1)
                assert not inside.any(), (p["mu"], cr.get_text())
        else:
            for ax in axes:
                names = sorted(t.get_text() for t in ax.texts if getattr(t, "_sublet_role", "") == "direct_label")
                assert names == sorted(style.ENV_LABELS["lender"][g] for g in f7.GROUPS)
            (row,) = [leg for leg in fig.legends if getattr(leg, "_sublet_role", "") == "key_row"]
            assert [t.get_text() for t in row.get_texts()] == [style.policy("a1").label, data["labels"]["minimum"]]


def test_c62_g2_sf_e2_pool_c_names_and_range():
    """C62 (group g2): sf_e2_pool (c) names the lender lines directly (lender_names) and keys only the two schedules,
    in a corner its data leave free, so that its y range is the data's padded by 6% (as built, a two-column key with
    ALG* and the line styles raised it, legend_headroom); (a) and (b) have one-line y labels. C62 fix round: (c)'s top
    is raised only where its top tick label would reach within TOP_TICK_GAP_PT of the axes top (top_tick_room, clear
    of the panel title), every tick kept."""
    import numpy as np
    from figs.common import TOP_TICK_GAP_PT
    from figs.supp import sf_e2_pool
    data = fixture_payload("sf_e2_pool")["data"]
    fig = sf_e2_pool.draw(data)
    ax_a, ax_b, ax_c = fig.axes[:3]
    assert "\n" not in ax_a.get_ylabel() and ax_a.get_ylabel() == ax_b.get_ylabel()
    names = sorted(t.get_text() for t in ax_c.texts if getattr(t, "_sublet_role", "") == "direct_label")
    assert names == sorted(style.ENV_LABELS["lender"].values())
    assert [t.get_text() for t in ax_c.get_legend().get_texts()] == [data["labels"]["trace"], data["labels"]["eager"]]
    vals = [v for g in data["c"].values() for s in g.values() for f in ("median", "ci_lo", "ci_hi") for v in s[f]
            if v is not None]
    lo, hi = min(vals + [1.0]), max(vals)
    y0, y1 = ax_c.get_ylim()
    assert y0 == pytest.approx(lo - 0.06 * (hi - lo)) and y1 >= hi + 0.06 * (hi - lo) - 1e-12
    assert np.isfinite(ax_c.get_ylim()).all()
    r = fig.canvas.get_renderer()
    to_pt = 72.0 / fig.dpi
    top = ax_c.get_window_extent(r).y1 * to_pt
    tops = [tk.label1.get_window_extent(r).y1 * to_pt for tk in ax_c.yaxis._update_ticks()
            if y0 <= tk.get_loc() <= y1 and tk.label1.get_visible() and tk.label1.get_text()]
    assert tops and max(tops) <= top - TOP_TICK_GAP_PT + 0.01
    if y1 > hi + 0.06 * (hi - lo) + 1e-12:                      # raised: no more than the gap needs
        assert max(tops) == pytest.approx(top - TOP_TICK_GAP_PT, abs=0.01)


def test_c62_g2_fix_titles_names_and_math():
    """C62 fix round (group g2): sf_e2_pool's panels are titled beside their letters at the caption size, as the
    family's other figures (labels.titles; as built it was the only untitled one), and (a)'s legend names the pool
    Series 2 as the paper's Fig. 2 and its caption do (as built "series-2"); sf_e6a's titles set lambda' in math (mathtext
    lambda\\prime, the prime at full size as LaTeX prints $\\lambda'$; as built an upright Unicode glyph) and
    sf_e2_por's y label alpha (as built an upright "α"); no title or label of the group's figures prints an upright
    Greek letter from Unicode."""
    import re
    from figs.supp import sf_e2_pool
    data = fixture_payload("sf_e2_pool")["data"]
    assert sf_e2_pool.pool_label("a1:GPU-series-2") == "Series 2"
    assert sf_e2_pool.pool_label("a1:A100-SXM4-80GB") == "A100"
    fig = sf_e2_pool.draw(data)
    titles = [t for t in fig.texts if getattr(t, "_sublet_role", "") == "panel_title"]
    assert [t.get_text() for t in titles] == [data["labels"]["titles"][p] for p in "abc"]
    assert [t.get_text() for t in titles] == ["Spot pools", "MaaS clusters by price quartile", "Whole traces"]
    assert all(t.get_fontsize() == style.LABEL_PT for t in titles)
    legend = [t.get_text() for t in fig.axes[0].get_legend().get_texts()]
    assert "Series 2" in legend or not any("series-2" in s["label"].lower() for s in data["a"].values())
    e6a = fixture_payload("sf_e6a")["data"]["labels"]["titles"]
    assert all(r"$\lambda\prime$" in t and "λ" not in t and "′" not in t for t in e6a.values())
    assert fixture_payload("sf_e2_por")["data"]["labels"]["y"] == r"PoR = CR* / (2 − $\alpha$)"
    greek = re.compile("[Ͱ-΢Τ-Ͽ]")         # Greek letters except the sum sign Sigma (U+03A3)
    for name in G2_NAMES:
        fig = module(name).draw(fixture_payload(name)["data"])
        texts = [t.get_text() for t in fig.texts] + [ax.get_ylabel() for ax in fig.axes] \
            + [ax.get_xlabel() for ax in fig.axes] + [t.get_text() for ax in fig.axes for t in ax.texts]
        assert not any(greek.search(t) for t in texts), (name, [t for t in texts if greek.search(t)])


@pytest.mark.parametrize("name", ("sf_e2_mu_ep", "sf_e2_mu_cost", "sf_e2_pool", "sf_e6a"))
def test_c62_g2_fix_title_descenders_clear_the_axes(name):
    """C62 fix round (group g2): the axes' tops lie sf_e2_mu_ep.title_drop_in below their standard place under the
    letters' line (the letters and titles where they were), so that a title's deepest descender (the ink of "p" at
    the caption size) ends TITLE_CLEAR_PT above the axes' top, half a spine width included (as built, the titles' mu
    met the tops of sf_e2_mu_ep's and sf_e2_mu_cost's y spines and "Spot," crossed sf_e6a's top frame)."""
    from matplotlib.font_manager import FontProperties
    from matplotlib.textpath import TextPath
    from figs.supp import sf_e2_mu_ep as ep
    fig = module(name).draw(fixture_payload(name)["data"])
    H = fig.get_size_inches()[1]
    letters = [t for t in fig.texts if getattr(t, "_sublet_role", "") == "panel_letter"]
    titles = [t for t in fig.texts if getattr(t, "_sublet_role", "") == "panel_title"]
    assert len(letters) == len(titles) == 3
    descent = -TextPath((0.0, 0.0), "p", size=style.LABEL_PT, prop=FontProperties()).vertices[:, 1].min()
    for ax, letter in zip(fig.axes[:3], letters):
        x0, y0, w, h = style.axes_rect_in(ax)
        rise_pt = (letter.get_position()[1] * H - (y0 + h)) * 72.0
        assert rise_pt == pytest.approx(ep.LETTER_RISE_PT + ep.title_drop_in() * 72.0, abs=1e-6)
        assert rise_pt - descent - 0.5 * style.AXES_PT >= ep.TITLE_CLEAR_PT - 1e-6
    standard = {"sf_e2_mu_ep": style.MARGIN_TOP + style.LEGEND_ROW, "sf_e2_mu_cost": style.MARGIN_TOP + style.LEGEND_ROW,
                "sf_e2_pool": style.MARGIN_TOP, "sf_e6a": style.MARGIN_TOP}[name]
    for letter in letters:                                          # the letters' line where it was
        assert letter.get_position()[1] * H == pytest.approx(H - standard + ep.LETTER_RISE_PT / 72.0, abs=1e-9)


def test_c62_g2_sf_e6a_frames_cues_halo_and_gutters():
    """C62 (group g2): sf_e6a's heatmaps are framed on all four sides, each has a cue in every region its cells have
    ("< 1", "= 1", "> 1", region_cues) over a cell of that region, the boundary's halo is HEAT_HALO_PT on each side,
    and (b) and (c) follow SHARED_GUTTER_IN after their left neighbors."""
    import numpy as np
    from figs import fig7_e2_e6 as f7
    from figs.supp import sf_e6a
    data = fixture_payload("sf_e6a")["data"]
    fig = sf_e6a.draw(data)
    r = fig.canvas.get_renderer()
    axes = fig.axes[:3]
    for ax, (p, _, _) in zip(axes, sf_e6a.PANELS):
        assert all(ax.spines[s].get_visible() for s in ("left", "bottom", "top", "right"))
        block = data[p]
        vals = np.array([[np.nan if v is None else v for v in row] for row in block["values"]], dtype=float)
        level, tol = block["contour"]["level"], block["contour"]["tol"]
        below, above = vals < level * (1 - tol), vals > level * (1 + 1e-9)
        regions = {"< 1": below, "> 1": above, "= 1": np.isfinite(vals) & ~below & ~above}
        cues = {t.get_text(): t for t in ax.texts if getattr(t, "_sublet_role", "") == "sign_cue"}
        assert set(cues) == {k for k, m in regions.items() if m.any()}
        for text, t in cues.items():
            bb = t.get_window_extent(r)
            x, y = ax.transData.inverted().transform((0.5 * (bb.x0 + bb.x1), 0.5 * (bb.y0 + bb.y1)))
            j = int(np.searchsorted(block["x_edges"], x)) - 1
            i = int(np.searchsorted(block["y_edges"], y)) - 1
            assert regions[text][i, j], (p, text)
        bound = [ln for ln in ax.lines if getattr(ln, "_sublet_role", "") == "theory:lower"]
        halos = [ln for ln in ax.lines if getattr(ln, "_sublet_role", "") == "halo"]
        assert [h.get_linewidth() for h in halos] == pytest.approx([b.get_linewidth() + 2 * f7.HEAT_HALO_PT
                                                                    for b in bound])
    for a, b in zip(axes[:-1], axes[1:]):
        ra, rb = style.axes_rect_in(a), style.axes_rect_in(b)
        assert abs(rb[0] - (ra[0] + ra[2]) - f7.SHARED_GUTTER_IN) < 1e-6


def test_c62_g2_sf_e6b_fills_keys_and_separators():
    """C62 (group g2): sf_e6b is 1.9 in high (2.2 in at 9 pt); (a)'s components carry Fig. 3(a)'s fills
    (fig4_v3.COMPONENT_FILLS) and the all-fallback level 1 is a reference line behind the bars; each panel's key is one
    row on its letter's line, ending before the next panel's slot or the page margin (letter_key); the rows fill the
    axes (no key band); no white separator runs under a printed share in (b)."""
    from matplotlib.colors import to_hex
    from figs import fig4_v3
    from figs.supp import sf_e6b
    assert style.figure_spec("sf_e6b").height_in == 1.9
    assert sf_e6b.COMPONENT_FILLS == fig4_v3.COMPONENT_FILLS and sf_e6b.HATCH_COLOR == fig4_v3.HATCH_COLOR
    data = fixture_payload("sf_e6b")["data"]
    fig = sf_e6b.draw(data)
    r = fig.canvas.get_renderer()
    ax_a, ax_b = fig.axes[:2]
    refs = [ln for ln in ax_a.lines if getattr(ln, "_sublet_role", "") == "reference"]
    assert [list(ln.get_xdata()) for ln in refs] == [[1.0, 1.0]]
    n = len(data["menus"])
    assert ax_a.get_ylim() == ax_b.get_ylim() == (n - 0.5, -0.5)
    letters = [t for t in fig.texts if getattr(t, "_sublet_role", "") == "panel_letter"]
    W = fig.get_size_inches()[0]
    for ax, letter, end in ((ax_a, letters[0], ax_b._sublet_slot_left_in), (ax_b, letters[1], W - style.MARGIN_RIGHT)):
        leg = ax.get_legend()
        assert getattr(leg, "_sublet_role", "") == "letter_key" and leg._ncols == len(leg.get_texts())
        bb = leg.get_window_extent(r)
        assert bb.x0 >= letter.get_window_extent(r).x1 and bb.x1 / fig.dpi <= end - sf_e6b.KEY_END_GAP_PT / 72.0 + 1e-6
    fills = {to_hex(p.get_facecolor()) for p in ax_a.patches if p.get_fill() and p.get_width() > 0}
    assert fills <= {f["facecolor"].lower() for f in sf_e6b.COMPONENT_FILLS.values()}
    seps = [ln for ln in ax_b.lines if ln.get_color() == "white"]
    assert seps
    inv = ax_b.transData.inverted()
    shares = []                                         # (row, x0, x1) of each printed share, in data coordinates
    for t in ax_b.texts:
        bb = t.get_window_extent(r)
        (x0, y0), (x1, y1) = inv.transform([(bb.x0, bb.y0), (bb.x1, bb.y1)])
        shares.append((round(0.5 * (y0 + y1)), x0, x1))
    for ln in seps:
        x, row = ln.get_xdata()[0], round(sum(ln.get_ydata()) / 2.0)
        assert not any(i == row and x0 <= x <= x1 for i, x0, x1 in shares), (row, x)
