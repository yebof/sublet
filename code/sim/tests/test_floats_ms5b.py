"""Tests of the MS5b floats (design/sublet_v2.md §11, W2, W4, W5, W13, row test_floats_ms5b.py): Table III v2, written
by figs/table3_v2.py; the hand-set Table II v2 (paper/floats/table2_policies_v2.tex) and Algorithm 1 v2
(paper/floats/alg1_guard_v2.tex); the hand-set supplementary table paper/supplement/tables/ms5b_deviations.tex.

- Table III v2, from the input tree tests/fixtures_figs_ms5b/inputs/ (reduced-mode driver outputs, not results): the
  rows of W2 in order, each named by its style.POLICIES label of the MS5b registry (no legacy key, check_policies and
  check_legacy pass), the seven columns, every cell equal to an independent recomputation from the fixture summaries,
  analysis.json and run files (medians by numpy, p* from analysis.json's crossing table by the lower median), the
  dashes of W2 (no gap run for BL2, A6 and Sublet one-way; BL0a's RC and p*); the caption and its note with the scope,
  the allowance, the certificate count and cases (naming the legacy guarded runs that the count includes), G3(b) for
  the guarded rows around A9 only, the aborts, H1's set, H2b's count and BL0b's ratio in overflow accounting, every
  number from the inputs, and never "every baseline"; the extract's scope block covers every row, week, gap day and
  mode; the writer refuses reduced input for paper/floats/, writes into SUBLET_FIGS_PDF_DIR when it is set, and
  --from-extract rewrites the same float; build() on the input tree equals the fixture extract, opens only result
  files, and lists every run file it read with its sha256.
- Table II v2: every policy named in a main-text figure or table (FIGURE_POLICIES of the manuscript's figures, Table
  III v2's rows, A9 and the lagged BL5) is a row, by its registry label or, for a legacy key, its configuration's name
  (W8); the status labels are those of design/theory/c3_c4_c5_general.md §9 (the headings of Lemma G5', Corollary G3',
  Remark R, Lemma P.1 and Proposition P, copied verbatim) and ms3_claims.W_AB, with their scopes; every guarantee part
  with a status word is copied from C3, W_AB or the frozen Table II (never upgraded); W(c), a conjecture after Theorem
  16 in the text, carries CONJECTURE in the dagger note, every part citing an MS5b result carries the mark of the note
  with its label, and only the three guarded
  rows at Sublet's allowance carry the allowance mark.
- Algorithm 1 v2: E is A9; the candidate ladder (A_E(t), the prefixes P1 with their sizes, P0, K0) in the order of
  ProjectedGuarded.candidates, an abort only if none passes; the allowance any nondecreasing online allowance, Sublet's
  min{W_k, LB'}; FB defined; the lines of the frozen float's mode S and wind-down (up to a box that keeps math on one
  line and a group that sets a line ragged right).
- ms5b_deviations.tex: exactly the items of the pre-registration's list (B1, B2, B3, B5, B12, B13, C2), each text equal
  to the pre-registration's §7 item after the markdown-to-LaTeX conversion is undone.
- Every float compiles with paper/layout_check/IEEEtran.cls without an overfull box (Table III v2 also at real-scale
  cell widths), and floats_heights.py measures the v2 floats next to BUDGETS_MS5B (skipped without pdflatex).
Every file is written under pytest's tmp_path; nothing is written into paper/ or code/sim/out/.

C47 (design/ms6_spec.md M7, M14, M17; unit U45 of the MS6 entry gate): the floats name results by \\ref to the paper's
labels of design/ms6_spec.md §5 (design/ms6/inventory_consistency.md §2.4) instead of the design names, and print no
experiment ID. Table III v2's title is "End-to-end cost per policy, medians of ..." (no "E7"), its note writes
Theorem~\\ref{thm:fullmodel}'s envelope with its cases (a) and (b) (W(c), a conjecture in the text, only where it has
runs), "the ratio bound at this allowance rests on
Corollary~\\ref{cor:ratio}" and the MS4 configuration's allowance as "($B_0$ = 10% of All-fallback)"; Table II v2's
cells and note cite Corollary~\\ref{cor:ratio}, Lemmas~\\ref{lem:onlinelb} and \\ref{lem:projection},
Proposition~\\ref{prop:noabort} (with Lemma P.1 as its premise), Theorem~\\ref{thm:fullmodel} and its extension,
Theorem~\\ref{thm:reduction}(d), Theorem~\\ref{thm:public}(a) and (c) and Theorem~\\ref{thm:notice}, the C3 §9
headings with their status labels and scopes copied verbatim up to that map of names (PAPER_NAMES, INNER_NAMES), and
every guarantee part with a status word copied from C3, W_AB or the frozen Table II with the sources' design names
read as their paper labels' \\ref (to_paper, PART_MAP: the result named, its status words and scope compared; a wrong
\\ref fails); Algorithm 1 v2 writes
$S=\\mathrm{Comb}_{\\gamma'}(\\mathrm{FB},\\mathrm{PD})$ and Lemma~\\ref{lem:onlinelb}, and its line 12 gains "T0g is
in its bound form" (Guarded._wind_down's condition, which the frozen line omits). The floats compile with the label
stub paper/generated/labels_stub.tex and without an undefined reference, and floats_heights.py measures them with it.
Each changed line names C47.

C49 (design/ms6_spec.md §8, D6: the page measurement and its cuts): Table II v2 is made compact. The scopes live with
the statements in Sections IV-VI, and the table cites results by label: it is a one-column float of the rows "Policy:
rule" and "Guarantee", the policies without a guarantee and the references full width, the information class a mark
on the name ($^N$: the a-priori bound N; $^P$: public reclaim information), and its long note, which copied the C3 §9
headings, W_AB and the pre-registration's scopes, is dropped. The tests that pinned that note
(test_table2_v2_status_labels_are_copied_with_scope and the Table II v2 checks of C47) check the new rule instead:
every cited result is a theorem, lemma, proposition or corollary of Sections IV-VI (PROVEN by M10, its scope in its
statement), each part that cites one carries PROVEN, the C3 §9 headings and W_AB keep their labels where their paper
results are stated, the only status word without a result (A3's) is copied from the frozen Table II, and each row
cites the results of TABLE2_REFS; the checks that still apply are kept (every policy of the main text a row, no
audit word, no contribution or design ID, ALG*'s rule). Each changed line names C49.

C50 (design/ms6_spec.md §7.2, the D5 review; with D4's as-built list of script items, §7.1 D4): Table III v2's note
uses Section VII's words: the gap reruns with "5-min routing" over "the LP bound", "an upper bound on the ratio to the
offline optimum" (no "slow grid", "merged" or "gap"); the certificate's modes as "trace, five stress and honoring
lenders"; and "Corollary~\\ref{cor:ratio}(b) holds for Sublet and Sublet, one-way, on core instances only" (no
"rests on": no ratio is claimed for the week runs). Table II v2 writes A3's scope in plain words, "only
with cold re-buys at the same site" for the frozen "in reference mode only" (the status rule reads the one as the
other), the PD heuristic as "revocable-only PD" and the notice-layer rows' "critical-ratio renting's notice layer".
Each changed line names C50.

C52 (design/ms7/plan.md §4, unit T1: the manuscript scan and its glossary G3-G6, G9): the main-text floats print no
all-caps status word. Table II v2's parts that cite results carry no status word (each is a statement of Sections
IV-VI), A3's bound reads "numerically verified only with cold re-buys at the same site" in plain words (the status rule
reads it as the frozen "VERIFIED NUMERICALLY in reference mode only"), the one-way guards run "at the per-LLM
allowance", ALG* is set as ALG$^\\ast$ (its registry label, "ALG*", which the figures draw, is unchanged), and the key
reads "Unmarked: private information". Algorithm 1 v2 writes the cap W_k with the paper's macro \\Wk (B_peak). Table
III v2's title drops the policy seed, its note names "the per-group allowance $\\min\\{\\Wk,\\mathrm{LB}'\\}$" without
"$\\kappa$ none", "Theorem~\\ref{thm:fullmodel}'s bound", the MS4 configuration "of the all-fallback bill" without "the
supplement's", and "Primary baselines (H1):" for "H1's set:". Each changed line names C52.

C58 (design/ms7/w_spec.md §1.3, §3, W-D3, W-D4 stage 1; unit W0 of the MS7 writing phase): the seven results of w_spec
§1.3 left Sections IV-VI and are ordinary environments of the supplement parts S-B, S-C and S-D with their slugs and
statements unchanged. The frozen Table II v2 still cites three of them (Lemma~\\ref{lem:projection},
Proposition~\\ref{prop:noabort}, Theorem~\\ref{thm:fullmodel}), so _statements() also reads the moved results (only
their slugs) from those parts, and the conjecture after Theorem~\\ref{thm:fullmodel} is looked for in s_d.tex. The
rule the tests check is unchanged. Each changed line names C58.
"""
from __future__ import annotations

import builtins
import copy
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from figs import style
from figs import table3_v2 as t3
from figs.common import json_number
from figs.inputs import Inputs
from sublet.experiments import ms3_claims

REPO = style.REPO
SIM = REPO / "code" / "sim"
FIX = Path(__file__).resolve().parent / "fixtures_figs_ms5b"
IN_ROOT = FIX / "inputs"
CONF = IN_ROOT / "code" / "sim" / "out" / "sublet_v2"
LAYOUT = REPO / "paper" / "layout_check"
FLOATS = REPO / "paper" / "floats"
DEVIATIONS = REPO / "paper" / "supplement" / "tables" / "ms5b_deviations.tex"
C3 = REPO / "design" / "theory" / "c3_c4_c5_general.md"
PREREG = REPO / "design" / "sublet_v2_prereg.md"
PDFLATEX = Path.home() / ".local" / "bin" / "pdflatex"
STALE = ("tests/fixtures_figs_ms5b/table3_v2.json is stale (the script's data changed): refresh it with "
         "`python tests/fixtures_figs_ms5b/refresh_extracts.py --only table3_v2` from code/sim")
# W2's rows in order, by registry key
ROW_KEYS = ("sublet_v2", "sublet_1way", "bl1_gp", "bl1n", "bl5n", "bl1", "bl1_bo", "bl5_cur", "bl5_tau60", "bl2",
            "bl3_0", "bl4", "a6", "bl0a")
NO_GAP = ("Sublet-1way", "BL2", "A6")            # W2: "--" for BL2, A6 and Sublet one-way
COLUMNS = ("usd", "saving_pct", "gap", "RC", "W0", "p_star")
MAIN_FIGURES = ("fig1", "fig2", "fig3", "fig4v2", "fig5", "fig6", "fig7")      # the manuscript's (W6)
# Table II v2's rows by registry key; a legacy key (W8) is named by its configuration
# C49 (design/ms6_spec.md §8, D6): the eight rows with a guarantee first, then the full-width rows: the policies
# without a guarantee (Two-timescale PD and PD heuristic merged) and the references with the offline benchmarks
TABLE2_ROWS = (("sublet_v2",), ("sublet_1way",), ("bl1_gp",), ("sublet", "bl1_guard", "a7_guard"),  # C49
               ("a2_frac", "a2_r1", "a2_theory"), ("a3",), ("rr_renew", "marking"), ("a1",),  # C49
               ("a9",), ("bl1n", "bl5n"), ("bl1", "bl1_bo"), ("bl5_cur", "bl5_lag", "bl5_tau60"),  # C49
               ("bl2", "bl3_0", "bl4"), ("a6", "a7"), ("prewarm", "bl6", None),  # C49
               ("bl0a", "bl0b", "opt", "opt_eager", "lb"))  # C49
TABLE2_GUARANTEED = 8  # C49: the rows with a Guarantee cell; the others span both columns
LEGACY_NAMES = {"sublet": style.POLICIES["bl5_g1"].label, "bl1_guard": style.POLICIES["bl1_g1"].label,
                "bl5": style.POLICIES["bl5_lag"].label, "a7_guard": "PD heuristic + one-way guard"}
STATUS_WORD = re.compile(r"PROVEN|VERIFIED NUMERICALLY|CONJECTURE")
# C52 (design/ms7/plan.md §4, T1 glossary G9): the status words in plain words, the only form the main text prints
PLAIN_STATUS = re.compile(r"\bproven\b|\bnumerically verified\b|\bconjecture\b")  # C52
ALG_STAR = r"ALG$^\ast$"  # C52: Table II v2's name of ALG* (registry label "ALG*", which the figures draw)
MACROS = REPO / "paper" / "macros.tex"  # C52: the paper's definition of \Wk
# C50 (design/ms6_spec.md §7.2, D5 review): A3's status scope in plain words, for the frozen table's "in reference mode
# only" (design/sim_spec_ms2.md §7.5: reference mode is x3 off, no rotation, and the reaction "cold")
A3_SCOPE_WORDS = "only with cold re-buys at the same site"  # C50
A3_SCOPE_FROZEN = "in reference mode only"  # C50
C3_HEADINGS = ("Lemma G5′", "Corollary G3′", "Remark R", "Lemma P.1", "Proposition P")
DEVIATION_ITEMS = ("B1", "B2", "B3", "B5", "B12", "B13", "C2")
# C47 (design/ms6_spec.md M7, §5): the label stub that gives \ref its printed numbers on the test documents
LABELS = REPO / "paper" / "generated" / "labels_stub.tex"
# C47: the paper's names of the MS5b results whose C3 §9 headings Table II v2's note copied (M14: Lemma P.1 is
# Proposition 15's premise), and the design names inside those headings mapped the same way (G3: "the ratio bound";
# Remark R(e): Lemma 11(e)); C48: the numbers as printed (paper/results.json)
PAPER_NAMES = {"Lemma G5′": r"Lemma~\ref{lem:onlinelb}", "Corollary G3′": r"Corollary~\ref{cor:ratio}",
               "Remark R": r"Lemma~\ref{lem:projection}", "Lemma P.1": r"Proposition~\ref{prop:noabort}'s premise",
               "Proposition P": r"Proposition~\ref{prop:noabort}"}
# C49 (design/ms6_spec.md §8, D6): INNER_NAMES, the map of the design names inside the C3 §9 headings that Table II
# v2's note copied, is dropped with the note; PAPER_NAMES now gives the paper result whose statement carries each
# heading's scope (test_table2_v2_cites_results_by_label_with_status_word)
# C47 (U46; M10, M11): words that stay out of the main-text floats (the supplement's mapping table lists the audit
# words), and the contribution IDs C1-C7 (M11; consistency §1.2 row C_S), which only Theorem 16's conditions C1-C3 may
# print (as "C1--C3" and "C1 of Theorem"); checked in Tables I, II v2, III v2 and Algorithm 1 v2
MAIN_TEXT_FORBIDDEN = re.compile(r"audited|numerically checked|\\mathrm\{Proj\}_")  # C47
CONTRIB_ID = re.compile(r"\bC[1-7]\b(?:--C[1-7]\b)?(?:\s+of\s+Theorem)?")  # C47
MAIN_TEXT_FLOATS = ("table1_price_of_revocation.tex", "table2_policies_v2.tex", "table3_v2.tex", "alg1_guard_v2.tex")
# C49 (design/ms6_spec.md §8, D6): PART_MAP and to_paper, which compared each guarantee part with its source's
# design names read as the paper's \ref, are dropped: the parts no longer copy their sources' scopes; a part cites
# results by \ref with their status word, and TABLE2_REFS fixes which results each row cites
# C47 (design/ms6_spec.md M7; design/ms6/inventory_consistency.md §2.4): the results each guarantee cell of Table II
# v2 cites, in order, by the first name of its row (label and part letters); every other row cites none
# C49: Corollary~\ref{cor:ratio} by its part, (b) at Sublet's allowance (B <= LB'), (a) at the original allowance
TABLE2_REFS = {
    "Sublet": ["cor:ratio(b)", "lem:onlinelb", "lem:projection", "prop:noabort", "thm:fullmodel"],  # C49
    "Sublet, one-way": ["cor:ratio(b)", "lem:onlinelb", "thm:fullmodel"],  # C49
    "Greedy + guard": ["prop:noabort", "thm:fullmodel"],
    "Lagged RetroRenting + one-way guard": ["cor:ratio(a)", "thm:fullmodel"],  # C49
    "A2 fractional": ["thm:reduction(d)", "thm:reduction(d)"],
    "RR-renew": ["thm:public(a)", "thm:public(c)"],
    ALG_STAR: ["thm:notice"]}  # C52: ALG$^\ast$
# C49 (design/ms6_spec.md §8, D6): the statements of Sections IV-VI, where the scopes of the results that Table II v2
# cites live, and their environments (M10: a Theorem, Lemma, Proposition or Corollary is PROVEN with its scope)
SECTIONS = REPO / "paper" / "sections"
STATEMENT_FILES = ("revocation.tex", "singlesite.tex", "sublet.tex")  # C49: Sections IV, V and VI
PROVEN_ENVS = ("theorem", "lemma", "proposition", "corollary")  # C49
# C58 (design/ms7/w_spec.md §1.3, §3, W-D3, W-D4 stage 1; unit W0): the seven results that moved to the supplement keep
# their slugs and statements as ordinary environments of the supplement parts S-B, S-C and S-D; the frozen Table II v2
# still cites three of them, so their statements are read there (only the moved slugs, the entries of
# paper/supplement/results/*.json with an ms6_number)
SUPP_SECTIONS = REPO / "paper" / "supplement" / "sections"  # C58
MOVED_FILES = ("s_b.tex", "s_c.tex", "s_d.tex")  # C58: where w_spec §1.3 puts the moved results
SUPP_RESULTS = REPO / "paper" / "supplement" / "results"  # C58
# C47: no design name of a result is printed in Table II v2 or Algorithm 1 v2 (M7)
DESIGN_NAMES = re.compile(r"G3\(b\)|G[35]\$'\$|\bW\([abc]\)|Theorem W|C3-T1|C3-Cor3|O1-[A-D]|C2-T4|Remark R|"
                          r"Lemma P\.1|Proposition P\b|\(P\.1, P\)|T11")


def _body(tex: str) -> str:
    return "\n".join(l for l in tex.splitlines() if not l.lstrip().startswith("%"))


def _rows(tex: str, start: str = r"\midrule", end: str = r"\bottomrule") -> list[list[str]]:
    body = _body(tex)
    part = body[body.index(start) + len(start):body.index(end)].replace(r"\addlinespace", "")
    return [[c.strip() for c in r.split("&")] for r in part.split(r"\\") if r.strip()]


def _ws(s: str) -> str:
    return " ".join(s.split())


def _fmt(v, d):
    if v is None:
        return "--"
    s = f"{v:.{d}f}"
    if float(s) == 0.0:
        s = s.lstrip("-")
    return "$-$" + s[1:] if s.startswith("-") else s


def _tree(rel: str):
    return json.loads((CONF / rel).read_text())


def _run_file(part: str, job: str) -> dict:
    name = re.sub(r"[^A-Za-z0-9_.-]+", "__", job) + ".json"
    return json.loads((CONF / part / "runs" / name).read_text())


@pytest.fixture
def written(tmp_path, monkeypatch):
    """The float and extract that the writer writes from the input tree, in tmp_path (--out)."""
    monkeypatch.setenv("SUBLET_FIGS_IN_ROOT", str(IN_ROOT))
    monkeypatch.setenv(style.ENV_OUT_DIR, str(tmp_path / "out"))
    monkeypatch.delenv(style.ENV_PDF_DIR, raising=False)
    t3.main(["--out", str(tmp_path / "floats")])
    tex = (tmp_path / "floats" / "table3_v2.tex").read_text(encoding="utf-8")
    ext = json.loads((tmp_path / "out" / "table3_v2.json").read_text(encoding="utf-8"))
    return tmp_path, tex, ext


# ---------------------------------------------------------------------------------------------------------------
# Table III v2
def test_rows_columns_and_registry(written):
    _, tex, ext = written
    assert tuple(k for _, k in t3.ROWS) == ROW_KEYS and t3.NAME == "table3_v2"
    assert r"\begin{table}[t]" in tex and r"\label{tab:e7}" in tex and r"\footnotesize" in tex
    assert r"\begin{tabular*}{\columnwidth}" in tex and r"\toprule" in tex and r"\cite" not in tex
    head, body = _rows(tex, r"\toprule", r"\midrule"), _rows(tex)
    assert len(head) == 2 and len(body) == len(ROW_KEYS) and all(len(r) == 7 for r in head + body)
    assert [r[0] for r in body] == [style.POLICIES[k].label for k in ROW_KEYS]
    header = " ".join(" ".join(r) for r in head)
    for word in ("Policy", "USD/week (k)", "overflow (total)", "Saving", r"(\%)", "ALG/", "LB", "RC", "$W_0$",
                 r"$p^\ast$"):
        assert word in header, word
    keys = set(ROW_KEYS)
    assert keys <= set(style.MS5B_KEYS) | {"bl1", "bl2", "bl4", "a6", "bl0a"}
    assert not keys & set(style.LEGACY_KEYS)
    style.check_policies(keys)
    style.check_legacy({"table3_v2": keys}, {})
    assert ext["data"]["order"] == [t for t, _ in t3.ROWS] and ext["data"]["columns"] == list(COLUMNS)
    assert "REDUCED INPUT" in tex                         # the fixture is a smoke run


def test_cells_equal_an_independent_recomputation(written):
    """Every printed cell recomputed from the fixture summaries, analysis.json and run files (numpy medians; p* from
    analysis.json's crossing table, a source other than the curves the script reads)."""
    _, tex, _ = written
    main, second, ana = _tree("main/summary.json"), _tree("second/summary.json"), _tree("analysis.json")
    body = {r[0]: r[1:] for r in _rows(tex)}
    weeks = sorted({r["cell"] for r in main["runs"] if r["kind"] == "week"})
    gap = [r for r in second["runs"] if r["kind"] == "gap"]
    gap_cells = sorted({r["cell"] for r in gap})
    p_weeks = sorted({r["cell"] for r in second["runs"] if r["kind"] == "week"})
    cross, curves = ana["reported"]["intensity_crossings"], ana["reported"]["intensity_curves"]
    top = max(p for c in curves.values() for w in c.values() for p, r in w["points"] if r is not None)
    for tag, key in t3.ROWS:
        cells = body[style.POLICIES[key].label]
        lr = {w: next(r for r in main["runs"] if r["tag"] == ("Sublet" if tag == "BL0a" else tag)
                      and r["mode"] == "L-tr" and r["cell"] == w and r["kind"] == "week") for w in weeks}
        files = {w: _run_file("main", lr[w]["job"]) for w in weeks}
        if tag == "BL0a":
            ovf = [lr[w]["bl0a_usd"] for w in weeks]
            tot = [files[w]["instances"]["base"]["references"]["bl0a_total_usd"] for w in weeks]
            want = [f"{_fmt(np.median(ovf) / 1e3, 1)} ({_fmt(np.median(tot) / 1e3, 1)})", _fmt(0.0, 1),
                    _fmt(np.median([next(r["bl0a_usd"] for r in gap if r["cell"] == c) / second["gap_lp"][c]
                                    for c in gap_cells]), 2), "--", _fmt(1.0, 3), "--"]
            assert cells == want, (tag, cells, want)
            continue
        r0 = [lr[w]["r0"] for w in weeks]
        ovf = [lr[w]["r0"] * lr[w]["bl0a_usd"] for w in weeks]
        tot = [next(r for r in files[w]["runs"] if r["mode"] == "L-tr")["accountings"]["total_usd"] for w in weeks]
        assert cells[0] == f"{_fmt(np.median(ovf) / 1e3, 1)} ({_fmt(np.median(tot) / 1e3, 1)})", tag
        assert cells[1] == _fmt(np.median([100 * (1 - x) for x in r0]), 1), tag
        if tag in NO_GAP:
            assert cells[2] == "--", tag
        else:
            assert cells[2] == _fmt(np.median([second["gap_ratio"][f"{tag}:{c}:0"] for c in gap_cells]), 2), tag
        assert cells[3] == _fmt(np.median([main["RC"][tag]["L-tr"][w]["0"] for w in weeks]), 3), tag
        assert cells[4] == _fmt(np.median([main["W0"]["0"][tag][w] for w in weeks]), 3), tag
        per = sorted((cross[tag][w] for w in p_weeks), key=lambda x: np.inf if x is None else x)
        low = per[(len(per) + 1) // 2 - 1]
        reach = min(max(p for p, r in curves[tag][w]["points"] if r is not None) for w in p_weeks)
        want_p = _fmt(low, 2) if low is not None else ("none" if reach >= top else f"$>${reach:g}")
        assert cells[5] == want_p, (tag, cells[5], want_p)


def test_caption_note_and_scope(written):
    _, tex, ext = written
    d = ext["data"]
    main, ana = _tree("main/summary.json"), _tree("analysis.json")
    m = re.search(r"\\caption\{(.*?)\}\n\\label\{tab:e7\}", _body(tex), re.S)
    assert m and m.group(1) == d["caption"]
    assert r"\parbox{\columnwidth}{\footnotesize\raggedright " + d["note"] + "}" in tex
    assert d["labels"]["caption"] == d["caption"] + " " + d["note"]
    full = d["labels"]["caption"]
    weeks = sorted({r["cell"] for r in main["runs"] if r["kind"] == "week"})
    gs, guarded = main["guard_summary"], main["guarded"]
    assert ("confirmation week" in d["caption"]) and "trace lender" in d["caption"] and "full menu" in d["caption"]
    assert r"$\mu/\tilde\beta=1$" in d["caption"] and "policy seed" not in d["caption"]                       # C52
    assert all(w in d["caption"] for w in weeks)
    note = d["note"]
    # C52 (T1 glossary G5, G6): Section VI's name, the cap by the paper's macro \Wk, no "kappa none"
    assert r"Guarded rows: per-group allowance $\min\{\Wk,\mathrm{LB}'\}$." in note                          # C52
    assert "W_k" not in note and r"\kappa" not in note                                                       # C52
    assert r"\providecommand{\Wk}{B_{\mathrm{peak}}}" in tex                                                 # C52
    assert r"\newcommand{\Wk}{B_{\mathrm{peak}}}" in MACROS.read_text(encoding="utf-8")                      # C52
    cases = {c: sum(1 for g in guarded if g["case"] == c) for c in ("W(a)", "W(b)", "W(c)")}
    n_modes = len({g["mode"] for g in guarded})
    # C47 (design/ms6_spec.md M7): Theorem W is Theorem~\ref{thm:fullmodel}, its cases W(a) and W(b) the parts (a) and
    # (b); W(c), a conjecture after the theorem in the text, is "the conjectured case", printed only where it has runs
    # (U46, second review: the theorem has no part (c))
    # C50 (D5 review): the modes by Section VII's lenders, every mode of the confirmation
    assert n_modes == len(t3.m5b.conf_modes())                                                         # C50
    # C52 (T1 scan): "bound" (the certificate checks Theorem 16's parts; "envelope" is Theorem 12's)
    assert (f"Theorem~\\ref{{thm:fullmodel}}'s bound held in {gs['held']} of {gs['n_runs']} guarded runs (trace, "
            f"five stress and honoring lenders; " in note) and "lender modes" not in note                  # C50; C52
    assert "envelope" not in note                                                                          # C52
    with pytest.raises(t3.MissingKey):                                                                   # C50
        t3.modes_text(n_modes - 1)
    want = [f"{c[1:]} {n}" for c, n in cases.items() if c != "W(c)"] + (
        [f"the conjectured case {cases['W(c)']}"] if cases["W(c)"] else [])
    assert "cases " + ", ".join(want) + ")" in note                                          # C47: (a) 382, (b) 66
    assert t3.cases_text({"W(a)": 1, "W(b)": 2, "W(c)": 0}) == "cases (a) 1, (b) 2"
    assert t3.cases_text({"W(a)": 1, "W(b)": 2, "W(c)": 3}) == "cases (a) 1, (b) 2, the conjectured case 3"
    # the count covers every guarded run of part main: the legacy row without a row here is named with its runs
    rows = {t for t, _ in t3.ROWS}
    legacy = sorted({g["tag"] for g in guarded} - rows)
    assert legacy == ["Sublet-MS4"]
    # C47 (design/ms6_spec.md M7): the MS4 configuration's allowance "($B_0$ = 10% of All-fallback)", where its
    # registry label (C41, unchanged) writes "($B_0=10\%$ BL0a)"; no "BL0a" in the note
    # C52 (T1 glossary G4, G12): "of the all-fallback bill", the main text's name of the configuration, and no "the
    # supplement's"
    lab = re.sub(r"\$([^$]*)\$", r"\\mbox{$\1$}", t3.note_label(style.POLICIES["sublet_ms4"].label, t3.FB_BILL))
    # C59 (RC19(3)): the registry label writes the allowance in words itself, so note_label leaves it as it is (the
    # versioned float, rewritten from its extract, keeps C52's "(\mbox{$B_0$}~=~10\% of the all-fallback bill)")
    assert lab == r"Lagged RetroRenting + one-way guard (\mbox{$B_0=10\%$} of the all-fallback bill)"           # C59
    assert f"; {sum(g['tag'] == 'Sublet-MS4' for g in guarded)} of {lab}; cases (a)" in note                    # C52
    assert "the supplement's" not in note                                                                    # C52
    assert "BL0a" not in note and "BL0a" not in d["caption"]
    # G3(b) through Corollary G3' only for the guarded rows around A9 (design §2.6; Table II v2 gives BL1-GP none)
    g3 = [t for t, _ in t3.ROWS if any(g["tag"] == t for g in guarded) and main["meta"]["tags"][t]["a9_family"]]
    assert g3 == ["Sublet", "Sublet-1way"]
    # C47 (design/ms6_spec.md M7, M14): G3(b) and Corollary G3' are Corollary~\ref{cor:ratio}
    # C50 (D5 review, statements S2): the bound holds on core instances only, not for these runs; C51: its shortest form
    assert ("; Corollary~\\ref{cor:ratio}(b) holds for Sublet and Sublet, one-way, on core instances "
            "(Lemma~\\ref{lem:projection}(e));" in note) and "Greedy + guard, on core" not in note        # C50; C51
    assert "rests on" not in note                                                                          # C50
    # C47 (M7, M17): no design name of a result and no experiment ID in the caption draft; C47 (print check of the
    # gate): nor an experiment-derived name such as the menu base "e7r" (the ID test is case-insensitive)
    assert not re.search(r"Theorem W|G3\(b\)|G3\$'\$|\bW\([abc]\)|\bE\d+[a-z]?\b", d["labels"]["caption"], re.I)
    assert d["caption"].startswith("End-to-end cost per policy, ")              # the fixture has one week
    lender = {_run_file("main", r["job"])["lender_models"]["L-tr"]["schedule"] for r in main["runs"]
              if r["tag"] == "Sublet" and r["mode"] == "L-tr" and r["kind"] == "week"}
    assert lender == {"trace"} and d["caption_source"]["lender"] == "trace"
    one = [g for g in guarded if g["tag"] == "Sublet-1way"]
    assert f"Sublet, one-way aborted in {sum(g['aborted'] for g in one)} of {len(one)} runs" in note
    # its aborts under the trace lender, read from main.guarded (mode L-tr), with its cost there (print check of U38)
    tr = sorted((g for g in one if g["mode"] == "L-tr" and g["aborted"]), key=lambda g: g["cell"])
    ta = d["caption_source"]["trace_aborts"]["Sublet-1way"]
    assert ta["weeks"] == [g["cell"] for g in tr]
    assert ta["t_a"] == [min(g["t_a"] for g in tr), max(g["t_a"] for g in tr)]
    r0 = [main["table"]["Sublet-1way"]["L-tr"][g["cell"]]["0"] for g in tr]
    assert ta["r0_aborted"] == [min(r0), max(r0)]
    assert f"(under the trace lender in {len(tr)} of {len(weeks)} week" in note
    for tag in ana["H2"]["set"]:                          # labels with their math boxed (no line break inside)
        key = dict(t3.ROWS).get(tag) or t3.CAPTION_ONLY[tag]
        assert re.sub(r"\$([^$]*)\$", r"\\mbox{$\1$}", style.POLICIES[key].label) in note, tag
    # C52 (T1 glossary G3): Section VII-C's "the primary baselines", defined as the policies this note lists
    assert "RetroRenting-style, lagged (supplement)" in note and "Primary baselines (H1):" in note           # C52
    assert "H1's set" not in note                                                                          # C52
    assert "H2b" not in note                            # C51: Section VII's "Pre-registered outcomes" reports H2b
    bl0b = [_run_file("main", r["job"])["instances"]["base"]["references"] for r in main["runs"]
            if r["tag"] == "Sublet" and r["mode"] == "L-tr" and r["kind"] == "week"]
    ratio = np.median([x["bl0b_overflow_usd"] / x["bl0a_usd"] for x in bl0b])
    # C47 (print check of the gate, U46; M11): a normalized cost "times the all-fallback bill", not "times All-fallback"
    assert f"Provision for peak: {ratio:.1f} times the all-fallback bill in overflow accounting." in note      # C47
    assert "All-fallback" not in note and "of the all-fallback bill)" in note                     # C47: M7; C52: G12
    zero = [t for t in d["order"] if d["rows"][t]["cells"]["p_star"]["value"] == 0.0]
    assert d["caption_source"]["p_zero_rows"] == zero and zero          # the fixture has rows with p* = 0
    assert "(0.00: $r_0>1$ already without reclaims; none:" in note and "$p=0$: no reclaim" not in note
    # C47 (M17, print check of the gate): the gap's menu by its name, "reduced", not MS4's base name e7r
    # C50 (D5 review): Section VII's words for the gap reruns: 5-min routing, the LP bound, the ratio to the optimum
    assert "every baseline" not in full and "reduced menu" in note and "e7r" not in full                    # C50
    assert ("(5-min routing, reduced menu) over the LP bound, an upper bound on the ratio to the offline optimum."
            in note) and "slow grid" not in note and "merged" not in note and "on the gap" not in note      # C50
    assert t3.grid_text("slow") == "5-min routing"                                                        # C50
    scope = d["tables"]["table3_v2.tex"]["scope"]
    assert scope["tags"] == [t for t, _ in t3.ROWS] and scope["keys"] == list(ROW_KEYS)
    assert scope["cells"] == weeks and scope["seeds"] == [0]
    assert scope["modes"] == ["L-tr", "L-eg", "L-ss", "L-iid-0.05", "L-iid-0.2", "L-co", "L-hon"]
    assert scope["gap_cells"] == sorted({r["cell"] for r in _tree("second/summary.json")["runs"] if r["kind"] == "gap"})
    assert d["meta"]["reduced"] is True and d["meta"]["git_revision"] == main["meta"]["git_revision"]


def test_caption_h2b_counts_on_real_shaped_input():
    """caption_parts on caption numbers of the confirmation's shape: no H2b sentence even with H2b failing (C51), the
    lagged BL5 pointed to the supplement, H1's set in the rows' order, three-point-grid readings."""
    cap = copy.deepcopy(json.loads((FIX / "table3_v2.json").read_text())["data"]["caption_source"])
    cap.update(weeks=[str(w) for w in range(301, 317)], n_weeks=16)
    cap["h2b"].update({"n_weeks": 16, "below_1": 16, "pass": False})
    cap["h2b"]["not_below_weeks"] = {"BL5-tau60": ["302", "307", "309"], "BL1-GP": [], "BL1N": [], "BL5N": []}
    cap["h2b"]["equal_weeks"] = {p: [] for p in cap["h2b"]["set"]}
    title, note = t3.caption_parts(cap)
    assert title.startswith("End-to-end cost per policy, medians of 16 confirmation weeks (301--316;")    # C47: M17
    assert "H2b" not in note and "3 of 16 weeks" not in note                                              # C51
    head = "Primary baselines (H1):"                                                                      # C52: G3
    order = note[note.index(head):note.index(".", note.index(head) + 30)]                                  # C52
    assert order.index("Greedy renting") < order.index("RetroRenting-style;") < order.index("CoCaR-style")
    assert order.endswith("RetroRenting-style, lagged (supplement)")


def test_trace_abort_text_on_real_shaped_input():
    """The note's account of a guarded row that aborts under the trace lender (print check of U38: Sublet one-way's
    medians mix its 6 aborted weeks, at all-fallback's cost, with 10 weeks at Sublet's cost): weeks, cost (C51: "the
    all-fallback bill" where r0 prints 1.000, no slots), and the rest at Sublet's cost or within a distance of it; no
    text for a row without such aborts; no '0.00' reading without a row whose p* is 0."""
    cap = copy.deepcopy(json.loads((FIX / "table3_v2.json").read_text())["data"]["caption_source"])
    cap.update(weeks=[str(w) for w in range(301, 317)], n_weeks=16, p_zero_rows=[])
    cap["aborts"] = {"Sublet": [0, 112], "Sublet-1way": [42, 112], "BL1-GP": [0, 112]}
    cap["trace_aborts"] = {"Sublet-1way": {
        "weeks": ["301", "306", "309", "311", "313", "316"], "n_weeks": 16, "t_a": [0, 22],
        "r0_aborted": [0.9999952, 1.0], "other_weeks": ["302", "303", "304", "305", "307", "308", "310", "312",
                                                         "314", "315"], "other_max_abs_diff_to_Sublet": 0.0}}
    _, note = t3.caption_parts(cap)
    assert ("Sublet, one-way aborted in 42 of 112 runs (under the trace lender in 6 of 16 weeks, at the all-fallback "
            "bill; in the rest at Sublet's cost); Sublet and Greedy + guard in none.") in note           # C47; C51
    assert "slots" not in note and "mix" not in note                                                     # C51
    assert "0.00:" not in note and "($p=0$" not in note
    cap["trace_aborts"]["Sublet-1way"].update(t_a=[5, 5], r0_aborted=[0.98, 1.0], other_max_abs_diff_to_Sublet=2e-4)
    _, note = t3.caption_parts(cap)
    assert ("6 of 16 weeks, at 0.980--1.000 times the all-fallback bill; in the rest within 0.0002 of Sublet's "
            "cost") in note                                                                           # C47: U46; C51
    cap["trace_aborts"] = {}
    _, note = t3.caption_parts(cap)
    assert "Sublet, one-way aborted in 42 of 112 runs; Sublet and Greedy + guard in none." in note


def test_writer_refuses_reduced_input_in_paper_and_honors_the_pdf_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("SUBLET_FIGS_IN_ROOT", str(IN_ROOT))
    monkeypatch.setenv(style.ENV_OUT_DIR, str(tmp_path / "out"))
    monkeypatch.delenv(style.ENV_PDF_DIR, raising=False)
    monkeypatch.setattr(t3, "FLOATS_DIR", tmp_path / "paper_floats")
    with pytest.raises(SystemExit, match="reduced"):
        t3.main([])
    assert not (tmp_path / "paper_floats").exists()
    with pytest.raises(SystemExit, match="reduced"):
        t3.main(["--from-extract", str(FIX / "table3_v2.json")])
    monkeypatch.setenv(style.ENV_PDF_DIR, str(tmp_path / "pdf"))         # a scratch build or a test
    rep = t3.main(["--from-extract", str(FIX / "table3_v2.json")])
    assert Path(rep["tex"]) == tmp_path / "pdf" / "table3_v2.tex" and not (tmp_path / "paper_floats").exists()


def test_from_extract_rewrites_the_same_float(written):
    tmp, tex, ext = written
    rep = t3.main(["--from-extract", str(tmp / "out" / "table3_v2.json"), "--out", str(tmp / "again")])
    assert (tmp / "again" / "table3_v2.tex").read_text(encoding="utf-8") == tex
    assert json.loads((tmp / "out" / "table3_v2.json").read_text()) == ext
    assert rep["data"]["caption"] == ext["data"]["caption"]


def test_build_on_the_input_tree_matches_the_fixture(monkeypatch):
    """build() opens only result files of the input root (patched open), equals the fixture extract's data, and lists
    every run file it read with the file's sha256 (W10)."""
    monkeypatch.setenv("SUBLET_FIGS_IN_ROOT", str(IN_ROOT))
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
    data = t3.build(inp)
    monkeypatch.undo()
    for p in opened:
        if REPO in p.parents:
            assert IN_ROOT in p.parents, f"opened {p}"
            style.check_source(p.relative_to(IN_ROOT).as_posix())
    data = json.loads(json.dumps(data, allow_nan=False, default=json_number))
    sources = data.pop("sources")
    fixture = json.loads((FIX / "table3_v2.json").read_text())
    assert data == fixture["data"], STALE
    assert fixture["sources"] == sources == inp.sources
    runs = {s for s in sources if "/runs/" in s}
    assert runs and runs == set(data["runs_sha256"])
    for rel, sha in data["runs_sha256"].items():
        assert hashlib.sha256((IN_ROOT / rel).read_bytes()).hexdigest() == sha, rel


def test_formats_and_helpers():
    assert t3.tex_value(None, 2) == "--" and t3.tex_value(-5.376, 1) == "$-$5.4" and t3.tex_value(-0.0004, 3) == "0.000"
    assert t3.lower_median([0.8, None, 1.0, None]) == 1.0 and t3.lower_median([None, None, 0.0, 0.0]) == 0.0
    assert t3.lower_median([0.34, 0.8, 0.8, 0.5]) == 0.5 and t3.lower_median([None, 0.5, None, None]) is None
    assert t3.weeks_text(["302", "301", "303"]) == "weeks 301--303" and t3.weeks_text(["101"]) == "week 101"
    assert t3.horizon_text(1440) == "day" and t3.horizon_text(120) == "120 min"


# ---------------------------------------------------------------------------------------------------------------
# Table II v2
def _has_words(tex: str, phrase: str) -> bool:
    """`phrase` occurs in `tex` up to whitespace, line breaks and ties (~)."""
    return re.search(r"(?:\s|~)+".join(re.escape(w) for w in phrase.split()), tex) is not None


def _name(key) -> str:
    if key is None:
        return "Revocable-only"
    if key == "a1":                         # C52: Table II v2 sets ALG* as ALG$^\ast$
        return ALG_STAR
    return LEGACY_NAMES.get(key) or style.POLICIES[key].label


def _norm_c3(s: str) -> str:
    return _ws(s.replace("`", "").replace("′", "'").replace("–", "--"))


def _norm_tex(s: str) -> str:
    s = re.sub(r"\{\\fontfamily\{cmtt\}\\selectfont\s+([^}]*)\}", r"\1", s)
    s = s.replace("$'$", "'").replace("`", "'").replace(r"\_", "_")
    return _ws(s)


def _c3_heading(src: str, ident: str) -> str:
    """'ID (body)' of C3 §9's bold heading of a result, with its balanced parentheses."""
    i = src.index(f"**{ident} (")
    j, depth = i + len(f"**{ident} ("), 1
    while depth:
        depth += (src[j] == "(") - (src[j] == ")")
        j += 1
    return src[i + 2:j]


def _t2_text(cell: str) -> str:
    """C49: a cell's text; a full-width row's without its \\multicolumn{2}{<spec>} wrapper."""
    m = re.match(r"^\\multicolumn\{2\}\{(?:[^{}]|\{[^{}]*\})*\}\s*\{(.*)\}$", cell.strip(), re.S)
    return m.group(1) if m else cell


def _t2_key(cell: str) -> str:
    """C49: a row's first name, without its italic label, its rule and the marks $^N$ and $^P$."""
    text = re.sub(r"^\\textit\{[^}]*\}\s*", "", _t2_text(cell).strip())
    return _ws(re.split(r"[;:]", text)[0].replace("$^N$", "").replace("$^P$", ""))


def _statements() -> dict:
    """C49: {label: (environment, statement)} of the theorem-like environments of Sections IV-VI (STATEMENT_FILES),
    comments removed. C58: and those of the seven results moved to the supplement (MOVED_FILES), by their slugs."""
    moved = {e["slug"] for f in sorted(SUPP_RESULTS.glob("*.json"))  # C58
             for e in json.loads(f.read_text(encoding="utf-8"))["results"] if e.get("ms6_number") is not None}  # C58
    assert len(moved) == 7, moved  # C58
    out = {}
    for d, files, keep in ((SECTIONS, STATEMENT_FILES, None), (SUPP_SECTIONS, MOVED_FILES, moved)):  # C58
        for f in files:  # C58
            src = _body((d / f).read_text(encoding="utf-8"))  # C58
            for m in re.finditer(r"\\begin\{(theorem|lemma|proposition|corollary|conjecture)\}(.*?)\\end\{\1\}", src,
                                 re.S):  # C58
                lab = re.search(r"\\label\{([^}]*)\}", m.group(2))
                if lab and (keep is None or lab.group(1) in keep):  # C58
                    out[lab.group(1)] = (m.group(1), m.group(2))
    assert moved <= set(out), sorted(moved - set(out))  # C58: every moved result is typeset where §1.3 puts it
    return out


def _t2_part_problem(part: str, statements: dict, frozen: set):
    """C49: why a guarantee part breaks the rule (None if it keeps it): a part that cites results cites statements of
    Sections IV-VI (PROVEN by M10); a part with a status word and no result equals a whole guarantee part of the frozen
    Table II (`frozen`, normalized), so with its scope (A3's); every other part is "none" or "may abort".
    C52 (design/ms7/plan.md §4, T1 glossary G9): a part that cites results carries no status word (as built under C49,
    PROVEN at its end); no part prints an all-caps status word; A3's part writes its status in plain words, ", numerically
    verified", which reads as the frozen " VERIFIED NUMERICALLY" (never upgraded: "proven" does not)."""
    refs = re.findall(r"\\ref\{([^}]*)\}", part)
    words = STATUS_WORD.findall(part)
    plain = PLAIN_STATUS.findall(part)  # C52
    if refs:
        if not all(statements.get(lab, ("",))[0] in PROVEN_ENVS for lab in refs):
            return "cites a result that is not a statement of Sections IV-VI"
        if words or plain:  # C52
            return "a cited result with a status word"  # C52
        return None
    if words:  # C52
        return "an all-caps status word"  # C52
    if plain:  # C52
        # C50: A3's scope in plain words (design/sim_spec_ms2.md §7.5) reads as the frozen "in reference mode only";
        # C52: its status in plain words as the frozen all-caps label
        p = re.sub(r",\s*numerically verified\b", " VERIFIED NUMERICALLY",
                   _ws(part).replace(A3_SCOPE_WORDS, A3_SCOPE_FROZEN))  # C52
        return None if _norm_tex(p) in frozen else "a status word not copied from the frozen Table II"  # C50; C52
    return None if _ws(part) in ("none", "may abort") else "a part without a result or a status word"


def test_table2_v2_rows_cover_every_policy_of_the_main_text():
    """Every policy that a main-text figure or table draws or names is a row of Table II v2.
    C49 (design/ms6_spec.md §8, D6: the scopes live with the statements in Sections IV-VI; the table cites results by
    label): a one-column float; the rows "Policy: rule" with a Guarantee cell, then the full-width rows; the
    information class of before is a mark on the name, and the note defines only the marks."""
    t = _body((FLOATS / "table2_policies_v2.tex").read_text(encoding="utf-8"))
    assert r"\begin{table}[t]" in t and r"\begin{table*}" not in t and r"\label{tab:policies}" in t     # C49
    rows = _rows(t)
    assert len(rows) == len(TABLE2_ROWS)
    assert [len(r) for r in rows] == [2] * TABLE2_GUARANTEED + [1] * (len(rows) - TABLE2_GUARANTEED)     # C49
    for row, keys in zip(rows, TABLE2_ROWS):
        assert all(_has_words(row[0], _name(k)) for k in keys), (keys, row[0])
    names = " ".join(r[0] for r in rows)
    need = {k for f in MAIN_FIGURES for k in style.FIGURE_POLICIES[f]} | set(ROW_KEYS) | {"a9", "bl5_lag"}
    missing = [k for k in sorted(need) if not _has_words(names, _name(k))]
    assert not missing, missing
    assert "fig4" not in MAIN_FIGURES                                     # the frozen MS4 Fig. 4 is not in it (W6)
    by = {_t2_key(r[0]): r for r in rows}                                                             # C49
    # C49: the class I1+N of before is the mark $^N$ on each name it applies to (the guarded rows and A2 with the
    # theory r-bar), I2 the mark $^P$ (Marking); the note defines both, and private reclaim information otherwise
    marked = [_ws(n) for r in rows for n in re.findall(r"([^;:]+?)\$\^N\$", _t2_text(r[0]))]          # C49
    assert marked == ["Sublet", "Sublet, one-way", "Greedy + guard", "Lagged RetroRenting + one-way guard",  # C49
                      "Greedy + one-way guard", "PD heuristic + one-way guard", r"A2, theory~$\bar{r}$"]   # C49
    assert [_ws(n) for r in rows for n in re.findall(r"([^;:]+?)\$\^P\$", _t2_text(r[0]))] == ["Marking"]  # C49
    note = _ws(t[t.index(r"\parbox"):t.index(r"\end{table}")])                                       # C49
    assert "Unmarked: private information; $^P$public; $^N$with the a-priori bound $N$." in note and len(note) < 120  # C52
    # C47 (design/ms6_spec.md M7): G3(b) is Corollary~\ref{cor:ratio}; Greedy + guard is not given it
    assert "may abort" in _ws(by["Sublet, one-way"][1]) and r"\ref{cor:ratio}" not in by["Greedy + guard"][1]  # C49
    # C49: the guarded rows at Sublet's allowance name it in their rule ("as Sublet"), the one-way guards of the
    # frozen figures Algorithm 1's original allowance; no allowance mark, dagger or note mark is left; C52 (T1 glossary
    # G5): that allowance is "the per-LLM allowance"
    assert "as Sublet" in by["Sublet, one-way"][0] and "as Sublet" in by["Greedy + guard"][0]           # C49
    assert "at the per-LLM allowance" in _ws(by["Lagged RetroRenting + one-way guard"][0])            # C52
    assert "original allowance" not in _ws(t)                                                         # C52
    assert not re.search(r"\$\^(?:\\S|\\P|\\dagger)\$", t)                                              # C49


def test_table2_v2_cites_results_by_label_with_status_word():
    """C49 (design/ms6_spec.md §8, D6): the scopes live with the statements in Sections IV-VI; the table cites results
    by label. Replaces test_table2_v2_status_labels_are_copied_with_scope, which pinned the long note that copied the
    C3 §9 headings, W_AB and the pre-registration's scopes: the caption says that each result holds with the scope its
    statement gives; every cited result is a theorem, lemma, proposition or corollary of Sections IV-VI (PROVEN by
    M10, its scope in its statement) and each part that cites one carries PROVEN; the C3 §9 headings and W_AB keep
    their labels where their paper results are stated (never strengthened: an upgraded or wrongly labeled part
    fails); the only status word without a result (A3's) is copied from the frozen Table II with its scope; and each
    row cites the results of TABLE2_REFS."""
    t = _body((FLOATS / "table2_policies_v2.tex").read_text(encoding="utf-8"))
    cap = _ws(t[t.index(r"\caption{"):t.index(r"\label{tab:policies}")])
    assert "each result holds with the scope its statement gives" in cap                              # C49
    st = _statements()
    frozen = {_norm_tex(p) for r in _rows((FLOATS / "table2_policies.tex").read_text(encoding="utf-8"))
              for p in r[3].split(";")}                                                               # C49
    rows = _rows(t)
    guaranteed = rows[:TABLE2_GUARANTEED]
    parts = [p.strip() for r in guaranteed for p in r[1].split(";")]
    bad = [(p, _t2_part_problem(p, st, frozen)) for p in parts if _t2_part_problem(p, st, frozen)]
    assert not bad, bad                                                                               # C49
    assert any("numerically verified " + A3_SCOPE_WORDS in _ws(p) for p in parts)                     # C52: A3's
    assert not any("reference mode" in _ws(p) for p in parts)                                          # C50
    assert not STATUS_WORD.search(t)                                                    # C52: no all-caps status word
    for right in (r"real cost ${\le}\,2\times$ accounted, numerically verified " + A3_SCOPE_WORDS,       # C52
                  r"Theorem~\ref{thm:fullmodel}", "none", "may abort"):                                  # C52
        assert _t2_part_problem(right, st, frozen) is None, right                                       # C52
    # C49: an upgraded label, a weakened one, a result outside Sections IV-VI and an uncopied claim are caught; C52: and
    # an all-caps status word, a cited result with a status word, and a plain status word that upgrades or drops A3's
    for wrong in (r"real cost ${\le}\,2\times$ accounted PROVEN in reference mode only",
                  r"real cost ${\le}\,2\times$ accounted PROVEN " + A3_SCOPE_WORDS,                       # C50
                  r"real cost ${\le}\,2\times$ accounted VERIFIED NUMERICALLY with cold re-buys",          # C50
                  r"real cost ${\le}\,2\times$ accounted VERIFIED NUMERICALLY",
                  r"real cost ${\le}\,2\times$ accounted VERIFIED NUMERICALLY " + A3_SCOPE_WORDS,           # C52
                  r"real cost ${\le}\,2\times$ accounted, proven " + A3_SCOPE_WORDS,                       # C52
                  r"real cost ${\le}\,2\times$ accounted, numerically verified",                           # C52
                  r"Theorem~\ref{thm:fullmodel} CONJECTURE", r"Theorem~\ref{thm:fullmodel} PROVEN",         # C52
                  r"Theorem~\ref{thm:fullmodel}, proven",                                                  # C52
                  r"Theorem~\ref{thm:fullmodel} PROVEN VERIFIED NUMERICALLY",
                  r"Section~\ref{sec:sublet}", r"Corollary~\ref{cor:missing}",                           # C52
                  "PROVEN on everything", "proven on everything"):                                         # C52
        assert _t2_part_problem(wrong, st, frozen), wrong
    # C49: the C3 §9 headings are PROVEN, and the paper result of each (PAPER_NAMES) is a statement of Section VI;
    # Theorem W(a)(b) (PROVEN under C1-C3) is Theorem~\ref{thm:fullmodel}, whose statement names C1--C3, and W(c)
    # (CONJECTURE) the conjecture after it, which the table does not claim
    src = C3.read_text(encoding="utf-8")
    for ident in C3_HEADINGS:
        h = _norm_c3(_c3_heading(src, ident))
        assert "PROVEN" in h and "CONJECTURE" not in h, ident                                        # C49
        lab = re.search(r"\\ref\{([^}]*)\}", PAPER_NAMES[ident]).group(1)
        assert st[lab][0] in PROVEN_ENVS, (ident, lab)                                              # C49
    assert "Theorem W(a)(b) (PROVEN for the engine as implemented under C1-C3" in ms3_claims.W_AB          # C49
    assert "W(c) (CONJECTURE)" in ms3_claims.W_AB and "C1--C3" in st["thm:fullmodel"][1]               # C49
    sub = _body((SUPP_SECTIONS / "s_d.tex").read_text(encoding="utf-8"))  # C58: thm:fullmodel is in S-D.4 now
    assert re.search(r"[Cc]onjecture", sub[sub.index(r"\label{thm:fullmodel}"):])                     # C49
    assert "(a)" in st["cor:ratio"][1] and "(b)" in st["cor:ratio"][1]                                 # C49
    # C49: the note no longer copies the scopes (they are in the statements)
    for gone in ("12.66", "wind-down tie tolerance", "core instances", "three float hypotheses", "its extension"):
        assert gone not in t, gone
    # C47: each row's guarantee cell cites exactly the results of the map of design/ms6/inventory_consistency.md
    # §2.4, in order (a substring check alone cannot tell "Theorem 3(a) PROVEN" from the start of "... on the family");
    # C49: with Corollary~\ref{cor:ratio}'s part, and no full-width row cites a result
    cited = {_t2_key(r[0]): ["".join(m) for m in re.findall(r"\\ref\{([^}]*)\}((?:\([a-z]\))*)", r[1])]
             for r in guaranteed}
    for name, want in TABLE2_REFS.items():
        assert cited[name] == want, (name, cited[name])
    assert not any(v for k, v in cited.items() if k not in TABLE2_REFS), cited
    assert not any(r"\ref" in r[0] for r in rows)                                                    # C49
    # C47 (U46, second review): Theorem~\ref{thm:fullmodel} is always cited whole (it has (a) and (b), and no (c))
    assert not re.search(r"\\ref\{thm:fullmodel\}\(", t)
    # C47 (design/ms6_spec.md M7): the cells name results only by \ref; the paper's labels of §5
    assert not DESIGN_NAMES.search(t), DESIGN_NAMES.findall(t)
    # C47 (M11, print check of the gate): no policy design ID but A2 and A3, which the table uses as names
    assert not re.findall(r"\bA(?:[14-9]|8P)\b|\bBL\d", t), re.findall(r"\bA(?:[14-9]|8P)\b|\bBL\d", t)
    stub = LABELS.read_text(encoding="utf-8")
    assert set(re.findall(r"\\ref\{([^}]*)\}", t)) <= set(re.findall(r"\\newlabel\{([^}]*)\}", stub))


@pytest.mark.parametrize("name", MAIN_TEXT_FLOATS)  # C47
def test_c47_main_text_floats_print_no_audit_word_and_no_contribution_id(name):  # C47
    """C47 (print check of the gate, U46): the main-text floats print neither "audited" nor "numerically checked" (M10:
    the supplement's mapping table lists them; the status labels themselves are kept), no Proj with a subscript (M12:
    theta is critical-ratio renting's theta_c), and no contribution ID C1-C7 (M11): only Theorem 16's conditions, as
    "C1--C3" or "C1 of Theorem~\\ref{thm:fullmodel}" (consistency §1.2, row C_S). Table III v2 is written by its
    script; its versioned float is checked here, the writer's own note in test_caption_note_and_scope.
    C49 (design/ms6_spec.md §8, D6: the scopes live with the statements in Sections IV-VI; the table cites results by
    label): Table II v2 no longer prints Lemma 11's heading, so Proj(E) and "numerically verified under deterministic
    floating point" are not pinned in it; ALG*'s rule is read from its "Policy: rule" cell."""
    t = _body((FLOATS / name).read_text(encoding="utf-8"))  # C47
    assert not MAIN_TEXT_FORBIDDEN.search(t), MAIN_TEXT_FORBIDDEN.findall(t)                         # C47
    assert not STATUS_WORD.search(t), STATUS_WORD.findall(t)                     # C52 (T1 glossary G9): no all caps
    ids = [m.group(0) for m in CONTRIB_ID.finditer(t)]  # C47
    assert all(i in ("C1--C3", "C1 of Theorem") for i in ids), ids                                 # C47
    if name == "table2_policies_v2.tex":  # C47
        rule = {_t2_key(r[0]): _ws(_t2_text(r[0]).split(":", 1)[1]) for r in _rows(t)}[ALG_STAR]  # C49; C52
        assert rule == "single-site notice rule"                                                   # C47, C49
        assert "numerically verified" in t                                     # C52: A3's status kept, in plain words

# ---------------------------------------------------------------------------------------------------------------
# Algorithm 1 v2
def test_algorithm1_v2_ladder_and_allowance():
    t = _body((FLOATS / "alg1_guard_v2.tex").read_text(encoding="utf-8"))
    assert r"\begin{figure}[t]" in t and r"\textbf{Algorithm 1}" in t and r"\footnotesize" in t
    assert not re.search(r"\\(usepackage|begin)\{(algorithm|algorithmic|algorithm2e|algpseudocode)", t)
    lines = re.findall(r"\\algl\{(\d+)\}", t)
    assert lines == [str(i) for i in range(1, len(lines) + 1)] and 12 <= len(lines) <= 18
    # C52 (T1 glossary G6): the cap W_k by the paper's macro \Wk, which the float provides as paper/macros.tex defines it
    assert r"\providecommand{\Wk}{B_{\mathrm{peak}}}" in t and "W_k" not in t                              # C52
    assert r"\newcommand{\Wk}{B_{\mathrm{peak}}}" in MACROS.read_text(encoding="utf-8")                   # C52
    for s in ("Sublet: $E$ is critical-ratio renting", r"Sublet's allowance $B(t)=\min\{\Wk(t),\mathrm{LB}'(t)\}$",  # C52
              r"any nondecreasing online allowance $B(t)$", "FB: all-fallback",
              # C47 (design/ms6_spec.md M7, M12): the doubling combination Comb of FB and PD, defined in the note
              r"S=\mathrm{Comb}_{\gamma'}(\mathrm{FB},\mathrm{PD})", "PD: the rounded primal-dual expert",
              r"$\mathrm{Comb}_{\gamma'}$: their doubling combination",
              r"\textbf{for} $Y$ in $A_E(t)$, P1, P0, K0 \textbf{do} \hfill(candidate ladder)",
              r"\hat a_Y\leftarrow\mathrm{ALG}(t-1)+p_Y+\mathrm{rent}_Y+G_Y+\Sigma_Y", "(test T0g)",
              r"\textbf{if} $\hat a_Y+R_Y\le\gamma C_S(t)+B(t)$ \textbf{then} execute $Y$; \textbf{next} $t$",
              r"$t_a\leftarrow t$; discard $A_E(t)$; mode $\leftarrow$ S \hfill(no candidate passed: abort)",
              r"$n'=n_b-1$, $\lfloor n_b/2\rfloor$,", r"$\lfloor n_b/4\rfloor$, 1 in turn", "$0<n'<n_b$",
              "P0: $A_E(t)$ without purchases", "K0: release every held lease", "adaptive wind-down",
              r"$\beta(K)=G+\Sigma+\mathrm{rent}-Q+R$", r"(Lemma~\ref{lem:onlinelb})",          # C47: M7
              # C47 (print check of the gate): line 12's "bound form" defined in the note, as C3 §9 defines it
              r"T0g's bound form: C1 of Theorem~\ref{thm:fullmodel} holds, no counted purchase or load was refused "
              r"other than as unavailable, and no counted lease ended early."):
        assert _ws(s) in _ws(t), s
    assert not DESIGN_NAMES.search(t), DESIGN_NAMES.findall(t)                                     # C47: M7
    # the ladder's order and P1's sizes are those of ProjectedGuarded.candidates
    code = (SIM / "sublet" / "algos" / "guard.py").read_text(encoding="utf-8")
    cand = code[code.index("    def candidates("):code.index("    def _evaluate(")]
    assert cand.index('("E", acts') < cand.index('("P1"') < cand.index('("P0"') < cand.index('("K0"')
    assert "{nb - 1, nb // 2, nb // 4, 1} - {0, nb}" in cand
    order = [t.index(x) for x in ("$A_E(t)$, P1, P0, K0", "(no candidate passed: abort)",
                                  r"$t>t_a$ \textbf{then}")]
    assert order == sorted(order)
    frozen = _body((FLOATS / "alg1_guard.tex").read_text(encoding="utf-8"))
    line = r"\\algl\{%d\}\{(\d)\}\{(.*?)\}\s*\n(?=\\algl|\\vspace)"
    def unbox(x):          # a box that keeps math on one line, a line set ragged right in a group of its own
        x = re.sub(r"\\mbox\{(\$[^$]*\$)\}", r"\1", _ws(x))
        return re.sub(r"^\{\\raggedright (.*)\\par\}$", r"\1", x)
    for i in range(9, 15):                                                 # mode S and the wind-down, unchanged
        old, new = re.search(line % i, frozen, re.S), re.search(line % (i + 1), t, re.S)
        assert old and new and old.group(1) == new.group(1), i
        # C47 (design/ms6_spec.md M7; consistency C-3): line 12's adaptive wind-down condition gains T0g's bound form
        want = unbox(old.group(2))
        if i == 11:
            want = want.replace("if $S$ follows FB", "if T0g is in its bound form and $S$ follows FB")
            assert want != unbox(old.group(2))
        assert unbox(new.group(2)) == want, i
    # C47: the condition is Guarded._wind_down's: every held lease is released (K0) when T0gBound is in its robust form
    wd = code[code.index("    def _wind_down("):code.index("    def _commit_wind_down(")]
    assert wd.index("if tb.robust:") < wd.index('why = "robust"') < wd.index('sx.followed != "FB"')


# ---------------------------------------------------------------------------------------------------------------
# ms5b_deviations.tex
def _prereg_items() -> dict:
    text = PREREG.read_text(encoding="utf-8")
    sec = text[text.index("## 7. Deviations and clarifications"):text.index("## 8. The gates")]
    out, block = {}, None
    for line in sec.splitlines():
        m = re.match(r"^\*([A-E])\. ", line)
        if m:
            block = m.group(1)
            continue
        m = re.match(r"^(\d+)\. (.*)$", line)
        if m and block:
            out[f"{block}{m.group(1)}"] = m.group(2)
    listed = re.search(r"reported in the paper with their reasons: (.*?)\. The other items", sec, re.S).group(1)
    return out, re.findall(r"\b([A-E]\d+)\b", listed)


def _md_plain(s: str) -> str:
    s = re.sub(r"`([^`]*)`", r"\1", s)
    s = re.sub(r"(?<![\\$])\*([^*]+?)\*", r"\1", s)
    return _ws(s.replace("′", "'"))


def _dev_plain(s: str) -> str:
    def code(m):
        return m.group(1).replace(r"\_", "_").replace(r"\{", "{").replace(r"\}", "}")
    s = re.sub(r"\\devcode\{((?:[^{}]|\\[{}])*)\}", code, s)
    s = re.sub(r"\\emph\{([^{}]*)\}", r"\1", s)
    s = s.replace(r"\S{}", "§").replace(r"\_", "_").replace(r"\#", "#").replace(r"\%", "%").replace(r"\&", "&")
    s = s.replace("``", '"').replace("''", '"').replace("`", "'").replace("--", "–").replace("$'$", "'")
    return _ws(s)


# C58 (design/ms7/w_spec.md W-D8, D3 of design/ms7/plan.md): the table states each registered item in the paper's
# names, without the copy's process records; the verbatim items stay in the pre-registration (its §7), which this test
# still reads. The rule checked: the seven registered items, in the registration's order, one row each, no design ID.
DEVIATION_ROWS = ("H3's abort clause", "Refuting the no-abort proposition", "Runs that H3's endpoint selects",
                  "Allowance of the guarded comparison rows", "RetroRenting + notice layer as built",
                  "Empty demand in critical-ratio renting", "Hypotheses of the no-abort proposition")
DESIGN_IDS = re.compile(r"\b(?:A8P?|A9(?:\.\d)?|BL\d[A-Za-z0-9-]*|Sublet-1way|Sublet-MS4|C3 §9|P\d|U\d\d)\b")


def test_deviations_table_equals_the_preregistration():
    items, listed = _prereg_items()
    assert tuple(listed) == DEVIATION_ITEMS                          # the registration still lists the seven items
    assert all(items[i].strip() for i in DEVIATION_ITEMS)
    rows = _rows(DEVIATIONS.read_text(encoding="utf-8"))
    assert [r[0] for r in rows] == list(DEVIATION_ROWS)
    assert len(DEVIATION_ROWS) == len(DEVIATION_ITEMS)
    for r in rows:
        text = _dev_plain("&".join(r[1:]))
        assert len(text.split()) >= 20, r[0]                         # each row states its item and its reason
        assert not DESIGN_IDS.search(text), (r[0], DESIGN_IDS.search(text).group(0))
    tex = _body(DEVIATIONS.read_text(encoding="utf-8"))
    assert r"\begin{table*}[t]" in tex and r"\label{tab:ms5b-deviations}" in tex


# ---------------------------------------------------------------------------------------------------------------
# Compilation and heights
def _compile(tmp_path: Path, folder: Path, name: str) -> str:
    # C47: with the label stub (design/ms6_spec.md M7), so that the floats' \ref print their numbers
    doc = ("\\documentclass[journal]{IEEEtran}\\usepackage{booktabs}\\usepackage{array}\n\\input{labels_stub.tex}\n"
           f"\\begin{{document}}\n\\input{{{name}.tex}}\nText.\n\\end{{document}}\n")
    (tmp_path / "doc.tex").write_text(doc)
    env = dict(os.environ, TEXINPUTS=f"{LAYOUT}:{folder}:{LABELS.parent}:")
    r = subprocess.run([str(PDFLATEX), "-interaction=nonstopmode", "-halt-on-error", "doc.tex"], cwd=tmp_path,
                       capture_output=True, text=True, env=env, timeout=300)
    log = (tmp_path / "doc.log").read_text(errors="replace")
    assert r.returncode == 0 and (tmp_path / "doc.pdf").is_file(), log[-2000:]
    return log


def _clean(log: str) -> None:
    assert "Overfull" not in log, [l for l in log.splitlines() if "Overfull" in l]
    assert "LaTeX Error" not in log and "Float too large" not in log and "not loadable" not in log
    assert "LaTeX Warning: Reference" not in log, [l for l in log.splitlines() if "Reference" in l]     # C47


@pytest.mark.skipif(not PDFLATEX.is_file(), reason=f"{PDFLATEX} is not installed")
@pytest.mark.parametrize("path", [FLOATS / "table2_policies_v2.tex", FLOATS / "alg1_guard_v2.tex", DEVIATIONS],
                         ids=lambda p: p.stem)
def test_hand_set_floats_compile(tmp_path, path):
    _clean(_compile(tmp_path, path.parent, path.stem))


@pytest.mark.skipif(not PDFLATEX.is_file(), reason=f"{PDFLATEX} is not installed")
def test_table3_v2_compiles_also_at_real_scale(written):
    """The float from the fixture, and from its extract with every cell at a real-scale width (USD in hundreds of
    thousands, a negative saving, a negative RC, W0 above 1, p*'s widest reading), without an overfull box."""
    tmp, _, ext = written
    (tmp / "c1").mkdir()
    _clean(_compile(tmp / "c1", tmp / "floats", "table3_v2"))
    big = copy.deepcopy(ext)
    for r in big["data"]["rows"].values():
        for col, text in zip(COLUMNS, ("135.0 (402.1)", "$-$71.7", "2.19", "$-$0.012", "1.565", "$>$0.2")):
            r["cells"][col]["text"] = text
    (tmp / "big.json").write_text(json.dumps(big))
    t3.main(["--from-extract", str(tmp / "big.json"), "--out", str(tmp / "bigfloats")])
    (tmp / "c2").mkdir()
    _clean(_compile(tmp / "c2", tmp / "bigfloats", "table3_v2"))


@pytest.mark.skipif(not PDFLATEX.is_file(), reason=f"{PDFLATEX} is not installed")
def test_v2_floats_are_measured(written):
    """floats_heights.measure with BUDGETS_MS5B on Table III v2 (from the fixture) and the two hand-set v2 floats, each
    next to its budget (informative; W11's FL-1)."""
    tmp, _, _ = written
    for name in ("table2_policies_v2", "alg1_guard_v2"):
        shutil.copy(FLOATS / f"{name}.tex", tmp / "floats" / f"{name}.tex")
    sys.path.insert(0, str(LAYOUT / "pageplan"))
    try:
        import floats_heights as fh
    finally:
        sys.path.remove(str(LAYOUT / "pageplan"))
    (tmp / "heights").mkdir()
    rep = fh.measure(fh.BUDGETS_MS5B, workdir=tmp / "heights", floats_dir=tmp / "floats")
    assert list(rep["floats"]) == list(fh.BUDGETS_MS5B)
    for name, v in rep["floats"].items():
        assert 0 < v["measured_pages"] < 1 and v["budget_pages"] == fh.BUDGETS_MS5B[name], name
        assert v["within_budget"] == (v["measured_pages"] <= v["budget_pages"] + 1e-9)
    assert rep["labels"]["file"] == "paper/generated/labels_stub.tex"           # C47: measured with the label stub
