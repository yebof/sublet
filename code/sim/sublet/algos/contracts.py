"""Contract rules P1-P4 (design/sim_spec_ms2.md §11; design §1.6, §3.2.5).

Functions of the PublicView only. A6 applies P1 and P3 as the PD's candidate mask at reset (menus
and prices are static in the simulator); A2-A5 use no rule.
  P1 (p1_mask, M34)  menu: drop a revocable contract dominated at its site in price, tau, H and
                     billed term; contracts flagged by common.treated_as_protected are never dropped.
  P2 (p2_table)      exposure: rho on the PD's slot-rounded window and H*_beta, per (l, j, k).
  P3 (p3_mask, M35)  notice to buy: per (site, LLM, tau) the smallest H with 60 H >= max(H*_mu, H*_beta),
                     else the largest H.
  P4                 price floor: lender-side (the builder prices revocable contracts at a0/(1 - b)
                     and drops b >= 1); no platform rule.
Status: P3 is a design rule (Q10); its H*_mu part is not proven at the default switch cost (Q17),
and C2's tau = 0 threshold at tau_k = 1 slot is an approximation.

MS5b addition (design/sublet_v2.md §8.1, C37): c2_contract_table, A9.3's table of base contracts, billed
terms, usable sites and C2-T2 insurance flags (algos/a9.py).
"""
from __future__ import annotations

from typing import Optional

import numpy as np

from .. import calib
from ..types import INF, PublicView
from . import c2rule
from .common import PolicyError, pd_window_slots, treated_as_protected


def _offered(view: PublicView, l: int, k: int) -> bool:
    return int(k) in view.sites[l].menu and bool(np.isfinite(view.price[l, k]))


def p1_mask(view: PublicView, *, ignore_notice: bool = False) -> np.ndarray:
    """(m, K) bool: (l, k) offered and not dominated (P1, M34). At site l a revocable contract k' (not
    flagged by treated_as_protected) is dropped iff another offered revocable contract k at l has
    a_lk <= a_lk', tau_k >= tau_k', H_k >= H_k' and P_k <= P_k', at least one strictly. With
    ignore_notice every H_k is read as 0 (BL6's notice-oblivious A6, §14)."""
    m, K = np.asarray(view.price).shape
    mask = np.zeros((m, K), dtype=bool)
    for l, site in enumerate(view.sites):
        offered = sorted(int(k) for k in site.menu if np.isfinite(view.price[l, k]))
        mask[l, offered] = True
        rev = [k for k in offered if not treated_as_protected(view, k)]

        def key(k):
            c = view.contracts[k]
            return (float(view.price[l, k]), int(c.tau_slots), 0 if ignore_notice else int(c.H_min),
                    int(c.prepaid_min))

        for k2 in rev:
            a2, t2, h2, p2 = key(k2)
            for k in rev:
                if k == k2:
                    continue
                a, t, h, p = key(k)
                if a <= a2 and t >= t2 and h >= h2 and p <= p2 and (a < a2 or t > t2 or h > h2 or p < p2):
                    mask[l, k2] = False
                    break
    return mask


def p2_table(view: PublicView, protected_window: Optional[int] = None) -> dict:
    """Exposure per offered (l, j, k) (P2): {(l, j, k): {'rho', 'H_star_beta_s', 'L_slots',
    'beta_tilde_usd'}} with rho = calib.rho(beta~, g_j, a_lk, L_k Δs) on the PD window L_k
    (common.pd_window_slots) and H*_beta = calib.H_star_beta_s(beta~, g_j, a_lk, 60 tau_k Δs) in
    seconds. A Contract.protected contract has rho = 1 and H*_beta None (a11's convention). rho uses
    the slot-rounded window, H*_beta the exact H_k, so rho <= 2 implies H_k >= H*_beta, and the
    converse holds when H_k is a multiple of Δs."""
    slow = view.grid.slow_min
    m, K = np.asarray(view.price).shape
    L = [pd_window_slots(view, k, protected_window) for k in range(K)]
    out = {}
    for l in range(m):
        for k in range(K):
            if not _offered(view, l, k):
                continue
            c = view.contracts[k]
            a = float(view.price[l, k])
            for j, LLM in enumerate(view.llms):
                bt = float(view.beta_tilde_usd[j, l, k])
                if c.protected:
                    rho, hb = 1.0, None
                else:
                    rho = calib.rho(bt, LLM.g, a, L[k] * slow)
                    hb = calib.H_star_beta_s(bt, LLM.g, a, 60.0 * c.tau_slots * slow)
                out[(l, j, k)] = {"rho": rho, "H_star_beta_s": hb, "L_slots": int(L[k]), "beta_tilde_usd": bt}
    return out


def protected_for_site(view: PublicView, j: int, l: int) -> Optional[tuple[int, int]]:
    """(l_p, k_p) of P3: the cheapest contract flagged by treated_as_protected at a site with
    delta_cl_p < inf for some client c of LLM j with delta_cl < inf; None if there is none (RRL)."""
    delta = np.asarray(view.client_delta_usd_per_h, dtype=np.float64)
    cl = [int(c) for c in np.flatnonzero(np.asarray(view.client_llm) == j) if np.isfinite(delta[c, l])]
    return c2rule.cheapest_protected(view, j, cl)


def p3_targets(view: PublicView, j: int, l: int, k: int, *, switch: str = "c2sw") -> dict:
    """Notice target of P3 for (l, j, k) at the contract's own price, in seconds: H*_mu (h_star_mu with
    rep_site = l and the protected contract of protected_for_site; INF for status 'NA-Cprime' or
    'NA-alpha>=1', M59), H*_beta, their maximum, and whether 60 H_k reaches it."""
    prot = protected_for_site(view, j, l)
    hm = c2rule.h_star_mu(view, j, l, k, l_prot=None if prot is None else prot[0],
                          k_prot=None if prot is None else prot[1], rep_site=l, switch=switch)
    st = hm["status"]
    hm_s = float("inf") if (hm["value_s"] is None or st.startswith("NA-")) else float(hm["value_s"])
    c = view.contracts[k]
    bt = float(view.beta_tilde_usd[j, l, k])
    hb_s = calib.H_star_beta_s(bt, view.llms[j].g, float(view.price[l, k]), 60.0 * c.tau_slots * view.grid.slow_min)
    target = max(hm_s, hb_s)
    return {"H_star_mu_s": hm_s, "H_star_mu_status": st, "H_star_beta_s": hb_s, "target_s": target,
            "reaches": 60.0 * c.H_min >= target}


def p3_mask(view: PublicView, mask: np.ndarray, *, switch: str = "c2sw") -> np.ndarray:
    """(m, J, K) bool (P3, M35). `mask` is P1's (m, K) mask (or an (m, J, K) mask). For each site l,
    LLM j and guaranteed period tau whose revocable contracts left in the mask have several notices:
    keep the contracts with the smallest H_k whose own target (p3_targets) is reached; if none
    reaches its target, keep those with the largest H_k. Other tau classes and contracts flagged by
    treated_as_protected are untouched."""
    mask = np.asarray(mask, dtype=bool)
    m, K = np.asarray(view.price).shape
    J = len(view.llms)
    if mask.shape == (m, K):
        M = np.repeat(mask[:, None, :], J, axis=1)
    elif mask.shape == (m, J, K):
        M = mask.copy()
    else:
        raise ValueError(f"p3_mask: mask has shape {mask.shape}, expected {(m, K)} or {(m, J, K)}")
    for l in range(m):
        for j in range(J):
            groups: dict[int, list[int]] = {}
            for k in range(K):
                if M[l, j, k] and not treated_as_protected(view, k):
                    groups.setdefault(int(view.contracts[k].tau_slots), []).append(k)
            for ks in groups.values():
                Hs = sorted({int(view.contracts[k].H_min) for k in ks})
                if len(Hs) < 2:
                    continue
                reach = {k: p3_targets(view, j, l, k, switch=switch)["reaches"] for k in ks}
                ok = [h for h in Hs if any(reach[k] for k in ks if view.contracts[k].H_min == h)]
                if ok:
                    keep = {k for k in ks if view.contracts[k].H_min == ok[0] and reach[k]}
                else:
                    keep = {k for k in ks if view.contracts[k].H_min == Hs[-1]}
                for k in ks:
                    if k not in keep:
                        M[l, j, k] = False
    return M


def c2_contract_table(view: PublicView, insure: bool = True) -> dict:
    """A9.3's contract table (design/sublet_v2.md §2.2 A9.3; §8.1, C37), a function of the PublicView only.

    Rev(l) holds the contracts offered at site l with a finite price that common.treated_as_protected does not
    flag and that P1 keeps (p1_mask); P3(l, j) = {k in Rev(l): p3_mask(view, p1_mask)[l, j, k]} (switch c2sw).
    The base contract is kbar(l, j) = argmin over P3(l, j) of (a_lk, P_k, -H_k, k), the key of the baselines'
    k*; -1 where Rev(l) is empty (P3(l, j) is never empty when Rev(l) is not, since P3 keeps a notice of every
    tau class). Billed term b_k = max(P_k, D_k) minutes for a revocable contract, P_k for a flagged one. Site l is
    usable for client c (LLM j) iff delta_cl < inf, kbar(l, j) >= 0 and sigma_cl = g_j a_{l kbar} + delta_cl < q_j;
    l0_c is c's usable site of least sigma (ties by site id). Insurance (C2-T2): k_p(l) is the cheapest flagged
    contract offered at l by (price, P_k, k), and l_p the usable flagged site of least sigma^p_cl = g_j a_{l k_p(l)}
    + delta_cl < q_j (ties by site id). With `insure`, a client with both l0 and l_p is insured iff
    c2rule.insure_up_front(c2rule.c2_units(view, j, l0, kbar(l0, j), l_prot=l_p, k_prot=k_p(l_p), rep_site=l0),
    'lb_react'); a PolicyError counts as not insured, and a client without l0 or l_p is not insured. Without
    `insure` the test is not evaluated and no client is insured.

    Returns {'kbar': (m, J) int64, 'b_min': (K,) float64, 'rev': (m, K) bool, 'p3': (m, J, K) bool, 'kp': (m,)
    int64 (-1: none), 'sigma': (n, m) float64 (INF where not usable), 'usable': (n, m) bool, 'l0': (n,) int64,
    'sigma_p': (n, m) float64 (INF where not a usable flagged site), 'lp': (n,) int64, 'insured': (n,) bool,
    'c2': per client None (no test) or {'alpha', 'ap', 'insure'} or {'error'}}.

    Status: P3 is a design rule (module docstring); C2-T2's ratio is PROVEN in C2's single-site model for
    insurance held to the end of the demand, its use per client with several sites is HEURISTIC, and 'lb_react'
    is a grid value (c2rule.cr_react_lb)."""
    price = np.asarray(view.price, dtype=np.float64)
    m, K = price.shape
    J, slow = len(view.llms), view.grid.slow_min
    cl = np.asarray(view.client_llm, dtype=np.int64)
    n = len(cl)
    delta = np.asarray(view.client_delta_usd_per_h, dtype=np.float64)
    g = np.array([x.g for x in view.llms], dtype=np.float64)
    q = np.array([x.q_usd_per_h for x in view.llms], dtype=np.float64)
    flagged = np.array([treated_as_protected(view, k) for k in range(K)], dtype=bool)
    b_min = np.array([float(c.prepaid_min) if flagged[k] else float(max(c.prepaid_min, c.D_min(slow)))
                      for k, c in enumerate(view.contracts)], dtype=np.float64)
    p1 = p1_mask(view)
    rev = p1 & ~flagged[None, :]
    p3 = p3_mask(view, p1) & rev[:, None, :]
    kbar = np.full((m, J), -1, dtype=np.int64)
    for l in range(m):
        for j in range(J):
            ks = [int(k) for k in np.flatnonzero(p3[l, j])]
            if ks:
                kbar[l, j] = min(ks, key=lambda k: (float(price[l, k]), int(view.contracts[k].prepaid_min),
                                                    -int(view.contracts[k].H_min), k))
    kp = np.full(m, -1, dtype=np.int64)
    for l, site in enumerate(view.sites):
        ks = [int(k) for k in site.menu if flagged[k] and np.isfinite(price[l, k])]
        if ks:
            kp[l] = min(ks, key=lambda k: (float(price[l, k]), int(view.contracts[k].prepaid_min), k))
    sigma = np.full((n, m), INF)
    sigma_p = np.full((n, m), INF)
    for c in range(n):
        j = int(cl[c])
        for l in range(m):
            if not np.isfinite(delta[c, l]):
                continue
            if kbar[l, j] >= 0:
                s = g[j] * price[l, kbar[l, j]] + delta[c, l]
                if s < q[j]:
                    sigma[c, l] = s
            if kp[l] >= 0:
                s = g[j] * price[l, kp[l]] + delta[c, l]
                if s < q[j]:
                    sigma_p[c, l] = s
    usable = np.isfinite(sigma)
    l0 = np.array([int(np.argmin(sigma[c])) if usable[c].any() else -1 for c in range(n)], dtype=np.int64)
    lp = np.array([int(np.argmin(sigma_p[c])) if np.isfinite(sigma_p[c]).any() else -1 for c in range(n)],
                  dtype=np.int64)
    insured = np.zeros(n, dtype=bool)
    tests: list = [None] * n
    if insure:
        for c in range(n):
            if l0[c] < 0 or lp[c] < 0:
                continue
            j, a, p = int(cl[c]), int(l0[c]), int(lp[c])
            try:
                u = c2rule.c2_units(view, j, a, int(kbar[a, j]), l_prot=p, k_prot=int(kp[p]), rep_site=a)
                ins = bool(c2rule.insure_up_front(u, "lb_react"))
                tests[c] = {"alpha": float(u.alpha), "ap": float(u.ap), "insure": ins}
            except PolicyError as e:
                ins = False
                tests[c] = {"error": str(e)}
            insured[c] = ins
    return {"kbar": kbar, "b_min": b_min, "rev": rev, "p3": p3, "kp": kp, "sigma": sigma, "usable": usable, "l0": l0,
            "sigma_p": sigma_p, "lp": lp, "insured": insured, "c2": tests}


__all__ = ["p1_mask", "p2_table", "p3_mask", "p3_targets", "protected_for_site", "c2_contract_table"]
