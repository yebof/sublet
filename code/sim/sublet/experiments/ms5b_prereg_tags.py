"""MS5b pre-registration: the resolved policy table of the confirmation (design/sublet_v2.md §3, §4.3, §4.4).

Prints Markdown on standard output, in three parts:

  1. Jobs: per confirmation part of e7h.py (main, seeds, second, e3, fam, grid; the full job lists of e7h.jobs, never
     the reduced ones) the number of jobs by kind and by pool ('pool', 'milp', 'alone') and the number of runs that
     the jobs owe (e7h.expected_runs).
  2. Lender modes: every lender mode of the week parts (main, seeds, second, grid) with the run spec's lender model
     (ms5b_common.mode_lender_model), the instance overrides (ms5b_common.mode_overrides) and the lender model that the
     drivers resolve on the confirmation's first week (drivers.run._lender_model over bench_e7f config seed 301).
  3. Policies: every tag of ms5b_common.TAGS that a confirmation part runs, with its registry id, the parts and job
     kinds that run it, its parameters as ms5b_common.TAGS states them, its information model and class, the driver
     inputs it receives, and all of its parameters resolved, defaults included.

How the parameters are resolved. Each policy is built as the drivers build it, and its resolved parameters are read
from the policy object as e7.run_entry records them: {**tag parameters, **policy.params()}. A tag that a week, gap,
E5, E3 or Q44 job runs is built on the confirmation's first week instance: bench_e7f config seed 301 (lender seed 301),
lender mode L-tr, policy seed 0, built as e7h.run_week builds it (ms5b_common.week_spec of BL0a, drivers.run.build),
with ms5b_common.tag_params(tag, instance), ms5b_common.week_spec and drivers.run.make_policy, which passes the driver
inputs (drivers.run.driver_inputs) and, for A8 and A8P, the lender's sale rule on_unavailable. A tag that only the fam
part runs is built on the first instance of e7h's fam job list (q44_study.family_core and instance.from_core, with
drivers.run.make_policy on {'policy': {...}} as e7h.run_fam does). A tag that both kinds of job run is built on both
instances and its resolved parameters must be equal (the script stops otherwise). Where policy.params() leaves a key
out while it holds its default (the baselines' QUIET_KEYS, design/sublet_v2.md §8.4; A8P's 'allowance' at 'alg1'),
the class's PARAMS default is filled in and the key is listed in the column 'filled from PARAMS'; for A8 and A8P the
same is done for the inner policy's parameters. The only instance-dependent tag parameter is Sublet-MS4's B0 =
0.1 BL0a of the run's own instance (ms4_common.sublet_params); its value on week 301 is printed, and every other
instance takes its own.

The policy tables of design/sublet_v2_prereg.md §3, and its job and lender-mode tables in §4, are this script's output
at the freeze commit, the commit that first versions the pre-registration.

Run from code/sim, under a memory cap (it builds one week instance and one family instance; no simulation):
  python -m sublet.experiments.ms5b_prereg_tags
"""
from __future__ import annotations

import copy
import json
import os
import sys
from collections import Counter

FIRST_WEEK = 301                     # §4.4(a): the confirmation's first week (bench_e7f config seed = lender seed)
POLICY_SEED = 0


def _fmt(v) -> str:
    """Compact JSON of a parameter dict (key order kept; numpy scalars and tuples as JSON numbers and lists)."""
    def conv(x):
        if isinstance(x, dict):
            return {str(k): conv(y) for k, y in x.items()}
        if isinstance(x, (list, tuple)):
            return [conv(y) for y in x]
        if hasattr(x, "item") and callable(x.item):
            return x.item()
        return x
    return json.dumps(conv(v), separators=(", ", ": "))


def _cell(s: str) -> str:
    return s.replace("|", "\\|")


def _md_table(head: list, rows: list) -> str:
    out = ["| " + " | ".join(head) + " |", "|" + "|".join("---" for _ in head) + "|"]
    out += ["| " + " | ".join(_cell(str(x)) for x in r) + " |" for r in rows]
    return "\n".join(out)


def job_tags(e7h, part: str) -> list:
    """[(job, [(tag, kind label)])] of a confirmation part's full job list."""
    out = []
    for j in e7h.jobs([part]):
        p = j.params
        k = p["kind"]
        if k in ("week", "e5", "gap"):
            names = [(p["tag"], k)]
        elif k == "e3cell":
            names = [(t, f"e3 {m}") for t, m in p["entries"]]
        elif k in ("q44", "fam"):
            names = [(t, k) for t, _s in p["entries"]]
        else:                                        # e3milp, gap_lp: benchmarks, no policy
            names = []
        out.append((j, names))
    return out


def expand(pid: str, rp: dict) -> tuple[dict, list]:
    """(all parameters, keys filled from the class PARAMS): rp over the class's PARAMS; for A8 and A8P also the inner
    policy's parameters over its class's PARAMS (keys of the inner listed as 'inner_params.<key>')."""
    from ..algos import guard, registry
    cls = registry.resolve(pid)
    base = dict(getattr(cls, "PARAMS", None) or {})
    full = {**copy.deepcopy(base), **copy.deepcopy(rp)}
    filled = [k for k in base if k not in rp]
    if pid in registry.GUARD_IDS:
        iid = full["inner"]
        icls = guard.ProjectedGuarded._proj_inner_class(iid) if pid == "A8P" else guard._inner_class(iid)
        ib = dict(getattr(icls, "PARAMS", None) or {})
        ip = dict(full.get("inner_params") or {})
        full["inner_params"] = {**copy.deepcopy(ib), **ip}
        filled += [f"inner_params.{k}" for k in ib if k not in ip]
    return full, filled


def resolve_on(name: str, inst, how: str) -> dict:
    """Build tag `name` on `inst` as the drivers do ('week': e7h.run_week's spec; 'fam': e7h.run_fam's) and return its
    resolved parameters, the full expansion, the driver inputs and the information class."""
    from ..algos import registry
    from ..drivers import run as drun
    from . import ms5b_common as m5
    t = m5.tag(name)
    params = m5.tag_params(name, inst)
    vals, imeta = drun.driver_inputs(t.id, params, inst)
    if how == "week":
        spec = m5.week_spec(t.id, params, mode=m5.TRACE_MODE, c=FIRST_WEEK, horizon_min=m5.WEEK_MIN,
                            seeds=(POLICY_SEED,), name=f"e7h_main_{name}")
        pol = drun.make_policy(spec, inst)
    else:
        pol = drun.make_policy({"policy": {"id": t.id, "params": params}}, inst, inputs=vals)
    rp = {**params, **(pol.params() or {})} if callable(getattr(pol, "params", None)) else dict(params)
    full, filled = expand(t.id, rp)
    inputs = {k: v for k, v in imeta.items() if k != "N_bound_source"}
    if t.id in registry.GUARD_IDS:
        inputs["on_unavailable"] = getattr(pol, "on_unavailable", None)
    return {"params": params, "resolved": rp, "full": full, "filled": filled, "inputs": inputs,
            "info_class": registry.info_class(t.id, rp, t.information)}


def main() -> int:
    os.environ["MS3_E7H_REDUCED"] = "0"                 # the full job lists (e7h.design reads it at call time)
    from ..drivers import run as drun
    from .e6 import bl0a_all
    from ..instance import from_core
    import numpy as np
    from . import e7h
    from . import ms5b_common as m5
    from . import q44_study as q44

    # ------------------------------------------------------------ 1. jobs per part
    uses: dict = {}                                     # tag -> {part: set of kind labels}
    job_rows = []
    first_fam = None
    week_kinds = {"week", "e5", "gap", "e3 shared", "e3 siloed", "q44"}
    modes_by_part: dict = {}
    for part in m5.CONF_PARTS:
        jt = job_tags(e7h, part)
        kinds = Counter(j.params["kind"] for j, _ in jt)
        pools = Counter(j.kind for j, _ in jt)
        runs = sum(len(e7h.expected_runs(j)) for j, _ in jt)
        job_rows.append([part, len(jt), ", ".join(f"{k} {n}" for k, n in sorted(kinds.items())),
                         ", ".join(f"{k} {n}" for k, n in sorted(pools.items())), runs])
        for j, names in jt:
            if j.params["kind"] == "week":
                modes_by_part.setdefault(part, [])
                for m in j.params["modes"]:
                    if m not in modes_by_part[part]:
                        modes_by_part[part].append(m)
            if j.params["kind"] == "fam" and first_fam is None:
                first_fam = j
            for t, lab in names:
                uses.setdefault(t, {}).setdefault(part, set()).add(lab)
    print("### Jobs per confirmation part (e7h.jobs, full lists)\n")
    print(_md_table(["part", "jobs", "jobs by kind", "jobs by pool", "runs owed"], job_rows))
    print()

    # ------------------------------------------------------------ the first week instance (as e7h.run_week builds it)
    spec0 = m5.week_spec("BL0a", {}, mode=m5.TRACE_MODE, c=FIRST_WEEK, horizon_min=m5.WEEK_MIN,
                         seeds=(POLICY_SEED,), name="e7h_build")
    inst, _model, _ecfg = drun.build(spec0, FIRST_WEEK)

    # ------------------------------------------------------------ 2. lender modes of the week parts
    mode_rows = []
    all_modes = []
    for part in ("main", "seeds", "second", "grid"):
        for m in modes_by_part.get(part, []):
            if m not in all_modes:
                all_modes.append(m)
    for m in all_modes:
        sp = m5.week_spec("BL0a", {}, mode=m, c=FIRST_WEEK, horizon_min=m5.WEEK_MIN, seeds=(POLICY_SEED,),
                          name="e7h_build")
        lm = drun._lender_model(sp, inst)
        parts = [p for p in ("main", "seeds", "second", "grid") if m in modes_by_part.get(p, [])]
        mode_rows.append([m, _fmt(m5.mode_lender_model(m)), _fmt(m5.mode_overrides(m)),
                          f"schedule {lm.schedule}, params {_fmt(dict(lm.params or {}))}, on_unavailable "
                          f"{lm.on_unavailable}, violations {lm.violations}, information {lm.information}",
                          ", ".join(parts)])
    print("### Lender modes of the week parts (bench_e7f config seed 301)\n")
    print(_md_table(["mode", "run spec lender_model", "overrides", "resolved lender model", "parts"], mode_rows))
    print()

    # ------------------------------------------------------------ the first family instance (as e7h.run_fam builds it)
    fam_inst = None
    if first_fam is not None:
        I, _F, _desc = q44.family_core(first_fam.params["family"], first_fam.params["values"])
        zero = [np.zeros(0, dtype=np.int64)] * int(I.a.shape[0])
        fam_inst, _ = from_core(I, zero)

    # ------------------------------------------------------------ 3. policies
    order = [t for t in m5.TAGS if t in uses]
    rows_a, rows_b = [], []
    notes = []
    for name in order:
        t = m5.tag(name)
        kinds = set().union(*uses[name].values())
        on_week = bool(kinds & week_kinds)
        on_fam = "fam" in kinds
        res = resolve_on(name, inst, "week") if on_week else None
        if on_fam:
            rf = resolve_on(name, fam_inst, "fam")
            if res is None:
                res = rf
            elif res["full"] != rf["full"]:
                print(f"ERROR: tag {name}: resolved parameters differ between the week and the family instance:\n"
                      f"  week {_fmt(res['full'])}\n  fam  {_fmt(rf['full'])}", file=sys.stderr)
                return 1
        where = (f"bench_e7f c{FIRST_WEEK}, L-tr" if on_week else
                 f"family {first_fam.params['inst']} ({first_fam.params['mode']})")
        if on_week and on_fam:
            where += f"; equal on family {first_fam.params['inst']}"
        parts = "; ".join(f"{p} ({', '.join(sorted(k))})" for p, k in uses[name].items())
        tp = m5.tag_params_text(name)
        rows_a.append([name, t.id, t.kind, parts, tp if isinstance(tp, str) else _fmt(tp), t.information,
                       res["info_class"]])
        rows_b.append([name, f"`{_fmt(res['full'])}`", ", ".join(res["filled"]) or "none",
                       _fmt(res["inputs"]) if res["inputs"] else "none", where])
        if t.params == "sublet_ms4":
            notes.append(f"Sublet-MS4 on week {FIRST_WEEK}: BL0a = {float(bl0a_all(inst))!r} USD, B0 = "
                         f"{float(res['resolved']['B0'])!r} USD (0.1 BL0a, {m5.PARAM_RULE_TEXT['sublet_ms4']}; "
                         f"every other instance, siloed sub-instance, E5, gap and Q44 instance takes 0.1 of its own "
                         f"BL0a).")
    print("### Policies of the confirmation: tags, ids and parts\n")
    print(_md_table(["tag", "registry id", "kind", "parts (job kinds)", "tag parameters (ms5b_common.TAGS)",
                     "information", "information class"], rows_a))
    print()
    print("### Policies of the confirmation: all parameters resolved\n")
    print(_md_table(["tag", "resolved parameters, defaults included", "filled from PARAMS",
                     "driver inputs on that instance", "built on"], rows_b))
    print()
    for n in notes:
        print(n)
        print()
    print(f"Families: the first instance of the fam part is {first_fam.params['inst']} under "
          f"{first_fam.params['mode']}." if first_fam is not None else "Families: no fam job.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
