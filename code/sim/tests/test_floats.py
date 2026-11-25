"""Tests of the floats of paper/floats/ and of paper/refs.bib (design/sim_spec_ms3.md §9 and §10, row test_floats.py).

- The three .tex files contain every row and label of §9: Table I's lenders, information models, orders, bounds and
  result IDs with the assumptions note and no example value; Table II's rows (1)-(18) of design/figure_plan.md §2 in
  order, named exactly by the style.POLICIES labels (BL7: "Revocable-only"), with their information classes, credits
  and status labels, row (13) worded as §9 prescribes; Algorithm 1's inputs, test, allowance, abort, wind-down and
  defaults, hand-set without an algorithm package.
- paper/refs.bib holds the keys the floats cite (C48: among the keys the sections cite), each entry equal to the
  BibTeX block of its literature/papers/<folder>/summary.md.
- The floats compile with pdflatex (paper/layout_check/IEEEtran.cls) in a temporary folder without errors or overfull
  boxes, and floats_heights.py reproduces the plan's mock-page constants (skipped if pdflatex is not installed).

C47 (design/ms6_spec.md M7, M13; unit U45 of the MS6 entry gate): Table I's caption says "Competitive ratio on the
single-LLM family, by lender and reclaim information" (M13), and its note names the results by \\ref to the paper's
labels of design/ms6_spec.md §5 instead of the design IDs C3-T4, C3-T4', O1-A to O1-D; the floats compile with the label
stub paper/generated/labels_stub.tex, without an undefined reference, and floats_heights.py measures them with it. Each
changed line names C47.

C50 (design/ms6_spec.md §7.2 D5 review): Table I's column heads drop "(I1)" and "(I2)", which the main text no longer
uses. Each changed line names C50.

C52 (design/ms7/plan.md §4, unit T1, glossary G9): the main-text floats print no all-caps status word; Table I's caption
drops "All bounds PROVEN." (its note names the theorem behind each bound, and a cited result carries no status word).
Each changed line names C52.

C58 (design/ms7/w_spec.md W-D7, §3; unit W0 of the MS7 writing phase): the label-stub test reads the new stub
paper/generated/labels_stub_ms7.tex, which follows the renumbered paper/results.json, and checks that the frozen stub
paper/generated/labels_stub.tex, which the frozen floats compile with, is still the MS6 map. Each changed line names C58.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

from figs import style

REPO = style.REPO
FLOATS = REPO / "paper" / "floats"
BIB = REPO / "paper" / "refs.bib"
LIT = REPO / "literature" / "papers"
LAYOUT = REPO / "paper" / "layout_check"
PDFLATEX = Path.home() / ".local" / "bin" / "pdflatex"
LABELS = REPO / "paper" / "generated" / "labels_stub.tex"      # C47: the paper's result labels (ms6_spec M7, §5)
NAMES = ("table1_price_of_revocation", "table2_policies", "alg1_guard")
CITED = {"narayana2020retrorenting", "mao2025skyserve", "qiu2026joint", "markarian2019online"}
# Table II, rows (1)-(18) of design/figure_plan.md §2: registry keys (None: BL7, label "Revocable-only", M41)
TABLE2_ROWS = (("sublet", "sublet_siloed"), ("a7_guard", "bl1_guard"), ("bl5",), ("bl1",), ("bl2",), ("bl4",),
               ("a7",), ("a6", "a6_siloed"), ("a2_frac", "a2_r1", "a2_theory"), ("a3",), ("rr_renew",),
               ("marking",), ("a1",), ("prewarm",), ("bl6",), (None,), ("bl0a", "bl0b"), ("opt", "opt_eager", "lb"))


def _tex(name) -> str:
    return (FLOATS / f"{name}.tex").read_text(encoding="utf-8")


def _body(tex: str) -> str:
    """The LaTeX without its comment lines."""
    return "\n".join(l for l in tex.splitlines() if not l.lstrip().startswith("%"))


def _has_words(tex: str, phrase: str) -> bool:
    """`phrase` occurs in `tex` up to whitespace, line breaks (\\\\) and \\shortstack[l]{ ... } wrappers."""
    sep = r"(?:\s|~|\\\\|\\shortstack\[l\]\{|\}|\{)+"
    return re.search(sep.join(re.escape(w) for w in phrase.split()), tex) is not None


def _cites(tex: str) -> set:
    return {k.strip() for m in re.finditer(r"\\cite(?:\[[^\]]*\])?\{([^}]*)\}", tex) for k in m.group(1).split(",")}


def _bib_entries(text: str) -> dict:
    return {m.group(1): m.group(0) for m in re.finditer(r"@\w+\{([^,\s]+),.*?\n\}", text, re.S)}


def _summary_entries() -> dict:
    # C48 (design/ms6_spec.md §3.4): paper/tools/bib.py also takes the @misc blocks of literature/sources/*.md
    # (web sources such as the Akash proposal), so the pin reads them too
    out = {}
    for s in sorted(LIT.glob("*/summary.md")) + sorted((LIT.parent / "sources").glob("*.md")):
        for block in re.findall(r"```bibtex\n(.*?)```", s.read_text(encoding="utf-8"), re.S):
            for k, e in _bib_entries(block).items():
                out.setdefault(k, (e, s))
    return out


# ---------------------------------------------------------------------------------------------------------------
def test_table1_rows_and_labels():
    t = _body(_tex("table1_price_of_revocation"))
    assert r"\begin{table}" in t and r"\toprule" in t and r"\bottomrule" in t and r"\caption{" in t
    # C47: the caption of design/ms6_spec.md M13 (no "price" name; the scope against OPT); C52 (T1 glossary G9): no
    # status word, since the note cites the theorem behind each bound
    assert _has_words(t, r"\caption{Competitive ratio on the single-LLM family, by lender and reclaim information, "
                         r"against $\mathrm{OPT}(\sigma,\omega)$.}")                                      # C52
    assert not re.search(r"PROVEN|VERIFIED NUMERICALLY|CONJECTURE", t)                                      # C52
    assert "Price of revocation" not in t
    for phrase in ("Private reclaim information", "Public reclaim information"):      # C50: without (I1), (I2)
        assert _has_words(t, phrase), phrase
    assert "(I1)" not in t and "(I2)" not in t                                         # C50
    rows = [r.replace(r"\addlinespace", "").strip() for r in t[t.index(r"\midrule"):t.index(r"\bottomrule")]
            .replace(r"\midrule", "").split(r"\\")]
    first = " ".join(r.split("&")[0].strip() for r in rows if r)            # the lender column, row by row
    assert _has_words(first, "Adaptive Oblivious, randomized algorithms"), first
    for cell in (r"\Theta(\min(\rho,m))", r"\Theta(\min(\rho,1+\log m))", r"\rho m/(m+\rho-1)", r"\min(\rho,2m)",
                 r"\min(\rho,m)/4", r"\min(\rho+1,0.63\log_2m)/4", r"\min(\rho,2h_m+1)", "the same bounds"):
        assert cell in t, cell
    # C47 (design/ms6_spec.md M7): the results by \ref to the labels of §5, in place of the design IDs C3-T4 and
    # C3-T4' (Theorem 2(a), (b)), O1-A (2(c)), O1-C (3(b)), O1-B (3(a)) and O1-D (3(c)); no design ID is printed
    # C47 (print check of the gate, U46): each lower bound with its lender, (c) (O1-A) the oblivious row's
    for rid in (r"Theorem~\ref{thm:lower}(a), (b) (adaptive) and (c) (oblivious, $m\ge3$, under",        # C47: U46
                r"Theorem~\ref{thm:public}(b) ($\tau\ge1$)",
                r"upper bounds: Theorem~\ref{thm:public}(a), and (c) for public information", r"$m\ge3$",
                r"$\tau\ge1$"):                                                    # C52: no "PROVEN" (G9)
        assert _has_words(t, rid), rid
    assert not re.search(r"C3-T4|O1-[A-D]", t)
    for phrase in ("per-site coupling", "one notice per lease", "no cheap probes", "lenders that always sell",
                   "asymptotic in"):
        assert _has_words(t, phrase), phrase
    # no example values (design Table 2.7 goes to the supplement): the only decimal is O1-C's constant
    assert re.findall(r"\d+\.\d+", t) == ["0.63"]


def test_table2_rows_in_order_with_registry_labels():
    t = _body(_tex("table2_policies"))
    rows = t[t.index(r"\midrule"):t.index(r"\bottomrule")].split(r"\\")
    rows = [r.strip() for r in rows if r.strip()]
    assert len(rows) == len(TABLE2_ROWS)
    for row, keys in zip(rows, TABLE2_ROWS):
        name = row.split("&")[0]
        labels = ["Revocable-only" if k is None else style.POLICIES[k].label for k in keys]
        assert all(_has_words(name, lab) for lab in labels), (labels, name)
        assert len(row.split("&")) == 4, row
    assert "bl7" not in style.POLICIES and "Revocable-only" not in {p.label for p in style.POLICIES.values()}
    # information classes (sim_spec_ms2 §2.3) and guarantees with their status labels (plan §2)
    info = [r.split("&")[2].strip() for r in rows]
    assert info[0] == info[1] == "I1$+N$" and info[8] == "I1; I1; I1$+N$" and info[11] == "I2"
    assert info[16] == "I1; hind." and info[17] == "off."
    for i, phrase in ((0, "G3(b) on the core PROVEN, audited"), (0, "W(c) CONJECTURE"), (1, "as Sublet"),
                      (6, "a labeled heuristic"), (7, "its components are heuristics"),
                      (8, "C3-T1 PROVEN; none; C3-Cor3 PROVEN"), (9, "VERIFIED NUMERICALLY in reference mode only"),
                      (10, "O1-B PROVEN on the family"), (11, "O1-D PROVEN on the family"),
                      (12, "C2-T4 with the C2-T4 thresholds only (PROVEN under (C$'$)); no ratio claimed at the "
                           "default switch cost"),
                      (16, "references"), (17, "benchmarks")):
        assert _has_words(rows[i].split("&")[3], phrase), (i, phrase)
    assert all(rows[i].split("&")[3].strip() == "none" for i in (2, 3, 4, 5, 13, 14, 15))
    assert r"For the engine as implemented under C1--C3" in t
    # credits (§9): BL5, BL4 (the ToN extension of qiu2025cocar), the PD machinery, BL3 in the note
    assert r"\cite[Alg.~1]{narayana2020retrorenting}" in rows[2] and r"\cite{qiu2026joint}" in rows[5]
    assert r"\cite{markarian2019online}" in rows[8] and r"\cite{mao2025skyserve}" in t


def test_algorithm1_content():
    t = _body(_tex("alg1_guard"))
    assert r"\begin{figure}" in t and r"\footnotesize" in t and r"\textbf{Algorithm 1}" in t
    assert not re.search(r"\\(usepackage|begin)\{(algorithm|algorithmic|algorithm2e|algpseudocode)", t)
    lines = re.findall(r"\\algl\{(\d+)\}", t)
    assert lines == [str(i) for i in range(1, len(lines) + 1)] and 12 <= len(lines) <= 18
    for s in (r"S=\mathrm{T11}_{\gamma'}(\mathrm{FB},R)", r"B(t)\leftarrow\min\{B_0,\kappa B_{\mathrm{on}}(t)\}",
              r"\hat a(t)\leftarrow\mathrm{ALG}(t-1)+p_E(t)+\mathrm{rent}(t)+G(t)+\Sigma(t)", "test T0g",
              r"\hat a(t)+R(t)\le\gamma C_S(t)+B(t)", "one-way abort", r"t_a\leftarrow t", "discard $A_E(t)$",
              r"\beta(K)=G+\Sigma+\mathrm{rent}-Q+R", "K1, K0, K2", "adaptive wind-down",
              "$E$'s actions on its own observation", r"$\gamma=1$", r"$\gamma'=1+1/\sqrt{2}$", r"$\kappa=10$",
              "one fresh replica per client", "RetroRenting-style", r"$G$, $\Sigma$: bounds"):
        assert s in t, s
    assert "S(t)" not in t.replace("C_S(t)", "")


def test_refs_bib_equals_the_summaries():
    cited = set()
    for n in NAMES:
        cited |= _cites(_body(_tex(n)))
    assert cited == CITED
    bib = _bib_entries(BIB.read_text(encoding="utf-8"))
    # C48 (design/ms6_spec.md §3.4): from MS6 the sections cite more keys than the floats, and paper/tools/bib.py
    # writes refs.bib from every key the main text cites, so refs.bib holds the floats' keys among others
    assert cited <= set(bib)
    src = _summary_entries()
    for k, e in bib.items():
        assert k in src, f"{k}: no BibTeX block in literature/papers/*/summary.md"
        assert e == src[k][0], f"{k} differs from the block in {src[k][1]}"
    assert src["qiu2026joint"][1].parent.name == "qiu2025cocar"


# ---------------------------------------------------------------------------------------------------------------
LABELS_MS7 = REPO / "paper" / "generated" / "labels_stub_ms7.tex"  # C58 (design/ms7/w_spec.md W-D7)


def test_label_stub_prints_the_manuscripts_numbers():
    """C48 (design/ms6_spec.md §5, M7): the label stub gives every result of the manuscript's result map
    paper/results.json the number the manuscript prints, and no other label.
    C58 (design/ms7/w_spec.md W-D7, §3; unit W0): that stub is now paper/generated/labels_stub_ms7.tex, for the MS7
    numbering; paper/generated/labels_stub.tex stays the frozen MS6 map that the frozen floats cite: its numbers are
    the ms6_number fields of the main-text entries and of the seven entries that moved to the supplement."""
    res = json.loads((REPO / "paper" / "results.json").read_text(encoding="utf-8"))["results"]
    stub = dict(re.findall(r"\\newlabel\{([^}]+)\}\{\{(\d+)\}\{1\}\}", LABELS_MS7.read_text(encoding="utf-8")))  # C58
    assert stub == {r["slug"]: str(r["number"]) for r in res}
    ms6 = {r["slug"]: str(r["ms6_number"]) for r in res if r.get("ms6_number") is not None}  # C58
    for f in sorted((REPO / "paper" / "supplement" / "results").glob("*.json")):  # C58
        ms6.update({r["slug"]: str(r["ms6_number"]) for r in json.loads(f.read_text(encoding="utf-8"))["results"]
                    if r.get("ms6_number") is not None})  # C58
    frozen = dict(re.findall(r"\\newlabel\{([^}]+)\}\{\{(\d+)\}\{1\}\}", LABELS.read_text(encoding="utf-8")))  # C58
    assert frozen == ms6 and sorted(map(int, frozen.values())) == list(range(1, 18))  # C58


@pytest.mark.skipif(not PDFLATEX.is_file(), reason=f"{PDFLATEX} is not installed")
@pytest.mark.parametrize("name", NAMES)
def test_floats_compile(name, tmp_path):
    # C47: with the label stub (design/ms6_spec.md M7), so that Table I's \ref print their numbers
    doc = ("\\documentclass[journal]{IEEEtran}\\usepackage{booktabs}\\usepackage{array}\n\\input{labels_stub.tex}\n"
           f"\\begin{{document}}\n\\input{{{name}.tex}}\nText.\n\\end{{document}}\n")
    (tmp_path / "doc.tex").write_text(doc)
    env = dict(os.environ, TEXINPUTS=f"{LAYOUT}:{FLOATS}:{LABELS.parent}:")
    r = subprocess.run([str(PDFLATEX), "-interaction=nonstopmode", "-halt-on-error", "doc.tex"], cwd=tmp_path,
                       capture_output=True, text=True, env=env, timeout=300)
    log = (tmp_path / "doc.log").read_text(errors="replace")
    assert r.returncode == 0 and (tmp_path / "doc.pdf").is_file(), log[-2000:]
    assert "Overfull" not in log, [l for l in log.splitlines() if "Overfull" in l]
    assert "LaTeX Error" not in log
    assert "LaTeX Warning: Reference" not in log, [l for l in log.splitlines() if "Reference" in l]     # C47


@pytest.mark.skipif(not PDFLATEX.is_file(), reason=f"{PDFLATEX} is not installed")
def test_floats_heights_method(tmp_path):
    sys.path.insert(0, str(LAYOUT / "pageplan"))
    try:
        import floats_heights as fh
    finally:
        sys.path.remove(str(LAYOUT / "pageplan"))
    rep = fh.measure(workdir=tmp_path)
    for k, p in rep["probes"].items():          # the plan's constants of the mock pages (figure_plan §3.1)
        assert abs(p["measured_pages"] - p["plan_value_pages"]) <= 0.001, (k, p)
    assert set(rep["floats"]) == set(NAMES)
    for k, v in rep["floats"].items():
        assert 0 < v["measured_pages"] < 1 and v["budget_pages"] == fh.BUDGETS[k]
    # C47 (design/ms6_spec.md M7): the mock pages \input the label stub, recorded with its sha256
    assert fh.LABELS == LABELS and rep["labels"]["file"] == "paper/generated/labels_stub.tex"
    assert rep["labels"]["sha256"] == hashlib.sha256(LABELS.read_bytes()).hexdigest()
