"""Tests of the MS3 additions C10-C13 to MS1/MS2 files (design/sim_spec_ms3.md §2.3, §10).

- C10 (config.py, instance.py): costs.beta_jl_usd as {LLM id: USD}; a map with equal values builds the same
  instance as the number (identical arrays and mu); each LLM's own fee fills beta_usd[j, :] and enters mu_j =
  r_mu beta_tilde_ref_j (oracle: hand computation); unknown, missing or invalid ids raise ConfigError.
- C11 (paths.py): import_ref("o1_lb") and import_c2().det_game / .necessity_lb run nothing on import (the
  sha256 of every file in c3/o1/out/, c2/out/ and c2/audit/out/ and the *.pyc files under code/theory_checks/
  are unchanged, nothing is printed) and reproduce the reference outputs: lb_A(16, 8) and lb_C(16, 8) equal
  o1_lb.json 'A' and lb_all equals por_default.json's LB_react_rig at the default inputs (to 1e-12).
- C12 (calib.py): instance_rho on from_core of the tight families equals the family's rho; beta_for_rho reaches
  the target to 1e-9 after a rebuild with the fee map; a target below the calibrated rho raises ConfigError; on
  bench_e1 with M1's menu both reproduce the MS3-spec measurement code/sim/out/ms3spec/e1_rho_probe.json
  (needs_a12).
- C13 (figs/style.py): every SUPP_POLICIES set passes check_policies; no FIGURE_POLICIES set uses the new keys;
  their colors are Okabe-Ito colors and their triples differ from every other key's (tests/test_figs_style.py
  itself is unchanged and is run separately).
"""
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from fixtures import SIM, explicit_client, explicit_llm, toy_config

from sublet import calib, paths
from sublet.config import ConfigError, load_config
from sublet.experiments.q44_study import instance_hash
from sublet.instance import build_instance, from_core

THEORY = SIM.parents[1] / "code" / "theory_checks"
REF_OUT_DIRS = (THEORY / "c3" / "o1" / "out", THEORY / "c2" / "out", THEORY / "c2" / "audit" / "out")
PROBE = SIM / "out" / "ms3spec" / "e1_rho_probe.json"
E1_MENU = {"time.fast_slot_min": 5,                       # M1: E1's menu without s5_tau5_H2, slow grid
           "contracts": [{"id": "s5_tau5_H60", "tau_min": 5, "H_min": 60},
                         {"id": "s5_tau60_H0", "tau_min": 60, "H_min": 0},
                         {"id": "protected", "tau_min": None, "H_min": 0, "prepaid_min": 5}],
           "lender_defaults.menu": ["s5_tau5_H60", "s5_tau60_H0"]}


# ---------------------------------------------------------------- C10: transfer fee per LLM
def _two_llm_config(fee, **over) -> dict:
    """The toy with a second LLM 'L' (g = 2) and a client for it; stranding with r_mu = 2, kv_share 0.25 and
    mu_fl/beta~ = 0.5, so that every mu component scales with beta_tilde_ref."""
    cfg = toy_config(**over)
    cfg["llms"] = [cfg["llms"][0], explicit_llm("L", g=2)]
    dem = cfg["borrowers"]["clients"][0]["demand"]["values"]
    cfg["borrowers"]["clients"].append(explicit_client(dem, llm="L"))
    cfg["costs"]["beta_jl_usd"] = fee
    cfg["stranding"].update(mu_over_beta_tilde=2.0, kv_share=0.25, mu_fl_over_beta_tilde=0.5)
    return cfg


def _arrays(inst) -> dict:
    st = inst.stranding
    return {"beta_usd": inst.beta_usd, "beta_tilde": inst.beta_tilde_usd(), "mu_kv": st.mu_kv_usd,
            "mu_fl": st.mu_fl_usd, "mu_fb": st.mu_fb_usd, "pi": st.pi_usd_per_min, "price": inst.price,
            "lam_s": inst.lam_s}


def test_c10_equal_fees_equal_the_scalar():
    """A fee map with equal values builds the same instance as the number: identical arrays (beta_usd, beta~,
    every mu) and the same q44_study.instance_hash."""
    for fee in (0.0, 0.7):
        a = build_instance(_two_llm_config(fee))
        b = build_instance(_two_llm_config({"L": fee, "M": fee}))
        for k, v in _arrays(a).items():
            w = _arrays(b)[k]
            assert v.dtype == w.dtype and v.shape == w.shape and np.array_equal(v, w), k
        assert instance_hash(a) == instance_hash(b)
    # an MS1 config is unchanged: the number keeps its meaning and its resolved form
    cfg = load_config(toy_config())
    assert cfg["costs"]["beta_jl_usd"] == 0.0


def test_c10_fee_per_llm_and_mu():
    """beta_usd[j, :] is LLM j's fee at every site; beta_tilde_ref_j includes it, so each mu component moves by
    its share of r_mu times the fee (hand computation: mu_kv = kv r_mu bt, mu_fb = (1 - kv) r_mu bt, mu_fl =
    0.5 bt with bt = fee_j + lam_ref / 3600 (g_j a0 + phi g_j q_GPU)); the resolved config keeps the map in
    the order of llms[] and resolves to itself."""
    fee = {"M": 1.25, "L": 4.0}
    base = build_instance(_two_llm_config(0.0))
    inst = build_instance(_two_llm_config(fee))
    assert [x.id for x in inst.llms] == ["M", "L"]
    assert np.array_equal(inst.beta_usd, np.array([[1.25] * inst.m, [4.0] * inst.m]))
    f = np.array([1.25, 4.0])
    st0, st = base.stranding, inst.stranding
    np.testing.assert_allclose(st.mu_kv_usd - st0.mu_kv_usd, 0.25 * 2.0 * f, rtol=0, atol=1e-12)
    np.testing.assert_allclose(st.mu_fb_usd - st0.mu_fb_usd, 0.75 * 2.0 * f, rtol=0, atol=1e-12)
    np.testing.assert_allclose(st.mu_fl_usd - st0.mu_fl_usd, 0.5 * f, rtol=0, atol=1e-12)
    # bt_ref of the toy by hand: median over the revocable lenders of lam_s (300 s at L0 and L1)
    a0, q = 2.85, 7.15
    bt = np.array([1.25 + 300 / 3600 * (1 * a0 + 1 * q), 4.0 + 300 / 3600 * (2 * a0 + 2 * q)])
    np.testing.assert_allclose(st.mu_fb_usd, 0.75 * 2.0 * bt, rtol=1e-12)
    # beta~ = fee + lam / 3600 (g a + phi g q) at every offered (l, k)
    bt_all = inst.beta_tilde_usd()
    ok = np.isfinite(inst.price)
    for j, x in enumerate(inst.llms):
        want = f[j] + inst.lam_s[j][:, None] / 3600 * (x.g * np.where(ok, inst.price, 0) + x.g * q)
        np.testing.assert_allclose(bt_all[j][ok], want[ok], rtol=1e-12)
    cfg = inst.config
    assert cfg["costs"]["beta_jl_usd"] == {"M": 1.25, "L": 4.0} and list(cfg["costs"]["beta_jl_usd"]) == ["M", "L"]
    assert load_config(cfg) == cfg
    assert instance_hash(build_instance(cfg)) == instance_hash(inst)
    assert any("transfer fee per LLM" in n for n in inst.notes)


@pytest.mark.parametrize("fee, match", [
    ({"M": 1.0, "L": 1.0, "X": 1.0}, r"unknown \['X'\]"),
    ({"M": 1.0}, r"missing \['L'\]"),
    ({"M": 1.0, "L": -0.5}, "costs.beta_jl_usd.L"),
    ({"M": 1.0, "L": "a11"}, "costs.beta_jl_usd.L"),
    ({"M": 1.0, "L": float("inf")}, "costs.beta_jl_usd.L"),
    ([1.0, 2.0], "costs.beta_jl_usd"),
])
def test_c10_unknown_or_missing_ids_raise(fee, match):
    with pytest.raises(ConfigError, match=match):
        load_config(_two_llm_config(fee))


# ---------------------------------------------------------------- C11: reference importers
def _sha_tree(dirs) -> dict:
    out = {}
    for d in dirs:
        for p in sorted(Path(d).rglob("*")):
            if p.is_file():
                out[str(p)] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def _pyc_snapshot() -> dict:
    return {str(p): p.stat().st_mtime_ns for p in THEORY.rglob("*.pyc")}


def test_c11_imports_run_nothing():
    """In a fresh interpreter that allows bytecode writing, import_ref('o1_lb') and import_c2() (det_game,
    necessity_lb with alg_star_exact) print nothing and change no file: the sha256 of every file in c3/o1/out/,
    c2/out/ and c2/audit/out/ and the *.pyc files under code/theory_checks/ are the same before and after.
    REF_MODULES keeps its MS2 key set (the MS1/MS2 test of C9 fixes it); o1_lb is the MS3 entry."""
    assert "o1_lb" not in paths.REF_MODULES and paths.MS3_REF_MODULES == {"o1_lb": paths.O1}
    before, pyc = _sha_tree(REF_OUT_DIRS), _pyc_snapshot()
    code = ("import sys; sys.dont_write_bytecode = True; sys.path.insert(0, %r)\n"
            "from sublet import paths\n"
            "sys.dont_write_bytecode = False\n"
            "m = paths.import_ref('o1_lb')\n"
            "ns = paths.import_c2()\n"
            "assert sys.dont_write_bytecode is False\n"
            "names = [m.__name__, ns.det_game.__name__, ns.necessity_lb.__name__,\n"
            "         sys.modules['alg_star_exact'].__name__]\n"
            "print('IMPORTED', *names)\n") % str(SIM)
    env = {k: v for k, v in os.environ.items() if k != "PYTHONDONTWRITEBYTECODE"}
    env["OMP_NUM_THREADS"] = "1"
    out = subprocess.run([sys.executable, "-c", code], cwd=str(SIM), env=env, capture_output=True, text=True,
                         timeout=120)
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip() == "IMPORTED o1_lb det_game necessity_lb alg_star_exact", out.stdout
    assert _sha_tree(REF_OUT_DIRS) == before
    assert _pyc_snapshot() == pyc


def test_c11_reference_values():
    """lb_A(16, 8), lb_C(16, 8) equal o1_lb.json 'A' at rho 16, m 8 (2.9565217391304346 with k 8;
    1.9568965900553659 with p 0.4); det_game.solve_det exists; necessity_lb.lb_all at por_default.json's inputs
    and H = H_s / beta_s equals its table_por_switch_beta LB_react_rig at mu 1, lambda 0.715, H_s 0.5
    (1.6726358111469841) to 1e-12; the modules come from their folders; unknown names still raise."""
    o1 = paths.import_ref("o1_lb")
    c2 = paths.import_c2()
    assert Path(o1.__file__).resolve().parent == paths.O1.resolve()
    assert Path(c2.det_game.__file__).resolve().parent == paths.C2.resolve()
    assert Path(c2.necessity_lb.__file__).resolve().parent == (paths.C2 / "audit").resolve()
    assert hasattr(c2.model, "Params") and hasattr(c2.families, "lb_react")       # the MS2 members are kept
    assert hasattr(c2.model_switch_cost, "opt_cost_bw")
    rows = json.loads((paths.O1 / "out" / "o1_lb.json").read_text())["A"]
    (row,) = [r for r in rows if r["rho"] == 16 and r["m"] == "8"]
    assert row["LB_A"] == 2.9565217391304346 and row["LB_C"] == 1.9568965900553659
    vA, kA = o1.lb_A(16, 8)
    vC, pC = o1.lb_C(16, 8)
    assert (vA, kA) == (row["LB_A"], row["k"]) and kA == 8
    assert float(vC) == row["LB_C"] and pC == row["p"] == 0.4
    assert callable(c2.det_game.solve_det)
    por = json.loads((paths.C2 / "out" / "por_default.json").read_text())
    inp = por["inputs"]
    (r,) = [x for x in por["table_por_switch_beta"] if x["mu"] == 1.0 and abs(x["lam"] - 0.715) < 1e-9
            and x["Hs"] == 0.5]
    assert r["LB_react_rig"] == 1.6726358111469841
    H = r["Hs"] / por["derived"]["beta_s"]
    assert abs(H - r["H"]) <= 1e-15
    v = c2.necessity_lb.lb_all(dict(b=1, a=inp["alpha"], ap=inp["alpha_p"], mu=1, lam=r["lam"], rrl=False), H,
                               include_insure=False)[0]
    assert abs(float(v) - r["LB_react_rig"]) <= 1e-12
    for bad in ("alg_check_targeted", "recheck_c2", "o1_game", "os"):
        with pytest.raises(ValueError):
            paths.import_ref(bad)


# ---------------------------------------------------------------- C12: instance_rho and beta_for_rho
@pytest.mark.parametrize("slot_min", [60, 5])
def test_c12_instance_rho_on_the_families(slot_min):
    """instance_rho of from_core(...) equals the family's rho: fam.Fam (rho = 1 + beta / (a D), D = tau + H) at
    m = 3 and check_c3_benchmark.single_site (C3-L1(c)'s tightness family, beta = (rho - 1) D, D = 3), for
    rho in {1.5, 2, 4, 16}; the slot length does not matter."""
    import check_c3_benchmark as cb
    import fam
    for r in (1.5, 2.0, 4.0, 16.0):
        F = fam.Fam(3, r, 2, 1, 24)
        inst, _ = from_core(F.core_instance(), [np.zeros(0, dtype=np.int64)] * 3, slot_min=slot_min)
        got = calib.instance_rho(inst)
        assert set(got) == {"j0"}
        assert got["j0"][0] == pytest.approx(F.rho, rel=1e-12, abs=0) and got["j0"][1:] == ("L0", "k0")
        I = cb.single_site((r - 1) * 3, T=24)
        inst, _ = from_core(I, [np.zeros(0, dtype=np.int64)], slot_min=slot_min)
        assert calib.instance_rho(inst)["j0"][0] == pytest.approx(r, rel=1e-12, abs=0)


def test_c12_beta_for_rho_round_trip():
    """On the toy with two LLMs: the calibrated rho by hand (L0's 'short': 1 + lam/3600 (g a + g q) / (g a D/60),
    D = max(L Δs, P) = 10 min); beta_for_rho reaches every target to 1e-9 after a rebuild with the fee map (also
    when the instance already has a fee, which is ignored); a target below the calibrated rho, or an LLM without
    a revocable pair, raises ConfigError; at the calibrated rho the fee is 0."""
    inst = build_instance(_two_llm_config(0.0))
    rho0 = calib.instance_rho(inst)
    a, q, lam = 2.85, 7.15, 300.0
    want = 1 + lam / 3600 * (a + q) / (a * 10 / 60)                    # g cancels: the same for M and L
    for j in ("M", "L"):
        assert rho0[j][0] == pytest.approx(want, rel=1e-12) and rho0[j][1:] == ("L0", "short")
    for target in (3.0, 4.0, 16.0):
        fee = calib.beta_for_rho(inst, target)
        assert set(fee) == {"M", "L"} and all(v > 0 for v in fee.values())
        got = calib.instance_rho(build_instance(_two_llm_config(fee)))
        for j in ("M", "L"):
            assert abs(got[j][0] - target) <= 1e-9 * target, (target, j, got[j])
        # the instance's own fee is ignored
        assert calib.beta_for_rho(build_instance(_two_llm_config({"M": 9.0, "L": 0.5})), target) == fee
    fee0 = calib.beta_for_rho(inst, rho0["M"][0])
    assert all(abs(v) <= 1e-12 for v in fee0.values())
    with pytest.raises(ConfigError, match="already exceeds the target 2"):
        calib.beta_for_rho(inst, 2.0)
    with pytest.raises(ConfigError, match="already exceeds"):
        calib.beta_for_rho(inst, 1.0)
    prot_only = build_instance(toy_config(sites=["P"]))
    assert calib.instance_rho(prot_only) == {"M": None}
    with pytest.raises(ConfigError, match="no usable revocable"):
        calib.beta_for_rho(prot_only, 4.0)


@pytest.mark.needs_a12
def test_c12_bench_e1_reproduces_the_probe():
    """bench_e1 with M1's menu (config seed 1): instance_rho equals code/sim/out/ms3spec/e1_rho_probe.json
    'base_rho' (1.0867712178170381 and 1.2309078518575627 at a2:c00/L1398-1398, s5_tau60_H0); for every target of
    {1.5, 2, 4, 8, 16} beta_for_rho equals the probe's fee per LLM and the instance rebuilt with the fee map
    (C10) reaches the target to 1e-9 with the probe's mu_fb (the probe added the fee to mu_fb by hand, which
    C10 now does in the builder)."""
    from sublet.drivers import run as drun

    def build(ov):
        sp = drun.load_run_spec({"schema_version": 1, "name": "t_e1rho", "instance": "bench_e1.json",
                                 "overrides": ov, "lender_model": {"schedule": "adaptive"},
                                 "policy": {"id": "BL0a", "params": {}}, "seeds": {"config": [1]}})
        return drun.build(sp, 1)[0]

    probe = json.loads(PROBE.read_text())
    inst0 = build(E1_MENU)
    got = calib.instance_rho(inst0)
    assert {k: list(v) for k, v in got.items()} == probe["base_rho"]
    for tgt, row in probe["targets"].items():
        fee = calib.beta_for_rho(inst0, float(tgt))
        for j, v in row["beta_usd_per_load"].items():
            assert fee[j] == pytest.approx(v, rel=1e-12), (tgt, j)
        inst = build({**E1_MENU, "costs.beta_jl_usd": fee})
        r = calib.instance_rho(inst)
        for j in fee:
            assert abs(r[j][0] - float(tgt)) <= 1e-9 * float(tgt) and list(r[j][1:]) == row["rho_reached"][j][1:]
        np.testing.assert_allclose(inst.stranding.mu_fb_usd, row["mu_fb_usd"], rtol=1e-12)


# ---------------------------------------------------------------- C13: supplementary registry keys
SF_NAMES = ("sf_e1_sched", "sf_e1_rotation", "sf_e2_por", "sf_e2_mu_ep", "sf_e2_mu_cost", "sf_e2_pool", "sf_e6a",
            "sf_e6b", "sf_e10_rho", "sf_e10_cross", "sf_e10b", "sf_e11_inst", "sf_e11_fam", "sf_e11_guard")


def test_c13_supplementary_keys():
    """The two keys as specified (label, color, marker, fill, family, group); their colors are Okabe-Ito colors
    and their (color, marker, fill) triples differ from every other key's; no FIGURE_POLICIES set uses them;
    SUPP_POLICIES names the 14 figures of §8.7 and every set passes check_policies; rotation and 'always cold'
    are drawn where §8.7 draws them."""
    from figs import style as st
    want = {"a3_rot": ("A3, rotation", "#CC79A7", "d", "open", "pd", "ours"),
            "cold": ("Always cold", "#56B4E9", "d", "filled", "prewarm", "baseline")}   # 'h' until 2026-10-22
    assert st.SUPP_ONLY_KEYS == ("a3_rot", "cold")
    for k, (label, color, marker, fill, family, group) in want.items():
        p = st.POLICIES[k]
        assert (p.label, p.color, p.marker, p.fill, p.family, p.group) == (label, color, marker, fill, family, group)
        assert p.color.upper() in {c.upper() for c in st.OKABE_ITO}
        others = [q.triple for q in st.POLICIES.values() if q.key != k]
        assert p.triple not in others, k
        assert not any(k in keys for keys in st.FIGURE_POLICIES.values()), k
    assert tuple(st.SUPP_POLICIES) == SF_NAMES
    for name, keys in st.SUPP_POLICIES.items():
        assert set(keys) <= set(st.POLICIES), name
        st.check_policies(keys)
    assert set(st.SUPP_POLICIES["sf_e1_rotation"]) == {"a3", "a3_rot"}
    assert set(st.SUPP_POLICIES["sf_e2_mu_ep"]) == {"a1", "prewarm", "cold", "bl6"}
    assert st.SUPP_POLICIES["sf_e2_mu_cost"] == ("a1",)                # Fig. 7(b) draws A1 only (§8.7)
    assert st.SUPP_POLICIES["sf_e11_inst"] == st.FIGURE_POLICIES["fig3"]
    assert "bl1" not in st.SUPP_POLICIES["sf_e11_fam"]          # it shares RR-renew's color outside its family
    used = {k for keys in st.SUPP_POLICIES.values() for k in keys}
    assert set(want) <= used
    # the legend order puts each new key after its family's existing key
    assert st.legend_order(["a3_rot", "a3"]) == ["a3", "a3_rot"]
    assert st.legend_order(["cold", "prewarm", "a1"]) == ["a1", "prewarm", "cold"]
    with pytest.raises(st.StyleError, match="share"):
        st.check_color_reuse(["bl5", "cold"])                     # same color, different families
