"""Core ORML model (theory core of design/theory/c3_c4_c5_general.md, Sec. 1).

Instance: T slots, m sites, J LLMs, K contract types (tau_k, H_k), per-site prices
a[l,k] per GPU-slot, loading cost beta[j,l], GPUs per replica g[j], fallback q per
client-slot, persistent clients (LLM, per-slot routing cost delta[c,l], activity mask).

A lease (l,j,k) bought at s costs C = beta[j,l] + g[j]*a[l,k]*L_k (L_k = tau_k + H_k,
prepaid guaranteed window, symmetric-notice simplification) and covers [s, s+L_k)
for sure. After s+L_k it continues at g[j]*a[l,k] per slot until released or
revoked (only relevant for OPT(sigma, omega) and for the 'renew' heuristic).

Solvers:
  opt_eager      MILP, any-start truncated columns  (= OPT under worst-case lender)
  lp_trunc       LP relaxation of the same
  lp_aligned     LP with aligned windows only
  opt_omega      MILP for OPT(sigma, omega) with a per-site announcement schedule
"""
import numpy as np
import scipy.sparse as sp
from scipy.optimize import milp, LinearConstraint, Bounds
from dataclasses import dataclass


@dataclass
class Instance:
    T: int
    tau: np.ndarray      # (K,)
    H: np.ndarray        # (K,)
    a: np.ndarray        # (m,K)
    beta: np.ndarray     # (J,m)
    g: np.ndarray        # (J,)
    q: float
    cl_llm: np.ndarray   # (n,)
    delta: np.ndarray    # (n,m), np.inf = infeasible (SLO)
    active: np.ndarray   # (n,T) bool
    owner: np.ndarray = None  # (n,) borrower id

    @property
    def m(self):
        return self.a.shape[0]

    @property
    def K(self):
        return len(self.tau)

    @property
    def J(self):
        return len(self.g)

    @property
    def n(self):
        return len(self.cl_llm)

    @property
    def L(self):
        return (self.tau + self.H).astype(int)

    def C(self, l, j, k):
        return float(self.beta[j, l] + self.g[j] * self.a[l, k] * self.L[k])

    def rent(self, l, j, k):
        return float(self.g[j] * self.a[l, k])

    def elements(self):
        """client-time requests (c,t), ordered by time."""
        el = [(c, t) for t in range(self.T) for c in range(self.n) if self.active[c, t]]
        return el

    def lj_pairs(self):
        """(l,j) pairs at which some client of LLM j is feasible."""
        s = set()
        for c in range(self.n):
            for l in range(self.m):
                if np.isfinite(self.delta[c, l]):
                    s.add((l, int(self.cl_llm[c])))
        return sorted(s)

    def rho(self):
        """rho = max_{j,l,k} (beta + g a L)/(g a L) over usable (l,j)."""
        r = 1.0
        for (l, j) in self.lj_pairs():
            for k in range(self.K):
                r = max(r, self.C(l, j, k) / (self.rent(l, j, k) * self.L[k]))
        return r

    def subset(self, clients=None, contracts=None):
        """restrict to a subset of clients and/or contract types."""
        import copy
        I = copy.deepcopy(self)
        if clients is not None:
            clients = np.asarray(clients)
            I.cl_llm = I.cl_llm[clients]
            I.delta = I.delta[clients]
            I.active = I.active[clients]
            if I.owner is not None:
                I.owner = I.owner[clients]
        if contracts is not None:
            contracts = np.asarray(contracts)
            I.tau = I.tau[contracts]
            I.H = I.H[contracts]
            I.a = I.a[:, contracts]
        return I


# ---------------------------------------------------------------- columns
def any_start_columns(I):
    cols = []
    for (l, j) in I.lj_pairs():
        for k in range(I.K):
            for s in range(I.T):
                cols.append((l, j, k, s, s, min(s + I.L[k], I.T), I.C(l, j, k)))
    return cols


def aligned_columns(I):
    cols = []
    for (l, j) in I.lj_pairs():
        for k in range(I.K):
            Lk = I.L[k]
            for s in range(0, I.T, Lk):
                cols.append((l, j, k, s, s, min(s + Lk, I.T), I.C(l, j, k)))
    return cols


# ---------------------------------------------------------------- facility-leasing (MI)LP
def solve_fl(I, cols, integral, time_limit=120.0):
    """min sum C x + sum delta z + q f  s.t. coverage. cols: (l,j,k,s,start,end,cost).
    Returns dict(fun, lb, x, status)."""
    el = I.elements()
    nE = len(el)
    if nE == 0:
        return dict(fun=0.0, lb=0.0, status=0, x=np.zeros(len(cols)), cols=cols)
    nX = len(cols)
    # index columns by (l,j) -> list of (idx,start,end)
    by_lj = {}
    for i, (l, j, k, s, st, en, cst) in enumerate(cols):
        by_lj.setdefault((l, j), []).append((i, st, en))
    # z variables for feasible (e,l)
    zidx = []
    for ei, (c, t) in enumerate(el):
        for l in range(I.m):
            if np.isfinite(I.delta[c, l]) and (l, int(I.cl_llm[c])) in by_lj:
                zidx.append((ei, l))
    nZ = len(zidx)
    nV = nX + nZ + nE
    cost = np.zeros(nV)
    cost[:nX] = [col[6] for col in cols]
    for zi, (ei, l) in enumerate(zidx):
        c, t = el[ei]
        cost[nX + zi] = I.delta[c, l]
    cost[nX + nZ:] = I.q
    rows, cidx, vals = [], [], []
    r = 0
    # coverage rows: -sum z - f <= -1
    z_of_e = {}
    for zi, (ei, l) in enumerate(zidx):
        z_of_e.setdefault(ei, []).append(zi)
    for ei in range(nE):
        for zi in z_of_e.get(ei, []):
            rows.append(r); cidx.append(nX + zi); vals.append(-1.0)
        rows.append(r); cidx.append(nX + nZ + ei); vals.append(-1.0)
        r += 1
    nCov = r
    # linking rows: z - sum x <= 0
    for zi, (ei, l) in enumerate(zidx):
        c, t = el[ei]
        j = int(I.cl_llm[c])
        rows.append(r); cidx.append(nX + zi); vals.append(1.0)
        for (i, st, en) in by_lj[(l, j)]:
            if st <= t < en:
                rows.append(r); cidx.append(i); vals.append(-1.0)
        r += 1
    A = sp.csr_matrix((vals, (rows, cidx)), shape=(r, nV))
    ub = np.zeros(r)
    ub[:nCov] = -1.0
    cons = LinearConstraint(A, -np.inf, ub)
    integ = np.zeros(nV)
    if integral:
        integ[:nX] = 1
    bounds = Bounds(np.zeros(nV), np.ones(nV))
    res = milp(cost, constraints=cons, integrality=integ, bounds=bounds,
               options=dict(time_limit=time_limit, disp=False))
    out = dict(fun=float(res.fun) if res.x is not None else np.nan, status=int(res.status))
    if integral:
        lb = getattr(res, 'mip_dual_bound', None)
        out['lb'] = float(lb) if lb is not None and np.isfinite(lb) else out['fun']
    else:
        out['lb'] = out['fun']
    out['x'] = res.x[:nX] if res.x is not None else None
    out['cols'] = cols
    return out


def opt_eager(I, time_limit=120.0):
    return solve_fl(I, any_start_columns(I), True, time_limit)


def lp_trunc(I):
    return solve_fl(I, any_start_columns(I), False)


def lp_aligned(I):
    return solve_fl(I, aligned_columns(I), False)


def opt_eager_cols(I, sol):
    """integral OPT_eager solution -> list of (l,j,k,s) columns."""
    return [(c[0], c[1], c[2], c[3]) for c, v in zip(sol['cols'], sol['x']) if v > 0.5]


# ---------------------------------------------------------------- reclaim schedules
def effective_end(I, omega, l, k, s):
    """omega[l]: sorted array of announcement times at site l.  A lease (l,k) bought at s
    is announced at the first r >= s+tau_k and ends at r+H_k (never before s+L_k)."""
    ann = omega[l]
    idx = np.searchsorted(ann, s + I.tau[k])
    if idx >= len(ann):
        return 10 ** 9
    return int(ann[idx] + I.H[k])


def opt_omega(I, omega, time_limit=120.0, relax=False):
    """MILP for OPT(sigma, omega): open o[l,j,k,s] (cost C, covers [s,s+L)), extension
    h[l,j,k,s,t] for t in [s+L, min(E,T)) (cost g a), contiguous."""
    el = I.elements()
    nE = len(el)
    T = I.T
    ocols = []        # (l,j,k,s)
    hvars = []        # (oi, t)
    for (l, j) in I.lj_pairs():
        for k in range(I.K):
            for s in range(T):
                oi = len(ocols)
                ocols.append((l, j, k, s))
                E = min(effective_end(I, omega, l, k, s), T)
                for t in range(s + I.L[k], E):
                    hvars.append((oi, t))
    nO, nH = len(ocols), len(hvars)
    zidx = []
    ljset = set(I.lj_pairs())
    for ei, (c, t) in enumerate(el):
        for l in range(I.m):
            if np.isfinite(I.delta[c, l]) and (l, int(I.cl_llm[c])) in ljset:
                zidx.append((ei, l))
    nZ = len(zidx)
    nV = nO + nH + nZ + nE
    cost = np.zeros(nV)
    for oi, (l, j, k, s) in enumerate(ocols):
        cost[oi] = I.C(l, j, k)
    for hi, (oi, t) in enumerate(hvars):
        l, j, k, s = ocols[oi]
        cost[nO + hi] = I.rent(l, j, k)
    for zi, (ei, l) in enumerate(zidx):
        c, t = el[ei]
        cost[nO + nH + zi] = I.delta[c, l]
    cost[nO + nH + nZ:] = I.q
    rows, cidx, vals = [], [], []
    ub = []
    r = 0
    z_of_e = {}
    for zi, (ei, l) in enumerate(zidx):
        z_of_e.setdefault(ei, []).append(zi)
    for ei in range(nE):
        for zi in z_of_e.get(ei, []):
            rows.append(r); cidx.append(nO + nH + zi); vals.append(-1.0)
        rows.append(r); cidx.append(nO + nH + nZ + ei); vals.append(-1.0)
        ub.append(-1.0); r += 1
    # contiguity: h[oi,t] <= h[oi,t-1] (or <= o[oi] for first)
    prev = {}
    for hi, (oi, t) in enumerate(hvars):
        rows.append(r); cidx.append(nO + hi); vals.append(1.0)
        if oi in prev:
            rows.append(r); cidx.append(nO + prev[oi]); vals.append(-1.0)
        else:
            rows.append(r); cidx.append(oi); vals.append(-1.0)
        prev[oi] = hi
        ub.append(0.0); r += 1
    # coverage of (l,j,t)
    cover = {}
    for oi, (l, j, k, s) in enumerate(ocols):
        for t in range(s, min(s + I.L[k], T)):
            cover.setdefault((l, j, t), []).append(oi)
    for hi, (oi, t) in enumerate(hvars):
        l, j, k, s = ocols[oi]
        cover.setdefault((l, j, t), []).append(nO + hi)
    for zi, (ei, l) in enumerate(zidx):
        c, t = el[ei]
        j = int(I.cl_llm[c])
        rows.append(r); cidx.append(nO + nH + zi); vals.append(1.0)
        for v in cover.get((l, j, t), []):
            rows.append(r); cidx.append(v); vals.append(-1.0)
        ub.append(0.0); r += 1
    A = sp.csr_matrix((vals, (rows, cidx)), shape=(r, nV))
    cons = LinearConstraint(A, -np.inf, np.array(ub))
    integ = np.zeros(nV)
    if not relax:
        integ[:nO + nH] = 1
    res = milp(cost, constraints=cons, integrality=integ,
               bounds=Bounds(np.zeros(nV), np.ones(nV)),
               options=dict(time_limit=time_limit, disp=False))
    fun = float(res.fun) if res.x is not None else np.nan
    lb = getattr(res, 'mip_dual_bound', None) if not relax else fun
    lb = float(lb) if lb is not None and np.isfinite(lb) else fun
    return dict(fun=fun, lb=lb, status=int(res.status))


# ---------------------------------------------------------------- generators
def random_instance(rng, T=36, m=4, J=2, n=8, K=3, slo=None, q=4.0,
                    contracts=None, beta_rng=(3.0, 8.0), on_mean=10, off_mean=6,
                    n_borrowers=None):
    if contracts is None:
        # (tau, H, price multiplier): spot-like, notice contract, long commitment
        contracts = [(1, 1, 1.0), (4, 2, 1.25), (12, 6, 1.6)][:K]
    tau = np.array([c[0] for c in contracts])
    H = np.array([c[1] for c in contracts])
    mult = np.array([c[2] for c in contracts])
    base = rng.uniform(0.8, 1.2, size=m)
    a = np.outer(base, mult)
    g = rng.choice([1, 2], size=J)
    beta = rng.uniform(*beta_rng, size=(J, m)) * g[:, None]
    sites = rng.uniform(0, 1, size=(m, 2))
    cl = rng.uniform(0, 1, size=(n, 2))
    dist = np.linalg.norm(cl[:, None, :] - sites[None, :, :], axis=2)
    delta = 1.0 * dist
    if slo is not None:
        delta = np.where(dist <= slo, delta, np.inf)
        # make sure each client has a feasible site
        for c in range(n):
            if not np.isfinite(delta[c]).any():
                l = int(np.argmin(dist[c])); delta[c, l] = dist[c, l]
    cl_llm = rng.integers(0, J, size=n)
    active = np.zeros((n, T), dtype=bool)
    for c in range(n):
        t = int(rng.integers(0, off_mean + 1))
        while t < T:
            on = 1 + rng.geometric(1.0 / on_mean)
            active[c, t:t + on] = True
            t += on + rng.geometric(1.0 / off_mean)
    owner = None
    if n_borrowers is not None:
        owner = rng.integers(0, n_borrowers, size=n)
    return Instance(T=T, tau=tau, H=H, a=a, beta=beta, g=g, q=q, cl_llm=cl_llm,
                    delta=delta, active=active, owner=owner)


def random_omega(rng, I, rate):
    """oblivious per-site announcement schedule: Bernoulli(rate) per site-slot."""
    return [np.sort(np.nonzero(rng.random(I.T) < rate)[0]) for _ in range(I.m)]
