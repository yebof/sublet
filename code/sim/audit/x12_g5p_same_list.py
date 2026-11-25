"""X12: Lemma G5'(c) on engine runs whose action lists act on objects created earlier in the same list. On every run
and at every slow slot t, ALG(t) >= LB'(t), up to the routing's tolerance.

Claim and source. design/theory/c3_c4_c5_general.md §9, Lemma G5'(c) (full model, pathwise), Steps 2 and 3 of its
proof: _load counts the replicas that exist at the moment of a Load, including those created earlier in the same
list and excluding those unloaded earlier (Step 2), and a replica is warm from t_rho phi + theta on and exists from
its load slot on (Step 3). The audit addendum of step P6 (design/sublet_v2.md §5) in design/theory/audit_guard.md:
its verdict on G5'(c), finding G5P-F7 (x10's fuzzer never acts on objects created earlier in the same list) and the
third and fourth rows of its 'Adversarial attempts'. The auditors' scratch scripts behind those rows are moved here
(open item 1 of the addendum). A violation is LB'(t) - ALG(t) > TOL max(1, ALG(t)) at some slow slot, TOL = 1e-9;
ALG(t) is the cumulative sum of the engine's per-slot ledger total. LB'(t) comes from the oracles of
x11_g5p_oracle.py, which are written from the text independently of online_lb.py (part (a): oracle_uf; part (b):
oracle_edge).

(a) 12000 runs of the policy Attack on x11's rand_instance (seed 20000 + run), in six styles drawn per run:
    'samelist' (Buy of 1-3 replicas, Unload of some of the new replicas by their predicted ids, Load of other LLMs
    onto the freed GPUs of the new lease, and Load then Unload of a just-loaded replica, all in one list), 'pack'
    (unload every replica of a held lease and fill it with LLMs of different g; Buys of the largest LLM), 'churn'
    (unload and reload most replicas every slot), 'late' (Loads onto leases whose announced death is at most one slow
    slot and two fast slots away, also after unloading their replicas), 'tight' (per LLM the slot's peak demand
    rounded up on the cheapest zeta-adjusted contract, leases released when their rent would start, free GPUs reused
    for other LLMs) and 'mix' (samelist, pack, churn and late); 'mix' and 'churn' also act from on_fast (SetAdmission,
    Drain), and 'mix' and 'pack' set admissions. Lender modes, one per run: trace, eager, adaptive, iid_step
    (D_slots 1, p 0.4), trace under I2, trace with on_unavailable 'refuse' (replaced by trace under I2 for the
    styles that predict ids, which need every Buy accepted; a mode the instance does not admit is replaced by
    trace and counted). EngineConfig(check_invariants=True, auto_drain in 30% of the runs).
(b) 400 instances of x11's rand_instance_edge (generator seed 1000 + i), each run under five lender modes (trace,
    eager, adaptive, iid_step and safe_site with D_slots 1) with two policies: SameList (random actions on observed
    objects, then new objects in the same list: Buys, Unloads of the new replicas, Loads onto the new leases, a few
    Releases of new leases; Drain and SetAdmission on observed replicas) and Lean (per group the slot's peak demand
    rounded up, 1 under kappa_infinite, 0 if r >= q in the capacitated case, on the cheapest zeta-adjusted (site,
    contract), each lease released at the slot in which its rent would start; with probability 0.2 a Buy of 2
    replicas, an Unload of the second and a Load of another LLM, which drives ALG(t) close to LB'(t)).
Every run's engine invariants (RunResult.invariant_failures) must be empty. The output counts the same-list
patterns, the leases with several LLMs, the tight slots and the minimum relative slack.

Usage: x12_g5p_same_list.py [n_a] [n_b] [--reduced]   (default 12000 runs and 400 instances (4000 runs), about
4 min on one worker; --reduced: 600 and 20). Audit addendum of step P6; code/sim/audit/, run by run_all.sh (step x12),
output code/sim/out/audit_fm/x12_out.txt. Exit status 1 on a violation, an engine invariant failure or a run that
raises."""
import math
import sys
import time
import traceback
from collections import Counter

import numpy as np

import audit_env  # noqa: F401
import x11_g5p_oracle as X11
from sublet.algos import online_lb as OL
from sublet.config import ConfigError, rng_streams
from sublet.engine import Engine, EngineConfig, simulate
from sublet.instance import public_view
from sublet.lender import Lender
from sublet.policies.base import Policy
from sublet.types import Buy, Drain, LenderModel, Load, Release, SetAdmission, Unload

TOL = 1e-9
STYLES = ("samelist", "pack", "churn", "late", "tight", "mix")
MODES = [dict(schedule="trace"), dict(schedule="eager"), dict(schedule="adaptive"),
         dict(schedule="iid_step", params={"D_slots": 1, "p": 0.4}), dict(schedule="trace", information="I2"),
         dict(schedule="trace", on_unavailable="refuse")]
MODES_B = ("trace", "eager", "adaptive", "iid_step", "safe_site")


def mode_name(mode):
    return mode["schedule"] + "".join(f" {k}={v}" for k, v in mode.items() if k not in ("schedule", "params"))


# ================================================================ part (a): the policy Attack
class Attack(Policy):
    """Actions on objects of the same list by predicted ids (engine ids are consecutive), in one of STYLES."""
    name = "attack"

    def __init__(self, seed, style):
        self.seed, self.style = int(seed), style

    def reset(self, view, rng):
        super().reset(view, rng)
        self.r = np.random.default_rng(self.seed)
        self.nL = 0          # leases created so far
        self.nR = 0          # replicas created so far
        self.g = [int(x.g) for x in view.llms]
        self.J = len(view.llms)
        self.wants_fast = self.style in ("mix", "churn")
        self.fast_cands = []

    def _count(self, results):
        for res in results:
            if res.ok and isinstance(res.action, Buy):
                self.nL += 1
                self.nR += int(res.action.n_replicas)
            elif res.ok and isinstance(res.action, Load):
                self.nR += 1

    def act(self, obs):
        self._count(obs.results)
        v, r = self.view, self.r
        Ds, Df = v.grid.slow_min, v.grid.fast_min
        minute = int(obs.minute)
        leases = dict(obs.leases)
        reps = {rid: rv for rid, rv in obs.replicas.items() if rv.lease_id in leases}
        free = {lid: L.gpus - sum(self.g[reps[x].llm] for x in L.replicas if x in reps) for lid, L in leases.items()}
        acts = []
        nL, nR = self.nL, self.nR          # predicted ids for this list (valid if every Buy and Load is accepted)
        dead_l, dead_r = set(), set()
        new_reps = {}                      # rid -> (lease id, llm) created in this list
        new_leases = {}                    # lid -> free GPUs

        def buy(l, k, j, n, adm=1.0):
            nonlocal nL, nR
            acts.append(Buy(int(l), int(k), int(j), int(n), admission=float(adm)))
            lid = nL
            nL += 1
            ids = list(range(nR, nR + n))
            nR += n
            for x in ids:
                new_reps[x] = (lid, j)
            new_leases[lid] = 0
            return lid, ids

        def unload_new(x):
            lid, j = new_reps.pop(x)
            acts.append(Unload(int(x)))
            new_leases[lid] += self.g[j]

        def load_new(lid, j):
            nonlocal nR
            if new_leases[lid] >= self.g[j]:
                acts.append(Load(int(lid), int(j)))
                new_leases[lid] -= self.g[j]
                new_reps[nR] = (lid, j)
                nR += 1
                return True
            return False

        def load_old(lid, j):
            nonlocal nR
            if lid not in dead_l and free[lid] >= self.g[j]:
                acts.append(Load(int(lid), int(j)))
                free[lid] -= self.g[j]
                nR += 1
                return True
            return False

        def unload_old(x):
            if x in reps and x not in dead_r and reps[x].lease_id not in dead_l:
                acts.append(Unload(int(x)))
                dead_r.add(x)
                free[reps[x].lease_id] += self.g[reps[x].llm]

        def release(lid):
            if lid not in dead_l:
                acts.append(Release(int(lid)))
                dead_l.add(lid)
                dead_r.update(x for x in reps if reps[x].lease_id == lid)

        sites = list(range(len(v.sites)))
        menu = {l: sorted(v.sites[l].menu) for l in sites}
        st = self.style
        if st in ("samelist", "mix"):
            for _ in range(int(r.integers(1, 3))):
                l = int(r.choice(sites))
                k = int(r.choice(menu[l]))
                j = int(r.integers(self.J))
                n = int(r.integers(1, 4))
                lid, ids = buy(l, k, j, n, adm=float(r.choice([1.0, 1.0, 0.5])))
                for x in ids:
                    if r.random() < 0.6:
                        unload_new(x)
                for _ in range(4):
                    load_new(lid, int(r.integers(self.J)))
                if r.random() < 0.15:          # Load, then Unload of the just-loaded replica, in the same list
                    if load_new(lid, int(r.integers(self.J))):
                        unload_new(nR - 1)
        if st in ("pack", "mix"):
            for lid in sorted(leases):
                if lid in dead_l:
                    continue
                if r.random() < 0.5:
                    for x in [x for x in leases[lid].replicas if x in reps]:
                        unload_old(x)
                    js = list(range(self.J))
                    r.shuffle(js)
                    for j in js * 3:
                        load_old(lid, j)
            if r.random() < 0.6:
                jb = int(np.argmax(self.g))
                l = int(r.choice(sites))
                buy(l, int(r.choice(menu[l])), jb, int(r.integers(1, 3)))
        if st in ("churn", "mix"):
            for x in sorted(reps):
                if r.random() < 0.7:
                    lid = reps[x].lease_id
                    unload_old(x)
                    load_old(lid, int(r.integers(self.J)))
        if st in ("late", "mix"):
            for lid, L in sorted(leases.items()):
                if L.death_min is not None and L.death_min - minute <= Ds + 2 * Df:
                    for j in range(self.J):
                        load_old(lid, j)
                    if r.random() < 0.5:
                        for x in [x for x in L.replicas if x in reps]:
                            unload_old(x)
                        for j in range(self.J):
                            load_old(lid, j)
            if not leases or r.random() < 0.3:
                l = int(r.choice(sites))
                buy(l, int(r.choice(menu[l])), int(r.integers(self.J)), 1)
        if st == "tight":
            for lid, L in sorted(leases.items()):
                if -(-L.prepaid_end_min // Df) * Df <= minute and r.random() < 0.8:
                    release(lid)
            dem = obs.demand
            cl = np.asarray(v.client_llm)
            for j in range(self.J):
                dj = float(dem[cl == j].sum(axis=0).max()) if np.any(cl == j) else 0.0
                tgt = int(math.ceil(dj - 1e-12))
                if v.kappa_infinite:
                    tgt = min(tgt, 1)
                have = sum(1 for x in reps if reps[x].llm == j and x not in dead_r and reps[x].lease_id not in dead_l)
                if tgt > have:
                    best = None
                    for l in sites:
                        for k in menu[l]:
                            P = v.contracts[k].prepaid_min
                            z = 1.0 if P == 0 else P / (-(-P // Df) * Df)
                            c = z * float(v.price[l, k])
                            if best is None or c < best[0]:
                                best = (c, l, k)
                    hosts = [lid for lid in leases if lid not in dead_l and free[lid] >= self.g[j]]
                    while tgt > have and hosts:
                        if load_old(hosts[0], j):
                            have += 1
                        else:
                            hosts.pop(0)
                    if tgt > have:
                        buy(best[1], best[2], j, tgt - have)
        if st in ("mix", "pack") and reps:
            for x in sorted(reps):
                if x not in dead_r and reps[x].lease_id not in dead_l and r.random() < 0.2:
                    acts.append(SetAdmission(int(x), float(r.choice([0.0, 0.3, 1.0]))))
        self.fast_cands = [x for x in reps if x not in dead_r and reps[x].lease_id not in dead_l]
        self.slot_end = minute + Ds
        self.lease_end = {x: (leases[reps[x].lease_id].death_min if leases[reps[x].lease_id].death_min is not None
                              else 10 ** 9) for x in self.fast_cands}
        return acts

    def on_fast(self, fo):
        r = self.r
        Df = self.view.grid.fast_min
        f = int(fo.f)
        c = [x for x in self.fast_cands if (f + 1) * Df < self.lease_end[x] and (f + 2) * Df <= self.slot_end + 10 ** 9]
        out = []
        if c and r.random() < 0.3:
            x = int(r.choice(c))
            if (f + 2) * Df <= self.lease_end[x]:
                out.append(SetAdmission(x, float(r.choice([0.0, 0.5, 1.0]))) if r.random() < 0.5
                           else Drain(x, int((f + 1) * Df)))
        return out


def run_a(s, st, worst, bad):
    rng = np.random.default_rng(777 + s)
    inst = X11.rand_instance(20000 + s)
    style = str(rng.choice(STYLES))
    mode = MODES[int(rng.integers(len(MODES)))]
    if style in ("samelist", "mix", "pack", "late", "tight") and mode.get("on_unavailable") == "refuse":
        mode = dict(schedule="trace", information="I2")     # predicted ids need every Buy accepted
    model = LenderModel(**mode)
    try:
        lender = Lender(inst, model, rng_streams(s)["lender"])
    except ConfigError:
        st["a: mode skipped (replaced by trace): " + mode_name(mode)] += 1
        mode = dict(schedule="trace")
        model = LenderModel(**mode)
        lender = Lender(inst, model, rng_streams(s)["lender"])
    auto_drain = bool(rng.random() < 0.3)
    pol = Attack(30000 + s, style)
    res = Engine(inst, lender, pol, EngineConfig(check_invariants=True, auto_drain=auto_drain),
                 rng_streams(s)["policy"]).run()
    ALG = np.cumsum(np.asarray(res.per_slot["total"], dtype=float))
    LB = np.array(X11.oracle_uf(inst)[0], dtype=float)
    slack = ALG - LB
    relslack = slack / np.maximum(1.0, ALG)
    tag = f"run {s} style={style} mode={mode_name(mode)} auto_drain={int(auto_drain)}"
    if np.any(-slack > TOL * np.maximum(1.0, ALG)):
        bad.append(("a: violation", tag, float(relslack.min())))
    if res.invariant_failures:
        bad.append(("a: engine invariant", tag, res.invariant_failures[:3]))
    st["a: runs"] += 1
    st[f"a: style {style}"] += 1
    st[f"a: mode {mode_name(mode)}"] += 1
    st["a: auto_drain"] += int(auto_drain)
    st["a: slots"] += len(ALG)
    st["a: tight slots (LB' > 0)"] += int(np.sum((np.abs(slack) <= TOL * np.maximum(1, ALG)) & (LB > 1e-12)))
    L_by = {L.id: L for L in res.leases}
    llms_on = {}
    for rp in res.replicas:
        llms_on.setdefault(rp.lease_id, set()).add(rp.llm)
    Df = inst.grid.fast_min
    st["a: leases with >= 2 LLMs"] += sum(1 for x in llms_on.values() if len(x) >= 2)
    st["a: replicas loaded after their lease's purchase"] += sum(1 for rp in res.replicas
                                                                 if rp.load_start_min > L_by[rp.lease_id].start_min)
    st["a: replicas created and unloaded in their load slot"] += sum(1 for rp in res.replicas
                                                                     if rp.end_fast == rp.load_start_min // Df)
    st["a: replicas never warm"] += sum(1 for rp in res.replicas if rp.warm_fast >= rp.end_fast)
    i = int(np.argmin(relslack))
    if relslack[i] < worst["a"][0]:
        worst["a"] = (float(relslack[i]), tag)


# ================================================================ part (b): the policies SameList and Lean
class SameList(Policy):
    """Random actions on observed objects, then new objects and actions on them in the same list (module docstring)."""
    name = "samelist"

    def __init__(self, seed):
        self.seed = seed

    def reset(self, view, rng):
        super().reset(view, rng)
        self.r = np.random.default_rng(self.seed)
        self.wants_fast = True
        self.nl = 0          # next lease id
        self.nr = 0          # next replica id
        self.g = [x.g for x in view.llms]
        self.stats = Counter()

    def act(self, obs):
        v, r = self.view, self.r
        J, m = len(v.llms), len(v.sites)
        acts = []
        leases = {lid: L for lid, L in obs.leases.items()}
        reps = {rid: rv for rid, rv in obs.replicas.items() if rv.lease_id in leases}
        free = {lid: L.gpus - sum(self.g[reps[x].llm] for x in L.replicas if x in reps) for lid, L in leases.items()}
        dead_l, dead_r = set(), set()
        for rid, rv in list(reps.items()):          # existing objects
            u = r.random()
            if u < 0.1:
                acts.append(Unload(rid))
                dead_r.add(rid)
                free[rv.lease_id] += self.g[rv.llm]
            elif u < 0.15:
                acts.append(Drain(rid, int(obs.minute) + int(r.integers(0, 2 * v.grid.slow_min))))
            elif u < 0.2:
                acts.append(SetAdmission(rid, float(r.choice([0.0, 0.4, 1.0]))))
        for lid in list(leases):
            if lid in dead_l:
                continue
            if r.random() < 0.15:
                acts.append(Release(lid))
                dead_l.add(lid)
                dead_r.update(x for x in reps if reps[x].lease_id == lid)
            elif r.random() < 0.3:
                j = int(r.integers(J))
                if free[lid] >= self.g[j]:
                    acts.append(Load(lid, j))
                    free[lid] -= self.g[j]
                    self.nr += 1
        newl = []                                   # new objects in the same list
        for _ in range(int(r.integers(0, 3))):
            l = int(r.integers(m))
            k = int(r.choice(sorted(v.sites[l].menu)))
            j = int(r.integers(J))
            nrep = int(r.integers(1, 4))
            acts.append(Buy(l, k, j, nrep, admission=float(r.choice([1.0, 1.0, 0.5, 0.0]))))
            self.stats["Buys"] += 1
            lid = self.nl
            self.nl += 1
            rids = list(range(self.nr, self.nr + nrep))
            self.nr += nrep
            newl.append([lid, nrep * self.g[j], rids, j])
        for lid, gp, rids, j in newl:
            freeg = 0
            for rid in list(rids):
                if r.random() < 0.4:
                    acts.append(Unload(rid))
                    rids.remove(rid)
                    freeg += self.g[j]
                    self.stats["Unloads of new replicas"] += 1
            for _ in range(3):
                j2 = int(r.integers(J))
                if freeg >= self.g[j2] and r.random() < 0.7:
                    acts.append(Load(lid, j2))
                    freeg -= self.g[j2]
                    self.nr += 1
                    self.stats["Loads onto new leases"] += 1
            if r.random() < 0.08:
                acts.append(Release(lid))
                self.stats["Releases of new leases"] += 1
        return acts

    def on_fast(self, fo):
        return []


class Lean(Policy):
    """Near the bound (module docstring, part (b))."""
    name = "lean"

    def __init__(self, seed, p_same=0.2):
        self.seed, self.p_same = seed, p_same

    def reset(self, view, rng):
        super().reset(view, rng)
        self.r = np.random.default_rng(self.seed)
        v = view
        self.grs = OL.groups(v)
        z = OL.zeta(v)
        self.best = []
        for j, cs, ss in self.grs:
            g = v.llms[j].g
            self.best.append(min((z[k] * g * v.price[l, k], v.beta_usd[j, l], l, k)
                                 for l in ss for k in v.sites[l].menu))
        self.g = [x.g for x in v.llms]
        self.nl = self.nr = 0
        self.mine = {}   # lease id -> (group index, rent_from_fast)

    def act(self, obs):
        v = self.view
        Df, phi = v.grid.fast_min, v.grid.phi
        t = int(obs.t)
        acts = []
        held = {gi: 0 for gi in range(len(self.grs))}
        for lid, L in obs.leases.items():
            if lid not in self.mine:
                continue
            gi, rf = self.mine[lid]
            if t * phi <= rf <= (t + 1) * phi - 1:       # rent would start inside this slot
                acts.append(Release(lid))
                continue
            if rf < t * phi:
                acts.append(Release(lid))
                continue
            held[gi] += 1
        for gi, (j, cs, ss) in enumerate(self.grs):
            rr, b, l, k = self.best[gi]
            q = v.llms[j].q_usd_per_h
            d = obs.demand[list(cs)].sum(axis=0)
            if v.kappa_infinite:
                tgt = 1 if d.max() > 0 else 0
            else:
                tgt = 0 if rr >= q else int(math.ceil(d.max() - 1e-12))
            for _ in range(max(0, tgt - held[gi])):
                P = v.contracts[k].prepaid_min
                rf = t * phi + (-(-P // Df))
                if self.r.random() < self.p_same:
                    acts.append(Buy(l, k, j, 2))
                    lid = self.nl
                    self.nl += 1
                    r0 = self.nr
                    self.nr += 2
                    acts.append(Unload(r0 + 1))
                    j2 = int(self.r.integers(len(v.llms)))
                    if self.g[j2] <= self.g[j]:
                        acts.append(Load(lid, j2))
                        self.nr += 1
                else:
                    acts.append(Buy(l, k, j, 1))
                    lid = self.nl
                    self.nl += 1
                    self.nr += 1
                self.mine[lid] = (gi, rf)
        return acts


def run_b(i, st, worst, bad, errors):
    inst = X11.rand_instance_edge(np.random.default_rng(1000 + i))
    lbs = X11.oracle_edge(inst)
    st["b: instances"] += 1
    st["b: kappa_infinite"] += int(inst.kappa_infinite)
    st["b: instances with a group"] += int(len(OL.groups(public_view(inst, "I1"))) > 0)
    for mode in MODES_B:
        for pk in ("same", "lean"):
            model = LenderModel(schedule=mode, params=({"D_slots": 1} if mode in ("iid_step", "safe_site") else {}))
            pol = SameList(i * 7 + 3) if pk == "same" else Lean(i * 7 + 5)
            tag = f"instance {i} mode={mode} policy={pol.name}"
            try:
                res = simulate(inst, pol, model, EngineConfig(), lender_seed=i, policy_seed=i)
            except Exception as e:  # a run that cannot be checked is a failure of the audit
                errors.append((tag, f"{type(e).__name__}: {e}", traceback.format_exc(limit=3)))
                continue
            st.update({"b: " + k: v for k, v in getattr(pol, "stats", {}).items()})
            alg = np.cumsum(np.asarray(res.per_slot["total"], dtype=float))
            st["b: runs"] += 1
            st[f"b: runs {pol.name}"] += 1
            st["b: slots"] += len(alg)
            if res.invariant_failures:
                bad.append(("b: engine invariant", tag, res.invariant_failures[:3]))
            slack = (alg - lbs) / np.maximum(1.0, alg)
            st["b: tight slots (LB' = 0 included)"] += int(np.sum(np.abs(alg - lbs) <= TOL * np.maximum(1.0, alg)))
            if np.any(slack < -TOL):
                bad.append(("b: violation", tag, float(slack.min())))
            key = f"b {pol.name}"
            if float(slack.min()) < worst[key][0]:
                worst[key] = (float(slack.min()), tag)
            st["b: leases with >= 2 LLMs"] += sum(1 for L in res.leases
                                                  if len({rp.llm for rp in res.replicas if rp.lease_id == L.id}) > 1)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    reduced = "--reduced" in sys.argv
    n_a = int(args[0]) if args else (600 if reduced else 12000)
    n_b = int(args[1]) if len(args) > 1 else (20 if reduced else 400)
    t0 = time.time()
    st, bad, errors = Counter(), [], []
    worst = {"a": (np.inf, ""), "b samelist": (np.inf, ""), "b lean": (np.inf, "")}
    for s in range(n_a):
        try:
            run_a(s, st, worst, bad)
        except Exception as e:  # a run that cannot be checked is a failure of the audit
            errors.append((f"a: run {s}", f"{type(e).__name__}: {e}", traceback.format_exc(limit=3)))
    for i in range(n_b):
        try:
            run_b(i, st, worst, bad, errors)
        except Exception as e:
            errors.append((f"b: instance {i}", f"{type(e).__name__}: {e}", traceback.format_exc(limit=3)))
    wall = time.time() - t0
    L = ["X12: Lemma G5'(c) pathwise on engine runs with same-list Load and Unload, ALG(t) >= LB'(t) at every slow "
         "slot (design/theory/c3_c4_c5_general.md §9, Lemma G5'(c), Steps 2-3; audit addendum of step P6 in "
         "design/theory/audit_guard.md, finding G5P-F7)",
         "oracle: LB' from x11_g5p_oracle.py (oracle_uf in (a), oracle_edge in (b)), written from the text; script "
         "code/sim/audit/x12_g5p_same_list.py",
         f"runs: (a) {st['a: runs']} of {n_a}, (b) {st['b: runs']} on {st['b: instances']} of {n_b} instances "
         f"({'reduced' if reduced else 'default'}); run errors: {len(errors)}; wall time {wall:.0f} s on one worker",
         f"tolerance: violation iff LB'(t) - ALG(t) > {TOL:g} max(1, ALG(t))", ""]
    L.append("(a) the policy Attack on x11's rand_instance:")
    for pre in ("a: style ", "a: mode skipped (replaced by trace): ", "a: mode "):
        items = [(k, v) for k, v in sorted(st.items()) if k.startswith(pre)
                 and not (pre == "a: mode " and k.startswith("a: mode skipped"))]
        L.append(f"  {pre[3:].strip(' :')}: " + (", ".join(f"{k[len(pre):]} {v}" for k, v in items) or "none"))
    for k in ("a: slots", "a: auto_drain", "a: leases with >= 2 LLMs",
              "a: replicas loaded after their lease's purchase", "a: replicas created and unloaded in their load slot",
              "a: replicas never warm", "a: tight slots (LB' > 0)"):
        L.append(f"  {k[3:]}: {st[k]}")
    L.append(f"  minimum relative slack (ALG(t) - LB'(t)) / max(1, ALG(t)): {worst['a'][0]:.6e} ({worst['a'][1]})")
    L.append("(b) the policies SameList and Lean on x11's rand_instance_edge:")
    for k in ("b: instances", "b: kappa_infinite", "b: instances with a group", "b: runs samelist", "b: runs lean",
              "b: slots", "b: Buys", "b: Unloads of new replicas", "b: Loads onto new leases",
              "b: Releases of new leases", "b: leases with >= 2 LLMs", "b: tight slots (LB' = 0 included)"):
        L.append(f"  {k[3:]}: {st[k]}")
    for key in ("b samelist", "b lean"):
        L.append(f"  minimum relative slack, {key[2:]}: {worst[key][0]:.6e} ({worst[key][1]})")
    kinds = Counter(b[0] for b in bad)
    L.append("failures by kind: " + (", ".join(f"{k} {v}" for k, v in sorted(kinds.items())) or "none"))
    for kind, tag, detail in bad[:20]:
        L.append(f"  FAIL {kind}: {tag}: {detail}")
    for tag, msg, tb in errors[:10]:
        L.append(f"  ERROR {tag}: {msg}")
        L.append("    " + tb.strip().replace("\n", "\n    "))
    nviol = sum(v for k, v in kinds.items() if k.endswith("violation"))
    ninv = sum(v for k, v in kinds.items() if k.endswith("engine invariant"))
    L.append(f"engine invariant failures: {ninv}")
    L.append(f"violations: {nviol}")
    print("\n".join(L), flush=True)
    return int(len(bad) > 0 or len(errors) > 0)


if __name__ == "__main__":
    if main():   # exit status 1 on a violation, an engine invariant failure or a run error (run_all.sh counts it)
        print("x12: a violation of ALG(t) >= LB'(t), an engine invariant failure or a run error", file=sys.stderr)
        sys.exit(1)
