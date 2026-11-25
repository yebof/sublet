"""E7c analysis: the reported quantities of the causal-demand rerun (design/ms7/plan.md X1, D4, D6; change C53;
design/ms7/feasibility/causal.md, RECOMMENDED DESIGN items 2 and 4). Its sha256 is recorded in
design/ms7/registration.md before the runs (D6) on the line 'e7c_analysis_sha256: <64 hex>', and e7c's parts refuse
to start unless this file still has that sha256; so every rule below is fixed before any lagged run exists. The
frozen confirmation and its analysis (ms5b_analysis.py) are untouched.

Inputs: <root>/out/e7c/lag/summary.json (the lagged runs), <root>/out/e7c/gate/summary.json (part gate's identity
checks, reported), and the revealed-slot rows of the confirmation, <root>/out/sublet_v2/main/summary.json, which also
holds the lagged RetroRenting-style rows (BL5's default build is lagged: e7c_tags.LAGGED_FROM_MAIN). Output:
<out>/analysis.json and analysis.md (default <root>/out/e7c/).

Quantities (r0 a run's overflow cost over BL0a; W0 the largest r0 over the five stress modes, None while one is
missing; RC = r0 under L-tr minus r0 under L-hon of the same week and policy, as ms5b_common.rc_rows; policy seed 0;
the weeks are the cells of the lag table, which e7h.collect fills for every expected run). Every quantity is
descriptive: per week, median, min and max, and sign counts; no p-value, no interval (the weeks are rotations of one
series, D4).
  1  per lagged policy (the 11 lag tags and BL5 from main): per week and the median over the weeks of L-tr r0, W0
     and RC, and the weeks with r0 below 1 and with W0 below 1 (H2's first count, design/sublet_v2.md §6);
  2  the margin of Sublet-lag against H1's lagged set {BL1-lag, BL1-BO-lag, BL2-lag, BL3-0-lag, BL4-lag, BL5} per
     week, on L-tr r0 and on W0, in H1's convention: Delta_w = min over the set of the metric minus Sublet-lag's
     (ms5b_common.paired_margins, the function of ms5b_analysis.h1; positive: Sublet-lag is cheaper than every
     policy of the set in that week, which on W0 is H2's 'below the set'), with the attaining policy per week; the
     counts of weeks with Delta_w above, at and below zero (wins, ties, losses), the weeks that a missing run
     decides (counted apart, a loss for Sublet-lag by the missing-run rule of design/sublet_v2.md §4.5); median, min
     and max over the other weeks;
  3  the same against the notice-aware lagged set {BL5-tau60-lag, BL1-GP-lag, BL1N-lag, BL5N-lag};
  4  per policy, lagged minus revealed (main's counterpart, e7c_tags.REVEALED_OF; lagged BL5 against BL5-cur) of L-tr
     r0, W0 and RC per week, with median, min and max, beside the revealed values themselves;
  5  the guard of Sublet-lag and BL1-GP-lag (their inner policy lagged, the guard's test on the realized slot): per
     run the projected slots, abort, certificate and envelope; totals per tag and mode;
  6  the identity r0(Sublet-lag) = r0(A9-lag) on every (week, mode) where Sublet-lag projected no slot and did not
     abort (there the executed trajectory is A9-lag's): the pairs, the exact equalities, the largest |difference|,
     and the runs left out (projected or aborted);
  7  part gate's outcome (pass, counts) and whether parts gate and lag ran at the same commit.
The output's meta records this file's sha256 beside the one design/ms7/registration.md records (its line
'e7c_analysis_sha256: <64 hex>', read from the repository's working tree), whether they match, and whether the lag
table's weeks are the 16 confirmation weeks; a mismatch is reported (stderr and meta), so that an analysis changed
after the runs is visible in its own output.

Command line, run from code/sim: python -m sublet.experiments.e7c_analysis [--root DIR] [--out DIR]
"""
from __future__ import annotations

import argparse
import hashlib
import statistics
import sys
from pathlib import Path
from typing import Optional, Sequence

from .. import paths
from . import e7c
from . import e7c_tags as ct
from . import ms3_common as mc
from . import ms5b_common as m5

EXP = "e7c"
TRACE, HON = m5.TRACE_MODE, m5.HON_MODE
SUBLET, INNER = "Sublet-lag", "A9-lag"
METRICS = ("r0", "W0", "RC")                       # r0 under L-tr, W0 over the stress modes, RC under L-tr
MARGIN_METRICS = ("r0", "W0")
BELOW_1 = ("r0", "W0")                             # metrics whose weeks below 1 (cheaper than BL0a) are counted
WEEKS_FULL = [mc.num_key(w) for w in m5.CONF_WEEKS]   # the lag part's weeks in a full run (301-316)
H1_SET = tuple(dict.fromkeys(ct.H1_LAGGED.values()))          # BL1-lag, BL1-BO-lag, BL2-lag, BL3-0-lag, BL4-lag, BL5
NOTICE_SET = tuple(ct.NOTICE_LAGGED.values())                 # BL5-tau60-lag, BL1-GP-lag, BL1N-lag, BL5N-lag
POLICIES = ct.LAG_TAGS + tuple(ct.LAGGED_FROM_MAIN)           # the lagged rows: 11 lag tags and BL5 (main)


# ---------------------------------------------------------------- inputs
def load(root=None) -> dict:
    """{'lag', 'gate', 'main'}: the summaries (None where missing) and the sha256 of each file read."""
    r = mc.ms3_root(root) / "out"
    files = {"lag": r / EXP / "lag" / "summary.json", "gate": r / EXP / "gate" / "summary.json",
             "main": r / m5.CONF_DIR / "main" / "summary.json"}
    out = {k: (mc.read_json(f) if f.is_file() else None) for k, f in files.items()}
    out["inputs"] = {k: {"path": str(f), "sha256": hashlib.sha256(f.read_bytes()).hexdigest() if f.is_file() else None}
                     for k, f in files.items()}
    return out


def val(table: dict, tag: str, mode: str, cell: str, seed: int = 0) -> Optional[float]:
    v = ((table.get(tag) or {}).get(mode) or {}).get(cell, {}).get(str(seed))
    return None if v is None else float(v)


def weeks_of(table: dict) -> list:
    cells = {c for by_m in table.values() for by_c in by_m.values() for c in by_c}
    return sorted((c for c in cells if c.isdigit()), key=int)


def metric(table: Optional[dict], tag: str, cell: str, name: str) -> Optional[float]:
    """r0 under L-tr, W0 (m5.w0_of over the five stress modes) or RC (L-tr minus L-hon) of one week and tag."""
    if not table:
        return None
    if name == "r0":
        return val(table, tag, TRACE, cell)
    if name == "W0":
        w, _m, _miss = m5.w0_of({m: val(table, tag, m, cell) for m in m5.stress_modes()})
        return w
    if name == "RC":
        a, h = val(table, tag, TRACE, cell), val(table, tag, HON, cell)
        return None if a is None or h is None else a - h
    raise ValueError(f"unknown metric {name!r}")


def lagged_table(s: dict, tag: str) -> Optional[dict]:
    """The table that holds a lagged row: part lag's for a lag tag, main's for the rows of LAGGED_FROM_MAIN."""
    src = s.get("main") if tag in ct.LAGGED_FROM_MAIN else s.get("lag")
    return (src or {}).get("table")


def lagged_tag(tag: str) -> str:
    return ct.LAGGED_FROM_MAIN.get(tag, tag)


def revealed_tag(tag: str) -> str:
    return ct.REVEALED_OF_MAIN.get(tag) or ct.REVEALED_OF[tag]


def describe(xs: Sequence[Optional[float]]) -> dict:
    """n, the values missing, median, min and max of the values that exist."""
    v = [float(x) for x in xs if x is not None]
    out = {"n": len(v), "n_missing": sum(1 for x in xs if x is None)}
    if v:
        out.update(median=float(statistics.median(v)), min=min(v), max=max(v))
    else:
        out.update(median=None, min=None, max=None)
    return out


# ---------------------------------------------------------------- the quantities
def per_policy(s: dict, weeks: list) -> dict:
    """Quantity 1: {policy: {metric: {'weeks': {w: value}, **describe}}} over POLICIES, with 'n_below_1' (the weeks
    whose value is below 1) for r0 and W0."""
    out = {}
    for p in POLICIES:
        tab = lagged_table(s, p)
        row = {}
        for k in METRICS:
            vals = {w: metric(tab, lagged_tag(p), w, k) for w in weeks}
            row[k] = {"weeks": vals, **describe(list(vals.values()))}
            if k in BELOW_1:
                row[k]["n_below_1"] = sum(1 for v in vals.values() if v is not None and v < 1.0)
        out[p] = row
    return out


def margins(s: dict, weeks: list, comp: Sequence[str], name: str) -> dict:
    """Quantities 2 and 3 on metric `name`, in H1's convention: per week Delta_w = min over `comp` of m minus
    m(Sublet-lag) (ms5b_common.paired_margins, as ms5b_analysis.h1; 'best' the attaining policy), None with the
    missing rows when a value is missing (a loss for Sublet-lag); the counts of wins (Delta_w > 0), ties and losses,
    and describe() over the weeks with a value."""
    sub = {w: metric(lagged_table(s, SUBLET), SUBLET, w, name) for w in weeks}
    oth = {p: {w: metric(lagged_table(s, p), lagged_tag(p), w, name) for w in weeks} for p in comp}
    mg = m5.paired_margins(sub, oth, weeks)
    rows, wins, ties, losses, lost = {}, 0, 0, 0, 0
    for w in weeks:
        g = mg[w]
        d = g["delta"]
        if d is None:
            rows[w] = {"delta": None, "best": None, "missing": [SUBLET if t == "Sublet" else t for t in g["missing"]],
                       "sublet": sub[w]}
            lost += 1
            continue
        wins += d > 0
        ties += d == 0
        losses += d < 0
        rows[w] = {"delta": d, "best": g["best"], "best_value": g["best_r0"], "sublet": g["sublet_r0"], "missing": []}
    return {"metric": name, "set": list(comp), "weeks": rows, "n_weeks": len(weeks), "n_wins": int(wins),
            "n_ties": int(ties), "n_losses": int(losses), "n_lost_missing": int(lost),
            **describe([r["delta"] for r in rows.values()]),
            "sign": "delta = min over the set minus Sublet-lag (H1's convention): delta > 0, Sublet-lag is cheaper "
                    "than every policy of the set in that week"}


def lag_deltas(s: dict, weeks: list) -> dict:
    """Quantity 4: {policy: {'revealed': tag, metric: {'weeks': {w: lagged - revealed}, **describe, 'revealed':
    {'weeks': {w: revealed value}, **describe}}}}."""
    rev_tab = (s.get("main") or {}).get("table")
    out = {}
    for p in POLICIES:
        tab, rt = lagged_table(s, p), revealed_tag(p)
        row = {"revealed": rt, "lagged_from": "main" if p in ct.LAGGED_FROM_MAIN else "lag"}
        for k in METRICS:
            d, rv = {}, {}
            for w in weeks:
                a, b = metric(tab, lagged_tag(p), w, k), metric(rev_tab, rt, w, k)
                rv[w] = b
                d[w] = None if a is None or b is None else a - b
            row[k] = {"weeks": d, **describe(list(d.values())),
                      "revealed": {"weeks": rv, **describe(list(rv.values()))}}
        out[p] = row
    return out


def guard_runs(s: dict) -> dict:
    """Quantity 5: per run of the guarded lag tags (part lag's rows with a guard) the projected slots, abort, t_a,
    certificate and envelope; totals per tag and per (tag, mode)."""
    rows = [r for r in (s.get("lag") or {}).get("runs") or [] if r.get("tag") in ct.GUARD_REALIZED and r.get("guard")]
    runs = [{"tag": r["tag"], "mode": r["mode"], "cell": r["cell"], "seed": r["seed"], "status": r.get("status"),
             "projected_slots": int(r["guard"].get("projected_slots") or 0), "aborted": bool(r["guard"].get("aborted")),
             "t_a": r["guard"].get("t_a"), "held": r["guard"].get("held"), "env_ok": r["guard"].get("env_ok"),
             "K0": int((r["guard"].get("projection") or {}).get("K0") or 0)} for r in rows]

    def tot(xs):
        return {"runs": len(xs), "runs_projected": sum(1 for x in xs if x["projected_slots"]),
                "projected_slots": sum(x["projected_slots"] for x in xs), "aborts": sum(1 for x in xs if x["aborted"]),
                "held": sum(1 for x in xs if x["held"] is True),
                "envelope_violations": sum(1 for x in xs if x["env_ok"] is False), "K0": sum(x["K0"] for x in xs)}
    by_tag = {t: tot([x for x in runs if x["tag"] == t]) for t in ct.GUARD_REALIZED}
    by_mode = {t: {m: tot([x for x in runs if x["tag"] == t and x["mode"] == m]) for m in m5.conf_modes()}
               for t in ct.GUARD_REALIZED}
    return {"runs": runs, "by_tag": by_tag, "by_tag_mode": by_mode,
            "label": {"Sublet-lag": "inner A9 lagged; the guard's test on the realized slot",
                      "BL1-GP-lag": "inner lagged; the guard reads the realized slot"}}


def identity(s: dict) -> dict:
    """Quantity 6: r0(Sublet-lag) against r0(A9-lag) on every (week, mode, seed) of an ok Sublet-lag run without a
    projected slot and without an abort, both runs ok."""
    lag = s.get("lag") or {}
    tab = lag.get("table") or {}
    pairs, left_out, missing = [], [], []
    for r in lag.get("runs") or []:
        if r.get("tag") != SUBLET:
            continue
        g = r.get("guard") or {}
        key = {"mode": r["mode"], "cell": r["cell"], "seed": r["seed"]}
        if r.get("status") != "ok":
            missing.append({**key, "why": f"Sublet-lag run {r.get('status')}"})
            continue
        if int(g.get("projected_slots") or 0) or g.get("aborted"):
            left_out.append({**key, "projected_slots": int(g.get("projected_slots") or 0),
                             "aborted": bool(g.get("aborted"))})
            continue
        b = val(tab, INNER, r["mode"], r["cell"], r["seed"])
        if b is None:
            missing.append({**key, "why": "no ok A9-lag run"})
            continue
        a = float(r["r0"])
        pairs.append({**key, "sublet": a, "a9": b, "diff": a - b, "exact": a == b})
    diffs = [abs(p["diff"]) for p in pairs]
    return {"n_pairs": len(pairs), "n_exact": sum(1 for p in pairs if p["exact"]),
            "max_abs_diff": max(diffs) if diffs else None, "holds": bool(pairs) and all(p["exact"] for p in pairs),
            "n_left_out": len(left_out), "left_out": left_out, "n_missing": len(missing), "missing": missing,
            "pairs": pairs, "rule": "exact float equality on runs without projection and without abort"}


def gate_outcome(s: dict) -> dict:
    """Quantity 7: part gate's decision and the commits of parts gate and lag."""
    g, lag = s.get("gate") or {}, s.get("lag") or {}
    d = g.get("decision") or {}
    rg, rl = (g.get("meta") or {}).get("git_revision"), (lag.get("meta") or {}).get("git_revision")
    return {"found": bool(g), "pass": d.get("pass"), "n_checks": d.get("n_checks"), "n_equal": d.get("n_equal"),
            "n_no_reference": d.get("n_no_reference"), "max_abs_diff": d.get("max_abs_diff"),
            "gate_revision": rg, "lag_revision": rl, "same_commit": rg is not None and rg == rl,
            "gate_reduced": (g.get("meta") or {}).get("reduced"), "lag_reduced": (lag.get("meta") or {}).get("reduced")}


def registration(sha: str, repo=None) -> dict:
    """This file's sha256 against the one design/ms7/registration.md records (read from the working tree of `repo`,
    default this repository; e7c.registered_sha256's line): {'path', 'exists', 'registered_sha256', 'matches'}."""
    f = Path(paths.REPO if repo is None else repo) / e7c.REGISTRATION
    want = e7c.registered_sha256(f.read_text(encoding="utf-8", errors="replace")) if f.is_file() else None
    return {"path": e7c.REGISTRATION, "exists": f.is_file(), "registered_sha256": want,
            "matches": want is not None and want == sha}


def analyse(s: dict, repo=None) -> dict:
    lag = s.get("lag") or {}
    weeks = weeks_of(lag.get("table") or {})
    sha = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    red = (lag.get("meta") or {}).get("reduced")
    return {"meta": {"exp": EXP, "spec": "design/ms7/plan.md X1, D4, D6 (C53)", "git_revision": mc.git_revision(),
                     "written": mc._now(), "analysis_sha256": sha, "registration": registration(sha, repo),
                     "inputs": s.get("inputs"), "weeks": weeks, "n_weeks": len(weeks),
                     "weeks_are_confirmation_weeks": weeks == WEEKS_FULL, "reduced": red,
                     "note": "descriptive: per week, median, min, max and sign counts; no p-values (D4)"},
            "policies": list(POLICIES), "h1_set": list(H1_SET), "notice_set": list(NOTICE_SET),
            "per_policy": per_policy(s, weeks),
            "margins": {"h1": {k: margins(s, weeks, H1_SET, k) for k in MARGIN_METRICS},
                        "notice": {k: margins(s, weeks, NOTICE_SET, k) for k in MARGIN_METRICS}},
            "lag_minus_revealed": lag_deltas(s, weeks), "guard": guard_runs(s), "identity": identity(s),
            "gate": gate_outcome(s)}


# ---------------------------------------------------------------- report
def _f(x, d: int = 4) -> str:
    return "-" if x is None else (f"{x:.{d}f}" if isinstance(x, float) else str(x))


def _rng(d: dict) -> str:
    return f"[{_f(d['min'])}, {_f(d['max'])}]"


def _rows(block: dict, policies, lead, tail=None) -> list:
    """Table rows of per_policy or lag_minus_revealed: lead(policy, row), the medians, the [min, max] cells and
    tail(policy, row)."""
    return [lead(p, block[p]) + [_f(block[p][k]["median"]) for k in METRICS] + [_rng(block[p][k]) for k in METRICS]
            + (tail(p, block[p]) if tail else []) for p in policies]


def report(a: dict) -> str:
    m = a["meta"]
    head = [f"{k} median" for k in METRICS] + [f"{k} [min, max]" for k in METRICS]
    rg = m["registration"]
    lines = [f"# E7c analysis ({m['spec']})", "", f"Weeks: {m['n_weeks']} (the confirmation weeks: "
             f"{m['weeks_are_confirmation_weeks']}); reduced: {m['reduced']}; {m['note']}.", "",
             f"Analysis sha256 {m['analysis_sha256'][:12]}; {rg['path']} records "
             f"{str(rg['registered_sha256'])[:12]}; matches {rg['matches']}.", ""]
    lines += ["## Lagged policies (median over the weeks; min, max)", "",
              mc.md_table(["policy"] + head + ["weeks r0 < 1", "weeks W0 < 1"],
                          _rows(a["per_policy"], a["policies"], lambda p, row: [p],
                                tail=lambda p, row: [row["r0"]["n_below_1"], row["W0"]["n_below_1"]])), ""]
    for nm, title in (("h1", "H1's set"), ("notice", "the notice-aware set")):
        for k in MARGIN_METRICS:
            g = a["margins"][nm][k]
            lines += [f"## Margin of Sublet-lag against {title}, {k}: min over ({', '.join(g['set'])}) minus "
                      f"Sublet-lag", "",
                      f"wins (delta > 0) {g['n_wins']}, ties {g['n_ties']}, losses {g['n_losses']}, decided by a "
                      f"missing run {g['n_lost_missing']} of {g['n_weeks']} weeks; median {_f(g['median'])}, "
                      f"min {_f(g['min'])}, max {_f(g['max'])}", "",
                      mc.md_table(["week", "delta", "best", "Sublet-lag", "best value"],
                                  [[w, _f(r["delta"]), r["best"], _f(r["sublet"]), _f(r.get("best_value"))]
                                   for w, r in g["weeks"].items()]), ""]
    lines += ["## Lagged minus revealed (median; min, max), beside the revealed medians", "",
              mc.md_table(["policy", "revealed"] + head + [f"revealed {k} median" for k in METRICS],
                          _rows(a["lag_minus_revealed"], a["policies"], lambda p, row: [p, row["revealed"]],
                                tail=lambda p, row: [_f(row[k]["revealed"]["median"]) for k in METRICS])), ""]
    g = a["guard"]
    lines += ["## Guard (inner lagged, test on the realized slot)", "",
              mc.md_table(["tag", "runs", "runs projected", "projected slots", "aborts", "held", "envelope violations"],
                          [[t, v["runs"], v["runs_projected"], v["projected_slots"], v["aborts"], v["held"],
                            v["envelope_violations"]] for t, v in g["by_tag"].items()]), ""]
    i = a["identity"]
    lines += ["## r0(Sublet-lag) = r0(A9-lag) without projection", "",
              f"pairs {i['n_pairs']}, exact {i['n_exact']}, max |diff| {_f(i['max_abs_diff'], 3)}, holds {i['holds']}; "
              f"left out (projected or aborted) {i['n_left_out']}, missing {i['n_missing']}", ""]
    ga = a["gate"]
    lines += ["## Part gate", "",
              f"found {ga['found']}, pass {ga['pass']} ({ga['n_equal']} of {ga['n_checks']} equal), same commit as "
              f"part lag {ga['same_commit']}", ""]
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m sublet.experiments.e7c_analysis", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=None, help="folder whose out/ holds e7c/ and sublet_v2/ (default MS3_ROOT or "
                                                 "this repository's code/sim)")
    ap.add_argument("--out", type=Path, default=None, help="output folder (default <root>/out/e7c)")
    a = ap.parse_args(argv)
    s = load(a.root)
    if s.get("lag") is None:
        print(f"[e7c_analysis] no part lag summary: {s['inputs']['lag']['path']}", file=sys.stderr)
        return 2
    res = analyse(s)
    rg = res["meta"]["registration"]
    if not rg["matches"]:
        print(f"[e7c_analysis] WARNING: this file's sha256 {res['meta']['analysis_sha256'][:12]} is not the one "
              f"{rg['path']} records ({str(rg['registered_sha256'])[:12]}); the output says so (meta.registration)",
              file=sys.stderr)
    out = a.out if a.out is not None else mc.ms3_root(a.root) / "out" / EXP
    mc.dump_json(res, Path(out) / "analysis.json")
    mc.write_text(report(res), Path(out) / "analysis.md")
    print(f"[e7c_analysis] {res['meta']['n_weeks']} weeks; identity holds {res['identity']['holds']}; gate pass "
          f"{res['gate']['pass']}; wrote {Path(out) / 'analysis.json'}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
