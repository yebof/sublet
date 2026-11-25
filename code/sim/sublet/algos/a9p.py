"""A9-P, the protected-only critical-ratio renter (design/ms7/plan.md X4, C54; design/ms7/feasibility/baselines.md
§1(d-ii), §2 item 2, §3 B1; registry id A9P, online-I1).

A subclass of A9 (algos/a9.py, NoticeCriticalRatio) with one parameter more, protected_only (True). With
protected_only every client that has a usable flagged site (contracts.c2_contract_table's l_p >= 0: a site whose
cheapest flagged contract k_p(l) gives sigma^p_cl = g_j a_{l k_p} + delta_cl < q_j) is insured, whatever C2-T2's test
says, so it buys only k_p at its usable flagged sites in (sigma^p, l) order, with A9.1's threshold theta_c at (l_p, k_p)
and A9.2's release rule unchanged (A9's insured branch); a client without such a site buys nothing (its demand goes to
fallback), so the policy never holds a revocable lease. This is BL7's opposite (revocable-only, baselines/wrappers.py)
and measures what renting without revocation is worth at the calibrated protected price; protected leases are never
announced, so its runs do not depend on the lender's schedule. With protected_only False the class is A9 itself (the
same ledger and report but for the parameter; tests/test_ms7_baselines.py).

Why a subclass and not a key of A9: tests/test_a9.py pins A9's OWN_PARAMS and NoticeCriticalRatio().params() ==
NoticeCriticalRatio.PARAMS, so a new A9 key, even one hidden by QUIET_KEYS, would change A9's frozen keys or its
records (the study's B1 placed the flag in a9.py; this module keeps a9.py and its records unchanged).

Status: HEURISTIC, as A9's rules (no ratio is claimed). Policy isolation (design/sim_spec_ms2.md §2.2): numpy, the
standard library and sublet.algos.a9 (which brings A9's allowed imports); no file is read.
"""
from __future__ import annotations

from typing import Optional

import numpy as np

from ..types import INF, PublicView, SlowObs
from .a9 import NoticeCriticalRatio
from .common import PolicyError


class ProtectedOnly(NoticeCriticalRatio):
    """A9-P (online-I1): A9 with every client that has a usable flagged site insured and no revocable purchase."""
    name = "A9P"
    PARAMS = {**NoticeCriticalRatio.PARAMS, "protected_only": True}

    def _validate(self) -> None:
        super()._validate()
        v = self._params["protected_only"]
        if not isinstance(v, (bool, np.bool_)):
            raise PolicyError(f"{type(self).__name__}: protected_only must be true or false, got {v!r}")

    def reset(self, view: PublicView, rng: np.random.Generator) -> None:
        super().reset(view, rng)
        self.n_no_flagged = 0
        if not self._params["protected_only"]:
            return
        tab = self.table
        lp = np.asarray(tab["lp"], dtype=np.int64)
        self.insured = lp >= 0
        self.n_no_flagged = int(np.sum(lp < 0))
        # A9.1's threshold at (l_p, k_p) for every client (A9.reset's insured branch); INF without a flagged site
        price = np.asarray(view.price, dtype=np.float64)
        st = self.sites
        g, q, cl, delta = st.g, st.q, st.cl_llm, st.delta
        for c in range(self.n):
            j, l = int(cl[c]), int(lp[c])
            k = int(self.kp[l]) if l >= 0 else -1
            if l < 0 or k < 0:
                self.l_c[c], self.theta[c], self.waste_rate[c] = -1, INF, 0.0
                continue
            a, dl = float(price[l, k]), float(delta[c, l])
            self.l_c[c] = l
            if self._params["theta"] == "be":
                self.theta[c], self.waste_rate[c] = g[j] * a / (q[j] - dl), q[j] - dl
            else:
                self.theta[c], self.waste_rate[c] = (g[j] * a + dl) / q[j], q[j]

    def _site(self, c: int, obs: SlowObs, excl: set) -> Optional[int]:
        """A9's site rule; with protected_only a client without a usable flagged site gets none."""
        if self._params["protected_only"] and not self.insured[c]:
            return None
        return super()._site(c, obs, excl)

    def report(self) -> dict:
        out = super().report()
        if "a9" in out:
            out["a9p"] = {"protected_only": bool(self._params["protected_only"]),
                          "clients_without_flagged_site": int(getattr(self, "n_no_flagged", 0))}
        return out


__all__ = ["ProtectedOnly"]
