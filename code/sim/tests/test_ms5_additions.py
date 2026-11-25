"""Tests of the MS5 additions C27-C32 to MS1-MS4 files (design/sim_spec_ms5.md §2.3, §10), and of C33's two lines of
tests/test_ms4_additions.py with and without the MS5 additions.

- C27 (engine.py): on configs/toy.json with BL5 and with A6, and with BL5 on the toy with 1-min routing (T_fast =
  5 T_slow, so that the two counts differ), RunResult.runtime holds the MS1 and MS2 keys in their order and after them
  reset_s, slow_step_s_sum, slow_step_s_max, n_slow_steps, fast_step_s_sum, fast_step_s_max, n_fast_steps, check_s and
  finish_s; n_slow_steps = T_slow and n_fast_steps = T_fast; the sums (math.fsum) and maxima equal those of the steps
  the engine recorded (Engine.rt), and the MS1 percentiles come from the same lists; reset_s <= policy_s; check_s lies
  within the fast steps; the two step sums with reset_s and finish_s are at most wall_s; and the run's components,
  schedule hash and events equal a digest stored from the same run on engine.py before C27 (C27_DIGESTS, measured on
  the engine of commit c82fa05f, the last commit before C27, and rechecked on that engine loaded beside the edited
  one). Delays inserted into the policy's reset, the online checks and the policy's report (run by _finish) show up
  in reset_s, check_s and finish_s and in no step sum; with the checks off check_s is 0 and the digest is the same.
- C28 (figs/print_sheet.py): two builds from copies of the same main-text figure PDFs in two temporary folders, at two
  different times and from two working folders, give byte-identical sheets with no trailer /ID; the cover's second
  line is "Built by code/sim/figs/print_sheet.py from the main-text figures, inputs sha256 <16 hex digits>", the digest
  recomputed from the sorted lines "<figure> <sha256>"; no page holds a date, a time or an absolute path; the record
  keeps 'written' and the input paths; a changed figure PDF changes the digest and the sheet (skipped without
  PyMuPDF; tests/test_figs_ms3.py::test_print_sheet and tests/test_ms4_additions.py's C22 test run unchanged).
- C29 (figs/style.py): SUPP_POLICIES_MS5 names sf_s1, sf_e9 and sf_slack with their §7 sets, every set passes
  check_policies; lb is the registry's computed lower bound (black, dashed); the registry keys and the MS3 and MS4
  maps (FIGURE_POLICIES, SUPP_POLICIES, SUPP_ONLY_KEYS, SUPP_POLICIES_MS4, SUPP_ONLY_KEYS_MS4) keep their MS4 values
  (C47: but for the sets that the MS6 gate's C46 moves to the configuration keys, design/ms6_spec.md M2, M4); the
  three figures are registered at their §7 sizes, which tests/test_figs_style.py's SUPP_SIZES_IN_USE covers.
- C30 (experiments/ms3_common.py): check_copy("s1") on a fake clone with the parts sweep and q28 in the drivers' shape
  passes with its tree digests and fails, with the path named, when one part lacks summary.json; E9's single folder
  passes with no part; the map's E6 and E7 entries are unchanged.
- C31 (conftest.py): needs_ms5_out on a temporary root, as a helper and in a pytest run of probe tests in a
  subprocess: a test whose file is missing is skipped, one whose file is present runs, a marker without arguments
  skips on an empty folder, the MS3 and MS4 roots do not count, and the quick suite's expression deselects them all.
- C32 (.gitignore): the three runs/ lines of S1 and E9.
- C33 (tests/test_ms4_additions.py): its C17 test (the copied tree counts 29 plus the MS5 scripts present) passes on a
  checkout without and with sf_s1, sf_e9 and sf_slack, and its C20 test (the copy-part map restricted to E6 and E7)
  with and without C30's entry.
"""
from __future__ import annotations

import copy
import dataclasses
import datetime
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import time
import types
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
import pytest

from fixtures import SIM, toy_config

import test_ms4_additions as t4
from sublet.config import rng_streams
from sublet.experiments import ms3_common as mc

REPO = SIM.parents[1]
FIG_DIR = REPO / "paper" / "figures"


# ---------------------------------------------------------------- C27: the engine's loop sums, setup and finish
C27_SEED = 7                      # config, lender and policy seed of the toy runs (toy.json's config seed)
MS2_RUNTIME_KEYS = ("wall_s", "slow_step_s_p50", "slow_step_s_p99", "fast_step_s_p50", "fast_step_s_p99",
                    "routing_s", "routing_lp_s", "routing_lp_calls", "policy_s", "peak_rss_mb", "policy_act_s_mean",
                    "policy_act_s_p50", "policy_act_s_p99", "policy_act_s_max", "n_alive_leases_max")
C27_KEYS = ("reset_s", "slow_step_s_sum", "slow_step_s_max", "n_slow_steps", "fast_step_s_sum", "fast_step_s_max",
            "n_fast_steps", "check_s", "finish_s")
# The runs on engine.py before C27 (commit c82fa05f): sha256 of the components and of the events (as JSON, through
# metrics._jsonable, sorted keys), the schedule hash of q44_study.schedule_hash and the number of events
C27_DIGESTS = {
    "BL5": {"components": "7f4dbcf4ce062220c5bad1f378a19d0e2388b3c95592e61a2496bc140ac625ae",
            "schedule_hash": "99ae7856873112367c745fe3679cade8bf908781b0962f3f8a05f578a673d049",
            "events": "92eaaef55830471667b4cf52162473a2ef82c9e54c5b1179d1baf625dfa2d42b", "n_events": 14},
    "A6": {"components": "c8d6804c8bf0ce0f267b83ab0f9a3e262ccbaff43b162f90df5b2a2c999f1bf5",
           "schedule_hash": "99ae7856873112367c745fe3679cade8bf908781b0962f3f8a05f578a673d049",
           "events": "6ae66f5f18b45bfc765a75da555a2cf017560ed392e3f49cbb92e1f9292414d6", "n_events": 18},
    "BL5_fast": {"components": "7f4dbcf4ce062220c5bad1f378a19d0e2388b3c95592e61a2496bc140ac625ae",
                 "schedule_hash": "99ae7856873112367c745fe3679cade8bf908781b0962f3f8a05f578a673d049",
                 "events": "ff97f40163109012f8ec05e02f1f92e442fc710d23d959f3a76ec5f87e6eb6e1", "n_events": 14},
}


def _toy_fast() -> dict:
    """toy.json with 1-min routing (fast slot 1 min on 5-min slow slots), as tests/test_run_spec.py builds it."""
    cfg = toy_config()
    cfg["time"]["fast_slot_min"] = 1
    vals = cfg["borrowers"]["clients"][0]["demand"]["values"]
    cfg["borrowers"]["clients"][0]["demand"]["values"] = [float(v) for v in np.repeat(vals, 5)]
    return cfg


C27_CASES = {"BL5": ("BL5", "toy.json"), "A6": ("A6", "toy.json"), "BL5_fast": ("BL5", _toy_fast)}


def _toy_engine(case: str, check_invariants: bool = True, wrap=None):
    """(engine, result, instance) of one C27 run: what engine.simulate does with lender and policy seed C27_SEED,
    keeping the Engine so that its recorded steps (Engine.rt) can be read; `wrap(engine, policy)` may replace
    methods by instance attributes before the run."""
    from sublet.drivers.run import build, load_run_spec, make_policy
    from sublet.engine import Engine
    from sublet.lender import Lender
    pid, src = C27_CASES[case]
    spec = load_run_spec({"schema_version": 1, "name": f"c27_{case}", "instance": src() if callable(src) else src,
                          "policy": {"id": pid, "params": {}}})
    inst, model, ecfg = build(spec, C27_SEED)
    assert ecfg.check_invariants                      # MS5 spec §0 item 5
    if not check_invariants:
        ecfg = dataclasses.replace(ecfg, check_invariants=False)
    pol = make_policy(spec, inst)
    streams = rng_streams(C27_SEED)
    eng = Engine(inst, Lender(inst, model, streams["lender"]), pol, ecfg, streams["policy"])
    if wrap is not None:
        wrap(eng, pol)
    return eng, eng.run(), inst


def _sha_json(obj) -> str:
    from sublet.metrics import _jsonable
    return hashlib.sha256(json.dumps(_jsonable(obj), sort_keys=True, allow_nan=False).encode()).hexdigest()


def _run_digest(res) -> dict:
    from sublet.experiments.q44_study import schedule_hash
    return {"components": _sha_json(dict(res.components)), "schedule_hash": schedule_hash(res.schedule),
            "events": _sha_json([[m, typ, payload] for m, typ, payload in res.events]), "n_events": len(res.events)}


@pytest.mark.parametrize("case", list(C27_CASES))
def test_c27_runtime_keys(case, tmp_path):
    """The new keys after the MS1 and MS2 keys; the counts equal the grid; the sums and maxima equal those of the
    recorded steps; reset_s <= policy_s; check_s within the fast steps; the parts at most wall_s; the run equal to the
    stored digest of the run before C27; write_run copies the keys into the run file."""
    from sublet.metrics import write_run
    eng, res, inst = _toy_engine(case)
    rt = res.runtime
    assert res.invariant_failures == []
    assert tuple(rt) == MS2_RUNTIME_KEYS + C27_KEYS
    slow, fast = eng.rt["slow"], eng.rt["fast"]
    assert rt["n_slow_steps"] == len(slow) == inst.grid.T_slow == 24
    assert rt["n_fast_steps"] == len(fast) == inst.grid.T_fast == (120 if case == "BL5_fast" else 24)
    assert rt["slow_step_s_sum"] == math.fsum(slow) and rt["slow_step_s_max"] == max(slow)
    assert rt["fast_step_s_sum"] == math.fsum(fast) and rt["fast_step_s_max"] == max(fast)
    assert (rt["slow_step_s_p50"], rt["slow_step_s_p99"]) == (float(np.percentile(slow, 50)),
                                                              float(np.percentile(slow, 99)))
    assert (rt["fast_step_s_p50"], rt["fast_step_s_p99"]) == (float(np.percentile(fast, 50)),
                                                              float(np.percentile(fast, 99)))
    assert all(isinstance(rt[k], float) for k in C27_KEYS if not k.startswith("n_"))
    assert all(type(rt[k]) is int for k in ("n_slow_steps", "n_fast_steps"))
    assert 0.0 <= rt["reset_s"] <= rt["policy_s"]
    assert 0.0 < rt["check_s"] <= rt["fast_step_s_sum"]
    assert rt["finish_s"] >= 0.0
    parts = rt["slow_step_s_sum"] + rt["fast_step_s_sum"] + rt["reset_s"] + rt["finish_s"]
    assert parts <= rt["wall_s"] + 1e-9, (parts, rt["wall_s"])
    assert _run_digest(res) == C27_DIGESTS[case]
    write_run(res, inst, tmp_path / "run.json")
    disk = json.loads((tmp_path / "run.json").read_text())["runtime"]
    assert list(disk) == list(rt) and all(disk[k] == rt[k] for k in C27_KEYS)


def test_c27_intervals():
    """Each new time measures its own interval: 0.03 s slept in the policy's reset, 2 ms in each online check and
    0.03 s in the policy's report (which _finish calls) show up in reset_s, check_s and finish_s (each also in
    policy_s, a fast step and nothing else, respectively), and the run's digest is unchanged. With the online checks
    off, check_s is 0.0 and the digest is the same."""
    sleep_reset, sleep_check, sleep_report = 0.03, 0.002, 0.03

    def wrap(eng, pol):
        reset, check, report = pol.reset, eng._check_fast, getattr(pol, "report", None)

        def slow_reset(*args):
            time.sleep(sleep_reset)
            return reset(*args)

        def slow_check(*args):
            time.sleep(sleep_check)
            return check(*args)

        def slow_report():
            time.sleep(sleep_report)
            return report() if callable(report) else {}
        pol.reset, eng._check_fast, pol.report = slow_reset, slow_check, slow_report
    eng, res, inst = _toy_engine("BL5", wrap=wrap)
    rt = res.runtime
    assert res.invariant_failures == [] and _run_digest(res) == C27_DIGESTS["BL5"]
    assert sleep_reset <= rt["reset_s"] <= rt["policy_s"]
    assert inst.grid.T_fast * sleep_check <= rt["check_s"] <= rt["fast_step_s_sum"]
    assert rt["finish_s"] >= sleep_report
    assert rt["slow_step_s_max"] < sleep_reset and rt["fast_step_s_max"] < sleep_report  # in neither step sum
    parts = rt["slow_step_s_sum"] + rt["fast_step_s_sum"] + rt["reset_s"] + rt["finish_s"]
    assert parts <= rt["wall_s"] + 1e-9
    eng, res, _ = _toy_engine("BL5", check_invariants=False)
    assert res.runtime["check_s"] == 0.0 and tuple(res.runtime) == MS2_RUNTIME_KEYS + C27_KEYS
    assert _run_digest(res) == C27_DIGESTS["BL5"]


# ---------------------------------------------------------------- C28: the deterministic print sheet
COVER_LINE = "Built by code/sim/figs/print_sheet.py from the main-text figures, inputs sha256 "


def _figure_pdfs() -> list[Path]:
    from figs import print_sheet
    return [FIG_DIR / f"{n}.pdf" for n in print_sheet.main_figures() if (FIG_DIR / f"{n}.pdf").is_file()]


def _sheet(monkeypatch, pdfs: dict, top: Path, now: datetime.datetime) -> tuple[dict, bytes]:
    """Build the sheet from copies of `pdfs` (figure -> source PDF) in top/in, into top/out, with the clock at `now`
    and top as the working folder; (record, sheet bytes)."""
    from figs import print_sheet, style as st
    fig_dir, out_dir = top / "in", top / "out"
    fig_dir.mkdir(parents=True)
    for n, p in pdfs.items():
        shutil.copy(p, fig_dir / f"{n}.pdf")
    monkeypatch.setenv(st.ENV_PDF_DIR, str(fig_dir))
    monkeypatch.setenv(st.ENV_OUT_DIR, str(out_dir))
    monkeypatch.chdir(top)

    class Clock(datetime.datetime):
        @classmethod
        def now(cls, tz=None):
            return now
    monkeypatch.setattr(print_sheet, "datetime", types.SimpleNamespace(datetime=Clock))     # print_sheet's clock only
    rep = print_sheet.main([])
    assert Path(rep["pdf"]) == out_dir / "print_check.pdf"
    return rep, Path(rep["pdf"]).read_bytes()


def _digest_lines(pdfs: dict) -> str:
    """The oracle of C28: sha256 of the sorted lines '<figure> <sha256>', each ending in a newline."""
    lines = sorted(f"{n} {hashlib.sha256(Path(p).read_bytes()).hexdigest()}" for n, p in pdfs.items())
    return hashlib.sha256("".join(f"{ln}\n" for ln in lines).encode()).hexdigest()


def test_c28_print_sheet_is_deterministic(tmp_path, monkeypatch):
    """Two builds from copies of the versioned main-text figure PDFs in two folders, a year apart and from two
    working folders, are byte-identical, with no trailer /ID; the cover names the inputs' digest and no date, time or
    folder; every included figure keeps its page; the record keeps 'written' (each build's time) and the input
    paths."""
    fitz = pytest.importorskip("fitz")
    from figs import print_sheet
    src = _figure_pdfs()
    if not src:
        pytest.skip(f"no main-text figure PDF in {FIG_DIR}")
    pdfs = {p.stem: p for p in src}
    a, b = tmp_path / "a", tmp_path / "deeper" / "b"
    rep_a, sheet_a = _sheet(monkeypatch, pdfs, a, datetime.datetime(2026, 10, 29, 12, 33, 4))
    rep_b, sheet_b = _sheet(monkeypatch, pdfs, b, datetime.datetime(2027, 11, 30, 1, 2, 3))
    assert sheet_a == sheet_b
    assert (rep_a["written"], rep_b["written"]) == ("2026-10-29T12:33:04", "2027-11-30T01:02:03")
    assert [r["file"] for r in rep_a["included"]] == [str(a / "in" / f"{n}.pdf") for n in pdfs]
    assert [r["file"] for r in rep_b["included"]] == [str(b / "in" / f"{n}.pdf") for n in pdfs]
    assert [r["figure"] for r in rep_a["included"]] == list(pdfs)
    assert rep_a["skipped"] == [n for n in print_sheet.main_figures() if n not in pdfs]
    digest = _digest_lines(pdfs)
    assert print_sheet.inputs_digest({n: hashlib.sha256(p.read_bytes()).hexdigest() for n, p in pdfs.items()}) \
        == digest
    with fitz.open(stream=sheet_a, filetype="pdf") as doc:
        assert "/ID" not in doc.pdf_trailer()
        assert doc.page_count == 1 + len(pdfs)
        cover_text = doc[0].get_text()
        cover = cover_text.splitlines()
        assert cover[1] == COVER_LINE + digest[:16]
        assert cover[0] == "Sublet main-text figures: print check at 100% (US letter)"
        text = "\n".join(page.get_text() for page in doc)       # the figure pages also hold the figures' texts
    assert not re.search(r"\d{4}-\d{2}-\d{2}|\d{1,2}:\d{2}", cover_text)    # no date, no time on the cover
    assert not re.search(r"(^|[\s(])/", cover_text, re.M)                     # no absolute path on the cover
    assert str(tmp_path) not in text and str(REPO) not in text and "/tmp/" not in text


def test_c28_changed_figure_changes_the_digest(tmp_path, monkeypatch):
    """A changed figure PDF (the main-text figure fig1 replaced by another valid PDF) changes the digest on the cover
    and the sheet; the digest follows the inputs alone."""
    fitz = pytest.importorskip("fitz")
    src = _figure_pdfs()
    if len(src) < 2:
        pytest.skip(f"fewer than two main-text figure PDFs in {FIG_DIR}")
    pdfs = {p.stem: p for p in src[:2]}
    first, second = list(pdfs)
    changed = {**pdfs, first: pdfs[second]}
    _, sheet_a = _sheet(monkeypatch, pdfs, tmp_path / "a", datetime.datetime(2026, 10, 29, 12, 0, 0))
    _, sheet_b = _sheet(monkeypatch, changed, tmp_path / "b", datetime.datetime(2026, 10, 29, 12, 0, 0))
    da, db = _digest_lines(pdfs), _digest_lines(changed)
    assert da != db and sheet_a != sheet_b
    for sheet, d in ((sheet_a, da), (sheet_b, db)):
        with fitz.open(stream=sheet, filetype="pdf") as doc:
            assert doc[0].get_text().splitlines()[1] == COVER_LINE + d[:16]


# ---------------------------------------------------------------- C29: the MS5 registry maps and sizes
# §2.3, C29; C47: sublet_ms4 in the frozen sublet's place, since S1 and E9 ran at MS4's allowance (C46,
# design/ms6_spec.md M2, M4)
MS5_SETS = {"sf_s1": ("sublet_ms4",), "sf_e9": ("sublet_ms4", "a6", "lb"), "sf_slack": ()}
MS5_SIZES = {"sf_s1": ("W2", 2.5), "sf_e9": ("W2", 2.2), "sf_slack": ("W2", 2.5)}           # §7.1-§7.3
MS4_POLICY_KEYS = ("sublet", "sublet_siloed", "a7_guard", "bl1_guard", "a7", "a6", "a6_siloed", "a6_red_off",
                   "a6_always2", "psi_01", "psi_03", "psi_05", "a2_frac", "a2_r1", "a2_theory", "a3", "a3_rot", "a4",
                   "a5", "rr_renew", "marking", "a1", "bl5", "bl1", "bl2", "bl3_n0", "bl3_n1", "bl3", "bl4",
                   "prewarm", "cold", "bl6", "bl0a", "bl0b", "opt", "opt_eager", "lb")
# C47: fig3 and fig5 with C46's configuration keys of Algorithm 1's defaults in place of the legacy keys
# (design/ms6_spec.md M2, M3, M4); the frozen fig1 and fig4 keep theirs
MS4_FIGURE_POLICIES = {
    "fig1": ("sublet",), "fig2": (),
    "fig3": ("bl5_g1", "a7_g1", "bl1_g1", "a7", "a6", "bl5_lag", "bl1", "bl2"),                          # C47
    "fig4": ("sublet", "sublet_siloed", "a7_guard", "a7", "a6", "a6_siloed", "bl5", "bl1", "bl2", "bl4", "bl0a",
             "bl0b", "opt"),
    "fig5": ("bl5_g1", "a2_frac", "a2_r1", "a2_theory", "a3", "rr_renew"),                               # C47
    "fig6": ("rr_renew", "a2_theory", "marking"),
    "fig7": ("a1", "prewarm", "bl6")}
# C47: the figures of MS4's allowance with sublet_ms4 (its siloed runs in the sharing line style), bl5_lag and a7_ms4
# (the guard around A7 at that allowance; C46, review of the gate), and sf_e7_allow, whose axis sweeps B0, with bl5_g1
# (C46, design/ms6_spec.md M2, M3, M4)
MS4_SUPP_POLICIES_MS4 = {
    "sf_e3_util": ("sublet_ms4", "a6", "a6_siloed", "bl2", "bl5_lag"),                                    # C47
    "sf_e3_mu": ("sublet_ms4", "a6", "a6_siloed", "bl2", "opt"),                                          # C47
    "sf_e4": ("psi_01", "psi_03", "psi_05", "a2_frac", "a5"),
    "sf_e5": ("sublet_ms4", "a6_red_off", "a6", "a6_always2", "bl3_n0", "bl3_n1", "bl3"),                 # C47
    "sf_e7_mix": ("sublet_ms4", "a7_ms4", "a7", "a6", "bl5_lag", "bl1", "bl2", "bl4"),                    # C47
    "sf_e7_mu": ("sublet_ms4", "a7_ms4", "a7", "a6", "bl5_lag", "bl1", "bl2", "bl4"),                     # C47
    "sf_e7_allow": ("bl5_g1", "bl5_lag"), "sf_e8": ()}                                                    # C47


def test_c29_ms5_sets_and_sizes():
    """SUPP_POLICIES_MS5 holds the three §7 figures with their sets, each within the registry and passing
    check_policies; lb is the computed lower bound (black, dashed line, benchmark); the registry keys and every MS3
    and MS4 map keep their MS4 values; sf_s1, sf_e9 and sf_slack are registered as supplementary figures at their §7
    sizes, each covered by tests/test_figs_style.py's SUPP_SIZES_IN_USE, and a script registers them again at the
    same size only."""
    from figs import style as st
    from test_figs_style import SUPP_SIZES_IN_USE
    assert st.SUPP_POLICIES_MS5 == MS5_SETS and tuple(st.SUPP_POLICIES_MS5) == ("sf_s1", "sf_e9", "sf_slack")
    for name, keys in st.SUPP_POLICIES_MS5.items():
        assert len(set(keys)) == len(keys) and set(keys) <= set(st.POLICIES), name
        st.check_policies(keys)
    lb = st.POLICIES["lb"]
    assert (lb.label, lb.color, lb.marker, lb.fill, lb.linestyle, lb.group) == \
        ("Lower bound", "#000000", None, "line", "--", "benchmark")
    # no key is new; the MS3 and MS4 maps are unchanged (tests/test_ms3_additions.py and test_ms4_additions.py fix them)
    # C45: C41 inserts the MS5b keys and fig4v2's set (design/sublet_v2.md §11, W7, W12); the earlier keys keep their
    # order and the earlier sets their values
    # C47: and C46's MS6 keys and fig1v2's set (design/ms6_spec.md M1, M3)
    assert tuple(k for k in st.POLICIES if k not in st.MS5B_KEYS and k not in st.MS6_KEYS
                 and k not in st.MS7_KEYS                                                  # C58: and MS7's keys
                 and k not in st.MS7_SUPP_KEYS                                             # C58 (W-G4)
                 and k not in st.MS8_SUPP_KEYS) == MS4_POLICY_KEYS                         # MS8
    assert {k: v for k, v in st.FIGURE_POLICIES.items()
            if k not in ("fig4v2", "fig1v2", "fig1v3", "fig4v3")} == MS4_FIGURE_POLICIES  # C58: fig1v3, fig4v3
    assert st.SUPP_POLICIES == t4.MS3_SUPP_POLICIES and st.SUPP_ONLY_KEYS == ("a3_rot", "cold")
    assert st.SUPP_POLICIES_MS4 == MS4_SUPP_POLICIES_MS4 and st.SUPP_ONLY_KEYS_MS4 == tuple(t4.WANT_KEYS)
    assert not set(st.SUPP_POLICIES_MS5) & (set(st.SUPP_POLICIES) | set(st.SUPP_POLICIES_MS4) | set(st.FIGURE_POLICIES))
    for name, (width, height) in MS5_SIZES.items():
        spec = st.FIGURES[name]
        assert (spec.width, spec.height_in, spec.main) == (width, height, False), name
        assert (width, height) in SUPP_SIZES_IN_USE, name
        assert st.register_supplementary(name, width, height) == spec
        with pytest.raises(st.StyleError, match="already registered"):
            st.register_supplementary(name, width, 2.4)
    # C45: C41 registers fig4v2 as a main-text figure (design/sublet_v2.md §11, W1); C47: C46 fig1v2 (design/ms6_spec.md
    # M1)
    assert sorted(k for k, s in st.FIGURES.items() if s.main) == sorted([f"fig{i}" for i in range(1, 8)] +
                                                                         ["fig4v2", "fig1v2", "fig1v3",
                                                                          "fig4v3"])    # C58: fig4v3


# ---------------------------------------------------------------- C30: the copy check of S1's two parts
S1_PARTS = ("sweep", "q28")


def test_c30_check_copy_s1_parts(tmp_path):
    """S1's folder with the parts sweep and q28 (each with its manifest, job records, run log and summary) passes,
    with tree_sha256 = tree_digest of the copy and the clone and tree_sha256_versioned leaving out each part's runs/;
    a part without summary.json fails summary_ok with that part's file named. E9's one folder passes with no part. The
    map's E6 and E7 entries are unchanged."""
    assert mc.COPY_PARTS["s1"] == S1_PARTS and "e9" not in mc.COPY_PARTS
    assert {k: mc.COPY_PARTS[k] for k in ("e6", "e7")} == {"e6": ("a", "b"), "e7": t4.E7_PARTS}

    def build(top):
        for part in S1_PARTS:
            t4._write_part(top / part, "s1", part)
    root, clone = t4._clone_with(tmp_path / "s1", "s1", build)
    copy_dir = root / "out" / "s1"
    res = mc.check_copy("s1", clone, root)
    assert res["pass"] is True and all(res["checks"].values()), res["checks"]
    assert res["parts"] == list(S1_PARTS) and res["n_files_copy"] == 2 * (len(t4._part_files("s1", "sweep")) + 3)
    assert {p: x["file"] for p, x in res["run_logs"].items()} == {p: f"{p}/run_s1.log" for p in S1_PARTS}
    assert res["manifest_git_revision"] == {p: t4.COMMIT for p in S1_PARTS}
    assert {p: s["file"] for p, s in res["summaries"].items()} == {p: f"{p}/summary.json" for p in S1_PARTS}
    assert res["no_revision_by_kind"] == {f"{p}/jobs": 1 for p in S1_PARTS}
    assert res["tree_sha256"] == mc.tree_digest(copy_dir) == mc.tree_digest(clone / "code" / "sim" / "out" / "s1")
    assert res["tree_sha256_versioned"] == mc.tree_digest(copy_dir, "s1") != res["tree_sha256"]
    assert mc._unversioned("s1", "sweep/runs/c=1/x.json") and mc._unversioned("s1", "q28/runs/c=1/x.json")
    assert not mc._unversioned("s1", "q28/jobs/x.json") and not mc._unversioned("s1", "sweep/summary.json")
    assert json.loads((root / "out" / "ms3_copy_s1.json").read_text())["pass"] is True
    t4._both(root, clone, "s1", lambda top: (top / "q28" / "summary.json").unlink())
    res = mc.check_copy("s1", clone, root)
    assert res["pass"] is False and [k for k, v in res["checks"].items() if not v] == ["summary_ok"]
    assert res["summaries"]["q28"]["file"] == "q28/summary.json" and res["summaries"]["q28"]["exists"] is False
    assert res["summaries"]["sweep"]["ok"] is True
    # E9 has one folder: no part, its run log at the top
    root9, clone9 = t4._clone_with(tmp_path / "e9", "e9", lambda top: t4._write_part(top, "e9", ""))
    res = mc.check_copy("e9", clone9, root9)
    assert res["pass"] is True and res["parts"] == [] and res["run_logs"]["e9"]["file"] == "run_e9.log"
    assert mc._unversioned("e9", "runs/pt=x/y.json") and not mc._unversioned("e9", "summary.json")


# ---------------------------------------------------------------- C31: the marker needs_ms5_out
def test_c31_needs_ms5_out_helper(tmp_path, monkeypatch):
    """conftest._ms5_out_missing (as _ms4_out_missing, C19): the named files missing under MS5_OUT_DIR, and the folder
    itself when a marker has no argument (alone or beside markers with files) and the folder is missing or empty."""
    import conftest
    out = tmp_path / "code" / "sim" / "out"
    monkeypatch.setattr(conftest, "MS5_OUT_DIR", out)
    assert conftest._ms5_out_missing([]) == [str(out)]
    assert conftest._ms5_out_missing(["s1/sweep/summary.json"]) == ["s1/sweep/summary.json"]
    out.mkdir(parents=True)
    assert conftest._ms5_out_missing([]) == [str(out)]
    assert conftest._ms5_out_missing(["e9/summary.json"], folder=True) == [str(out), "e9/summary.json"]
    (out / "e9").mkdir()
    (out / "e9" / "summary.json").write_text("{}")
    assert conftest._ms5_out_missing(["e9/summary.json"], folder=True) == [] and conftest._ms5_out_missing([]) == []
    assert conftest.MS4_OUT_DIR != out and conftest.MS3_OUT_DIR != out     # the MS3 and MS4 markers keep their roots
    assert conftest.MS5_OUT_ROOT == Path(os.environ.get("SUBLET_MS5_OUT_ROOT") or REPO)


PROBE_TESTS = '''
import pytest


@pytest.mark.needs_ms5_out("s1/sweep/summary.json")
def test_present():
    pass


@pytest.mark.needs_ms5_out("e9/summary.json")
def test_missing():
    pass


@pytest.mark.needs_ms5_out()
def test_folder():
    pass


@pytest.mark.needs_ms5_out("s1/sweep/summary.json")
@pytest.mark.parametrize("case", [pytest.param("q28", marks=pytest.mark.needs_ms5_out("s1/q28/summary.json")), "sweep"])
def test_case(case):
    pass
'''


def _probe_run(tmp_path: Path, root: Path, *args, other_root: Path | None = None) -> dict:
    """Run the probe tests in a pytest subprocess with code/sim/conftest.py as plugin and SUBLET_MS5_OUT_ROOT=root (the
    MS3 and MS4 roots at `other_root` if given); {test id: 'passed' | 'skipped' | 'failed'} from its JUnit XML."""
    probe = tmp_path / "probe" / "test_probe.py"
    probe.parent.mkdir(exist_ok=True)
    probe.write_text(PROBE_TESTS)
    xml = tmp_path / "probe" / f"report_{len(list(probe.parent.glob('report_*.xml')))}.xml"
    env = dict(os.environ, PYTHONPATH=str(SIM), SUBLET_MS5_OUT_ROOT=str(root), PYTHONDONTWRITEBYTECODE="1")
    if other_root is not None:
        env.update(SUBLET_MS3_OUT_ROOT=str(other_root), SUBLET_MS4_OUT_ROOT=str(other_root))
    r = subprocess.run([sys.executable, "-m", "pytest", "-p", "no:cacheprovider", "-p", "conftest", "-q",
                        f"--rootdir={probe.parent}", "-c", os.devnull, f"--junitxml={xml}", *args, str(probe)],
                       cwd=str(probe.parent), env=env, capture_output=True, text=True, timeout=120)
    assert r.returncode in (0, 5), r.stdout + r.stderr                # 5: every test deselected
    assert "PytestUnknownMarkWarning" not in r.stdout + r.stderr
    out = {}
    for tc in ET.parse(xml).getroot().iter("testcase"):
        kind = "skipped" if tc.find("skipped") is not None else \
            "failed" if tc.find("failure") is not None or tc.find("error") is not None else "passed"
        out[tc.get("name")] = kind
    return out


def test_c31_needs_ms5_out_in_a_pytest_run(tmp_path):
    """On a temporary root (SUBLET_MS5_OUT_ROOT): with an empty out folder every probe test is skipped (the marker
    without arguments too), also while the MS3 and MS4 roots hold every file; with s1/sweep/summary.json present the
    tests that need only it run, the ones that need e9/summary.json or s1/q28/summary.json (a parametrized case's own
    marker) are skipped; the quick suite's expression deselects them all."""
    root, full = tmp_path / "root", tmp_path / "full"
    out = root / "code" / "sim" / "out"
    out.mkdir(parents=True)
    for rel in ("s1/sweep/summary.json", "s1/q28/summary.json", "e9/summary.json"):
        p = full / "code" / "sim" / "out" / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("{}")
    names = ("test_present", "test_missing", "test_folder", "test_case[q28]", "test_case[sweep]")
    assert _probe_run(tmp_path, root) == {n: "skipped" for n in names}
    assert _probe_run(tmp_path, root, other_root=full) == {n: "skipped" for n in names}
    (out / "s1" / "sweep").mkdir(parents=True)
    (out / "s1" / "sweep" / "summary.json").write_text("{}")
    assert _probe_run(tmp_path, root) == {"test_present": "passed", "test_missing": "skipped",
                                          "test_folder": "passed", "test_case[q28]": "skipped",
                                          "test_case[sweep]": "passed"}
    assert _probe_run(tmp_path, full) == {n: "passed" for n in names}
    quick = "not needs_raw and not needs_ms2_checks and not needs_ms3_out and not needs_ms4_out and not needs_ms5_out"
    assert _probe_run(tmp_path, root, "-m", quick) == {}
    assert _probe_run(tmp_path, root, "--strict-markers", "-m", "needs_ms5_out") == {
        "test_present": "passed", "test_missing": "skipped", "test_folder": "passed", "test_case[q28]": "skipped",
        "test_case[sweep]": "passed"}


# ---------------------------------------------------------------- C32: .gitignore
def test_c32_gitignore_lines():
    """The three runs/ folders of S1's parts and of E9 are ignored, each by its own line."""
    lines = {ln.strip() for ln in (REPO / ".gitignore").read_text().splitlines()}
    want = ["code/sim/out/s1/sweep/runs/", "code/sim/out/s1/q28/runs/", "code/sim/out/e9/runs/"]
    assert [w for w in want if w not in lines] == []


# ---------------------------------------------------------------- C33: the two lines of tests/test_ms4_additions.py
MS5_SCRIPTS = ("sf_s1", "sf_e9", "sf_slack")       # the MS5 figure scripts of §2.1 in figs/supp/
# C45: the MS5b supplementary scripts (design/sublet_v2.md §11, W3, W4; unit U39), left out of the copied tree like
# the MS5 scripts, so that the count below holds before and after they exist
MS5B_SUPP_SCRIPTS = ("sf_e3_v2", "sf_e7_intensity", "sf_e7_decomp", "sf_e7_boundary", "sf_e7_grid_dev", "sf_fam_v2",
                     "sf_e7_links")


@pytest.mark.parametrize("with_ms5", [False, True], ids=["without", "with"])
def test_c33_ms4_tests_with_and_without_ms5(tmp_path, monkeypatch, with_ms5):
    """tests/test_ms4_additions.py's C17 test on a checkout whose figs/supp/ lacks or holds sf_s1, sf_e9 and sf_slack
    (the count of the copied tree is 29 plus the MS5 scripts present; figure_scripts() still gives the 20 MS3
    scripts), and its C20 test with the copy-part map without or with C30's entry s1."""
    checkout = tmp_path / "checkout"
    for sub in ("figs", "figs/supp"):
        (checkout / sub).mkdir(parents=True)
        for p in (SIM / sub).glob("*.py"):
            if p.stem not in MS5_SCRIPTS + MS5B_SUPP_SCRIPTS + t4.MS7_SUPP + t4.MS8_SUPP:   # C45: MS5b; C58: MS7; MS8
                shutil.copy(p, checkout / sub / p.name)
    if with_ms5:
        for n in MS5_SCRIPTS:
            (checkout / "figs" / "supp" / f"{n}.py").write_text(f'NAME = "{n}"\n')
    n_sf = len(list((checkout / "figs" / "supp").glob("sf_*.py")))
    assert n_sf == 22 + (3 if with_ms5 else 0)
    monkeypatch.setattr(t4, "SIM", checkout)
    (tmp_path / "c17").mkdir()
    t4.test_c17_figure_scripts_are_the_20_ms3_scripts(tmp_path / "c17", monkeypatch)
    parts = copy.deepcopy(mc.COPY_PARTS)
    if with_ms5:
        parts["s1"] = S1_PARTS
    else:
        parts.pop("s1", None)
    monkeypatch.setattr(mc, "COPY_PARTS", parts)
    (tmp_path / "c20").mkdir()
    t4.test_c20_check_copy_e7_parts(tmp_path / "c20")
