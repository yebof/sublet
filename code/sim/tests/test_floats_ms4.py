"""Tests of Table III, paper/floats/table3_e7.tex, and of its writer figs/table3_e7.py (design/sim_spec_ms4.md §9 and §10,
row test_floats_ms4.py), and of the MS4 note in Table II (§13 item 1).

- The float written from the fixture table3.json (tests/fixtures_figs_ms4/inputs/, reduced-mode driver outputs, not
  results) holds every row of §9 in order, named by its style.POLICIES label, and every column, each cell the median
  of table3.json formatted as §9 states ("--" where it is null, with its note in the extract); its caption gives the
  scope, Sublet's MS4 allowance and the certificate counts from table3.json (a null count or a part of E7 left out of
  the count raises); it cites nothing. The writer refuses a
  label that differs from the registry's and never writes a reduced table into paper/floats/; --from-extract rewrites
  the same float.
- The float compiles in a temporary folder with paper/layout_check/IEEEtran.cls without an overfull box, and
  floats_heights.py --ms4 measures it next to its budget (skipped without pdflatex).
- Table II carries the note on Sublet's MS4 allowance on rows (1)-(2) (B0 = 10% of BL0a, gamma 1, kappa none,
  Theorem W(a)(b)'s envelope, G3(b) not applying, the class I1 + N + BL0a).
Every file is written under pytest's tmp_path; nothing is written into paper/ or code/sim/out/.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

from figs import style
from figs import table3_e7 as t3w

REPO = style.REPO
FIX_ROOT = Path(__file__).resolve().parent / "fixtures_figs_ms4" / "inputs"
FIX_T3 = FIX_ROOT / "code/sim/out/e7/table3.json"
LAYOUT = REPO / "paper" / "layout_check"
FLOATS = REPO / "paper" / "floats"
PDFLATEX = Path.home() / ".local" / "bin" / "pdflatex"
# §9's rows in order, by registry key
ROW_KEYS = ("sublet", "bl5", "bl1", "bl2", "bl4", "a7", "a7_guard", "a6", "bl0b", "bl0a")
COLUMNS = ("usd", "saving_pct", "gap", "fallback_share_after_reclaims", "W0", "abort_share")


def _body(tex: str) -> str:
    return "\n".join(l for l in tex.splitlines() if not l.lstrip().startswith("%"))


def _rows(tex: str, start: str = r"\midrule", end: str = r"\bottomrule") -> list[list[str]]:
    """The cells of the rows between `start` and `end` (the body; the header with toprule, midrule)."""
    body = _body(tex)
    part = body[body.index(start) + len(start):body.index(end)]
    return [[c.strip() for c in r.split("&")] for r in part.split(r"\\") if r.strip()]


@pytest.fixture
def written(tmp_path, monkeypatch):
    """The float and extract written by the writer from the fixture table3.json, in tmp_path."""
    monkeypatch.setenv("SUBLET_FIGS_IN_ROOT", str(FIX_ROOT))
    monkeypatch.setenv(style.ENV_OUT_DIR, str(tmp_path / "out"))
    rep = t3w.main(["--out", str(tmp_path / "floats")])
    tex = (tmp_path / "floats" / "table3_e7.tex").read_text(encoding="utf-8")
    ext = json.loads((tmp_path / "out" / "table3_e7.json").read_text(encoding="utf-8"))
    return tmp_path, tex, ext, rep


def _fmt(v, d):
    if v is None:
        return "--"
    s = f"{v:.{d}f}"
    if float(s) == 0.0:
        s = s.lstrip("-")
    return "$-$" + s[1:] if s.startswith("-") else s


# ---------------------------------------------------------------------------------------------------------------
def test_rows_and_columns_with_registry_labels(written):
    _, tex, ext, _ = written
    t3 = json.loads(FIX_T3.read_text())
    assert r"\begin{table}" in tex and r"\toprule" in tex and r"\bottomrule" in tex and r"\footnotesize" in tex
    assert [t3["rows"][t]["style_key"] for t in t3["order"]] == list(ROW_KEYS)
    head, body = _rows(tex, r"\toprule", r"\midrule"), _rows(tex)
    assert len(head) == 2 and len(body) == len(ROW_KEYS)
    assert all(len(r) == 1 + len(COLUMNS) for r in head + body)
    assert [r[0] for r in body] == [style.POLICIES[k].label for k in ROW_KEYS]
    header = " ".join(" ".join(r) for r in head)
    for word in ("Policy", "USD/week (k)", "overflow (total)", "Saving", r"(\%)", "ALG/", "LB", "Fallback",
                 "after recl.", "$W_0$", "Abort", "share"):
        assert word in header, word
    for tag, r in zip(t3["order"], body):
        row = t3["rows"][tag]
        ovf, tot = row["usd"]["overflow"]["median"], row["usd"]["total"]["median"]
        assert r[1] == ("--" if ovf is None else _fmt(ovf / 1e3, 1) + ("" if tot is None else f" ({_fmt(tot / 1e3, 1)})"))
        sv = row["saving_pct"]["median"]
        assert r[2] == _fmt(sv, 1 if sv is None or abs(sv) < 100 else 0)
        for cell, col in zip(r[3:], COLUMNS[2:]):
            assert cell == _fmt(row[col]["median"], 2), (tag, col, cell)
            if row[col]["median"] is None:
                assert ext["data"]["notes"][f"{tag}.{col}"] == row[col]["note"]
    # §9's dashes: no gap for BL0b, no fallback share for BL0a and BL0b, no W0 for BL0b, no abort share unguarded
    by = dict(zip(t3["order"], body))
    assert by["BL0b"][3] == "--" and by["BL0b"][4] == by["BL0a"][4] == "--" and by["BL0b"][5] == "--"
    assert all(by[t][6] == "--" for t in t3["order"] if t not in ("Sublet", "A7G"))
    assert by["BL0a"][5] == _fmt(1.0, 2)


def test_caption_scope_allowance_and_certificates(written):
    _, tex, ext, _ = written
    cap = json.loads(FIX_T3.read_text())["caption"]
    m = re.search(r"\\caption\{(.*)\}\s*\n\\label\{tab:e7\}", _body(tex), re.S)
    assert m, "no caption"
    text = m.group(1)
    c = cap["certificates"]
    assert f"{c['held']} of {c['n']} certificates held" in text
    for case in ("W(a)", "W(b)", "W(c)"):
        assert f"{case} {c['by_case'][case]['runs']}" in text
    assert r"$B_0$ = 10\% of all-fallback" in text and r"$\gamma=1$" in text
    assert cap["B0_rule"] == "0.1*BL0a" and cap["gamma"] == 1.0
    s = cap["scope"]
    assert f"{s['lender']} lender" in text and "full menu" in text and r"$\mu/\tilde\beta=1$" in text
    assert f"{len(s['alignments'])} alignment" in text and f"{len(s['policy_seeds'])} seed" in text
    assert "slow grid, e7r menu" in text
    assert ext["data"]["caption"] == text and ext["sources"] == ["code/sim/out/e7/table3.json"]


def test_cites_nothing_and_marks_a_reduced_input(written):
    _, tex, _, _ = written
    assert r"\cite" not in tex
    assert "REDUCED INPUT" in tex          # the fixture is a smoke run (meta.reduced)


def test_writer_refuses_wrong_labels_and_reduced_tables_in_paper(tmp_path, monkeypatch):
    t3 = json.loads(FIX_T3.read_text())
    t3["rows"]["BL5"]["label"] = "RetroRenting"
    root = tmp_path / "root"
    p = root / "code/sim/out/e7/table3.json"
    p.parent.mkdir(parents=True)
    p.write_text(json.dumps(t3))
    monkeypatch.setenv("SUBLET_FIGS_IN_ROOT", str(root))
    monkeypatch.setenv(style.ENV_OUT_DIR, str(tmp_path / "out"))
    with pytest.raises(KeyError, match="style.POLICIES label"):
        t3w.main(["--out", str(tmp_path / "floats")])
    monkeypatch.setattr(t3w, "FLOATS_DIR", tmp_path / "paper_floats")
    monkeypatch.setenv("SUBLET_FIGS_IN_ROOT", str(FIX_ROOT))
    with pytest.raises(SystemExit, match="reduced"):
        t3w.main([])
    assert not (tmp_path / "paper_floats").exists()


def test_caption_refuses_null_counts_and_parts_left_out():
    """The certificate count is printed only from table3.json's numbers over every part of E7: a null n, held or case
    count raises (never "0 of 0"), and so does a part not counted (caption.certificates.parts_counted) or a part
    summary not used (meta.sources.<part>.used)."""
    t3 = json.loads(FIX_T3.read_text())
    cap, sources = t3["caption"], t3["meta"]["sources"]
    text = t3w.caption_text(cap, sources)
    c = cap["certificates"]
    assert f"{c['held']} of {c['n']} certificates held" in text
    for path in (("n",), ("held",), ("by_case", "W(b)", "runs")):
        bad = json.loads(json.dumps(cap))
        d = bad["certificates"]
        for k in path[:-1]:
            d = d[k]
        d[path[-1]] = None
        with pytest.raises(KeyError, match="null"):
            t3w.caption_text(bad, sources)
    bad = json.loads(json.dumps(cap))
    bad["certificates"]["by_case"] = {}
    with pytest.raises(KeyError, match="not found"):
        t3w.caption_text(bad, sources)
    bad = json.loads(json.dumps(cap))
    bad["certificates"]["parts_counted"]["stress"] = False
    with pytest.raises(KeyError, match=r"\['stress'\]"):
        t3w.caption_text(bad, sources)
    src = json.loads(json.dumps(sources))
    src["gap"]["used"] = False
    with pytest.raises(KeyError, match=r"\['gap'\]"):
        t3w.caption_text(cap, src)


def test_from_extract_rewrites_the_same_float(written, monkeypatch):
    tmp, tex, _, _ = written
    t3w.main(["--from-extract", str(tmp / "out" / "table3_e7.json"), "--out", str(tmp / "again")])
    assert (tmp / "again" / "table3_e7.tex").read_text(encoding="utf-8") == tex


def test_formats():
    assert t3w.tex_value(None, 2) == "--" and t3w.tex_value(-5.376, 1) == "$-$5.4" and t3w.tex_value(-0.04, 1) == "0.0"
    assert t3w.share_text("0.1*BL0a") == r"10\%"
    with pytest.raises(KeyError):
        t3w.share_text("auto")


# ---------------------------------------------------------------------------------------------------------------
@pytest.mark.skipif(not PDFLATEX.is_file(), reason=f"{PDFLATEX} is not installed")
def test_float_compiles_and_is_measured(written):
    tmp, _, _, _ = written
    doc = ("\\documentclass[journal]{IEEEtran}\\usepackage{booktabs}\\usepackage{array}\n\\begin{document}\n"
           "\\input{table3_e7.tex}\nText.\n\\end{document}\n")
    (tmp / "doc.tex").write_text(doc)
    env = dict(os.environ, TEXINPUTS=f"{LAYOUT}:{tmp / 'floats'}:")
    r = subprocess.run([str(PDFLATEX), "-interaction=nonstopmode", "-halt-on-error", "doc.tex"], cwd=tmp,
                       capture_output=True, text=True, env=env, timeout=300)
    log = (tmp / "doc.log").read_text(errors="replace")
    assert r.returncode == 0 and (tmp / "doc.pdf").is_file(), log[-2000:]
    assert "Overfull" not in log, [l for l in log.splitlines() if "Overfull" in l]
    assert "LaTeX Error" not in log
    sys.path.insert(0, str(LAYOUT / "pageplan"))
    try:
        import floats_heights as fh
    finally:
        sys.path.remove(str(LAYOUT / "pageplan"))
    (tmp / "heights").mkdir()
    rep = fh.measure(fh.BUDGETS_MS4, workdir=tmp / "heights", floats_dir=tmp / "floats")
    v = rep["floats"]["table3_e7"]
    assert 0 < v["measured_pages"] < 1 and v["budget_pages"] == 0.125
    assert v["within_budget"] == (v["measured_pages"] <= 0.125 + 1e-9)


# ---------------------------------------------------------------------------------------------------------------
def test_table2_note_on_the_ms4_allowance():
    """§13 item 1: rows (1)-(2) of Table II carry the note on Sublet's MS4 allowance (Sublet, Sublet siloed and PD
    heuristic + guard, not Greedy + guard, which has no MS4 run)."""
    t = _body((FLOATS / "table2_policies.tex").read_text(encoding="utf-8"))
    rows = [r.strip() for r in t[t.index(r"\midrule"):t.index(r"\bottomrule")].split(r"\\") if r.strip()]
    mark = r"$^\ddagger$"
    assert rows[0].split("&")[0].count(mark) == 2
    assert rows[1].split("&")[0].count(mark) == 1 and "Greedy + guard" + mark not in rows[1]
    assert all(mark not in r for r in rows[2:])
    note = t[t.index(r"\end{tabular}"):]
    assert note.count(mark) == 1
    for s in ("E3, E5 and E7", r"$\gamma=1$", r"$\kappa$ none", r"$B_0$ = 10\% of the run's all-fallback bill",
              r"I1$+N+$BL0a", r"$\mathrm{ALG}(T)\le C_S(T)+B_0$", "G3(b) does not apply (G3(d), G6)",
              "Algorithm~1's"):
        assert s in " ".join(note.split()), s
