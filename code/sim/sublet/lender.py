"""Lender model (design/sim_spec.md §3.5, §6).

The lender is the environment. It owns one announcement set R_l per site (sorted unique int64
slow slots); a lease follows the reclaim rule T5 with the R of its site (sublet.reclaim), so one
announcement hits every lease on the site that is past its guaranteed period and not yet
announced. Protected contracts are never announced and protected sites keep R = {} in every mode.

Schedule modes (§6.6): 'trace' (layer sets from the lendable slack, synthetic R_explicit),
'eager' (every slot), 'adaptive' (built online from the platform's leases, as the lender of
pd.real_cost_renew(adversary=True)), 'safe_site' and 'iid_step' (the O1 constructions of
c3/o1/fam.py, same RNG calls), 'correlated' (trace sets plus group shocks). The lender also
checks purchases (capacity and the 'refuse' option, §6.4) and buffer violations (§6.5).

Nothing in this module reaches a policy directly: the engine passes notices, refusals and,
under information model I2 only, the per-site announcement bits (§6.7).
"""
from __future__ import annotations

import math
from typing import Optional

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view

from . import reclaim
from .types import Instance, LeaseView, LenderModel, Notice, Schedule

SCHEDULES = ("trace", "eager", "adaptive", "safe_site", "iid_step", "correlated")
# keys allowed in LenderModel.params per schedule (§4.2); a missing key or None means "resolve"
PARAM_KEYS = {
    "trace": (), "eager": (), "adaptive": (),
    "safe_site": ("D_slots", "k", "Phi"),
    "iid_step": ("D_slots", "p", "U"),
    "correlated": ("p_sh", "groups", "delay_slots_max"),
}
CORRELATED_GROUPS = (None, "all", "none", "region")   # params.groups of 'correlated' ('region': MS7 C54)
REFUSE_SCHEDULES = ("trace", "correlated")      # where t in R_l means "band unavailable" (§6.4)
VIOLATION_SCHEDULES = ("trace", "correlated")   # where the buffer check applies (§5.1 step 2)
SLACK_SLOT_MIN = 5                              # resolution of the lender slack series (calib, §6.1)


def _config_error(msg: str) -> Exception:
    # config.py (U1) is imported here rather than at module level, so that importing lender.py
    # does not depend on config.py and no import cycle can arise.
    from .config import ConfigError
    return ConfigError(msg)


# ---------------------------------------------------------------- instance helpers
def _revocable_sites(inst: Instance) -> list[int]:
    """Indices of the sites that can be announced (kind 'layer' or 'synthetic'), in site order."""
    return [i for i, s in enumerate(inst.sites) if s.kind != "protected"]


def _site_lender(inst: Instance) -> np.ndarray:
    """(m,) index into inst.lenders of each site's lender (from LenderTrace.site_index, else by
    lender id); -1 if the site has no LenderTrace."""
    own = np.full(inst.m, -1, dtype=np.int64)
    for li, lt in enumerate(inst.lenders):
        for i in lt.site_index:
            own[i] = li
    by_id = {lt.lender: li for li, lt in enumerate(inst.lenders)}
    for i, s in enumerate(inst.sites):
        if own[i] < 0:
            own[i] = by_id.get(s.lender, -1)
    return own


def _layer_lo(site) -> int:
    """local_layer_lo used to order and nest sites; a synthetic site is one band, the lowest (1)."""
    return 1 if site.local_layer_lo is None else int(site.local_layer_lo)


def _runs(R: np.ndarray) -> list[tuple[int, int]]:
    """(onset, length) of the maximal runs of consecutive slots in the sorted set R, in time order."""
    if len(R) == 0:
        return []
    brk = np.flatnonzero(np.diff(R) != 1) + 1
    first = np.r_[0, brk]
    last = np.r_[brk, len(R)]
    return [(int(R[a]), int(b - a)) for a, b in zip(first, last)]


def _family_D(inst: Instance) -> int:
    """D_k in slow slots of the revocable contracts, which must all agree (§4.2, safe_site/iid_step)."""
    slow = inst.grid.slow_min
    rev = [c for c in inst.contracts if not c.protected]
    if not rev:
        raise _config_error("D_slots is null and the instance has no revocable contract")
    bad = [c.id for c in rev if c.H_min % slow != 0]
    if bad:
        raise _config_error(f"D_slots is null and H_min of {bad} is not a multiple of "
                            f"slow_min = {slow}")
    Ds = sorted({c.tau_slots + c.H_min // slow for c in rev})
    if len(Ds) > 1:
        raise _config_error(f"D_slots is null and the revocable contracts differ in D: {Ds} slots")
    return Ds[0]


def _int_param(name: str, v, lo: int) -> int:
    if isinstance(v, bool) or not isinstance(v, (int, np.integer)) or v < lo:
        raise _config_error(f"lender_model.params.{name} must be an integer >= {lo}, got {v!r}")
    return int(v)


def _prob_param(name: str, v) -> float:
    if isinstance(v, bool) or not isinstance(v, (int, float, np.floating, np.integer)) \
            or not 0.0 <= float(v) <= 1.0:
        raise _config_error(f"lender_model.params.{name} must be a probability, got {v!r}")
    return float(v)


def resolve_params(inst: Instance, model: LenderModel) -> dict:
    """Validate `model` against the built instance and resolve the null parameters of §4.2.

    Raises ConfigError for an unknown schedule, information model or option, for 'refuse' with a
    schedule other than 'trace' or 'correlated', for params keys of another schedule, for safe_site
    with fewer than 2 revocable sites, and for safe_site / iid_step with D_slots null when the
    revocable contracts differ in D_k or an H_k is not a multiple of slow_min."""
    if model.schedule not in SCHEDULES:
        raise _config_error(f"unknown lender schedule {model.schedule!r}")
    if model.information not in ("I1", "I2"):
        raise _config_error(f"unknown information model {model.information!r}")
    if model.on_unavailable not in ("sell", "refuse"):
        raise _config_error(f"unknown on_unavailable {model.on_unavailable!r}")
    if model.violations not in ("absorb", "reclaim"):
        raise _config_error(f"unknown violations option {model.violations!r}")
    if model.on_unavailable == "refuse" and model.schedule not in REFUSE_SCHEDULES:
        raise _config_error(f"on_unavailable 'refuse' needs schedule 'trace' or 'correlated', "
                            f"not {model.schedule!r}")
    params = dict(model.params or {})
    extra = sorted(set(params) - set(PARAM_KEYS[model.schedule]))
    if extra:
        raise _config_error(f"lender_model.params {extra} do not belong to schedule {model.schedule!r}")
    T = inst.grid.T_slow
    m_r = len(_revocable_sites(inst))
    out: dict = {}
    if model.schedule == "safe_site":
        if m_r < 2:
            raise _config_error(f"safe_site needs at least 2 revocable sites, the instance has {m_r}")
        D = params.get("D_slots")
        D = _family_D(inst) if D is None else _int_param("D_slots", D, 1)
        k = params.get("k")
        k = max(2, m_r) if k is None else _int_param("k", k, 1)
        Phi = params.get("Phi")
        Phi = max(1, T // (k * D)) if Phi is None else _int_param("Phi", Phi, 1)
        out = {"D_slots": D, "k": k, "Phi": Phi}
    elif model.schedule == "iid_step":
        D = params.get("D_slots")
        D = _family_D(inst) if D is None else _int_param("D_slots", D, 1)
        p = params.get("p")
        p = 0.5 if p is None else _prob_param("p", p)
        U = params.get("U")
        U = T // D if U is None else _int_param("U", U, 0)
        out = {"D_slots": D, "p": p, "U": U}
    elif model.schedule == "correlated":
        if params.get("p_sh") is None:
            raise _config_error("schedule 'correlated' needs lender_model.params.p_sh")
        groups = params.get("groups")
        if groups not in CORRELATED_GROUPS:
            raise _config_error(f"lender_model.params.groups must be null, 'all', 'none' or 'region', "
                                f"got {groups!r}")
        dmax = params.get("delay_slots_max")
        dmax = math.ceil(5 / inst.grid.slow_min) if dmax is None \
            else _int_param("delay_slots_max", dmax, 0)
        out = {"p_sh": _prob_param("p_sh", params["p_sh"]), "groups": groups,
               "delay_slots_max": dmax}
    return out


# ---------------------------------------------------------------- announcement sets
def _base_R(inst: Instance, own: np.ndarray, i: int) -> np.ndarray:
    """The 'trace' set of site i (§6.2-§6.3): layer sites from the lendable slack, synthetic sites
    R_explicit, protected sites empty."""
    site = inst.sites[i]
    T = inst.grid.T_slow
    if site.kind == "protected":
        return np.zeros(0, dtype=np.int64)
    if site.kind == "synthetic":
        if site.R_explicit is None:
            return np.zeros(0, dtype=np.int64)
        R = np.asarray(site.R_explicit, dtype=np.int64)
        return np.unique(R[(R >= 0) & (R < T)])
    if site.kind != "layer":
        raise ValueError(f"site {site.id}: unknown kind {site.kind!r}")
    if own[i] < 0 or inst.lenders[own[i]].S_lend is None:
        raise ValueError(f"layer site {site.id} has no lendable slack series")
    lt = inst.lenders[own[i]]
    if site.layer_lo is None or site.layer_hi is None:
        raise ValueError(f"layer site {site.id} has no layer indices")
    S_lend = np.asarray(lt.S_lend, dtype=np.float64)
    if len(S_lend) != T:
        raise ValueError(f"layer site {site.id}: S_lend has {len(S_lend)} slots, horizon {T}")
    # The merged layers have identical sets over the horizon (§6.2); the top one is used and the
    # bottom one checked, so that a wrong merge is caught here.
    R = reclaim.layer_R(S_lend, site.layer_hi * lt.layer_gpus)
    if site.layer_lo != site.layer_hi and \
            not np.array_equal(R, reclaim.layer_R(S_lend, site.layer_lo * lt.layer_gpus)):
        raise ValueError(f"layer site {site.id} merges layers with different announcement sets")
    return R


def _safe_site(inst: Instance, params: dict, rng: np.random.Generator) -> list[np.ndarray]:
    """O1-A phases (fam.safe_site_schedule, same RNG calls), truncated to [0, T_s)."""
    T, rev = inst.grid.T_slow, _revocable_sites(inst)
    m_r, P, Phi = len(rev), params["k"] * params["D_slots"], params["Phi"]
    S = [int(rng.integers(m_r))]
    for _ in range(1, Phi):
        cand = [l for l in range(m_r) if l != S[-1]]
        S.append(int(cand[rng.integers(len(cand))]))
    R = [np.zeros(0, dtype=np.int64) for _ in inst.sites]
    for l, i in enumerate(rev):
        slots = [np.arange(ph * P, (ph + 1) * P, dtype=np.int64) for ph, s in enumerate(S) if s != l]
        r = np.concatenate(slots) if slots else np.zeros(0, dtype=np.int64)
        R[i] = r[r < T]
    return R


def _iid_step(inst: Instance, params: dict, rng: np.random.Generator) -> list[np.ndarray]:
    """O1-C steps (fam.iid_step_schedule, same RNG calls), truncated to [0, T_s)."""
    T, rev = inst.grid.T_slow, _revocable_sites(inst)
    D, p = params["D_slots"], params["p"]
    hits: list[list[int]] = [[] for _ in rev]
    for u in range(1, params["U"]):
        for l in range(len(rev)):
            if rng.random() < p:
                hits[l].append(u * D)
    R = [np.zeros(0, dtype=np.int64) for _ in inst.sites]
    for l, i in enumerate(rev):
        r = np.array(hits[l], dtype=np.int64)
        R[i] = r[r < T]
    return R


def _correlated(inst: Instance, base: list[np.ndarray], own: np.ndarray, params: dict,
                rng: np.random.Generator) -> list[np.ndarray]:
    """Trace sets plus group shocks (§6.6, S11), computed from the base sets only (no cascades).

    One shock draw per (source lender, onset, target lender) (§10 S11). The members
    of a group are the lenders with at least one revocable site (a lender without sites can receive
    nothing); the group is the lenders' Site.group, unless params.groups is 'all' (one group), 'none'
    (every lender its own group) or 'region' (the lenders of one region, by the Site.region of the lender's
    sites; MS7 C54, the regional stress L-co-reg of design/ms7/feasibility/baselines.md §2 item 6).
    Normative RNG order: for each member l in lender index order that has
    another member in its group, let U_l be the set of slots that are a run onset (t in R_b, t - 1 not
    in R_b) of the base set R_b of at least one site b of l; for each t in U_l in increasing order and
    each other member l' of the group in index order: one rng.random() < p_sh and, on success, one delay
    delta = rng.integers(0, delay_slots_max + 1), shared by this (l, t, l'). Then every site b of l
    with a run onset at t, of run length L_b, adds {t + delta, ..., t + delta + L_b - 1}, truncated to
    [0, T_slow), to R of every site of l' whose local_layer_lo is at least that of b (nesting is
    preserved). Protected sites stay empty.

    Merge consequences (merge_identical_layers, §10 S32): merged layers share their base sets, so U_l,
    and with it the number and order of the draws, does not depend on the merge setting, and each
    (onset, target lender) is shocked with probability p_sh in both settings (the per-site draw that
    this rule replaced drew k times for an onset shared by k layer sites, a probability of
    1 - (1 - p_sh)^k). What can still differ is the target side: a merged target site takes the shock
    of a source site b only if its lowest layer is at or above b's local_layer_lo, while with one site
    per layer each of its layers at or above b's takes it. The realized per-layer sets therefore agree
    across merge settings when every merged site of the target lenders is a single layer, and more
    generally when, in the merged setting, no target site with local layers lo, ..., hi has a source
    site (a site with a nonempty base set of another member of its group) whose local_layer_lo lies in
    lo + 1, ..., hi."""
    T = inst.grid.T_slow
    p_sh, dmax, mode = params["p_sh"], params["delay_slots_max"], params["groups"]
    members = []   # (lender index, group key, its revocable sites in increasing local_layer_lo)
    for li in range(len(inst.lenders)):
        sites = sorted((i for i in range(inst.m) if own[i] == li and inst.sites[i].kind != "protected"),
                       key=lambda i: (_layer_lo(inst.sites[i]), i))
        if not sites:
            continue
        if mode == "region":
            key = ("region", inst.sites[sites[0]].region)
        else:
            key = inst.sites[sites[0]].group if mode is None else ("all" if mode == "all" else li)
        members.append((li, key, sites))
    added: list[list[np.ndarray]] = [[] for _ in inst.sites]
    for li, key, sites in members:
        others = [x for x in members if x[1] == key and x[0] != li]
        if not others:
            continue
        runs_of = {b: dict(_runs(base[b])) for b in sites}         # onset -> run length, per site
        for t0 in sorted(set().union(*runs_of.values())):          # U_l in increasing order
            src = [(_layer_lo(inst.sites[b]), runs_of[b][t0]) for b in sites if t0 in runs_of[b]]
            for _, _, sites2 in others:
                if rng.random() < p_sh:
                    d = int(rng.integers(0, dmax + 1))
                    for lo_b, run in src:
                        shock = np.arange(t0 + d, min(T, t0 + d + run), dtype=np.int64)
                        for b2 in sites2:
                            if _layer_lo(inst.sites[b2]) >= lo_b:
                                added[b2].append(shock)
    return [np.union1d(base[i], np.concatenate(added[i])).astype(np.int64) if added[i] else base[i]
            for i in range(inst.m)]


def build_R(inst: Instance, model: LenderModel, rng: np.random.Generator) -> list[np.ndarray]:
    """The static announcement sets of §6.6 for every non-adaptive mode, one sorted unique int64
    array per site (used by Lender and by the benchmarks). The 'trace' sets of layer sites come
    from reclaim.layer_R on LenderTrace.S_lend; protected sites are empty in every mode. Only
    'safe_site', 'iid_step' and 'correlated' draw from `rng`."""
    params = resolve_params(inst, model)
    mode, T = model.schedule, inst.grid.T_slow
    if mode == "adaptive":
        raise ValueError("the 'adaptive' sets are built online; use Lender.realized() after the run")
    empty = np.zeros(0, dtype=np.int64)
    if mode == "eager":
        return [empty.copy() if s.kind == "protected" else np.arange(T, dtype=np.int64)
                for s in inst.sites]
    if mode == "safe_site":
        return _safe_site(inst, params, rng)
    if mode == "iid_step":
        return _iid_step(inst, params, rng)
    own = _site_lender(inst)
    base = [_base_R(inst, own, i) for i in range(inst.m)]
    if mode == "trace":
        return base
    return _correlated(inst, base, own, params, rng)


def owed_series(inst: Instance, li: int) -> np.ndarray:
    """(T_slow,) GPUs that trace lender `li` owes to its other borrowers at each slow slot (§6.5, S10).

    The v0 layers below the offered block are lent under the lender's offered contracts, so a v0
    level that becomes unavailable is announced then and is gone at the latest D^max later:
    owed(t) = g^lay * min(v0, floor(max_{t' in [t - h, t]} S_lend(t') / g^lay)), h = ceil(D^max / slow_min)
    slow slots, with S_lend(t') = (S_full - B)^+ at the aligned index (off + t' * slow_min // 5) mod N
    of §6.1, so the window reaches back before the horizon start."""
    lt = inst.lenders[li]
    T, slow = inst.grid.T_slow, inst.grid.slow_min
    if lt.S_full is None or lt.v0 == 0 or lt.layer_gpus <= 0:
        return np.zeros(T, dtype=np.int64)
    S_full = np.asarray(lt.S_full, dtype=np.float64)
    N = len(S_full)
    S_lend_full = np.maximum(S_full - float(lt.B_gpus), 0.0)
    h = -(-int(lt.D_max_lender_min) // slow)
    tt = np.arange(-h, T, dtype=np.int64)
    idx = (int(lt.offset_5min) + (tt * slow) // SLACK_SLOT_MIN) % N
    top = sliding_window_view(S_lend_full[idx], h + 1).max(axis=1)      # (T,): max over [t - h, t]
    g = int(lt.layer_gpus)
    return g * np.minimum(int(lt.v0), np.floor(top / g).astype(np.int64))


# ---------------------------------------------------------------- the lender
class Lender:
    """Announcement sets, notices, purchase checks and buffer violations of one run (§3.5, §6).

    Public attributes: `inst`, `model`, `params` (resolved schedule parameters) and
    `information` ('I1' or 'I2'). `begin_slot` must be called once per slow slot in order under
    'adaptive' (its sets grow online); the other modes have static sets fixed at construction."""

    def __init__(self, inst: Instance, model: LenderModel, rng: np.random.Generator):
        self.inst, self.model = inst, model
        self.params = resolve_params(inst, model)
        self.information = model.information
        m, T = inst.m, inst.grid.T_slow
        self._adaptive = model.schedule == "adaptive"
        self._revocable = np.array([s.kind != "protected" for s in inst.sites], dtype=bool)
        self._tau = [c.tau_slots for c in inst.contracts]   # None for protected contracts
        self._H = [c.H_min for c in inst.contracts]
        self._mask = np.zeros((m, T), dtype=bool)           # _mask[l, t] iff t in R_l
        if not self._adaptive:   # adaptive: every R_l starts empty
            for i, R in enumerate(build_R(inst, model, rng)):
                self._mask[i, R] = True
        self._last_t = -1
        own = _site_lender(inst)
        # trace lenders with sites take part in the buffer check (§6.5)
        self._checked = [li for li, lt in enumerate(inst.lenders)
                         if lt.S is not None and np.any(own == li)]
        self._sites_of = {inst.lenders[li].lender: set(np.flatnonzero(own == li).tolist())
                          for li in range(len(inst.lenders))}
        self._owed = {li: owed_series(inst, li) for li in self._checked}

    def _R(self) -> tuple[np.ndarray, ...]:
        return tuple(np.flatnonzero(row).astype(np.int64) for row in self._mask)

    def static_schedule(self) -> Optional[Schedule]:
        """The precomputed sets for every mode except 'adaptive' (None); protected sites empty."""
        if self._adaptive:
            return None
        return Schedule(self.model.schedule, self._R(), True)

    def begin_slot(self, t: int, leases: list[LeaseView]) -> tuple[np.ndarray, list[Notice]]:
        """Announcements of slow slot t (rule T9 step 1).

        `leases`: the platform's leases alive in fast slot t*phi. Under 'adaptive', t is first
        added to R_l of every site l at which one of them reaches start_slot + tau_k = t. Returns
        site_announced ((m,) bool, t in R_l, for every information model: the engine shows it to the
        policy only under I2) and one Notice for every unannounced revocable lease with
        start_slot + tau_k <= t at a site with t in R_l (death minute t*slow_min + H_k)."""
        T = self.inst.grid.T_slow
        if not 0 <= t < T:
            raise ValueError(f"slot {t} outside the horizon [0, {T})")
        if self._adaptive:
            if t != self._last_t + 1:
                raise ValueError(f"adaptive lender: begin_slot({t}) after slot {self._last_t}; "
                                 "every slot must be called once, in order")
            for lv in leases:
                tau = self._tau[lv.contract]
                if tau is not None and self._revocable[lv.site] and lv.start_slot + tau == t:
                    self._mask[lv.site, t] = True
        announced = self._mask[:, t].copy()
        notices = []
        for lv in leases:
            tau = self._tau[lv.contract]
            if tau is None or lv.announce_slot is not None:
                continue
            if lv.start_slot + tau <= t and announced[lv.site]:
                notices.append(Notice(lv.id, t, t * self.inst.grid.slow_min + self._H[lv.contract]))
        self._last_t = max(self._last_t, t)
        return announced, notices

    def purchase_ok(self, t: int, site: int, gpus: int, held_gpus: int) -> tuple[bool, str]:
        """Purchase check of §6.4: (False, 'unavailable') under on_unavailable = 'refuse' if t is in
        R_site; else (False, 'capacity') if held_gpus + gpus exceeds the site's capacity; else
        (True, ''). held_gpus: the platform's GPUs at the site in fast slot t*phi, minus those
        released and plus those bought earlier in the same action list."""
        if self.model.on_unavailable == "refuse" and self._mask[site, t]:
            return False, "unavailable"
        if held_gpus + gpus > self.inst.sites[site].capacity_gpus:
            return False, "capacity"
        return True, ""

    def owed(self, t: int) -> dict[str, int]:
        """GPUs owed to other borrowers at slow slot t (owed_series) per checked trace lender."""
        return {self.inst.lenders[li].lender: int(self._owed[li][t]) for li in self._checked}

    def violations(self, t: int, leased_gpus_by_lender: dict[str, int]) -> list[dict]:
        """Buffer violations at slow slot t (§6.5, S10): for each trace lender with sites, the
        requirement req = owed(t) (owed_series) + the platform's GPUs at its sites (missing lender ids
        count 0) against the physical slack S^h(t); a violation is req > S^h(t). Each entry has the
        deficit (req - S)^+ and the attributable deficit (req - S)^+ - (owed - S)^+, the part that would
        vanish if the platform held nothing there. Empty under schedules other than 'trace' and
        'correlated'."""
        if self.model.schedule not in VIOLATION_SCHEDULES:
            return []
        out = []
        for li in self._checked:
            lt = self.inst.lenders[li]
            owed = int(self._owed[li][t])
            req = owed + int(leased_gpus_by_lender.get(lt.lender, 0))
            slack = float(lt.S[t])
            if req > slack:
                deficit = req - slack
                out.append({"lender": lt.lender, "t": int(t), "required": req, "slack": slack,
                            "deficit": deficit, "owed": owed,
                            "deficit_attributable": deficit - max(0.0, owed - slack)})
        return out

    def violation_victims(self, t: int, leases: list[LeaseView], v: dict) -> list[int]:
        """'reclaim' variant of §6.5: ids of the platform's leases at v['lender']'s sites to end at
        minute t*slow_min, in LIFO order (highest layer_hi first; within a site the latest start
        first; ties by the higher lease id, i.e. the later purchase), until the GPUs ended cover
        v['deficit']. Returns fewer if all leases there together do not cover it."""
        sites = self._sites_of.get(v["lender"], set())
        cand = [lv for lv in leases if lv.site in sites]
        hi = [self.inst.sites[lv.site].layer_hi for lv in cand]
        order = sorted(range(len(cand)), key=lambda i: (-(hi[i] if hi[i] is not None else 0),
                                                        -cand[i].start_min, -cand[i].id))
        need, out = float(v["deficit"]), []
        for i in order:
            if need <= 0:
                break
            out.append(cand[i].id)
            need -= cand[i].gpus
        return out

    def realized(self) -> Schedule:
        """The announcement sets actually used (with the adaptive additions so far): the omega of
        OPT(sigma, omega). `realized` is False only for an adaptive lender before its last slot."""
        done = (not self._adaptive) or self._last_t >= self.inst.grid.T_slow - 1
        return Schedule(self.model.schedule, self._R(), done)
