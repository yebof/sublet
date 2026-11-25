"""E7h: the MS5b pilot P0-P5 and the confirmation of Sublet v2 (design/sublet_v2.md §4, §5, §8.1; unit U35).

Parts (E7H_PART; one part per run of run_e7h.sh, in the order of §5: p0, p2a, p3, p1, p2, then P2's allowance branch
p0r, p1r, p2r, p3r, then p4, p5, and, after the freeze P6, the confirmation parts main, seeds, second, e3, fam, grid).
Pilot outputs go to <root>/out/sublet_v2_pilot/<part>/, confirmation outputs to <root>/out/sublet_v2/<part>/ (jobs/,
logs/, runs/ (not versioned), manifest.json, summary.json, tables.md, run_e7h.log). The cells are those of §5's table
(pilot), of P2's entry in the pilot log of §0 (the rerun parts) and of §4.4 (confirmation):

  p0     reproductions on dev seeds 101-103 (NBR-repro, NBR-repro-G and BL5N: 101-104) under L-tr and L-eg: RCRb-repro,
         CR-repro, BL1N-repro, NBR-repro, NBR-repro-G (A8P around NBR-repro, safe 'fb'), BL5N (§3: against the
         prototype's dev numbers, dev:skeptic/out/dev_summary.json); A8P-MS4 (A8P with project
         false around BL5 at Sublet-MS4's parameters) at E7 alignment 1, policy seed 0, L-tr against the stored run
         (13,932.930630343202 USD); the notice premium of P3 on the E7 menu; the check of RC: BL1, BL5-cur and A9 at
         E7 alignment 1 under L-tr, L-eg and L-hon
  p2a    E3 config seeds 101-104 x b in {1, 2, 4, 8, 16, 32} (u 8, mu 1), shared, trace: Sublet, A9 and Proto-alt
         (the alternative allowance min{W_k, LB'} through the prototype copies around the registered A9)
  p3     the families of Q6 at policy seeds 10-12 and the fresh families of §5 P3 (FRESH_P3): A9, A9-noIns, Sublet,
         RR_RENEW, MARKING (I2), BL1-G, BL5-G (RR_RENEW and MARKING not on F3); exact OPT by q44_study._family_lb
  p1     (i) bench_e7f seeds 107-112 x the six modes: A9, CR, A9-noMBB, A9-noCommit, A9-noIns, A9-kstar, A9-static,
         BL1, BL1-BO, BL2, BL3-0, BL4, BL5, BL5-cur, BL1N, BL5N; (ii) the Q44 tuning cells I1 c3, I2 c1, I3 c1 and
         I4 config seeds 11-12 x {L-tr, L-eg, L-ss, L-co, L-iid-0.2}: A9, A9-noCommit, A9-noIns; (iii) E3 101-104 x
         b, shared, trace: A9, A9-noIns
  p2     (i) Sublet on seeds 107-110 x the six modes; on 107-108 x {L-tr, L-eg} Sublet-1way and the prototypes
         Proto-alt, Proto-F5 (F5 at Algorithm 1's allowance) and Proto-F5-alt; BL1-GP on 107-110 x {L-tr, L-eg};
         (ii) E3 101-104 x b (shared, trace) and the Q44 tuning cells and I4 c11-12 under L-tr: Sublet and Proto-alt
  P2's allowance branch (pilot log of §0, entry "P2, 2026-11-02": Algorithm 1's allowance failed test (3), the
  alternative passed, so Sublet is A8P at 'allowance' 'lb' (ms5b_common.sublet_v2_params) and P0-P2 rerun for it on
  bench_e7f seeds 117-120 with the one-day cells of P2 (ii) unchanged, and P3's Sublet runs are repeated). The parts
  p2a, p3 and p2 ran Sublet at Algorithm 1's allowance (Sublet-alg1's parameters), and p2 also ran Sublet-1way and
  BL1-GP at it; a rerun of them now takes P2's allowance.
  p0r    the reproduction of the built allowance: Sublet on the cells of P2 on which Proto-alt ran (107-108 x {L-tr,
         L-eg}, E3 101-104 x b shared, the Q44 tuning cells and I4 c11-12 under L-tr) against Proto-alt's runs in p2
         (r0 to REPRO_TOL, B(T) to B_REL_TOL, every run at ms5b_common.LB_RULE), and A8P-MS4 as p0 runs it (the
         identity of the project-false path, IDENTITY_USD)
  p1r    A9 on seeds 117-120 x the six modes (policy seed 0): the reference of p2r's price of the guard; P1's decisions
         are not reapplied (A9 does not change)
  p2r    (i) Sublet on seeds 117-120 x the six modes; Sublet-1way on 117-118 x {L-tr, L-eg}; BL1-GP on 117-120 x
         {L-tr, L-eg}; Proto-F5-alt (F5 at the alternative allowance, as p2 ran it) on 117-118 x {L-tr, L-eg}, for
         §5's F5 clause; (ii) Sublet on the one-day cells of P2 (ii) (E3 101-104 x b shared, the Q44 tuning cells and
         I4 c11-12 under L-tr); A9's runs from p1r (weeks) and p1 (one-day cells). Sublet-alg1 is not rerun (its test
         (3) failure on the unchanged one-day cells stands)
  p3r    Sublet on P3's family cells (the families of Q6 and FRESH_P3 at policy seeds 10-12, exact OPT as p3)
  p4     E3 101-104 x b with the shared LP bound: Sublet and A9 siloed (their shared runs are p2r's and P1's; a
         shared run of Sublet counts only at Sublet's allowance, sublet_v2_params, and any other is missing, so p2's
         runs at Algorithm 1's allowance are never read), BL1 and BL5-cur shared and siloed, Sublet-MS4 shared; one
         shared MILP at b in {1, 8, 32} (c 101; its solve time);
         the Q44 tuning cells and I4 c11-12 x the five modes of p1 (ii): Sublet, BL1, BL5, BL5-cur; E5 config seeds
         103-104 x {short, long} x {trace, all1}: Sublet, A9, A9-noIns, BL3-0, BL5, BL5-cur
  p5     seeds 107-108 x {L-vr, L-rf, L-ad, L-b999 (buffer quantile p99.9), iid_step p in {0 (L-hon), 0.05, 0.1, 0.2,
         0.34, 0.5, 0.8, 1}}: Sublet, A9, BL1, BL5-cur, BL1N; A9-lag and BL1-lag (demand_lag 1) under L-tr
  main   §4.4(a): weeks 301-316 x {L-tr, the five stress modes, L-hon}, policy seed 0, the 22 tags of §3 (E7_TAGS)
  seeds  §4.4(a): policy seeds 1-2 on weeks 301-304 x the seven modes for Sublet, BL1 and BL5-cur
  second §4.4(b), weeks 301-304: L-vr, L-rf, L-ad, L-b999 and iid_step p in {0.1, 0.34, 0.5, 0.8, 1} for Sublet, A9,
         BL1, BL1-BO, BL3-0, BL4, BL5-cur, BL5-tau60, BL1N, BL5N, BL1-GP and Sublet-MS4; A9-lag, Sublet-lag and BL1-lag
         under L-tr (BL5's L-tr runs are main's); the E5 menus at E5 config seeds 301-304 x {trace, all1} for Sublet,
         A9, BL3-0, BL5, BL5-cur, Sublet-MS4; the gap days ms4_common.gap_instance(c), c = 301-304, for the tags of
         (b) with the merged LP (gap_lp, 'alone')
  e3     §4.4(c): E3 config seeds 301-304 x b, u 8, mu 1: Sublet, A9, BL1, BL5-cur and Sublet-MS4, each shared and
         siloed, with the LPs of the shared instance and of every borrower and the MILP jobs of MS4's E3 (shared and
         per borrower: 276 'milp' jobs), e3.cell_benchmarks for the bounds and brackets
  fam    §4.4(d): the Q6 instances at policy seeds 13-22 and the confirmation's fresh instances (FRESH_CONF): A9,
         A9-noIns, Sublet, BL1-G, BL5-G, BL1-GP, RR_RENEW, MARKING; under F-ad and F-eg A9, A9-noIns and RR_RENEW run
         once per instance (no random draw, counted once)
  grid   §4.4(e), development-exposed: the E7 grid (alignments 1-4 x policy seeds 0-2 under L-tr; alignment 1 x seeds
         0-2 under the stress modes; seed-free tags at seed 0 only) with the 22 tags, the gap reruns of alignments 1-4
         with their merged LPs, and the Q44 held-out cells of Q1 and Q2 (block modes, seeds 0-2) for Sublet, A9, BL1-GP

Jobs (ids by ms3_common.job_id: 'e7h:<part>:k=<kind>:...'; the E3 cells and MILPs keep e3's ids e3.cell_id and
e3.milp_id, so that e3.run_milp and e3.cell_benchmarks apply unchanged). A week job runs one tag on one week (config
seed = lender seed) under every lender mode of its cell in one process, so that A9's contract table (§2.2, A9.3) is
computed once per job (§5); the instance is built once per job (L-b999 builds its own). One-day cells (E3, Q44, E5,
families) run all their tags in one job. Every job writes runs/<job file>.json (E3: e3.cell_file); its record carries
the git revision, and every pilot output carries ms5b_common.pilot_record (the anchor, HEAD, the sha256 of the note at
HEAD); a pilot job refuses to run unless the anchor is an ancestor of HEAD (ms5b_common.check_pilot). A confirmation
job refuses to run unless ms5b_common.check_confirmation passes (the pre-registration at HEAD, a clean tree, the
analysis script's sha256 as recorded); reduced runs record the gate without enforcing it (they use development cells
only). The prototype jobs use the copies in ms5b_proto/ (labeled prototype).

Command line (ms3_common.main), run from code/sim:
  python -m sublet.experiments.e7h --list | --job ID | --summary | --estimate | --manifest  [--out DIR]
  python -m sublet.experiments.e7h --check-start          the gate of the part(s) of E7H_PART; exit 1 if refused
  python -m sublet.experiments.e7h --retry-list --out DIR  the missing-run rule's rerun (§4.5): moves the record of
                                                           every pool job not 'ok', or 'ok' with a run that raised or
                                                           failed an invariant, to retry/ (once per job) and prints
                                                           '<kind> <id>' for run_e7h.sh to launch again
Without --out the part's folder is the default (one part in E7H_PART). Reduced runs (MS3_E7H_REDUCED=1, run_e7h.sh
--reduced): development cells only; the pilot parts as MS4's reduced mode (the first seed of each group, policy seed
0, a 2-hour horizon; E3 b in {1, 8} and the Q44 cells in the slow-slot window [156, 180) of e3.REDUCED); the
confirmation parts on bench_e7f config seed 101, E3 and E5 config seed 101, the Q6 family instances at policy seed 0
(first instance of each family, first mode) and the Q44 tuning cell I2 c1, with a 2-hour horizon for the week runs,
never a seed or instance of §4.4. Summaries carry meta.reduced; never a result.

Status labels (copied from design/sublet_v2.md §2.5 and §2.6 after the P6 audit addendum, design/theory/audit_guard.md):
Theorem W(a)(b), G2 and G3(b) PROVEN for A8; for A8P through Remark R, PROVEN, audited (on core exports up to WD_TIE);
Lemma G5' and Corollary G3' (the allowance min{W_k, LB'}, G3(b)'s constant about 12.66) PROVEN, audited; Proposition
P PROVEN, audited ((d) under its three float hypotheses); A9's rules HEURISTIC; no competitive ratio is claimed for
A9 on the full model.
"""
from __future__ import annotations

import os

os.environ.setdefault("OMP_NUM_THREADS", "1")

import argparse
import contextlib
import copy
import hashlib
import re
import statistics
import sys
import time
from pathlib import Path
from typing import Optional

import numpy as np

from .. import paths
from . import e3
from . import e7
from . import ms3_common as mc
from . import ms4_common as m4
from . import ms5b_common as m5
from .ms3_common import Job, job_id, num_key, put

EXP = "e7h"
SPEC = "design/sublet_v2.md §4, §5, §8.1"
PILOT_PARTS = ("p0", "p2a", "p3", "p1", "p2", "p0r", "p1r", "p2r", "p3r", "p4", "p5")   # §5's run order, P2's branch
RERUN_PARTS = ("p0r", "p1r", "p2r", "p3r")                    # P2's allowance branch (pilot log, "P2, 2026-11-02")
CONF_PARTS = m5.CONF_PARTS                                     # main, seeds, second, e3, fam, grid (§4.4)
PARTS = PILOT_PARTS + CONF_PARTS
REDUCED_ENV = "MS3_E7H_REDUCED"
REDUCED_HORIZON_MIN = 120
E3_WINDOW = tuple(e3.REDUCED["horizon"])                       # slow slots [156, 180), 13:00-15:00
REPRO_TOL = 0.005                                              # P0: every reproduction within 0.005 BL0a per cell
B_REL_TOL = 1e-9                                               # p0r: B(T) of Sublet against Proto-alt's, relative
IDENTITY_USD = 13932.930630343202                              # P0: out/e7/main/jobs/e7__main__pol__Sublet__mu__1__c__1
IDENTITY_TOL = 1e-9
RC_FLAG = -0.005                                               # P0: a negative RC below it is traced
PROTO_DIR = Path(__file__).resolve().parent / "ms5b_proto"
DEV = paths.SIM_OUT / "sublet_v2_dev"

# ---------------------------------------------------------------- cells (§4.2, §4.4, §5)
DEV_REPRO = (101, 102, 103)
DEV_NBR = (101, 102, 103, 104)
P1_WEEKS = (107, 108, 109, 110, 111, 112)
P2_WEEKS = (107, 108, 109, 110)
P2_PAIR = (107, 108)
RERUN_WEEKS = (117, 118, 119, 120)                             # §4.1's reserve for P2's allowance branch
RERUN_PAIR = (117, 118)
P5_WEEKS = (107, 108)
E3_PILOT = (101, 102, 103, 104)
E5_PILOT = (103, 104)
SEEDS_WEEKS = (301, 302, 303, 304)
E3_CONF = (301, 302, 303, 304)
E5_CONF = (301, 302, 303, 304)
GRID_ALIGNMENTS = (1, 2, 3, 4)
GRID_SEEDS = (0, 1, 2)
REDUCED_WEEK = 101
U, MU = 8, 1.0
Q44_TUNING = (("Q1", "I1", 3), ("Q1", "I2", 1), ("Q2", "I3", 1), ("Q1", "I4", 11), ("Q1", "I4", 12))
Q44_P1_MODES = ("L-tr", "L-eg", "L-ss", "L-co", "L-iid-0.2")
Q44_HELD_OUT = (("Q1", "I1", (4, 7)), ("Q1", "I2", (2, 3, 4, 5, 6, 7, 8)), ("Q2", "I3", (2, 3, 4)),
                ("Q1", "I4", (1, 2, 3, 4, 5, 6, 7, 8)))
REDUCED_Q44 = ("Q1", "I2", 1)
E5_MENUS = ("short", "long")
E5_LEVELS = ("trace", "all1")
P1_TAGS = ("A9", "CR", "A9-noMBB", "A9-noCommit", "A9-noIns", "A9-kstar", "A9-static", "BL1", "BL1-BO", "BL2",
           "BL3-0", "BL4", "BL5", "BL5-cur", "BL1N", "BL5N")
P1_Q44_TAGS = ("A9", "A9-noCommit", "A9-noIns")
P4_E3 = (("Sublet", "siloed"), ("A9", "siloed"), ("BL1", "shared"), ("BL1", "siloed"), ("BL5-cur", "shared"),
         ("BL5-cur", "siloed"), ("Sublet-MS4", "shared"))
P4_Q44_TAGS = ("Sublet", "BL1", "BL5", "BL5-cur")
P4_E5_TAGS = ("Sublet", "A9", "A9-noIns", "BL3-0", "BL5", "BL5-cur")
P4_MILP_B = (1, 8, 32)
P5_TAGS = ("Sublet", "A9", "BL1", "BL5-cur", "BL1N")
P5_MODES = m5.SECOND_MODES + (m5.B999_MODE,) + tuple(m5.iid_mode(p) for p in m5.IID_P5)
SECOND_TAGS = ("Sublet", "A9", "BL1", "BL1-BO", "BL3-0", "BL4", "BL5-cur", "BL5-tau60", "BL1N", "BL5N", "BL1-GP",
               "Sublet-MS4")
SECOND_MODES = m5.SECOND_MODES + (m5.B999_MODE,) + tuple(m5.iid_mode(p) for p in m5.IID_CONF)
SECOND_E5_TAGS = ("Sublet", "A9", "BL3-0", "BL5", "BL5-cur", "Sublet-MS4")
LAG_TAGS_CONF = ("A9-lag", "Sublet-lag", "BL1-lag")
CONF_E3 = tuple((t, m) for t in ("Sublet", "A9", "BL1", "BL5-cur", "Sublet-MS4") for m in ("shared", "siloed"))
GRID_Q44_TAGS = ("Sublet", "A9", "BL1-GP")
P3_TAGS = ("A9", "A9-noIns", "Sublet", "RR_RENEW", "MARKING", "BL1-G", "BL5-G")
FAM_TAGS = ("A9", "A9-noIns", "Sublet", "BL1-G", "BL5-G", "BL1-GP", "RR_RENEW", "MARKING")
FAM_ONCE = ("A9", "A9-noIns", "RR_RENEW")          # §4.4(d): no random draw, one run per instance under F-ad, F-eg
P3_SEEDS = (10, 11, 12)
FAM_SEEDS = tuple(range(13, 23))
NOT_ON_F3 = ("RR_RENEW", "MARKING")
# §5 P3 and §4.4(d): the fresh families (fam: the class of the T4/O1 or C3-P5 construction)
FRESH_P3 = ({"id": "P3F1", "fam": "F1", "kind": "fam", "m": [3, 6, 12], "rho": [5, 12, 32], "tau": 2, "H": 1,
             "T": 48, "modes": ["F-ad"]},
            {"id": "P3F2", "fam": "F2", "kind": "fam", "m": [3, 6, 12], "rho": [5, 12, 32], "tau": 2, "H": 1,
             "T": 96, "modes": ["F-ss", "F-iid", "F-eg"]},
            {"id": "P3F3", "fam": "F3", "kind": "c3p5", "beta": [3, 10, 20], "T": [64, 128], "modes": ["F-eg"]})
FRESH_CONF = ({"id": "CF1", "fam": "F1", "kind": "fam", "m": [5, 10], "rho": [7, 24], "tau": 3, "H": 2, "T": 72,
               "modes": ["F-ad"]},
              {"id": "CF2", "fam": "F2", "kind": "fam", "m": [5, 10], "rho": [7, 24], "tau": 3, "H": 2, "T": 144,
               "modes": ["F-ss", "F-iid", "F-eg"]},
              {"id": "CF3", "fam": "F3", "kind": "c3p5", "beta": [4, 24], "T": [96], "modes": ["F-eg"]})
# §5's compute estimates (seconds per week run; dev:skeptic and dev:perf wall_s, e7.EST_WEEK_S) and one-day runs
EST_WEEK_S = {"A9": 21.6, "A8P": 169.2, "A8": 140.2, "BL1": 14.8, "BL2": 25.2, "BL3": 14.4, "BL4": 27.9, "BL5": 12.6,
              "A6": 49.4, "proto": 169.2}
EST_TABLE_S = 44.0                                 # A9's contract table, once per A9-family job (§5)
EST_DAY_S = {"A8P": 15.0, "A8": 12.0, "proto": 15.0}
EST_DAY_OTHER_S = 3.0
EST_JOB_S = 5.0
EST_FAM_RUN_S = 0.5
EST_LP_S = 207.1                                   # e7.EST_LP_S (one merged gap LP)


# ---------------------------------------------------------------- settings and parts
def design() -> dict:
    red = os.environ.get(REDUCED_ENV, "0") == "1"
    return {"reduced": red, "horizon_min": REDUCED_HORIZON_MIN if red else m5.WEEK_MIN,
            "window": list(E3_WINDOW) if red else None, "e5_horizon_min": REDUCED_HORIZON_MIN if red else None,
            "gap_horizon_min": REDUCED_HORIZON_MIN if red else m4.DAY_MIN}


def parts() -> list:
    v = os.environ.get("E7H_PART", "")
    ps = [p for p in v.replace(",", " ").split() if p]
    bad = [p for p in ps if p not in PARTS]
    if bad:
        raise ValueError(f"E7H_PART must name parts of {list(PARTS)}, got {v!r}")
    return ps or list(PARTS)


def is_pilot(part: str) -> bool:
    return part in PILOT_PARTS


def part_dir(part: str, root=None) -> Path:
    """<root>/out/sublet_v2_pilot/<part> or <root>/out/sublet_v2/<part> (root as ms3_common.ms3_root)."""
    return mc.ms3_root(root) / "out" / (m5.PILOT_DIR if is_pilot(part) else m5.CONF_DIR) / part


def run_path(out, jid: str) -> Path:
    return Path(out) / "runs" / mc.job_file_name(jid)


def gap_lp_path(out, c: int) -> Path:
    return Path(out) / "lb" / f"gap_lp_c{int(c)}.json"


# ---------------------------------------------------------------- job lists (§4.4, §5)
def _first(xs, red: bool):
    return tuple(xs)[:1] if red else tuple(xs)


def _est_week(t: str, n_runs: int, hz: int) -> float:
    if t in m5.PROTO:
        key, fam = "proto", True
    else:
        tg = m5.tag(t)
        key, fam = tg.id, tg.a9_family
    return EST_JOB_S + (EST_TABLE_S if fam else 0.0) + n_runs * EST_WEEK_S.get(key, 20.0) * hz / m5.WEEK_MIN


def _est_day(t: str) -> float:
    return EST_DAY_S.get("proto" if t in m5.PROTO else m5.tag(t).id, EST_DAY_OTHER_S)


def _weeks(part: str, tags, weeks, modes, seeds, hz: int, seed_free_once: bool = False) -> list:
    out = []
    for c in weeks:
        for t in tags:
            ss = tuple(seeds)[:1] if seed_free_once and t not in m5.PROTO and m5.seed_free(t) else tuple(seeds)
            out.append(Job(job_id(EXP, part, k="week", tag=t, c=int(c)), "pool",
                           {"part": part, "kind": "week", "tag": t, "c": int(c), "modes": list(modes),
                            "policy_seeds": [int(s) for s in ss], "horizon_min": int(hz)},
                           _est_week(t, len(modes) * len(ss), hz)))
    return out


def _e3cells(part: str, cs, bs, entries, lp: str, window) -> list:
    out = []
    for c in cs:
        for b in bs:
            n_sub = sum(1 for _t, m in entries if m == "siloed")
            est = EST_JOB_S + sum(_est_day(t) * (b if m == "siloed" else 1) for t, m in entries) + \
                (1 + (b if lp == "all" else 0)) * 0.4 * (lp != "none")
            out.append(Job(e3.cell_id(b, U, MU, c), "pool",
                           {"part": part, "kind": "e3cell", "b": int(b), "u": U, "mu": MU, "c": int(c),
                            "entries": [list(x) for x in entries], "policy_seeds": [0], "lp": lp,
                            "horizon": None if window is None else list(window), "siloed": n_sub > 0}, est))
    return out


def _e3milps(part: str, cs, bs, window, parts_of=None) -> list:
    out = []
    for c in cs:
        for b in bs:
            for pt in (parts_of(b) if parts_of else ["shared"] + e3.borrower_ids(b)):
                out.append(Job(e3.milp_id(b, U, MU, c, pt), "milp",
                               {"part": part, "kind": "e3milp", "b": int(b), "u": U, "mu": MU, "c": int(c),
                                "part_": pt, "horizon": None if window is None else list(window)},
                               mc.wall_timeout_s()))
    return out


def _q44(part: str, cells, entries, modes_of, window) -> list:
    """Q44 cell jobs: cells (block, instance, config seed); entries [(tag, seeds)]; modes_of(block) the modes."""
    out = []
    for blk, inst, c in cells:
        modes = list(modes_of(blk))
        n = sum(len(s) for _t, s in entries) * len(modes)
        out.append(Job(job_id(EXP, part, k="q44", inst=inst, c=int(c)), "pool",
                       {"part": part, "kind": "q44", "block": blk, "inst": inst, "c": int(c), "modes": modes,
                        "entries": [[t, [int(x) for x in s]] for t, s in entries],
                        "window": None if window is None else list(window)},
                       EST_JOB_S + EST_TABLE_S + n * 5.0))
    return out


def _e5(part: str, cs, tags, hz) -> list:
    out = []
    for c in cs:
        for menu in E5_MENUS:
            for t in tags:
                out.append(Job(job_id(EXP, part, k="e5", menu=menu, tag=t, c=int(c)), "pool",
                               {"part": part, "kind": "e5", "menu": menu, "tag": t, "c": int(c),
                                "levels": list(E5_LEVELS), "policy_seeds": [0], "horizon_min": hz},
                               _est_week(t, len(E5_LEVELS), hz or m5.WEEK_MIN)))
    return out


def _gap(part: str, cs, tags, seeds, hz) -> list:
    out = [Job(job_id(EXP, part, k="gap_lp", c=int(c)), "alone", {"part": part, "kind": "gap_lp", "c": int(c),
                                                                    "horizon_min": hz},
               EST_JOB_S + EST_LP_S * hz / m4.DAY_MIN) for c in cs]
    for c in cs:
        for t in tags:
            ss = tuple(seeds)[:1] if m5.seed_free(t) else tuple(seeds)
            out.append(Job(job_id(EXP, part, k="gap", tag=t, c=int(c)), "pool",
                           {"part": part, "kind": "gap", "tag": t, "c": int(c), "policy_seeds": [int(s) for s in ss],
                            "horizon_min": hz}, _est_week(t, len(ss), hz)))
    return out


def q6_families() -> list:
    """The families of block Q6 (q44_study.load_block('Q6')), each with its class 'fam' = its id."""
    from . import q44_study as q44
    return [{**f, "fam": f["id"]} for f in q44.load_block("Q6")["families"]]


def _fam(part: str, fams, tags, seeds, *, once: bool, first_only: bool = False) -> list:
    from . import q44_study as q44
    out = []
    for fam in fams:
        insts = q44.family_instances(fam)
        modes = list(fam["modes"])
        if first_only:
            insts, modes = insts[:1], modes[:1]
        for v in insts:
            fid = q44._fam_instance_id(fam, **v)
            for md in modes:
                tl = [t for t in tags if not (fam["kind"] == "c3p5" and t in NOT_ON_F3)]
                fixed = q44.FAMILY_MODES[md]["lender_seeds"] == "fixed"
                ent = [[t, [int(s) for s in (seeds[:1] if once and fixed and t in FAM_ONCE else seeds)]] for t in tl]
                out.append(Job(job_id(EXP, part, k="fam", src=fam["id"], inst=fid, mode=md), "pool",
                               {"part": part, "kind": "fam", "family": copy.deepcopy(fam), "values": v,
                                "inst": fid, "mode": md, "entries": ent},
                               EST_JOB_S + EST_FAM_RUN_S * sum(len(s) for _t, s in ent)))
    return out


def jobs(ps=None) -> list:
    """The jobs of the parts `ps` (default: E7H_PART) in run order; each part's cells as the module docstring says."""
    ps = parts() if ps is None else list(ps)
    d = design()
    red, hz, win = d["reduced"], d["horizon_min"], d["window"]
    tr_eg = ("L-tr", "L-eg")
    out: list = []
    for part in ps:
        J: list = []
        if part == "p0":
            for t in ("RCRb-repro", "CR-repro", "BL1N-repro"):
                J += _weeks(part, [t], _first(DEV_REPRO, red), tr_eg, (0,), hz)
            for t in ("NBR-repro", "NBR-repro-G", "BL5N"):
                J += _weeks(part, [t], _first(DEV_NBR, red), tr_eg, (0,), hz)
            J += _weeks(part, ["A8P-MS4"], (1,), ("L-tr",), (0,), hz)
            J += _weeks(part, ["BL1", "BL5-cur", "A9"], (1,), ("L-tr", "L-eg", m5.HON_MODE), (0,), hz)
            J.append(Job(job_id(EXP, part, k="premium", c=1), "pool", {"part": part, "kind": "premium", "c": 1,
                                                                       "horizon_min": hz}, EST_JOB_S + EST_TABLE_S))
        elif part == "p2a":
            J += _e3cells(part, _first(E3_PILOT, red), (1, 8) if red else e3.BS,
                          [("Sublet", "shared"), ("A9", "shared"), ("Proto-alt", "shared")], "none", win)
        elif part == "p3":
            J += _fam(part, q6_families() + list(FRESH_P3), P3_TAGS, P3_SEEDS[:1] if red else P3_SEEDS, once=False,
                      first_only=red)
        elif part == "p1":
            J += _weeks(part, P1_TAGS, _first(P1_WEEKS, red), m5.main_modes(), (0,), hz)
            J += _q44(part, _first(Q44_TUNING, red), [(t, (0,)) for t in P1_Q44_TAGS], lambda b: Q44_P1_MODES, win)
            J += _e3cells(part, _first(E3_PILOT, red), (1, 8) if red else e3.BS,
                          [("A9", "shared"), ("A9-noIns", "shared")], "none", win)
        elif part == "p2":
            J += _weeks(part, ["Sublet"], _first(P2_WEEKS, red), m5.main_modes(), (0,), hz)
            J += _weeks(part, ["Sublet-1way", "Proto-alt", "Proto-F5", "Proto-F5-alt"], _first(P2_PAIR, red), tr_eg,
                        (0,), hz)
            J += _weeks(part, ["BL1-GP"], _first(P2_WEEKS, red), tr_eg, (0,), hz)
            J += _e3cells(part, _first(E3_PILOT, red), (1, 8) if red else e3.BS,
                          [("Sublet", "shared"), ("Proto-alt", "shared")], "none", win)
            J += _q44(part, _first(Q44_TUNING, red), [("Sublet", (0,)), ("Proto-alt", (0,))], lambda b: ("L-tr",),
                      win)
        elif part == "p0r":
            J += _weeks(part, ["Sublet"], _first(P2_PAIR, red), tr_eg, (0,), hz)
            J += _e3cells(part, _first(E3_PILOT, red), (1, 8) if red else e3.BS, [("Sublet", "shared")], "none", win)
            J += _q44(part, _first(Q44_TUNING, red), [("Sublet", (0,))], lambda b: ("L-tr",), win)
            J += _weeks(part, ["A8P-MS4"], (1,), ("L-tr",), (0,), hz)
        elif part == "p1r":
            J += _weeks(part, ["A9"], _first(RERUN_WEEKS, red), m5.main_modes(), (0,), hz)
        elif part == "p2r":
            J += _weeks(part, ["Sublet"], _first(RERUN_WEEKS, red), m5.main_modes(), (0,), hz)
            J += _weeks(part, ["Sublet-1way"], _first(RERUN_PAIR, red), tr_eg, (0,), hz)
            J += _weeks(part, ["BL1-GP"], _first(RERUN_WEEKS, red), tr_eg, (0,), hz)
            J += _weeks(part, ["Proto-F5-alt"], _first(RERUN_PAIR, red), tr_eg, (0,), hz)
            J += _e3cells(part, _first(E3_PILOT, red), (1, 8) if red else e3.BS, [("Sublet", "shared")], "none", win)
            J += _q44(part, _first(Q44_TUNING, red), [("Sublet", (0,))], lambda b: ("L-tr",), win)
        elif part == "p3r":
            J += _fam(part, q6_families() + list(FRESH_P3), ("Sublet",), P3_SEEDS[:1] if red else P3_SEEDS,
                      once=False, first_only=red)
        elif part == "p4":
            bs = (1, 8) if red else e3.BS
            J += _e3cells(part, _first(E3_PILOT, red), bs, P4_E3, "shared", win)
            J += _e3milps(part, (E3_PILOT[0],), [b for b in P4_MILP_B if b in bs], win, parts_of=lambda b: ["shared"])
            J += _q44(part, _first(Q44_TUNING, red), [(t, (0,)) for t in P4_Q44_TAGS], lambda b: Q44_P1_MODES, win)
            J += _e5(part, _first(E5_PILOT, red), P4_E5_TAGS, d["e5_horizon_min"])
        elif part == "p5":
            J += _weeks(part, P5_TAGS, _first(P5_WEEKS, red), P5_MODES, (0,), hz)
            J += _weeks(part, ["A9-lag", "BL1-lag"], _first(P5_WEEKS, red), ("L-tr",), (0,), hz)
        elif part == "main":
            J += _weeks(part, m5.E7_TAGS, (REDUCED_WEEK,) if red else m5.CONF_WEEKS, m5.conf_modes(), (0,), hz)
        elif part == "seeds":
            J += _weeks(part, ("Sublet", "BL1", "BL5-cur"), (REDUCED_WEEK,) if red else SEEDS_WEEKS, m5.conf_modes(),
                        (1,) if red else (1, 2), hz)
        elif part == "second":
            ws = (REDUCED_WEEK,) if red else SEEDS_WEEKS
            J += _weeks(part, SECOND_TAGS, ws, SECOND_MODES, (0,), hz)
            J += _weeks(part, LAG_TAGS_CONF, ws, ("L-tr",), (0,), hz)
            J += _e5(part, (REDUCED_WEEK,) if red else E5_CONF, SECOND_E5_TAGS, d["e5_horizon_min"])
            J += _gap(part, ws, SECOND_TAGS, (0,), d["gap_horizon_min"])
        elif part == "e3":
            cs, bs = ((REDUCED_WEEK,), (1, 8)) if red else (E3_CONF, e3.BS)
            J += _e3cells(part, cs, bs, CONF_E3, "all", win)
            J += _e3milps(part, cs, bs, win)
        elif part == "fam":
            if red:
                J += _fam(part, q6_families(), FAM_TAGS, (0,), once=True, first_only=True)
            else:
                J += _fam(part, q6_families() + list(FRESH_CONF), FAM_TAGS, FAM_SEEDS, once=True)
        elif part == "grid":
            if red:
                J += _weeks(part, m5.E7_TAGS, (REDUCED_WEEK,), m5.main_modes(), (0,), hz)
                J += _gap(part, (REDUCED_WEEK,), m5.E7_TAGS, (0,), d["gap_horizon_min"])
                J += _q44(part, (REDUCED_Q44,), [(t, (0,)) for t in GRID_Q44_TAGS], lambda b: ("L-tr",), win)
            else:
                J += _weeks(part, m5.E7_TAGS, (1,), m5.main_modes(), GRID_SEEDS, hz, seed_free_once=True)
                J += _weeks(part, m5.E7_TAGS, GRID_ALIGNMENTS[1:], ("L-tr",), GRID_SEEDS, hz, seed_free_once=True)
                J += _gap(part, GRID_ALIGNMENTS, m5.E7_TAGS, GRID_SEEDS, d["gap_horizon_min"])
                from . import q44_study as q44
                cells = [(blk, i, c) for blk, i, cs in Q44_HELD_OUT for c in cs]
                J += _q44(part, cells, [(t, (0,) if m5.seed_free(t) else GRID_SEEDS) for t in GRID_Q44_TAGS],
                          lambda b: q44.load_block(b)["modes"], None)
        out += J
    return out


def jobs_all() -> list:
    return jobs(list(PARTS))


# ---------------------------------------------------------------- the gates (§4.3, §5)
_GATE: dict = {}


def gate(part: str) -> dict:
    """The gate of a part, checked once per process: the pilot anchor for a pilot part (refused unless it is an
    ancestor of HEAD), the confirmation's checks for a confirmation part (refused unless they pass; recorded and not
    enforced in reduced runs, which use development cells only). Raises RuntimeError when refused."""
    key = "pilot" if is_pilot(part) else "confirmation"
    if key not in _GATE:
        if key == "pilot":
            ok, why, rec = m5.check_pilot()
            _GATE[key] = {"kind": "pilot", "ok": ok, "reason": why, "enforced": True, "pilot": rec}
        else:
            ok, why, rec = m5.check_confirmation()
            red = design()["reduced"]
            _GATE[key] = {"kind": "confirmation", "ok": ok, "reason": why, "enforced": not red, "confirmation": rec}
            if red:
                _GATE[key]["note"] = "reduced run on development cells: the gate is recorded, not enforced"
    g = _GATE[key]
    if g["enforced"] and not g["ok"]:
        raise RuntimeError(g["reason"])
    return g


def _meta_run(job: Job) -> dict:
    part = job.params["part"]
    return {"exp": EXP, "job": job.id, "part": part, "spec": SPEC, "git_revision": mc.git_revision(),
            "versions": mc.versions(), "written": mc._now(), "reduced": design()["reduced"], "gate": gate(part)}


def _errs(errors: list) -> list:
    return [{k: v for k, v in e.items() if k != "traceback"} for e in errors]


# ---------------------------------------------------------------- the prototype runs (P2a, P2; §8.1)
def proto_modules():
    """The prototype copies (ms5b_proto/run_proj.py, projected.py, lb.py), imported by name from their folder as the
    dev scripts imported each other."""
    d = str(PROTO_DIR)
    if d not in sys.path:
        sys.path.insert(0, d)
    import projected
    import run_proj
    return run_proj, projected


@contextlib.contextmanager
def f5_patch(on: bool):
    """F5 (route G over W^C, audit open item 4) as run_proj.main applies it (its class T0gF5, copied verbatim), while
    the block runs; guard.T0gBound is restored after it."""
    if not on:
        yield
        return
    import sublet.algos.guard as G
    orig = G.T0gBound

    class T0gF5(orig):
        def _replicas(self, obs, actions):
            r = super()._replicas(obs, actions)
            if r is None:
                return None
            reps, counted, n_unc = r
            return [(j, l, lid, np.ones_like(inB, dtype=bool), lo, hi) for (j, l, lid, inB, lo, hi) in reps], \
                counted, n_unc
    G.T0gBound = T0gF5
    try:
        yield
    finally:
        G.T0gBound = orig


def proto_run(name: str, spec_of, inst, model, ecfg, c: int, ps: int):
    """One prototype run around the registered A9 (§5 P2a, P2): run_proj.allowance's series and parameters for the
    tag's rule on the instance (inst_dict, wk_series, lb.lb_series), an A8P policy of `spec_of(params)` for the
    driver inputs and A8's other defaults, then projected.ProjectedGuard with that A8P's resolved parameters, an
    A9 instance (sublet.algos.a9 at the inner parameters) as its inner policy, rho 1 (the reserve in the test) and
    projection on, under F5 if the tag says so. Returns (res, pol, spec, extra)."""
    from ..algos.a9 import NoticeCriticalRatio
    from ..drivers import run as drun
    from ..engine import simulate
    from ..instance import public_view
    rp, pj = proto_modules()
    cfg = m5.PROTO[name]
    view = public_view(inst, model.information)
    d = rp.inst_dict(inst, view)
    bser, par = rp.allowance(cfg["rule"], inst, d, view)
    params = {"inner": "A9", "project": True, **par}
    spec = spec_of(params)
    base = drun.make_policy(spec, inst)
    p = {k: copy.deepcopy(v) for k, v in base._p.items() if k != "project"}
    p["inner"] = NoticeCriticalRatio(**dict(base._p.get("inner_params") or {}))
    p["inner_params"] = {}
    with f5_patch(cfg["f5"]):
        pol = pj.ProjectedGuard(**p, N_bound=base.N_bound, on_unavailable=base.on_unavailable, allowance_series=bser,
                                rho=1.0, project=True)
        res = simulate(inst, pol, model, ecfg, lender_seed=int(c), policy_seed=int(ps))
    alg = np.cumsum(np.asarray(res.per_slot["total"], dtype=np.float64))
    viol = max((alg[t] + R - rhs for (t, _a, R, rhs) in pol.env), default=None)
    extra = {"label": "prototype", "rule": cfg["rule"], "f5": cfg["f5"], "rho": 1.0, "project": True,
             "files_sha256": {f: hashlib.sha256((PROTO_DIR / f).read_bytes()).hexdigest()
                              for f in ("lb.py", "projected.py", "run_proj.py")},
             "B_T": None if bser is None else float(bser[-1]), "env_max_violation_usd": viol,
             "env_slots": len(pol.env), "projection": dict(pol.proj)}
    return res, pol, spec, extra


# ---------------------------------------------------------------- jobs: week runs
def one_run(spec: dict, name: str, inst, model, ecfg, refs: dict, own, c: int, ps: int, mode: str) -> dict:
    """One run of tag `name` on `inst` under `model` (e7.one_run's steps; BL2 through ms4_common.siloed_run), as
    ms5b_common.week_entry's (or siloed_week_entry's) entry."""
    from ..algos import registry
    from ..drivers.run import driver_inputs, make_policy
    from ..engine import simulate
    pid, params = spec["policy"]["id"], dict(spec["policy"]["params"] or {})
    t0 = time.perf_counter()
    if registry.entry(pid).runner == "siloed":
        d = m4.siloed_run(inst, spec, model, ecfg, c, ps)
        return m5.siloed_week_entry(d, inst, model, refs, own, tag_name=name, spec=spec, ps=ps, c=c, mode=mode,
                                    wall_s=time.perf_counter() - t0)
    _, imeta = driver_inputs(pid, params, inst)
    pol = make_policy(spec, inst)
    res = simulate(inst, pol, model, ecfg, lender_seed=int(c), policy_seed=int(ps))
    return m5.week_entry(res, inst, model, refs, own, tag_name=name, spec=spec, pol=pol, ps=ps, c=c, mode=mode,
                         wall_s=time.perf_counter() - t0, imeta=imeta)


def one_proto(name: str, spec_of, inst, model, ecfg, refs: dict, own, c: int, ps: int, mode: str) -> dict:
    """One prototype run's entry (week_entry's fields, policy id A8P's spec, plus 'prototype')."""
    t0 = time.perf_counter()
    res, pol, spec, extra = proto_run(name, spec_of, inst, model, ecfg, c, ps)
    e = m5.week_entry(res, inst, model, refs, own, tag_name=name, spec=spec, pol=pol, ps=ps, c=c, mode=mode,
                      wall_s=time.perf_counter() - t0)
    e["prototype"] = extra
    return e


def _print(e: dict, where: str) -> None:
    a8 = e.get("a8") or {}
    print(f"[e7h] {where} {e['tag']} {e['mode']} p{e['policy_seed']}: ALG {e['ALG']:.4f} USD, r0 {e.get('r0')}, "
          f"status {e.get('status')}, t_a {a8.get('t_a')}, projected {a8.get('projected_slots')}, "
          f"{e.get('wall_s', 0.0):.1f} s", flush=True)


def run_week(job: Job, outputs: mc.JobOutputs, out: Path, *, tags=None, meta_of=None) -> dict:
    """One week job: tag p['tag'] on week c under each mode of p['modes'] and each policy seed, the instance built once
    (L-b999's own instance once more). MS7 hooks (design/ms7/plan.md X1, C53), whose defaults are this driver's own:
    `tags`, the module whose tag, tag_params and tag_table resolve the tag (default ms5b_common; e7c passes
    e7c_tags), and `meta_of`, the run file's meta of a job (default _meta_run, with this driver's gate; e7c passes its
    own, so that its records never carry the confirmation's gate)."""
    from ..drivers import run as drun
    from ..lender import resolve_params
    tg = m5 if tags is None else tags
    p = job.params
    name, c, hz, seeds = p["tag"], int(p["c"]), int(p["horizon_min"]), [int(s) for s in p["policy_seeds"]]
    meta = (_meta_run if meta_of is None else meta_of)(job)
    t0 = time.perf_counter()
    insts: dict = {}

    def inst_of(mode):
        key = m5.instance_key(mode)
        if key not in insts:
            spec0 = m5.week_spec("BL0a", {}, mode=m5.B999_MODE if key == "b999" else "L-tr", c=c, horizon_min=hz,
                                 seeds=seeds, name="e7h_build")
            inst, _, ecfg = drun.build(spec0, c)
            if not ecfg.check_invariants:
                raise RuntimeError("MS5b runs need check_invariants=True")
            insts[key] = {"inst": inst, "ecfg": ecfg, "refs": m4.references(inst), "own": e7._own(inst),
                          "hash": mc.instance_hash(inst), "sizes": e7.instance_sizes(inst)}
        return insts[key]
    errors, rows, models, params_rec = [], [], {}, {}
    for mode in p["modes"]:
        b = inst_of(mode)
        inst, ecfg, refs, own = b["inst"], b["ecfg"], b["refs"], b["own"]
        if name in m5.PROTO:
            def spec_of(params, mode=mode):
                return m5.week_spec("A8P", params, mode=mode, c=c, horizon_min=hz, seeds=seeds,
                                    name=f"e7h_{p['part']}_{name}")
            spec = spec_of({"inner": "A9", "project": True})
            fn, args = one_proto, (name, spec_of)
        else:
            params = tg.tag_params(name, inst)
            params_rec[m5.instance_key(mode)] = params
            spec = m5.week_spec(tg.tag(name).id, params, mode=mode, c=c, horizon_min=hz, seeds=seeds,
                                name=f"e7h_{p['part']}_{name}")
            fn, args = one_run, (spec, name)
        model = drun._lender_model(spec, inst)
        models[mode] = {**e7._lender_dict(model), "resolved": resolve_params(inst, model)}
        for ps in seeds:
            e = mc.try_run(errors, f"{name} {mode} p{ps}", fn, *args, inst, model, ecfg, refs, own, c, ps, mode)
            if e is not None:
                rows.append(e)
                _print(e, f"{p['part']} c{c}")
    rec = {"meta": meta, "part": p["part"], "kind": "week", "tag": name, "tags": tg.tag_table([name]),
           "params": params_rec, "c": c, "modes": list(p["modes"]), "policy_seeds": seeds, "horizon_min": hz,
           "instances": {k: {"instance_hash": v["hash"], "sizes": v["sizes"], "references": v["refs"],
                             "own_capacity_usd": v["own"]} for k, v in insts.items()},
           "lender_models": models, "wall_s": time.perf_counter() - t0, "runs": rows, "errors": _errs(errors)}
    outputs.dump(e7._jsonish(rec), run_path(out, job.id), compact=True)
    return {"runs": len(rows), "errors": errors, "instance_hash": (insts.get("base") or {}).get("hash"),
            "r0": [[r["mode"], r["policy_seed"], r.get("r0")] for r in rows]}


def run_premium(job: Job, outputs: mc.JobOutputs, out: Path) -> dict:
    """P0's notice premium of P3 on the E7 menu (§5 P0): per contract class (tau, H) of the week instance of alignment
    c the cheapest price per GPU-hour over the revocable sites that offer it, its premium over the cheapest revocable
    contract, and the base contracts kbar that A9.3's table picks (counts over usable (site, LLM) pairs)."""
    from ..algos.a9 import contract_table
    from ..drivers import run as drun
    from ..instance import public_view
    p = job.params
    c, hz = int(p["c"]), int(p["horizon_min"])
    meta = _meta_run(job)
    inst, model, _ = drun.build(m5.week_spec("BL0a", {}, c=c, horizon_min=hz, name="e7h_premium"), c)
    view = public_view(inst, model.information)
    price = np.asarray(view.price, dtype=np.float64)
    rows = []
    for k, ct in enumerate(view.contracts):
        offer = [l for l, s in enumerate(view.sites) if k in s.menu and (s.kind == "protected") == bool(ct.protected)
                 and np.isfinite(price[l, k])]
        pr = [float(price[l, k]) for l in offer]
        rows.append({"contract": ct.id, "tau_slots": ct.tau_slots,
                     "tau_min": None if ct.tau_slots is None else ct.tau_slots * view.grid.slow_min,
                     "H_min": ct.H_min, "prepaid_min": ct.prepaid_min, "class": ct.klass,
                     "protected": bool(ct.protected), "n_sites": len(offer),
                     "min_price_usd_per_gpu_h": min(pr) if pr else None,
                     "median_price_usd_per_gpu_h": float(np.median(pr)) if pr else None})
    rev = [r["min_price_usd_per_gpu_h"] for r in rows if r["min_price_usd_per_gpu_h"] is not None
           and not r["protected"]]
    base = min(rev) if rev else None
    for r in rows:
        put(r, "premium_over_cheapest", None if base is None or r["min_price_usd_per_gpu_h"] is None
            else r["min_price_usd_per_gpu_h"] / base - 1.0, "no revocable price")
    tab = contract_table(view, insure=True)
    kbar = np.asarray(tab["kbar"])
    picks: dict = {}
    for k in kbar[kbar >= 0].ravel():
        cid = view.contracts[int(k)].id
        picks[cid] = picks.get(cid, 0) + 1
    rec = {"meta": meta, "part": p["part"], "kind": "premium", "c": c, "horizon_min": hz,
           "instance_hash": mc.instance_hash(inst), "contracts": rows, "kbar_counts": dict(sorted(picks.items())),
           "note": "cheapest price per contract over the revocable sites offering it; kbar of A9.3 per usable "
                   "(site, LLM) pair (contracts.c2_contract_table)", "runs": []}
    outputs.dump(e7._jsonish(rec), run_path(out, job.id), compact=True)
    return {"runs": 0, "contracts": len(rows)}


# ---------------------------------------------------------------- jobs: one-day cells (E3, Q44, E5) and gap days
def _siloed_spec(name: str, inst):
    """(SILOED parameters, params_of) of a tag run per borrower (E3 siloed, Q41(a)): the inner id with the tag's
    parameters; Sublet's and Sublet-MS4's sub-runs take their rule on their own sub-instance (as E3's
    Sublet-siloed)."""
    t = m5.tag(name)
    if isinstance(t.params, str):
        rule = m5.PARAM_RULES[t.params]
        base = rule(inst)
        inner_p = {k: v for k, v in base.items()}
        if t.id == "A8":
            return {"inner": "A8", "inner_params": {"inner": base["inner"]}}, rule
        return {"inner": t.id, "inner_params": inner_p}, rule
    return {"inner": t.id, "inner_params": m5.tag_params(name)}, None


def _e3_shared(name, sh_inst, model, ecfg, refs, ov_sh, c, ps, seeds) -> dict:
    from ..algos import registry
    from ..drivers import run as drun
    from ..engine import simulate
    t0 = time.perf_counter()
    if name in m5.PROTO:
        def spec_of(params):
            return e3.run_spec("A8P", params, ov_sh, c, seeds, name)
        res, pol, spec, extra = proto_run(name, spec_of, sh_inst, model, ecfg, c, ps)
        pid, params = "A8P", dict(spec["policy"]["params"])
    else:
        pid, params, extra = m5.tag(name).id, m5.tag_params(name, sh_inst), None
        spec = e3.run_spec(pid, params, ov_sh, c, seeds, name)
        pol = drun.make_policy(spec, sh_inst)
        res = simulate(sh_inst, pol, model, ecfg, lender_seed=c, policy_seed=int(ps))
    rp = {**params, **(pol.params() or {})}
    row = {"tag": name, "policy_id": pid, "params": rp, "mode": "shared", "p": int(ps),
           "info_class": registry.info_class(pid, rp, model.information), **e3.run_row(res, sh_inst, model, refs)}
    if pid in m5.GUARDED_IDS:
        row["a8"] = m5.guard_fields(res, sh_inst, params, model.information)
    a9 = m5.a9_fields(res.metrics.get("policy") or {})
    if a9 is not None:
        row["a9"] = a9
    if extra is not None:
        row["prototype"] = extra
    row["r0"] = (row.get("accountings") or {}).get("overflow_over_bl0a")
    row["wall_s"] = time.perf_counter() - t0
    return row


def _e3_siloed(name, si_inst, sh_inst, model, ecfg, refs, ov_si, c, ps, seeds) -> dict:
    from ..algos import registry
    from ..experiments.e6 import bl0a_all
    from . import q44_study as q44
    t0 = time.perf_counter()
    params0, pof = _siloed_spec(name, si_inst)
    spec = e3.run_spec("SILOED", params0, ov_si, c, seeds, name)
    d = m4.siloed_run(si_inst, spec, model, ecfg, c, int(ps), params_of=pof)
    subs = []
    for srow, res_b, sub in zip(d["sub_runs"], d["results"], d["instances"]):
        x = {**srow, **e3.run_row(res_b, sub, model), "bl0a_usd": float(bl0a_all(sub))}
        if params0["inner"] == "A8P":
            x.update(m5.allowance_fields(m4.a8_record(res_b, sub, srow["params"], model.information), srow["params"]))
        if params0["inner"] in m5.GUARDED_IDS:
            x.update(m5.guard_extras(res_b, res_b.metrics.get("policy") or {}))
        a9 = m5.a9_fields(res_b.metrics.get("policy") or {})
        if a9 is not None:
            x["a9"] = a9
        subs.append(x)
    served = sum(r["served_load_min"] for r in subs)
    cap = sum(r["capacity_load_min"] for r in subs)
    total = float(d["total"])
    rvs = [r["ratio_validity"] for r in subs if r["ratio_validity"] is not None]
    row = {"tag": name, "policy_id": "SILOED", "inner_id": d["inner_id"], "params": params0, "mode": "siloed",
           "p": int(ps), "info_class": registry.info_class("SILOED", params0, model.information),
           "inner_params_of": None if pof is None else m5.PARAM_RULE_TEXT[m5.tag(name).params],
           "ALG": total, "components": {k: float(v) for k, v in d["components"].items()},
           "grouped": q44.grouped(d["components"]), "accountings": m4.accountings(total, sh_inst, refs),
           "replica_utilization": served / cap if cap > 0 else None, "served_load_min": served,
           "capacity_load_min": cap, "loads": sum(r["loads"] for r in subs),
           "n_invariant_failures": len(d["invariant_failures"]),
           "invariant_failures": list(d["invariant_failures"])[:10],
           "gpu_only_lease_slots": sum(r["gpu_only_lease_slots"] for r in subs),
           "ratio_validity": rvs[0] if rvs else None,
           "plan_class_p1": bool(subs) and all(r["plan_class_p1"] for r in subs),
           "schedule_hashes": sorted({r["schedule_hash"] for r in subs}), "n_sub_runs": len(subs),
           "certificates": m4.count_certificates([r for r in subs if "certificate" in r]) if subs and
           "certificate" in subs[0] else None, "sub_runs": subs}
    row["r0"] = row["accountings"].get("overflow_over_bl0a")
    row["wall_s"] = time.perf_counter() - t0
    return row


def run_e3cell(job: Job, outputs: mc.JobOutputs, out: Path) -> dict:
    """One E3 cell (§4.4(c); P2a, P1 (iii), P2 (ii), P4): e3's shared and siloed instances, the LPs ('none',
    'shared', or 'all': the shared instance and every sub-instance, as e3.run_cell), the runs of p['entries'] and the
    cell record at e3.cell_file in the fields e3.run_milp and e3.cell_benchmarks read."""
    from .. import config as C
    from .e6 import bl0a_all
    p = job.params
    b, u, mu, c = int(p["b"]), int(p["u"]), float(p["mu"]), int(p["c"])
    hz, seeds = p.get("horizon"), [int(s) for s in p["policy_seeds"]]
    meta = _meta_run(job)
    t_start = time.perf_counter()
    limit = mc.milp_limit_s()
    sh_inst, model, ecfg, ov_sh = e3.build_instance(b, u, mu, c, True, hz)
    si_inst, _, _, ov_si = e3.build_instance(b, u, mu, c, False, hz)
    subs = e3.sub_instances(si_inst)
    refs = m4.references(sh_inst)
    sched = e3.trace_schedule(sh_inst, model, c)
    sh = mc.schedule_hash(sched)
    sub_sched = {bid: e3.trace_schedule(s, model, c) for bid, s in subs.items()}
    sub_sh = {bid: mc.schedule_hash(s) for bid, s in sub_sched.items()}
    ih = {"shared": mc.instance_hash(sh_inst), "siloed": mc.instance_hash(si_inst),
          "sub": {bid: mc.instance_hash(s) for bid, s in subs.items()}}
    errors: list = []
    lps: dict = {}
    lp_parts = [] if p["lp"] == "none" else ([("shared", sh_inst, sched)] + (
        [(bid, subs[bid], sub_sched[bid]) for bid in subs] if p["lp"] == "all" else []))
    for part, inst_x, sch in lp_parts:
        def one_lp(part=part, inst_x=inst_x, sch=sch):
            rec = e3.solve_bench(inst_x, sch, "lp", limit, job=job.id, kind="lp", part=part,
                                 borrower=None if part == "shared" else part, b=b, u=u, mu=mu, c=c,
                                 instance_hash=ih["shared"] if part == "shared" else ih["sub"][part],
                                 schedule_hash=sh if part == "shared" else sub_sh[part], gate=meta["gate"])
            path = e3.lp_file(out, b, u, mu, c, part)
            outputs.dump(rec, path)
            lps[part] = {"file": e3._rel(path, out), "status": rec["status"], "objective": rec["objective"],
                         "n_vars": rec["size"].get("n_vars"), "solve_s": rec["solve_s"]}
        mc.try_run(errors, f"lp_{part}", one_lp)
    rows = []
    for name, mode in p["entries"]:
        for ps in seeds:
            if mode == "shared":
                r = mc.try_run(errors, f"{name}_{mode}_p{ps}", _e3_shared, name, sh_inst, model, ecfg, refs, ov_sh,
                               c, ps, seeds)
            else:
                r = mc.try_run(errors, f"{name}_{mode}_p{ps}", _e3_siloed, name, si_inst, sh_inst, model, ecfg, refs,
                               ov_si, c, ps, seeds)
            if r is not None:
                r["status"] = m5.run_status(r)
                rows.append(r)
                print(f"[e7h] {job.id} {name} {mode} p{ps}: ALG {r['ALG']:.4f}, r0 {r.get('r0')}, "
                      f"{r['wall_s']:.2f} s", flush=True)
    mismatch = [{"tag": r["tag"], "p": r["p"], "borrower": s.get("borrower")} for r in rows
                for s in ([r] if r["mode"] == "shared" else r["sub_runs"])
                if s["schedule_hash"] != (sh if r["mode"] == "shared" else sub_sh[s["borrower"]])]
    rec = {"meta": meta, "job": job.id, "exp": EXP, "part": p["part"], "kind": "e3cell", "b": b, "u": u, "mu": mu,
           "c": c, "mu_key": num_key(mu), "config": e3.CONFIG, "overrides": {"shared": ov_sh, "siloed": ov_si},
           "horizon": hz, "borrower_list": e3.borrower_ids(b), "instances": ih,
           "config_hashes": {"shared": C.config_hash(sh_inst.config), "siloed": C.config_hash(si_inst.config)},
           "schedule_hash": sh, "sub_schedule_hashes": sub_sh, "schedule_mismatch": mismatch,
           "lender_model": e7._lender_dict(model), "sizes": e3.inst_sizes(sh_inst),
           "borrowers": e3.borrower_block(sh_inst, si_inst, b),
           "bl0a": {"shared": float(bl0a_all(sh_inst)), "siloed": float(bl0a_all(si_inst)),
                    "sub": {bid: float(bl0a_all(s)) for bid, s in subs.items()}},
           "references": refs, "lps": lps, "policy_seeds": seeds, "entries": p["entries"],
           "tags": m5.tag_table(sorted({t for t, _m in p["entries"]})), "runs": rows, "errors": _errs(errors),
           "git_revision": mc.git_revision(), "wall_s": time.perf_counter() - t_start}
    outputs.dump(e7._jsonish(rec), e3.cell_file(out, b, u, mu, c), compact=True)
    return {"runs": len(rows), "errors": errors, "lps": len(lps), "instance_hash": ih["shared"],
            "schedule_mismatch": len(mismatch)}


def run_e3milp(job: Job, outputs: mc.JobOutputs, out: Path) -> dict:
    """One MILP of a cell (§4.4(c), P4's sizing): e3.run_milp unchanged on e3's job id and the cell record that
    run_e3cell wrote (instance and schedule hashes checked there); its record gains the part's gate."""
    import json
    g = gate(job.params["part"])
    p = job.params
    ej = Job(job.id, "milp", {"b": p["b"], "u": p["u"], "mu": p["mu"], "c": p["c"], "part": p["part_"],
                              "horizon": p["horizon"]}, job.est_s)
    r = e3.run_milp(ej, outputs, out)
    for path in outputs.paths:                           # the gate (and the pilot record) in every output (§5)
        tmp = mc.partial_path(path)
        d = json.loads(tmp.read_text())
        d["gate"] = g
        tmp.write_text(json.dumps(mc.jsonable(d), indent=1, allow_nan=False) + "\n")
    return r


def _q44_build(blk: str, inst_id: str, c: int, window):
    from ..drivers import run as drun
    from ..instance import restrict_horizon
    from . import q44_study as q44
    block = q44.load_block(blk)
    idef = next(i for i in block["instances"] if i["id"] == inst_id)
    spec = drun.load_run_spec(q44.run_spec(block, idef, "BL0a", "L-tr", c, [0]))
    inst, _, ecfg = drun.build(spec, c)
    if window:
        inst = restrict_horizon(inst, int(window[0]), int(window[1]))
    return block, idef, inst, ecfg


def _q44_spec(block, idef, name: str, mode: str, c: int, seeds, params) -> dict:
    """q44_study.run_spec of the cell-mode (BL0a's, then the tag's id, parameters and information model)."""
    from ..drivers import run as drun
    from . import q44_study as q44
    raw = q44.run_spec(block, idef, "BL0a", mode, c, seeds)
    raw["name"] = re.sub(r"[^A-Za-z0-9_.-]", "_", name)
    raw["policy"] = {"id": "A8P" if name in m5.PROTO else m5.tag(name).id, "params": copy.deepcopy(params)}
    if name not in m5.PROTO and m5.tag(name).information != "I1":
        raw["lender_model"]["information"] = m5.tag(name).information
    return drun.load_run_spec(raw)


def run_q44(job: Job, outputs: mc.JobOutputs, out: Path) -> dict:
    """One Q44 cell (P1 (ii), P2 (ii), P4, grid): the instance of q44_study's block (built once; the window in reduced
    runs), every tag of p['entries'] at its seeds under each mode."""
    from ..drivers import run as drun
    p = job.params
    c = int(p["c"])
    meta = _meta_run(job)
    block, idef, inst, ecfg = _q44_build(p["block"], p["inst"], c, p.get("window"))
    refs, own = m4.references(inst), e7._own(inst)
    errors, rows = [], []
    for mode in p["modes"]:
        for name, seeds in p["entries"]:
            for ps in seeds:
                if name in m5.PROTO:
                    def spec_of(params, mode=mode, seeds=seeds):
                        return _q44_spec(block, idef, name, mode, c, seeds, params)
                    spec = spec_of({"inner": "A9", "project": True})
                    model = drun._lender_model(spec, inst)
                    e = mc.try_run(errors, f"{name} {mode} p{ps}", one_proto, name, spec_of, inst, model, ecfg, refs,
                                   own, c, ps, mode)
                else:
                    spec = _q44_spec(block, idef, name, mode, c, seeds, m5.tag_params(name, inst))
                    model = drun._lender_model(spec, inst)
                    e = mc.try_run(errors, f"{name} {mode} p{ps}", one_run, spec, name, inst, model, ecfg, refs, own,
                                   c, ps, mode)
                if e is not None:
                    rows.append(e)
                    _print(e, f"{p['part']} {p['inst']} c{c}")
    rec = {"meta": meta, "part": p["part"], "kind": "q44", "block": p["block"], "inst": p["inst"], "c": c,
           "modes": p["modes"], "entries": p["entries"], "window": p.get("window"),
           "tags": m5.tag_table([t for t, _s in p["entries"]]), "instance_hash": mc.instance_hash(inst),
           "instance": e7.instance_sizes(inst), "references": refs, "own_capacity_usd": own, "runs": rows,
           "errors": _errs(errors)}
    outputs.dump(e7._jsonish(rec), run_path(out, job.id), compact=True)
    return {"runs": len(rows), "errors": errors, "instance_hash": rec["instance_hash"]}


def run_e5(job: Job, outputs: mc.JobOutputs, out: Path) -> dict:
    """One E5 cell (P4, second): e5.e5_instance of the menu at mu 1 (the long menu with the short menu's demand), the
    tag under the levels trace and all1."""
    from ..drivers import run as drun
    from . import e5
    p = job.params
    name, menu, c, hz = p["tag"], p["menu"], int(p["c"]), p.get("horizon_min")
    meta = _meta_run(job)
    inst, _, ecfg, info = e5.e5_instance(menu, MU, c, "trace", horizon_min=hz)
    refs, own = m4.references(inst), e7._own(inst)
    errors, rows = [], []
    params = m5.tag_params(name, inst)
    for level in p["levels"]:
        spec = e5.e5_spec(menu, MU, c, level, m5.tag(name).id, params, horizon_min=hz)
        model = drun._lender_model(spec, inst)
        for ps in p["policy_seeds"]:
            e = mc.try_run(errors, f"{name} {level} p{ps}", one_run, spec, name, inst, model, ecfg, refs, own, c,
                           int(ps), level)
            if e is not None:
                rows.append(e)
                _print(e, f"{p['part']} e5 {menu} c{c}")
    rec = {"meta": meta, "part": p["part"], "kind": "e5", "tag": name, "tags": m5.tag_table([name]), "menu": menu,
           "c": c, "levels": p["levels"], "horizon_min": hz, "params": params, "instance_hash": mc.instance_hash(inst),
           "instance_info": info, "references": refs, "own_capacity_usd": own, "runs": rows, "errors": _errs(errors)}
    outputs.dump(e7._jsonish(rec), run_path(out, job.id), compact=True)
    return {"runs": len(rows), "errors": errors}


def run_gap(job: Job, outputs: mc.JobOutputs, out: Path) -> dict:
    """One gap-day job (second, grid; E7(e)'s instance ms4_common.gap_instance(c)): the tag at its seeds with
    drivers.run.ratio_validity('slow', ...)."""
    from ..drivers.run import _lender_model, ratio_validity
    p = job.params
    name, c, hz = p["tag"], int(p["c"]), int(p["horizon_min"])
    meta = _meta_run(job)
    inst, model, ecfg, info = m4.gap_instance(c, horizon_min=hz)
    refs, own, ih = m4.references(inst), e7._own(inst), mc.instance_hash(inst)
    rv = ratio_validity(e7.GAP_GRID, inst, model)
    params = m5.tag_params(name, inst)
    spec = e7.gap_spec(m5.tag(name).id, params, horizon_min=hz, c=c, seeds=p["policy_seeds"], name=f"e7h_gap_{name}")
    model = _lender_model(spec, inst)
    errors, rows = [], []
    for ps in p["policy_seeds"]:
        e = mc.try_run(errors, f"{name} p{ps}", one_run, spec, name, inst, model, ecfg, refs, own, c, int(ps), "L-tr")
        if e is not None:
            e.update(ratio_validity=rv, instance_hash=ih)
            rows.append(e)
            _print(e, f"{p['part']} gap c{c}")
    rec = {"meta": meta, "part": p["part"], "kind": "gap", "tag": name, "tags": m5.tag_table([name]), "c": c,
           "horizon_min": hz, "params": params, "instance_hash": ih, "instance_info": info, "references": refs,
           "own_capacity_usd": own, "ratio_validity": rv, "runs": rows, "errors": _errs(errors)}
    outputs.dump(e7._jsonish(rec), run_path(out, job.id), compact=True)
    return {"runs": len(rows), "errors": errors, "instance_hash": ih}


def run_gap_lp(job: Job, outputs: mc.JobOutputs, out: Path) -> dict:
    """The merged LP of a gap day (as e7.run_gap_lp, §3.8 of the MS4 spec): BL0a's engine run gives the schedule,
    drivers.bench.bench_for(res, inst, 'lp', grid='slow', merged=True, allow_large=True, time_limit_s=1500); writes
    lb/gap_lp_c<c>.json (versioned)."""
    from ..drivers.bench import bench_for
    from ..drivers.run import make_policy, ratio_validity
    from ..engine import simulate
    from .e1 import _solve_record
    from .e6 import bl0a_all
    p = job.params
    c, hz = int(p["c"]), int(p["horizon_min"])
    meta = _meta_run(job)
    inst, model, ecfg, info = m4.gap_instance(c, horizon_min=hz)
    ih = mc.instance_hash(inst)
    spec = e7.gap_spec("BL0a", {}, horizon_min=hz, c=c, seeds=(0,), name="e7h_gap_BL0a")
    res = simulate(inst, make_policy(spec, inst), model, ecfg, lender_seed=c, policy_seed=0)
    sh = mc.schedule_hash(res.schedule)
    t0 = time.perf_counter()
    sr = bench_for(res, inst, "lp", grid=e7.GAP_GRID, merged=True, allow_large=True, time_limit_s=e7.GAP_LP_LIMIT_S,
                   return_plan=False)
    size = sr.size or {}
    lp = _solve_record(sr, job=job.id, kind="lp", c=c, instance_hash=ih, schedule_hash=sh,
                       time_limit_s=e7.GAP_LP_LIMIT_S, merged=True, merged_sites=size.get("merged_sites"),
                       horizon_min=hz, bl0a_analytic_usd=float(bl0a_all(inst)),
                       bl0a_engine_usd=float(res.components["total"]),
                       ratio_validity=ratio_validity(e7.GAP_GRID, inst, model), demand_sha256=info.get("demand_sha256"),
                       label="merged relaxation LP bound (Proposition M6, PROVEN)", wall_s=time.perf_counter() - t0,
                       gate=meta["gate"], reduced=meta["reduced"])
    outputs.dump(lp, gap_lp_path(out, c))
    return {"runs": 1, "errors": [], "status": sr.status, "objective": sr.objective, "instance_hash": ih,
            "schedule_hash": sh}


# ---------------------------------------------------------------- jobs: families (P3, fam)
def run_fam(job: Job, outputs: mc.JobOutputs, out: Path) -> dict:
    """One family instance-mode (§4.4(d), P3), as q44_study.run_family: every tag at its seeds ('paired' modes: lender
    seed = policy seed; 'fixed': lender seed 0), exact OPT by q44_study._family_lb (per schedule, per run under the
    adaptive lender), the certificate (q44_study.certificate, core_exact) of every A8 and A8P run with Lemma G5's
    check B_on(T) <= OPT, the purchase count (leases bought) and the projected slots."""
    from ..algos import registry
    from ..drivers import run as drun
    from ..engine import EngineConfig, simulate
    from ..instance import from_core
    from ..types import LenderModel
    from . import q44_study as q44
    p = job.params
    fam, v, mode = p["family"], p["values"], p["mode"]
    meta = _meta_run(job)
    fmode = q44.FAMILY_MODES[mode]
    I, F, desc = q44.family_core(fam, v)
    zero = [np.zeros(0, dtype=np.int64)] * int(I.a.shape[0])
    ih = mc.instance_hash(from_core(I, zero)[0])
    lbs: dict = {}
    errors, rows = [], []
    for name, seeds in p["entries"]:
        tg = m5.tag(name)
        model = LenderModel(schedule=fmode["schedule"], information=tg.information, params=dict(fmode["params"]))
        for s in seeds:
            lseed = int(s) if fmode["lender_seeds"] == "paired" else 0

            def one(name=name, s=s, lseed=lseed, model=model):
                inst, _ = from_core(I, zero)
                params = m5.tag_params(name, inst)
                vals, imeta = drun.driver_inputs(tg.id, params, inst)
                pol = drun.make_policy({"policy": {"id": tg.id, "params": params}}, inst, inputs=vals)
                t0 = time.perf_counter()
                res = simulate(inst, pol, model, EngineConfig(check_invariants=True), lender_seed=lseed,
                               policy_seed=int(s))
                if fmode["oblivious"]:
                    if lseed not in lbs:
                        lbs[lseed] = q44._family_lb(fam, F, I, res, inst)
                    opt, lbm = lbs[lseed]
                else:
                    opt, lbm = q44._family_lb(fam, F, I, res, inst)
                rep = res.metrics.get("policy") or {}
                tot = float(res.components["total"])
                row = {"tag": name, "policy_id": tg.id, "params": params, "policy_seed": int(s), "lender_seed": lseed,
                       "information": tg.information, "total": tot, "n_purchases": len(res.leases), "opt": float(opt),
                       "opt_method": lbm.get("method"), "ratio_opt": tot / opt if opt > 0 else None,
                       "n_invariant_failures": len(res.invariant_failures),
                       "components": {k: float(x) for k, x in res.components.items()},
                       "info_class": registry.info_class(tg.id, params, tg.information),
                       "schedule_hash": mc.schedule_hash(res.schedule), "wall_s": time.perf_counter() - t0}
                if tg.id in m5.GUARDED_IDS:
                    cert = q44.certificate(res, inst, rep, core_exact=True)
                    if cert.get("available") and "B_on_T" in cert:
                        cert["lemma_G5_ok"] = bool(cert["B_on_T"] <= opt * (1 + q44.CERT_TOL) + q44.CERT_TOL)
                        cert["held"] = bool(cert["held"] and cert["lemma_G5_ok"])
                    from .e1 import cert_case
                    row["a8"] = {"certificate": {k: x for k, x in cert.items() if not isinstance(x, list)},
                                 "certificate_case": cert_case(cert), "t_a": rep.get("t_a"),
                                 "aborted": rep.get("aborted"), **m5.guard_extras(res, rep)}
                a9 = m5.a9_fields(rep)
                if a9 is not None:
                    row["a9"] = a9
                row["status"] = "invariant_failure" if row["n_invariant_failures"] else "ok"
                return row
            r = mc.try_run(errors, f"{name} p{s}", one)
            if r is not None:
                rows.append(r)
    rec = {"meta": meta, "part": p["part"], "kind": "fam", "family": fam, "values": v, "inst": p["inst"],
           "mode": mode, "mode_def": fmode, "core_instance": desc, "instance_hash": ih,
           "fam_class": fam.get("fam", fam["id"]), "entries": p["entries"],
           "tags": m5.tag_table([t for t, _s in p["entries"]]), "lbs": {num_key(k): v[0] for k, v in lbs.items()},
           "runs": rows, "errors": _errs(errors)}
    outputs.dump(e7._jsonish(rec), run_path(out, job.id), compact=True)
    print(f"[e7h] {job.id}: {len(rows)} runs, {len(errors)} errors", flush=True)
    return {"runs": len(rows), "errors": errors}


RUNNERS = {"week": run_week, "premium": run_premium, "e3cell": run_e3cell, "e3milp": run_e3milp, "q44": run_q44,
           "e5": run_e5, "gap": run_gap, "gap_lp": run_gap_lp, "fam": run_fam}


def run(job: Job, outputs: mc.JobOutputs, out: Path) -> dict:
    gate(job.params["part"])
    return RUNNERS[job.params["kind"]](job, outputs, out)


# ---------------------------------------------------------------- outputs of a part
def output_path(out, job: Job) -> Optional[Path]:
    p = job.params
    k = p["kind"]
    if k == "e3cell":
        return e3.cell_file(out, p["b"], p["u"], p["mu"], p["c"])
    if k == "e3milp":
        return e3.milp_file(out, p["b"], p["u"], p["mu"], p["c"], p["part_"])
    if k == "gap_lp":
        return gap_lp_path(out, p["c"])
    return run_path(out, job.id)


def part_outputs(out_p: Path, js: list) -> tuple:
    """({job id: output} of the jobs whose record says 'ok', {job id: status} of the others ('no record' without one),
    ignored outputs: an output present while its job's record is not 'ok')."""
    recs = mc.read_records(out_p)
    files, not_ok, ignored = {}, {}, []
    for j in js:
        rec = recs.get(j.id) or {}
        path = output_path(out_p, j)
        if rec.get("status") != "ok":
            not_ok[j.id] = rec.get("status") or "no record"
            if path is not None and path.is_file():
                ignored.append({"job": j.id, "status": rec.get("status"), "output": e3._rel(path, out_p)})
            continue
        d = mc.read_json(path) if path is not None else None
        if d is None:
            not_ok[j.id] = "ok record without a readable output"
            continue
        files[j.id] = d
    return files, not_ok, ignored


def cell_key(job: Job) -> str:
    """The cell of a run in a summary's tables: the week (config seed), '<inst>:c<c>' (Q44), '<menu>:c<c>' (E5),
    'gap:c<c>', 'b<b>:c<c>' (E3), '<instance>:<mode>' (families)."""
    p = job.params
    k = p["kind"]
    if k == "week":
        return num_key(p["c"])
    if k == "q44":
        return f"{p['inst']}:c{p['c']}"
    if k == "e5":
        return f"{p['menu']}:c{p['c']}"
    if k == "gap":
        return f"gap:c{p['c']}"
    if k == "e3cell":
        return f"b{p['b']}:c{p['c']}"
    if k == "fam":
        return f"{p['inst']}:{p['mode']}"
    return job.id


def expected_runs(job: Job) -> list:
    """(tag, mode, cell, seed) of every run a job owes."""
    p = job.params
    k, cell = p["kind"], cell_key(job)
    if k == "week":
        return [(p["tag"], m, cell, int(s)) for m in p["modes"] for s in p["policy_seeds"]]
    if k == "q44":
        return [(t, m, cell, int(s)) for m in p["modes"] for t, ss in p["entries"] for s in ss]
    if k == "e5":
        return [(p["tag"], lv, cell, int(s)) for lv in p["levels"] for s in p["policy_seeds"]]
    if k == "gap":
        return [(p["tag"], "L-tr", cell, int(s)) for s in p["policy_seeds"]]
    if k == "e3cell":
        return [(t, m, cell, int(s)) for t, m in p["entries"] for s in p["policy_seeds"]]
    if k == "fam":
        return [(t, p["mode"], cell, int(s)) for t, ss in p["entries"] for s in ss]
    return []


def guard_brief(a8: Optional[dict]) -> Optional[dict]:
    """The guard facts of a run (H3, P2 (1)): certificate held and case, envelope, abort, S on FB everywhere, T0g in
    bound form everywhere, robust slots, S's switches, projected slots and counts, B(T), the allowance rule and, only
    when the record has it (A8P at 'allowance' 'lb'; ms5b_common.guard_extras), the OnlineLB's block online_lb."""
    if not a8:
        return None
    cert = a8.get("certificate") or {}
    env = a8.get("envelope") or {}
    return {"held": cert.get("held"), "case": a8.get("certificate_case"), "env_ok": env.get("ok"),
            "env_max_excess_usd": env.get("max_excess_usd"), "aborted": bool(a8.get("aborted")), "t_a": a8.get("t_a"),
            "s_fb_all": a8.get("s_fb_all"), "t0g_bound_all": a8.get("t0g_bound_all"), "project": a8.get("project"),
            "robust_slots": a8.get("robust_slots"), "switches": a8.get("switches"),
            "projected_slots": a8.get("projected_slots"), "projection": a8.get("projection"), "B_T": a8.get("B_T"),
            "B0_rule": a8.get("B0_rule"), "B0_usd": a8.get("B0_usd"),
            "info_class_reported": a8.get("info_class_reported"),
            **({"online_lb": dict(a8["online_lb"])} if isinstance(a8.get("online_lb"), dict) else {})}


def _a9_brief(a9: Optional[dict]) -> Optional[dict]:
    if not a9:
        return None
    return {k: a9.get(k) for k in ("insured", "marks", "phase_ends", "mark_expiries", "notices", "commit_fallbacks")}


def brief(e: dict, job: Job) -> dict:
    """One run's row in a summary: the cell, tag, mode and seed, r0, ALG, BL0a, the status of the missing-run rule, the
    fallback and stranding totals, the fallback shares, the leases, the guard facts, A9's counts and, for families,
    total, purchases and OPT."""
    p = job.params
    k = p["kind"]
    row = {"job": job.id, "kind": k, "cell": cell_key(job), "tag": e["tag"],
           "mode": e.get("mode", p.get("mode")), "seed": int(e.get("policy_seed", e.get("p", 0))),
           "status": e.get("status") or m5.run_status(e), "r0": e.get("r0"), "ALG": e.get("ALG", e.get("total")),
           "n_invariant_failures": e.get("n_invariant_failures")}
    if k == "e3cell":
        row.update(mode=e["mode"], b=p["b"], c=p["c"])
    elif k == "fam":
        row.update(fam=p["family"].get("fam"), src=p["family"]["id"], inst=p["inst"], total=e["total"],
                   n_purchases=e["n_purchases"], opt=e["opt"], ratio_opt=e.get("ratio_opt"),
                   lender_seed=e.get("lender_seed"))
    else:
        row.update(c=p.get("c"), bl0a_usd=e.get("bl0a_usd"), fallback_usd=e.get("fallback_usd"),
                   stranding_usd=e.get("stranding_usd"), fallback_share=e.get("fallback_share"),
                   fallback_share_after_reclaims=e.get("fallback_share_after_reclaims"), n_leases=e.get("n_leases"))
        if "ratio_validity" in e:
            row["ratio_validity"] = e.get("ratio_validity")
    if e.get("prototype"):
        row["prototype"] = {k2: e["prototype"].get(k2) for k2 in ("label", "rule", "f5", "B_T",
                                                                  "env_max_violation_usd", "projection")}
    g = guard_brief(e.get("a8"))
    if g is not None:
        row["guard"] = g
    if e.get("sub_runs") and any("certificate" in s or "envelope" in s for s in e["sub_runs"]):
        row["sub_guard"] = [{"borrower": s.get("borrower"), **(guard_brief(s) or {})} for s in e["sub_runs"]]
    a9 = _a9_brief(e.get("a9")) or _a9_sum([s.get("a9") for s in e.get("sub_runs") or []])
    if a9 is not None:
        row["a9"] = a9
    return row


def _a9_sum(xs) -> Optional[dict]:
    xs = [x for x in xs if x]
    if not xs:
        return None
    return {k: sum(int(x.get(k) or 0) for x in xs) for k in ("insured", "marks", "phase_ends", "mark_expiries",
                                                             "notices", "commit_fallbacks")}


def collect(out_p: Path, js: list) -> dict:
    """The rows of a part: every run of the 'ok' jobs (brief), the missing runs of the expected grid with their reason
    (the job's status, the run's error, or the run's status), the table {tag: {mode: {cell: {seed: r0}}}} of the ok
    runs (null for a run that is missing or failed: the missing-run rule), the guarded runs (H3) and the files."""
    files, not_ok, ignored = part_outputs(out_p, js)
    by_id = {j.id: j for j in js}
    rows, guarded = [], []
    have: dict = {}
    for jid, f in files.items():
        j = by_id[jid]
        for e in f.get("runs") or []:
            r = brief(e, j)
            rows.append(r)
            have[(r["tag"], r["mode"], r["cell"], r["seed"])] = r
            if r.get("guard"):
                guarded.append({k: r[k] for k in ("job", "cell", "tag", "mode", "seed")} | r["guard"])
            for sg in r.get("sub_guard") or []:
                guarded.append({k: r[k] for k in ("job", "cell", "tag", "mode", "seed")} | sg)
    missing, table = [], {}
    for j in js:
        errs = {e.get("tag"): e.get("error") for e in (files.get(j.id) or {}).get("errors") or []}
        for key in expected_runs(j):
            t, m, cell, s = key
            r = have.get(key)
            ok = r is not None and r["status"] == "ok"
            table.setdefault(t, {}).setdefault(m, {}).setdefault(cell, {})[num_key(s)] = r["r0"] if ok else None
            if not ok:
                why = r["status"] if r is not None else (not_ok.get(j.id) or next(iter(errs.values()), None)
                                                         or "run missing")
                missing.append({"job": j.id, "tag": t, "mode": m, "cell": cell, "seed": s, "why": why})
    return {"files": files, "not_ok": not_ok, "ignored": ignored, "rows": rows, "table": table, "missing": missing,
            "guarded": guarded}


def guard_summary(guarded: list) -> dict:
    """H3's counts over guarded runs: certificates held, envelope violations, aborts, aborts of a projecting run (A8P
    with project true) while S follows FB at every slot and T0g stays in bound form (Proposition P; the one-way guard,
    A8 and A8P with project false, may abort so), S switches, robust-form runs, projected slots and K0 uses."""
    n = len(guarded)
    prop_p = [g for g in guarded if g.get("project") is True and g.get("aborted") and g.get("s_fb_all")
              and g.get("t0g_bound_all")]
    return {"n_runs": n, "held": sum(1 for g in guarded if g.get("held") is True),
            "not_held": [g for g in guarded if g.get("held") is not True][:50],
            "envelope_violations": [g for g in guarded if g.get("env_ok") is False][:50],
            "n_envelope_violations": sum(1 for g in guarded if g.get("env_ok") is False),
            "aborts": sum(1 for g in guarded if g.get("aborted")),
            "aborts_s_fb_bound_form": prop_p[:50], "n_aborts_s_fb_bound_form": len(prop_p),
            "runs_with_switches": sum(1 for g in guarded if g.get("switches")),
            "runs_with_robust_slots": sum(1 for g in guarded if g.get("robust_slots")),
            "projected_slots": sum(int(g.get("projected_slots") or 0) for g in guarded),
            "runs_projected": sum(1 for g in guarded if g.get("projected_slots")),
            "K0": sum(int((g.get("projection") or {}).get("K0") or 0) for g in guarded),
            "dropped_buys": sum(int((g.get("projection") or {}).get("dropped_buys") or 0) for g in guarded)}


def _val(table: dict, t: str, m: str, cell: str, seed: int = 0) -> Optional[float]:
    return ((table.get(t) or {}).get(m) or {}).get(cell, {}).get(num_key(seed))


def w0_table(table: dict, cells, tags, seed: int = 0) -> dict:
    """{tag: {cell: W0 or null}}: the largest r0 over the five stress modes at the seed (null while a mode is
    missing)."""
    out = {}
    for t in tags:
        for cell in cells:
            w, mode, miss = m5.w0_of({m: _val(table, t, m, cell, seed) for m in m5.stress_modes()})
            out.setdefault(t, {})[cell] = w if w is not None else None
    return out


def _median(xs) -> Optional[float]:
    v = [float(x) for x in xs if x is not None]
    return float(statistics.median(v)) if v else None


def _mean(xs) -> Optional[float]:
    v = [float(x) for x in xs if x is not None]
    return float(np.mean(v)) if v else None


def _meta(part: str, js: list, col: dict, **extra) -> dict:
    d = design()
    tags = sorted({t for j in js for t, *_ in expected_runs(j)})
    m = {"exp": EXP, "part": part, "spec": SPEC, "git_revision": mc.git_revision(), "versions": mc.versions(),
         "written": mc._now(), "reduced": d["reduced"], "design": d, "tags": m5.tag_table(tags),
         "jobs": len(js), "jobs_ok": len(col["files"]), "jobs_not_ok": col["not_ok"], "ignored_outputs": col["ignored"],
         "n_runs": len(col["rows"]), "n_missing": len(col["missing"])}
    if is_pilot(part):
        m["pilot"] = m5.pilot_record()
    else:
        ok, why, rec = m5.check_confirmation()
        m["confirmation_gate"] = {"ok": ok, "reason": why, "record": rec}
    if d["reduced"]:
        m["reduced_note"] = f"reduced job list ({REDUCED_ENV}=1): development cells only; not a result"
    m.update(extra)
    return m


# ---------------------------------------------------------------- summaries: the pilot decisions (§5)
def dev_refs() -> dict:
    """P0's references from the development outputs (read only): {(prototype, c, mode): r0} for perf's RCRb, CR and
    BL1Rb (dev:perf/out/b3-b9.jsonl, the files and order of pilot_summary.py), skeptic's NBR (dev_summary.json,
    trace and L-eg), skeptic's BL5N (the same file; §3: BL5N keeps the prototype's rule so that P0 can reproduce
    its dev numbers) and the guarded NBR at Algorithm 1's allowance with safe 'fb' (guarded_summary.json)."""
    import json
    out: dict = {}
    for f in ("b3.jsonl", "b4.jsonl", "b5.jsonl", "b6.jsonl", "b7.jsonl", "b8.jsonl", "b9.jsonl"):
        path = DEV / "perf" / "out" / f
        for ln in (path.read_text().splitlines() if path.is_file() else []):
            if ln.strip():
                r = json.loads(ln)
                mode = "L-" + r["mode"] if r["mode"].startswith("iid-") else r["mode"]
                out[(f"perf:{r['pol']}", int(r["c"]), mode)] = float(r["r0"])
    ds = mc.read_json(DEV / "skeptic" / "out" / "dev_summary.json") or {}
    for name in ("NBR", "BL5N"):
        for c, v in (ds.get(name) or {}).items():
            if v.get("trace") is not None:
                out[(f"skeptic:{name}", int(c), "L-tr")] = float(v["trace"])
            if v.get("eg") is not None:
                out[(f"skeptic:{name}", int(c), "L-eg")] = float(v["eg"])
    gs = mc.read_json(DEV / "skeptic" / "out" / "guarded_summary.json") or []
    for r in gs:
        if r.get("inner") == "NBR" and r.get("safe") == "fb" and r.get("project") and r.get("allow") == "alg1":
            out[("guarded:NBR", int(r["seed"]), r["mode"])] = float(r["r0"])
    return out


REPRO_OF = {"RCRb-repro": "perf:RCRb", "CR-repro": "perf:CR", "BL1N-repro": "perf:BL1Rb", "NBR-repro": "skeptic:NBR",
            "NBR-repro-G": "guarded:NBR", "BL5N": "skeptic:BL5N"}


def decide_p0(col: dict) -> dict:
    refs = dev_refs()
    rep = []
    for r in col["rows"]:
        if r["tag"] in REPRO_OF and r["kind"] == "week":
            ref = refs.get((REPRO_OF[r["tag"]], int(r["c"]), r["mode"]))
            d = None if ref is None or r["r0"] is None else r["r0"] - ref
            rep.append({"tag": r["tag"], "prototype": REPRO_OF[r["tag"]], "c": r["c"], "mode": r["mode"],
                        "r0": r["r0"], "r0_dev": ref, "diff": d, "within": d is not None and abs(d) <= REPRO_TOL})
    ident = next((r for r in col["rows"] if r["tag"] == "A8P-MS4"), None)
    idv = None if ident is None else ident["ALG"] - IDENTITY_USD
    rc_tags = ("BL1", "BL5-cur", "A9")
    rc = m5.rc_rows([{**r, "config_seed": r["c"], "policy_seed": r["seed"]} for r in col["rows"]
                     if r["tag"] in rc_tags and r["kind"] == "week"])
    side = [{"tag": r["tag"], "mode": r["mode"], "r0": r["r0"], "fallback_share": r.get("fallback_share"),
             "fallback_share_after_reclaims": r.get("fallback_share_after_reclaims"),
             "fallback_usd": r.get("fallback_usd"), "stranding_usd": r.get("stranding_usd"),
             "RC": ((rc.get(r["tag"]) or {}).get(r["mode"]) or {}).get(num_key(r["c"]), {}).get("0")}
            for r in col["rows"] if r["tag"] in rc_tags and r["kind"] == "week"]
    flags = [x for x in side if x["RC"] is not None and x["RC"] < RC_FLAG]
    prem = next((f for f in col["files"].values() if f.get("kind") == "premium"), None)
    repro_ok = bool(rep) and all(x["within"] for x in rep) and not [m for m in col["missing"]
                                                                   if m["tag"] in REPRO_OF]
    ident_ok = idv is not None and abs(idv) <= IDENTITY_TOL
    red = {"reduced_note": "a reduced run (2-hour horizon) compares nothing with the development weeks"} \
        if design()["reduced"] else {}
    return {**red, "reproductions": rep, "n_reproductions": len(rep), "n_within": sum(1 for x in rep if x["within"]),
            "worst_abs_diff": max((abs(x["diff"]) for x in rep if x["diff"] is not None), default=None),
            "tolerance": REPRO_TOL, "reproductions_ok": repro_ok,
            "identity": {"ALG": None if ident is None else ident["ALG"], "stored_usd": IDENTITY_USD, "diff_usd": idv,
                         "tolerance_usd": IDENTITY_TOL, "ok": ident_ok,
                         "stored_job": "code/sim/out/e7/main/jobs/e7__main__pol__Sublet__mu__1__c__1.json"},
            "rc_check": {"rows": side, "RC": rc, "below_flag": flags, "flag": RC_FLAG,
                         "note": "decides nothing; a negative RC below -0.005 BL0a is traced in the pre-registration"},
            "premium": None if prem is None else {"contracts": prem["contracts"], "kbar_counts": prem["kbar_counts"]},
            "gate": {"identity_ok": ident_ok, "reproductions_ok": repro_ok,
                     "p2a_may_start": ident_ok and repro_ok,
                     "note": "P2a also needs every MS1-MS5, Q44 and new test passing (not seen by this summary)"}}


def _cell_r0(rows, tag, kind=None, mode=None) -> dict:
    return {r["cell"]: r["r0"] for r in rows if r["tag"] == tag and r["status"] == "ok"
            and (kind is None or r["kind"] == kind) and (mode is None or r["mode"] == mode) and r["seed"] == 0}


def decide_p2a(col: dict) -> dict:
    rows = col["rows"]
    s, a, x = (_cell_r0(rows, t, "e3cell") for t in ("Sublet", "A9", "Proto-alt"))
    cells = sorted(set(s) | set(a) | set(x))
    tab = [{"cell": c, "Sublet": s.get(c), "A9": a.get(c), "Proto-alt": x.get(c),
            "price_sublet": None if s.get(c) is None or a.get(c) is None else s[c] - a[c],
            "price_alt": None if x.get(c) is None or a.get(c) is None else x[c] - a[c]} for c in cells]
    med = _median(t["price_sublet"] for t in tab)
    return {"cells": tab, "n_cells": len(tab), "median_price_sublet": med,
            "median_price_alt": _median(t["price_alt"] for t in tab), "threshold": 0.03,
            "start_lemma_g5_proof": med is not None and med > 0.03,
            "note": "no decision; above 0.03 the written proof of Lemma G5' starts at once (§10, branch)"}


def decide_p3(col: dict) -> dict:
    rows = [r for r in col["rows"] if r["kind"] == "fam"]
    by = {(r["inst"], r["mode"], r["seed"], r["tag"]): r for r in rows}
    mism, n_pairs = [], 0
    for (inst, mode, seed, t), r in by.items():
        if t != "A9" or r.get("fam") not in ("F1", "F2"):
            continue
        rr = by.get((inst, mode, seed, "RR_RENEW"))
        if rr is None:
            continue
        n_pairs += 1
        if abs(r["total"] - rr["total"]) > 1e-9 * max(1.0, abs(rr["total"])) or r["n_purchases"] != rr["n_purchases"]:
            mism.append({"inst": inst, "mode": mode, "seed": seed, "A9": [r["total"], r["n_purchases"]],
                         "RR_RENEW": [rr["total"], rr["n_purchases"]]})
    proj = [r for r in rows if r["tag"] == "Sublet" and r.get("fam") in ("F1", "F2")
            and (r.get("guard") or {}).get("projected_slots")]
    f3 = {}
    for r in rows:
        if r.get("fam") == "F3":
            f3.setdefault(r["tag"], []).append(r.get("ratio_opt"))
    return {"identity": {"n_pairs": n_pairs, "mismatches": mism, "ok": n_pairs > 0 and not mism,
                         "rule": "A9 equals RR_RENEW in total cost and purchase count on every F1/F2 run"},
            "sublet_projected_runs_f1f2": len(proj),
            "sublet_runs_f1f2": sum(1 for r in rows if r["tag"] == "Sublet" and r.get("fam") in ("F1", "F2")),
            "h4_wording": "the deployed policy equals RR-renew on F1/F2" if not proj and rows else
            "the identity holds for A9; Sublet projects in the counted runs",
            "f3_ratio_opt": {t: {"mean": _mean(v), "max": max((x for x in v if x is not None), default=None),
                                 "n": len(v)} for t, v in f3.items()},
            "f3_aborts": {t: sum(1 for r in rows if r.get("fam") == "F3" and r["tag"] == t
                                 and (r.get("guard") or {}).get("aborted")) for t in ("Sublet", "BL1-G", "BL5-G")}}


def _week_tables(col, tags, weeks) -> tuple:
    cells = [num_key(c) for c in weeks]
    tr = {t: {c: _val(col["table"], t, "L-tr", c) for c in cells} for t in tags}
    return cells, tr, w0_table(col["table"], cells, tags)


def week_cells(col: dict) -> list:
    """The week cells of a part's grid (the table holds every expected run, null where missing), in week order."""
    return sorted({c for by_m in col["table"].values() for by_c in by_m.values() for c in by_c if c.isdigit()},
                  key=int)


def decide_p1(col: dict) -> dict:
    weeks = [int(c) for c in week_cells(col)]
    cells, tr, w0 = _week_tables(col, P1_TAGS, weeks)
    q = {}
    for r in col["rows"]:
        if r["kind"] == "q44" and r["status"] == "ok":
            q.setdefault(r["tag"], {}).setdefault(r["cell"], {})[r["mode"]] = r["r0"]

    def mean_of(t, d):
        v = [d[t][c] for c in cells]
        return None if any(x is None for x in v) or not v else float(np.mean(v))
    commit_in = {"A9": {"trace_mean": mean_of("A9", tr), "W0_mean": mean_of("A9", w0)},
                 "A9-noCommit": {"trace_mean": mean_of("A9-noCommit", tr), "W0_mean": mean_of("A9-noCommit", w0)}}
    cell_rows, cell_bad = [], []
    q_stress = [m for m in Q44_P1_MODES if m != "L-tr"]
    for cell in sorted(set((q.get("A9") or {})) | set((q.get("A9-noCommit") or {}))):
        a, n = (q.get("A9") or {}).get(cell, {}), (q.get("A9-noCommit") or {}).get(cell, {})
        wa = max((a.get(m) for m in q_stress), default=None) if all(a.get(m) is not None for m in q_stress) else None
        wn = max((n.get(m) for m in q_stress), default=None) if all(n.get(m) is not None for m in q_stress) else None
        d_tr = None if a.get("L-tr") is None or n.get("L-tr") is None else n["L-tr"] - a["L-tr"]
        d_w = None if wa is None or wn is None else wn - wa
        cell_rows.append({"cell": cell, "trace_diff": d_tr, "W0_diff": d_w})
        if d_tr is None or d_w is None or d_tr > 0.02 or d_w > 0.02:
            cell_bad.append(cell)
    ci = commit_in
    have = all(v is not None for d in ci.values() for v in d.values())
    drop = have and ci["A9-noCommit"]["trace_mean"] < ci["A9"]["trace_mean"] and \
        ci["A9-noCommit"]["W0_mean"] < ci["A9"]["W0_mean"] and not cell_bad and bool(cell_rows)
    # insurance (D9): A9 insured > 0 on an L-tr or trace cell of (i)-(iii) where A9-noIns costs less
    ins = []
    for r in col["rows"]:
        if r["tag"] == "A9" and r["status"] == "ok" and (r.get("a9") or {}).get("insured") and \
                (r["mode"] in ("L-tr", "shared")):
            o = next((x for x in col["rows"] if x["tag"] == "A9-noIns" and x["cell"] == r["cell"]
                      and x["mode"] == r["mode"] and x["seed"] == r["seed"] and x["status"] == "ok"), None)
            ins.append({"cell": r["cell"], "mode": r["mode"], "insured": r["a9"]["insured"], "r0": r["r0"],
                        "r0_noIns": None if o is None else o["r0"],
                        "noIns_cheaper": o is not None and o["r0"] < r["r0"]})
    insure_false = any(x["noIns_cheaper"] for x in ins)
    # GO is evaluated on A9 after both choices (§5): A9-noCommit's runs if the commitment rule is dropped, A9-noIns's
    # if insurance is switched off; with both, no P1 run has A9's new defaults and the rerun rule of §5 applies
    eff = ("A9-noCommit" if drop else "A9") if not insure_false else (None if drop else "A9-noIns")
    if eff is None:
        return {"weeks": cells, "trace": tr, "W0": w0, "q44": q,
                "commitment": {"inputs": commit_in, "cells_ii": cell_rows, "cells_failing": cell_bad, "drop": drop},
                "insurance": {"cells": ins, "insure_false": insure_false}, "effective_A9": None,
                "go": {"GO": None, "rerun_required": True,
                       "note": "commit and insure both change A9's defaults: P1 reruns A9 under them (§5's rerun "
                               "rule) before GO is evaluated"}}
    margins, below = [], 0
    for c in cells:
        a = tr[eff][c]
        base = [tr[t][c] for t in m5.H1_SET]
        if a is None or any(x is None for x in base):
            margins.append(None)
            continue
        m = min(base) - a
        margins.append(m)
        below += m > 0
    med = _median(margins)
    rule_a = below >= 5 and med is not None and med >= 0.03 and len(cells) == 6
    rule_b = len(cells) == 6 and all(w0[eff][c] is not None and w0[eff][c] <= 0.90 for c in cells)
    inv = [r for r in col["rows"] if r["tag"] == eff and r["status"] == "invariant_failure"]
    fb = None if (rule_a and rule_b) else ("F1" if rule_b else ("F2" if rule_a else "F3"))
    return {"weeks": cells, "trace": tr, "W0": w0, "q44": q,
            "commitment": {"inputs": commit_in, "cells_ii": cell_rows, "cells_failing": cell_bad, "drop": drop,
                           "rule": "dropped iff A9-noCommit's mean L-tr r0 and mean W0 over the six weeks are both "
                                   "lower than A9's and on no cell of (ii) its L-tr r0 or W0 exceeds A9's by > 0.02"},
            "insurance": {"cells": ins, "insure_false": insure_false},
            "effective_A9": eff,
            "go": {"a": {"weeks_below": below, "median_margin": med, "margins": margins, "pass": rule_a},
                   "b": {"pass": rule_b, "threshold": 0.90}, "c": {"invariant_failures": len(inv), "pass": not inv},
                   "GO": rule_a and rule_b and not inv, "fallback": fb}}


def _sibling(out_p: Path, part: str) -> Path:
    return Path(out_p).parent / part


def _rows_of(part: str, out_p: Path) -> list:
    js = [j for j in jobs_all() if j.params["part"] == part]
    return collect(_sibling(out_p, part), js)["rows"]


def _sibling_rows(part: str, out_p: Path) -> tuple:
    """(rows, source) of the sibling part `part` of the folder out_p: its collected rows (the run files under runs/,
    as _rows_of reads them; source 'runs'), else, when none is readable (the repository's copy of a pilot step keeps
    no runs/), the rows of its summary.json (brief's rows; source 'summary.json'), else ([], 'none')."""
    rows = _rows_of(part, out_p)
    if rows:
        return rows, "runs"
    s = mc.read_json(_sibling(out_p, part) / "summary.json")
    if isinstance(s, dict) and s.get("runs"):
        return list(s["runs"]), "summary.json"
    return [], "none"


P2_RULE = ("test (1) no abort with S on FB and T0g in bound form, no envelope violation; (2) price of the guard <= "
           "0.01 median, <= 0.03 max over the E7 runs of (i); (3) median <= 0.03 over the 29 one-day cells of (ii)")
P2_BOTH_FAIL = ("keep Algorithm 1's allowance (both fail): report its price, H6 without a threshold, run Sublet on "
                "seeds 111-112 and reapply P1's rule (a)")


def allowance_tests(name: str, col: dict, a9: dict) -> dict:
    """P2's test of an allowance (§5, P2's row) on the runs of tag `name` in a part's rows: the price of the guard
    (the run's r0 minus A9's, same (cell, mode), from `a9`) over the week runs and over the one-day runs (E3 shared,
    Q44); test (1) no run of the tag that projects (project not false) aborts while S follows FB at every slot and
    T0g stays in bound form, and no envelope violation; (2) median <= 0.01 and maximum <= 0.03 over the week runs;
    (3) median <= 0.03 over the one-day cells; and the guard summary of its runs."""
    rows = col["rows"]
    wk = {(r["cell"], r["mode"]): r["r0"] for r in rows if r["tag"] == name and r["kind"] == "week"
          and r["status"] == "ok"}
    day = {(r["cell"], r["mode"]): r["r0"] for r in rows if r["tag"] == name and r["kind"] in ("e3cell", "q44")
           and r["status"] == "ok"}
    pw = [{"cell": k, "price": None if a9.get(k) is None else v - a9[k]} for k, v in wk.items()]
    pd = [{"cell": k, "price": None if a9.get(k) is None else v - a9[k]} for k, v in day.items()]
    g = [x for x in col["guarded"] if x["tag"] == name]
    t1 = not [x for x in g if x.get("project") is not False and x.get("aborted") and x.get("s_fb_all")
              and x.get("t0g_bound_all")] and not [x for x in g if x.get("env_ok") is False]
    pr_w = [x["price"] for x in pw if x["price"] is not None]
    pr_d = [x["price"] for x in pd if x["price"] is not None]
    med_w, max_w, med_d = _median(pr_w), max(pr_w, default=None), _median(pr_d)
    t2 = med_w is not None and med_w <= 0.01 and max_w is not None and max_w <= 0.03
    t3 = med_d is not None and med_d <= 0.03
    return {"week_prices": pw, "day_prices": pd, "test1": t1, "median_week": med_w, "max_week": max_w,
            "test2": t2, "median_day": med_d, "n_day_cells": len(pr_d), "test3": t3,
            "passes": t1 and t2 and t3, "guard": guard_summary(g)}


def decide_p2(col: dict, out_p: Path) -> dict:
    p1 = _rows_of("p1", out_p)
    a9 = {(r["cell"], r["mode"]): r["r0"] for r in p1 if r["tag"] == "A9" and r["status"] == "ok" and r["seed"] == 0}
    out = {name: allowance_tests(name, col, a9) for name in ("Sublet", "Proto-alt")}
    a, b = out["Sublet"]["passes"], out["Proto-alt"]["passes"]
    decision = ("keep Algorithm 1's allowance" if a else
                ("build the alternative (algos/online_lb.py), Lemma G5' on the critical path, rerun P0-P2 on seeds "
                 "117-120" if b else P2_BOTH_FAIL))
    other = {t: guard_summary([x for x in col["guarded"] if x["tag"] == t])
             for t in ("Sublet-1way", "BL1-GP", "Proto-F5", "Proto-F5-alt")}
    return {"allowances": {"algorithm1": out["Sublet"], "alternative": out["Proto-alt"]}, "decision": decision,
            "others": other, "p1_rows_used": len(p1), "rule": P2_RULE}


# ---------------------------------------------------------------- summaries: P2's allowance branch (pilot log, P2)
def _rel_diff(a: Optional[float], b: Optional[float]) -> Optional[float]:
    """(a - b) / max(|a|, |b|), 0 when a == b, None when either is missing."""
    if a is None or b is None:
        return None
    return 0.0 if a == b else (float(a) - float(b)) / max(abs(float(a)), abs(float(b)))


def decide_p0r(col: dict, out_p: Path) -> dict:
    """P0's rerun for the built allowance (pilot log of §0, entry "P2, 2026-11-02", its reading of "P0-P2 rerun"; §5's
    P0 row): per cell of P2 on which Proto-alt ran (107-108 x {L-tr, L-eg}, the E3 cells shared, the Q44 cells under
    L-tr), |r0(Sublet) - r0(Proto-alt)| <= REPRO_TOL, Sublet (A8P at 'allowance' 'lb', algos/online_lb.py) from this
    part and Proto-alt from the sibling folder p2 (_sibling_rows); the largest difference; the cells without both
    runs; per cell also the allowance at the horizon, B_T(Sublet) (the guard's, guard_extras) against B_T(Proto-alt)
    (the prototype extract of p2's rows) and their relative difference (_rel_diff), within B_REL_TOL wherever both
    exist (OnlineLB equals the prototype's series bit for bit on these cells, tests/test_online_lb.py's needs_raw
    test); the allowance rules of Sublet's runs (B0_rule), each LB_RULE; the identity of A8P's project-false path
    (A8P-MS4) against IDENTITY_USD to IDENTITY_TOL. Passes iff every cell of the grid is within REPRO_TOL, none is
    missing, every Sublet run's rule is ms5b_common.LB_RULE, every B_T pair is within B_REL_TOL and the identity
    holds. The test suites that P0 also reruns are not seen by this summary."""
    p2, src = _sibling_rows("p2", out_p)
    proto = {(r["cell"], r["mode"]): r for r in p2 if r["tag"] == "Proto-alt" and r["status"] == "ok"
             and r["seed"] == 0 and r["r0"] is not None}
    sub = {(r["cell"], r["mode"]): r for r in col["rows"] if r["tag"] == "Sublet" and r["seed"] == 0}
    grid = sorted(((cell, m) for m, by_c in (col["table"].get("Sublet") or {}).items() for cell in by_c),
                  key=lambda k: (not k[0].isdigit(), k[0], k[1]))
    cells, missing = [], []
    for cell, m in grid:
        s = _val(col["table"], "Sublet", m, cell)
        xr = proto.get((cell, m))
        x = None if xr is None else xr["r0"]
        d = None if s is None or x is None else s - x
        b_s = None if s is None else ((sub.get((cell, m)) or {}).get("guard") or {}).get("B_T")
        b_x = None if xr is None else (xr.get("prototype") or {}).get("B_T")
        rb = _rel_diff(b_s, b_x)
        cells.append({"cell": cell, "mode": m, "r0": s, "r0_proto_alt": x, "diff": d,
                      "within": d is not None and abs(d) <= REPRO_TOL, "B_T": b_s, "B_T_proto_alt": b_x,
                      "B_rel_diff": rb, "B_within": None if rb is None else abs(rb) <= B_REL_TOL})
        if d is None:
            missing.append({"cell": cell, "mode": m, "sublet": s is not None, "proto_alt": x is not None})
    ident = next((r for r in col["rows"] if r["tag"] == "A8P-MS4" and r["status"] == "ok"), None)
    idv = None if ident is None else ident["ALG"] - IDENTITY_USD
    ident_ok = idv is not None and abs(idv) <= IDENTITY_TOL
    repro_ok = bool(cells) and not missing and all(x["within"] for x in cells)
    rules = sorted({str((r.get("guard") or {}).get("B0_rule")) for r in col["rows"] if r["tag"] == "Sublet"})
    rules_ok = rules == [m5.LB_RULE]
    b_ok = all(x["B_within"] is not False for x in cells)
    red = {"reduced_note": "a reduced run (2-hour horizon, the E3 window) compares only with a reduced p2, never with "
                           "P2's runs; its identity cannot hold (the stored run is a full week)"} \
        if design()["reduced"] else {}
    return {**red, "cells": cells, "n_cells": len(cells), "n_within": sum(1 for x in cells if x["within"]),
            "worst_abs_diff": max((abs(x["diff"]) for x in cells if x["diff"] is not None), default=None),
            "tolerance": REPRO_TOL, "missing_cells": missing, "reproduction_ok": repro_ok,
            "allowance": {"n_compared": sum(1 for x in cells if x["B_rel_diff"] is not None),
                          "n_within": sum(1 for x in cells if x["B_within"]),
                          "worst_abs_rel_diff": max((abs(x["B_rel_diff"]) for x in cells
                                                     if x["B_rel_diff"] is not None), default=None),
                          "tolerance_rel": B_REL_TOL, "ok": b_ok,
                          "note": "B_T(Sublet) (online_lb.py through the guard's B_curve) against B_T(Proto-alt) (the "
                                  "prototype's series) wherever both exist"},
            "sublet_B0_rules": rules, "rules_ok": rules_ok, "p2_rows": len(p2), "p2_source": src,
            "identity": {"ALG": None if ident is None else ident["ALG"], "stored_usd": IDENTITY_USD, "diff_usd": idv,
                         "tolerance_usd": IDENTITY_TOL, "ok": ident_ok,
                         "stored_job": "code/sim/out/e7/main/jobs/e7__main__pol__Sublet__mu__1__c__1.json"},
            "passes": repro_ok and ident_ok and rules_ok and b_ok,
            "note": "P0's rerun also needs every MS1-MS5, Q44 and new test passing (not seen by this summary)"}


def decide_p1r(col: dict) -> dict:
    """A record only (pilot log, P2's entry): A9's runs on seeds 117-120 under the six modes, the reference of p2r's
    price of the guard on the week cells; P1's decisions are not reapplied, since A9 does not change. Its L-tr r0 and
    W0 per week as information, and the runs that are missing or failed an invariant."""
    weeks = [int(c) for c in week_cells(col)]
    cells, tr, w0 = _week_tables(col, ("A9",), weeks)
    return {"weeks": cells, "trace": tr["A9"], "W0": w0["A9"],
            "n_runs": sum(1 for r in col["rows"] if r["tag"] == "A9"),
            "invariant_failures": sum(1 for r in col["rows"] if r["status"] == "invariant_failure"),
            "missing": len(col["missing"]),
            "note": "a record only: P1's decisions are not reapplied (A9 does not change); A9's runs on seeds 117-120 "
                    "are the reference of p2r's price of the guard on the week cells"}


P2R_BOTH_FAIL = P2_BOTH_FAIL + "; F5 is raised only if F5 passes the test where neither allowance does"
P2R_INCOMPLETE = "incomplete: rerun the missing runs (§4.5's rerun) or supply the reference folders"
P2R_OTHERS = ("Sublet-1way", "BL1-GP", "Proto-F5-alt")


def _one_day_r0(rows) -> dict:
    return {(r["cell"], r["mode"]): r["r0"] for r in rows if r["tag"] == "Sublet" and r["status"] == "ok"
            and r["seed"] == 0 and r["kind"] in ("e3cell", "q44")}


def decide_p2r(col: dict, out_p: Path) -> dict:
    """P2 rerun in full with Sublet at the built allowance (pilot log, P2's entry): P2's tests (1)-(3) for Sublet
    (allowance_tests, as decide_p2 computes them), with the price of the guard against A9 from the sibling p1r on the
    week cells (seeds 117-120) and from the sibling p1 on the one-day cells (P1 (ii)'s Q44 rows under L-tr and P1
    (iii)'s E3 shared rows). The inputs must be complete: every Sublet run of the part's grid (the 24 week runs of (i)
    and the 29 one-day cells of (ii); the reduced grid in reduced runs) ok, and A9's reference of every one of its
    cells; the missing Sublet runs (with the reason, collect's) and the missing references are listed. Decision:
    P2R_INCOMPLETE, never a branch of §5's table, while anything is missing; else 'keep the alternative allowance' if
    Sublet passes, otherwise P2's 'both fail' branch with §5's F5 clause (P2R_BOTH_FAIL; Algorithm 1's allowance
    already failed test (3) on the unchanged one-day cells at P2). Also the guard summaries of Sublet-1way, BL1-GP and
    Proto-F5-alt (F5 at the alternative allowance, for the F5 clause) with Proto-F5-alt's price of the guard on its
    week cells (information), the missing runs of those tags, and, when the sibling p0r has runs (or its
    summary.json), whether p0r's and this part's one-day Sublet runs have equal r0 (a determinism check, deciding
    nothing). Sublet-alg1 is not rerun (its test (3) failure on the unchanged one-day cells stands)."""
    p1r, src_r = _sibling_rows("p1r", out_p)
    p1, src_1 = _sibling_rows("p1", out_p)
    a9 = {(r["cell"], r["mode"]): r["r0"] for r in p1
          if r["tag"] == "A9" and r["status"] == "ok" and r["seed"] == 0
          and ((r["kind"] == "q44" and r["mode"] == "L-tr") or (r["kind"] == "e3cell" and r["mode"] == "shared"))}
    a9.update({(r["cell"], r["mode"]): r["r0"] for r in p1r
               if r["tag"] == "A9" and r["status"] == "ok" and r["seed"] == 0 and r["kind"] == "week"})
    res = allowance_tests("Sublet", col, a9)
    grid = sorted(((cell, m) for m, by_c in (col["table"].get("Sublet") or {}).items() for cell in by_c),
                  key=lambda k: (not k[0].isdigit(), k[0], k[1]))
    n_week = sum(1 for c, _m in grid if c.isdigit())
    miss_runs = [{k: x[k] for k in ("cell", "mode", "seed", "why")} for x in col["missing"] if x["tag"] == "Sublet"]
    miss_refs = [{"cell": c, "mode": m} for c, m in grid if a9.get((c, m)) is None]
    complete = n_week > 0 and len(grid) > n_week and not miss_runs and not miss_refs
    passes = res["passes"] if complete else None
    decision = P2R_INCOMPLETE if not complete else ("keep the alternative allowance" if passes else P2R_BOTH_FAIL)
    other = {t: guard_summary([x for x in col["guarded"] if x["tag"] == t]) for t in P2R_OTHERS}
    f5 = [{"cell": (r["cell"], r["mode"]), "price": None if a9.get((r["cell"], r["mode"])) is None
           else r["r0"] - a9[(r["cell"], r["mode"])]} for r in col["rows"]
          if r["tag"] == "Proto-F5-alt" and r["kind"] == "week" and r["status"] == "ok"]
    pf = [x["price"] for x in f5 if x["price"] is not None]
    p0r, src_0 = _sibling_rows("p0r", out_p)
    here, there = _one_day_r0(col["rows"]), _one_day_r0(p0r)
    both = sorted(set(here) & set(there))
    uneq = [{"cell": c, "mode": m, "r0": here[(c, m)], "r0_p0r": there[(c, m)]} for c, m in both
            if here[(c, m)] != there[(c, m)]]
    return {"allowance": {"rule": m5.LB_RULE, **res}, "complete": complete, "passes": passes, "decision": decision,
            "expected": {"week_runs": n_week, "day_cells": len(grid) - n_week},
            "missing_sublet_runs": miss_runs, "missing_references": miss_refs,
            "others": other,
            "missing_other_runs": {t: sum(1 for x in col["missing"] if x["tag"] == t) for t in P2R_OTHERS},
            "f5": {"week_prices": f5, "median_week": _median(pf), "max_week": max(pf, default=None), "n": len(pf),
                   "note": "Proto-F5-alt on 117-118 x {L-tr, L-eg} against p1r's A9: information for §5's F5 clause "
                           "(F5 is raised only if F5 passes the test where neither allowance does)"},
            "a9_rows": {"p1r": len(p1r), "p1": len(p1)}, "a9_sources": {"p1r": src_r, "p1": src_1},
            "a9_cells": {"week": sum(1 for k in a9 if k[0].isdigit()), "day": sum(1 for k in a9 if not k[0].isdigit())},
            "determinism_p0r": {"source": src_0, "n_compared": len(both), "n_equal": len(both) - len(uneq),
                                "unequal": uneq[:50], "equal": (not uneq) if both else None,
                                "note": "p0r and p2r run the same one-day Sublet runs (instance, parameters, seeds): "
                                        "their r0 must be equal; a check, it decides nothing"},
            "rule": P2_RULE,
            "not_rerun": "Sublet-alg1 (its test (3) failure on the unchanged one-day cells stands)",
            "note": "otherwise branch: Algorithm 1's allowance already failed test (3) on the unchanged one-day cells "
                    "at P2"}


FAM12 = ("F1", "F2")


def decide_p3r(col: dict, js: Optional[list] = None) -> dict:
    """P3's Sublet runs repeated at the built allowance (§5's P3 row: 'Sublet's runs are repeated if P2 changes the
    allowance'), on the part's jobs `js` (default: jobs(['p3r'])): the count of ok Sublet runs with a projected slot
    on F1/F2, which decides H4's wording by P3's rule (0 lets H4 state that the deployed policy equals RR-renew there;
    A9's identity with RR_RENEW is P3's, A9 unchanged), with the Sublet F1/F2 runs that are missing (collect's
    missing list: no run, a failed job or a run that is not ok; the family class from the job). The RR-renew wording
    is given only when none is missing, the count is 0 and the ok F1/F2 runs number the grid's; a projected run gives
    the A9 wording; otherwise the wording is undecided (None, with the reason). Sublet's ALG/OPT on F3 (mean, max, n)
    and its aborts (at slot 0, with S not on FB at every slot) over the ok runs, the others listed apart; its guard
    summary (aborts, aborts with S on FB and T0g in bound form, envelope violations, certificates held); and, as
    information, the runs whose LB'(T) (online_lb.LB_T) or B(T) exceeds the exact OPT to q44_study.CERT_TOL (Lemma
    G5'(b): B(T) <= LB'(T) <= OPT)."""
    from .q44_study import CERT_TOL
    js = jobs(["p3r"]) if js is None else list(js)
    fam_of = {j.id: (j.params.get("family") or {}).get("fam") for j in js}
    exp12 = sum(1 for j in js if fam_of[j.id] in FAM12 for x in expected_runs(j) if x[0] == "Sublet")
    miss12 = [x for x in col["missing"] if x["tag"] == "Sublet" and fam_of.get(x["job"]) in FAM12]
    miss3 = [x for x in col["missing"] if x["tag"] == "Sublet" and fam_of.get(x["job"]) == "F3"]
    rows = [r for r in col["rows"] if r["kind"] == "fam" and r["tag"] == "Sublet"]
    f12 = [r for r in rows if r.get("fam") in FAM12 and r["status"] == "ok"]
    proj = [r for r in f12 if (r.get("guard") or {}).get("projected_slots")]
    complete = not miss12 and exp12 > 0 and len(f12) == exp12
    if proj:
        wording, why = "the identity holds for A9; Sublet projects in the counted runs", None
    elif complete:
        wording, why = "the deployed policy equals RR-renew on F1/F2", None
    else:
        wording = None
        why = (f"undecided: {len(miss12)} of {exp12} Sublet F1/F2 runs missing ({len(f12)} ok); rerun them (§4.5's "
               f"rerun) before H4's wording is set")
    f3 = [r for r in rows if r.get("fam") == "F3" and r["status"] == "ok"]
    f3_bad = [{k: r.get(k) for k in ("inst", "mode", "seed", "status")} for r in rows
              if r.get("fam") == "F3" and r["status"] != "ok"]
    v = [r.get("ratio_opt") for r in f3 if r.get("ratio_opt") is not None]
    ab3 = [r for r in f3 if (r.get("guard") or {}).get("aborted")]
    gs = guard_summary([x for x in col["guarded"] if x["tag"] == "Sublet"])

    def vs_opt(get, name):
        xs = [(r, get(r.get("guard") or {})) for r in rows if r.get("opt") is not None]
        xs = [(r, b) for r, b in xs if b is not None]
        over = [{k: r.get(k) for k in ("inst", "mode", "seed", "fam", "opt")} | {name: b} for r, b in xs
                if b > r["opt"] * (1 + CERT_TOL) + CERT_TOL]
        return {"n_checked": len(xs), "n_over": len(over), "over": over[:50],
                "max_ratio": max((b / r["opt"] for r, b in xs if r["opt"] > 0), default=None)}
    return {"sublet_projected_runs_f1f2": len(proj), "sublet_runs_f1f2": len(f12), "sublet_runs_f1f2_expected": exp12,
            "missing_runs_f1f2": len(miss12),
            "missing_f1f2": [{k: x[k] for k in ("job", "cell", "seed", "why")} for x in miss12][:50],
            "projected_runs_f1f2": [{k: r.get(k) for k in ("inst", "mode", "seed", "fam")}
                                    | {"projected_slots": r["guard"]["projected_slots"]} for r in proj][:50],
            "h4_wording": wording, **({"h4_undecided": why} if why else {}),
            "f3_ratio_opt": {"mean": _mean(v), "max": max(v, default=None), "n": len(f3)},
            "f3_aborts": len(ab3), "f3_aborts_t_a_0": sum(1 for r in ab3 if r["guard"].get("t_a") == 0),
            "f3_aborts_s_not_fb": sum(1 for r in ab3 if r["guard"].get("s_fb_all") is False),
            "f3_not_ok": f3_bad, "missing_runs_f3": len(miss3),
            "guard": {k: gs[k] for k in ("n_runs", "held", "aborts", "n_aborts_s_fb_bound_form",
                                         "n_envelope_violations", "runs_projected", "projected_slots", "K0")},
            "lb_vs_opt": {**vs_opt(lambda g: (g.get("online_lb") or {}).get("LB_T"), "LB_T"),
                          "note": "LB'(T) <= OPT (Lemma G5'(b), PROVEN, audited), to "
                                  "q44_study.CERT_TOL; information, no rule"},
            "allowance_vs_opt": {**vs_opt(lambda g: g.get("B_T"), "B_T"),
                                 "note": "B(T) = min{W_k, LB'}(T) <= LB'(T) <= OPT (Lemma G5'(b), PROVEN, "
                                         "audited), to q44_study.CERT_TOL; information, no rule"},
            "rule": "P3's: the count of Sublet runs with a projected slot on F1/F2 decides H4's wording (0: the "
                    "deployed policy equals RR-renew there), given only when no Sublet F1/F2 run is missing; the F3 "
                    "numbers fix the family wording, no criterion",
            "note": "A9's identity with RR_RENEW on F1/F2 is P3's (A9 unchanged)"}


def _lb_of(f: dict, out_p: Path) -> Optional[float]:
    lp = (f.get("lps") or {}).get("shared")
    if not lp:
        return None
    rec = mc.read_json(out_p / lp["file"]) or {}
    return rec.get("objective") if rec.get("status") == 0 else None


SUBLET_SHARED_PART = "p2r"


def decide_p4(col: dict, out_p: Path) -> dict:
    """P4 (§5's P4 row). Sublet's shared E3 runs ('the shared runs of Sublet ... from P2') come from the sibling p2r
    (P2 rerun with Sublet at P2's allowance, pilot log, P2's entry), A9's from p1. A Sublet run is reused only if it
    was made at Sublet's current allowance (ms5b_common.run_allowance of the run equals sublet_v2_params' 'allowance');
    a run at another allowance counts as missing, and p2's runs at Algorithm 1's allowance are never read, so the
    shared and siloed rows of H5 never mix two allowances. Records the source (sublet_shared_from: the part, or 'none'
    when no run qualifies), the allowance, the runs excluded for their allowance and the cells without a reused run."""
    lbs, hashes = {}, {}
    for f in col["files"].values():
        if f.get("kind") == "e3cell":
            key = f"b{f['b']}:c{f['c']}"
            lbs[key], hashes[key] = _lb_of(f, out_p), f["instances"]["shared"]
    p1 = collect(_sibling(out_p, "p1"), [j for j in jobs_all() if j.params["part"] == "p1"])
    p2 = collect(_sibling(out_p, SUBLET_SHARED_PART),
                 [j for j in jobs_all() if j.params["part"] == SUBLET_SHARED_PART])
    want = m5.sublet_v2_params()["allowance"]
    shared_from, other_allowance = {}, []
    for src, t in ((p2, "Sublet"), (p1, "A9")):
        for jid, f in src["files"].items():
            if f.get("kind") != "e3cell":
                continue
            key = f"b{f['b']}:c{f['c']}"
            for e in f["runs"]:
                if e["tag"] == t and e["mode"] == "shared" and m5.run_ok(e):
                    if t == "Sublet" and m5.run_allowance(e) != want:
                        other_allowance.append({"cell": key, "allowance": m5.run_allowance(e)})
                        continue
                    shared_from[(t, key)] = {"ALG": e["ALG"], "hash_ok": f["instances"]["shared"] == hashes.get(key)}
    sub_keys = sorted(k for t, k in shared_from if t == "Sublet")
    ratio: dict = {}
    for r in col["rows"]:
        if r["kind"] == "e3cell" and r["status"] == "ok" and lbs.get(r["cell"]):
            ratio.setdefault(f"{r['tag']}:{r['mode']}", {})[r["cell"]] = r["ALG"] / lbs[r["cell"]]
    for (t, key), v in shared_from.items():
        if lbs.get(key) and v["hash_ok"]:
            ratio.setdefault(f"{t}:shared", {})[key] = v["ALG"] / lbs[key]
    bs = sorted({int(k.split(":")[0][1:]) for k in lbs})
    med = {name: {b: _median(v for k, v in (ratio.get(name) or {}).items() if k.startswith(f"b{b}:")) for b in bs}
           for name in ratio}
    sh, si = med.get("Sublet:shared", {}), med.get("Sublet:siloed", {})
    rule1 = bool(bs) and all(sh.get(b) is not None and si.get(b) is not None and sh[b] < si[b] for b in bs if b >= 2)
    ms4 = ratio.get("Sublet-MS4:shared") or {}
    cmp_ = [(k, v, ms4.get(k)) for k, v in (ratio.get("Sublet:shared") or {}).items()]
    n_le = sum(1 for _k, a, b in cmp_ if b is not None and a <= b)
    milp = []
    for jid, f in col["files"].items():
        if "status" in f and f.get("kind") == "milp":
            milp.append({"job": jid, "status": f.get("status"), "objective": f.get("objective"), "gap": f.get("gap"),
                         "solve_s": f.get("solve_s"), "size": f.get("size")})
    e5 = [r for r in col["rows"] if r["kind"] == "e5"]
    d9 = [{"cell": r["cell"], "mode": r["mode"], "insured": r["a9"]["insured"]} for r in e5
          if r["tag"] == "A9" and r["mode"] == "trace" and (r.get("a9") or {}).get("insured")]
    d9_cheaper = [x for x in d9 if any(o["tag"] == "A9-noIns" and o["cell"] == x["cell"] and o["mode"] == "trace"
                                       and o["r0"] is not None and o["r0"] < next(
                                           (r["r0"] for r in e5 if r["tag"] == "A9" and r["cell"] == x["cell"]
                                            and r["mode"] == "trace"), 1e300) for o in e5)]
    return {"lb_shared_lp": lbs, "ratios": ratio, "medians_by_b": med,
            "h5": {"shared_below_siloed_every_b_ge_2": rule1, "sublet_le_ms4_cells": n_le, "n_cells": len(cmp_),
                   "status": "primary" if rule1 and n_le >= 20 else "secondary",
                   "rule": "primary iff the median over seeds of Sublet's shared ALG/LB is below Sublet siloed's at "
                           "every b >= 2 and Sublet <= Sublet-MS4 in at least 20 of 24 cells"},
            "shared_runs_reused": {f"{t}:{k}": v for (t, k), v in shared_from.items()},
            "sublet_shared_from": SUBLET_SHARED_PART if sub_keys else "none", "sublet_shared_allowance": want,
            "sublet_shared_excluded": other_allowance,
            "sublet_shared_missing": sorted((k for k in lbs if k not in sub_keys), key=lambda k: (len(k), k)),
            "milp_sizing": milp,
            "e5_d9": {"insured_cells": d9, "noIns_cheaper": d9_cheaper, "changes_A9": bool(d9_cheaper)}}


def decide_p5(col: dict) -> dict:
    curves = {}
    for t in P5_TAGS:
        for c in week_cells(col):
            curves.setdefault(t, {})[c] = m5.intensity_curve(
                {p: _val(col["table"], t, m5.iid_mode(p), c) for p in m5.CURVE_P})
    lag = {t: {c: _val(col["table"], t, "L-tr", c) for c in week_cells(col)} for t in ("A9-lag", "BL1-lag")}
    return {"intensity_curves": curves, "lagged_demand": lag,
            "note": "wording only: which boundary results are pre-registered as secondary (no rule changes)"}


# ---------------------------------------------------------------- summaries: the confirmation parts (§4.4, §4.5)
def conf_tables(col: dict, part: str) -> dict:
    out: dict = {}
    cells = week_cells(col)
    tags = sorted({t for t, by_m in col["table"].items() if any(c.isdigit() for by_c in by_m.values() for c in by_c)})
    seeds = sorted({s for t in tags for by_c in col["table"][t].values() for c in by_c if c.isdigit()
                    for s in by_c[c]}, key=int)
    if cells:
        out["W0"] = {s: w0_table(col["table"], cells, tags, int(s)) for s in seeds}
        out["RC"] = m5.rc_rows([{**r, "config_seed": r["c"], "policy_seed": r["seed"]} for r in col["rows"]
                                if r["kind"] == "week"])
        if part in ("second", "main", "grid"):
            out["intensity_curves"] = {t: {c: m5.intensity_curve({p: _val(col["table"], t, m5.iid_mode(p), c)
                                                                  for p in m5.CURVE_P}) for c in cells}
                                       for t in tags}
    gap = {}
    for f in col["files"].values():
        if "objective" in f and str(f.get("job", "")).find("k=gap_lp") >= 0:
            gap[f"gap:c{f['c']}"] = f.get("objective") if f.get("status") == 0 else None
    if gap:
        out["gap_lp"] = gap
        out["gap_ratio"] = {f"{r['tag']}:{r['cell']}:{r['seed']}": (r["ALG"] / gap[r["cell"]] if gap.get(r["cell"])
                                                                     else None)
                            for r in col["rows"] if r["kind"] == "gap" and r["status"] == "ok"}
    return out


def e3_benchmarks(col: dict, out_p: Path) -> dict:
    """Per E3 cell: e3.cell_benchmarks (the shared LB by Q39's rule, the siloed sum and the bracket) and ALG/LB of
    every run against the shared LB (shared and siloed runs alike, as MS4's E3)."""
    out = {}
    for f in col["files"].values():
        if f.get("kind") != "e3cell":
            continue
        key = f"b{f['b']}:c{f['c']}"
        try:
            cb = e3.cell_benchmarks(out_p, f)
        except Exception as err:          # a cell without its LPs: recorded
            out[key] = {"error": f"{type(err).__name__}: {err}"}
            continue
        lb = cb["shared"].get("LB")
        out[key] = {"LB": lb, "LB_source": cb["shared"].get("LB_source"), "bracket": cb["bracket"],
                    "ratios": {f"{e['tag']}:{e['mode']}": (e["ALG"] / lb if lb else None) for e in f["runs"]
                               if m5.run_ok(e)}}
    return out


def fam_identity(col: dict) -> dict:
    """H4's inputs on the family runs: per (instance, mode, seed) A9 against RR_RENEW (total and purchases) and
    Sublet's projected slots, with the class (F1, F2, F3), the source (Q6 or fresh) and the mode."""
    rows = [r for r in col["rows"] if r["kind"] == "fam"]
    by = {(r["inst"], r["mode"], r["seed"], r["tag"]): r for r in rows}
    out = []
    for (inst, mode, seed, t), r in sorted(by.items(), key=lambda kv: str(kv[0])):
        if t != "A9" or r.get("fam") not in ("F1", "F2"):
            continue
        rr = next((by.get((inst, mode, s, "RR_RENEW")) for s in (seed,) if by.get((inst, mode, s, "RR_RENEW"))),
                  None) or next((x for k, x in by.items() if k[0] == inst and k[1] == mode and k[3] == "RR_RENEW"),
                                None)
        sub = [x for k, x in by.items() if k[0] == inst and k[1] == mode and k[3] == "Sublet"]
        out.append({"inst": inst, "mode": mode, "seed": seed, "src": r["src"], "fam": r["fam"],
                    "A9_total": r["total"], "A9_purchases": r["n_purchases"],
                    "RR_total": None if rr is None else rr["total"],
                    "RR_purchases": None if rr is None else rr["n_purchases"],
                    "equal": rr is not None and abs(r["total"] - rr["total"]) <= 1e-9 * max(1.0, abs(rr["total"]))
                    and r["n_purchases"] == rr["n_purchases"],
                    "sublet_projected_runs": sum(1 for x in sub if (x.get("guard") or {}).get("projected_slots"))})
    return {"pairs": out}


def summary_part(part: str, out_p: Path) -> dict:
    out_p = Path(out_p)
    js = [j for j in jobs_all() if j.params["part"] == part]
    col = collect(out_p, js)
    s = {"meta": _meta(part, js, col), "runs": col["rows"], "table": col["table"], "missing": col["missing"],
         "guarded": col["guarded"], "guard_summary": guard_summary(col["guarded"])}
    if part == "p0":
        s["decision"] = decide_p0(col)
    elif part == "p2a":
        s["decision"] = decide_p2a(col)
    elif part == "p3":
        s["decision"] = decide_p3(col)
    elif part == "p1":
        s["decision"] = decide_p1(col)
    elif part == "p2":
        s["decision"] = decide_p2(col, out_p)
    elif part == "p0r":
        s["decision"] = decide_p0r(col, out_p)
    elif part == "p1r":
        s["decision"] = decide_p1r(col)
    elif part == "p2r":
        s["decision"] = decide_p2r(col, out_p)
    elif part == "p3r":
        s["decision"] = decide_p3r(col, js)
    elif part == "p4":
        s["decision"] = decide_p4(col, out_p)
    elif part == "p5":
        s["decision"] = decide_p5(col)
    else:
        s.update(conf_tables(col, part))
        if part == "e3":
            s["e3"] = e3_benchmarks(col, out_p)
        if part == "fam":
            s["fam"] = fam_identity(col)
    mc.dump_json(e7._jsonish(s), out_p / "summary.json")
    mc.write_text(tables(s), out_p / "tables.md")
    return s


def tables(s: dict) -> str:
    """tables.md: the r0 of every run (tag, mode, cell, seed) and the part's decision or the missing runs."""
    m = s["meta"]
    lines = [f"# E7h part {m['part']} ({SPEC})", ""]
    if m.get("reduced"):
        lines += [f"Reduced run: {m.get('reduced_note')}", ""]
    rows = [[r["tag"], r["mode"], r["cell"], r["seed"], r.get("r0"), r["status"],
             (r.get("guard") or {}).get("projected_slots"), (r.get("guard") or {}).get("aborted")]
            for r in s["runs"]]
    lines += ["## Runs (r0 = cost over BL0a; families: ALG / OPT in ratio_opt of summary.json)", "",
              mc.md_table(["tag", "mode", "cell", "seed", "r0", "status", "projected", "aborted"], rows), ""]
    lines += ["## Missing runs (the missing-run rule, §4.5)", "",
              mc.md_table(["job", "tag", "mode", "cell", "seed", "why"],
                          [[x["job"], x["tag"], x["mode"], x["cell"], x["seed"], x["why"]] for x in s["missing"]]), ""]
    g = s["guard_summary"]
    lines += ["## Guarded runs", "", mc.md_table(["runs", "held", "envelope violations", "aborts",
                                                  "aborts with S on FB and T0g bound", "projected slots", "K0"],
                                                 [[g["n_runs"], g["held"], g["n_envelope_violations"], g["aborts"],
                                                   g["n_aborts_s_fb_bound_form"], g["projected_slots"], g["K0"]]]), ""]
    if "decision" in s:
        import json
        lines += ["## Decision inputs (§5)", "", "```", json.dumps(e7._jsonish(s["decision"]), indent=1)[:20000],
                  "```", ""]
    return "\n".join(lines) + "\n"


def summary(out) -> dict:
    """The summary of the part whose folder `out` is (its name), else of the one part of E7H_PART."""
    out = Path(out)
    part = out.name if out.name in PARTS else None
    if part is None:
        ps = parts()
        if len(ps) != 1:
            raise ValueError(f"--summary needs one part (E7H_PART) or a part's folder, got {out}")
        part = ps[0]
    return summary_part(part, out)


def manifest_extra(out) -> dict:
    """The job grid's design, the instance hashes the run files record (no instance is rebuilt) and the sha256 of the
    driver layer and of the prototype copies."""
    out = Path(out)
    part = out.name if out.name in PARTS else (parts()[0] if len(parts()) == 1 else None)
    js = [j for j in jobs_all() if part is None or j.params["part"] == part]
    hashes = {}
    for j in js:
        f = mc.read_json(output_path(out, j)) if output_path(out, j) is not None else None
        if isinstance(f, dict):
            h = f.get("instance_hash") or ((f.get("instances") or {}).get("shared")
                                           if isinstance((f.get("instances") or {}).get("shared"), str) else None)
            if h is None and isinstance(f.get("instances"), dict):
                h = {k: v.get("instance_hash") for k, v in f["instances"].items() if isinstance(v, dict)} or None
            hashes[j.id] = h
    files = [Path(__file__), Path(m5.__file__), m5.ANALYSIS] + sorted(PROTO_DIR.glob("*.py"))
    return {"part": part, "design": design(), "instance_hashes_from_outputs": hashes,
            "sources_sha256": {str(f.relative_to(paths.REPO)): (hashlib.sha256(f.read_bytes()).hexdigest()
                                                                 if f.is_file() else None) for f in files},
            "gate": None if part is None else _manifest_gate(part)}


def _manifest_gate(part: str) -> dict:
    """The gate as the manifest's process sees it (the --manifest process runs no job, so gate()'s cache is empty):
    the pilot record or the confirmation's checks, recorded and not enforced."""
    if is_pilot(part):
        ok, why, rec = m5.check_pilot()
        return {"kind": "pilot", "ok": ok, "reason": why, "pilot": rec}
    ok, why, rec = m5.check_confirmation()
    return {"kind": "confirmation", "ok": ok, "reason": why, "confirmation": rec}


# ---------------------------------------------------------------- the missing-run rule's rerun (§4.5)
def retry_list(out) -> list:
    """The pool jobs of the part to run once more (§4.5): a record not 'ok' (error, failed, oom_at_3G, a 'running'
    record left by a killed process), or 'ok' with a run that raised or that failed an invariant; each one's record
    is moved to retry/ (versioned) and its output to runs/retry/ first, and a job with a record in retry/ already is
    not listed again (one rerun).
    A job without a record was never launched and is left to the next run. Returns '<kind> <id>' lines."""
    out = Path(out)
    part = out.name if out.name in PARTS else parts()[0]
    js = [j for j in jobs_all() if j.params["part"] == part and j.kind == "pool"]
    lines = []
    for j in js:
        name = mc.job_file_name(j.id)
        old = out / "retry" / name
        if old.is_file():
            continue
        rec = mc.read_record(out, j.id)
        if rec is None:                     # never launched (E7H_ONLY, or a stopped script): not a failed run
            continue
        path = output_path(out, j)
        bad = rec.get("status") != "ok" or int(rec.get("n_errors") or 0) > 0
        if not bad and path is not None:
            f = mc.read_json(path) or {}
            bad = any(m5.run_status(e) == "invariant_failure" or e.get("status") == "invariant_failure"
                      for e in f.get("runs") or [])
        if not bad:
            continue
        old.parent.mkdir(parents=True, exist_ok=True)
        mc.dump_json({"job": j.id, "first_record": rec, "moved": mc._now(), "rule": "design/sublet_v2.md §4.5"}, old)
        if mc.record_path(out, j.id).is_file():
            mc.record_path(out, j.id).unlink()
        if path is not None and path.is_file():          # the run data stay unversioned (runs/, C40)
            keep = out / "runs" / "retry" / name
            keep.parent.mkdir(parents=True, exist_ok=True)
            path.rename(keep)
        lines.append(f"{j.kind} {j.id}")
    return lines


# ---------------------------------------------------------------- command line
def main(argv=None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if "--check-start" in args:
        rc = 0
        for part in parts():
            try:
                g = gate(part)
                print(f"[e7h] {part}: gate {g['kind']} {'ok' if g['ok'] else 'REFUSED (not enforced)'}: {g['reason']}")
            except RuntimeError as err:
                print(f"[e7h] {part}: REFUSED: {err}", file=sys.stderr)
                rc = 1
        return rc
    if "--retry-list" in args:
        ap = argparse.ArgumentParser(prog="python -m sublet.experiments.e7h --retry-list")
        ap.add_argument("--retry-list", action="store_true", required=True)
        ap.add_argument("--out", type=Path, required=True)
        a = ap.parse_args(args)
        for ln in retry_list(a.out):
            print(ln)
        return 0
    if "--out" not in args and any(x in args for x in ("--job", "--summary", "--manifest")):
        ps = parts()
        if len(ps) == 1:
            args += ["--out", str(part_dir(ps[0]))]
    return mc.main(EXP, jobs=jobs, run=run, summary=summary, script=__file__, manifest_extra=manifest_extra,
                   argv=args, description=__doc__)


if __name__ == "__main__":
    sys.exit(main())
