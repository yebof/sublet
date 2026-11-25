"""E7r's selection rules T and W on the tune part (design/ms7/plan.md X4, D6; change C54; design/ms7/feasibility/
baselines.md §2 item 3). Its sha256 is recorded in design/ms7/registration.md before the runs, and every e7r part
refuses to start unless the file still has that sha256 (ms7_baselines.check_registration); so every rule below is
fixed, deterministic and complete, and the file depends only on the tune summary and ms3_common's file helpers.

Input: <root>/out/e7r/tune/summary.json (e7r.summary_part: its table {tag: {mode: {week: {seed: r0}}}}, null for a
missing or failed run, and meta.tags with each configuration's family, registry id and parameters). Output:
<root>/out/e7r/tune/selection.json and selection.md, which the parts confirm and eval read.

Rules (copied from the feasibility study §2 item 3; r0 is a run's overflow cost over BL0a, policy seed 0):
  per configuration g of a family and tune week w: r0_tr(g, w) = r0 under L-tr; W0(g, w) = the largest r0 over the
  five stress modes STRESS_MODES (null while one is missing). med_T(g) and med_W(g) are the medians over the weeks
  WEEKS (statistics.median); g is eligible iff every one of its runs in these cells is ok (no null: the missing-run
  rule makes a configuration with a missing run ineligible, recorded with its missing cells).
  T  = the eligible configuration with the least (med_T, grid index)
  W  = the eligible configuration with the least (med_W, med_T, grid index)
  A family without an eligible configuration has no T and no W (recorded; the later parts then lack its tuned rows).
  The tuned tags are '<family>-T' and '<family>-W'; when W is the configuration of T, '<family>-W' is an alias of
  '<family>-T' (aliases) and runs once.
H1-type comparisons (trace cost) use a family's T setting and H2-type comparisons (worst case) its W setting; Sublet
gets no tuning. No statistical test is run (the weeks are rotations of one series).
"""
from __future__ import annotations

import argparse
import hashlib
import re
import statistics
import sys
from pathlib import Path
from typing import Optional

from . import ms3_common as mc

FAMILIES = ("BL1", "BL2", "BL3", "BL4", "BL5", "MPC")
TRACE_MODE = "L-tr"
STRESS_MODES = ("L-eg", "L-ss", "L-iid-0.05", "L-iid-0.2", "L-co")
WEEKS = (113, 114, 115, 116)
REDUCED_WEEKS = (101,)
SEED = "0"
_GRID = re.compile(r"^(?P<fam>[A-Z0-9]+)-g(?P<i>\d{2})$")


def _val(table: dict, tag: str, mode: str, week) -> Optional[float]:
    v = ((table.get(tag) or {}).get(mode) or {}).get(mc.num_key(week), {}).get(SEED)
    return None if v is None else float(v)


def config_stats(table: dict, tag: str, weeks) -> dict:
    """r0_tr and W0 per week, their medians over the weeks and the eligibility of one configuration."""
    tr, w0, missing = {}, {}, []
    for w in weeks:
        k = mc.num_key(w)
        tr[k] = _val(table, tag, TRACE_MODE, w)
        st = [_val(table, tag, m, w) for m in STRESS_MODES]
        w0[k] = None if any(v is None for v in st) else max(st)
        missing += [[k, m] for m, v in zip((TRACE_MODE,) + STRESS_MODES, [tr[k]] + st) if v is None]
    ok = not missing and bool(weeks)
    return {"r0_tr": tr, "W0": w0, "median_r0_tr": statistics.median(tr.values()) if ok else None,
            "median_W0": statistics.median(w0.values()) if ok else None, "eligible": ok, "missing": missing}


def select(summary: dict) -> dict:
    """The selection of every family from a tune summary (module docstring)."""
    meta = summary.get("meta") or {}
    table = summary.get("table") or {}
    weeks = REDUCED_WEEKS if meta.get("reduced") else WEEKS
    tags = meta.get("tags") or {}
    fams: dict = {}
    for name in sorted(tags):
        mm = _GRID.match(name)
        if mm is None or mm.group("fam") not in FAMILIES:
            continue
        fams.setdefault(mm.group("fam"), []).append((int(mm.group("i")), name))
    out = {"families": {}, "tuned": {}, "aliases": {}}
    for fam in FAMILIES:
        cfgs = sorted(fams.get(fam, []))
        stats = {}
        for i, name in cfgs:
            t = tags[name]
            stats[name] = {"index": i, "policy_id": t["policy_id"], "params": t["params"],
                           **config_stats(table, name, weeks)}
        el = [n for _i, n in cfgs if stats[n]["eligible"]]
        T = min(el, key=lambda n: (stats[n]["median_r0_tr"], stats[n]["index"])) if el else None
        W = min(el, key=lambda n: (stats[n]["median_W0"], stats[n]["median_r0_tr"], stats[n]["index"])) if el else None
        out["families"][fam] = {"configs": stats, "n_configs": len(cfgs), "n_eligible": len(el), "T": T, "W": W,
                                "default": cfgs[0][1] if cfgs else None}
        for rule, g in (("T", T), ("W", W)):
            if g is None:
                continue
            out["tuned"][f"{fam}-{rule}"] = {"family": fam, "rule": rule, "config": g,
                                            "policy_id": stats[g]["policy_id"], "params": stats[g]["params"],
                                            "median_r0_tr": stats[g]["median_r0_tr"],
                                            "median_W0": stats[g]["median_W0"]}
        if T is not None and W == T:
            out["aliases"][f"{fam}-W"] = f"{fam}-T"
    out["weeks"] = list(weeks)
    return out


def _md(sel: dict) -> str:
    lines = ["# E7r tune: the selected settings (rules T and W, e7r_select.py)", ""]
    if sel["meta"].get("reduced"):
        lines += ["Reduced run (development cell only): not a result.", ""]
    rows = []
    for fam, f in sel["families"].items():
        for rule in ("T", "W"):
            g = f[rule]
            c = f["configs"].get(g) or {}
            rows.append([fam, rule, g, c.get("policy_id"), c.get("params"), c.get("median_r0_tr"), c.get("median_W0"),
                         f["n_eligible"], f["n_configs"]])
    lines += [mc.md_table(["family", "rule", "config", "policy", "params", "median r0 L-tr", "median W0", "eligible",
                           "configs"], rows), ""]
    if sel["aliases"]:
        lines += ["Aliases (W equal to T): " + ", ".join(f"{a} = {b}" for a, b in sorted(sel["aliases"].items())), ""]
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m sublet.experiments.e7r_select", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=None, help="folder whose out/e7r/tune/ holds the tune summary (default MS3_ROOT "
                                                 "or this repository's code/sim)")
    a = ap.parse_args(argv)
    tune = mc.ms3_root(a.root) / "out" / "e7r" / "tune"
    src = tune / "summary.json"
    s = mc.read_json(src)
    if not isinstance(s, dict):
        print(f"[e7r_select] {src} is missing or unreadable", file=sys.stderr)
        return 2
    sel = select(s)
    me = Path(__file__).resolve()
    sel["meta"] = {"script": "code/sim/sublet/experiments/e7r_select.py",
                   "script_sha256": hashlib.sha256(me.read_bytes()).hexdigest(),
                   "summary_sha256": hashlib.sha256(src.read_bytes()).hexdigest(),
                   "summary_git_revision": (s.get("meta") or {}).get("git_revision"),
                   "git_revision": mc.git_revision(), "written": mc._now(),
                   "reduced": bool((s.get("meta") or {}).get("reduced")),
                   "rules": {"T": "min (median r0 under L-tr, grid index)",
                             "W": "min (median W0 over the five stress modes, median r0 under L-tr, grid index)",
                             "eligible": "every run of the tune cells ok"},
                   "stress_modes": list(STRESS_MODES), "trace_mode": TRACE_MODE}
    mc.dump_json(sel, tune / "selection.json")
    mc.write_text(_md(sel), tune / "selection.md")
    n = sum(1 for f in sel["families"].values() if f["T"] is not None)
    print(f"[e7r_select] {n} of {len(FAMILIES)} families selected; aliases {sel['aliases']}; "
          f"wrote {tune / 'selection.json'}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
