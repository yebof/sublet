"""Tests of sublet/traces/ (design/sim_spec.md §3.4.2, §3.9; §9.2)."""
import numpy as np
import pytest

from fixtures import load_json

from sublet.paths import ANALYSIS_OUT
from sublet.traces import borrowers, lenders

SPOT_L7 = ["a1:A100-SXM4-80GB", "a1:A800-SXM4-80GB", "a1:GPU-series-2", "a1:H800"]
MAAS20 = [f"a2:c{i:02d}" for i in range(20)]
# §10 S34: chosen site (first 8 hex digits) and its share of the cluster's mean slack, a12_sim_inputs.json
MAAS_MULTI_SITE = {"c00": ("a7c1032f", 0.63061), "c01": ("6674f859", 0.50337), "c06": ("f32ff241", 0.44213),
                   "c13": ("8f1ad249", 0.40006), "c16": ("941df8d8", 0.73074)}


def test_slack_shapes():
    """6 a1 series of 50,993 slots and 20 a2 series of 2,016 slots, equal to the npz arrays."""
    z1 = np.load(ANALYSIS_OUT / "a1_slack_series.npz")
    z2 = np.load(ANALYSIS_OUT / "a2_slack_series.npz")
    assert lenders.lender_names("maas20") == MAAS20
    assert lenders.lender_names("spot_L7") == SPOT_L7
    assert lenders.lender_names("all24") == MAAS20 + SPOT_L7
    spot_all = lenders.lender_names("spot_all")
    assert sorted(spot_all) == sorted(f"a1:{k}" for k in z1.files) and len(spot_all) == 6
    assert lenders.lender_names() == lenders.lender_names("all24")
    for name in spot_all:
        s = lenders.slack(name)
        assert s.shape == (50993,) and s.dtype == np.float64
        assert np.array_equal(s, z1[name[3:]].astype(np.float64))
        assert lenders.lender_kind(name) == "spot"
    for name in MAAS20:
        s = lenders.slack(name)
        assert s.shape == (2016,) and s.dtype == np.float64
        assert np.array_equal(s, z2[name[3:]].astype(np.float64))
        assert lenders.lender_kind(name) == "maas"


def test_wildchat_profiles():
    """wildchat('early') equals a4b borrower_model.early; p_o has length 168 and mean 1; sum r_oj = 1."""
    ref = load_json(ANALYSIS_OUT / "a4b_wildchat_weekly.json")["borrower_model"]["early"]
    p_o, r_oj = borrowers.wildchat("early")
    assert set(p_o) == set(ref["p_o"]) and set(r_oj) == set(ref["r_oj"])
    for o, p in p_o.items():
        p = np.asarray(p)
        assert p.shape == (168,)
        assert np.array_equal(p, np.asarray(ref["p_o"][o], dtype=float))
        assert abs(p.mean() - 1.0) <= 1e-6, (o, p.mean())
    for o, by_tier in r_oj.items():
        assert set(by_tier) == {"M", "L"}
        for j, v in by_tier.items():
            assert v == ref["r_oj"][o][j]
    assert abs(sum(v for t in r_oj.values() for v in t.values()) - 1.0) <= 1e-9


def test_xi_unit_mean_per_cell():
    """mean of xi(x) is 1 in every hour-of-week cell with a positive profile; 1.0 where it is 0."""
    rng = np.random.default_rng(3)
    N = 2 * 10080 + 1234
    x = rng.gamma(2.0, 1.0, size=N) * (rng.random(N) < 0.9)
    i = np.arange(N)
    cell = (i // 60) % 168
    x[cell == 5] = 0.0                      # a cell with a zero profile
    prof = borrowers.hour_of_week_profile(x)
    assert prof.shape == (168,)
    for h in range(168):
        assert abs(prof[h] - x[cell == h].mean()) <= 1e-12 * max(1.0, x[cell == h].mean())
    xi = borrowers.xi(x)
    assert xi.shape == x.shape
    for h in range(168):
        m = cell == h
        if prof[h] > 0:
            assert abs(xi[m].mean() - 1.0) <= 1e-9, h
        else:
            assert np.all(xi[m] == 1.0)
    w = borrowers.weighted(borrowers.BorrowerSeries("t", np.array([1.0, 2.0]), np.array([3.0, 4.0]),
                                                    np.array([1.0, 1.0]), None), 0.5)
    assert np.array_equal(w, np.array([3.5, 5.0]))


@pytest.mark.needs_a12
def test_minute_io_reproduces_a3():
    """in + out of a12_minute_io.npz equals a3_minute_series.npz on every a3 series (exact)."""
    z3 = np.load(ANALYSIS_OUT / "a3_minute_series.npz")
    names = set(borrowers.series_names())
    for name in z3.files:
        assert name in names
        s = borrowers.load_series(name)
        assert s.inp.shape == s.out.shape == s.req.shape == z3[name].shape
        assert np.array_equal(s.inp + s.out, z3[name]), name
    chk = load_json(ANALYSIS_OUT / "a12_sim_inputs.json")["checks"]["reproduce_a3"]
    diffs, flags = [], []

    def walk(v, key=""):
        if isinstance(v, dict):
            for k, x in v.items():
                walk(x, k)
        elif isinstance(v, list):
            for x in v:
                walk(x, key)
        elif isinstance(v, bool):
            flags.append(v)
        elif isinstance(v, (int, float)) and "diff" in key:
            diffs.append(v)
    walk(chk)
    assert len(diffs) >= len(z3.files) and all(v == 0 for v in diffs) and all(flags), chk


@pytest.mark.needs_a12
def test_burstgpt_split_sums():
    """The four splits of burstgpt_<i> (ChatGPT / GPT-4 x conv / api) sum to the unsplit series."""
    names = set(borrowers.series_names())
    for i in (1, 2, 3):
        base = borrowers.load_series(f"burstgpt_{i}")
        parts = [borrowers.load_series(f"burstgpt_{i}__{m}__{t}")
                 for m in ("ChatGPT", "GPT-4") for t in ("conv", "api")
                 if f"burstgpt_{i}__{m}__{t}" in names]
        assert len(parts) == 4, (i, sorted(n for n in names if n.startswith(f"burstgpt_{i}__")))
        for f in ("inp", "out", "req"):
            tot = np.sum([getattr(p, f) for p in parts], axis=0)
            assert tot.shape == getattr(base, f).shape
            assert np.array_equal(tot, getattr(base, f)), (i, f)
        assert base.start_utc is None


@pytest.mark.needs_a12
def test_maas_cluster_map():
    """20 entries c00..c19 with one site_id each; groups('site_id') maps them to 'site:<site_id>'. §10 S34:
    the chosen site holds the largest share of the cluster's mean slack (site_share), the shares cover
    every site of the entry and sum to 1, n_site_ids matches them, and a single-site cluster has share 1.
    corr_groups_dS: the components of corr(dS) > 0.2 over the a2 week, recomputed here from
    a2_slack_series.npz."""
    J = load_json(ANALYSIS_OUT / "a12_sim_inputs.json")
    mc = J["maas_clusters"]
    assert [e["npz_key"] for e in mc] == [f"c{i:02d}" for i in range(20)]
    assert all(e["site_id"] is not None and not isinstance(e["site_id"], list) for e in mc)
    for e in mc:
        sh = e["site_shares"]
        assert e["n_site_ids"] == len(sh) == len(e["sites"]) and set(sh) == {x["site_id"] for x in e["sites"]}
        assert abs(sum(sh.values()) - 1.0) <= 1e-9 and all(v >= 0 for v in sh.values()), e["npz_key"]
        assert sh[e["site_id"]] == e["site_share"] == max(sh.values()), e["npz_key"]
        if e["n_site_ids"] == 1:
            assert sh == {e["site_id"]: 1.0}
    # the S34 outcome for the five multi-site clusters (mean-slack shares over days 140-146; the earlier
    # rule, most online GPU-hours, chose fe1a1f3a, 6674f859, 6674f859, 5e0fc6f8 and 53161150)
    multi = {e["npz_key"]: (e["site_id"][5:13], e["site_share"]) for e in mc if e["n_site_ids"] > 1}
    assert sorted(multi) == list(MAAS_MULTI_SITE)
    for k, (site, share) in MAAS_MULTI_SITE.items():
        assert multi[k][0] == site and abs(multi[k][1] - share) <= 1e-4, (k, multi[k])
    cg = J["corr_groups_dS"]
    assert cg["threshold"] == 0.2
    with np.load(ANALYSIS_OUT / "a2_slack_series.npz") as z:
        keys = list(z.files)
        dS = {k: np.diff(z[k].astype(float)) for k in keys}
    adj = {k: set() for k in keys}
    for i, a in enumerate(keys):
        for b in keys[i + 1:]:
            with np.errstate(invalid="ignore", divide="ignore"):    # a constant series gives NaN: no edge
                c = np.corrcoef(dS[a], dS[b])[0, 1]
            if c > 0.2:
                adj[a].add(b)
                adj[b].add(a)
    comps, seen = [], set()
    for k in keys:
        if k in seen:
            continue
        stack, comp = [k], set()
        while stack:
            x = stack.pop()
            if x not in comp:
                comp.add(x)
                stack.extend(adj[x] - comp)
        seen |= comp
        comps.append(sorted(comp))
    assert sorted(cg["groups"]) == sorted(comps)
    assert sorted(x for g in cg["groups"] for x in g) == keys
    g = lenders.groups("site_id")
    for e in mc:
        assert g[f"a2:{e['npz_key']}"] == f"site:{e['site_id']}"
    for name in lenders.lender_names("spot_all"):
        assert g[name] == name
    g0 = lenders.groups("none")
    assert all(g0[n] == n for n in g0) and set(MAAS20) <= set(g0)
    ga = lenders.groups("all")
    assert set(ga.values()) == {"all"} and set(MAAS20) <= set(ga)


@pytest.mark.needs_raw
@pytest.mark.slow
def test_load_requests_smoke():
    r = borrowers.load_requests("azure2024_conv", n_max=1000)
    assert {"t_s", "inp", "out"} <= set(r)
    assert len(r["t_s"]) == len(r["inp"]) == len(r["out"]) == 1000
    assert np.all(np.diff(r["t_s"]) >= 0)
    assert r["t_s"][0] >= 0
