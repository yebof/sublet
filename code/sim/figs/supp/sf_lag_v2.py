"""sf_lag_v2: the causal-demand runs, with every policy on the previous slot's demand, on the confirmation weeks, with
the tables lag_v2_modes.tex, lag_v2_policies.tex, lag_v2_margins.tex, lag_v2_guard.tex and the data file
lag_v2_runs.csv (design/ms7/registration.md §2-§3, X1; design/ms7/w_spec.md §4, unit W-G4; design/ms7/plan.md X1;
change C58).

Question: does Sublet's ordering hold when every policy plans on the previous slot's demand? Every number is read from
the registered analysis code/sim/out/e7c/analysis.json (sublet/experiments/e7c_analysis.py, its sha256 in
design/ms7/registration.md), part lag's summary code/sim/out/e7c/lag/summary.json (the lagged runs' r0 under every
lender) and the confirmation's code/sim/out/sublet_v2/main/summary.json (the lagged RetroRenting-style rows, which part
main holds, and the revealed counterparts); the analysis's values are checked against the summaries (StyleError: a
stale input), and inputs from full runs must be the registered analysis on the 16 confirmation weeks
(check_registered; review of W-G4 A). The statistics are descriptive (registration §3; design/ms7/plan.md D4): per
week, the median, min and max over the weeks and sign counts; no p-value.

Figure (W2 x 2.5 in; block A of style.SUPP_POLICIES_MS7). Each panel's key sits on its letter's baseline, right of
the letter ((a): the two margins; (b), keying (b) and (c): lagged and revealed; ms7_a_lib.letter_keys; C62, in place of
the legend row of the four series, which keyed (a)'s and (b)'s series in one row).
(a) Per week, two sub-panels on one week axis: "Cost margin", the least L-tr r0 over the lagged primary baselines
    minus Sublet-lag's (analysis margins.h1.r0, the confirmation's convention: positive when Sublet costs less; filled
    hexagons, keyed "vs. best primary") and the same over the lagged notice-aware set (margins.notice.r0; open
    squares, "vs. best notice-aware"); "W0 margin", the same on W0 (the largest r0 over the five stress lenders;
    margins.*.W0). A week with a negative or missing margin of a sub-panel's series is shaded in that sub-panel; a
    missing run is a loss (registration §3).
(b) Per policy (one row each, named on the y axis by the registry label of the policy with the slot revealed, since
    each row draws the policy lagged and revealed (C62; as built, the lagged policy's label, ", lagged" on every row);
    groups: Sublet and its inner policy, the notice-aware set, the primary baselines), the L-tr r0 with every policy
    lagged (filled diamond: the median over the weeks; bar: min-max; analysis per_policy) and the same policy with the
    slot revealed (open circle and bar; the confirmation's runs, analysis lag_minus_revealed.<policy>.r0.revealed); the
    grey line marks all-fallback, named inside the axes at its top end, the line stopping short of the name
    (ms7_a_lib.line_label_inside; C62 fix round: as built the name stood above the axes on (b)'s key row, right of
    "Revealed slot", and read as a third key entry without a sample).
(c) The same for W0, sharing (b)'s rows.

Tables (after hook, figs.common.write_table; from the extract's `tables`, so --from-extract rewrites them; each with
its scope; ms5b_e7_lib.longtable, one-column mode):
  lag_v2_modes.tex     per lagged policy, r0 under each of the seven lenders: the median over the weeks and [min,
                       max] (the summaries' tables)
  lag_v2_policies.tex  per lagged policy, L-tr r0, W0 and RC (r0 under L-tr minus r0 under L-hon), and lagged minus
                       revealed of each (analysis per_policy and lag_minus_revealed): the median and [min, max], with
                       the weeks in which r0 and W0 are below 1
  lag_v2_margins.tex   the margins of (a) per set and metric: wins, ties, losses, the weeks a missing run decides,
                       median, min and max (analysis margins), and how often each policy is the least of its set
  lag_v2_guard.tex     the guard of Sublet-lag and greedy renting with the guard (inner policy lagged, the guard's test
                       on the realized slot) per lender: runs, runs with a projected slot, projected slots, K0 uses,
                       aborts, certificates held, envelope violations (analysis guard), with the identity r0(Sublet-lag)
                       = r0(A9-lag) on the runs without projection and abort (analysis identity) and the gate's
                       reproduction of the confirmation (analysis gate) in its caption
  lag_v2_runs.csv      every lagged run: policy, tag, the revealed policy and tag, lender, week, policy seed, r0
                       lagged and revealed (6 decimals) and, for the two guarded policies, projected slots, abort,
                       certificate held and envelope kept; the extract keeps its lines and sha256
In the lender and policy tables a dagger marks a median over fewer weeks (a missing run; ms7_a_lib.fewer_mark, review
of W-G4 A). labels.caption is a caption draft (no design names; every count read from the inputs).

RUN_INPUTS are the two run outputs of X1; figs/rebuild.py keeps the entry pending until they are copied in. A missing
input stops the script with exit code 2 and the file named; data from a reduced run is never written into
paper/supplement/ or code/sim/out/figs/ (ms7_a_lib.guard_reduced). Run from code/sim:
python -m figs.supp.sf_lag_v2 [--from-extract [JSON]].
"""
from __future__ import annotations

import sys
from collections import Counter
from typing import Any, Mapping, Sequence

from figs import style
from figs.common import MissingKey, need, write_table
from figs.inputs import Inputs
from figs.supp import ms5b_e7_lib as L
from figs.supp import ms7_a_lib as A
from sublet.experiments import ms5b_common as m5

NAME = "sf_lag_v2"
KEYS = style.SUPP_POLICIES_MS7[NAME]
E7C = "code/sim/out/e7c/analysis.json"
E7C_LAG = "code/sim/out/e7c/lag/summary.json"
MAIN = "code/sim/out/sublet_v2/main/summary.json"
RUN_INPUTS = (E7C, E7C_LAG)           # the MS7 run outputs this figure needs (figs/rebuild.py)
INPUTS = (E7C, E7C_LAG, MAIN)
TABLES = ("lag_v2_modes.tex", "lag_v2_policies.tex", "lag_v2_margins.tex", "lag_v2_guard.tex", "lag_v2_runs.csv")
RUNS_CSV = TABLES[-1]
SEED = 0
TRACE, HON = m5.TRACE_MODE, m5.HON_MODE
STRESS = tuple(m5.stress_modes())
MODE_ORDER = tuple(m5.conf_modes())
SUBLET, INNER = "Sublet-lag", "A9-lag"
KEY_OF_TAG = {**L.KEY_OF_TAG, **style.MS7_KEY_OF_TAG}
SETS = ("h1", "notice")
METRICS = ("r0", "W0")
SET_LABEL = {"h1": "Primary baselines", "notice": "Notice-aware policies"}
SERIES = {"h1_r0": "a", "notice_r0": "b", "h1_W0": "a", "notice_W0": "b", "lagged": "c", "revealed": "d"}
# the panels' keys (C62): (a)'s two margins, (b)'s lagged and revealed medians with their bars (keying (b) and (c))
LEGEND = {"a": (("a", "vs. best primary", False), ("b", "vs. best notice-aware", False)),
          "b": (("c", style.ENV_LABELS["demand"]["lagged"], True), ("d", style.ENV_LABELS["demand"]["revealed"], True))}
AXES_RATIOS = (1.55, 1.0, 1.0)        # (a), (b), (c): shares of the width left after the reserves
LABELS = {"a_x": "Week", "a_y": {"cost": "Cost margin", "w0": "$W_0$ margin"}, "b_x": "Trace cost / all-fallback",
          "c_x": "Worst case $W_0$", "fallback": "All-fallback"}
NAME_IN = 1.3                         # the tables' name column (in): a label on one or two lines at 8 pt
NAME_FIT_IN = 1.1                     # name_cells splits a label wider than this (its estimate drops math glyphs)
style.register_supplementary(NAME, "W2", 2.5)


def key_of(tag: str) -> str:
    try:
        return KEY_OF_TAG[tag]
    except KeyError:
        raise style.StyleError(f"{NAME}: no registry key for tag {tag!r}") from None


def label_of(tag: str) -> str:
    return style.POLICIES[key_of(tag)].label


# ---------------------------------------------------------------------------------------------------------------
# inputs and checks
def _val(table: Mapping, tag: str, mode: str, week: str):
    v = L.val(table, tag, mode, week, SEED)
    return None if v is None else float(v)


def _same(a, b) -> bool:
    return (a is None and b is None) or (a is not None and b is not None and float(a) == float(b))


def rows_order(an: Mapping) -> tuple[list[str], list[int]]:
    """The rows: Sublet-lag and its inner policy, the notice-aware set, the primary baselines (the analysis's sets in
    its order); with the indices where a group starts (separators)."""
    pol = list(need(an, "policies", what=E7C))
    notice, h1 = list(need(an, "notice_set", what=E7C)), list(need(an, "h1_set", what=E7C))
    rows = [SUBLET, INNER] + notice + h1
    if sorted(rows) != sorted(pol) or len(set(rows)) != len(rows):
        raise style.StyleError(f"{E7C}: policies {pol} are not Sublet-lag, A9-lag, the notice set and H1's set")
    if sorted(key_of(t) for t in rows) != sorted(KEYS):
        raise style.StyleError(f"{NAME}: the analysis's policies {rows} are not the registered set {list(KEYS)}")
    return rows, [2, 2 + len(notice)]


def tables_of(an: Mapping, lag: Mapping, main: Mapping) -> dict:
    """{tag: the summary table that holds its lagged runs} (part lag's, or main's for the rows the analysis marks
    lagged_from 'main'), with each revealed counterpart in main's table."""
    out = {}
    for t, r in need(an, "lag_minus_revealed", what=E7C).items():
        out[t] = need(main if r.get("lagged_from") == "main" else lag, "table", what=MAIN if r.get("lagged_from")
                      == "main" else E7C_LAG)
    return out


def modes_of(lag: Mapping) -> list[str]:
    t = need(lag, "table", what=E7C_LAG)
    ms = {m for by_m in t.values() for m in by_m}
    return sorted(ms, key=lambda m: (MODE_ORDER.index(m) if m in MODE_ORDER else len(MODE_ORDER), m))


def check(an: Mapping, lag: Mapping, main: Mapping, rows: Sequence[str], weeks: Sequence[str],
          modes: Sequence[str]) -> None:
    """The analysis against the summaries (StyleError: a stale input): each policy's per-week L-tr r0, W0 (the largest
    r0 over the five stress lenders) and RC (L-tr minus L-hon), and each revealed value against main's table."""
    tabs = tables_of(an, lag, main)
    lag_weeks = L.weeks_of(need(lag, "table", what=E7C_LAG))
    if [str(w) for w in need(an, "meta", "weeks", what=E7C)] != list(weeks) or lag_weeks != list(weeks):
        raise style.StyleError(f"{NAME}: the analysis's weeks {list(weeks)} are not part lag's {lag_weeks}")
    if not set(STRESS) <= set(modes) or TRACE not in modes or HON not in modes:
        raise style.StyleError(f"{E7C_LAG}: lenders {list(modes)} lack the confirmation's {list(MODE_ORDER)}")
    bad = []
    for t in rows:
        tab = tabs[t]
        rev_t = an["lag_minus_revealed"][t]["revealed"]
        for w in weeks:
            r0 = _val(tab, t, TRACE, w)
            ws = [_val(tab, t, m, w) for m in STRESS]
            w0 = None if any(v is None for v in ws) else max(ws)
            hon = _val(tab, t, HON, w)
            rc = None if r0 is None or hon is None else r0 - hon
            pp = an["per_policy"][t]
            for k, v in (("r0", r0), ("W0", w0), ("RC", rc)):
                if not _same(pp[k]["weeks"].get(w), v):
                    bad.append(f"{t} {k} week {w}")
            rv = an["lag_minus_revealed"][t]
            rr0 = _val(main["table"], rev_t, TRACE, w)
            rws = [_val(main["table"], rev_t, m, w) for m in STRESS]
            rw0 = None if any(v is None for v in rws) else max(rws)
            rh = _val(main["table"], rev_t, HON, w)
            rrc = None if rr0 is None or rh is None else rr0 - rh
            for k, v in (("r0", rr0), ("W0", rw0), ("RC", rrc)):
                if not _same(rv[k]["revealed"]["weeks"].get(w), v):
                    bad.append(f"{t} revealed {k} week {w}")
    if bad:
        raise style.StyleError(f"{NAME}: {E7C} differs from the summaries (stale input): {bad[:6]}")


def check_registered(an: Mapping, lag: Mapping) -> None:
    """Inputs from full runs must be the registered analysis on the confirmation weeks (design/ms7/registration.md §1,
    §3; review of W-G4 A, as figs/supp/ms7_x3_lib.check_registered): StyleError where neither the analysis nor part
    lag's summary is reduced and the analysis's sha256 is not the one the registration records, or its weeks are not
    the 16 confirmation weeks. Reduced inputs pass (their figures never reach the versioned folders)."""
    m = need(an, "meta", what=E7C)
    if m.get("reduced") or (lag.get("meta") or {}).get("reduced"):
        return
    reg = m.get("registration") or {}
    if reg.get("matches") is not True or m.get("weeks_are_confirmation_weeks") is not True:
        raise style.StyleError(f"{NAME}: {E7C} is not the registered analysis on the confirmation weeks (registration "
                               f"matches {reg.get('matches')}, sha256 {str(m.get('analysis_sha256'))[:12]} against "
                               f"{str(reg.get('registered_sha256'))[:12]}; confirmation weeks "
                               f"{m.get('weeks_are_confirmation_weeks')}; design/ms7/registration.md §1): rerun "
                               f"sublet/experiments/e7c_analysis.py on the copied outputs")


# ---------------------------------------------------------------------------------------------------------------
# the figure's data
def panel_a(an: Mapping, weeks: Sequence[str]) -> dict:
    a: dict[str, Any] = {"x": [int(w) for w in weeks], "weeks": list(weeks),
                         "subpanels": [["cost", ["h1_r0", "notice_r0"]], ["w0", ["h1_W0", "notice_W0"]]]}
    for s in SETS:
        for k in METRICS:
            g = need(an, "margins", s, k, what=E7C)
            a[f"{s}_{k}"] = [g["weeks"][w]["delta"] for w in weeks]
    a["shaded"] = {name: A.flagged_columns(a["x"], a, keys) for name, keys in a["subpanels"]}
    a["missing"] = {f"{s}_{k}": [w for w in weeks if an["margins"][s][k]["weeks"][w]["delta"] is None]
                    for s in SETS for k in METRICS}
    return a


def _stat(d: Mapping) -> dict:
    return {k: d.get(k) for k in ("n", "n_missing", "median", "min", "max")}


def panel_rows(an: Mapping, rows: Sequence[str], k: str) -> list[dict]:
    return [{"key": key_of(t), "tag": t, "lagged": _stat(an["per_policy"][t][k]),
             "revealed": _stat(an["lag_minus_revealed"][t][k]["revealed"])} for t in rows]


# ---------------------------------------------------------------------------------------------------------------
# tables
def modes_table(an, lag, main, rows, weeks, modes) -> dict:
    tabs = tables_of(an, lag, main)
    out = []
    for t in rows:
        out.append({"tag": t, "key": key_of(t), "label": label_of(t),
                    "stats": {m: A.describe([_val(tabs[t], t, m, w) for w in weeks]) for m in modes}})
    return {"modes": list(modes), "rows": out, "scope": {"tags": list(rows), "modes": list(modes),
                                                       "weeks": list(weeks)}}


def policies_table(an, rows, weeks) -> dict:
    out = []
    for t in rows:
        pp, lr = an["per_policy"][t], an["lag_minus_revealed"][t]
        out.append({"tag": t, "key": key_of(t), "label": label_of(t), "revealed_tag": lr["revealed"],
                    "revealed_label": L.label(lr["revealed"]),
                    **{k: _stat(pp[k]) for k in ("r0", "W0", "RC")},
                    **{f"d_{k}": _stat(lr[k]) for k in ("r0", "W0", "RC")},
                    "n_r0_below_1": pp["r0"]["n_below_1"], "n_W0_below_1": pp["W0"]["n_below_1"]})
    return {"rows": out, "scope": {"tags": list(rows), "weeks": list(weeks), "modes": [TRACE, HON, *STRESS]}}


def margins_table(an, weeks) -> dict:
    out = []
    for s in SETS:
        for k in METRICS:
            g = an["margins"][s][k]
            best = Counter(g["weeks"][w]["best"] for w in weeks if g["weeks"][w]["best"] is not None)
            order = sorted(best.items(), key=lambda kv: (-kv[1], g["set"].index(kv[0])))   # most weeks first
            out.append({"set": s, "metric": k, "members": list(g["set"]),
                        **{f: g[f] for f in ("n_weeks", "n_wins", "n_ties", "n_losses", "n_lost_missing", "median",
                                             "min", "max")},
                        "best": [[t, label_of(t), n] for t, n in order]})
    return {"rows": out, "scope": {"tags": [SUBLET] + list(an["h1_set"]) + list(an["notice_set"]),
                                   "weeks": list(weeks)}}


GUARD_COLS = ("runs", "runs_projected", "projected_slots", "K0", "aborts", "held", "envelope_violations")


def guard_table(an, modes) -> dict:
    g = need(an, "guard", what=E7C)
    rows = []
    for t, tot in g["by_tag"].items():
        for m in modes:
            c = (g["by_tag_mode"].get(t) or {}).get(m) or {}
            rows.append({"tag": t, "key": key_of(t), "label": label_of(t), "mode": m,
                         **{k: int(c.get(k) or 0) for k in GUARD_COLS}})
        rows.append({"tag": t, "key": key_of(t), "label": label_of(t), "mode": "all",
                     **{k: int(tot.get(k) or 0) for k in GUARD_COLS}})
    i, ga = need(an, "identity", what=E7C), need(an, "gate", what=E7C)
    ident = {k: i.get(k) for k in ("n_pairs", "n_exact", "max_abs_diff", "holds", "n_left_out", "n_missing")}
    gate = {k: ga.get(k) for k in ("found", "pass", "n_checks", "n_equal", "n_no_reference", "max_abs_diff",
                                   "same_commit")}
    return {"rows": rows, "identity": ident, "gate": gate,
            "scope": {"tags": list(g["by_tag"]), "modes": list(modes)}}


RUNS_COLUMNS = ("policy", "tag", "revealed_policy", "revealed_tag", "lender_mode", "week", "policy_seed", "r0_lagged",
                "r0_revealed", "projected_slots", "aborted", "certificate_held", "envelope_ok")


def _flag(v) -> str:
    return "" if v is None else ("1" if v else "0")


def runs_entry(an, lag, main, rows, weeks, modes) -> dict:
    tabs = tables_of(an, lag, main)
    guard = {(r["tag"], r["mode"], str(r["cell"]), int(r["seed"])): r for r in an["guard"]["runs"]}
    out = []
    for t in rows:
        rt = an["lag_minus_revealed"][t]["revealed"]
        for m in modes:
            for w in weeks:
                gr = guard.get((t, m, w, SEED))
                out.append([L.plain_label(label_of(t)), t, L.plain_label(L.label(rt)), rt, m, w, SEED,
                            A.csv_num(_val(tabs[t], t, m, w)), A.csv_num(_val(main["table"], rt, m, w)),
                            "" if gr is None else int(gr["projected_slots"]),
                            "" if gr is None else _flag(gr["aborted"]),
                            "" if gr is None else _flag(gr["held"]), "" if gr is None else _flag(gr["env_ok"])])
    return A.csv_entry(RUNS_CSV, RUNS_COLUMNS, out, {"tags": list(rows), "modes": list(modes), "weeks": list(weeks),
                                                     "seeds": [SEED]})


# ---------------------------------------------------------------------------------------------------------------
def caption_values(d: Mapping) -> dict:
    """The numbers of the caption draft, each read from the inputs (labels.caption_values; the integrator's \\val
    entries): the weeks, the weeks in which Sublet-lag is below every lagged primary baseline on cost and on W0, and
    the weeks with a missing run."""
    mg = {(r["set"], r["metric"]): r for r in d["tables"]["lag_v2_margins"]["rows"]}
    return {"n_weeks": len(d["a"]["weeks"]), "wins_cost_primary": mg[("h1", "r0")]["n_wins"],
            "wins_w0_primary": mg[("h1", "W0")]["n_wins"], "wins_cost_notice": mg[("notice", "r0")]["n_wins"],
            "wins_w0_notice": mg[("notice", "W0")]["n_wins"],
            "missing_weeks": sorted({w for v in d["a"]["missing"].values() for w in v}, key=int)}


def caption(d: Mapping, v: Mapping) -> str:
    """The caption draft: no design names; every count from caption_values."""
    n, miss = v["n_weeks"], v["missing_weeks"]
    lost = (f" A run is missing in week{'s' if len(miss) > 1 else ''} {', '.join(miss)}: a loss for Sublet."
            if miss else "")
    return (f"Demand one slot late on {n} confirmation week{'s' if n != 1 else ''} (policy seed 0): every policy plans "
            f"on the previous slot's demand; the guard of Sublet and of greedy renting with the guard still tests the "
            f"realized slot. (a) Per week, the least primary baseline (filled) or notice-aware policy (open) minus "
            f"Sublet, each lagged, on the trace cost and on W0 (positive: Sublet costs less; shaded: a negative or "
            f"missing margin); Sublet is below every primary baseline in {v['wins_cost_primary']} of {n} weeks on cost "
            f"and {v['wins_w0_primary']} on W0. (b) Trace cost and (c) W0 per policy: median over the weeks (marker) "
            f"and min-max (bar), with demand lagged (filled) and revealed (open); grey: all-fallback.{lost}")


def build(inp: Inputs) -> dict:
    an = A.read_json(inp, E7C, RUN_INPUTS, NAME)
    lag = A.read_json(inp, E7C_LAG, RUN_INPUTS, NAME)
    main = A.read_json(inp, MAIN, RUN_INPUTS, NAME)
    weeks = [str(w) for w in need(an, "meta", "weeks", what=E7C)]
    if not weeks:
        raise MissingKey(f"{E7C}: no week")
    rows, seps = rows_order(an)
    modes = modes_of(lag)
    check(an, lag, main, rows, weeks, modes)
    check_registered(an, lag)
    tables = {"lag_v2_modes": modes_table(an, lag, main, rows, weeks, modes),
              "lag_v2_policies": policies_table(an, rows, weeks),
              "lag_v2_margins": margins_table(an, weeks),
              "lag_v2_guard": guard_table(an, modes),
              "lag_v2_runs": runs_entry(an, lag, main, rows, weeks, modes)}
    am, lm, mm = an.get("meta") or {}, lag.get("meta") or {}, main.get("meta") or {}
    reduced = {"e7c": bool(am.get("reduced")), "lag": bool(lm.get("reduced")), "main": bool(mm.get("reduced"))}
    data = {"keys": list(KEYS), "rows": [key_of(t) for t in rows], "tags": list(rows), "separators": seps,
            "a": panel_a(an, weeks), "b": panel_rows(an, rows, "r0"), "c": panel_rows(an, rows, "W0"),
            "series": dict(SERIES), "legend": {k: [list(e) for e in v] for k, v in LEGEND.items()},
            "labels": {**LABELS, "rows": [r["revealed_label"] for r in tables["lag_v2_policies"]["rows"]]},
            "tables": tables,
            "checks": {"registration_matches": (am.get("registration") or {}).get("matches"),
                       "weeks_are_confirmation_weeks": am.get("weeks_are_confirmation_weeks"),
                       "identity_holds": tables["lag_v2_guard"]["identity"]["holds"],
                       "gate_pass": tables["lag_v2_guard"]["gate"]["pass"]},
            "meta": {"git_revision": {"e7c": am.get("git_revision"), "lag": lm.get("git_revision"),
                                      "main": mm.get("git_revision")},
                     "analysis_sha256": am.get("analysis_sha256"), "reduced": any(reduced.values()),
                     "reduced_by_input": reduced, "weeks": list(weeks), "modes": list(modes)}}
    data["labels"]["caption_values"] = caption_values(data)
    data["labels"]["caption"] = caption(data, data["labels"]["caption_values"])
    data["meta"]["sources"] = list(inp.sources)
    return data


# ---------------------------------------------------------------------------------------------------------------
def draw(data: Mapping) -> Any:
    fig = style.new_figure(NAME)
    lab, keys = data["labels"], data["legend"]
    names = lab["rows"]
    room = A.key_room_in([e[0] for es in keys.values() for e in es])
    ax_a, ax_b, ax_c = style.panel_row(fig, AXES_RATIOS, top=style.MARGIN_TOP + room, sharey=[False, False, True],
                                       left=[A.margins_reserve(fig, data["a"]), A.names_reserve(fig, names),
                                             style.LEFT_SHARED])
    subs = A.split_rows(fig, ax_a, 2)
    A.draw_margins(subs, data["a"], data["series"], lab["a_y"], lab["a_x"])
    for ax, rows, xl, nm in ((ax_b, data["b"], lab["b_x"], names), (ax_c, data["c"], lab["c_x"], None)):
        ax.set_xlim(*A.row_limits(rows, ("lagged", "revealed"), 1.0))
        A.draw_rows(ax, rows, ("lagged", "revealed"), data["series"], ref=1.0, xlabel=xl, names=nm,
                    separators=data["separators"])
    A.align_xlabels([subs[-1], ax_b, ax_c])
    letters = style.panel_letters([subs[0], ax_b, ax_c])
    A.letter_keys(fig, letters, {0: [tuple(e) for e in keys["a"]], 1: [tuple(e) for e in keys["b"]]}, room)
    A.line_label_inside(ax_b, 1.0, lab["fallback"])     # C62 fix round: inside (b), capping its line at 1
    fig._sublet_panels = {"a": subs, "b": ax_b, "c": ax_c}
    return fig


# ---------------------------------------------------------------------------------------------------------------
# LaTeX
def _name_rows(label: str) -> list[str]:
    return L.name_cells(L.tex(label), 2, NAME_FIT_IN)


def _pairs(n_rows: int) -> list[list[int]]:
    """The two lines of each policy, kept on one page."""
    return [[2 * i, 2 * i + 1] for i in range(n_rows)]


def _weeks_text(d: Mapping) -> str:
    ws = d["a"]["weeks"]
    return (f"{len(ws)} confirmation week{'s' if len(ws) != 1 else ''} (week{'s' if len(ws) != 1 else ''} "
            + L.week_span(ws) + ", policy seed 0)")


def modes_tex(t: Mapping, d: Mapping) -> str:
    body = []
    for r in t["rows"]:
        nm = _name_rows(r["label"])
        top, low = A.med_rows([r["stats"][m] for m in t["modes"]])
        body += [[nm[0]] + top, [nm[1]] + low]
    cap = (r"The cost over all-fallback, $r_0$, of every policy under each of the " + f"{len(t['modes'])}"
           + r" lenders with every policy on the previous slot's demand, over the " + _weeks_text(d)
           + r": the median over the weeks (first line) and the minimum and maximum (second line)."
           + _fewer_note(body) + r" The guard of Sublet and of greedy renting with the guard tests the realized "
           r"slot. Every run's $r_0$, lagged and revealed, is in the data file " + L.tex(RUNS_CSV) + ".")
    return A.longtable("@{}p{" + f"{NAME_IN}in" + "}" + "r" * len(t["modes"]) + "@{}", cap, "tab:s-lag-v2-modes",
                       ["Policy"] + list(t["modes"]), body,
                       rules=[2 * i for i in d["separators"]], together=_pairs(len(t["rows"])))


def policies_tex(t: Mapping, d: Mapping) -> str:
    body = []
    for r in t["rows"]:
        nm = _name_rows(r["label"])
        stats = [r["r0"], r["W0"], r["RC"], r["d_r0"], r["d_W0"], r["d_RC"]]
        fmts = (".3f",) * 6
        two = [A.med_rows([s], f) for s, f in zip(stats, fmts)]
        top = [x[0][0] for x in two] + [str(r["n_r0_below_1"]), str(r["n_W0_below_1"])]
        low = [x[1][0] for x in two] + ["", ""]
        body += [[nm[0]] + top, [nm[1]] + low]
    cap = (r"Every policy on the previous slot's demand, over the " + _weeks_text(d) + r": $r_0$ under the trace "
           r"lender L-tr, $W_0$ (the largest $r_0$ over the five stress lenders) and the revocation cost "
           r"RC $=r_0(\mbox{L-tr})-r_0(\mbox{L-hon})$, then each of them lagged minus revealed ($\Delta$, per week, "
           r"against the same policy with the slot revealed; for RetroRenting-style, lagged, against "
           r"RetroRenting-style). First line: the median over the weeks; second line: the minimum and maximum."
           + _fewer_note(body) + r" The last two columns count the weeks with $r_0<1$ and with $W_0<1$.")
    head = ["Policy", "$r_0$", "$W_0$", "RC", r"$\Delta r_0$", r"$\Delta W_0$", r"$\Delta$RC", "$r_0<1$", "$W_0<1$"]
    return A.longtable("@{}p{" + f"{NAME_IN}in" + "}rrrrrrrr@{}", cap, "tab:s-lag-v2-policies", head, body,
                       rules=[2 * i for i in d["separators"]], together=_pairs(len(t["rows"])))


def margins_tex(t: Mapping, d: Mapping) -> str:
    body, prev = [], None
    for r in t["rows"]:
        best = "; ".join(f"{L.tex(lab)} ({n})" for _, lab, n in r["best"]) or "--"
        body.append([L.rag(SET_LABEL[r["set"]]) if r["set"] != prev else "", f"${r['metric'][0]}_0$", str(r["n_weeks"]),
                     str(r["n_wins"]), str(r["n_ties"]), str(r["n_losses"]), str(r["n_lost_missing"]),
                     A.num(r["median"]), A.num(r["min"]), A.num(r["max"]), L.rag(best)])
        prev = r["set"]
    sets = {r["set"]: r["members"] for r in t["rows"]}
    cap = (r"The margin of Sublet, lagged, per week over the " + _weeks_text(d) + r": the least $r_0$ under L-tr "
           r"(or the least $W_0$) over a set of policies minus Sublet's, every policy on the previous slot's demand "
           r"(positive: Sublet costs less). The primary baselines: " + L.join_labels([label_of(x) for x in sets["h1"]])
           + r". The notice-aware policies: " + L.join_labels([label_of(x) for x in sets["notice"]])
           + r". The weeks with a positive margin (wins), a zero margin (ties) and a negative margin (losses), and "
           r"the weeks that a missing run decides (lost, a loss); the median, minimum and maximum of the margin over "
           r"the other weeks; and the number of weeks in which each policy is the least of its set.")
    starts = [i for i, r in enumerate(t["rows"]) if i == 0 or r["set"] != t["rows"][i - 1]["set"]]
    return A.longtable("@{}p{0.95in}lrrrrrrrrp{2.05in}@{}", cap, "tab:s-lag-v2-margins",
                       ["Set", "", "Weeks", "Wins", "Ties", "Losses", "Lost", "Median", "Min", "Max",
                        "Least of the set (weeks)"], body, rules=starts,
                       together=[[a, b - 1] for a, b in zip(starts, starts[1:] + [len(body)])])


GUARD_HEAD = {"runs": "Runs", "runs_projected": "Projected", "projected_slots": r"Proj.\ slots", "K0": "K0",
              "aborts": "Aborts", "held": "Held", "envelope_violations": "Env."}


def _fewer_note(body: Sequence[Sequence[str]]) -> str:
    """The caption's note on A.FEWER_MARK when a cell of `body` carries it (review of W-G4 A: a median over fewer weeks
    was not marked)."""
    return (" " + A.FEWER_MARK + r": over fewer weeks (a missing run)."
            if any(A.FEWER_MARK in c for row in body for c in row) else "")


def _in_sentence(label: str) -> str:
    """A registry label inside a sentence (A.prose, in TeX), followed by a comma where the label holds one, so that the
    sentence does not run on into the label's last part (review of W-G4 A: "runs of Sublet, lagged with no projected
    slot")."""
    return L.tex(A.prose(label)) + ("," if "," in label else "")


def _identity_text(i: Mapping) -> str:
    sub, inner = _in_sentence(label_of(SUBLET)), _in_sentence(label_of(INNER))
    if not i.get("n_pairs"):
        return (r" Each of the " + f"{i.get('n_left_out') or 0}" + r" runs of " + sub + r" projected a slot or "
                r"aborted, so none can be compared with " + inner + r" on a run without projection.")
    diff = i.get("max_abs_diff")
    out = (r" On the " + f"{i['n_pairs']}" + r" runs of " + sub + r" with no projected slot and no abort, its $r_0$ "
           r"equals that of " + inner + r" exactly in " + f"{i['n_exact']}"
           + ("" if not diff else r" (largest difference below " + L.bound_text(float(diff)) + ")")
           + r"; the " + f"{i.get('n_left_out') or 0}" + r" runs that projected or aborted are left out")
    if i.get("n_missing"):
        out += r", and " + f"{i['n_missing']}" + r" have no run to compare"
    return out + "."


def _gate_text(g: Mapping) -> str:
    if not g.get("found"):
        return r" No rerun of the confirmation's runs precedes the lagged runs."
    out = (r" Before the lagged runs, " + f"{g.get('n_equal') or 0}" + r" of " + f"{g.get('n_checks') or 0}"
           + r" reruns of the confirmation's runs reproduced their $r_0$ exactly")
    if g.get("n_no_reference"):
        out += r" (" + f"{g['n_no_reference']}" + r" without a confirmation run to compare)"
    return out + (r", at the commit of the lagged runs." if g.get("same_commit") else r".")


def guard_tex(t: Mapping, d: Mapping) -> str:
    body, starts, prev = [], [], None
    n_modes = len(d["meta"]["modes"])
    for r in t["rows"]:
        if r["tag"] != prev:
            starts.append(len(body))
            nm = L.name_cells(L.tex(r["label"]), n_modes + 1, NAME_FIT_IN)
        name = nm.pop(0)
        prev = r["tag"]
        body.append([name, r["mode"]]
                    + [f"{r[k]:,}" for k in GUARD_COLS])
    cap = (r"The guard of Sublet, lagged, and of greedy renting with the guard, inner policy lagged (the guard's test "
           r"reads the realized slot), per lender and over all lenders, over the " + _weeks_text(d) + r": runs, runs "
           r"with a projected slot (Projected), projected slots, K0 uses, aborts, certificates held and envelope "
           r"violations (Env.)." + _identity_text(t["identity"]) + _gate_text(t["gate"]))
    return A.longtable("@{}p{" + f"{NAME_IN}in" + "}l" + "r" * len(GUARD_COLS) + "@{}", cap, "tab:s-lag-v2-guard",
                       ["Policy", "Lender"] + [GUARD_HEAD[k] for k in GUARD_COLS], body, rules=starts,
                       together=[[a, b - 1] for a, b in zip(starts, starts[1:] + [len(body)])])


def write_tables(data: Mapping, report: Mapping) -> None:
    """The four tables and the data file from the extract's `tables` (figs.common.write_table; the data file's
    sha256 checked against the extract's)."""
    t = data["tables"]
    head = L.table_head
    paths = [write_table(TABLES[0], head(NAME, [E7C_LAG, MAIN]) + modes_tex(t["lag_v2_modes"], data)),
             write_table(TABLES[1], head(NAME, [E7C]) + policies_tex(t["lag_v2_policies"], data)),
             write_table(TABLES[2], head(NAME, [E7C]) + margins_tex(t["lag_v2_margins"], data)),
             write_table(TABLES[3], head(NAME, [E7C]) + guard_tex(t["lag_v2_guard"], data)),
             write_table(RUNS_CSV, A.csv_from_entry(t["lag_v2_runs"]))]
    print(f"[{NAME}] wrote {', '.join(str(p) for p in paths)}")


def main(argv: Sequence[str] | None = None) -> dict:
    return A.main(NAME, build, draw, argv, after=write_tables, doc=__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
