"""X2: randomized search for counterexamples to T0gBound's soundness and Theorem W(b) (independent checker).

For each case: A8 (test T0g, safe 'fb', wind-down 'adaptive' or 'release', reserve on, B0 = 1e12 so that only
forced aborts trip) around an inner policy on a small rich instance, one reference run and a forced abort at every
slot. Checked from the engine's ledger and the instance only (not from test oracles):
  m(t) = ALG(t) - a_hat(t) <= tol at every executed E-mode slot (soundness of T0gBound, a-hat from the report);
  Phi(u) = sum_{v >= u} (cost(v) - Q(v)) <= budget(u) at t_a (budget = R(t_a - 1) of the reference run) and at every
  later adaptive slot of the wind-down log;
  the final bound of Theorem W(b) with the run's own B (here vacuous) is algebra given these two.
Usage: x2_random_search.py <block> [n_seeds]. With the environment variable AUDIT_WC=1, T0gBound routes G over W^C
(the probe of finding F5, audit_env.route_over_wc; the audit's "X2 patched", block P).
Audit of the full-model guard (design/theory/audit_guard.md); code/sim/audit/, run by run_all.sh, output
code/sim/out/audit_fm/x2_out.txt (blocks A, B, C) and x2p_out.txt (AUDIT_WC=1, block P)."""
import os
import sys
import time
from collections import Counter

import numpy as np

import audit_env  # noqa: F401
from audit_env import TG
from sublet.algos.guard import Guarded
from sublet.engine import EngineConfig, simulate
from sublet.types import Buy, Drain, Load, LenderModel, Release, SetAdmission, Unload

TOL = 1e-9
NO_ABORT = {"B0": 1e12, "kappa": None}

MODELS = {
    "eager": {"schedule": "eager"},
    "trace": {"schedule": "trace"},
    "iid": {"schedule": "iid_step", "params": {"D_slots": 1, "p": 0.3}},
    "adaptive": {"schedule": "adaptive"},
    "safe": {"schedule": "safe_site", "params": {"D_slots": 2, "k": 2, "Phi": None}},
    "corr": {"schedule": "correlated", "params": {"p_sh": 1.0, "groups": "all"}},
    "traceI2": {"schedule": "trace", "information": "I2"},
    "refuse": {"schedule": "trace", "on_unavailable": "refuse"},
    "refuseI2": {"schedule": "trace", "on_unavailable": "refuse", "information": "I2"},
}

# extra time grids beyond the test suite's _RICH: notice 0 (death at the announcement slot's start), phi = 1,
# notice equal to the slow slot, a fast slot that does not divide the notice. tests/test_guard.py took them over as
# _RICH_EXTRA (variants 4-7 of _rich_instance); the audit's scratch version appended them to _RICH itself.
EXTRA = ({"slow": 5, "fast": 5, "horizon": 150, "H": (0, 5), "caps": (3, 3)},
         {"slow": 10, "fast": 2, "horizon": 200, "H": (0, 1), "caps": (4, 4)},
         {"slow": 6, "fast": 1, "horizon": 150, "H": (6, 0), "caps": (2, 3)},
         {"slow": 12, "fast": 4, "horizon": 240, "H": (5, 23), "caps": (5, 2)})
assert tuple(TG._RICH_EXTRA) == EXTRA and len(TG._RICH) == 4


def rich(seed, variant, kinf):
    """TG._rich_instance: variants 0-3 the grids of _RICH, 4-7 those of EXTRA."""
    return TG._rich_instance(seed, variant, kinf)


class Adv(TG._RandomInner):
    """_RandomInner plus edge patterns at about half its slots: a Drain exactly at the next slot's first minute or
    one minute before it; a SetAdmission after a Drain of the same replica (and the reverse); a second Drain of a
    replica with a pending drain; an Unload followed by a Load on the same lease; a Release followed by a Buy at the
    same site; a Buy of n = 2 replicas with admission 0.3. Never names an object of its own list."""
    name = "adv"

    def act(self, obs):
        acts = list(super().act(obs))
        r, view = self.r, self.view
        if r.random() < 0.5:
            return acts
        Ds = view.grid.slow_min
        gone_l = {int(a.lease_id) for a in acts if isinstance(a, Release)}
        gone_r = {int(a.replica_id) for a in acts if isinstance(a, Unload)}
        reps = sorted(int(rid) for rid, rv in obs.replicas.items()
                      if rv.lease_id in obs.leases and rv.lease_id not in gone_l and rid not in gone_r)
        leases = sorted(l for l in obs.leases if l not in gone_l)
        kind = str(r.choice(("drain_edge", "drain_adm", "adm_drain", "redrain", "swap", "relbuy", "buy2")))
        if kind in ("drain_edge", "drain_adm", "adm_drain", "redrain") and reps:
            rid = int(r.choice(reps))
            at = int(obs.minute + Ds - int(r.choice((0, 1))))
            if kind == "drain_edge":
                acts.append(Drain(rid, at))
            elif kind == "drain_adm":
                acts += [Drain(rid, int(obs.minute)), SetAdmission(rid, float(r.choice((0.5, 1.0))))]
            elif kind == "adm_drain":
                acts += [SetAdmission(rid, 1.0), Drain(rid, int(obs.minute + r.integers(0, 2 * Ds)))]
            else:
                rv = obs.replicas[rid]
                if rv.drain_min is not None:
                    acts.append(Drain(rid, max(int(obs.minute), int(rv.drain_min) + int(r.integers(-Ds, Ds)))))
        elif kind == "swap" and reps:
            rid = int(r.choice(reps))
            lid = int(obs.replicas[rid].lease_id)
            acts += [Unload(rid), Load(lid, int(r.integers(0, len(view.llms))))]
        elif kind == "relbuy" and leases:
            lid = int(r.choice(leases))
            L = obs.leases[lid]
            if L.site in range(len(view.sites)) and L.contract in view.sites[L.site].menu:
                acts += [Release(lid), Buy(L.site, int(L.contract), int(r.integers(0, len(view.llms))), 1)]
        elif kind == "buy2":
            l = int(r.integers(0, len(view.sites)))
            acts.append(Buy(l, int(r.choice(sorted(view.sites[l].menu))), int(r.integers(0, len(view.llms))), 2,
                            admission=0.3))
        return acts


def q_slot(inst):
    return TG._q_slot(inst)


def check(inst, res, tag, budget_ref=None):
    """Returns (max m over executed slots, max Phi - budget over the wind-down, info)."""
    rep = res.metrics["policy"]
    assert res.invariant_failures == [], (tag, res.invariant_failures[:2])
    tot = np.asarray(res.per_slot["total"], dtype=float)
    alg = np.cumsum(tot)
    g = rep["guard"]
    t_a = rep["t_a"]
    ex = g["slots"] if t_a is None else g["slots"][:-1]
    scale = max(1.0, float(alg[-1]))
    mmax = max([alg[t] - g["a_hat"][i] for i, t in enumerate(ex)] or [-np.inf]) / scale
    pmax = -np.inf
    info = {}
    if t_a is not None:
        Q = q_slot(inst)
        phi = np.cumsum((tot - Q)[::-1])[::-1]
        bud = rep["budget_t_a"]
        if budget_ref is not None:
            assert bud == budget_ref, (tag, bud, budget_ref)
        pmax = (phi[t_a] - bud) / scale
        for e in rep["wd"]:
            pmax = max(pmax, (phi[e["t"]] - e["budget"]) / scale)
        info = {"phi": float(phi[t_a]), "R": float(bud), "choices": [e["choice"] for e in rep["wd"]],
                "strand_t_a": float(res.per_slot["stranding"][t_a])}
    return mmax, pmax, info


def run_case(inst, lm, make_inner, rule, tag, auto_drain, stats):
    cautious = lm.get("on_unavailable") == "refuse"
    kw = dict(test="T0g", safe="fb", wind_down=rule, on_unavailable="refuse" if cautious else None, **NO_ABORT)
    cfg = EngineConfig(auto_drain=auto_drain)
    model = LenderModel(**lm)
    ref = simulate(inst, Guarded(inner=make_inner(), **kw), model, cfg, policy_seed=0)
    m0, _, _ = check(inst, ref, (tag, "ref"))
    rrep = ref.metrics["policy"]
    worst_m, worst_p = m0, -np.inf
    stats["slots"] += len(rrep["guard"]["slots"])
    stats["robust"] += len(rrep["t0g"]["robust_slots"])
    stats["victims"] += sum(len(v.get("victims", [])) for v in ref.violations)
    stats["uncertain"] += int(sum(rrep["t0g"]["uncertain"]))
    for t_a in range(inst.grid.T_slow):
        res = simulate(inst, Guarded(inner=make_inner(), abort_at=t_a, **kw), model, cfg, policy_seed=0)
        R = rrep["guard"]["reserve"][t_a - 1] if t_a > 0 else 0.0
        m, p, info = check(inst, res, (tag, t_a), budget_ref=R)
        worst_m, worst_p = max(worst_m, m), max(worst_p, p)
        stats["aborts"] += 1
        stats["kept"] += sum(1 for c in info["choices"] if c != "K0")
        stats["tight"] += int(info["R"] > 0 and info["phi"] >= 0.5 * info["R"])
        if p > TOL or m > TOL:
            print("VIOLATION", tag, t_a, m, p, info, flush=True)
            stats["viol"] += 1
    return worst_m, worst_p


def main():
    if os.environ.get("AUDIT_WC") == "1":
        audit_env.route_over_wc(True)
    block = sys.argv[1] if len(sys.argv) > 1 else "A"
    nseeds = int(sys.argv[2]) if len(sys.argv) > 2 else 2
    stats = Counter()
    t0 = time.time()
    worst_m = worst_p = -np.inf
    nvar = len(TG._RICH) + len(EXTRA)
    for s in range(nseeds):
        for v in range(nvar):
            for i, (mname, lm) in enumerate(MODELS.items()):
                kinf = bool((s + v + i) % 2)
                ad = bool((s + i) % 2)
                rule = "adaptive" if (s + v) % 3 else "release"
                seed = 1000 * (ord(block) - 64) + 37 * s + 5 * v + i
                try:
                    inst = rich(seed, v, kinf)
                except Exception:                             # a lender mode that the instance does not admit
                    stats["skip_" + mname] += 1
                    continue
                Inner = Adv if (s + i) % 2 else TG._RandomInner
                try:
                    m, p = run_case(inst, lm, lambda: Inner(seed), rule, (block, s, v, mname, kinf, ad, rule,
                                                                           Inner.name), ad, stats)
                except Exception as e:
                    if "ConfigError" in type(e).__name__ or "safe_site" in str(e):
                        stats["skip_" + mname] += 1
                        continue
                    raise
                worst_m, worst_p = max(worst_m, m), max(worst_p, p)
                stats["cases"] += 1
    print(f"block {block}: {dict(stats)}  max m/scale = {worst_m:.3e}  max (Phi - budget)/scale = {worst_p:.3e}  "
          f"{time.time() - t0:.0f} s", flush=True)
    return int(stats["viol"] > 0 or worst_m > TOL or worst_p > TOL)


if __name__ == "__main__":
    if main():               # exit status 1 on a violation, the reference runs' m included (run_all.sh counts it)
        print("x2: m(t) or Phi - budget above the tolerance", file=sys.stderr)
        sys.exit(1)
