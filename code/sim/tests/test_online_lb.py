"""Tests of sublet/algos/online_lb.py (OnlineLB: the per-group online lower bound LB'(t) of Lemma G5', W_k(t) and the
allowance B(t) = min{W_k(t), LB'(t)}; design/theory/c3_c4_c5_general.md §9, Lemma G5', Corollary G3') and of A8P's
allowance option 'lb' (guard.ProjectedGuarded; design/sublet_v2.md §2.5, §5 P2).

Oracles.
(a) The prototype copies sublet/experiments/ms5b_proto/{lb.py, run_proj.py}: on fixture instances that meet the
    conditions (i)-(iii) of C3 §9's 'Relation to the prototype' (online_lb.conditions) OnlineLB's LB'(t), W_k(t) and
    B(t) equal lb.lb_series, run_proj.wk_series and run_proj.allowance('mix:0:1:1:Wk', ...) bit for bit, and its
    groups are lb.groups in the same order: configs/toy.json (5-min fast slots; also with 1-min fast slots, with
    kappa_infinite, and under the billing modes commit_tau and per_slot), configs/ms2_multi_small.json at 6 h (1-min
    fast slots; also with 5-min fast slots under commit_tau and per_slot, where every offered P_k is a multiple of 5),
    and random toy variants (fast slots of 1, 2 and 5 min, all three billing modes with every P_k a multiple of the
    fast slot, two LLMs, five to seven clients with random routing costs and so several groups per LLM, peaks of
    several replicas, kappa_infinite with every rent below q, every rent above q, whole-millisecond load times,
    including whole numbers of fast slots). Hand values: LB'(T) and W_k(T) of configs/toy.json; W_k's tolerance
    (three co-located clients with demands 1.1, 1.3 and 0.6 in one fast slot, whose sum is 3.0000000000000004: three
    replicas, as run_proj.wk_series counts them); conditions (i)-(iv) on the probes of (b), on a load time in the
    half-millisecond corner, where OnlineLB's entry cost is the corrected one and the prototype's is larger by r (lam_s
    / 60 - theta Delta_f) / 60, and on a single-fast-slot horizon with seven and eight co-located clients (iv).
(b) The two prototype defects of code/theory_checks/c3/check_g5p.py (probes 0 and 2; C3 §9, 'What does not hold',
    item 1), rebuilt here as check_g5p._probe_spec builds them: OnlineLB's LB'(T) equals the hand values 1.4 (P_k =
    7 min on 5-min fast slots) and 24.0 (kappa_infinite, rent 12 above q 10, two clients) and is at most the
    fast-grid MILP's incumbent (opt.milp.solve_opt as check_g5p.py solves it) under the schedules trace, eager and
    none, while the prototype's value (2.0, 40.0) exceeds the MILP optimum under none.
(c) The engine's ledger: ALG(t) >= LB'(t) at every slow slot, up to 1e-9 relative (Lemma G5'(c)), with LB' from an
    OnlineLB on the instance's demand, on runs of BL1, BL5, A9, A8P (allowance 'lb', project true and false) and the
    random inner policies of tests/test_guard.py (_RandomInner, _OwnListInner: Loads, Unloads, several LLMs per
    lease), alone and under A8P, on _rich_instance variants (both kappa_infinite values; stranding, load times and
    notices off the fast grid) and random toy variants, under the lender modes trace, eager, iid_step, adaptive and
    trace with on_unavailable 'refuse'.
(d) The fast-grid MILP: LB'(T) <= its incumbent (>= OPT_P1) under trace, eager and none on small instances (Lemma
    G5'(d)).
(e) Nondecreasing series; non-anticipation: LB'(t), W_k(t) and B(t) unchanged, bit for bit, when the demand after slot
    t is set to 0; PolicyError for a slot out of order or a demand of the wrong shape.
(f) A8P with allowance 'lb': PolicyError unless kappa is None, and for an unknown allowance; params() lists the option
    only at 'lb'. On engine runs (A9, BL1 and _RandomInner inside; project true and false; several lender modes)
    the guard's B(t) and the report's safe.B_curve equal an independent OnlineLB's B series bit for bit; the envelope
    ALG(t) + R(t) <= gamma C_S(t) + B(t) holds at every executed slot from the ledger (Theorem W, step (1); C_S
    rebuilt from the instance's all-fallback cost with S on FB); the report records allowance 'lb', kappa None and
    online_lb; ms4_common.certify and q44_study.certificate hold in Theorem W's cases. A8P(A9, 'lb') equals the
    prototype projected.ProjectedGuard at run_proj.allowance's series, built as e7h.proto_run builds it, ledger and
    lease records bit for bit, and A8P(A9, 'lb') with project false equals the prototype with project false (A8 at
    the same series) likewise. At Algorithm 1's allowance A8P's runs, with the option omitted or 'alg1', have the
    digests (ledger, lease records, the full report, params()) measured on commit df9024d1, before the option existed
    (ALG1_DIGESTS); the report there has no key 'allowance' or 'online_lb'. At 'lb' the report records B0 None.
(g) needs_raw, needs_a12: on every cell on which the prototype Proto-alt ran in pilot step P2, built as e7h builds it
    (the E3 cells e3.build_instance(b, 8, 1, c, shared) for config seeds 101-104 and every b of e3.BS; the Q44 tuning
    cells Q1 I1 c3, Q1 I2 c1, Q2 I3 c1 and I4 c11-12 (e7h._q44_build); the bench_e7f weeks 107 and 108, one instance
    for L-tr and L-eg, with the view of each mode's information), conditions (i)-(iv) hold and OnlineLB's series
    equals the prototype's bit for bit.
"""
from __future__ import annotations

import copy
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from fixtures import CONFIGS, explicit_client, load_json, toy_config, toy_instance
from test_guard import T0G_TOL, _N, _OwnListInner, _RandomInner, _inner, _lease_rows, _ms, _no_times, _q_slot, \
    _rich_instance

from sublet.algos import online_lb as OL
from sublet.algos.common import PolicyError
from sublet.algos import guard as guard_mod
from sublet.algos.guard import GUARD_TOL, ProjectedGuarded
from sublet.engine import EngineConfig, simulate
from sublet.instance import build_instance, public_view
from sublet.metrics import _jsonable
from sublet.types import LenderModel, Schedule

SIM = Path(__file__).resolve().parents[1]
PROTO_DIR = SIM / "sublet" / "experiments" / "ms5b_proto"
RULE_ALT = "mix:0:1:1:Wk"            # ms5b_common.RULE_ALT, the prototype's rule of the alternative allowance
REL = 1e-9                           # ALG(t) >= LB'(t) up to REL max(1, LB'(t)) (Lemma G5'(c); INV2, INV3)
MODES = {"trace": {"schedule": "trace"}, "eager": {"schedule": "eager"},
         "iid": {"schedule": "iid_step", "params": {"D_slots": 1, "p": 0.3}}, "adaptive": {"schedule": "adaptive"},
         "refuse": {"schedule": "trace", "on_unavailable": "refuse"}}


def _proto():
    """The prototype copies (lb, run_proj, projected), imported by name from their folder as e7h.proto_modules does."""
    d = str(PROTO_DIR)
    if d not in sys.path:
        sys.path.insert(0, d)
    import lb
    import projected
    import run_proj
    return lb, run_proj, projected


def _proto_series(inst, view) -> tuple:
    """(LB, W_k, B, groups, info) of the prototype: lb.lb_series (its per-group info), run_proj.wk_series,
    run_proj.allowance(RULE_ALT) and lb.groups as (j, clients, sites)."""
    L, RP, _ = _proto()
    d = RP.inst_dict(inst, view)
    LB, _W, info = L.lb_series(d)
    Wk = RP.wk_series(view, d)
    B, par = RP.allowance(RULE_ALT, inst, d, view)
    assert par == {"B0": 1e12, "kappa": None}
    grs = [(int(g["llm"]), tuple(int(c) for c in g["clients"]), tuple(int(s) for s in g["sites"])) for g in L.groups(d)]
    return LB, Wk, B, grs, info


def _a9():
    from sublet.algos.a9 import NoticeCriticalRatio
    return NoticeCriticalRatio()


# ================================================================ fixture instances
def _toy_f1():
    cfg = toy_config()
    cfg["time"]["fast_slot_min"] = 1
    c = cfg["borrowers"]["clients"][0]
    c["demand"]["values"] = [float(v) for v in np.repeat(c["demand"]["values"], 5)]
    return build_instance(cfg)


def _toy_kinf():
    cfg = toy_config()
    cfg["llms"][0]["kappa_wtok_per_min"] = "inf"
    cfg["costs"]["kappa_infinite"] = True
    return build_instance(cfg)


def _ms2_f5(billing: str):
    cfg = load_json(CONFIGS / "ms2_multi_small.json")
    cfg["seed"] = 3
    cfg["time"].update(fast_slot_min=5, horizon_min=360)
    cfg["billing"] = billing
    return build_instance(cfg)


def _valid_variant(i: int, hor: int = 240, n_cl=None):
    """A toy-based instance that meets (i)-(iii): slow slot 10 min, fast slot 1, 5 or 2 min, the billing modes
    prepaid_D, commit_tau and per_slot with notices that are multiples of the fast slot (so every P_k is), two LLMs (1
    and 2 GPUs per replica), five to seven clients with random routing costs (some infinite or not below q, so an LLM
    can have several groups), on/off demand with peaks of up to six replicas, whole-millisecond load times (some a
    whole number of fast slots), random loading charges, kappa_infinite at i % 4 = 3 with every rent below q, and
    every rent at or above q at i % 5 = 4 (capacitated: all-fallback groups)."""
    rng = np.random.default_rng(9100 + i)
    fast = (1, 5, 2)[i % 3]
    billing = ("prepaid_D", "commit_tau", "per_slot")[(i // 3) % 3]
    kinf = i % 4 == 3
    dear = (not kinf) and i % 5 == 4
    slow = 10
    cfg = toy_config()
    cfg["time"].update(slow_slot_min=slow, fast_slot_min=fast, horizon_min=hor)
    cfg["billing"] = billing
    H = [int(x) * fast for x in rng.choice([0, 1, 2, 5], size=2)]
    cfg["contracts"] = [{"id": "short", "tau_min": slow, "H_min": H[0]},
                        {"id": "long", "tau_min": 2 * slow, "H_min": H[1]},
                        {"id": "prot", "tau_min": None, "H_min": 0, "prepaid_min": slow}]
    cfg["llms"] = [cfg["llms"][0], {**cfg["llms"][0], "id": "M2", "g": 2}]
    qg = float(cfg["prices"]["q_gpu_usd_per_gpu_h"])
    lo, hi = (1.0, 1.5) if dear else (0.2, 0.9)
    cfg["prices"]["a_protected_usd_per_gpu_h"] = float(rng.uniform(lo, hi) * qg)
    for e in cfg["lenders"]:
        if e["kind"] == "synthetic":
            e["prices"] = {"short": float(rng.uniform(lo, hi) * qg), "long": float(rng.uniform(lo, hi) * qg)}
            e["R"] = [r for r in e["R"] if r < hor // slow]
    n = int(n_cl or 5 + i % 3)
    T_f = hor // fast
    llm = ["M", "M2"] + [str(rng.choice(["M", "M2"])) for _ in range(n - 2)]
    base = cfg["borrowers"]["clients"][0]
    cfg["borrowers"]["clients"] = [{**base, "llm": x, "borrowers": [f"b{k}"],
                                    "demand": {"kind": "array", "values": [1.0] * T_f}} for k, x in enumerate(llm)]
    inst = build_instance(cfg)
    m, J = inst.m, inst.J
    q = np.array([x.q_usd_per_h for x in inst.llms])
    cl = np.asarray(inst.clients.llm)
    dl = np.empty((n, m))
    for c in range(n):
        for l in range(m):
            u = rng.random()
            dl[c, l] = (np.inf if u < 0.35 else q[cl[c]] * (1.0 + rng.random()) if u < 0.45
                        else q[cl[c]] * rng.uniform(0.0, 0.9))
    inst.clients.delta_usd_per_h = dl
    dem = np.zeros((n, T_f))
    for c in range(n):
        dem[c] = np.where(rng.random(T_f) < 0.75, rng.choice([0.3, 1.0, 1.7, 2.5, 3.6]) * (0.5 + rng.random(T_f)), 0.0)
    inst.clients.demand = dem
    inst.lam_s = rng.choice([0.0, 60.0 * fast, 120.0 * fast, 37.5, 61.234, 245.0, 700.125, 1300.0],
                            size=(J, m)).astype(float)
    inst.beta_usd = rng.uniform(0.0, 0.3, (J, m))
    inst.kappa_infinite = bool(kinf)
    return inst


def _colocated(n: int, hor: int, values=None):
    """configs/toy.json on a horizon of `hor` minutes (5-min slow and fast slots; revocation slots past it dropped)
    with n co-located clients of LLM M in region r0 (borrowers b0, b1, ...; so one group), client c with the demand
    values[c] per fast slot (1.0 at every fast slot by default)."""
    cfg = toy_config()
    cfg["time"]["horizon_min"] = int(hor)
    T_f = int(hor) // 5
    for e in cfg["lenders"]:
        if e["kind"] == "synthetic":
            e["R"] = [r for r in e["R"] if r < T_f]
    vals = [[1.0] * T_f] * n if values is None else values
    cfg["borrowers"]["clients"] = [explicit_client(v, borrower=f"b{c}") for c, v in enumerate(vals)]
    return build_instance(cfg)


def _a_instances() -> dict:
    out = {"toy": toy_instance(), "toy_f1": _toy_f1(), "toy_kinf": _toy_kinf(),
           "toy_commit": toy_instance({"billing": "commit_tau"}), "toy_perslot": toy_instance({"billing": "per_slot"}),
           "ms2_f1": _ms(3, 360), "ms2_f5_commit": _ms2_f5("commit_tau"), "ms2_f5_perslot": _ms2_f5("per_slot")}
    for i in range(15):
        out[f"v{i}"] = _valid_variant(i)
    return out


def _probe_cfg(i: int) -> dict:
    """check_g5p._probe_spec(i)'s config, i in (0, 2): one revocable site (menu 'short', tau 5 min, R empty) and the
    protected site, beta = 0, lambda = 0, q_GPU = 10 USD/GPU-h, no stranding charge, 2 h, demand 1 per client; probe 0:
    notice 2 min (prepaid_D: P = 7 min on 5-min fast slots), price 1; probe 2: kappa_infinite, notice 5 min, prices 12
    above q, two clients."""
    cfg = toy_config()
    cfg["name"] = f"probe_v{i}"
    cfg["seed"] = 300 + i
    kinf = i == 2
    cfg["billing"] = "prepaid_D"
    cfg["time"] = {"slow_slot_min": 5, "fast_slot_min": 5, "horizon_min": 120, "start_minute_of_week": 0}
    cfg["prices"]["q_gpu_usd_per_gpu_h"] = 10.0
    cfg["prices"]["a_protected_usd_per_gpu_h"] = 12.0 if kinf else 5.0
    cfg["contracts"] = [{"id": "short", "tau_min": 5, "H_min": 5 if kinf else 2},
                        {"id": "prot", "tau_min": None, "H_min": 0, "prepaid_min": 5}]
    cfg["lenders"] = [{"id": "L0", "kind": "synthetic", "region": "r0", "group": "g0", "menu": ["short"],
                       "prices": {"short": 12.0 if kinf else 1.0}, "capacity_gpus": 64, "R": [],
                       "load_scenario": "explicit", "lam_s": 0.0},
                      {"id": "P", "kind": "protected", "region": "r0", "group": "gp", "menu": ["prot"],
                       "capacity_gpus": None, "load_scenario": "explicit", "lam_s": 0.0}]
    cfg["costs"]["beta_jl_usd"] = 0.0
    cfg["stranding"]["mu_over_beta_tilde"] = 0.0
    if kinf:
        cfg["llms"][0]["kappa_wtok_per_min"] = "inf"
        cfg["costs"]["kappa_infinite"] = True
    cfg["borrowers"] = {"model": "explicit", "clients": [
        {"llm": "M", "region": "r0", "slo_class": "strict", "borrowers": [f"b{c}"],
         "demand": {"kind": "array", "values": [1.0] * 24}} for c in range(2 if kinf else 1)]}
    return cfg


def _schedules(inst) -> dict:
    """The schedules of check_g5p.py: trace (the lender's static schedule at lender seed = config seed), eager, none."""
    from sublet.config import rng_streams
    from sublet.lender import Lender
    trace = Lender(inst, LenderModel(), rng_streams(int(inst.seed))["lender"]).static_schedule()
    none = Schedule("none", tuple(np.zeros(0, dtype=np.int64) for _ in inst.sites), True)
    return {"trace": trace, "eager": Schedule.eager(inst), "none": none}


def _milp(inst, sch):
    """(incumbent, status) of the fast-grid MILP (opt.milp.solve_opt, as check_g5p.py: gap 1e-9, 120 s)."""
    from sublet.opt.milp import solve_opt
    r = solve_opt(inst, sch, grid="fast", time_limit_s=120.0, mip_rel_gap=1e-9, return_plan=False)
    assert r.objective is not None and np.isfinite(r.objective), r.status_msg
    return float(r.objective), int(r.status)


# ================================================================ (a) equality with the prototype
def test_hand_values_toy():
    """configs/toy.json by hand: one group (client 0; sites L0, L1, P), r = 2.85 (L0's 'short', zeta 1), hat-beta = 0 +
    2.85 x 5 / 60 (lam 300 s = one 5-min fast slot), n_f = d_f in {0, 1} on 16 fast slots with demand 1, so LB'(T) =
    min{16 x 7.15 x 5 / 60, hat-beta + 16 x 2.85 x 5 / 60} = 4.0375; W_k(T) = beta~ + a P / 60 at L0's k* ('short',
    P = 10 min) = 300 / 3600 (2.85 + 7.15) + 2.85 x 10 / 60 = 1.308333...; B(T) = W_k(T)."""
    inst = toy_instance()
    view = public_view(inst, "I1")
    assert OL.groups(view) == [(0, (0,), (0, 1, 2))]
    olb = OL.OnlineLB(view)
    gr = olb.groups[0]
    assert gr.kind == "cap" and gr.r == 2.85 and abs(gr.hb - 2.85 * 5 / 60) <= 1e-15
    s = OL.series(view, inst.clients.demand)
    assert abs(s["LB"][-1] - 4.0375) <= 1e-12 and abs(s["Wk"][-1] - (300 / 3600 * 10.0 + 2.85 * 10 / 60)) <= 1e-12
    assert s["B"][-1] == s["Wk"][-1] and len(s["B"]) == inst.grid.T_slow
    assert np.all(s["LB"][:2] == 0.0) and s["Wk"][0] == 0.0          # no demand in slots 0 and 1


def test_wk_tolerance():
    """W_k's tolerance ceil(peak - WK_TOL) by hand: configs/toy.json with three co-located clients (one group, sites L0,
    L1, P) whose demands in fast slot 3 are 1.1, 1.3 and 0.6 (0 elsewhere but for client 0's 1.0 in slots 6-9):
    d_Gamma(3) = (1.1 + 1.3) + 0.6 = 3.0000000000000004 in client order, so the peak is just above 3, and W_k counts 3
    replicas (ceil(peak) would count 4): W_k(t) = 0 before slot 3 and 3 p_Gamma from slot 3 on, p_Gamma = beta~ + a P
    / 60 at L0's k* ('short', P = 10 min) = 1.308333...; the series equals run_proj.wk_series (and LB', B the
    prototype's) bit for bit."""
    vals = [[0.0] * 24 for _ in range(3)]
    vals[0][3], vals[1][3], vals[2][3] = 1.1, 1.3, 0.6
    vals[0][6:10] = [1.0] * 4
    inst = _colocated(3, 120, vals)
    view = public_view(inst, "I1")
    assert OL.groups(view) == [(0, (0, 1, 2), (0, 1, 2))]
    assert OL.conditions(view)["valid"] is True
    olb = OL.OnlineLB(view)
    gr = olb.groups[0]
    dg = gr.demand(np.asarray(inst.clients.demand, dtype=np.float64))
    assert dg[3] == 3.0000000000000004 and dg[3] > 3.0 and float(np.ceil(dg[3])) == 4.0
    assert abs(gr.p - (300 / 3600 * 10.0 + 2.85 * 10 / 60)) <= 1e-12
    s = OL.series(view, inst.clients.demand)
    want = np.where(np.arange(inst.grid.T_slow) >= 3, 3.0 * gr.p, 0.0)
    assert np.array_equal(s["Wk"], want), s["Wk"]
    LBp, Wkp, Bp, _grs, _info = _proto_series(inst, view)
    for key, ref in (("LB", LBp), ("Wk", Wkp), ("B", Bp)):
        assert np.array_equal(s[key], ref), (key, s[key], ref)


def test_prototype_equality():
    """(a): on every fixture instance of _a_instances, which meet (i)-(iii), OnlineLB's groups are lb.groups in order
    and its LB'(t), W_k(t) and B(t) equal the prototype's bit for bit at every slow slot. Coverage: an LLM with two or
    more groups, a group with a peak of at least two replicas (prototype Nmax >= 2), the kinds capacitated,
    all-fallback and uncapacitated, fast slots of 1, 2 and 5 min, the three billing modes, and slots at which B
    takes LB' (LB' < W_k) and at which it takes W_k (W_k < LB')."""
    st = Counter()
    for name, inst in _a_instances().items():
        view = public_view(inst, "I1")
        cond = OL.conditions(view)
        assert cond == {"i": True, "ii": True, "iii": True, "iv": True, "valid": True}, (name, cond)
        LBp, Wkp, Bp, grs, info = _proto_series(inst, view)
        assert OL.groups(view) == grs, name
        olb = OL.OnlineLB(view)
        for t in range(inst.grid.T_slow):
            olb.step(SimpleNamespace(t=t, demand=inst.clients.demand[:, t * inst.grid.phi:(t + 1) * inst.grid.phi]))
        for key, got, want in (("LB", olb.LB_series, LBp), ("Wk", olb.Wk_series, Wkp), ("B", olb.B_series, Bp)):
            got = np.asarray(got)
            assert got.shape == want.shape and np.array_equal(got, want), (name, key, np.max(np.abs(got - want)))
        assert olb.report() == {"LB_T": LBp[-1], "Wk_T": Wkp[-1], "B_T": Bp[-1], "n_groups": len(grs)}, name
        llms = Counter(j for j, _c, _s in grs)
        st["multi_group_llm"] += any(v >= 2 for v in llms.values())
        st["nmax_ge_2"] += any(int(g["Nmax"]) >= 2 for g in info)
        for gr in olb.groups:
            st["kind:" + gr.kind] += 1
        st[f"fast:{inst.grid.fast_min}"] += 1
        st["billing:" + inst.billing] += 1
        L, W = np.asarray(olb.LB_series), np.asarray(olb.Wk_series)
        st["B=LB<Wk"] += int(np.sum(L < W))
        st["B=Wk<LB"] += int(np.sum(W < L))
    for k in ("multi_group_llm", "nmax_ge_2", "kind:cap", "kind:fb", "kind:unc", "fast:1", "fast:2", "fast:5",
              "billing:prepaid_D", "billing:commit_tau", "billing:per_slot", "B=LB<Wk", "B=Wk<LB"):
        assert st[k] > 0, (k, st)


def test_conditions_and_corner():
    """conditions(view) by hand: the probes of (b) fail (ii) (probe 0, P_k = 7 on 5-min fast slots) and (i) (probe 2,
    kappa_infinite with r >= q); configs/toy.json with 5-min fast slots and the notice 2 min fails (ii); a load time of
    60.0004 s on 1-min fast slots (lam_ms = 60000, a whole fast slot, below 1000 lam_s) is in the corner and fails
    (iii): there OnlineLB's entry cost uses Lambda-bar = theta Delta_f = 1 min, and the prototype's K is larger by r
    (fl(60.0004 / 60) - 1) / 60 (C3 §9, at most r / 7.2e6 per entry), while the rest of its data is unchanged. (iv)
    on configs/toy.json cut to one 5-min slot with n co-located clients (one group): it holds for n = 7, fails for n
    = 8 (numpy's pairwise sum of lb.py's one-column reduction), and holds for n = 8 on a horizon of two fast slots;
    (i)-(iii) hold on all three."""
    for i, want in ((0, {"i": True, "ii": False, "iii": True, "iv": True}),
                    (2, {"i": False, "ii": True, "iii": True, "iv": True})):
        cond = OL.conditions(public_view(build_instance(_probe_cfg(i)), "I1"))
        assert cond == {**want, "valid": False}, (i, cond)
    inst = toy_instance({"contracts.0.H_min": 2})
    assert OL.conditions(public_view(inst, "I1"))["ii"] is False
    inst = _toy_f1()
    inst.lam_s = np.full_like(inst.lam_s, 60.0004)
    view = public_view(inst, "I1")
    assert OL.conditions(view) == {"i": True, "ii": True, "iii": False, "iv": True, "valid": False}
    gr = OL.OnlineLB(view).groups[0]
    L, RP, _ = _proto()
    p = L.group_params(RP.inst_dict(inst, view), L.groups(RP.inst_dict(inst, view))[0])
    assert gr.r == p["r"] and gr.hb == 0.0 + gr.r * 1.0 / 60.0
    assert p["K"] - gr.hb == pytest.approx(gr.r * (60.0004 / 60.0 - 1.0) / 60.0, rel=1e-6) and p["K"] > gr.hb
    for n, hor, iv in ((7, 5, True), (8, 5, False), (8, 10, True)):
        view = public_view(_colocated(n, hor), "I1")
        assert view.grid.T_fast == hor // 5 and [len(c) for _j, c, _s in OL.groups(view)] == [n], (n, hor)
        assert OL.conditions(view) == {"i": True, "ii": True, "iii": True, "iv": iv, "valid": iv}, (n, hor)


# ================================================================ (b) the prototype's defects
def test_probe_defects():
    """(b): probe 0 (P_k = 7 min on 5-min fast slots, zeta = 0.7) gives LB'(T) = 1.4 and probe 2 (kappa_infinite, rent
    12 above q 10, two clients: no all-fallback shortcut) gives 24.0, each at most the fast-grid MILP's incumbent under
    trace, eager and none; the prototype's values 2.0 and 40.0 exceed the MILP optimum under none (status optimal)."""
    L, RP, _ = _proto()
    for i, want, proto in ((0, 1.4, 2.0), (2, 24.0, 40.0)):
        inst = build_instance(_probe_cfg(i))
        view = public_view(inst, "I1")
        lb = float(OL.series(view, inst.clients.demand)["LB"][-1])
        assert abs(lb - want) <= 1e-12 * want, (i, lb)
        lbp = float(L.lb_series(RP.inst_dict(inst, view))[0][-1])
        assert abs(lbp - proto) <= 1e-12 * proto, (i, lbp)
        for sn, sch in _schedules(inst).items():
            obj, status = _milp(inst, sch)
            assert lb <= obj * (1 + REL) + 1e-12, (i, sn, lb, obj)
            if sn == "none":
                assert status == 0 and lbp > obj * (1 + 1e-6), (i, lbp, obj)
                assert abs(obj - want) <= 1e-6 * want, (i, obj)          # LB' is tight on both probes


# ================================================================ (c) ALG(t) >= LB'(t) on engine runs
def _policy(kind: str, inst, seed: int, onu):
    if kind in ("BL1", "BL5"):
        return _inner(kind)
    if kind == "A9":
        return _a9()
    if kind == "random":
        return _RandomInner(seed)
    if kind == "ownlist":
        return _OwnListInner(seed)
    if kind == "A8P":
        return ProjectedGuarded(inner="A9", allowance="lb", kappa=None, N_bound=_N(inst), on_unavailable=onu)
    if kind == "A8P-1way":
        return ProjectedGuarded(inner="A9", allowance="lb", kappa=None, project=False, N_bound=_N(inst),
                                on_unavailable=onu)
    if kind == "A8P-random":
        return ProjectedGuarded(inner=_RandomInner(seed), safe="fb", allowance="lb", kappa=None, on_unavailable=onu)
    if kind == "A8P-ownlist":
        return ProjectedGuarded(inner=_OwnListInner(seed), safe="fb", allowance="lb", kappa=None, on_unavailable=onu)
    raise ValueError(kind)


A9_KINDS = ("A9", "A8P", "A8P-1way")    # policies around A9 (its contract table is cached per view, a9.contract_table)


def _c_instance(k: int, kind: str):
    """The k-th instance of (c): _rich_instance variants 0-7 (kappa_infinite at odd k) and random toy variants; for the
    policies around A9 one of four of them (A9's insurance test takes seconds per new instance, then it is cached)."""
    if kind in A9_KINDS:
        k = (0, 1, 2, 6)[k % 4]
    if k % 3 == 2:
        return _valid_variant(20 + k, hor=120)
    return _rich_instance(k % 2, (k // 3 * 2 + k % 3) % 8, bool(k % 2))


def test_alg_at_least_lb():
    """(c): ALG(t) >= LB'(t) - REL max(1, LB'(t)) at every slow slot of every run, no invariant failure. Policies BL1,
    BL5, A9, A8P(A9, 'lb') (project true and false), _RandomInner and _OwnListInner alone and under A8P (safe 'fb',
    'lb'); every policy under each lender mode of MODES on two instances. Coverage: Loads, Unloads and leases that
    carried replicas of two LLMs (in the random runs), and runs with LB'(T) > 0.5 ALG(T)."""
    st = Counter()
    kinds = ("BL1", "BL5", "A9", "A8P", "A8P-1way", "random", "ownlist", "A8P-random", "A8P-ownlist")
    k = 0
    for kind in kinds:
        for mname, lm in MODES.items():
            for _ in range(2):
                inst = _c_instance(k, kind)
                k += 1
                onu = "refuse" if lm.get("on_unavailable") == "refuse" else None
                pol = _policy(kind, inst, 31 * k + 7, onu)
                res = simulate(inst, pol, LenderModel(**lm), EngineConfig(), policy_seed=k % 3)
                tag = (kind, mname, k)
                assert res.invariant_failures == [], (tag, res.invariant_failures[:3])
                alg = np.cumsum(np.asarray(res.per_slot["total"], dtype=np.float64))
                lb = OL.series(public_view(inst, lm.get("information", "I1")), inst.clients.demand)["LB"]
                gap = lb - alg - REL * np.maximum(1.0, lb)
                assert np.all(gap <= 0.0), (tag, int(np.argmax(gap)), float(np.max(lb - alg)))
                st["runs"] += 1
                st["tight"] += bool(lb[-1] > 0.5 * alg[-1])
                multi = {}
                for r in res.replicas:
                    multi.setdefault(r.lease_id, set()).add(r.llm)
                st["two_llm_leases"] += sum(1 for v in multi.values() if len(v) >= 2)
                st["unloads"] += sum(1 for e in res.events if e[1] == "unload")
    assert st["runs"] == len(kinds) * len(MODES) * 2
    assert st["tight"] > 0 and st["two_llm_leases"] > 0 and st["unloads"] > 0, st


# ================================================================ (d) LB'(T) <= the fast-grid MILP
def test_lb_le_milp():
    """(d): LB'(T) <= OPT_P1, the fast-grid MILP's optimum (solved to optimality on every case; Lemma G5'(d)), under
    trace, eager and none on configs/toy.json, its kappa_infinite variant, two random toy variants (2 h, three
    clients; the second with kappa_infinite) and configs/ms2_multi_small.json at 1 h; also LB'(T) <= BL0a (the
    instance's all-fallback bill)."""
    cases = {"toy": toy_instance(), "toy_kinf": _toy_kinf(), "v1": _valid_variant(1, hor=120, n_cl=3),
             "v3": _valid_variant(3, hor=120, n_cl=3), "ms2_1h": _ms(3, 60)}
    n = 0
    for name, inst in cases.items():
        lb = float(OL.series(public_view(inst, "I1"), inst.clients.demand)["LB"][-1])
        assert lb <= float(np.sum(_q_slot(inst))) * (1 + REL), name
        for sn, sch in _schedules(inst).items():
            obj, status = _milp(inst, sch)
            assert status == 0 and lb <= obj * (1 + REL) + 1e-12, (name, sn, lb, obj, status)
            n += 1
    assert n == 15


# ================================================================ (e) monotone, non-anticipative, step order
def test_monotone_and_nonanticipative():
    """(e): LB', W_k and B are nondecreasing on every instance; with the demand after slot t set to 0 (t in {0, T/3,
    T/2, T - 2}) the series through t are unchanged bit for bit; a skipped or repeated slot and a demand of the wrong
    shape raise PolicyError; before the first step LB = W_k = B = 0."""
    insts = [toy_instance(), _toy_kinf(), _ms(3, 360), build_instance(_probe_cfg(0)), build_instance(_probe_cfg(2))]
    insts += [_valid_variant(i) for i in (0, 3, 4, 7)] + [_rich_instance(1, v, bool(v % 2)) for v in range(4)]
    for k, inst in enumerate(insts):
        view = public_view(inst, "I1")
        d = np.asarray(inst.clients.demand, dtype=np.float64)
        s = OL.series(view, d)
        T, phi = inst.grid.T_slow, inst.grid.phi
        for key in ("LB", "Wk", "B"):
            assert s[key].shape == (T,) and np.all(np.diff(s[key]) >= 0.0) and s[key][0] >= 0.0, (k, key)
        for t in sorted({0, T // 3, T // 2, T - 2}):
            d2 = d.copy()
            d2[:, (t + 1) * phi:] = 0.0
            s2 = OL.series(view, d2)
            for key in ("LB", "Wk", "B"):
                assert np.array_equal(s2[key][:t + 1], s[key][:t + 1]), (k, t, key)
    inst = toy_instance()
    olb = OL.OnlineLB(public_view(inst, "I1"))
    assert (olb.t, olb.LB, olb.Wk, olb.B, olb.LB_series) == (-1, 0.0, 0.0, 0.0, [])
    d = inst.clients.demand
    with pytest.raises(PolicyError):
        olb.step(SimpleNamespace(t=1, demand=d[:, 1:2]))
    olb.step(SimpleNamespace(t=0, demand=d[:, 0:1]))
    with pytest.raises(PolicyError):
        olb.step(SimpleNamespace(t=0, demand=d[:, 0:1]))
    with pytest.raises(PolicyError):
        olb.step(SimpleNamespace(t=1, demand=d[:, 1:3]))


# ================================================================ (f) A8P with allowance 'lb'
def test_a8p_allowance_params():
    """(f): PARAMS has 'allowance' 'alg1'; 'lb' needs kappa None (A8P's default kappa 10 raises PolicyError), an unknown
    allowance raises PolicyError; params() leaves the option out at 'alg1' (the records of Algorithm 1's allowance
    stay those of the pilot's A8P runs) and lists it at 'lb'; at 'alg1' the resolved parameters _p do not hold it
    either (e7h.proto_run passes an A8P's _p, without project, to the prototype's Guarded subclass)."""
    assert ProjectedGuarded.PARAMS["allowance"] == "alg1"
    for bad in ({"allowance": "lb"}, {"allowance": "lb", "kappa": 10.0}, {"allowance": "lb", "kappa": 0.0},
                {"allowance": "x"}, {"allowance": None}, {"allowance": "LB"}):
        with pytest.raises(PolicyError):
            ProjectedGuarded(inner="BL1", safe="fb", **bad)
    p0 = ProjectedGuarded(inner="BL1", safe="fb").params()
    assert "allowance" not in ProjectedGuarded(inner="BL1", safe="fb", allowance="alg1")._p
    assert "allowance" not in p0 and ProjectedGuarded(inner="BL1", safe="fb", allowance="alg1").params() == p0
    p = ProjectedGuarded(inner="BL1", safe="fb", allowance="lb", kappa=None).params()
    assert p["allowance"] == "lb" and p["kappa"] is None and {k: v for k, v in p.items() if k != "allowance"} == \
        {**p0, "kappa": None}
    p1 = ProjectedGuarded(inner="BL1", safe="fb", allowance="lb", kappa=None, project=False).params()
    assert p1["project"] is False and p1["allowance"] == "lb"


def _envelope_lb(inst, res, gamma: float, B: np.ndarray, safe_fb: bool, tag) -> int:
    """ALG(t) + R(t) <= gamma C_S(t) + B(t) + GUARD_TOL max(1, |rhs|) + T0G_TOL max(1, ALG(t)) at every executed slot
    (Theorem W, step (1)), ALG from the ledger, C_S the cumulative all-fallback cost rebuilt from the instance (S on
    FB; the report's curve is checked against it) or the report's curve (S = T11(FB, R)), B the independent series
    (the guard's B(t) must equal it bit for bit) and R(t) the report's reserve. Returns the slots checked."""
    rep = res.metrics["policy"]
    g = rep["guard"]
    t_a = rep["t_a"]
    alg = np.cumsum(np.asarray(res.per_slot["total"], dtype=np.float64))
    C_S = np.cumsum(_q_slot(inst))
    if safe_fb:
        assert np.allclose(rep["safe"]["C_S_curve"], C_S, rtol=1e-12, atol=1e-9), tag
    else:
        C_S = np.asarray(rep["safe"]["C_S_curve"], dtype=np.float64)
    n = 0
    for i, t in enumerate(g["slots"]):
        assert g["B"][i] == B[t], (tag, t, g["B"][i], B[t])
        if t_a is not None and t >= t_a:
            continue
        rhs = gamma * C_S[t] + B[t]
        lhs = alg[t] + g["reserve"][i]
        assert lhs <= rhs + GUARD_TOL * max(1.0, abs(rhs)) + T0G_TOL * max(1.0, alg[t]), (tag, t, lhs, rhs)
        n += 1
    return n


def test_a8p_lb_runs():
    """(f): A8P at allowance 'lb' around A9 (safe 'fb+pd'; project true and false), BL1 and _RandomInner (safe 'fb',
    gamma 1 and 0.5) on toy variants and _rich_instance variants under trace, eager, iid_step and 'refuse' (the option
    passed): no invariant failure; report allowance 'lb', kappa None, B0 None (top level and guard.B0; B0 is unused),
    online_lb = the independent OnlineLB's {LB_T, Wk_T, B_T, n_groups}, safe.B_curve = its B series (length T) bit for
    bit; the envelope from the ledger
    (_envelope_lb); ms4_common.certify and q44_study.certificate available and held in Theorem W's cases W(a), W(b).
    Coverage: aborting runs (project false), projected slots, and runs in which B(T) = LB'(T) < W_k(T)."""
    from sublet.experiments import ms4_common as m4
    from sublet.experiments import q44_study as q44
    st = Counter()
    cases = []
    for v in range(4):
        cases.append(("A9", _valid_variant(30 + v), {}))
        cases.append(("A9-1way", _valid_variant(40 + v), {"project": False}))
        cases.append(("BL1", _rich_instance(0, v, False), {"safe": "fb"}))
        cases.append(("random", _rich_instance(1, v + 4, bool(v % 2)), {"safe": "fb", "gamma": 0.5 + 0.5 * (v % 2)}))
    for ci, (inner, inst, kw) in enumerate(cases):
        for mname in ("trace", "eager", "iid", "refuse"):
            lm = MODES[mname]
            onu = "refuse" if mname == "refuse" else None
            inn = _RandomInner(11 * ci + 3) if inner == "random" else ("A9" if inner.startswith("A9") else inner)
            extra = {} if kw.get("safe") == "fb" else {"N_bound": _N(inst)}
            pol = ProjectedGuarded(inner=inn, allowance="lb", kappa=None, on_unavailable=onu, **extra, **kw)
            res = simulate(inst, pol, LenderModel(**lm), EngineConfig(), policy_seed=ci % 2)
            tag = (inner, ci, mname)
            assert res.invariant_failures == [], (tag, res.invariant_failures[:3])
            rep = res.metrics["policy"]
            view = public_view(inst, lm.get("information", "I1"))
            s = OL.series(view, inst.clients.demand)
            T = inst.grid.T_slow
            assert rep["allowance"] == "lb" and rep["kappa"] is None and rep["project"] is kw.get("project", True), tag
            assert rep["B0"] is None and rep["guard"]["B0"] is None, tag
            assert rep["online_lb"] == {"LB_T": s["LB"][-1], "Wk_T": s["Wk"][-1], "B_T": s["B"][-1],
                                        "n_groups": len(OL.groups(view))}, tag
            assert len(rep["safe"]["B_curve"]) == T and np.array_equal(rep["safe"]["B_curve"], s["B"]), tag
            assert pol.olb.t == T - 1 and len(pol.olb.B_series) == T, tag      # one step per act call, every mode
            st["slots"] += _envelope_lb(inst, res, float(kw.get("gamma", 1.0)), s["B"], kw.get("safe") == "fb", tag)
            cert, case = m4.certify(res, inst)
            c2 = q44.certificate(res, inst, rep, core_exact=False)
            assert cert["available"] and c2["available"] and cert["kappa"] is None, (tag, cert)
            assert cert["B_T"] == s["B"][-1], tag
            if inner != "random":                                    # registry.info_class needs a registered inner
                assert m4.a8_record(res, inst, pol.params())["B0_report_usd"] is None, tag
            if case in ("W(a)", "W(b)"):
                assert cert["held"] is True and c2["held"] is True, (tag, case, cert)
                st["held:" + case] += 1
            else:
                st["case:" + case] += 1
            st["aborts"] += rep["t_a"] is not None
            st["projected"] += rep["projection"]["slots"]
            st["B=LB"] += bool(s["LB"][-1] < s["Wk"][-1])
            st["runs"] += 1
    assert st["runs"] == len(cases) * 4 and st["held:W(a)"] > 0 and st["aborts"] > 0, st
    assert st["projected"] > 0 and st["B=LB"] > 0 and st["slots"] > 0, st


def _proto_policy(inst, model, project: bool):
    """The prototype projected.ProjectedGuard at run_proj.allowance(RULE_ALT)'s series, as e7h.proto_run builds it: an
    A8P of the rule's parameters (B0 1e12, kappa None) for the driver inputs and A8's other defaults, its resolved
    parameters without project (e7h.proto_run's filter, unchanged), an A9 instance as the inner policy, rho 1 and
    projection as given."""
    _L, RP, PJ = _proto()
    from sublet.algos.a9 import NoticeCriticalRatio
    view = public_view(inst, model.information)
    bser, par = RP.allowance(RULE_ALT, inst, RP.inst_dict(inst, view), view)
    base = ProjectedGuarded(inner="A9", N_bound=_N(inst), on_unavailable=model.on_unavailable, **par)
    p = {k: copy.deepcopy(v) for k, v in base._p.items() if k != "project"}
    p["inner"] = NoticeCriticalRatio(**dict(base._p.get("inner_params") or {}))
    p["inner_params"] = {}
    return PJ.ProjectedGuard(**p, N_bound=base.N_bound, on_unavailable=base.on_unavailable, allowance_series=bser,
                             rho=1.0, project=project), bser


def test_a8p_lb_equals_prototype():
    """(f): A8P(A9, allowance 'lb', kappa None) against the prototype projected.ProjectedGuard at run_proj.allowance's
    series (_proto_policy), with project true and with project false (A8 around A9 at the same series in both codes),
    on toy, ms2 (6 h) and random toy variants under trace, iid_step and 'refuse' (the option passed): the per-slot
    ledgers and the lease records are identical bit for bit (so the totals are equal), the guard's B(t) series equals
    the prototype's, and the abort slot is the same. Coverage: projected slots and aborts (project false)."""
    st = Counter()
    insts = {"toy": toy_instance(), "ms2": _ms(3, 360), "v1": _valid_variant(51), "v2": _valid_variant(52)}
    for name, inst in insts.items():
        for mname in ("trace", "iid", "refuse"):
            model = LenderModel(**MODES[mname])
            for project in (True, False):
                onu = model.on_unavailable
                pol = ProjectedGuarded(inner="A9", allowance="lb", kappa=None, project=project, N_bound=_N(inst),
                                       on_unavailable=onu)
                res = simulate(inst, pol, model, EngineConfig(), policy_seed=0)
                ppol, bser = _proto_policy(inst, model, project)
                ref = simulate(inst, ppol, model, EngineConfig(), policy_seed=0)
                tag = (name, mname, project)
                assert res.invariant_failures == [] and ref.invariant_failures == [], tag
                for k in ref.per_slot:
                    assert np.array_equal(res.per_slot[k], ref.per_slot[k]), (tag, k)
                assert res.components == ref.components and _lease_rows(res) == _lease_rows(ref), tag
                rep, rr = res.metrics["policy"], ppol.report()
                assert rep["t_a"] == rr["t_a"], tag
                assert np.array_equal(rep["safe"]["B_curve"], bser), tag
                st["aborts"] += rep["t_a"] is not None
                st["projected"] += rep["projection"]["slots"] if project else 0
                st["runs"] += 1
    assert st["runs"] == 24 and st["aborts"] > 0 and st["projected"] > 0, st


# ---------------------------------------------------------------- Algorithm 1's allowance: digests before the option
def _alg1_cases() -> dict:
    """{name: (instance builder, A8P keywords without 'allowance' (the inner as an id or a builder), lender model
    fields, policy seed)}: A8P at Algorithm 1's allowance around A9, BL1, BL5, _RandomInner and _OwnListInner, project
    true and false, constant and capped allowances."""
    return {
        "toy:A9:trace": (toy_instance, {"inner": "A9"}, {"schedule": "trace"}, 0),
        "toy:A9:iid": (toy_instance, {"inner": "A9"}, MODES["iid"], 1),
        "ms2:A9:trace": (lambda: _ms(3, 360), {"inner": "A9"}, {"schedule": "trace"}, 0),
        "v0:A9:eager": (lambda: _valid_variant(60), {"inner": "A9"}, {"schedule": "eager"}, 0),
        "rich0:BL1:trace": (lambda: _rich_instance(0, 0, False), {"inner": "BL1"}, {"schedule": "trace"}, 0),
        "rich1:BL1:trace": (lambda: _rich_instance(0, 1, False), {"inner": "BL1"}, {"schedule": "trace"}, 0),
        "rich2:BL5:1way": (lambda: _rich_instance(0, 2, False), {"inner": "BL5", "project": False},
                           {"schedule": "trace"}, 0),
        "rich3:random": (lambda: _rich_instance(1, 3, True), {"inner": lambda: _RandomInner(5), "safe": "fb",
                                                              "B0": 3.0, "kappa": None}, {"schedule": "eager"}, 0),
        "rich5:ownlist": (lambda: _rich_instance(1, 5, False), {"inner": lambda: _OwnListInner(9), "safe": "fb",
                                                                "B0": 0.3, "kappa": None, "gamma": 0.5},
                          {"schedule": "trace"}, 0),
        "toy:A9:1way": (toy_instance, {"inner": "A9", "project": False}, {"schedule": "trace"}, 0),
    }


def _alg1_digest(name: str, allowance=None) -> str:
    """sha256 of one case's run: components (hex), lease records, the full report without wall times (canonical
    JSON), and params(); A8P is built with allowance omitted (None) or as given; at Algorithm 1's allowance the report
    must not hold the keys of 'lb' (allowance, online_lb)."""
    build, kw, lm, ps = _alg1_cases()[name]
    inst = build()
    kw = {k: (v() if callable(v) else v) for k, v in kw.items()}
    if kw.get("safe") != "fb":
        kw["N_bound"] = _N(inst)
    if allowance is not None:
        kw["allowance"] = allowance
    pol = ProjectedGuarded(**kw)
    res = simulate(inst, pol, LenderModel(**lm), EngineConfig(), policy_seed=ps)
    assert res.invariant_failures == [], name
    rep = res.metrics.get("policy") or {}
    assert "allowance" not in rep and "online_lb" not in rep, name
    blob = json.dumps({"components": {k: float(v).hex() for k, v in sorted(res.components.items())},
                       "leases": _lease_rows(res), "report": _jsonable(_no_times(rep)),
                       "params": _jsonable(pol.params())}, sort_keys=True, default=str)
    return hashlib.sha256(blob.encode()).hexdigest()


# sha256 of _alg1_digest(name) on commit df9024d1 (guard.py before the option 'allowance'), per case of _alg1_cases()
ALG1_DIGESTS = {
    'toy:A9:trace': "7bd39b302ce94b764ba5f9b74bdef4a3a35208f751496dc037bdcb11edb890cb",
    'toy:A9:iid': "8c805177e273dd3ffa9728049ecf83cbc0052112665879ece349ab4835a2486f",
    'ms2:A9:trace': "ccbee1df520050ecbcfda2b1bb29b9a16277c27e0c65464adf1bbe4eed220f01",
    'v0:A9:eager': "504917968fe12c04899b05da3b791612aae4b28171556df2608e069ef23e2906",
    'rich0:BL1:trace': "b15a5b5842681f1c3889fcd33f4cf64d7d91a1cc2dadce93d0db619bab57c758",
    'rich1:BL1:trace': "677d5d77119add9dae818766f028feb5d88483f174694d1be888edfb842e8419",
    'rich2:BL5:1way': "c16771f13861e67d3c2f7c4211fb7d59b2304787e135bb1a0f487c5f73c7bb3f",
    'rich3:random': "cf2ae20a9628c06bf88593254543e79c2a8d7d79da53388588a03b24cbbe381f",
    'rich5:ownlist': "d4cdaa96621ace6e35edabf3e1efdb21f2625b4b30f41fd19ff14975e4fead21",
    'toy:A9:1way': "3dc447e9b13d366093461be137a9c0ffd1f704e903e3941fbdbde944a52bb923",
}


def test_alg1_bit_identical():
    """(f): A8P at Algorithm 1's allowance, with the option omitted and with allowance 'alg1', gives the run, the full
    report and params() measured before the option existed: the report has A8's keys, Remark R(a)'s four (project,
    projection, candidates, dropped_fast) and neither 'allowance' nor 'online_lb', and records the resolved B0."""
    assert set(ALG1_DIGESTS) == set(_alg1_cases())
    for name in _alg1_cases():
        assert _alg1_digest(name) == ALG1_DIGESTS[name], name
        assert _alg1_digest(name, "alg1") == ALG1_DIGESTS[name], name
    build, kw, lm, ps = _alg1_cases()["toy:A9:trace"]
    inst = build()
    res = simulate(inst, ProjectedGuarded(inner="A9", N_bound=_N(inst)), LenderModel(**lm), policy_seed=ps)
    rep = res.metrics["policy"]
    assert "allowance" not in rep and "online_lb" not in rep and rep["kappa"] == 10.0, sorted(rep)
    assert {"project", "projection", "candidates", "dropped_fast"} <= set(rep), sorted(rep)
    b0 = guard_mod.b0_auto(public_view(inst, "I1"))
    assert rep["B0"] == rep["guard"]["B0"] == b0 and rep["safe"]["B_curve"] == [min(b0, 10.0 * b) for b in
                                                                                 rep["safe"]["B_on"]]


# ================================================================ (g) pilot instances (raw traces)
def _p2_cells():
    """[(name, instance, [information models])]: every cell on which Proto-alt ran in pilot step P2 (e7h's part p2,
    full mode), built as e7h builds it: the E3 cells (e3.build_instance(b, U, MU, c, True) for c in E3_PILOT and b in
    e3.BS; the cell's lender model), the Q44 tuning cells (e7h._q44_build without a window; the block's L-tr model, as
    run_q44 builds Proto-alt's), and the bench_e7f weeks of P2_PAIR (run_week's instance: ms5b_common.week_spec of
    BL0a at L-tr over the week, drivers.run.build; L-tr and L-eg share it, instance_key 'base', each with its lender
    model from the Proto-alt spec of its mode)."""
    from sublet.drivers import run as drun
    from sublet.experiments import e3, e7h
    from sublet.experiments import ms5b_common as m5
    assert set(m5.instance_key(m) for m in ("L-tr", "L-eg")) == {"base"}
    out = []
    for c in e7h.E3_PILOT:
        for b in e3.BS:
            inst, model, _ecfg, _ov = e3.build_instance(b, e7h.U, e7h.MU, c, True)
            out.append((f"e3:b{b}:c{c}", inst, [model.information]))
    for blk, iid, c in e7h.Q44_TUNING:
        block, idef, inst, _ecfg = e7h._q44_build(blk, iid, c, None)
        spec = e7h._q44_spec(block, idef, "Proto-alt", "L-tr", c, (0,), {"inner": "A9", "project": True})
        out.append((f"q44:{blk}:{iid}:c{c}", inst, [drun._lender_model(spec, inst).information]))
    for c in e7h.P2_PAIR:
        spec0 = m5.week_spec("BL0a", {}, mode="L-tr", c=c, horizon_min=m5.WEEK_MIN, seeds=(0,), name="e7h_build")
        inst, _model, _ecfg = drun.build(spec0, c)
        infos = []
        for mode in ("L-tr", "L-eg"):
            spec = m5.week_spec("A8P", {"inner": "A9", "project": True}, mode=mode, c=c, horizon_min=m5.WEEK_MIN,
                                seeds=(0,), name="e7h_p2_Proto-alt")
            infos.append(drun._lender_model(spec, inst).information)
        out.append((f"week:c{c}", inst, sorted(set(infos))))
    return out


@pytest.mark.needs_raw
@pytest.mark.needs_a12
def test_pilot_instances_equal_prototype():
    """(g): on every cell on which Proto-alt ran in P2 (_p2_cells: the 24 E3 cells, the 5 Q44 tuning cells and the
    bench_e7f weeks 107 and 108 under L-tr and L-eg), with the view of each information model the cell's Proto-alt runs
    used, conditions (i)-(iv) hold and OnlineLB's groups, LB'(t), W_k(t) and B(t) equal the prototype's (lb.groups,
    lb.lb_series, run_proj.wk_series, run_proj.allowance('mix:0:1:1:Wk')) bit for bit (C3 §9, 'Relation to the
    prototype', audit note on the pilot-cell conditions)."""
    from sublet.experiments import e3, e7h
    cells = _p2_cells()
    assert len(cells) == len(e7h.E3_PILOT) * len(e3.BS) + len(e7h.Q44_TUNING) + len(e7h.P2_PAIR) == 31
    n = 0
    for name, inst, infos in cells:
        for info in infos:
            view = public_view(inst, info)
            cond = OL.conditions(view)
            assert cond == {"i": True, "ii": True, "iii": True, "iv": True, "valid": True}, (name, info, cond)
            s = OL.series(view, inst.clients.demand)
            LBp, Wkp, Bp, grs, _info = _proto_series(inst, view)
            assert OL.groups(view) == grs, (name, info)
            for key, want in (("LB", LBp), ("Wk", Wkp), ("B", Bp)):
                assert np.array_equal(s[key], want), (name, info, key, float(np.max(np.abs(s[key] - want))))
            n += 1
    assert n >= len(cells)
