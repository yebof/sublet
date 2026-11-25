"""Policy A1: C2's single-site rent / buy / insure rule in the engine (design/sim_spec_ms2.md §9.4;
design Table 5.7, §5.4.1).

Domain (PolicyError otherwise): one client c0 of LLM j; one revocable site l_r and one revocable
contract k_r on it with g_j a < q_j (alpha < 1, M59); protected contracts (flagged by
common.treated_as_protected, M47) at reachable sites, of which A1 uses the cheapest (l_p, k_p); none:
RRL mode (C2-Cor6: cold reaction, no insurance). Engine: auto_drain=False.

At reset A1 maps (l_r, k_r) into C2 units (c2rule.c2_units, rep_site l_p, or l_r in RRL mode),
evaluates the thresholds (C2-T4 with switch 'beta', C2-SW with 'c2sw'), fixes the reaction and the
insurance decision (C2-T2, M21) and the purchase delay n_s0 = ceil(s0_min / Δs) (M28). Per slow slot
it runs the ski-rental clock of each demand episode: buy revocable (or protected if insured) n_s0
slots into the episode; at a notice react cold (nothing until the death) or warm (buy protected at
the latest pre-warm slot, timing.latest_prewarm_slot); restart the clock at a revocation death
without protection (M29); release at the episode end after the billed term (M50). ALG*'s
wait-and-insure branch has no engine counterpart (M30).

Status: C2-T4 (2 - alpha for H >= H*_mu under (C'), PROVEN) holds for this rule in C2's game, which
harness/c2_harness.py checks; at the default switch cost the reaction is the C2-SW formula's
(CONJECTURE, Q11, Q17). In the engine (tau_k >= 1 slot, resale, prepaid billing) A1 has no proven
ratio.
"""
from __future__ import annotations

import math
from typing import Optional

import numpy as np

from ..timing import latest_prewarm_slot
from ..types import Buy, PublicView, SlowObs
from ..policies.base import Policy
from . import c2rule
from .common import EPS_DEMAND, LeaseBook, PolicyError, lam_ms, resolve_params, slot_max_demand, \
    treated_as_protected

_CHOICES = {"reaction": ("c2sw", "cold", "prewarm_if_feasible"), "switch": ("c2sw", "beta"),
            "insure": ("lb_react", "never", "always"), "s0_round": ("ceil", "floor"),
            "release": ("after_prepaid", "immediate")}


class A1(Policy):
    """C2's ALG* on one site (§9.4). Parameters as design/sim_spec_ms2.md §4.2."""
    name = "A1"
    PARAMS = {"reaction": "c2sw", "switch": "c2sw", "insure": "lb_react", "s0_round": "ceil",
              "release": "after_prepaid", "i2_wait": False, "site_rev": None, "contract_rev": None,
              "site_prot": None}

    def __init__(self, **kw):
        self._params, _ = resolve_params(self.PARAMS, kw, "A1")
        for name, allowed in _CHOICES.items():
            if self._params[name] not in allowed:
                raise PolicyError(f"A1: {name} must be one of {allowed}, got {self._params[name]!r}")
        if not isinstance(self._params["i2_wait"], (bool, np.bool_)):
            raise PolicyError(f"A1: i2_wait must be a bool, got {self._params['i2_wait']!r}")
        for name in ("site_rev", "site_prot", "contract_rev"):
            v = self._params[name]
            if v is not None and (isinstance(v, bool) or not isinstance(v, (int, np.integer, str))):
                raise PolicyError(f"A1: {name} must be None, an index or an id, got {v!r}")

    def params(self) -> dict:
        return dict(self._params)

    # -------------------------------------------------------- domain
    @staticmethod
    def _index(items, value, what: str) -> int:
        if isinstance(value, str):
            ids = [x.id for x in items]
            if value not in ids:
                raise PolicyError(f"A1: unknown {what} id {value!r}; known {ids}")
            return ids.index(value)
        v = int(value)
        if not 0 <= v < len(items):
            raise PolicyError(f"A1: {what} index {v} out of range")
        return v

    def _domain(self, view: PublicView) -> None:
        p = self._params
        if len(view.client_llm) != 1:
            raise PolicyError(f"A1: one client required, the instance has {len(view.client_llm)}")
        self.c0 = 0
        self.j = j = int(view.client_llm[0])
        delta = np.asarray(view.client_delta_usd_per_h, dtype=np.float64)[0]

        def offered(l, k):
            return int(k) in view.sites[l].menu and bool(np.isfinite(view.price[l, k]))

        def rev_contracts(l):
            return [int(k) for k in view.sites[l].menu if offered(l, k) and not treated_as_protected(view, k)]

        if p["site_rev"] is None:
            cand = [l for l in range(len(view.sites)) if rev_contracts(l)]
            if len(cand) != 1:
                raise PolicyError(f"A1: {len(cand)} sites offer a revocable contract; pass site_rev")
            l_r = cand[0]
        else:
            l_r = self._index(view.sites, p["site_rev"], "site")
        ks = rev_contracts(l_r)
        if p["contract_rev"] is None:
            if len(ks) != 1:
                raise PolicyError(f"A1: site {l_r} offers {len(ks)} revocable contracts; pass contract_rev")
            k_r = ks[0]
        else:
            k_r = self._index(view.contracts, p["contract_rev"], "contract")
            if k_r not in ks:
                raise PolicyError(f"A1: contract {k_r} is not a revocable contract offered at site {l_r}")
        if not np.isfinite(delta[l_r]):
            raise PolicyError(f"A1: the client cannot be served from the revocable site {l_r} (delta = inf)")
        if c2rule.alpha_of(view, j, l_r, k_r) >= 1:
            raise PolicyError(f"A1: g_j a >= q_j at site {l_r} contract {k_r} (alpha >= 1, outside C2's model, M59)")
        if p["site_prot"] is None:
            prot = c2rule.cheapest_protected(view, j, [self.c0])
        else:
            l_p = self._index(view.sites, p["site_prot"], "site")
            if not np.isfinite(delta[l_p]):
                raise PolicyError(f"A1: the client cannot be served from the protected site {l_p}")
            prot = c2rule.cheapest_protected(view, j, [self.c0], sites=[l_p])
            if prot is None:
                raise PolicyError(f"A1: site {l_p} offers no protected contract")
        self.l_r, self.k_r = l_r, k_r
        self.l_p, self.k_p = (None, None) if prot is None else prot
        self.rrl = prot is None

    # -------------------------------------------------------- reset
    def reset(self, view: PublicView, rng: np.random.Generator) -> None:
        super().reset(view, rng)
        p = self._params
        self._domain(view)
        j, l_r, k_r = self.j, self.l_r, self.k_r
        self.units = c2rule.c2_units(view, j, l_r, k_r, l_prot=self.l_p, k_prot=self.k_p,
                                     rep_site=self.l_r if self.rrl else self.l_p, switch=p["switch"])
        u = self.units
        self.th = c2rule.c2_thresholds(u.alpha, u.ap, u.mu, u.lam, 1.0, None if p["switch"] == "beta" else u.bw)
        if self.rrl or p["reaction"] == "cold":
            self.reaction = "cold"
        elif p["reaction"] == "prewarm_if_feasible":
            self.reaction = "warm"
        else:
            self.reaction = self.th.react
        self.insured = c2rule.insure_up_front(u, p["insure"])
        self.s0_min = c2rule.s0_min(view, j, l_r, k_r)
        x = self.s0_min / view.grid.slow_min
        self.n_s0 = int(math.ceil(x) if p["s0_round"] == "ceil" else math.floor(x))
        self.status = c2rule.hstar_status(u.alpha, u.ap, u.mu, u.lam, p["switch"],
                                          c2rule.at_default_calibration(u))
        self._lam_ms_p = None if self.rrl else int(lam_ms(view)[j, self.l_p])
        self.book = LeaseBook()
        self.clock: Optional[int] = None
        self.rev: Optional[int] = None
        self.prot: Optional[int] = None
        self.pending: Optional[int] = None
        self.noticed: set[int] = set()
        self.counts = {"episodes": 0, "buy_rev": 0, "buy_insure": 0, "buy_prewarm": 0, "notices": 0,
                       "prewarm_decided": 0, "prewarm_cancelled": 0, "cold_notices": 0, "revocations": 0,
                       "cold_deaths": 0, "restarts": 0, "refused": 0, "releases": 0}

    # -------------------------------------------------------- slot
    def act(self, obs: SlowObs) -> list:
        view, p, c = self.view, self._params, self.counts
        t = obs.t
        slow = view.grid.slow_min
        # 1. results of last slot's purchases, notices, deaths
        for key, r in self.book.begin(obs):
            if not r.ok:
                c["refused"] += 1
            elif key == "rev":
                self.rev = r.lease_id
            else:
                self.prot = r.lease_id
        for n in obs.notices:
            self.noticed.add(int(n.lease_id))
        if self.prot is not None and self.prot not in obs.leases:
            self.prot = None
        if self.rev is not None and self.rev not in obs.leases:
            lid, self.rev = self.rev, None
            if lid in self.noticed or self.book.cause(lid) in ("reclaim", "violation"):
                c["revocations"] += 1
                if self.pending is not None and self.pending > t:
                    self.pending = t              # died before the commit slot (e.g. a violation): buy now
                if self.prot is None and self.pending is None:
                    c["cold_deaths"] += 1
                    c["restarts"] += 1
                    self.clock = t
        # 2.-3. episode end
        on = bool(slot_max_demand(obs)[self.c0] > EPS_DEMAND)
        if not on:
            if self.pending is not None:
                c["prewarm_cancelled"] += 1       # test (b): no demand before or at the commit slot
            self.clock = self.pending = None
            for lid in (self.rev, self.prot):
                L = obs.leases.get(lid) if lid is not None else None
                if L is not None and (p["release"] == "immediate" or t * slow >= L.prepaid_end_min):
                    self.book.release(lid)
                    c["releases"] += 1
                    if lid == self.rev:
                        self.rev = None
                    else:
                        self.prot = None
            return self.book.assemble(obs, view)
        # 4. new episode
        if self.clock is None and self.rev is None and self.prot is None and self.pending is None:
            self.clock = t
            c["episodes"] += 1
        # 5. notice on the revocable lease
        for n in obs.notices:
            if self.rev is None or int(n.lease_id) != self.rev or self.prot is not None:
                continue
            c["notices"] += 1
            t_c = None
            if self.reaction == "warm":
                t_c = latest_prewarm_slot(t, int(n.death_min), self._lam_ms_p, view.grid)
            if t_c is None:
                c["cold_notices"] += 1
            else:
                self.pending = t_c
                c["prewarm_decided"] += 1
        staged = False
        # 6. pre-warm commit (test (b): demand is on)
        if self.pending is not None and self.pending == t:
            self.book.buy("prot", Buy(self.l_p, self.k_p, self.j, 1, tag="a1:prewarm"))
            c["buy_prewarm"] += 1
            self.pending = None
            staged = True
        # 7. ski-rental purchase n_s0 slots into the episode
        if (not staged and self.rev is None and self.prot is None and self.pending is None
                and self.clock is not None and t >= self.clock + self.n_s0):
            if self.insured:
                self.book.buy("insure", Buy(self.l_p, self.k_p, self.j, 1, tag="a1:insure"))
                c["buy_insure"] += 1
            elif not (p["i2_wait"] and obs.site_announced is not None and bool(obs.site_announced[self.l_r])):
                self.book.buy("rev", Buy(self.l_r, self.k_r, self.j, 1, tag="a1"))
                c["buy_rev"] += 1
        # 8. a protected lease is kept until the episode ends
        return self.book.assemble(obs, view)

    def report(self) -> dict:
        u, th = self.units, self.th
        th_min = {f"{k}_min": u.to_min(getattr(th, k)) for k in ("s0", "Rw", "Rc", "Rh", "Hc", "Hh", "Hstar", "Rrho")}
        return {"sites": {"rev": [self.l_r, self.k_r], "prot": None if self.rrl else [self.l_p, self.k_p]},
                "rrl": self.rrl, "units": u.as_dict(), "th": th.as_dict(), "th_minutes": th_min,
                "reaction": self.reaction, "status": self.status, "insured": self.insured,
                "s0_min": self.s0_min, "n_s0": self.n_s0, "counts": dict(self.counts),
                "book": dict(self.book.stats)}


__all__ = ["A1"]
