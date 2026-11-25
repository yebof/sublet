"""MS7 baselines and stress regimes: tags, lender modes, W0+, the tuning grid and the gate of e7r.py (design/ms7/plan.md
X4, X5, D6; change C54; design/ms7/feasibility/baselines.md §2 items 1-7, §3 B6).

What the driver e7r.py and its scripts e7r_select.py and e7r_analysis.py share, on top of the MS5b driver layer
(ms5b_common, imported unchanged, as are e7h.py, ms5b_common.TAGS and ms5b_analysis.py, so the frozen confirmation and
its sha256 stay intact):

  weeks (D6)                TUNE_WEEKS 113-116 and CONFIRM_WEEKS 121-124 (bench_e7f seeds reserved and unused by
                            MS5b, design/sublet_v2.md §4.1), EVAL_WEEKS 301-316 (the confirmation's weeks); every
                            bench_e7f seed rotates the same MaaS week, so tuning on 113-116 is in-sample,
                            the exposure Sublet's pilot had (feasibility §5 risk 8)
  lender modes (X5)         the six main modes (TUNE_MODES: L-tr and the five stress modes of W0), the confirmation's
                            seven (L-hon added), and NEW_MODES: low i.i.d. rates L-iid-0.0005, L-iid-0.002 (SpotLake's
                            14.71% and 45.61% of requests interrupted within 24 h, lee2022spotlake p. 9 Table 3, read as
                            a constant hazard per 5-min site-slot: p = 1 - (1 - f)^(1/288) = 5.5e-4 and 2.1e-3, rounded
                            down; a derived conversion, labeled so) and L-iid-0.0124 (3.571 reclaims per
                            lease-day, design/q44_practical_sublet.md §5.3), the regional correlated lender
                            L-co-reg-<p_sh> (schedule 'correlated', groups 'region': every lender of a region shocks
                            the others of its region, lender._correlated; p_sh 0.5 and 1) and the peak-aligned trace
                            lender L-pk (a constructed stress: peak_aligned_config); mode_lender_model, instance_key,
                            week_spec
  W0 and W0+                W0 is the largest r0 over the five stress modes (ms5b_common.w0_of, unchanged); W0+ the
                            largest over W0PLUS_MODES = the five and NEW_MODES (w0plus_of). The adaptive lender of
                            Theorem 2(a) (L-ad) is in W0+ by its identity with L-eg (ADAPTIVE_EQUIV): with per-site
                            coupling and tau >= 1 slot both announce each lease at exactly s + tau (lender.py), so its
                            r0 equals L-eg's (all 48 paired runs of the confirmation's parts main and second, max
                            difference 0; feasibility §1(e) item 4); it needs no run
  tags (X4)                 MS7_TAGS: the contract-only transplants '-c2' (BL1-c2 as A9 flags, BL1_AS_A9 being BL1's
                            identity, BL2-c2, BL3-0-c2, BL4-c2, BL5-cur-c2; feasibility §2 item 1), A9-P (registry A9P,
                            item 2), SpotHedge with spares as built (BL3-1, BL3-2) and per LLM with none while idle and
                            c2 contracts (BL3-1-llm, BL3-2-llm, item 4), the MPC baseline at its defaults and its
                            lookahead reference MPC-oracle (item 5); the existing tags of ms5b_common.TAGS by name
                            (EXISTING_EVAL_TAGS, run under EXISTING_MODES: the new modes and L-tr, the latter a
                            bit-for-bit check against the confirmation's part main)
  tuning (item 3)           GRIDS per family (BL1, BL2, BL3, BL4, BL5, MPC; at most 24 configurations of existing knobs
                            plus contract_rule each, the family's as-built setting first) as tags '<family>-g<NN>'; the
                            pre-stated rules T (minimum median r0 under L-tr over TUNE_WEEKS) and W (minimum median W0,
                            ties by the median r0 under L-tr) are code in e7r_select.py; the tuned tags '<family>-T' and
                            '<family>-W' resolve from its selection.json (tuned_tags)
  the gate (D6)             registration_record and check_registration: design/ms7/registration.md at HEAD, a clean tree
                            and the sha256 of e7r_select.py and e7r_analysis.py (on disk and at HEAD) equal to the lines
                            'e7r_select_sha256: <64 hex>' and 'e7r_analysis_sha256: <64 hex>' of the registration

Sublet gets no tuning (feasibility §2 item 3). Every option a tag sets defaults to the frozen behaviour and is hidden
from the records at its default (baselines/common.py QUIET_KEYS; tests/test_ms7_baselines.py). Status: the tags are
baselines and stress regimes (no ratio is claimed for any of them); L-pk is a constructed stress and the SpotLake rates
a derived conversion, each labeled so.

Importing this module loads the standard library, numpy, ms3_common, ms4_common and ms5b_common (which loads e7); the
drivers, the instance builder and the policies are imported inside the functions that need them.
"""
from __future__ import annotations

import copy
import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Optional

import numpy as np

from . import ms3_common as mc
from . import ms4_common as m4
from . import ms5b_common as m5

# ---------------------------------------------------------------- files and the gate (D6)
SPEC = "design/ms7/plan.md X4, X5 (C54); design/ms7/feasibility/baselines.md"
REGISTRATION = "design/ms7/registration.md"
EXP = "e7r"
HERE = Path(__file__).resolve().parent
SELECT_FILE = HERE / "e7r_select.py"
ANALYSIS_FILE = HERE / "e7r_analysis.py"
REGISTERED = {"e7r_select.py": ("code/sim/sublet/experiments/e7r_select.py",
                                re.compile(r"^e7r_select_sha256:\s*([0-9a-f]{64})\s*$", re.MULTILINE)),
              "e7r_analysis.py": ("code/sim/sublet/experiments/e7r_analysis.py",
                                  re.compile(r"^e7r_analysis_sha256:\s*([0-9a-f]{64})\s*$", re.MULTILINE))}

# ---------------------------------------------------------------- weeks and modes (D6, X5)
TUNE_WEEKS = (113, 114, 115, 116)
CONFIRM_WEEKS = (121, 122, 123, 124)
EVAL_WEEKS = m5.CONF_WEEKS                         # 301-316
REDUCED_WEEK = 101                                 # development cell of the reduced runs (as e7h's)
WEEK_MIN = m5.WEEK_MIN
IID_LOW = (0.0005, 0.002, 0.0124)
IID_LOW_MODES = tuple(m5.iid_mode(p) for p in IID_LOW)
CO_REG_P = (0.5, 1.0)
CO_REG_PREFIX = "L-co-reg-"
CO_REG_MODES = tuple(f"{CO_REG_PREFIX}{mc.num_key(p)}" for p in CO_REG_P)
PK_MODE = "L-pk"
NEW_MODES = IID_LOW_MODES + CO_REG_MODES + (PK_MODE,)
TUNE_MODES = m5.main_modes()                       # L-tr and the five stress modes
CONF_MODES = m5.conf_modes()                       # plus L-hon
EVAL_MODES = CONF_MODES + NEW_MODES
W0_MODES = m5.stress_modes()
W0PLUS_MODES = W0_MODES + NEW_MODES
ADAPTIVE_EQUIV = {"L-ad": "L-eg"}
ADAPTIVE_NOTE = ("L-ad (Theorem 2(a)'s adaptive lender) is in W0+ by its identity with L-eg: both announce each lease "
                 "at s + tau (per-site coupling, tau >= 1 slot), so r0(L-ad) = r0(L-eg); the 48 paired runs of the "
                 "confirmation's parts main and second differ by 0 (feasibility §1(e) item 4); no run")
MODE_NOTES = {
    "L-iid-0.0005": "iid_step, D_slots 1, p 0.0005: SpotLake 14.71% of requests interrupted within 24 h "
                    "(lee2022spotlake p. 9, Table 3) as a constant hazard per 5-min site-slot, 1 - 0.8529^(1/288) = "
                    "5.5e-4, rounded down (derived conversion)",
    "L-iid-0.002": "iid_step, D_slots 1, p 0.002: SpotLake 45.61% within 24 h, 1 - 0.5439^(1/288) = 2.1e-3, rounded "
                   "down (derived conversion)",
    "L-iid-0.0124": "iid_step, D_slots 1, p 0.0124: 3.571 reclaims per lease-day (a5b_exposure_thresholds.json; "
                    "design/q44_practical_sublet.md §5.3)",
    "L-co-reg-0.5": "correlated, p_sh 0.5, groups 'region' (lender._correlated)",
    "L-co-reg-1": "correlated, p_sh 1, groups 'region' (lender._correlated)",
    "L-pk": "trace lender with each lender's daily slack minimum moved to its region's borrower peak (constructed "
            "stress; peak_aligned_config)",
}


def _co_reg_p(mode: str) -> Optional[float]:
    if not mode.startswith(CO_REG_PREFIX):
        return None
    try:
        p = float(mode[len(CO_REG_PREFIX):])
    except ValueError:
        return None
    return p if 0.0 < p <= 1.0 and f"{CO_REG_PREFIX}{mc.num_key(p)}" == mode else None


def mode_lender_model(mode: str) -> dict:
    """The run spec's lender model of a mode: L-co-reg-<p> is {'schedule': 'correlated', 'params': {'p_sh': p, 'groups':
    'region'}}, L-pk the config's trace lender ({}; its instance is peak_aligned_config's), every other mode
    ms5b_common.mode_lender_model's (q44_study.MODES, L-hon, the iid_step grid, L-b999). ValueError if unknown."""
    p = _co_reg_p(mode)
    if p is not None:
        return {"schedule": "correlated", "params": {"p_sh": p, "groups": "region"}}
    if mode == PK_MODE:
        return {}
    return m5.mode_lender_model(mode)


def instance_key(mode: str) -> str:
    """The instance a mode runs on within one week: 'pk' (peak_aligned_config) for L-pk, 'b999' for L-b999, else
    'base'."""
    mode_lender_model(mode)
    if mode == PK_MODE:
        return "pk"
    return m5.instance_key(mode)


def week_spec(policy_id: str, params=None, *, mode: str = "L-tr", c: int = 1, horizon_min: int = WEEK_MIN, seeds=(0,),
              name: str = EXP) -> dict:
    """The validated run spec of one week run: ms5b_common.week_spec for its modes, else ms4_common.e7_spec (mu = 1,
    the config's trace lender with mode_lender_model on top) for L-co-reg-<p> and L-pk; config seed c, lender
    'config', policy `seeds`. The spec of an L-pk run names the base instance's config; the run uses the instance of
    peak_aligned_instance (its record carries the offsets and the hash)."""
    if mode in CO_REG_MODES or mode == PK_MODE or _co_reg_p(mode) is not None:
        return m4.e7_spec(policy_id, params, mu=m5.MU, horizon_min=int(horizon_min),
                          lender_model=mode_lender_model(mode), overrides={}, name=name,
                          seeds={"config": [int(c)], "lender": "config", "policy": [int(p) for p in seeds]})
    return m5.week_spec(policy_id, params, mode=mode, c=int(c), horizon_min=int(horizon_min), seeds=seeds, name=name)


# ---------------------------------------------------------------- the peak-aligned trace lender L-pk (X5)
SERIES_DAY = 1440 // 5                             # 5-min slots of the slack series per day (lender.SLACK_SLOT_MIN)


def _day_profile(x: np.ndarray, phase: np.ndarray) -> np.ndarray:
    """Mean of x per phase value in 0..SERIES_DAY-1 (NaN where a phase has no sample)."""
    s = np.bincount(phase, weights=x, minlength=SERIES_DAY)
    n = np.bincount(phase, minlength=SERIES_DAY)
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(n > 0, s / np.maximum(n, 1), np.nan)


def peak_aligned_config(inst) -> tuple[dict, dict]:
    """(config, record) of L-pk (feasibility §1(e) item 2, §2 item 6): a copy of the resolved inst.config (a rebuild
    from it reproduces the instance, feasibility §1(e)) in which every trace lender's offset is moved so that its daily
    slack minimum falls on its region's borrower peak, keeping the base offset's day. Borrower peak of region r: the
    5-min phase p_r (of the series day, counted from horizon minute 0: phase of slow slot t = (t Δs / 5) mod 288)
    with the largest mean over the horizon of the summed slot means of r's clients (ties: the lowest phase). Slack
    minimum of lender l: the phase m_l of its full series S_full (index mod 288) with the least mean slack (ties: the
    lowest). New offset: o' = 288 floor(o / 288) + ((m_l - p_r) mod 288), o the base offset modulo N = len(S_full);
    so at the horizon's peak phase the lender's series is at its minimum phase. The lender reads its series at index
    (offset + t Δs / 5) mod N (lender.py), so a window that runs past the series end keeps the phase only when N is a
    multiple of 288 (the MaaS week series); for another N (the spot series) o' moves back by the fewest whole days
    with o' + T Δs / 5 <= N (days_back; o' >= 0 kept), else o' mod N. A lender without a series, a site or a region
    with borrower demand keeps its offset. Only the reclaim timing is meant to change: the buffer curve and v_top do
    not depend on the offset, and peak_aligned_instance records whether the sites, their capacities, the prices and
    the references equal the base instance's. A constructed stress, labeled so."""
    cfg = copy.deepcopy(inst.config)
    g = inst.grid
    T, slow = g.T_slow, g.slow_min
    d = np.asarray(inst.clients.demand, dtype=np.float64).reshape(inst.n, T, g.phi).mean(axis=2)
    phase = ((np.arange(T, dtype=np.int64) * slow) // 5) % SERIES_DAY
    regions = list(inst.clients.region)
    peaks = {}
    for r in sorted(set(regions)):
        tot = d[[i for i, x in enumerate(regions) if x == r]].sum(axis=0)
        prof = _day_profile(tot, phase)
        if not np.any(np.nan_to_num(prof) > 0):
            continue
        p = int(np.nanargmax(prof))
        mean = float(np.nanmean(prof))
        peaks[r] = {"phase": p, "peak_over_mean": float(prof[p] / mean) if mean > 0 else None}
    traces = {lt.lender: lt for lt in inst.lenders}
    span = T * slow // 5                           # series steps read over the horizon (lender.SLACK_SLOT_MIN)
    rows = []
    for e in cfg.get("lenders") or []:
        if e.get("kind") != "trace":
            continue
        lt = traces.get(e["id"])
        row = {"lender": e["id"], "region": e.get("region"), "offset_base": e.get("offset")}
        why = None
        if lt is None or lt.S_full is None:
            why = "no slack series in the instance"
        elif not any(s.lender == e["id"] for s in inst.sites):
            why = "no site in the instance"
        elif e.get("region") not in peaks:
            why = "no borrower demand in its region"
        if why is not None:
            row.update(offset=e.get("offset"), moved=False, why=why)
            rows.append(row)
            continue
        S = np.asarray(lt.S_full, dtype=np.float64)
        N = len(S)
        prof = _day_profile(S, np.arange(N, dtype=np.int64) % SERIES_DAY)
        m_l = int(np.nanargmin(prof))
        base = int(e["offset"]) % N
        p_r = peaks[e["region"]]["phase"]
        new = SERIES_DAY * (base // SERIES_DAY) + (m_l - p_r) % SERIES_DAY
        back = 0
        if N % SERIES_DAY and new + span > N:
            back = -(-(new + span - N) // SERIES_DAY)
            if new - SERIES_DAY * back < 0:
                back = 0
        new = (new - SERIES_DAY * back) % N
        e["offset"] = int(new)
        row.update(offset=int(new), moved=True, slack_min_phase=m_l, region_peak_phase=p_r, series_len=N,
                   days_back=int(back))
        rows.append(row)
    rec = {"rule": "L-pk: daily slack minimum on the region's borrower peak, base offset's day kept (constructed)",
           "region_peaks": peaks, "lenders": rows, "n_moved": sum(1 for x in rows if x["moved"])}
    return cfg, rec


def peak_aligned_instance(inst):
    """(instance, record) of L-pk: instance.build_instance(peak_aligned_config(inst)[0]) and its record, which adds
    whether the site ids, the site capacities, the price matrix and the BL0a references (ms4_common.references) equal
    the base instance's (`same_as_base`)."""
    from ..instance import build_instance
    cfg, rec = peak_aligned_config(inst)
    pk = build_instance(cfg)
    a, b = list(inst.sites), list(pk.sites)
    rec["same_as_base"] = {
        "site_ids": [s.id for s in a] == [s.id for s in b],
        "capacities": [s.capacity_gpus for s in a] == [s.capacity_gpus for s in b],
        "prices": np.shape(inst.price) == np.shape(pk.price) and bool(np.array_equal(inst.price, pk.price)),
        "references": m4.references(inst) == m4.references(pk)}
    return pk, rec


# ---------------------------------------------------------------- tags (X4)
@dataclass(frozen=True)
class Tag:
    """One MS7 tag: registry id, parameters (a dict; minimal: no knob at its default), family (the tuning family, or the
    group it is reported with), kind, role and information class."""
    id: str
    params: dict
    family: str
    kind: str
    role: str
    information: str = "online-I1"


# the knobs the grids vary, with the policies' defaults (tests/test_ms7_baselines.py pins them to the classes' PARAMS)
KNOB_DEFAULTS = {
    "BL1": {"demand_stat": "max", "defer_release": True, "backoff_cap": None},
    "A9": {"target": "ratio", "release": "ski", "site_rule": "ski", "mbb": True, "commit": True, "insure": True,
           "contract_rule": "c2", "demand_stat": "max", "defer_release": True},
    "BL2": {"keep": "none", "contract_rule": "kstar", "defer_release": True},
    "BL3": {"n_extra": 2, "react_at": "notice", "zone": "lender", "contract_rule": "kstar", "extra_scope": "pool",
            "extra_when_idle": True},
    "BL4": {"window_min": 60, "contract_rule": "kstar"},
    "BL5": {"use_current_slot": False, "contract_rule": "kstar", "lookback": None, "refetch_after_reclaim": "rule",
            "tau_min": None},
    "MPC": {"window_min": 60, "replan_slots": 1, "forecast": "persistence", "contract_rule": "kstar", "ewma_alpha": 0.5,
            "rounding": "nearest", "holding": "stage"},
    "A9P": {"protected_only": True},
}


def _same(a, b) -> bool:
    return type(a) is type(b) and a == b


def minimal(policy_id: str, params: Mapping) -> dict:
    """params without the knobs of KNOB_DEFAULTS[policy_id] that hold their default (so equal settings have equal
    parameter dicts across tags, the frozen confirmation's included)."""
    d = KNOB_DEFAULTS.get(policy_id, {})
    return {k: copy.deepcopy(v) for k, v in params.items() if not (k in d and _same(v, d[k]))}


# BL1 as A9 flags: reproduces BL1 exactly (feasibility §1(c); tests/test_ms7_baselines.py); BL1-c2 swaps k* for kbar
BL1_AS_A9 = {"target": "ceil", "release": "now", "site_rule": "static", "mbb": False, "commit": False, "insure": False,
             "contract_rule": "kstar"}
BL1_C2 = minimal("A9", {**BL1_AS_A9, "contract_rule": "c2"})
SPARES_LLM = {"extra_scope": "llm", "extra_when_idle": False, "contract_rule": "c2"}

MS7_TAGS = {t[0]: Tag(*t[1:]) for t in (
    # contract-only transplants (feasibility §2 item 1): each baseline with A9.3's base contract kbar only
    ("BL1-c2", "A9", BL1_C2, "BL1", "transplant-c2", "BL1's planning (A9 with BL1's flags) with kbar contracts"),
    ("BL2-c2", "BL2", {"contract_rule": "c2"}, "BL2", "transplant-c2", "BL2 with kbar contracts (siloed runner)"),
    ("BL3-0-c2", "BL3", {"n_extra": 0, "contract_rule": "c2"}, "BL3", "transplant-c2", "BL3-0 with kbar contracts"),
    ("BL4-c2", "BL4", {"contract_rule": "c2"}, "BL4", "transplant-c2", "BL4 with kbar in its contract sets"),
    ("BL5-cur-c2", "BL5", {"use_current_slot": True, "contract_rule": "c2"}, "BL5", "transplant-c2",
     "BL5-cur with kbar contracts (BL5N without make-before-break)"),
    # protected-only renter (item 2)
    ("A9-P", "A9P", {}, "A9P", "protected-only",
     "A9 with every client insured at its flagged site: no revocable lease"),
    # SpotHedge with spares (item 4): as built (BLD-14, spares per pool also while idle) and per LLM, none while idle
    ("BL3-1", "BL3", {"n_extra": 1}, "BL3", "spares", "BL3 with 1 spare per pool, as built (MS4 E5's BL3-1)"),
    ("BL3-2", "BL3", {}, "BL3", "spares", "BL3 with 2 spares per pool, as built (MS2 default)"),
    ("BL3-1-llm", "BL3", {"n_extra": 1, **SPARES_LLM}, "BL3", "spares",
     "BL3 with 1 spare per LLM, none while N_Tar = 0, kbar contracts (SkyServe's per-service N_Extra)"),
    ("BL3-2-llm", "BL3", {**SPARES_LLM}, "BL3", "spares",
     "BL3 with 2 spares per LLM, none while N_Tar = 0, kbar contracts"),
    # the MPC baseline (item 5) at its defaults and its lookahead reference
    ("MPC", "MPC", {}, "MPC", "mpc",
     "receding-horizon LP with per-stage holding, persistence forecast, W 60 min, replan every slot"),
    ("MPC-oracle", "MPC", {"forecast": "oracle"}, "MPC", "mpc-reference",
     "MPC with the realized demand of the window (lookahead reference only)", "lookahead-60min"),
)}
# the existing tags of ms5b_common.TAGS that e7r runs under EXISTING_MODES: NEW_MODES (their seven modes are in the
# confirmation's part main, whose runs the analysis reads) and L-tr once more, whose runs must equal main's bit for bit
# (e7r_analysis's identity check: the runs of the two commits are only combined if the frozen behaviour is unchanged)
EXISTING_EVAL_TAGS = ("Sublet", "A9", "BL1", "BL1-BO", "BL2", "BL3-0", "BL4", "BL5", "BL5-cur", "BL5-tau60", "BL5N",
                      "BL1N", "BL1-GP", "CR", "A9-kstar")
EXISTING_MODES = (m5.TRACE_MODE,) + NEW_MODES
EVAL_FIXED = ("BL1-c2", "BL2-c2", "BL3-0-c2", "BL4-c2", "BL5-cur-c2", "A9-P", "BL3-1", "BL3-2", "BL3-1-llm",
              "BL3-2-llm")                         # every EVAL_MODES
EVAL_REFERENCE = ("MPC-oracle",)                   # REFERENCE_MODES only (a lookahead reference for the trace cost)
REFERENCE_MODES = ("L-tr", "L-hon")
AS_BUILT_C2 = (("BL1", "BL1-c2"), ("BL2", "BL2-c2"), ("BL3-0", "BL3-0-c2"), ("BL4", "BL4-c2"),
               ("BL5-cur", "BL5-cur-c2"))

# ---------------------------------------------------------------- the tuning grid (item 3)
FAMILIES = ("BL1", "BL2", "BL3", "BL4", "BL5", "MPC")
FAMILY_DEFAULT = {"BL1": "BL1", "BL2": "BL2", "BL3": "BL3-0", "BL4": "BL4", "BL5": "BL5-cur", "MPC": "MPC"}
MAX_GRID = 24


def _grid_bl1() -> list:
    out = [("BL1", {"demand_stat": ds, "defer_release": dr, "backoff_cap": bo})
           for bo in (None, 288) for dr in (True, False) for ds in ("max", "mean")]
    out += [("A9", {**BL1_C2, "demand_stat": ds, "defer_release": dr})
            for dr in (True, False) for ds in ("max", "mean")]
    return out


def _grid_bl2() -> list:
    return [("BL2", {"keep": k, "contract_rule": cr, "defer_release": dr})
            for cr in ("kstar", "c2") for dr in (True, False) for k in ("none", "s0")]


def _grid_bl3() -> list:
    out = [("BL3", {"n_extra": 0, "contract_rule": cr, "zone": z, "react_at": ra})
           for cr in ("kstar", "c2") for z in ("lender", "group") for ra in ("notice", "death")]
    out += [("BL3", {"n_extra": n, "extra_scope": sc, "extra_when_idle": idle, "contract_rule": cr})
            for n in (1, 2) for sc, idle in (("pool", True), ("llm", False)) for cr in ("kstar", "c2")]
    return out


def _grid_bl4() -> list:
    return [("BL4", {"window_min": w, "contract_rule": cr}) for cr in ("kstar", "c2") for w in (60, 30, 120)]


def _grid_bl5() -> list:
    out = [("BL5", {"use_current_slot": cur, "contract_rule": cr, "lookback": lb, "refetch_after_reclaim": rf})
           for cr in ("kstar", "c2") for cur in (True, False) for lb in (None, 288) for rf in ("rule", "immediate")]
    out += [("BL5", {"use_current_slot": cur, "tau_min": 60}) for cur in (True, False)]
    return out


def _grid_mpc() -> list:
    return [("MPC", {"forecast": f, "replan_slots": r, "contract_rule": cr})
            for cr in ("kstar", "c2") for f in ("persistence", "ewma") for r in (1, 3)]


_GRID_FNS = {"BL1": _grid_bl1, "BL2": _grid_bl2, "BL3": _grid_bl3, "BL4": _grid_bl4, "BL5": _grid_bl5,
             "MPC": _grid_mpc}


def grid(family: str) -> dict:
    """{'<family>-g<NN>': (registry id, minimal parameters)} of a family, in grid order; g00 is the family's as-built
    setting (FAMILY_DEFAULT)."""
    if family not in _GRID_FNS:
        raise KeyError(f"unknown tuning family {family!r}; known {list(FAMILIES)}")
    rows = _GRID_FNS[family]()
    return {f"{family}-g{i:02d}": (pid, minimal(pid, p)) for i, (pid, p) in enumerate(rows)}


def grid_tags() -> dict:
    """Every grid configuration as a Tag (kind 'grid')."""
    out = {}
    for fam in FAMILIES:
        for name, (pid, p) in grid(fam).items():
            out[name] = Tag(pid, p, fam, "grid", f"tuning configuration {name} of {fam}")
    return out


def family_default(family: str) -> tuple[str, dict]:
    """(registry id, parameters) of a family's as-built setting: the MS5b tag of FAMILY_DEFAULT, or MS7's MPC."""
    name = FAMILY_DEFAULT[family]
    if name in MS7_TAGS:
        t = MS7_TAGS[name]
        return t.id, copy.deepcopy(t.params)
    t = m5.tag(name)
    return t.id, copy.deepcopy(dict(t.params))


def tuned_tags(selection: Optional[Mapping]) -> dict:
    """{'<family>-T' | '<family>-W': Tag} from e7r_select.py's selection (its 'tuned' block); {} without one."""
    out = {}
    for name, x in ((selection or {}).get("tuned") or {}).items():
        out[name] = Tag(x["policy_id"], dict(x["params"]), x["family"], "tuned",
                        f"{x['rule']} setting of {x['family']}: {x['config']} (e7r_select.py)")
    return out


def tag(name: str, selection: Optional[Mapping] = None) -> Tag:
    """The Tag of a name: MS7_TAGS, a grid configuration, a tuned setting (needs the selection) or an MS5b tag (its
    family 'ms5b', its parameters a dict or the name itself for the instance-dependent ones, resolved by
    tag_params)."""
    if name in MS7_TAGS:
        return MS7_TAGS[name]
    g = grid_tags()
    if name in g:
        return g[name]
    tt = tuned_tags(selection)
    if name in tt:
        return tt[name]
    t = m5.tag(name)
    return Tag(t.id, name if isinstance(t.params, str) else dict(t.params), "ms5b", t.kind, t.role, t.information)


def tag_params(name: str, inst=None, selection: Optional[Mapping] = None) -> dict:
    """The resolved parameters of a tag on the run's instance (m5.tag_params for the MS5b tags)."""
    t = tag(name, selection)
    if t.family == "ms5b":
        return m5.tag_params(name, inst)
    return copy.deepcopy(dict(t.params))


def tag_table(names: Iterable[str], selection: Optional[Mapping] = None) -> dict:
    """{tag: {policy_id, params (or their rule), family, kind, role, information}} for a summary's meta."""
    out = {}
    for n in names:
        t = tag(n, selection)
        par = m5.tag_params_text(n) if t.family == "ms5b" else copy.deepcopy(dict(t.params))
        out[n] = {"policy_id": t.id, "params": par, "family": t.family, "kind": t.kind, "role": t.role,
                  "information": t.information}
    return out


# ---------------------------------------------------------------- W0+ (X5)
def w0plus_of(r0_by_mode: Mapping[str, Optional[float]]) -> tuple[Optional[float], Optional[str], list]:
    """(W0+, its mode, the modes without an r0) of one week, policy and seed: the largest r0 over W0PLUS_MODES (L-ad
    through L-eg, ADAPTIVE_EQUIV); None while a mode is missing."""
    miss = [m for m in W0PLUS_MODES if r0_by_mode.get(m) is None]
    if miss:
        return None, None, miss
    m = max(W0PLUS_MODES, key=lambda k: (r0_by_mode[k], -W0PLUS_MODES.index(k)))
    return float(r0_by_mode[m]), m, []


# ---------------------------------------------------------------- estimates (seconds; feasibility §1(a), §4)
# per run of a full week: the confirmation's job medians over 7 modes (out/sublet_v2/main/jobs, feasibility §1(a); A9's
# contract table, once per job, taken out of the A9 family's), BL3 with spares from the feasibility probes, and MPC
# from this unit's timing probe on bench_e7f 113 with a 1-day horizon under L-tr and L-eg (holding 'stage', routing
# 'region'), times 7: about 55 s per day replanning every slot (one LP of about 0.17 s per slot), 18 s every 3 slots,
# the oracle forecast about 1.5 times that
EST_RUN_S = {"A8P": 222.0, "A8": 200.0, "A9": 28.0, "A9P": 28.0, "BL1": 33.0, "BL1-BO": 10.5, "BL2": 31.0,
             "BL3": 27.0, "BL3-spares": 85.0, "BL4": 29.0, "BL5": 15.0, "BL5N": 23.0, "A6": 50.0, "MPC": 390.0,
             "MPC-r3": 130.0}
EST_MPC_ORACLE = 1.5
EST_TABLE_S = 44.0                                 # A9's contract table, once per job of the A9 family
EST_JOB_S = 10.0


def est_run_s(t: Tag) -> float:
    """The estimated wall time of one full-week run of a tag."""
    p = t.params if isinstance(t.params, dict) else {}
    if t.id == "MPC":
        base = EST_RUN_S["MPC-r3" if int(p.get("replan_slots", 1)) >= 3 else "MPC"]
        return base * (EST_MPC_ORACLE if p.get("forecast") == "oracle" else 1.0)
    if t.id == "BL3" and int(p.get("n_extra", 2)) > 0:
        return EST_RUN_S["BL3-spares"]
    if t.id == "BL1" and p.get("backoff_cap") is not None:
        return EST_RUN_S["BL1-BO"]
    if t.id == "BL5" and p.get("mbb"):
        return EST_RUN_S["BL5N"]
    return EST_RUN_S.get(t.id, 30.0)


def a9_family(name: str, t: Tag) -> bool:
    """Whether a job of the tag builds A9's contract table: A9 and A9P, and the MS5b tags of the A9 family (A8P around
    A9; ms5b_common.Tag.a9_family)."""
    if t.family == "ms5b":
        return bool(m5.tag(name).a9_family)
    return t.id in ("A9", "A9P")


# ---------------------------------------------------------------- the gate (D6)
def registration_record() -> dict:
    """The gate's facts: HEAD, whether design/ms7/registration.md exists at HEAD, the sha256 of e7r_select.py and
    e7r_analysis.py that it records, their sha256 at HEAD and on disk, and the dirty paths (ms5b_common.dirty_paths)."""
    reg = m5.file_at("HEAD", REGISTRATION)
    text = None if reg is None else reg.decode("utf-8", "replace")
    files = {}
    for name, (rel, rx) in REGISTERED.items():
        mm = rx.search(text) if text else None
        disk = HERE / name
        files[name] = {"recorded": mm.group(1) if mm else None, "head": m5._sha(m5.file_at("HEAD", rel)),
                       "disk": hashlib.sha256(disk.read_bytes()).hexdigest() if disk.is_file() else None}
    return {"head": m5.head_commit(), "registration": REGISTRATION, "registration_at_head": reg is not None,
            "registration_sha256": m5._sha(reg), "files": files, "dirty_paths": m5.dirty_paths()}


def check_registration(rec: Optional[Mapping] = None) -> tuple[bool, str, dict]:
    """(ok, reason, record): an e7r part runs only if design/ms7/registration.md exists at HEAD, the working tree is
    clean and e7r_select.py and e7r_analysis.py have, on disk and at HEAD, the sha256 the registration records (D6)."""
    rec = dict(rec if rec is not None else registration_record())
    why = []
    if not rec.get("registration_at_head"):
        why.append(f"{REGISTRATION} does not exist at HEAD")
    if rec.get("dirty_paths") is None:
        why.append("git cannot tell whether the working tree is clean")
    elif rec["dirty_paths"]:
        why.append(f"the working tree is dirty ({len(rec['dirty_paths'])} paths, e.g. {rec['dirty_paths'][:3]})")
    for name, f in (rec.get("files") or {}).items():
        want = f.get("recorded")
        if rec.get("registration_at_head") and want is None:
            why.append(f"{REGISTRATION} records no line '{name[:-3]}_sha256: <64 hex>'")
        for k in ("disk", "head"):
            if want is not None and f.get(k) != want:
                why.append(f"{name} on {k} {str(f.get(k))[:12]} differs from the registration's {want[:12]}")
    if why:
        return False, "e7r does not start (design/ms7/plan.md D6): " + "; ".join(why), rec
    return True, "registration at HEAD, clean tree, sha256 of e7r_select.py and e7r_analysis.py as registered", rec


__all__ = ["SPEC", "REGISTRATION", "TUNE_WEEKS", "CONFIRM_WEEKS", "EVAL_WEEKS", "IID_LOW_MODES", "CO_REG_MODES",
           "PK_MODE", "NEW_MODES", "TUNE_MODES", "CONF_MODES", "EVAL_MODES", "W0_MODES", "W0PLUS_MODES",
           "ADAPTIVE_EQUIV", "MODE_NOTES", "mode_lender_model", "instance_key", "week_spec", "peak_aligned_config",
           "peak_aligned_instance", "Tag", "KNOB_DEFAULTS", "minimal", "BL1_AS_A9", "BL1_C2", "MS7_TAGS",
           "EXISTING_EVAL_TAGS", "EXISTING_MODES", "EVAL_FIXED", "EVAL_REFERENCE", "REFERENCE_MODES", "AS_BUILT_C2",
           "FAMILIES", "FAMILY_DEFAULT", "grid", "grid_tags", "family_default", "tuned_tags", "tag", "tag_params", "tag_table", "w0plus_of", "est_run_s",
           "a9_family", "registration_record", "check_registration"]
