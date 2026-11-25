"""Single-site DP for OPT(sigma, omega) on a bench grid (design/sim_spec.md §7).

The DP is exact on the domain of §7.1 (one client and one LLM; at most one usable site with
revocable contracts; equal routing costs at the usable sites; on/off demand of at most one
replica load on the bench grid; mu_kv = 0; every usable site of unlimited capacity or of at
least (N_Q + 2) g_j GPUs) over the plan class of §7.3: one replica per lease; a serving lease
that is always warm and serves all of the demand or none of it; the leases bought at the last
N_Q decision slots whose replicas are still loading, at most one per site and slot; a lease
starts to serve when its replica turns warm or never serves. Claim D2 (§7.6, CONJECTURE until
its tests pass) is that this class loses nothing on the domain, so that DP = MILP (§8).

The DP builds its own discrete model from an Instance and a Schedule (rules T5-T10 of §3.1
with the bench slot in place of the fast slot). It shares no discretization code with
opt/milp.py (§2.2); the death table comes from reclaim.death_bench.

State at the start of bench slot t, before the deaths of slot t, stored densely as an array
of shape (n_p, n_q, 2):
  p      index 0: no serving lease; per option o the ages Lambda_o .. Y_o - 1 ("young"), then
         one entry "old" (age >= Y_o; its death follows from t by Lemma D1, §7.2);
  Q      mixed-radix code of the loading leases: for each site whose load time Lambda is
         positive and each position i = 0 .. ceil(Lambda / phi_b) - 1 (the (i+1)-th last
         decision slot before t), 0 or the 1-based index of the option bought there;
  sigma  1 if the demand was served in slot t - 1.
Young ages whose start is not a decision slot, and Q digits of expired positions, are
unreachable; they are kept so that every stage is a plain gather (ages shift by one per slot).

The backward recurrence makes one vectorized step per bench slot in four stages, from the
end of the slot to its start: serve (sigma'), decisions (release, purchases; decision slots
only), promotion (which warm lease serves), death. The argmin of every stage is stored per
slot (int8, int16 at decision slots: at most 2 + 2 / phi_b bytes per state and slot), and a
forward pass from the initial state (empty, empty, 0) recovers the plan. The cost of that
plan is recomputed from its leases and its serve decisions and must equal the DP value
(a self-check that raises RuntimeError otherwise).
"""
from __future__ import annotations

import resource
import time
from dataclasses import dataclass
from itertools import product
from typing import Optional

import numpy as np

from .. import reclaim
from ..types import BenchGrid, Instance, PlannedLease, Schedule, SolveResult

COMPONENTS = ("lease_prepaid", "lease_rent", "loading", "routing", "fallback",
              "stranding_kv", "stranding_fl", "stranding_fb", "stranding_pi")
_TOL = 1e-12          # relative tolerance of the domain checks (on/off levels, equal routing costs)
_CHECK_TOL = 1e-9     # relative tolerance of the plan-cost self-check


class DomainError(ValueError):
    """The instance lies outside the domain of the single-site DP (§7.1)."""


# ---------------------------------------------------------------------------- helpers
def _ceil_div(a: int, b: int) -> int:
    return -(-int(a) // int(b))


def _bench(inst: Instance, grid: str) -> tuple[int, int, int]:
    """(Δ_b, φ_b = Δ_s / Δ_b, T_b) of the bench grid."""
    if grid not in ("slow", "fast"):
        raise ValueError(f"the DP supports the bench grids 'slow' and 'fast', not {grid!r}")
    db = inst.grid.bench_min(grid)
    return db, inst.grid.slow_min // db, inst.grid.T_bench(grid)


def _bench_demand(inst: Instance, grid: str) -> np.ndarray:
    """Demand of client 0 per bench slot: the mean over the fast slots of a bench slot."""
    d = np.asarray(inst.clients.demand[0], dtype=np.float64)
    if grid == "slow" and inst.grid.phi > 1:
        d = d.reshape(inst.grid.T_slow, inst.grid.phi).mean(axis=1)
    return d


def _usable_sites(inst: Instance) -> list[int]:
    """Sites l with delta_cl < q_j for the single client (the DP ignores the others)."""
    q = inst.llms[0].q_usd_per_h
    delta = inst.clients.delta_usd_per_h[0]
    return [l for l in range(inst.m) if delta[l] < q]


def _offered(inst: Instance, l: int) -> list[int]:
    return sorted(k for k in inst.sites[l].menu if np.isfinite(inst.price[l, k]))


def _rss_mb() -> float:
    """Current resident memory from /proc/self/statm."""
    try:
        with open("/proc/self/statm") as f:
            pages = int(f.read().split()[1])
        return pages * resource.getpagesize() / 2 ** 20
    except OSError:
        return float("nan")


def _peak_rss_mb() -> float:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0


# ---------------------------------------------------------------------------- domain
def _check_domain(inst: Instance, sched: Schedule, grid: str) -> tuple[list[tuple[int, str]], bool]:
    """Failed items of §7.1 as (item, reason), and whether the bench demand exceeds one
    replica load without kappa_infinite (which always raises)."""
    db, phi_b, _ = _bench(inst, grid)
    if len(sched.R) != inst.m:
        raise ValueError(f"schedule has {len(sched.R)} announcement sets for {inst.m} sites")
    if not sched.realized:
        raise ValueError("schedule is not realized (adaptive schedule before the run)")
    if inst.n != 1 or inst.J != 1:
        return [(1, f"item 1: the DP needs one client and one LLM (n={inst.n}, J={inst.J})")], False
    out: list[tuple[int, str]] = []
    usable = _usable_sites(inst)
    rev = [l for l in usable if any(not inst.contracts[k].protected for k in _offered(inst, l))]
    if len(rev) > 1:
        out.append((2, "item 2: more than one usable site offers revocable contracts ("
                    + ", ".join(inst.sites[l].id for l in rev) + ")"))
    if len(usable) > 1:
        dl = np.asarray(inst.clients.delta_usd_per_h[0, usable], dtype=np.float64)
        if float(np.ptp(dl)) > _TOL * max(1.0, float(np.max(np.abs(dl)))):
            out.append((2, "item 2: the usable sites have unequal routing costs"))
    d = _bench_demand(inst, grid)
    pos = d[d > 0]
    over_one = False
    if len(pos):
        hi, lo = float(pos.max()), float(pos.min())
        if hi - lo > _TOL * max(1.0, hi):
            out.append((3, "item 3: the bench demand is not on/off "
                        f"(positive values {lo:.6g} to {hi:.6g})"))
        if not inst.kappa_infinite and hi > 1.0 + _TOL:
            over_one = True
            out.append((3, f"item 3: the bench demand reaches {hi:.6g} replica loads (above one)"))
    mu_kv = float(inst.stranding.mu_kv_usd[0])
    if mu_kv != 0.0:
        out.append((4, f"item 4: mu_kv = {mu_kv:.6g} USD; the DP does not charge moves"))
    lam_ms = inst.lam_ms()
    lam_max = max((_ceil_div(lam_ms[0, l], 60000 * db) for l in usable), default=0)
    n_q = _ceil_div(lam_max, phi_b)
    need = (n_q + 2) * inst.llms[0].g
    small = [inst.sites[l].id for l in usable
             if np.isfinite(inst.sites[l].capacity_gpus) and inst.sites[l].capacity_gpus < need]
    if small:
        out.append((5, f"item 5: capacity below (N_Q + 2) g = {need} GPUs at " + ", ".join(small)))
    return out, over_one


def dp_domain(inst: Instance, sched: Schedule, grid: BenchGrid = "slow") -> list[str]:
    """Reasons the instance is outside the exact domain of §7.1 ([] = inside)."""
    return [msg for _, msg in _check_domain(inst, sched, grid)[0]]


# ---------------------------------------------------------------------------- model
@dataclass
class _Opt:
    """Option o = (site, contract) on the bench grid (§7.3)."""
    site: int
    k: int
    prot: bool
    lam: int        # Λ_o: bench slots until the replica is warm
    P: int          # P_o = ceil(P_k / Δ_b): ages >= P_o are rent-bearing (rule T7)
    Y: int          # leases of age >= Y_o are "old" (Lemma D1)
    rent: float     # r_o = g a Δ_b / 60 per rent-bearing bench slot
    charge: float   # c_o = β + g a P_k / 60 at purchase
    delta: float    # routing cost of the site, USD per replica-load-hour
    base: int = 0   # p index of age Λ_o (the "old" entry if Y_o = Λ_o)


@dataclass
class _Lease:
    o: int
    s: int                     # start, bench slot (a decision slot)
    E: int                     # death, bench slot (T_b if never)
    rel: Optional[int] = None  # bench slot of release (a decision slot), None if held


class _DP:
    def __init__(self, inst: Instance, sched: Schedule, grid: str, refuse: bool):
        db, phi, tb = _bench(inst, grid)
        self.inst, self.grid = inst, grid
        self.db, self.phi, self.Tb, self.Ts = db, phi, tb, inst.grid.T_slow
        self.d = _bench_demand(inst, grid)
        self.dhat = np.minimum(np.concatenate(([0.0], self.d[:-1])), self.d)
        llm = inst.llms[0]
        self.g, self.q = llm.g, float(llm.q_usd_per_h)
        self.mu = float(inst.stranding.mu_fb_usd[0])
        delta = inst.clients.delta_usd_per_h[0]
        lam_ms = inst.lam_ms()
        R = [np.unique(np.asarray(r, dtype=np.int64)) for r in sched.R]

        # ---- options and the death table E[o, s] (rule T10; meaningful at decision slots)
        opts: list[_Opt] = []
        E, refused = [], []
        for l in _usable_sites(inst):
            lam = _ceil_div(lam_ms[0, l], 60000 * db)
            for k in _offered(inst, l):
                c = inst.contracts[k]
                a = float(inst.price[l, k])
                P = _ceil_div(c.prepaid_min, db)
                A = max(P, lam)
                Y = A if c.protected else max(A, _ceil_div(c.D_min(inst.grid.slow_min), db))
                opts.append(_Opt(l, k, c.protected, lam, P, Y, self.g * a * db / 60.0,
                                 float(inst.beta_usd[0, l]) + self.g * a * c.prepaid_min / 60.0,
                                 float(delta[l])))
                if c.protected:
                    E.append(np.full(tb, tb, dtype=np.int64))
                else:
                    e = [reclaim.death_bench(R[l], s, c, inst.grid, grid) for s in range(self.Ts)]
                    E.append(np.repeat(np.asarray(e, dtype=np.int64), phi))
                ref = np.zeros(self.Ts, dtype=bool)
                if refuse:
                    ref[R[l][(R[l] >= 0) & (R[l] < self.Ts)]] = True
                refused.append(ref)
        self.opts = opts
        n_o = len(opts)
        self.E = np.stack(E) if E else np.zeros((1, tb), dtype=np.int64)
        self.refused = np.stack(refused) if refused else np.zeros((0, self.Ts), dtype=bool)
        self.o_lam = np.array([o.lam for o in opts], dtype=np.int64)
        self.o_charge = np.array([o.charge for o in opts], dtype=np.float64)

        # ---- p axis
        n_p = 1
        for o in opts:
            o.base = n_p
            n_p += o.Y - o.lam + 1
        p_opt = np.full(n_p, -1, dtype=np.int64)
        p_age = np.zeros(n_p, dtype=np.int64)
        p_old = np.zeros(n_p, dtype=bool)
        adv = np.arange(n_p, dtype=np.int64)
        for i, o in enumerate(opts):
            for a in range(o.lam, o.Y):
                x = o.base + a - o.lam
                p_opt[x], p_age[x], adv[x] = i, a, x + 1   # x + 1 is age a + 1 or "old"
            x = o.base + o.Y - o.lam
            p_opt[x], p_old[x] = i, True
        has = p_opt >= 0
        oc = np.maximum(p_opt, 0)

        def per_p(values, dtype):
            """Option attribute per p entry (0 for the empty entry)."""
            v = np.array(values or [0], dtype=dtype)
            return np.where(has, v[oc], 0).astype(dtype)

        self.n_p, self.p_opt, self.p_optc, self.adv = n_p, p_opt, oc, adv
        self.p_age, self.p_old = p_age, p_old
        self.p_has = has
        self.p_prot = per_p([o.prot for o in opts], bool)
        self.p_P = per_p([o.P for o in opts], np.int64)
        self.p_Y = per_p([o.Y for o in opts], np.int64)
        self.p_rate = per_p([o.rent for o in opts], np.float64)
        self.p_delta = per_p([o.delta for o in opts], np.float64)
        self.p_rent = np.where(has & (p_old | (p_age >= self.p_P)), self.p_rate, 0.0)

        # ---- Q axis: positions (site, i) with a mixed-radix code
        self.qsites = sorted({o.site for o in opts if o.lam > 0})
        self.site_opts = {l: [i for i, o in enumerate(opts) if o.site == l]
                          for l in {o.site for o in opts}}
        self.site_lam = {o.site: o.lam for o in opts}
        pos_of, radix = [], []
        for l in self.qsites:
            n_pos = _ceil_div(self.site_lam[l], phi)
            pos_of.append(list(range(len(radix), len(radix) + n_pos)))
            radix += [1 + len(self.site_opts[l])] * n_pos
        self.pos_of = pos_of
        radix = np.array(radix, dtype=np.int64)
        w = np.concatenate(([1], np.cumprod(radix)[:-1])).astype(np.int64)[:len(radix)]
        n_q = int(np.prod(radix)) if len(radix) else 1
        self.n_q, self.w = n_q, w
        self.digits = (np.arange(n_q, dtype=np.int64)[:, None] // w[None, :]) % radix[None, :]
        # digit -> option index, and digit -> p index of the promoted lease, per Q site
        self.dig_opt = [np.array([-1] + self.site_opts[l], dtype=np.int64) for l in self.qsites]
        self.dig_newp = [np.array([0] + [opts[i].base for i in self.site_opts[l]], dtype=np.int64)
                         for l in self.qsites]

        # ---- per phase ph = t mod φ_b: warming positions, Q after promotion, loading rent
        self.warm, self.Qr, self.rentQ = [], [], []
        ar = np.arange(n_q, dtype=np.int64)
        for ph in range(phi):
            off = ph if ph > 0 else phi       # position i holds the purchase of t - off - i φ_b
            wl = []
            for qi, l in enumerate(self.qsites):
                lam = self.site_lam[l]
                if lam >= off and (lam - off) % phi == 0:
                    wl.append((qi, pos_of[qi][(lam - off) // phi]))
            self.warm.append(wl)
            self.Qr.append(ar - sum((self.digits[:, j] * w[j] for _, j in wl),
                                    np.zeros(n_q, np.int64)))
            rq = np.zeros(n_q)
            for qi, l in enumerate(self.qsites):
                for i, j in enumerate(pos_of[qi]):
                    age = ph + i * phi        # age in slot t of a lease at position i of Q_{t+1}
                    lut = np.array([0.0] + [opts[o].rent if age >= opts[o].P else 0.0
                                            for o in self.site_opts[l]])
                    rq += lut[self.digits[:, j]]
            self.rentQ.append(rq)

        # ---- decisions: purchase combinations and the Q code after the shift
        combos = list(product(*[range(1 + len(self.site_opts[l])) for l in self.qsites]))
        shift = np.zeros(n_q, dtype=np.int64)
        for qi in range(len(self.qsites)):
            ps = pos_of[qi]
            for i in range(len(ps) - 1):
                shift += self.digits[:, ps[i]] * w[ps[i + 1]]
        self.Qn = [shift + sum(int(cb[qi]) * int(w[ps[0]]) for qi, ps in enumerate(pos_of))
                   for cb in combos]
        zopts = [i for i, o in enumerate(opts) if o.lam == 0]
        self.cands = []                       # (combo, Λ=0 option or -1, release bit)
        for bi in range(len(combos)):
            self.cands += [(bi, -1, 0), (bi, -1, 1)] + [(bi, z, 0) for z in zopts]
        self.cand_opts = []
        M = np.zeros((len(self.cands), n_o))
        for c, (bi, z, _) in enumerate(self.cands):
            ol = [int(self.dig_opt[qi][dg]) for qi, dg in enumerate(combos[bi]) if dg > 0]
            ol += [z] if z >= 0 else []
            self.cand_opts.append(ol)
            M[c, ol] = 1.0
        self.combos, self.M = combos, M
        self.n_states = n_p * n_q * 2

    # ------------------------------------------------------------------ per-slot pieces
    def _p_death(self, t: int) -> np.ndarray:
        """Death bench slot of the lease behind every p entry, for p alive in slot t - 1."""
        s = np.where(self.p_old, self.phi * ((t - self.p_Y) // self.phi), t - self.p_age)
        return self.E[self.p_optc, np.clip(s, 0, self.Tb - 1)]

    def _retire_p(self, t: int, tplus: int, Ep: np.ndarray) -> np.ndarray:
        """Rent of the serving lease over [t, t+) if it retires at the non-decision slot t."""
        first = np.where(self.p_old, t, np.maximum(t, t - self.p_age + self.p_P))
        r = self.p_rate * np.maximum(0, np.minimum(tplus, Ep) - first)
        return np.where(self.p_has, r, 0.0)

    def _retire_w(self, t: int, tplus: int, qi: int) -> np.ndarray:
        """Per digit: rent over [t, t+) of the lease turning warm at t if it retires."""
        s = t - self.site_lam[self.qsites[qi]]
        out = [0.0]
        for o in self.site_opts[self.qsites[qi]]:
            op = self.opts[o]
            e = int(self.E[o, max(s, 0)])
            out.append(op.rent * max(0, min(tplus, e) - max(t, s + op.P)))
        return np.array(out)

    def _serve(self, t: int, ph: int, V: np.ndarray):
        """G[p4, Qn, sigma]: value after the decisions of slot t; argmin sigma' (bool) or None."""
        vn = V[self.adv]
        dt = float(self.d[t])
        fb = self.q * dt * self.db / 60.0
        g0 = fb + self.mu * self.dhat[t] * np.array([0.0, 1.0])[None, None, :] + vn[:, :, 0:1]
        if dt > 0 and self.n_p > 1:
            g1 = (self.p_delta * dt * self.db / 60.0)[:, None, None] + vn[:, :, 1:2]
            g1 = np.broadcast_to(g1, g0.shape).copy()
            g1[0] = np.inf                    # no warm lease, no service
            arg = g1 < g0
            G = np.where(arg, g1, g0)
        else:
            arg = None
            G = g0
        return G + self.rentQ[ph][None, :, None] + self.p_rent[:, None, None], arg

    def _allowed(self, t: int) -> np.ndarray:
        """Options that may be bought at decision slot t (§7.4 step 3)."""
        return (self.E[:, t] > t + self.o_lam) & ~self.refused[:, t // self.phi]

    def _decide(self, t: int, G: np.ndarray):
        """B[p2, Qr, sigma] at a decision slot and the argmin candidate code."""
        bad = (self.M @ (~self._allowed(t)).astype(np.float64)) > 0
        cost = self.M @ self.o_charge
        vals, codes, cache = [], [], {}
        for c, (bi, z, rel) in enumerate(self.cands):
            if bad[c]:
                continue
            if bi not in cache:
                cache[bi] = G[:, self.Qn[bi], :]
            gq = cache[bi]
            v = gq[self.opts[z].base][None] if z >= 0 else (gq[0:1] if rel else gq)
            vals.append(np.broadcast_to(cost[c] + v, G.shape))
            codes.append(c)
        st = np.stack(vals)
        a = st.argmin(axis=0)
        return np.take_along_axis(st, a[None], axis=0)[0], np.asarray(codes, dtype=np.int16)[a]

    def _promote(self, t: int, ph: int, Nx: np.ndarray, Ep: np.ndarray):
        """C[p1, Q, sigma]: choice of the serving lease among p1 and the leases turning warm."""
        qr = self.Qr[ph]
        wl = self.warm[ph]
        wd = [self.digits[:, j] for _, j in wl]
        any_w = np.zeros(self.n_q, dtype=bool)
        for x in wd:
            any_w |= x > 0
        if ph == 0:                           # decision slot: retiring leases are released at t
            ret_p = np.zeros(self.n_p)
            ret_w = [np.zeros(self.n_q) for _ in wl]
        else:
            tplus = min((t // self.phi + 1) * self.phi, self.Tb)
            ret_p = self._retire_p(t, tplus, Ep)
            ret_w = [self._retire_w(t, tplus, qi)[x] for (qi, _), x in zip(wl, wd)]
        tot = sum(ret_w, np.zeros(self.n_q))
        keep = Nx[:, qr, :] + tot[None, :, None]
        keep[0, any_w, :] = np.inf            # no serving lease: one of the warm ones serves
        cands = [keep]
        for (qi, _), x, rw in zip(wl, wd, ret_w):
            v = Nx[self.dig_newp[qi][x], qr, :]
            cnd = v[None] + ret_p[:, None, None] + (tot - rw)[None, :, None]
            cnd[:, x == 0, :] = np.inf
            cands.append(cnd)
        st = np.stack(cands)
        a = st.argmin(axis=0)
        return np.take_along_axis(st, a[None], axis=0)[0], a.astype(np.int8)

    # ------------------------------------------------------------------ backward recurrence
    def backward(self, store: bool) -> float:
        n_p, n_q, phi, tb = self.n_p, self.n_q, self.phi, self.Tb
        shape = (n_p, n_q, 2)
        warm_t = [t for t in range(tb) if self.warm[t % phi]]
        self.rowC = np.full(tb, -1, dtype=np.int64)
        self.rowC[warm_t] = np.arange(len(warm_t))
        if store:
            self.argG = np.zeros((tb,) + shape, dtype=np.int8)
            self.argB = np.zeros((self.Ts,) + shape, dtype=np.int16)
            self.argC = np.zeros((len(warm_t),) + shape, dtype=np.int8)
        self.rss_after_build_mb = _rss_mb()
        V = np.zeros(shape)
        for t in range(tb - 1, -1, -1):
            ph = t % phi
            G, aG = self._serve(t, ph, V)
            if store and aG is not None:
                self.argG[t] = aG
            if ph == 0:
                Nx, aB = self._decide(t, G)
                if store:
                    self.argB[t // phi] = aB
            else:
                Nx = G
            Ep = self._p_death(t)
            if self.warm[ph]:
                Nx, aC = self._promote(t, ph, Nx, Ep)
                if store:
                    self.argC[self.rowC[t]] = aC
            dead = self.p_has & ~self.p_prot & (Ep <= t)
            V = Nx[np.where(dead, 0, np.arange(n_p))]
        return float(V[0, 0, 0])

    # ------------------------------------------------------------------ forward pass
    def forward(self):
        """Follow the stored argmins from (empty, empty, 0); returns leases and serve bits."""
        phi, tb = self.phi, self.Tb
        leases: list[_Lease] = []
        qpos = np.full(self.digits.shape[1], -1, dtype=np.int64)   # lease id per Q position
        p, qx, sig, cur = 0, 0, 0, None
        serve = np.zeros(tb, dtype=np.int8)
        server = np.full(tb, -1, dtype=np.int64)
        for t in range(tb):
            ph = t % phi
            dec = ph == 0
            tplus = min((t // phi + 1) * phi, tb)
            # 1. death
            Ep = self._p_death(t)
            if p != 0:
                if cur is None:
                    raise RuntimeError(f"DP state has a serving lease, the plan none, at t={t}")
                L = leases[cur]
                dead = (not self.p_prot[p]) and Ep[p] <= t
                if (L.E <= t) != dead:
                    raise RuntimeError(f"DP death of the serving lease is wrong at t={t}")
                if dead:
                    p, cur = 0, None
            # 2. promotion
            if self.warm[ph]:
                wl = [(qi, j) for qi, j in self.warm[ph] if self.digits[qx, j] > 0]
                if wl:
                    c = int(self.argC[self.rowC[t], p, qx, sig])
                    members = [(qi, j, int(qpos[j])) for qi, j in wl]
                    rel = t if dec else (tplus if tplus < tb else None)
                    if c == 0:
                        chosen = None
                    else:
                        qi_c, j_c = self.warm[ph][c - 1]
                        chosen = next(m for m in members if m[1] == j_c)
                        if cur is not None:
                            leases[cur].rel = rel
                        cur = chosen[2]
                        p = int(self.dig_newp[qi_c][self.digits[qx, j_c]])
                    for m in members:
                        if m is not chosen:
                            leases[m[2]].rel = rel
                for _, j in self.warm[ph]:
                    qpos[j] = -1
                qx = int(self.Qr[ph][qx])
            # 3. decisions
            if dec:
                code = int(self.argB[t // phi, p, qx, sig])
                bi, z, rel = self.cands[code]
                if (rel or z >= 0) and cur is not None:
                    leases[cur].rel = t
                    p, cur = 0, None
                new = {}
                for o in self.cand_opts[code]:
                    leases.append(_Lease(o, t, int(self.E[o, t])))
                    new[o] = len(leases) - 1
                for qi, ps in enumerate(self.pos_of):
                    if qpos[ps[-1]] >= 0:
                        raise RuntimeError(f"loading lease dropped from Q at t={t}")
                    qpos[ps[1:]] = qpos[ps[:-1]].copy()
                    dg = self.combos[bi][qi]
                    qpos[ps[0]] = new[int(self.dig_opt[qi][dg])] if dg > 0 else -1
                qx = int(self.Qn[bi][qx])
                if z >= 0:
                    p, cur = self.opts[z].base, new[z]
            # 4. serve
            s1 = 0
            if p != 0 and self.d[t] > 0:
                s1 = int(self.argG[t, p, qx, sig])
            if s1:
                L = leases[cur]
                if not (L.s + self.opts[L.o].lam <= t < L.E):
                    raise RuntimeError(f"serving lease not warm and alive at t={t}")
            serve[t], server[t] = s1, (cur if cur is not None else -1)
            # 5. next state
            p, sig = int(self.adv[p]), s1
        return leases, serve, server

    # ------------------------------------------------------------------ plan cost and plan
    def plan_cost(self, leases: list[_Lease], serve: np.ndarray, server: np.ndarray) -> dict:
        """Ledger split of §5.6 for the plan, recomputed from its leases and serve decisions."""
        comp = dict.fromkeys(COMPONENTS, 0.0)
        a_db = self.db / 60.0
        for L in leases:
            o = self.opts[L.o]
            end = min(L.E, self.Tb if L.rel is None else L.rel)
            comp["lease_prepaid"] += o.charge - float(self.inst.beta_usd[0, o.site])
            comp["loading"] += float(self.inst.beta_usd[0, o.site])
            comp["lease_rent"] += o.rent * max(0, end - L.s - o.P)
        prev = 0
        for t in range(self.Tb):
            dt = float(self.d[t])
            if serve[t]:
                comp["routing"] += self.opts[leases[server[t]].o].delta * dt * a_db
            else:
                comp["fallback"] += self.q * dt * a_db
            comp["stranding_fb"] += self.mu * max(0.0, self.dhat[t] * prev - dt * serve[t])
            prev = int(serve[t])
        comp["lease"] = comp["lease_prepaid"] + comp["lease_rent"]
        comp["stranding"] = (comp["stranding_kv"] + comp["stranding_fl"]
                             + comp["stranding_fb"] + comp["stranding_pi"])
        comp["total"] = sum(comp[c] for c in COMPONENTS)
        return comp

    def plan(self, leases: list[_Lease], serve: np.ndarray) -> list[PlannedLease]:
        """PlannedLease per lease (§7.5): release slots, admission_off intervals in fast slots."""
        phi, tb = self.phi, self.Tb
        fac = self.db // self.inst.grid.fast_min
        off = (serve == 0) & (self.d > 0)
        out = []
        for L in leases:
            o = self.opts[L.o]
            rel = L.rel if (L.rel is not None and L.rel < min(L.E, tb)) else None
            end = min(L.E, tb if rel is None else rel)
            iv, a = [], None
            for t in range(L.s + o.lam, end + 1):
                on = t < end and off[t]
                if on and a is None:
                    a = t
                elif not on and a is not None:
                    iv.append((a * fac, t * fac))
                    a = None
            out.append(PlannedLease(site=o.site, contract=o.k, llm=0, start_slot=L.s // phi,
                                    release_slot=None if rel is None else rel // phi, n=1,
                                    admission_off=tuple(iv)))
        return out


# ---------------------------------------------------------------------------- solver
def solve_dp(inst: Instance, sched: Schedule, *, grid: BenchGrid = "slow",
             refuse_unavailable: bool = False, strict: bool = True,
             return_plan: bool = True) -> SolveResult:
    """OPT(sigma, omega) of a single-site instance by the DP of §7.

    strict=True raises DomainError outside the domain of §7.1. strict=False still solves when
    the only failed items are 2 and 3 and the bench demand never exceeds one replica load (or
    kappa_infinite); the value is then an upper bound on OPT_P1 and the reasons go to
    status_msg. Items 1, 4 and 5, and demand above one replica load, always raise.
    refuse_unavailable: no purchase at site l in a slow slot of sched.R[l] (§7.4 step 3).
    return_plan=False skips the argmin storage and the forward pass (value only; components
    then hold only 'total').
    """
    t0 = time.perf_counter()
    items, over_one = _check_domain(inst, sched, grid)
    failed = {i for i, _ in items}
    if items and (strict or over_one or not failed <= {2, 3}):
        raise DomainError("; ".join(msg for _, msg in items))
    status_msg = "optimal" if not items else (
        "upper bound on OPT_P1 (outside the DP domain): " + "; ".join(msg for _, msg in items))
    dp = _DP(inst, sched, grid, refuse_unavailable)
    build_s = time.perf_counter() - t0
    t1 = time.perf_counter()
    value = dp.backward(store=return_plan)
    plan, comp = None, {"total": value}
    if return_plan:
        leases, serve, server = dp.forward()
        comp = dp.plan_cost(leases, serve, server)
        if abs(comp["total"] - value) > _CHECK_TOL * max(1.0, abs(value)):
            raise RuntimeError(f"DP plan costs {comp['total']!r}, DP value {value!r}")
        plan = dp.plan(leases, serve)
    solve_s = time.perf_counter() - t1
    choice_bytes = sum(getattr(dp, a).nbytes for a in ("argG", "argB", "argC") if hasattr(dp, a))
    size = {"n_states": dp.n_states, "n_p": dp.n_p, "n_q": dp.n_q, "T_b": dp.Tb,
            "n_options": len(dp.opts), "N_Q": max((len(p) for p in dp.pos_of), default=0),
            "choice_bytes": int(choice_bytes), "rss_after_build_mb": dp.rss_after_build_mb}
    return SolveResult(method="dp", benchmark="eager" if sched.mode == "eager" else "omega",
                       grid=grid, status=0, status_msg=status_msg, objective=value,
                       dual_bound=value, gap=0.0, plan=plan, components=comp, size=size,
                       build_s=build_s, solve_s=solve_s, peak_rss_mb=_peak_rss_mb())
