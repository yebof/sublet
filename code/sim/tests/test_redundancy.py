"""Tests of the redundancy rule (design/sim_spec_ms2.md §12; §17.2 test_redundancy.py).

§3 gives no interface for algos/redundancy.py; the tests use the module's functions `lam_min_s`,
`is_exposed`, `spare_needed` and the class `RedundancyRule(view, mode=..., nu_per_day=...)` with
`step(obs, book, slots)`, `on_results(pairs)` and `report()`, driven by hand-made observations on
configs/toy.json (contract 'short' with H = 2 min, load times 300 s, so lambda_min = 300 s; L0 and
L1 in different correlation groups) and stand-in logical slots (key, lease, ptr, pool).
"""
from __future__ import annotations

import json
from types import SimpleNamespace

import numpy as np

from fixtures import site_index, toy_instance

from sublet.algos.common import LeaseBook
from sublet.algos.redundancy import RedundancyRule, default_nu_per_day, is_exposed, lam_min_s, spare_needed
from sublet.instance import public_view
from sublet.paths import ANALYSIS_OUT
from sublet.types import ActionResult, Buy, LeaseView, Release, ReplicaView, SlowObs

A5B = json.loads((ANALYSIS_OUT / "a5b_exposure_thresholds.json").read_text())
SLOW = 5


def _setup():
    inst = toy_instance({"contracts.0.H_min": 2, "lenders.0.lam_s": 300.0, "lenders.1.lam_s": 300.0,
                         "lenders.2.lam_s": 600.0})
    view = public_view(inst, "I1")
    ids = [c.id for c in inst.contracts]
    return inst, view, site_index(inst, "L0"), site_index(inst, "L1"), site_index(inst, "P"), ids.index("short"), \
        ids.index("long"), ids.index("prot")


def _lease(lid, site, k, start, prepaid_end=None, announce=None):
    return LeaseView(id=lid, site=site, contract=k, gpus=1, start_slot=start, start_min=start * SLOW,
                     prepaid_end_min=start * SLOW + 10 if prepaid_end is None else prepaid_end,
                     announce_slot=announce, death_min=None, replicas=(lid * 10,))


def _obs(inst, t, leases, results=()):
    reps = [ReplicaView(id=L.id * 10, lease_id=L.id, llm=0, state="warm", load_start_min=0, warm_fast=0,
                        admission=1.0, drain_min=None) for L in leases]
    return SlowObs(t=t, minute=t * SLOW, demand=np.ones((inst.n, inst.grid.phi)), leases={L.id: L for L in leases},
                   replicas={r.id: r for r in reps}, notices=[], ended=[], results=list(results),
                   site_announced=None, served_prev=np.zeros((inst.J, inst.m)), fallback_prev=np.zeros(inst.n),
                   cost_so_far=0.0)


def _slots(n, l0, l1, k, first_id=100):
    return [SimpleNamespace(key=(l0, 0, k, i), lease=first_id + i, ptr=l0, pool=(l0, l1)) for i in range(n)]


def _step(rule, inst, view, t, leases, slots, results=(), book=None):
    book = book or LeaseBook()
    obs = _obs(inst, t, leases, results)
    rule.on_results(book.begin(obs))
    rule.step(obs, book, slots)
    return book.assemble(obs, view), book


# ---------------------------------------------------------------- exposure
def test_exposure_hand():
    """§12 (M36): a lease is exposed iff alive, revocable, past tau_k (t >= start + tau_k) and
    60 H_k < lambda_min(P) = min over the pool of lam_s[j, l]; the rule counts n_exp per slot."""
    inst, view, l0, l1, lp, short, long_, prot = _setup()
    assert lam_min_s(view, 0, (l0, l1)) == 300.0 and lam_min_s(view, 0, (l0, l1, lp)) == 300.0
    assert lam_min_s(view, 0, (lp,)) == 600.0
    lam = 300.0
    L = _lease(1, l0, short, start=2)                 # tau = 1 slot, H = 2 min < 5 min
    assert not is_exposed(view, L, 2, lam)            # inside its guaranteed period
    assert is_exposed(view, L, 3, lam) and is_exposed(view, L, 9, lam)
    assert not is_exposed(view, _lease(2, l0, long_, start=0), 9, lam)      # H = 10 min >= lambda_min / 60
    assert is_exposed(view, _lease(2, l0, long_, start=0), 9, 601.0)         # 600 s < 601 s
    assert not is_exposed(view, _lease(3, lp, prot, start=0), 9, lam)       # protected
    rule = RedundancyRule(view, mode="off")
    leases = [_lease(100 + i, l0, short, start=0) for i in range(3)] + [_lease(103, l0, long_, start=0)]
    slots = _slots(3, l0, l1, short) + [SimpleNamespace(key=(l0, 0, long_, 0), lease=103, ptr=l0, pool=(l0, l1))]
    acts, _ = _step(rule, inst, view, 4, leases, slots)
    assert acts == []
    rep = rule.report()
    assert rep["n_exp"][4] == 3 and rep["groups_with_spare"][4] == 0


# ---------------------------------------------------------------- threshold
def test_spare_threshold():
    """§12 (M37): at alpha = 0.3986 (L0's 'short' at a0 = 2.85), nu = 3.571 per day
    (a5b `spare_threshold.nu_per_day_used`) and lambda_min = 300 s a spare appears iff n_exp >= 33
    (a5b `n_exp_threshold` 32.14), at the other correlation group's site L1, with its non-exposed
    contract 'long' (60 H = 600 s >= lambda_min)."""
    inst, view, l0, l1, lp, short, long_, prot = _setup()
    st = A5B["spare_threshold"]
    nu = default_nu_per_day()
    assert nu == st["nu_per_day_used"] and st["lambda_s"] == 300.0
    alpha = view.llms[0].g * float(view.price[l0, short]) / view.llms[0].q_usd_per_h
    assert abs(alpha - A5B["inputs"]["alpha"]) <= 1e-12
    assert abs(alpha / (nu * 300.0 / 86400.0) - st["n_exp_threshold"]) <= 1e-9 * st["n_exp_threshold"]
    assert not spare_needed("rule", 32, alpha, nu, 300.0) and spare_needed("rule", 33, alpha, nu, 300.0)
    assert view.sites[l0].group != view.sites[l1].group
    for n, want in ((32, []), (33, [Buy(l1, long_, 0, 1, tag="spare", admission=1.0)])):
        rule = RedundancyRule(view, mode="rule")
        leases = [_lease(100 + i, l0, short, start=0) for i in range(n)]
        acts, _ = _step(rule, inst, view, 3, leases, _slots(n, l0, l1, short))
        assert [a for a in acts if isinstance(a, Buy)] == want, (n, acts)
        assert rule.report()["n_exp"][3] == n


# ---------------------------------------------------------------- modes and release
def test_modes():
    """§12: 'always2' buys a spare for one exposed replica, 'off' never; the spare goes to another
    correlation group; once the condition fails it is released at the first slot at or after its billed
    term, not before."""
    inst, view, l0, l1, lp, short, long_, prot = _setup()
    one = [_lease(100, l0, short, start=0)]
    for mode, n, want in (("always2", 1, 1), ("off", 33, 0), ("rule", 1, 0)):
        rule = RedundancyRule(view, mode=mode)
        leases = [_lease(100 + i, l0, short, start=0) for i in range(n)]
        acts, _ = _step(rule, inst, view, 3, leases, _slots(n, l0, l1, short))
        spares = [a for a in acts if isinstance(a, Buy) and a.tag == "spare"]
        assert len(spares) == want, (mode, acts)
        assert all(a.site == l1 for a in spares)
    # release: spare bought at slot 3 ('long': D = 20 min, prepaid to minute 35); the exposed lease is gone
    rule = RedundancyRule(view, mode="always2")
    acts, book = _step(rule, inst, view, 3, one, _slots(1, l0, l1, short))
    i, b = next((i, a) for i, a in enumerate(acts) if isinstance(a, Buy))
    spare = _lease(500, b.site, b.contract, start=3, prepaid_end=3 * SLOW + 20)
    res = [ActionResult(index=i, action=b, ok=True, lease_id=500, replica_ids=(5000,), reason="")]
    acts, book = _step(rule, inst, view, 4, [spare], _slots(1, l0, l1, short, first_id=900), res, book)
    assert acts == []                                          # condition failed, still inside the billed term
    for t in (5, 6):
        acts, book = _step(rule, inst, view, t, [spare], [], (), book)
        assert acts == [], t
    acts, book = _step(rule, inst, view, 7, [spare], [], (), book)      # 7 * 5 = 35 >= prepaid end
    assert acts == [Release(500)]
    rep = rule.report()
    assert rep["buys"] == 1 and rep["releases"] == 1


# ---------------------------------------------------------------- spare site, contract, alpha and re-buy
def test_choose_spare():
    """§12: the spare site minimizes the column cost per guaranteed hour C / (L_k Δs / 60) (not C), ties by pi;
    at that site a non-exposed contract (60 H >= lambda_min) is preferred even when an exposed one is cheaper
    per hour; the site of the majority correlation group is skipped."""
    from sublet.algos.common import pd_window_slots
    from sublet.types import INF
    inst, view, l0, l1, lp, short, long_, prot = _setup()
    L = np.array([pd_window_slots(view, k, None) for k in range(inst.K)])
    assert L[short] == 1 and L[long_] == 4
    pi = np.arange(inst.m)
    from sublet.algos.redundancy import choose_spare
    C = np.full((inst.m, 1, inst.K), INF)
    C[l1, 0, short], C[l1, 0, long_] = 0.1, 10.0          # 'short' (60 H = 120 s < 600 s) far cheaper per hour
    assert choose_spare(view, 0, (l1,), None, 600.0, L, C, pi) == (l1, long_)
    assert choose_spare(view, 0, (l1,), None, 60.0, L, C, pi) == (l1, short)    # both safe: the cheaper per hour
    C2 = np.full((inst.m, 1, inst.K), INF)
    C2[l0, 0, short], C2[l1, 0, long_] = 1.0, 1.5         # per hour: 1.0 / (5/60) = 12 at L0, 1.5 / (20/60) = 4.5 at L1
    assert choose_spare(view, 0, (l0, l1), None, 0.0, L, C2, pi) == (l1, long_)
    assert choose_spare(view, 0, (l0, l1), view.sites[l1].group, 0.0, L, C2, pi) == (l0, short)
    C3 = np.full((inst.m, 1, inst.K), INF)
    C3[l0, 0, short], C3[l1, 0, short] = 1.0, 1.0         # tie: pi decides
    assert choose_spare(view, 0, (l0, l1), None, 0.0, L, C3, np.array([l1, l0, lp])) == (l1, short)
    assert choose_spare(view, 0, (l0, l1), None, 0.0, L, C3, pi) == (l0, short)


def test_dead_spare_rebought():
    """§12: a spare that dies is re-bought at the next slot while the condition holds ('always2')."""
    inst, view, l0, l1, lp, short, long_, prot = _setup()
    rule = RedundancyRule(view, mode="always2")
    one = [_lease(100, l0, short, start=0)]
    acts, book = _step(rule, inst, view, 3, one, _slots(1, l0, l1, short))
    i, b = next((i, a) for i, a in enumerate(acts) if isinstance(a, Buy))
    spare = _lease(500, b.site, b.contract, start=3, prepaid_end=3 * SLOW + 20)
    res = [ActionResult(index=i, action=b, ok=True, lease_id=500, replica_ids=(5000,), reason="")]
    acts, book = _step(rule, inst, view, 4, one + [spare], _slots(1, l0, l1, short), res, book)
    assert not [a for a in acts if isinstance(a, Buy)]
    acts, book = _step(rule, inst, view, 5, one, _slots(1, l0, l1, short), (), book)      # the spare died
    assert [a for a in acts if isinstance(a, Buy) and a.tag == "spare"] == [b], acts
    assert rule.report()["buys"] == 2


def test_alpha_at_cheapest_exposed():
    """§12: alpha = g a / q at the cheapest price among the group's exposed leases: with exposed leases at L0
    'short' (2.85, alpha 0.3986) and L1 'short' (2.9, alpha 0.4056) and nu = 58 per day the threshold
    n_exp nu lambda / 86400 = 2 x 58 x 300 / 86400 = 0.4028 lies between them, so a spare is bought."""
    inst, view, l0, l1, lp, short, long_, prot = _setup()
    q = view.llms[0].q_usd_per_h
    a0, a1 = float(view.price[l0, short]) / q, float(view.price[l1, short]) / q
    thr = 2 * 58.0 * 300.0 / 86400.0
    assert a0 < thr < a1
    rule = RedundancyRule(view, mode="rule", nu_per_day=58.0)
    leases = [_lease(100, l0, short, start=0), _lease(101, l1, short, start=0)]
    slots = [SimpleNamespace(key=(l0, 0, short, 0), lease=100, ptr=l0, pool=(l0, l1)),
             SimpleNamespace(key=(l0, 0, short, 1), lease=101, ptr=l1, pool=(l0, l1))]
    acts, _ = _step(rule, inst, view, 3, leases, slots)
    assert [a for a in acts if isinstance(a, Buy) and a.tag == "spare"], acts
    rule1 = RedundancyRule(view, mode="rule", nu_per_day=58.0)
    acts1, _ = _step(rule1, inst, view, 3, leases[1:], slots[1:])            # one exposed lease at 0.4056 > 0.2014
    assert not [a for a in acts1 if isinstance(a, Buy)]
