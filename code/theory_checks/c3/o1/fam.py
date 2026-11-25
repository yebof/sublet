"""O1 helpers: the single-LLM, always-active-client family of Theorem 4
(design/theory/c3_c4_c5_general.md, Sec. 4) and design/theory/o1_oblivious_lender.md.

Model.  m sites, one contract (tau, H), D = tau + H, rent a per slot, loading cost beta,
rho = 1 + beta/(a D).  A lease bought at s at site l costs beta + a*max(D, held) and covers
[s, death), death = r + H with r = first announcement in R_l with r >= s + tau (death =
infinity if none).  Slots 0..T-1 must all be covered (fallback q >= beta + a per slot).

Schedules omega: list of sorted int arrays R_l.
"""
import math
import numpy as np

INF = 10 ** 9


class Fam:
    def __init__(self, m, rho, tau, H, T, a=1.0):
        self.m, self.tau, self.H, self.T, self.a = m, int(tau), int(H), int(T), float(a)
        self.D = self.tau + self.H
        self.rho = float(rho)
        self.beta = (rho - 1.0) * a * self.D
        self.q = self.beta + a * self.D + 1.0

    def ann(self, omega, l, s):
        """first announcement r >= s + tau at site l (INF if none)."""
        R = omega[l]
        i = np.searchsorted(R, s + self.tau)
        return int(R[i]) if i < len(R) else INF

    def death(self, omega, l, s):
        r = self.ann(omega, l, s)
        return r + self.H if r < INF else INF

    def lease_cost(self, s, release):
        return self.beta + self.a * max(self.D, release - s)

    def core_instance(self):
        """same instance in the core model of code/theory_checks/c3/core.py (for MILP cross-checks)."""
        import os, sys
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
        from core import Instance
        m, T = self.m, self.T
        return Instance(T=T, tau=np.array([self.tau]), H=np.array([self.H]),
                        a=np.full((m, 1), self.a), beta=np.full((1, m), self.beta),
                        g=np.array([1]), q=self.q, cl_llm=np.array([0]),
                        delta=np.zeros((1, m)), active=np.ones((1, T), dtype=bool))


# ------------------------------------------------------------------ exact OPT(sigma, omega)
def opt_dp(F, omega):
    """Exact OPT(sigma, omega) on the family by DP over 'next uncovered slot'.
    f(t) = min( q + f(t+1),  min_{l, t < e <= min(death(l,t), T)} beta + a max(D, e-t) + f(e) ).
    Returns (cost, number of purchases + fallback slots on an optimal plan)."""
    T = F.T
    f = np.zeros(T + 1)
    cnt = np.zeros(T + 1, dtype=int)
    for t in range(T - 1, -1, -1):
        best, bc = F.q + f[t + 1], cnt[t + 1] + 1
        for l in range(F.m):
            d = min(F.death(omega, l, t), T)
            for e in range(t + 1, d + 1):
                v = F.lease_cost(t, e) + f[e]
                if v < best - 1e-12 or (abs(v - best) <= 1e-12 and cnt[e] + 1 < bc):
                    best, bc = v, cnt[e] + 1
        f[t], cnt[t] = best, bc
    return float(f[0]), int(cnt[0])


# ------------------------------------------------------------------ schedules
def all_slots(T):
    return np.arange(T, dtype=int)


def safe_site_schedule(F, k, Phi, rng, S=None):
    """Phase construction of Theorem O1-A: Phi phases of length P = k D; in phase i exactly one
    'safe' site S_i (uniform, S_i != S_{i-1}) has no announcement; every other site announces
    in every slot of the phase.  Returns (omega, S)."""
    m, P = F.m, k * F.D
    if S is None:
        S = [int(rng.integers(m))]
        for _ in range(1, Phi):
            c = [l for l in range(m) if l != S[-1]]
            S.append(int(c[rng.integers(len(c))]))
    om = [[] for _ in range(m)]
    for i, si in enumerate(S):
        for l in range(m):
            if l != si:
                om[l].extend(range(i * P, (i + 1) * P))
    return [np.array(sorted(o), dtype=int) for o in om], S


def iid_step_schedule(F, p, U, rng):
    """Theorem O1-C construction: steps of length D; at slot uD (u = 1..U-1) each site is
    announced independently with probability p."""
    om = [[] for _ in range(F.m)]
    for u in range(1, U):
        for l in range(F.m):
            if rng.random() < p:
                om[l].append(u * F.D)
    return [np.array(o, dtype=int) for o in om]


def bernoulli_schedule(F, rate, rng):
    return [np.nonzero(rng.random(F.T) < rate)[0].astype(int) for _ in range(F.m)]


# ------------------------------------------------------------------ algorithms
def run_renew(F, omega, choose, rng=None):
    """Hold one lease; keep it (paying rent) while it survives; when it dies at d buy the next
    one at d at site choose(prev_site, rng).  Returns (cost, number of leases)."""
    t, site, cost, n = 0, None, 0.0, 0
    while t < F.T:
        site = choose(site, rng)
        d = F.death(omega, site, t)
        cost += F.lease_cost(t, min(d, F.T))
        n += 1
        t = d
    return cost, n


def rr_choose(m):
    return lambda prev, rng: 0 if prev is None else (prev + 1) % m


def stay_choose(prev, rng):
    return 0


def rand_choose(m):
    def c(prev, rng):
        if prev is None or m == 1:
            return int(rng.integers(m))
        x = int(rng.integers(m - 1))
        return x if x < prev else x + 1
    return c


def run_eager(F):
    n = math.ceil(F.T / F.D)
    return sum(F.lease_cost(i * F.D, min((i + 1) * F.D, F.T)) for i in range(n)), n


def marking_phases(F, omega):
    """Phases of the full-information marking algorithm (depend on omega only).
    Phase j starts at p_j (p_0 = 0); site l is marked at the first announcement r in R_l with
    r >= p_j + tau; p'_j = time the last site is marked; p_{j+1} = p'_j + H.
    Returns list of (p_j, p'_j or None)."""
    ph, p = [], 0
    while p < F.T:
        marks = [F.ann(omega, l, p) for l in range(F.m)]   # first r >= p + tau
        pe = max(marks)
        if pe >= F.T:
            ph.append((p, None)); break
        ph.append((p, pe))
        p = pe + F.H
    return ph


def run_marking(F, omega, rng):
    """Full-information randomized marking (Theorem O1-D).  Within a phase the algorithm holds
    one lease at a uniformly random unmarked site; when its site becomes marked (whether or not
    its own lease is hit) it buys a fresh lease at a uniformly random still-unmarked site at the
    same slot; when all sites are marked it keeps its lease until p_{j+1}, where it buys a fresh
    lease at a uniformly random site.  Returns (cost, number of leases)."""
    T, m = F.T, F.m
    phases = marking_phases(F, omega)
    cost, n = 0.0, 0
    cur = None  # (site, s)

    def close(c, t):
        nonlocal cost
        if c is not None:
            s = c[1]
            assert F.death(omega, c[0], s) >= t, 'coverage gap'
            cost += F.lease_cost(s, min(t, T))

    for (p, pe) in phases:
        close(cur, p)
        cur = (int(rng.integers(m)), p); n += 1
        marks = {l: F.ann(omega, l, p) for l in range(m)}
        end = pe if pe is not None else T
        # process marking events in time order
        for t in sorted(set(v for v in marks.values() if v <= end and v < T)):
            newly = [l for l in range(m) if marks[l] == t]
            unmarked = [l for l in range(m) if marks[l] > t]
            if cur[0] in newly and unmarked:
                close(cur, t)
                cur = (int(unmarked[rng.integers(len(unmarked))]), t); n += 1
        # until the next phase start (or T) the current lease is kept; check it survives
    close(cur, T)
    return cost, n


def marking_expected_leases(F, omega):
    """Exact E[number of leases] of run_marking: per phase 1 + sum over marking events that
    leave some site unmarked of k/u (k sites marked at that slot, u unmarked just before)."""
    tot = 0.0
    for (p, pe) in marking_phases(F, omega):
        tot += 1.0
        marks = [F.ann(omega, l, p) for l in range(F.m)]
        end = pe if pe is not None else F.T
        u = F.m
        for t in sorted(set(v for v in marks if v <= end and v < F.T)):
            k = sum(1 for v in marks if v == t)
            if u - k > 0:
                tot += k / u
            u -= k
    return tot
