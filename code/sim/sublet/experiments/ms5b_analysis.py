"""MS5b analysis: the confirmation hypotheses H1-H6 and H2b from the part summaries (design/sublet_v2.md §4.5, §6,
§8.1; unit U35). Its sha256 is recorded in design/sublet_v2_prereg.md after its dry run on the pilot outputs (P6),
and the confirmation parts of e7h.py refuse to start unless the file still has that sha256; so every rule below is
fixed, deterministic and complete, and CONFIG holds the only values the pilot sets (§6: H5's status from P4, H6's
threshold from P2's allowance branch, H4's wording from P3), which P6 fills in before the hash is taken.

Inputs: <root>/out/sublet_v2/<part>/summary.json of e7h's confirmation parts (main, seeds, second, e3, fam, grid);
with --pilot, the pilot summaries <root>/out/sublet_v2_pilot/{p1, p1r, p2r, p3, p3r, p4}/summary.json read in the
same shapes (the dry run of P6, after P2's allowance branch: p1, p1r and p2r as main, so that Sublet's week runs are
p2r's at the allowance P2 selected and p2's runs at Algorithm 1's allowance are left out; p3 as fam with its Sublet
rows replaced by p3r's; p4's ratios as e3). Output: <out>/analysis.json and analysis.md
(default <root>/out/sublet_v2/; with --pilot <root>/out/sublet_v2_pilot/).

Rules (copied from §6 and §4.5; r0 is a run's overflow cost over BL0a, W0 the largest r0 over the five stress modes,
policy seed 0, weeks the cells of main's table):
  H1  primary, trace: Sublet's L-tr r0 below the per-week minimum over H1's set {BL1, BL1-BO, BL2, BL3-0, BL4, BL5,
      BL5-cur} in at least 12 of 16 weeks (one-sided sign test, p = 2517/65536 for 12 of 16; descriptive), and the
      median paired margin Delta_w = min_set r0 - r0(Sublet) >= 0.02 BL0a with a week-bootstrap 95% interval above 0
      (10,000 resamples, numpy.random.default_rng(20261031)); the one-sided Wilcoxon signed-rank test is reported.
  H2  primary, robustness: per week Sublet's W0 < 1 in 16 of 16 weeks and below the W0 of every policy of H1's set in
      16 of 16 weeks; the median of Sublet's W0 <= 0.85.
  H2b secondary: Sublet's W0 below that of BL5-tau60, BL1-GP, BL1N and BL5N in 16 of 16 weeks.
  H3  primary, certificate: in every guarded run (A8P and A8 rows, all parts) the certificate holds and the envelope
      ALG(t) + R(t) <= gamma C_S(t) + B(t) + tolerance holds at every executed slot; no A8P run in which S follows FB
      at every slot and T0g stays in bound form aborts (a projecting run: project true; the one-way rows, A8 and
      Sublet-1way, are counted apart); aborts, switches of S, robust-form runs, projected slots, dropped Buys and K0
      uses are reported.
  H4  primary, families: on every counted F1/F2 run (the confirmation's fresh instances; the Q6 instances under F-ss
      and F-iid) A9 equals RR_RENEW in total cost and purchase count, and Sublet projects in no such run; F3 against
      BL1-G, BL5-G and A9 alone, no criterion. With P3's wording 'A9' (§6, H4's consequence: Sublet projects on a
      counted run) H4 states the identity for A9 alone and reports the number of runs in which Sublet projects.
  H5  primary or secondary (CONFIG, from P4): on E3 at config seeds 301-304, the median over the seeds of Sublet's
      ALG/LB <= that of Sublet-MS4 at every b, and the median over the seeds of Sublet's shared ALG/LB below that of
      Sublet siloed at every b >= 2 (LB: the shared instance's bound by Q39's rule).
  H6  secondary: the median of r0(Sublet) - r0(A9) over the trace and stress week runs of (a) <= 0.01 BL0a (no
      threshold if CONFIG['H6_threshold'] is None).
Missing runs (§4.5): a run that is missing or failed after its rerun (null in the summaries' tables) makes the week a
loss for Sublet in every hypothesis that uses it: a margin it decides is LOSS_MARGIN (below every real margin), a
price it decides is LOSS_PRICE (above every real price), a W0 comparison it decides fails; statistics that a loss
decides are written as null with a note. Reported with no threshold: the transplants (Sublet against BL1N and BL5N
per week), the per-week Pareto front of L-tr r0 and W0 over the tags of §3 that are not ablations of A9, the
stress-intensity curve over the iid_step grids of (a) and (b) together (main's and second's runs of the same tag,
week and policy seed merged before the crossing of 1 is found), RC under every mode (each run paired with the L-hon
run of the same tag, week and policy seed from main or seeds, so second's modes get their RC from main's L-hon runs),
policy seeds 1-2, the second part's results, the development-exposed grid.
"""
from __future__ import annotations

import argparse
import statistics
import sys
from pathlib import Path
from typing import Optional

from . import ms3_common as mc
from . import ms5b_common as m5

# set at P6 from the pilot (§6), before the sha256 of this file is recorded in design/sublet_v2_prereg.md; values as
# set on 2026-11-02: P4 made H5 primary, P2 selected the alternative allowance (kept by p2r), so H6 keeps its
# threshold, and p3r found no projecting Sublet run on F1/F2, so H4 keeps the wording 'deployed'
CONFIG = {"H5_status": "primary",          # P4: 'primary' or 'secondary'
          "H6_threshold": 0.01,            # P2: None if Algorithm 1's allowance was kept after both allowances failed
          "H4_wording": "deployed"}        # P3: 'deployed' (Sublet equals RR-renew) or 'A9' (the identity for A9 only)
H1_WINS = 12
H1_MARGIN = 0.02
H2_MEDIAN = 0.85
LOSS_MARGIN = -1.0e9
LOSS_PRICE = 1.0e9
LOSS_LIMIT = 1.0e8
# the tags of §3 that are not ablations of A9 (§3 flags BL1N, CR and the A9-* tags as ablations of our method)
PARETO_TAGS = tuple(t for t in m5.E7_TAGS if t not in ("BL1N", "CR") + m5.ABLATIONS)
COUNTED_Q6_MODES = ("F-ss", "F-iid")
PILOT_AS = {"main": ("p1", "p1r", "p2r"), "fam": ("p3", "p3r"), "e3": ("p4",)}


# ---------------------------------------------------------------- inputs
def load(root: Path, pilot: bool = False) -> dict:
    """{part: summary} of the confirmation parts (with pilot, the pilot summaries in their shapes; missing: absent)."""
    base = mc.ms3_root(root) / "out" / (m5.PILOT_DIR if pilot else m5.CONF_DIR)
    if not pilot:
        return {p: s for p in m5.CONF_PARTS if (s := mc.read_json(base / p / "summary.json")) is not None}
    got = {p: mc.read_json(base / p / "summary.json") for ps in PILOT_AS.values() for p in ps}
    out = {}
    tabs = [got[p] for p in PILOT_AS["main"] if got.get(p)]
    if tabs:
        table: dict = {}
        for s in tabs:
            for t, by_m in s["table"].items():
                for m, by_c in by_m.items():
                    for c, by_s in by_c.items():
                        if c.isdigit():
                            table.setdefault(t, {}).setdefault(m, {}).setdefault(c, {}).update(by_s)
        out["main"] = {"table": table, "guarded": [g for s in tabs for g in s.get("guarded") or []],
                       "missing": [x for s in tabs for x in s.get("missing") or []], "RC": {}}
    fam = [got[p] for p in PILOT_AS["fam"] if got.get(p)]
    if fam:
        # a later part repeats an earlier part's runs of the tags it holds (p3r: P3's Sublet runs at the allowance
        # P2 selected, §5 P3's row): those tags' runs, table rows, guarded and missing records come from it
        s = dict(fam[0])
        for r in fam[1:]:
            tags = set(r.get("table") or {}) | {x["tag"] for x in r.get("runs") or []}
            for k in ("runs", "guarded", "missing"):
                s[k] = [x for x in s.get(k) or [] if x.get("tag") not in tags] + list(r.get(k) or [])
            kept = {t: v for t, v in (s.get("table") or {}).items() if t not in tags}
            s["table"] = {**kept, **(r.get("table") or {})}
        out["fam"] = s
    if got.get("p4"):
        d = got["p4"].get("decision") or {}
        e3 = {}
        for name, by_cell in (d.get("ratios") or {}).items():
            for cell, v in by_cell.items():
                e3.setdefault(cell, {"ratios": {}})["ratios"][name] = v
        out["e3"] = {"e3": e3, "guarded": got["p4"].get("guarded") or [], "missing": got["p4"].get("missing") or []}
    return out


def val(table: dict, tag: str, mode: str, cell: str, seed: int = 0) -> Optional[float]:
    return ((table.get(tag) or {}).get(mode) or {}).get(cell, {}).get(str(seed))


def weeks_of(table: dict) -> list:
    cells = {c for by_m in table.values() for by_c in by_m.values() for c in by_c}
    return sorted((c for c in cells if c.isdigit()), key=int)


def w0(table: dict, tag: str, cell: str) -> Optional[float]:
    v, _m, _miss = m5.w0_of({m: val(table, tag, m, cell) for m in m5.stress_modes()})
    return v


def _clean(x: Optional[float], limit: float = LOSS_LIMIT) -> Optional[float]:
    return None if x is None or abs(x) >= limit else float(x)


def _stat_block(values: list) -> dict:
    """Median, bootstrap interval and Wilcoxon test of margins with LOSS_MARGIN for missing weeks."""
    if not values:
        return {"n": 0, "median": None, "ci": [None, None], "wilcoxon": None}
    b = m5.bootstrap_median_ci(values)
    w = m5.wilcoxon_signed_rank(values)
    lost = sum(1 for v in values if v <= -LOSS_LIMIT)
    out = {"n": len(values), "n_loss_weeks": lost, "median": _clean(b["median"]), "ci": [_clean(x) for x in b["ci"]],
           "B": b["B"], "seed": b["seed"], "wilcoxon": {k: w.get(k) for k in ("n_nonzero", "W_plus", "p")}}
    if lost:
        out["note"] = f"{lost} week(s) lost by the missing-run rule (margin below every real margin)"
    return out


# ---------------------------------------------------------------- hypotheses
def h1(s: dict) -> dict:
    tab = s["table"]
    weeks = weeks_of(tab)
    sub = {w: val(tab, "Sublet", "L-tr", w) for w in weeks}
    oth = {t: {w: val(tab, t, "L-tr", w) for w in weeks} for t in m5.H1_SET}
    mg = m5.paired_margins(sub, oth, weeks)
    d = [LOSS_MARGIN if mg[w]["delta"] is None else mg[w]["delta"] for w in weeks]
    wins = sum(1 for x in d if x > 0)
    st = _stat_block(d)
    sign = m5.sign_test_p(wins, len(weeks))
    ok = wins >= H1_WINS and st["median"] is not None and st["median"] >= H1_MARGIN and st["ci"][0] is not None \
        and st["ci"][0] > 0
    return {"kind": "primary", "weeks": weeks, "margins": mg, "wins": wins, "n_weeks": len(weeks), "sign_test": sign,
            "median_margin": st, "pass": bool(ok and len(weeks) == 16),
            "threshold": {"wins": H1_WINS, "median_margin": H1_MARGIN, "ci_low": 0.0},
            "note": "descriptive tests (§4.5, Dependence); every week's result is listed"}


def h2(s: dict, tags=m5.H1_SET, kind: str = "primary") -> dict:
    tab = s["table"]
    weeks = weeks_of(tab)
    rows, below1, below_all = [], 0, 0
    for w in weeks:
        a = w0(tab, "Sublet", w)
        o = {t: w0(tab, t, w) for t in tags}
        b1 = a is not None and a < 1.0
        ba = a is not None and all(v is not None and a < v for v in o.values())
        below1 += b1
        below_all += ba
        rows.append({"week": w, "Sublet": a, "others": o, "below_1": b1, "below_all": ba})
    med = statistics.median([r["Sublet"] for r in rows]) if rows and all(r["Sublet"] is not None for r in rows) \
        else None
    n = len(weeks)
    if kind == "primary":
        ok = n == 16 and below1 == n and below_all == n and med is not None and med <= H2_MEDIAN
    else:
        ok = n == 16 and below_all == n
    out = {"kind": kind, "set": list(tags), "weeks": rows, "n_weeks": n, "weeks_below_1": below1,
           "weeks_below_set": below_all, "pass": bool(ok)}
    if kind == "primary":
        mc.put(out, "median_W0", med, "a week without W0 (missing-run rule)")
    return out


def _guarded(parts: dict) -> tuple[list, list]:
    g, miss = [], []
    for p, s in parts.items():
        g += [{"part": p, **x} for x in s.get("guarded") or []]
        miss += [{"part": p, **x} for x in s.get("missing") or [] if m5.is_guarded(x["tag"])]
    return g, miss


def h3(parts: dict) -> dict:
    g, miss = _guarded(parts)
    bad_cert = [x for x in g if x.get("held") is not True]
    bad_env = [x for x in g if x.get("env_ok") is False]
    # Proposition P: a projecting run (A8P with project true); the one-way rows (A8, Sublet-1way) are counted apart
    prop = [x for x in g if x.get("project") is True and x.get("aborted") and x.get("s_fb_all")
            and x.get("t0g_bound_all")]
    one_way = [x for x in g if x.get("project") is not True and x.get("aborted")]
    ok = bool(g) and not bad_cert and not bad_env and not prop and not miss
    return {"kind": "primary", "n_runs": len(g), "n_not_held": len(bad_cert), "not_held": bad_cert[:100],
            "n_envelope_violations": len(bad_env), "envelope_violations": bad_env[:100],
            "n_aborts_s_fb_bound_form": len(prop), "aborts_s_fb_bound_form": prop[:100],
            "n_missing_guarded_runs": len(miss), "missing_guarded_runs": miss[:100],
            "one_way_aborts": len(one_way),
            "aborts": sum(1 for x in g if x.get("aborted")),
            "runs_with_switches": sum(1 for x in g if x.get("switches")),
            "runs_with_robust_slots": sum(1 for x in g if x.get("robust_slots")),
            "projected_slots": sum(int(x.get("projected_slots") or 0) for x in g),
            "runs_projected": sum(1 for x in g if x.get("projected_slots")),
            "dropped_buys": sum(int((x.get("projection") or {}).get("dropped_buys") or 0) for x in g),
            "K0": sum(int((x.get("projection") or {}).get("K0") or 0) for x in g), "pass": ok}


def _counted(r: dict) -> bool:
    return r.get("fam") in ("F1", "F2") and (not str(r.get("src", "")).startswith("F")
                                             or r.get("mode") in COUNTED_Q6_MODES)


def h4(s: dict) -> dict:
    rows = [r for r in s.get("runs") or [] if r.get("kind") == "fam"]
    by = {(r["inst"], r["mode"], r["seed"], r["tag"]): r for r in rows if r.get("status") == "ok"}
    pairs, bad, missing = 0, [], []
    for r in rows:
        if r["tag"] != "A9" or not _counted(r):
            continue
        rr = by.get((r["inst"], r["mode"], r["seed"], "RR_RENEW")) or next(
            (x for k, x in sorted(by.items(), key=lambda kv: str(kv[0])) if k[0] == r["inst"] and k[1] == r["mode"]
             and k[3] == "RR_RENEW"), None)
        if r.get("status") != "ok" or rr is None:
            missing.append({"inst": r["inst"], "mode": r["mode"], "seed": r["seed"]})
            continue
        pairs += 1
        if abs(r["total"] - rr["total"]) > 1e-9 * max(1.0, abs(rr["total"])) or r["n_purchases"] != rr["n_purchases"]:
            bad.append({"inst": r["inst"], "mode": r["mode"], "seed": r["seed"],
                        "A9": [r["total"], r["n_purchases"]], "RR_RENEW": [rr["total"], rr["n_purchases"]]})
    miss_runs = [x for x in s.get("missing") or [] if x["tag"] in ("A9", "RR_RENEW", "Sublet")]
    proj = [{"inst": r["inst"], "mode": r["mode"], "seed": r["seed"]} for r in rows
            if r["tag"] == "Sublet" and _counted(r) and (r.get("guard") or {}).get("projected_slots")]
    f3 = {}
    for r in rows:
        if r.get("fam") == "F3" and r.get("status") == "ok":
            f3.setdefault(r["tag"], []).append(r.get("ratio_opt"))
    ident = pairs > 0 and not bad and not missing and not miss_runs
    # P3's wording (§6): 'deployed' claims that Sublet equals RR-renew (identity and no projecting run); 'A9' states
    # the identity for A9 alone and reports Sublet's projecting runs
    ok = ident if CONFIG["H4_wording"] == "A9" else (ident and not proj)
    return {"kind": "primary", "n_counted_pairs": pairs, "mismatches": bad, "missing_pairs": missing,
            "missing_runs": miss_runs[:100], "identity_holds": ident, "sublet_projected_runs": len(proj),
            "sublet_projected": proj[:100], "pass": bool(ok),
            "wording": CONFIG["H4_wording"],
            "f3_ratio_opt": {t: {"mean": statistics.fmean([x for x in v if x is not None]) if any(
                x is not None for x in v) else None, "n": len(v)} for t, v in sorted(f3.items())}}


def _ratios(s: dict) -> dict:
    out: dict = {}
    for cell, v in (s.get("e3") or {}).items():
        for name, r in (v.get("ratios") or {}).items():
            out.setdefault(name, {})[cell] = r
    return out


def h5(s: dict) -> dict:
    rat = _ratios(s)
    cells = sorted({c for v in rat.values() for c in v})
    bs = sorted({int(c.split(":")[0][1:]) for c in cells})
    seeds = sorted({c.split(":")[1] for c in cells})

    def med(name, b):
        v = [(rat.get(name) or {}).get(f"b{b}:{c}") for c in seeds]
        return None if not v or any(x is None for x in v) else statistics.median(v)
    rows, ok1, ok2 = [], True, True
    for b in bs:
        sh, ms4, si = med("Sublet:shared", b), med("Sublet-MS4:shared", b), med("Sublet:siloed", b)
        c1 = sh is not None and ms4 is not None and sh <= ms4
        c2 = b < 2 or (sh is not None and si is not None and sh < si)
        ok1, ok2 = ok1 and c1, ok2 and c2
        rows.append({"b": b, "Sublet_shared": sh, "Sublet_MS4_shared": ms4, "Sublet_siloed": si,
                     "le_MS4": c1, "shared_below_siloed": c2})
    return {"kind": CONFIG["H5_status"], "b": rows, "seeds": seeds, "pass": bool(bs) and ok1 and ok2}


def h6(s: dict) -> dict:
    tab = s["table"]
    weeks = weeks_of(tab)
    diffs, lost = [], 0
    for w in weeks:
        for m in m5.main_modes():
            a, b = val(tab, "Sublet", m, w), val(tab, "A9", m, w)
            if a is None or b is None:
                diffs.append(LOSS_PRICE)
                lost += 1
            else:
                diffs.append(a - b)
    med = statistics.median(diffs) if diffs else None
    thr = CONFIG["H6_threshold"]
    out = {"kind": "secondary", "n": len(diffs), "n_loss": lost, "threshold": thr,
           "pass": None if thr is None else bool(med is not None and med <= thr and med < LOSS_LIMIT)}
    mc.put(out, "median_price", _clean(med), "decided by a missing run" if med is not None else "no run")
    return out


# ---------------------------------------------------------------- reported in full
def intensity_curves(parts: dict) -> dict:
    """{tag: {week: curve}}: the stress-intensity curve (§4.5) of every tag and week on the iid_step grids of (a) and
    (b) together, policy seed 0: main's and second's tables merged per (tag, week) before m5.intensity_curve finds
    the first p with r0 > 1. A point enters when the tag's grid in either part holds that mode for that week (null
    if its run is missing, which the curve notes); a week without second's runs has (a)'s points only."""
    tabs = [(parts.get(p) or {}).get("table") or {} for p in ("main", "second")]
    out: dict = {}
    for t in sorted({t for tab in tabs for t in tab}):
        weeks = sorted({c for tab in tabs for by_c in (tab.get(t) or {}).values() for c in by_c if c.isdigit()},
                       key=int)
        for c in weeks:
            pts = {}
            for p in m5.CURVE_P:
                m = m5.iid_mode(p)
                have = [tab for tab in tabs if c in ((tab.get(t) or {}).get(m) or {})]
                if have:
                    pts[p] = next((v for v in (val(tab, t, m, c) for tab in have) if v is not None), None)
            if len(pts) > 1:
                out.setdefault(t, {})[c] = m5.intensity_curve(pts)
    return out


def rc_all(parts: dict) -> dict:
    """RC (§4.5) under every mode: every ok week run of main, seeds and second paired with the ok L-hon run of the
    same tag, week and policy seed (main's and seeds' L-hon runs; second has none), {tag: {mode: {week: {seed:
    RC}}}}."""
    rows = [{**r, "config_seed": r["c"], "policy_seed": r["seed"]} for p in ("main", "seeds", "second")
            for r in (parts.get(p) or {}).get("runs") or [] if r.get("kind") == "week" and r.get("status") == "ok"]
    return m5.rc_rows(rows)


def reported(parts: dict) -> dict:
    main = parts.get("main") or {}
    tab = main.get("table") or {}
    weeks = weeks_of(tab)
    trans = {w: {t: {"L-tr": val(tab, t, "L-tr", w), "W0": w0(tab, t, w)} for t in ("Sublet", "BL1N", "BL5N")}
             for w in weeks}
    pareto = {}
    for w in weeks:
        pts = {t: (val(tab, t, "L-tr", w), w0(tab, t, w)) for t in PARETO_TAGS}
        pts = {t: p for t, p in pts.items() if None not in p}
        pareto[w] = sorted(t for t, (a, b) in pts.items()
                           if not any((x <= a and y <= b) and (x < a or y < b) for u, (x, y) in pts.items() if u != t))
    curves = intensity_curves(parts)
    cross = {t: {c: cv.get("first_p_above_1") for c, cv in by_c.items()} for t, by_c in curves.items()}
    return {"transplants": trans, "pareto_front": pareto, "intensity_crossings": cross, "intensity_curves": curves,
            "RC": rc_all(parts),
            "seeds": (parts.get("seeds") or {}).get("table"),
            "second": {k: (parts.get("second") or {}).get(k) for k in ("gap_ratio", "W0")},
            "grid_development_exposed": {k: (parts.get("grid") or {}).get(k) for k in ("W0", "gap_ratio")}}


def analyse(parts: dict) -> dict:
    main = parts.get("main")
    out = {"config": dict(CONFIG), "parts_found": sorted(parts)}
    for k, fn, src in (("H1", h1, "main"), ("H2", h2, "main"), ("H6", h6, "main"), ("H4", h4, "fam"),
                       ("H5", h5, "e3")):
        out[k] = fn(parts[src]) if parts.get(src) else {"pass": None, "note": f"no {src} summary"}
    out["H2b"] = h2(main, m5.H2B_SET, "secondary") if main else {"pass": None, "note": "no main summary"}
    out["H3"] = h3(parts)
    out["reported"] = reported(parts)
    return out


def markdown(a: dict) -> str:
    lines = ["# MS5b confirmation analysis (design/sublet_v2.md §6)", ""]
    rows = []
    for k in ("H1", "H2", "H2b", "H3", "H4", "H5", "H6"):
        h = a.get(k) or {}
        rows.append([k, h.get("kind"), h.get("pass")])
    lines += [mc.md_table(["hypothesis", "kind", "pass"], rows), ""]
    h = a.get("H1") or {}
    if h.get("margins"):
        lines += ["## H1: per-week margins (min over H1's set minus Sublet, L-tr)", "",
                  mc.md_table(["week", "Delta", "best", "missing"],
                              [[w, x["delta"], x["best"], ",".join(x["missing"])] for w, x in h["margins"].items()]),
                  ""]
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m sublet.experiments.ms5b_analysis", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=None, help="folder whose out/ holds sublet_v2/ (default MS3_ROOT or code/sim)")
    ap.add_argument("--out", type=Path, default=None, help="output folder (default the input folder)")
    ap.add_argument("--pilot", action="store_true", help="the dry run on the pilot summaries (P6)")
    a = ap.parse_args(argv)
    parts = load(a.root, a.pilot)
    res = analyse(parts)
    res["meta"] = {"script": m5.ANALYSIS_REL, "sha256": m5.analysis_sha256(), "pilot_dry_run": bool(a.pilot),
                   "git_revision": mc.git_revision(), "written": mc._now()}
    out = a.out or (mc.ms3_root(a.root) / "out" / (m5.PILOT_DIR if a.pilot else m5.CONF_DIR))
    mc.dump_json(res, Path(out) / "analysis.json")
    mc.write_text(markdown(res), Path(out) / "analysis.md")
    print("[ms5b_analysis] " + ", ".join(f"{k} {res[k].get('pass')}" for k in ("H1", "H2", "H2b", "H3", "H4", "H5",
                                                                                 "H6")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
