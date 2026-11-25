"""Online algorithms for the ORML core (design/theory/c3_c4_c5_general.md, Sec. 3, 5).

FracPD   : multiplicative primal-dual on the exponential covering form of the
           truncated-column facility-leasing LP (aligned windows), optional
           lambda-interpolation with a predicted solution (Sec. 5).
round_pd : threshold rounding (theta_F = min of r uniforms), analysed rule and
           practical rule.
real_cost_renew : cost of the integral solution when surviving leases are renewed
           (pay rent only) under a per-site reclaim schedule omega.
follow_prediction, combine : FP algorithm and the doubling combiner.
"""
import math
import numpy as np
from scipy.optimize import brentq


def _solve_Y(vals, bs, cs):
    """find Y>0 with sum_v (v+b) exp(Y/c) - b = 1."""
    vals = np.asarray(vals); bs = np.asarray(bs); cs = np.asarray(cs)

    def h(Y):
        return float(np.sum((vals + bs) * np.exp(np.minimum(Y / cs, 700.0)) - bs) - 1.0)
    lo, hi = 0.0, float(np.min(cs)) * 1e-3
    while h(hi) < 0:
        lo, hi = hi, hi * 2.0
    return brentq(h, lo, hi, xtol=1e-14, rtol=1e-12, maxiter=500)


class FracPD:
    def __init__(self, I, lam=1.0, pred_cols=None, nearest_pred=False):
        """nearest_pred=True: add only the nearest predicted column F_hat(e) to each request's
        candidate set (the audit's T9 fix), so d <= mK + 2 independently of the prediction."""
        self.I = I
        self.lam = lam
        self.nearest_pred = nearest_pred
        self.pred = []  # list of (l,j,k,s)
        if pred_cols is not None and lam < 1.0:
            self.pred = list(pred_cols)
        # d = max number of variables in one constraint
        pmax = 0
        for t in range(I.T):
            for j in range(I.J):
                cnt = sum(1 for (l, jj, k, s) in self.pred if jj == j and s <= t < s + I.L[k])
                pmax = max(pmax, cnt)
        self.d = I.m * I.K + 1 + (min(pmax, 1) if nearest_pred else pmax)
        self.x = {}
        self.load = {}       # dual load per variable key
        self.cost_of = {}    # cost per variable key (for checks)
        self.dual = 0.0
        self.serv_cost = 0.0
        self.records = []    # per element: (c,t,cand,xs,ys,f,deltas)
        self.max_iter_hit = 0

    def cands(self, c, t):
        I = self.I
        j = int(I.cl_llm[c])
        out = []
        for l in range(I.m):
            if not np.isfinite(I.delta[c, l]):
                continue
            for k in range(I.K):
                Lk = I.L[k]
                out.append(('A', l, j, k, (t // Lk) * Lk))
            if not self.nearest_pred:
                for (pl, pj, pk, ps) in self.pred:
                    if pl == l and pj == j and ps <= t < ps + I.L[pk]:
                        out.append(('P', pl, pj, pk, ps))
        if self.nearest_pred:
            pc = [(float(I.delta[c, pl]), i, (pl, pj, pk, ps)) for i, (pl, pj, pk, ps) in enumerate(self.pred)
                  if pj == j and ps <= t < ps + I.L[pk] and np.isfinite(I.delta[c, pl])]
            if pc:
                out.append(('P',) + min(pc)[2])
        return out

    def process(self, c, t):
        I = self.I
        cand = self.cands(c, t)
        dl = {F: float(I.delta[c, F[1]]) for F in cand}
        y = {F: (1.0 if dl[F] == 0 else 0.0) for F in cand}
        f = 0.0
        for F in cand:
            self.x.setdefault(F, 0.0)
            self.cost_of[('x', F)] = I.C(F[1], F[2], F[3])
        # predicted variables for this element
        phat = set()
        if self.pred:
            pc = [F for F in cand if F[0] == 'P']
            if pc:
                Fp = min(pc, key=lambda F: dl[F])
                if dl[Fp] < I.q:
                    phat = {('x', Fp), ('y', Fp)}
            if not phat:
                phat = {('f',)}
        it = 0
        while True:
            w = sum(min(self.x[F], y[F]) for F in cand) + f
            if w >= 1.0 - 1e-10:
                break
            it += 1
            if it > 2000:
                self.max_iter_hit += 1
                break
            V = []
            for F in cand:
                V.append(('x', F) if self.x[F] <= y[F] else ('y', F))
            V.append(('f',))
            Pe = [v for v in V if v in phat]
            vals, cs, bs = [], [], []
            for v in V:
                if v[0] == 'x':
                    vals.append(self.x[v[1]]); cs.append(self.cost_of[v])
                elif v[0] == 'y':
                    vals.append(y[v[1]]); cs.append(dl[v[1]])
                else:
                    vals.append(f); cs.append(I.q)
                if Pe:
                    bs.append(self.lam / self.d + (1 - self.lam) * (v in Pe) / len(Pe))
                else:
                    bs.append(1.0 / self.d)
            Y = _solve_Y(vals, bs, cs)
            for v, v0, b, cv in zip(V, vals, bs, cs):
                nv = (v0 + b) * math.exp(min(Y / cv, 700.0)) - b
                if v[0] == 'x':
                    self.x[v[1]] = nv
                    key = v
                elif v[0] == 'y':
                    y[v[1]] = nv
                    key = ('y', (c, t), v[1])
                    self.cost_of[key] = cv
                else:
                    f = nv
                    key = ('f', (c, t))
                    self.cost_of[key] = cv
                self.load[key] = self.load.get(key, 0.0) + Y
            self.dual += Y
        self.serv_cost += sum(dl[F] * y[F] for F in cand) + I.q * f
        self.records.append((c, t, cand, {F: self.x[F] for F in cand}, dict(y), f, dl))

    def run(self):
        for (c, t) in self.I.elements():
            self.process(c, t)
        return self

    def primal(self):
        I = self.I
        fac = sum(I.C(F[1], F[2], F[3]) * v for F, v in self.x.items())
        return fac + self.serv_cost

    def check_dual_feasible(self):
        """max over variables of load / (cost * ln(1 + d/lam_eff))."""
        lam_eff = self.lam if self.pred else 1.0
        worst = 0.0
        for key, ld in self.load.items():
            cv = self.cost_of[key]
            if cv > 0:
                worst = max(worst, ld / (cv * math.log(1 + self.d / lam_eff)))
        return worst


def pred_cost(I, pred_cols):
    """c(P_hat(sigma)): predicted columns + per element min(q, min delta to predicted col)."""
    tot = sum(I.C(l, j, k) for (l, j, k, s) in pred_cols)
    for (c, t) in I.elements():
        j = int(I.cl_llm[c])
        best = I.q
        for (l, jj, k, s) in pred_cols:
            if jj == j and s <= t < s + I.L[k] and I.delta[c, l] < best:
                best = I.delta[c, l]
        tot += best
    return tot


# ---------------------------------------------------------------- rounding
def round_pd(pd, rng, N=None, r=None):
    """Threshold rounding of a FracPD run.  Returns dict with analysed-rule cost,
    practical-rule cost, open events (F, time) of the practical rule, and per-slot
    cost curve of the practical rule."""
    I = pd.I
    if N is None:
        N = max(I.n * I.T, 3)   # a-priori upper bound on #client-slot requests
    if r is None:
        r = int(math.ceil(2 * math.log(N)))
    theta = {}

    def th(F):
        if F not in theta:
            theta[F] = 1.0 - rng.random() ** (1.0 / r)
        return theta[F]
    opened_thr = {}      # F -> time opened by threshold
    opened_prac = {}     # F -> time opened (threshold or fixup), practical rule
    cost_an = 0.0
    cost_pr = 0.0
    curve = np.zeros(I.T)
    n_fix_an = 0
    for (c, t, cand, xs, ys, f, dl) in pd.records:
        # threshold openings
        for F in cand:
            if F not in opened_thr and xs[F] > th(F):
                opened_thr[F] = t
                cst = I.C(F[1], F[2], F[3])
                cost_an += cst
                if F not in opened_prac:
                    opened_prac[F] = t
                    cost_pr += cst; curve[t] += cst
        # analysed rule
        if f >= 0.5:
            cost_an += I.q
        else:
            usable = [F for F in cand if min(xs[F], ys[F]) > th(F)]
            if usable:
                cost_an += min(dl[F] for F in usable)
            else:
                n_fix_an += 1
                cost_an += min([I.q] + [I.C(F[1], F[2], F[3]) + dl[F] for F in cand])
        # practical rule
        best, bestF = I.q, None
        for F in cand:
            cc = dl[F] if F in opened_prac else I.C(F[1], F[2], F[3]) + dl[F]
            if cc < best:
                best, bestF = cc, F
        if bestF is not None and bestF not in opened_prac:
            opened_prac[bestF] = t
            cst = I.C(bestF[1], bestF[2], bestF[3])
            cost_pr += cst; curve[t] += cst
            best -= cst
            cost_pr += best; curve[t] += best
        else:
            cost_pr += best; curve[t] += best
    return dict(cost_an=cost_an, cost_pr=cost_pr, opened=opened_prac, curve=curve,
                r=r, n_fix_an=n_fix_an, service_only=None)


def service_cost_given_open(I, opened):
    """per-slot service cost (connection/fallback) given open columns -> time."""
    curve = np.zeros(I.T)
    for (c, t) in I.elements():
        j = int(I.cl_llm[c])
        best = I.q
        for F, t0 in opened.items():
            _, l, jj, k, s = F
            if jj == j and t0 <= t < s + I.L[k] and I.delta[c, l] < best:
                best = I.delta[c, l]
        curve[t] += best
    return curve


def real_cost_renew(I, opened, omega, adversary=False):
    """Execute the integral solution with lease renewal.  For each (l,j,k) the needed
    coverage is U = union over opened windows F of [open time, window end).  A lease is
    bought (cost C) when coverage is needed and none is alive; past its prepaid window it
    is kept at rent g*a per slot while needed; it dies at the reclaim end.
    If adversary=True, omega is built adaptively: site l gets an announcement at every
    time an alive lease there reaches age tau (cat-and-mouse).  Returns (cost, omega)."""
    T = I.T
    need = {}
    for F, t0 in opened.items():
        _, l, j, k, s = F
        key = (l, j, k)
        U = need.setdefault(key, np.zeros(T, dtype=bool))
        U[t0:min(s + I.L[k], T)] = True
    ann = [set() for _ in range(I.m)] if adversary else [set(map(int, o)) for o in omega]
    leases = {key: None for key in need}   # key -> [start, end(effective or None)]
    cost = 0.0
    for t in range(T):
        # adversary: announce at sites where a lease reaches age tau now
        if adversary:
            for key, ls in leases.items():
                if ls is not None and t == ls[0] + I.tau[key[2]]:
                    ann[key[0]].add(t)
        for key, U in need.items():
            l, j, k = key
            ls = leases[key]
            # determine whether the current lease is dead at t
            if ls is not None:
                s0 = ls[0]
                rs = [r for r in ann[l] if r >= s0 + I.tau[k] and r <= t]
                if rs and min(rs) + I.H[k] <= t:
                    ls = None
            if U[t]:
                if ls is None:
                    ls = [t]
                    cost += I.C(l, j, k)
                    if adversary and I.tau[k] == 0:
                        ann[l].add(t)
                elif t >= ls[0] + I.L[k]:
                    cost += I.rent(l, j, k)
            else:
                if ls is not None and t >= ls[0] + I.L[k]:
                    ls = None   # release
            leases[key] = ls
    om = [np.array(sorted(a), dtype=int) for a in ann]
    return cost, om


# ---------------------------------------------------------------- learning-augmented
def follow_prediction(I, pred_cols):
    """FP: buy each predicted column at its start, serve each element by min(q, min delta).
    Returns (cost curve, state function)."""
    curve = np.zeros(I.T)
    for (l, j, k, s) in pred_cols:
        if s < I.T:
            curve[s] += I.C(l, j, k)
    for (c, t) in I.elements():
        j = int(I.cl_llm[c])
        best = I.q
        for (l, jj, k, s) in pred_cols:
            if jj == j and s <= t < s + I.L[k] and I.delta[c, l] < best:
                best = I.delta[c, l]
        curve[t] += best
    return curve


def combine(I, pred_cols, curve_fp, opened_R, curve_R, gamma=2.0):
    """Doubling combiner.  Follow X until its cumulative simulated cost would exceed
    gamma * (other's cumulative cost); then buy the other's alive leases and follow it.
    Returns (total cost, number of switches)."""
    T = I.T
    CF = np.cumsum(curve_fp)
    CR = np.cumsum(curve_R)
    cur = 'F' if CF[0] <= CR[0] else 'R'
    total = 0.0
    switches = 0

    def state_cost(which, t):
        if which == 'F':
            return sum(I.C(l, j, k) for (l, j, k, s) in pred_cols if s <= t < s + I.L[k])
        return sum(I.C(F[1], F[2], F[3]) for F, t0 in opened_R.items()
                   if t0 <= t and F[4] + I.L[F[3]] > t)

    def serv(which, t):
        # service cost at t of the followed algorithm = its curve minus purchases at t
        if which == 'F':
            buys = sum(I.C(l, j, k) for (l, j, k, s) in pred_cols if s == t)
            return curve_fp[t] - buys
        buys = sum(I.C(F[1], F[2], F[3]) for F, t0 in opened_R.items() if t0 == t)
        return curve_R[t] - buys
    for t in range(T):
        Cx = CF if cur == 'F' else CR
        Cy = CR if cur == 'F' else CF
        prev = Cx[t - 1] if t > 0 else 0.0
        inc = (curve_fp if cur == 'F' else curve_R)[t]
        if prev + inc > gamma * Cy[t] + 1e-12:
            cur = 'R' if cur == 'F' else 'F'
            switches += 1
            total += state_cost(cur, t) + serv(cur, t)
        else:
            total += inc
    return total, switches
