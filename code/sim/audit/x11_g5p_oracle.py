"""X11: LB'(t), W_k(t) and B(t) from an oracle written from C3 §9's definition, against the built allowance
(sublet/algos/online_lb.py), x10's lb_prime and the prototype.

Claim and source. design/theory/c3_c4_c5_general.md §9, 'Per-group allowance': the groups (G-i)-(G-iii), the
full-model and core forms of LB', Lemma G5'(a) (LB', W_k and B = min{W_k, LB'} are nonnegative, nondecreasing and
non-anticipative), 'Relation to the prototype' (under (i)-(iii) the prototype computes LB'; outside them each of its
three differences raises its value) and 'The pilot's instance of U' (W_k); online_lb.py's module docstring (OnlineLB
computes the definition exactly and online). The audit addendum of step P6 (design/sublet_v2.md §5) in
design/theory/audit_guard.md: the verdicts on the two forms of LB', on G5'(a) and on online_lb.py, the first two rows
of its 'Adversarial attempts', and finding G5P-F7 (check_g5p.py takes its groups from the prototype). The auditors'
scratch scripts behind those rows are moved here (open item 1 of the addendum).

Oracles. Two oracles of LB', written from the text separately from each other and independently of online_lb.py, of
x10_g5p_pathwise.lb_prime and of the prototype sublet/experiments/ms5b_proto/lb.py:
  oracle_uf    groups by union-find per LLM over client and site nodes (a component without a site is no group);
               zeta_k, theta_jl = ceil(round(1000 Lambda_jl) / (60000 Delta_f)), Lambda-bar_jl = min{Lambda_jl / 60,
               theta_jl Delta_f}, r_Gamma and hat-beta as defined; capacitated: Xi_nu(t) = nu hat-beta + Delta_f/60
               sum_{f <= f_t} min_{0 <= n <= nu} h_f(n), with the minimum over n and over nu in 0..ceil(max d) + 3 by
               brute force (not the closed form n°); uncapacitated: min{Delta_f/60 sum q d, hat-beta + Delta_f/60 sum
               min(r, q d)}. exact=True does the same arithmetic in fractions.Fraction on the float64 inputs.
  oracle_edge  groups by union-find over integer nodes (client c; site node n + j m + l of LLM j); the minimum over
               nu in 0..ceil(max_{f <= f_t} d) + 2 recomputed from scratch at every slow slot.
W_k is checked against the formula of 'The pilot's instance of U' on oracle_uf's groups, with the baselines' k*(l)
(baselines.common.k_star) and PublicView.beta_tilde_usd.

(a) 4000 random full-model instances (rand_instance: configs/toy.json with time grids of slow slot 5 or 10 min and
    fast slot dividing it, 1-3 LLMs with g in {1, 2, 3}, 1-7 clients, routing costs infinite, >= q or below q (groups
    split by routing costs), prices with some rents above q, prepaid terms not multiples of the fast slot, load times
    in and next to the half-millisecond corner, loading charges >= 0, kappa_infinite in 40%). Per instance:
    online_lb.series, x10's lb_prime and oracle_uf agree to 1e-12 relative (max(1, |LB'|)); W_k equals the formula
    (bit equality counted, 1e-12 relative required); B = min{W_k, LB'} bit for bit; LB', W_k and B nondecreasing
    and >= 0; non-anticipation: the series through slot t = T/2 are bit-equal when the demand after t is replaced;
    conditions (i)-(iii) of 'Relation to the prototype' recomputed from oracle_uf's groups equal
    online_lb.conditions; under (i)-(iii) the prototype (run_proj.inst_dict, lb.lb_series) equals oracle_uf to 1e-12
    relative, and outside them it is never below it (by more than 1e-9 relative). The first 60 instances: oracle_uf
    in float64 equals its exact Fraction variant to 1e-12 relative. 200 random core instances
    (theory_checks/c3/core.Instance, exported with instance.from_core, no announcements): online_lb.series equals the
    core form of C3 §9 (per group min{sum q n_Gamma, min beta + sum min(r, q n_Gamma)}, r = min g a over the group's
    sites and contracts) to 1e-12 relative.
(b) 400 edge-case instances (rand_instance_edge, on the three sites of configs/toy.json: prepaid terms 0, a fast
    slot, not a multiple of it; exact ties q (d - floor d) = r; r >= q; Lambda^ms = 0 with Lambda > 0 (the corner at
    0) and Lambda just above whole fast slots; two LLMs sharing sites; clients without a usable arc; kappa_infinite in
    35%): online_lb.series equals oracle_edge to 1e-12 relative; oracle_uf and x10's lb_prime equal oracle_edge too.
    The output counts the instances with each edge case.

Usage: x11_g5p_oracle.py [n_a] [n_b] [--reduced]   (default 4000 and 400 instances, about 20 s on one worker;
--reduced: 400 and 40). Audit addendum of step P6; code/sim/audit/, run by run_all.sh (step x11), output
code/sim/out/audit_fm/x11_out.txt. Exit status 1 on a mismatch beyond 1e-12 relative or a failed property (B, W_k,
monotonicity, non-anticipation, conditions, the prototype under or outside (i)-(iii), the core form), or on an
instance that raises."""
import dataclasses
import json
import math
import sys
import time
import traceback
from collections import Counter
from fractions import Fraction

import numpy as np

import audit_env  # noqa: F401
from audit_env import SIM
import core  # noqa: E402  (code/theory_checks/c3, on sys.path through audit_env)
import x10_g5p_pathwise as X10
from sublet.algos import online_lb as OL
from sublet.baselines.common import k_star
from sublet.instance import build_instance, from_core, public_view, validate
from sublet.types import INF, LLM, Clients, Contract, Stranding, TimeGrid

PROTO = SIM / "sublet" / "experiments" / "ms5b_proto"
if str(PROTO) not in sys.path:
    sys.path.insert(0, str(PROTO))
import run_proj as RP  # noqa: E402  (prototype copy; inserts its own folder and code/sim)
import lb as PL  # noqa: E402  (prototype copy)

REL = 1e-12            # agreement of two computations of the same value, relative to max(1, |value|)
PROTO_BELOW = 1e-9     # the prototype is "below" LB' outside (i)-(iii) iff by more than this, relative
N_EXACT, N_CORE = 60, 200


def rel(a, b) -> float:
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    if not (np.all(np.isfinite(a)) and np.all(np.isfinite(b))):
        return float("inf")             # a non-finite value never passes a tolerance
    return float(np.max(np.abs(a - b) / np.maximum(1.0, np.abs(b)))) if b.size else 0.0


# ================================================================ oracle_uf (with an exact variant)
def comps_uf(n, m, cl, ok, J):
    """Groups per LLM by union-find over ('c', c) and ('s', l) nodes: [(j, clients, sites)], components with a site."""
    out = []
    for j in range(J):
        cs = [c for c in range(n) if cl[c] == j]
        parent = {}

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x
        for c in cs:
            parent[("c", c)] = ("c", c)
            for l in range(m):
                if ok[c, l]:
                    parent.setdefault(("s", l), ("s", l))
        for c in cs:
            for l in range(m):
                if ok[c, l]:
                    a, b = find(("c", c)), find(("s", l))
                    if a != b:
                        parent[a] = b
        grp = {}
        for x in parent:
            grp.setdefault(find(x), []).append(x)
        for v in grp.values():
            C = sorted(y[1] for y in v if y[0] == "c")
            S = sorted(y[1] for y in v if y[0] == "s")
            if S:
                out.append((j, C, S))
    return out


def oracle_uf(inst, exact=False):
    """(LB'(t) for t = 0..T_slow-1, per-group info) from C3 §9's full-model form, brute force over n and nu
    (module docstring). exact=True: Fraction arithmetic on the float64 inputs."""
    g = inst.grid
    Df, phi, Ts = int(g.fast_min), int(g.phi), int(g.T_slow)
    F = (lambda x: Fraction(x)) if exact else (lambda x: float(x))
    q = [F(x.q_usd_per_h) for x in inst.llms]
    gj = [int(x.g) for x in inst.llms]
    n, m, J = inst.n, inst.m, inst.J
    cl = [int(x) for x in inst.clients.llm]
    dl = np.asarray(inst.clients.delta_usd_per_h, dtype=float)
    ok = np.zeros((n, m), dtype=bool)
    for c in range(n):
        for l in range(m):
            ok[c, l] = math.isfinite(dl[c, l]) and F(dl[c, l]) < q[cl[c]]
    lam = np.asarray(inst.lam_s, dtype=float)
    D = np.asarray(inst.clients.demand, dtype=float)
    LB = [F(0)] * Ts
    info = []
    for j, C, S in comps_uf(n, m, cl, ok, J):
        def zeta(k):
            P = int(inst.contracts[k].prepaid_min)
            if P == 0:
                return F(1)
            return F(Fraction(P, -(-P // Df) * Df)) if exact else P / (-(-P // Df) * Df)
        r = min(zeta(k) * gj[j] * F(inst.price[l, k]) for l in S for k in inst.sites[l].menu)
        lbars, corner = [], False
        for l in S:
            lms = int(np.round(1000.0 * lam[j, l]))
            th = -(-lms // (60000 * Df))
            lbars.append(min(F(lam[j, l]) / 60, F(th * Df)))
            corner |= lms % (60000 * Df) == 0 and 1000.0 * lam[j, l] > lms
        bhat = min(F(inst.beta_usd[j, l]) for l in S) + r * min(lbars) / 60
        dG = [sum((F(D[c, f]) for c in C), F(0)) for f in range(D.shape[1])]
        qj = q[j]
        if inst.kappa_infinite:
            A0 = F(0)
            A1 = bhat
            for t in range(Ts):
                for f in range(t * phi, (t + 1) * phi):
                    A0 += qj * dG[f] * Df / 60
                    A1 += min(r, qj * dG[f]) * Df / 60
                LB[t] += min(A0, A1)
        else:
            top = int(math.ceil(max(float(x) for x in dG))) + 3 if dG else 3
            S_nu = [F(0)] * (top + 1)
            for t in range(Ts):
                for f in range(t * phi, (t + 1) * phi):
                    h = [nn * r + qj * max(dG[f] - nn, F(0)) for nn in range(top + 1)]
                    run = h[0]
                    for nu in range(top + 1):
                        run = min(run, h[nu])
                        S_nu[nu] += run * Df / 60
                LB[t] += min(nu * bhat + S_nu[nu] for nu in range(top + 1))
        info.append(dict(j=j, C=C, S=S, r=r, q=qj, bhat=bhat, corner=corner))
    return LB, info


def conditions_uf(inst, info):
    """Conditions (i)-(iii) of C3 §9's 'Relation to the prototype' from oracle_uf's groups: (i) kappa_infinite false
    or no group with r >= q_j; (ii) Delta_f divides every offered P_k (finite price at some site's menu); (iii) no
    load time of a group's LLM at a group site in the half-millisecond corner."""
    Df = int(inst.grid.fast_min)
    c1 = (not inst.kappa_infinite) or all(gi["r"] < gi["q"] for gi in info)
    offered = {int(k) for l, s in enumerate(inst.sites) for k in s.menu if np.isfinite(inst.price[l, k])}
    c2 = all(int(inst.contracts[k].prepaid_min) % Df == 0 for k in offered)
    c3 = not any(gi["corner"] for gi in info)
    return {"i": bool(c1), "ii": bool(c2), "iii": bool(c3)}


def wk_oracle(inst, view, info):
    """W_k(t) of 'The pilot's instance of U': per group with a k*(l) site, p_Gamma ceil(peak - 1e-9), p_Gamma = min
    over those sites of beta~_{j l k*} + g_j a_{l k*} P_{k*} / 60, peak the running maximum of d_Gamma."""
    ks = k_star(view)
    phi = inst.grid.phi
    D = np.asarray(inst.clients.demand, dtype=float)
    out = np.zeros(inst.grid.T_slow)
    for gi in info:
        j, C, S = gi["j"], gi["C"], gi["S"]
        ps = [float(view.beta_tilde_usd[j, l, ks[l]]) + inst.llms[j].g * float(view.price[l, ks[l]])
              * inst.contracts[ks[l]].prepaid_min / 60.0 for l in S if ks[l] >= 0]
        if not ps:
            continue
        dG = D[C].sum(axis=0)
        peak = np.maximum.accumulate(dG)[phi - 1::phi]
        out += min(ps) * np.ceil(peak - 1e-9)
    return out


def core_form(I):
    """LB'(t) of C3 §9's core form on a core.Instance (requests = active[c, t])."""
    n, m, J = I.n, I.m, I.J
    ok = np.isfinite(I.delta) & (I.delta < I.q)
    LB = np.zeros(int(I.T))
    for j, C, S in comps_uf(n, m, list(I.cl_llm), ok, J):
        r = min(float(I.g[j]) * float(I.a[l, k]) for l in S for k in range(I.K))
        b = min(float(I.beta[j, l]) for l in S)
        nG = I.active[C].sum(axis=0).astype(float)
        LB += np.minimum(np.cumsum(I.q * nG), b + np.cumsum(np.minimum(r, I.q * nG)))
    return LB


def rand_instance(seed, corner_prob=0.4, allow_kinf=True):
    """A random full-model instance from configs/toy.json (part (a) of the module docstring)."""
    rng = np.random.default_rng(seed)
    cfg = json.load(open(SIM / "configs" / "toy.json"))
    slow = int(rng.choice([5, 10]))
    fast = int(rng.choice([d for d in (1, 2, 5, 10) if slow % d == 0]))
    T_slow = int(rng.integers(4, 16))
    cfg["time"] = {"slow_slot_min": slow, "fast_slot_min": fast, "horizon_min": slow * T_slow,
                   "start_minute_of_week": 0}
    cfg["billing"] = str(rng.choice(["prepaid_D", "per_slot", "commit_tau"]))
    cfg["contracts"] = [{"id": "short", "tau_min": slow, "H_min": int(rng.choice([0, 1, 2, 3, 7]))},
                        {"id": "long", "tau_min": 2 * slow, "H_min": int(rng.choice([0, 4, 10, 13]))},
                        {"id": "prot", "tau_min": None, "H_min": 0, "prepaid_min": int(rng.choice([slow, 7, 3]))}]
    J = int(rng.choice([1, 2, 3]))
    base = cfg["llms"][0]
    cfg["llms"] = [{**base, "id": f"M{j}" if j else "M", "g": int(rng.choice([1, 2, 3]))} for j in range(J)]
    n = int(rng.integers(1, 8))
    phi = slow // fast
    Tf = T_slow * phi
    clients = []
    for c in range(n):
        lev = rng.choice([0.0, 0.2, 0.5, 1.0, 1.3, 2.0, 2.7, 4.1], size=Tf)
        dem = lev * rng.uniform(0.6, 1.4, size=Tf) * (rng.random(Tf) < 0.8)
        clients.append({"llm": cfg["llms"][int(rng.integers(J))]["id"], "region": "r0", "slo_class": "strict",
                        "borrowers": [f"b{c}"], "demand": {"kind": "array", "values": [float(x) for x in dem]}})
    cfg["borrowers"] = {"model": "explicit", "clients": clients}
    for e in cfg["lenders"]:
        if e["kind"] == "synthetic":
            e["capacity_gpus"] = 512
            e["R"] = sorted(set(int(x) for x in rng.integers(0, T_slow, size=int(rng.integers(0, 4)))))
    cfg["stranding"]["mu_over_beta_tilde"] = float(rng.choice([0.0, 0.5]))
    kinf = allow_kinf and bool(rng.random() < 0.4)
    if kinf:
        for x in cfg["llms"]:
            x["kappa_wtok_per_min"] = "inf"
        cfg["costs"]["kappa_infinite"] = True
    inst = build_instance(cfg)
    m = inst.m
    qv = np.array([x.q_usd_per_h for x in inst.llms])
    cl = np.asarray(inst.clients.llm)
    dl = np.empty((n, m))
    for c in range(n):
        for l in range(m):
            u = rng.random()
            dl[c, l] = (np.inf if u < 0.2 else qv[cl[c]] * rng.uniform(1.0, 1.4) if u < 0.3
                        else qv[cl[c]] * rng.choice([0.0, 0.05, 0.3, 0.7, 0.99]))
    price = np.array(inst.price, dtype=float, copy=True)
    fin = np.isfinite(price)
    gmax = max(x.g for x in inst.llms)
    price[fin] = rng.uniform(0.1, 1.6, size=fin.sum()) * float(qv.min()) / gmax
    lam = np.round(rng.uniform(0, 700, size=(J, m)), 3)
    near = rng.random((J, m)) < corner_prob
    k = rng.integers(0, 4, size=(J, m))
    off = rng.choice([-0.0004, 0.0001, 0.0003, 0.0004, 0.00049, 0.0005, 0.0006], size=(J, m))
    lam = np.maximum(np.where(near, 60.0 * fast * k + off, lam), 0.0)
    beta = rng.choice([0.0, 0.01, 0.2, 1.5], size=(J, m)) * (rng.random((J, m)) < 0.8)
    cs = []
    for ct in inst.contracts:
        P = int(ct.prepaid_min)
        if rng.random() < 0.5:
            P = int(rng.choice([0, 1, 2, 3, 4, 6, 7, 9, 11, 13]))
        cs.append(dataclasses.replace(ct, prepaid_min=P))
    llms = tuple(dataclasses.replace(x, q_usd_per_h=float(x.q_usd_per_h * rng.uniform(0.5, 1.5))) for x in inst.llms)
    out = dataclasses.replace(inst, price=price, lam_s=lam, beta_usd=beta, contracts=tuple(cs), llms=llms,
                              clients=dataclasses.replace(inst.clients, delta_usd_per_h=dl))
    validate(out)
    return out


def rand_core(seed):
    """A random core.Instance (part (a)'s core-form check)."""
    rng = np.random.default_rng(50000 + seed)
    m, K, J, n, T = (int(rng.integers(1, 4)), int(rng.integers(1, 3)), int(rng.integers(1, 3)),
                     int(rng.integers(1, 6)), int(rng.integers(3, 12)))
    tau = rng.integers(1, 4, size=K)
    H = rng.integers(0, 3, size=K)
    a = rng.uniform(0.1, 3.0, size=(m, K))
    beta = rng.uniform(0.1, 5.0, size=(J, m))
    g = rng.integers(1, 3, size=J)
    q = float(rng.uniform(1.0, 6.0))
    cl = rng.integers(0, J, size=n)
    delta = np.where(rng.random((n, m)) < 0.3, np.inf, rng.uniform(0, 1.3 * q, size=(n, m)))
    active = rng.random((n, T)) < 0.6
    return core.Instance(T=T, tau=tau, H=H, a=a, beta=beta, g=g, q=q, cl_llm=cl, delta=delta, active=active)


# ================================================================ oracle_edge and the edge-case instances
BASE = build_instance(str(SIM / "configs" / "toy.json"))


def oracle_edge(inst):
    """(T_slow,) LB'(t) from C3 §9's full-model form, written separately from oracle_uf (module docstring)."""
    g = inst.grid
    Df, phi, T = g.fast_min, g.phi, g.T_slow
    J, m, n = len(inst.llms), len(inst.sites), inst.clients.n
    q = np.array([x.q_usd_per_h for x in inst.llms])
    gj = np.array([x.g for x in inst.llms])
    cl = inst.clients.llm
    dl = inst.clients.delta_usd_per_h
    usable = np.isfinite(dl) & (dl < q[cl][:, None])
    par = list(range(n + m * J))

    def f(x):
        while par[x] != x:
            par[x] = par[par[x]]
            x = par[x]
        return x
    for c in range(n):
        for l in range(m):
            if usable[c, l]:
                a, b = f(c), f(n + cl[c] * m + l)
                par[a] = b
    comps = {}
    for c in range(n):
        if usable[c].any():
            comps.setdefault(f(c), [cl[c], set(), set()])
            comps[f(c)][1].add(c)
    for c in range(n):
        for l in range(m):
            if usable[c, l]:
                comps[f(c)][2].add(l)
    zeta = []
    for ct in inst.contracts:
        P = ct.prepaid_min
        zeta.append(1.0 if P == 0 else P / (math.ceil(P / Df) * Df))
    lms = np.round(1000.0 * inst.lam_s).astype(np.int64)
    total = np.zeros(T)
    for j, C, S in comps.values():
        j = int(j)
        r = min(zeta[k] * gj[j] * inst.price[l, k] for l in S for k in inst.sites[l].menu)
        lbar = min(min(inst.lam_s[j, l] / 60.0, math.ceil(lms[j, l] / (60000 * Df)) * Df) for l in S)
        hb = min(inst.beta_usd[j, l] for l in S) + r * lbar / 60.0
        d = inst.clients.demand[sorted(C)].sum(axis=0)
        for t in range(T):
            dd = d[:(t + 1) * phi]
            if inst.kappa_infinite:
                v = min(Df / 60 * np.sum(q[j] * dd), hb + Df / 60 * np.sum(np.minimum(r, q[j] * dd)))
            else:
                Vmax = int(math.ceil(dd.max())) + 2 if len(dd) else 2
                best = math.inf
                for nu in range(Vmax + 1):
                    s = nu * hb
                    for x in dd:
                        s += Df / 60 * min(nn * r + q[j] * max(x - nn, 0.0) for nn in range(nu + 1))
                    best = min(best, s)
                v = best
            total[t] += v
    return total


def rand_instance_edge(rng):
    """An edge-case instance on configs/toy.json's three sites (part (b) of the module docstring)."""
    slow, fast = [(5, 5), (5, 1), (10, 5), (10, 2), (6, 3), (12, 4)][rng.integers(6)]
    T = int(rng.integers(4, 13))
    phi = slow // fast
    Tf = T * phi
    J = int(rng.integers(1, 3))
    gs = [int(rng.integers(1, 4)) for _ in range(J)]
    qs = [float(rng.choice([6.0, 10.0, 30.0, 60.0])) * g for g in gs]
    llms = tuple(LLM(f"j{j}", "M", gs[j], 10.0, 1e6, 0.3, 20.0, qs[j]) for j in range(J))

    def P():
        return int(rng.choice([0, fast, 2 * fast, 7, slow, 3 * slow, 11]))
    contracts = (Contract("short", 1, int(rng.choice([0, fast, slow])), P(), "general"),
                 Contract("long", 2, int(rng.choice([0, slow])), P(), "general"),
                 Contract("prot", None, 0, P(), "protected"))
    m = 3
    sites = []
    for l, s in enumerate(BASE.sites):
        R = None
        if s.kind != "protected":
            R = np.unique(rng.integers(0, T, size=int(rng.integers(0, 4)))).astype(np.int64)
        sites.append(dataclasses.replace(s, capacity_gpus=INF, R_explicit=R))
    price = np.full((m, 3), INF)
    for l in range(2):
        for k in (0, 1):
            price[l, k] = float(rng.choice([1.0, 2.0, 3.0, 5.0, 12.0, 40.0]))
    price[2, 2] = float(rng.choice([2.0, 6.0, 15.0]))
    lam = np.zeros((J, m))            # load times: zero, the corner at 0, just above whole fast slots, whole, generic
    for j in range(J):
        for l in range(m):
            c = rng.integers(5)
            if c == 0:
                lam[j, l] = 0.0
            elif c == 1:
                lam[j, l] = 0.0004
            elif c == 2:
                lam[j, l] = 60.0 * fast * int(rng.integers(1, 3)) + 0.0003
            elif c == 3:
                lam[j, l] = 60.0 * fast * int(rng.integers(1, 3))
            else:
                lam[j, l] = float(rng.uniform(1, 400))
    beta = np.round(rng.uniform(0, 3, size=(J, m)), 2) * (rng.random((J, m)) < 0.7)
    n = int(rng.integers(1, 6))
    cl = rng.integers(0, J, size=n).astype(np.int64)
    delta = np.zeros((n, m))
    for c in range(n):
        q = qs[cl[c]]
        for l in range(m):
            u = rng.random()
            delta[c, l] = INF if u < 0.25 else (q * rng.uniform(1.0, 1.4) if u < 0.4 else q * rng.uniform(0, 0.6))
    dem = rng.choice([0.0, 0.5, 1.0, 1.25, 2.0, 2.5, 3.0], size=(n, Tf)) * (rng.random((n, Tf)) < 0.8)
    clients = Clients(llm=cl, region=("r0",) * n, slo_class=("strict",) * n, borrowers=(("b0",),) * n,
                      delta_usd_per_h=delta, demand=dem)
    st = Stranding(rng.uniform(0, 1, J) * (rng.random(J) < 0.5), rng.uniform(0, 1, J) * (rng.random(J) < 0.5),
                   rng.uniform(0, 1, J) * (rng.random(J) < 0.5), rng.uniform(0, 0.1, J) * (rng.random(J) < 0.5),
                   float(rng.uniform(0, 3)))
    if rng.random() < 0.4:      # clean: routing 0 or infeasible, no stranding, no loading charge
        delta = np.where(np.isfinite(delta) & (delta < np.array(qs)[cl][:, None]), 0.0, INF)
        clients = dataclasses.replace(clients, delta_usd_per_h=delta)
        z0 = np.zeros(J)
        st = Stranding(z0, z0.copy(), z0.copy(), z0.copy(), 0.0)
        beta = np.zeros((J, m))
    inst = dataclasses.replace(BASE, grid=TimeGrid(slow, fast, T, 0), contracts=contracts, llms=llms,
                               sites=tuple(sites), price=price, lam_s=lam, beta_usd=beta, clients=clients,
                               stranding=st, kappa_infinite=bool(rng.random() < 0.35),
                               load_scenario=("explicit",) * m)
    validate(inst)
    return inst


def edge_features(inst, info, st):
    """Coverage counts of part (b), from oracle_uf's groups."""
    Df, J = int(inst.grid.fast_min), inst.J
    offered = {int(k) for l, s in enumerate(inst.sites) for k in s.menu if np.isfinite(inst.price[l, k])}
    P = [int(inst.contracts[k].prepaid_min) for k in offered]
    st["b: an offered P_k = 0"] += int(any(p == 0 for p in P))
    st["b: an offered P_k not a multiple of Delta_f"] += int(any(p % Df for p in P))
    D = np.asarray(inst.clients.demand, dtype=float)
    tie = big = False
    for gi in info:
        d = D[gi["C"]].sum(axis=0)
        tie |= bool(np.any(gi["q"] * (d - np.floor(d)) == gi["r"]))
        big |= gi["r"] >= gi["q"]
    st["b: a tie q (d - floor d) = r"] += int(tie)
    st["b: a group with r >= q"] += int(big)
    lam = np.asarray(inst.lam_s, dtype=float)
    lms = np.round(1000.0 * lam).astype(np.int64)
    st["b: the corner at 0 at a group site"] += int(any(lms[gi["j"], l] == 0 and lam[gi["j"], l] > 0
                                                        for gi in info for l in gi["S"]))
    st["b: a load-time corner at a group site"] += int(any(gi["corner"] for gi in info))
    sites_of = [set(l for gi in info if gi["j"] == j for l in gi["S"]) for j in range(J)]
    st["b: two LLMs with groups sharing a site"] += int(J >= 2 and bool(sites_of[0] & sites_of[1]))
    grouped = set(c for gi in info for c in gi["C"])
    st["b: a client without a usable arc"] += int(len(grouped) < inst.n)
    st["b: kappa_infinite"] += int(inst.kappa_infinite)


# ================================================================ parts
def guarded(part, fn, s, errors):
    """fn(s), with an exception recorded as an error of the audit (the instance cannot be checked)."""
    try:
        fn(s)
    except Exception as e:
        errors.append((part, s, f"{type(e).__name__}: {e}", traceback.format_exc(limit=4)))


def part_a(s, st, worst, bad):
    inst = rand_instance(10000 + s)
    view = public_view(inst, "I1")
    lb_or, info = oracle_uf(inst)
    lb_or = np.array(lb_or, dtype=float)
    ser = OL.series(view, inst.clients.demand)
    lb_x10, _ = X10.lb_prime(inst)
    e_ol, e_x10 = rel(ser["LB"], lb_or), rel(lb_x10, lb_or)
    worst["a: online_lb vs oracle_uf"] = max(worst["a: online_lb vs oracle_uf"], e_ol)
    worst["a: x10 lb_prime vs oracle_uf"] = max(worst["a: x10 lb_prime vs oracle_uf"], e_x10)
    if e_ol > REL:
        bad.append(("a: online_lb != oracle_uf", s, e_ol))
    if e_x10 > REL:
        bad.append(("a: x10 lb_prime != oracle_uf", s, e_x10))
    wk = wk_oracle(inst, view, info)
    e_wk = rel(ser["Wk"], wk)
    worst["a: W_k vs formula"] = max(worst["a: W_k vs formula"], e_wk)
    st["a: W_k entries not bit-equal to the formula"] += int(np.sum(ser["Wk"] != wk))
    if e_wk > REL:
        bad.append(("a: W_k != formula", s, e_wk))
    if np.any(ser["B"] != np.minimum(ser["Wk"], ser["LB"])):
        bad.append(("a: B != min{W_k, LB'} bit for bit", s, None))
    for key in ("LB", "Wk", "B"):
        if np.any(np.diff(ser[key]) < 0) or np.any(ser[key] < 0):
            bad.append((f"a: {key} decreases or is negative", s, None))
    Ts, phi = inst.grid.T_slow, inst.grid.phi
    t = Ts // 2
    dem = np.array(inst.clients.demand, dtype=float, copy=True)
    dem[:, (t + 1) * phi:] = 7.0 * np.random.default_rng(s).random(dem[:, (t + 1) * phi:].shape)
    ser2 = OL.series(view, dem)
    if any(np.any(ser2[k][:t + 1] != ser[k][:t + 1]) for k in ("LB", "Wk", "B")):
        bad.append(("a: anticipates (series through T/2 change with later demand)", s, None))
    cond = OL.conditions(view)
    cu = conditions_uf(inst, info)
    if any(cu[k] != cond[k] for k in ("i", "ii", "iii")):
        bad.append(("a: conditions (i)-(iii) differ from online_lb.conditions", s, (cu, cond)))
    lb_pr, _, _ = PL.lb_series(RP.inst_dict(inst, view))
    e_pr = rel(lb_pr, lb_or)
    if cu["i"] and cu["ii"] and cu["iii"]:
        st["a: (i)-(iii) hold"] += 1
        worst["a: prototype vs oracle_uf under (i)-(iii)"] = max(
            worst["a: prototype vs oracle_uf under (i)-(iii)"], e_pr)
        if e_pr > REL:
            bad.append(("a: prototype != LB' under (i)-(iii)", s, e_pr))
    else:
        st["a: (i)-(iii) fail"] += 1
        st["a: prototype differs outside (i)-(iii)"] += int(e_pr > REL)
        if np.any(lb_pr < lb_or - PROTO_BELOW * np.maximum(1.0, lb_or)):
            bad.append(("a: prototype below LB' outside (i)-(iii)", s, None))
    st["a: instances"] += 1
    st["a: kappa_infinite"] += int(inst.kappa_infinite)
    st["a: at least 2 groups"] += int(len(info) >= 2)
    st["a: a load-time corner at a group site ((iii) fails)"] += int(not cu["iii"])
    st["a: Delta_f not dividing an offered P_k ((ii) fails, zeta < 1)"] += int(not cu["ii"])
    st["a: kappa_infinite with a group r >= q ((i) fails)"] += int(not cu["i"])


def part_a_exact(s, st, worst, bad):
    inst = rand_instance(10000 + s)
    a = np.array(oracle_uf(inst)[0], dtype=float)
    b = np.array([float(x) for x in oracle_uf(inst, exact=True)[0]])
    e = rel(a, b)
    worst["a: oracle_uf float64 vs exact"] = max(worst["a: oracle_uf float64 vs exact"], e)
    if e > REL:
        bad.append(("a: oracle_uf float64 != exact", s, e))
    st["a: exact instances"] += 1


def part_a_core(s, st, worst, bad):
    I = rand_core(s)
    inst, _ = from_core(I, [np.zeros(0, dtype=int)] * I.m)
    ser = OL.series(public_view(inst, "I1"), inst.clients.demand)
    e = rel(ser["LB"], core_form(I))
    worst["a: from_core online_lb vs core form"] = max(worst["a: from_core online_lb vs core form"], e)
    if e > REL:
        bad.append(("a: from_core online_lb != core form", s, e))
    st["a: core instances"] += 1


def part_b(s, st, worst, bad):
    inst = rand_instance_edge(np.random.default_rng(1000 + s))
    ref = oracle_edge(inst)
    ser = OL.series(public_view(inst, "I1"), inst.clients.demand)
    lb_uf, info = oracle_uf(inst)
    for key, v in (("online_lb", ser["LB"]), ("oracle_uf", np.array(lb_uf, dtype=float)),
                   ("x10 lb_prime", X10.lb_prime(inst)[0])):
        e = rel(v, ref)
        worst[f"b: {key} vs oracle_edge"] = max(worst[f"b: {key} vs oracle_edge"], e)
        if e > REL:
            bad.append((f"b: {key} != oracle_edge", s, e))
    edge_features(inst, info, st)
    st["b: instances"] += 1


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    reduced = "--reduced" in sys.argv
    n_a = int(args[0]) if args else (400 if reduced else 4000)
    n_b = int(args[1]) if len(args) > 1 else (40 if reduced else 400)
    t0 = time.time()
    st, worst, bad, errors = Counter(), Counter(), [], []
    for name, n, fn in (("a", n_a, lambda s: part_a(s, st, worst, bad)),
                        ("a exact", N_EXACT, lambda s: part_a_exact(s, st, worst, bad)),
                        ("a core", N_CORE, lambda s: part_a_core(s, st, worst, bad)),
                        ("b", n_b, lambda s: part_b(s, st, worst, bad))):
        for s in range(n):
            guarded(name, fn, s, errors)
    wall = time.time() - t0
    L = ["X11: LB'(t), W_k(t) and B(t) against oracles written from the definition "
         "(design/theory/c3_c4_c5_general.md §9, 'Per-group allowance', Lemma G5'(a), 'Relation to the prototype'; "
         "audit addendum of step P6 in design/theory/audit_guard.md)",
         "oracles: oracle_uf (union-find groups, brute-force minima, an exact Fraction variant) and oracle_edge "
         "(written separately), against sublet/algos/online_lb.py, x10_g5p_pathwise.lb_prime and the prototype "
         "sublet/experiments/ms5b_proto/lb.py; script code/sim/audit/x11_g5p_oracle.py",
         f"instances: (a) {st['a: instances']} of {n_a}, exact {st['a: exact instances']}, core "
         f"{st['a: core instances']}; (b) {st['b: instances']} of {n_b} ({'reduced' if reduced else 'default'}); "
         f"wall time {wall:.0f} s on one worker",
         f"tolerance: agreement to {REL:g} relative (max(1, |value|)); B, monotonicity and non-anticipation bit for "
         f"bit; prototype below LB' outside (i)-(iii) iff by more than {PROTO_BELOW:g} relative", ""]
    L.append("(a) random full-model instances:")
    for k in ("a: instances", "a: kappa_infinite", "a: at least 2 groups",
              "a: a load-time corner at a group site ((iii) fails)",
              "a: Delta_f not dividing an offered P_k ((ii) fails, zeta < 1)",
              "a: kappa_infinite with a group r >= q ((i) fails)", "a: (i)-(iii) hold", "a: (i)-(iii) fail",
              "a: prototype differs outside (i)-(iii)", "a: W_k entries not bit-equal to the formula"):
        L.append(f"  {k[3:]}: {st[k]}")
    L.append("  max relative differences:")
    for k in ("a: online_lb vs oracle_uf", "a: x10 lb_prime vs oracle_uf", "a: W_k vs formula",
              "a: prototype vs oracle_uf under (i)-(iii)", "a: oracle_uf float64 vs exact",
              "a: from_core online_lb vs core form"):
        L.append(f"    {k[3:]}: {worst[k]:.6e}")
    L.append("(b) edge-case instances:")
    for k in ("b: instances", "b: kappa_infinite", "b: an offered P_k = 0",
              "b: an offered P_k not a multiple of Delta_f", "b: a tie q (d - floor d) = r", "b: a group with r >= q",
              "b: the corner at 0 at a group site", "b: a load-time corner at a group site",
              "b: two LLMs with groups sharing a site", "b: a client without a usable arc"):
        L.append(f"  {k[3:]}: {st[k]}")
    L.append("  max relative differences:")
    for k in ("b: online_lb vs oracle_edge", "b: oracle_uf vs oracle_edge", "b: x10 lb_prime vs oracle_edge"):
        L.append(f"    {k[3:]}: {worst[k]:.6e}")
    kinds = Counter(b[0] for b in bad)
    L.append("failures by kind: " + (", ".join(f"{k} {v}" for k, v in sorted(kinds.items())) or "none"))
    for kind, s, detail in bad[:20]:
        L.append(f"  FAIL {kind}: instance {s}: {detail}")
    for name, s, msg, tb in errors[:10]:
        L.append(f"  ERROR part {name}, instance {s}: {msg}")
        L.append("    " + tb.strip().replace("\n", "\n    "))
    L.append(f"failures: {len(bad)}, errors: {len(errors)}")
    print("\n".join(L), flush=True)
    return int(len(bad) > 0 or len(errors) > 0)


if __name__ == "__main__":
    if main():   # exit status 1 on a mismatch, a failed property or an error (run_all.sh counts it)
        print("x11: a mismatch with the oracle, a failed property or an error", file=sys.stderr)
        sys.exit(1)
