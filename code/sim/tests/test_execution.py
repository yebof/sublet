"""Tests of the execution layer and policy A3 (sublet/algos/execution.py, a3.py; design/sim_spec_ms2.md
§7; R2 of §17.3; §17.2)."""
import json
import math

import numpy as np

import fam
import pd as ref_pd

from fixtures import (CM_ROWS, CONFIGS, c3b_case, cm_case, explicit_client, lease_cost,
                      ms2_checks_dir, toy_config)

from sublet.algos.a3 import A3
from sublet.algos.common import LeaseBook, column_cost, pd_window_slots
from sublet.algos.execution import ExecutionLayer, LogicalSlot, RRSiteRule
from sublet.algos.handler import ReclaimHandler
from sublet.engine import simulate
from sublet.instance import build_instance, from_core, public_view
from sublet.policies import RenewReplay
from sublet.policies.base import Policy
from sublet.timing import latest_prewarm_slot
from sublet.types import LeaseView, LenderModel, SlowObs

TC = CONFIGS.parents[1] / "theory_checks" / "c3"
TOL = 1e-9
RATES = (0.0, 0.02, 0.1, 0.3, 1.0)


def _close(a, b, tol=TOL) -> bool:
    return abs(float(a) - float(b)) <= tol * max(1.0, abs(float(b)))


def _a3_ref(rbar, I):
    """A3 in reference mode (x3 off, X2 'reference', cold reaction), §7.5."""
    if rbar == "theory":
        return A3(rbar="theory", N_bound=max(I.n * I.T, 3), x3=False, x2="reference", reaction="cold")
    return A3(rbar=1, x3=False, x2="reference", reaction="cold")


# ---------------------------------------------------------------- reference mode
def test_reference_mode_equals_renew_replay():
    """§7.5: A3 with x3=False, x2='reference', reaction='cold' and policy_rng = default_rng(s) equals
    RenewReplay(round_pd(FracPD(I).run(), default_rng(s), r)['opened']) on c3b_case seeds 0-9, rates 0,
    0.02, 0.1, 0.3, 1.0, s in {0, 1}, r-bar in {theory, 1}: identical ledgers (components and per-slot
    components to 1e-12, the same leases)."""
    for seed in range(10):
        I, _ = c3b_case(seed, 0.0)
        pdr = ref_pd.FracPD(I).run()
        rounds = {(s, rb): ref_pd.round_pd(pdr, np.random.default_rng(s), r=None if rb == "theory" else 1)
                  for s in (0, 1) for rb in ("theory", 1)}
        for rate in RATES:
            I2, om = c3b_case(seed, rate)
            inst, _ = from_core(I2, om)
            for (s, rb), x in rounds.items():
                tag = f"seed {seed} rate {rate} s {s} r {rb}"
                pol = _a3_ref(rb, I2)
                a = simulate(inst, pol, policy_rng=np.random.default_rng(s))
                b = simulate(inst, RenewReplay(x["opened"]))
                assert a.invariant_failures == [] and b.invariant_failures == [], tag
                assert pol.opened_ref() == x["opened"], tag
                for k, v in b.components.items():
                    assert abs(a.components[k] - v) <= 1e-12 * max(1.0, abs(v)), (tag, k, a.components[k], v)
                for k, v in b.per_slot.items():
                    assert np.all(np.abs(a.per_slot[k] - v) <= 1e-12 * np.maximum(1.0, np.abs(v))), (tag, k)
                la = sorted((L.site, L.contract, L.start_slot, L.end_min, L.end_cause) for L in a.leases)
                lb = sorted((L.site, L.contract, L.start_slot, L.end_min, L.end_cause) for L in b.leases)
                assert la == lb, tag


def test_c4_lower_a_pd_columns():
    """R2 (PD columns of c4_lower.txt (a)): cm_case(m, rho) for the 16 rows under the adaptive lender, A3 in
    reference mode with policy_rng = default_rng(s), s = 0..3: the realized R equals
    pd.real_cost_renew(I, opened, None, adversary=True)[1]; mean and minimum over s of (engine lease cost +
    pd.service_cost_given_open(I, opened).sum()) / fam.opt_dp(Fam(m, rho, 2, 1, 48), R) equal c4_lower.json
    a[*] pd_r1, pd_r1_min (r-bar = 1) and pd_rth, pd_rth_min (theory r-bar), 1e-9."""
    rows = json.loads((TC / "out" / "c4_lower.json").read_text())["a"]
    assert [(r["m"], r["rho"]) for r in rows] == list(CM_ROWS)
    for row in rows:
        m, rho = row["m"], row["rho"]
        I = cm_case(m, rho)
        F = fam.Fam(m, rho, 2, 1, 48)
        inst, _ = from_core(I, [np.zeros(0, np.int64)] * m)
        for tag, rb in (("pd_r1", 1), ("pd_rth", "theory")):
            ratios = []
            for s in range(4):
                pol = _a3_ref(rb, I)
                res = simulate(inst, pol, LenderModel(schedule="adaptive"), policy_rng=np.random.default_rng(s))
                assert res.invariant_failures == [], (m, rho, tag, s)
                opened = pol.opened_ref()
                _, om = ref_pd.real_cost_renew(I, opened, None, adversary=True)
                R = [np.asarray(r, dtype=np.int64) for r in res.schedule.R]
                assert all(np.array_equal(a, b) for a, b in zip(R, om)), (m, rho, tag, s)
                serv = float(ref_pd.service_cost_given_open(I, opened).sum())
                ratios.append((lease_cost(res.components) + serv) / fam.opt_dp(F, R)[0])
            assert _close(np.mean(ratios), row[tag]), (m, rho, tag, np.mean(ratios), row[tag])
            assert _close(np.min(ratios), row[tag + "_min"]), (m, rho, tag, np.min(ratios), row[tag + "_min"])


# ---------------------------------------------------------------- hand instances
class _LayerDriver(Policy):
    """A constant planner around an ExecutionLayer: opens[t] = [(key, s, L)] are opened at slot t; the layer
    is built at reset with `layer_kw` and a ReclaimHandler(view, **handler_kw)."""
    name = "layer_driver"

    def __init__(self, opens, handler_kw=None, **layer_kw):
        self.opens = opens
        self.handler_kw = {"reaction": "cold"} if handler_kw is None else handler_kw
        self.layer_kw = layer_kw

    def reset(self, view, rng):
        super().reset(view, rng)
        self.book = LeaseBook()
        self.handler = ReclaimHandler(view, **self.handler_kw)
        self.layer = ExecutionLayer(view, self.book, handler=self.handler, **self.layer_kw)
        self.slot_log = []

    def act(self, obs):
        self.layer.absorb(self.book.begin(obs))
        for key, s, L in self.opens.get(obs.t, ()):
            self.layer.open(key, t0=obs.t, s=s, L=L)
        self.layer.step(obs)
        self.slot_log.append({k: (sl.lease, sl.ptr, sl.next_lease) for k, sl in self.layer.slots.items()})
        return self.book.assemble(obs, self.view)

    def report(self):
        return self.layer.report()


def _three_sites(R, demand, *, prices=(2.85, 2.85, 2.85), H_min=5, lam=0.0, fast=5, T=24, contracts=None):
    """Synthetic sites S0, S1 (region r0) and S2 (region r1), unlimited capacity, one contract c (tau 5 min,
    H_min) unless `contracts` [(id, tau_min, H_min)] is given, explicit R per site, load time lam; clients
    of the toy LLM: demand[c] = (region, slo, per-slow-slot values)."""
    cfg = toy_config(sites=["L0", "L1"])
    cfg["time"] = {"slow_slot_min": 5, "fast_slot_min": fast, "horizon_min": 5 * T, "start_minute_of_week": 0}
    cs = contracts if contracts is not None else [("c", 5, H_min)]
    cfg["contracts"] = [{"id": k, "tau_min": t, "H_min": h} for k, t, h in cs]
    cfg["regions"] = {"list": ["r0", "r1"], "adjacency": [["r0", "r1"]], "default_slo_class": "strict",
                      "relaxed_routing_cost_over_q": 0.05}
    base = dict(cfg["lenders"][0])
    lenders = []
    for i in range(3):
        L = dict(base)
        L.update({"id": f"S{i}", "group": f"g{i}", "region": "r0" if i < 2 else "r1", "menu": [k for k, _, _ in cs],
                  "prices": {k: float(prices[i]) for k, _, _ in cs}, "capacity_gpus": 1000, "R": list(R[i]),
                  "lam_s": float(lam)})
        lenders.append(L)
    cfg["lenders"] = lenders
    phi = 5 // fast
    cfg["borrowers"]["clients"] = [
        {**explicit_client(np.repeat(np.asarray(v, dtype=float), phi).tolist(), borrower=f"b{c}"),
         "region": reg, "slo_class": slo} for c, (reg, slo, v) in enumerate(demand)]
    cfg["stranding"]["mu_over_beta_tilde"] = 0.0
    return build_instance(cfg)


def _sites_of(res):
    return [(L.site, L.start_slot) for L in sorted(res.leases, key=lambda x: x.id)]


def _obs(t, n, leases, demand=None):
    D = np.ones((n, 1)) if demand is None else np.asarray(demand, dtype=float).reshape(n, 1)
    return SlowObs(t, 5 * t, D, leases, {}, [], [], [], None, np.zeros((1, 3)), np.zeros(n), 0.0)


def _lv(lid, site, ann=None):
    return LeaseView(lid, site, 0, 1, 0, 0, 10, ann, None if ann is None else 5 * ann + 5, ())


def test_x3_rotation_hand():
    """§7.3 (M15): three synthetic sites with explicit R. A revocation death moves the logical slot to the next
    pool site after ptr in pi's cyclic order, where the pool (sites offering k, SLO-feasible for every stranded
    client, C <= zeta min C) is recomputed at each death from the stranded clients of that slot; zeta = 2
    excludes a site three times as dear; the skip rule skips sites with another own lease in its notice
    period unless every pool site would be skipped; an empty pool keeps ptr."""
    T = 24
    on = [1] * 6 + [0] * 4 + [1] * 14                     # client 0 (r0, strict): off in slots 6-9
    demand = [("r0", "strict", on), ("r1", "relaxed", [1] * T)]
    R = ([2], [6], [10])
    # S0 bought at 0, announced at 2, dead from slot 3: S = {c0, c1}, S2 infeasible for c0 -> S1.
    # S1 announced at 6, dead from slot 7: c0 off, S = {c1}, every site feasible -> S2 (after S1).
    # S2 announced at 10, dead from slot 11: S = {c0, c1} -> pool {S0, S1}, after S2 cyclically -> S0.
    inst = _three_sites(R, demand)
    pol = _LayerDriver({0: [((0, 0, 0, 0), 0, T)]}, x3=True, x2="reference", zeta=2.0, skip_rule=True)
    res = simulate(inst, pol)
    assert res.invariant_failures == []
    assert _sites_of(res) == [(0, 0), (1, 3), (2, 7), (0, 11)], _sites_of(res)
    assert pol.layer.report()["rotations"] == 3
    # pi = (0, 2, 1): after S0 the pool {S0, S1} gives S1 (S2 infeasible); after S1 with every site feasible
    # the cyclic order (0, 2, 1) wraps to S0
    pol = _LayerDriver({0: [((0, 0, 0, 0), 0, T)]}, x3=True, zeta=2.0, skip_rule=True, site_perm=np.array([0, 2, 1]))
    res = simulate(inst, pol)
    assert _sites_of(res)[:3] == [(0, 0), (1, 3), (0, 7)], _sites_of(res)
    # zeta: S1 three times as dear leaves every pool; at slot 3 the pool is {S0}: the slot stays at S0
    dear = _three_sites(R, demand, prices=(2.85, 3 * 2.85, 2.85))
    v = public_view(dear, "I1")
    L = pd_window_slots(v, 0, None)
    assert column_cost(v, 1, 0, 0, L) > 2 * column_cost(v, 0, 0, 0, L)
    pol = _LayerDriver({0: [((0, 0, 0, 0), 0, T)]}, x3=True, zeta=2.0, skip_rule=True)
    res = simulate(dear, pol)
    sites = _sites_of(res)
    assert sites[0] == (0, 0) and sites[1] == (0, 3) and all(s != 1 for s, _ in sites), sites
    pol = _LayerDriver({0: [((0, 0, 0, 0), 0, T)]}, x3=True, zeta=math.inf, skip_rule=True)
    assert _sites_of(simulate(dear, pol))[1] == (1, 3)
    # the site rule itself on hand observations (pi = identity; S = {c0, c1} unless stated)
    view = public_view(inst, "I1")
    rr = RRSiteRule(view, zeta=2.0, skip_rule=True)
    sl = LogicalSlot(key=(0, 0, 0, 0), need=np.ones(T, dtype=bool), ptr=0)
    assert rr.pool(sl, _obs(3, 2, {}), 3) == [0, 1]
    assert rr.pool(sl, _obs(3, 2, {}, demand=[0, 1]), 3) == [0, 1, 2]
    assert rr.next_site(sl, _obs(3, 2, {}), 3) == 1
    busy1 = {7: _lv(7, 1, ann=3)}                                       # another own lease at S1, announced
    assert rr.next_site(sl, _obs(3, 2, busy1), 3) == 0                   # S1 skipped: S0 (cyclically last)
    assert RRSiteRule(view, skip_rule=False).next_site(sl, _obs(3, 2, busy1), 3) == 1
    assert rr.next_site(sl, _obs(3, 2, busy1, demand=[0, 1]), 3) == 2    # pool {S0, S1, S2}: S1 skipped
    assert rr.next_site(sl, _obs(3, 2, {7: _lv(7, 1)}), 3) == 1          # unannounced: not skipped
    sl_own = LogicalSlot(key=(0, 0, 0, 0), need=np.ones(T, dtype=bool), ptr=0, lease=7)
    assert rr.next_site(sl_own, _obs(3, 2, busy1), 3) == 1               # the slot's own lease is not skipped
    every = {7: _lv(7, 1, ann=3), 8: _lv(8, 0, ann=2), 9: _lv(9, 2, ann=3)}
    assert rr.next_site(sl, _obs(3, 2, every), 3) == 1                   # all skipped: the rule is ignored
    assert rr.stats["skip_ignored"] >= 1
    rr_dear = RRSiteRule(public_view(dear, "I1"), zeta=2.0, skip_rule=True)
    assert rr_dear.pool(sl, _obs(3, 2, {}, demand=[0, 1]), 3) == [0, 2]
    sl2 = LogicalSlot(key=(2, 0, 0, 0), need=np.ones(T, dtype=bool), ptr=2)
    assert rr.pool(sl2, _obs(3, 2, {}, demand=[1, 0]), 3) == [0, 1, 2]   # S = {c1}: c0 has delta = inf at S2


def test_logical_slot_keeps_rotated_lease():
    """§7.1 (M12): after a rotation of the slot (S0, j, k, 0) to S1, the PD's next window of type (S0, ...) is
    realized by the alive lease at S1 (a renewal), with no purchase at S0."""
    T = 24
    inst = _three_sites(([1], [], []), [("r0", "strict", [1] * T)])
    opens = {0: [((0, 0, 0, 0), 0, 4)], 4: [((0, 0, 0, 0), 4, 4)], 8: [((0, 0, 0, 0), 8, 4)]}
    pol = _LayerDriver(opens, x3=True, x2="reference")
    res = simulate(inst, pol)
    assert res.invariant_failures == []
    # S0 bought at 0, announced at 1, dead from slot 2 (minute 10): rotation to S1, bought at 2
    assert _sites_of(res) == [(0, 0), (1, 2)], _sites_of(res)
    s1 = [L for L in res.leases if L.site == 1][0]
    assert s1.end_min >= 12 * 5                                     # kept through the windows [4, 8) and [8, 12)
    rep = pol.layer.report()
    assert rep["renewals"] >= 2 and rep["purchases"] == {"first": 1, "cold": 1, "prewarm": 0, "rebuy": 0, "move": 0}
    assert all(t < 2 or log[(0, 0, 0, 0)][1] == 1 for t, log in enumerate(pol.slot_log))   # ptr stays at S1


def _timer_case(demand, H_min=5):
    """One site S0 (R empty), contract (5 min, H_min), λ = 300 s, a = 2.85, q = 7.15: n_idle =
    ceil((beta~ / (g a)) 60 / Δs) = ceil(300/60 (1 + 7.15/2.85) / 5) = 4 slots."""
    T = len(demand)
    inst = _three_sites(([], [], []), [("r0", "strict", demand)], H_min=H_min, lam=300.0, T=T)
    pol = _LayerDriver({0: [((0, 0, 0, 0), 0, 2)]}, x3=True, x2="timer")
    res = simulate(inst, pol)
    assert res.invariant_failures == []
    return pol, res


def test_x2_timer_hand():
    """§7.2 step 6 (X2 'timer', M14): n_idle from beta~ / (g a); a lease with need false is idle at t iff its
    attributed load over t - 1 is 0; it is released after n_idle idle slots, not before the end of its billed
    term; attributed load resets the counter."""
    on = [1, 1] + [0] * 14
    pol, res = _timer_case(on)
    v = pol.view
    bt = float(v.beta_tilde_usd[0, 0, 0])
    assert abs(bt - 300 / 3600 * (2.85 + 7.15)) <= 1e-12
    assert pol.layer.n_idle(0, 0, 0) == math.ceil(bt / 2.85 * 60 / 5) == 4
    # need ends at 2; slot 1 served load, so t = 2 is not idle; idle at 3, 4, 5, 6: released at 6
    assert [(L.site, L.start_slot, L.end_min, L.end_cause) for L in res.leases] == [(0, 0, 30, "release")]
    # load in slot 4 resets the counter: idle at 3, 4; reset at 5 (load in 4); idle 6, 7, 8, 9: released at 9
    on2 = [1, 1, 0, 0, 1] + [0] * 11
    _, res2 = _timer_case(on2)
    assert [(L.start_slot, L.end_min) for L in res2.leases] == [(0, 45)]
    # a billed term of 35 min (H = 30): idle from 3, n_idle reached at 6, released at 7 (minute 35)
    _, res3 = _timer_case(on, H_min=30)
    assert [(L.start_slot, L.end_min) for L in res3.leases] == [(0, 35)]
    assert res3.leases[0].prepaid_end_min == 35


def test_prewarm_through_layer():
    """§7.2 steps 1-3, §10 (X4): two sites, λ' = 60 s, H = 5 min, Δf = 1, handler forced to pre-warm
    ('prewarm_if_feasible'): at the notice (r = 4, E = 25) the replacement is bought at
    latest_prewarm_slot(4, 25, 60000) = 4 at the X3 site S1, is warm at minute 21 before the old lease dies at
    25, so no load goes to fallback in the handover; at the death the pre-warmed lease becomes the slot's lease
    and nothing else is bought."""
    T = 12
    inst = _three_sites(([4], [], []), [("r0", "strict", [1] * T)], lam=60.0, fast=1, T=T)
    g = inst.grid
    assert latest_prewarm_slot(4, 25, 60_000, g) == 4
    pol = _LayerDriver({0: [((0, 0, 0, 0), 0, T)]}, handler_kw={"reaction": "prewarm_if_feasible"},
                       x3=True, x2="reference")
    res = simulate(inst, pol)
    assert res.invariant_failures == []
    assert _sites_of(res) == [(0, 0), (1, 4)], _sites_of(res)
    old, new = sorted(res.leases, key=lambda x: x.id)
    assert old.end_min == 25 and old.end_cause == "reclaim" and new.start_min == 20 and new.end_cause == "horizon"
    rep = pol.layer.report()
    assert rep["prewarm"]["decided"] == rep["prewarm"]["committed"] == 1 and rep["purchases"]["prewarm"] == 1
    assert rep["purchases"]["cold"] == 0 and rep["decisions"] == {"forced": 1}
    fb = res.per_slot["fallback"]
    assert fb[0] > 0 and np.all(fb[1:] == 0.0), fb                  # only the first load's minute
    log5 = pol.slot_log[5][(0, 0, 0, 0)]
    assert log5[0] == new.id and log5[2] is None                     # next_lease became the lease


def test_a3_rotation_adaptive():
    """C3-T4 (PROVEN): A3 with rotation (x3 on) on cm_case under the adaptive lender: every ratio engine total /
    fam.opt_dp(Fam(m, rho, 2, 1, 48), realized R) is at least LB_T - 1e-9 (r-bar 1 and theory, s = 0..3);
    the values go to ms2_checks/a3_rotation_c4a.json next to c4_lower.json's (informative: how much of the
    adaptive gap rotation recovers, E1)."""
    rows = json.loads((TC / "out" / "c4_lower.json").read_text())["a"]
    out = []
    for row in rows:
        m, rho = row["m"], row["rho"]
        I = cm_case(m, rho)
        F = fam.Fam(m, rho, 2, 1, 48)
        inst, _ = from_core(I, [np.zeros(0, np.int64)] * m)
        rec = {"m": m, "rho": rho, "LB_T": row["LB_T"], "ref": {k: row[k] for k in
                                                                ("stay", "rr", "pd_r1", "pd_r1_min", "pd_rth", "pd_rth_min")}}
        for tag, rb in (("r1", 1), ("rth", "theory")):
            vals = []
            for s in range(4):
                pol = A3(rbar=1, x3=True) if rb == 1 else A3(rbar="theory", N_bound=max(I.n * I.T, 3), x3=True)
                res = simulate(inst, pol, LenderModel(schedule="adaptive"), policy_rng=np.random.default_rng(s))
                assert res.invariant_failures == [], (m, rho, tag, s)
                R = [np.asarray(r, dtype=np.int64) for r in res.schedule.R]
                ratio = res.components["total"] / fam.opt_dp(F, R)[0]
                assert ratio >= row["LB_T"] - 1e-9, (m, rho, tag, s, ratio, row["LB_T"])
                vals.append(ratio)
            rec[f"a3_x3_{tag}"] = {"mean": float(np.mean(vals)), "min": float(np.min(vals)), "values": vals}
        out.append(rec)
    p = ms2_checks_dir() / "a3_rotation_c4a.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"description": "A3 with X3 rotation (x2 reference, reaction c2sw) on check_c4_lower "
                                            "part (a) under the adaptive lender: engine total / opt_dp(realized R)",
                             "rows": out}, indent=1) + "\n")


# ---------------------------------------------------------------- hand-driven layer (§7.2 details)
def _hobs(inst, t, *, leases=(), notices=(), ended=(), results=(), D=None):
    """SlowObs at slow slot t on a _three_sites instance (every client at demand D, default 1)."""
    n, phi = inst.n, inst.grid.phi
    dem = np.ones((n, phi)) if D is None else np.repeat(np.asarray(D, dtype=float).reshape(n, 1), phi, axis=1)
    return SlowObs(t=t, minute=t * inst.grid.slow_min, demand=dem, leases={L.id: L for L in leases},
                   replicas={}, notices=list(notices), ended=list(ended), results=list(results),
                   site_announced=None, served_prev=np.zeros((inst.J, inst.m)), fallback_prev=np.zeros(n),
                   cost_so_far=0.0)


def _hand_layer(inst, reaction="cold", **kw):
    view = public_view(inst, "I1")
    book = LeaseBook()
    layer = ExecutionLayer(view, book, handler=ReclaimHandler(view, reaction=reaction), **kw)
    return view, book, layer


def _hstep(layer, book, view, obs):
    layer.absorb(book.begin(obs))
    layer.step(obs)
    return book.assemble(obs, view)


def test_violation_death_rotates():
    """§7.2 step 2 (M13): a death with cause 'violation' (no notice) is a revocation: X3 moves the slot to the
    next pool site (S0 -> S1) and counts a revoked death; a release by the policy (X2) is no revocation and
    keeps ptr, so the re-buy for the next window is at the same site."""
    from sublet.types import ActionResult, Buy
    T = 24
    inst = _three_sites(([], [], []), [("r0", "strict", [1] * T)])
    view, book, layer = _hand_layer(inst, x3=True, x2="reference")
    layer.open((0, 0, 0, 0), t0=0, s=0, L=T)
    a0 = _hstep(layer, book, view, _hobs(inst, 0))
    assert a0 == [Buy(0, 0, 0, 1, tag="x1")]
    lv = LeaseView(7, 0, 0, 1, 0, 0, 10, None, None, ())
    assert _hstep(layer, book, view, _hobs(inst, 1, leases=[lv], results=[ActionResult(0, a0[0], True, 7, (), "")])) == []
    a2 = _hstep(layer, book, view, _hobs(inst, 2, ended=[(7, 8, "violation")]))
    assert a2 == [Buy(1, 0, 0, 1, tag="x1")]
    rep = layer.report()
    assert rep["revoked_deaths"] == 1 and rep["other_deaths"] == 0 and rep["rotations"] == 1
    assert rep["purchases"]["cold"] == 1
    # X2 release: need [0, 2), lease released at slot 2; the next window re-buys at S0 (no rotation)
    pol = _LayerDriver({0: [((0, 0, 0, 0), 0, 2)], 4: [((0, 0, 0, 0), 4, 2)]}, x3=True, x2="reference")
    res = simulate(_three_sites(([], [], []), [("r0", "strict", [1] * 8)], T=8), pol)
    assert res.invariant_failures == []
    assert [(L.site, L.start_slot, L.end_cause) for L in sorted(res.leases, key=lambda x: x.id)] == \
        [(0, 0, "release"), (0, 4, "release")]
    rep = pol.layer.report()
    assert rep["rotations"] == 0 and rep["revoked_deaths"] == 0 and rep["purchases"]["rebuy"] == 1


def test_early_death_drops_pending_prewarm():
    """§7.2 step 2: a lease that dies (violation) before the commit slot of its pre-warm drops the pending
    decision (report prewarm 'dropped'), and step 4 buys at once at the site the decision chose (S1); the
    death does not rotate ptr again (a decision moved it), and no 'prewarm' purchase follows at t_c."""
    from sublet.types import ActionResult, Buy, Notice
    T = 24
    inst = _three_sites(([], [], []), [("r0", "strict", [1] * T)])
    view, book, layer = _hand_layer(inst, reaction="prewarm_if_feasible", x3=True, x2="reference")
    layer.open((0, 0, 0, 0), t0=0, s=0, L=T)
    a0 = _hstep(layer, book, view, _hobs(inst, 0))
    lv = LeaseView(7, 0, 0, 1, 0, 0, 10, 1, 60, ())
    a1 = _hstep(layer, book, view, _hobs(inst, 1, leases=[lv], notices=[Notice(7, 1, 60)],
                                         results=[ActionResult(0, a0[0], True, 7, (), "")]))
    assert a1 == []
    sl = layer.slots[(0, 0, 0, 0)]
    assert sl.pending is not None and sl.pending.t_commit == latest_prewarm_slot(1, 60, 0, inst.grid) == 12
    assert sl.ptr == 1 and sl.ptr_moved
    a2 = _hstep(layer, book, view, _hobs(inst, 2, ended=[(7, 9, "violation")]))
    assert a2 == [Buy(1, 0, 0, 1, tag="x1")]
    rep = layer.report()
    assert rep["prewarm"]["dropped"] == 1 and rep["prewarm"]["decided"] == 1 and rep["prewarm"]["committed"] == 0
    assert rep["rotations"] == 1 and sl.pending is None
    lv2 = LeaseView(8, 1, 0, 1, 2, 10, 20, None, None, ())
    for t in range(3, 14):
        acts = _hstep(layer, book, view, _hobs(inst, t, leases=[lv2],
                                              results=[ActionResult(0, a2[0], True, 8, (), "")] if t == 3 else []))
        assert acts == [], (t, acts)


def test_prewarm_commit_needs_coverage_and_confirm():
    """§7.2 step 3: at t_commit a pre-warm is bought only if the slot needs coverage at t_commit (window [0, 5),
    t_c = 5: decided, not committed), and only if handler.confirm holds (the stranded client's demand is 0 at
    t_c: cancelled, counted; the death re-buys cold at the decision's site when demand is back)."""
    inst = _three_sites(([4], [], []), [("r0", "strict", [1] * 12)], lam=60.0, fast=1, T=12, H_min=10)
    assert latest_prewarm_slot(4, 30, 60_000, inst.grid) == 5
    pol = _LayerDriver({0: [((0, 0, 0, 0), 0, 5)]}, handler_kw={"reaction": "prewarm_if_feasible"},
                       x3=True, x2="reference")
    res = simulate(inst, pol)
    assert res.invariant_failures == []
    rep = pol.layer.report()
    assert rep["prewarm"]["decided"] == 1 and rep["prewarm"]["committed"] == 0, rep["prewarm"]
    assert not [L for L in res.leases if L.tag == "prewarm"]
    # need through the horizon, demand 0 in slot 5 = t_c: confirm fails
    on = [1] * 12
    on[5] = 0
    inst2 = _three_sites(([4], [], []), [("r0", "strict", on)], lam=60.0, fast=1, T=12, H_min=10)
    pol2 = _LayerDriver({0: [((0, 0, 0, 0), 0, 12)]}, handler_kw={"reaction": "prewarm_if_feasible"},
                        x3=True, x2="reference")
    res2 = simulate(inst2, pol2)
    assert res2.invariant_failures == []
    rep2 = pol2.layer.report()
    assert rep2["prewarm"]["decided"] == 1 and rep2["prewarm"]["cancelled"] == 1, rep2["prewarm"]
    assert rep2["prewarm"]["committed"] == 0 and pol2.handler.report()["cancelled"] == 1
    assert not [L for L in res2.leases if L.tag == "prewarm"]
    # the old lease dies at minute 30 (slot 6): a cold re-buy at the decision's site S1
    assert _sites_of(res2) == [(0, 0), (1, 6)], _sites_of(res2)
    assert rep2["purchases"]["cold"] == 1


def test_x2_reference_waits_for_billed_term():
    """§7.2 step 6, x2 = 'reference': release at the first unneeded slot t with t >= start + L_k and
    t Δs >= prepaid_end_min. Contract (tau 5 min, H 7 min): L = 1 + 7 // 5 = 2 slots but a billed term of
    12 min (prepaid_D): the lease is kept at slot 2 (minute 10 < 12) and released at slot 3 (minute 15)."""
    inst = _three_sites(([], [], []), [("r0", "strict", [1, 1] + [0] * 6)], H_min=7, T=8)
    v = public_view(inst, "I1")
    assert pd_window_slots(v, 0, None) == 2 and v.contracts[0].prepaid_min == 12
    pol = _LayerDriver({0: [((0, 0, 0, 0), 0, 2)]}, x3=True, x2="reference")
    res = simulate(inst, pol)
    assert res.invariant_failures == []
    assert [(L.start_slot, L.prepaid_end_min, L.end_min, L.end_cause) for L in res.leases] == [(0, 12, 15, "release")]


def test_move_releases_when_warm():
    """§8.3 MK1/MK2 through ExecutionLayer.move: a fresh lease at the new site is bought now and the old lease is
    released at the first slow slot in which the new replica is warm: lambda' = 420 s bought at minute 15 is
    warm in fast slot warm_fast(15, 420000, 1) = 22, slow slot 5 (Δf = 1); release='now' releases at once."""
    from sublet.timing import warm_fast
    from sublet.types import Buy, Release
    inst = _three_sites(([], [], []), [("r0", "strict", [1] * 24)], lam=420.0, fast=1)
    assert warm_fast(15, 420_000, 1) == 22
    for release, want in (("warm", [(7, 5)]), ("now", [])):
        view, book, layer = _hand_layer(inst, x3=True, x2="reference")
        layer.open((0, 0, 0, 0), t0=0, s=0, L=24)
        sl = layer.slots[(0, 0, 0, 0)]
        sl.lease, sl.lease_site = 7, 0
        lv = LeaseView(7, 0, 0, 1, 0, 0, 10, None, None, ())
        obs = _hobs(inst, 3, leases=[lv])
        book.begin(obs)
        layer.move(sl, 1, obs, 3, release)
        assert sl.retiring == want and sl.ptr == 1
        acts = book.assemble(obs, view)
        assert (Release(7) in acts) == (release == "now") and Buy(1, 0, 0, 1, tag="move") in acts
        if release == "warm":
            for t in (4, 5):                       # the retiring lease is released at its slot, not before
                o = _hobs(inst, t, leases=[lv, LeaseView(8, 1, 0, 1, 3, 15, 25, None, None, ())])
                book.begin(o)
                sl.lease, sl.buying = 8, False
                layer.step(o)
                assert (Release(7) in book.assemble(o, view)) == (t == 5), t


def test_x3_pool_zeta():
    """§7.3: X3's pool keeps the feasible sites with C <= zeta min C (zeta = 2): a site 1.5 times as dear
    stays in the pool, and leaves it with zeta = 1."""
    inst = _three_sites(([], [], []), [("r0", "strict", [1] * 24), ("r1", "relaxed", [1] * 24)],
                        prices=(2.85, 1.5 * 2.85, 2.85))
    v = public_view(inst, "I1")
    sl = LogicalSlot(key=(0, 0, 0, 0), need=np.ones(24, dtype=bool), ptr=0)
    obs = _hobs(inst, 3)
    assert RRSiteRule(v, zeta=2.0).pool(sl, obs, 3) == [0, 1]
    assert RRSiteRule(v, zeta=1.0).pool(sl, obs, 3) == [0]


def test_prewarm_replacement_announced_at_takeover():
    """§7.2 steps 1-2, §10: a pre-warmed replacement announced before or in the slot in which it takes over
    still gets a handler decision (at the takeover, with the notice period left): forced pre-warm, H = 60 min,
    lambda' = 60 s, Δf = 1. S0 is announced at slot 4 (death minute 80, slot 16), its replacement is bought at
    S1 at t_c = 15; S1 is announced at slot 16 (the takeover slot): a second pre-warm at S0 at
    latest_prewarm_slot(16, 140) = 27, no cold purchase and no fallback after slot 0. With lambda' = 600 s the
    replacement is bought at 14 and announced at 15, before the takeover at 16: a pre-warm at 25."""
    T = 40
    inst = _three_sites(([4], [16], []), [("r0", "strict", [1] * T)], H_min=60, lam=60.0, fast=1, T=T)
    assert latest_prewarm_slot(4, 80, 60_000, inst.grid) == 15 and latest_prewarm_slot(16, 140, 60_000, inst.grid) == 27
    pol = _LayerDriver({0: [((0, 0, 0, 0), 0, T)]}, handler_kw={"reaction": "prewarm_if_feasible"}, x3=True,
                       x2="reference")
    res = simulate(inst, pol)
    assert res.invariant_failures == []
    assert _sites_of(res) == [(0, 0), (1, 15), (0, 27)], _sites_of(res)
    rep = pol.layer.report()
    assert rep["decisions"] == {"forced": 2} and rep["purchases"]["prewarm"] == 2 and rep["purchases"]["cold"] == 0
    fb = res.per_slot["fallback"]
    assert fb[0] > 0 and np.all(fb[1:] == 0.0), np.nonzero(fb)[0]
    # announced before the takeover (lambda' = 600 s)
    inst2 = _three_sites(([4], [15], []), [("r0", "strict", [1] * T)], H_min=60, lam=600.0, fast=1, T=T)
    g = inst2.grid
    assert latest_prewarm_slot(4, 80, 600_000, g) == 14 and latest_prewarm_slot(16, 135, 600_000, g) == 25
    pol2 = _LayerDriver({0: [((0, 0, 0, 0), 0, T)]}, handler_kw={"reaction": "prewarm_if_feasible"}, x3=True,
                        x2="reference")
    res2 = simulate(inst2, pol2)
    assert res2.invariant_failures == []
    assert _sites_of(res2) == [(0, 0), (1, 14), (0, 25)], _sites_of(res2)
    rep2 = pol2.layer.report()
    assert rep2["decisions"] == {"forced": 2} and rep2["purchases"]["cold"] == 0
    fb2 = res2.per_slot["fallback"]
    assert np.all(fb2[2:] == 0.0), np.nonzero(fb2)[0]


def test_takeover_decision_sees_notice_at_t():
    """§7.2 steps 1-2, §10 step 4 (F1): the takeover decision on a notice that came before the takeover slot t
    uses r_slot = max(r, t), so its pre-warm commits at or after t, or it is cold ('infeasible'). Forced pre-warm,
    H = 10 min, lambda' = 420 s, Δf = 1: S0 is announced at slot 4 (death minute 30, slot 6); its replacement
    is bought at S1 at latest_prewarm_slot(4, 30) = 4 (minute 20, warm at 27); S1 is announced at slot 5
    (death minute 35), before its takeover at 6. latest_prewarm_slot(6, 35) is None (35 - 7 = 28 < 30): the
    takeover decision is 'infeasible', and S1's death at slot 7 re-buys cold at X3's next site S0 (minute 35,
    warm at 42). Fallback falls only in the two cold loads, slots 0-1 and 7-8 (5 + 2 minutes each). With the
    notice's own r = 5 the decision would get t_commit = 5 < 6 and stay pending, which blocks step 4."""
    T = 24
    inst = _three_sites(([4], [5], []), [("r0", "strict", [1] * T)], H_min=10, lam=420.0, fast=1, T=T)
    g = inst.grid
    assert latest_prewarm_slot(4, 30, 420_000, g) == 4 and latest_prewarm_slot(5, 35, 420_000, g) == 5
    assert latest_prewarm_slot(6, 35, 420_000, g) is None
    pol = _LayerDriver({0: [((0, 0, 0, 0), 0, T)]}, handler_kw={"reaction": "prewarm_if_feasible"}, x3=True,
                       x2="reference")
    res = simulate(inst, pol)
    assert res.invariant_failures == []
    assert _sites_of(res) == [(0, 0), (1, 4), (0, 7)], _sites_of(res)
    leases = sorted(res.leases, key=lambda x: x.id)
    assert [(L.start_min, L.end_min, L.end_cause) for L in leases] == \
        [(0, 30, "reclaim"), (20, 35, "reclaim"), (35, 5 * T, "horizon")], leases
    rep = pol.layer.report()
    assert rep["decisions"] == {"forced": 1, "infeasible": 1}, rep["decisions"]
    assert rep["purchases"] == {"first": 1, "cold": 1, "prewarm": 1, "rebuy": 0, "move": 0}, rep["purchases"]
    assert rep["prewarm"]["decided"] == rep["prewarm"]["committed"] == 1
    sl = pol.layer.slots[(0, 0, 0, 0)]
    assert sl.pending is None and sl.lease == leases[2].id
    fb = res.per_slot["fallback"]
    assert np.nonzero(fb)[0].tolist() == [0, 1, 7, 8], np.nonzero(fb)[0]
    assert _close(fb[7], fb[0]) and _close(fb[8], fb[1]) and _close(fb[0], 2.5 * fb[1]), fb[:9]


def test_a3_refused_window_not_retried():
    """§6.5 with §7.2 step 7 (M11): A3 on a toy with 1-GPU sites (8 units, u = 4): a purchase of a logical
    slot at its own site that the pre-check drops refuses the PD column of its window, and that window
    leaves the slot's coverage, so the slot stages no purchase for it later (unless another opened window of
    the slot covers the slot); report exec 'windows_dropped' counts them."""
    from fixtures import capped_toy_instance, purchases_in_refused_windows, refusal_recorder
    inst = capped_toy_instance()
    n_drop = 0
    for s in range(3):
        pol = A3(rbar=1)
        rec = refusal_recorder(pol)
        res = simulate(inst, pol, policy_rng=np.random.default_rng(s))
        assert res.invariant_failures == [], s
        rep = res.metrics["policy"]
        refused = rec["refused"]
        assert rep["exec"]["columns_refused"] == len(refused) and rep["exec"]["windows_dropped"] <= len(refused)
        n_drop += rep["exec"]["windows_dropped"]
        bad = purchases_in_refused_windows(rec)
        assert bad == [], (s, bad[:5])
    assert n_drop > 0
