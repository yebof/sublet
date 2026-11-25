"""Tests of the main-text floats of the MS7 manuscript (design/ms7/w_spec.md §2.4-§2.8 and §3, row
test_floats_ms7.py; change C58). Skeleton of unit W-T: a float that its unit has not written yet is skipped, so the
file runs from the start of the writing phase and tests each float once it exists.

- The tools agree on the floats: texscan.MAIN_FLOATS (paper/tools/), BUDGETS_MS7 of
  paper/layout_check/pageplan/floats_heights.py and the float budgets of paper/tools/measure_sections.py, each the
  page budget of w_spec §1.1.
- Every MS7 float names results by \\ref to a label of the new stub paper/generated/labels_stub_ms7.tex (the
  renumbered paper/results.json) or to a label that the main text or the supplement defines, and prints neither an
  all-caps status word nor a design ID (paper/tools/check_style.py's float mode).
- The hand-set floats (the notation table, Table II on the price of revocation, the policy glossary, Algorithms 1 v3
  and 2) compile with paper/layout_check/IEEEtran.cls, the paper's macros and the stub, without an overfull box, a
  LaTeX error or an undefined reference other than a supplement label; floats_heights.py --ms7's measure() measures
  the floats that exist next to BUDGETS_MS7 (skipped without pdflatex).
- Algorithm 1 v3 (w_spec §2.7): the core-only guard, its lines numbered 1..n (n at most 12), the ladder A_E(t), P1,
  P0, K0 in that order, the test T0g as one inequality against gamma C_S(t) + B(t), the abort to mode S, no wind-down
  in the lines, and the note's pointers to Theorem 11 and the supplement's definition of the guard.
- Algorithm 2 (w_spec §2.7): its lines numbered 1..n (n at most 12), the insurance test with "or CR_ins < LB_react",
  the notice rule max{H*_mu, H*_beta}, the commitment bound A and the marking budget ell.
- The glossary (w_spec §2.8): label tab:policies, and every policy that a main-text figure draws (Fig. 1 v3, Fig. 3 =
  fig4v3, or fig4v2 until fig4v3 is registered, Fig. 6 = fig7; Figs. 4 and 5 of w_spec, fig5 and fig6, are in the
  supplement), every policy that Section VII-E names (RR-renew, Marking) and every row of Table IV is a row, by its
  registry label (ALG* set as ALG$^\\ast$).
- Tables IV and V (w_spec §2.8, unit W-G2): the versioned float equals its script's --from-extract output (skipped
  until the script and its extract exist).
Every file is written under pytest's tmp_path; nothing is written into paper/ or code/sim/out/.
"""
from __future__ import annotations

import importlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from figs import style

REPO = style.REPO
PAPER = REPO / "paper"
FLOATS = PAPER / "floats"
LAYOUT = PAPER / "layout_check"
SUPP = PAPER / "supplement"
PDFLATEX = Path.home() / ".local" / "bin" / "pdflatex"
LABELS_MS7 = PAPER / "generated" / "labels_stub_ms7.tex"
HAND_SET = ("table_notation", "table1_price_of_revocation", "table2_glossary", "alg1_guard_v3", "alg2_crr")
SCRIPTS = {"table3_v3": "figs.table3_v3", "table5_alglb": "figs.table5_alglb"}       # unit W-G2
EXTRACTS = {"table3_v3": REPO / "code/sim/out/figs/table3_v3.json",
            "table5_alglb": REPO / "code/sim/out/figs/table5_alglb.json"}
# The policy figures of the MS7 main text: Figs. 1 (fig1v3), 3 (fig4v3) and 6 (fig7). Figs. 4 and 5 of w_spec §3 (fig5,
# fig6) are Supplement Figs. fig:loss and fig:public (paper/supplement/sections/s_f1.tex), so their policies (A2, A3,
# Lagged RetroRenting + one-way guard) left the glossary with Table IV v2 (unit T, after the X4/X5 runs); RR-renew
# and Marking stay as rows because Section VII-E names them.
MS7_FIGURES = ("fig1v3", "fig4v3", "fig7")
ALG_STAR = "ALG$^\\ast$"                                      # the registry's "ALG*" as the floats set it (C52)
STATUS_WORD = re.compile(r"\b(?:PROVEN|CONJECTURE|VERIFIED NUMERICALLY)\b")


def _import(folder: Path, name: str):
    sys.path.insert(0, str(folder))
    try:
        return importlib.import_module(name)
    finally:
        sys.path.remove(str(folder))


texscan = _import(PAPER / "tools", "texscan")
check_style = _import(PAPER / "tools", "check_style")
measure_sections = _import(PAPER / "tools", "measure_sections")
fh = _import(LAYOUT / "pageplan", "floats_heights")


def _need(name: str) -> str:
    p = FLOATS / f"{name}.tex"
    if not p.is_file():
        pytest.skip(f"paper/floats/{name}.tex is not written yet (w_spec §4)")
    return p.read_text(encoding="utf-8")


def _body(tex: str) -> str:
    return "\n".join(l for l in tex.splitlines() if not l.lstrip().startswith("%"))


def _ws(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def _has_words(tex: str, phrase: str) -> bool:
    """`phrase` occurs in `tex` up to whitespace and ties (~)."""
    return re.search(r"(?:\s|~)+".join(re.escape(w) for w in phrase.split()), tex) is not None


def _macros() -> dict:
    """The zero-argument macros of paper/macros.tex: name -> body."""
    text = texscan.strip_comments((PAPER / "macros.tex").read_text(encoding="utf-8"))
    out = {}
    for m in re.finditer(r"\\newcommand\{\\([A-Za-z]+)\}\{", text):
        e = texscan.match_group(text, m.end() - 1)
        out[m.group(1)] = text[m.end():e - 1]
    return out


def _flat(tex: str) -> str:
    """Math and text without layout: the paper's zero-argument macros expanded, \\mathrm and \\textup dropped, braces,
    dollars and spaces removed, \\{ \\} as parentheses, \\star and \\ast as *."""
    macros = _macros()
    for _ in range(3):
        tex = re.sub(r"\\([A-Za-z]+)(?![A-Za-z])", lambda m: macros.get(m.group(1), m.group(0)), tex)
    tex = tex.replace("\\{", "(").replace("\\}", ")")
    tex = re.sub(r"\\(?:mathrm|textup|text|mbox)\b", "", tex)
    tex = tex.replace("\\star", "*").replace("\\ast", "*")
    return re.sub(r"[{}$\s~]", "", tex)


def _alg_lines(tex: str) -> list:
    """[(number, text)] of an algorithm float's \\algl{n}{indent}{text} lines."""
    out = []
    for m in re.finditer(r"\\algl\{(\d+)\}\{[\d.]+\}\{", tex):
        e = texscan.match_group(tex, m.end() - 1)
        out.append((int(m.group(1)), tex[m.end():e - 1]))
    return out


def _defined_labels() -> set:
    """The labels a float may \\ref: the stub's results and every \\label of the main text, its floats and the
    supplement."""
    stub = texscan.strip_comments(LABELS_MS7.read_text(encoding="utf-8"))
    out = set(re.findall(r"\\newlabel\{([^}]*)\}", stub))
    for f in list((PAPER / "sections").glob("*.tex")) + list(FLOATS.glob("*.tex")) + list(SUPP.rglob("*.tex")):
        out |= set(re.findall(r"\\label\{([^}]*)\}", texscan.strip_comments(f.read_text(encoding="utf-8"))))
    return out


def _supplement_labels() -> set:
    out = set()
    for f in SUPP.rglob("*.tex"):
        out |= set(re.findall(r"\\label\{([^}]*)\}", texscan.strip_comments(f.read_text(encoding="utf-8"))))
    return out


# ---------------------------------------------------------------------------------------------------------------
# The tools agree
def test_tools_name_the_same_floats_and_budgets():
    assert tuple(fh.BUDGETS_MS7) == texscan.MAIN_FLOATS
    assert fh.BUDGETS_MS7 == {"table_notation": 0.155, "table1_price_of_revocation": 0.130, "table2_glossary": 0.258,
                              "table3_v3": 0.258, "table5_alglb": 0.120, "alg1_guard_v3": 0.155, "alg2_crr": 0.180}
    by_file = {f: r[2] for r in measure_sections.FLOAT_BUDGETS for f in r[4]}
    assert by_file == fh.BUDGETS_MS7
    assert fh.OUT_MS7 == REPO / "code/sim/out/figs/floats_heights_ms7.json" and fh.LABELS_MS7 == LABELS_MS7
    assert fh.ms7_macros()[0] == PAPER / "macros.tex"


def test_the_ms7_stub_numbers_the_main_results():
    """The stub defines each main-text result of paper/results.json with its number (W-D7)."""
    entries = [e for e in json.loads((PAPER / "results.json").read_text())["results"]
               if not str(e["section"]).startswith("S-")]
    stub = dict(re.findall(r"\\newlabel\{([^}]*)\}\{\{([^}]*)\}",
                           texscan.strip_comments(LABELS_MS7.read_text(encoding="utf-8"))))
    assert stub == {e["slug"]: str(e["number"]) for e in entries}


@pytest.mark.parametrize("name", texscan.MAIN_FLOATS)
def test_float_refs_status_words_and_ids(name):
    tex = _body(_need(name))
    refs = set(re.findall(r"\\ref\{([^}]*)\}", tex))
    assert refs <= _defined_labels(), sorted(refs - _defined_labels())
    assert not STATUS_WORD.search(tex), STATUS_WORD.findall(tex)                   # C52: no all-caps status word
    errors, *_ = check_style.check_file(FLOATS / f"{name}.tex")
    assert errors == [], errors


# ---------------------------------------------------------------------------------------------------------------
# Compilation and heights
def _compile(tmp_path: Path, name: str) -> str:
    macros = fh.ms7_macros()
    names = []
    for m in macros:
        n = m.name if m.parent.name != "macros" else f"macros_{m.name}"
        shutil.copy(m, tmp_path / n)
        names.append(n)
    shutil.copy(LABELS_MS7, tmp_path / LABELS_MS7.name)
    doc = (fh.PREAMBLE_MS7 + "".join(f"\n\\input{{{n}}}" for n in names) + f"\n\\input{{{LABELS_MS7.name}}}\n"
           f"\\begin{{document}}\n\\input{{{name}.tex}}\nText.\n\\end{{document}}\n")
    (tmp_path / "doc.tex").write_text(doc)
    env = dict(os.environ, TEXINPUTS=f"{LAYOUT}:{FLOATS}:{tmp_path}:")
    r = subprocess.run([str(PDFLATEX), "-interaction=nonstopmode", "-halt-on-error", "doc.tex"], cwd=tmp_path,
                       capture_output=True, text=True, env=env, timeout=300)
    log = (tmp_path / "doc.log").read_text(errors="replace")
    assert r.returncode == 0 and (tmp_path / "doc.pdf").is_file(), log[-2000:]
    return log


@pytest.mark.skipif(not PDFLATEX.is_file(), reason=f"{PDFLATEX} is not installed")
@pytest.mark.parametrize("name", HAND_SET)
def test_hand_set_floats_compile(tmp_path, name):
    _need(name)
    log = _compile(tmp_path, name)
    assert "Overfull" not in log, [l for l in log.splitlines() if "Overfull" in l]
    assert "LaTeX Error" not in log and "Float too large" not in log
    undefined = set(re.findall(r"Reference `([^']+)' on page \d+ undefined", log))
    assert undefined <= _supplement_labels(), sorted(undefined - _supplement_labels())


@pytest.mark.skipif(not PDFLATEX.is_file(), reason=f"{PDFLATEX} is not installed")
def test_ms7_floats_are_measured(tmp_path):
    """floats_heights.measure with BUDGETS_MS7 (--ms7 --allow-missing): each float that exists next to its budget,
    the others listed as missing; the stub and the macros recorded with their sha256 (informative heights)."""
    present = [n for n in fh.BUDGETS_MS7 if (FLOATS / f"{n}.tex").is_file()]
    if not present:
        pytest.skip("no MS7 float is written yet")
    rep = fh.measure(fh.BUDGETS_MS7, workdir=tmp_path, labels=fh.LABELS_MS7, macros=fh.ms7_macros(),
                     preamble=fh.PREAMBLE_MS7, missing_ok=True)
    assert list(rep["floats"]) == present
    assert rep.get("missing", []) == [n for n in fh.BUDGETS_MS7 if n not in present]
    for name, v in rep["floats"].items():
        assert 0 < v["measured_pages"] < 1 and v["budget_pages"] == fh.BUDGETS_MS7[name], name
        assert v["within_budget"] == (v["measured_pages"] <= v["budget_pages"] + 1e-9)
        assert set(v["undefined_refs"]) <= _supplement_labels(), (name, v["undefined_refs"])
    assert rep["labels"]["file"] == "paper/generated/labels_stub_ms7.tex"
    assert [m["file"] for m in rep["macros"]][0] == "paper/macros.tex" and rep["preamble"] == fh.PREAMBLE_MS7


# ---------------------------------------------------------------------------------------------------------------
# Algorithms 1 v3 and 2
def test_algorithm1_v3_core_guard():
    tex = _body(_need("alg1_guard_v3"))
    assert r"\begin{figure}[t]" in tex and r"\textbf{Algorithm 1}" in tex
    lines = _alg_lines(tex)
    assert [n for n, _ in lines] == list(range(1, len(lines) + 1)) and len(lines) <= 12, [n for n, _ in lines]
    text = {n: _flat(t) for n, t in lines}
    ladder = [n for n, t in text.items() if re.search(r"A_E\(t\),P1,P0,K0", t)]
    assert len(ladder) == 1, text
    test = [n for n, t in text.items() if re.search(r"\\hata_Y\(t\)(?:\+R_Y\(t\))?\\le\\gammaC_S\(t\)\+B\(t\)", t)]
    assert len(test) == 1 and test[0] == ladder[0] + 1, text                       # the test T0g inside the ladder
    assert "T0g" in tex
    abort = [n for n, t in text.items() if "abort" in t]
    assert abort and abort[0] > test[0] and any("mode=S" in t for t in text.values()), text
    assert not any(re.search(r"wind-?down", t, re.I) for _, t in lines)          # the core only: no wind-down line
    note = tex[tex.rindex(r"\algl{"):]
    assert r"\ref{thm:additive}" in note and r"\ref{def:s-fm-guard}" in note


def test_algorithm2_critical_ratio_renting():
    tex = _body(_need("alg2_crr"))
    assert r"\begin{figure}[t]" in tex and r"\textbf{Algorithm 2}" in tex
    lines = _alg_lines(tex)
    assert [n for n, _ in lines] == list(range(1, len(lines) + 1)) and len(lines) <= 12, [n for n, _ in lines]
    flat = _flat(" ".join(t for _, t in lines))
    assert "orCR_ins<LB_react" in flat or "orCR_ins<LB_react" in flat.replace("\\textless", "<"), flat
    assert re.search(r"max\((?:H\^\*_\\mu,H\^\*_\\beta|H\^\*_\\beta,H\^\*_\\mu)\)", flat), flat
    assert re.search(r"(?:atmost|\\le)(?:A|age)(?:more)?slots?", flat), flat                            # the commitment bound
    assert "upsilon_" in _flat(tex) and "budget" in tex                                        # the marking budget (RC19(7))


# ---------------------------------------------------------------------------------------------------------------
# The glossary
def _label(key: str) -> str:
    return ALG_STAR if key == "a1" else style.POLICIES[key].label


def _has_label(tex: str, label: str) -> bool:
    """`label` occurs in the glossary verbatim, or (C58, for Fig. 3 v3(c)'s names) as 'Head, a / b / ...: rule' with
    `label` = 'Head, b': a row that gives the head once and the suffixes separated by '/' before its colon."""
    if _has_words(tex, label):
        return True
    if ", " not in label:
        return False
    head, tail = label.split(", ", 1)
    ws = r"(?:\s|~)+"
    words = lambda p: ws.join(re.escape(w) for w in p.split())
    item = r"[^/:&]*?"
    return re.search(words(head) + "," + ws + rf"(?:{item}/{ws})*" + words(tail) + rf"(?:{ws}/{item})*:", tex) is not None


def _table4_rows() -> list:
    if not (FLOATS / "table3_v3.tex").is_file():
        return []
    t = _body((FLOATS / "table3_v3.tex").read_text(encoding="utf-8"))
    body = t[t.index(r"\midrule"):t.index(r"\bottomrule")] if r"\midrule" in t and r"\bottomrule" in t else ""
    rows = [r.split("&")[0].strip() for r in body.split(r"\\") if "&" in r]
    return [re.sub(r"^\\midrule\s*", "", r) for r in rows if r]


def test_glossary_covers_every_policy_of_the_main_figures_and_tables():
    tex = _body(_need("table2_glossary"))
    assert r"\label{tab:policies}" in tex and r"\begin{table}[t]" in tex
    figures = [f if f in style.FIGURE_POLICIES else "fig4v2" if f == "fig4v3" else None for f in MS7_FIGURES]
    keys = {k for f in figures if f for k in style.FIGURE_POLICIES[f]} | {"a9", "bl5_lag", "rr_renew", "marking"}
    missing = sorted(_label(k) for k in keys if not _has_label(tex, _label(k)))
    assert not missing, missing
    rows = [r for r in _table4_rows() if not _has_words(tex, r)]
    assert not rows, rows


# ---------------------------------------------------------------------------------------------------------------
# Tables IV and V (unit W-G2)
@pytest.mark.parametrize("name", sorted(SCRIPTS))
def test_script_tables_rewrite_from_their_extracts(tmp_path, name):
    _need(name)
    try:
        mod = importlib.import_module(SCRIPTS[name])
    except ModuleNotFoundError:
        pytest.skip(f"{SCRIPTS[name]} is not written yet (unit W-G2)")
    if not EXTRACTS[name].is_file():
        pytest.skip(f"{EXTRACTS[name].relative_to(REPO)} is not written yet (unit W-G2)")
    mod.main(["--from-extract", str(EXTRACTS[name]), "--out", str(tmp_path)])
    assert (tmp_path / f"{name}.tex").read_bytes() == (FLOATS / f"{name}.tex").read_bytes()


@pytest.mark.skipif(not PDFLATEX.is_file(), reason=f"{PDFLATEX} is not installed")
def test_heights_cli_ms7_and_missing_floats(tmp_path):
    """floats_heights.py --ms7 on a floats folder that lacks some MS7 floats stops without writing; with
    --allow-missing it measures the others into --out only and lists the missing ones; --allow-missing needs --ms7."""
    d = tmp_path / "floats"
    d.mkdir()
    for n in ("table1_price_of_revocation",):                     # a float that exists since MS3 (unchanged)
        shutil.copy(FLOATS / f"{n}.tex", d / f"{n}.tex")
    script = LAYOUT / "pageplan" / "floats_heights.py"
    out = tmp_path / "h.json"
    r = subprocess.run([sys.executable, str(script), "--ms7", "--floats", str(d), "--out", str(out)],
                       capture_output=True, text=True, timeout=600)
    assert r.returncode == 1 and not out.exists() and "not written yet" in r.stderr
    r = subprocess.run([sys.executable, str(script), "--ms7", "--allow-missing", "--floats", str(d), "--out", str(out)],
                       capture_output=True, text=True, timeout=600)
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]
    rep = json.loads(out.read_text())
    assert list(rep["floats"]) == ["table1_price_of_revocation"]
    assert rep["missing"] == [n for n in fh.BUDGETS_MS7 if n != "table1_price_of_revocation"]
    assert rep["labels"]["file"] == "paper/generated/labels_stub_ms7.tex"
    r = subprocess.run([sys.executable, str(script), "--allow-missing", "--out", str(out)], capture_output=True,
                       text=True)
    assert r.returncode == 2 and "--allow-missing needs --ms7" in r.stderr
