"""Stand-in run outputs at the registered scale for the tests of the X7 supplementary script sf_e8q
(tests/test_figs_ms8_x7.py; design/ms8/plan.md W). **The numbers are made up here, deterministically, and exist only
in the test's temporary folder; they are not results and never reach paper/ or code/sim/out/.**

``standin_tree(root)`` writes, under root/code/sim/out/, an E8q summary and hist.json at the registered grid
(design/ms8/registration.md §2: tiers S, M, L x windows 5, 15, 60 min x alignments 1-4, the four tags and the bill at
W in {0, 1, 2.5, 10} s) in the shape of the fixture tree's reduced summary (tests/fixtures_figs_ms8/x7/inputs/, whose
cells, window classes, histograms and fallback splits it rescales), marked a full run whose registration gate passed,
with E8 v2's versioned summary (code/sim/out/e8v2/a/summary.json, a versioned result file) copied in as Q-0's reference
and each tag's fluid cost and replayed cost at W = 0 set to E8 v2's stored pair (so that Q-0 passes and the costs have
a realistic layout; every other value is made up). Unlike the reduced run, the stand-ins have reclaim windows (each
tag's reclaim class a scaled-down copy of its load class, RECLAIM_SHARE of its counters and histograms, with some copies
stranded) and one TTFT tail in the histogram's last bin (CAPPED: CAPPED_SHARE of the class's copies), so that every
window class and a percentile printed as a bound are exercised; then it runs the frozen analysis
(sublet/experiments/e8q_analysis.py) on them. The figure script then runs on root as SUBLET_FIGS_IN_ROOT.
"""
from __future__ import annotations

import copy
import hashlib
import json
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
SIM = HERE.parents[2]
FIX_OUT = HERE / "inputs" / "code" / "sim" / "out"
E8V2 = SIM / "out" / "e8v2" / "a" / "summary.json"
GATE = {"kind": "ms8_registration", "ok": True, "enforced": True, "note": "stand-in (tests only)"}
TAGS = ("Sublet", "A9", "BL1-BO", "BL5-cur")
BILL = "BL0a"
WAITS = ("0", "1", "2.5", "10")
WINDOWS = (5, 15, 60)
ALIGNMENTS = (1, 2, 3, 4)
SCALE = 28                         # a week over the reduced run's six hours (copies, slots)
# the replayed cost at W over the one at W = 0 (before the per-cell noise): the queue moves work into own capacity
DROP = {"0": 1.0, "1": 0.86, "2.5": 0.78, "10": 0.7}
RECLAIM_SHARE = 4                  # the reclaim class: the load class's counters and histograms // RECLAIM_SHARE
STRANDED_SHARE = 0.02              # of the reclaim class's copies
CAPPED = ("L", "BL1-BO", "overflow")   # (tier, tag, class) whose fallback histogram gets mass in the last bin
CAPPED_SHARE = 0.03


def u(*key) -> float:
    """A deterministic number in [0, 1) from `key`."""
    h = hashlib.sha256(json.dumps([str(k) for k in key]).encode()).digest()
    return int.from_bytes(h[:8], "big") / 2 ** 64


def _write(out: Path, rel: str, obj) -> None:
    p = out / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=1))


def _scale_counts(bc: dict, f: int) -> dict:
    return {cn: {k: (v * f if isinstance(v, (int, float)) and not isinstance(v, bool) else v) for k, v in z.items()}
            for cn, z in bc.items()}


def _with_reclaim(bc: dict) -> dict:
    """The reclaim class from the load class (RECLAIM_SHARE, STRANDED_SHARE); the other classes unchanged."""
    ld = bc.get("load") or {}
    if not ld.get("copies"):
        return bc
    rc = {k: (type(v)(v // RECLAIM_SHARE) if isinstance(v, (int, float)) and not isinstance(v, bool) else v)
          for k, v in ld.items()}
    rc["stranded"] = int(rc.get("copies", 0) * STRANDED_SHARE)
    return {**bc, "reclaim": rc}


def _tag_cell(x: dict, key: tuple, tag: str, c_fluid: float, c_rep0: float) -> dict:
    """The reduced cell `x` rescaled to the fluid cost c_fluid, its replayed cost at W = 0 c_rep0 and made-up replayed
    costs at the other W, each by_W consistent (C_replay = lease + loading + routing + fallback + stranding, the
    fallback split by demand adding up, E and the gap from the costs)."""
    y = copy.deepcopy(x)
    fl = dict(y["fluid"])
    f = c_fluid / float(fl["total"]) if fl.get("total") else 1.0
    fl = {k: float(v) * f for k, v in fl.items()}
    y["fluid"], y["C_fluid"] = fl, c_fluid
    y["lease_usd"] = fl["lease"] + fl["loading"]
    y["status"] = "ok"
    y["e8v2"] = None
    base = fl["lease"] + fl["loading"]
    for W, b in y["by_W"].items():
        rep = c_rep0 if W == "0" else c_rep0 * DROP[W] * (1.0 + 0.08 * (u("r", *key, tag, W) - 0.5))
        rep = max(rep, base * 1.001)
        r = dict(b.get("replay") or {})
        routing, strand = 0.01 * (rep - base) * u("ro", *key, tag, W), 0.002 * (rep - base) * u("st", *key, tag, W)
        fallback = rep - base - routing - strand
        r.update(routing=routing, stranding=strand, fallback=fallback, total=routing + strand + fallback)
        fbd = copy.deepcopy(b.get("fallback_by_demand") or {})
        z, p = float(fbd["zero"]["usd"]), float(fbd["positive"]["usd"])
        share = z / (z + p) if z + p > 0 else 0.3
        fbd["zero"]["usd"], fbd["positive"]["usd"] = share * fallback, (1 - share) * fallback
        b.update(C_fluid=c_fluid, C_replay=rep, error=(rep - c_fluid) / rep, gap_usd=rep - c_fluid, replay=r,
                 fallback_by_demand=fbd, by_class=_with_reclaim(_scale_counts(b.get("by_class") or {}, SCALE)))
    y["classes"] = {k: int(v) * SCALE for k, v in (y.get("classes") or {}).items()}
    if y["classes"].get("load"):
        y["classes"]["reclaim"] = y["classes"]["load"] // RECLAIM_SHARE
    return y


def e8q(out: Path) -> None:
    s = json.loads((FIX_OUT / "e8q" / "summary.json").read_text())
    ref = json.loads(E8V2.read_text())
    meta = dict(s["meta"])
    meta.update(reduced=False, gate=dict(GATE), git_revision="0" * 40)
    meta.pop("reduced_note", None)
    g = ref["meta"]["grid"]
    meta["grid"] = {**meta["grid"], "windows": list(WINDOWS), "alignments": list(ALIGNMENTS),
                    "horizon_min": g["horizon_min"], "market_tightness": g["market_tightness"]}
    cells = {}
    for tier in meta["grid"]["tiers"]:
        red = s["cells"][tier]
        for w in WINDOWS:
            src = red[str(w)] if str(w) in red else red[min(red, key=lambda k: abs(int(k) - w))]
            src = src[next(iter(src))]
            for c in ALIGNMENTS:
                key = (tier, w, c)
                rc = ref["cells"][tier][str(w)][str(c)]
                d = {t: _tag_cell(src[t], key, t, float(rc[t]["C_fluid"]), float(rc[t]["C_replay"])) for t in TAGS}
                bill0 = max(float(rc[t]["C_replay"]) for t in TAGS) * (1.25 + 0.2 * u("b", *key))
                bx = copy.deepcopy(src[BILL])
                bx["by_W"] = {W: {**b, "C_replay": bill0 * DROP[W], "C_fluid": bill0 * 0.97,
                                  "error": (bill0 * DROP[W] - bill0 * 0.97) / (bill0 * DROP[W]),
                                  "gap_usd": bill0 * DROP[W] - bill0 * 0.97,
                                  "by_class": _scale_counts(b.get("by_class") or {}, SCALE)}
                              for W, b in bx["by_W"].items()}
                bx["C_fluid"] = bill0 * 0.97
                d[BILL] = bx
                cells.setdefault(tier, {}).setdefault(str(w), {})[str(c)] = d
    _write(out, "e8q/summary.json", {**s, "meta": meta, "cells": cells, "missing": []})
    h = json.loads((FIX_OUT / "e8q" / "hist.json").read_text())
    h["meta"] = {**h["meta"], "reduced": False, "grid": meta["grid"], "git_revision": "0" * 40}
    nb = int(h["meta"]["hist"]["n_bins"])
    for t, a in h["tiers"].items():
        for tg, b in a.items():
            for W, x in b.items():
                for cn, y in x.items():
                    for kn, sp in y.items():
                        if sp:
                            sp["counts"] = [int(v) * SCALE * len(WINDOWS) * len(ALIGNMENTS) // 2 for v in sp["counts"]]
                if tg != BILL and any(x.get("load", {}).values()):
                    x["reclaim"] = {kn: None if not sp else {"lo": sp["lo"], "counts": [v // RECLAIM_SHARE
                                                                                         for v in sp["counts"]]}
                                    for kn, sp in x["load"].items()}
                if (t, tg) == CAPPED[:2] and x.get(CAPPED[2]):
                    y = x[CAPPED[2]]
                    tot = sum(sum(sp["counts"]) for sp in y.values() if sp)
                    dense = [0] * nb
                    sp = y.get("fallback")
                    if sp:
                        for i, v in enumerate(sp["counts"]):
                            dense[sp["lo"] + i] += v
                    dense[nb - 1] += max(1, int(CAPPED_SHARE * tot))
                    lo = next(i for i, v in enumerate(dense) if v)
                    y["fallback"] = {"lo": lo, "counts": dense[lo:]}
    _write(out, "e8q/hist.json", h)
    (out / "e8v2" / "a").mkdir(parents=True, exist_ok=True)
    shutil.copy(E8V2, out / "e8v2" / "a" / "summary.json")


def standin_tree(root: Path) -> Path:
    """The stand-in summary, hist.json and E8 v2's summary under root/code/sim/out/ with the analysis run on them;
    returns root."""
    sim = Path(root) / "code" / "sim"
    e8q(sim / "out")
    from sublet.experiments import e8q_analysis as A
    if A.run_analysis(root=sim) is None:
        raise RuntimeError("the stand-in tree misses an input of the analysis")
    return Path(root)
