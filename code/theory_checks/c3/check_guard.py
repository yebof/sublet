"""Guard checks: Lemma G1, Theorem G2, Corollary G3, Proposition G4, Lemma G5 and Proposition G6 of
design/theory/c3_c4_c5_general.md §9 (first stated in design/q44_practical_sublet.md §3; audit
design/theory/audit_guard.md), on the ORML core of c3_c4_c5_general.md §1 (independent of code/sim).

Model (core.py): slots t in [T]; a lease (l,j,k) bought at s costs C = beta + g a D_k, is alive on
[s, s+D_k) for sure and afterwards pays rent g a per slot while held and alive; a per-site
announcement schedule; a lease is announced at the first announcement r >= s + tau_k of its site and
dies at r + H_k; within a slot the slot's announcements are revealed, the platform acts (releases,
purchases), an adaptive lender may announce again (post-action, only tau_k = 0 purchases or the
random 'hold' rule), then the slot's requests are routed at min cost over the leases alive at t
(fallback q). ALG(t) = purchases + rent + service through t.

Safe experts S (eager, lender-independent; built from pd.py):
  R      rounded ORML-PD (FracPD + round_pd, practical rule), rbar = 1 ('r1') or ceil(2 ln N) ('rth');
         P_R(u) = columns opened at u, L_R(u) = opened columns whose aligned window contains u.
  FB     all-fallback, curve = follow_prediction(I, []) (FP with an empty prediction).
  T11    C3-T11 doubling combiner of FB and R (gamma' = 1+1/sqrt2), the rule of pd.combine written
         as an eager algorithm (copies of the new expert's live set at a switch); its total and
         number of switches are checked against pd.combine.
  Further eager experts, used in the expert checks and the forced-abort runs, not as the guard's S:
  T11RR  the same rule for R_r1 and R_rth; T11FP for FP (pd.follow_prediction of a late prediction:
         OPT_eager columns of the activity shifted by 6 slots) and R, checked against pd.combine with
         that prediction; T11FPx the same two experts started with the dearer one at slot 0, so the
         rule can switch at slot 0 (empty phase 0); SH_greedy, SH_random the eager shadows of the
         inner policies greedy and random (the policy run alone against omega_all; its rent there must
         be 0), and T11SH = T11(SH_greedy, R_r1) started with the shadow (Proposition G4 with an eager
         shadow).
Inner policies E: 'fb' (never buys), 'greedy' (BL1-like: on an uncovered request buy the (l,k)
minimising C/D_k + delta if below q; hold a lease while it served load in the previous slot; release
it once idle and past its prepaid window), 'greedy_i2' (greedy that also reads every site's
announcements of the slot, I2, and avoids announced sites for new leases when another feasible site
exists), 'greedy_rev' (P5 family only: greedy restricted to the revocable contract), 'random'
(random releases, also inside windows, and random purchases), 'twin' (executes the guard's own S
as in Lemma G1(b) from slot 0: buys P_S(u) at u and releases each lease at its window end; it
reads S's realized purchases, so it shares R's coins),
'adv_fill' (scripted adversary: knows S, gamma, B and the test; each slot it buys the most expensive
lease types up to the test threshold, never releases except under T0/T0g to stay below it, so under
T1 it accumulates unchecked rent), 'adv_trip' (adv_fill plus one extra purchase at a seeded slot t*,
which forces an abort there under T0 and T1), 'g6i' (Proposition G6 (i): one lease per client at
slot 0).
Lenders: 'obl0' (no announcement), 'obl0.2' (oblivious Bernoulli(0.2) per site-slot), 'eager'
(omega_all), 't4' (adaptive C3-T4 rule: announce at a site when a platform lease there reaches age
tau; post-action for tau = 0), 'hold' (adaptive, random: announce at a site with probability 1/2
whenever the platform holds an unannounced lease there past its commitment).
Guard (§9): tests T0 (service bounded by q n(t)), T0g (service bounded by min-cost routing over the
leases held after A_E(t) that are inside their prepaid window, which are alive for every lender) and
T1 (purchase pre-check); gamma in {0.25, 1, 1+1/sqrt2, 3}; allowances 'zero', 'B0' (one fresh lease
per client) and 'cap' (min{B0, kappa B_on(t)}, kappa = 10). At an abort Lemma G1(b) with X = S.

Instances: 380 random core instances (families rand, slo, spiky, tau0 with contracts
(tau,H) in {(0,1),(2,0),(6,3)}, with q drawn from {2,4,10}, and hq, as rand with q in {12,20}), the
C3-P5 insurance family and the C3-T4 cat-and-mouse family of check_c4_lower.py, Proposition G6's
instances I_n, n in {4,16,64}, and the tightness instance of Theorem G2 (one per gamma).
Runs: the grid S x gamma x test x allowance x lender x E with the guard; E alone (no guard) for the
identity of Theorem G2(a); forced aborts at slots {0, 1, T/3, 2T/3, T-1} with the holdings of greedy,
random and adv_fill (T1, B0) for every expert, and at every slot with the holdings of random under
the adaptive lender 'hold' for R, T11 and T11FPx, for Lemma G1(b) from arbitrary holdings and
Proposition G4's execution from slot 0. Instance checks: eager definition and Lemma G1(a) for every
expert, C3-T11 and Proposition G4 bounds at every t, non-anticipation of C_S(t) and B_on(t)
(recomputed on the demand cut after T/2), the demand-truncation identity that the earlier G4 proof
used (informational: FP buys after the cut), Lemma G5 against OPT_eager (MILP dual bound), q|sigma|
and the LP relaxation of OPT(sigma, no announcement), which is <= OPT(sigma, omega) for every omega.
Corollary G3 (sound tests T0, T0g) against OPT_eager pathwise on every run (this implies the
expectation bound) and as means over the three R seeds on the families; on the families also against
max(2,rho) OPT(sigma, omega) of the realized schedule (core.opt_omega).
Every inequality is reported with its number of evaluations, violations (LHS > RHS + 1e-7 max(1,|RHS|)),
the maximum excess LHS - RHS (<= 0 required) and the maximum ratio LHS/RHS (<= 1 required). Lines
named 'impl. ...' hold by construction of the guard code (implementation checks, not evidence).

K0 check (MS5b, step P6 of design/sublet_v2.md §5 and its §8.1; C3 §9: Definition R, Lemma P.1, Proposition P and its
code-level clause). The projected guard (A8P's rule) is written on the core in this script (run_proj; nothing is
imported from code/sim): at slot t in mode E it evaluates the ladder of E's list (Definition R (R1): E; P1_n' with the
first n' purchases and E's releases, n' in {n_b-1, n_b/2, n_b/4, 1} minus {0, n_b}; P0, E's releases alone; K0, a
release of every held lease) and executes the first list with test value <= rhs(t) + GUARD_TOL max(1,|rhs(t)|),
rhs = gamma C_S(t) + B(t); if none passes it aborts as the guard does. Main grid: S in {FB} and the T11(FB,R) experts
that switch at least once (one that never switches equals FB or R and is not rerun), gamma in {1, 1+1/sqrt2, 3},
tests T0g and T0, the three allowances, the five lenders (adaptive included), the grid's inner policies and adv_hold
(adv_fill without releases, so that leases rent past their windows and K0 gets executed). Each run is made twice: in
exact arithmetic (every cost an integer on the scale 2**sh, the exact value of the float data; the limit exact, with
C_S the exact sum of S's float increments) and in the code's float64 arithmetic. Claims, exact: at every slot t at which
every earlier slot was executed and S follows FB, K0's test value ALG(t-1) + q n(t), with ALG(t-1) from the run's own
ledger, passes against gamma C_S(t) + B(t) + tol(t) (Proposition P(c)); no abort at a slot where S follows FB, for
S = FB, and for S = T11(FB,R) aborts only where it follows R; K0 passes wherever gamma c_S(t) + B(t) - B(t-1) >= q n(t),
for every S and gamma (Remark "what P uses of FB"); ALG(t) <= ahat(t) at every executed slot, whichever candidate was
executed (Lemma P.1 on the core); c_S(t) == q n(t) where S follows FB (identity (b) on the core, where R = S_K0 = 0 and
G_K0 = Q); G2(c) for the projected guard (Remark R(e)). Float64: every abort with S on FB is classified by the
code-level clause (k0_clause: X(t_a), m(t_a-1) and the identity's terms in fractions.Fraction, the terms must add up to
X(t_a) exactly, then (R1) and (R2)), and the float runs whose path differs from the exact run are counted. The core
float edge scan (k0_edge_job) puts slot 2's purchase within rounding of its limit, so that float64 aborts occur at
slot 3 with S on FB; each must classify as a rounding abort, and the exact runs must not abort. Negative controls,
exact, each of which must fail at least once: gamma = 0.25 < 1 with S = FB; test T1 with S = FB (K0's T1 value is
ALG(t-1)); S = R at slots with gamma c_S(t) + B(t) - B(t-1) < q n(t). The core has no Load, Unload, Drain or
SetAdmission, no robust form of T0g, no stranding (R = S_K0 = 0) and no refusal, so the K0 check covers only the
skeleton of Proposition P (the step at t-1 and c_S = Q); the full-model content is audited by
code/sim/audit/x9_prop_p.py. The K0 lines are appended after the earlier output and leave it unchanged; the TOTAL
VIOLATIONS line counts them too.
Output: out/guard.json, out/guard.txt. Workers: env GUARD_WORKERS (default 2); about 18 min on 2 workers (about 14 min
before the K0 check was added).
"""
import os, sys, json, math, time, random
from fractions import Fraction
os.environ.setdefault('OMP_NUM_THREADS', '1')
import numpy as np
import multiprocessing as mp
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from core import Instance, random_instance, random_omega, opt_eager, opt_omega, opt_eager_cols   # noqa: E402
from pd import FracPD, round_pd, follow_prediction, combine                      # noqa: E402
from check_c4_lower import cm_instance, single                                   # noqa: E402

OUT = os.path.join(HERE, 'out')
TOL = 1e-7
G2C = 1.0 + 1.0 / math.sqrt(2.0)          # gamma' of the C3-T11 combiner inside S
GAMMAS = (0.25, 1.0, G2C, 3.0)           # gamma of the guard
TESTS = ('T0', 'T0g', 'T1')
SOUND = ('T0', 'T0g')                     # tests with ALG(t) <= ahat(t) for every lender (m == 0)
ALLOWS = ('zero', 'B0', 'cap')
KAPPA = 10.0
RAND_FAMS = (('rand', 100), ('slo', 80), ('spiky', 60), ('tau0', 80), ('hq', 60))
E_RAND = ('fb', 'greedy', 'greedy_i2', 'random', 'twin', 'adv_fill', 'adv_trip')
LENDERS = ('obl0', 'obl0.2', 'eager', 't4', 'hold')
INF = float('inf')
FAM_COLS = (('T0', 'R', 'r1'), ('T0', 'R', 'rth'), ('T0', 'T11', 'r1'), ('T0', 'T11', 'rth'), ('T0g', 'R', 'r1'),
            ('T0g', 'T11', 'rth'), ('T1', 'R', 'r1'), ('T1', 'T11', 'rth'))


def cfac(g):
    return g + g * g / (g - 1.0)


def alpha_N(I):
    N = max(I.n * I.T, 3)
    return 4 * math.ceil(2 * math.log(N)) * math.log(I.m * I.K + 2) + 1


def kappa_of(allow):
    return {'zero': 0.0, 'cap': KAPPA}.get(allow)


# ------------------------------------------------------------------------------------------ stats
class Stats:
    """name -> [n, n_viol, max_excess, where, max_ratio, where_ratio, violations(<=6)]."""

    def __init__(self):
        self.d = {}

    def add(self, name, lhs, rhs, where):
        e = self.d.get(name)
        if e is None:
            e = self.d[name] = [0, 0, -INF, None, -INF, None, []]
        lhs = float(lhs); rhs = float(rhs)
        ex = lhs - rhs
        e[0] += 1
        if ex > e[2]:
            e[2] = ex; e[3] = where
        if rhs > 1e-9:
            r = lhs / rhs
            if r > e[4]:
                e[4] = r; e[5] = where
        if ex > TOL * max(1.0, abs(rhs)):
            e[1] += 1
            if len(e[6]) < 6:
                e[6].append([where, lhs, rhs])

    def add_arr(self, name, lhs, rhs, where):
        lhs = np.asarray(lhs, float); rhs = np.asarray(rhs, float)
        if lhs.size == 0:
            return
        ex = lhs - rhs
        i = int(np.argmax(ex))
        self.add(name, lhs[i], rhs[i], where)
        e = self.d[name]
        e[0] += lhs.size - 1
        pos = rhs > 1e-9
        if pos.any():
            r = lhs[pos] / rhs[pos]
            k = int(np.argmax(r))
            if r[k] > e[4]:
                e[4] = float(r[k]); e[5] = where
        bad = ex > TOL * np.maximum(1.0, np.abs(rhs))
        nb = int(bad.sum()) - (1 if bad[i] else 0)
        if nb > 0:
            e[1] += nb
            for k in np.nonzero(bad)[0]:
                if k != i and len(e[6]) < 6:
                    e[6].append([where + f' [u={int(k)}]', float(lhs[k]), float(rhs[k])])

    def merge(self, other):
        for name, o in other.items():
            e = self.d.get(name)
            if e is None:
                self.d[name] = [o[0], o[1], o[2], o[3], o[4], o[5], list(o[6])]
                continue
            e[0] += o[0]; e[1] += o[1]
            if o[2] > e[2]:
                e[2], e[3] = o[2], o[3]
            if o[4] > e[4]:
                e[4], e[5] = o[4], o[5]
            e[6] = (e[6] + o[6])[:6]


class Info:
    """Informational aggregates: key -> [n, aborts, sum ratio, max ratio]."""

    def __init__(self):
        self.d = {}

    def add(self, key, aborted, ratio):
        e = self.d.setdefault(key, [0, 0, 0.0, -INF])
        e[0] += 1; e[1] += int(aborted); e[2] += ratio; e[3] = max(e[3], ratio)

    def merge(self, other):
        for k, o in other.items():
            e = self.d.setdefault(k, [0, 0, 0.0, -INF])
            e[0] += o[0]; e[1] += o[1]; e[2] += o[2]; e[3] = max(e[3], o[3])


# ------------------------------------------------------------------------------------------ instance context
class Ctx:
    def __init__(self, I, name):
        self.I, self.name = I, name
        T = I.T
        self.RQ = [[c for c in range(I.n) if I.active[c, t]] for t in range(T)]
        self.nreq = np.array([len(r) for r in self.RQ], dtype=float)
        self.cl = [int(x) for x in I.cl_llm]
        self.dl = I.delta.tolist()
        self.q = float(I.q)
        self.D = [int(x) for x in I.L]
        self.tau = [int(x) for x in I.tau]
        self.H = [int(x) for x in I.H]
        self.types = [(l, j, k) for l in range(I.m) for j in range(I.J) for k in range(I.K)]
        self.Cp = {typ: I.C(*typ) for typ in self.types}
        self.rentp = {typ: I.rent(*typ) for typ in self.types}
        self.feas = [[l for l in range(I.m) if math.isfinite(self.dl[c][l])] for c in range(I.n)]
        # allowances (§3.4)
        self.B0 = float(sum(min([self.Cp[(l, self.cl[c], k)] for l in self.feas[c] for k in range(I.K)] or [0.0])
                            for c in range(I.n)))
        self.Cmin = []
        for j in range(I.J):
            us = {l for c in range(I.n) if self.cl[c] == j for l in self.feas[c]}
            self.Cmin.append(min([self.Cp[(l, j, k)] for l in us for k in range(I.K)] or [INF]))
        nj = np.zeros((I.J, T))
        for t in range(T):
            for c in self.RQ[t]:
                nj[self.cl[c], t] += 1
        self.nj = np.cumsum(nj, axis=1)
        self.Bon = np.array([sum(min(self.q * self.nj[j, t], self.Cmin[j]) for j in range(I.J)) for t in range(T)])
        self.qsig = self.q * float(self.nreq.sum())

    def allowance(self, allow):
        T = self.I.T
        if allow == 'zero':
            return np.zeros(T)
        if allow == 'B0':
            return np.full(T, self.B0)
        if allow == 'cap':
            return np.minimum(self.B0, KAPPA * self.Bon)
        raise ValueError(allow)

    def route_bound(self, t, live_types):
        """sum_e min{q, min_{p in L, j_p = j_e} delta_{e l_p}} (eager definition, item 3)."""
        sites = {}
        for (l, j, k) in live_types:
            sites.setdefault(j, set()).add(l)
        tot = 0.0
        for c in self.RQ[t]:
            b = self.q
            dc = self.dl[c]
            for l in sites.get(self.cl[c], ()):
                if dc[l] < b:
                    b = dc[l]
            tot += b
        return tot


# ------------------------------------------------------------------------------------------ eager experts
class Safe:
    """buys[u]: list of (sid, typ); live[u]: list of (sid, typ, s_p); inc[u] = c_S(u)."""

    def __init__(self, ctx, kind, tag, seed, buys, live, inc, R=None, X=None, switches=0, combine_total=None,
                 sw_slots=()):
        self.kind, self.tag, self.seed = kind, tag, seed
        self.name = kind if tag is None else f'{kind}_{tag}'
        self.buys, self.live = buys, live
        self.inc = np.asarray(inc, float)
        self.C = np.cumsum(self.inc)
        Cp = ctx.Cp
        self.buycost = np.array([sum(Cp[typ] for _, typ in b) for b in buys])
        self.livecost = np.array([sum(Cp[typ] for _, typ, _ in lv) for lv in live])
        self.W = np.array([sum(Cp[typ] for _, typ, sp in lv if sp < u) for u, lv in enumerate(live)])
        self.sigma = self.inc - self.buycost
        self.R, self.X = R, X
        self.switches = switches
        self.sw_slots = list(sw_slots)
        self.combine_total = combine_total

    def Cm1(self, t):
        return float(self.C[t - 1]) if t >= 1 else 0.0


def expert_FB(ctx):
    T = ctx.I.T
    curve = follow_prediction(ctx.I, [])
    return Safe(ctx, 'FB', None, None, [[] for _ in range(T)], [[] for _ in range(T)], curve)


def expert_R(ctx, rnd, tag, seed):
    I = ctx.I
    T = I.T
    buys = [[] for _ in range(T)]
    live = [[] for _ in range(T)]
    for F, t0 in sorted(rnd['opened'].items(), key=lambda x: (x[1], x[0])):
        typ = (F[1], F[2], F[3])
        end = F[4] + int(I.L[F[3]])
        buys[t0].append((F, typ))
        for u in range(t0, min(end, T)):
            live[u].append((F, typ, t0))
    S = Safe(ctx, 'R', tag, seed, buys, live, rnd['curve'])
    S.opened = rnd['opened']
    return S


def expert_FP(ctx, pred_cols, tag='shift6'):
    """FP of C3-T11 (pd.follow_prediction): buy each predicted column (l,j,k,s) at s, live on [s, s+D_k)."""
    I = ctx.I
    T = I.T
    buys = [[] for _ in range(T)]
    live = [[] for _ in range(T)]
    for col in sorted(pred_cols):
        l, j, k, s0 = col
        sid = ('P',) + tuple(col)
        buys[s0].append((sid, (l, j, k)))
        for u in range(s0, min(s0 + int(I.L[k]), T)):
            live[u].append((sid, (l, j, k), s0))
    S = Safe(ctx, 'FP', tag, None, buys, live, follow_prediction(I, pred_cols))
    S.pred = list(pred_cols)
    return S


def predicted_cols(I, shift=6):
    """A late prediction: OPT_eager columns of the activity shifted right by `shift` slots."""
    Ip = I.subset()
    A = np.zeros_like(I.active)
    A[:, shift:] = I.active[:, :-shift]
    Ip.active = A
    return opt_eager_cols(Ip, opt_eager(Ip))


def combine_eager(ctx, X, Y, gamma=G2C, first='cheaper'):
    """The C3-T11 doubling rule of pd.combine for two eager experts X and Y, written as an eager
    algorithm: follow the current expert while its curve is <= gamma times the other's; at a switch
    buy a copy of each lease of the new expert's live set and charge sum_{L_new(t)} C_p + sigma_new(t);
    while following an expert, buy its purchases and charge its increment. The first expert is the
    one with the smaller C(0) ('cheaper', as pd.combine), the larger ('dearer', so that the rule can
    switch at slot 0), or 'X'/'Y'. Returns (buys, live, inc, switch slots)."""
    T = ctx.I.T
    ex = {'X': X, 'Y': Y}
    CC = {'X': np.cumsum(X.inc), 'Y': np.cumsum(Y.inc)}
    if first == 'cheaper':
        cur = 'X' if CC['X'][0] <= CC['Y'][0] else 'Y'
    elif first == 'dearer':
        cur = 'X' if CC['X'][0] > CC['Y'][0] else 'Y'
    else:
        cur = first
    inc = np.zeros(T)
    buys = [[] for _ in range(T)]
    live = [[] for _ in range(T)]
    copy_of, tphase, sw = {}, -1, []
    for t in range(T):
        oth = 'Y' if cur == 'X' else 'X'
        prev = CC[cur][t - 1] if t > 0 else 0.0
        if prev + ex[cur].inc[t] > gamma * CC[oth][t] + 1e-12:
            cur = oth
            sw.append(t)
            Z = ex[cur]
            copy_of, tphase = {}, t
            for (sid, typ, sp) in Z.live[t]:
                csid = ('copy', t, cur, sid)
                copy_of[sid] = csid
                buys[t].append((csid, typ))
            inc[t] = Z.livecost[t] + Z.sigma[t]
        else:
            Z = ex[cur]
            inc[t] = Z.inc[t]
            buys[t] = [((cur, sid), typ) for (sid, typ) in Z.buys[t]]
        for (sid, typ, sp) in ex[cur].live[t]:
            if sid in copy_of:
                live[t].append((copy_of[sid], typ, tphase))
            else:
                assert sp > tphase, 'live lease bought before the phase start without a copy'
                live[t].append(((cur, sid), typ, sp))
    return buys, live, inc, sw


def expert_T11(ctx, FB, R, rnd, gamma=G2C):
    """C3-T11 combination of FB and R; cross-checked against pd.combine (FP with an empty prediction)."""
    buys, live, inc, sws = combine_eager(ctx, FB, R, gamma)
    tot, sw = combine(ctx.I, [], FB.inc, rnd['opened'], R.inc, gamma=gamma)
    return Safe(ctx, 'T11', R.tag, R.seed, buys, live, inc, R=R, X=FB, switches=len(sws),
                combine_total=(tot, sw), sw_slots=sws)


def expert_T11RR(ctx, R1, R2, gamma=G2C):
    """Proposition G4 with two eager experts that both buy leases: T11(R_r1, R_rth)."""
    buys, live, inc, sws = combine_eager(ctx, R1, R2, gamma)
    return Safe(ctx, 'T11RR', None, R1.seed, buys, live, inc, R=R2, X=R1, switches=len(sws), sw_slots=sws)


def expert_T11FP(ctx, FP, R, gamma=G2C, first='cheaper'):
    """C3-T11 itself: FP (late prediction) and R; cross-checked against pd.combine with that prediction.
    first='dearer' starts with the expert of larger C(0) (kind 'T11FPx', no pd.combine cross-check)."""
    buys, live, inc, sws = combine_eager(ctx, FP, R, gamma, first)
    if first == 'cheaper':
        tot, sw = combine(ctx.I, FP.pred, FP.inc, R.opened, R.inc, gamma=gamma)
        return Safe(ctx, 'T11FP', R.tag, R.seed, buys, live, inc, R=R, X=FP, switches=len(sws),
                    combine_total=(tot, sw), sw_slots=sws)
    return Safe(ctx, 'T11FPx', R.tag, R.seed, buys, live, inc, R=R, X=FP, switches=len(sws), sw_slots=sws)


def expert_T11SH(ctx, SH, R, gamma=G2C):
    """Proposition G4 with an eager shadow: T11(SH, R) started with the shadow."""
    buys, live, inc, sws = combine_eager(ctx, SH, R, gamma, 'X')
    return Safe(ctx, 'T11SH', R.tag, R.seed, buys, live, inc, R=R, X=SH, switches=len(sws), sw_slots=sws)


def expert_shadow(ctx, ename, seedkey):
    """Eager shadow E^eag of the inner policy `ename` (greedy or random): E run alone against omega_all,
    where every lease is announced at s + tau_k and dies at s + D_k. P(u) = E's purchases at u, L(u) =
    its leases alive at u, c(u) = its cost at u (no rent under omega_all; the rent is returned and
    checked to be 0)."""
    T = ctx.I.T
    lend = Lender(ctx, 'obl', [np.arange(T)] * ctx.I.m, seedkey)
    g = Guard(ctx, None, 1.0, 'T1', 'zero')
    rec = run(ctx, g, make_E(ctx, ename, g, seedkey), lend, mode='never', record=True)
    buys = [[(('sh', uid), typ) for (uid, typ) in b] for b in rec['buys_u']]
    live = [[(('sh', uid), typ, sp) for (uid, typ, sp) in a] for a in rec['alive_u']]
    S = Safe(ctx, 'SH', ename, None, buys, live, rec['cost'])
    S.rent_total = float(rec['rent'].sum())
    return S


def check_expert(st, ctx, S, where):
    """Eager definition (items 1-3), Lemma G1(a) at every slot, C3-T11/Prop G4 for the combiner."""
    T = ctx.I.T
    D = ctx.D
    prev, bought = set(), set()
    for u in range(T):
        live_ids = {sid for (sid, _, _) in S.live[u]}
        buy_ids = [sid for (sid, _) in S.buys[u]]
        bad = sum(1 for sid in buy_ids if sid not in live_ids)
        bad += sum(1 for (sid, _, sp) in S.live[u] if (sid in set(buy_ids)) != (sp == u))
        st.add('eager def. item 2: P_X(u) in L_X(u), bought at u', bad, 0, where)
        bad = len(live_ids - prev - set(buy_ids)) + len(set(buy_ids) & bought) + (len(buy_ids) - len(set(buy_ids)))
        st.add('eager def. item 2: L_X(u) in L_X(u-1) + P_X(u), each purchase once', bad, 0, where)
        bad = sum(1 for (_, typ, sp) in S.live[u] if not (sp <= u < sp + D[typ[2]]))
        st.add('eager def. item 2: s_p <= u < s_p + D_k for p in L_X(u)', bad, 0, where)
        st.add('eager def. item 3: routing bound over L_X(u) <= sigma_X(u)',
               ctx.route_bound(u, [typ for (_, typ, _) in S.live[u]]), S.sigma[u], where)
        st.add('G1(a): sum_{L_X(t)} C_p == W_X(t) + sum_{P_X(t)} C_p (|diff|)',
               abs(S.livecost[u] - S.W[u] - S.buycost[u]), 0, where)
        st.add('G1(a): W_X(t) <= C_X(t-1)', S.W[u], S.Cm1(u), where)
        bought |= set(buy_ids)
        prev = live_ids
    if S.kind == 'T11':
        tot, sw = S.combine_total
        st.add('G4: eager T11(FB,R) total == pd.combine total (|diff|)', abs(float(S.C[-1]) - tot), 0, where)
        st.add('G4: eager T11(FB,R) switches == pd.combine switches (|diff|)', abs(S.switches - sw), 0, where)
        st.add_arr('G4 / C3-T11: C_T11(t) <= c(gamma\') min{C_FB(t), C_R(t)}', S.C,
                   cfac(G2C) * np.minimum(np.cumsum(ctx.nreq * ctx.q), S.R.C), where)
    if S.kind == 'T11RR':
        st.add_arr('G4: C_T11(R_r1,R_rth)(t) <= c(gamma\') min{C_R_r1(t), C_R_rth(t)}', S.C,
                   cfac(G2C) * np.minimum(S.X.C, S.R.C), where)
    if S.kind == 'T11FP':
        tot, sw = S.combine_total
        st.add('G4: eager T11(FP,R) total == pd.combine total (|diff|)', abs(float(S.C[-1]) - tot), 0, where)
        st.add('G4: eager T11(FP,R) switches == pd.combine switches (|diff|)', abs(S.switches - sw), 0, where)
        st.add_arr('G4 / C3-T11: C_T11(FP,R)(t) <= c(gamma\') min{C_FP(t), C_R(t)}', S.C,
                   cfac(G2C) * np.minimum(S.X.C, S.R.C), where)
    if S.kind == 'T11FPx':
        st.add_arr('G4: T11(FP,R) started with the dearer expert (switch at slot 0 possible): '
                   'C(t) <= c(gamma\') min{C_FP(t), C_R(t)}', S.C, cfac(G2C) * np.minimum(S.X.C, S.R.C), where)
    if S.kind == 'T11SH':
        st.add_arr('G4: T11(eager shadow of greedy, R_r1): C(t) <= c(gamma\') min{C_SH(t), C_R(t)}', S.C,
                   cfac(G2C) * np.minimum(S.X.C, S.R.C), where)
    if S.kind == 'SH':
        st.add('eager shadow: rent of E alone under omega_all (must be 0)', S.rent_total, 0, where)


# ------------------------------------------------------------------------------------------ leases, lenders
_UID = [0]


class Lease:
    __slots__ = ('typ', 'l', 'j', 'k', 's', 'end', 'tau', 'H', 'rent', 'ann', 'death', 'link', 'used', 'uid')

    def __init__(self, ctx, typ, s, link=None):
        _UID[0] += 1
        self.uid = _UID[0]
        l, j, k = typ
        self.typ, self.l, self.j, self.k, self.s = typ, l, j, k, s
        self.end = s + ctx.D[k]
        self.tau, self.H = ctx.tau[k], ctx.H[k]
        self.rent = ctx.rentp[typ]
        self.ann = None
        self.death = None
        self.link = link
        self.used = False


class Lender:
    def __init__(self, ctx, kind, omega=None, seed='0'):
        self.kind = kind
        m = ctx.I.m
        self.R = [set(int(x) for x in o) for o in omega] if kind == 'obl' else [set() for _ in range(m)]
        self.rng = random.Random(seed)

    def _announce(self, t, held):
        R = self.R
        for L in held:
            if L.ann is None and L.s + L.tau <= t and t in R[L.l]:
                L.ann = t
                L.death = t + L.H

    def pre(self, t, held):
        if self.kind == 't4':
            for L in held:
                if L.s + L.tau == t and (L.death is None or L.death > t):
                    self.R[L.l].add(t)
        elif self.kind == 'hold':
            for l in sorted({L.l for L in held if L.ann is None and L.s + L.tau <= t}):
                if self.rng.random() < 0.5:
                    self.R[l].add(t)
        self._announce(t, held)

    def post(self, t, held):
        if self.kind == 't4':
            for L in held:
                if L.s == t and L.tau == 0:
                    self.R[L.l].add(t)
        elif self.kind == 'hold':
            for l in sorted({L.l for L in held if L.s == t and L.tau == 0 and L.ann is None}):
                if self.rng.random() < 0.5:
                    self.R[l].add(t)
        self._announce(t, held)

    def omega(self):
        return [np.array(sorted(r), dtype=int) for r in self.R]


def lender_specs(ctx, seed_key):
    I = ctx.I
    rng = np.random.default_rng(random.Random(seed_key).getrandbits(32))
    return {'obl0': ('obl', [np.array([], dtype=int)] * I.m),
            'obl0.2': ('obl', random_omega(rng, I, 0.2)),
            'eager': ('obl', [np.arange(I.T)] * I.m),
            't4': ('t4', None),
            'hold': ('hold', None)}


def make_lender(ctx, spec, seed):
    kind, omega = spec
    return Lender(ctx, kind, omega, seed)


# ------------------------------------------------------------------------------------------ inner policies
class EFallback:
    def decide(self, t, held, ALG):
        return [], []


class EScript:
    def __init__(self, plan):
        self.plan = plan    # t -> list of types

    def decide(self, t, held, ALG):
        return [], list(self.plan.get(t, []))


def _sites(held, relids):
    s = {}
    for L in held:
        if id(L) not in relids:
            s.setdefault(L.j, set()).add(L.l)
    return s


class EGreedy:
    """lender=None: own-lease feedback (I1). With a lender (I2, public reclaim information), new leases
    avoid the sites announced at slot t (R_l n {t}, observed before acting) when another feasible site exists."""

    def __init__(self, ctx, allowed=None, lender=None):
        self.ctx = ctx
        self.allowed = list(range(ctx.I.K)) if allowed is None else list(allowed)
        self.lender = lender

    def decide(self, t, held, ALG):
        cx = self.ctx
        q = cx.q
        rel = [L for L in held if t >= L.end and not L.used]
        relids = {id(L) for L in rel}
        sites = _sites(held, relids)
        new = []
        for c in cx.RQ[t]:
            j, dc = cx.cl[c], cx.dl[c]
            if any(dc[l] < q for l in sites.get(j, ())):
                continue
            best, arg = q, None
            cand = cx.feas[c]
            if self.lender is not None:
                quiet = [l for l in cand if t not in self.lender.R[l]]
                cand = quiet or cand
            for l in cand:
                for k in self.allowed:
                    v = cx.Cp[(l, j, k)] / cx.D[k] + dc[l]
                    if v < best - 1e-12:
                        best, arg = v, (l, j, k)
            if arg is not None:
                new.append(arg)
                sites.setdefault(j, set()).add(arg[0])
        return rel, new


class ERandom:
    def __init__(self, ctx, seed):
        self.ctx = ctx
        self.rng = random.Random(seed)

    def decide(self, t, held, ALG):
        cx, rng = self.ctx, self.rng
        q = cx.q
        rel = [L for L in held if rng.random() < 0.15]
        relids = {id(L) for L in rel}
        sites = _sites(held, relids)
        new = []
        for c in cx.RQ[t]:
            j, dc = cx.cl[c], cx.dl[c]
            if any(dc[l] < q for l in sites.get(j, ())):
                continue
            if cx.feas[c] and rng.random() < 0.5:
                l = rng.choice(cx.feas[c])
                k = rng.randrange(cx.I.K)
                new.append((l, j, k))
                sites.setdefault(j, set()).add(l)
        if rng.random() < 0.15:
            new.append(rng.choice(cx.types))
        return rel, new


class EAdv:
    """Scripted adversary that knows the guard: fills the test threshold every slot."""

    def __init__(self, ctx, guard, trip=None):
        self.ctx, self.g, self.trip = ctx, guard, trip
        self.order = sorted(ctx.types, key=lambda typ: (-ctx.Cp[typ], typ))

    def decide(self, t, held, ALG):
        cx, g = self.ctx, self.g
        thr = float(g.thr[t])
        eps = 1e-9 * (1.0 + abs(thr))
        rel = []
        if g.test in ('T0', 'T0g'):
            if g.test == 'T0':
                base = ALG + cx.q * len(cx.RQ[t])
            else:   # T0g: service bound over the held leases inside their window; new leases only lower it
                base = ALG + cx.route_bound(t, [L.typ for L in held if t < L.end])
            past = [L for L in held if t >= L.end]
            rent = sum(L.rent for L in past)
            if base + rent > thr - eps:
                for L in sorted(past, key=lambda L: -L.rent):
                    if base + rent <= thr - eps:
                        break
                    rel.append(L)
                    rent -= L.rent
            budget = thr - eps - base - rent
        else:
            budget = thr - eps - ALG
        new = []
        for typ in self.order:
            c = cx.Cp[typ]
            while budget >= c and len(new) < 12:
                new.append(typ)
                budget -= c
        if self.trip is not None and t == self.trip:
            new.append(self.order[0])
        return rel, new


class EAdvHold(EAdv):
    """K0 check only: adv_fill without its releases. Each slot it buys the most expensive lease types up to the test
    threshold (none once the rent of its leases past their windows has used up the slack) and never releases, so
    its leases pay rent while alive; E's list then fails, and the ladder's P0 (when it exists) keeps those leases
    while K0 releases them."""

    def decide(self, t, held, ALG):
        cx, g = self.ctx, self.g
        thr = float(g.thr[t])
        eps = 1e-9 * (1.0 + abs(thr))
        if g.test in ('T0', 'T0g'):
            base = ALG + (cx.q * len(cx.RQ[t]) if g.test == 'T0'
                          else cx.route_bound(t, [L.typ for L in held if t < L.end]))
            budget = thr - eps - base - sum(L.rent for L in held if t >= L.end)
        else:
            budget = thr - eps - ALG
        new = []
        for typ in self.order:
            c = cx.Cp[typ]
            while budget >= c and len(new) < 12:
                new.append(typ)
                budget -= c
        return [], new


class ETwin:
    """Executes the eager S as in Lemma G1(b) from slot 0: buys P_S(u) at u (P_S(0) = L_S(0)) and releases
    every lease at its window end. Reads S's realized purchases, so it shares R's coins."""

    def __init__(self, S):
        self.S = S

    def decide(self, t, held, ALG):
        return [L for L in held if t >= L.end], [typ for (_, typ) in self.S.buys[t]]


def make_E(ctx, ename, guard, seed, trip=None, lender=None):
    if ename == 'fb':
        return EFallback()
    if ename == 'twin':
        return ETwin(guard.S)
    if ename == 'greedy':
        return EGreedy(ctx)
    if ename == 'greedy_i2':
        return EGreedy(ctx, lender=lender)
    if ename == 'greedy_rev':
        return EGreedy(ctx, allowed=[0])
    if ename == 'random':
        return ERandom(ctx, seed)
    if ename == 'adv_fill':
        return EAdv(ctx, guard, None)
    if ename == 'adv_trip':
        return EAdv(ctx, guard, trip)
    if ename == 'g6i':
        return EScript({0: [(0, 0, 0)] * ctx.I.n})
    if ename == 'adv_hold':
        return EAdvHold(ctx, guard, None)
    raise ValueError(ename)


# ------------------------------------------------------------------------------------------ guard
class Guard:
    def __init__(self, ctx, S, gamma, test, allow):
        self.S, self.gamma, self.test, self.allow = S, gamma, test, allow
        self.B = ctx.allowance(allow)
        self.thr = (gamma * S.C + self.B) if S is not None else np.full(ctx.I.T, INF)


def route(ctx, alive, reqs):
    first = {}
    for L in alive:
        key = (L.j, L.l)
        if key not in first:
            first[key] = L
    by_j = {}
    for (j, l), L in first.items():
        by_j.setdefault(j, []).append((l, L))
    serv, used = 0.0, set()
    q = ctx.q
    for c in reqs:
        best, arg = q, None
        dc = ctx.dl[c]
        for (l, L) in by_j.get(ctx.cl[c], ()):
            if dc[l] < best:
                best, arg = dc[l], L
        serv += best
        if arg is not None:
            used.add(id(arg))
    return serv, used


def run(ctx, guard, E, lender, mode='test', t_force=None, record=False):
    """mode 'test': the guard; 'never': E alone; 'force': execute E for t < t_force, abort at t_force.
    record=True also returns the purchases (uid, typ) and the alive leases (uid, typ, s) of every slot."""
    T = ctx.I.T
    S = guard.S
    q = ctx.q
    held = []
    ALG = 0.0
    cum, buy, rent, serv = np.zeros(T), np.zeros(T), np.zeros(T), np.zeros(T)
    ahat = np.full(T, np.nan)
    log = []
    ta = None
    miss = 0
    buys_u, alive_u = [], []
    for t in range(T):
        newleases = []
        lender.pre(t, held)
        held = [L for L in held if L.death is None or L.death > t]
        reqs = ctx.RQ[t]
        if ta is None:
            rel, new = E.decide(t, held, ALG)
            relids = {id(L) for L in rel}
            keep = [L for L in held if id(L) not in relids]
            pE = 0.0
            for typ in new:
                pE += ctx.Cp[typ]
            if guard.test in ('T0', 'T0g'):
                rb = 0.0
                for L in keep:
                    if t >= L.end:
                        rb += L.rent
                if guard.test == 'T0':
                    a = ALG + pE + rb + q * len(reqs)
                else:   # T0g: route over the held leases inside their prepaid window (alive for every lender)
                    a = ALG + pE + rb + ctx.route_bound(t, [L.typ for L in keep if t < L.end] + list(new))
            else:
                a = ALG + pE
            if mode == 'never':
                ok = True
            elif mode == 'force':
                ok = t < t_force
            else:
                thr = float(guard.thr[t])
                ok = a <= thr + 1e-12 * (1.0 + abs(thr))
            if ok:
                ahat[t] = a
                newleases = [Lease(ctx, typ, t) for typ in new]
                held = keep + newleases
                buy[t] = pE
                log.extend((t, typ) for typ in new)
            else:
                ta = t
        if ta is not None:
            held = [L for L in held if t < L.end]          # Lemma G1(b)(3): release at window end
            src = S.live[t] if t == ta else S.buys[t]       # (1) copies of L_S(t_a); (2) P_S(u)
            newL = [Lease(ctx, x[1], t, link=x[0]) for x in src]
            held = held + newL
            b = 0.0
            for L in newL:
                b += ctx.Cp[L.typ]
            buy[t] = b
            log.extend((t, L.typ) for L in newL)
        lender.post(t, held)
        alive = [L for L in held if L.death is None or L.death > t]
        if record:
            buys_u.append([(L.uid, L.typ) for L in newleases])
            alive_u.append([(L.uid, L.typ, L.s) for L in alive])
        r = 0.0
        for L in alive:
            if t >= L.end:
                r += L.rent
        sv, used = route(ctx, alive, reqs)
        for L in held:
            L.used = id(L) in used
        rent[t], serv[t] = r, sv
        ALG += buy[t] + r + sv
        cum[t] = ALG
        if ta is not None:
            bylink = {L.link: L for L in alive if L.link is not None}
            for (sid, typ, sp) in S.live[t]:
                L = bylink.get(sid)
                if L is None or L.typ != typ:
                    miss += 1
    out = dict(cum=cum, buy=buy, rent=rent, serv=serv, ahat=ahat, ta=ta, miss=miss, log=log,
               cost=buy + rent + serv, omega=lender.omega())
    if record:
        out['buys_u'], out['alive_u'] = buys_u, alive_u
    return out


# ------------------------------------------------------------------------------------------ checks per run
def g1_checks(st, S, rec, where):
    ta = rec['ta']
    T = len(rec['cum'])
    st.add('impl. G1(a): real copy purchase at t_a == sum_{L_S(t_a)} C_p (|diff|)',
           abs(rec['buy'][ta] - S.livecost[ta]), 0, where)
    st.add('G1(b): cost(t_a) <= sum_{L_S(t_a)} C_p + sigma_S(t_a)', rec['cost'][ta],
           S.livecost[ta] + S.sigma[ta], where)
    if ta + 1 < T:
        st.add_arr('G1(b): cost(u) <= c_S(u) for u > t_a', rec['cost'][ta + 1:], S.inc[ta + 1:], where)
    st.add('G1(b): rent paid at slots >= t_a', float(rec['rent'][ta:].sum()), 0, where)
    st.add('G1(b): p in L_S(u), u >= t_a, without an alive linked lease of its type (count)', rec['miss'], 0, where)
    st.add('G1(b): S-mode cost ALG(T)-ALG(t_a-1) <= W_S(t_a)+C_S(T)-C_S(t_a-1)',
           rec['cum'][-1] - (rec['cum'][ta - 1] if ta >= 1 else 0.0),
           S.W[ta] + S.C[-1] - S.Cm1(ta), where)


def g2_checks(st, ctx, guard, rec, where, alone=None):
    S, g, B = guard.S, guard.gamma, guard.B
    T = ctx.I.T
    ALG = float(rec['cum'][-1])
    ta = rec['ta']
    nex = T if ta is None else ta
    cum = rec['cum']
    mvals = np.maximum(0.0, cum[:nex] - rec['ahat'][:nex]) if nex > 0 else np.zeros(0)
    M = float(mvals.max()) if nex > 0 else 0.0
    if nex > 0:
        if guard.test in SOUND:
            st.add_arr(f'{guard.test}: ALG(t) <= ahat(t) at executed slots (m == 0)', cum[:nex], rec['ahat'][:nex], where)
        else:
            st.add_arr('impl. T1: m(t) <= rent(t) + service(t) at executed slots (equality by definition)', mvals,
                       rec['rent'][:nex] + rec['serv'][:nex], where)
        st.add_arr('impl. G2 E-mode: ALG(t) <= gamma C_S(t) + B(t) + m(t) at executed slots', cum[:nex],
                   g * S.C[:nex] + B[:nex] + mvals, where)
    if ta is None:
        st.add('impl. G2(a): no abort: ALG(T) <= gamma C_S(T) + B(T) + m(T)', ALG, g * S.C[-1] + B[-1] + mvals[-1], where)
        if alone is not None:
            st.add('impl. G2(a): no abort: max_t |ALG(t) - E alone(t)|', float(np.max(np.abs(cum - alone['cum']))), 0, where)
            st.add('impl. G2(a): no abort: purchase log differs from E alone (0/1)', int(rec['log'] != alone['log']), 0, where)
        if g == 1.0 and guard.test in SOUND:
            st.add('G2(c) gamma=1, sound test (T0, T0g), no abort: ALG(T) <= C_S(T) + B(T)', ALG, S.C[-1] + B[-1], where)
    else:
        mp_ = float(mvals[ta - 1]) if ta >= 1 else 0.0
        Cp_, Bp, Ap = S.Cm1(ta), (float(B[ta - 1]) if ta >= 1 else 0.0), (float(cum[ta - 1]) if ta >= 1 else 0.0)
        W = float(S.W[ta])
        rhs1 = S.C[-1] + (g - 1.0) * Cp_ + W + Bp + mp_
        rhs2 = (1.0 + g) * S.C[-1] + B[-1] + mp_
        st.add('G2(b) abort: ALG(T) <= C_S(T)+(gamma-1)C_S(t_a-1)+W_S(t_a)+B(t_a-1)+m(t_a-1)', ALG, rhs1, where)
        st.add('G2(b) abort: first RHS <= (1+gamma)C_S(T)+B(T)+m(t_a-1)', rhs1, rhs2, where)
        st.add('G2(b) abort: ALG(T) <= (1+gamma)C_S(T)+B(T)+m(t_a-1)', ALG, rhs2, where)
        if ta >= 1:
            st.add('impl. G2(b) abort: ALG(t_a-1) <= gamma C_S(t_a-1)+B(t_a-1)+m(t_a-1)', Ap, g * Cp_ + Bp + mp_, where)
        if g == 1.0 and guard.test in SOUND:
            st.add('G2(c) gamma=1, sound test (T0, T0g), abort: ALG(T) <= C_S(T)+W_S(t_a)+B(t_a-1)', ALG,
                   S.C[-1] + W + Bp, where)
        g1_checks(st, S, rec, where)
    st.add('G2(c): ALG(T) <= (1+gamma)C_S(T) + B(T) + M', ALG, (1.0 + g) * S.C[-1] + B[-1] + M, where)
    return M


def g3_checks(st, ctx, guard, ALG, OPT, where):
    """Corollary G3 (a sound test T0 or T0g, B(t) <= kappa B_on(t)); returns the bound values for the mean checks."""
    kap = kappa_of(guard.allow)
    if guard.test not in SOUND or kap is None:
        return None
    S, g = guard.S, guard.gamma
    BonT = float(ctx.Bon[-1])
    aN = alpha_N(ctx.I)
    out = {}
    if S.kind == 'R':
        st.add('G3(a)/(c) pathwise: ALG <= (1+gamma) C_R(T) + kappa B_on(T)', ALG, (1 + g) * S.C[-1] + kap * BonT, where)
        if S.tag == 'rth':
            out['a'] = ((1 + g) * aN + kap) * OPT
            st.add('G3(a): ALG <= ((1+gamma) alpha_N + kappa) OPT_eager (pathwise)', ALG, out['a'], where)
    elif S.kind == 'T11':
        mn = min(ctx.qsig, float(S.R.C[-1]))
        st.add('G3(b)/(c) pathwise: ALG <= (1+gamma) c(gamma\') min{C_FB(T),C_R(T)} + kappa B_on(T)', ALG,
               (1 + g) * cfac(G2C) * mn + kap * BonT, where)
        if S.tag == 'rth':
            out['b'] = ((1 + g) * cfac(G2C) + kap) * min(ctx.qsig, aN * OPT)
            st.add('G3(b): ALG <= ((1+gamma) c(gamma\') + kappa) min{q|sigma|, alpha_N OPT_eager} (pathwise)',
                   ALG, out['b'], where)
    return out


def g5_checks(st, ctx, OPT, lp0, where):
    Bon = ctx.Bon
    st.add('G5: B_on nondecreasing (max decrease)', float(np.max(np.maximum(0.0, Bon[:-1] - Bon[1:]))) if len(Bon) > 1 else 0.0, 0, where)
    st.add('G5: B_on(T) <= q|sigma|', Bon[-1], ctx.qsig, where)
    st.add('G5: B_on(T) <= OPT_eager (MILP dual bound)', Bon[-1], OPT, where)
    st.add('G5: B_on(T) <= LP relaxation of OPT(sigma, no announcement) (<= OPT(sigma,omega) for all omega)',
           Bon[-1], lp0, where)
    B = ctx.allowance('cap')
    st.add('G5: capped B nondecreasing (max decrease)', float(np.max(np.maximum(0.0, B[:-1] - B[1:]))) if len(B) > 1 else 0.0, 0, where)
    st.add_arr('impl. G5: capped B(t) <= kappa B_on(t)', B, KAPPA * Bon, where)


# ------------------------------------------------------------------------------------------ K0 check (MS5b, P6)
GUARD_TOL = 1e-12        # code/sim guard.py: a list passes if ahat + R <= rhs + GUARD_TOL max(1, |rhs|)
CERT_TOL = 1e-9          # q44_study.CERT_TOL, the scale of the code-level clause's (R2)
U53 = Fraction(1, 2 ** 53)
K0_GAMMAS = (1.0, G2C, 3.0)
K0_TESTS = ('T0g', 'T0')
K0_NEG_GAMMA = 0.25


class XScale:
    """Exact images of the instance's float data as integers scaled by 2**sh (every float is dyadic, so
    v * 2**sh is an integer for sh large enough): sums of these integers are the exact sums of the floats."""

    def __init__(self, ctx):
        vals = [ctx.q] + list(ctx.Cp.values()) + list(ctx.rentp.values()) + \
            [x for row in ctx.dl for x in row if math.isfinite(x)]
        self.sh = max([float(v).as_integer_ratio()[1].bit_length() - 1 for v in vals] + [0])
        self.one = 1 << self.sh
        self.q = self.i(ctx.q)
        self.Cp = {typ: self.i(v) for typ, v in ctx.Cp.items()}
        self.rentp = {typ: self.i(v) for typ, v in ctx.rentp.items()}
        self.dl = [[(self.i(x) if math.isfinite(x) else None) for x in row] for row in ctx.dl]
        self.qsum = [self.q * len(r) for r in ctx.RQ]
        self.qsum_f = []
        for r in ctx.RQ:
            v = 0.0
            for _ in r:
                v += ctx.q
            self.qsum_f.append(v)

    def i(self, v):
        n, d = float(v).as_integer_ratio()
        assert self.one % d == 0
        return n * (self.one // d)

    def frac(self, x):
        return Fraction(x, self.one)


def k0_follows_fb(S, FB):
    """S follows FB at t (after S's step at t): FB always; T11(FB, R) starts with the cheaper expert at slot 0
    (pd.combine's rule, combine_eager 'cheaper') and toggles at its switch slots; R never."""
    T = len(S.inc)
    if S.kind == 'FB':
        return [True] * T
    if S.kind != 'T11':
        return [False] * T
    cur = bool(FB.C[0] <= S.R.C[0])
    sw = set(S.sw_slots)
    out = []
    for t in range(T):
        if t in sw:
            cur = not cur
        out.append(cur)
    return out


class K0Lim:
    """Per (S, gamma, allowance): the exact limit rhs(t) + tol(t), rhs = gamma C_S(t) + B(t) with C_S(t) the exact
    sum of S's float increments, tol = GUARD_TOL max(1, |rhs|) (as an integer floor on the scale 2**sh, so that an
    integer test value passes iff it is <= the exact limit), the code's float64 limit (y = fl(gamma C_S), rhs =
    fl(y + B), tau = fl(GUARD_TOL max(1,|rhs|)), lim = fl(rhs + tau), C_S the float running total), and the
    condition of Remark (what P uses of FB), gamma c_S(t) + B(t) - B(t-1) >= q n(t), in exact arithmetic."""

    def __init__(self, ctx, S, gamma, B):
        xs = ctx.xs
        g = Fraction(gamma)
        CS = Fraction(0)
        Bp = Fraction(0)
        self.lim_i, self.cond, self.rhs_x, self.tol_x, self.rhs_i40 = [], [], [], [], []
        self.f = []          # code float64 values per slot: (C_S, B, y, rhs, tau, lim)
        for t in range(ctx.I.T):
            c = Fraction(float(S.inc[t]))
            CS += c
            Bt = Fraction(float(B[t]))
            rhs = g * CS + Bt
            tol = Fraction(GUARD_TOL) * max(Fraction(1), abs(rhs))
            lim = rhs + tol
            self.lim_i.append((lim.numerator << xs.sh) // lim.denominator)
            self.rhs_i40.append((rhs.numerator << (xs.sh + 40)) // rhs.denominator)
            self.rhs_x.append(rhs)
            self.tol_x.append(tol)
            self.cond.append(g * c + Bt - Bp >= xs.frac(xs.q * int(ctx.nreq[t])))
            Bp = Bt
            CSf, Bf = float(S.C[t]), float(B[t])
            y = gamma * CSf
            rf = y + Bf
            tau = GUARD_TOL * max(1.0, abs(rf))
            self.f.append((CSf, Bf, y, rf, tau, rf + tau))
        self.lim_f = [x[5] for x in self.f]
        self.CS_T, self.B_T = CS, Bp


def k0_ladder(held, rel, new):
    """Definition R (R1) on the core. A = E's releases, then its purchases (the core's slot order). E: A; P1_n' for
    n' in {n_b-1, n_b/2, n_b/4, 1} minus {0, n_b}, decreasing, if n_b >= 2: the first n' purchases and the releases
    of held leases, in A's order; P0 if fewer than |A| actions name a held lease: those releases; K0: a release of
    every held lease, in increasing id. Returns [(name, releases, purchases)]."""
    A = [('R', L) for L in rel] + [('B', typ) for typ in new]
    hid = {id(L) for L in held}
    IB = [i for i, a in enumerate(A) if a[0] == 'B']
    Im = [i for i, a in enumerate(A) if a[0] == 'R' and id(a[1]) in hid]
    nb = len(IB)

    def split(idx):
        return [A[i][1] for i in idx if A[i][0] == 'R'], [A[i][1] for i in idx if A[i][0] == 'B']

    out = [('E', list(rel), list(new))]
    if nb >= 2:
        for npr in sorted({nb - 1, nb // 2, nb // 4, 1} - {0, nb}, reverse=True):
            out.append(('P1',) + split(sorted(IB[:npr] + Im)))
    if len(Im) < len(A):
        out.append(('P0',) + split(Im))
    out.append(('K0', sorted(held, key=lambda L: L.uid), []))
    return out


def k0_bound(ctx, t, typs, dl, q, zero, qsum):
    """Core T0g service bound sum_e min{q, min delta_{e l}} over the given lease types, with the selection made on
    the float routing costs (exact) and the selected values summed in the mode's arithmetic (route_bound's order).
    qsum: the value without leases (q added once per request in that order)."""
    if not typs:
        return qsum
    sites = {}
    for (l, j, k) in typs:
        sites.setdefault(j, set()).add(l)
    tot = zero
    for c in ctx.RQ[t]:
        b, v = ctx.q, q
        dcf, dcm = ctx.dl[c], dl[c]
        for l in sites.get(ctx.cl[c], ()):
            if dcf[l] < b:
                b, v = dcf[l], dcm[l]
        tot += v
    return tot


def k0_serve(ctx, alive, reqs, dl, q, zero, qsum):
    """route() in the mode's arithmetic: min-cost service over the alive leases and the set of leases used."""
    if not alive:
        return qsum, set()
    first = {}
    for L in alive:
        first.setdefault((L.j, L.l), L)
    by_j = {}
    for (j, l), L in first.items():
        by_j.setdefault(j, []).append((l, L))
    serv, used = zero, set()
    for c in reqs:
        b, v, arg = ctx.q, q, None
        dcf, dcm = ctx.dl[c], dl[c]
        for (l, L) in by_j.get(ctx.cl[c], ()):
            if dcf[l] < b:
                b, v, arg = dcf[l], dcm[l], L
        serv += v
        if arg is not None:
            used.add(id(arg))
    return serv, used


def run_proj(ctx, S, gamma, test, allow, ename, lspec, keyroot, lname, lim, exact, fol, trip=None, E=None):
    """The projected guard (A8P's rule, C3 §9 and Definition R) on the core, written in this script: at slot t in
    mode E it evaluates the ladder of E's list in order under the test and executes the first list Y with
    ahat_Y(t) <= rhs(t) + tol(t); if none passes it aborts and follows Lemma G1(b) with X = S from t_a (as run()).
    exact=True: every cost is an exact integer on the scale 2**sh and the comparison is exact (lim.lim_i);
    exact=False: the code's float64 arithmetic (lim.f). Records per slot t <= t_a (every earlier slot executed)
    K0's test value ALG(t-1) + q n(t) (T0, T0g) or ALG(t-1) (T1) against the limit, the executed candidate, and
    ALG(t) against ahat(t) at executed slots."""
    T = ctx.I.T
    xs = ctx.xs
    guard = Guard(ctx, S, gamma, test, allow)               # what E sees (adv_fill reads thr and the test)
    lender = make_lender(ctx, lspec, f'{keyroot}|{lname}')
    if E is None:
        E = make_E(ctx, ename, guard, f'{keyroot}|{lname}|{ename}', trip, lender)
    if exact:
        q, Cp, rentp, dl, zero = xs.q, xs.Cp, xs.rentp, xs.dl, 0
        LIM, QS = lim.lim_i, xs.qsum
    else:
        q, Cp, rentp, dl, zero = ctx.q, ctx.Cp, ctx.rentp, ctx.dl, 0.0
        LIM, QS = lim.lim_f, xs.qsum_f
    held = []
    ALG = zero
    ta = None
    names = []
    k0 = []           # (t, value, passes) for t <= t_a
    mrec = []         # (ALG(t), ahat(t)) at executed slots
    flog = []         # float runs: per executed slot (ALG(t-1), name, p, rent, bound, ahat)
    for t in range(T):
        lender.pre(t, held)
        held = [L for L in held if L.death is None or L.death > t]
        reqs = ctx.RQ[t]
        nreq = len(reqs)
        bc = zero
        if ta is None:
            if test == 'T1':
                kv = ALG
            elif test == 'T0':
                kv = ALG + zero + zero + q * nreq
            else:
                kv = ALG + zero + zero + QS[t]
            k0.append((t, kv, kv <= LIM[t]))
            rel, new = E.decide(t, held, ALG if not exact else ALG / xs.one)
            sel = None
            for (nm, rl, buys) in k0_ladder(held, rel, new):
                relids = {id(L) for L in rl}
                keep = [L for L in held if id(L) not in relids]
                p = zero
                for typ in buys:
                    p += Cp[typ]
                rb = sb = zero
                if test == 'T1':
                    a = ALG + p
                else:
                    for L in keep:
                        if t >= L.end:
                            rb += rentp[L.typ]
                    if test == 'T0':
                        sb = q * nreq
                    else:
                        sb = k0_bound(ctx, t, [L.typ for L in keep if t < L.end] + list(buys), dl, q, zero, QS[t])
                    a = ALG + p + rb + sb
                if a <= LIM[t]:
                    sel = (nm, keep, buys, p, rb, sb, a)
                    break
            if sel is None:
                ta = t
            else:
                nm, keep, buys, p, rb, sb, a = sel
                names.append(nm)
                if not exact:
                    flog.append((ALG, nm, p, rb, sb, a))
                held = keep + [Lease(ctx, typ, t) for typ in buys]
                bc = p
        if ta is not None:
            held = [L for L in held if t < L.end]           # Lemma G1(b)(3)
            src = S.live[t] if t == ta else S.buys[t]
            newL = [Lease(ctx, x[1], t, link=x[0]) for x in src]
            held = held + newL
            for L in newL:
                bc += Cp[L.typ]
        lender.post(t, held)
        alive = [L for L in held if L.death is None or L.death > t]
        r = zero
        for L in alive:
            if t >= L.end:
                r += rentp[L.typ]
        sv, used = k0_serve(ctx, alive, reqs, dl, q, zero, QS[t])
        for L in held:
            L.used = id(L) in used
        ALG = ALG + (bc + r + sv)
        if ta is None:
            mrec.append((ALG, sel[6]))
    return dict(ta=ta, names=names, k0=k0, mrec=mrec, flog=flog, ALG=ALG, fol=fol, exact=exact)


def k0_clause(ctx, S, gamma, lim, rec, FB):
    """'Deciding an abort from one run' (C3 §9) on the core, for a float64 abort at t_a with S on FB: from the
    logged float64 values (hex) computes, in exact rational arithmetic, X(t_a) = ahat_K0(t_a) - lim(t_a),
    m(t_a-1) and the terms of the clause's identity (R(t-1) = S_K0 = 0 and sigma(t-1) = fl(ahat(t-1) + 0.0) on the
    core; Q(t) = FB's float increment), checks that the terms add up to X(t_a) exactly, and evaluates
    (R1) X <= m(t_a-1) + (11+5k) u ahat_K0(t_a), k = n + phi(J+1) + 2 with phi = 1, and
    (R2) m(t_a-1) <= CERT_TOL max(1, ALG(t_a-1))."""
    F = Fraction
    ta = rec['ta']
    k0v = rec['k0'][ta][1]
    ALG1 = rec['mrec'][ta - 1][0] if ta >= 1 else 0.0
    CS, Bt, y, rhs, tau, limt = lim.f[ta]
    G = ctx.xs.qsum_f[ta]
    Q = float(FB.inc[ta])
    if ta >= 1:
        A2, _, p1, r1, g1, ah1 = rec['flog'][ta - 1]
        sig1 = ah1 + 0.0
        CS1, B1, y1, rhs1, tau1, lim1 = lim.f[ta - 1]
    else:
        A2 = p1 = r1 = g1 = ah1 = sig1 = CS1 = B1 = y1 = rhs1 = tau1 = lim1 = 0.0
    g = F(gamma)
    X = F(k0v) - F(limt)
    m1 = max(F(0), F(ALG1) - F(ah1))
    terms = dict(
        alg_minus_ahat=F(ALG1) - F(ah1), sigma_minus_lim=F(sig1) - F(lim1), tau_diff=F(tau1) - F(tau),
        gamma_m1_Q=-(g - 1) * F(Q), dB=-(F(Bt) - F(B1)), S_minus_R=F(0), G_minus_Q=F(G) - F(Q),
        eps_a=F(k0v) - F(ALG1) - F(G) - F(0), eps_sigma=F(ah1) + F(0) - F(sig1),
        eps_lim1=F(lim1) - F(rhs1) - F(tau1), eps_lim=-(F(limt) - F(rhs) - F(tau)),
        gamma_eps_C=-g * (F(CS) - F(CS1) - F(Q)), eps_rhs=-(F(rhs) - F(y) - F(Bt)), eps_rhs1=F(rhs1) - F(y1) - F(B1),
        eps_y=-(F(y) - g * F(CS)), eps_y1=F(y1) - g * F(CS1))
    tot = sum(terms.values(), F(0))
    kk = ctx.I.n + 1 * (ctx.I.J + 1) + 2
    r1ok = X <= m1 + (11 + 5 * kk) * U53 * F(k0v)
    r2ok = m1 <= F(CERT_TOL) * max(F(1), F(ALG1))
    logv = {'t_a': ta, 'ALG(t_a-2)': float(A2).hex(), 'p(t_a-1)': float(p1).hex(), 'rent(t_a-1)': float(r1).hex(),
            'G(t_a-1)': float(g1).hex(), 'ahat(t_a-1)': float(ah1).hex(), 'sigma(t_a-1)': float(sig1).hex(),
            'C_S,B,y,rhs,tau,lim(t_a-1)': [float(v).hex() for v in (CS1, B1, y1, rhs1, tau1, lim1)],
            'ALG(t_a-1)': float(ALG1).hex(), 'Q(t_a)': float(Q).hex(),
            'C_S,B,y,rhs,tau,lim(t_a)': [float(v).hex() for v in (CS, Bt, y, rhs, tau, limt)],
            'K0 p,rent,G,S,R,ahat': [float(v).hex() for v in (0.0, 0.0, G, 0.0, 0.0, k0v)], 'n,J,phi': [ctx.I.n, ctx.I.J, 1]}
    return dict(X=float(X), m=float(m1), sum_ok=(tot == X), R1=bool(r1ok), R2=bool(r2ok),
                rounding=bool(r1ok and r2ok), log=logv, terms={k: float(v) for k, v in terms.items()})


class K0Res:
    """Aggregates of the K0 check: claims (exact; violation = a failed exact comparison or a positive count),
    negative controls (evals, failures, aborts), executed candidates, aborts, float64 aborts and their clause."""

    def __init__(self):
        self.claims = {}     # name -> [evals, viol, min slack (float of exact), min rel slack, where]
        self.neg = {}        # name -> [evals, fails, aborts, runs, where of first failure]
        self.cands = {}
        self.cnt = {}
        self.mx = {}
        self.clauses = []

    def claim(self, name, slack, rel, where, viol):
        e = self.claims.setdefault(name, [0, 0, INF, INF, None])
        e[0] += 1
        e[1] += int(viol)
        if rel < e[3]:
            e[2], e[3], e[4] = slack, rel, where

    def c(self, key, v=1):
        self.cnt[key] = self.cnt.get(key, 0) + v

    def m(self, key, v):
        self.mx[key] = max(self.mx.get(key, -INF), v)

    def negadd(self, name, evals, fails, aborts, where):
        e = self.neg.setdefault(name, [0, 0, 0, 0, None])
        e[0] += evals; e[1] += fails; e[2] += aborts; e[3] += 1
        if fails and e[4] is None:
            e[4] = where

    def merge(self, o):
        for k, v in o['claims'].items():
            e = self.claims.setdefault(k, [0, 0, INF, INF, None])
            e[0] += v[0]; e[1] += v[1]
            if v[3] < e[3]:
                e[2], e[3], e[4] = v[2], v[3], v[4]
        for k, v in o['neg'].items():
            e = self.neg.setdefault(k, [0, 0, 0, 0, None])
            for i in range(4):
                e[i] += v[i]
            if e[4] is None:
                e[4] = v[4]
        for k, v in o['cands'].items():
            self.cands[k] = self.cands.get(k, 0) + v
        for k, v in o['cnt'].items():
            self.cnt[k] = self.cnt.get(k, 0) + v
        for k, v in o['mx'].items():
            self.mx[k] = max(self.mx.get(k, -INF), v)
        self.clauses += o['clauses']

    def dump(self):
        return dict(claims=self.claims, neg=self.neg, cands=self.cands, cnt=self.cnt, mx=self.mx, clauses=self.clauses)


def k0_eval_exact(res, ctx, S, gamma, test, lim, rec, where, main):
    """Claims on one exact run. main: S in {FB, T11}, gamma >= 1, T0g/T0 (Proposition P's hypotheses)."""
    xs = ctx.xs
    fol, ta = rec['fol'], rec['ta']
    for (t, kv, ok) in rec['k0']:
        slf = (lim.rhs_i40[t] - (kv << 40)) / (xs.one << 40)     # rhs(t) - K0's value, exact to 2^-(sh+40)
        rel = slf / max(1.0, abs(float(lim.rhs_x[t])))
        if test != 'T1' and lim.cond[t]:
            res.claim('Remark (what P uses of FB): K0 passes where gamma c_S(t)+B(t)-B(t-1) >= q n(t), any S and gamma',
                      slf, rel, f'{where} t={t}', not ok)
        if main and fol[t]:
            res.claim('P(c): K0 passes, ALG(t-1)+q n(t) <= gamma C_S(t)+B(t)+tol(t) (S on FB, gamma >= 1)',
                      slf, rel, f'{where} t={t}', not ok)
    if test != 'T1':
        for t, (A, a) in enumerate(rec['mrec']):
            sl = (a - A) / xs.one
            res.claim('P.1 (core): ALG(t) <= ahat(t) at every executed slot, whichever candidate (m == 0)',
                      sl, sl / max(1.0, abs(a / xs.one)), f'{where} t={t} cand={rec["names"][t]}', A > a)
        g2 = (1 + Fraction(gamma)) * lim.CS_T + lim.B_T - xs.frac(rec['ALG'])
        res.claim('G2(c) for the projected guard (Remark R(e)): ALG(T) <= (1+gamma) C_S(T) + B(T)', float(g2),
                  float(g2) / max(1.0, float(lim.CS_T)), where, g2 < 0)
    if main:
        onfb = ta is not None and fol[ta]
        res.claim(f'P(c): aborts at a slot where S follows FB, S = {"FB" if S.kind == "FB" else "T11(FB,R)"} (count)',
                  -float(onfb), -float(onfb), where, onfb)
        for nm in rec['names']:
            res.cands[nm] = res.cands.get(nm, 0) + 1
        res.c('runs main exact')
        res.c('runs main exact with a projected slot', int(any(nm != 'E' for nm in rec['names'])))
        res.c('slots K0-checked on FB (main exact)', sum(1 for (t, _, _) in rec['k0'] if fol[t]))
        if ta is not None:
            res.c(f'aborts main exact {S.kind} at {"FB" if fol[ta] else "R"} slot')


def k0_part(ctx, FB, experts, lenders, keyroot, enames):
    """The K0 check on one instance: the main grid (S in {FB} + the T11 experts, gamma in K0_GAMMAS, tests T0g and
    T0, the three allowances, every lender and inner policy) in exact and in float64 arithmetic, and the negative
    controls (gamma = 0.25 with S = FB; test T1 with S = FB; S = R) in exact arithmetic."""
    ctx.xs = XScale(ctx)
    xs = ctx.xs
    res = K0Res()
    T = ctx.I.T
    enames = tuple(enames) + ('adv_hold',)
    Ts = [S for S in experts if S.kind == 'T11' and S.switches > 0]
    res.c('T11 experts without a switch (equal to FB or R; not rerun)', sum(1 for S in experts if S.kind == 'T11' and S.switches == 0))
    res.c('T11 experts with a switch (main grid)', len(Ts))
    Rs = [S for S in experts if S.kind == 'R' and S.tag == 'r1']
    for S in [FB] + Ts:
        fol = k0_follows_fb(S, FB)
        for t in range(T):
            if fol[t]:
                d = Fraction(float(S.inc[t])) - xs.frac(xs.q * int(ctx.nreq[t]))
                res.claim('P(b) identity on the core: c_S(t) == q n(t) where S follows FB (|diff|, exact)',
                          -abs(float(d)), -abs(float(d)), f'{ctx.name} S={S.name}(seed {S.seed}) t={t}', d != 0)
    for S in [FB] + Ts:
        fol = k0_follows_fb(S, FB)
        for gamma in K0_GAMMAS:
            for allow in ALLOWS:
                lim = K0Lim(ctx, S, gamma, ctx.allowance(allow))
                for test in K0_TESTS:
                    for lname in LENDERS:
                        for ename in enames:
                            trip = (random.Random(f'k0|{keyroot}|{S.name}|{S.seed}|{gamma}|{test}|{allow}|{lname}').randrange(T)
                                    if ename == 'adv_trip' else None)
                            where = (f'{ctx.name} S={S.name}(seed {S.seed}) gamma={gamma:.4f} {test} B={allow} '
                                     f'lender={lname} E={ename}' + (f' t*={trip}' if trip is not None else ''))
                            rx = run_proj(ctx, S, gamma, test, allow, ename, lenders[lname], keyroot, lname, lim, True, fol, trip)
                            k0_eval_exact(res, ctx, S, gamma, test, lim, rx, where, True)
                            rf = run_proj(ctx, S, gamma, test, allow, ename, lenders[lname], keyroot, lname, lim, False, fol, trip)
                            res.c('runs main float64')
                            res.c('float64 runs whose executed lists or abort slot differ from the exact run',
                                  int(rf['names'] != rx['names'] or rf['ta'] != rx['ta']))
                            res.c('float64: K0 fails at a slot where S follows FB',
                                  sum(1 for (t, _, ok) in rf['k0'] if fol[t] and not ok))
                            if rf['mrec']:
                                res.m('float64: max m(t)/max(1,ALG(t)) at executed slots',
                                      max(max(0.0, A - a) / max(1.0, abs(A)) for (A, a) in rf['mrec']))
                            if rf['ta'] is not None:
                                res.c('float64 aborts')
                                if fol[rf['ta']]:
                                    cl = k0_clause(ctx, S, gamma, lim, rf, FB)
                                    cl['where'] = where
                                    res.clauses.append(cl)
    # negative controls (exact)
    fol = k0_follows_fb(FB, FB)
    for allow in ALLOWS:
        B = ctx.allowance(allow)
        lim = K0Lim(ctx, FB, K0_NEG_GAMMA, B)
        lim1 = K0Lim(ctx, FB, 1.0, B)
        for lname in LENDERS:
            for ename in enames:
                trip = random.Random(f'k0n|{keyroot}|{allow}|{lname}').randrange(T) if ename == 'adv_trip' else None
                for test in K0_TESTS:
                    where = f'{ctx.name} S=FB gamma=0.2500 {test} B={allow} lender={lname} E={ename}'
                    rx = run_proj(ctx, FB, K0_NEG_GAMMA, test, allow, ename, lenders[lname], keyroot, lname, lim, True, fol, trip)
                    k0_eval_exact(res, ctx, FB, K0_NEG_GAMMA, test, lim, rx, where, False)
                    nf = sum(1 for (t, _, ok) in rx['k0'] if not ok)
                    res.negadd('gamma = 0.25 < 1, S = FB, T0g/T0: K0 fails at a slot on FB', len(rx['k0']), nf,
                               int(rx['ta'] is not None), where)
                where = f'{ctx.name} S=FB gamma=1.0000 T1 B={allow} lender={lname} E={ename}'
                rx = run_proj(ctx, FB, 1.0, 'T1', allow, ename, lenders[lname], keyroot, lname, lim1, True, fol, trip)
                k0_eval_exact(res, ctx, FB, 1.0, 'T1', lim1, rx, where, False)
                nf = sum(1 for (t, _, ok) in rx['k0'] if not ok)
                res.negadd('test T1, S = FB, gamma = 1: K0 (T1 value ALG(t-1)) fails at a slot on FB', len(rx['k0']),
                           nf, int(rx['ta'] is not None), where)
    for S in Rs:
        fol = k0_follows_fb(S, FB)
        for gamma in K0_GAMMAS:
            for allow in ALLOWS:
                lim = K0Lim(ctx, S, gamma, ctx.allowance(allow))
                for test in ('T0g',):
                    for lname in LENDERS:
                        for ename in enames:
                            trip = (random.Random(f'k0|{keyroot}|{S.name}|{S.seed}|{gamma}|{test}|{allow}|{lname}').randrange(T)
                                    if ename == 'adv_trip' else None)
                            where = (f'{ctx.name} S={S.name}(seed {S.seed}) gamma={gamma:.4f} {test} B={allow} '
                                     f'lender={lname} E={ename}')
                            rx = run_proj(ctx, S, gamma, test, allow, ename, lenders[lname], keyroot, lname, lim, True, fol, trip)
                            k0_eval_exact(res, ctx, S, gamma, test, lim, rx, where, False)
                            ev = [(t, ok) for (t, _, ok) in rx['k0'] if not lim.cond[t]]
                            res.negadd('S = R, slots with gamma c_S(t)+B(t)-B(t-1) < q n(t): K0 fails', len(ev),
                                       sum(1 for (_, ok) in ev if not ok), int(rx['ta'] is not None and not lim.cond[rx['ta']]),
                                       where)
    return res.dump()


class EEdge:
    """Scripted inner policy of the float edge scan: buys one lease of type (0,0,0) at slot 2 and releases every
    held lease at slot 3."""

    def decide(self, t, held, ALG):
        if t == 2:
            return [], [(0, 0, 0)]
        if t == 3:
            return list(held), []
        return [], []


def k0_edge_job():
    """Float edge scan on the core (the core form of the scenario of C3 §9, "Floating point"): one site, one LLM,
    one client active at slots 0-2 (none at 3), one contract tau = 3, H = 1 (variants with C + delta <= q, where the edge B0 would be <= 0, are skipped); S = FB, gamma = 1, test T0g, a constant
    allowance B0 scanned in 81 steps of ulp(ahat(2)) around the value at which slot 2's purchase sits at its limit. At slot 3
    (no request, so rhs(3) = rhs(2) and tol(3) = tol(2)) E's list is K0 itself, and K0 passes in exact arithmetic iff
    m(2) = 0; in float64 ALG(2) = fl(ALG(1) + fl(C + delta)) and ahat(2) = fl(fl(ALG(1) + C) + delta) can differ by
    an ulp. Every float64 abort with S on FB is classified by the code-level clause; the exact runs must not abort."""
    res = K0Res()
    T = 6
    for beta in (9.7, 11.3, 13.3, 15.1, 17.9, 19.7, 23.1, 29.3):
        for dlt in (0.1, 0.3, 0.7, 1.3, 1.9):
            for q in (10.0, 13.3, 17.1):
                act = np.zeros((1, T), dtype=bool)
                act[0, :3] = True
                I = Instance(T=T, tau=np.array([3]), H=np.array([1]), a=np.array([[1.1]]), beta=np.array([[beta]]),
                             g=np.array([1]), q=q, cl_llm=np.zeros(1, dtype=int), delta=np.array([[dlt]]), active=act)
                ctx = Ctx(I, f'edge beta={beta} delta={dlt} q={q}')
                ctx.xs = XScale(ctx)
                FB = expert_FB(ctx)
                fol = [True] * T
                spec = ('obl', [np.array([], dtype=int)])
                ref = run_proj(ctx, FB, 1.0, 'T0g', 'B0', None, spec, ctx.name, 'obl0',
                               K0Lim(ctx, FB, 1.0, np.full(T, 1e6)), False, fol, E=EEdge())
                a2 = ref['flog'][2][5]                      # ahat(2): slot 2's purchase at limit when lim(2) = a2
                Bs = (a2 / (1.0 + GUARD_TOL) if a2 > 1.0 else a2 - GUARD_TOL) - float(FB.C[2])
                if Bs <= 0:                                 # C + delta <= q: slot 2's purchase is no edge
                    continue
                res.c('edge variants')
                for kk in range(-40, 41):
                    B0 = Bs + kk * math.ulp(a2)
                    lim = K0Lim(ctx, FB, 1.0, np.full(T, B0))
                    where = f'{ctx.name} B0={B0.hex()}'
                    for exact in (True, False):
                        rec = run_proj(ctx, FB, 1.0, 'T0g', 'B0', None, spec, ctx.name, 'obl0', lim, exact, fol, E=EEdge())
                        md = 'exact' if exact else 'float64'
                        res.c(f'edge runs {md}')
                        if rec['ta'] is not None:
                            res.c(f'edge aborts {md} at slot {rec["ta"]}')
                            if exact:
                                res.claim('edge scan: no exact abort (count)', -1.0, -1.0, where, True)
                            else:
                                cl = k0_clause(ctx, FB, 1.0, lim, rec, FB)
                                cl['where'] = where
                                res.clauses.append(cl)
                        elif exact:
                            res.claim('edge scan: no exact abort (count)', 0.0, 0.0, where, False)
                        if not exact and rec['ta'] is None and len(rec['mrec']) > 2:
                            res.c('edge float64 runs without abort with m(2) > 0',
                                  int(rec['mrec'][2][0] > rec['mrec'][2][1]))
    return res.dump()


# ------------------------------------------------------------------------------------------ jobs
def make_random(fam, seed):
    base = {'rand': 52000, 'slo': 53000, 'spiky': 54000, 'tau0': 55000, 'hq': 56000}[fam]
    rng = np.random.default_rng(base + seed)
    q = float(rng.choice([12.0, 20.0] if fam == 'hq' else [2.0, 4.0, 10.0]))
    if fam in ('rand', 'hq'):
        return random_instance(rng, T=36, m=4, J=2, n=8, q=q)
    if fam == 'slo':
        return random_instance(rng, T=36, m=5, J=2, n=10, slo=0.45, q=q)
    if fam == 'spiky':
        return random_instance(rng, T=36, m=4, J=1, n=10, on_mean=2, off_mean=8, q=q)
    if fam == 'tau0':
        return random_instance(rng, T=36, m=4, J=2, n=8, q=q, contracts=[(0, 1, 0.9), (2, 0, 1.1), (6, 3, 1.4)])
    raise ValueError(fam)


def lp_no_announcement(I):
    return float(opt_omega(I, [np.array([], dtype=int)] * I.m, relax=True)['fun'])


def build_experts(ctx, pd, seeds, pred_cols=None):
    FB = expert_FB(ctx)
    ex = []
    for sd in seeds:
        for tag, r in (('r1', 1), ('rth', None)):
            rnd = round_pd(pd, np.random.default_rng(sd), r=r)
            R = expert_R(ctx, rnd, tag, sd)
            ex.append(R)
            ex.append(expert_T11(ctx, FB, R, rnd))
    extra = [expert_T11RR(ctx, ex[i], ex[i + 2]) for i in range(0, len(ex), 4)]   # T11(R_r1, R_rth) per seed
    if pred_cols is not None:
        FP = expert_FP(ctx, pred_cols)
        extra = [FP] + extra + [expert_T11FP(ctx, FP, R) for R in ex if R.kind == 'R']
        extra += [expert_T11FP(ctx, FP, R, first='dearer') for R in ex if R.kind == 'R']
    shkey = f'shadow|{seeds[0]}'                       # independent of ctx.name (non-anticipation rebuild)
    SHg, SHr = expert_shadow(ctx, 'greedy', shkey), expert_shadow(ctx, 'random', shkey)
    extra += [SHg, SHr, expert_T11SH(ctx, SHg, ex[0])]
    return FB, ex, extra


def check_nonanticipation(st, ctx, seeds, FB, experts, extra, where, pred_cols=None):
    """C_S(t) and B_on(t) must be known at slot t: recompute them on the demand cut after T/2."""
    I = ctx.I
    tc = I.T // 2
    It = I.subset()
    It.active = I.active.copy()
    It.active[:, tc + 1:] = False
    ctxt = Ctx(It, ctx.name + ' (cut)')
    FBt, ext, extrat = build_experts(ctxt, FracPD(It).run(), seeds, pred_cols)
    z = np.zeros(tc + 1)
    trunc = {}
    for S, St in zip([FB] + experts + extra, [FBt] + ext + extrat):
        assert S.name == St.name
        st.add_arr('non-anticipation: |C_S(t) - C_S(t) with demand cut after T/2|, t <= T/2',
                   np.abs(S.C[:tc + 1] - St.C[:tc + 1]), z, f'{where} S={S.name}(seed {S.seed})')
        # the identity "C(t) = total of the same rule on the demand cut after t" (earlier G4 proof)
        e = trunc.setdefault(S.kind, [0, 0])
        e[0] += 1
        e[1] += int(St.C[-1] > S.C[tc] + 1e-9 * (1.0 + abs(S.C[tc])))
    st.add_arr('non-anticipation: |B_on(t) - B_on(t) with demand cut after T/2|, t <= T/2',
               np.abs(ctx.Bon[:tc + 1] - ctxt.Bon[:tc + 1]), z, where)
    return trunc


def grid_runs(ctx, st, info, FB, experts, enames, OPT, lenders, keyroot, collect=None, omega_opt=None):
    """Main grid: experts x gamma x test x allowance x lender x E. Returns number of runs."""
    T = ctx.I.T
    alone_cache = {}
    nruns = 0
    for si, S in enumerate(experts):
        if 'twin' in enames:      # the twin alone tracks S from slot 0 (Lemma G1(b), t = 0): ALG(t) <= C_S(t)
            for lname in LENDERS:
                g0 = Guard(ctx, S, 1.0, 'T1', 'zero')
                rec = run(ctx, g0, ETwin(S), make_lender(ctx, lenders[lname], f'{keyroot}|{lname}'), mode='never')
                st.add_arr('G1(b) from slot 0: twin of S alone, ALG(t) <= C_S(t) at every t', rec['cum'], S.C,
                           f'{ctx.name} S={S.name}(seed {S.seed}) lender={lname} E=twin alone')
        tas = {}
        for gi, gamma in enumerate(GAMMAS):
            for test in TESTS:
                for allow in ALLOWS:
                    guard = Guard(ctx, S, gamma, test, allow)
                    for lname in LENDERS:
                        spec = lenders[lname]
                        lseed = f'{keyroot}|{lname}'
                        for ename in enames:
                            eseed = f'{keyroot}|{lname}|{ename}'
                            trip = None
                            if ename == 'adv_trip':
                                trip = random.Random(f'{keyroot}|{si}|{gi}|{test}|{allow}|{lname}').randrange(T)
                            lend = make_lender(ctx, spec, lseed)
                            rec = run(ctx, guard, make_E(ctx, ename, guard, eseed, trip, lend), lend)
                            nruns += 1
                            where = (f'{ctx.name} S={S.name}(seed {S.seed}) gamma={gamma:.4f} {test} B={allow} '
                                     f'lender={lname} E={ename}' + (f' t*={trip}' if trip is not None else ''))
                            alone = None
                            if not ename.startswith('adv'):
                                tas[(gi, allow, lname, ename, test)] = T if rec['ta'] is None else rec['ta']
                            if ename == 'twin':
                                info.add(('twin', test, allow, round(gamma, 4)), rec['ta'] is not None, 0.0)
                                if test == 'T0g' and gamma >= 1.0:
                                    st.add('T0g remark: the twin of S (S executed per G1(b) from slot 0) is never '
                                           'aborted when gamma >= 1 (0/1)', int(rec['ta'] is not None), 0, where)
                            if rec['ta'] is None:
                                ak = ((lname, ename) if not (ename.startswith('adv') or ename == 'twin')
                                      else (lname, ename, si, gi, test, allow))
                                alone = alone_cache.get(ak)
                                if alone is None:
                                    lend = make_lender(ctx, spec, lseed)
                                    alone = run(ctx, guard, make_E(ctx, ename, guard, eseed, trip, lend), lend, mode='never')
                                    alone_cache[ak] = alone
                            g2_checks(st, ctx, guard, rec, where, alone)
                            ALG = float(rec['cum'][-1])
                            bounds = g3_checks(st, ctx, guard, ALG, OPT, where)
                            rat = ALG / OPT if OPT > 0 else 0.0
                            info.add((S.kind, S.tag, round(gamma, 4), test, allow), rec['ta'] is not None, rat)
                            info.add(('E', ename, test, allow), rec['ta'] is not None, rat)
                            if rec['ta'] is not None:
                                info.add(('W', S.kind, S.tag), S.W[rec['ta']] > 0, rec['ta'] / T)
                            if collect is not None:
                                collect.append(dict(S=S.kind, tag=S.tag, seed=S.seed, gamma=gamma, test=test,
                                                    allow=allow, lender=lname, E=ename, ALG=ALG, ta=rec['ta'],
                                                    bounds=bounds))
                            if omega_opt is not None and bounds and 'a' in bounds:
                                key = tuple(tuple(int(x) for x in o) for o in rec['omega'])
                                if key not in omega_opt:
                                    omega_opt[key] = opt_omega(ctx.I, rec['omega'])['lb']
                                rho = ctx.I.rho()
                                kap = kappa_of(allow)
                                st.add('G3(a): ALG <= ((1+gamma) alpha_N + kappa) max(2,rho) OPT(sigma,omega realized)',
                                       ALG, ((1 + gamma) * alpha_N(ctx.I) + kap) * max(2.0, rho) * omega_opt[key], where)
        # T0g's test value is at most T0's on the common history (E alone), so T0g aborts no earlier
        for (gi, allow, lname, ename, test), ta0 in tas.items():
            if test == 'T0':
                ta1 = tas[(gi, allow, lname, ename, 'T0g')]
                st.add('T0g aborts no earlier than T0 (same S, gamma, allowance, lender, E; 0/1)', int(ta1 < ta0), 0,
                       f'{ctx.name} S={S.name}(seed {S.seed}) gamma={GAMMAS[gi]:.4f} B={allow} lender={lname} E={ename}')
    return nruns


def forced_runs(ctx, st, FB, experts, lenders, keyroot):
    """Lemma G1(b) from several slots with the holdings of greedy, random and adv_fill (T1, B0),
    and Prop G4's execution from slot 0 (ALG(T) <= C_S(T))."""
    T = ctx.I.T
    nruns = 0
    for S in [FB] + experts:
        for lname in LENDERS:
            spec = lenders[lname]
            for ename, (gtest, gallow) in (('greedy', ('T0', 'zero')), ('random', ('T0', 'zero')),
                                           ('adv_fill', ('T1', 'B0'))):
                guard = Guard(ctx, S, 1.0, gtest, gallow)
                for t0 in sorted({0, 1, T // 3, (2 * T) // 3, T - 1}):
                    rec = run(ctx, guard, make_E(ctx, ename, guard, f'{keyroot}|{lname}|{ename}'),
                              make_lender(ctx, spec, f'{keyroot}|{lname}'), mode='force', t_force=t0)
                    nruns += 1
                    where = f'{ctx.name} forced abort t0={t0} S={S.name}(seed {S.seed}) lender={lname} E={ename}'
                    g1_checks(st, S, rec, where)
                    if t0 == 0:
                        st.add('G4/G1(b): tracking S from slot 0 (any lender): ALG(T) <= C_S(T)',
                               rec['cum'][-1], S.C[-1], where)
    for S in [x for x in experts if x.kind in ('R', 'T11', 'T11FPx')]:
        guard = Guard(ctx, S, 1.0, 'T0', 'zero')
        for t0 in range(T):
            rec = run(ctx, guard, make_E(ctx, 'random', guard, f'{keyroot}|hold|random'),
                      make_lender(ctx, lenders['hold'], f'{keyroot}|hold'), mode='force', t_force=t0)
            nruns += 1
            g1_checks(st, S, rec, f'{ctx.name} forced abort (every slot) t0={t0} S={S.name}(seed {S.seed}) lender=hold E=random')
    return nruns


def random_job(args):
    fam, seed = args
    t0 = time.time()
    I = make_random(fam, seed)
    ctx = Ctx(I, f'{fam}#{seed}')
    st, info = Stats(), Info()
    oe = opt_eager(I)
    OPT = float(oe['lb'])
    lp0 = lp_no_announcement(I)
    g5_checks(st, ctx, OPT, lp0, ctx.name)
    st.add('LP(sigma, no announcement) <= OPT_eager', lp0, float(oe['fun']), ctx.name)
    pd = FracPD(I).run()
    seeds = [61000 + 97 * seed + {'rand': 0, 'slo': 1, 'spiky': 2, 'tau0': 3, 'hq': 4}[fam]]
    pred = predicted_cols(I)
    FB, experts, extra = build_experts(ctx, pd, seeds, pred)
    for S in [FB] + experts + extra:
        check_expert(st, ctx, S, f'{ctx.name} S={S.name}')
    trunc = check_nonanticipation(st, ctx, seeds, FB, experts, extra, ctx.name, pred)
    lenders = lender_specs(ctx, ctx.name)
    n1 = grid_runs(ctx, st, info, FB, experts, E_RAND, OPT, lenders, ctx.name)
    n2 = forced_runs(ctx, st, FB, experts + extra, lenders, ctx.name)
    tk = time.time()
    k0 = k0_part(ctx, FB, experts, lenders, ctx.name, E_RAND)
    secs_k0 = time.time() - tk
    t11_switches = [S.switches for S in experts if S.kind == 'T11']
    return dict(name=ctx.name, stats=st.d, info=info.d, runs=n1, forced=n2, mip_status=int(oe['status']), k0=k0,
                secs_k0=secs_k0,
                q=ctx.q, t11_switches=t11_switches, t11rr_switches=[S.switches for S in extra if S.kind == 'T11RR'],
                t11fp_switches=[S.switches for S in extra if S.kind == 'T11FP'],
                t11fpx_sw=[S.sw_slots for S in extra if S.kind == 'T11FPx'],
                t11sh_sw=[S.sw_slots for S in extra if S.kind == 'T11SH'], trunc=trunc,
                OPT=OPT, Bon=float(ctx.Bon[-1]), B0=ctx.B0, qsig=ctx.qsig, alphaN=alpha_N(I),
                n_el=int(ctx.nreq.sum()), secs=time.time() - t0)


def family_job(args):
    fam, par = args
    t0 = time.time()
    if fam == 'P5':
        T = 48
        I = single(T, [(1, 1), (T, 0)], float(par), [1.0, 1.3])
        name = f'P5 beta={par}'
        enames = ('fb', 'greedy', 'greedy_i2', 'greedy_rev', 'random', 'twin', 'adv_fill', 'adv_trip')
    else:
        m, rho = par
        I = cm_instance(m, rho)
        name = f'T4 m={m} rho={rho}'
        enames = ('fb', 'greedy', 'greedy_i2', 'random', 'twin', 'adv_fill', 'adv_trip')
    ctx = Ctx(I, name)
    st, info = Stats(), Info()
    oe = opt_eager(I)
    OPT = float(oe['lb'])
    lp0 = lp_no_announcement(I)
    g5_checks(st, ctx, OPT, lp0, name)
    pd = FracPD(I).run()
    seeds = [71000, 71001, 71002]
    pred = predicted_cols(I)
    FB, experts, extra = build_experts(ctx, pd, seeds, pred)
    for S in [FB] + experts + extra:
        check_expert(st, ctx, S, f'{name} S={S.name}(seed {S.seed})')
    trunc = check_nonanticipation(st, ctx, seeds, FB, experts, extra, name, pred)
    lenders = lender_specs(ctx, name)
    collect, omega_opt = [], {}
    n1 = grid_runs(ctx, st, info, FB, experts, enames, OPT, lenders, name, collect=collect, omega_opt=omega_opt)
    n2 = forced_runs(ctx, st, FB, experts + extra, lenders, name)
    # expectation forms of Corollary G3: means over the R seeds
    groups = {}
    for r in collect:
        if r['bounds']:
            k = (r['S'], r['tag'], r['gamma'], r['test'], r['allow'], r['lender'], r['E'])
            groups.setdefault(k, []).append(r)
    for k, rs in groups.items():
        mean = float(np.mean([r['ALG'] for r in rs]))
        where = f'{name} S={k[0]}_{k[1]} gamma={k[2]:.4f} {k[3]} B={k[4]} lender={k[5]} E={k[6]} (mean of {len(rs)} R seeds)'
        if 'a' in rs[0]['bounds']:
            st.add('G3(a): mean over R seeds of ALG <= ((1+gamma) alpha_N + kappa) OPT_eager', mean, rs[0]['bounds']['a'], where)
        if 'b' in rs[0]['bounds']:
            st.add('G3(b): mean over R seeds of ALG <= ((1+gamma) c(gamma\') + kappa) min{q|sigma|, alpha_N OPT_eager}',
                   mean, rs[0]['bounds']['b'], where)
    # summary table for the default-like configuration (T0, capped, gamma = 1)
    E_alone = {}
    for lname in LENDERS:
        for ename in enames:
            if ename.startswith('adv') or ename == 'twin':
                continue
            g = Guard(ctx, experts[0], 1.0, 'T0', 'cap')
            lend = make_lender(ctx, lenders[lname], f'{name}|{lname}')
            rec = run(ctx, g, make_E(ctx, ename, g, f'{name}|{lname}|{ename}', None, lend), lend, mode='never')
            E_alone[(lname, ename)] = float(rec['cum'][-1])
    table = []
    for lname in LENDERS:
        for ename in enames:
            row = dict(lender=lname, E=ename, E_alone_over_OPT=(E_alone[(lname, ename)] / OPT if (lname, ename) in E_alone else None))
            for test, kind, tag in FAM_COLS:
                rs = [r for r in collect if r['S'] == kind and r['tag'] == tag and r['gamma'] == 1.0 and r['test'] == test
                      and r['allow'] == 'cap' and r['lender'] == lname and r['E'] == ename]
                row[f'{test} {kind}_{tag}'] = dict(ratio=float(np.mean([r['ALG'] for r in rs])) / OPT,
                                                   aborts=sum(r['ta'] is not None for r in rs), n=len(rs))
            table.append(row)
    CS = {f'{S.kind}_{S.tag}': float(np.mean([x.C[-1] for x in experts if x.kind == S.kind and x.tag == S.tag])) / OPT
          for S in experts}
    tk = time.time()
    k0 = k0_part(ctx, FB, experts, lenders, name, enames)
    secs_k0 = time.time() - tk
    return dict(name=name, stats=st.d, info=info.d, runs=n1, forced=n2, mip_status=int(oe['status']), OPT=OPT,
                k0=k0, secs_k0=secs_k0,
                rho=I.rho(), Bon=float(ctx.Bon[-1]), B0=ctx.B0, qsig=ctx.qsig, alphaN=alpha_N(I), table=table,
                CS_over_OPT=CS, n_omega_opt=len(omega_opt), trunc=trunc,
                t11fpx_sw=[S.sw_slots for S in extra if S.kind == 'T11FPx'], secs=time.time() - t0)


def g6_instance(n, active_slots):
    T = 2
    act = np.zeros((n, T), dtype=bool)
    for t in active_slots:
        act[:, t] = True
    return Instance(T=T, tau=np.array([1]), H=np.array([1]), a=np.array([[1.0]]), beta=np.array([[1.0]]),
                    g=np.array([1]), q=2.0, cl_llm=np.zeros(n, dtype=int), delta=np.zeros((n, 1)), active=act)


def g6_job():
    st, rows = Stats(), []
    for scen, act, ename in (('i', (1,), 'g6i'), ('ii', (0, 1), 'fb')):
        for n in (4, 16, 64):
            I = g6_instance(n, act)
            name = f'G6 I_{n} ({scen})'
            ctx = Ctx(I, name)
            oe = opt_eager(I)
            OPT = float(oe['fun'])
            st.add('G6: |OPT_eager(I_n) - 3|', abs(OPT - 3.0), 0, name)
            st.add('G6: B0 == 3n (|diff|)', abs(ctx.B0 - 3.0 * n), 0, name)
            pd = FracPD(I).run()
            FB, experts, extra = build_experts(ctx, pd, list(range(81000, 81010)))
            lenders = lender_specs(ctx, name)
            for S in [FB] + experts + extra:
                check_expert(st, ctx, S, f'{name} S={S.name}(seed {S.seed})')
            res = {}
            for S in experts:
                for gamma in GAMMAS:
                    for test in TESTS:
                        for allow in ALLOWS:
                            guard = Guard(ctx, S, gamma, test, allow)
                            for lname in ('eager', 't4'):
                                rec = run(ctx, guard, make_E(ctx, ename, guard, name), make_lender(ctx, lenders[lname], name))
                                where = f'{name} S={S.name}(seed {S.seed}) gamma={gamma:.4f} {test} B={allow} lender={lname} E={ename}'
                                alone = None
                                if rec['ta'] is None:
                                    alone = run(ctx, guard, make_E(ctx, ename, guard, name),
                                                make_lender(ctx, lenders[lname], name), mode='never')
                                g2_checks(st, ctx, guard, rec, where, alone)
                                ALG = float(rec['cum'][-1])
                                g3_checks(st, ctx, guard, ALG, OPT, where)
                                if scen == 'i' and allow == 'B0':
                                    st.add('G6(i): constant B0, any test (T0, T0g, T1): 3n <= ALG', 3.0 * n, ALG, where)
                                if scen == 'ii' and test == 'T1':
                                    st.add('G6(ii): T1, any allowance: 2n <= ALG', 2.0 * n, ALG, where)
                                if scen == 'i' and test in SOUND and allow == 'cap':
                                    st.add('G6 remark: (i) T0 and T0g, capped: abort at slot 0 (0/1 violation)',
                                           int(rec['ta'] != 0), 0, where)
                                if scen == 'ii' and test in SOUND:
                                    pred = 2.0 * n > gamma * S.C[0] + guard.B[0] + 1e-12
                                    st.add('G6 remark: (ii) T0 and T0g abort at 0 iff 2n > gamma C_S(0)+B(0) (0/1 violation)',
                                           int(pred != (rec['ta'] == 0)), 0, where)
                                key = (test, allow, S.kind, S.tag)
                                res.setdefault(key, []).append((ALG / OPT, rec['ta']))
            for (test, allow, kind, tag), v in sorted(res.items()):
                rows.append(dict(scen=scen, n=n, test=test, allow=allow, S=f'{kind}_{tag}', OPT_eager=OPT,
                                 ratio_mean=float(np.mean([x[0] for x in v])), ratio_min=float(np.min([x[0] for x in v])),
                                 ratio_max=float(np.max([x[0] for x in v])),
                                 abort_slots=sorted({('none' if x[1] is None else str(x[1])) for x in v})))
    return dict(stats=st.d, rows=rows)


def tight_job():
    """Theorem G2(b)/(c) attained with equality. T = 10, one LLM, one client active in every slot, q = 10,
    one contract tau = 10, H = 0 (D = 10). Site 0: delta = 0, C = 110. Site 1: delta = inf (unusable),
    C = gamma*110 - 10. S = FP buying one site-0 lease at slot 0 (C_S(T) = 110). E buys one site-1 lease at
    slots 0 and 1. Under T0 and T0g with B = 0: ahat(0) = gamma*110 = gamma C_S(0) (executed), the guard
    aborts at slot 1 and ALG = (1+gamma) 110 = (1+gamma) C_S(T) + B(T) under every lender."""
    st, rows = Stats(), []
    T = 10
    for gamma in GAMMAS:
        c1 = gamma * 110.0 - 10.0
        I = Instance(T=T, tau=np.array([10]), H=np.array([0]), a=np.array([[1.0], [1.0]]),
                     beta=np.array([[100.0, c1 - 10.0]]), g=np.array([1]), q=10.0, cl_llm=np.zeros(1, dtype=int),
                     delta=np.array([[0.0, INF]]), active=np.ones((1, T), dtype=bool))
        ctx = Ctx(I, f'tight gamma={gamma:.4f}')
        S = expert_FP(ctx, [(0, 0, 0, 0)], tag='site0')
        check_expert(st, ctx, S, ctx.name)
        lenders = lender_specs(ctx, ctx.name)
        for test in TESTS:
            guard = Guard(ctx, S, gamma, test, 'zero')
            for lname in LENDERS:
                rec = run(ctx, guard, EScript({0: [(1, 0, 0)], 1: [(1, 0, 0)]}), make_lender(ctx, lenders[lname], ctx.name))
                where = f'{ctx.name} {test} B=zero lender={lname}'
                g2_checks(st, ctx, guard, rec, where)
                ALG = float(rec['cum'][-1])
                bound = (1.0 + gamma) * float(S.C[-1])
                if test in SOUND:
                    st.add('G2 tightness: |ALG - ((1+gamma) C_S(T) + B(T))| on the tightness instance (T0, T0g)',
                           abs(ALG - bound), 0, where)
                    st.add('G2 tightness: abort slot == 1 on the tightness instance (T0, T0g; 0/1)',
                           int(rec['ta'] != 1), 0, where)
                rows.append(dict(gamma=gamma, test=test, lender=lname, ta=rec['ta'], ALG=ALG, CS=float(S.C[-1]),
                                 bound_without_M=bound))
    return dict(stats=st.d, rows=rows)


# ------------------------------------------------------------------------------------------ main
def fmt_stats(d):
    L = []
    names = sorted(d.keys())
    w = max(len(nm) for nm in names)
    L.append(f"  {'inequality'.ljust(w)}  {'evals':>8} {'viol':>5} {'max(LHS-RHS)':>13} {'max LHS/RHS':>12}  at max LHS/RHS (else at max excess)")
    for nm in names:
        e = d[nm]
        mr = f'{e[4]:12.6f}' if e[4] > -INF else f"{'-':>12}"
        where = e[5] if e[4] > -INF else e[3]
        L.append(f'  {nm.ljust(w)}  {e[0]:8d} {e[1]:5d} {e[2]:13.3e} {mr}  {where}')
    return L


if __name__ == '__main__':
    t_start = time.time()
    os.makedirs(OUT, exist_ok=True)
    nw = int(os.environ.get('GUARD_WORKERS', '2'))
    rjobs = [(f, s) for f, cnt in RAND_FAMS for s in range(cnt)]
    fjobs = [('P5', b) for b in (2, 6, 14, 30)] + [('T4', (m, r)) for m in (2, 4) for r in (2, 4, 8, 16)]
    ST, INFO_R, INFO_F = Stats(), Info(), Info()
    with mp.get_context('spawn').Pool(nw) as p:
        fam_async = p.map_async(family_job, fjobs, chunksize=1)
        R = []
        for i, r in enumerate(p.imap_unordered(random_job, rjobs, chunksize=2)):
            R.append(r)
            if (i + 1) % 40 == 0:
                print(f'  random instances done: {i + 1}/{len(rjobs)} ({time.time() - t_start:.0f} s)', flush=True)
        F = fam_async.get()
    G6 = g6_job()
    TG = tight_job()
    EDGE = k0_edge_job()
    jix = {f'{f}#{sd}': i for i, (f, sd) in enumerate(rjobs)}
    R.sort(key=lambda r: jix[r['name']])            # merge in job order: ties of the 'at' columns are deterministic
    for r in R:
        ST.merge(r['stats']); INFO_R.merge(r['info'])
    for r in F:
        ST.merge(r['stats']); INFO_F.merge(r['info'])
    ST.merge(G6['stats'])
    ST.merge(TG['stats'])
    K0 = K0Res()
    for r in R + F:
        K0.merge(r['k0'])
    K0E = K0Res()
    K0E.merge(EDGE)
    R.sort(key=lambda r: r['name'])
    runtime = time.time() - t_start
    k0_neg_ok = {k: v[1] > 0 for k, v in K0.neg.items()}
    k0_cl = K0.clauses + K0E.clauses
    k0_viol = (sum(e[1] for e in K0.claims.values()) + sum(e[1] for e in K0E.claims.values())
               + sum(1 for ok in k0_neg_ok.values() if not ok) + sum(1 for c in k0_cl if not (c['rounding'] and c['sum_ok']))
               + int(len(K0E.clauses) == 0))
    nviol = sum(e[1] for e in ST.d.values()) + k0_viol
    out = dict(runtime_s=runtime, workers=nw, n_random=len(R), n_families=len(F),
               runs_random=sum(r['runs'] for r in R), forced_random=sum(r['forced'] for r in R),
               runs_families=sum(r['runs'] for r in F), forced_families=sum(r['forced'] for r in F),
               mip_status=sorted({r['mip_status'] for r in R + F}), total_violations=nviol,
               stats={k: dict(evals=v[0], violations=v[1], max_excess=v[2], where_max_excess=v[3],
                              max_ratio=(v[4] if v[4] > -INF else None), where_max_ratio=v[5], violation_examples=v[6])
                      for k, v in sorted(ST.d.items())},
               info_random={'|'.join(map(str, k)): dict(runs=v[0], aborts=v[1], mean_ALG_over_OPT=v[2] / v[0], max_ALG_over_OPT=v[3])
                            for k, v in sorted(INFO_R.d.items(), key=lambda x: tuple(map(str, x[0]))) if k[0] not in ('W', 'twin')},
               twin_aborts_random={'|'.join(map(str, k[1:])): dict(runs=v[0], aborts=v[1])
                                   for k, v in sorted(INFO_R.d.items(), key=lambda x: tuple(map(str, x[0]))) if k[0] == 'twin'},
               twin_aborts_families={'|'.join(map(str, k[1:])): dict(runs=v[0], aborts=v[1])
                                     for k, v in sorted(INFO_F.d.items(), key=lambda x: tuple(map(str, x[0]))) if k[0] == 'twin'},
               tightness=TG['rows'],
               aborts_with_W_positive={f'{k[1]}_{k[2]}': dict(aborts=v[0], W_positive=v[1], mean_ta_over_T=v[2] / v[0])
                                       for k, v in INFO_R.d.items() if k[0] == 'W'},
               families=[{k: v for k, v in r.items() if k not in ('stats', 'info', 'k0')} for r in F],
               random_instances=[{k: v for k, v in r.items() if k not in ('stats', 'info', 'k0')} for r in R],
               g6=G6['rows'],
               k0=dict(violations=k0_viol, claims=K0.claims, negative_controls=K0.neg, negative_controls_fail=k0_neg_ok,
                       executed_candidates=K0.cands, counts=K0.cnt, maxima=K0.mx, clauses_main=K0.clauses,
                       edge=dict(claims=K0E.claims, counts=K0E.cnt, clauses=K0E.clauses),
                       secs_k0_jobs=sum(r['secs_k0'] for r in R + F)))
    json.dump(out, open(os.path.join(OUT, 'guard.json'), 'w'), indent=1, default=float)

    L = ['Guard checks on the ORML core (design/theory/c3_c4_c5_general.md §9: G1-G6; audit design/theory/audit_guard.md); '
         'script check_guard.py',
         f'random instances: {len(R)} ({", ".join(f"{f} {c}" for f, c in RAND_FAMS)}; T=36, q in {{2,4,10}}, hq q in {{12,20}}; '
         'tau0 contracts (tau,H) in {(0,1),(2,0),(6,3)}); '
         f'families: P5 beta in {{2,6,14,30}} (T=48, q=1e4), T4 m in {{2,4}} x rho in {{2,4,8,16}} (T=48); G6 I_n, n in {{4,16,64}}; '
         'tightness instance of G2 (T=10), one per gamma',
         f'guard runs: {out["runs_random"]} random + {out["runs_families"]} family (grid S x gamma x test x allowance x lender x E), '
         f'forced-abort runs: {out["forced_random"] + out["forced_families"]}; MILP status {out["mip_status"]}; '
         f'runtime {runtime:.0f} s on {nw} workers',
         'S in {R_r1, R_rth, T11_r1, T11_rth} (one R seed per instance, three on the families, ten on G6); '
         'gamma in {0.25, 1, 1+1/sqrt2, 3}; tests T0, T0g, T1; allowances zero, B0, cap (kappa=10); '
         'lenders obl0, obl0.2, eager, t4 (adaptive C3-T4), hold (adaptive random); E in fb, greedy, greedy_i2, random, '
         'twin (executes S per G1(b) from slot 0, same coins), adv_fill, adv_trip (+ greedy_rev on P5); further eager '
         'experts (expert checks, forced aborts): FB, FP, T11RR, T11FP, T11FPx, SH_greedy, SH_random, T11SH',
         f'TOTAL VIOLATIONS: {nviol}',
         '', 'Inequalities (violation: LHS > RHS + 1e-7 max(1,|RHS|); slack = RHS - LHS = -(max excess)).',
         "Lines named 'impl. ...' hold by construction of the guard code: implementation checks, not evidence for the results."]
    L += fmt_stats(ST.d)
    if nviol:
        L.append('')
        L.append('Violations (up to 6 per inequality):')
        for nm, e in sorted(ST.d.items()):
            for v in e[6]:
                L.append(f'  {nm}: {v[0]}: LHS {v[1]:.6g} RHS {v[2]:.6g}')
    L.append('')
    L.append('Random instances, abort rate and ALG/OPT_eager by safe expert, gamma, test, allowance (all lenders and E):')
    L.append('  S     rbar  gamma   test allow  runs   abort%  mean ALG/OPT  max ALG/OPT')
    for k, v in sorted(INFO_R.d.items(), key=lambda x: tuple(map(str, x[0]))):
        if k[0] in ('E', 'W', 'twin'):
            continue
        L.append(f'  {k[0]:5s} {str(k[1]):4s} {k[2]:6.4f} {k[3]:4s} {k[4]:5s} {v[0]:6d}  {100 * v[1] / v[0]:6.1f}  {v[2] / v[0]:10.3f}  {v[3]:10.3f}')
    sw = [x for r in R for x in r['t11_switches']]
    swq = {}
    for r in R:
        for x in r['t11_switches']:
            swq.setdefault(r['q'], []).append(x)
    swrr = [x for r in R for x in r['t11rr_switches']]
    swfp = [x for r in R for x in r['t11fp_switches']]
    L.append(f'T11(FB,R) experts on random instances: {len(sw)}, with >= 1 switch {sum(x > 0 for x in sw)} (by q: ' +
             ', '.join(f'q={k:g} {sum(x > 0 for x in v)}/{len(v)}' for k, v in sorted(swq.items())) +
             f'), max switches {max(sw)}; T11(R_r1,R_rth): {len(swrr)}, with >= 1 switch {sum(x > 0 for x in swrr)}, '
             f'max {max(swrr)}; T11(FP late prediction, R): {len(swfp)}, with >= 1 switch {sum(x > 0 for x in swfp)}, '
             f'with >= 2 {sum(x > 1 for x in swfp)}, max {max(swfp)}')
    fx = [x for r in R for x in r['t11fpx_sw']]
    fxf = [x for r in F for x in r['t11fpx_sw']]
    shs = [x for r in R for x in r['t11sh_sw']]
    L.append(f'T11(FP,R) started with the dearer expert (T11FPx): random {len(fx)}, with a switch at slot 0 '
             f'{sum(1 for x in fx if x and x[0] == 0)}, with >= 2 switches {sum(len(x) >= 2 for x in fx)}, max '
             f'{max(len(x) for x in fx)}; families {len(fxf)}, switch at slot 0 {sum(1 for x in fxf if x and x[0] == 0)}; '
             f'T11(SH_greedy,R_r1): {len(shs)}, with >= 1 switch {sum(len(x) > 0 for x in shs)}, max {max(len(x) for x in shs)}')
    tr = {}
    for r in R + F:
        for k, v in r['trunc'].items():
            e = tr.setdefault(k, [0, 0]); e[0] += v[0]; e[1] += v[1]
    L.append('Demand-truncation identity of the earlier G4 proof ("C(t) = total of the rule on the demand cut after t"), '
             't = T/2: experts whose total on the cut demand exceeds C(T/2): ' +
             ', '.join(f'{k} {v[1]}/{v[0]}' for k, v in sorted(tr.items())) + ' (the horizon truncation of §9 is used instead)')
    L.append('Aborts with W_S(t_a) > 0 (term of G2(b) exercised): ' +
             ', '.join(f"{k[1]}_{k[2]} {v[1]}/{v[0]}" for k, v in sorted(INFO_R.d.items(), key=lambda x: tuple(map(str, x[0])))
                       if k[0] == 'W'))
    L.append('Random instances, by inner policy E, test, allowance (all S, gamma, lenders):')
    L.append('  E          test allow  runs   abort%  mean ALG/OPT  max ALG/OPT')
    for k, v in sorted(INFO_R.d.items(), key=lambda x: tuple(map(str, x[0]))):
        if k[0] != 'E':
            continue
        L.append(f'  {k[1]:10s} {k[2]:4s} {k[3]:5s} {v[0]:6d}  {100 * v[1] / v[0]:6.1f}  {v[2] / v[0]:10.3f}  {v[3]:10.3f}')
    L.append('Twin of S (E executes S per G1(b) from slot 0, shares R\'s coins; ALG_E(t) <= C_S(t)): abort rate by test, '
             'allowance, gamma (random instances, all S and lenders | families)')
    L.append('  test allow  gamma    runs  abort%  | fam runs  abort%')
    for k, v in sorted(INFO_R.d.items(), key=lambda x: tuple(map(str, x[0]))):
        if k[0] != 'twin':
            continue
        vf = INFO_F.d.get(k, [0, 0, 0.0, 0.0])
        L.append(f'  {k[1]:4s} {k[2]:5s} {k[3]:6.4f} {v[0]:7d}  {100 * v[1] / v[0]:6.1f}  | {vf[0]:7d}  '
                 f'{(100 * vf[1] / vf[0]) if vf[0] else float("nan"):6.1f}')
    L.append('')
    L.append('Families: ratios to OPT_eager, capped allowance, gamma=1 (guarded: mean over 3 R seeds; '
             'aborts out of 3 in parentheses); C_S/OPT is the safe expert\'s accounted total')
    for r in F:
        cs = ', '.join(f'{k} {v:.3f}' for k, v in sorted(r['CS_over_OPT'].items()))
        L.append(f"  {r['name']}: OPT_eager {r['OPT']:.3f}, rho {r['rho']:.3f}, B0 {r['B0']:.3f}, B_on(T) {r['Bon']:.3f}; "
                 f"C_S/OPT: {cs}; distinct realized omegas solved {r['n_omega_opt']}")
        L.append('    lender  E           E alone | guarded: T0 R_r1  T0 R_rth   T0 T11_r1  T0 T11_rth T0g R_r1   T0g T11_rth '
                 'T1 R_r1    T1 T11_rth')
        for row in r['table']:
            ea = '   -   ' if row['E_alone_over_OPT'] is None else f"{row['E_alone_over_OPT']:7.3f}"
            cells = '  '.join(f"{row[f'{a} {b}_{c}']['ratio']:7.3f}({row[f'{a} {b}_{c}']['aborts']})" for a, b, c in FAM_COLS)
            L.append(f"    {row['lender']:7s} {row['E']:10s} {ea} | {cells}")
    L.append('')
    L.append('Proposition G6 on I_n (one site, C=3, q=2, T=2, n co-located clients): ALG/OPT_eager over S seeds, gamma, lenders eager and t4')
    L.append('  (i) clients at slot 1, E buys one lease per client at slot 0;  (ii) clients at slots 0 and 1, E never buys')
    L.append('  scen  n   test allow S         ratio mean   min      max      abort slots')
    for row in G6['rows']:
        L.append(f"  {row['scen']:4s} {row['n']:3d} {row['test']:4s} {row['allow']:5s} {row['S']:9s} {row['ratio_mean']:9.3f} "
                 f"{row['ratio_min']:8.3f} {row['ratio_max']:8.3f}   {','.join(row['abort_slots'])}")
    L.append('')
    L.append('Tightness of Theorem G2(b)/(c) (T=10, q=10, site 0: delta=0, C=110; site 1 unusable, C=gamma*110-10; '
             'S = FP buying site 0 at slot 0; E buys a site-1 lease at slots 0 and 1; B=0): over the five lenders')
    L.append('  gamma   test  abort slots  ALG (min-max)        (1+gamma) C_S(T)')
    for gamma in GAMMAS:
        for test in TESTS:
            rs = [x for x in TG['rows'] if x['gamma'] == gamma and x['test'] == test]
            L.append(f"  {gamma:6.4f} {test:4s}  {','.join(sorted({str(x['ta']) for x in rs})):11s}  "
                     f"{min(x['ALG'] for x in rs):9.3f}-{max(x['ALG'] for x in rs):9.3f}  {rs[0]['bound_without_M']:9.3f}")
    # ---- K0 check (MS5b, P6): appended so that the lines above reproduce
    kc = K0.cnt
    L.append('')
    L.append('K0 check of the projected guard (MS5b, P6; design/theory/c3_c4_c5_general.md §9: Definition R, Lemma P.1, '
             'Proposition P and its code-level clause; design/sublet_v2.md §8.1)')
    L.append(f"projected-guard runs on the main grid: {kc.get('runs main exact', 0)} exact + {kc.get('runs main float64', 0)} "
             'float64 (S in {FB} + the T11(FB,R) experts with a switch; gamma in {1, 1+1/sqrt2, 3}; tests T0g, T0; '
             'allowances zero, B0, cap; lenders obl0, obl0.2, eager, t4, hold; E: the grid\'s inner policies + adv_hold); '
             f"T11 experts without a switch, equal to FB or R and not rerun: {kc.get('T11 experts without a switch (equal to FB or R; not rerun)', 0)} "
             f"(with a switch: {kc.get('T11 experts with a switch (main grid)', 0)}); negative controls (exact): "
             f"{sum(v[3] for v in K0.neg.values())} runs; core float edge scan: {K0E.cnt.get('edge runs exact', 0)} exact + "
             f"{K0E.cnt.get('edge runs float64', 0)} float64 runs; runtime of the K0 parts {sum(r['secs_k0'] for r in R + F):.0f} s "
             'summed over the jobs')
    L.append('The core has no Load, Unload, Drain or SetAdmission, no robust form of T0g, no stranding (R = S_K0 = 0) and no '
             'refusal: the check covers the skeleton of Proposition P (the step at t-1 and c_S = Q). Exact runs: every cost '
             'an integer on the scale 2^sh (the exact value of the float data), the limit rhs + GUARD_TOL max(1,|rhs|) '
             'with rhs = gamma C_S + B exact (C_S the exact sum of S\'s float increments); float64 runs: the code\'s arithmetic.')
    L.append('Executed candidates (main grid, exact; slots): ' + ', '.join(f'{k} {K0.cands.get(k, 0)}' for k in ('E', 'P1', 'P0', 'K0'))
             + f"; runs with a projected slot: {kc.get('runs main exact with a projected slot', 0)} of {kc.get('runs main exact', 0)}; "
             f"slots K0-checked with S on FB: {kc.get('slots K0-checked on FB (main exact)', 0)}")
    L.append(f"Aborts (main grid, exact): S = FB {kc.get('aborts main exact FB at FB slot', 0)}; S = T11(FB,R) at slots where S "
             f"follows R {kc.get('aborts main exact T11 at R slot', 0)}, where it follows FB {kc.get('aborts main exact T11 at FB slot', 0)}")
    L.append(f'K0 CHECK VIOLATIONS: {k0_viol}')
    L.append('Claims (exact; violation: the exact comparison fails, or a count above 0); slack = RHS - LHS at its minimum, '
             'rel = slack / max(1, |RHS|); for the two K0 lines RHS = gamma C_S(t) + B(t) without tol(t) (exact to 2^-40 of '
             'the scale), and K0 passes iff slack >= -tol(t):')
    cl_all = dict(K0.claims)
    cl_all.update(K0E.claims)
    w = max(len(k) for k in cl_all)
    L.append(f"  {'claim'.ljust(w)}  {'evals':>8} {'viol':>5} {'min slack':>11} {'min rel':>11}  at min")
    for k in sorted(cl_all):
        e = cl_all[k]
        L.append(f'  {k.ljust(w)}  {e[0]:8d} {e[1]:5d} {e[2]:11.3e} {e[3]:11.3e}  {e[4]}')
    L.append('Negative controls (each must fail: failing evaluations > 0 required):')
    w = max(len(k) for k in K0.neg)
    L.append(f"  {'control'.ljust(w)}  {'evals':>7} {'fails':>6} {'aborts':>6} {'runs':>6}  fails>0  first failure at")
    for k in sorted(K0.neg):
        e = K0.neg[k]
        L.append(f"  {k.ljust(w)}  {e[0]:7d} {e[1]:6d} {e[2]:6d} {e[3]:6d}  {'yes' if e[1] > 0 else 'NO':7s}  {e[4]}")
    mxm = K0.mx.get('float64: max m(t)/max(1,ALG(t)) at executed slots', float('nan'))
    L.append(f"Float64 runs (main grid): {kc.get('runs main float64', 0)}; executed lists or abort slot differ from the exact run: "
             f"{kc.get('float64 runs whose executed lists or abort slot differ from the exact run', 0)}; aborts "
             f"{kc.get('float64 aborts', 0)}, at slots where S follows FB {len(K0.clauses)}; K0 fails at slots on FB: "
             f"{kc.get('float64: K0 fails at a slot where S follows FB', 0)}; max m(t)/max(1,ALG(t)) at executed slots {mxm:.3e}")
    ec = K0E.cnt
    L.append('Core float edge scan (one site, one LLM, one client active at slots 0-2, tau=3, H=1; '
             f"{ec.get('edge variants', 0)} variants of beta, delta, q with C + delta > q; S = FB, gamma = 1, T0g, constant B0 "
             'in 81 steps of ulp(ahat(2)) around slot 2\'s edge; E buys at '
             f"slot 2 and releases at slot 3): exact runs {ec.get('edge runs exact', 0)}, aborts "
             f"{sum(v for k, v in ec.items() if k.startswith('edge aborts exact'))}; float64 runs {ec.get('edge runs float64', 0)}, "
             f"aborts {sum(v for k, v in ec.items() if k.startswith('edge aborts float64'))} ("
             + (', '.join(f"at slot {k.split()[-1]}: {v}" for k, v in sorted(ec.items()) if k.startswith('edge aborts float64'))
                or 'none') + '); float64 runs without abort with m(2) > 0: '
             f"{ec.get('edge float64 runs without abort with m(2) > 0', 0)}")
    for lab, cls in (('main grid', K0.clauses), ('edge scan', K0E.clauses)):
        if not cls:
            L.append(f'Code-level clause ("Deciding an abort from one run"), {lab}: no float64 abort with S on FB')
            continue
        L.append(f'Code-level clause ("Deciding an abort from one run"), {lab}: float64 aborts with S on FB {len(cls)}; '
                 f"identity terms add up to X(t_a) exactly {sum(c['sum_ok'] for c in cls)}; (R1) holds {sum(c['R1'] for c in cls)}; "
                 f"(R2) holds {sum(c['R2'] for c in cls)}; rounding aborts {sum(c['rounding'] for c in cls)}; "
                 f"max X(t_a) {max(c['X'] for c in cls):.3e}; max m(t_a-1) {max(c['m'] for c in cls):.3e}")
        c = cls[0]
        L.append(f"  first: {c['where']}: X(t_a) {c['X']:.3e}, m(t_a-1) {c['m']:.3e}; logged values (hex) {json.dumps(c['log'])}")
    txt = '\n'.join(L)
    print(txt)
    open(os.path.join(OUT, 'guard.txt'), 'w').write(txt + '\n')
