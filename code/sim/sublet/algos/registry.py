"""Policy registry (design/sim_spec_ms2.md §4.2).

Each policy id maps to a lazy 'module:attr' target, a runner and an information class (§2.3).
Targets are resolved with importlib only when a run needs them (`resolve`), so importing this
module imports no policy module (§2.2). The runner selects what `drivers/run.py::run` does with
an id: 'simulate' (an engine run of a Policy), 'siloed' (per-borrower sub-instance runs through
`drivers/siloed.py`), 'analytic' (BL0b, no engine run) or 'bench' (BL8, only through the run
spec's `bench` field). Driver inputs (`N_bound`, `pred_cols`, `pred_demand`, `future_demand`) are
computed by `drivers/run.py::make_policy`; `needed_inputs` says which ones a parameter set needs.

Q44 additions (design/q44_practical_sublet.md §6.1 item 5): A7, practical Sublet (A6 with the PS
settings of §2.1), and A8, the guarded policy of §3.10 around an inner id of A8_INNER_IDS. A8 is a
wrapper with its own rules: it is kept out of WRAPPERS and INNER_IDS (so that the checks of BL6 and
BL7 stay unchanged), receives its own `N_bound` when S_rbar = 'theory' and its safe expert contains R
(safe 'fb+pd' or 'pd'; guard.Guarded needs N exactly then) and the inner's driver inputs in
`inner_params`; drivers/run.py also passes it the run's lender option `on_unavailable` (not a driver input of
INPUTS: it comes from the lender model, not from the instance). Its default test is 'T0g' (decision of
2026-10-17, design/q44_practical_sublet.md §8.11).

MS5b additions (design/sublet_v2.md §8.1 C34): A9, notice-aware critical-ratio renting (§2.2), and A8P, the
projected guard (§2.4, class guard.ProjectedGuarded) around an inner id of A8P_INNER_IDS (A8_INNER_IDS and A9;
inner default 'A9'). Both rows are in MS5B, which `entry` reads after REGISTRY: POLICY_IDS stays the table of §4.2
with the Q44 rows, which tests/test_run_spec.py::test_registry_complete and
tests/test_policy_isolation.py::test_policy_registry_cases_cover_simulate_runner pin and which must pass unchanged
(design/sublet_v2.md §8.2, §8.3). A8P is A8 in inner_of, a8_own_inputs, needed_inputs and info_class (its own
entry's defaults), and in drivers/run.py's special cases of A8 (C35); A8's rows and A8_INNER_IDS are unchanged.

MS7 additions (design/ms7/plan.md X4, C54): A9P, the protected-only critical-ratio renter (algos/a9p.py), and MPC, the
receding-horizon LP baseline (baselines/mpc.py; `future_demand` iff forecast = 'oracle', information class
'lookahead-<W>min' then). Both rows are in MS7, which `entry` reads after MS5B; POLICY_IDS, MS5B and the guards' inner
ids are unchanged.

MS8 addition (design/ms8/plan.md D2, X6): CAP, the naive spend cap around an inner id of CAP_INNER_IDS (A9, BL1, BL5;
algos/budget_cap.py, a labeled baseline). Its row is in MS8, which `entry` reads after MS7; POLICY_IDS, MS5B, MS7 and
the guards' inner ids are unchanged, and CAP is not in inner_of, needed_inputs or info_class's special cases (its inner
ids need no driver input; its class is the entry's, online-I1).

This module imports only the standard library (policy isolation, §2.2): it raises KeyError and
ValueError, which the driver turns into ConfigError.
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import Optional

RUNNERS = ("simulate", "siloed", "analytic", "bench")
INPUTS = ("N_bound", "pred_cols", "pred_demand", "future_demand")


@dataclass(frozen=True)
class Entry:
    """One registry row of §4.2."""
    id: str
    target: str                             # 'module:attr', resolved lazily
    runner: str                             # one of RUNNERS
    info: str                               # information class at the default parameters ('inner': as inner)
    policy_class: bool = True               # target is a Policy class (make_policy builds it)
    params: Optional[tuple[str, ...]] = None    # parameter names when the target has no PARAMS; None: target.PARAMS
    defaults: tuple[tuple[str, object], ...] = ()   # table defaults of the parameters that select inputs or the class
    inputs: tuple[str, ...] = ()            # driver inputs the id can receive (§4.2, last column)

    def default(self, name: str):
        return dict(self.defaults).get(name)


_A2_DEF = (("rbar", 1),)

REGISTRY: dict[str, Entry] = {e.id: e for e in (
    Entry("A1", "sublet.algos.a1:A1", "simulate", "online-I1"),
    Entry("A2", "sublet.algos.a2:A2", "simulate", "online-I1", defaults=_A2_DEF, inputs=("N_bound",)),
    Entry("A3", "sublet.algos.a3:A3", "simulate", "online-I1", defaults=_A2_DEF, inputs=("N_bound",)),
    Entry("A4", "sublet.algos.a4:A4", "simulate", "online-I2", defaults=_A2_DEF, inputs=("N_bound",)),
    Entry("A5", "sublet.algos.a5:A5", "simulate", "online-I1", defaults=(("R_rbar", 1),),
          inputs=("pred_cols", "N_bound")),
    Entry("A6", "sublet.algos.a6:A6", "simulate", "online-I1",
          defaults=(("variant", "practical"), ("predictions", False)),
          inputs=("N_bound", "pred_cols", "pred_demand")),
    Entry("RR_RENEW", "sublet.algos.family:RRRenew", "simulate", "online-I1"),
    Entry("MARKING", "sublet.algos.family:Marking", "simulate", "online-I2"),
    Entry("BL0a", "sublet.policies.trivial:AlwaysFallback", "simulate", "online-I1"),
    Entry("BL0b", "sublet.drivers.provision:bl0b_usd", "analytic", "hindsight-reference", policy_class=False,
          params=("a_commit", "accounting")),
    Entry("BL1", "sublet.baselines.greedy:GreedyLease", "simulate", "online-I1"),
    Entry("BL2", "sublet.baselines.ski:SkiRental", "siloed", "online-I1"),
    Entry("BL3", "sublet.baselines.spothedge:SpotHedgeStyle", "simulate", "online-I1"),
    Entry("BL4", "sublet.baselines.cocar:CoCaRStyle", "simulate", "online-I1",
          defaults=(("demand", "previous"), ("window_min", 60)), inputs=("future_demand",)),
    Entry("BL5", "sublet.baselines.retrorenting:RetroRentingStyle", "simulate", "online-I1"),
    Entry("BL6", "sublet.baselines.wrappers:NoticeOblivious", "simulate", "inner", defaults=(("inner", "A1"),),
          inputs=INPUTS),
    Entry("BL7", "sublet.baselines.wrappers:RevocableOnly", "simulate", "inner", defaults=(("inner", "A1"),),
          inputs=INPUTS),
    Entry("BL8", "sublet.drivers.bench:bench_for", "bench", "offline", policy_class=False, params=()),
    Entry("SILOED", "sublet.drivers.siloed:run_siloed", "siloed", "inner", policy_class=False,
          params=("inner", "inner_params"), inputs=INPUTS),
    # Q44 (design/q44_practical_sublet.md §6.1 item 5): practical Sublet and the guarded policy
    Entry("A7", "sublet.algos.a7:PracticalSublet", "simulate", "online-I1",
          defaults=(("variant", "practical"), ("predictions", False)),
          inputs=("N_bound", "pred_cols", "pred_demand")),
    Entry("A8", "sublet.algos.guard:Guarded", "simulate", "inner",
          defaults=(("inner", "A7"), ("S_rbar", "theory"), ("safe", "fb+pd"), ("test", "T0g")), inputs=INPUTS),
)}

# MS5b (design/sublet_v2.md §8.1 C34): A9 and the projected guard A8P, kept out of POLICY_IDS (module docstring)
MS5B: dict[str, Entry] = {e.id: e for e in (
    Entry("A9", "sublet.algos.a9:NoticeCriticalRatio", "simulate", "online-I1"),
    Entry("A8P", "sublet.algos.guard:ProjectedGuarded", "simulate", "inner",
          defaults=(("inner", "A9"), ("S_rbar", "theory"), ("safe", "fb+pd"), ("test", "T0g"), ("project", True)),
          inputs=INPUTS),
)}

# MS7 (design/ms7/plan.md X4, C54): the protected-only renter and the MPC baseline, kept out of POLICY_IDS and MS5B
MS7: dict[str, Entry] = {e.id: e for e in (
    Entry("A9P", "sublet.algos.a9p:ProtectedOnly", "simulate", "online-I1"),
    Entry("MPC", "sublet.baselines.mpc:RecedingLP", "simulate", "online-I1",
          defaults=(("forecast", "persistence"), ("window_min", 60)), inputs=("future_demand",)),
)}

# MS8 (design/ms8/plan.md D2): the naive spend cap, kept out of POLICY_IDS, MS5B and MS7
MS8: dict[str, Entry] = {e.id: e for e in (
    Entry("CAP", "sublet.algos.budget_cap:BudgetCapped", "simulate", "online-I1",
          defaults=(("inner", "A9"), ("X", "lb"), ("count", "paid"), ("on_bind", "stop"))),
)}

# Policies of the MS1 package that are not in §4.2, runnable through a run spec for tests and
# replays: FixedPlan takes `plan`, a list of PlannedLease fields (objects or lists).
EXTRA: dict[str, Entry] = {e.id: e for e in (
    Entry("FIXED_PLAN", "sublet.policies.trivial:FixedPlan", "simulate", "offline", params=("plan",)),
)}

POLICY_IDS = tuple(REGISTRY)
MS5B_IDS = tuple(MS5B)
MS7_IDS = tuple(MS7)
MS8_IDS = tuple(MS8)
WRAPPERS = ("BL6", "BL7")      # policy classes around an inner id (`inner`, `inner_params`)
INNER_IDS = ("A1", "A2", "A6")     # inner ids of BL6 and BL7 (§15.8)
A8_INNER_IDS = ("A7", "A3", "A6", "BL1", "BL5")   # inner ids of A8 (Q44 note §3.10, §6.1 item 5)
A8P_INNER_IDS = A8_INNER_IDS + ("A9",)          # inner ids of A8P (design/sublet_v2.md §2.4; guard.PROJ_INNER_IDS)
GUARD_IDS = ("A8", "A8P")                       # the guarded ids, with A8's rules in this module and drivers/run.py
CAP_INNER_IDS = ("A9", "BL1", "BL5")            # inner ids of CAP (MS8; budget_cap.CAP_INNER_IDS)


def entry(policy_id: str) -> Entry:
    """The registry entry of `policy_id` (§4.2 ids, then MS5B, then MS7, then MS8, then EXTRA); KeyError if unknown."""
    e = (REGISTRY.get(policy_id) or MS5B.get(policy_id) or MS7.get(policy_id) or MS8.get(policy_id)
         or EXTRA.get(policy_id))
    if e is None:
        raise KeyError(f"unknown policy id {policy_id!r}; known: "
                       f"{list(REGISTRY) + list(MS5B) + list(MS7) + list(MS8) + list(EXTRA)}")
    return e


def resolve(policy_id: str):
    """Import the target of `policy_id` and return it (a Policy class or a driver function)."""
    mod, _, attr = entry(policy_id).target.partition(":")
    return getattr(importlib.import_module(mod), attr)


def param_names(policy_id: str) -> Optional[tuple[str, ...]]:
    """The allowed parameter names of `policy_id`: the entry's list, else the keys of the target's
    PARAMS (resolves the target); None if the target declares no PARAMS."""
    e = entry(policy_id)
    if e.params is not None:
        return e.params
    p = getattr(resolve(policy_id), "PARAMS", None)
    return None if p is None else tuple(p)


def _param(e: Entry, params: dict, name: str):
    return params[name] if name in params else e.default(name)


def inner_of(policy_id: str, params: dict) -> Optional[tuple[str, dict]]:
    """(inner id, inner parameters) of BL6, BL7, SILOED, A8 (inner default 'A7') and A8P (inner default 'A9');
    None for other ids."""
    e = entry(policy_id)
    if policy_id not in WRAPPERS and policy_id != "SILOED" and policy_id not in GUARD_IDS:
        return None
    inner = _param(e, params, "inner")
    return inner, dict(params.get("inner_params") or {})


def a8_own_inputs(params: dict, policy_id: str = "A8") -> tuple[str, ...]:
    """The driver inputs of A8 itself (not of its inner id): `N_bound` iff S_rbar = 'theory' and the safe
    expert contains R (safe 'fb+pd', the default, or 'pd'): the a-priori N of R's theory r-bar (C3-T2; Q44
    note §6.1 item 5). With safe = 'fb' R is not built and no N is read (guard.Guarded). policy_id 'A8P'
    applies the same rule with A8P's entry defaults (design/sublet_v2.md §8.1 C34)."""
    if policy_id not in GUARD_IDS:
        raise ValueError(f"a8_own_inputs: one of {list(GUARD_IDS)}, not {policy_id!r}")
    e = entry(policy_id)
    uses_R = _param(e, params, "safe") != "fb"
    return ("N_bound",) if uses_R and _param(e, params, "S_rbar") == "theory" else ()


def needed_inputs(policy_id: str, params: dict) -> tuple[str, ...]:
    """The driver inputs that `make_policy` computes for `policy_id` with `params` (§4.2):
    A2-A4 `N_bound` iff rbar = 'theory'; A5 `pred_cols`, and `N_bound` iff R_rbar = 'theory';
    A6 and A7 `N_bound` iff variant = 'theory', `pred_cols` and `pred_demand` iff predictions, and
    `pred_demand` alone for reaction = 'test_a' without predictions (test (a) of §10 needs the
    predicted demand); BL4 `future_demand` iff demand = 'oracle'; BL6, BL7 and SILOED those of
    their inner id; A8 and A8P their own `N_bound` iff S_rbar = 'theory' with R in their safe expert (safe
    not 'fb') plus those of their inner id (in the order of INPUTS); A9 none; MS7: A9P none, MPC `future_demand`
    iff forecast = 'oracle'."""
    e = entry(policy_id)
    inner = inner_of(policy_id, params)
    if policy_id in GUARD_IDS:
        need = set(a8_own_inputs(params, policy_id)) | set(needed_inputs(*inner))
        return tuple(k for k in INPUTS if k in need)
    if inner is not None:
        return needed_inputs(*inner)
    if policy_id in ("A2", "A3", "A4"):
        return ("N_bound",) if _param(e, params, "rbar") == "theory" else ()
    if policy_id == "A5":
        return ("pred_cols",) + (("N_bound",) if _param(e, params, "R_rbar") == "theory" else ())
    if policy_id in ("A6", "A7"):
        out = ("N_bound",) if _param(e, params, "variant") == "theory" else ()
        if _param(e, params, "predictions"):
            out += ("pred_cols", "pred_demand")
        elif params.get("reaction") == "test_a":
            out += ("pred_demand",)
        return out
    if policy_id == "BL4":
        return ("future_demand",) if _param(e, params, "demand") == "oracle" else ()
    if policy_id == "MPC":            # MS7 C54
        return ("future_demand",) if _param(e, params, "forecast") == "oracle" else ()
    return ()


def info_class(policy_id: str, params: dict, information: str = "I1",
               pred_label: Optional[str] = None) -> str:
    """Information class of a run (§2.3, §4.2): the entry's class at the default parameters, with
    ' + a-priori N' where the theory r-bar uses the driver's N (M6), ' + prediction:<label>' for
    A5 and for A6 and A7 with predictions or with reaction 'test_a', 'online-I2' for A6 and A7 under
    I2, 'lookahead-<W>min' for BL4's oracle and MPC's oracle forecast (MS7), and the inner id's class for BL6, BL7
    and SILOED. A8:
    the inner id's class plus ' + a-priori N' when S_rbar = 'theory' and safe is not 'fb' (Q44 note §6.1
    item 5: the a-priori N of the safe expert's R), so
    info_class('A8', {}) is 'online-I1 + a-priori N'. A8P as A8 with its own defaults (design/sublet_v2.md §2.4:
    info_class('A8P', {}) is 'online-I1 + a-priori N', A9's class plus the a-priori N, with no BL0a)."""
    e = entry(policy_id)
    inner = inner_of(policy_id, params)
    if policy_id in GUARD_IDS:
        cls = info_class(inner[0], inner[1], information, pred_label)
        if a8_own_inputs(params, policy_id) and "a-priori N" not in cls:
            cls += " + a-priori N"
        return cls
    if inner is not None:
        return info_class(inner[0], inner[1], information, pred_label)
    cls = e.info
    pred = " + prediction" + (f":{pred_label}" if pred_label else "")
    if policy_id in ("A2", "A3", "A4") and _param(e, params, "rbar") == "theory":
        cls += " + a-priori N"
    elif policy_id == "A5":
        cls += pred + (" + a-priori N" if _param(e, params, "R_rbar") == "theory" else "")
    elif policy_id in ("A6", "A7"):
        cls = "online-I2" if information == "I2" else "online-I1"
        if _param(e, params, "predictions") or params.get("reaction") == "test_a":
            cls += pred
        if _param(e, params, "variant") == "theory":
            cls += " + a-priori N"
    elif policy_id == "BL4" and _param(e, params, "demand") == "oracle":
        cls = f"lookahead-{int(_param(e, params, 'window_min'))}min"
    elif policy_id == "MPC" and _param(e, params, "forecast") == "oracle":        # MS7 C54
        cls = f"lookahead-{int(_param(e, params, 'window_min'))}min"
    return cls


__all__ = ["Entry", "REGISTRY", "MS5B", "MS7", "MS8", "EXTRA", "POLICY_IDS", "MS5B_IDS", "MS7_IDS", "MS8_IDS",
           "RUNNERS", "INPUTS", "WRAPPERS",
           "INNER_IDS", "A8_INNER_IDS", "A8P_INNER_IDS", "GUARD_IDS", "CAP_INNER_IDS", "entry", "resolve", "param_names", "inner_of",
           "a8_own_inputs", "needed_inputs", "info_class"]
