"""Tests of the exact C2 game on the finer H grid (design/sim_spec_ms3.md §6.6, §10 row test_c2_grid.py).

- the grid builder gives exactly the floats of por_default.py's H_BASE (round(i / 20, 12) and round(i / 10, 12), never
  0.05 * i), and lambda = inputs.lambda_default of code/theory_checks/c2/out/por_default.json, so that T = Hs + 13 and
  Rmax = Hs + 6 are the same floats as there; the cell counts of §6.6 (29 main cells, 330 supplement cells);
- game.json's meta.hstar.1.0.715 is por_default.json's Hstar_formula at mu = 1, lambda = 0.715 (C2-T4's threshold);
- E2-1 (slow): the game reproduces table_por_switch_beta's CR at mu = 1, lambda_default, Hs = H_BASE exactly
  (1e-12).
"""
import pytest

from sublet.experiments import e2


def test_grid_floats_and_counts():
    por = e2.por()
    gi = e2.game_inputs()
    assert gi["LAM"] == por["inputs"]["lambda_default"] and gi["AL"] == por["inputs"]["alpha"]
    assert gi["AP"] == por["inputs"]["alpha_p"] and gi["BW"] == por["inputs"]["bw_default"]
    assert gi["BS"] == 1.65 * (1 - por["inputs"]["alpha"]) and gi["BS"] == por["derived"]["beta_s"]
    base = e2.h_base()
    assert base == [0.0, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0]          # por_default.py H_BASE
    lam_key = e2.num(gi["LAM"])
    assert lam_key == "0.715" and e2.lam_keys()[lam_key] == gi["LAM"]
    main = e2.game_grid("beta", 1.0, lam_key)
    assert all(h in main for h in base)                                  # the same floats, not 0.05 * i
    assert 0.75 in main and 0.7500000000000001 not in main
    for h in base:
        hs = next(x for x in main if x == h)
        assert hs + 13.0 == h + 13.0 and hs + 6.0 == h + 6.0
    n_main = sum(1 for g in main.values() if "main" in g)
    assert n_main == 29                                                  # 26 points to 1.25 plus 1.5, 2, 3 (M24)
    supp = 0
    for switch, mu, lk in e2.game_jobs_params():
        supp += sum(1 for g in e2.game_grid(switch, mu, lk).values() if "supp" in g)
    assert supp == 330                                                   # §6.6
    assert len(e2.game_jobs_params()) == 10
    assert sorted(set(e2.game_grid("beta", 2.0, "0").keys()))[-1] == 6.0
    assert sorted(set(e2.game_grid("beta", 0.5, "0").keys()))[-1] == 2.0


def test_hstar_meta():
    m = e2.game_meta()
    gi = e2.game_inputs()
    row = next(r for r in e2.por()["table_por_switch_beta"] if r["mu"] == 1.0 and r["lam"] == gi["LAM"])
    h = m["hstar"]["1"]["0.715"]
    assert h["H_beta"] == pytest.approx(row["Hstar_formula"], rel=1e-12)
    assert h["H_min"] == pytest.approx(h["H_beta"] * gi["min_per_beta_tilde"], rel=1e-15)
    assert sorted(m["hstar"]) == ["0.2", "0.5", "1", "2"] and sorted(m["hstar"]["1"]) == ["0", "0.715"]
    assert gi["min_per_beta_tilde"] == pytest.approx(90.0 * (gi["AL"] + gi["PHI"]) / 60.0, rel=1e-15)


@pytest.mark.slow
def test_e2_1_reproduces_table_por():
    """E2-1: the 8 H_BASE cells at mu = 1, lambda = inputs.lambda_default, switch beta~ (about 70 s)."""
    gi = e2.game_inputs()
    rows = [e2._game_cell(("beta", 1.0, gi["LAM"], h, gi)) for h in e2.h_base()]
    chk = e2.check_e2_1(rows)
    assert chk["pass"], chk
    assert chk["max_abs_diff"] <= 1e-12 and not chk["missing_Hs"]
    assert [r["plan_type"] for r in rows] == [r["plan_type"] for r in sorted(
        (x for x in e2.por()["table_por_switch_beta"] if x["mu"] == 1.0 and x["lam"] == gi["LAM"]),
        key=lambda x: x["Hs"])]
