"""Tests of Tables IV and V of the MS7 manuscript: figs/table3_v3.py (label tab:e7) and figs/table5_alglb.py (label
tab:alglb), with their rebuild entries in figs/rebuild.py (design/ms7/w_spec.md §2.8 and §4, unit W-G2; change C58).

Quick (the compile and height cases are skipped without pdflatex). The inputs are the input tree
tests/fixtures_figs_ms7/inputs/ (reduced-mode outputs, not results; README there) and the fixture extracts
tests/fixtures_figs_ms7/table3_v3.json and table5_alglb.json (tests/fixtures_figs_ms7/refresh_extracts.py); every file is
written under pytest's tmp_path.

- The rows are style.TABLE_POLICIES_MS7's, printed by their registry labels; Table IV has at most 16 rows.
- build() on the input tree gives the fixture extract; --from-extract rewrites the float byte for byte and the extract
  unchanged; the float has its label, booktabs rules and one row per policy.
- Value oracles: Table IV's confirmation rows are Table III v2's per-week cells, their r0 the confirmation summary's
  (100 (1 - r0) = Table III v2's saving in every week); MPC and protected-only renting from the e7r analysis and eval
  runs (overflow ALG, total = overflow + own capacity); r0 and W0 with their min-max over the weeks below the median
  (RC16(4)), none for All-fallback; the lagged column from the e7c analysis
  through lag_minus_revealed; the kbar column from the e7r transplants; "--" where no run exists; the note names the
  lagged cell of RetroRenting-style's row, RetroRenting-style, lagged (the e7c analysis's lagged BL5-cur, in its
  h1_set), by its registry label as a primary baseline (C9). Table V's medians and
  ranges from part second's gap ratios, All-fallback's from its bill over the bound, the seed spread from the S1 v2
  analysis; the bound-gap column appears only when a bound file is a MILP's.
- The checks: a missing input (exit 2, the file named), weeks that differ, a bl0a_usd that differs, an e7c analysis in
  which BL5 is not the lagged BL5-cur or not a primary baseline, an S1 v2 analysis of other confirmation summaries;
  reduced input is never written into paper/floats/.
- With the paper's class, macros and the ms7 label stub both floats compile without an overfull box, Table IV's note
  in three lines (two before C9); at real scale (the versioned confirmation files with stand-in run analyses in tmp_path)
  floats_heights.py --ms7's measure() puts Table IV, with its ranges (RC16(4)), no higher than Table III v2, the float
  it replaces (TABLE4_MAX_PAGES, floats_heights_ms5b.json: 0.2767 page; 0.2577 on the confirmation; the budget 0.198
  of BUDGETS_MS7 predates the ranges), and Table V at the pages study's measured mock (0.1202 page, the source of its
  0.120 budget).
- figs/rebuild.py (C58): both tables are float entries after Table III v2, pending without their run outputs.
"""
from __future__ import annotations

import importlib
import json
import os
import shutil
import statistics
import subprocess
import sys
from pathlib import Path

import pytest

from figs import style
from figs import rebuild as rb
from figs.inputs import Inputs

FIX = Path(__file__).resolve().parent / "fixtures_figs_ms7"
IN_ROOT = FIX / "inputs"
OUT = IN_ROOT / "code" / "sim" / "out"
REPO = style.REPO
PAPER = REPO / "paper"
LAYOUT = PAPER / "layout_check"
PDFLATEX = Path.home() / ".local" / "bin" / "pdflatex"
TABLES = {"table3_v3": "figs.table3_v3", "table5_alglb": "figs.table5_alglb"}
TABLE4_MAX_PAGES = 0.2767       # Table III v2's measured height (floats_heights_ms5b.json), the float Table IV replaces


def mod(name):
    return importlib.import_module(TABLES[name])


def jl(p):
    return json.loads(Path(p).read_text())


def stale(name):
    return (f"tests/fixtures_figs_ms7/{name}.json is stale: refresh it with `python "
            f"tests/fixtures_figs_ms7/refresh_extracts.py --only {name}` from code/sim")


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("SUBLET_FIGS_IN_ROOT", str(IN_ROOT))
    monkeypatch.setenv(style.ENV_PDF_DIR, str(tmp_path / "pdf"))
    monkeypatch.setenv(style.ENV_OUT_DIR, str(tmp_path / "out"))
    return tmp_path


def copy_tree(tmp_path):
    root = tmp_path / "tree"
    shutil.copytree(IN_ROOT, root)
    return root


# ---------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("name", sorted(TABLES))
def test_rows_are_the_registry_labels(name):
    m = mod(name)
    keys = tuple(r[1] for r in m.ROWS)
    assert keys == style.TABLE_POLICIES_MS7[name] and len(keys) <= 16
    d = jl(FIX / f"{name}.json")["data"]
    assert [d["rows"][t]["label"] for t in d["order"]] == [style.POLICIES[k].label for k in keys]


@pytest.mark.parametrize("name", sorted(TABLES))
def test_build_matches_fixture_and_from_extract_is_byte_stable(name, env):
    m = mod(name)
    data = json.loads(json.dumps(m.build(Inputs()), allow_nan=False))
    data.pop("sources")
    assert data == jl(FIX / f"{name}.json")["data"], stale(name)
    rep = m.main(["--out", str(env / "a")])
    tex = (env / "a" / f"{name}.tex").read_text()
    assert jl(rep["json"]) == jl(FIX / f"{name}.json")
    m.main(["--from-extract", rep["json"], "--out", str(env / "b")])
    assert (env / "b" / f"{name}.tex").read_text() == tex
    assert rf"\label{{{m.LABEL}}}" in tex and r"\toprule" in tex and r"\bottomrule" in tex
    body = tex[tex.index(r"\midrule"):tex.index(r"\bottomrule")]
    assert [ln.split(" & ")[0] for ln in body.splitlines()[1:]] == [data["rows"][t]["label"] for t in data["order"]]
    assert "REDUCED INPUT" in tex


def test_table4_value_oracles():
    m = mod("table3_v3")
    d = jl(FIX / "table3_v3.json")["data"]
    t2 = jl(OUT / "figs" / "table3_v2.json")["data"]
    e7c, e7r = jl(OUT / "e7c" / "analysis.json"), jl(OUT / "e7r" / "analysis.json")
    ev = jl(OUT / "e7r" / "eval" / "summary.json")
    main = jl(OUT / "sublet_v2" / "main" / "summary.json")
    weeks = t2["caption_source"]["weeks"]
    own = {w: t2["rows"]["BL0a"]["cells"]["usd"]["total"]["by_cell"][w]
           - t2["rows"]["BL0a"]["cells"]["usd"]["overflow"]["by_cell"][w] for w in weeks}
    lag_of = {v["revealed"]: k for k, v in e7c["lag_minus_revealed"].items()}
    c2_of = {p["as_built"]: p["c2"] for p in e7r["as_built_vs_c2"]}
    med = statistics.median
    for tag, key, src in m.ROWS:
        cells = d["rows"][tag]["cells"]
        if src == "conf":
            c = t2["rows"][tag]["cells"]
            assert cells["usd"]["overflow"] == med(c["usd"]["overflow"]["by_cell"][w] for w in weeks)
            for col in ("saving_pct", "RC", "W0"):
                assert cells[col]["text"] == c[col]["text"], (tag, col)
            r0 = {w: (1.0 if tag == "BL0a" else main["table"][tag]["L-tr"][w]["0"]) for w in weeks}
            assert all(abs(100 * (1 - r0[w]) - c["saving_pct"]["by_cell"][w]) < 1e-9 for w in weeks), tag
            w0 = {w: c["W0"]["by_cell"][w] for w in weeks}
        else:
            alg = {r["cell"]: r["ALG"] for r in ev["runs"] if r["tag"] == tag and r["mode"] == "L-tr"}
            pw = e7r["tags"][tag]["per_week"]
            assert cells["usd"]["overflow"] == med(alg[w] for w in weeks)
            assert cells["usd"]["total"] == med(alg[w] + own[w] for w in weeks)
            assert cells["saving_pct"]["value"] == med(100 * (1 - pw[w]["r0_tr"]) for w in weeks)
            assert cells["W0"]["value"] == med(pw[w]["W0"] for w in weeks)
            assert cells["RC"]["value"] == med(pw[w]["RC"]["L-tr"] for w in weeks)
            r0 = {w: pw[w]["r0_tr"] for w in weeks}
            w0 = {w: pw[w]["W0"] for w in weeks}
        # RC16(4): r0 (in place of the saving) and W0 with their min-max over the weeks, none for the reference
        assert cells["r0"]["value"] == med(r0[w] for w in weeks) and cells["r0"]["by_week"] == r0, tag
        for col, vals in (("r0", r0), ("W0", w0)):
            assert (cells[col]["min"], cells[col]["max"]) == (min(vals.values()), max(vals.values())), (tag, col)
            want = None if tag == "BL0a" else f"{min(vals.values()):.3f}--{max(vals.values()):.3f}"
            assert cells[col]["range_text"] == want, (tag, col)
        if tag in lag_of:
            assert cells["lag_r0"]["value"] == med(e7c["per_policy"][lag_of[tag]]["r0"]["weeks"][w] for w in weeks)
        else:
            assert cells["lag_r0"]["text"] == "--"
        if tag in c2_of:
            assert cells["W0_kbar"]["value"] == med(e7r["tags"][c2_of[tag]]["per_week"][w]["W0"] for w in weeks)
        else:
            assert cells["W0_kbar"]["text"] == "--"
    assert d["rows"]["BL0a"]["cells"]["RC"]["text"] == "--" and d["rows"]["BL0a"]["cells"]["W0"]["text"] == "1.000"
    assert d["rows"]["BL0a"]["cells"]["r0"]["text"] == "1.000"
    assert d["columns"] == ["usd", "r0", "lag_r0", "RC", "W0", "W0_kbar"]
    assert d["rows"]["MPC-T"]["label"] == "MPC" and d["rows"]["A9-P"]["lagged"] is None
    # C9: RetroRenting-style's lagged cell is RetroRenting-style, lagged (tag BL5, the lagged BL5-cur of the e7c
    # analysis, in its h1_set: a primary baseline), named in the note by its registry label
    assert lag_of["BL5-cur"] == "BL5" and "BL5" in e7c["h1_set"] and d["rows"]["BL5-cur"]["lagged"] == "BL5"
    named = {"row": "BL5-cur", "row_label": style.POLICIES["bl5_cur"].label, "lagged": "BL5",
             "label": style.POLICIES["bl5_lag"].label, "primary": True}
    assert d["caption_source"]["lag_named"] == [named] and named["label"] == "RetroRenting-style, lagged"
    assert "(RetroRenting-style's row: RetroRenting-style, lagged, a primary baseline)" in d["note"]
    for old in ("Medians of per-week values, min--max below.", "$r_0$, lagged: demand one slot late",
                r"$W_0$, $\bar k$: with Algorithm~2's base contract.", "--: not run."):
        assert old in d["note"], old
    # RC16(4): the float prints each range below its median (the macro the float defines), not the saving
    tex = mod("table3_v3").float_tex(d)
    assert r"\providecommand{\TableIVcell}[2]" in tex and "Saving" not in tex
    sub = d["rows"]["Sublet"]["cells"]
    assert rf"\TableIVcell{{{sub['r0']['text']}}}{{{sub['r0']['range_text']}}}" in tex


def test_table5_value_oracles(tmp_path, monkeypatch):
    m = mod("table5_alglb")
    d = jl(FIX / "table5_alglb.json")["data"]
    sec = jl(OUT / "sublet_v2" / "second" / "summary.json")
    s1 = jl(OUT / "s1v2" / "analysis.json")
    cells = sorted({r["cell"] for r in sec["runs"] if r["kind"] == "gap"})
    for tag, key in m.ROWS:
        r = d["rows"][tag]
        if tag == "BL0a":
            vals = [next(x["bl0a_usd"] for x in sec["runs"] if x["kind"] == "gap" and x["cell"] == c) / sec["gap_lp"][c]
                    for c in cells]
        else:
            vals = [sec["gap_ratio"][f"{tag}:{c}:0"] for c in cells]
        assert (r["median"], r["min"], r["max"]) == (statistics.median(vals), min(vals), max(vals))
        sp = (s1["seed_spread"]["by_tag"].get(tag) or {}).get("max_abs_diff")
        assert r["seed_spread"] == sp and r["texts"]["seeds"] == ("--" if sp is None else f"{sp:.3f}")
    assert d["columns"] == ["gap", "range", "seeds"] and d["note"] == ""
    # a MILP bound file adds the bound-gap column and says so in the title
    root = copy_tree(tmp_path)
    for f in (root / "code/sim/out/sublet_v2/second/lb").glob("*.json"):
        b = jl(f)
        b.update(method="milp", gap=0.012)
        f.write_text(json.dumps(b))
    monkeypatch.setenv("SUBLET_FIGS_IN_ROOT", str(root))
    d2 = m.build(Inputs())
    assert d2["columns"] == ["gap", "range", "bound_gap", "seeds"] and "MILP dual bound" in d2["caption"]
    assert d2["rows"]["Sublet"]["texts"]["bound_gap"] == "0.012"


# ---------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("name,path", [("table3_v3", "code/sim/out/e7c/analysis.json"),
                                       ("table3_v3", "code/sim/out/e7r/eval/summary.json"),
                                       ("table5_alglb", "code/sim/out/s1v2/analysis.json")])
def test_missing_input_exits_2(name, path, tmp_path, monkeypatch, capsys):
    root = copy_tree(tmp_path)
    (root / path).unlink()
    monkeypatch.setenv("SUBLET_FIGS_IN_ROOT", str(root))
    monkeypatch.setenv(style.ENV_OUT_DIR, str(tmp_path / "out"))
    with pytest.raises(SystemExit) as e:
        mod(name).main(["--out", str(tmp_path / "f")])
    assert e.value.code == 2 and path in capsys.readouterr().err
    assert not (tmp_path / "f").exists()


def test_inconsistent_inputs_are_refused(tmp_path, monkeypatch):
    root = copy_tree(tmp_path)
    monkeypatch.setenv("SUBLET_FIGS_IN_ROOT", str(root))
    out = root / "code/sim/out"
    f = out / "e7c/analysis.json"
    old = f.read_text()
    q = json.loads(old)
    q["meta"]["weeks"] = ["999"]
    f.write_text(json.dumps(q))
    with pytest.raises(style.StyleError, match="weeks"):
        mod("table3_v3").build(Inputs())
    f.write_text(old)
    f = out / "e7r/eval/summary.json"
    q = jl(f)
    for r in q["runs"]:
        r["bl0a_usd"] *= 1.01
    f.write_text(json.dumps(q))
    with pytest.raises(style.StyleError, match="bl0a_usd"):
        mod("table3_v3").build(Inputs())
    f.write_text(json.dumps(jl(IN_ROOT / "code/sim/out/e7r/eval/summary.json")))
    f = out / "e7c/analysis.json"              # C9: BL5 must be the lagged BL5-cur and a primary baseline
    old = f.read_text()
    q = json.loads(old)
    q["h1_set"] = [t for t in q["h1_set"] if t != "BL5"]
    f.write_text(json.dumps(q))
    with pytest.raises(style.StyleError, match="h1_set"):
        mod("table3_v3").build(Inputs())
    q = json.loads(old)
    q["lag_minus_revealed"]["BL5"]["revealed"] = "BL5-tau60"
    q["lag_minus_revealed"].pop("BL5-tau60-lag")
    f.write_text(json.dumps(q))
    with pytest.raises(style.StyleError, match="lagged policy of the row BL5-cur"):
        mod("table3_v3").build(Inputs())
    f.write_text(old)
    f = out / "figs/table3_v2.json"            # own capacity differing between two rows (review of W-G2)
    old = f.read_text()
    q = json.loads(old)
    cell = q["data"]["rows"]["BL1"]["cells"]["usd"]["total"]["by_cell"]
    w = sorted(cell)[0]
    cell[w] += 5.0
    f.write_text(json.dumps(q))
    with pytest.raises(style.StyleError, match="own capacity"):
        mod("table3_v3").build(Inputs())
    f.write_text(old)
    f = out / "sublet_v2/main/summary.json"    # RC16(4): r0 of another confirmation than Table III v2's saving
    old = f.read_text()
    q = json.loads(old)
    blk = q["table"]["Sublet"]["L-tr"]
    blk[sorted(blk)[0]]["0"] += 0.01
    f.write_text(json.dumps(q))
    with pytest.raises(style.StyleError, match="another confirmation"):
        mod("table3_v3").build(Inputs())
    f.write_text(old)
    f = out / "s1v2/analysis.json"
    q = jl(f)
    q["meta"]["confirmation_inputs"] = {k: "0" * 64 for k in q["meta"]["confirmation_inputs"]}
    f.write_text(json.dumps(q))
    with pytest.raises(style.StyleError, match="other confirmation summaries"):
        mod("table5_alglb").build(Inputs())


@pytest.mark.parametrize("name", sorted(TABLES))
def test_reduced_input_is_not_written_into_paper(name, tmp_path, monkeypatch):
    m = mod(name)
    d = jl(FIX / f"{name}.json")["data"]
    assert d["meta"]["reduced"] is True
    with pytest.raises(SystemExit, match="reduced"):
        m.write_float(d, m.FLOATS_DIR)
    assert not (m.FLOATS_DIR / f"{name}.tex").is_file() or "REDUCED" not in (m.FLOATS_DIR / f"{name}.tex").read_text()
    # nor into code/sim/out/figs/ (review of W-G2: a reduced extract there ends the rebuild entry's pending state);
    # main() stops before writing the float
    monkeypatch.setenv("SUBLET_FIGS_IN_ROOT", str(IN_ROOT))
    monkeypatch.delenv(style.ENV_OUT_DIR, raising=False)
    before = (style.DEFAULT_OUT_DIR / f"{name}.json").is_file()
    with pytest.raises(SystemExit, match="reduced"):
        m.main(["--out", str(tmp_path / "f")])
    assert (style.DEFAULT_OUT_DIR / f"{name}.json").is_file() == before and not (tmp_path / "f").exists()


# ---------------------------------------------------------------------------------------------------------------
# Compilation and heights
def _fh():
    sys.path.insert(0, str(LAYOUT / "pageplan"))
    try:
        return importlib.import_module("floats_heights")
    finally:
        sys.path.remove(str(LAYOUT / "pageplan"))


def real_scale_tree(tmp_path: Path) -> Path:
    """The repository's versioned Table III v2 extract and part second, the S1 v2 smoke analysis's shape with the
    seed spread of this repository's confirmation recomputed (ms7_sens_analysis.seed_spread), and stand-in e7c and
    e7r analyses on the 16 weeks; the stand-ins' numbers exist only in the test."""
    from sublet.experiments import ms7_sens_analysis as M
    root = tmp_path / "real"
    out = root / "code/sim/out"
    src = REPO / "code/sim/out"
    for rel in ("figs/table3_v2.json", "sublet_v2/second/summary.json", "sublet_v2/main/summary.json",
                "sublet_v2/seeds/summary.json"):
        (out / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(src / rel, out / rel)
    shutil.copytree(src / "sublet_v2/second/lb", out / "sublet_v2/second/lb")
    t2 = jl(out / "figs/table3_v2.json")["data"]
    weeks = t2["caption_source"]["weeks"]
    main = jl(out / "sublet_v2/main/summary.json")
    T, W0 = main["table"], main["W0"]["0"]
    lag = {"Sublet-lag": "Sublet", "BL1-lag": "BL1", "BL1-BO-lag": "BL1-BO", "BL2-lag": "BL2", "BL3-0-lag": "BL3-0",
           "BL4-lag": "BL4", "BL5-tau60-lag": "BL5-tau60", "BL5N-lag": "BL5N", "BL1N-lag": "BL1N",
           "BL1-GP-lag": "BL1-GP", "BL5": "BL5-cur"}
    e7c = {"meta": {"weeks": weeks}, "lag_minus_revealed": {k: {"revealed": v} for k, v in lag.items()},
           "h1_set": ["BL1-lag", "BL1-BO-lag", "BL2-lag", "BL3-0-lag", "BL4-lag", "BL5"],
           "per_policy": {k: {"r0": {"weeks": {w: T["BL5" if k == "BL5" else v]["L-tr"][w]["0"] + 0.09 for w in weeks}}}
                          for k, v in lag.items()}}
    bl0a = t2["rows"]["BL0a"]["cells"]["usd"]["overflow"]["by_cell"]
    tags, runs = {}, []
    for tag, srcs, dr in (("MPC-T", "BL4", -0.2), ("A9-P", "Sublet", 0.17), ("BL1-c2", "BL1", 0.0),
                          ("BL2-c2", "BL2", 0.0), ("BL3-0-c2", "BL3-0", 0.0), ("BL4-c2", "BL4", 0.0),
                          ("BL5-cur-c2", "BL5-cur", 0.0)):
        pw = {w: {"r0_tr": T[srcs]["L-tr"][w]["0"] + dr, "W0": W0[srcs][w] - 0.3, "RC": {"L-tr": 0.004}}
              for w in weeks}
        tags[tag] = {"per_week": pw}
        runs += [{"kind": "week", "tag": tag, "mode": "L-tr", "cell": w, "seed": 0, "status": "ok",
                  "ALG": pw[w]["r0_tr"] * bl0a[w], "bl0a_usd": bl0a[w]} for w in weeks]
    e7r = {"weeks": weeks, "tags": tags, "as_built_vs_c2": [{"as_built": b, "c2": f"{b}-c2"} for b in
                                                            ("BL1", "BL2", "BL3-0", "BL4", "BL5-cur")]}
    conf = M.seed_spread(main, jl(out / "sublet_v2/seeds/summary.json"))
    import hashlib
    s1 = {"meta": {"confirmation_inputs": {
        f"out/sublet_v2/{p}/summary.json": hashlib.sha256((out / f"sublet_v2/{p}/summary.json").read_bytes())
        .hexdigest() for p in ("main", "seeds")}}, "seed_spread": conf}
    for rel, obj in (("e7c/analysis.json", e7c), ("e7r/analysis.json", e7r), ("e7r/eval/summary.json",
                                                                              {"runs": runs}),
                     ("s1v2/analysis.json", s1)):
        (out / rel).parent.mkdir(parents=True, exist_ok=True)
        (out / rel).write_text(json.dumps(obj))
    return root


def _compile(tmp_path: Path, floats_dir: Path, name: str) -> str:
    fh = _fh()
    names = []
    for m in fh.ms7_macros():
        n = m.name if m.parent.name != "macros" else f"macros_{m.name}"
        shutil.copy(m, tmp_path / n)
        names.append(n)
    stub = PAPER / "generated" / "labels_stub_ms7.tex"
    shutil.copy(stub, tmp_path / stub.name)
    doc = (fh.PREAMBLE_MS7 + "".join(f"\n\\input{{{n}}}" for n in names) + f"\n\\input{{{stub.name}}}\n"
           f"\\begin{{document}}\n\\input{{{name}.tex}}\nText.\n\\end{{document}}\n")
    (tmp_path / "doc.tex").write_text(doc)
    env = dict(os.environ, TEXINPUTS=f"{LAYOUT}:{floats_dir}:{tmp_path}:")
    r = subprocess.run([str(PDFLATEX), "-interaction=nonstopmode", "-halt-on-error", "doc.tex"], cwd=tmp_path,
                       capture_output=True, text=True, env=env, timeout=300)
    log = (tmp_path / "doc.log").read_text(errors="replace")
    assert r.returncode == 0, log[-2000:]
    return log


@pytest.mark.skipif(not PDFLATEX.is_file(), reason=f"{PDFLATEX} is not installed")
def test_real_scale_floats_compile_and_fit(tmp_path, monkeypatch):
    root = real_scale_tree(tmp_path)
    monkeypatch.setenv("SUBLET_FIGS_IN_ROOT", str(root))
    monkeypatch.setenv(style.ENV_OUT_DIR, str(tmp_path / "out"))
    floats = tmp_path / "floats"
    shutil.copytree(PAPER / "floats", floats)
    for name in TABLES:
        for f in floats.glob(f"{name}.tex"):
            f.unlink()
        mod(name).main(["--out", str(floats)])
        d = tmp_path / f"c_{name}"
        d.mkdir()
        log = _compile(d, floats, name)
        assert "Overfull" not in log and "LaTeX Error" not in log, [l for l in log.splitlines() if "Overfull" in l]
        if name == "table3_v3":                    # a note of three lines: w_spec §2.8's two (review of W-G2: it had
            import fitz                            # three) and C9's one more (RetroRenting-style's lagged cell)
            with fitz.open(d / "doc.pdf") as doc:
                lines = ["".join(sp["text"] for sp in ln["spans"]) for b in doc[0].get_text("dict")["blocks"]
                         for ln in b.get("lines", [])]
            first = next(i for i, t in enumerate(lines) if t.startswith("Medians of per-week values"))
            assert lines[first + 2].rstrip().endswith("not run."), lines[first:first + 4]
            assert "RetroRenting-style, lagged" in " ".join(lines[first:first + 3]).replace("- ", "-")
    # 16-week value oracles (review of W-G2: the fixture has one week, where every median is trivial): Table IV's
    # confirmation rows print Table III v2's cells, Table V's medians its ALG/LB column
    t2 = jl(root / "code/sim/out/figs/table3_v2.json")["data"]["rows"]
    for name, m in (("table3_v3", mod("table3_v3")), ("table5_alglb", mod("table5_alglb"))):
        d = jl(tmp_path / "out" / f"{name}.json")["data"]
        for row in m.ROWS:
            tag, src = row[0], (row[2] if len(row) > 2 else "conf")
            if src != "conf":
                continue
            if name == "table3_v3":
                c = d["rows"][tag]["cells"]
                assert c["usd"]["text"] == t2[tag]["cells"]["usd"]["text"], tag
                assert [c[k]["text"] for k in ("saving_pct", "RC", "W0")] == \
                    [t2[tag]["cells"][k]["text"] for k in ("saving_pct", "RC", "W0")], tag
                s = t2[tag]["cells"]["saving_pct"]           # r0 is the saving's 1 - s/100 at 16 weeks
                assert abs(100 * (1 - c["r0"]["value"]) - s["value"]) < 1e-9, tag
            else:
                assert d["rows"][tag]["texts"]["gap"] == t2[tag]["cells"]["gap"]["text"], tag
    fh = _fh()
    budgets = {k: fh.BUDGETS_MS7[k] for k in TABLES}
    (tmp_path / "h").mkdir()
    rep = fh.measure(budgets, workdir=tmp_path / "h", floats_dir=floats, labels=fh.LABELS_MS7, macros=fh.ms7_macros(),
                     preamble=fh.PREAMBLE_MS7)
    assert rep["floats"]["table3_v3"]["measured_pages"] <= TABLE4_MAX_PAGES + 1e-9
    assert rep["floats"]["table5_alglb"]["measured_pages"] <= 0.1202 + 1e-9      # the pages study's mock (budget 0.120)


# ---------------------------------------------------------------------------------------------------------------
@pytest.fixture
def registry_without_test_figures():
    leaked = {k: v for k, v in style.FIGURES.items() if k.startswith("test_")}
    for k in leaked:
        del style.FIGURES[k]
    yield
    style.FIGURES.update(leaked)


def test_rebuild_float_entries_and_pending(registry_without_test_figures, tmp_path):
    ents = rb.entries()
    names = [e.name for e in ents]
    by = {e.name: e for e in ents}
    assert names.index("table3_v3") == names.index("table3_v2") + 1
    assert names.index("table5_alglb") == names.index("table3_v3") + 1
    for name, module in TABLES.items():
        e = by[name]
        assert (e.kind, e.module, e.extract) == ("float", module, f"code/sim/out/figs/{name}.json")
        assert e.outputs == (f"paper/floats/{name}.tex", f"code/sim/out/figs/{name}.json")
        assert rb.MS7_PENDING[name] == mod(name).RUN_INPUTS
        assert rb.argv_of(rb.Run(tmp_path, tmp_path, True, None, True), e)[2:] == \
            [module, "--from-extract", "--out", str(tmp_path / "paper/floats")]
        assert rb.is_pending(tmp_path, e)
    cov = rb.coverage(REPO, ents)
    if not all((REPO / p).is_file() for p in rb.MS7_PENDING["table3_v3"]):
        assert "table3_v3" in cov["pending"] and "paper/floats/table3_v3.tex" not in cov["missing"]
