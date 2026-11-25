"""Tests of sublet/config.py (design/sim_spec.md §2.3, §4; §9.2)."""
import numpy as np
import pytest

from fixtures import DELETE, TOY_PATH, load_json, toy_config

from sublet.config import ENGINE_FIELDS, ConfigError, config_hash, load_config, rng_streams
from sublet.paths import ANALYSIS_OUT

A11 = ANALYSIS_OUT / "a11_calibration.json"
REGIONS5 = ["north_america", "europe", "east_asia", "south_southeast_asia", "south_america"]
ADJ_S7 = [("north_america", "europe"), ("north_america", "south_america"), ("north_america", "east_asia"),
          ("europe", "south_southeast_asia"), ("east_asia", "south_southeast_asia")]


def _contract(cfg, cid):
    return next(c for c in cfg["contracts"] if c["id"] == cid)


def test_toy_loads_with_defaults():
    """The toy config resolves, with the §4.2 defaults filled in for the fields it omits."""
    cfg = load_config(TOY_PATH)
    assert cfg["schema_version"] == 1 and cfg["name"] == "toy" and cfg["seed"] == 7
    assert cfg["billing"] == "prepaid_D"
    assert cfg["time"]["slow_slot_min"] == 5 and cfg["time"]["fast_slot_min"] == 5
    assert cfg["time"]["horizon_min"] == 120 and cfg["time"]["start_minute_of_week"] == 0
    assert cfg["time"]["clock_alignment"] == "random_offset"
    assert cfg["prices"]["a0_usd_per_gpu_h"] == 2.85 and cfg["prices"]["q_gpu_usd_per_gpu_h"] == 7.15
    assert cfg["prices"]["a_protected_usd_per_gpu_h"] == 5.97
    assert cfg["prices"]["revocable_price"] == "explicit" and cfg["prices"]["buffer_quantile"] == "p99"
    assert [c["id"] for c in cfg["contracts"]] == ["short", "long", "prot"]
    # klass default: calib.contract_klass (a11 menu() rule): tau = slot and H <= 2 -> spot-like, ...
    assert [c["klass"] for c in cfg["contracts"]] == ["general", "general", "protected"]
    assert _contract(cfg, "prot")["prepaid_min"] == 5
    assert cfg["protected_per_region"]["enabled"] is False
    lm = cfg["lender_model"]
    assert (lm["schedule"], lm["information"], lm["on_unavailable"], lm["violations"]) == \
        ("trace", "I1", "sell", "absorb")
    assert lm["merge_identical_layers"] is False and lm["params"] == {}     # default off (§10 S32)
    assert cfg["costs"]["phi"] == 1.0 and cfg["costs"]["beta_jl_usd"] == 0.0
    assert cfg["costs"]["kappa_infinite"] is False
    st = cfg["stranding"]
    assert st["mu_over_beta_tilde"] == 1.0 and st["kv_share"] == 0.0
    assert st["mu_fl_over_beta_tilde"] == 0.0 and st["pi_over_q"] == 0.0 and st["W_f_min"] == 0
    assert st["beta_tilde_ref"] == {"price": "a0", "load_time": "median_site"}
    assert cfg["units"]["per_replica"] == 4
    assert set(cfg["engine"]) <= set(ENGINE_FIELDS)
    b = cfg["bench"]
    assert b["grid"] == "slow" and b["time_limit_s"] == 60 and b["mip_rel_gap"] == 1e-9
    assert b.get("max_vars", 200000) == 200000
    assert cfg["regions"]["list"] == ["r0"] and cfg["regions"]["default_slo_class"] == "strict"
    # loading twice gives the same resolved dict (and hash)
    assert config_hash(load_config(TOY_PATH)) == config_hash(cfg)

    # a stripped toy: the omitted top-level fields take their §4.2 defaults
    a11 = load_json(A11)["inputs"]
    stripped = toy_config({"seed": DELETE, "billing": DELETE, "costs": DELETE, "units": DELETE,
                           "engine": DELETE, "bench": DELETE, "stranding": DELETE,
                           "protected_per_region": DELETE, "prices.a0_usd_per_gpu_h": DELETE,
                           "prices.q_gpu_usd_per_gpu_h": DELETE, "prices.a_protected_usd_per_gpu_h": DELETE,
                           "prices.revocable_price": DELETE, "time.start_minute_of_week": DELETE})
    c2 = load_config(stripped)
    assert c2["seed"] == 0 and c2["billing"] == "prepaid_D"
    assert c2["time"]["start_minute_of_week"] == 0
    assert c2["prices"]["a0_usd_per_gpu_h"] == a11["a0"] == 2.85
    assert c2["prices"]["q_gpu_usd_per_gpu_h"] == a11["q_GPU"] == 7.15
    assert c2["prices"]["a_protected_usd_per_gpu_h"] == a11["a_p"] == 5.97
    assert c2["prices"]["revocable_price"] == "ir"
    assert c2["costs"] == {"phi": 1.0, "beta_jl_usd": 0.0, "kappa_infinite": False}
    assert c2["units"] == {"per_replica": 8}
    assert c2["protected_per_region"]["enabled"] is False
    st = c2["stranding"]
    assert (st["mu_over_beta_tilde"], st["kv_share"], st["mu_fl_over_beta_tilde"], st["pi_over_q"],
            st["W_f_min"]) == (1.0, 0.0, 0.0, 0.0, 0)
    assert st["beta_tilde_ref"] == {"price": "a0", "load_time": "median_site"}
    assert set(c2["engine"]) <= set(ENGINE_FIELDS)
    defaults = {"auto_drain": False, "record_routing": False, "check_invariants": True, "tol": 1e-9}
    assert all(c2["engine"][k] == v for k, v in defaults.items() if k in c2["engine"])
    bench = {"grid": "slow", "time_limit_s": 300, "mip_rel_gap": 1e-4, "max_vars": 200000}
    assert all(c2["bench"].get(k, v) == v for k, v in bench.items())

    # regions omitted: the five a4b regions, the S7 adjacency, relaxed clients, delta_1/q = 0.05
    noreg = toy_config({"regions": DELETE, "lenders.0.region": "europe", "lenders.1.region": "europe",
                        "lenders.2.region": "europe", "borrowers.clients.0.region": "europe",
                        "borrowers.clients.0.slo_class": "relaxed"})
    c3 = load_config(noreg)
    assert c3["regions"]["list"] == REGIONS5
    assert {frozenset(p) for p in c3["regions"]["adjacency"]} == {frozenset(p) for p in ADJ_S7}
    assert c3["regions"]["default_slo_class"] == "relaxed"
    assert c3["regions"]["relaxed_routing_cost_over_q"] == 0.05


@pytest.mark.parametrize("path,value", [
    ("foo", 1),
    ("time.foo", 1),
    ("lenders.0.foo", 1),
    ("contracts.0.foo", 1),
    ("borrowers.clients.0.foo", 1),
    ("lender_model.foo", 1),
])
def test_unknown_key_raises(path, value):
    with pytest.raises(ConfigError):
        load_config(toy_config({path: value}))


BAD = {
    "tau_not_multiple_of_slot": {"contracts.0.tau_min": 7},
    "fast_slot_not_dividing_slow": {"time.fast_slot_min": 2},
    "horizon_not_multiple": {"time.horizon_min": 122},
    "protected_with_notice": {"contracts.2.H_min": 5},
    "unknown_contract_in_menu": {"lenders.0.menu": ["short", "nope"]},
    "refuse_with_eager": {"lender_model.on_unavailable": "refuse", "lender_model.schedule": "eager"},
    "refuse_with_adaptive": {"lender_model.on_unavailable": "refuse", "lender_model.schedule": "adaptive"},
    "refuse_with_safe_site": {"lender_model.on_unavailable": "refuse", "lender_model.schedule": "safe_site"},
    "refuse_with_iid_step": {"lender_model.on_unavailable": "refuse", "lender_model.schedule": "iid_step"},
    "params_of_other_schedule_trace": {"lender_model.params": {"p_sh": 0.5}},
    "params_of_other_schedule_iid": {"lender_model.schedule": "iid_step", "lender_model.params": {"p_sh": 0.5}},
    "params_of_other_schedule_correlated": {"lender_model.schedule": "correlated",
                                            "lender_model.params": {"p_sh": 0.5, "D_slots": 2}},
    "unsplit_burstgpt_without_tier": {"borrowers": {"model": "series", "list": [
        {"id": "b1", "series": "burstgpt_1", "week_index": None, "region": "r0", "slo_class": "strict"}]}},
    "kappa_infinite_with_finite_kappa": {"costs.kappa_infinite": True},
}


@pytest.mark.parametrize("name", list(BAD))
def test_bad_values_raise(name):
    with pytest.raises(ConfigError):
        load_config(toy_config(BAD[name]))


def test_rng_streams_deterministic():
    """Same seed, same draws; the four streams are SeedSequence(seed).spawn(4) in the order
    build, lender, policy, bench, and they differ."""
    for seed in (0, 7, 123456):
        a, b = rng_streams(seed), rng_streams(seed)
        assert list(a) == ["build", "lender", "policy", "bench"]
        kids = np.random.SeedSequence(seed).spawn(4)
        draws = {}
        for i, name in enumerate(["build", "lender", "policy", "bench"]):
            x, y = a[name].random(8), b[name].random(8)
            assert np.array_equal(x, y)
            assert np.array_equal(x, np.random.default_rng(kids[i]).random(8))
            draws[name] = x
        vals = list(draws.values())
        assert all(not np.array_equal(vals[i], vals[j]) for i in range(4) for j in range(i + 1, 4))
    assert not np.array_equal(rng_streams(1)["build"].random(4), rng_streams(2)["build"].random(4))


def test_menu_preset_matches_a11():
    """menu_preset 'a11_default' at 5-min slots: ids, tau, H and D of the a11 s5 contracts, plus 'protected'."""
    a11 = load_json(A11)["contracts"]
    cfg = toy_config({"contracts": DELETE, "menu_preset": "a11_default",
                      "lenders.0.menu": ["s5_tau5_H5", "s5_tau60_H0"],
                      "lenders.0.prices": {"s5_tau5_H5": 2.85, "s5_tau60_H0": 3.0},
                      "lenders.1.menu": ["s5_tau5_H2"], "lenders.1.prices": {"s5_tau5_H2": 2.9},
                      "lenders.2.menu": ["protected"]})
    res = load_config(cfg)
    got = {c["id"]: c for c in res["contracts"]}
    want = {k: v for k, v in a11.items() if v.get("slot_min") == 5}
    assert len(want) == 20
    assert set(got) == set(want) | {"protected"}
    for k, v in want.items():
        c = got[k]
        assert c["tau_min"] == v["tau_min"] and c["H_min"] == v["H_min"], k
        assert c["tau_min"] + c["H_min"] == v["D_exact_min"], k
        assert c["tau_min"] in (5, 60) and c["H_min"] in (0, 1, 2, 5, 10, 15, 30, 60, 120, 240)
    p = got["protected"]
    assert p["tau_min"] is None and p["H_min"] == 0 and p["prepaid_min"] == 5
