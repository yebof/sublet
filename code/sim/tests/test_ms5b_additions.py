"""Tests of the MS5b baseline options, addition C38 to baselines/common.py, greedy.py and retrorenting.py, and of the
registry and driver additions C34 and C35 (design/sublet_v2.md §3, §8.1, §8.2; §8.3 test_ms5b_additions.py).

- Defaults: BL1 and BL5 (several parameter sets) and A8 around each, on configs/toy.json under the trace lender and
  i.i.d. announcements and on four random toys, give runs whose digest (every ledger component, every lease record
  and the policy's report, wall-clock keys left out) equals the digest of the same run on commit 5c2dd201, the last
  commit before C38 (DIGESTS, measured on a clean copy of that commit's code/sim with the same digest function);
  passing every new option at its default gives the same digests, so the records stay those of MS1-MS5 (params()
  leaves the new keys out at their defaults, QUIET_KEYS).
- Keys, validation and the registry: the new keys and defaults of GreedyLease.PARAMS and
  RetroRentingStyle.PARAMS, params() at the defaults as in MS2 and with a set option, PolicyError for bad values,
  registry.param_names and make_policy accept the options, A8 passes them to its inner policy.
- backoff_cap (BL1-BO): the back-off sequence on hand-made observations (b_l <- 1, doubling within until_l + 2 b_l,
  capped, reset after a quiet period; only own 'reclaim' and 'violation' ends count; the site choice avoids a site
  while t <= until_l); on engine runs no purchase falls in a back-off interval replayed from the run's own ends.
- tau_min (BL5-tau60): k* over tau_k Δs >= tau_min, a site without such a contract is not usable, BL5 buys only
  those contracts.
- contract_rule 'c2' (BL5N): every purchase uses kbar(l, j) = argmin over P3(l, j) of (a_lk, P_k, -H_k, k), the
  usable arcs, scores, rent and fetch cost are those of kbar (skipped while contracts.c2_contract_table, C37 of
  another unit, is missing); without that function the option raises PolicyError.
- mbb (BL5N): at u_L = timing.latest_prewarm_slot(r, E, lam_c, grid) the instance buys a replacement at its
  cheapest usable site with no own lease under notice and keeps its rule state, the noticed lease serves until its
  death; a refused replacement is a forced eviction; with every usable site under notice it uses a noticed one.
- demand_lag (greedy): demand_of and the target read slot t - L's demand (zeros before), and BL1 with lag 1 makes
  the decisions of BL1 on the demand shifted by one slot.
- Registry and driver (C34, C35): the rows of A9 and A8P (kept out of POLICY_IDS, which tests/test_run_spec.py and
  tests/test_policy_isolation.py pin), A8P_INNER_IDS, A8P's defaults against ProjectedGuarded.PARAMS, A8's rows
  unchanged, A8P as A8 in inner_of, a8_own_inputs, needed_inputs and info_class; make_policy's routing of A8P (own
  N_bound, the inner's inputs, on_unavailable), the inner check and auto_drain; A9, A8P and A8P around BL1 through
  make_policy in plan class P1 (the case of test_plan_class_p1, whose P1_CASES does not list the MS5B ids) and
  through drivers.run.run with the run file's resolved parameters and information class.
"""
from __future__ import annotations

import hashlib
import json
import math

import numpy as np
import pytest

from fixtures import random_toy_config, site_index, toy_config

from sublet.algos import contracts, registry
from sublet.algos.common import PolicyError, lam_ms
from sublet.baselines.common import SiteTable, c2_base_contracts, k_star
from sublet.baselines.greedy import GreedyLease
from sublet.baselines.retrorenting import RetroRentingStyle
from sublet.drivers.run import make_policy
from sublet.engine import EngineConfig, simulate
from sublet.instance import build_instance, public_view
from sublet.timing import latest_prewarm_slot
from sublet.types import ActionResult, Buy, LeaseView, LenderModel, Release, SlowObs

HAS_C2_TABLE = hasattr(contracts, "c2_contract_table")
NEEDS_C2_TABLE = pytest.mark.skipif(not HAS_C2_TABLE, reason="contracts.c2_contract_table (C37, design/sublet_v2.md "
                                                             "§8.1, written by another MS5b unit) is not in this build")
BL1_NEW = {"backoff_cap": None, "demand_lag": 0}
BL5_NEW = {"tau_min": None, "contract_rule": "kstar", "mbb": False}
IID = {"schedule": "iid_step", "params": {"D_slots": 1, "p": 0.3}}

# sha256 of _digest(run) on commit 5c2dd201 (before C38), per case of _cases()
DIGESTS = {
    'toy:BL1:{}:trace': "405d865c071993b1a1e7b56140f6bdcc29a73aa0adf3d52148ad4d322d97f855",
    'toy:BL1:{}:iid0.3': "ef6463320ce8449a0fa416f9ece18ac567507f2b2b04e156f332d866e59032d2",
    'toy:BL1:{"demand_stat": "mean"}:trace': "97eb1db27e0f62ad610ca0c147803914ec41a51fd1393c493cefeb844035f874",
    'toy:BL1:{"demand_stat": "mean"}:iid0.3': "16bd4819573bae7a125b74a2a7b4a65daeb4cbf717c8e6d36d7f8db62f2bc1a4",
    'toy:BL5:{}:trace': "0602d6a414ad7fecb0e94e8fc834124ccb01c18f6ffe0cc43ec0fff3374fa411",
    'toy:BL5:{}:iid0.3': "cdff81b5724888100d62e1dd0d071ca629933f1f40cc93d75aa46a372154f226",
    'toy:BL5:{"use_current_slot": true}:trace': "c15ee055954b79b2f6d014a7c3a3e8c88c533b2b5c80503b7383084d5d60f7de",
    'toy:BL5:{"use_current_slot": true}:iid0.3': "49ebf255af4a55aaa84aabe70d01a82a22143b63b5cd24035b36c18f4e419a30",
    'toy:BL5:{"refetch_after_reclaim": "immediate"}:trace':
        "dc890c33522955276a40ee520adb827db60dd64579e9e976258bb0eabaf79304",
    'toy:BL5:{"refetch_after_reclaim": "immediate"}:iid0.3':
        "3b6e15246d9af7b5a08c58c62a627dfa4964215d3a91e4999f2e7ceae8ad8d3f",
    'toy:A8:{"inner": "BL1", "safe": "fb"}:trace': "3ae20dd81db3da9e2a9ce045c1756d2d7bc57e345c7b81e01e8c452623990c2f",
    'toy:A8:{"inner": "BL1", "safe": "fb"}:iid0.3': "150d1275d9ca0da29509efb96bb0e87e8b7151f6e91bfde638202ec5678bfcde",
    'toy:A8:{"inner": "BL5", "safe": "fb"}:trace': "91ceba2c001601e698688c1d8b5b2e85d689619c3494e9dfd95579b031235675",
    'toy:A8:{"inner": "BL5", "safe": "fb"}:iid0.3': "b2fea89f4d0c9f256561b87e5b93376f7e985910b9bca03148a8b6bb30e300ed",
    'rand0:BL1:{}:trace': "c3e192ef8911c10a90a86525d059a78fb8e5e7b97de5d12c6f3df57f610fdf3b",
    'rand0:BL5:{}:trace': "cac62961609fefa60a9def5bf1f57d9db6316cb60fd9b1722c50a4b0638ab41d",
    'rand0:BL5:{"use_current_slot": true}:trace': "d40f66176d563e25299badae778beefb4dc5ca680d03df1c32906a71cd32f9b1",
    'rand1:BL1:{}:trace': "b82bb8ecdb86cd1c14a0b1a499c23fd219c81cf3fafcf5ccc44530c4e069445f",
    'rand1:BL5:{}:trace': "50d1d0b2c8f6c7a230b216e5a897ef4e2b808266b1557c5864d235257918718a",
    'rand1:BL5:{"use_current_slot": true}:trace': "699eb884cdaab9e8715e893c2c3d2a663c30d4175301c42b65483878e44ac6b1",
    'rand2:BL1:{}:trace': "37b1bc3810be3981927650a1ee8bd7cf9e84133244daa35f23a24fe47a555e51",
    'rand2:BL5:{}:trace': "e568a0725d97b5227d07d98f4b46e068621daab7683b98612f62e809fd777420",
    'rand2:BL5:{"use_current_slot": true}:trace': "4486806db7f00a5084044b1a7189ac5355016734de6bc12e6e604629210c46af",
    'rand3:BL1:{}:trace': "f96dab8bc4a0bb5dca5554d667132de9a3dbd642c5012e3a0b5af0181bdb0a22",
    'rand3:BL5:{}:trace': "244805047e35c600047d3a0326efbb471433c81c14e8d75b40d056d458523b06",
    'rand3:BL5:{"use_current_slot": true}:trace': "534271d46ee5fb1750eec61981c7d0e3c851406d6771414797c66f9ac9d86398",
}


# ---------------------------------------------------------------- runs and digests
def _jsonable(x):
    if isinstance(x, dict):
        return {str(k): _jsonable(v) for k, v in x.items() if "time_s" not in str(k) and "wall_s" not in str(k)}
    if isinstance(x, (list, tuple)):
        return [_jsonable(v) for v in x]
    if isinstance(x, np.ndarray):
        return _jsonable(x.tolist())
    if isinstance(x, np.integer):
        return int(x)
    if isinstance(x, (float, np.floating)):
        return float(x).hex()
    return x


def _digest(res) -> str:
    comp = {k: float(v).hex() for k, v in sorted(res.components.items())}
    leases = [[L.site, L.contract, L.gpus, L.start_slot, L.start_min, L.prepaid_end_min, L.announce_slot, L.death_min,
               L.release_min, L.end_min, L.end_cause, float(L.prepaid_usd).hex(), float(L.rent_usd).hex(), L.tag]
              for L in res.leases]
    rep = _jsonable(res.metrics.get("policy") or {})
    blob = json.dumps({"components": comp, "leases": leases, "report": rep}, sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()


def _cases() -> dict:
    """{name: (config, policy id, params, lender model fields, seed)}, the cases of DIGESTS."""
    toy = toy_config()
    out = {}
    for pid, params in (("BL1", {}), ("BL1", {"demand_stat": "mean"}), ("BL5", {}), ("BL5", {"use_current_slot": True}),
                        ("BL5", {"refetch_after_reclaim": "immediate"}), ("A8", {"inner": "BL1", "safe": "fb"}),
                        ("A8", {"inner": "BL5", "safe": "fb"})):
        out[f"toy:{pid}:{json.dumps(params, sort_keys=True)}:trace"] = (toy, pid, params, {}, 0)
        out[f"toy:{pid}:{json.dumps(params, sort_keys=True)}:iid0.3"] = (toy, pid, params, IID, 3)
    for s in range(4):
        cfg = random_toy_config(np.random.default_rng(100 + s), n_clients=2, two_llms=bool(s % 2))
        for pid, params in (("BL1", {}), ("BL5", {}), ("BL5", {"use_current_slot": True})):
            out[f"rand{s}:{pid}:{json.dumps(params, sort_keys=True)}:trace"] = (cfg, pid, params, {}, s)
    return out


CASES = _cases()


def _run(inst, pid, params, lm=None, seed=0):
    pol = make_policy({"policy": {"id": pid, "params": dict(params)}}, inst)
    model = LenderModel(**{"schedule": "trace", "information": "I1", **(lm or {})})
    res = simulate(inst, pol, model, EngineConfig(check_invariants=True), lender_seed=seed, policy_seed=seed)
    assert not res.invariant_failures, res.invariant_failures[:3]
    return res


def _with_defaults(pid, params) -> dict:
    """params with every C38 option of the policy (or of A8's inner policy) at its default."""
    if pid == "A8":
        new = BL1_NEW if params["inner"] == "BL1" else BL5_NEW
        return {**params, "inner_params": dict(new)}
    return {**params, **(BL1_NEW if pid == "BL1" else BL5_NEW)}


@pytest.mark.parametrize("name", sorted(CASES))
def test_defaults_reproduce_runs(name):
    """Every new option at its default reproduces the run of commit 5c2dd201 bit for bit, report included."""
    cfg, pid, params, lm, seed = CASES[name]
    inst = build_instance(cfg)
    assert _digest(_run(inst, pid, params, lm, seed)) == DIGESTS[name], name
    assert _digest(_run(inst, pid, _with_defaults(pid, params), lm, seed)) == DIGESTS[name], name


# ---------------------------------------------------------------- keys, validation, registry
def test_option_keys_validation_and_registry():
    assert GreedyLease.PARAMS == {"defer_release": True, "demand_stat": "max", "site_order": "auto",
                                  "backoff_cap": None, "demand_lag": 0}
    assert RetroRentingStyle.PARAMS == {"use_current_slot": False, "refetch_after_reclaim": "rule", "lookback": None,
                                        "defer_release": True, "tau_min": None, "contract_rule": "kstar", "mbb": False}
    # params() at the defaults: the MS2 keys only; a set option is listed, a default passed explicitly is not
    assert GreedyLease().params() == {"defer_release": True, "demand_stat": "max", "site_order": "auto"}
    assert GreedyLease(**BL1_NEW).params() == GreedyLease().params()
    assert RetroRentingStyle(**BL5_NEW).params() == {"use_current_slot": False, "refetch_after_reclaim": "rule",
                                                     "lookback": None, "defer_release": True}
    assert GreedyLease(backoff_cap=288).params()["backoff_cap"] == 288
    assert GreedyLease(demand_lag=1).params()["demand_lag"] == 1
    p = RetroRentingStyle(use_current_slot=True, contract_rule="c2", mbb=True).params()
    assert p["contract_rule"] == "c2" and p["mbb"] is True and "tau_min" not in p
    assert RetroRentingStyle(tau_min=60).params()["tau_min"] == 60

    class Sub(GreedyLease):            # a subclass without its own QUIET_KEYS lists every key
        pass
    assert set(Sub().params()) == set(GreedyLease.PARAMS)
    bad = [(GreedyLease, {"backoff_cap": 0}), (GreedyLease, {"backoff_cap": True}), (GreedyLease, {"backoff_cap": 2.5}),
           (GreedyLease, {"demand_lag": -1}), (GreedyLease, {"demand_lag": True}), (GreedyLease, {"demand_lag": 0.5}),
           (GreedyLease, {"tau_min": 60}), (GreedyLease, {"mbb": True}), (GreedyLease, {"contract_rule": "c2"}),
           (RetroRentingStyle, {"tau_min": -1}), (RetroRentingStyle, {"tau_min": True}),
           (RetroRentingStyle, {"tau_min": "60"}), (RetroRentingStyle, {"contract_rule": "k*"}),
           (RetroRentingStyle, {"mbb": 1}), (RetroRentingStyle, {"contract_rule": "c2", "tau_min": 60}),
           (RetroRentingStyle, {"backoff_cap": 288}), (RetroRentingStyle, {"demand_lag": 1})]
    for cls, kw in bad:
        with pytest.raises(PolicyError):
            cls(**kw)
    assert {"backoff_cap", "demand_lag"} <= set(registry.param_names("BL1"))
    assert {"tau_min", "contract_rule", "mbb"} <= set(registry.param_names("BL5"))
    inst = build_instance(toy_config())
    for pid, params in (("BL1", {"backoff_cap": 288}), ("BL1", {"demand_lag": 1}),
                        ("BL5", {"use_current_slot": True, "tau_min": 10})):
        assert make_policy({"policy": {"id": pid, "params": params}}, inst).params() == \
            {**registry.resolve(pid)().params(), **params}
    a8 = make_policy({"policy": {"id": "A8", "params": {"inner": "BL1", "safe": "fb",
                                                        "inner_params": {"backoff_cap": 288}}}}, inst)
    assert a8.params()["inner_params"]["backoff_cap"] == 288 and a8.inner.params()["backoff_cap"] == 288


# ---------------------------------------------------------------- backoff_cap (BL1-BO)
class _Driver:
    """Feeds a baseline hand-made slow-slot observations: every Buy succeeds (lease ids from 100) and its lease
    lives until the test ends it (`ended`) or the policy releases it (reported with cause 'release')."""

    def __init__(self, inst, pol):
        self.inst, self.pol = inst, pol
        self.view = public_view(inst, "I1")
        pol.reset(self.view, np.random.default_rng(0))
        self.slow = inst.grid.slow_min
        self.alive: dict[int, LeaseView] = {}
        self.results: list = []
        self.released: list = []
        self.next_id = 100

    def step(self, t: int, D, ended=()) -> list:
        """Slot t with demand D[c] in every fast slot and the ends (lease id, cause); returns the slot's Buys."""
        ends = [(lid, t * self.slow, "release") for lid in self.released]
        for lid, cause in ended:
            self.alive.pop(lid, None)
            ends.append((lid, t * self.slow, cause))
        n, phi = self.inst.n, self.inst.grid.phi
        dem = np.repeat(np.asarray(D, dtype=float).reshape(n, 1), phi, axis=1)
        obs = SlowObs(t=t, minute=t * self.slow, demand=dem, leases=dict(self.alive), replicas={}, notices=[],
                      ended=ends, results=list(self.results), site_announced=None,
                      served_prev=np.zeros((self.inst.J, self.inst.m)), fallback_prev=np.zeros(n), cost_so_far=0.0)
        acts = self.pol.act(obs)
        self.results, self.released = [], []
        for i, a in enumerate(acts):
            if isinstance(a, Buy):
                lid, self.next_id = self.next_id, self.next_id + 1
                self.alive[lid] = LeaseView(lid, a.site, a.contract, 1, t, t * self.slow, t * self.slow + self.slow,
                                            None, None, ())
                self.results.append(ActionResult(i, a, True, lid, (), ""))
            elif isinstance(a, Release):
                self.alive.pop(a.lease_id)
                self.released.append(a.lease_id)
        return [a for a in acts if isinstance(a, Buy)]


def test_backoff_sequence():
    """The back-off of design/sublet_v2.md §3 (BL1-BO) at backoff_cap 3 on the toy (k* sites L0 at 2.85 and L1 at
    2.9 USD/GPU-h, so L0 first): b_l <- 1 at a first end or after a quiet period (t > until_l + 2 b_l), else
    min(2 b_l, cap); until_l <- t + b_l; purchases avoid l while t <= until_l (none if every usable site is
    backed off); a 'release' end and the end of a lease that is not the policy's are no events."""
    inst = build_instance(toy_config({"lenders.0.R": [], "lenders.1.R": []}))
    L0, L1 = site_index(inst, "L0"), site_index(inst, "L1")
    dr = _Driver(inst, GreedyLease(backoff_cap=3))

    def state():
        return {int(l): (v["events"], v["b"], v["until"]) for l, v in dr.pol.report()["backoff"]["by_site"].items()}

    # (slot, ends, sites of the slot's Buys, back-off state per site after the slot)
    plan = [(0, [], [L0, L0], {}),
            (1, [(100, "reclaim")], [L1], {L0: (1, 1, 2)}),
            (2, [(101, "reclaim")], [L1], {L0: (2, 2, 4)}),                            # 2 <= 2 + 2: doubled
            (3, [(102, "violation")], [], {L0: (2, 2, 4), L1: (1, 1, 4)}),            # both backed off: no Buy
            (4, [], [], {L0: (2, 2, 4), L1: (1, 1, 4)}),
            (5, [], [L0], {L0: (2, 2, 4), L1: (1, 1, 4)}),                             # 5 > 4: both free again
            (6, [(104, "reclaim")], [L1], {L0: (3, 3, 9), L1: (1, 1, 4)}),            # min(4, cap 3)
            (7, [(103, "release"), (999, "reclaim")], [L1], {L0: (3, 3, 9), L1: (1, 1, 4)}),
            (10, [(105, "reclaim")], [L0], {L0: (3, 3, 9), L1: (2, 1, 11)}),          # 10 > 4 + 2: reset to 1
            (11, [(107, "reclaim")], [], {L0: (4, 3, 14), L1: (2, 1, 11)}),           # capped again
            (12, [], [L1], {L0: (4, 3, 14), L1: (2, 1, 11)})]
    for t, ends, sites, want in plan:
        got = [b.site for b in dr.step(t, [2.0], ends)]
        assert got == sites, (t, got, sites)
        assert state() == want, (t, state(), want)
    rep = dr.pol.report()["backoff"]
    assert rep["cap"] == 3 and rep["events"] == 6
    # without the option the same observations re-buy at L0 at once
    dr0 = _Driver(inst, GreedyLease())
    dr0.step(0, [2.0])
    assert [b.site for b in dr0.step(1, [2.0], [(100, "reclaim")])] == [L0] and "backoff" not in dr0.pol.report()


def _replay_backoff(res, inst, cap) -> tuple[dict, list]:
    """The back-off replayed from a run's own lease ends: final {site: (events, b, until)} and the intervals
    (site, first slot, last slot) in which the site was backed off."""
    slow, T = inst.grid.slow_min, inst.grid.T_slow
    ends = sorted((math.ceil(L.end_min / slow), L.site) for L in res.leases if L.end_cause in ("reclaim", "violation"))
    ends = [(t, l) for t, l in ends if t < T]                 # an end after the last slot is never reported
    b, until, ev, spans = {}, {}, {}, []
    for t, l in ends:
        bl = b.get(l, 0)
        bl = 1 if (bl == 0 or t > until[l] + 2 * bl) else min(2 * bl, cap)
        b[l], until[l], ev[l] = bl, t + bl, ev.get(l, 0) + 1
        spans.append((l, t, t + bl))
    return {l: (ev[l], b[l], until[l]) for l in b}, spans


@pytest.mark.parametrize("cap", [1, 4, 288])
def test_backoff_engine(cap):
    """Engine runs of BL1-BO (toy and two random toys, i.i.d. announcements): no purchase falls in a back-off
    interval replayed from the run's own reclaim and violation ends, the report's state equals the replay, and
    the purchases differ from BL1's."""
    cfgs = [toy_config({"borrowers.clients.0.demand.values": [1] * 24})] + \
        [random_toy_config(np.random.default_rng(300 + s), n_clients=2, p_on=0.9) for s in range(2)]
    moved = 0
    for i, cfg in enumerate(cfgs):
        inst = build_instance(cfg)
        lm = {"schedule": "iid_step", "params": {"D_slots": 1, "p": 0.4}}
        res = _run(inst, "BL1", {"backoff_cap": cap}, lm, seed=i + 1)
        final, spans = _replay_backoff(res, inst, cap)
        assert spans, i
        for L in res.leases:
            hit = [(l, a, z) for l, a, z in spans if l == L.site and a <= L.start_slot <= z]
            assert not hit, (i, L.site, L.start_slot, hit)
        rep = res.metrics["policy"]["backoff"]
        assert {int(l): (v["events"], v["b"], v["until"]) for l, v in rep["by_site"].items()} == final, i
        assert max(v[1] for v in final.values()) <= cap
        base = _run(inst, "BL1", {}, lm, seed=i + 1)
        moved += [(L.site, L.start_slot) for L in res.leases] != [(L.site, L.start_slot) for L in base.leases]
    assert moved >= 1


# ---------------------------------------------------------------- tau_min (BL5-tau60)
def test_tau_min():
    """k* over the contracts with tau_k Δs >= tau_min (toy: 'short' tau 5 min, 'long' tau 10 min at L0 and L1);
    with no such contract a site is not usable; BL5 with tau_min buys only those contracts."""
    inst = build_instance(toy_config({"borrowers.clients.0.demand.values": [1] * 24}))
    v = public_view(inst, "I1")
    ids = [c.id for c in v.contracts]
    L0, L1, P = (site_index(inst, s) for s in ("L0", "L1", "P"))
    assert list(k_star(v, None)) == list(k_star(v))
    assert [ids[k] for k in k_star(v)[[L0, L1]]] == ["short", "short"]
    for tau in (6, 10):
        assert [ids[k] for k in k_star(v, tau)[[L0, L1]]] == ["long", "long"] and k_star(v, tau)[P] == -1
    assert list(k_star(v, 15)) == [-1, -1, -1]
    st = SiteTable(v, np.arange(inst.m), tau_min=10)
    assert st.tau_min == 10 and st.score[0, L0] == 3.0 and st.usable[0, L1]
    assert not SiteTable(v, np.arange(inst.m), tau_min=15).usable.any()
    res = _run(inst, "BL5", {"use_current_slot": True, "tau_min": 10})
    assert res.leases and {ids[L.contract] for L in res.leases} == {"long"}
    assert res.metrics["policy"]["params"]["tau_min"] == 10
    assert {ids[L.contract] for L in _run(inst, "BL5", {"use_current_slot": True}).leases} == {"short"}
    assert not _run(inst, "BL5", {"use_current_slot": True, "tau_min": 15}).leases


# ---------------------------------------------------------------- contract_rule 'c2' (BL5N)
def _ab_config(**over) -> dict:
    """The toy with contracts 'a' (tau 5 min, H 0) and 'b' (tau 5 min, H 10 min) at L0 (2.85, 3.0) and L1 (2.9,
    3.1): P1 keeps both, k* is 'a', and P3 keeps only 'b' (60 H_a = 0 s is below every notice target)."""
    cfg = toy_config({"borrowers.clients.0.demand.values": [1] * 24, **over})
    cfg["contracts"] = [{"id": "a", "tau_min": 5, "H_min": 0}, {"id": "b", "tau_min": 5, "H_min": 10},
                        {"id": "prot", "tau_min": None, "H_min": 0, "prepaid_min": 5}]
    cfg["lenders"][0].update({"menu": ["a", "b"], "prices": {"a": 2.85, "b": 3.0}})
    cfg["lenders"][1].update({"menu": ["a", "b"], "prices": {"a": 2.9, "b": 3.1}})
    return cfg


def _kbar_spec(v) -> np.ndarray:
    """kbar(l, j) of design/sublet_v2.md §2.2 A9.3 from p1_mask and p3_mask."""
    p1 = contracts.p1_mask(v)
    p3 = contracts.p3_mask(v, p1)
    m, K = np.asarray(v.price).shape
    out = np.full((m, len(v.llms)), -1, dtype=np.int64)
    for l in range(m):
        for j in range(len(v.llms)):
            ks = [k for k in range(K) if p3[l, j, k] and p1[l, k] and not v.contracts[k].protected
                  and np.isfinite(v.price[l, k])]
            if ks:
                out[l, j] = min(ks, key=lambda k: (float(v.price[l, k]), v.contracts[k].prepaid_min,
                                                   -v.contracts[k].H_min, k))
    return out


@NEEDS_C2_TABLE
def test_contract_rule_c2():
    """BL5 with contract_rule 'c2' buys kbar(l, j) at every site; its usable arcs, scores, rent and fetch cost are
    those of kbar; 'kstar' keeps k*. Also on a random toy with two LLMs, kbar is c2_contract_table's."""
    inst = build_instance(_ab_config())
    v = public_view(inst, "I1")
    ids = [c.id for c in v.contracts]
    L0, L1, P = (site_index(inst, s) for s in ("L0", "L1", "P"))
    want = _kbar_spec(v)
    assert [ids[k] for k in want[[L0, L1], 0]] == ["b", "b"] and want[P, 0] == -1
    assert [ids[k] for k in k_star(v)[[L0, L1]]] == ["a", "a"]
    assert np.array_equal(c2_base_contracts(v), want)
    assert np.array_equal(c2_base_contracts(v), contracts.c2_contract_table(v, insure=False)["kbar"])
    pol = RetroRentingStyle(use_current_slot=True, contract_rule="c2")
    pol.reset(v, np.random.default_rng(0))
    st = pol.sites
    assert np.array_equal(st.kc, want) and [st.contract(l, 0) for l in (L0, L1)] == [int(want[L0, 0]),
                                                                                     int(want[L1, 0])]
    for l in (L0, L1):
        a = float(v.price[l, want[l, 0]])
        assert st.price_of(l, 0) == a and st.score[0, l] == v.llms[0].g * a + v.client_delta_usd_per_h[0, l]
        rent, M, _ = pol._c_M(0, l)
        q = v.llms[0].q_usd_per_h
        assert rent == v.llms[0].g * a / q
        assert M == 60.0 * float(v.beta_tilde_usd[0, l, want[l, 0]]) / (q * v.grid.slow_min)
    assert not st.usable[0, P] and pol.home == [L0]
    res = _run(inst, "BL5", {"use_current_slot": True, "contract_rule": "c2"})
    assert res.leases and all(L.contract == want[L.site, 0] for L in res.leases)
    assert res.metrics["policy"]["contracts"] == want.tolist()
    base = _run(inst, "BL5", {"use_current_slot": True})
    assert {ids[L.contract] for L in base.leases} == {"a"} and "contracts" not in base.metrics["policy"]
    cfg = random_toy_config(np.random.default_rng(7), n_clients=2, two_llms=True)
    instr = build_instance(cfg)
    vr = public_view(instr, "I1")
    assert np.array_equal(c2_base_contracts(vr), _kbar_spec(vr))
    res = _run(instr, "BL5", {"contract_rule": "c2"})
    kr = _kbar_spec(vr)
    client_of = {L.id: int(L.tag.split(":")[1]) for L in res.leases}            # tag bl5:<client>:<instance>
    assert all(L.contract == kr[L.site, int(vr.client_llm[client_of[L.id]])] for L in res.leases)


def test_contract_rule_c2_needs_table(monkeypatch):
    """Without contracts.c2_contract_table the option 'c2' raises PolicyError at reset; 'kstar' never reads it."""
    monkeypatch.delattr(contracts, "c2_contract_table", raising=False)
    inst = build_instance(_ab_config())
    v = public_view(inst, "I1")
    with pytest.raises(PolicyError, match="c2_contract_table"):
        RetroRentingStyle(contract_rule="c2").reset(v, np.random.default_rng(0))
    RetroRentingStyle().reset(v, np.random.default_rng(0))


# ---------------------------------------------------------------- mbb (BL5N)
def _mbb_config(**over) -> dict:
    """The toy with demand 1 in every slot and one announcement, at L0 in slot 8 (contract 'short': tau 5, H 5
    min; load times 300 s at L0 and L1)."""
    return toy_config({"borrowers.clients.0.demand.values": [1] * 24, "lenders.0.R": [8], "lenders.1.R": [], **over})


def test_mbb():
    """BL5 (use_current_slot) hosts at L0 from slot 2; L0 announces in slot 8 (death minute 45). With mbb the
    instance buys a replacement at u_L = latest_prewarm_slot(8, 45, lam_c, grid) = 8 at L1 (L0, cheaper, holds a
    lease under notice), keeps its rule state (no new fetch), the noticed lease is reclaimed at its death (never
    released) and nothing strands; without mbb the death is a forced eviction and the rule re-fetches at 12."""
    inst = build_instance(_mbb_config())
    v = public_view(inst, "I1")
    L0, L1 = site_index(inst, "L0"), site_index(inst, "L1")
    lam = int(lam_ms(v)[0, [L0, L1]].max())
    u = latest_prewarm_slot(8, 45, lam, v.grid)
    assert lam == 300000 and u == 8
    off = _run(inst, "BL5", {"use_current_slot": True})
    assert [(L.site, L.start_slot, L.end_cause) for L in off.leases] == [(L0, 2, "reclaim"), (L0, 12, "horizon")]
    assert off.components["stranding_fb"] > 0
    on = _run(inst, "BL5", {"use_current_slot": True, "mbb": True})
    got = [(L.site, L.start_slot, L.end_min, L.end_cause, L.release_min, L.tag) for L in on.leases]
    assert got == [(L0, 2, 45, "reclaim", None, "bl5:0:1"), (L1, u, 120, "horizon", None, "bl5:0:1:mbb")], got
    assert on.components["stranding_fb"] == 0 and on.components["total"] < off.components["total"]
    rep = on.metrics["policy"]
    assert rep["instances"][0]["events"] == [[2, "fetch"], [8, "detach"], [8, "mbb"]]
    assert {k: rep["mbb"][k] for k in ("detached", "buys", "ok", "failed", "no_site", "noticed_site_used")} == \
        {"detached": 1, "buys": 1, "ok": 1, "failed": 0, "no_site": 0, "noticed_site_used": 0}
    assert rep["mbb"]["lam_c_ms"] == [lam] and rep["counts"]["deaths"] == 1 and rep["counts"]["releases"] == 0
    assert "mbb" not in off.metrics["policy"]


def test_mbb_refused_and_noticed_fallback():
    """A refused replacement (L1 also announced in slot 8, lender option on_unavailable 'refuse') is a forced
    eviction in the slot its result arrives, and the rule re-fetches later; with L1 priced above fallback, L0 is
    the only usable site and holds the lease under notice, and the replacement goes there."""
    inst = build_instance(_mbb_config(**{"lenders.1.R": [8]}))
    L0, L1 = site_index(inst, "L0"), site_index(inst, "L1")
    res = _run(inst, "BL5", {"use_current_slot": True, "mbb": True}, {"on_unavailable": "refuse"})
    rep = res.metrics["policy"]
    assert rep["instances"][0]["events"][:6] == [[2, "fetch"], [8, "detach"], [8, "mbb"], [9, "refused"],
                                                 [9, "forced"], [12, "fetch"]]
    assert rep["mbb"]["failed"] == 1 and rep["counts"]["refused"] == 1
    assert [(L.site, L.start_slot) for L in res.leases] == [(L0, 2), (L0, 12)]
    inst2 = build_instance(_mbb_config(**{"lenders.1.prices.short": 7.5, "lenders.1.prices.long": 7.6}))
    res2 = _run(inst2, "BL5", {"use_current_slot": True, "mbb": True})
    assert res2.metrics["policy"]["mbb"]["noticed_site_used"] == 1
    assert [(L.site, L.start_slot, L.tag) for L in res2.leases][:2] == [(L0, 2, "bl5:0:1"), (L0, 8, "bl5:0:1:mbb")]


# ---------------------------------------------------------------- demand_lag (greedy)
def test_demand_lag():
    """demand_of returns obs.demand itself without a lag and slot t - L's demand with demand_lag L (zeros for
    t < L); the target follows; BL1 with demand_lag 1 makes the decisions of BL1 on the demand shifted by one
    slot (no announcement, so the lender does not depend on the decisions)."""
    inst = build_instance(toy_config())
    v = public_view(inst, "I1")
    seq = [0.0, 1.5, 0.3, 2.0, 0.0, 1.0]
    for lag in (0, 1, 2):
        pol = GreedyLease(demand_lag=lag)
        pol.reset(v, np.random.default_rng(0))
        for t, D in enumerate(seq):
            obs = SlowObs(t=t, minute=5 * t, demand=np.full((1, 1), D), leases={}, replicas={}, notices=[], ended=[],
                          results=[], site_announced=None, served_prev=np.zeros((inst.J, inst.m)),
                          fallback_prev=np.zeros(1), cost_so_far=0.0)
            if lag == 0:
                assert pol.demand_of(obs) is obs.demand
            want = seq[t - lag] if t >= lag else 0.0
            assert pol.demand_of(obs)[0, 0] == want and list(pol.target(obs)) == [math.ceil(want - 1e-9)], (lag, t)
            pol.act(obs)
    d = toy_config()["borrowers"]["clients"][0]["demand"]["values"]
    quiet = {"lenders.0.R": [], "lenders.1.R": []}
    lagged = _run(build_instance(toy_config(quiet)), "BL1", {"demand_lag": 1})
    shifted = _run(build_instance(toy_config({**quiet, "borrowers.clients.0.demand.values": [0] + d[:-1]})), "BL1", {})
    rec = lambda res: [(L.site, L.contract, L.start_slot, L.release_min, L.end_cause) for L in res.leases]
    assert rec(lagged) and rec(lagged) == rec(shifted)
    assert rec(lagged) != rec(_run(build_instance(toy_config(quiet)), "BL1", {}))


# ---------------------------------------------------------------- registry and driver (C34, C35)
def test_registry_a9_a8p_rows():
    """C34 (design/sublet_v2.md §8.1): A9 and A8P are class-backed ids with runner 'simulate' in MS5B, not in
    POLICY_IDS; A8P_INNER_IDS is A8_INNER_IDS and A9 and equals guard.PROJ_INNER_IDS; A8P's registry defaults are the
    class's; A8's rows and A8_INNER_IDS are unchanged; inner_of, a8_own_inputs, needed_inputs and info_class treat
    A8P as A8 with inner default 'A9' (info class online-I1 + a-priori N, §2.4); A9 needs no driver input and has
    class online-I1."""
    from sublet.algos import guard
    from sublet.algos.a9 import NoticeCriticalRatio
    assert registry.MS5B_IDS == ("A9", "A8P") and not set(registry.MS5B_IDS) & set(registry.POLICY_IDS)
    for pid, cls in (("A9", NoticeCriticalRatio), ("A8P", guard.ProjectedGuarded)):
        e = registry.entry(pid)
        assert e.runner == "simulate" and e.policy_class and registry.resolve(pid) is cls
        assert registry.param_names(pid) == tuple(cls.PARAMS)
    assert (registry.entry("A9").info, registry.entry("A9").inputs) == ("online-I1", ())
    assert (registry.entry("A8P").info, registry.entry("A8P").inputs) == ("inner", registry.INPUTS)
    assert registry.A8_INNER_IDS == ("A7", "A3", "A6", "BL1", "BL5")
    assert registry.A8P_INNER_IDS == registry.A8_INNER_IDS + ("A9",) == guard.PROJ_INNER_IDS
    keys = ("inner", "S_rbar", "safe", "test")
    assert dict(registry.entry("A8").defaults) == {k: guard.Guarded.PARAMS[k] for k in keys}
    assert dict(registry.entry("A8P").defaults) == {k: guard.ProjectedGuarded.PARAMS[k] for k in keys + ("project",)}
    assert "A8P" not in registry.WRAPPERS and "A8P" not in registry.INNER_IDS
    assert registry.inner_of("A8P", {}) == ("A9", {}) and registry.inner_of("A9", {}) is None
    assert registry.inner_of("A8P", {"inner": "BL1", "inner_params": {"backoff_cap": 288}}) == \
        ("BL1", {"backoff_cap": 288})
    assert registry.a8_own_inputs({}, "A8P") == ("N_bound",)
    assert registry.a8_own_inputs({"safe": "fb"}, "A8P") == registry.a8_own_inputs({"S_rbar": 1}, "A8P") == ()
    with pytest.raises(ValueError):
        registry.a8_own_inputs({}, "A9")
    assert registry.needed_inputs("A9", {}) == registry.needed_inputs("A9", {"demand_lag": 1}) == ()
    assert registry.needed_inputs("A8P", {}) == ("N_bound",) and registry.needed_inputs("A8P", {"safe": "fb"}) == ()
    assert registry.needed_inputs("A8P", {"S_rbar": 1, "inner": "A6", "inner_params": {"variant": "theory"}}) == \
        ("N_bound",)
    assert registry.info_class("A9", {}) == "online-I1"
    assert registry.info_class("A8P", {}) == "online-I1 + a-priori N"
    assert registry.info_class("A8P", {"safe": "fb"}) == registry.info_class("A8P", {"S_rbar": 1}) == "online-I1"
    assert registry.info_class("A8P", {"safe": "fb", "inner": "A6", "inner_params": {"variant": "theory"}}) == \
        "online-I1 + a-priori N"
    assert registry.info_class("A8", {}) == "online-I1 + a-priori N" and registry.inner_of("A8", {}) == ("A7", {})
    assert registry.needed_inputs("A8", {}) == ("N_bound",) and registry.needed_inputs("A8", {"safe": "fb"}) == ()


class _FakeA8P:
    """Stands in for guard.ProjectedGuarded in the routing test: records its keywords."""
    PARAMS = {"inner": "A9", "inner_params": {}, "safe": "fb+pd", "S_rbar": "theory", "gamma": 1.0,
              "gamma_T11": 1.7, "test": "T0g", "wind_down": "auto", "reserve": True, "B0": "auto", "kappa": 10.0,
              "abort_at": None, "project": True, "allowance": "alg1"}
    INPUTS = ("N_bound", "on_unavailable")

    def __init__(self, **kw):
        self.kw = kw


def test_make_policy_a8p_routing(monkeypatch):
    """C35: make_policy gives A8P its own N_bound iff S_rbar = 'theory' with R in its safe expert, the inner's driver
    inputs in inner_params (N_bound of an inner A6 with variant 'theory'; none for A9 and BL1) and the run's
    on_unavailable from the run spec's lender model; the inner must be one of A8P_INNER_IDS, and A8 still rejects
    A9; a guarded baseline runs with auto_drain false (§15.1), A8P around A9 or A6 may run with auto_drain true."""
    from sublet.algos import guard
    from sublet.config import ConfigError
    from sublet.drivers import run as drun
    from sublet.instance import units
    assert set(_FakeA8P.PARAMS) == set(guard.ProjectedGuarded.PARAMS)
    real = registry.resolve
    monkeypatch.setattr(registry, "resolve", lambda pid: _FakeA8P if pid == "A8P" else real(pid))
    inst = build_instance(toy_config())
    N = max(len(units(inst).client) * inst.grid.T_slow, 3)
    p = make_policy({"policy": {"id": "A8P", "params": {}}}, inst)
    assert p.kw["N_bound"] == N and p.kw["inner_params"] == {} and p.kw["on_unavailable"] == "sell"
    p = make_policy({"policy": {"id": "A8P", "params": {}}, "lender_model": {"on_unavailable": "refuse"}}, inst)
    assert p.kw["on_unavailable"] == "refuse"
    p = make_policy({"policy": {"id": "A8P", "params": {"S_rbar": 1, "inner": "A6",
                                                         "inner_params": {"variant": "theory"}}}}, inst)
    assert "N_bound" not in p.kw and p.kw["inner_params"] == {"variant": "theory", "N_bound": N}
    p = make_policy({"policy": {"id": "A8P", "params": {"inner": "BL1", "safe": "fb",
                                                         "inner_params": {"backoff_cap": 288}}}}, inst)
    assert "N_bound" not in p.kw and p.kw["inner_params"] == {"backoff_cap": 288}
    p = make_policy({"policy": {"id": "A8P", "params": {"inner_params": {"demand_lag": 1}}}}, inst)
    assert p.kw["N_bound"] == N and p.kw["inner_params"] == {"demand_lag": 1}

    def spec(params, **kw):
        return {"schema_version": 1, "name": "t_a8p", "instance": "toy.json",
                "policy": {"id": "A8P", "params": params}, **kw}
    for bad in ({"inner": "A2"}, {"inner": "A8"}, {"inner": "A8P"}, {"inner": "BL2"}, {"inner": "BL6"},
                {"project_typo": True}, {"inner_params": {"target_typo": 1}}):
        with pytest.raises(ConfigError):
            drun.load_run_spec(spec(bad))
    with pytest.raises(ConfigError):
        drun.load_run_spec({**spec({}), "policy": {"id": "A8", "params": {"inner": "A9"}}})
    for inner in ("BL1", "BL5"):
        with pytest.raises(ConfigError):
            drun.load_run_spec(spec({"inner": inner}, engine={"auto_drain": True}))
    for inner in ("A9", "A6"):
        drun.load_run_spec(spec({"inner": inner}, engine={"auto_drain": True}))


@pytest.mark.parametrize("pid,params", [("A9", {}), ("A8P", {}), ("A8P", {"inner": "BL1"})])
def test_plan_class_p1_and_run_file(pid, params, tmp_path):
    """The case of tests/test_policy_isolation.py::test_plan_class_p1 for the MS5B ids: A9, A8P (inner A9) and A8P
    around BL1 through make_policy on ms2_multi_small.json (half a day, its P1_HORIZON_MIN) run in plan class P1
    (Buy with one replica, Release, Drain, SetAdmission; no GPU-only lease slot) with the engine's invariant checks
    on, and buy leases; drivers.run.run writes the run file with the policy id, the resolved parameters (A8P: project
    true, the inner's id and parameters) and the information class of registry.info_class."""
    from fixtures import policy_actions_recorder
    from sublet.drivers import run as drun
    spec = drun.load_run_spec({"schema_version": 1, "name": f"p1_{pid}", "instance": "ms2_multi_small.json",
                               "overrides": {"time.horizon_min": 720}, "policy": {"id": pid, "params": params}})
    inst, model, ecfg = drun.build(spec, spec["seeds"]["config"][0])
    assert ecfg.check_invariants
    rec = policy_actions_recorder(drun.make_policy(spec, inst))
    res = simulate(inst, rec, model, ecfg, policy_seed=0)
    assert res.invariant_failures == []
    kinds = {type(a).__name__ for _, a in rec.actions}
    assert "Buy" in kinds and kinds <= {"Buy", "Release", "Drain", "SetAdmission"}, kinds
    assert all(a.n_replicas == 1 for _, a in rec.actions if isinstance(a, Buy))
    assert res.metrics["gpu_only_lease_slots"] == 0
    short = {**spec, "name": f"rf_{pid}", "overrides": {"time.horizon_min": 120}, "seeds": {**spec["seeds"]}}
    out = drun.run(short, out_dir=tmp_path)
    files = sorted(tmp_path.glob("*.json"))
    assert len(out) == len(files) == 1 and out[0].invariant_failures == []
    meta = json.loads(files[0].read_text())["meta"]
    assert meta["policy_id"] == pid
    assert meta["info_class"] == registry.info_class(pid, meta["params"]) == \
        ("online-I1" if pid == "A9" else "online-I1 + a-priori N")
    if pid == "A8P":
        inner = params.get("inner", "A9")
        assert meta["params"]["project"] is True and meta["params"]["inner"] == inner
        assert meta["params"]["inner_params"] == registry.resolve(inner)().params()
        assert meta["driver_inputs"]["N_bound"] > 0
    else:
        assert meta["params"] == registry.resolve("A9")().params() and meta["driver_inputs"] == {}


@pytest.mark.parametrize("inner", ["A9", "A8P"])
def test_siloed_a9_a8p(inner, tmp_path):
    """SILOED around A9 and A8P (design/sublet_v2.md §3: E3 runs Sublet and A9 siloed) through drivers.run.run on
    ms2_multi_small.json (two hours): one run file per borrower with the inner id, its information class and, for
    A8P, the N_bound of the borrower's sub-instance (M6); no invariant failure."""
    from sublet.drivers import run as drun
    from sublet.instance import units
    spec = {"schema_version": 1, "name": f"sil_{inner}", "instance": "ms2_multi_small.json",
            "overrides": {"time.horizon_min": 120}, "policy": {"id": "SILOED", "params": {"inner": inner}}}
    d = drun.run(spec, out_dir=tmp_path)[0]
    assert d["invariant_failures"] == [] and len(d["results"]) == len(d["instances"]) == 4
    want = "online-I1" if inner == "A9" else "online-I1 + a-priori N"
    summ = json.loads(next(tmp_path.glob("*_sum.json")).read_text())["meta"]
    assert (summ["inner_id"], summ["info_class"]) == (inner, want)
    for bi, sub in enumerate(d["instances"]):
        meta = json.loads(next(tmp_path.glob(f"*_b{bi}.json")).read_text())["meta"]
        assert (meta["inner_id"], meta["info_class"]) == (inner, want)
        if inner == "A8P":
            assert meta["driver_inputs"]["N_bound"] == max(len(units(sub).client) * sub.grid.T_slow, 3)
            assert meta["params"]["inner"] == "A9" and meta["params"]["project"] is True
        else:
            assert meta["driver_inputs"] == {}
