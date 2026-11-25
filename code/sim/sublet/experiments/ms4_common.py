"""Shared MS4 driver layer (design/sim_spec_ms4.md §2.1, §2.2, §2.5, §2.6, §3.3, §3.4, §3.7(c)(e); open choices M1,
M2, M22, M35, M36; deliverable D30, unit U19).

What more than one MS4 driver (E3, E5, E7) needs, on top of the MS3 layer ms3_common, which the MS4 drivers use
unchanged (job ids, records, resume, the MILP limit, Q39's lower bound and the brackets, aggregation):

  Sublet's allowance (M36, §3.3)  B0_SHARE, B0_RULE, sublet_params, theory_params, allowance_record, a8_record,
                                  info_class_reported, count_certificates, need_params, allowance_need
  both accountings (Q32, M2)      references, accountings
  certificates (§2.2)             certify, siloed_run
  W0 (note §5.5, §3.9)            w0, stress_modes
  benchmarks (§2.5)               sum_bench
  instances (§3.4, §3.7)          e7_spec, mode_lender_model, routing_overrides, e7r_h5_overrides, e7r_h5_spec,
                                  gap_instance

Sublet's allowance (M36, adopted on 2026-10-26; share re-set to 10% on 2026-10-26 by the same procedure on
the instances as built, measurement 9). Every A8 run of MS4 (Sublet = A8 around BL5, A7 + guard = A8 around A7, every
Sublet-siloed sub-run) uses gamma = 1, kappa None (the constant allowance of guard.Ratchet.allowance, B(t) = B0) and
B0 = B0_SHARE x BL0a of the run's own instance (B0_SHARE 0.1), with BL0a = e6.bl0a_all(inst),
the all-fallback bill of the run's horizon, computed by the driver before the run and passed to A8 as the number
B0; a driver never types B0. Theorem W(a)(b) (PROVEN for the engine as implemented under C1-C3, audited) then gives
ALG(T) <= C_S(T) + B0 without an abort and with an abort after which S follows FB at every slot; G3(b)'s ratio does
not apply (G3(d), G6), and W(c) stays CONJECTURE. The allowance sweep E7(f) calls sublet_params with its shares and
theory_params for Algorithm 1's defaults (B0 'auto', kappa 10).

Information class (§2.2). registry.info_class is not changed, so a run record's info_class of Sublet stays
'online-I1 + a-priori N'; a run whose B0_rule is a share of BL0a also records info_class_reported = 'online-I1 +
a-priori N + a-priori BL0a' (INFO_CLASS_REPORTED): the exact all-fallback bill of the realized horizon, a
hindsight-reference statistic passed a priori as N is, which no theorem assumes known.

Run records (§2.6). Every A8 entry carries B0_rule, B0_usd, bl0a_usd, gamma, kappa (allowance_record),
info_class_reported, the certificate, its case, t_a and aborted (a8_record); every summary counts the
certificates by case and held (count_certificates). Every cost entry of E7, and of E3 and E5 where they report
cost over BL0a, carries both accountings (accountings), and each summary's meta the references (references).

Importing this module loads only the standard library, numpy and ms3_common; the drivers, e1, e6, q44_study and
the guard are imported inside the functions that need them.
"""
from __future__ import annotations

import copy
import dataclasses
import math
from typing import Callable, Iterable, Mapping, Optional

import numpy as np

from .ms3_common import num_key, put

# ---------------------------------------------------------------- Sublet's allowance (§3.3, M36)
B0_SHARE = 0.1                          # M36: B0 = 10% of the run's own BL0a (measurement 9)
B0_RULE = "0.1*BL0a"                    # the record's B0_rule of B0_SHARE
GAMMA = 1.0                             # M36: gamma = 1
THEORY_RULE = "auto, kappa 10"          # Algorithm 1's defaults (guard.Guarded.PARAMS): the sweep's theory point
CONSTANT_RULE = "constant"              # a number B0 that is no share of BL0a (to SHARE_DIGITS digits)
SHARE_DIGITS = 6                        # significant digits of a share in B0_rule ("0.005*BL0a")
SHARE_TOL = 1e-12                       # relative tolerance of B0 = share x BL0a (check E7-6)
INFO_BL0A = " + a-priori BL0a"          # §2.2: the a-priori scalar of a share rule
INFO_CLASS_REPORTED = "online-I1 + a-priori N + a-priori BL0a"    # Sublet's reported class under I1 (§2.2)
CASES = ("W(a)", "W(b)", "W(c)", "unavailable")                    # e1.cert_case
PROVEN_CASES = ("W(a)", "W(b)")                                     # Theorem W's proven cases
CERT_PER_SLOT = ("ALG_per_slot",)       # q44_study.certificate's per-slot list: left out of run records
NEED_B0 = 1e12                          # an allowance that never binds (measurement 8; need_params)

# ---------------------------------------------------------------- instances (§3.4, §3.7(c)(e), M1, M22, M35)
E7_CONFIG = "bench_e7f.json"            # M35: the memory benchmark's config, with the driver's overrides
E7R_CONFIG = "bench_e7r.json"           # the gap reruns' config (§3.7(e))
WEEK_MIN = 10080
DAY_MIN = 1440
MU_DEFAULT = 1.0                        # mu / beta~ at the headline (the configs' value, set explicitly)
ENGINE = {"check_invariants": True}     # §0 item 5: overrides the bench configs' false
E7_SEEDS = {"config": [1], "lender": "config", "policy": [0]}       # the specs' seeds unless a driver passes its own
# the contracts.0 and lender_defaults.menu override of Q44's block Q4 (experiments/q44_blocks/Q4.json, instance I2-H5)
H5_OVERRIDES = {"contracts.0": {"id": "s5_tau5_H5", "tau_min": 5, "H_min": 5},
                "lender_defaults.menu": ["s5_tau5_H5", "s5_tau5_H60", "s5_tau60_H0"]}
# M1 (alternative (b), decided 2026-10-26): n cross-region routing links, nested subgraphs of the default adjacency
# S7 (config.DEFAULT_ADJACENCY, MS1 spec §10 S7) on the main grid's five regions; None: S7 itself, the main grid
ROUTING_LINKS = {0: (),
                 2: (("north_america", "south_america"), ("east_asia", "south_southeast_asia")),
                 3: (("north_america", "south_america"), ("east_asia", "south_southeast_asia"),
                     ("north_america", "europe")),
                 5: None}


# ---------------------------------------------------------------- Sublet's allowance (§2.1, §3.3, M36)
def _finite(v) -> Optional[float]:
    """float(v) if v is a finite number (not a bool), else None."""
    if v is None or isinstance(v, bool):
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


def _share(share) -> float:
    if isinstance(share, bool) or not isinstance(share, (int, float, np.integer, np.floating)):
        raise TypeError(f"share must be a number, got {share!r}")
    s = float(share)
    if not math.isfinite(s) or s < 0:
        raise ValueError(f"share must be a finite number >= 0, got {share!r}")
    return s


def sublet_params(inst, inner: str = "BL5", share: float = B0_SHARE) -> dict:
    """A8's parameters under M36 (§2.1, §3.3): {'inner': inner, 'gamma': 1.0, 'kappa': None, 'B0': share x
    e6.bl0a_all(inst)}, with BL0a (`experiments/e6.py`, BL0a's analytic cost) of the run's own instance `inst`; with
    kappa None, guard.Ratchet.allowance gives the constant allowance B(t) = B0. Sublet takes inner 'BL5', A7 + guard
    inner 'A7' (the registry default of A8), a Sublet-siloed sub-run its sub-instance, the allowance sweep (§3.7(f))
    its shares. ValueError for an inner id that A8 does not guard (registry.A8_INNER_IDS)."""
    from ..algos.registry import A8_INNER_IDS
    from .e6 import bl0a_all
    if inner not in A8_INNER_IDS:
        raise ValueError(f"sublet_params: A8 guards one of {list(A8_INNER_IDS)}, not {inner!r}")
    return {"inner": str(inner), "gamma": GAMMA, "kappa": None, "B0": _share(share) * bl0a_all(inst)}


def theory_params(inner: str = "BL5") -> dict:
    """The allowance sweep's theory point (§2.1, §3.7(f)): {'inner': inner}, so that A8 runs with Algorithm 1's
    defaults (guard.Guarded.PARAMS: gamma 1, B0 'auto', one fresh replica per client, kappa 10); its records carry
    B0_rule THEORY_RULE ('auto, kappa 10', allowance_record)."""
    from ..algos.registry import A8_INNER_IDS
    if inner not in A8_INNER_IDS:
        raise ValueError(f"theory_params: A8 guards one of {list(A8_INNER_IDS)}, not {inner!r}")
    return {"inner": str(inner)}


def _b0_rule(b0: float, bl0a: float) -> str:
    """'<share>*BL0a' if b0 = share x bl0a to SHARE_TOL (relative) for a share of at most SHARE_DIGITS significant
    digits, else CONSTANT_RULE."""
    if bl0a > 0 and math.isfinite(bl0a) and b0 >= 0:
        s = float(f"{b0 / bl0a:.{SHARE_DIGITS}g}")
        if abs(s * bl0a - b0) <= SHARE_TOL * abs(b0):
            return f"{num_key(s)}*BL0a"
    return CONSTANT_RULE


def allowance_record(params: Mapping, inst) -> dict:
    """The allowance fields that every A8 run record carries (§2.1, §2.2, §2.6; check E7-6): B0_rule, B0_usd (the B0
    in USD that A8 resolves), bl0a_usd (e6.bl0a_all of the run's own instance), gamma and kappa (the resolved values:
    A8's defaults guard.Guarded.PARAMS where `params` leave them out). B0_rule is '<share>*BL0a' for a number B0 that
    is a share of bl0a_usd (to 1e-12 relative, at most 6 significant digits; B0_RULE for sublet_params' default),
    'auto, kappa <kappa>' for B0 'auto' (THEORY_RULE at A8's defaults; B0_usd is then guard.b0_auto of the instance's
    public view, the value A8 resolves at reset and reports as 'B0'), and 'constant' for any other number."""
    from ..algos.guard import Guarded, b0_auto
    from ..instance import public_view
    from .e6 import bl0a_all
    p = {**Guarded.PARAMS, **dict(params or {})}
    bl0a = float(bl0a_all(inst))
    kappa = None if p["kappa"] is None else float(p["kappa"])
    if p["B0"] == "auto":
        b0 = float(b0_auto(public_view(inst, "I1")))      # b0_auto reads prices, beta~ and routing arcs only
        rule = "auto, kappa " + ("None" if kappa is None else num_key(kappa, strict=False))
    else:
        b0 = float(p["B0"])
        rule = _b0_rule(b0, bl0a)
    return {"B0_rule": rule, "B0_usd": b0, "bl0a_usd": bl0a, "gamma": float(p["gamma"]), "kappa": kappa}


def info_class_reported(info_class: str, b0_rule: str) -> str:
    """The class that the summaries and Table III's caption use (§2.2): `info_class` (registry.info_class of the run,
    unchanged) plus ' + a-priori BL0a' when B0_rule is a share of BL0a ('<share>*BL0a'), else `info_class`."""
    if str(b0_rule).endswith("*BL0a") and "a-priori BL0a" not in info_class:
        return info_class + INFO_BL0A
    return info_class


# ---------------------------------------------------------------- certificates (§2.2, §2.6)
def certify(res, inst) -> tuple[dict, str]:
    """(certificate, case) of one A8 run or sub-run (§2.2): q44_study.certificate(res, inst, res.metrics['policy'],
    core_exact=False), as e1.py calls it, and Theorem W's case by e1.cert_case: 'W(a)' (no abort), 'W(b)' (an abort
    after which S follows FB at every slot: proven), 'W(c)' (another abort: CONJECTURE, counted) or 'unavailable'.
    The certificate keeps its per-slot list ALG_per_slot (a8_record leaves it out of the run record)."""
    from . import q44_study as q44
    from .e1 import cert_case
    cert = q44.certificate(res, inst, res.metrics.get("policy") or {}, core_exact=False)
    return cert, cert_case(cert)


def a8_record(res, inst, params: Mapping, information: str = "I1", *, per_slot: bool = False) -> dict:
    """The fields of §2.6 that every A8 entry of MS4 carries, from the run `res` on `inst` with the parameters
    `params` that the driver passed (sublet_params, theory_params or a sweep share): allowance_record's B0_rule,
    B0_usd, bl0a_usd, gamma and kappa; B0_report_usd (the B0 that A8 resolved, its report field 'B0', ratchet.B0);
    info_class (registry.info_class('A8', params, information), unchanged) and info_class_reported (§2.2); the
    certificate (certify; without ALG_per_slot unless per_slot) and certificate_case; t_a and aborted (A8's
    report)."""
    from ..algos import registry
    rec = allowance_record(params, inst)
    rep = res.metrics.get("policy") or {}
    cert, case = certify(res, inst)
    if not per_slot:
        cert = {k: v for k, v in cert.items() if k not in CERT_PER_SLOT}
    info = registry.info_class("A8", dict(params or {}), information)
    rec.update(B0_report_usd=rep.get("B0"), info_class=info,
               info_class_reported=info_class_reported(info, rec["B0_rule"]), certificate=cert,
               certificate_case=case, t_a=rep.get("t_a"), aborted=rep.get("aborted"))
    return rec


def count_certificates(records: Iterable[Mapping]) -> dict:
    """The certificate counts of a summary (§2.6) over A8 records (a8_record, or any mapping with 'certificate' and
    'certificate_case'): n, held (certificates with held true), by_case {case: {'runs', 'held'}} over CASES, and
    failures, the runs of Theorem W's proven cases (W(a), W(b)) whose certificate is not held (a bug, checks E3-5,
    E5-5, E7-1); W(c) runs are counted under by_case."""
    by = {c: {"runs": 0, "held": 0} for c in CASES}
    n = held = fail = 0
    for r in records:
        cert = r.get("certificate") or {}
        case = r.get("certificate_case") or "unavailable"
        if case not in by:
            raise ValueError(f"count_certificates: unknown case {case!r}")
        ok = cert.get("held") is True
        n += 1
        held += ok
        by[case]["runs"] += 1
        by[case]["held"] += ok
        fail += case in PROVEN_CASES and not ok
    return {"n": n, "held": held, "by_case": by, "failures": fail}


def need_params(inner: str = "BL5") -> dict:
    """A8's parameters of the allowance-need run (§3.3, §4.4; measurement 8): {'inner': inner, 'gamma': 1.0,
    'kappa': None, 'B0': NEED_B0}. The allowance never binds, so A8 never aborts and executes its inner policy's
    actions unchanged; allowance_need reads the need from the run's guard series."""
    from ..algos.registry import A8_INNER_IDS
    if inner not in A8_INNER_IDS:
        raise ValueError(f"need_params: A8 guards one of {list(A8_INNER_IDS)}, not {inner!r}")
    return {"inner": str(inner), "gamma": GAMMA, "kappa": None, "B0": NEED_B0}


def allowance_need(res, gamma: float = GAMMA, b0: Optional[float] = None) -> dict:
    """The smallest constant allowance (kappa None) with which A8 at `gamma` does not abort on the trajectory of the
    A8 run `res` (§3.3, §4.4; measurement 8's need_constant_allowance_usd): need = max(0, max_t [a-hat(t) + R(t) -
    gamma C_S(t)]) over the guard's slots (the report's guard.a_hat, guard.reserve and guard.C_S). Until an abort the
    trajectories of the inner policy and of the safe expert depend neither on gamma nor on the allowance, so one run
    with need_params serves every gamma and constant B0. With `b0` (a constant allowance in USD) also B0_usd,
    margin_usd = b0 - need and t_a_at_B0, the first slot at which the guard with B(t) = b0 aborts (the test of
    guard.Ratchet.step: a-hat(t) + R(t) > gamma C_S(t) + b0 + GUARD_TOL max(1, |gamma C_S(t) + b0|)), None if it
    does not. Returns {'need_usd', 'excess_max_usd' (the maximum before the clip at 0), 'need_slot' (its slot),
    'gamma', 'n_slots'[, 'B0_usd', 'margin_usd', 't_a_at_B0']}. ValueError for a run without a guard report or one
    that aborted."""
    from ..algos.guard import GUARD_TOL
    rep = res.metrics.get("policy") or {}
    g = rep.get("guard")
    if not isinstance(g, Mapping) or not g.get("slots"):
        raise ValueError("allowance_need: the run has no A8 guard report")
    if g.get("t_a") is not None or rep.get("aborted"):
        raise ValueError(f"allowance_need: the run aborted at slot {g.get('t_a')}; run A8 with need_params")
    gam = float(gamma)
    exc = [a + r - gam * c for a, r, c in zip(g["a_hat"], g["reserve"], g["C_S"])]
    i = max(range(len(exc)), key=exc.__getitem__)
    out = {"need_usd": max(0.0, float(exc[i])), "excess_max_usd": float(exc[i]), "need_slot": int(g["slots"][i]),
           "gamma": gam, "n_slots": len(exc)}
    if b0 is not None:
        b = float(b0)
        t_a = next((int(t) for t, a, r, c in zip(g["slots"], g["a_hat"], g["reserve"], g["C_S"])
                    if a + r > gam * c + b + GUARD_TOL * max(1.0, abs(gam * c + b))), None)
        out.update(B0_usd=b, margin_usd=b - out["need_usd"], t_a_at_B0=t_a)
    return out


def siloed_run(inst, spec: Mapping, model, ecfg, lender_seed: int, policy_seed: int,
               params_of: Optional[Callable] = None) -> dict:
    """A siloed run (§2.1, §2.2, §4.5; Q41(a)) through drivers.siloed.run_siloed on the merge-false instance `inst`,
    with a factory that builds each sub-policy by drivers.run.make_policy from its own sub-instance (restrict_clients)
    and the parameters params_of(sub) (Sublet siloed: sublet_params, so that each sub-run has its own B0; None: the
    spec's parameters, for BL2 and SILOED{A6}, as drivers/run.run builds them). The inner id is the spec's SILOED
    inner id, or the spec's policy id itself (BL2, or an A8 or A6 spec run per borrower). The same seeds in every
    sub-run; the costs are summed. Returns run_siloed's dict (components summed, per_slot, borrowers, clients,
    results, instances, invariant_failures, seeds) plus inner_id, total, sub_runs (per sub-run: borrower, clients,
    params, resolved_params, info_class, total, components, n_invariant_failures, gpu_only_lease_slots,
    plan_class_p1 and, for A8, the fields of a8_record: one certificate and allowance record per sub-run) and
    certificates (count_certificates over the sub-runs; None unless the inner id is A8)."""
    from ..algos import registry
    from ..drivers.run import make_policy
    from ..drivers.siloed import run_siloed
    from . import q44_study as q44
    pid, params = spec["policy"]["id"], dict(spec["policy"].get("params") or {})
    if pid == "SILOED":
        iid, ipar = registry.inner_of(pid, params)
    else:
        iid, ipar = pid, params
    built: list = []

    def factory(sub):
        p = copy.deepcopy(ipar) if params_of is None else dict(params_of(sub))
        pol = make_policy({**spec, "policy": {"id": iid, "params": p}}, sub)
        built.append((p, pol))
        return pol
    d = run_siloed(inst, factory, model, ecfg, lender_seed=int(lender_seed), policy_seed=int(policy_seed))
    subs = []
    for (b, idx, res, sub), (p, pol) in zip(zip(d["borrowers"], d["clients"], d["results"], d["instances"]), built):
        rp = {**p, **(pol.params() or {})} if callable(getattr(pol, "params", None)) else dict(p)
        row = {"borrower": b, "clients": list(idx), "params": p, "resolved_params": rp,
               "info_class": registry.info_class(iid, rp, model.information),
               "total": float(res.components["total"]), "components": {k: float(v) for k, v in res.components.items()},
               "n_invariant_failures": len(res.invariant_failures),
               "gpu_only_lease_slots": int(res.metrics.get("gpu_only_lease_slots", 0)),
               "plan_class_p1": bool(q44.plan_class_p1(res, sub))}
        if iid == "A8":
            row.update(a8_record(res, sub, p, model.information))
        subs.append(row)
    return {**d, "inner_id": iid, "total": float(d["components"].get("total", 0.0)), "sub_runs": subs,
            "certificates": count_certificates(subs) if iid == "A8" else None}


# ---------------------------------------------------------------- both accountings (Q32, M2; §2.1, §2.6)
def references(inst) -> dict:
    """The references of a summary's meta (§2.1, §2.6, §3.10): bl0a_usd (e6.bl0a_all), own_capacity_usd
    (provision.own_capacity_usd), bl0a_total_usd (BL0a in total accounting, BL0a plus own capacity), bl0b_overflow_usd
    and bl0b_total_usd (provision.bl0b_usd in both accountings) and committed_price_usd_per_gpu_h
    (provision.committed_price, the a_commit of both). A value that provision cannot give (an instance without
    borrower_stats, as explicit and from_core instances) is null with a '<key>_note' (§2.6)."""
    from ..drivers import provision
    from .e6 import bl0a_all
    out = {"bl0a_usd": float(bl0a_all(inst))}
    for k, fn in (("own_capacity_usd", lambda: provision.own_capacity_usd(inst)),
                  ("bl0b_overflow_usd", lambda: provision.bl0b_usd(inst, accounting="overflow")),
                  ("bl0b_total_usd", lambda: provision.bl0b_usd(inst, accounting="total")),
                  ("committed_price_usd_per_gpu_h", lambda: provision.committed_price(inst))):
        try:
            out[k] = float(fn())
        except ValueError as err:
            put(out, k, None, str(err))
    own = out["own_capacity_usd"]
    put(out, "bl0a_total_usd", None if own is None else out["bl0a_usd"] + own, out.get("own_capacity_usd_note"))
    return out


def _ratio(d: dict, key: str, a: Optional[float], b: Optional[float], what: str) -> None:
    if a is None or b is None:
        put(d, key, None, f"{what} unavailable")
    elif not b > 0:
        put(d, key, None, f"{what}: denominator {b!r} is not positive")
    else:
        d[key] = float(a) / float(b)


def accountings(overflow_usd: float, inst, refs: Optional[Mapping] = None) -> dict:
    """A run's cost in both accountings of Q32 (§2.1, §2.6; M2), the fields of measurement 1's accountings block:
    overflow_usd (the ledger total), total_usd = overflow_usd + own_capacity_usd(inst), overflow_over_bl0a,
    total_over_bl0a (BL0a plus own capacity in the denominator), own_share_of_total (own capacity over total_usd),
    overflow_over_bl0b and total_over_bl0b (BL0b in the same accounting). `refs` (references(inst)) saves recomputing
    the references for many runs of one instance. A value that cannot be computed (no own capacity, a zero
    denominator) is null with a '<key>_note' (§2.6)."""
    x = _finite(overflow_usd)
    if x is None:
        raise ValueError(f"accountings: the overflow cost must be a finite number, got {overflow_usd!r}")
    r = dict(refs) if refs is not None else references(inst)
    own, b0 = r.get("own_capacity_usd"), r.get("bl0a_usd")
    tot = None if own is None else x + own
    out = {"overflow_usd": x}
    put(out, "total_usd", tot, r.get("own_capacity_usd_note") or "own capacity unavailable")
    _ratio(out, "overflow_over_bl0a", x, b0, "BL0a")
    _ratio(out, "total_over_bl0a", tot, None if own is None or b0 is None else b0 + own, "BL0a + own capacity")
    _ratio(out, "own_share_of_total", own, tot, "own capacity")
    _ratio(out, "overflow_over_bl0b", x, r.get("bl0b_overflow_usd"), "BL0b (overflow accounting)")
    _ratio(out, "total_over_bl0b", tot, r.get("bl0b_total_usd"), "BL0b (total accounting)")
    return out


# ---------------------------------------------------------------- W0 (note §5.5; §2.1, §3.9)
def _values(cell) -> list:
    if isinstance(cell, Mapping):
        return list(cell.values())
    if isinstance(cell, (list, tuple)):
        return list(cell)
    raise TypeError(f"w0: a cell is a {{seed: r0}} map or a list of r0 values, got {type(cell).__name__}")


def stress_modes() -> tuple[str, ...]:
    """The stress modes of W0 (note §5.5, §3.9): the modes of q44_study.MODES with stress true, in its order
    (L-eg, L-ss, L-iid-0.05, L-iid-0.2, L-co)."""
    from . import q44_study as q44
    return tuple(m for m, d in q44.MODES.items() if d.get("stress"))


def w0(r0_by_mode_cell_seed: Mapping, expected: Optional[Iterable[str]] = None) -> dict:
    """Note §5.5's W0 of one policy (§2.1, §3.9): per stress mode the mean of r0 = cost / BL0a over the policy seeds
    of each cell, the median over the cells; W0 = the largest of these over the modes, with the mode that attains it
    (the first in the given order on a tie). With E7's one cell (alignment 1) it is the maximum over the five stress
    modes of the 3-seed mean of r0. Input {mode: {cell: {seed: r0} or [r0, ...]}}; an r0 of None (a run without
    output) is left out and counted. `expected` names the modes that W0 covers: by default every stress mode
    (stress_modes()), else the given ones, each a stress mode. Returns {'value', 'mode', 'seed_range' (the [min, max]
    of r0 over the attaining mode's runs: one cell gives no bootstrap interval, §3.9), 'per_mode' {mode: {'value',
    'n_cells', 'cell_means', 'n_runs', 'n_missing', 'seed_range'}}, 'expected', 'modes_missing'}. An expected mode
    that is absent from the input or has no r0 is listed in modes_missing (its per_mode row in null form) and makes
    value null with a note, keeping 'value_partial', the largest over the other modes, since W0 over fewer modes
    would understate it. A mode key outside `expected` (a misspelled or unknown mode, a mode that is not a stress
    mode as 'L-tr', or a stress mode that `expected` leaves out) raises ValueError, as does an `expected` that names
    a mode that is not a stress mode or no mode."""
    stress = stress_modes()
    want = stress if expected is None else tuple(dict.fromkeys([expected] if isinstance(expected, str)
                                                               else expected))
    if not want or any(m not in stress for m in want):
        raise ValueError(f"w0: expected must name stress modes of q44_study.MODES {list(stress)}, got {list(want)}")
    per, missing = {}, []
    for mode, cells in r0_by_mode_cell_seed.items():
        if mode not in want:
            raise ValueError(f"w0: mode {mode!r} is not one of the expected stress modes {list(want)}")
        if not isinstance(cells, Mapping):
            raise TypeError(f"w0: mode {mode!r} needs a {{cell: r0 values}} map, got {type(cells).__name__}")
        means, runs, n_miss = {}, [], 0
        for cell, vals in cells.items():
            v = []
            for x in _values(vals):
                f = _finite(x)
                if x is not None and f is None:
                    raise ValueError(f"w0: r0 {x!r} of mode {mode!r}, cell {cell!r} is not a finite number")
                if f is None:
                    n_miss += 1
                else:
                    v.append(f)
            if v:
                means[cell] = float(np.mean(v))
                runs += v
        row = {"n_cells": len(means), "cell_means": means, "n_runs": len(runs), "n_missing": n_miss}
        if means:
            row.update(value=float(np.median(list(means.values()))), seed_range=[min(runs), max(runs)])
        else:
            put(row, "value", None, "no r0")
            row["seed_range"] = None
            missing.append(mode)
        per[mode] = row
    for mode in want:
        if mode not in per:
            per[mode] = put({"n_cells": 0, "cell_means": {}, "n_runs": 0, "n_missing": 0}, "value", None,
                            "no runs of this mode")
            per[mode]["seed_range"] = None
            missing.append(mode)
    have = [(m, r["value"]) for m, r in per.items() if r["value"] is not None]
    best = max(have, key=lambda t: t[1]) if have else (None, None)      # max keeps the first of equal values
    out = {"per_mode": per, "expected": list(want), "modes_missing": missing}
    if missing or not have:
        put(out, "value", None, f"modes without r0: {missing}" if missing else "no mode")
        out.update(value_partial=best[1], mode=best[0])
    else:
        out.update(value=best[1], mode=best[0])
    out["seed_range"] = per[best[0]]["seed_range"] if best[0] is not None else None
    return out


# ---------------------------------------------------------------- benchmarks (§2.5, §4.6)
def _empty(rec) -> bool:
    return rec is None or (isinstance(rec, Mapping) and rec.get("empty") is True)


def sum_bench(records: Iterable) -> dict:
    """The sum of per-sub-instance benchmark records (§2.1, §2.5, §4.6), so that ms3_common.bracket applies to E3's
    siloed OPT (bracket(sum_bench(silo records), shared record)): each record is ms3_common.bench_values (or
    lb_record) of one sub-instance, or None (or {'empty': True}) for a sub-instance without overflow, whose OPT is 0
    and needs no MILP. incumbent and LB are the sums over the parts (an empty part adds 0; null with a note if a
    non-empty part has none), exact iff every part is exact (an empty part is), gap the largest gap of the parts,
    grid the parts' common grid (ValueError if two differ). Also n_parts, n_empty, LB_sources (count per source) and
    the indices of the parts without an incumbent or an LB."""
    parts = list(records)
    inc = lb = 0.0
    no_inc, no_lb, gaps, grids, srcs = [], [], [], set(), {}
    exact, n_empty = True, 0
    for i, r in enumerate(parts):
        if _empty(r):
            n_empty += 1
            continue
        if not isinstance(r, Mapping):
            raise TypeError(f"sum_bench: part {i} is a {type(r).__name__}, not a benchmark record")
        v, w = _finite(r.get("incumbent")), _finite(r.get("LB"))
        if v is None:
            no_inc.append(i)
        else:
            inc += v
        if w is None:
            no_lb.append(i)
        else:
            lb += w
            src = str(r.get("LB_source"))
            srcs[src] = srcs.get(src, 0) + 1
        g = _finite(r.get("gap"))
        if g is not None:
            gaps.append(g)
        exact = exact and bool(r.get("exact"))
        if r.get("grid") is not None:
            grids.add(r["grid"])
    if len(grids) > 1:
        raise ValueError(f"sum_bench: parts on different grids {sorted(grids)}")
    out = {"n_parts": len(parts), "n_empty": n_empty, "exact": bool(exact),
           "gap": max(gaps) if gaps else None, "grid": next(iter(grids), None), "LB_sources": srcs,
           "parts_without_incumbent": no_inc, "parts_without_LB": no_lb}
    put(out, "incumbent", None if no_inc else inc, f"parts {no_inc} have no incumbent")
    put(out, "LB", None if no_lb else lb, f"parts {no_lb} have no lower bound")
    if out["gap"] is None:
        out["gap_note"] = "no part with a gap" if len(parts) > n_empty else "every part is empty"
    return out


# ---------------------------------------------------------------- instances (§3.4, §3.7, M1, M22, M35)
def _spec(config: str, policy_id: str, params, overrides: dict, lender_model, name: str, seeds, out: str) -> dict:
    from ..drivers.run import load_run_spec
    return load_run_spec({"schema_version": 1, "name": name, "instance": config, "overrides": overrides,
                          "lender_model": copy.deepcopy(dict(lender_model or {})), "engine": dict(ENGINE),
                          "policy": {"id": policy_id, "params": copy.deepcopy(dict(params or {}))},
                          "seeds": copy.deepcopy(dict(seeds or E7_SEEDS)), "bench": None, "out": out})


def e7_spec(policy_id: str, params: Optional[Mapping] = None, *, mu: float = MU_DEFAULT, horizon_min: int = WEEK_MIN,
            lender_model: Optional[Mapping] = None, overrides: Optional[Mapping] = None, name: str = "e7",
            seeds: Optional[Mapping] = None) -> dict:
    """The validated E7 run spec (§3.4, M35; drivers.run.load_run_spec) on configs/bench_e7f.json, as e6.e6b_spec
    builds E6(b)'s on bench_e7r.json: the driver's overrides time.horizon_min (10080, one week), stranding.
    mu_over_beta_tilde (mu; 1 at the headline, set explicitly) and the extra `overrides` (e.g. routing_overrides(n);
    ValueError if they set the horizon or mu), engine.check_invariants true (the config sets it false, §0 item 5),
    the lender model keys over the config's trace lender (I1, 'sell', 'absorb'; {} for L-tr, mode_lender_model for a
    stress mode) and the policy. The config file stays the memory benchmark's. Seeds (for drivers.run.run; a driver
    builds with build(spec, c) and runs with lender seed c): default config [1], lender 'config', policy [0]."""
    ov = {"time.horizon_min": int(horizon_min), "stranding.mu_over_beta_tilde": float(mu)}
    extra = dict(overrides or {})
    clash = sorted(set(extra) & set(ov))
    if clash:
        raise ValueError(f"e7_spec: pass {clash} as horizon_min and mu, not in overrides")
    ov.update(copy.deepcopy(extra))
    return _spec(E7_CONFIG, policy_id, params, ov, lender_model, name, seeds, "code/sim/out/e7")


def mode_lender_model(mode: str) -> dict:
    """The run spec's lender model of an E7 lender mode (§3.7(d)(f)): {} for 'L-tr' (the config's trace lender, as
    measurements 1 and 8), else q44_study.MODES[mode]['lender_model'] unchanged (M21)."""
    from . import q44_study as q44
    if mode not in q44.MODES:
        raise ValueError(f"mode_lender_model: unknown lender mode {mode!r}; known {list(q44.MODES)}")
    return {} if mode == "L-tr" else copy.deepcopy(q44.MODES[mode]["lender_model"])


def routing_overrides(n: int) -> dict:
    """M1 (§3.7(c); Fig. 4(b); alternative (b), decided on 2026-10-26 after the U19 review): the overrides of n
    cross-region routing links, {'regions.adjacency': ROUTING_LINKS[n]} for n in {0, 2, 3}, and {} for n = 5, the main
    grid's instance (bench_e7f.json has no adjacency key, so the builder uses S7, config.DEFAULT_ADJACENCY). The sets
    are nested subgraphs of S7: none; north_america-south_america and east_asia-south_southeast_asia; plus
    north_america-europe; S7's five links. The builder uses regions.adjacency only for the routing costs (a relaxed
    client may route to a site of an adjacent region at delta = relaxed_routing_cost_over_q x q_j, instance.py), so
    every n has the main grid's five regions, lenders, sites, contracts, clients, demand, Gamma and BL0a; only the
    cross-region arcs differ (measurement 9, allowance_need_ms4_e7_links*.json, cross_region_arcs)."""
    if isinstance(n, bool) or not isinstance(n, (int, np.integer)) or int(n) not in ROUTING_LINKS:
        raise ValueError(f"routing_overrides: n must be one of {sorted(ROUTING_LINKS)}, got {n!r}")
    links = ROUTING_LINKS[int(n)]
    return {} if links is None else {"regions.adjacency": [list(e) for e in links]}


def e7r_h5_overrides(horizon_min: int = DAY_MIN) -> dict:
    """The overrides of the gap reruns on configs/bench_e7r.json (§3.7(e), §3.8; measurement 3's
    e7r_h5_lp_estimate.json `overrides`): time.horizon_min 1440 (one day), the slow grid q44_study.GRIDS['slow']
    (time.fast_slot_min 5), stranding.mu_over_beta_tilde 1 (M34) and Q44's block Q4 substitution H5_OVERRIDES
    (contracts.0 = s5_tau5_H5 in place of s5_tau5_H2, lender_defaults.menu = [s5_tau5_H5, s5_tau5_H60,
    s5_tau60_H0]). `horizon_min` is for reduced runs and tests only."""
    from . import q44_study as q44
    return {"time.horizon_min": int(horizon_min), **copy.deepcopy(q44.GRIDS["slow"]),
            "stranding.mu_over_beta_tilde": 1.0, **copy.deepcopy(H5_OVERRIDES)}


def e7r_h5_spec(policy_id: str, params: Optional[Mapping] = None, *, horizon_min: int = DAY_MIN, name: str = "e7_gap",
                seeds: Optional[Mapping] = None) -> dict:
    """The validated run spec of a gap rerun (§3.7(e)): configs/bench_e7r.json with e7r_h5_overrides(), the config's
    trace lender (I1, 'sell', 'absorb'), engine.check_invariants true and the policy; gap_instance builds its
    instance, and the drivers build the policy from it (make_policy, which reads the spec's lender model)."""
    return _spec(E7R_CONFIG, policy_id, params, e7r_h5_overrides(horizon_min), {}, name, seeds, "code/sim/out/e7/gap")


def gap_instance(c: int, *, horizon_min: int = DAY_MIN) -> tuple:
    """(inst, model, ecfg, info) of the gap reruns at alignment c (§2.1, §3.7(e), M22): the one builder that both
    e7:gap_run and e7:gap_lp use, so that their q44_study.instance_hash agree (the hash covers borrower_stats). The
    instance is bench_e7r.json with e7r_h5_overrides() at config seed c, whose clients.demand is replaced
    (instance.with_demand) by the first day (minutes 0-1440) of the E7 week instance's demand of the same alignment
    (e7_spec at mu = 1, config seed c), averaged to the rerun's 5-min fast slots, and whose borrower_stats are the
    week instance's, as e6.e6b_instance replaces both (MS3 spec M31) and week_day1 of out/ms4spec/e7r_h5_lp.py did;
    InstanceError if the client lists differ or the fast slots are not nested. info: demand ('e7_week_day1'),
    bl0a_own_demand (BL0a under the rerun instance's own demand), own_demand_sha256, demand_sha256
    (e6.demand_sha256 of the demand used), bl0a_usd (under it), the week's and the rerun's start minute of the week,
    the aggregation, the Gamma notes and the week's overrides."""
    from ..drivers.run import build
    from ..instance import InstanceError, with_demand
    from .e6 import bl0a_all, demand_sha256
    if not 0 < int(horizon_min) <= WEEK_MIN:
        raise ValueError(f"gap_instance: horizon_min must be in (0, {WEEK_MIN}], got {horizon_min!r}")
    inst, model, ecfg = build(e7r_h5_spec("BL0a", {}, horizon_min=horizon_min), int(c))
    own_sha, own_bl0a = demand_sha256(inst), float(bl0a_all(inst))
    wspec = e7_spec("BL0a", {})
    wk = build(wspec, int(c))[0]
    a, b = inst.clients, wk.clients
    if not (np.array_equal(a.llm, b.llm) and a.region == b.region and a.slo_class == b.slo_class
            and a.borrowers == b.borrowers):
        raise InstanceError(f"gap_instance(c = {c}): the E7 week instance's clients differ from the rerun instance's")
    f = inst.grid.fast_min // wk.grid.fast_min
    if f < 1 or f * wk.grid.fast_min != inst.grid.fast_min:
        raise InstanceError(f"gap_instance: fast slots of {inst.grid.fast_min} and {wk.grid.fast_min} min are not "
                            "nested")
    n_fast = inst.grid.T_fast
    d = np.asarray(wk.clients.demand, dtype=np.float64)[:, : n_fast * f].reshape(inst.n, n_fast, f).mean(axis=2)
    inst = dataclasses.replace(with_demand(inst, d), borrower_stats={k: dict(v) for k, v in wk.borrower_stats.items()})
    info = {"demand": "e7_week_day1", "bl0a_own_demand": own_bl0a, "own_demand_sha256": own_sha,
            "demand_sha256": demand_sha256(inst), "bl0a_usd": float(bl0a_all(inst)),
            "week_start_mow": int(wk.grid.start_mow), "rerun_start_mow": int(inst.grid.start_mow),
            "start_mow_equal": bool(wk.grid.start_mow == inst.grid.start_mow),
            "aggregation": f"mean over {f} fast slots of {wk.grid.fast_min} min, first {n_fast * f} min of the week",
            "gamma_note": [n for n in inst.notes if "Gamma" in n],
            "week_gamma_note": [n for n in wk.notes if "Gamma" in n], "week_overrides": dict(wspec["overrides"]),
            "note": "clients.demand = the E7 week instance's first-day demand (instance.with_demand) and "
                    "borrower_stats = the week instance's, as e6.e6b_instance replaces both (M22)"}
    return inst, model, ecfg, info


__all__ = ["B0_SHARE", "B0_RULE", "THEORY_RULE", "INFO_CLASS_REPORTED", "CASES", "ROUTING_LINKS", "H5_OVERRIDES",
           "sublet_params", "theory_params", "allowance_record", "info_class_reported", "certify", "a8_record",
           "count_certificates", "need_params", "allowance_need", "siloed_run", "references", "accountings",
           "stress_modes", "w0", "sum_bench", "e7_spec", "mode_lender_model", "routing_overrides", "e7r_h5_overrides",
           "e7r_h5_spec", "gap_instance"]
