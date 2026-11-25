"""A stand-in e7r tree at the scale of the real runs, for the layout tests of figs/supp/sf_bl_ms7.py and
sf_stress_ms7.py (design/ms7/w_spec.md §4, unit W-G4 B). **Its numbers are made up from the reduced fixture tree by a
seeded perturbation and exist only in the tests: never results, never written into the repository.**

    standin_root(dst) -> dst          # writes dst/code/sim/out/e7r/{eval,confirm,tune}/summary.json,
                                      # tune/selection.json and analysis.json

The fixture tree (inputs/, one development week) gives each tag's r0 per lender mode; the stand-in repeats it on the
16 evaluation weeks 301-316, the four tuning weeks 113-116 and the four confirmation weeks 121-124, each value times a
seeded week factor and a seeded factor per run. The tune summary goes through the frozen selection rules
(sublet.experiments.e7r_select.select) and the parts through the frozen analysis (sublet.experiments.e7r_analysis
.analysis), so the stand-in analysis has the real analysis's structure (16 weeks, every tag, the aliases of its own
selection). There is no confirmation summary (main, second): the confirmation's tags read eval's rows, and the checks
that need main report none.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
FIX = HERE / "inputs" / "code" / "sim" / "out" / "e7r"
EVAL_WEEKS = tuple(range(301, 317))
TUNE_WEEKS = (113, 114, 115, 116)
CONFIRM_WEEKS = (121, 122, 123, 124)
SEED = 20261109


def _rd(p: Path) -> dict:
    return json.loads(Path(p).read_text())


def _text(obj) -> str:
    return json.dumps(obj, indent=1, allow_nan=False) + "\n"


def _perturbed(base: dict, weeks, rng, week_sd: float = 0.08, run_sd: float = 0.04) -> dict:
    """{mode: {week: {'0': value}}} from {mode: value}: value x week factor x run factor (None stays None)."""
    wf = {w: 1.0 + week_sd * float(rng.standard_normal()) for w in weeks}
    out = {}
    for m, v in base.items():
        out[m] = {str(w): {"0": None if v is None else float(v) * wf[w] * (1.0 + run_sd * float(rng.standard_normal()))}
                  for w in weeks}
    return out


def standin_root(dst: Path, seed: int = SEED) -> Path:
    from sublet.experiments import e7r_analysis as EA
    from sublet.experiments import e7r_select as ES
    from sublet.experiments import ms3_common as mc

    rng = np.random.default_rng(seed)
    a = _rd(FIX / "analysis.json")
    tune0 = _rd(FIX / "tune" / "summary.json")
    w0 = str(a["weeks"][0])
    e = Path(dst) / "code" / "sim" / "out" / "e7r"
    # tune and the selection (the frozen rules)
    ttab = {}
    for t in sorted(tune0["table"]):
        base = {m: (by.get(w0) or {}).get("0") for m, by in tune0["table"][t].items()}
        ttab[t] = _perturbed(base, TUNE_WEEKS, rng)
    tune = {"meta": {**copy.deepcopy(tune0["meta"]), "weeks": list(TUNE_WEEKS), "reduced": False,
                     "git_revision": "standin"}, "table": ttab}
    (e / "tune").mkdir(parents=True, exist_ok=True)
    (e / "tune" / "summary.json").write_text(_text(tune))
    sel = ES.select(json.loads(json.dumps(tune)))
    sel["meta"] = {"script": "code/sim/sublet/experiments/e7r_select.py", "reduced": False,
                   "summary_sha256": hashlib.sha256((e / "tune" / "summary.json").read_bytes()).hexdigest(),
                   "summary_git_revision": "standin", "git_revision": "standin"}
    sel_text = _text(sel)
    (e / "tune" / "selection.json").write_text(sel_text)
    sel_rec = {"path": "out/e7r/tune/selection.json", "sha256": hashlib.sha256(sel_text.encode()).hexdigest()}
    aliases = sel["aliases"]
    # eval: every tag of the fixture analysis except the stand-in selection's aliases; a tuned tag's rows from the
    # fixture's tag of that name (its configuration may differ: a stand-in)
    etab, emeta = {}, {}
    for t, x in sorted(a["tags"].items()):
        if t in aliases:
            continue
        if x.get("kind") == "tuned" and t not in sel["tuned"]:
            continue
        pw = x["per_week"][w0]["r0"]
        etab[t] = _perturbed(dict(pw), EVAL_WEEKS, rng)
        info = {k: x.get(k) for k in ("policy_id", "params", "family", "kind", "role")}
        if t in sel["tuned"]:
            info.update(policy_id=sel["tuned"][t]["policy_id"], params=sel["tuned"][t]["params"])
        emeta[t] = info
    ev = {"meta": {"exp": "e7r", "part": "eval", "git_revision": "standin", "reduced": False,
                   "weeks": list(EVAL_WEEKS), "tags": emeta, "selection": sel_rec, "aliases": aliases},
          "table": etab}
    (e / "eval").mkdir(parents=True, exist_ok=True)
    (e / "eval" / "summary.json").write_text(_text(ev))
    # confirm: each family's as-built setting and its T and W settings (not the aliases)
    ctab = {}
    for fam in EA.FAMILIES:
        for name in (EA.FAMILY_DEFAULT[fam], f"{fam}-T", f"{fam}-W"):
            if name in aliases or (name != EA.FAMILY_DEFAULT[fam] and name not in sel["tuned"]):
                continue
            src = a["tags"].get(name) or a["tags"].get(f"{fam}-T")
            base = {m: src["per_week"][w0]["r0"].get(m) for m in ("L-tr",) + EA.STRESS_MODES}
            ctab[name] = _perturbed(base, CONFIRM_WEEKS, rng)
    conf = {"meta": {"exp": "e7r", "part": "confirm", "git_revision": "standin", "reduced": False,
                     "weeks": list(CONFIRM_WEEKS), "selection": sel_rec, "aliases": aliases}, "table": ctab}
    (e / "confirm").mkdir(parents=True, exist_ok=True)
    (e / "confirm" / "summary.json").write_text(_text(conf))
    inp = EA.load(Path(dst) / "code" / "sim", frozen=Path(dst) / "no_confirmation")
    res = EA.analysis(inp)
    mc.dump_json(res, e / "analysis.json")
    return Path(dst)
