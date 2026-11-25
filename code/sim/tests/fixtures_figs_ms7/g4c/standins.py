"""Stand-in run outputs at the registered scale for the tests of the X3 supplementary scripts (tests/test_figs_ms7_c.py;
design/ms7/w_spec.md §4, unit W-G4, writer C). **The numbers are made up here, deterministically, and exist only in the
test's temporary folder; they are not results and never reach paper/ or code/sim/out/.**

``standin_tree(root)`` writes, under root/code/sim/out/, summaries of the four X3 parts with the registered grids
(design/ms7/registration.md §2: S1 v2 on weeks 301-304 with part w0 on 301-302, E5 v2 on config seeds 301-304, E8 v2
with three tiers, three windows and four alignments, E9 v2 on E9's sixteen points at four alignments) in the shape of
the fixture tree's reduced summaries (tests/fixtures_figs_ms7/g4c/inputs/, whose meta, points and rows they keep), each
marked a full run whose registration gate passed, and then runs the frozen analysis
(sublet/experiments/ms7_sens_analysis.py) on them, with the MS5b fixture's confirmation for the seed spread. The S1 v2
savings follow the shape of the MS5 sensitivity study's medians (code/sim/out/s1/sweep/summary.json, a versioned
result file) where a setting has one, so that the tornado's bars and end labels have a realistic layout; E9 v2's sites
and LLMs are E9's (code/sim/out/e9/summary.json). The figure scripts then run on root as SUBLET_FIGS_IN_ROOT.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SIM = HERE.parents[2]
FIX_OUT = HERE / "inputs" / "code" / "sim" / "out"
MS5B_CONF = SIM / "tests" / "fixtures_figs_ms5b" / "inputs" / "code" / "sim" / "out" / "sublet_v2"
GATE = {"kind": "ms7_registration", "ok": True, "enforced": True, "note": "stand-in (tests only)"}
WEEKS = [301, 302, 303, 304]
W0_WEEKS = [301, 302]
TAGS4 = ("Sublet", "A9", "BL1-BO", "BL5-cur")
W0_TAGS = TAGS4 + ("BL4",)
MODES = ("L-eg", "L-ss", "L-iid-0.05", "L-iid-0.2", "L-co")


def u(*key) -> float:
    """A deterministic number in [0, 1) from `key`."""
    h = hashlib.sha256(json.dumps([str(k) for k in key]).encode()).digest()
    return int.from_bytes(h[:8], "big") / 2 ** 64


def _load(rel: str) -> dict:
    return json.loads((FIX_OUT / rel).read_text())


def _write(out: Path, rel: str, obj) -> None:
    p = out / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=1))


def _full(meta: dict, **grid) -> dict:
    m = dict(meta)
    m.update(reduced=False, gate=dict(GATE), git_revision="0" * 40)
    m.pop("reduced_note", None)
    return m


def s1v2(out: Path) -> None:
    sw = _load("s1v2/sweep/summary.json")
    v1 = json.loads((SIM / "out" / "s1" / "sweep" / "summary.json").read_text())["points"]
    meta = _full(sw["meta"])
    meta["grids"] = {**meta["grids"], "weeks": WEEKS, "horizon_min": 10080}

    def r0_sublet(n, w):
        base = (((v1.get(n) or {}).get("overflow_over_bl0a") or {}).get("median"))
        if base is None:
            base = 0.72 + 0.3 * (u("pt", n) - 0.5)
        return base + 0.04 * (u("wk", n, w) - 0.5)
    table = {t: {"L-tr": {}} for t in TAGS4}
    for n in sw["points"]:
        for t in TAGS4:
            table[t]["L-tr"][n] = {}
            for w in WEEKS:
                s = r0_sublet(n, w)
                off = {"Sublet": 0.0, "A9": -0.02 * u("a9", n, w), "BL1-BO": 0.02 + 0.06 * (u("bo", n, w) - 0.3),
                       "BL5-cur": 0.08 + 0.05 * u("rr", n, w)}[t]
                table[t]["L-tr"][n][str(w)] = {"0": s + off}
    reused = {}
    for n, r in sw["reused"].items():
        reused[n] = {**{k: v for k, v in r.items() if k != "by_tag"},
                     "by_tag": {t: {str(w): r0_sublet(n, w) + {"Sublet": 0.0, "A9": -0.01, "BL1-BO": 0.03,
                                                              "BL5-cur": 0.09, "BL4": 0.2}[t] for w in WEEKS}
                                for t in W0_TAGS}}
    _write(out, "s1v2/sweep/summary.json", {**sw, "meta": meta, "table": table, "reused": reused})
    w0 = _load("s1v2/w0/summary.json")
    wm = _full(w0["meta"])
    wm["grids"] = {**wm["grids"], "weeks": W0_WEEKS}
    pts = wm["grids"]["points"]
    t2 = {t: {m: {n: {str(w): {"0": 0.8 + 0.6 * u("w0", t, m, n, w) + (0.0 if t != "Sublet" else -0.2)}
                      for w in W0_WEEKS} for n in pts} for m in MODES} for t in W0_TAGS}
    W0 = {}
    for t in W0_TAGS:
        W0[t] = {}
        for n in pts:
            W0[t][n] = {}
            for w in W0_WEEKS:
                vals = {m: t2[t][m][n][str(w)]["0"] for m in MODES}
                m = max(vals, key=vals.get)
                W0[t][n][str(w)] = {"W0": vals[m], "mode": m, "missing": []}
    dflt = {t: {str(w): 0.9 + 0.3 * u("d", t, w) - (0.15 if t == "Sublet" else 0.0) for w in W0_WEEKS}
            for t in W0_TAGS}
    _write(out, "s1v2/w0/summary.json", {**w0, "meta": wm, "table": t2, "W0": W0, "reused_default_W0": dflt})


def e5v2(out: Path) -> None:
    s = _load("e5v2/summary.json")
    meta = _full(s["meta"])
    meta["grid"] = {**meta["grid"], "weeks": WEEKS, "horizon_min": 10080}
    level_f = {"trace": 1.0, "sh0.25": 1.03, "sh0.5": 1.06, "sh1": 1.1, "all1": 1.9}
    base = {"Sublet": 0.72, "A9": 0.70, "BL1-BO": 0.74, "BL5-cur": 0.83, "BL3-0": 0.86, "BL3-2": 0.97}
    cells = {}
    for lv, a in s["cells"].items():
        for mn, b in a.items():
            for mk, x in b.items():
                for t, e in x.items():
                    f = level_f[lv] * (1.6 if mn == "long" else 1.0) * (1.0 + 0.15 * (float(mk) - 1.0))
                    if t.startswith("BL3") and lv == "all1":
                        f *= 4.0 + 6.0 * u("bl3", mn, t)
                    by = {str(w): base[t] * f * (1.0 + 0.05 * (u(lv, mn, mk, t, w) - 0.5)) for w in WEEKS}
                    cells.setdefault(lv, {}).setdefault(mn, {}).setdefault(mk, {})[t] = {
                        **e, "by_c": by, "n_runs": len(WEEKS), "n_runs_expected": len(WEEKS)}
    _write(out, "e5v2/summary.json", {**s, "meta": meta, "cells": cells})


def e8v2(out: Path) -> None:
    s = _load("e8v2/a/summary.json")
    meta = _full(s["meta"])
    meta["grid"] = {**meta["grid"], "windows": [5, 15, 60], "alignments": [1, 2, 3, 4], "horizon_min": 10080,
                    "market_tightness": 0.5}
    tags = ("Sublet", "A9", "BL1-BO", "BL5-cur")
    base = {"Sublet": 1.0, "A9": 0.97, "BL1-BO": 1.06, "BL5-cur": 1.1, "A6": 1.3}
    tier_f = {"S": 1.0, "M": 1.8, "L": 2.6}

    def pair(key, t):
        fl = 100.0 * base[t] * tier_f.get(key[0], 1.0) * (1.0 + 0.06 * (u("f", *key, t) - 0.5))
        err = 0.15 + 0.2 * u("e", *key, t)
        return {"C_fluid": fl, "C_replay": fl / (1.0 - err), "error": err}
    cells, a6 = {}, {}
    for tier in meta["grid"]["tiers"]:
        for w in meta["grid"]["windows"]:
            for c in meta["grid"]["alignments"]:
                key = (tier, w, c)
                cells.setdefault(tier, {}).setdefault(str(w), {})[str(c)] = {t: pair(key, t) for t in tags}
                a6.setdefault(tier, {}).setdefault(str(w), {})[str(c)] = pair(key, "A6")
    mc, mca6 = {}, {}
    for w in meta["grid"]["windows"]:
        for pf in ("off", "on"):
            key = ("mc", w, pf)
            mc.setdefault(str(w), {})[pf] = {t: pair(key, t) for t in tags}
            mca6.setdefault(str(w), {})[pf] = pair(key, "A6")
    _write(out, "e8v2/a/summary.json", {**s, "meta": meta, "cells": cells, "reused_a6": a6, "mooncake": mc,
                                        "reused_a6_mooncake": mca6})


def e9v2(out: Path) -> None:
    s = _load("e9v2/summary.json")
    e9 = json.loads((SIM / "out" / "e9" / "summary.json").read_text())["points"]
    meta = _full(s["meta"])
    meta["grid"] = {**meta["grid"], "alignments": [1, 2, 3, 4], "horizon_min": 1440}
    pts = {}
    for p, e in e9.items():
        sx = e["sites_x_llms"]
        pol = {}
        for t, f in (("Sublet", 1.0), ("A9", 0.25)):
            by = {}
            for c in (1, 2, 3, 4):
                act = f * 2e-4 * sx * (1.0 + 0.2 * u("act", p, t, c))
                by[str(c)] = {"policy_act_s_mean": act, "slow_loop_s_per_h": 12.0 * act * 1.02, "hours": 24.0,
                              "n_slow_steps": 288, "fast_loop_s_per_h": 0.01 * sx ** 0.5, "loops_s_per_h":
                              12.0 * act * 1.02 + 0.01 * sx ** 0.5, "peak_rss_mb": 100 + 0.2 * sx * f,
                              "projected_slots": int(10 * u("pj", p, c)), "slow_step_p99_s": 3 * act}
            med = {k: sorted(v[k] for v in by.values())[1] for k in ("loops_s_per_h", "peak_rss_mb",
                                                                     "slow_loop_s_per_h", "fast_loop_s_per_h",
                                                                     "policy_act_s_mean")}
            pol[t] = {"n_runs": 4, "alignments": [1, 2, 3, 4], "by_alignment": by, "median": med,
                      "max": {"peak_rss_mb": max(v["peak_rss_mb"] for v in by.values())}}
        act1 = pol["Sublet"]["by_alignment"]["1"]["policy_act_s_mean"]
        inner = pol["A9"]["by_alignment"]["1"]["policy_act_s_mean"]
        g = act1 - inner
        parts = {"lb": 0.003 * g, "test": 0.02 * g, "projection": 0.01 * g}
        parts["other"] = 0.001 * g
        parts["safe"] = g - sum(parts.values())
        pts[p] = {**{k: e.get(k) for k in ("n_sites", "n_llms", "n_contracts", "sites_x_llms", "n_units")},
                  "policies": pol, "split": {"c": 1, "identical": not p.endswith("V32_SML"),
                                             "split": {"per_slot_mean_s": {"act": act1, "inner_act": inner, "guard": g,
                                                                           **parts}}}}
    checks = {"E9v2-1": {"status": "pass", "cap_mb": 3072.0, "n_over_cap": 0, "n_runs": 128}}
    _write(out, "e9v2/summary.json", {**s, "meta": meta, "points": pts, "checks": checks})


def standin_tree(root: Path) -> Path:
    """The stand-in summaries and their analyses under root/code/sim/out/; returns root."""
    sim = Path(root) / "code" / "sim"
    out = sim / "out"
    for f in (s1v2, e5v2, e8v2, e9v2):
        f(out)
    from sublet.experiments import ms7_sens_analysis as M
    M.run_analysis(list(M.EXPS), root=sim, conf_dir=MS5B_CONF)
    return Path(root)
