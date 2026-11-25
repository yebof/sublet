"""Tests of the contract rules P1-P3 (design/sim_spec_ms2.md §11, §3.6; §17.2 test_contract_rules.py).

Instances are variants of configs/toy.json with a hand-made menu at the revocable site L0. Expected
masks follow §11 by hand; P2's rho and H*_beta are compared with sublet.calib and with the rows of
a11_calibration.json (as MS1's test_rho_Hstar_matches_a11_rows); P3's targets are
max(H*_mu, H*_beta) at each contract's own price, with h_star_mu of §9.2.
"""
from __future__ import annotations

import json

import numpy as np

from fixtures import site_index, toy_config

from sublet import calib
from sublet.algos.c2rule import h_star_mu
from sublet.algos.contracts import p1_mask, p2_table, p3_mask
from sublet.instance import build_instance, public_view
from sublet.paths import ANALYSIS_OUT

A11 = json.loads((ANALYSIS_OUT / "a11_calibration.json").read_text())


def _menu_instance(contracts, prices, *, billing="prepaid_D", lam=300.0, lam_prot=300.0, mu_ratio=1.0,
                   with_prot=True):
    """toy.json with the revocable site L0 offering `contracts` [(id, tau_min, H_min)] at `prices`, L1 removed,
    the protected site P (contract 'prot'; without P if with_prot is False), explicit load times."""
    cfg = toy_config(sites=["L0", "P"] if with_prot else ["L0"])
    cfg["billing"] = billing
    cfg["contracts"] = [{"id": i, "tau_min": t, "H_min": h} for i, t, h in contracts] + \
                       ([{"id": "prot", "tau_min": None, "H_min": 0, "prepaid_min": 5}] if with_prot else [])
    L0 = cfg["lenders"][0]
    L0.update({"menu": [i for i, _, _ in contracts], "prices": {i: float(prices[i]) for i, _, _ in contracts},
               "lam_s": float(lam)})
    if with_prot:
        cfg["lenders"][1].update({"lam_s": float(lam_prot)})
    cfg["stranding"]["mu_over_beta_tilde"] = float(mu_ratio)
    inst = build_instance(cfg)
    return inst, public_view(inst, "I1")


def _k(inst, cid):
    return [c.id for c in inst.contracts].index(cid)


# ---------------------------------------------------------------- P1
def test_p1_hand():
    """§11 P1 (M34): a revocable contract equal in tau, H and billed term but dearer is removed; with
    prepaid_D a longer notice prepays more, so a cheaper contract with a longer H does not dominate; with
    per_slot billing (no prepaid term) it does; a contract flagged by treated_as_protected (tau >= T_s) is
    never removed; non-offered pairs are False."""
    contracts = [("x1", 5, 5), ("x2", 5, 5), ("x3", 5, 10), ("z", 120, 0)]
    prices = {"x1": 2.85, "x2": 3.0, "x3": 2.80, "z": 9.0}
    for billing, keep in (("prepaid_D", {"x1": True, "x2": False, "x3": True, "z": True}),
                          ("per_slot", {"x1": False, "x2": False, "x3": True, "z": True})):
        inst, view = _menu_instance(contracts, prices, billing=billing)
        assert inst.grid.T_slow * inst.grid.slow_min <= 120          # z: tau >= T_s, treated as protected
        l0, lp = site_index(inst, "L0"), site_index(inst, "P")
        M = p1_mask(view)
        assert M.shape == (inst.m, inst.K)
        got = {cid: bool(M[l0, _k(inst, cid)]) for cid in keep}
        assert got == keep, (billing, got)
        assert bool(M[lp, _k(inst, "prot")]) and not M[lp, _k(inst, "x1")] and not M[l0, _k(inst, "prot")]


# ---------------------------------------------------------------- P2
def test_p2_matches_calib():
    """§11 P2: rho on the PD window L_k Δs and H*_beta on tau_k with the exact H_k, per (l, j, k), equal
    sublet.calib on the view's beta~ (exact) and the a11 rows of tier M (maas_a10, 5-min slot) at the
    maas_p99_median prices for every load scenario (1e-9)."""
    rows = A11["rows"]["maas_a10"]["M"]
    n = 0
    for sc, row in rows.items():
        cons = [(k, c["tau_min"], c["H_min"]) for k, c in A11["contracts"].items()
                if k != "protected" and c["slot_min"] == 5
                and c["price_refs"]["maas_p99_median"]["a_usd_per_gpu_h"] is not None]
        prices = {k: A11["contracts"][k]["price_refs"]["maas_p99_median"]["a_usd_per_gpu_h"] for k, _, _ in cons}
        cfg_lam = row["lambda_s"]
        inst, view = _menu_instance(cons, prices, lam=cfg_lam)
        assert view.llms[0].g == row["g"]
        l0 = site_index(inst, "L0")
        tab = p2_table(view)
        for k, tau, H in cons:
            kk = _k(inst, k)
            e = tab[(l0, 0, kk)]
            bt = float(view.beta_tilde_usd[0, l0, kk])
            c = view.contracts[kk]
            L = c.tau_slots + c.H_min // view.grid.slow_min
            assert e["rho"] == calib.rho(bt, 1, prices[k], L * view.grid.slow_min), (sc, k)
            assert e["H_star_beta_s"] == calib.H_star_beta_s(bt, 1, prices[k], 60.0 * c.tau_slots * view.grid.slow_min)
            ref = row["by_contract"][k]
            assert abs(bt - ref["beta_tilde_usd"]) <= 1e-9 * max(1.0, ref["beta_tilde_usd"]), (sc, k)
            assert abs(e["rho"] - ref["rho"]) <= 1e-9 * max(1.0, ref["rho"]), (sc, k, e["rho"], ref["rho"])
            assert abs(e["H_star_beta_s"] - ref["H_star_beta_s"]) <= 1e-9 * max(1.0, abs(ref["H_star_beta_s"])), (sc, k)
            n += 1
    assert n > 0


# ---------------------------------------------------------------- P3
def _targets(view, inst, l, kk):
    lp, kp = site_index(inst, "P"), _k(inst, "prot")
    hm = h_star_mu(view, 0, l, kk, l_prot=lp, k_prot=kp, rep_site=l)
    hm_s = np.inf if (hm["value_s"] is None or hm["status"] in ("NA-Cprime", "NA-alpha>=1")) else hm["value_s"]
    c = view.contracts[kk]
    hb = calib.H_star_beta_s(float(view.beta_tilde_usd[0, l, kk]), view.llms[0].g, float(view.price[l, kk]),
                             60.0 * c.tau_slots * view.grid.slow_min)
    return max(hm_s, hb), hm


def test_p3_hand():
    """§11 P3 (M35): among the tau = 1 slot contracts of a site P3 keeps the smallest H whose 60 H reaches
    max(H*_mu, H*_beta) at its own price, else the largest H; a contract with g_j a >= q_j has h_star_mu
    status 'NA-alpha>=1' and never reaches its target; contracts of other tau classes are untouched."""
    Hs = (0, 2, 5, 15, 60)
    contracts = [(f"h{h}", 5, h) for h in Hs] + [("hot", 5, 240), ("t60", 60, 5)]
    prices = {**{f"h{h}": 2.85 for h in Hs}, "hot": 7.5, "t60": 3.2}
    # lambda = 300 s: H*_beta = beta~/(g a) - tau = 752.6 s, reached first by H = 15 min
    inst, view = _menu_instance(contracts, prices, lam=300.0)
    l0 = site_index(inst, "L0")
    hot = _k(inst, "hot")
    t, hm = _targets(view, inst, l0, hot)
    assert hm["status"] == "NA-alpha>=1" and hm["value_s"] is None and np.isinf(t)
    M = p3_mask(view, p1_mask(view))
    assert M.shape == (inst.m, inst.J, inst.K)
    reach = {h: 60.0 * h >= _targets(view, inst, l0, _k(inst, f"h{h}"))[0] for h in Hs}
    want = min(h for h in Hs if reach[h])
    assert want == 15, reach
    got = {cid: bool(M[l0, 0, _k(inst, cid)]) for cid, _, _ in contracts}
    assert got == {**{f"h{h}": h == want for h in Hs}, "hot": False, "t60": True}, got
    # lambda = 3000 s: no notice of the menu reaches H*_beta (about 170 min): keep the largest H
    inst2, view2 = _menu_instance(contracts, prices, lam=3000.0)
    l0 = site_index(inst2, "L0")
    assert not any(60.0 * h >= _targets(view2, inst2, l0, _k(inst2, f"h{h}"))[0] for h in Hs)
    M2 = p3_mask(view2, p1_mask(view2))
    got2 = {cid: bool(M2[l0, 0, _k(inst2, cid)]) for cid, _, _ in contracts}
    assert got2 == {**{f"h{h}": False for h in Hs}, "hot": True, "t60": True}, got2



def test_p3_protected_choice():
    """§11 P3 (M35): H*_mu uses the cheapest reachable protected contract (status VERIFIED or CONJECTURE with
    switch c2sw) and the RRL thresholds without one (status 'RRL'). With lambda = 30 s and mu = 2 beta~ the
    H*_mu part binds (H*_beta < 0); its target equals c2_thresholds(units).Hstar beta~ / q 3600 s recomputed from
    the C2 units, and the kept notice is the smallest H that reaches it, in both menus."""
    from sublet.algos.c2rule import c2_thresholds, c2_units
    from sublet.algos.contracts import p3_targets
    Hs = (0, 1, 2, 5, 15, 60)
    contracts = [(f"h{h}", 5, h) for h in Hs]
    prices = {f"h{h}": 2.85 for h in Hs}
    kept = {}
    for with_prot in (True, False):
        inst, view = _menu_instance(contracts, prices, lam=30.0, lam_prot=30.0, mu_ratio=2.0, with_prot=with_prot)
        l0 = site_index(inst, "L0")
        lp = site_index(inst, "P") if with_prot else None
        kp = _k(inst, "prot") if with_prot else None
        q = view.llms[0].q_usd_per_h
        reach, binds = {}, 0
        for h in Hs:
            k = _k(inst, f"h{h}")
            tg = p3_targets(view, 0, l0, k)
            u = c2_units(view, 0, l0, k, l_prot=lp, k_prot=kp, rep_site=l0)
            th = c2_thresholds(u.alpha, u.ap, u.mu, u.lam, 1.0, u.bw)
            want_mu = th.Hstar * u.beta_tilde_usd / q * 3600.0
            assert abs(tg["H_star_mu_s"] - want_mu) <= 1e-9 * want_mu, (with_prot, h, tg, want_mu)
            if with_prot:
                assert tg["H_star_mu_status"] in ("VERIFIED", "CONJECTURE"), (h, tg)
            else:
                assert tg["H_star_mu_status"] == "RRL" and u.ap is None, (h, tg)
            binds += tg["H_star_mu_s"] > tg["H_star_beta_s"]
            assert tg["target_s"] == max(tg["H_star_mu_s"], tg["H_star_beta_s"])
            reach[h] = 60.0 * h >= tg["target_s"]
            assert tg["reaches"] == reach[h]
        assert binds == len(Hs)
        ok = [h for h in Hs if reach[h]]
        M = p3_mask(view, p1_mask(view))
        got = {h: bool(M[l0, 0, _k(inst, f"h{h}")]) for h in Hs}
        assert got == {h: (h == ok[0]) if ok else (h == Hs[-1]) for h in Hs}, (with_prot, got, reach)
        kept[with_prot] = [h for h in Hs if got[h]]
    assert kept[True] and kept[False]


def test_p3_na_cprime_is_unreachable():
    """§11 P3 (M59): an H*_mu with status 'NA-Cprime' counts as infinite: every tau = 1 slot contract at price 5.0
    (alpha = 0.70, alpha_p <= alpha (2 - alpha): (C') fails) misses its target, so P3 keeps the largest H."""
    from sublet.algos.contracts import p3_targets
    Hs = (0, 2, 5, 15, 60)
    inst, view = _menu_instance([(f"h{h}", 5, h) for h in Hs], {f"h{h}": 5.0 for h in Hs}, lam=300.0)
    l0 = site_index(inst, "L0")
    st = {h: p3_targets(view, 0, l0, _k(inst, f"h{h}")) for h in Hs}
    assert all(t["H_star_mu_status"].startswith("NA-Cprime") and np.isinf(t["H_star_mu_s"]) for t in st.values()), st
    hm = h_star_mu(view, 0, l0, _k(inst, "h15"), l_prot=site_index(inst, "P"), k_prot=_k(inst, "prot"), rep_site=l0)
    assert hm["value_s"] is not None and 60.0 * 15 >= max(hm["value_s"], st[15]["H_star_beta_s"])   # finite: reached
    M = p3_mask(view, p1_mask(view))
    assert {h: bool(M[l0, 0, _k(inst, f"h{h}")]) for h in Hs} == {h: h == 60 for h in Hs}
