"""Tests of the out-of-sample calibration keys (MS7 C55; design/ms7/plan.md §3 X2, design/ms7/feasibility/oos.md §4
items 1-4 and 8): config.py's lenders[].calib_slots and the regional borrowers' wildchat_model 'a4c_fit',
p_o_week, demand_fit and gamma; instance.py's calibration window and fit-period demand; traces/borrowers.py's
WildChat week loader; code/analysis/a4c_wildchat_weeks.py's output.

Quick (no a12 outputs):
- frozen: the toy config's resolved-config hash and instance hash equal those measured at HEAD before C55
  (a pristine copy of code/ at commit 56b847be), and no resolved config carries a C55 key that it was not given;
- calib_slots on an inline trace lender: B = b x the calibration window's mean slack with b the P99 envelope of the
  window (calib.buffer_curve), v_top the P25 of the window's lendable slack, the IR prices a0 / (1 - b) of the
  window, and the replay over the whole series at the offset (S, S_lend = (S_full - B)^+); calib_slots [0, N] builds
  the instance of no calib_slots (same hash); a window too short for the menu's longest lender window, bad bounds and
  a synthetic lender's own calib_slots raise ConfigError; lender_defaults' calib_slots applies to trace lenders only;
  the resolved config carries calib_slots only when set and resolves to itself;
- a4c's output: 73 full weeks, 37 fit, Monday starts, the fit window before the first held-out week, each week's
  profile of mean 1, the non-pooled regions' profiles equal a4c's separable() of the week's counts and the pooled
  regions' that of their pool window's counts, the fit model 'a4c_fit' through traces.borrowers.wildchat, and the
  constants e7o takes from it.
With the a12 outputs (needs_a12):
- frozen: the hashes of the shipped configs and of E7 week instances (seeds 1, 301, 101; horizons 10080, 120,
  4320) as measured before C55;
- p_o_week swaps only the evaluated demand's profile (the instance with wildchat_week patched to return the averaged
  p_o equals the instance without the key); a demand_fit equal to the evaluated horizon's own sources and minutes
  gives the same demand, C0_loads and peak_loads as no demand_fit; a pinned gamma equal to the computed one gives
  the same demand, twice it twice the demand (bit for bit); with gamma pinned the demand does not depend on the
  lender calibration (the e7o arms); bad values raise ConfigError.
"""
import copy
import json
import sys

import numpy as np
import pytest

from fixtures import SIM, inline_trace_lender, toy_config

from sublet import calib
from sublet.config import ConfigError, config_hash, load_config
from sublet.instance import build_instance
from sublet.experiments.q44_study import instance_hash
from sublet.traces import borrowers as tb

ANALYSIS = SIM.parents[1] / "code" / "analysis"
A4C = ANALYSIS / "out" / "a4c_wildchat_weeks.json"
# measured at HEAD 56b847be before C55 (scratch hashes.py on a pristine `git archive` copy of code/): config_hash of
# the resolved config and q44_study.instance_hash of the built instance
FROZEN = {
    "toy.json": ("07105b6e447c805df9ecd0a8f975474934b1f0c219964eba58cb0a6d68864458",
                 "5ffa0b9659c66f8beb2d5a51b010b60f6ba2b751bfcf0607851d2e36fefb6b87"),
    "example_1day.json": ("a3a2ab1363efb67760357a7dbcba15deea3d9a5e8695972524176009599bd630",
                          "29e7d7141c1399e2780c9ffda1cade6bc5cf89e0a406aab95408d938e0eb01a3"),
    "ms2_multi_small.json": ("86b8709154f92c8e2a500f5509b4e6d88f57561d8e746606510aed36177df5c3",
                             "a00f1d62a04f2c73d80aa384caca8de8225127ad39390ce9c5d26227f9e4664c"),
    "ms2_single_site.json": ("ec9c96496ee86fc1f3ed0eed6c89eff1b6b10039814f090b3470e33d3ca4ad5c",
                             "cbf8a8d6cb475a89ed021646001ff6f92d2492e9278f5289df5157bbff958ea0"),
    "q44_spot_1day.json": ("5aca791cfcfb132ab91897842dac863efd4898d9b3ae7747dc0a012459081064",
                           "fcdfd26c622a4f70fff9e9c57b9e9617db263292bea54ba90d8c19dfe1a7a98f"),
    "bench_e7r.json": ("f3ab9d0e2e8682b743439891472ef371568667014224757745ace20c1e04e0fe",
                       "615d958eda908878ac3ab17ea4c478affa727fd867d83edfcb5e2c92ee036df6"),
    "bench_dp_maas.json": ("8f77025250ddffbdcb3c14cd65b8d20607f157017d298e34af63cf0613d603b0",
                           "459ef53842d68b9a46cdbc4c3e9927e41a7c723efdf1954ba90e2c3f33a521a9"),
    "bench_dp_spot.json": ("ca1cef9f25736314c8fab94b598251392d625caa50f5600b72d718bca46df49e",
                           "ab82333a67c6cb3a3f51351fbe5444601aa38ab2cbbcbdbfff49dfe6099da04e"),
    "bench_e1.json": ("8553b49cb82975dc00b527653239f639c10603944fef9dd41369704dd73f8c20",
                      "29e7d7141c1399e2780c9ffda1cade6bc5cf89e0a406aab95408d938e0eb01a3"),
    "bench_e7s.json": ("93ba86547fc207e050e006eb4cf30176e621a8b10e0cfdcdd636206a7ad9d3cb",
                       "651654fff869533a3f68c8795caafffab0450387275780fe53fa29617c1b4292"),
    "ms3_e10b_trace.json": ("0d9797b8fb98da3647d6ee47be2ac68b262c506df5748573f165cf8ef7b707da",
                            "1cf4cb6e8619fc912dff315b435365428726ba4c43e8977f8490e6adce32dfad"),
}
FROZEN_E7 = {   # (config seed, horizon_min): bench_e7f.json through ms4_common.e7_spec's overrides
    (1, 10080): ("13ec7b8686eaa32655d9aacbf3a165d59348e23409889db1ac8aad5a34eb623d",
                 "f1b5be0fcf6e2cd7e084036bad5796ace7168ee277a2d908072f0152cbb49d5e"),
    (301, 10080): ("cff23545d8fc3a493f702b3fec072fdaf90dc95e9ea416cf5566280ad86fd79c",
                   "2b619e9c729caa92598f444d715a469866c5a5875f57eec7cb8b948f77d4bba6"),
    (101, 120): ("156ab355157ac4ae80956c335d0d06b772e649461a554cdb96c71389c346e825",
                 "037bc069dae13e922b562fb59844552be4254d8e0a1ab54443b3816fb975a848"),
    (301, 4320): ("3f3297d64be0b5353d567778bc1d5be63d0f325ba689d5302f8d7f6b2f3aa490",
                  "67dbe1a031d0769fdac93a72b5b4d05743f6f7985295c73bf2155719fbc2b6ef"),
}
C55_BORROWER_KEYS = ("p_o_week", "demand_fit", "gamma")


def _no_c55_keys(cfg: dict) -> None:
    assert all("calib_slots" not in e for e in cfg["lenders"])
    assert all(k not in cfg["borrowers"] for k in C55_BORROWER_KEYS)


# ---------------------------------------------------------------- frozen hashes
def test_toy_hashes_unchanged():
    cfg = load_config("toy.json")
    assert (config_hash(cfg), instance_hash(build_instance("toy.json"))) == FROZEN["toy.json"]
    _no_c55_keys(cfg)


@pytest.mark.needs_a12
@pytest.mark.parametrize("name", [n for n in FROZEN if n != "toy.json"])
def test_shipped_config_hashes_unchanged(name):
    cfg = load_config(name)
    assert (config_hash(cfg), instance_hash(build_instance(name))) == FROZEN[name]
    _no_c55_keys(cfg)


def _e7_raw(c: int, hz: int) -> dict:
    from sublet.drivers import run as drun
    from sublet.experiments import ms4_common as m4
    raw = drun.instance_config(m4.e7_spec("BL0a", {}, horizon_min=hz))
    raw["seed"] = int(c)
    return raw


@pytest.mark.needs_a12
@pytest.mark.parametrize("key", list(FROZEN_E7))
def test_e7_week_instance_hashes_unchanged(key):
    raw = _e7_raw(*key)
    cfg = load_config(raw)
    assert (config_hash(cfg), instance_hash(build_instance(raw))) == FROZEN_E7[key]
    _no_c55_keys(cfg)


# ---------------------------------------------------------------- calib_slots
# 40 slots of a sawtooth (1-slot drops of 30 GPUs, mean 155) followed by 60 slots of a slow ramp (drops of 1):
# the calibration window [0, 40) sees the deep drops, the whole series a mixture
CAL = [200.0 - 30 * (i % 4) for i in range(40)]
EVAL = [300.0 - (i % 20) for i in range(60)]
SERIES = CAL + EVAL


def _inline_cfg(calib_slots=None, offset: int = 40, defaults: dict = None, **lender) -> dict:
    cfg = toy_config({"time.horizon_min": 40, "borrowers.clients.0.demand.values": [0, 0, 1, 1, 1, 1, 0, 0],
                      "prices.revocable_price": "ir"}, sites=["P"])
    L = inline_trace_lender(SERIES, "X", prices={}, offset=offset, n_layers=2, layer_gpus=8, **lender)
    if calib_slots is not None:
        L["calib_slots"] = list(calib_slots)
    cfg["lenders"] = [L] + cfg["lenders"]
    if defaults is not None:
        cfg["lender_defaults"] = dict(defaults)
    return cfg


def _lender(inst, lid="X"):
    return next(lt for lt in inst.lenders if lt.lender == lid)


def test_calibration_window_buffer_lease_size_and_prices():
    inst = build_instance(_inline_cfg((0, 40)))
    full = build_instance(_inline_cfg())
    S_full, S_cal = np.asarray(SERIES), np.asarray(CAL)
    lt, lf = _lender(inst), _lender(full)
    D = lt.D_max_lender_min
    assert D == lf.D_max_lender_min == 10                          # the toy's 'short' contract: tau 5, H 5
    b = calib.buffer_curve(S_cal, D)["env"][D]["p99"]
    b_full = calib.buffer_curve(S_full, D)["env"][D]["p99"]
    assert lt.B_gpus == pytest.approx(b * S_cal.mean(), rel=1e-12) and b != b_full
    assert lf.B_gpus == pytest.approx(b_full * S_full.mean(), rel=1e-12)
    v_top = int(np.floor(np.percentile(np.maximum(S_cal - lt.B_gpus, 0.0), 25) / 8))
    assert lt.v0 + lt.n_layers == v_top and lt.n_layers == 2
    k = [c.id for c in inst.contracts].index("short")
    l = lt.site_index[0]
    assert inst.price[l, k] == pytest.approx(inst.a0_usd_per_gpu_h / (1.0 - b), rel=1e-12)
    # replay: the whole series at the offset, the fitted buffer
    idx = 40 + np.arange(inst.grid.T_slow)
    assert np.array_equal(lt.S, S_full[idx]) and np.array_equal(lt.S_full, S_full)
    assert np.array_equal(lt.S_lend, np.maximum(S_full[idx] - lt.B_gpus, 0.0))
    assert any("calib_slots" in n and "[0, 40)" in n for n in inst.notes)


def test_calibration_window_of_the_whole_series_is_the_frozen_build():
    a, b = build_instance(_inline_cfg((0, len(SERIES)))), build_instance(_inline_cfg())
    assert instance_hash(a) == instance_hash(b)
    assert a.config["lenders"][0]["calib_slots"] == [0, len(SERIES)] and "calib_slots" not in b.config["lenders"][0]


def test_calibration_window_validation():
    with pytest.raises(ConfigError, match="calib_slots"):
        build_instance(_inline_cfg((0, 2)))                         # D_max 10 min = 2 slots: the window is too short
    for bad in ((10, 10), (5, len(SERIES) + 1), (-1, 10), [3], "0:10"):
        with pytest.raises(ConfigError):
            load_config(_inline_cfg(bad))
    synthetic = dict(toy_config()["lenders"][0], R=[6, 7])         # L0, kind 'synthetic', R inside 8 slots
    for other in (dict(synthetic, calib_slots=[0, 4]), dict(_inline_cfg()["lenders"][1], calib_slots=[0, 4])):
        cfg = _inline_cfg()                                        # lenders X (trace) and P (protected)
        cfg["lenders"] = [e for e in cfg["lenders"] if e["id"] != other["id"]] + [other]
        with pytest.raises(ConfigError, match="only trace lenders take calib_slots"):
            load_config(cfg)


def test_calibration_window_defaults_and_resolution():
    synthetic = dict(toy_config()["lenders"][0], R=[6, 7])
    cfg = _inline_cfg(defaults={"calib_slots": [0, 40]})
    cfg["lenders"].append(synthetic)
    r = load_config(cfg)
    by = {e["id"]: e for e in r["lenders"]}
    assert by["X"]["calib_slots"] == [0, 40] and "calib_slots" not in by["L0"] and "calib_slots" not in by["P"]
    assert config_hash(load_config(r)) == config_hash(r)
    explicit = _inline_cfg((0, 40))
    explicit["lenders"].append(synthetic)
    assert instance_hash(build_instance(r)) == instance_hash(build_instance(explicit))
    assert "calib_slots" not in load_config(_inline_cfg())["lenders"][0]


# ---------------------------------------------------------------- a4c's output and the week loader
def _a4c():
    if str(ANALYSIS) not in sys.path:
        sys.path.insert(0, str(ANALYSIS))
    import a4c_wildchat_weeks
    return a4c_wildchat_weeks


def test_a4c_weeks_and_the_loader():
    from sublet.experiments import e7o
    d = json.loads(A4C.read_text())
    weeks = tb.wildchat_weeks()
    assert len(weeks) == d["n_weeks"] == e7o.WILDCHAT_N_WEEKS == 73
    assert sum(w["split"] == "fit" for w in weeks) == d["n_fit"] == e7o.WILDCHAT_N_FIT == 37
    assert [w["index"] for w in weeks] == list(range(73)) and all(w["active_hours"] >= 150 for w in weeks)
    assert all(w["split"] == ("fit" if w["index"] < 37 else "held_out") for w in weeks)
    import pandas as pd
    assert all(pd.Timestamp(w["start_utc"]).dayofweek == 0 for w in weeks)
    assert d["split_utc"] == weeks[37]["start_utc"] and d["reproduce_a4b_early"]["ok"] is True
    a4c = _a4c()
    pool = set(d["pool_regions"])
    assert pool == {"south_southeast_asia", "south_america"} and d["pool_weeks"] == 4
    for k in (0, 36, 37, 40, 72):
        p = tb.wildchat_week(k)
        assert set(p) == set(e7o.REGIONS)
        a, b = d["pool_window"][k]
        assert b - a == 4 and (a >= 37) == (k >= 37) and (b <= 37 or a >= 37) and a <= k < b
        for o, v in p.items():
            assert v.shape == (168,) and abs(v.mean() - 1.0) < 1e-5 and v.min() >= 0
            C = np.asarray(d["counts"][o], dtype=float)
            want = a4c.separable(C[a:b].sum(0) if o in pool else C[k])[0]
            assert np.max(np.abs(v - want)) <= 1e-6, (k, o)          # rounded to 6 decimals
    with pytest.raises(KeyError):
        tb.wildchat_week(73)
    p_o, r_oj = tb.wildchat("a4c_fit")
    assert set(p_o) == set(r_oj) == set(e7o.REGIONS)
    assert abs(sum(x for v in r_oj.values() for x in v.values()) - 1.0) < 1e-9
    assert all(abs(v.mean() - 1.0) < 1e-4 for v in p_o.values())
    assert d["borrower_model"]["a4c_fit"]["window_utc"][1] == d["split_utc"]


# ---------------------------------------------------------------- demand (needs the a12 outputs)
def _regional(c: int = 101, hz: int = 120, **b) -> dict:
    cfg = load_config(_e7_raw(c, hz))
    cfg["borrowers"].update(copy.deepcopy(b))
    return cfg


@pytest.mark.needs_a12
def test_p_o_week_swaps_only_the_profile(monkeypatch):
    base = _regional()
    week = _regional(p_o_week=40)
    a, b = build_instance(base), build_instance(week)
    assert not np.array_equal(a.clients.demand, b.clients.demand) and week["borrowers"]["p_o_week"] == 40
    p_o, _ = tb.wildchat(base["borrowers"]["wildchat_model"])
    monkeypatch.setattr(tb, "wildchat_week", lambda i: p_o)
    assert instance_hash(build_instance(week)) == instance_hash(a)


@pytest.mark.needs_a12
def test_demand_fit_on_the_evaluated_minutes_is_the_frozen_demand():
    base = _regional()
    b = base["borrowers"]
    lead = b["smoothing_min"] - 1
    fit = {"xi_sources": {o: {"series": v["series"], "offset_min": v["offset_min"]}
                          for o, v in b["xi_sources"].items()},
           "horizon_min": base["time"]["horizon_min"], "start_minute_of_week": base["time"]["start_minute_of_week"]}
    a, f = build_instance(base), build_instance(_regional(demand_fit=fit))
    assert lead == 14 and np.array_equal(a.clients.demand, f.clients.demand)
    for k, st in a.borrower_stats.items():
        g = f.borrower_stats[k]
        assert (g["C0_loads"], g["peak_loads"]) == (st["C0_loads"], st["peak_loads"]) and g["C0_from"] == "demand_fit"
        assert "gamma" not in st and "C0_from" not in st


@pytest.mark.needs_a12
def test_pinned_gamma():
    from sublet.experiments import e7o
    oos = build_instance(e7o.cell_config("fwd", "oos", 0))
    gam = next(iter(oos.borrower_stats.values()))["gamma"]
    pinned = build_instance(e7o.cell_config("fwd", "oos", 0, gamma=gam))
    twice = build_instance(e7o.cell_config("fwd", "oos", 0, gamma=2 * gam))
    is_ = build_instance(e7o.cell_config("fwd", "is", 0, gamma=gam))
    assert instance_hash(pinned) == instance_hash(oos)
    assert np.array_equal(twice.clients.demand, 2 * oos.clients.demand)
    # the arms: the same demand and borrower stats, other lenders (calibration), so other supply
    assert np.array_equal(is_.clients.demand, oos.clients.demand) and is_.borrower_stats == oos.borrower_stats
    sup = [sum(s.capacity_gpus for s in i.sites if s.kind == "layer") for i in (oos, is_)]
    assert sup[0] != sup[1] and all(e.get("calib_slots") for e in oos.config["lenders"] if e["kind"] == "trace")
    assert not any("calib_slots" in e for e in is_.config["lenders"])
    note = [n for n in pinned.notes if "Gamma" in n][0]
    assert "pinned" in note and "C0 from borrowers.demand_fit" in note


@pytest.mark.needs_a12
def test_borrower_key_validation():
    for b, msg in (({"p_o_week": 73}, "p_o_week"), ({"gamma": 0.0}, "gamma"), ({"gamma": -1.0}, "gamma"),
                   ({"wildchat_model": "late"}, "wildchat_model")):
        with pytest.raises(ConfigError, match=msg):
            load_config(_regional(**b))
    base = _regional()
    xs = {o: {"series": "burstgpt_1", "offset_min": 0} for o in base["regions"]["list"]}
    for fit, msg in (({"xi_sources": xs}, "horizon_min"),
                     ({"xi_sources": {**xs, "europe": {"series": "burstgpt_1", "offset_min": "random"}},
                       "horizon_min": 60}, "offset_min"),
                     ({"xi_sources": {k: v for k, v in xs.items() if k != "europe"}, "horizon_min": 60}, "europe"),
                     ({"xi_sources": xs, "horizon_min": 60, "start_minute_of_week": 10080}, "start_minute_of_week"),
                     ({"xi_sources": xs, "horizon_min": 60, "extra": 1}, "unknown key")):
        with pytest.raises(ConfigError, match=msg):
            load_config(_regional(demand_fit=fit))
    r = load_config(_regional(demand_fit={"xi_sources": xs, "horizon_min": 60}, gamma=3, p_o_week=0,
                              wildchat_model="a4c_fit"))
    assert r["borrowers"]["demand_fit"]["start_minute_of_week"] == 0 and r["borrowers"]["gamma"] == 3.0
    assert config_hash(load_config(r)) == config_hash(r)
