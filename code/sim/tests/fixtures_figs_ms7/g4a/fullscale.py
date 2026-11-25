"""Full-scale stand-in input trees for the tests of figs/supp/sf_lag_v2.py and sf_oos.py (tests/test_figs_ms7_a.py;
design/ms7/w_spec.md §4, unit W-G4, writer A). **Not results**: every number is the fixture tree's reduced-run value
(inputs/, development week 101) scaled by a deterministic factor; the trees exist only under pytest's tmp_path (or a
scratch folder) and are never versioned.

    write_tree(root)   writes under root/code/sim/out/: e7c/lag/summary.json, e7c/gate/summary.json,
                       sublet_v2/main/summary.json and e7c/analysis.json for the 16 confirmation weeks 301-316, and
                       e7o/{fwd,rev}/summary.json and e7o/analysis.json for 16 cells per fold; each analysis is the
                       registered script's own (e7c_analysis.analyse, e7o_analysis.analyse) on the stand-in summaries,
                       so its structure is the real one at full scale

The stand-ins hold one missing run each (X1: CoCaR-style, lagged under L-co in week 305; X2: CoCaR-style under L-co in
cell 7 of the reverse fold's out-of-sample arm), so the missing-run rule shows; Sublet-lag projects no slot in every
third week, where its r0 is set to A9-lag's (the identity of the analysis then has pairs).

Command line (from code/sim): python tests/fixtures_figs_ms7/g4a/fullscale.py ROOT
"""
from __future__ import annotations

import copy
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SIM = HERE.parents[2]
if str(SIM) not in sys.path:
    sys.path.insert(0, str(SIM))

from sublet.experiments import e7c_analysis as E7C  # noqa: E402
from sublet.experiments import e7o_analysis as E7O  # noqa: E402

FIX = HERE / "inputs" / "code" / "sim" / "out"
WEEKS = [str(w) for w in range(301, 317)]
CELLS = list(range(16))
MISSING_X1 = ("BL4-lag", "L-co", "305")
MISSING_X2 = ("rev", "oos", "BL4", "L-co", 7)


def _h(s: str) -> float:
    return sum((i + 1) * ord(c) for i, c in enumerate(s)) % 97 / 97.0


def factor(*keys, i: int) -> float:
    """A deterministic factor near 1 for week (or cell) index i and the keys (tag, mode, ...)."""
    a = sum(_h(str(k)) for k in keys)
    return 1.0 + 0.07 * math.sin(1.3 * i + 6.0 * a) + 0.025 * math.cos(0.7 * i + 3.0 * a)


def _load(rel: str) -> dict:
    return json.loads((FIX / rel).read_text())


def _dump(obj, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=1, allow_nan=False) + "\n")


# ---------------------------------------------------------------------------------------------------------------
def x1(root: Path) -> None:
    lag, main = _load("e7c/lag/summary.json"), _load("sublet_v2/main/summary.json")
    base_w = sorted({c for by_m in lag["table"].values() for by_c in by_m.values() for c in by_c}, key=int)[0]
    table = {}
    for t, by_m in lag["table"].items():
        for m, by_c in by_m.items():
            b = by_c[base_w]["0"]
            for i, w in enumerate(WEEKS):
                if (t, m, w) == MISSING_X1:
                    continue
                table.setdefault(t, {}).setdefault(m, {})[w] = {"0": b * factor(t, m, i=i)}
    runs = []
    guard0 = {r["tag"]: {} for r in lag["runs"]}
    for r in lag["runs"]:
        guard0[r["tag"]][r["mode"]] = r["guard"]
    for t, by_mode in guard0.items():
        for m, g in by_mode.items():
            for i, w in enumerate(WEEKS):
                gg = copy.deepcopy(g)
                if i % 3 == 0:
                    gg["projected_slots"] = 0
                    gg.setdefault("projection", {})["K0"] = 0
                    if t == "Sublet-lag":
                        table[t][m][w] = dict(table["A9-lag"][m][w])
                runs.append({"tag": t, "mode": m, "cell": w, "seed": 0, "status": "ok", "r0": table[t][m][w]["0"],
                             "guard": gg})
    meta = {"exp": "e7c", "part": "lag", "git_revision": "standin", "reduced": False}
    lag_s = {"meta": meta, "table": table, "runs": runs}
    mtab = {}
    for t, by_m in main["table"].items():
        for m, by_c in by_m.items():
            b = by_c[base_w]["0"]
            for i, w in enumerate(WEEKS):
                mtab.setdefault(t, {}).setdefault(m, {})[w] = {"0": b * factor(t, m, "revealed", i=i)}
    main_s = {"meta": {"exp": "e7h", "part": "main", "git_revision": "standin-main", "reduced": False},
              "table": mtab}
    gate = {"meta": {"git_revision": "standin", "reduced": False},
            "decision": {"pass": True, "n_checks": 96, "n_equal": 96, "n_no_reference": 0, "max_abs_diff": 0.0}}
    out = root / "code" / "sim" / "out"
    _dump(lag_s, out / "e7c" / "lag" / "summary.json")
    _dump(gate, out / "e7c" / "gate" / "summary.json")
    _dump(main_s, out / "sublet_v2" / "main" / "summary.json")
    s = {"lag": lag_s, "gate": gate, "main": main_s, "inputs": {}}
    _dump(E7C.analyse(s), out / "e7c" / "analysis.json")


# ---------------------------------------------------------------------------------------------------------------
def _facts(ins: dict) -> dict:
    lenders = {}
    for kind in ("maas", "spot"):
        n, b = (ins.get("n_lenders") or {}).get(kind) or 0, (ins.get("b_median") or {}).get(kind)
        for j in range(n):
            lenders[f"{kind}{j}"] = {"kind": kind, "b": b}
    return {"lenders": lenders, "supply_gpus": ins.get("supply_gpus"), "gamma": ins.get("gamma"),
            "C0_from": ins.get("C0_from")}


def x2(root: Path) -> None:
    an = _load("e7o/analysis.json")
    main = json.loads((root / "code" / "sim" / "out" / "sublet_v2" / "main" / "summary.json").read_text())
    parts = {}
    for f, x in an["folds"].items():
        runs, inst = [], {}
        c0 = str(x["cells"][0])
        for arm in E7O.ARMS:
            for t in x["tags"]:
                e = x["per_cell"][arm][t][c0]
                for k in CELLS:
                    for m in E7O.MODES:
                        if (f, arm, t, m, k) == MISSING_X2:
                            runs.append({"arm": arm, "tag": t, "mode": m, "cell": k, "seed": 0, "status": "failed",
                                         "r0": None})
                            continue
                        v = e["r0"][m]
                        src = {s: dict(e["sources"][m][s]) for s in E7O.SOURCES} if m in E7O.SOURCE_MODES else {}
                        for s in src:
                            for fld in src[s]:
                                src[s][fld] = int(round(src[s][fld] * factor(f, arm, t, m, s, fld, i=k)))
                        runs.append({"arm": arm, "tag": t, "mode": m, "cell": k, "seed": 0, "status": "ok",
                                     "r0": None if v is None else v * factor(f, arm, t, m, i=k), "sources": src})
            ins = x["instances"][arm][c0]
            for k in CELLS:
                inst.setdefault(arm, {})[f"k{k}"] = {
                    "facts": _facts(ins), "references": {"bl0a_usd": ins["bl0a_usd"] * factor(f, "bl0a", i=k)},
                    "n_instance_hashes": ins["n_instance_hashes"]}
        parts[f] = {"meta": {"part": f, "git_revision": "standin", "reduced": False, "n_runs": len(runs),
                             "cells": [{"k": k, "c": 301 + k} for k in CELLS], "design": {"tags": list(x["tags"])}},
                    "runs": runs, "instances": inst}
    out = root / "code" / "sim" / "out"
    for f, s in parts.items():
        _dump(s, out / "e7o" / f / "summary.json")
    a = E7O.analyse({"parts": parts, "conf": main, "inputs": {}})
    _dump(a, out / "e7o" / "analysis.json")


def write_tree(root) -> Path:
    root = Path(root)
    x1(root)
    x2(root)
    return root


if __name__ == "__main__":
    print(write_tree(sys.argv[1]))
