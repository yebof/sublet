"""Tests of figs/ms7_review_extract.py's versioned output (code/sim/out/ms7/review_extract.json): its counts and
medians agree with the cells it stores and with the registered analyses it was checked against. The run files it
reads (out/e8v2/a/runs/, out/s1v2/*/runs/) are not versioned, so the extract itself is not rebuilt here."""
import json
import statistics
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
OUT = REPO / "code/sim/out/ms7/review_extract.json"

pytestmark = pytest.mark.skipif(not OUT.exists(), reason="review extract not written")


@pytest.fixture(scope="module")
def rx():
    return json.loads(OUT.read_text(encoding="utf-8"))


def _json(rel):
    return json.loads((REPO / rel).read_text(encoding="utf-8"))


def test_meta_records_inputs(rx):
    ins = rx["meta"]["inputs"]
    assert "code/sim/out/e8v2/analysis.json" in ins and "code/sim/out/s1v2/analysis.json" in ins
    assert sum(1 for k in ins if k.startswith("code/sim/out/e8v2/a/runs/pairs/")) == 36
    assert all(len(v) == 64 for v in ins.values())


FURTHER_PARTS = {"e7c/lag": "e7c/lag", "e7o/fwd": "e7o/fwd", "e7o/rev": "e7o/rev", "e7r_eval": "e7r/eval"}


def test_further_runs_on_fb(rx):
    f = rx["guard_fb"]["further"]
    assert f["runs"] == f["s_fb_all"] > 0 and f["aborted"] == 0
    assert set(f["by_part"]) == set(FURTHER_PARTS)
    assert f["runs"] == sum(p["runs"] for p in f["by_part"].values())
    for key, p in f["by_part"].items():
        d = _json(f"code/sim/out/{FURTHER_PARTS[key]}/summary.json")
        g = d["guarded"]
        assert p["runs"] == len(g)
        assert p["s_fb_all"] == sum(1 for r in g if r.get("s_fb_all") is True)
        assert p["aborted"] == sum(1 for r in g if r.get("aborted") is True) == 0
    lo = f["lag_oos"]
    assert lo["runs"] == lo["s_fb_all"] == sum(f["by_part"][k]["runs"] for k in ("e7c/lag", "e7o/fwd", "e7o/rev"))
    assert lo["aborted"] == 0
    e7r = f["by_part"]["e7r_eval"]                   # X4/X5: Sublet and Greedy + guard, 16 weeks x 7 lenders each
    gs = _json("code/sim/out/e7r/eval/summary.json")["guard_summary"]
    assert e7r["runs"] == gs["n_runs"] and gs["aborts"] == 0
    assert set(e7r["by_tag"]) == {"Sublet", "BL1-GP"}


def test_families(rx):
    fam = rx["guard_fb"]["fam_sublet"]
    assert fam["runs"] == sum(v["runs"] for v in fam["by_family"].values())
    assert fam["runs"] == sum(v["runs"] for v in fam["by_src"].values())
    f3 = fam["by_family"]["F3"]
    assert f3["s_fb_all"] == 0 and f3["start_pd_runs"] == f3["runs"] and f3["switch_runs"] == 0
    ex = _json("code/sim/out/ms7/eval_extract.json")["fam_f3"]["by_tag"]["Sublet"]
    assert f3["aborted"] == ex["aborts"] == ex["aborts_at_slot0"]


def test_replay_medians_from_cells(rx):
    rp = rx["replay"]
    cells = [rp["cells"][t][w][c] for t in rp["cells"] for w in rp["cells"][t] for c in rp["cells"][t][w]]
    assert len(cells) == rp["n_cells"] == 36
    for tag, row in rp["by_tag"].items():
        for k in ("r0_fluid", "r0_replay"):
            xs = [c["by_tag"][tag][k] for c in cells]
            assert row[k]["median"] == pytest.approx(statistics.median(xs), rel=1e-12)
            assert row[k]["min"] == pytest.approx(min(xs)) and row[k]["max"] == pytest.approx(max(xs))
    for c in cells:
        assert c["overflow_growth"] == pytest.approx(c["bill_replay_usd"] / c["bl0a_fluid_usd"])
        assert c["overflow_growth"] > 1.0
        for tag, x in c["by_tag"].items():
            assert x["r0_replay"] == pytest.approx(x["C_replay"] / c["bill_replay_usd"])
            assert x["r0_fluid"] == pytest.approx(x["C_fluid"] / c["bl0a_fluid_usd"])


def test_replay_matches_registered_analysis(rx):
    an = _json("code/sim/out/e8v2/analysis.json")
    rp = rx["replay"]
    head = an["headline"]["cells"]
    assert rp["sublet_below_both"] == {"fluid": head["sublet_beats_pair_fluid"],
                                       "replay": head["sublet_beats_pair_replay"]}
    for t in rp["cells"]:
        for w in rp["cells"][t]:
            for c, cell in rp["cells"][t][w].items():
                for tag, x in cell["by_tag"].items():
                    assert x["C_fluid"] == pytest.approx(an["cells"][t][w][c]["fluid"][tag], rel=1e-9)
                    assert x["C_replay"] == pytest.approx(an["cells"][t][w][c]["replay"][tag], rel=1e-9)


def test_sens_points(rx):
    an = _json("code/sim/out/s1v2/analysis.json")
    s = rx["sens"]
    assert set(s["points"]) == set(an["points"])
    gp = [r["guard_price_median"] for r in s["points"].values()]
    assert s["guard_price"]["min"] == min(gp) and s["guard_price"]["max"] == max(gp)
    for pt, r in s["points"].items():
        assert r["margin_median"] == an["points"][pt]["vs_pair"]["delta_median"]
        assert r["weeks_hold"] == an["points"][pt]["vs_pair"]["weeks_hold"]
    assert sorted(s["lose_all_weeks"]) == sorted(pt for pt, r in s["points"].items() if r["weeks_hold"] == 0)
    held = an["n_points_all_weeks_hold"]
    assert held == sum(1 for r in s["points"].values() if r["weeks_hold"] == r["n_weeks"])
    sub = rx["guard_fb"]["s1v2_sublet"]
    assert sub["runs"] == sub["s_fb_all"] and sub["aborted"] == 0
    for pt, weeks in s["near_bill"].items():
        for x in weeks.values():
            assert not x["aborted"] and x["s_fb_all"]


def test_e5_menus(rx):
    an = _json("code/sim/out/e5v2/analysis.json")["headline"]
    e5 = rx["e5"]
    assert e5["short"]["cells"] + e5["long"]["cells"] == an["n_cells"]
    assert e5["short"]["hold"] + e5["long"]["hold"] == an["vs_baselines"]["cells_all_weeks_hold"]


# Part 5 (bounds): Theorem 11's bound with S on FB, ALG <= bill + B(T), run by run (references computed afterwards)
def test_bounds_label_and_inputs(rx):
    b = rx["bounds"]
    assert "computed after the registered analyses" in b["label"] and "B_T" in b["definition"]
    ins = rx["meta"]["inputs"]
    runs = [k for k in ins if k.startswith("code/sim/out/e7o/") and "__tag__Sublet__" in k]
    assert len(runs) == 64      # 2 folds x 2 arms x 16 cells


def test_bounds_oos_cells(rx):
    an = _json("code/sim/out/e7o/analysis.json")
    oos = rx["bounds"]["oos"]
    for fold in ("fwd", "rev"):
        for arm in ("oos", "is"):
            row = oos[fold][arm]
            cells = row["cells"]
            assert sorted(cells, key=int) == [str(c) for c in an["folds"][fold]["cells"]]
            assert row["runs"] == row["s_fb_all"] == sum(c["runs"] for c in cells.values()) > 0
            assert row["aborted"] == 0 and row["max_excess_usd"] <= 0.0
            for k, c in cells.items():
                ref = an["folds"][fold]["per_cell"][arm]["Sublet"][k]
                assert c["W0"] == pytest.approx(ref["W0"], rel=1e-12) and c["W0_mode"] == ref["W0_mode"]
                assert c["max_excess_usd"] <= 0.0 and c["B_T_eq_Wk_T"]
                assert 0.0 < c["B_T_over_bill"]["min"] <= c["B_T_over_bill"]["max"] < 1.0
            above = sorted(k for k, c in cells.items() if c["W0"] > 1.0)
            assert sorted(row["w0_above_1"]) == above
            assert len(above) == len(cells) - an["folds"][fold]["criteria"][arm]["H2"]["cells_below_1"]
            shares = [x for k in above for x in cells[k]["B_T_over_bill"].values()]
            assert row["B_T_over_bill_w0_above_1"] == ({"min": min(shares), "max": max(shares)} if shares else None)
    for arm in ("oos", "is"):
        b = oos["by_arm"][arm]
        assert b["w0_above_1"] == [f"{f}:{k}" for f in ("fwd", "rev") for k in oos[f][arm]["w0_above_1"]]
        assert b["runs"] == b["s_fb_all"] == oos["fwd"][arm]["runs"] + oos["rev"][arm]["runs"] and b["aborted"] == 0
        lo = min(oos[f][arm]["B_T_over_bill_w0_above_1"]["min"] for f in ("fwd", "rev"))
        hi = max(oos[f][arm]["B_T_over_bill_w0_above_1"]["max"] for f in ("fwd", "rev"))
        assert b["B_T_over_bill_w0_above_1"] == {"min": lo, "max": hi}
        assert b["max_excess_usd"] <= 0.0


def test_bounds_sens(rx):
    s = rx["bounds"]["sens"]
    sub = rx["guard_fb"]["s1v2_sublet"]["by_point"]
    assert set(s["by_point"]) == set(sub)
    for key, b in s["by_point"].items():
        assert b["runs"] == sub[key]["runs"] and b["max_excess_usd"] <= 0.0
        assert 0.0 < b["B_T_over_bill"]["min"] <= b["B_T_over_bill"]["max"] < 1.0
    assert s["max_excess_usd"] == max(b["max_excess_usd"] for b in s["by_point"].values())
    near = rx["sens"]["near_bill"]
    assert set(s["near_bill"]) == set(near)
    for pt, weeks in near.items():
        assert set(s["near_bill"][pt]) == set(weeks)
        for wk, x in weeks.items():
            y = s["near_bill"][pt][wk]
            assert y["r0"] == x["r0"] and y["excess_usd"] <= 0.0
            assert y["bound_r0"] == pytest.approx(1.0 + y["B_T_over_bill"]) and y["r0"] <= y["bound_r0"] + 1e-9
    w0p = _json("code/sim/out/s1v2/analysis.json")["w0"]["points"]
    assert set(s["w0"]) == {k.split(":", 1)[1] for k in sub if k.startswith("w0:")} and set(s["w0"]) <= set(w0p)
    for pt, weeks in s["w0"].items():
        for wk, r in weeks.items():
            assert r["W0"] == pytest.approx(w0p[pt]["W0"]["Sublet"][wk], rel=1e-12)
            assert r["W0_a9"] == pytest.approx(w0p[pt]["W0"]["A9"][wk], rel=1e-12)
            assert r["gap"] == pytest.approx(r["bound_r0"] - r["W0"]) and r["gap"] >= -1e-9
    hi = [r for p in s["w0"].values() for r in p.values() if r["W0_a9"] > 1.0]
    assert s["w0_a9_above_1"]["weeks"] == len(hi) > 0
    assert s["w0_a9_above_1"]["gap_max"] == max(r["gap"] for r in hi)


def test_bounds_greedy_guard_weeks(rx):
    g = rx["bounds"]["gp_week"]
    rows = _json("code/sim/out/figs/sf_e7_decomp.json")["data"]["tables"]["e7v2_weeks"]
    ref = next(r for r in rows["rows"] if r["tag"] == "BL1-GP")["W0"]["values"]
    weeks = rows.get("weeks") or sorted(g, key=int)
    assert [g[w]["W0"] for w in weeks] == pytest.approx(ref, rel=1e-12)
    sm = rx["bounds"]["gp_week_summary"]
    assert sm["W0_max"] == max(ref) and g[sm["W0_max_week"]]["W0"] == sm["W0_max"]
    assert all(r["gap"] >= -1e-9 and r["gap"] == pytest.approx(r["bound_r0"] - r["W0"]) for r in g.values())
    share = _json("code/sim/out/ms7/eval_extract.json")["allowance"]["sublet_week_main"]["B_T_over_bl0a_max"]
    assert sm["B_T_over_bill_max"] == pytest.approx(share, rel=1e-9)     # B_peak depends on demand and sites only
