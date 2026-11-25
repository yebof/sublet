"""Tests of the MS5b driver layer: sublet/experiments/ms5b_common.py, e7h.py, run_e7h.sh, ms5b_analysis.py and the
prototype copies of ms5b_proto/ (design/sublet_v2.md §8.3, row test_e7h.py; §4.2-§4.5, §5, §8.1).

Quick (no raw data):
- the job lists: the pilot parts only on the cells of §4.2 and §5's table (dev seeds 101-104 and E7 alignment 1 for
  P0, bench_e7f seeds 107-112, E3 101-104, E5 103-104, the Q44 tuning cells and I4 c11-12, the families of Q6 at
  policy seeds 10-12 and P3's fresh families), with §5's run counts; the confirmation parts only on weeks 301-316, E3
  and E5 config seeds 301-304, the family cells of §4.4(d) and, for part grid, the development-exposed cells of
  §4.4(e); the reduced job list of every confirmation part holds no seed or instance of §4.4; one job per (week,
  A9-family tag) covers every mode of its cell;
- P2's allowance branch (the pilot log of §0, entry "P2, 2026-11-02"): the job lists, counts and reduced lists of
  p0r, p1r, p2r and p3r (development cells only: P2's Proto-alt cells, seeds 117-120, the one-day cells of P2 (ii),
  P3's family cells; Proto-F5-alt on 117-118 for §5's F5 clause), the run order, the tags after P2's decision
  (Sublet at 'allowance' 'lb' with kappa None, BL1-GP as Sublet's guard around BL1, Sublet-alg1), the policies of
  Sublet, Sublet-1way, BL1-GP and Sublet-lag built by drivers.run.make_policy at 'lb', decide_p0r (r0, B(T) against
  the prototype's, the allowance rule), decide_p1r, decide_p2r (complete inputs or 'incomplete', the F5 clause, the
  determinism check against p0r) and decide_p3r (missing F1/F2 runs, ok runs only, LB'(T) and B(T) against OPT) on
  synthetic rows and run files (the sibling folders p2, p1r, p1 and p0r, from their run files or their
  summary.json), decide_p2's recorded decision reproduced from the repository's p1 and p2 summaries, and decide_p4's
  Sublet shared runs from p2r at Sublet's allowance only (never p2's);
- the gates: the confirmation parts refuse to start without the pre-registration, on a dirty tree or with another
  analysis hash (and record without enforcing in reduced runs), the pilot parts without the anchor; this
  repository's anchor is an ancestor of HEAD;
- the tag table against §2.3 and §3 (typed from the note), Sublet's parameters, the lender modes, L-hon (no
  announcement, no refusal, no violation) and RC as the paired difference on fixture runs (ms2_multi_small);
- the statistics of §4.5: the sign test's p for 12 of 16, the bootstrap with its fixed seed, the exact Wilcoxon test
  against an enumeration, the paired margins; the missing-run rule on synthetic job records (collect, retry_list and
  the analysis); the analysis's H1-H6 and H2b on synthetic summaries;
- the prototype copies: each equals its dev source but for the labeled lines;
- the copy check of out/sublet_v2/ (ms5b_common.check_copy) on a synthetic tree and a fake clone;
- run_e7h.sh with a fake driver: the gate refusal, the pass order (pool, alone, MILPs with the b00 parts last), the
  missing-run rule's rerun, E7H_ONLY, the parts' folders, and bash -n.
With the a12 outputs (needs_a12): one reduced week job of each kind P0 runs (BL1 under L-tr, L-eg and L-hon; A8P
around NBR-repro) through e7h's runner, with the run file's gate, mode, r0, status, A8P record and guard facts; and
p0r's reduced Sublet week job and one E3 cell job at P2's allowance, with the record's allowance fields (LB_RULE,
'lb', no B0, kappa None), B(T) equal to the OnlineLB's, the certificate and the envelope.
Marker needs_ms5b_out: the copied confirmation outputs (every part's summary, the copy check, the analysis).
"""
import copy
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from fixtures import SIM

from sublet.experiments import e3
from sublet.experiments import e7h
from sublet.experiments import ms3_common as mc
from sublet.experiments import ms5b_analysis as ma
from sublet.experiments import ms5b_common as m5

REPO = SIM.parents[1]
RUN = SIM / "sublet" / "experiments" / "run_e7h.sh"
DEV_GA = SIM / "out" / "sublet_v2_dev" / "guard_allowance"
# §4.2 and §5, typed from the note
DEV_WEEKS = {"p0": {101, 102, 103, 104, 1}, "p1": set(range(107, 113)), "p2": set(range(107, 111)),
             "p5": {107, 108},
             # P2's allowance branch (pilot log of §0, entry "P2, 2026-11-02"): §4.1's reserve 117-120
             "p0r": {107, 108, 1}, "p1r": set(range(117, 121)), "p2r": set(range(117, 121))}
E3_PILOT, E5_PILOT = {101, 102, 103, 104}, {103, 104}
TUNING = {("I1", 3), ("I2", 1), ("I3", 1), ("I4", 11), ("I4", 12)}
CONF_WEEKS = set(range(301, 317))
# §3 and §2.3, typed from the note: tag -> (registry id, parameters; None for the instance-dependent ones)
SPEC_TAGS = {
    "Sublet": ("A8P", None), "A9": ("A9", {}), "Sublet-1way": ("A8P", None), "BL1-GP": ("A8P", None),
    "Sublet-MS4": ("A8", None), "BL1": ("BL1", {}), "BL1-BO": ("BL1", {"backoff_cap": 288}), "BL2": ("BL2", {}),
    "BL3-0": ("BL3", {"n_extra": 0}), "BL4": ("BL4", {}), "BL5-cur": ("BL5", {"use_current_slot": True}),
    "BL5": ("BL5", {}), "BL5-tau60": ("BL5", {"use_current_slot": True, "tau_min": 60}),
    "BL5N": ("BL5", {"use_current_slot": True, "contract_rule": "c2", "mbb": True}),
    "BL1N": ("A9", {"target": "ceil", "release": "now"}),
    "CR": ("A9", {"contract_rule": "kstar", "mbb": False, "site_rule": "static", "commit": False, "insure": False}),
    "A9-noMBB": ("A9", {"mbb": False}), "A9-noCommit": ("A9", {"commit": False}), "A9-noIns": ("A9", {"insure": False}),
    "A9-kstar": ("A9", {"contract_rule": "kstar"}), "A9-static": ("A9", {"site_rule": "static"}), "A6": ("A6", {}),
    "NBR-repro": ("A9", {"site_rule": "noticed", "commit": False, "insure": False}),
    "RCRb-repro": ("A9", {"theta": "cr", "tie": "rank"}),
    "CR-repro": ("A9", {"contract_rule": "kstar", "mbb": False, "site_rule": "static", "commit": False,
                        "insure": True, "theta": "cr", "tie": "rank"}),
    "BL1N-repro": ("A9", {"target": "ceil", "release": "now", "tie": "rank"}),
}


@pytest.fixture()
def reduced(monkeypatch):
    monkeypatch.setenv(e7h.REDUCED_ENV, "1")


def _jobs(part, reduced=False, monkeypatch=None):
    return [j for j in e7h.jobs([part])]


def _runs(js, kind=None):
    return [(j, x) for j in js if kind is None or j.params["kind"] == kind for x in e7h.expected_runs(j)]


# ---------------------------------------------------------------- the job lists (§4.2, §4.4, §5)
def test_pilot_jobs_only_on_the_development_set(monkeypatch):
    monkeypatch.delenv(e7h.REDUCED_ENV, raising=False)
    for part in e7h.PILOT_PARTS:
        js = e7h.jobs([part])
        mc.check_jobs(js)
        assert js and all(j.params["part"] == part for j in js)
        for j in js:
            p = j.params
            if p["kind"] in ("week", "premium"):
                assert p["c"] in DEV_WEEKS[part], (part, j.id)
                assert p.get("horizon_min") == m5.WEEK_MIN
            elif p["kind"] in ("e3cell", "e3milp"):
                assert p["c"] in E3_PILOT and p["u"] == 8 and p["mu"] == 1.0 and p["horizon"] is None, j.id
            elif p["kind"] == "e5":
                assert p["c"] in E5_PILOT and part == "p4", j.id
            elif p["kind"] == "q44":
                assert (p["inst"], p["c"]) in TUNING, j.id
            elif p["kind"] == "fam":
                assert part in ("p3", "p3r") and all(s in (10, 11, 12) for _t, ss in p["entries"] for s in ss), j.id
                assert p["family"]["id"] in ("F1", "F2", "F3", "P3F1", "P3F2", "P3F3")
            else:
                raise AssertionError(j.id)
    # §5's run counts
    p1 = e7h.jobs(["p1"])
    assert len(_runs(p1, "week")) == 576 and len(_runs(p1, "q44")) + len(_runs(p1, "e3cell")) == 123
    assert len(_runs(e7h.jobs(["p2a"]), "e3cell")) == 72
    p2 = e7h.jobs(["p2"])
    assert len(_runs(p2, "e3cell")) + len(_runs(p2, "q44")) == 58
    assert sorted({x[0] for _j, x in _runs(p2, "week")}) == ["BL1-GP", "Proto-F5", "Proto-F5-alt", "Proto-alt",
                                                              "Sublet", "Sublet-1way"]
    p0 = _runs(e7h.jobs(["p0"]), "week")                # 44 runs of §5's P0 row and BL5N's 8 (§3)
    assert len(p0) == 52 and len([x for _j, x in p0 if x[0] == "BL5N"]) == 8
    p3 = e7h.jobs(["p3"])
    assert len(p3) == 53 + 9 + 27 + 6
    assert all("RR_RENEW" not in [t for t, _s in j.params["entries"]] for j in p3
               if j.params["family"]["kind"] == "c3p5")
    # P3's fresh families (§5 P3)
    fr = {f["id"]: f for f in e7h.FRESH_P3}
    assert (fr["P3F1"]["m"], fr["P3F1"]["rho"], fr["P3F1"]["tau"], fr["P3F1"]["H"], fr["P3F1"]["T"]) == \
        ([3, 6, 12], [5, 12, 32], 2, 1, 48)
    assert (fr["P3F2"]["T"], fr["P3F2"]["modes"]) == (96, ["F-ss", "F-iid", "F-eg"])
    assert (fr["P3F3"]["beta"], fr["P3F3"]["T"]) == ([3, 10, 20], [64, 128])
    p4 = e7h.jobs(["p4"])
    assert [j.id for j in p4 if j.kind == "milp"] == [e3.milp_id(b, 8, 1.0, 101, "shared") for b in (1, 8, 32)]
    assert {j.params["menu"] for j in p4 if j.params["kind"] == "e5"} == {"short", "long"}
    p5 = e7h.jobs(["p5"])
    assert set(next(j for j in p5 if j.params["tag"] == "A9").params["modes"]) == \
        {"L-vr", "L-rf", "L-ad", "L-b999", "L-hon", "L-iid-0.05", "L-iid-0.1", "L-iid-0.2", "L-iid-0.34",
         "L-iid-0.5", "L-iid-0.8", "L-iid-1"}
    # no pilot job touches the held-back seeds 113-124 or the confirmation's, but for P2's allowance branch, which
    # opens the reserve 117-120 (§4.1, §4.2)
    for part in e7h.PILOT_PARTS:
        ok = set(e7h.RERUN_WEEKS) if part in e7h.RERUN_PARTS else set()
        assert not [j for j in e7h.jobs([part]) if (113 <= int(j.params.get("c", 0)) or int(j.params.get("c", 0)) > 300)
                    and int(j.params["c"]) not in ok]


def test_confirmation_jobs_only_on_section_4_4(monkeypatch):
    monkeypatch.delenv(e7h.REDUCED_ENV, raising=False)
    main = e7h.jobs(["main"])
    assert len(main) == 22 * 16 and {j.params["c"] for j in main} == CONF_WEEKS
    assert all(j.params["modes"] == list(m5.conf_modes()) and j.params["policy_seeds"] == [0] for j in main)
    assert {j.params["tag"] for j in main} == set(m5.E7_TAGS) and len(m5.E7_TAGS) == 22
    seeds = e7h.jobs(["seeds"])
    assert {(j.params["tag"], j.params["c"]) for j in seeds} == {(t, c) for t in ("Sublet", "BL1", "BL5-cur")
                                                                  for c in (301, 302, 303, 304)}
    assert all(j.params["policy_seeds"] == [1, 2] for j in seeds)
    sec = e7h.jobs(["second"])
    assert {j.params["c"] for j in sec} == {301, 302, 303, 304}
    assert set(next(j for j in sec if j.params["kind"] == "week" and j.params["tag"] == "BL1").params["modes"]) == \
        {"L-vr", "L-rf", "L-ad", "L-b999", "L-iid-0.1", "L-iid-0.34", "L-iid-0.5", "L-iid-0.8", "L-iid-1"}
    assert {j.kind for j in sec if j.params["kind"] == "gap_lp"} == {"alone"}
    e3j = e7h.jobs(["e3"])
    assert {j.params["c"] for j in e3j} == {301, 302, 303, 304}
    assert sum(1 for j in e3j if j.kind == "milp") == 276 and sum(1 for j in e3j if j.kind == "pool") == 24
    fam = e7h.jobs(["fam"])
    assert len(fam) == 53 + 4 + 12 + 2
    fresh = {f["id"]: f for f in e7h.FRESH_CONF}
    assert (fresh["CF1"]["m"], fresh["CF1"]["rho"], fresh["CF1"]["tau"], fresh["CF1"]["H"], fresh["CF1"]["T"]) == \
        ([5, 10], [7, 24], 3, 2, 72)
    assert (fresh["CF2"]["T"], fresh["CF3"]["beta"], fresh["CF3"]["T"]) == (144, [4, 24], [96])
    for j in fam:
        fixed = j.params["mode"] in ("F-ad", "F-eg")
        for t, ss in j.params["entries"]:
            want = [13] if fixed and t in ("A9", "A9-noIns", "RR_RENEW") else list(range(13, 23))
            assert ss == want, (j.id, t)
    grid = e7h.jobs(["grid"])
    weeks = {j.params["c"] for j in grid if j.params["kind"] in ("week", "gap", "gap_lp")}
    assert weeks == {1, 2, 3, 4}
    q = {(j.params["inst"], j.params["c"]) for j in grid if j.params["kind"] == "q44"}
    assert not q & TUNING and len(q) == 2 + 7 + 3 + 8
    a9 = next(j for j in grid if j.params["kind"] == "week" and j.params["tag"] == "A9" and j.params["c"] == 1)
    assert a9.params["policy_seeds"] == [0]
    sub = next(j for j in grid if j.params["kind"] == "week" and j.params["tag"] == "Sublet" and j.params["c"] == 1)
    assert sub.params["policy_seeds"] == [0, 1, 2] and sub.params["modes"] == list(m5.main_modes())


def test_reduced_confirmation_lists_hold_no_cell_of_section_4_4(reduced):
    for part in e7h.CONF_PARTS:
        js = e7h.jobs([part])
        assert js, part
        for j in js:
            p = j.params
            if "c" in p:
                assert p["c"] in (101,) or (p["kind"] == "q44" and (p["inst"], p["c"]) == ("I2", 1)), j.id
            if p["kind"] == "week":
                assert p["horizon_min"] == e7h.REDUCED_HORIZON_MIN
            if p["kind"] == "fam":
                assert p["family"]["id"] in ("F1", "F2", "F3")
                assert all(ss == [0] for _t, ss in p["entries"]), j.id
            if p["kind"] in ("e3cell", "e3milp"):
                assert p["horizon"] == list(e7h.E3_WINDOW)
    for part in e7h.PILOT_PARTS:
        assert all(j.params.get("c", 101) not in CONF_WEEKS for j in e7h.jobs([part]))


def test_one_job_per_week_and_a9_family_tag_covers_every_mode(monkeypatch):
    monkeypatch.delenv(e7h.REDUCED_ENV, raising=False)
    for part, modes in (("p1", m5.main_modes()), ("main", m5.conf_modes()), ("p5", e7h.P5_MODES)):
        js = [j for j in e7h.jobs([part]) if j.params["kind"] == "week"]
        seen: dict = {}
        for j in js:
            t = j.params["tag"]
            if t in m5.PROTO or m5.tag(t).a9_family:
                key = (j.params["c"], t)
                assert key not in seen, (part, key)
                seen[key] = j
                if t not in ("A9-lag", "BL1-lag"):
                    assert tuple(j.params["modes"]) == tuple(modes), (part, j.id)
        assert seen, part
    assert {t for t, v in m5.TAGS.items() if v.a9_family} >= {"Sublet", "Sublet-1way", "A9", "BL1N", "CR", "A9-noMBB",
                                                            "A9-noCommit", "A9-noIns", "A9-kstar", "A9-static"}


# ---------------------------------------------------------------- P2's allowance branch (pilot log of §0, P2's entry)
def _kind_runs(js) -> dict:
    out: dict = {}
    for j in js:
        for x in e7h.expected_runs(j):
            out.setdefault(j.params["kind"], []).append(x)
    return out


def _cm(xs, tag=None) -> set:
    """{(cell, mode)} of expected runs (tag, mode, cell, seed)."""
    return {(x[2], x[1]) for x in xs if tag is None or x[0] == tag}


ONE_DAY = {(f"b{b}:c{c}", "shared") for b in e3.BS for c in E3_PILOT} | {(f"{i}:c{c}", "L-tr") for i, c in TUNING}


def test_rerun_parts_job_lists(monkeypatch):
    """p0r, p1r, p2r and p3r (the pilot log's reading of 'P0-P2 rerun for it'): their cells and run counts, on
    development cells only (P2's Proto-alt cells and E7 alignment 1 for p0r, seeds 117-120 for p1r and p2r, the
    one-day cells of P2 (ii) unchanged, P3's family cells for p3r)."""
    monkeypatch.delenv(e7h.REDUCED_ENV, raising=False)
    assert e7h.RERUN_WEEKS == (117, 118, 119, 120) and e7h.RERUN_PAIR == (117, 118)
    assert e7h.RERUN_PARTS == ("p0r", "p1r", "p2r", "p3r")
    tr_eg = ("L-tr", "L-eg")
    # p0r: Sublet on every cell of P2 on which Proto-alt ran, and A8P-MS4 as p0 runs it
    js = e7h.jobs(["p0r"])
    mc.check_jobs(js)
    r = _kind_runs(js)
    assert len(js) == 32 and (len(r["week"]), len(r["e3cell"]), len(r["q44"])) == (5, 24, 5)
    p2 = _kind_runs(e7h.jobs(["p2"]))
    assert _cm(r["week"], "Sublet") == _cm(p2["week"], "Proto-alt") == {(str(c), m) for c in (107, 108) for m in tr_eg}
    assert _cm(r["e3cell"] + r["q44"]) == _cm(p2["e3cell"] + p2["q44"], "Proto-alt") == ONE_DAY
    assert {x[0] for x in r["e3cell"] + r["q44"]} == {"Sublet"}
    assert [x for x in r["week"] if x[0] == "A8P-MS4"] == [("A8P-MS4", "L-tr", "1", 0)]
    p0 = next(j for j in e7h.jobs(["p0"]) if j.params.get("tag") == "A8P-MS4")
    a8 = next(j for j in js if j.params.get("tag") == "A8P-MS4")
    assert {k: v for k, v in a8.params.items() if k != "part"} == {k: v for k, v in p0.params.items() if k != "part"}
    # p1r: A9 on 117-120 under the six modes, policy seed 0
    js = e7h.jobs(["p1r"])
    assert len(js) == 4 and len(_runs(js)) == 24 and {j.params["c"] for j in js} == set(e7h.RERUN_WEEKS)
    assert all(j.params["tag"] == "A9" and j.params["modes"] == list(m5.main_modes()) and j.params["policy_seeds"]
               == [0] for j in js)
    # p2r: P2 in full with Sublet at the built allowance and F5 at the alternative (§5's F5 clause); no Proto-alt,
    # Proto-F5 (Algorithm 1's allowance) or Sublet-alg1 run
    js = e7h.jobs(["p2r"])
    mc.check_jobs(js)
    r = _kind_runs(js)
    tags = ("Sublet", "Sublet-1way", "BL1-GP", "Proto-F5-alt")
    assert len(js) == 41 and len(_runs(js)) == 69 and len(r["week"]) == 40
    assert {t: sum(1 for x in r["week"] if x[0] == t) for t in tags} == {"Sublet": 24, "Sublet-1way": 4, "BL1-GP": 8,
                                                                        "Proto-F5-alt": 4}
    assert _cm(r["week"], "Sublet") == {(str(c), m) for c in e7h.RERUN_WEEKS for m in m5.main_modes()}
    assert _cm(r["week"], "Sublet-1way") == _cm(r["week"], "Proto-F5-alt") == {(str(c), m) for c in (117, 118)
                                                                               for m in tr_eg}
    assert _cm(r["week"], "BL1-GP") == {(str(c), m) for c in e7h.RERUN_WEEKS for m in tr_eg}
    assert m5.PROTO["Proto-F5-alt"] == {**m5.PROTO["Proto-F5-alt"], "rule": m5.RULE_ALT, "f5": True}
    assert _cm(r["e3cell"] + r["q44"]) == ONE_DAY and len(r["e3cell"]) + len(r["q44"]) == 29
    assert {x[0] for x in r["e3cell"] + r["q44"]} == {"Sublet"}
    # p3r: Sublet alone on P3's family cells at P3's seeds
    js, p3 = e7h.jobs(["p3r"]), e7h.jobs(["p3"])
    assert len(js) == len(p3) == 95 and len(_runs(js)) == 285
    assert all(j.params["entries"] == [["Sublet", [10, 11, 12]]] for j in js)
    assert [(j.params["inst"], j.params["mode"]) for j in js] == [(j.params["inst"], j.params["mode"]) for j in p3]
    # the A9-family week jobs of p1r cover every mode of their cell; Sublet-alg1 runs in no part
    assert not [x for j in e7h.jobs_all() for x in e7h.expected_runs(j) if x[0] == "Sublet-alg1"]


def test_rerun_parts_reduced_lists(reduced):
    """Reduced p0r-p3r: development cells only, the first seed of each group as the other pilot parts (a 2-hour
    horizon, E3 b in {1, 8} at c 101 and the Q44 cell I1 c3 in E3_WINDOW, P3's first instances at seed 10)."""
    want = {"p0r": (5, 6), "p1r": (1, 6), "p2r": (7, 15), "p3r": (6, 6)}
    for part in e7h.RERUN_PARTS:
        js = e7h.jobs([part])
        assert (len(js), len(_runs(js))) == want[part], part
        for j in js:
            p = j.params
            if p["kind"] == "week":
                assert p["horizon_min"] == e7h.REDUCED_HORIZON_MIN and p["policy_seeds"] == [0]
                assert p["c"] in ({107, 1} if part == "p0r" else {117}), j.id
            elif p["kind"] == "e3cell":
                assert p["c"] == 101 and p["b"] in (1, 8) and p["horizon"] == list(e7h.E3_WINDOW), j.id
            elif p["kind"] == "q44":
                assert (p["inst"], p["c"]) == ("I1", 3) and p["window"] == list(e7h.E3_WINDOW), j.id
            else:
                assert p["kind"] == "fam" and part == "p3r" and p["entries"] == [["Sublet", [10]]], j.id
    assert {j.params["tag"] for j in e7h.jobs(["p2r"]) if j.params["kind"] == "week"} == {"Sublet", "Sublet-1way",
                                                                                         "BL1-GP", "Proto-F5-alt"}


def test_rerun_parts_run_order_and_folders(monkeypatch, tmp_path):
    assert e7h.PILOT_PARTS == ("p0", "p2a", "p3", "p1", "p2", "p0r", "p1r", "p2r", "p3r", "p4", "p5")
    assert e7h.PILOT_PARTS[5:9] == e7h.RERUN_PARTS and all(e7h.is_pilot(p) for p in e7h.RERUN_PARTS)
    monkeypatch.setenv("E7H_PART", "p0r,p1r p2r p3r")
    assert e7h.parts() == ["p0r", "p1r", "p2r", "p3r"]
    assert e7h.part_dir("p2r", tmp_path) == tmp_path.resolve() / "out" / "sublet_v2_pilot" / "p2r"
    assert list(dict.fromkeys(j.params["part"] for j in e7h.jobs_all()))[:len(e7h.PILOT_PARTS)] == \
        list(e7h.PILOT_PARTS)
    assert "p0 | p2a | p3 | p1 | p2 | p0r | p1r | p2r | p3r | p4 | p5 |" in RUN.read_text()
    p, ev, out = _run_fake(tmp_path, [["e7h:p0r:k=week:tag=Sublet:c=107", "pool", "p0r", 0.1]], "p0r")
    assert p.returncode == 0, p.stdout + p.stderr
    assert set(ev) == {"e7h:p0r:k=week:tag=Sublet:c=107", "summary:p0r"}
    assert (out / "sublet_v2_pilot" / "p0r" / "summary.json").is_file()


LB = {"inner": "A9", "project": True, "allowance": "lb", "kappa": None}


def test_tag_parameters_after_p2():
    """P2's decision in the tags: Sublet at 'allowance' 'lb' with kappa None; Sublet-1way and Sublet-lag follow it;
    BL1-GP is the rule 'Sublet's guard with inner BL1'; Sublet-alg1 keeps Algorithm 1's allowance and is in no
    hypothesis set; allowance_fields relabels only records at P2's allowance."""
    inst = object()
    assert m5.tag_params("Sublet", inst) == LB
    assert m5.tag_params("Sublet-1way", inst) == {**LB, "project": False}
    assert m5.tag_params("Sublet-lag", inst) == {**LB, "inner_params": {"demand_lag": 1}}
    assert m5.TAGS["BL1-GP"].params == "bl1_gp" and m5.tag_params("BL1-GP", inst) == {**LB, "inner": "BL1"}
    assert m5.tag_params_text("BL1-GP") == "ms5b_common.sublet_v2_params(inst) with inner 'BL1'"
    assert m5.tag_table(["BL1-GP"])["BL1-GP"]["params"] == m5.PARAM_RULE_TEXT["bl1_gp"]
    with pytest.raises(ValueError, match="need the instance"):
        m5.tag_params("BL1-GP")
    assert set(m5.PARAM_RULES) == set(m5.PARAM_RULE_TEXT)
    a = m5.TAGS["Sublet-alg1"]
    assert (a.id, a.params, a.kind, a.a9_family, a.information) == ("A8P", {"inner": "A9", "project": True}, "guard",
                                                                    True, "I1")
    assert a.role == "Sublet at Algorithm 1's allowance (P2's first allowance; reference)"
    assert m5.tag_params("Sublet-alg1") == {"inner": "A9", "project": True}
    assert "Sublet-alg1" not in m5.E7_TAGS + m5.H1_SET + m5.H2B_SET + m5.ABLATIONS
    assert m5.is_guarded("Sublet-alg1") and m5.is_guarded("BL1-GP") and not m5.seed_free("BL1-GP")
    rec = {"B0_rule": "auto, kappa None", "B0_usd": 24.32, "B0_report_usd": 24.33, "kappa": None}
    assert m5.allowance_fields(dict(rec), {"inner": "BL1"}) == rec and m5.allowance_fields(dict(rec), None) == rec
    assert m5.allowance_fields(dict(rec), LB) == {"B0_rule": m5.LB_RULE, "B0_usd": None, "B0_report_usd": None,
                                                  "kappa": None, "allowance": "lb"}
    # a run's allowance: its parameters' key (A8P keeps it only at 'lb'), its A8 record's, else Algorithm 1's
    assert m5.run_allowance({"params": LB}) == "lb" and m5.run_allowance({"a8": {"allowance": "lb"}}) == "lb"
    assert m5.run_allowance({"params": {"inner": "A9", "project": True}}) == "alg1" and m5.run_allowance(None) == "alg1"
    from sublet.algos import guard
    if "allowance" not in guard.ProjectedGuarded.PARAMS:
        pytest.skip("ProjectedGuarded has no parameter 'allowance' yet (algos/online_lb.py not built)")
    for t in ("Sublet", "Sublet-1way", "BL1-GP", "Sublet-lag", "Sublet-alg1"):
        assert set(m5.tag_params(t, inst)) <= set(guard.ProjectedGuarded.PARAMS), t


def test_tag_policies_build_at_the_built_allowance():
    """drivers.run.make_policy accepts the tags' parameters after P2's decision (as e7h's runners call it, on a toy
    instance): Sublet, Sublet-1way (project false), BL1-GP (inner BL1) and Sublet-lag (A9 on slot t - 1's demand) are
    A8P at allowance 'lb' with kappa None, and their resolved parameters keep 'allowance' 'lb'; Sublet-alg1 is A8P at
    Algorithm 1's allowance (kappa 10, no 'allowance' key)."""
    from fixtures import toy_instance
    from sublet.algos import guard
    from sublet.drivers import run as drun
    inst = toy_instance({})
    for t, project, inner in (("Sublet", True, "A9"), ("Sublet-1way", False, "A9"), ("BL1-GP", True, "BL1"),
                              ("Sublet-lag", True, "A9")):
        pol = drun.make_policy({"policy": {"id": m5.tag(t).id, "params": m5.tag_params(t, inst)}}, inst)
        assert isinstance(pol, guard.ProjectedGuarded) and pol.allowance_rule == "lb", t
        rp = pol.params()
        assert rp["allowance"] == "lb" and rp["kappa"] is None and rp["project"] is project and rp["inner"] == inner, t
    assert drun.make_policy({"policy": {"id": "A8P", "params": m5.tag_params("Sublet-lag", inst)}},
                            inst).params()["inner_params"]["demand_lag"] == 1
    pol = drun.make_policy({"policy": {"id": "A8P", "params": m5.tag_params("Sublet-alg1", inst)}}, inst)
    assert pol.allowance_rule == "alg1" and "allowance" not in pol.params() and pol.params()["kappa"] == 10


def _write_part(out: Path, js, tag: str, r0_of, skip=(), extra=None) -> None:
    """Ok records and outputs of the jobs `js` holding one entry per expected run of `tag` (r0 = r0_of(cell, mode);
    extra(cell, mode) the entry's other fields, e.g. its 'a8' record or 'prototype' extract)."""
    for j in js:
        ents = [{"tag": t, "mode": m, "policy_seed": s, "p": s, "config_seed": j.params.get("c"), "r0": r0_of(cell, m),
                 "ALG": 100.0 * r0_of(cell, m), "n_invariant_failures": 0, "status": "ok",
                 **(extra(cell, m) if extra else {})}
                for t, m, cell, s in e7h.expected_runs(j) if t == tag and (cell, m) not in skip]
        if ents:
            _write_job(out, j.id, "ok", ents, kind_path=e7h.output_path(out, j))


def _base(cell: str, mode: str) -> float:
    return 0.5 + 0.001 * (len(cell) + 3 * len(mode)) + (0.01 if cell.isdigit() else 0.0)


def _bt(cell: str, mode: str) -> float:
    """A synthetic allowance at the horizon per cell (USD)."""
    return 20.0 + len(cell) + 0.5 * len(mode)


def test_decide_p0r_against_p2s_proto_alt(monkeypatch, tmp_path):
    """decide_p0r on synthetic run files: Sublet (this part) against Proto-alt in the sibling p2 per cell, within
    REPRO_TOL; a cell beyond it, a cell without Proto-alt and an identity off by 1e-6 USD each fail; B_T(Sublet)
    against the prototype's B_T within B_REL_TOL (1e-12 passes, 1e-6 fails, a cell without the prototype's B_T is not
    compared); a Sublet run at another allowance rule fails; p2's rows are read from its run files, or from its
    summary.json when it keeps no runs/."""
    monkeypatch.delenv(e7h.REDUCED_ENV, raising=False)
    root = tmp_path / "a"
    out = root / "p0r"
    p0r = e7h.jobs(["p0r"])
    _write_part(root / "p2", e7h.jobs(["p2"]), "Proto-alt", _base,
                extra=lambda c, m: {"prototype": {"label": "prototype", "rule": m5.RULE_ALT, "B_T": _bt(c, m)}})

    def col_with(dr=1e-4, alg=e7h.IDENTITY_USD, odd=None, b_odd=None, b_rel=0.0, rule_odd=None):
        shutil.rmtree(out, ignore_errors=True)

        def a8(c, m):
            return {"a8": {"B0_rule": "auto, kappa 10" if (c, m) == rule_odd else m5.LB_RULE, "allowance": "lb",
                           "B_T": _bt(c, m) * (1.0 + (b_rel if (c, m) == b_odd else 0.0))}}
        _write_part(out, p0r, "Sublet", lambda c, m: _base(c, m) + (0.01 if (c, m) == odd else dr), extra=a8)
        j = next(j for j in p0r if j.params.get("tag") == "A8P-MS4")
        _write_job(out, j.id, "ok", [{"tag": "A8P-MS4", "mode": "L-tr", "policy_seed": 0, "r0": alg / 2e4,
                                      "ALG": alg, "n_invariant_failures": 0, "status": "ok"}])
        return e7h.collect(out, p0r)
    d = e7h.decide_p0r(col_with(), out)
    assert d["passes"] and d["reproduction_ok"] and d["identity"]["ok"] and d["p2_source"] == "runs"
    assert d["n_cells"] == d["n_within"] == 33 and not d["missing_cells"]
    assert d["worst_abs_diff"] == pytest.approx(1e-4) and d["tolerance"] == e7h.REPRO_TOL
    assert {(x["cell"], x["mode"]) for x in d["cells"]} == ONE_DAY | {(str(c), m) for c in (107, 108)
                                                                     for m in ("L-tr", "L-eg")}
    assert d["sublet_B0_rules"] == [m5.LB_RULE] and d["rules_ok"]
    al = d["allowance"]
    assert al["ok"] and al["n_compared"] == al["n_within"] == 33 and al["worst_abs_rel_diff"] == 0.0
    assert al["tolerance_rel"] == e7h.B_REL_TOL == 1e-9
    x = next(x for x in d["cells"] if x["cell"] == "107" and x["mode"] == "L-eg")
    assert x["B_T"] == x["B_T_proto_alt"] == _bt("107", "L-eg") and x["B_rel_diff"] == 0.0 and x["B_within"]
    d = e7h.decide_p0r(col_with(b_odd=("b4:c102", "shared"), b_rel=1e-12), out)
    assert d["passes"] and d["allowance"]["worst_abs_rel_diff"] == pytest.approx(1e-12, rel=1e-3)
    d = e7h.decide_p0r(col_with(b_odd=("I2:c1", "L-tr"), b_rel=1e-6), out)  # r0 within REPRO_TOL, B(T) off by 1e-6
    assert d["reproduction_ok"] and not d["allowance"]["ok"] and not d["passes"] and d["allowance"]["n_within"] == 32
    d = e7h.decide_p0r(col_with(rule_odd=("108", "L-tr")), out)              # one run at Algorithm 1's rule
    assert d["reproduction_ok"] and not d["rules_ok"] and not d["passes"]
    assert d["sublet_B0_rules"] == sorted(["auto, kappa 10", m5.LB_RULE])
    d = e7h.decide_p0r(col_with(odd=("b8:c103", "shared")), out)
    assert not d["passes"] and d["n_within"] == 32 and d["worst_abs_diff"] == pytest.approx(0.01)
    d = e7h.decide_p0r(col_with(alg=e7h.IDENTITY_USD + 1e-6), out)
    assert d["reproduction_ok"] and not d["identity"]["ok"] and not d["passes"]
    q = next(j for j in e7h.jobs(["p2"]) if j.params["kind"] == "q44" and j.params["inst"] == "I3")
    mc.record_path(root / "p2", q.id).unlink()
    d = e7h.decide_p0r(col_with(), out)
    assert not d["passes"] and d["missing_cells"] == [{"cell": "I3:c1", "mode": "L-tr", "sublet": True,
                                                       "proto_alt": False}]
    assert d["allowance"]["n_compared"] == 32 and d["allowance"]["ok"]
    # the repository's copy of p2 keeps no runs/: its summary's rows are read (brief keeps the prototype's B_T; a row
    # without it is not compared)
    root2 = tmp_path / "b"
    grid = ONE_DAY | {(str(c), m) for c in (107, 108) for m in ("L-tr", "L-eg")}
    rows = [{"tag": "Proto-alt", "kind": "week" if c.isdigit() else ("e3cell" if c.startswith("b") else "q44"),
             "cell": c, "mode": m, "seed": 0, "status": "ok", "r0": _base(c, m),
             **({} if c == "107" else {"prototype": {"B_T": _bt(c, m)}})} for c, m in sorted(grid)]
    mc.dump_json({"runs": rows}, root2 / "p2" / "summary.json")
    out2 = root2 / "p0r"
    shutil.copytree(out, out2)
    d2 = e7h.decide_p0r(e7h.collect(out2, p0r), out2)
    assert d2["passes"] and d2["p2_source"] == "summary.json" and d2["p2_rows"] == 33
    assert d2["allowance"]["n_compared"] == 31 and d2["allowance"]["ok"]
    shutil.rmtree(root2 / "p2")
    d3 = e7h.decide_p0r(e7h.collect(out2, p0r), out2)
    assert not d3["passes"] and d3["p2_source"] == "none" and len(d3["missing_cells"]) == 33


def _guarded(tag, **kw):
    return {"job": "j", "cell": "117", "tag": tag, "mode": "L-tr", "seed": 0, "held": True, "env_ok": True,
            "aborted": False, "s_fb_all": True, "t0g_bound_all": True, "project": True, **kw}


def test_decide_p2r_prices_from_p1r_and_p1(monkeypatch, tmp_path):
    """decide_p2r: P2's tests for Sublet with A9's r0 from p1r on the week cells and from p1 (Q44 under L-tr, E3
    shared) on the one-day cells; 'keep the alternative allowance' when it passes, P2's 'both fail' text with §5's F5
    clause when test (3), (2) or (1) fails; 'incomplete' (no branch of §5's table) when p1 or p1r is absent or a Sublet
    run is missing, with the missing runs and references listed; the guard summaries of Sublet-1way, BL1-GP and
    Proto-F5-alt with Proto-F5-alt's prices; the determinism check against p0r's one-day runs."""
    monkeypatch.delenv(e7h.REDUCED_ENV, raising=False)
    root = tmp_path / "pilot"
    out = root / "p2r"
    _write_part(root / "p1r", e7h.jobs(["p1r"]), "A9", _base)
    # p1 from its summary.json (no runs/): A9's one-day rows, a decoy week row on 117 and an A9-noIns row
    p1 = [{"tag": "A9", "kind": "e3cell" if c.startswith("b") else "q44", "cell": c, "mode": m, "seed": 0,
           "status": "ok", "r0": _base(c, m)} for c, m in ONE_DAY]
    p1 += [{"tag": "A9", "kind": "q44", "cell": "I1:c3", "mode": "L-eg", "seed": 0, "status": "ok", "r0": 0.1},
           {"tag": "A9", "kind": "week", "cell": "117", "mode": "L-tr", "seed": 0, "status": "ok", "r0": 0.0},
           {"tag": "A9-noIns", "kind": "e3cell", "cell": "b1:c101", "mode": "shared", "seed": 0, "status": "ok",
            "r0": 0.0}]
    mc.dump_json({"runs": p1}, root / "p1" / "summary.json")
    p2r = e7h.jobs(["p2r"])

    def run(day=0.001, week=0.002, guarded=(), skip=()):
        shutil.rmtree(out, ignore_errors=True)
        _write_part(out, p2r, "Sublet", lambda c, m: _base(c, m) + (week if c.isdigit() else day), skip=skip)
        _write_part(out, [j for j in p2r if j.params.get("tag") == "Proto-F5-alt"], "Proto-F5-alt",
                    lambda c, m: _base(c, m) + 0.004)
        col = e7h.collect(out, p2r)
        col["guarded"] = [_guarded("Sublet"), _guarded("Sublet-1way", project=False, aborted=True),
                          _guarded("BL1-GP"), _guarded("Proto-F5-alt")] + list(guarded)
        return e7h.decide_p2r(col, out)
    d = run()
    a = d["allowance"]
    assert d["complete"] and d["passes"] and d["decision"] == "keep the alternative allowance"
    assert a["rule"] == m5.LB_RULE and d["expected"] == {"week_runs": 24, "day_cells": 29}
    assert not d["missing_sublet_runs"] and not d["missing_references"]
    assert a["test1"] and a["test2"] and a["test3"] and len(a["week_prices"]) == 24 and a["n_day_cells"] == 29
    assert a["median_week"] == pytest.approx(0.002) and a["max_week"] == pytest.approx(0.002)   # p1r's, not p1's 117
    assert a["median_day"] == pytest.approx(0.001)
    assert d["a9_sources"] == {"p1r": "runs", "p1": "summary.json"} and d["a9_cells"] == {"week": 24, "day": 29}
    assert d["others"]["Sublet-1way"]["aborts"] == 1 and d["others"]["BL1-GP"]["n_runs"] == 1
    assert d["others"]["Proto-F5-alt"]["n_runs"] == 1 and d["missing_other_runs"] == {"Sublet-1way": 4, "BL1-GP": 8,
                                                                                       "Proto-F5-alt": 0}
    assert d["f5"]["n"] == 4 and d["f5"]["median_week"] == pytest.approx(0.004) and "F5 clause" in d["f5"]["note"]
    assert "Sublet-alg1" in d["not_rerun"] and "F5" not in d["not_rerun"]
    assert d["determinism_p0r"] == {**d["determinism_p0r"], "source": "none", "n_compared": 0, "equal": None}
    assert e7h.P2R_BOTH_FAIL.startswith(e7h.P2_BOTH_FAIL) and e7h.P2R_BOTH_FAIL.endswith(
        "F5 is raised only if F5 passes the test where neither allowance does")
    d = run(day=0.05)
    assert d["complete"] and d["passes"] is False and not d["allowance"]["test3"]
    assert d["decision"] == e7h.P2R_BOTH_FAIL
    d = run(week=0.02)
    assert not d["allowance"]["test2"] and d["decision"] == e7h.P2R_BOTH_FAIL
    d = run(guarded=[_guarded("Sublet", aborted=True)])                          # test (1): a Proposition-P abort
    assert not d["allowance"]["test1"] and d["allowance"]["guard"]["n_aborts_s_fb_bound_form"] == 1
    assert d["passes"] is False and d["decision"] == e7h.P2R_BOTH_FAIL
    assert run(guarded=[_guarded("Sublet", aborted=True, s_fb_all=False)])["passes"]       # S switched to R
    d = run(guarded=[_guarded("Sublet", env_ok=False)])
    assert d["passes"] is False and d["decision"] == e7h.P2R_BOTH_FAIL
    # a Sublet run missing: incomplete, whatever the prices
    d = run(skip={("119", "L-co"), ("b16:c104", "shared")})
    assert not d["complete"] and d["passes"] is None and d["decision"] == e7h.P2R_INCOMPLETE
    assert {(x["cell"], x["mode"]) for x in d["missing_sublet_runs"]} == {("119", "L-co"), ("b16:c104", "shared")}
    assert not d["missing_references"] and d["allowance"]["passes"]       # the tests on the 51 present runs pass
    # the determinism check: p0r's one-day runs equal, then one off
    p0r = e7h.jobs(["p0r"])
    _write_part(root / "p0r", p0r, "Sublet", lambda c, m: _base(c, m) + 0.001)
    dm = run()["determinism_p0r"]
    assert dm["source"] == "runs" and dm["n_compared"] == dm["n_equal"] == 29 and dm["equal"] is True
    _write_part(root / "p0r", p0r, "Sublet", lambda c, m: _base(c, m) + (0.0011 if c == "I4:c12" else 0.001))
    dm = run()["determinism_p0r"]
    assert dm["equal"] is False and dm["n_equal"] == 28 and [x["cell"] for x in dm["unequal"]] == ["I4:c12"]
    assert run()["decision"] == "keep the alternative allowance"               # the check decides nothing
    shutil.rmtree(root / "p0r")
    # no one-day reference (p1 absent): incomplete, the 29 one-day cells listed
    shutil.rmtree(root / "p1")
    d = run()
    assert d["decision"] == e7h.P2R_INCOMPLETE and d["passes"] is None and d["a9_sources"]["p1"] == "none"
    assert len(d["missing_references"]) == 29 and all(not x["cell"].isdigit() for x in d["missing_references"])
    assert d["allowance"]["median_day"] is None
    # no week reference (p1r absent): incomplete, the 24 week cells listed
    mc.dump_json({"runs": p1}, root / "p1" / "summary.json")
    shutil.rmtree(root / "p1r")
    d = run()
    assert d["decision"] == e7h.P2R_INCOMPLETE and d["a9_sources"]["p1r"] == "none"
    assert len(d["missing_references"]) == 24 and all(x["cell"].isdigit() for x in d["missing_references"])


def test_decide_p1r_is_a_record(monkeypatch, tmp_path):
    monkeypatch.delenv(e7h.REDUCED_ENV, raising=False)
    out = tmp_path / "p1r"
    js = e7h.jobs(["p1r"])
    _write_part(out, js, "A9", lambda c, m: 0.55 + (0.2 if m in m5.stress_modes() else 0.0) + (0.01 * (m == "L-co")))
    d = e7h.decide_p1r(e7h.collect(out, js))
    assert d["weeks"] == ["117", "118", "119", "120"] and d["n_runs"] == 24 and d["missing"] == 0
    assert d["trace"] == {c: pytest.approx(0.55) for c in d["weeks"]}
    assert d["W0"] == {c: pytest.approx(0.76) for c in d["weeks"]} and "not reapplied" in d["note"]


def _fam_job(fam: str, inst: str, seeds) -> mc.Job:
    return mc.Job(e7h.job_id(e7h.EXP, "p3r", k="fam", src=fam, inst=inst, mode="F-ad"), "pool",
                  {"part": "p3r", "kind": "fam", "family": {"id": fam, "fam": fam}, "inst": inst, "mode": "F-ad",
                   "entries": [["Sublet", list(seeds)]]})


def test_decide_p3r_on_synthetic_family_rows(monkeypatch):
    """decide_p3r on synthetic family rows of a small grid (F1 at seeds 10-11, F2 at 10, F3 at 10-11): H4's RR-renew
    wording only with every F1/F2 run present and ok and none projected; a missing (or not ok) F1/F2 run leaves the
    wording undecided, a projected one gives the A9 wording; F3's ratios and aborts over the ok runs only; LB'(T) and
    B(T) against OPT; the default grid is jobs(['p3r'])."""
    monkeypatch.delenv(e7h.REDUCED_ENV, raising=False)
    js = [_fam_job("F1", "F1_a", (10, 11)), _fam_job("F2", "F2_a", (10,)), _fam_job("F3", "F3_a", (10, 11))]

    def row(fam, inst, seed, proj=0, ratio=1.0, aborted=False, t_a=None, s_fb=True, b_t=5.0, lb_t=None,
            status="ok"):
        g = {"projected_slots": proj, "aborted": aborted, "t_a": t_a, "s_fb_all": s_fb, "held": True,
             "env_ok": True, "t0g_bound_all": True, "project": True, "projection": {"K0": 0}, "B_T": b_t,
             **({} if lb_t is None else {"online_lb": {"LB_T": lb_t, "Wk_T": 7.0, "B_T": b_t, "n_groups": 1}})}
        return {"job": next(j.id for j in js if j.params["inst"] == inst), "kind": "fam", "tag": "Sublet", "fam": fam,
                "inst": inst, "cell": f"{inst}:F-ad", "mode": "F-ad", "seed": seed, "status": status,
                "ratio_opt": ratio, "opt": 10.0, "guard": g}
    rows = [row("F1", "F1_a", s, lb_t=6.0) for s in (10, 11)] + [row("F2", "F2_a", 10)] + \
        [row("F3", "F3_a", 10, ratio=1.5), row("F3", "F3_a", 11, ratio=2.5, aborted=True, t_a=0, s_fb=False)]

    def col(rs, missing=()):
        return {"rows": rs, "guarded": [{"tag": r["tag"], **r["guard"]} for r in rs], "missing": list(missing)}
    d = e7h.decide_p3r(col(rows), js)
    assert d["sublet_projected_runs_f1f2"] == 0 and d["sublet_runs_f1f2"] == d["sublet_runs_f1f2_expected"] == 3
    assert d["missing_runs_f1f2"] == 0 and "h4_undecided" not in d
    assert d["h4_wording"] == "the deployed policy equals RR-renew on F1/F2"
    assert d["f3_ratio_opt"] == {"mean": pytest.approx(2.0), "max": 2.5, "n": 2} and d["f3_not_ok"] == []
    assert (d["f3_aborts"], d["f3_aborts_t_a_0"], d["f3_aborts_s_not_fb"]) == (1, 1, 1)
    assert d["guard"]["aborts"] == 1 and d["guard"]["n_aborts_s_fb_bound_form"] == 0 and d["guard"]["n_runs"] == 5
    assert d["allowance_vs_opt"]["n_checked"] == 5 and d["allowance_vs_opt"]["n_over"] == 0
    assert d["allowance_vs_opt"]["max_ratio"] == pytest.approx(0.5)
    assert d["lb_vs_opt"]["n_checked"] == 2 and d["lb_vs_opt"]["n_over"] == 0
    assert d["lb_vs_opt"]["max_ratio"] == pytest.approx(0.6)
    rows[2] = row("F2", "F2_a", 10, b_t=10.5)                                    # B(T) above OPT: listed
    assert e7h.decide_p3r(col(rows), js)["allowance_vs_opt"]["over"][0]["B_T"] == 10.5
    rows[2] = row("F2", "F2_a", 10, b_t=5.0, lb_t=10.5)     # LB'(T) above OPT while B(T) = W_k binds below it: caught
    d = e7h.decide_p3r(col(rows), js)
    assert d["lb_vs_opt"]["n_over"] == 1 and d["lb_vs_opt"]["over"][0]["LB_T"] == 10.5
    assert d["allowance_vs_opt"]["n_over"] == 0
    # a missing F2 run (collect's missing list): H4's wording undecided
    miss = [{"job": js[1].id, "tag": "Sublet", "mode": "F-ad", "cell": "F2_a:F-ad", "seed": 10, "why": "oom_at_3G"}]
    d = e7h.decide_p3r(col(rows[:2] + rows[3:], miss), js)
    assert d["h4_wording"] is None and d["missing_runs_f1f2"] == 1 and "1 of 3" in d["h4_undecided"]
    assert d["missing_f1f2"] == [{"job": js[1].id, "cell": "F2_a:F-ad", "seed": 10, "why": "oom_at_3G"}]
    # a run that is present but not ok is in collect's missing list too, and not counted as an F1/F2 run
    bad = row("F2", "F2_a", 10, status="invariant_failure")
    d = e7h.decide_p3r(col(rows[:2] + [bad] + rows[3:], [{**miss[0], "why": "invariant_failure"}]), js)
    assert d["h4_wording"] is None and d["sublet_runs_f1f2"] == 2
    d = e7h.decide_p3r(col(rows[:2] + rows[3:]), js)                  # fewer runs than the grid, nothing listed
    assert d["h4_wording"] is None and d["missing_runs_f1f2"] == 0 and d["sublet_runs_f1f2"] == 2
    # a projected run gives the A9 wording, also with another run missing
    rows[2] = row("F2", "F2_a", 10)
    rows[1] = row("F1", "F1_a", 11, proj=3)
    d = e7h.decide_p3r(col(rows), js)
    assert d["sublet_projected_runs_f1f2"] == 1 and d["projected_runs_f1f2"][0]["projected_slots"] == 3
    assert d["h4_wording"] == "the identity holds for A9; Sublet projects in the counted runs"
    assert e7h.decide_p3r(col(rows[:2] + rows[3:], miss), js)["h4_wording"] == d["h4_wording"]
    rows[3] = row("F3", "F3_a", 10, ratio=1.5, aborted=True)                     # S on FB, T0g bound: Proposition P
    assert e7h.decide_p3r(col(rows), js)["guard"]["n_aborts_s_fb_bound_form"] == 1
    # F3: a run that is not ok is listed apart, not in the ratios or the aborts
    rows[4] = row("F3", "F3_a", 11, ratio=9.0, aborted=True, t_a=0, s_fb=False, status="invariant_failure")
    d = e7h.decide_p3r(col(rows), js)
    assert d["f3_ratio_opt"] == {"mean": 1.5, "max": 1.5, "n": 1} and d["f3_aborts"] == 1
    assert d["f3_not_ok"] == [{"inst": "F3_a", "mode": "F-ad", "seed": 11, "status": "invariant_failure"}]
    # the default grid: P3's 95 jobs; its F1/F2 runs at seeds 10-12
    full = e7h.jobs(["p3r"])
    n12 = sum(1 for j in full if j.params["family"].get("fam") in ("F1", "F2") for _x in e7h.expected_runs(j))
    assert e7h.decide_p3r(col([]))["sublet_runs_f1f2_expected"] == n12 == 243


def test_decide_p4_takes_sublets_shared_runs_from_p2r(monkeypatch, tmp_path):
    """decide_p4 reuses Sublet's shared E3 runs from the sibling p2r only when the run was made at Sublet's current
    allowance (sublet_v2_params' 'lb'): p2's runs (Algorithm 1's allowance) are never read, a p2r run at Algorithm 1's
    allowance or a failed one leaves the cell missing, and the summary records the source, the allowance, the excluded
    runs and the missing cells."""
    monkeypatch.delenv(e7h.REDUCED_ENV, raising=False)
    root = tmp_path / "pilot"
    out = root / "p4"
    mc.dump_json({"status": 0, "objective": 40.0}, out / "lp.json")
    col = {"rows": [], "files": {"x": {"kind": "e3cell", "b": 1, "c": 101, "instances": {"shared": "h"},
                                       "lps": {"shared": {"file": "lp.json"}}}}}
    alg1 = {"inner": "A9", "project": True, "gamma": 1.0, "B0": "auto", "kappa": 10.0}
    lb = {**m5.sublet_v2_params(), "gamma": 1.0, "B0": "auto"}

    def cell(part, alg, params, inv=0):
        jid = e3.cell_id(1, 8, 1.0, 101)
        run = {"tag": "Sublet", "mode": "shared", "p": 0, "ALG": alg, "r0": alg / 100.0, "n_invariant_failures": inv,
               "params": params}
        _write_job(root / part, jid, "ok", kind_path=e3.cell_file(root / part, 1, 8, 1.0, 101), runs=[run])
        f = e3.cell_file(root / part, 1, 8, 1.0, 101)
        d = json.loads(f.read_text())
        d.update(kind="e3cell", b=1, c=101, instances={"shared": "h"})
        f.write_text(json.dumps(d))
    assert m5.sublet_v2_params()["allowance"] == "lb"
    cell("p2", 60.0, alg1)                                        # p2's run at Algorithm 1's allowance: never read
    d = e7h.decide_p4(col, out)
    assert d["sublet_shared_from"] == "none" and "Sublet:b1:c101" not in d["shared_runs_reused"]
    assert "Sublet:shared" not in d["ratios"] and d["sublet_shared_missing"] == ["b1:c101"]
    assert d["sublet_shared_allowance"] == "lb" and d["sublet_shared_excluded"] == []
    cell("p2r", 55.0, alg1)                                       # a p2r run at Algorithm 1's allowance: missing
    d = e7h.decide_p4(col, out)
    assert d["sublet_shared_from"] == "none" and d["sublet_shared_missing"] == ["b1:c101"]
    assert d["sublet_shared_excluded"] == [{"cell": "b1:c101", "allowance": "alg1"}]
    cell("p2r", 50.0, lb, inv=1)                                  # a failed run at 'lb': missing
    d = e7h.decide_p4(col, out)
    assert d["sublet_shared_from"] == "none" and d["sublet_shared_missing"] == ["b1:c101"]
    cell("p2r", 50.0, lb)
    d = e7h.decide_p4(col, out)
    assert d["sublet_shared_from"] == "p2r" and d["shared_runs_reused"]["Sublet:b1:c101"]["ALG"] == 50.0
    assert d["ratios"]["Sublet:shared"]["b1:c101"] == pytest.approx(1.25) and d["sublet_shared_missing"] == []


def test_decide_p2_reproduces_its_recorded_decision(monkeypatch):
    """decide_p2 (and allowance_tests, shared with decide_p2r) unchanged: P2's recorded decision in the repository's
    out/sublet_v2_pilot/p2/summary.json is recomputed exactly from that summary's rows and p1's summary rows (the
    copies keep no runs/, so p1's rows are read through _sibling_rows' summary.json fallback)."""
    base = SIM / "out" / "sublet_v2_pilot"
    if not (base / "p2" / "summary.json").is_file() or not (base / "p1" / "summary.json").is_file():
        pytest.skip("the pilot's p1 and p2 summaries are not in this checkout")
    from sublet.experiments import e7
    s2 = json.loads((base / "p2" / "summary.json").read_text())
    col = {"rows": s2["runs"], "guarded": s2["guarded"], "table": s2["table"], "missing": s2["missing"]}
    monkeypatch.setattr(e7h, "_rows_of", lambda part, out_p: json.loads(
        (Path(out_p).parent / part / "summary.json").read_text())["runs"])
    d = json.loads(json.dumps(e7._jsonish(e7h.decide_p2(col, base / "p2"))))
    assert d == s2["decision"]
    assert d["decision"].startswith("build the alternative (algos/online_lb.py)")


# ---------------------------------------------------------------- the gates (§4.3, §5)
def _conf_rec(**kw):
    rec = {"head": "h", "prereg_at_head": True, "analysis_sha256_prereg": "a" * 64, "analysis_sha256_head": "a" * 64,
           "analysis_sha256_disk": "a" * 64, "dirty_paths": [], "pilot": {}}
    rec.update(kw)
    return rec


def test_confirmation_gate_refusals():
    assert m5.check_confirmation(_conf_rec())[0] is True
    ok, why, _ = m5.check_confirmation(_conf_rec(prereg_at_head=False, analysis_sha256_prereg=None))
    assert not ok and "does not exist at HEAD" in why
    ok, why, _ = m5.check_confirmation(_conf_rec(dirty_paths=[" M code/sim/sublet/algos/a9.py"]))
    assert not ok and "dirty" in why
    ok, why, _ = m5.check_confirmation(_conf_rec(analysis_sha256_disk="b" * 64))
    assert not ok and "analysis_sha256_disk" in why
    ok, why, _ = m5.check_confirmation(_conf_rec(analysis_sha256_prereg=None))
    assert not ok and "records no line" in why
    ok, why, _ = m5.check_confirmation(_conf_rec(dirty_paths=None))
    assert not ok and "cannot tell" in why
    text = "# Pre-registration\n\nanalysis_sha256: " + "c" * 64 + "\n"
    assert m5.prereg_sha256_recorded(text) == "c" * 64 and m5.prereg_sha256_recorded("no hash") is None


def test_dirty_paths_ignore_the_run_outputs(monkeypatch):
    porcelain = (" M code/sim/sublet/algos/a9.py\n?? code/sim/out/sublet_v2/main/\n?? code/sim/sublet/x.py\n"
                 "?? code/sim/out/sublet_v2/main/jobs/a.json\n")
    monkeypatch.setattr(m5, "git", lambda *a: porcelain)
    assert m5.dirty_paths() == [" M code/sim/sublet/algos/a9.py", "?? code/sim/sublet/x.py"]
    monkeypatch.setattr(m5, "git", lambda *a: None)
    assert m5.dirty_paths() is None


def test_gate_of_the_parts(monkeypatch, tmp_path):
    monkeypatch.delenv(e7h.REDUCED_ENV, raising=False)
    monkeypatch.setattr(e7h, "_GATE", {})
    monkeypatch.setattr(m5, "check_pilot", lambda rec=None: (False, "anchor not an ancestor", {}))
    with pytest.raises(RuntimeError, match="anchor not an ancestor"):
        e7h.gate("p1")
    monkeypatch.setattr(m5, "check_confirmation", lambda rec=None: (False, "no pre-registration", {}))
    with pytest.raises(RuntimeError, match="no pre-registration"):
        e7h.gate("main")
    # a refused job: run() raises, so its record says 'error' and no output is written
    j = next(j for j in e7h.jobs(["main"]))
    rec = mc.run_job("e7h", j, lambda o: e7h.run(j, o, tmp_path), tmp_path, resume=False)
    assert rec["status"] == "error" and "no pre-registration" in rec["error"]
    assert not (tmp_path / "runs").exists()
    # reduced runs record the confirmation gate without enforcing it
    monkeypatch.setattr(e7h, "_GATE", {})
    monkeypatch.setenv(e7h.REDUCED_ENV, "1")
    g = e7h.gate("main")
    assert g["ok"] is False and g["enforced"] is False and "not enforced" in g["note"]
    monkeypatch.setattr(e7h, "_GATE", {})
    with pytest.raises(RuntimeError):
        e7h.gate("p0")                                  # the pilot anchor is enforced in reduced runs too
    monkeypatch.setattr(m5, "check_pilot", lambda rec=None: (True, "ok", {"anchor": m5.PILOT_ANCHOR}))
    monkeypatch.setattr(e7h, "_GATE", {})
    assert e7h.gate("p0")["ok"] is True


def test_this_repository_passes_the_pilot_gate_and_not_the_confirmation():
    if not (REPO / ".git").exists():
        pytest.skip("not a git checkout")
    ok, why, rec = m5.check_pilot()
    assert ok, why
    assert rec["anchor"] == m5.PILOT_ANCHOR and rec["head"] and re.fullmatch(r"[0-9a-f]{64}", rec["spec_sha256_head"])
    assert rec["sections_changed_since_anchor"] is not None
    assert m5.check_pilot({"anchor_is_ancestor": False, "head": "x"})[0] is False
    if not (REPO / m5.PREREG).exists():
        assert m5.check_confirmation()[0] is False


def test_sections_of_the_note():
    text = "x\n## 4. Protocol\nA\n## 5. Pilot P0-P6\nB\n## 6. Confirmation hypotheses\nC\n## 7. Fallbacks\nD\n"
    s = m5.sections(text, ("5", "6"))
    assert s == {"5": "## 5. Pilot P0-P6\nB\n", "6": "## 6. Confirmation hypotheses\nC\n"}


# ---------------------------------------------------------------- tags, modes, L-hon and RC (§2.3, §3, §4.5)
def test_tags_as_the_note_states():
    for t, (pid, params) in SPEC_TAGS.items():
        assert m5.TAGS[t].id == pid, t
        if params is not None:
            assert m5.tag_params(t) == params, t
    lb = {"inner": "A9", "project": True, "allowance": "lb", "kappa": None}     # P2's decision (pilot log, P2)
    assert m5.sublet_v2_params() == lb and m5.sublet_v2_params(object()) == lb
    assert m5.TAGS["NBR-repro-G"].params == {"inner": "A9", "inner_params": SPEC_TAGS["NBR-repro"][1], "safe": "fb"}
    assert m5.tag_params("A9-lag") == {"demand_lag": 1} and m5.tag_params("BL1-lag") == {"demand_lag": 1}
    assert m5.TAGS["MARKING"].information == "I2"
    assert m5.H1_SET == ("BL1", "BL1-BO", "BL2", "BL3-0", "BL4", "BL5", "BL5-cur")
    assert m5.H2B_SET == ("BL5-tau60", "BL1-GP", "BL1N", "BL5N")
    assert m5.seed_free("A9") and m5.seed_free("A9-noIns") and m5.seed_free("BL1N")
    assert not m5.seed_free("CR") and not m5.seed_free("RCRb-repro") and not m5.seed_free("Sublet")
    with pytest.raises(ValueError, match="need the instance"):
        m5.tag_params("Sublet")
    assert m5.RULE_ALT == "mix:0:1:1:Wk" and m5.PROTO["Proto-F5"]["rule"] == "alg1"


def test_lender_modes():
    assert m5.L_HON == {"schedule": "iid_step", "params": {"D_slots": 1, "p": 0.0}}
    assert m5.mode_lender_model("L-hon") == m5.L_HON and m5.mode_lender_model("L-tr") == {}
    assert m5.mode_lender_model("L-iid-0.34") == {"schedule": "iid_step", "params": {"D_slots": 1, "p": 0.34}}
    assert m5.mode_lender_model("L-iid-0.05")["params"]["p"] == 0.05            # q44_study's mode
    assert m5.mode_lender_model("L-b999") == {} and m5.mode_overrides("L-b999") == {"prices.buffer_quantile": "p99.9"}
    assert m5.mode_overrides("L-eg") == {} and m5.instance_key("L-b999") == "b999"
    assert [m5.iid_mode(p) for p in m5.IID_P5] == ["L-hon", "L-iid-0.05", "L-iid-0.1", "L-iid-0.2", "L-iid-0.34",
                                                   "L-iid-0.5", "L-iid-0.8", "L-iid-1"]
    for bad in ("L-x", "L-iid-0", "L-iid-1.5", "L-iid-0.340"):
        with pytest.raises(ValueError):
            m5.mode_lender_model(bad)
    assert m5.stress_modes() == ("L-eg", "L-ss", "L-iid-0.05", "L-iid-0.2", "L-co")
    s = m5.week_spec("A9", {}, mode="L-hon", c=301, horizon_min=120, seeds=(0,))
    assert s["lender_model"] == m5.L_HON and s["seeds"]["config"] == [301]
    assert s["overrides"]["time.horizon_min"] == 120 and s["overrides"]["stranding.mu_over_beta_tilde"] == 1.0


def test_l_hon_has_no_announcement_and_rc_is_the_paired_difference():
    """BL1 on ms2_multi_small (two hours) under the config's trace lender and under L-hon: no announcement, no
    refusal, no violation under L-hon; rc_rows gives r0(L-tr) - r0(L-hon) per week, policy and seed."""
    from sublet.drivers import run as drun
    from sublet.engine import simulate
    rows = []
    for mode, lm in (("L-tr", {}), ("L-hon", m5.L_HON)):
        spec = drun.load_run_spec({"schema_version": 1, "name": f"hon_{mode}", "instance": "ms2_multi_small.json",
                                   "overrides": {"time.horizon_min": 120}, "lender_model": lm,
                                   "policy": {"id": "BL1", "params": {}}})
        inst, model, ecfg = drun.build(spec, 1)
        res = simulate(inst, drun.make_policy(spec, inst), model, ecfg, lender_seed=1, policy_seed=0)
        if mode == "L-hon":
            assert model.schedule == "iid_step" and all(len(r) == 0 for r in res.schedule.R)
            assert int((res.metrics.get("refused") or {}).get("unavailable", 0)) == 0
            assert not res.violations and not any(L.end_cause in ("reclaim", "violation") for L in res.leases)
        rows.append({"tag": "BL1", "mode": mode, "config_seed": 1, "policy_seed": 0, "status": "ok",
                     "r0": float(res.components["total"]) / 1000.0, "n_invariant_failures": 0})
    rc = m5.rc_rows(rows)
    assert rc == {"BL1": {"L-tr": {"1": {"0": rows[0]["r0"] - rows[1]["r0"]}}}}
    bad = copy.deepcopy(rows)
    bad[1]["n_invariant_failures"] = 1                                    # a failed L-hon run: no RC
    assert m5.rc_rows(bad) == {}


# ---------------------------------------------------------------- statistics (§4.5)
def test_sign_test_twelve_of_sixteen():
    s = m5.sign_test_p(12, 16)
    assert (s["numerator"], s["denominator"]) == (2517, 65536)
    assert s["p"] == m5.SIGN_P_12_OF_16 == 2517 / 65536 and round(s["p"], 4) == 0.0384
    assert m5.sign_test_p(0, 16)["p"] == 1.0 and m5.sign_test_p(16, 16)["numerator"] == 1


def test_bootstrap_with_its_fixed_seed():
    x = [0.03, 0.05, -0.01, 0.02, 0.04, 0.06, 0.01, 0.02, 0.03, -0.02, 0.05, 0.04, 0.02, 0.01, 0.03, 0.07]
    b = m5.bootstrap_median_ci(x)
    assert (b["B"], b["seed"], b["n"]) == (10000, 20261031, 16) and m5.BOOT_SEED == 20261031
    v = np.asarray(x)
    idx = np.random.default_rng(20261031).integers(0, 16, size=(10000, 16))
    lo, hi = np.percentile(np.median(v[idx], axis=1), [2.5, 97.5])
    assert b["ci"] == [float(lo), float(hi)] and b["median"] == float(np.median(v))
    assert m5.bootstrap_median_ci(x) == b                                 # deterministic
    assert m5.bootstrap_median_ci([])["median"] is None


def test_wilcoxon_exact_against_an_enumeration():
    rng = np.random.default_rng(3)
    for n in (1, 5, 9, 12):
        x = list(np.round(rng.normal(0.01, 0.03, size=n), 2)) + [0.0]          # ties and a zero
        w = m5.wilcoxon_signed_rank(x)
        nz = [a for a in x if a != 0]
        absr = np.abs(nz)
        ranks = np.array([np.mean([i + 1 for i, b in enumerate(np.sort(absr)) if b == a]) for a in absr])
        wp = ranks[np.asarray(nz) > 0].sum()
        tot = 0
        for mask in range(2 ** len(nz)):
            s = sum(ranks[i] for i in range(len(nz)) if mask >> i & 1)
            tot += s >= wp - 1e-12
        assert w["W_plus"] == pytest.approx(wp) and w["p"] == pytest.approx(tot / 2 ** len(nz)), n
        assert w["zeros_dropped"] == sum(1 for a in x if a == 0) >= 1


def test_paired_margins_and_the_missing_run_rule():
    sub = {"1": 0.5, "2": 0.6, "3": None}
    oth = {"BL1": {"1": 0.7, "2": 0.55, "3": 0.8}, "BL5": {"1": 0.65, "2": None, "3": 0.9}}
    m = m5.paired_margins(sub, oth, ["1", "2", "3"])
    assert m["1"]["delta"] == pytest.approx(0.15) and m["1"]["best"] == "BL5"
    assert m["2"]["delta"] is m5.LOSS and m["2"]["missing"] == ["BL5"]       # another policy's run is missing
    assert m["3"]["delta"] is m5.LOSS and m["3"]["missing"] == ["Sublet"]
    assert m5.run_status(None) == "missing" and m5.run_status({"r0": 1.0}) == "ok"
    assert m5.run_status({"r0": 1.0, "n_invariant_failures": 2}) == "invariant_failure"
    assert m5.run_status({"r0": 1.0, "sub_runs": [{"n_invariant_failures": 1}]}) == "invariant_failure"
    c = m5.intensity_curve({0.0: 0.6, 0.1: 0.8, 0.2: None, 0.34: 1.2, 0.5: 1.4})
    assert c["first_p_above_1"] == 0.34 and c["first_p_note"] and c["points"][0] == [0.0, 0.6]
    w, mode, miss = m5.w0_of({"L-eg": 0.7, "L-ss": 0.9, "L-iid-0.05": 0.6, "L-iid-0.2": 0.8, "L-co": 0.9})
    assert (w, mode, miss) == (0.9, "L-ss", [])
    assert m5.w0_of({"L-eg": 0.7})[0] is None


def _write_job(out: Path, jid: str, status: str, runs=None, errors=None, kind_path=None):
    rec = {"job": jid, "status": status, "n_errors": len(errors or []), "git_revision": "x"}
    mc.dump_json(rec, mc.record_path(out, jid))
    if runs is not None:
        mc.dump_json({"meta": {"git_revision": "x"}, "runs": runs, "errors": errors or []},
                     kind_path or e7h.run_path(out, jid))


def _entry(tag, mode, c, r0, inv=0):
    return {"tag": tag, "mode": mode, "policy_seed": 0, "config_seed": c, "r0": r0, "ALG": 100.0 * r0,
            "n_invariant_failures": inv, "status": "invariant_failure" if inv else "ok"}


def test_missing_run_rule_on_synthetic_job_records(monkeypatch, tmp_path):
    """collect() lists a job without an 'ok' record, a run that raised and a run with an invariant failure as missing
    (null in the table); retry_list moves each such record to retry/ once; the analysis counts the week as a loss."""
    monkeypatch.delenv(e7h.REDUCED_ENV, raising=False)
    out = tmp_path / "main"
    js = [j for j in e7h.jobs(["main"]) if j.params["c"] == 301 and j.params["tag"] in ("Sublet", "BL1", "BL2")]
    by = {j.params["tag"]: j for j in js}
    modes = list(m5.conf_modes())
    _write_job(out, by["Sublet"].id, "ok", [_entry("Sublet", m, 301, 0.5, inv=int(m == "L-eg")) for m in modes])
    _write_job(out, by["BL1"].id, "ok", [_entry("BL1", m, 301, 0.7) for m in modes if m != "L-ss"],
               errors=[{"tag": "BL1 L-ss p0", "error": "ValueError: boom"}])
    _write_job(out, by["BL2"].id, "oom_at_3G")
    col = e7h.collect(out, js)
    t = col["table"]
    assert t["Sublet"]["L-tr"]["301"]["0"] == 0.5 and t["Sublet"]["L-eg"]["301"]["0"] is None
    assert t["BL1"]["L-ss"]["301"]["0"] is None and t["BL2"]["L-tr"]["301"]["0"] is None
    why = {(x["tag"], x["mode"]): x["why"] for x in col["missing"]}
    assert why[("Sublet", "L-eg")] == "invariant_failure" and why[("BL1", "L-ss")] == "ValueError: boom"
    assert why[("BL2", "L-tr")] == "oom_at_3G" and len(why) == 1 + 1 + len(modes)
    lines = e7h.retry_list(out)
    assert sorted(lines) == sorted(f"pool {by[t].id}" for t in ("Sublet", "BL1", "BL2"))
    assert all((out / "retry" / mc.job_file_name(by[t].id)).is_file() for t in by)
    assert not mc.record_path(out, by["Sublet"].id).exists() and not e7h.run_path(out, by["Sublet"].id).exists()
    assert (out / "runs" / "retry" / mc.job_file_name(by["Sublet"].id)).is_file()
    assert e7h.retry_list(out) == []                                       # one rerun only
    # the analysis: the week whose Sublet W0 run failed is a loss of H2
    s = {"table": t}
    assert ma.h2(s)["weeks_below_set"] == 0


# ---------------------------------------------------------------- the analysis on synthetic summaries (§6)
def _table(weeks, val):
    t: dict = {}
    for tag in set(m5.E7_TAGS):
        for m in m5.conf_modes():
            for w in weeks:
                t.setdefault(tag, {}).setdefault(m, {})[str(w)] = {"0": val(tag, m, w)}
    return t


def test_analysis_hypotheses_on_synthetic_summaries(monkeypatch):
    weeks = list(range(301, 317))

    def val(tag, m, w):
        base = {"Sublet": 0.55, "A9": 0.548}.get(tag, 0.62)
        if m in m5.stress_modes():
            base += {"Sublet": 0.2, "A9": 0.21}.get(tag, 0.5)
        if tag == "Sublet" and m == "L-tr" and w in (301, 302, 303):
            base = 0.70                                                    # three weeks lost on the trace
        return base
    main = {"table": _table(weeks, val), "guarded": [], "missing": []}
    h1 = ma.h1(main)
    assert h1["wins"] == 13 and h1["n_weeks"] == 16 and h1["sign_test"]["numerator"] == \
        sum(__import__("math").comb(16, i) for i in range(13, 17))
    assert h1["median_margin"]["median"] == pytest.approx(0.07) and h1["pass"] is True
    h2 = ma.h2(main)
    assert h2["pass"] is True and h2["weeks_below_1"] == 16 and h2["median_W0"] == pytest.approx(0.75)
    assert ma.h2(main, m5.H2B_SET, "secondary")["pass"] is True
    h6 = ma.h6(main)                                    # 80 stress runs at 0.75 - 0.758, 16 trace runs above
    assert h6["median_price"] == pytest.approx(-0.008) and h6["pass"] is True and h6["n"] == 96
    # a missing Sublet run loses its week everywhere
    main2 = copy.deepcopy(main)
    main2["table"]["Sublet"]["L-tr"]["310"]["0"] = None
    h1b = ma.h1(main2)
    assert h1b["wins"] == 12 and h1b["margins"]["310"]["delta"] is None and h1b["median_margin"]["n_loss_weeks"] == 1
    main2["table"]["A9"]["L-eg"]["305"]["0"] = None
    assert ma.h6(main2)["n_loss"] == 2
    # H3: a Proposition-P abort of an A8P run fails it; an A8 abort with S switched does not
    g = [{"tag": "Sublet", "held": True, "env_ok": True, "aborted": False, "project": True},
         {"tag": "Sublet-MS4", "held": True, "env_ok": True, "aborted": True, "s_fb_all": True, "t0g_bound_all": True,
          "project": None},
         {"tag": "Sublet-1way", "held": True, "env_ok": True, "aborted": True, "s_fb_all": True, "t0g_bound_all": True,
          "project": False}]
    h3 = ma.h3({"main": {"guarded": g, "missing": []}})
    assert h3["pass"] is True and h3["one_way_aborts"] == 2
    g.append({"tag": "Sublet", "held": True, "env_ok": True, "aborted": True, "s_fb_all": True, "t0g_bound_all": True,
              "project": True})
    h3 = ma.h3({"main": {"guarded": g, "missing": []}})
    assert h3["pass"] is False and h3["n_aborts_s_fb_bound_form"] == 1
    g[-1] = {**g[-1], "aborted": False, "env_ok": False}
    assert ma.h3({"main": {"guarded": g, "missing": []}})["n_envelope_violations"] == 1
    assert ma.h3({"main": {"guarded": g[:1], "missing": [{"tag": "Sublet", "mode": "L-tr", "cell": "301",
                                                          "seed": 0, "why": "oom_at_3G"}]}})["pass"] is False
    # H4 on family rows: counted fresh and Q6 F-ss runs; a projected Sublet run fails it
    rows = []
    for inst, src, mode in (("CF1_m5_r7", "CF1", "F-ad"), ("F2_m2_r4", "F2", "F-ss"), ("F2_m2_r4", "F2", "F-eg")):
        for t in ("A9", "RR_RENEW", "Sublet"):
            rows.append({"kind": "fam", "inst": inst, "src": src, "fam": src[-2:] if src.startswith("C") else src,
                         "mode": mode, "seed": 13, "tag": t, "status": "ok", "total": 10.0, "n_purchases": 3,
                         "guard": {"projected_slots": 0} if t == "Sublet" else None})
    rows[0]["fam"] = rows[1]["fam"] = rows[2]["fam"] = "F1"
    h4 = ma.h4({"runs": rows, "missing": []})
    assert h4["n_counted_pairs"] == 2 and h4["pass"] is True                # F2 under F-eg is not counted
    rows[2]["guard"] = {"projected_slots": 4}
    assert ma.h4({"runs": rows, "missing": []})["pass"] is False
    # P3's wording 'A9' (§6): the identity for A9 alone decides, Sublet's projecting runs are reported
    monkeypatch.setitem(ma.CONFIG, "H4_wording", "A9")
    h4a = ma.h4({"runs": rows, "missing": []})
    assert h4a["pass"] is True and h4a["sublet_projected_runs"] == 1 and h4a["wording"] == "A9"
    rows[0]["total"] = 11.0
    assert ma.h4({"runs": rows, "missing": []})["pass"] is False
    rows[0]["total"] = 10.0
    monkeypatch.setitem(ma.CONFIG, "H4_wording", "deployed")
    # H5 on E3 ratios
    e3s = {"e3": {f"b{b}:c{c}": {"ratios": {"Sublet:shared": 1.2, "Sublet-MS4:shared": 1.5,
                                             "Sublet:siloed": 1.2 + 0.1 * (b > 1)}}
                  for b in (1, 2, 4) for c in (301, 302, 303, 304)}}
    assert ma.h5(e3s)["pass"] is True and ma.h5(e3s)["kind"] == ma.CONFIG["H5_status"]
    e3s["e3"]["b4:c301"]["ratios"]["Sublet:siloed"] = 1.0
    e3s["e3"]["b4:c302"]["ratios"]["Sublet:siloed"] = 1.0
    assert ma.h5(e3s)["pass"] is False
    a = ma.analyse({"main": main, "fam": {"runs": rows, "missing": []}, "e3": e3s})
    assert set(a) >= {"H1", "H2", "H2b", "H3", "H4", "H5", "H6", "reported"}
    assert a["reported"]["pareto_front"]["301"]
    json.dumps(mc.jsonable(a), allow_nan=False)


def test_intensity_curve_and_rc_across_parts():
    """§4.5: the stress-intensity curve merges main's iid_step grid (p = 0, 0.05, 0.2) with second's (0.1, 0.34, 0.5,
    0.8, 1) per tag, week and seed before the first p with r0 > 1 is found; a week without second's runs has (a)'s
    points only. RC under second's modes pairs each run with main's L-hon run of the same tag, week and seed."""
    main_tab = {"BL1": {m5.iid_mode(p): {"301": {"0": v}, "305": {"0": v}}
                        for p, v in ((0.0, 0.6), (0.05, 0.8), (0.2, 0.95))}}
    sec_tab = {"BL1": {m5.iid_mode(p): {"301": {"0": v}}
                       for p, v in ((0.1, 0.9), (0.34, 1.05), (0.5, 1.2), (0.8, 1.3), (1.0, 1.4))}}
    parts = {"main": {"table": main_tab}, "second": {"table": sec_tab}}
    cv = ma.intensity_curves(parts)
    assert cv["BL1"]["301"]["first_p_above_1"] == 0.34 and len(cv["BL1"]["301"]["points"]) == 8
    assert cv["BL1"]["305"]["first_p_above_1"] is None and len(cv["BL1"]["305"]["points"]) == 3
    assert "first_p_note" not in cv["BL1"]["305"]
    assert ma.reported(parts)["intensity_crossings"]["BL1"] == {"301": 0.34, "305": None}
    main_tab["BL1"]["L-iid-0.2"]["301"]["0"] = 1.01          # main alone would report 0.2; second's 0.1 comes first
    sec_tab["BL1"]["L-iid-0.1"]["301"]["0"] = 1.02
    assert ma.intensity_curves(parts)["BL1"]["301"]["first_p_above_1"] == 0.1
    sec_tab["BL1"]["L-iid-0.1"]["301"]["0"] = None           # a missing run of the grid is noted
    c = ma.intensity_curves(parts)["BL1"]["301"]
    assert c["first_p_above_1"] == 0.2 and c["first_p_note"]

    def run(mode, r0):
        return {"kind": "week", "status": "ok", "tag": "BL1", "mode": mode, "c": 301, "seed": 0, "r0": r0,
                "n_invariant_failures": 0}
    rc = ma.rc_all({"main": {"runs": [run(m5.HON_MODE, 0.6), run("L-tr", 0.7)]},
                    "second": {"runs": [run("L-vr", 0.9), {**run("L-rf", 2.0), "status": "invariant_failure"}]}})
    assert rc["BL1"]["L-vr"]["301"]["0"] == pytest.approx(0.3) and rc["BL1"]["L-tr"]["301"]["0"] == pytest.approx(0.1)
    assert "L-rf" not in rc["BL1"] and m5.HON_MODE not in rc["BL1"]


def test_analysis_script_is_deterministic(tmp_path):
    """Two runs of the analysis on the same (empty) root give the same results but for the meta block."""
    r1 = ma.analyse(ma.load(tmp_path))
    r2 = ma.analyse(ma.load(tmp_path))
    assert r1 == r2 and r1["parts_found"] == []
    assert m5.analysis_sha256() == hashlib.sha256(m5.ANALYSIS.read_bytes()).hexdigest()


# ---------------------------------------------------------------- the prototype copies (§8.1)
@pytest.mark.parametrize("name", ["lb.py", "projected.py", "run_proj.py"])
def test_prototype_copies_differ_only_in_their_scratch_paths(name):
    src = (DEV_GA / name).read_text().splitlines()
    cp = (e7h.PROTO_DIR / name).read_text().splitlines()
    head = cp[:4]
    assert all(x.startswith("# ") for x in head) and "PROTOTYPE" in head[0] and "labeled prototype" in head[3]
    assert head[1] == "# sha256 " + hashlib.sha256((DEV_GA / name).read_bytes()).hexdigest()
    body = [x for x in cp[4:] if not x.startswith("# Changed against the source") and not (
        x.startswith("# ") and cp.index(x) > len(cp) - 6)]
    diff = [(a, b) for a, b in zip(src, body) if a != b]
    assert len(body) == len(src), name
    for a, b in diff:
        assert "/work" in a or a.startswith("import collect"), (a, b)
    assert len(diff) == {"lb.py": 0, "projected.py": 1, "run_proj.py": 2}[name]


def test_prototype_modules_import_and_lb_series():
    rp, pj = e7h.proto_modules()
    assert pj.ProjectedGuard.name == "A8P" and rp.C is None
    import lb
    d = {"client_llm": np.array([0, 0]), "delta": np.array([[0.0, np.inf], [0.1, 0.0]]), "q": np.array([4.0]),
         "g": np.array([1]), "price": np.array([[1.0], [1.5]]), "beta": np.array([[0.5, 0.5]]),
         "lam_s": np.array([[60.0, 60.0]]), "prepaid_min": np.array([60]), "menu_mask": np.array([[True], [True]]),
         "demand": np.array([[0.5, 1.5, 1.0, 0.0], [1.0, 1.0, 0.2, 0.2]]), "kinf": False, "fast_min": 15, "phi": 2}
    LB, W, info = lb.lb_series(d)
    assert LB.shape == (2,) and np.all(np.diff(LB) >= 0) and len(info) == 1 and info[0]["n_sites"] == 2


# ---------------------------------------------------------------- run_e7h.sh with a fake driver
FAKE_DRIVER = '''
import json, os, sys, time
from sublet.experiments import ms3_common as mc

def jobs():
    part = os.environ.get("E7H_PART", "")
    return [mc.Job(j, k, {"part": p, "sleep": s}) for j, k, p, s in json.loads(os.environ["FAKE_JOBS"])
            if not part or p == part]

def run(job, outputs, out):
    t0 = time.time()
    time.sleep(job.params["sleep"])
    with open(os.environ["FAKE_EVENTS"], "a") as f:
        f.write(f"{job.id} {t0} {time.time()}\\n")
    return {"runs": 0}

def summary(out):
    with open(os.environ["FAKE_EVENTS"], "a") as f:
        f.write(f"summary:{os.environ.get('E7H_PART')} {time.time()} {time.time()}\\n")
    mc.dump_json({"records": len(mc.read_records(out))}, out / "summary.json")

if __name__ == "__main__":
    if "--check-start" in sys.argv:
        ok = os.environ.get("FAKE_GATE", "1") == "1"
        print(f"[e7h] {os.environ.get('E7H_PART')}: gate {'ok' if ok else 'REFUSED'}")
        sys.exit(0 if ok else 1)
    if "--retry-list" in sys.argv:
        out = sys.argv[sys.argv.index("--out") + 1]
        mark = os.path.join(out, "retried")
        if not os.path.exists(mark):
            open(mark, "w").close()
            for j in json.loads(os.environ.get("FAKE_RETRY", "[]")):
                print(f"pool {j}")
        sys.exit(0)
    sys.exit(mc.main("e7h", jobs=jobs, run=run, summary=summary))
'''


def _scope_env() -> dict:
    if shutil.which("systemd-run") is None:
        return {"MS3_SCOPE": "0"}
    r = subprocess.run(["systemd-run", "--user", "--scope", "-q", "-p", "MemoryMax=3G", "-p", "MemorySwapMax=0",
                        "true"], capture_output=True, timeout=60)
    return {} if r.returncode == 0 else {"MS3_SCOPE": "0"}


def _run_fake(tmp_path: Path, jobs: list, parts: str, events: str = "events.txt", **extra):
    root = tmp_path / "root"
    (root / "out" / "e11").mkdir(parents=True, exist_ok=True)
    (root / "out" / "e11" / "summary.json").write_text("{}\n")
    mod = tmp_path / "mod"
    mod.mkdir(exist_ok=True)
    (mod / "fake_e7h.py").write_text(FAKE_DRIVER)
    env = {k: v for k, v in os.environ.items() if not k.startswith(("MS3_", "FAKE_", "E7H_"))}
    env.update(MS3_ROOT=str(root), MS3_WORKERS="2", MS3_POLL_S="0.2", MS3_PY=sys.executable, MS3_MODULE="fake_e7h",
               PYTHONPATH=os.pathsep.join([str(mod), str(SIM)]), FAKE_JOBS=json.dumps(jobs), E7H_PART=parts,
               FAKE_EVENTS=str(tmp_path / events), **_scope_env(), **extra)
    p = subprocess.run(["bash", str(RUN)], env=env, capture_output=True, text=True, timeout=300)
    ev: dict = {}
    f = tmp_path / events
    for line in (f.read_text().splitlines() if f.is_file() else []):
        jid, t0, t1 = line.split()
        ev.setdefault(jid, []).append((float(t0), float(t1)))
    return p, ev, root / "out"


FAKE_JOBS = [["e7h:p0:k=week:tag=A9:c=101", "pool", "p0", 0.3],
             ["e7h:p0:k=week:tag=BL1:c=101", "pool", "p0", 0.3],
             ["e7h:p0:k=gap_lp:c=101", "alone", "p0", 0.2],
             ["e3:milp:b=1:u=8:mu=1:c=101:part=b00", "milp", "p0", 0.1],
             ["e3:milp:b=1:u=8:mu=1:c=101:part=shared", "milp", "p0", 0.3],
             ["e7h:main:k=week:tag=A9:c=101", "pool", "main", 0.1]]


def test_run_script_passes_retry_and_folders(tmp_path):
    p, ev, out = _run_fake(tmp_path, FAKE_JOBS, "p0 main", FAKE_RETRY=json.dumps(["e7h:p0:k=week:tag=BL1:c=101"]))
    assert p.returncode == 0, p.stdout + p.stderr
    p0 = out / "sublet_v2_pilot" / "p0"
    assert len(ev["e7h:p0:k=week:tag=BL1:c=101"]) == 2 and len(ev["e7h:p0:k=week:tag=A9:c=101"]) == 1   # rerun once
    pools = max(t1 for j in ("e7h:p0:k=week:tag=A9:c=101",) for _t0, t1 in ev[j])
    alone = ev["e7h:p0:k=gap_lp:c=101"][0]
    shared, b00 = ev["e3:milp:b=1:u=8:mu=1:c=101:part=shared"][0], ev["e3:milp:b=1:u=8:mu=1:c=101:part=b00"][0]
    assert pools <= alone[0] and alone[1] <= shared[0] and shared[1] <= b00[0]       # pool, alone, MILPs, b00 last
    assert b00[1] <= ev["e7h:p0:k=week:tag=BL1:c=101"][1][0] <= ev["summary:p0"][0][0]
    assert ev["summary:p0"][0][1] <= ev["e7h:main:k=week:tag=A9:c=101"][0][0] <= ev["summary:main"][0][0]
    for d in (p0, out / "sublet_v2" / "main"):
        recs = mc.read_records(d)
        assert recs["e7h:summary"]["status"] == "ok" and recs["e7h:manifest"]["status"] == "ok", d
        log = (d / "run_e7h.log").read_text()
        assert log.rstrip().splitlines()[-1].startswith("[run_e7h] done ") and "gate ok" in log
    assert "rerun once (§4.5): 1 pool job(s)" in (p0 / "run_e7h.log").read_text()


def test_run_script_refuses_and_filters(tmp_path):
    p, ev, out = _run_fake(tmp_path / "a", FAKE_JOBS, "main", FAKE_GATE="0")
    assert p.returncode == 2 and ev == {}
    assert "refused: part main does not start" in (out / "sublet_v2" / "main" / "run_e7h.log").read_text()
    p, ev, out = _run_fake(tmp_path / "b", FAKE_JOBS, "p0", E7H_ONLY="tag=A9:")
    assert p.returncode == 0, p.stdout + p.stderr
    assert set(ev) == {"e7h:p0:k=week:tag=A9:c=101", "summary:p0"}
    p, _, _ = _run_fake(tmp_path / "c", FAKE_JOBS, "", events="ev_c.txt")
    assert p.returncode == 2 and "E7H_PART must name" in p.stderr
    p, _, _ = _run_fake(tmp_path / "d", FAKE_JOBS, "p9", events="ev_d.txt")
    assert p.returncode == 2 and "unknown part" in p.stderr


def test_run_script_parses():
    assert subprocess.run(["bash", "-n", str(RUN)]).returncode == 0
    assert os.access(RUN, os.X_OK)


# ---------------------------------------------------------------- needs_a12: reduced jobs through e7h's runner
@pytest.mark.needs_a12
def test_reduced_week_jobs_through_the_runner(tmp_path, monkeypatch):
    """Two reduced P0 jobs: BL1 at E7 alignment 1 under L-tr, L-eg and L-hon, and A8P around NBR-repro (safe 'fb')
    at dev seed 101 under L-tr and L-eg: ok records, the pilot gate in the run file, r0 = ALG / BL0a, RC from the
    L-hon run, and A8P's record with its certificate, envelope and projection counts."""
    monkeypatch.setenv(e7h.REDUCED_ENV, "1")
    monkeypatch.setenv("MS3_ROOT", str(tmp_path))
    monkeypatch.setattr(e7h, "_GATE", {})
    out = tmp_path / "out" / "sublet_v2_pilot" / "p0"
    js = {j.id: j for j in e7h.jobs(["p0"])}
    for jid in ("e7h:p0:k=week:tag=BL1:c=1", "e7h:p0:k=week:tag=NBR-repro-G:c=101"):
        rec = mc.run_job("e7h", js[jid], lambda o, j=js[jid]: e7h.run(j, o, out), out, resume=False)
        assert rec["status"] == "ok" and rec["n_errors"] == 0, rec.get("error")
    f = json.loads(e7h.run_path(out, "e7h:p0:k=week:tag=BL1:c=1").read_text())
    assert f["meta"]["gate"]["kind"] == "pilot" and f["meta"]["gate"]["pilot"]["anchor_is_ancestor"] is True
    assert f["horizon_min"] == 120 and [r["mode"] for r in f["runs"]] == ["L-tr", "L-eg", "L-hon"]
    assert f["lender_models"]["L-hon"]["schedule"] == "iid_step"
    for r in f["runs"]:
        assert r["status"] == "ok" and r["r0"] == pytest.approx(r["ALG"] / r["bl0a_usd"], rel=1e-12)
    g = json.loads(e7h.run_path(out, "e7h:p0:k=week:tag=NBR-repro-G:c=101").read_text())
    for r in g["runs"]:
        a8 = r["a8"]
        assert r["policy_id"] == "A8P" and a8["certificate"]["available"] and a8["certificate_case"] == "W(a)"
        assert a8["envelope"]["ok"] and a8["s_fb_all"] is True and a8["B0_rule"] == "auto, kappa 10"
        assert a8["info_class_reported"] == "online-I1" and "a9" in r and r["a9"]["insured"] == 0
        assert set(a8["projection"]) == {"slots", "P1", "P0", "K0", "dropped_buys", "dropped_other",
                                         "guard_releases"}
    col = e7h.collect(out, [js["e7h:p0:k=week:tag=BL1:c=1"]])
    rc = m5.rc_rows([{**r, "config_seed": r["c"], "policy_seed": r["seed"]} for r in col["rows"]])
    assert set(rc["BL1"]) == {"L-tr", "L-eg"}


@pytest.mark.needs_a12
def test_reduced_p0r_jobs_at_the_built_allowance(tmp_path, monkeypatch):
    """p0r's reduced Sublet week job (week 107 under L-tr and L-eg, 2-hour horizon) and its E3 cell job at b 1 (c 101,
    the E3 window) through e7h's runner: A8P at 'allowance' 'lb' in every run's parameters and record (B0_rule
    LB_RULE, allowance 'lb', B0_usd and B0_report_usd None, kappa None), B(T) equal to the OnlineLB's B_T in the
    report's online_lb block (LB'(T) and W_k(T) with it, B(T) their minimum), the certificate available and the
    envelope ok; the summary rows carry the rule, B(T) and the online_lb block."""
    monkeypatch.setenv(e7h.REDUCED_ENV, "1")
    monkeypatch.setenv("MS3_ROOT", str(tmp_path))
    monkeypatch.setattr(e7h, "_GATE", {})
    out = tmp_path / "out" / "sublet_v2_pilot" / "p0r"
    js = {j.id: j for j in e7h.jobs(["p0r"])}
    week, cell = "e7h:p0r:k=week:tag=Sublet:c=107", e3.cell_id(1, 8, 1.0, 101)
    for jid in (week, cell):
        rec = mc.run_job("e7h", js[jid], lambda o, j=js[jid]: e7h.run(j, o, out), out, resume=False)
        assert rec["status"] == "ok" and rec["n_errors"] == 0, rec.get("error")
    f = json.loads(e7h.run_path(out, week).read_text())
    g = json.loads(e3.cell_file(out, 1, 8, 1.0, 101).read_text())
    assert [r["mode"] for r in f["runs"]] == ["L-tr", "L-eg"] and [r["mode"] for r in g["runs"]] == ["shared"]
    for r in f["runs"] + g["runs"]:
        a8 = r["a8"]
        assert r["policy_id"] == "A8P" and r["status"] == "ok" and m5.run_allowance(r) == "lb", r["mode"]
        assert r["params"]["allowance"] == "lb" and r["params"]["kappa"] is None
        assert a8["B0_rule"] == m5.LB_RULE and a8["allowance"] == "lb" and a8["kappa"] is None
        assert a8["B0_usd"] is None and a8["B0_report_usd"] is None
        olb = a8["online_lb"]
        assert set(olb) == {"LB_T", "Wk_T", "B_T", "n_groups"} and olb["n_groups"] >= 1
        assert a8["B_T"] == olb["B_T"] == min(olb["LB_T"], olb["Wk_T"]) and a8["B_T"] > 0
        assert a8["certificate"]["available"] and a8["envelope"]["ok"] and a8["s_fb_all"] is True
    for jid in (week, cell):
        rows = e7h.collect(out, [js[jid]])["rows"]
        assert rows and all(r["guard"]["B0_rule"] == m5.LB_RULE and r["guard"]["B_T"] == r["guard"]["online_lb"]["B_T"]
                            for r in rows)


# ---------------------------------------------------------------- needs_ms5b_out: the copied confirmation
@pytest.mark.needs_ms5b_out(*[f"sublet_v2/{p}/summary.json" for p in m5.CONF_PARTS], "ms3_copy_sublet_v2.json")
def test_confirmation_outputs():
    import conftest
    out = conftest.MS5B_OUT_DIR
    for p in m5.CONF_PARTS:
        s = json.loads((out / "sublet_v2" / p / "summary.json").read_text())
        assert s["meta"]["part"] == p and s["meta"]["reduced"] is False
        assert s["meta"]["confirmation_gate"]["record"]["prereg_at_head"] is True
    rec = json.loads((out / "ms3_copy_sublet_v2.json").read_text())
    assert rec["pass"] is True
    a = ma.analyse(ma.load(conftest.MS5B_OUT_ROOT / "code" / "sim"))
    assert set(a["parts_found"]) == set(m5.CONF_PARTS)


# ---------------------------------------------------------------- the copy check of out/sublet_v2 (§4.3)
def _fake_part(top: Path, part: str, commit: str) -> None:
    d = top / part
    mc.dump_json({"meta": {"git_revision": commit}}, d / "manifest.json")
    mc.dump_json({"meta": {"git_revision": commit, "part": part}}, d / "summary.json")
    for jid in ("e7h:summary", "e7h:manifest"):
        mc.dump_json({"job": jid, "status": "ok", "git_revision": commit}, mc.record_path(d, jid))
    mc.dump_json({"meta": {"git_revision": commit}, "runs": []}, d / "runs" / "x.json", compact=True)
    (d / "run_e7h.log").write_text("[run_e7h] part x\n[run_e7h] done 2026-11-12T00:00:00+08:00\n")


def test_check_copy_of_the_confirmation(tmp_path):
    commit = "a" * 40
    root, clone = tmp_path / "root", tmp_path / "clone"
    for p in m5.CONF_PARTS:
        _fake_part(root / "out" / "sublet_v2", p, commit)
    shutil.copytree(root / "out" / "sublet_v2", clone / "code" / "sim" / "out" / "sublet_v2")
    (clone / ".git").mkdir(parents=True)
    (clone / ".git" / "HEAD").write_text(commit + "\n")
    rec = m5.check_copy(clone, root)
    assert rec["pass"] is True, rec["checks"]
    assert (root / "out" / m5.COPY_RECORD).is_file() and rec["clone_commit"] == commit
    (root / "out" / "sublet_v2" / "main" / "summary.json").write_text("{}\n")
    (root / "out" / "sublet_v2" / "e3" / "run_e7h.log").write_text("[run_e7h] part e3\n")
    rec = m5.check_copy(clone, root, record=tmp_path / "r.json")
    assert rec["pass"] is False and not rec["checks"]["same_sha256"] and not rec["checks"]["run_log_done"]
    with pytest.raises(FileNotFoundError):
        m5.check_copy(tmp_path / "nowhere", root)
