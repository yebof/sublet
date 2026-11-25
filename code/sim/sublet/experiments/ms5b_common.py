"""Shared MS5b driver layer (design/sublet_v2.md §2.3, §2.5, §3, §4.3-§4.5, §5, §8.1; unit U35).

What the pilot and confirmation driver e7h.py and the analysis ms5b_analysis.py share, on top of the MS3 and MS4 driver
layers (ms3_common, ms4_common) and the frozen drivers e7, e3, e5 and q44_study, which are imported unchanged:

  Sublet's parameters (§2.5)     sublet_v2_params: {'inner': 'A9', 'project': True, 'allowance': 'lb', 'kappa': None}:
                                 P2's decision (pilot log of §0, entry "P2, 2026-11-02"): the alternative allowance
                                 B(t) = min{W_k(t), LB'(t)} of algos/online_lb.py (C3 §9, Lemma G5', Corollary G3';
                                 B0 unused), with guard.Guarded.PARAMS' other defaults; Sublet-1way, Sublet-lag and
                                 BL1-GP take the same allowance (their rules start from it), Sublet-alg1 keeps
                                 Algorithm 1's (B0 'auto', kappa 10) as a reference; allowance_fields, LB_RULE
  the tag table (§2.3, §3)       TAGS (every pilot and confirmation tag: registry id, parameters, kind, A9 family),
                                 tag_params, PROTO (the prototype runs of P2a and P2), E7_TAGS, H1_SET, H2B_SET
  lender modes (§4.4, §4.5)      the modes of q44_study.MODES, L-hon (no announcement, no refusal, no violation), the
                                 iid_step intensity grid and L-b999 (prices.buffer_quantile 'p99.9' under L-tr):
                                 mode_lender_model, mode_overrides, week_spec (on top of e7.week_spec)
  run entries                    week_entry and siloed_week_entry (e7.run_entry and e7.siloed_entry plus the mode, r0,
                                 the A8P record, the guard's envelope and projection, A9's report), guard_fields
  RC and the curve (§4.5)        rc_rows, intensity_curve, w0_of
  statistics (§4.5)              sign_test_p, bootstrap_median_ci, wilcoxon_signed_rank, paired_margins, the
                                 missing-run rule (run_status, LOSS)
  the gates (§4.3, §5)           pilot_record and check_pilot (the pilot anchor is an ancestor of HEAD),
                                 confirmation_record and check_confirmation (design/sublet_v2_prereg.md at HEAD, a
                                 clean tree, the analysis script's sha256), check_copy (the copy check of
                                 out/sublet_v2/ against the clean clone, as ms3_common.check_copy does for MS3-MS5;
                                 python -m sublet.experiments.ms5b_common --check-copy CLONE [--root] [--report])

RC (§4.5, D6, copied from the note): RC(w, p, M) = r0(w, p, M) - r0(w, p, L-hon), same week, policy and policy seed,
where L-hon is the lender model {"schedule": "iid_step", "params": {"D_slots": 1, "p": 0.0}}: no announcement, no
refusal for unavailability and no buffer violation (lender.REFUSE_SCHEDULES and VIOLATION_SCHEDULES hold only 'trace'
and 'correlated'), so every lease lives until the platform releases it or the horizon ends; capacities are unchanged.
It can be negative; it is reported as measured.

Statistics (§4.5): per-week paired differences Delta_w = r0(w, best) - r0(w, Sublet), best the per-week minimum over
the comparison set; a one-sided sign test (12 of 16 gives p = 2517/65536 = 0.0384); the median of Delta_w with a
week-bootstrap 95% percentile interval (10,000 resamples of the weeks, numpy.random.default_rng(20261031)); the
one-sided Wilcoxon signed-rank test (exact, zeros dropped, tied |Delta| at their mean rank). The weeks are not
independent samples (§4.5, "Dependence"): the tests are descriptive.

Missing runs (§4.5): a run that crashes, is killed for memory or time, or has an invariant failure is rerun once with
the same seeds and code (run_e7h.sh's retry pass); if it fails again, the week counts as a loss for Sublet in every
hypothesis that uses that run, whichever policy's run is missing, and the failure is reported. run_status gives a run's
status; a margin that a missing run decides is LOSS.

Status labels (copied from design/sublet_v2.md §2.5 and §2.6 after the P6 audit addendum, design/theory/audit_guard.md):
Theorem W(a)(b), G2 and G3(b) PROVEN for A8; for A8P through Remark R, PROVEN, audited (on core exports up to WD_TIE);
Lemma G5' and Corollary G3' (the allowance min{W_k, LB'}, G3(b)'s constant about 12.66) PROVEN, audited; Proposition
P PROVEN, audited ((d) under its three float hypotheses); A9's rules HEURISTIC; no competitive ratio is claimed for
A9 on the full model.

Importing this module loads the standard library, numpy, sublet.paths, ms3_common, ms4_common and e7; the drivers and
q44_study are imported inside the functions that need them.
"""
from __future__ import annotations

import copy
import hashlib
import math
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Optional, Sequence

import numpy as np

from .. import paths
from . import e7
from . import ms3_common as mc
from . import ms4_common as m4
from .ms3_common import num_key, put

# ---------------------------------------------------------------- files and the gates (§4.3, §5)
SPEC = "design/sublet_v2.md"
PREREG = "design/sublet_v2_prereg.md"
ANALYSIS = Path(__file__).resolve().parent / "ms5b_analysis.py"
ANALYSIS_REL = "code/sim/sublet/experiments/ms5b_analysis.py"
# the pilot anchor (§5): the first commit that versions design/sublet_v2.md with §5 and §6
PILOT_ANCHOR = "a6b242f7a6e9cb5629e49c2d1b10b8b781e5c655"
PILOT_DIR = "sublet_v2_pilot"          # <root>/out/sublet_v2_pilot/<part>/
CONF_DIR = "sublet_v2"                 # <root>/out/sublet_v2/<part>/
# the line of design/sublet_v2_prereg.md that records the analysis script's sha256 after its dry run (P6, §4.3)
PREREG_SHA_RE = re.compile(r"^analysis_sha256:\s*([0-9a-f]{64})\s*$", re.MULTILINE)
SECTION_RE = re.compile(r"^## (\d+)\. ", re.MULTILINE)
PILOT_SECTIONS = ("5", "6")            # a change of §5 or §6 after the anchor is a deviation (§5)

# ---------------------------------------------------------------- weeks and modes (§4.4, §4.5)
WEEK_MIN = m4.WEEK_MIN
MU = 1.0
CONF_WEEKS = tuple(range(301, 317))                # §4.4(a): bench_e7f config seeds 301-316
L_HON = {"schedule": "iid_step", "params": {"D_slots": 1, "p": 0.0}}
IID_CONF = (0.1, 0.34, 0.5, 0.8, 1.0)              # §4.4(b): with 0.05 and 0.2 of (a) and p = 0 (L-hon)
IID_P5 = (0.0, 0.05, 0.1, 0.2, 0.34, 0.5, 0.8, 1.0)     # §5 P5
CURVE_P = IID_P5                                   # the stress-intensity curve's grid (§4.5)
B999_MODE = "L-b999"                               # prices.buffer_quantile 'p99.9' under L-tr (§4.4(b), P5)
B999_OVERRIDES = {"prices.buffer_quantile": "p99.9"}
TRACE_MODE = "L-tr"
HON_MODE = "L-hon"
SECOND_MODES = ("L-vr", "L-rf", "L-ad")            # §4.4(b), P5 (q44_study.MODES)
BOOT_SEED = 20261031
BOOT_B = 10000
SIGN_P_12_OF_16 = 2517 / 65536                     # §4.5 (derived)
LOSS = None                                        # a margin decided by a missing run (the missing-run rule)


def stress_modes() -> tuple:
    """The five stress modes of W0 (ms4_common.stress_modes: L-eg, L-ss, L-iid-0.05, L-iid-0.2, L-co)."""
    return m4.stress_modes()


def main_modes() -> tuple:
    """L-tr and the five stress modes (P1, §4.4(a))."""
    return (TRACE_MODE,) + stress_modes()


def conf_modes() -> tuple:
    """The modes of §4.4(a): L-tr, the five stress modes and L-hon."""
    return main_modes() + (HON_MODE,)


def iid_mode(p: float) -> str:
    """The mode name of iid_step at p: L-hon at p = 0, else 'L-iid-<p>' (num_key; q44_study's names at 0.05 and
    0.2)."""
    return HON_MODE if float(p) == 0.0 else f"L-iid-{num_key(float(p))}"


def _iid_p(mode: str) -> Optional[float]:
    if mode == HON_MODE:
        return 0.0
    if mode.startswith("L-iid-"):
        try:
            return float(mode[len("L-iid-"):])
        except ValueError:
            return None
    return None


def mode_lender_model(mode: str) -> dict:
    """The run spec's lender model of a mode: ms4_common.mode_lender_model for q44_study.MODES (L-tr: {}), L_HON for
    L-hon, iid_step with D_slots 1 at the mode's p for the other 'L-iid-<p>' modes, and {} (the config's trace lender)
    for L-b999. ValueError for an unknown mode."""
    from . import q44_study as q44
    if mode in q44.MODES:
        return m4.mode_lender_model(mode)
    if mode == HON_MODE:
        return copy.deepcopy(L_HON)
    if mode == B999_MODE:
        return {}
    p = _iid_p(mode)
    if p is not None and 0.0 < p <= 1.0 and iid_mode(p) == mode:
        return {"schedule": "iid_step", "params": {"D_slots": 1, "p": p}}
    raise ValueError(f"unknown MS5b lender mode {mode!r}")


def mode_overrides(mode: str) -> dict:
    """The instance overrides of a mode: B999_OVERRIDES for L-b999, else {} (the lender mode does not change the
    instance)."""
    mode_lender_model(mode)
    return copy.deepcopy(B999_OVERRIDES) if mode == B999_MODE else {}


def instance_key(mode: str) -> str:
    """The instance a mode runs on within one week: 'b999' for L-b999, else 'base'."""
    return "b999" if mode == B999_MODE else "base"


def week_spec(policy_id: str, params=None, *, mode: str = TRACE_MODE, c: int = 1, horizon_min: int = WEEK_MIN,
              seeds=(0,), name: str = "e7h") -> dict:
    """The validated run spec of one week run: e7.week_spec at mu = 1 for a mode of q44_study.MODES, else
    ms4_common.e7_spec (the builder e7.week_spec calls) with mode_lender_model and mode_overrides (L-hon, the
    iid_step grid, L-b999); config seed c, lender 'config', policy `seeds`."""
    from . import q44_study as q44
    if mode in q44.MODES:
        return e7.week_spec(policy_id, params, mu=MU, mode=mode, horizon_min=int(horizon_min), c=int(c),
                            seeds=seeds, name=name)
    return m4.e7_spec(policy_id, params, mu=MU, horizon_min=int(horizon_min), lender_model=mode_lender_model(mode),
                      overrides=mode_overrides(mode), name=name,
                      seeds={"config": [int(c)], "lender": "config", "policy": [int(p) for p in seeds]})


# ---------------------------------------------------------------- Sublet and the tags (§2.3, §2.5, §3)
def sublet_v2_params(inst=None) -> dict:
    """Sublet's parameters (§2.5 and P2's decision, pilot log of §0, entry "P2, 2026-11-02"): {'inner': 'A9', 'project':
    True, 'allowance': 'lb', 'kappa': None}, whatever the instance. Algorithm 1's allowance (B0 'auto', kappa 10) failed
    P2's test (3) and the alternative's prototype passed all three, so by §5's decision table Sublet is A8P around A9 at
    the alternative allowance B(t) = min{W_k(t), LB'(t)} (algos/online_lb.py, on the corrected LB' of C3 §9's Lemma G5';
    kappa None, so B0 is unused; G3(b) through Corollary G3', PROVEN, audited), with Guarded.PARAMS' other defaults
    (gamma 1, safe 'fb+pd', test T0g with the reserve, wind-down 'auto'). The tag Sublet-alg1 keeps Algorithm 1's
    allowance as a reference."""
    return {"inner": "A9", "project": True, "allowance": "lb", "kappa": None}


# B0_rule of an A8P record at P2's allowance (allowance_fields)
LB_RULE = "lb: min{W_k(t), LB'(t)}, kappa None"


def allowance_fields(rec: dict, params: Optional[Mapping]) -> dict:
    """An A8 record's allowance fields at P2's allowance (params with 'allowance' 'lb', §2.5): ms4_common's
    allowance_record reads only B0 and kappa and would report B0 'auto' with kappa None, so B0_rule becomes LB_RULE,
    B0_usd and B0_report_usd None (B0 is unused; a8_record copies the report's 'B0' into B0_report_usd) and
    'allowance' 'lb' is added; B(T) is guard_extras' B_T (the guard's report). A record of any other parameters is
    returned unchanged (every run before P2's decision keeps its record)."""
    if (params or {}).get("allowance") == "lb":
        rec.update(B0_rule=LB_RULE, B0_usd=None, allowance="lb")
        if "B0_report_usd" in rec:
            rec["B0_report_usd"] = None
    return rec


def run_allowance(e: Optional[Mapping]) -> str:
    """The allowance rule of an A8P run entry (or brief row): its resolved parameters' 'allowance' (A8P keeps the key
    only at 'lb'), else its A8 record's (allowance_fields), else 'alg1' (Guarded.PARAMS' Algorithm 1 allowance, the
    only one of every run before P2's decision)."""
    e = e or {}
    return str((e.get("params") or {}).get("allowance") or (e.get("a8") or {}).get("allowance") or "alg1")


NBR_REPRO = {"site_rule": "noticed", "commit": False, "insure": False}
CR_PARAMS = {"contract_rule": "kstar", "mbb": False, "site_rule": "static", "commit": False, "insure": False}


def _sublet_1way(inst) -> dict:
    return {**sublet_v2_params(inst), "project": False}


def _bl1_gp(inst) -> dict:
    """BL1-GP (§3, D10): Sublet's guard around BL1, so a guarded comparison row takes Sublet's guard parameters, now
    P2's allowance (before P2's decision: {'inner': 'BL1'}, Algorithm 1's)."""
    return {**sublet_v2_params(inst), "inner": "BL1"}


def _sublet_ms4(inst) -> dict:
    return m4.sublet_params(inst, "BL5")


def _a8p_ms4(inst) -> dict:
    return {**m4.sublet_params(inst, "BL5"), "project": False}


def _sublet_lag(inst) -> dict:
    return {**sublet_v2_params(inst), "inner_params": {"demand_lag": 1}}


# instance-dependent parameter rules (a driver never types B0)
PARAM_RULES = {"sublet_v2": sublet_v2_params, "sublet_1way": _sublet_1way, "sublet_ms4": _sublet_ms4,
               "a8p_ms4": _a8p_ms4, "sublet_lag": _sublet_lag, "bl1_gp": _bl1_gp}
PARAM_RULE_TEXT = {"sublet_v2": "ms5b_common.sublet_v2_params(inst)",
                   "sublet_1way": "ms5b_common.sublet_v2_params(inst) with project false",
                   "sublet_ms4": "ms4_common.sublet_params(inst, 'BL5')",
                   "a8p_ms4": "ms4_common.sublet_params(inst, 'BL5') with project false",
                   "sublet_lag": "ms5b_common.sublet_v2_params(inst) with inner_params {'demand_lag': 1}",
                   "bl1_gp": "ms5b_common.sublet_v2_params(inst) with inner 'BL1'"}


@dataclass(frozen=True)
class Tag:
    """One tag of §2.3 and §3: registry id, parameters (a dict, or a key of PARAM_RULES for the instance-dependent
    ones), kind (headline, inner, guard, legacy, baseline, transplant, ablation, continuity, repro, lag, family),
    whether it belongs to the A9 family (A9, the A9-parameter tags of §2.3 and A8P around A9: one job per week and tag
    covers every lender mode, §5), the information model and its role."""
    id: str
    params: object
    kind: str
    a9_family: bool
    role: str
    information: str = "I1"


TAGS = {t[0]: Tag(*t[1:]) for t in (
    # §3 (the E7 tags, in its order)
    ("Sublet", "A8P", "sublet_v2", "headline", True,
     "headline (D1, D2, D3): A8P around A9 at P2's allowance min{W_k, LB'} (kappa None)"),
    ("A9", "A9", {}, "inner", True, "the inner policy alone; with Sublet, the price of the guard"),
    ("Sublet-1way", "A8P", "sublet_1way", "guard", True, "the one-way guard around A9 at the same allowance"),
    ("BL1-GP", "A8P", "bl1_gp", "guard", False, "the certificate without the revocation layer (D10)"),
    ("Sublet-MS4", "A8", "sublet_ms4", "legacy", False, "legacy row: A8 around BL5, B0 = 0.1 BL0a"),
    ("BL1", "BL1", {}, "baseline", False, "greedy, as built"),
    ("BL1-BO", "BL1", {"backoff_cap": 288}, "baseline", False, "generic site back-off"),
    ("BL2", "BL2", {}, "baseline", False, "per-borrower ski rental (siloed runner)"),
    ("BL3-0", "BL3", {"n_extra": 0}, "baseline", False, "SpotHedge-style, notice-reactive"),
    ("BL4", "BL4", {}, "baseline", False, "CoCaR-style"),
    ("BL5-cur", "BL5", {"use_current_slot": True}, "baseline", False, "main RetroRenting-style row (D7)"),
    ("BL5", "BL5", {}, "baseline", False, "lagged build, supplement"),
    ("BL5-tau60", "BL5", {"use_current_slot": True, "tau_min": 60}, "baseline", False, "rent long windows"),
    ("BL5N", "BL5", {"use_current_slot": True, "contract_rule": "c2", "mbb": True}, "transplant", False,
     "partial transplant of A9.3 and A9.4 onto BL5-cur"),
    ("BL1N", "A9", {"target": "ceil", "release": "now"}, "transplant", True,
     "BL1's planning with the whole revocation layer A9.3-A9.5"),
    ("CR", "A9", CR_PARAMS, "ablation", True, "planning half alone (A9.1, A9.2)"),
    ("A9-noMBB", "A9", {"mbb": False}, "ablation", True, "ablation of A9.4"),
    ("A9-noCommit", "A9", {"commit": False}, "ablation", True, "ablation of the commitment rule (P1's choice)"),
    ("A9-noIns", "A9", {"insure": False}, "ablation", True, "ablation of C2-T2 (families, D9)"),
    ("A9-kstar", "A9", {"contract_rule": "kstar"}, "ablation", True, "ablation of A9.3's contract rule"),
    ("A9-static", "A9", {"site_rule": "static"}, "ablation", True, "ablation of A9.5's marking"),
    ("A6", "A6", {}, "continuity", False, "continuity (the theory algorithm)"),
    # §2.3: P0's reproductions of the prototypes (never paper rows)
    ("NBR-repro", "A9", NBR_REPRO, "repro", True, "P0: reproduction of NBR (dev:skeptic/nbr.py)"),
    ("RCRb-repro", "A9", {"theta": "cr", "tie": "rank"}, "repro", True, "P0: reproduction of RCRb (dev:perf/rcr.py)"),
    ("CR-repro", "A9", {**CR_PARAMS, "insure": True, "theta": "cr", "tie": "rank"}, "repro", True,
     "P0: reproduction of perf's CR"),
    ("BL1N-repro", "A9", {"target": "ceil", "release": "now", "tie": "rank"}, "repro", True,
     "P0: reproduction of BL1Rb"),
    ("NBR-repro-G", "A8P", {"inner": "A9", "inner_params": NBR_REPRO, "safe": "fb"}, "repro", True,
     "P0: A8P around NBR-repro with safe 'fb' (dev:skeptic/out/guarded_summary.json)"),
    ("A8P-MS4", "A8P", "a8p_ms4", "repro", False,
     "P0: A8P with project false around BL5 at Sublet-MS4's parameters (the stored E7 run)"),
    # P2's allowance branch (pilot log, entry "P2, 2026-11-02"): never rerun, in no hypothesis set
    ("Sublet-alg1", "A8P", {"inner": "A9", "project": True}, "guard", True,
     "Sublet at Algorithm 1's allowance (P2's first allowance; reference)"),
    # §4.4(b), P5: lagged demand
    ("A9-lag", "A9", {"demand_lag": 1}, "lag", True, "A9 on slot t - 1's demand"),
    ("BL1-lag", "BL1", {"demand_lag": 1}, "lag", False, "BL1 on slot t - 1's demand"),
    ("Sublet-lag", "A8P", "sublet_lag", "lag", True, "Sublet with inner A9 on slot t - 1's demand"),
    # families (§4.4(d), P3; q44_study.POLICIES for RR_RENEW, MARKING, BL1-G and BL5-G)
    ("RR_RENEW", "RR_RENEW", {}, "family", False, "RR-renew (O1-B)"),
    ("MARKING", "MARKING", {}, "family", False, "MARKING (O1-D, I2)", "I2"),
    ("BL1-G", "A8", {"inner": "BL1"}, "family", False, "A8 around BL1 (E11)"),
    ("BL5-G", "A8", {"inner": "BL5"}, "family", False, "A8 around BL5 (E11)"),
)}
E7_TAGS = ("Sublet", "A9", "Sublet-1way", "BL1-GP", "Sublet-MS4", "BL1", "BL1-BO", "BL2", "BL3-0", "BL4", "BL5-cur",
           "BL5", "BL5-tau60", "BL5N", "BL1N", "CR", "A9-noMBB", "A9-noCommit", "A9-noIns", "A9-kstar", "A9-static",
           "A6")                                   # the 22 tags of §3
H1_SET = ("BL1", "BL1-BO", "BL2", "BL3-0", "BL4", "BL5", "BL5-cur")     # H1, H2 and P1's rule (a)
H2B_SET = ("BL5-tau60", "BL1-GP", "BL1N", "BL5N")                       # H2b
ABLATIONS = tuple(t for t, v in TAGS.items() if v.kind == "ablation")
GUARDED_IDS = ("A8", "A8P")
# the prototype runs of P2a and P2 (§5, §8.1): copies of dev:guard_allowance/projected.py and run_proj.py around the
# registered A9; rule as run_proj.allowance reads it ('alg1': Algorithm 1's; RULE_ALT: min{W_k(t), LB'(t)}, §2.5),
# reserve in the test (rho 1), projection on, F5 (route G over W^C, audit open item 4) as run_proj.main applies it
RULE_ALT = "mix:0:1:1:Wk"
PROTO = {"Proto-alt": {"rule": RULE_ALT, "f5": False, "role": "the alternative allowance min{W_k, LB'} (§2.5)"},
         "Proto-F5": {"rule": "alg1", "f5": True, "role": "F5 on at Algorithm 1's allowance (D4)"},
         "Proto-F5-alt": {"rule": RULE_ALT, "f5": True, "role": "F5 on at the alternative allowance (D4)"}}


def tag(name: str) -> Tag:
    if name not in TAGS:
        raise KeyError(f"unknown MS5b tag {name!r}; known {list(TAGS)}")
    return TAGS[name]


def tag_params(name: str, inst=None) -> dict:
    """The resolved parameters of a tag on the run's own instance `inst` (needed by the PARAM_RULES tags only)."""
    t = tag(name)
    if isinstance(t.params, str):
        if inst is None:
            raise ValueError(f"tag {name}: its parameters ({PARAM_RULE_TEXT[t.params]}) need the instance")
        return copy.deepcopy(PARAM_RULES[t.params](inst))
    return copy.deepcopy(dict(t.params))


def tag_params_text(name: str):
    """The parameters of a tag as the summaries list them: the dict, or the text of its rule."""
    t = tag(name)
    return PARAM_RULE_TEXT[t.params] if isinstance(t.params, str) else copy.deepcopy(dict(t.params))


def is_guarded(name: str) -> bool:
    return name in PROTO or tag(name).id in GUARDED_IDS


def seed_free(name: str) -> bool:
    """Whether a tag's run does not depend on the policy seed (§2.2: A9 at its defaults reads neither pi nor the
    policy's random streams): registry id A9 with the site rule 'ski' and the tie rule 'lru' (the 'static' and
    'noticed' site rules and the 'rank' tie read pi). Guarded tags draw (the safe expert's R) and are never
    seed-free."""
    t = tag(name)
    if t.id != "A9" or isinstance(t.params, str):
        return False
    p = dict(t.params)
    return p.get("site_rule", "ski") == "ski" and p.get("tie", "lru") == "lru"


def tag_table(names: Iterable[str]) -> dict:
    """{tag: {policy_id, params (or their rule), kind, a9_family, role, information}} for a summary's meta."""
    out = {}
    for n in names:
        if n in PROTO:
            out[n] = {"policy_id": "prototype", "params": dict(PROTO[n]), "kind": "prototype", "a9_family": True,
                      "role": PROTO[n]["role"], "information": "I1", "label": "prototype"}
            continue
        t = tag(n)
        out[n] = {"policy_id": t.id, "params": tag_params_text(n), "kind": t.kind, "a9_family": t.a9_family,
                  "role": t.role, "information": t.information}
    return out


# ---------------------------------------------------------------- run entries
def a9_fields(rep: Mapping) -> Optional[dict]:
    """A9's report counts (§8.1: marks, phase ends, mark expiries, notices, commitment fallbacks, contracts bought, the
    insured clients), from an A9 run's report or from the inner report of a guard around A9; None otherwise."""
    a9 = rep.get("a9") if isinstance(rep.get("a9"), Mapping) else ((rep.get("inner") or {}).get("a9"))
    if not isinstance(a9, Mapping):
        return None
    return {k: copy.deepcopy(v) for k, v in a9.items() if k not in ("theta", "site_c", "c2", "insured_flags")}


def envelope(res, rep: Mapping) -> dict:
    """The envelope of Theorem W's step (1) from the ledger (§5 P2 (1), H3): max over the executed E-mode slots t of
    ALG(t) + R(t) - (gamma C_S(t) + B(t)), ALG(t) the ledger's cumulative cost through slot t, R, C_S and B from the
    guard's report; ok iff every slot is within guard.GUARD_TOL max(1, |rhs|) + q44_study.CERT_TOL max(1, ALG(t)):
    the guard's own test plus the routing LP's tolerance between T0g's bound and the ledger (the certificate's
    tolerance; tests/test_guard_projection.py's oracle). Executed slots: the guard's slots without t_a."""
    from ..algos.guard import GUARD_TOL
    from .q44_study import CERT_TOL
    g = rep.get("guard") or {}
    slots = list(g.get("slots") or [])
    if g.get("t_a") is not None and slots:
        slots = slots[:-1]
    n = len(slots)
    if not n:
        return put({"n_slots": 0, "ok": True}, "max_excess_usd", None, "no executed E-mode slot")
    alg = np.cumsum(np.asarray(res.per_slot["total"], dtype=np.float64))
    rhs = np.asarray(g["rhs"][:n], dtype=np.float64)
    R = np.asarray(g["reserve"][:n], dtype=np.float64)
    a = alg[np.asarray(slots, dtype=np.int64)]
    ex = a + R - rhs
    tol = GUARD_TOL * np.maximum(1.0, np.abs(rhs)) + CERT_TOL * np.maximum(1.0, a)
    i = int(np.argmax(ex))
    return {"n_slots": n, "max_excess_usd": float(ex[i]), "max_excess_slot": int(slots[i]),
            "ok": bool(np.all(ex <= tol)), "n_violations": int(np.sum(ex > tol)),
            "tolerance": "GUARD_TOL max(1, |rhs|) + CERT_TOL max(1, ALG(t))"}


def guard_extras(res, rep: Mapping) -> dict:
    """The guard facts of an A8 or A8P run (§2.4, §5 P2, H3): the envelope, whether S followed FB at every slot (the
    safe expert's followed run-length list) and T0g stayed in bound form (no robust slot), S's switches, the
    projection counts and the executed candidates (A8P; run-length encoded, their number of runs), K0 uses, aborts,
    B(T) (B_T, the last entry of the safe expert's B_curve) and, only when the report has it (A8P at 'allowance'
    'lb'), its online_lb block {LB_T, Wk_T, B_T, n_groups}, so that a record at Algorithm 1's allowance is unchanged."""
    safe = rep.get("safe") or {}
    fol = safe.get("followed") or []
    t0g = rep.get("t0g") or {}
    robust = list(t0g.get("robust_slots") or [])
    proj = rep.get("projection")
    out = {"envelope": envelope(res, rep), "s_fb_all": bool(fol) and all(r[0] == "FB" for r in fol),
           "t0g_bound_all": not robust and not t0g.get("robust_all"), "robust_slots": len(robust),
           "switches": safe.get("switches"), "aborted": bool(rep.get("aborted")), "t_a": rep.get("t_a"),
           "project": rep.get("project"), "projection": copy.deepcopy(proj) if isinstance(proj, Mapping) else None,
           "projected_slots": int((proj or {}).get("slots", 0)) if isinstance(proj, Mapping) else 0,
           "candidates_runs": len(rep.get("candidates") or []), "dropped_fast": rep.get("dropped_fast"),
           "B_T": (safe.get("B_curve") or [None])[-1]}
    if isinstance(rep.get("online_lb"), Mapping):
        out["online_lb"] = dict(rep["online_lb"])
    return out


def guard_fields(res, inst, params: Mapping, information: str) -> dict:
    """The A8 record of an A8 or A8P run: e7._a8_fields (ms4_common.a8_record, which reads A8P's report as A8's:
    the allowance record, the certificate of q44_study.certificate and its case, info_class with
    registry.info_class('A8', params) and info_class_reported, t_a, aborted; the safe expert's costs), its allowance
    fields at P2's allowance (allowance_fields), plus guard_extras."""
    rec = allowance_fields(e7._a8_fields(res, inst, dict(params), information), params)
    rec.update(guard_extras(res, res.metrics.get("policy") or {}))
    return rec


def _add_fields(e: dict, res, inst, model, tag_name: str, mode: str, params: Mapping) -> dict:
    """The MS5b fields of a week, gap or one-day run entry: mode, r0 (the overflow cost over BL0a), the fallback and
    stranding totals, the run's status (run_status), the A8P record (A8's of e7.run_entry for A8), the guard's facts
    and A9's report."""
    pid = e["policy_id"]
    rep = res.metrics.get("policy") or {}
    acc = e.get("accountings") or {}
    e.update(tag=tag_name, mode=mode, r0=acc.get("overflow_over_bl0a"),
             fallback_usd=float(res.components.get("fallback", 0.0)),
             stranding_usd=float(res.components.get("stranding", 0.0)))
    if pid == "A8P":
        e["a8"] = guard_fields(res, inst, params, model.information)
        e["info_class_reported"] = e["a8"]["info_class_reported"]
    elif pid == "A8":
        e["a8"].update(guard_extras(res, rep))
    a9 = a9_fields(rep)
    if a9 is not None:
        e["a9"] = a9
    e["status"] = run_status(e)
    return e


def week_entry(res, inst, model, refs: dict, own, *, tag_name: str, spec: dict, pol, ps: int, c: int, mode: str,
               wall_s: float, imeta: Optional[dict] = None) -> dict:
    """One engine run's entry: e7.run_entry (ALG, both accountings, components, metrics, invariants, plan class P1,
    intensity, leases, the A8 record for A8) plus _add_fields."""
    e = e7.run_entry(res, inst, model, refs, own, tag=tag_name, spec=spec, pol=pol, ps=ps, c=c, wall_s=wall_s,
                     imeta=imeta)
    return _add_fields(e, res, inst, model, tag_name, mode, spec["policy"]["params"] or {})


def siloed_week_entry(d: dict, inst, model, refs: dict, own, *, tag_name: str, spec: dict, ps: int, c: int,
                      mode: str, wall_s: float) -> dict:
    """The entry of a siloed run (BL2): e7.siloed_entry plus the mode, r0, the fallback and stranding totals and the
    status."""
    e = e7.siloed_entry(d, inst, model, refs, own, tag="BL2", spec=spec, ps=ps, c=c, wall_s=wall_s)
    acc = e.get("accountings") or {}
    e.update(tag=tag_name, mode=mode, r0=acc.get("overflow_over_bl0a"),
             fallback_usd=float(d["components"].get("fallback", 0.0)),
             stranding_usd=float(d["components"].get("stranding", 0.0)))
    e["status"] = run_status(e)
    return e


def run_status(e: Optional[Mapping]) -> str:
    """A run's status for the missing-run rule (§4.5): 'missing' (no entry), 'invariant_failure' (the run or a
    sub-run has one), 'no_cost' (no r0), else 'ok'."""
    if not e:
        return "missing"
    if e.get("n_invariant_failures") or any(s.get("n_invariant_failures") for s in e.get("sub_runs") or []):
        return "invariant_failure"
    if e.get("r0") is None and e.get("ALG") is None:
        return "no_cost"
    return "ok"


def run_ok(e: Optional[Mapping]) -> bool:
    return run_status(e) == "ok"


# ---------------------------------------------------------------- RC, W0, the curve (§4.5)
def rc_rows(rows: Iterable[Mapping], modes: Optional[Sequence[str]] = None) -> dict:
    """RC(w, p, M) = r0(w, p, M) - r0(w, p, L-hon) (§4.5) for every (week c, tag, policy seed) with an ok L-hon run:
    {tag: {mode: {c: {seed: RC}}}} over the modes M other than L-hon (all, or `modes`); runs that are not ok are left
    out."""
    by: dict = {}
    for r in rows:
        if run_ok(r) and r.get("r0") is not None:
            by[(r["tag"], r["mode"], int(r["config_seed"]), int(r["policy_seed"]))] = float(r["r0"])
    out: dict = {}
    for (t, m, c, s), v in sorted(by.items()):
        if m == HON_MODE or (modes is not None and m not in modes):
            continue
        h = by.get((t, HON_MODE, c, s))
        if h is not None:
            out.setdefault(t, {}).setdefault(m, {}).setdefault(num_key(c), {})[num_key(s)] = v - h
    return out


def w0_of(r0_by_mode: Mapping[str, Optional[float]]) -> tuple[Optional[float], Optional[str], list]:
    """(W0, its mode, the stress modes without an ok r0) of one week, policy and seed: the largest r0 over the five
    stress modes; None while a mode is missing (the missing-run rule then decides)."""
    miss = [m for m in stress_modes() if r0_by_mode.get(m) is None]
    if miss:
        return None, None, miss
    m = max(stress_modes(), key=lambda k: (r0_by_mode[k], -stress_modes().index(k)))
    return float(r0_by_mode[m]), m, []


def intensity_curve(r0_by_p: Mapping[float, Optional[float]]) -> dict:
    """The stress-intensity curve of one policy and week (§4.5): the points (p, r0) in p order (p = 0 is L-hon) and
    the first p at which r0 > 1 (None if none; first_p_note when a point before it is missing)."""
    pts = sorted((float(p), None if v is None else float(v)) for p, v in r0_by_p.items())
    out = {"points": [[p, v] for p, v in pts]}
    first, gap = None, False
    for p, v in pts:
        if v is None:
            gap = True
            continue
        if v > 1.0:
            first = p
            break
    put(out, "first_p_above_1", first, "r0 <= 1 at every p measured")
    if gap:
        out["first_p_note"] = "a point of the grid has no run"
    return out


# ---------------------------------------------------------------- statistics (§4.5)
def sign_test_p(k: int, n: int) -> dict:
    """One-sided sign test: P(X >= k) for X ~ Binomial(n, 1/2), exactly (numerator over 2^n)."""
    k, n = int(k), int(n)
    if n < 0 or k < 0:
        raise ValueError(f"sign_test_p: k = {k}, n = {n}")
    num = sum(math.comb(n, i) for i in range(max(k, 0), n + 1))
    return {"k": k, "n": n, "numerator": num, "denominator": 2 ** n, "p": num / 2 ** n if n >= 0 else None}


def bootstrap_median_ci(x: Sequence[float], B: int = BOOT_B, seed: int = BOOT_SEED, level: float = 0.95) -> dict:
    """The median of x with the week-bootstrap percentile interval (§4.5): B resamples of the len(x) values with
    replacement drawn by numpy.random.default_rng(seed) (one integers((B, n)) draw), the median of each, and the
    (1 - level) / 2 and (1 + level) / 2 percentiles (numpy's linear rule)."""
    v = np.asarray(list(x), dtype=np.float64)
    out = {"n": int(v.size), "B": int(B), "seed": int(seed), "level": float(level)}
    if v.size == 0:
        out.update(median=None, median_note="no value", ci=[None, None])
        return out
    if not np.all(np.isfinite(v)):
        raise ValueError("bootstrap_median_ci: non-finite value")
    rng = np.random.default_rng(int(seed))
    idx = rng.integers(0, v.size, size=(int(B), v.size))
    med = np.median(v[idx], axis=1)
    lo, hi = np.percentile(med, [100 * (1 - level) / 2, 100 * (1 + level) / 2])
    out.update(median=float(np.median(v)), ci=[float(lo), float(hi)])
    return out


def wilcoxon_signed_rank(x: Sequence[float]) -> dict:
    """The one-sided Wilcoxon signed-rank test of median > 0 (§4.5): zeros dropped, |x| ranked with ties at their mean
    rank, W+ the sum of the ranks of the positive values, and the exact p = P(W+ >= observed) under independent random
    signs (a dynamic program over twice the ranks, which are integers)."""
    v = [float(a) for a in x]
    if any(not math.isfinite(a) for a in v):
        raise ValueError("wilcoxon_signed_rank: non-finite value")
    nz = [a for a in v if a != 0.0]
    n = len(nz)
    out = {"n": len(v), "n_nonzero": n, "zeros_dropped": len(v) - n}
    if n == 0:
        out.update(W_plus=None, p=None, p_note="every value is zero")
        return out
    order = sorted(range(n), key=lambda i: abs(nz[i]))
    ranks2 = [0] * n                                    # twice the mean ranks (integers)
    i = 0
    while i < n:
        j = i
        while j + 1 < n and abs(nz[order[j + 1]]) == abs(nz[order[i]]):
            j += 1
        for k in range(i, j + 1):
            ranks2[order[k]] = (i + 1) + (j + 1)        # 2 x mean of ranks i+1 .. j+1
        i = j + 1
    w2 = sum(r for r, a in zip(ranks2, nz) if a > 0)
    tot = sum(ranks2)
    counts = np.zeros(tot + 1, dtype=object)
    counts[0] = 1
    for r in ranks2:
        nxt = counts.copy()
        nxt[r:] = nxt[r:] + counts[:tot + 1 - r]
        counts = nxt
    num = int(sum(counts[w2:]))
    out.update(W_plus=w2 / 2.0, numerator=num, denominator=2 ** n, p=num / 2 ** n)
    return out


def paired_margins(sublet: Mapping, others: Mapping[str, Mapping], weeks: Sequence) -> dict:
    """Per week w: Delta_w = min over the comparison set of r0(w, tag) - r0(w, Sublet) (§4.5), 'best' the attaining
    tag, and LOSS (None, with the missing runs) when Sublet's run or any run of the set is missing (the missing-run
    rule). `sublet` {w: r0 or None}, `others` {tag: {w: r0 or None}}."""
    out = {}
    for w in weeks:
        s = sublet.get(w)
        vals = {t: d.get(w) for t, d in others.items()}
        miss = ([] if s is not None else ["Sublet"]) + [t for t, v in vals.items() if v is None]
        if miss:
            out[w] = {"delta": LOSS, "best": None, "missing": miss}
            continue
        best = min(vals, key=lambda t: (vals[t], list(vals).index(t)))
        out[w] = {"delta": float(vals[best]) - float(s), "best": best, "best_r0": float(vals[best]),
                  "sublet_r0": float(s), "missing": []}
    return out


# ---------------------------------------------------------------- git (read-only) and the gates (§4.3, §5)
def git(*args) -> Optional[str]:
    """Read-only git in this repository (--no-optional-locks, as figs/rebuild.py): stdout, or None on an error."""
    try:
        r = subprocess.run(["git", "--no-optional-locks", "-C", str(paths.REPO), *args], capture_output=True,
                           text=True, timeout=60)
        return r.stdout if r.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        return None


def head_commit() -> Optional[str]:
    h = git("rev-parse", "HEAD")
    return h.strip() if h else None


def is_ancestor(anchor: str, head: Optional[str] = None) -> Optional[bool]:
    """Whether `anchor` is an ancestor of `head` (default HEAD); None if git cannot tell (no repository)."""
    try:
        r = subprocess.run(["git", "--no-optional-locks", "-C", str(paths.REPO), "merge-base", "--is-ancestor",
                            anchor, head or "HEAD"], capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    return {0: True, 1: False}.get(r.returncode)


def file_at(rev: str, rel: str) -> Optional[bytes]:
    """The bytes of the repository file `rel` at commit `rev`, None if it does not exist there."""
    try:
        r = subprocess.run(["git", "--no-optional-locks", "-C", str(paths.REPO), "show", f"{rev}:{rel}"],
                           capture_output=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout if r.returncode == 0 else None


def dirty_paths() -> Optional[list]:
    """The paths that make the working tree dirty (§4.3): every tracked change, and every untracked path outside
    code/sim/out/ (the outputs of the runs themselves); None if git cannot tell."""
    s = git("status", "--porcelain", "--untracked-files=normal")
    if s is None:
        return None
    out = []
    for ln in s.splitlines():
        if not ln.strip():
            continue
        st, p = ln[:2], ln[3:].strip().strip('"')
        if st == "??" and p.startswith("code/sim/out/"):
            continue
        out.append(ln)
    return out


def _sha(b: Optional[bytes]) -> Optional[str]:
    return None if b is None else hashlib.sha256(b).hexdigest()


def sections(text: str, names: Iterable[str]) -> dict:
    """{name: the text of section '## <name>. ...' up to the next '## <n>. ' heading} of a design note."""
    hits = [(m.group(1), m.start()) for m in SECTION_RE.finditer(text)]
    out = {}
    for i, (n, s) in enumerate(hits):
        if n in names:
            out[n] = text[s: hits[i + 1][1] if i + 1 < len(hits) else len(text)]
    return out


def pilot_record() -> dict:
    """The pilot's provenance (§5), written into every pilot output: the anchor, HEAD, whether the anchor is an
    ancestor of HEAD, the sha256 of design/sublet_v2.md at HEAD and at the anchor, and whether §5 or §6 changed since
    the anchor (a deviation, §5)."""
    head = head_commit()
    spec_head, spec_anchor = file_at("HEAD", SPEC), file_at(PILOT_ANCHOR, SPEC)
    changed = None
    if spec_head is not None and spec_anchor is not None:
        a = sections(spec_anchor.decode("utf-8", "replace"), PILOT_SECTIONS)
        h = sections(spec_head.decode("utf-8", "replace"), PILOT_SECTIONS)
        changed = sorted(n for n in PILOT_SECTIONS if a.get(n) != h.get(n))
    return {"anchor": PILOT_ANCHOR, "head": head, "anchor_is_ancestor": is_ancestor(PILOT_ANCHOR, head),
            "spec": SPEC, "spec_sha256_head": _sha(spec_head), "spec_sha256_anchor": _sha(spec_anchor),
            "sections_changed_since_anchor": changed}


def check_pilot(rec: Optional[Mapping] = None) -> tuple[bool, str, dict]:
    """(ok, reason, record): a pilot step runs only if the pilot anchor is an ancestor of HEAD (§5)."""
    rec = dict(rec if rec is not None else pilot_record())
    if rec.get("anchor_is_ancestor") is True:
        return True, "the pilot anchor is an ancestor of HEAD", rec
    return False, (f"the pilot anchor {PILOT_ANCHOR[:8]} is not an ancestor of HEAD {str(rec.get('head'))[:8]} "
                   f"(anchor_is_ancestor {rec.get('anchor_is_ancestor')!r}): no pilot step runs (§5)"), rec


def analysis_sha256() -> Optional[str]:
    return _sha(ANALYSIS.read_bytes()) if ANALYSIS.is_file() else None


def prereg_sha256_recorded(text: Optional[str]) -> Optional[str]:
    """The analysis script's sha256 that the pre-registration records (its line 'analysis_sha256: <64 hex>')."""
    if not text:
        return None
    m = PREREG_SHA_RE.search(text)
    return m.group(1) if m else None


def confirmation_record() -> dict:
    """The confirmation's gate facts (§4.3): HEAD, whether design/sublet_v2_prereg.md exists at HEAD and the analysis
    sha256 it records, the sha256 of ms5b_analysis.py at HEAD and on disk, the dirty paths, and the pilot record."""
    pre = file_at("HEAD", PREREG)
    at_head = file_at("HEAD", ANALYSIS_REL)
    return {"head": head_commit(), "prereg": PREREG, "prereg_at_head": pre is not None,
            "prereg_sha256": _sha(pre),
            "analysis_sha256_prereg": prereg_sha256_recorded(None if pre is None else pre.decode("utf-8", "replace")),
            "analysis_sha256_head": _sha(at_head), "analysis_sha256_disk": analysis_sha256(),
            "dirty_paths": dirty_paths(), "pilot": pilot_record()}


def check_confirmation(rec: Optional[Mapping] = None) -> tuple[bool, str, dict]:
    """(ok, reason, record): a confirmation part runs only if design/sublet_v2_prereg.md exists at HEAD, the working
    tree is clean (dirty_paths empty) and the sha256 of experiments/ms5b_analysis.py (on disk and at HEAD) equals the
    one the pre-registration records (§4.3, §8.1)."""
    rec = dict(rec if rec is not None else confirmation_record())
    why = []
    if not rec.get("prereg_at_head"):
        why.append(f"{PREREG} does not exist at HEAD")
    if rec.get("dirty_paths") is None:
        why.append("git cannot tell whether the working tree is clean")
    elif rec["dirty_paths"]:
        why.append(f"the working tree is dirty ({len(rec['dirty_paths'])} paths, e.g. {rec['dirty_paths'][:3]})")
    want = rec.get("analysis_sha256_prereg")
    if rec.get("prereg_at_head") and want is None:
        why.append(f"{PREREG} records no line 'analysis_sha256: <64 hex>'")
    for k in ("analysis_sha256_disk", "analysis_sha256_head"):
        if want is not None and rec.get(k) != want:
            why.append(f"{k} {str(rec.get(k))[:12]} differs from the pre-registration's {want[:12]}")
    if why:
        return False, "the confirmation does not start (§4.3): " + "; ".join(why), rec
    return True, "pre-registration at HEAD, clean tree, analysis sha256 as recorded", rec


# ---------------------------------------------------------------- the copy check of out/sublet_v2 (§4.3)
CONF_PARTS = ("main", "seeds", "second", "e3", "fam", "grid")
COPY_RECORD = "ms3_copy_sublet_v2.json"
DRIVER_EXP = "e7h"


def check_copy(clone, root=None, record=None, parts: Sequence[str] = CONF_PARTS) -> dict:
    """The copy check of the confirmation (§4.3; the rules of ms3_common.check_copy, whose experiment folder must be
    named after the driver, which out/sublet_v2/ is not): <root>/out/sublet_v2/ against CLONE/code/sim/out/sublet_v2/
    (CLONE the clean clone's repository root): equal file lists and sha256 (runs/ included), no symbolic links, every
    JSON file readable and recording the clone's commit where it records a revision (a job record of
    --record-failure, and the e3 part's lb/ files of e3.run_milp, may record none), every part's manifest with the
    clone's commit, its summary.json an object with 'ok' records e7h:summary and e7h:manifest, no record still
    'running', and every part's run log run_e7h.log ending with '[run_e7h] done'. Writes <root>/out/
    ms3_copy_sublet_v2.json (or `record`) and returns it; a missing folder raises."""
    r = mc.ms3_root(root)
    copy_dir = r / "out" / CONF_DIR
    clone_repo = Path(clone).resolve()
    clone_out = clone_repo / "code" / "sim" / "out" / CONF_DIR
    for what, d in (("the clone's folder", clone_out), ("this repository's copy", copy_dir)):
        if not d.is_dir():
            raise FileNotFoundError(f"check_copy: {what} {d} is not a folder")
    if clone_out.samefile(copy_dir):
        raise ValueError(f"check_copy: the clone's folder {clone_out} is the copy itself")
    commit = mc.clone_commit(clone_repo)
    t = mc._compare_trees(copy_dir, clone_out)
    a = t["copy"]
    links = sorted({f"copy:{p}" for p, f in a.items() if f.is_symlink()}
                   | {f"clone:{p}" for p, f in t["clone"].items() if f.is_symlink()})
    differs, unreadable, unexpected, running = [], [], [], []
    small: dict = {}
    for rel in sorted(p for p in a if p.endswith(".json")):
        d, ok = mc._load_json_file(a[rel])
        if not ok:
            unreadable.append(rel)
            continue
        part, _, sub = rel.partition("/")
        if sub in ("manifest.json", "summary.json") or re.fullmatch(r"jobs/[^/]+\.json", sub):
            small[rel] = d
        revs = mc._recorded_revisions(d)
        if not revs:
            rec_ok = re.fullmatch(r"jobs/[^/]+\.json", sub) and isinstance(d, dict) and "rule" in d \
                and "git_revision" not in d
            if not (rec_ok or (part == "e3" and sub.startswith("lb/"))):
                unexpected.append(rel)
        elif revs != {commit}:
            differs.append(rel)
        if re.fullmatch(r"jobs/[^/]+\.json", sub) and isinstance(d, dict) and d.get("status") == "running":
            running.append(rel)
    per_part = {}
    for p in parts:
        man = small.get(f"{p}/manifest.json")
        rev = (man.get("meta") or {}).get("git_revision") if isinstance(man, dict) else None
        recs = {x.get("job"): x.get("status") for k, x in small.items() if k.startswith(f"{p}/jobs/")
                and isinstance(x, dict)}
        last = mc._last_line(copy_dir / p / f"run_{DRIVER_EXP}.log")
        per_part[p] = {"manifest_revision": rev, "summary_object": isinstance(small.get(f"{p}/summary.json"), dict),
                       "summary_record": recs.get(f"{DRIVER_EXP}:summary"),
                       "manifest_record": recs.get(f"{DRIVER_EXP}:manifest"), "log_last_line": last,
                       "log_done": last is not None and last.startswith(f"[run_{DRIVER_EXP}] done ")}
    checks = {"same_file_list": not t["only_copy"] and not t["only_clone"] and bool(a),
              "same_sha256": not t["mismatch"], "no_symlinks": not links, "json_readable": not unreadable,
              "revisions": not differs, "revisions_recorded": not unexpected,
              "manifest_revision": all(x["manifest_revision"] == commit for x in per_part.values()),
              "summary_ok": all(x["summary_object"] and x["summary_record"] == "ok" and x["manifest_record"] == "ok"
                                for x in per_part.values()),
              "no_running_records": not running, "run_log_done": all(x["log_done"] for x in per_part.values())}
    res = {"check": "copy", "exp": CONF_DIR, "driver": DRIVER_EXP, "pass": all(checks.values()), "checks": checks,
           "copy": str(copy_dir), "clone": str(clone_repo), "clone_out": str(clone_out), "clone_commit": commit,
           "parts": list(parts), "per_part": per_part, "tree_sha256": mc._tree_digest(t["digest_copy"]),
           "tree_sha256_versioned": mc._tree_digest({p: d for p, d in t["digest_copy"].items()
                                                     if "/runs/" not in f"/{p}"}),
           "n_files_copy": len(a), "n_files_clone": len(t["clone"]), "only_in_copy": t["only_copy"][:200],
           "only_in_clone": t["only_clone"][:200], "sha256_mismatch": t["mismatch"][:200], "symlinks": links[:200],
           "json_unreadable": unreadable[:200], "revision_differs": differs[:200],
           "no_revision_unexpected": unexpected[:200], "running_records": running[:200],
           "checked_by": {"module": "sublet.experiments.ms5b_common", "git_revision": mc.git_revision()},
           "time": mc._now()}
    mc.dump_json(res, Path(record) if record is not None else r / "out" / COPY_RECORD)
    return res


def _cli(argv=None) -> int:
    """python -m sublet.experiments.ms5b_common --check-copy CLONE [--root DIR] [--report FILE]: the copy check of
    out/sublet_v2/ against the clean clone (CLONE its repository root); exit 1 if it fails, 2 if it cannot run."""
    import argparse
    import sys
    ap = argparse.ArgumentParser(prog="python -m sublet.experiments.ms5b_common", description=_cli.__doc__)
    ap.add_argument("--check-copy", metavar="CLONE", required=True)
    ap.add_argument("--root", default=None)
    ap.add_argument("--report", type=Path, default=None)
    a = ap.parse_args(argv)
    try:
        res = check_copy(a.check_copy, a.root, a.report)
    except (OSError, ValueError) as err:
        print(f"[ms5b] copy check not run: {err}", file=sys.stderr)
        return 2
    failed = [k for k, v in res["checks"].items() if not v]
    print(f"[ms5b] copy check sublet_v2 {'pass' if res['pass'] else 'FAIL'}: {res['n_files_copy']} files, clone "
          f"commit {res['clone_commit']}" + (f"; failed: {', '.join(failed)}" if failed else ""), flush=True)
    return 0 if res["pass"] else 1


__all__ = ["SPEC", "PREREG", "PILOT_ANCHOR", "L_HON", "TAGS", "E7_TAGS", "H1_SET", "H2B_SET", "PROTO", "RULE_ALT",
           "LB_RULE", "sublet_v2_params", "allowance_fields", "run_allowance", "tag", "tag_params", "tag_table",
           "is_guarded", "seed_free", "mode_lender_model", "mode_overrides", "iid_mode", "week_spec", "week_entry",
           "siloed_week_entry", "guard_fields", "envelope", "run_status", "rc_rows", "w0_of", "intensity_curve",
           "sign_test_p", "bootstrap_median_ci", "wilcoxon_signed_rank", "paired_margins", "pilot_record",
           "check_pilot", "confirmation_record", "check_confirmation", "check_copy"]


if __name__ == "__main__":
    raise SystemExit(_cli())
