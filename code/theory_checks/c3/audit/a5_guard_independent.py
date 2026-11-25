"""Independent audit checks of G1-G6 (C3 §9). Own simulator, own inner policies, own lenders,
own T11 combination; uses core.py / pd.py only for instances, OPT_eager and the reference R
(FracPD + round_pd). Not check_guard.py's code, except in part (H), which cross-checks its
simulator against this one.

Parts:
 (A) guard grid: S x gamma x test x allowance x lender x E; gamma in {0.25, 1, 1+1/sqrt2, 3},
     tests T0, T1 and T0g (service bounded by routing over in-window leases);
 (B) forced aborts at every slot from the holdings of three inner policies (Lemma G1(b));
 (C) G4 stress with synthetic eager experts (many switches, either expert first, switch at 0);
 (D) eager shadow E^eag of a renting policy (eager definition, non-anticipation, T11(E^eag, R));
 (E) G4(ii) proof wording: demand truncation vs horizon truncation for FP;
 (F) tightness of G2(b)/(c);
 (G) running-maximum allowance for clients revealed online (<= OPT_eager);
 (H) cross-check of check_guard.run against this simulator.

Audit of C3 §9: design/theory/audit_guard.md. Reference code: core.py, pd.py and (part H) check_guard.py
of code/theory_checks/c3.
Usage: python a5_guard_independent.py PART, PART in {A, A1, C, E, F, H, all}; A runs (A), (B), (D) and (G)
on 32 instances, A1 the same on the instance tau0#0 only. Output: out/a5_guard_independent_PART.txt
(also printed). Workers for part A: env GUARD_WORKERS (default 1); results are merged in job order, so
the output does not depend on the worker count except for the run times.
"""
import sys, math, random, json, time, os, zlib


def h(*a):
    return zlib.crc32(repr(a).encode())

HERE = os.path.dirname(os.path.abspath(__file__))
C3DIR = os.path.dirname(HERE)
sys.path.insert(0, C3DIR)
import numpy as np
from core import Instance, random_instance, opt_eager, opt_eager_cols
from pd import FracPD, round_pd, follow_prediction

INF = float('inf')
G2C = 1.0 + 1.0 / math.sqrt(2.0)
TOL = 1e-7
OUTDIR = os.path.join(HERE, 'out')


def cfac(g):
    return g + g * g / (g - 1.0)


class Stats:
    def __init__(self):
        self.d = {}

    def add(self, name, lhs, rhs, where=''):
        e = self.d.setdefault(name, [0, 0, -INF, -INF, None, []])
        lhs, rhs = float(lhs), float(rhs)
        e[0] += 1
        ex = lhs - rhs
        if ex > e[2]:
            e[2] = ex
        if rhs > 1e-9 and lhs / rhs > e[3]:
            e[3] = lhs / rhs; e[4] = where
        if ex > TOL * max(1.0, abs(rhs)):
            e[1] += 1
            if len(e[5]) < 5:
                e[5].append((where, lhs, rhs))

    def merge(self, o):
        for k, v in o.items():
            e = self.d.setdefault(k, [0, 0, -INF, -INF, None, []])
            e[0] += v[0]; e[1] += v[1]; e[2] = max(e[2], v[2])
            if v[3] > e[3]:
                e[3], e[4] = v[3], v[4]
            e[5] = (e[5] + v[5])[:5]

    def lines(self):
        L = []
        for k in sorted(self.d):
            e = self.d[k]
            mr = f'{e[3]:.6f}' if e[3] > -INF else '-'
            L.append(f'{k:95s} n={e[0]:9d} viol={e[1]:3d} maxex={e[2]:.2e} maxratio={mr}  [{e[4]}]')
            for v in e[5]:
                L.append(f'     VIOLATION {v}')
        return L


# ------------------------------------------------------------------ instance wrapper
class Ix:
    def __init__(self, I, name):
        self.I, self.name = I, name
        self.T, self.q = I.T, float(I.q)
        self.D = [int(x) for x in I.L]
        self.tau = [int(x) for x in I.tau]
        self.H = [int(x) for x in I.H]
        self.types = [(l, j, k) for l in range(I.m) for j in range(I.J) for k in range(I.K)]
        self.C = {ty: I.C(*ty) for ty in self.types}
        self.rentp = {ty: I.rent(*ty) for ty in self.types}
        self.req = [[c for c in range(I.n) if I.active[c, t]] for t in range(I.T)]
        self.llm = [int(x) for x in I.cl_llm]
        self.dl = np.asarray(I.delta, float)
        self.nreq = np.array([len(r) for r in self.req], float)
        feas = [[l for l in range(I.m) if np.isfinite(self.dl[c, l])] for c in range(I.n)]
        self.feas = feas
        self.B0 = sum(min([self.C[(l, self.llm[c], k)] for l in feas[c] for k in range(I.K)] or [0.0]) for c in range(I.n))
        Cmin = []
        for j in range(I.J):
            us = {l for c in range(I.n) if self.llm[c] == j for l in feas[c]}
            Cmin.append(min([self.C[(l, j, k)] for l in us for k in range(I.K)] or [INF]))
        self.Cmin = Cmin
        nj = np.zeros((I.J, I.T))
        for t in range(I.T):
            for c in self.req[t]:
                nj[self.llm[c], t] += 1
        self.njc = np.cumsum(nj, axis=1)
        self.Bon = np.array([sum(min(self.q * self.njc[j, t], Cmin[j]) for j in range(I.J)) for t in range(I.T)])
        self.qsig = self.q * self.nreq.sum()

    def route(self, t, types):
        by = {}
        for (l, j, k) in types:
            by.setdefault(j, set()).add(l)
        tot = 0.0
        for c in self.req[t]:
            b = self.q
            for l in by.get(self.llm[c], ()):
                if self.dl[c, l] < b:
                    b = float(self.dl[c, l])
            tot += b
        return tot

    def allowance(self, kind, kappa=10.0):
        if kind == 'zero':
            return np.zeros(self.T)
        if kind == 'B0':
            return np.full(self.T, self.B0)
        if kind == 'cap':
            return np.minimum(self.B0, kappa * self.Bon)
        raise ValueError(kind)


# ------------------------------------------------------------------ eager experts
class Eager:
    def __init__(self, ix, name, buys, live, inc):
        self.name, self.buys, self.live = name, buys, live
        self.inc = np.asarray(inc, float)
        self.Cc = np.cumsum(self.inc)
        self.buycost = np.array([sum(ix.C[ty] for _, ty in b) for b in buys])
        self.livecost = np.array([sum(ix.C[ty] for _, ty, _ in lv) for lv in live])
        self.W = np.array([sum(ix.C[ty] for _, ty, sp in lv if sp < u) for u, lv in enumerate(live)])
        self.sigma = self.inc - self.buycost
        self.switches = 0

    def Cm1(self, t):
        return float(self.Cc[t - 1]) if t >= 1 else 0.0


def ex_FB(ix):
    T = ix.T
    return Eager(ix, 'FB', [[] for _ in range(T)], [[] for _ in range(T)], ix.q * ix.nreq)


def ex_R(ix, pdrun, seed, r):
    rnd = round_pd(pdrun, np.random.default_rng(seed), r=r)
    T = ix.T
    buys = [[] for _ in range(T)]; live = [[] for _ in range(T)]
    for F, t0 in sorted(rnd['opened'].items(), key=lambda x: (x[1], x[0])):
        ty = (F[1], F[2], F[3])
        buys[t0].append((('R', F), ty))
        for u in range(t0, min(F[4] + ix.D[F[3]], T)):
            live[u].append((('R', F), ty, t0))
    e = Eager(ix, f'R_r{r if r else "th"}', buys, live, rnd['curve'])
    e.opened = rnd['opened']
    return e


def ex_FP(ix, cols, tag='FP'):
    T = ix.T
    buys = [[] for _ in range(T)]; live = [[] for _ in range(T)]
    for (l, j, k, s) in sorted(cols):
        if s >= T:
            continue
        pid = (tag, l, j, k, s)
        buys[s].append((pid, (l, j, k)))
        for u in range(s, min(s + ix.D[k], T)):
            live[u].append((pid, (l, j, k), s))
    inc = np.array([sum(ix.C[ty] for _, ty in buys[u]) + ix.route(u, [ty for _, ty, _ in live[u]]) for u in range(T)])
    return Eager(ix, tag, buys, live, inc)


def ex_synth(ix, rng, name, parity, phase_len=4, growth=G2C ** 0.5):
    """Synthetic eager expert: random purchases (any type), each live on [s, r) with r <= s + D;
    sigma = routing bound over the live set + a nonnegative random extra that alternates between
    a high and a low regime by phase and grows geometrically (to force many switches)."""
    T = ix.T
    buys = [[] for _ in range(T)]; live = [[] for _ in range(T)]
    pid = 0
    for u in range(T):
        for _ in range(int(rng.poisson(0.7))):
            ty = ix.types[int(rng.integers(len(ix.types)))]
            r = u + int(rng.integers(1, ix.D[ty[2]] + 1))
            pid += 1
            buys[u].append(((name, pid), ty))
            for v in range(u, min(r, T)):
                live[v].append(((name, pid), ty, u))
    inc = np.zeros(T)
    for u in range(T):
        hi = ((u // phase_len) % 2) == parity
        extra = float(rng.exponential(1.0)) * growth ** u * (4.0 if hi else 0.02)
        inc[u] = sum(ix.C[ty] for _, ty in buys[u]) + ix.route(u, [ty for _, ty, _ in live[u]]) + extra
    return Eager(ix, name, buys, live, inc)


def combine(ix, X, Y, gp=G2C, first='cheaper'):
    """The note's rule (C3 §9, Prop G4), written independently. first in {'X','Y','cheaper'}."""
    T = ix.T
    ex = {'X': X, 'Y': Y}
    if first == 'cheaper':
        cur = 'X' if X.Cc[0] <= Y.Cc[0] else 'Y'
    else:
        cur = first
    buys = [[] for _ in range(T)]; live = [[] for _ in range(T)]; inc = np.zeros(T)
    copy, tstart, sw = {}, -1, 0
    for t in range(T):
        oth = 'Y' if cur == 'X' else 'X'
        if ex[cur].Cc[t] > gp * ex[oth].Cc[t]:
            cur, sw = oth, sw + 1
            Z = ex[cur]
            copy, tstart = {}, t
            for (pid, ty, sp) in Z.live[t]:
                cid = ('copy', t, cur, pid)
                copy[pid] = cid
                buys[t].append((cid, ty))
            inc[t] = Z.livecost[t] + Z.sigma[t]
        else:
            Z = ex[cur]
            buys[t] = [((cur, pid), ty) for (pid, ty) in Z.buys[t]]
            inc[t] = Z.inc[t]
        for (pid, ty, sp) in ex[cur].live[t]:
            if pid in copy:
                live[t].append((copy[pid], ty, tstart))
            else:
                live[t].append(((cur, pid), ty, sp))
    e = Eager(ix, f'T11({X.name},{Y.name},{first})', buys, live, inc)
    e.switches = sw
    e.X, e.Y = X, Y
    return e


def check_eager(st, ix, S, where):
    T = ix.T
    prev, seen = set(), set()
    for u in range(T):
        lids = [pid for pid, _, _ in S.live[u]]
        bids = [pid for pid, _ in S.buys[u]]
        st.add('eager item 2: P(u) subset of L(u)', len(set(bids) - set(lids)), 0, where)
        st.add('eager item 2: L(u) subset of L(u-1) + P(u)', len(set(lids) - prev - set(bids)), 0, where)
        st.add('eager item 1: purchases are new leases (each id bought once)', len(set(bids) & seen) + len(bids) - len(set(bids)), 0, where)
        st.add('eager item 2: s_p <= u < s_p + D for p in L(u)',
               sum(1 for _, ty, sp in S.live[u] if not (sp <= u < sp + ix.D[ty[2]])), 0, where)
        st.add('eager item 3: routing bound over L(u) <= sigma(u)', ix.route(u, [ty for _, ty, _ in S.live[u]]), S.sigma[u], where)
        st.add('G1(a): W(t) <= C(t-1)', S.W[u], S.Cm1(u), where)
        seen |= set(bids)
        prev = set(lids)


# ------------------------------------------------------------------ simulator
class Lease:
    __slots__ = ('ty', 'l', 'j', 'k', 's', 'end', 'tau', 'H', 'rent', 'ann', 'death', 'link', 'tag')

    def __init__(self, ix, ty, s, link=None, tag='E'):
        self.ty = ty; self.l, self.j, self.k = ty; self.s = s
        self.end = s + ix.D[self.k]; self.tau = ix.tau[self.k]; self.H = ix.H[self.k]
        self.rent = ix.rentp[ty]; self.ann = None; self.death = INF; self.link = link; self.tag = tag


class Lender:
    """kinds: 'obl' (schedule R), 'snipe' (adaptive: announce at a site as soon as any held lease there
    is past its commitment, before and after the platform acts), 'pastwin' (adaptive: announce at a
    site when a held lease there is past its prepaid window: kills rented leases), 'hunt' (adaptive
    random: announce w.p. 0.6 at sites holding a guard-bought lease ('S' tag) past commitment, and
    w.p. 0.2 elsewhere)."""

    def __init__(self, ix, kind, R=None, seed=0):
        self.kind = kind
        self.R = [set(map(int, r)) for r in R] if R is not None else [set() for _ in range(ix.I.m)]
        self.rng = random.Random(seed)

    def _ann(self, t, held):
        for L in held:
            if L.ann is None and L.s + L.tau <= t and t in self.R[L.l]:
                L.ann = t; L.death = t + L.H

    def _adapt(self, t, held):
        elig = [L for L in held if L.ann is None and L.s + L.tau <= t and L.death > t]
        if self.kind == 'snipe':
            for L in elig:
                self.R[L.l].add(t)
        elif self.kind == 'pastwin':
            for L in elig:
                if t >= L.end:
                    self.R[L.l].add(t)
        elif self.kind == 'hunt':
            sites = {}
            for L in elig:
                sites[L.l] = sites.get(L.l, False) or (L.tag == 'S')
            for l in sorted(sites):
                if self.rng.random() < (0.6 if sites[l] else 0.2):
                    self.R[l].add(t)

    def pre(self, t, held):
        if self.kind != 'obl':
            self._adapt(t, held)
        self._ann(t, held)

    def post(self, t, held):
        if self.kind != 'obl':
            self._adapt(t, held)
        self._ann(t, held)


def run(ix, S, E, lender, gamma, B, test, mode='guard', t_force=None):
    T, q = ix.T, ix.q
    thr = gamma * S.Cc + B
    held, ALG = [], 0.0
    cum, cost, buy, rent, serv, ahat = (np.zeros(T) for _ in range(6))
    ahat[:] = np.nan
    ta, miss, log = None, 0, []
    for t in range(T):
        lender.pre(t, held)
        held = [L for L in held if L.death > t]
        if ta is None:
            rel, new = E.decide(t, held, ALG, thr)
            rid = {id(L) for L in rel}
            keep = [L for L in held if id(L) not in rid]
            pE = sum(ix.C[ty] for ty in new)
            rb = sum(L.rent for L in keep if t >= L.end)
            if test == 'T0':
                a = ALG + pE + rb + q * ix.nreq[t]
            elif test == 'T1':
                a = ALG + pE
            elif test == 'T0g':
                a = ALG + pE + rb + ix.route(t, [L.ty for L in keep if t < L.end] + list(new))
            else:
                raise ValueError(test)
            if mode == 'alone':
                ok = True
            elif mode == 'force':
                ok = t < t_force
            else:
                ok = a <= thr[t] + 1e-12 * (1 + abs(thr[t]))
            if ok:
                ahat[t] = a
                held = keep + [Lease(ix, ty, t) for ty in new]
                buy[t] = pE
                log.append((t, tuple(sorted(new))))
            else:
                ta = t
        if ta is not None:
            held = [L for L in held if t < L.end]
            src = S.live[t] if t == ta else S.buys[t]
            nl = [Lease(ix, x[1], t, link=x[0], tag='S') for x in src]
            held = held + nl
            buy[t] = sum(ix.C[L.ty] for L in nl)
        lender.post(t, held)
        alive = [L for L in held if L.death > t]
        rent[t] = sum(L.rent for L in alive if t >= L.end)
        serv[t] = ix.route(t, [L.ty for L in alive])
        cost[t] = buy[t] + rent[t] + serv[t]
        ALG += cost[t]
        cum[t] = ALG
        if ta is not None:
            links = {L.link: L for L in alive if L.link is not None}
            for (pid, ty, sp) in S.live[t]:
                L = links.get(pid)
                if L is None or L.ty != ty:
                    miss += 1
        E.observe(t, alive) if hasattr(E, 'observe') else None
    return dict(cum=cum, cost=cost, buy=buy, rent=rent, serv=serv, ahat=ahat, ta=ta, miss=miss, log=log)


# ------------------------------------------------------------------ inner policies (own)
class EFB:
    def decide(self, t, held, ALG, thr):
        return [], []


class ERenter:
    """BL1-like renting policy: keep a past-window lease while some current request of its LLM is
    best served there; otherwise release it; buy the cheapest-per-slot type for uncovered requests."""

    def __init__(self, ix):
        self.ix = ix

    def decide(self, t, held, ALG, thr):
        ix = self.ix
        rel = []
        for L in held:
            if t >= L.end:
                useful = any(ix.llm[c] == L.j and ix.dl[c, L.l] < ix.q for c in ix.req[t])
                if not useful:
                    rel.append(L)
        rid = {id(L) for L in rel}
        sites = {}
        for L in held:
            if id(L) not in rid:
                sites.setdefault(L.j, set()).add(L.l)
        new = []
        for c in ix.req[t]:
            j = ix.llm[c]
            if any(ix.dl[c, l] < ix.q for l in sites.get(j, ())):
                continue
            best, arg = ix.q, None
            for l in ix.feas[c]:
                for k in range(ix.I.K):
                    v = ix.C[(l, j, k)] / ix.D[k] + ix.dl[c, l]
                    if v < best - 1e-12:
                        best, arg = v, (l, j, k)
            if arg is not None:
                new.append(arg); sites.setdefault(j, set()).add(arg[0])
        return rel, new


class EHoard:
    """Buys the most expensive feasible type for each uncovered request, never releases."""

    def __init__(self, ix):
        self.ix = ix

    def decide(self, t, held, ALG, thr):
        ix = self.ix
        sites = {}
        for L in held:
            sites.setdefault(L.j, set()).add(L.l)
        new = []
        for c in ix.req[t]:
            j = ix.llm[c]
            if any(ix.dl[c, l] < ix.q for l in sites.get(j, ())):
                continue
            cands = [(ix.C[(l, j, k)], (l, j, k)) for l in ix.feas[c] for k in range(ix.I.K)]
            if cands:
                ty = max(cands)[1]
                new.append(ty); sites.setdefault(j, set()).add(ty[0])
        return [], new


class EAdv:
    """Knows the threshold and the test: buys random types up to just below the threshold every slot,
    never releases (under T0 it releases past-window leases only to stay below)."""

    def __init__(self, ix, test, seed):
        self.ix, self.test = ix, test
        self.rng = random.Random(seed)

    def decide(self, t, held, ALG, thr):
        ix = self.ix
        th = float(thr[t]) - 1e-9 * (1 + abs(float(thr[t])))
        rel = []
        base = ALG
        if self.test in ('T0', 'T0g'):
            past = sorted([L for L in held if t >= L.end], key=lambda L: -L.rent)
            rent = sum(L.rent for L in past)
            serv = ix.q * ix.nreq[t]          # T0g bound is <= this, so staying below T0 is enough
            while past and base + rent + serv > th:
                L = past.pop(0); rel.append(L); rent -= L.rent
            base += rent + serv
        new = []
        for _ in range(20):
            ty = ix.types[self.rng.randrange(len(ix.types))]
            if base + ix.C[ty] <= th:
                new.append(ty); base += ix.C[ty]
        return rel, new


class ETwin:
    """Correlated with S: shares R's coins (same opened columns). Buys R's purchases when R opens
    them, keeps a lease past its window while R counts on a lease of its type (renting), releases otherwise."""

    def __init__(self, ix, R, rent=True):
        self.ix, self.R, self.rentmode = ix, R, rent

    def decide(self, t, held, ALG, thr):
        live_types = {ty for _, ty, _ in self.R.live[t]}
        rel = [L for L in held if t >= L.end and (not self.rentmode or L.ty not in live_types)]
        return rel, [ty for _, ty in self.R.buys[t]]


class EAborter:
    """Hoards, then at slot t* buys more than the threshold to force an abort there."""

    def __init__(self, ix, tstar):
        self.h, self.tstar, self.ix = EHoard(ix), tstar, ix

    def decide(self, t, held, ALG, thr):
        rel, new = self.h.decide(t, held, ALG, thr)
        if t == self.tstar:
            ty = max(self.ix.types, key=lambda x: self.ix.C[x])
            n = int(max(1, math.ceil((float(thr[t]) - ALG) / self.ix.C[ty]) + 1))
            new = new + [ty] * min(n, 200)
        return rel, new


def make_E(ix, name, test, seed, S, R):
    if name == 'fb':
        return EFB()
    if name == 'renter':
        return ERenter(ix)
    if name == 'hoard':
        return EHoard(ix)
    if name == 'adv':
        return EAdv(ix, test, seed)
    if name == 'twin':
        return ETwin(ix, R, rent=True)
    if name == 'twin0':
        return ETwin(ix, R, rent=False)
    if name == 'aborter':
        return EAborter(ix, random.Random(seed).randrange(ix.T))
    raise ValueError(name)


def make_lender(ix, kind, seed):
    T, m = ix.T, ix.I.m
    if kind == 'none':
        return Lender(ix, 'obl', [[] for _ in range(m)])
    if kind == 'all':
        return Lender(ix, 'obl', [list(range(T)) for _ in range(m)])
    if kind == 'bern':
        rng = np.random.default_rng(seed)
        return Lender(ix, 'obl', [list(np.nonzero(rng.random(T) < 0.3)[0]) for _ in range(m)])
    return Lender(ix, kind, None, seed)


LENDERS = ('none', 'all', 'bern', 'snipe', 'pastwin', 'hunt')


# ------------------------------------------------------------------ guard checks
def guard_checks(st, ix, S, gamma, B, test, rec, where, alone=None):
    T = ix.T
    cum = rec['cum']; ta = rec['ta']
    ALG = float(cum[-1])
    nex = T if ta is None else ta
    m = np.maximum(0.0, cum[:nex] - rec['ahat'][:nex])
    M = float(m.max()) if nex else 0.0
    if test in ('T0', 'T0g'):
        for t in range(nex):
            st.add(f'{test}: m(t) == 0 (ALG(t) <= ahat(t)) at executed slots', cum[t], rec['ahat'][t], where)
    if ta is None:
        st.add('G2(a): ALG <= gamma C_S(T) + B(T) + m(T-1)', ALG, gamma * S.Cc[-1] + B[-1] + m[-1], where)
        if alone is not None:
            st.add('G2(a): no abort => run identical to E alone (max |ALG(t) diff| + log diff)',
                   float(np.max(np.abs(cum - alone['cum']))) + (0 if rec['log'] == alone['log'] else 1), 0, where)
    else:
        mp = float(m[ta - 1]) if ta >= 1 else 0.0
        Bp = float(B[ta - 1]) if ta >= 1 else 0.0
        rhs1 = S.Cc[-1] + (gamma - 1) * S.Cm1(ta) + S.W[ta] + Bp + mp
        st.add('G2(b) first: ALG <= C_S(T)+(g-1)C_S(ta-1)+W_S(ta)+B(ta-1)+m(ta-1)', ALG, rhs1, where)
        st.add('G2(b) second: ALG <= (1+g)C_S(T)+B(T)+m(ta-1)', ALG, (1 + gamma) * S.Cc[-1] + B[-1] + mp, where)
        if gamma < 1:
            st.add('G2(b) first, gamma<1 (negative term exercised)', ALG, rhs1, where)
        g1b(st, ix, S, rec, where)
    st.add('G2(c): ALG <= (1+g)C_S(T)+B(T)+M', ALG, (1 + gamma) * S.Cc[-1] + B[-1] + M, where)
    return M


def g1b(st, ix, S, rec, where):
    ta = rec['ta']; T = ix.T
    st.add('G1(b): copy purchase at ta == sum_{L_S(ta)} C (|diff|)', abs(rec['buy'][ta] - S.livecost[ta]), 0, where)
    st.add('G1(b): cost(ta) <= sum_{L_S(ta)} C + sigma_S(ta)', rec['cost'][ta], S.livecost[ta] + S.sigma[ta], where)
    for u in range(ta + 1, T):
        st.add('G1(b): cost(u) <= c_S(u), u > ta', rec['cost'][u], S.inc[u], where)
    st.add('G1(b): rent at slots >= ta', float(rec['rent'][ta:].sum()), 0, where)
    st.add('G1(b): uncovered p in L_S(u), u >= ta', rec['miss'], 0, where)
    st.add('G1(b): ALG(T)-ALG(ta-1) <= W_S(ta)+C_S(T)-C_S(ta-1)', rec['cum'][-1] - (rec['cum'][ta - 1] if ta else 0.0),
           S.W[ta] + S.Cc[-1] - S.Cm1(ta), where)


# ------------------------------------------------------------------ eager shadow
def eager_shadow(ix, Epol_factory):
    """E simulated alone against omega_all (I1: every lease announced at s+tau, dies at s+D)."""
    T = ix.T
    E = Epol_factory()
    lend = make_lender(ix, 'all', 0)
    held = []
    buys = [[] for _ in range(T)]; live = [[] for _ in range(T)]; rentsum = 0.0
    pid = 0
    for t in range(T):
        lend.pre(t, held)
        held = [L for L in held if L.death > t]
        rel, new = E.decide(t, held, 0.0, np.full(T, INF))
        rid = {id(L) for L in rel}
        held = [L for L in held if id(L) not in rid]
        for ty in new:
            pid += 1
            L = Lease(ix, ty, t, link=('Eeag', pid))
            held.append(L)
            buys[t].append((L.link, ty))
        lend.post(t, held)
        alive = [L for L in held if L.death > t]
        rentsum += sum(L.rent for L in alive if t >= L.end)
        for L in alive:
            live[t].append((L.link, L.ty, L.s))
    inc = np.array([sum(ix.C[ty] for _, ty in buys[u]) + ix.route(u, [ty for _, ty, _ in live[u]]) for u in range(T)])
    return Eager(ix, 'Eeag', buys, live, inc), rentsum


# ------------------------------------------------------------------ instances
def make_inst(fam, seed):
    rng = np.random.default_rng(910000 + 37 * seed + {'rand': 0, 'tau0': 1, 'slo': 2, 'hq': 3}[fam])
    q = float(rng.choice([2.0, 4.0, 10.0])) if fam != 'hq' else float(rng.choice([15.0, 30.0]))
    if fam == 'rand' or fam == 'hq':
        return random_instance(rng, T=24, m=3, J=2, n=6, q=q)
    if fam == 'tau0':
        return random_instance(rng, T=24, m=3, J=2, n=6, q=q, contracts=[(0, 1, 0.9), (2, 0, 1.1), (5, 2, 1.4)])
    if fam == 'slo':
        return random_instance(rng, T=24, m=4, J=2, n=7, slo=0.45, q=q)


def experts_for(ix, seed):
    I = ix.I
    pdr = FracPD(I).run()
    FB = ex_FB(ix)
    R1 = ex_R(ix, pdr, 5000 + seed, 1)
    Rth = ex_R(ix, pdr, 6000 + seed, None)
    rng = np.random.default_rng(7000 + seed)
    A = ex_synth(ix, rng, 'SA', 0); Bx = ex_synth(ix, rng, 'SB', 1)
    Eeag, rs = eager_shadow(ix, lambda: ERenter(ix))
    Ss = [FB, R1, Rth,
          combine(ix, FB, R1, first='cheaper'), combine(ix, FB, Rth, first='Y'),
          combine(ix, A, Bx, first='X'), combine(ix, A, Bx, first='Y'),
          combine(ix, Eeag, R1, first='X')]
    return Ss, R1, Rth, Eeag, rs, (A, Bx), pdr


def job(args):
    fam, seed = args
    st = Stats()
    info = {'aborts': {}, 'switches': [], 'synth_switch_at0': 0, 'post_abort_switch': 0, 'ta_W_pos': 0, 'aborts_total': 0}
    I = make_inst(fam, seed)
    ix = Ix(I, f'{fam}#{seed}')
    Ss, R1, Rth, Eeag, rs, (A, Bx), pdr = experts_for(ix, seed)
    st.add('Eeag: rent under omega_all == 0', rs, 0, ix.name)
    for S in Ss + [A, Bx, Eeag]:
        check_eager(st, ix, S, f'{ix.name} {S.name}')
    for S in Ss:
        if S.name.startswith('T11'):
            info['switches'].append(S.switches)
            mn = np.minimum(S.X.Cc, S.Y.Cc)
            for t in range(ix.T):
                st.add('G4(ii): C_T11(t) <= c(gp) min{C_X(t),C_Y(t)}', S.Cc[t], cfac(G2C) * mn[t], f'{ix.name} {S.name} t={t}')
    # non-anticipation (demand cut after T/2) for R, synth-based not needed (coins), Eeag and combinations
    tc = ix.T // 2
    Ic = I.subset(); Ic.active = I.active.copy(); Ic.active[:, tc + 1:] = False
    ixc = Ix(Ic, ix.name + ' cut')
    Ssc, _, _, Eeagc, _, _, _ = experts_for(ixc, seed)
    for S, Sc in zip(Ss + [Eeag], Ssc + [Eeagc]):
        st.add('non-anticipation: max_{t<=T/2} |C_S(t) - C_S^cut(t)|', float(np.max(np.abs(S.Cc[:tc + 1] - Sc.Cc[:tc + 1]))), 0,
               f'{ix.name} {S.name}')
    # (A) guard grid
    nruns = 0
    for si, S in enumerate(Ss):
        for gamma in (0.25, 1.0, G2C, 3.0):
            for test in ('T0', 'T1', 'T0g'):
                for allow in ('zero', 'B0', 'cap'):
                    B = ix.allowance(allow)
                    for lk in LENDERS:
                        for en in ('fb', 'renter', 'hoard', 'adv', 'twin', 'aborter'):
                            eseed = h(fam, seed, si, gamma, test, allow, lk, en)
                            lseed = h(fam, seed, lk)
                            rec = run(ix, S, make_E(ix, en, test, eseed, S, R1), make_lender(ix, lk, lseed), gamma, B, test)
                            nruns += 1
                            where = f'{ix.name} S={S.name} g={gamma:.3f} {test} B={allow} L={lk} E={en}'
                            alone = None
                            if rec['ta'] is None and en in ('renter', 'twin', 'hoard'):
                                alone = run(ix, S, make_E(ix, en, test, eseed, S, R1), make_lender(ix, lk, lseed), gamma, B, test,
                                            mode='alone')
                            guard_checks(st, ix, S, gamma, B, test, rec, where, alone)
                            k = (test, allow, en)
                            a = info['aborts'].setdefault('|'.join(map(str, k)), [0, 0])
                            a[0] += 1; a[1] += int(rec['ta'] is not None)
                            if rec['ta'] is not None:
                                info['aborts_total'] += 1
                                info['ta_W_pos'] += int(S.W[rec['ta']] > 0)
                                if S.name.startswith('T11') and S.switches:
                                    # did S switch after the abort?  (switch slots = slots whose buys are copies)
                                    sw_after = any(any(isinstance(pid, tuple) and pid and pid[0] == 'copy' for pid, _ in S.buys[u])
                                                   for u in range(rec['ta'] + 1, ix.T))
                                    info['post_abort_switch'] += int(sw_after)
                            # G3 pathwise envelope (T0 and T0g; cap or zero allowance)
                            if test in ('T0', 'T0g') and allow in ('zero', 'cap'):
                                kap = 10.0 if allow == 'cap' else 0.0
                                st.add('G3 envelope: ALG <= (1+g) C_S(T) + kappa B_on(T)', rec['cum'][-1],
                                       (1 + gamma) * S.Cc[-1] + kap * ix.Bon[-1], where)
    # (B) forced aborts at every slot
    for S in Ss:
        for lk in LENDERS:
            for en, test, allow in (('renter', 'T0', 'zero'), ('hoard', 'T1', 'B0'), ('adv', 'T1', 'B0'), ('twin', 'T1', 'zero')):
                B = ix.allowance(allow)
                for t0 in range(ix.T):
                    eseed = h(fam, seed, S.name, lk, en)
                    rec = run(ix, S, make_E(ix, en, test, eseed, S, R1), make_lender(ix, lk, h(fam, seed, lk)),
                              1.0, B, test, mode='force', t_force=t0)
                    g1b(st, ix, S, rec, f'{ix.name} forced t0={t0} S={S.name} L={lk} E={en}')
                    if t0 == 0:
                        st.add('G1(b)/G4(iii): tracking from slot 0: ALG(T) <= C_S(T)', rec['cum'][-1], S.Cc[-1],
                               f'{ix.name} S={S.name} L={lk}')
    # G5 and capped allowance
    oe = opt_eager(I)
    OPT = float(oe['lb'])
    st.add('G5: B_on(T) <= OPT_eager (MILP lb)', ix.Bon[-1], OPT, ix.name)
    st.add('G5: B_on(T) <= q|sigma|', ix.Bon[-1], ix.qsig, ix.name)
    # (G) running maximum with clients revealed online
    seen = set(); tb = 0.0
    for t in range(ix.T):
        seen |= set(ix.req[t])
        val = 0.0
        for j in range(I.J):
            us = {l for c in seen if ix.llm[c] == j for l in ix.feas[c]}
            cm = min([ix.C[(l, j, k)] for l in us for k in range(I.K)] or [INF])
            val += min(ix.q * ix.njc[j, t], cm)
        tb = max(tb, val)
    st.add('G5 variant: running-max allowance (clients online) <= OPT_eager', tb, OPT, ix.name)
    info['tildeB_over_Bon'] = tb / ix.Bon[-1] if ix.Bon[-1] > 0 else 1.0
    info['runs'] = nruns
    info['OPT'] = OPT
    return st.d, info


# ------------------------------------------------------------------ (C) G4 stress, many switches
def g4_stress(nrep=150):
    st = Stats()
    sws = []
    for rep in range(nrep):
        rng = np.random.default_rng(424242 + rep)
        I = random_instance(rng, T=30, m=3, J=2, n=6, q=float(rng.choice([2.0, 6.0])),
                            contracts=[(0, 1, 1.0), (2, 1, 1.2), (4, 3, 1.5)])
        ix = Ix(I, f'stress#{rep}')
        A = ex_synth(ix, rng, 'SA', 0, phase_len=int(rng.integers(2, 6)), growth=float(rng.uniform(1.2, 1.8)))
        Bx = ex_synth(ix, rng, 'SB', 1, phase_len=int(rng.integers(2, 6)), growth=float(rng.uniform(1.2, 1.8)))
        for gp in (1.05, 1.3, G2C, 2.5):
            for first in ('X', 'Y', 'cheaper'):
                S = combine(ix, A, Bx, gp, first)
                sws.append(S.switches)
                check_eager(st, ix, S, f'{ix.name} gp={gp} {first}')
                mn = np.minimum(A.Cc, Bx.Cc)
                for t in range(ix.T):
                    st.add('G4(ii) stress: C(t) <= c(gp) min{C_X(t),C_Y(t)}', S.Cc[t], cfac(gp) * mn[t],
                           f'{ix.name} gp={gp:.3f} first={first} t={t} sw={S.switches}')
                for lk in LENDERS:
                    rec = run(ix, S, EFB(), make_lender(ix, lk, rep), 1.0, np.zeros(ix.T), 'T0', mode='force', t_force=0)
                    g1b(st, ix, S, rec, f'{ix.name} gp={gp:.3f} first={first} L={lk}')
                    st.add('G4(iii) stress: executed from slot 0: ALG(T) <= C(T)', rec['cum'][-1], S.Cc[-1], f'{ix.name} L={lk}')
    return st, sws


# ------------------------------------------------------------------ (E) demand-truncation wording
def truncation_wording():
    out = []
    for seed in range(30):
        rng = np.random.default_rng(880000 + seed)
        I = random_instance(rng, T=24, m=3, J=2, n=6, q=4.0)
        cols = opt_eager_cols(I, opt_eager(I))
        ix = Ix(I, f'tr#{seed}')
        FP = ex_FP(ix, cols)
        pdr = FracPD(I).run()
        R = ex_R(ix, pdr, 1234 + seed, 1)
        Sfull = combine(ix, FP, R, first='X')
        tc = ix.T // 2
        Ic = I.subset(); Ic.active = I.active.copy(); Ic.active[:, tc + 1:] = False
        ixc = Ix(Ic, 'cut')
        FPc = ex_FP(ixc, cols)
        Rc = ex_R(ixc, FracPD(Ic).run(), 1234 + seed, 1)
        Scut = combine(ixc, FPc, Rc, first='X')
        out.append(dict(seed=seed, C_t=float(Sfull.Cc[tc]), total_on_cut_demand=float(Scut.Cc[-1]),
                        FP_t=float(FP.Cc[tc]), FP_cut_total=float(FPc.Cc[-1]),
                        bound_t=float(cfac(G2C) * min(FP.Cc[tc], R.Cc[tc]))))
    return out


# ------------------------------------------------------------------ (F) tightness of G2(b)/(c)
def tightness():
    """Site 0: delta=0, beta=100; site 1: delta=inf (useless), beta chosen so one lease costs 100.
    One contract tau=10, H=0 (D=10=T), a=1, g=1: C0 = 110. q=10, one client active every slot.
    S = FP that buys site 0 at slot 0 (eager, deterministic). E: slot 0 buys one useless lease (100);
    slot 1 buys another (forces the abort under T0, gamma=1, B=0)."""
    T = 10
    I = Instance(T=T, tau=np.array([10]), H=np.array([0]), a=np.array([[1.0], [1.0]]), beta=np.array([[100.0, 90.0]]),
                 g=np.array([1]), q=10.0, cl_llm=np.zeros(1, dtype=int), delta=np.array([[0.0, np.inf]]),
                 active=np.ones((1, T), dtype=bool))
    ix = Ix(I, 'tight')
    S = ex_FP(ix, [(0, 0, 0, 0)])

    class ET:
        def decide(self, t, held, ALG, thr):
            return [], ([(1, 0, 0)] if t <= 1 else [])
    res = []
    for lk in LENDERS:
        rec = run(ix, S, ET(), make_lender(ix, lk, 0), 1.0, np.zeros(T), 'T0')
        res.append(dict(lender=lk, ta=rec['ta'], ALG=float(rec['cum'][-1]), bound=float(2 * S.Cc[-1]),
                        first_rhs=float(S.Cc[-1] + S.W[rec['ta']] if rec['ta'] is not None else np.nan)))
    return res


# ------------------------------------------------------------------ (H) cross-check of check_guard.run
def crosscheck(n_inst=12):
    import check_guard as cg
    st = Stats()
    ndiff = 0; nrun = 0
    for fam, s in [('rand', i) for i in range(n_inst // 2)] + [('tau0', i) for i in range(n_inst // 2)]:
        I = cg.make_random(fam, s)
        ctx = cg.Ctx(I, f'{fam}#{s}')
        pdr = FracPD(I).run()
        FBc, exs, extra = cg.build_experts(ctx, pdr, [61000 + 97 * s])
        ix = Ix(I, ctx.name)
        lenders = cg.lender_specs(ctx, ctx.name)
        for Sc in [FBc] + exs:
            S = Eager(ix, Sc.name, [[(pid, ty) for pid, ty in b] for b in Sc.buys],
                      [[(pid, ty, sp) for pid, ty, sp in lv] for lv in Sc.live], Sc.inc)
            for gamma in (1.0, G2C):
                for test in ('T0', 'T1'):
                    for allow in ('zero', 'B0', 'cap'):
                        g = cg.Guard(ctx, Sc, gamma, test, allow)
                        B = ix.allowance(allow)
                        st.add('crosscheck: allowance equal', float(np.max(np.abs(g.B - B))), 0, ctx.name)
                        for lname in ('obl0', 'obl0.2', 'eager'):
                            kind, omega = lenders[lname]
                            for plan_seed in range(3):
                                prng = random.Random(h(fam, s, plan_seed))
                                plan = {t: [ix.types[prng.randrange(len(ix.types))] for _ in range(prng.randrange(3))]
                                        for t in range(ix.T) if prng.random() < 0.4}
                                recA = cg.run(ctx, g, cg.EScript(plan), cg.make_lender(ctx, lenders[lname], 'x'))

                                class EP:
                                    def decide(self, t, held, ALG, thr):
                                        return [], list(plan.get(t, []))
                                recB = run(ix, S, EP(), Lender(ix, 'obl', [list(map(int, o)) for o in omega]), gamma, B, test)
                                nrun += 1
                                d = abs(float(recA['cum'][-1]) - float(recB['cum'][-1])) + (0 if recA['ta'] == recB['ta'] else 1)
                                ndiff += int(d > 1e-9)
                                st.add('crosscheck: |ALG_check_guard - ALG_indep| + [ta differs]', d, 0,
                                       f'{ctx.name} {Sc.name} g={gamma:.3f} {test} {allow} {lname} plan{plan_seed}')
    return st, nrun, ndiff


if __name__ == '__main__':
    import multiprocessing as mp
    t0 = time.time()
    part = sys.argv[1] if len(sys.argv) > 1 else 'all'
    L = []
    if part in ('all', 'A'):
        jobs = [(f, s) for f in ('rand', 'tau0', 'slo', 'hq') for s in range(8)]
        ST = Stats(); infos = []
        nw = int(os.environ.get('GUARD_WORKERS', '1'))
        if nw <= 1:
            for d, info in map(job, jobs):
                ST.merge(d); infos.append(info)
        else:
            with mp.get_context('spawn').Pool(nw) as p:
                for d, info in p.imap(job, jobs):     # ordered, so ties in maxratio resolve as with one worker
                    ST.merge(d); infos.append(info)
        L.append(f'== (A)(B)(G) guard grid + forced aborts: {len(jobs)} instances, '
                 f'{sum(i["runs"] for i in infos)} guard runs, {time.time() - t0:.0f} s')
        L += ST.lines()
        ab = {}
        for i in infos:
            for k, v in i['aborts'].items():
                a = ab.setdefault(k, [0, 0]); a[0] += v[0]; a[1] += v[1]
        L.append('abort rates (test|allow|E): ' + '; '.join(f'{k} {100 * v[1] / v[0]:.1f}%' for k, v in sorted(ab.items())))
        sw = [x for i in infos for x in i['switches']]
        L.append(f'T11 experts: {len(sw)}, switches distribution: ' +
                 str({k: sw.count(k) for k in sorted(set(sw))}))
        L.append(f'aborts {sum(i["aborts_total"] for i in infos)}, with W_S(ta)>0 {sum(i["ta_W_pos"] for i in infos)}, '
                 f'with a switch of S after ta {sum(i["post_abort_switch"] for i in infos)}')
        L.append('running-max allowance / B_on(T): max ' + f'{max(i["tildeB_over_Bon"] for i in infos):.3f}')
    if part == 'A1':
        d, info = job(('tau0', 0))
        ST = Stats(); ST.d = d
        L += ST.lines(); L.append(str({k: v for k, v in info.items() if k != 'aborts'}))
    if part in ('all', 'C'):
        st, sws = g4_stress()
        L.append(f'== (C) G4 stress: {len(sws)} combinations, switches max {max(sws)}, mean {np.mean(sws):.2f}, '
                 f'>=4 switches {sum(x >= 4 for x in sws)}')
        L += st.lines()
    if part in ('all', 'E'):
        tr = truncation_wording()
        bad = [r for r in tr if r['total_on_cut_demand'] > r['C_t'] + 1e-9]
        L.append(f'== (E) G4(ii) wording: instances where the total on demand cut after T/2 exceeds C(T/2): {len(bad)}/{len(tr)}')
        for r in bad[:3]:
            L.append(f'   {r}')
        L.append(f'   C(t) <= c(gp) min(C_X(t),C_Y(t)) at t=T/2 still holds on all: {all(r["C_t"] <= r["bound_t"] + 1e-9 for r in tr)}')
    if part in ('all', 'F'):
        L.append('== (F) tightness of G2(b)/(c):')
        for r in tightness():
            L.append(f'   {r}')
    if part in ('all', 'H'):
        st, nrun, ndiff = crosscheck()
        L.append(f'== (H) cross-check of check_guard.run vs this simulator: {nrun} runs, {ndiff} differ')
        L += st.lines()
    L.append(f'total time {time.time() - t0:.0f} s')
    txt = '\n'.join(L)
    print(txt)
    os.makedirs(OUTDIR, exist_ok=True)
    with open(os.path.join(OUTDIR, f'a5_guard_independent_{part}.txt'), 'w') as f:
        f.write(txt + '\n')
