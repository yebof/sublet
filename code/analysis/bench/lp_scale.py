"""Timing benchmark (planning only): compact fluid OPT_eager LP/MILP at trace-like sizes.
Variables: n[l,j,k,s] lease starts; x[l,j,t] live replicas <= sum_k sum_{s in (t-D_k, t]} n;
packing sum_j g_j x <= cap[l,t]; z[i,l,t] routing (SLO-feasible pairs only) with
sum_{i of LLM j} z <= kappa_j x[l,j,t]; coverage sum_l z + f >= d. Random data, shapes only."""
import sys, time
import numpy as np, scipy.sparse as sp
from scipy.optimize import milp, LinearConstraint, Bounds

def build(T, m, J, K, n, feas_frac, rng):
    D = np.array([1, 6, 24])[:K]; g = np.array([1, 8, 16])[:J]; kap = np.array([8., 4., 2.])[:J]
    a = rng.uniform(0.2, 0.5, (m, K)) * np.array([1, 1.2, 1.5])[:K]
    beta = rng.uniform(2, 10, (J, m)) * g[:, None]
    cap = rng.integers(16, 64, (m, T)).astype(float)
    cl = rng.integers(0, J, n)
    feas = rng.random((n, m)) < feas_frac
    for i in range(n):
        if not feas[i].any(): feas[i, rng.integers(m)] = True
    d = rng.gamma(2.0, 2.0, (n, T))
    q = 1.0
    # index helpers
    nN = m * J * K * T; nX = m * J * T
    pairs = np.argwhere(feas)                 # (i,l)
    nZ = len(pairs) * T; nF = n * T
    oN, oX, oZ, oF = 0, nN, nN + nX, nN + nX + nZ
    nV = oF + nF
    iN = lambda l, j, k, s: ((l * J + j) * K + k) * T + s
    iX = lambda l, j, t: oX + (l * J + j) * T + t
    cost = np.zeros(nV)
    for l in range(m):
        for j in range(J):
            for k in range(K):
                cost[iN(l, j, k, 0):iN(l, j, k, 0) + T] = beta[j, l] + g[j] * a[l, k] * D[k]
    delta = rng.uniform(0, 0.2, len(pairs))
    cost[oZ:oF] = np.repeat(delta, T)
    cost[oF:] = q
    R, C, V, ub = [], [], [], []
    r = 0
    t_idx = np.arange(T)
    # coverage-by-leases rows: x[l,j,t] - sum_k sum_{s=t-D_k+1..t} n <= 0
    for l in range(m):
        for j in range(J):
            for t in range(T):
                R.append(r); C.append(iX(l, j, t)); V.append(1.0)
                for k in range(K):
                    for s in range(max(0, t - D[k] + 1), t + 1):
                        R.append(r); C.append(iN(l, j, k, s)); V.append(-1.0)
                ub.append(0.0); r += 1
    # packing: sum_j g_j x[l,j,t] <= cap
    for l in range(m):
        for t in range(T):
            for j in range(J):
                R.append(r); C.append(iX(l, j, t)); V.append(float(g[j]))
            ub.append(cap[l, t]); r += 1
    # replica capacity: sum_{i: cl=j, feas} z[i,l,t] - kap_j x[l,j,t] <= 0
    zpos = {}
    for p, (i, l) in enumerate(pairs):
        zpos.setdefault((l, cl[i]), []).append(p)
    for (l, j), ps in zpos.items():
        for t in range(T):
            for p in ps:
                R.append(r); C.append(oZ + p * T + t); V.append(1.0)
            R.append(r); C.append(iX(l, j, t)); V.append(-kap[j])
            ub.append(0.0); r += 1
    # demand coverage: -sum_l z[i,l,t] - f[i,t] <= -d
    zof = {}
    for p, (i, l) in enumerate(pairs):
        zof.setdefault(i, []).append(p)
    for i in range(n):
        for t in range(T):
            for p in zof[i]:
                R.append(r); C.append(oZ + p * T + t); V.append(-1.0)
            R.append(r); C.append(oF + i * T + t); V.append(-1.0)
            ub.append(-d[i, t]); r += 1
    A = sp.csr_matrix((V, (R, C)), shape=(r, nV))
    return cost, A, np.array(ub), nV, nN

def run(T, m, J, K, n, feas_frac, integral, tl):
    rng = np.random.default_rng(0)
    t0 = time.time()
    cost, A, ub, nV, nN = build(T, m, J, K, n, feas_frac, rng)
    tb = time.time() - t0
    integ = np.zeros(nV)
    if integral: integ[:nN] = 1
    t0 = time.time()
    res = milp(cost, constraints=LinearConstraint(A, -np.inf, ub), integrality=integ,
               bounds=Bounds(0, np.inf), options=dict(time_limit=tl, disp=False))
    ts = time.time() - t0
    gap = None
    if integral and res.x is not None:
        lb = getattr(res, 'mip_dual_bound', np.nan); gap = (res.fun - lb) / max(abs(res.fun), 1e-9)
    print(f"T={T} m={m} J={J} K={K} n={n} feas={feas_frac} int={integral} vars={nV} rows={A.shape[0]} nnz={A.nnz} "
          f"build={tb:.1f}s solve={ts:.1f}s status={res.status} gap={gap}", flush=True)

if __name__ == "__main__":
    cfgs = [
        (96, 6, 3, 3, 12, 0.5, True, 300),
        (288, 6, 3, 3, 12, 0.5, True, 300),
        (288, 24, 3, 3, 30, 0.33, False, 1800),
        (2016, 24, 3, 3, 30, 0.33, False, 3600),
    ]
    which = [int(x) for x in sys.argv[1:]] or range(len(cfgs))
    for w in which:
        run(*cfgs[w])
