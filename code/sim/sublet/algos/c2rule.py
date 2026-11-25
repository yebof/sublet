"""C2 rule: thresholds of C2-T4 and C2-SW, ALG* as a plan function, C2 units of a lease, H*_mu and
the insurance test (design/sim_spec_ms2.md §9; design/theory/c2_single_site.md §1, §6).

C2 units: fallback price q = 1, the normalizer beta = beta~ = 1 and times in units of beta~ / q.
`c2_thresholds` evaluates the expressions of the reference scripts in their order, so that the
values agree bit for bit: `c2/alg_check.py::thresholds` (lines 101-113, switch cost beta, C2-T4),
`c2/audit/model_switch_cost_default.py::c2sw` (lines 59-68, switch cost bw, C2-SW, CONJECTURE) and
`c2/audit/alg_star_exact.py::thresholds(..., rrl=True)` (lines 31-36, no protected contract,
C2-Cor6). `AlgStarRule` is ALG* of C2 §6 written as a plan; `harness/c2_harness.py` prices its
plans in C2's game. `c2_units` maps a revocable lease of the PublicView into C2 units (§9.2, M23);
`h_star_mu` and `hstar_status` give H*_mu with the status labels of a11 (§9.2); `insure_up_front`
is the insurance test of C2-T2 (§9.3, M21). Contracts with alpha = g_j a / q_j >= 1 lie outside
C2's results (M59): `c2_units` raises PolicyError for them and `h_star_mu` returns no value.

Policy isolation (§2.2): numpy, the standard library, sublet.types, sublet.calib (a11 inputs) and
sublet.algos.common; the reference module `families` only through `paths.import_c2`, lazily, for
the insurance bound.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Literal, Optional, Sequence

import numpy as np

from .. import calib
from ..types import INF, PublicView
from .common import PolicyError, treated_as_protected

MU_EXACT_POINTS = (0.2, 0.5, 1.0, 2.0)    # mu / beta~ of the exact-game points (model_switch_cost_default.txt)
SWITCHES = ("c2sw", "beta")


def _big(num: float, den: float) -> float:
    """num / den, and +-inf (sign of num > 0) for den = 0 (`big` of alg_check.py, `div` of c2sw)."""
    if den == 0:
        return INF if num > 0 else -INF
    return num / den


# ---------------------------------------------------------------- thresholds
@dataclass(frozen=True)
class C2Thresholds:
    """Thresholds of ALG* in C2 units (C2 §6): s0 = beta/(1-alpha), R_wait, R_cold, R_warm, H(R_cold),
    max(lam, H(R_warm)), H* = min of the two, the reaction (cold iff H_c <= H_h), its threshold R_rho
    and the regime of R_rho ('sit-out' iff R_rho <= R_wait + tol)."""
    s0: float; Rw: float; Rc: float; Rh: float; Hc: float; Hh: float; Hstar: float
    react: Literal["cold", "warm"]; Rrho: float; regime: Literal["sit-out", "known window"]
    rrl: bool = False              # no protected contract (ap None): C2-Cor6

    def as_dict(self) -> dict:
        return asdict(self)


def c2_thresholds(alpha, ap, mu, lam, beta=1.0, bw=None, tol=1e-12) -> C2Thresholds:
    """ALG*'s thresholds (§9.1). bw None: C2-T4 (switch cost beta), the expressions of
    alg_check.thresholds; bw given: C2-SW (CONJECTURE), those of model_switch_cost_default.c2sw;
    ap None: RRL (C2-Cor6), those of alg_star_exact.thresholds(rrl=True), bw ignored and chi never
    computed. PolicyError for alpha >= 1 (outside C2's model, M59)."""
    a, b = alpha, beta
    if not a < 1:
        raise PolicyError(f"c2_thresholds: alpha = {alpha!r} >= 1 is outside C2's model (M59)")
    s0 = b / (1 - a)
    c = 2 - a
    Rw = c * b / (1 - a) ** 2

    def H(R):
        return R - s0 if R <= Rw + tol else R

    if ap is None:
        Rc = s0 + mu / (2 * (1 - a))
        Hc = H(Rc)
        return C2Thresholds(s0=s0, Rw=Rw, Rc=Rc, Rh=INF, Hc=Hc, Hh=INF, Hstar=Hc, react="cold", Rrho=Rc,
                            regime="sit-out" if Rc <= Rw + tol else "known window", rrl=True)
    kap = c * ap - a
    if bw is None:
        Rc = max(s0 + mu / (2 * (1 - a)), _big(mu - 2 * (1 - a) * b, a * (1 - a)), _big(mu + a * b, kap))
        Rh = max(s0 + b / (2 * (1 - a)), _big((1 + a) * b, kap))
        if lam > 0:
            Rh = max(Rh, lam + _big((1 + a) * b, a * (1 - a)))
    else:
        Rc = max(s0 + mu / (2 * (1 - a)), _big(mu + a * b - (2 - a) * bw, a * (1 - a)), _big(mu + a * b, kap))
        Rh = max(s0 + bw / (2 * (1 - a)), _big(a * b + bw, kap),
                 lam + _big(a * b + bw, a * (1 - a)) if lam > 0 else -INF)
    Hc = H(Rc)
    Hh = max(lam, H(Rh))
    react = "cold" if Hc <= Hh else "warm"
    Rrho = Rc if react == "cold" else Rh
    return C2Thresholds(s0=s0, Rw=Rw, Rc=Rc, Rh=Rh, Hc=Hc, Hh=Hh, Hstar=min(Hc, Hh), react=react, Rrho=Rrho,
                        regime="sit-out" if Rrho <= Rw + tol else "known window", rrl=False)


class AlgStarRule:
    """ALG* (C2 §6; alg_check.alg_star_cost) as a plan function. Without a notice it buys the
    revocable lease at s_buy; for a window end R announced at a = R - H, `plan(R, H)` returns
      ('none', s)                    R = inf (no reclaim);
      ('react-cold', s, R)           a >= s or R >= R_thr, reaction cold (pay mu at R, stay on fallback);
      ('react-warm', s, R, R - lam)  a >= s or R >= R_thr, reaction warm (commit protected at R - lam,
                                     handover at R);
      ('wait-insure', max(R, s))     otherwise: stay on fallback, buy protected at max(R, s);
      ('fallback',)                  otherwise in RRL mode: stay on fallback to the end of the demand."""

    def __init__(self, s_buy: float, R_thr: float, react: str, lam: float, rrl: bool = False):
        if react not in ("cold", "warm"):
            raise ValueError(f"AlgStarRule: react must be 'cold' or 'warm', got {react!r}")
        if rrl and react != "cold":
            raise ValueError("AlgStarRule: the RRL mode reacts cold")
        self.s, self.R_thr, self.react, self.lam, self.rrl = s_buy, R_thr, react, lam, bool(rrl)

    @classmethod
    def from_thresholds(cls, th: C2Thresholds, lam: float) -> "AlgStarRule":
        return cls(th.s0, th.Rrho, th.react, lam, th.rrl)

    def plan(self, R: float, H: float) -> tuple:
        s = self.s
        if math.isinf(R):
            return ("none", s)
        a = R - H
        if a >= s or R >= self.R_thr:
            if self.react == "cold":
                return ("react-cold", s, R)
            return ("react-warm", s, R, R - self.lam)
        if self.rrl:
            return ("fallback",)
        return ("wait-insure", max(R, s))


def ins_plan(th: C2Thresholds) -> tuple:
    """C2-T2's insuring algorithm INS: buy protection at s0 whatever the window ('wait-insure', s0)."""
    return ("wait-insure", th.s0)


# ---------------------------------------------------------------- C2 units of a lease
@dataclass(frozen=True)
class C2Units:
    """A revocable lease in C2 units (§9.2, M23): q = 1, beta = beta~_jlk = 1, one time unit =
    beta~ / q_j hours. ap and bw are None without a protected contract (RRL)."""
    alpha: float; ap: Optional[float]; mu: float; lam: float; bw: Optional[float]; H: float
    beta_tilde_usd: float; time_unit_h: float

    def to_min(self, x: float) -> float:
        """C2 time -> minutes."""
        return x * self.time_unit_h * 60.0

    def as_dict(self) -> dict:
        return asdict(self)


def _offered(view: PublicView, l: int, k: int) -> bool:
    return int(k) in view.sites[l].menu and bool(np.isfinite(view.price[l, k]))


def alpha_of(view: PublicView, j: int, l: int, k: int) -> float:
    """alpha = g_j price[l, k] / q_j (INF if (l, k) is not offered)."""
    a = float(view.price[l, k])
    if not np.isfinite(a):
        return INF
    return view.llms[j].g * a / float(view.llms[j].q_usd_per_h)


def s0_min(view: PublicView, j: int, l: int, k: int) -> float:
    """C2's s0 in minutes, 60 beta~_jlk / (q_j - g_j a_lk) (§9.2); PolicyError unless g_j a_lk < q_j."""
    a = float(view.price[l, k])
    L = view.llms[j]
    q, g = float(L.q_usd_per_h), L.g
    if not np.isfinite(a) or not g * a < q:
        raise PolicyError(f"s0_min: site {l} contract {k} has g a >= q_j for LLM {j} (alpha >= 1, M59)")
    return 60.0 * float(view.beta_tilde_usd[j, l, k]) / (q - g * a)


def c2_units(view: PublicView, j: int, l: int, k: int, *, l_prot: Optional[int], k_prot: Optional[int],
             rep_site: int, mu_usd: Optional[float] = None, switch: str = "c2sw") -> C2Units:
    """C2 units of a revocable lease of contract k at site l for LLM j (§9.2 table): beta~ at the
    lease's own price; alpha = g_j a_lk / q_j; ap = g_j a_p / q_j at (l_prot, k_prot) (None: RRL);
    mu = (mu_fb_j + pi_j (W_f - H_k)^+) / beta~, or mu_usd / beta~; lam from lam_s[j, rep_site];
    bw = (beta_{j,rep} + g_j a_p lam' / 3600) / beta~ for switch 'c2sw', 1 for 'beta', None in RRL
    mode; H = (H_k / 60) q_j / beta~. rep_site is set by the caller (A1: l_p, or l_r in RRL mode;
    the handler: the replacement site; P3: l). PolicyError if (l, k) is not offered, if
    g_j a_lk >= q_j (alpha >= 1, M59) or if beta~ <= 0."""
    if switch not in SWITCHES:
        raise PolicyError(f"c2_units: switch must be one of {SWITCHES}, got {switch!r}")
    if not _offered(view, l, k):
        raise PolicyError(f"c2_units: contract {k} is not offered at site {l}")
    LLM = view.llms[j]
    q, g = float(LLM.q_usd_per_h), LLM.g
    a = float(view.price[l, k])
    if not g * a < q:
        raise PolicyError(f"c2_units: g_j a = {g * a!r} >= q_j = {q!r} at site {l} contract {k} "
                          "(alpha >= 1, outside C2's results, M59)")
    bt = float(view.beta_tilde_usd[j, l, k])
    if not (np.isfinite(bt) and bt > 0):
        raise PolicyError(f"c2_units: beta~ = {bt!r} at site {l} contract {k}; C2 units need beta~ > 0")
    alpha = g * a / q
    lam_rep = float(view.lam_s[j, rep_site])
    lam = (lam_rep / 3600.0) * q / bt
    if l_prot is None:
        ap = bw = None
    else:
        if k_prot is None or not _offered(view, l_prot, k_prot):
            raise PolicyError(f"c2_units: protected contract {k_prot} is not offered at site {l_prot}")
        a_p = float(view.price[l_prot, k_prot])
        ap = g * a_p / q
        bw = 1.0 if switch == "beta" else (float(view.beta_usd[j, rep_site]) + g * a_p * lam_rep / 3600.0) / bt
    Hk = int(view.contracts[k].H_min)
    if mu_usd is None:
        st = view.stranding
        mu_usd = float(st.mu_fb_usd[j]) + float(st.pi_usd_per_min[j]) * max(float(st.W_f_min) - Hk, 0.0)
    return C2Units(alpha=alpha, ap=ap, mu=float(mu_usd) / bt, lam=lam, bw=bw, H=(Hk / 60.0) * q / bt,
                   beta_tilde_usd=bt, time_unit_h=bt / q)


def cheapest_protected(view: PublicView, j: int, clients: Sequence[int],
                       sites: Optional[Sequence[int]] = None) -> Optional[tuple[int, int]]:
    """(l_p, k_p): the cheapest offered contract flagged by common.treated_as_protected (M47) at a
    site with delta_cl < inf for some client c of `clients` (by price, then site and contract
    index), among `sites` if given; None if there is none (RRL)."""
    delta = np.asarray(view.client_delta_usd_per_h, dtype=np.float64)
    cl = [int(c) for c in clients]
    best, key = None, None
    for l in (range(len(view.sites)) if sites is None else sites):
        l = int(l)
        if not cl or not any(np.isfinite(delta[c, l]) for c in cl):
            continue
        for k in view.sites[l].menu:
            k = int(k)
            if not treated_as_protected(view, k) or not np.isfinite(view.price[l, k]):
                continue
            kk = (float(view.price[l, k]), l, k)
            if key is None or kk < key:
                best, key = (l, k), kk
    return best


# ---------------------------------------------------------------- H*_mu and its status
def _defaults() -> tuple[float, float, float]:
    """alpha, alpha_p, phi of the default calibration (a11_calibration.json `inputs`)."""
    i = calib.A11["inputs"]
    return float(i["alpha"]), float(i["alpha_p"]), float(i["phi"])


def at_default_calibration(units: C2Units, tol: float = 1e-9) -> bool:
    """True iff alpha, alpha_p, lam and bw equal the default calibration's (alpha and alpha_p of a11
    `inputs`, lam = 1/(alpha + phi), bw = alpha_p/(alpha + phi)) within tol: the points that
    model_switch_cost_default.txt checks in the exact game (§9.2)."""
    AL, AP, PHI = _defaults()
    if units.ap is None or units.bw is None:
        return False
    return (abs(units.alpha - AL) <= tol and abs(units.ap - AP) <= tol
            and abs(units.lam - 1.0 / (AL + PHI)) <= tol and abs(units.bw - AP / (AL + PHI)) <= tol)


def hstar_status(alpha, ap, mu, lam, switch, at_default_price) -> str:
    """Status label of H*_mu (C2 units), the rule of a11_calibration.py (c_conditions and
    hstar_mu_entries, lines 292-333) plus the lam <= s0 clause of (C') and two labels, tested in this
    order: 'NA-alpha>=1' if alpha >= 1; 'RRL' if ap is None; 'NA-Cprime' if (C') fails ((2-a) ap >= 1,
    ap > a (2-a), lam <= s0 = 1/(1-a) + 1e-12); switch 'beta': 'PROVEN-Cor5' for the simple form under
    (C) (mu <= 1, or mu <= 2 with the Cor 5(3) proviso), else 'PROVEN-T4'; switch 'c2sw': 'VERIFIED'
    at the default price with mu in {0.2, 0.5, 1, 2}, else 'CONJECTURE'; suffix ' +C-fails' when (C')
    holds and (C) (also alpha <= 1/2) fails."""
    if switch not in SWITCHES:
        raise PolicyError(f"hstar_status: switch must be one of {SWITCHES}, got {switch!r}")
    a = alpha
    if a >= 1:
        return "NA-alpha>=1"
    if ap is None:
        return "RRL"
    s0 = 1 / (1 - a)
    if not ((2 - a) * ap >= 1 and ap > a * (2 - a) and lam <= s0 + 1e-12):
        return "NA-Cprime"
    cond_c = a <= 0.5
    if switch == "beta":
        chi = (2 - a) * ap - a
        proviso = (mu + a) / chi <= s0 + mu / (2 * (1 - a))
        simple = cond_c and (mu <= 1 or (mu <= 2 and proviso))
        status = "PROVEN-Cor5" if simple else "PROVEN-T4"
    else:
        exact_mu = any(abs(mu - v) <= 1e-9 for v in MU_EXACT_POINTS)
        status = "VERIFIED" if (at_default_price and exact_mu) else "CONJECTURE"
    if not cond_c:
        status += " +C-fails"
    return status


def h_star_mu(view: PublicView, j: int, l: int, k: int, *, l_prot: Optional[int] = None,
              k_prot: Optional[int] = None, rep_site: Optional[int] = None, mu_usd: Optional[float] = None,
              switch: str = "c2sw") -> dict:
    """H*_mu of contract k at site l for LLM j at its own price (§9.2): {'value_s' (H* in seconds),
    'over_lambda' (H*/lam; None for lam = 0), 'reaction' ('cold' or 'warm'), 'regime', 'status'}.
    Keywords as c2_units (rep_site defaults to l; l_prot None: RRL thresholds). For g_j a_lk >= q_j
    the values are None and the status is 'NA-alpha>=1', without calling c2_units or c2_thresholds
    (M59); likewise status 'NA-beta~=0' where beta~_jlk = 0 (C2 units undefined). A status
    'NA-Cprime' keeps the formula's value; P3 counts every 'NA-' status as infinite. PolicyError if
    (l, k) is not offered."""
    if not _offered(view, l, k):
        raise PolicyError(f"h_star_mu: contract {k} is not offered at site {l}")
    if alpha_of(view, j, l, k) >= 1:
        return {"value_s": None, "over_lambda": None, "reaction": None, "regime": None, "status": "NA-alpha>=1"}
    if not float(view.beta_tilde_usd[j, l, k]) > 0:
        return {"value_s": None, "over_lambda": None, "reaction": None, "regime": None, "status": "NA-beta~=0"}
    u = c2_units(view, j, l, k, l_prot=l_prot, k_prot=k_prot, rep_site=l if rep_site is None else rep_site,
                 mu_usd=mu_usd, switch=switch)
    th = c2_thresholds(u.alpha, u.ap, u.mu, u.lam, 1.0, None if switch == "beta" else u.bw)
    return {"value_s": th.Hstar * u.time_unit_h * 3600.0,
            "over_lambda": th.Hstar / u.lam if u.lam > 0 else None,
            "reaction": th.react, "regime": th.regime,
            "status": hstar_status(u.alpha, u.ap, u.mu, u.lam, switch, at_default_calibration(u))}


# ---------------------------------------------------------------- insurance (C2-T2)
_LB_CACHE: dict = {}
LB_STATS = {"calls": 0, "hits": 0}     # families.lb_react evaluations and cache hits


def _sig12(x) -> Optional[float]:
    if x is None:
        return None
    x = float(x)
    return float(f"{x:.12g}") if math.isfinite(x) else x


def cr_react_lb(units: C2Units) -> float:
    """LB_react(H) of C2-T3: families.lb_react(Params(mu, alpha, ap, H, lam))[0] with tau = 0 and
    beta = 1 (switch cost beta), evaluated on the parameters rounded to 12 significant digits and
    cached per that tuple. It is a grid value, not certified (§9.3). Without a protected contract the
    protected option is removed (allow_p False)."""
    key = tuple(_sig12(v) for v in (units.mu, units.alpha, units.ap, units.H, units.lam))
    if key in _LB_CACHE:
        LB_STATS["hits"] += 1
        return _LB_CACHE[key]
    from ..paths import import_c2
    c2 = import_c2()
    mu, al, ap, H, lam = key
    if ap is None:
        P = c2.model.Params(mu=mu, alpha=al, H=H, lam=lam, allow_p=False)
    else:
        P = c2.model.Params(mu=mu, alpha=al, ap=ap, H=H, lam=lam)
    with np.errstate(invalid="ignore", over="ignore", divide="ignore"):
        v = float(c2.families.lb_react(P)[0])
    LB_STATS["calls"] += 1
    _LB_CACHE[key] = v
    return v


def insure_up_front(units: C2Units, rule: str = "lb_react") -> bool:
    """Buy protection up front (C2-T2's INS) instead of the revocable lease (§9.3, M21). 'never' and
    'always' as named; 'lb_react': with CR_ins = max(2 - alpha, alpha_p / alpha) (C2-T2, PROVEN),
    insure iff alpha_p <= alpha (2 - alpha) (C2-T2(4), decided without a call) or
    CR_ins < LB_react(H) (cr_react_lb). Always False without a protected contract (RRL)."""
    if rule not in ("lb_react", "never", "always"):
        raise PolicyError(f"insure_up_front: rule must be 'lb_react', 'never' or 'always', got {rule!r}")
    if units.ap is None or rule == "never":
        return False
    if rule == "always":
        return True
    a, ap = units.alpha, units.ap
    if ap <= a * (2 - a):
        return True
    if a <= 0:
        return False                 # CR_ins infinite (families.cr_ins)
    return max(2 - a, ap / a) < cr_react_lb(units)


__all__ = ["C2Thresholds", "c2_thresholds", "AlgStarRule", "ins_plan", "C2Units", "c2_units", "alpha_of",
           "s0_min", "cheapest_protected", "at_default_calibration", "hstar_status", "h_star_mu",
           "cr_react_lb", "insure_up_front", "LB_STATS", "MU_EXACT_POINTS"]
