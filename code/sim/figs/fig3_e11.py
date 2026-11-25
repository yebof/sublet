"""Fig. 3: the guard keeps the renting rule's trace cost and caps its worst case (E11; design/figure_plan.md §1,
Fig. 3; design/sim_spec_ms3.md §8.3): Algorithm 1 without projection (the one-way guard, A8) around three inner
policies, at Algorithm 1's defaults.

MS6 C46 (design/ms6_spec.md M2-M6): the guarded series are their configurations' keys, E11's tag BL5-G the lagged
RetroRenting-style rule with the one-way guard (bl5_g1, "Lagged RetroRenting + one-way guard"), BL5 bl5_lag, BL1-G
bl1_g1 and PS-G a7_g1; the data tags are E11's. The legend pairs each inner policy's open marker with its guarded
configuration's filled marker under the inner policy's name, and one entry says "paired, filled: + one-way guard
(Algorithm 1 without projection)" (style.guard_pair_handles, M5; C47: "paired", since the unpaired Two-timescale PD and
per-borrower ski rental, which follow, have filled markers too, and the note stands below the latter).
The drawn labels name no design ID (M6): (c)'s G3(b) line is "core ratio bound"; the caption (LaTeX, in the
manuscript) gives the paper's result numbers and names whose bound it is (labels.g3b_of).

Claims and status labels (plan §1): G2 and G3(b) PROVEN, audited; Theorem W(a)(b) PROVEN for the engine as
implemented under C1-C3, audited, and checked per run by the certificate; Theorem W(c) CONJECTURE; C3-P5 PROVEN for
the revocable-only limit in (c). Trace and stress costs are measurements on the one-day instances I1-I4 at
alpha = 0.40, 1-min routing, medians over held-out cells.

(a) Consistency against robustness, from code/sim/out/e11/summary.json D4.criteria: x the median cost over the
cheapest of BL1, BL2 and BL5 under the trace lender (D1), y the largest median cost over all-fallback across the
stress lenders (W0); a marker at the policy's worst instance on each axis, whiskers to its best; thin arrows with
open heads from each inner policy to its guarded version, from marker edge to marker edge, where the two markers leave
room for one (none from BL5 to BL5-G, drawn just below it: the legend pairs them);
reference lines at 1; the study's pre-set criteria region (x <= 1 + x_T, y <= 1 + y_S from D4.thresholds) shaded
(decision 7). BL1-G nearly covers PS-G and is drawn over it, smaller and with a white edge. C47 (print check of the
gate, U46): BL5-G's marker is drawn above every other series with a white casing (A_CASED, CASING_PT), so that the
x-whiskers of BL1-G and PS-G, which run at its height, pass behind it instead of seeming to start at its tip.
(b) Cost over all-fallback against the realized announcements per site-day on I4 (intensity, tuning cells included,
M37), one point per lender mode, median with its 95% bootstrap interval (D2.I4). C47 (print check of the gate): where
the lagged RetroRenting-style rule and its guarded configuration agree within B_AGREE_PCT percent at every point
(medians; within 1% on E11), the pair is drawn once, as the guarded configuration, and a key shows the pair's two
samples side by side with "agree within p%" (b.agree; the keys of sf_e11_fam): drawn twice, their open < and filled >
printed as bow ties. C62: the key stands on (b)'s letter line, right of the letter, as the paper's Fig. 4 sets its
keys (letter_key; in (b)'s upper left corner before, where the y axis rose by the key's height above the data).
(c) The insurance family F3 under the eager lender at T = 192 (D5.families.F3): ALG/OPT against rho_1, the
revocable-only limit a1 rho1 / a2 for T -> infinity (C3-P5) and the G3(b) bound of each instance,
((1 + gamma) c(gamma') + kappa) min{q|sigma| / OPT_eager, alpha_N} with c(g) = g + g^2/(g - 1) and
alpha_N = 4 ceil(2 ln N) ln(mK + 2) + 1, from the run files code/sim/out/e11/runs/Q6/<instance>/core/F-eg/
BL5-G_c0_l0_p0.json (q|sigma| = metrics.policy.safe.C_FB, OPT_eager = q44.opt, N = meta.driver_inputs.N_bound,
gamma, gamma', kappa = meta.params) and m, K parsed from cell_family.json's core_instance (M36), labeled "core ratio
bound" (BL5-G's run files). BL1 and A7 (PS) coincide on F3 and are drawn once in BL1's style.
The legend holds the three pairs, Two-timescale PD, per-borrower ski rental and the note in two rows, read by column
(C62: at 7 pt one row with M5's note still needs 8.6 in against the page's 7.08 in; 7.3 in with the note cut to
"paired, filled: + one-way guard"); the guarded variants of A7 and BL1 are also labeled directly in (a), on two
lines, each joined to its marker by a leader (BL1-G shares BL2's filled down triangle in greyscale), and (c) names
BL1 = A7 in a key; the limit's label is joined to its line's end by a leader.
C62 (the type scale of the caption; figures high-end, informative, readable): the keys of (b) and (c) stand on their
panels' letter line, right of the letter, their labels on its baseline (letter_key; in (b)'s upper left corner and
inside (c), on two lines below the core ratio bound's label, before), and the axes' tops lie letter_line_drop_in
below that line, so that the keys' descenders end LETTER_KEY_CLEAR_PT above the axes; (a)'s y label is centered (at
9 pt it was set 2.5 pt low, clear of the panel letter); the log axes ((b)'s x, (c)'s y) have no minor ticks (labeled
ticks at 3, 10, 30, ... and at the decades; (c)'s decades are 27 pt high); and the x labels of the row share one
baseline as the PDF prints them ((c)'s mathtext rho_1 sat 1 pt high; common.align_baselines). The extract is
unchanged.

The run files are not versioned, so the extract code/sim/out/figs/fig3.json carries every plotted value and label and
is the figure's source; ``--from-extract`` redraws the figure from it alone. Run from code/sim:
``python -m figs.fig3_e11 [--from-extract [JSON]]`` (figs.common.cli).
"""
from __future__ import annotations

import math
import re
import sys

import numpy as np
from matplotlib.lines import Line2D
from matplotlib.markers import TICKUP, MarkerStyle
from matplotlib.ticker import MaxNLocator, NullLocator

from figs import style
from figs.common import LEADER_PT, agreement, align_baselines, cli
from figs.inputs import Inputs

NAME = "fig3"
SUMMARY = "code/sim/out/e11/summary.json"
RUN_DIR = "code/sim/out/e11/runs/Q6"
INSTANCES = ("I1", "I2", "I3", "I4")
# tag-to-key map (sim_spec_ms3 §8.3; C46, design/ms6_spec.md M2-M4: the configuration keys of Algorithm 1's defaults)
TAG_KEY = {"BL5-G": "bl5_g1", "BL5": "bl5_lag", "BL1": "bl1", "BL2": "bl2", "PS": "a7", "PS-G": "a7_g1",
           "BL1-G": "bl1_g1", "A6": "a6"}
A_TAGS = ("A6", "BL1", "BL2", "PS", "BL5", "BL1-G", "PS-G", "BL5-G")       # drawn in this order, BL5-G last
ARROWS = (("BL5", "BL5-G"), ("PS", "PS-G"), ("BL1", "BL1-G"))
B_TAGS = ("A6", "BL1", "BL2", "PS", "BL5", "BL5-G")
B_INSTANCE = "I4"
# C47 (print check of the gate): in (b) the lagged RetroRenting-style rule and its guarded configuration agree within
# B_AGREE_PCT percent at every point (medians; on E11 within 1%), and their open < and filled > overprinted into bow
# ties that matched neither legend sample; such a pair is drawn once, as the guarded configuration, and named in a key
# in (b)'s upper left corner: the pair's two samples side by side (as in the legend) and "agree within p%" (as the
# keys of sf_e11_fam), above every drawn value
B_PAIR = ("bl5_lag", "bl5_g1")
B_AGREE_PCT = 5                      # common.AGREE_MAX_PCT: the largest agreement drawn as one series with a key
B_KEY_SAME, B_KEY_NEAR = "equal", "agree within {pct}%"
B_KEY_HANDLE = 1.6                   # (b): the key's handle length (font sizes), the pair's two markers side by side
MODES = ("L-tr", "L-eg", "L-ss", "L-iid-0.0124", "L-iid-0.05", "L-iid-0.2", "L-co")
C_FAMILY, C_T, C_MODE = "F3", 192, "F-eg"
C_TAGS = ("BL5", "BL1", "PS-G", "BL5-G")          # BL1 stands for BL1 = PS (asserted equal)
# C46 (M5): the legend, (inner, guarded) pairs of one entry each, then the unpaired policies; with the note, in two
# rows read by column (the pairs first)
PAIRS = (("bl5_lag", "bl5_g1"), ("a7", "a7_g1"), ("bl1", "bl1_g1"))
UNPAIRED = ("a6", "bl2")
A_LABELED = ("a7_g1", "bl1_g1")      # (a): the guarded variants labeled directly (they nearly coincide)
A_TWO_LINES = ("a7_g1", "bl1_g1")    # direct labels of (a) set on two lines, so that they end left of A6's whisker
A_ON_TOP = "bl1_g1"                  # (a): drawn over A7 + guard, which it nearly covers, smaller and with a white edge
ON_TOP_SCALE = 0.8                   # its marker size relative to the registry's
# C47 (print check of the gate, U46): (a) draws the lagged RetroRenting-style rule's guarded marker above every other
# series with a white casing, so that the x-whiskers of Greedy + one-way guard and PD heuristic + one-way guard, which
# run at its height (y 1.024 against its 1.018) from x 1.00 and 1.06 to 1.41-1.42, pass behind it with a gap instead
# of seeming to start at its tip (read as its own whisker to 1.42); its own whiskers are drawn above the casing
A_CASED = "bl5_g1"
CASING_PT = 0.8                      # (a): the white casing's width outside the marker's edge
A_LABEL_BELOW = ("bl1_g1",)          # (a): labeled below right of the guarded pair, the other above right, so that no
                                     # leader runs along the arrows, which arrive from above
LABEL_OFFSET_PT = (6.0, 3.0)         # (a): offset of a direct label's corner nearest its marker, right and up or down
                                     # (C46: 6 pt right, so that "+ one-way guard" ends clear of A6's whisker)
LINE_STEP_PT = 1.25 * style.TICK_PT  # (a): height of a line of direct-label text, kept free under the guarded pair
ARROW_PT = 0.5                       # (a): line width of the arrows from inner to guarded policies
ARROW_HEAD_PT = (2.2, 1.1)           # their open heads: length and half-width
ARROW_GAP_PT = 0.6                   # gap between an arrow's or a leader's ends and the marker edges
ARROW_MIN_PT = 2.0 * ARROW_HEAD_PT[0]   # shortest arrow drawn: two markers closer than this edge to edge get none
LIMIT_LIFT_PT = 5.5                  # (c): the limit's label sits this far above its line's end, joined by a leader
TRACE_GAP_PT = 1.5                   # (b): gaps of the trace lender's name to its tick below and to the data above
C_KEY_HANDLE = 1.6                   # (c): the key's handle length (font sizes)
LETTER_KEY_GAP_PT = 3.0              # C62: a panel's key starts this far right of its letter (fig4_v3.KEY_X_GAP_PT)
LETTER_KEY_CLEAR_PT = 3.0            # C62: a key's ink ends this far above the axes it keys (fig4_v3.KEY_AXES_GAP_PT)
LETTER_RISE_PT = 1.2                 # style.panel_letters: the letters' baseline this far above the axes' top
KEYS = tuple(TAG_KEY[t] for t in TAG_KEY)
STATUS = {
    "G2_G3b": "PROVEN, audited",
    "W_ab": "PROVEN for the engine as implemented under C1-C3, audited; checked per run by the certificate",
    "W_c": "CONJECTURE; it occurred in no full-model run",
    "C3-P5": "PROVEN (the revocable-only limit in (c))",
    "BL5": "no ratio in our model",
    "scope": "one-day instances I1-I4, alpha = 0.40, 1-min routing, medians over held-out cells",
}


def c_gamma(g: float) -> float:
    """c(gamma') = gamma' + gamma'^2 / (gamma' - 1) (design Table 2.10)."""
    return g + g * g / (g - 1.0)


def alpha_N(N: float, m: int, K: int) -> float:
    """alpha_N = 4 ceil(2 ln N) ln(mK + 2) + 1 (design Table 2.10)."""
    return 4.0 * math.ceil(2.0 * math.log(N)) * math.log(m * K + 2) + 1.0


def g3b(q_sigma: float, opt_eager: float, N: float, m: int, K: int, gamma: float, gamma_T11: float,
        kappa: float) -> float:
    """Corollary G3(b) as a ratio to OPT_eager: ((1 + gamma) c(gamma') + kappa) min{q|sigma| / OPT_eager, alpha_N}."""
    return ((1.0 + gamma) * c_gamma(gamma_T11) + kappa) * min(q_sigma / opt_eager, alpha_N(N, m, K))


_SINGLE = re.compile(r"^check_c4_lower\.single\(\s*\d+\s*,\s*\[(.*?)\]\s*,")


def parse_mK(core_instance: str) -> tuple[int, int]:
    """(m, K) of a family instance built by check_c4_lower.single: one site, K = the number of contracts."""
    mt = _SINGLE.match(core_instance.strip())
    if mt is None:
        raise style.StyleError(f"cannot read m and K from core_instance {core_instance!r}")
    K = len(re.findall(r"\(", mt.group(1)))
    if K < 1:
        raise style.StyleError(f"no contract in core_instance {core_instance!r}")
    return 1, K


def _pt(ax, x: float, y: float) -> np.ndarray:
    """Display position of the data point (x, y) in pt."""
    return np.asarray(ax.transData.transform((x, y)), dtype=float) * style.BP_PER_IN / ax.figure.dpi


def marker_radius_pt(key: str, size: float) -> float:
    """Radius of the circle around the marker of `key` at `size` pt, its 0.6-pt edge included."""
    m = MarkerStyle(style.policy(key).marker)
    return float(np.hypot(*m.get_path().transformed(m.get_transform()).vertices.T).max()) * size \
        + 0.5 * style.MARKER_EDGE_PT


def marker_reach_pt(markers, u) -> float:
    """How far a ray from the origin along the unit vector u (pt, x right, y up) runs before it leaves the last of
    `markers`, (key, center, size) triples with centers in pt relative to the origin, out to the outer side of their
    0.6-pt edges; 0 if it meets none. Arrows and leaders end there, so that no line or head covers a marker."""
    reach = 0.0
    for key, center, size in markers:
        m = MarkerStyle(style.policy(key).marker)
        for poly in m.get_path().transformed(m.get_transform()).to_polygons():
            P = np.asarray(poly, dtype=float) * size + np.asarray(center, dtype=float)
            for a, b in zip(P, np.roll(P, -1, axis=0)):
                d = b - a
                den = u[0] * d[1] - u[1] * d[0]
                if abs(den) < 1e-12:
                    continue
                t = (a[0] * d[1] - a[1] * d[0]) / den       # u t = a + s d
                s = (a[0] * u[1] - a[1] * u[0]) / den
                if t > 0.0 and -1e-9 <= s <= 1.0 + 1e-9:
                    reach = max(reach, t + 0.5 * style.MARKER_EDGE_PT)
    return reach


def legend_entries() -> list:
    """(handle, label) of the legend (C46, design/ms6_spec.md M5): the pairs of PAIRS (style.guard_pair_handles, the
    inner policy's open marker beside its guarded configuration's filled one, labeled with the inner policy's name),
    the policies of UNPAIRED, then the note GUARD_PAIR_NOTE; markers only, as the pairs are drawn. In two rows read by
    column: the pairs first."""
    return (style.guard_pair_handles(PAIRS, note=False) + style.policy_handles(UNPAIRED, lines=False)
            + style.guard_pair_handles(PAIRS[:1])[-1:])


# ---------------------------------------------------------------------------------------------------------------
def collect_a(S: dict) -> dict:
    crit, thr = S["D4"]["criteria"], S["D4"]["thresholds"]
    out = {}
    for tag in TAG_KEY:
        c = crit[tag]
        d1 = [c["D1"][i] for i in INSTANCES]
        w0 = [c["W0"][i] for i in INSTANCES]
        if any(v is None for v in d1 + w0):
            raise style.StyleError(f"D4.criteria.{tag} lacks an instance")
        out[TAG_KEY[tag]] = {"tag": tag, "D1": dict(zip(INSTANCES, d1)), "W0": dict(zip(INSTANCES, w0)),
                             "x": max(d1), "x_min": min(d1), "x_argmax": INSTANCES[int(np.argmax(d1))],
                             "y": max(w0), "y_min": min(w0), "y_argmax": INSTANCES[int(np.argmax(w0))]}
    return {"series": out, "arrows": [[TAG_KEY[a], TAG_KEY[b]] for a, b in ARROWS],
            "criteria": {"x_T": thr["x_T"], "y_S": thr["y_S"], "x_max": 1.0 + thr["x_T"], "y_max": 1.0 + thr["y_S"],
                         "T": thr.get("T"), "S": thr.get("S")}}


def collect_b(S: dict) -> dict:
    D2 = S["D2"][B_INSTANCE]["modes"]
    xs = {m: S["intensity"][f"{B_INSTANCE}|{m}"]["announcements_per_site_day"] for m in MODES}
    order = sorted(MODES, key=lambda m: xs[m])
    series = {}
    for tag in B_TAGS:
        r = [D2[m]["r0"][tag] for m in order]
        series[TAG_KEY[tag]] = {"tag": tag, "modes": order, "x": [xs[m] for m in order],
                                "median": [v["median"] for v in r], "ci_lo": [v["median_ci95"][0] for v in r],
                                "ci_hi": [v["median_ci95"][1] for v in r], "n": [v["n"] for v in r]}
    ag = agreement(series[B_PAIR[0]]["median"], series[B_PAIR[1]]["median"])
    agree = None
    if ag is not None and ag["within_pct"] <= B_AGREE_PCT:
        agree = {"pair": list(B_PAIR), "drawn": B_PAIR[1], **ag,
                 "key": B_KEY_SAME if ag["within_pct"] == 0 else B_KEY_NEAR.format(pct=ag["within_pct"])}
    return {"instance": B_INSTANCE, "modes": order, "intensity": [xs[m] for m in order], "series": series,
            "agree": agree}


def collect_c(S: dict, inp: Inputs) -> dict:
    fam = S["D5"]["families"][C_FAMILY]
    keys = [k for k in fam if k.endswith(f"_T{C_T}:{C_MODE}")]
    keys.sort(key=lambda k: fam[k]["rho1"])
    rho1 = [fam[k]["rho1"] for k in keys]
    series = {}
    for tag in C_TAGS:
        key = TAG_KEY[tag]
        series[key] = {"tag": tag, "x": rho1, "mean": [fam[k]["ratio"][tag]["mean"] for k in keys],
                       "min": [fam[k]["ratio"][tag]["min"] for k in keys],
                       "max": [fam[k]["ratio"][tag]["max"] for k in keys],
                       "runs": [fam[k]["ratio"][tag]["runs"] for k in keys]}
    ps = [fam[k]["ratio"]["PS"]["mean"] for k in keys]
    bl1 = series["bl1"]["mean"]
    coincide = all(abs(a - b) <= 1e-12 * max(1.0, abs(b)) for a, b in zip(ps, bl1))
    if not coincide:
        raise style.StyleError(f"BL1 and PS do not coincide on {C_FAMILY} at T = {C_T} ({bl1} vs {ps}); "
                               "draw them separately")
    series["bl1"]["coincides_with"] = "PS"
    limit = [fam[k]["bounds"]["revocable_only_asymptote_a1rho1_over_a2"] for k in keys]
    g3 = []
    for k in keys:
        inst = k.split(":", 1)[0]
        mode = k.split(":", 1)[1]
        rf = f"{RUN_DIR}/{inst}/core/{mode}/BL5-G_c0_l0_p0.json"
        cf = f"{RUN_DIR}/{inst}/core/{mode}/cell_family.json"
        run, cell = inp.json(rf), inp.json(cf)
        p = run["meta"]["params"]
        m, K = parse_mK(cell["core_instance"])
        row = {"instance": inst, "run_file": rf, "cell_file": cf, "core_instance": cell["core_instance"],
               "q_sigma": float(run["metrics"]["policy"]["safe"]["C_FB"]), "OPT_eager": float(run["q44"]["opt"]),
               "N": float(run["meta"]["driver_inputs"]["N_bound"]), "m": m, "K": K, "gamma": float(p["gamma"]),
               "gamma_T11": float(p["gamma_T11"]), "kappa": float(p["kappa"])}
        row["alpha_N"] = alpha_N(row["N"], m, K)
        row["c_gamma_T11"] = c_gamma(row["gamma_T11"])
        row["G3b"] = g3b(row["q_sigma"], row["OPT_eager"], row["N"], m, K, row["gamma"], row["gamma_T11"],
                         row["kappa"])
        g3.append(row)
    return {"family": C_FAMILY, "T": C_T, "mode": C_MODE, "instances": keys, "rho1": rho1, "series": series,
            "revocable_only_limit": limit, "G3b": [r["G3b"] for r in g3], "G3b_inputs": g3}


def collect(inp: Inputs) -> dict:
    S = inp.json(SUMMARY)
    return {"git_revision": S["meta"]["git_revision"], "a": collect_a(S), "b": collect_b(S),
            "c": collect_c(S, inp), "status": STATUS, "labels": {
                "a_x": "Trace cost / best renting",
                "a_y": "Stress cost / all-fallback",
                "a_x_long": "Cost / best renting baseline, trace lender (worst instance; whiskers to the best)",
                "a_y_long": "Worst stress cost / all-fallback (worst instance; whiskers to the best)",
                "b_x": "Announcements per site-day",
                "b_y": "Cost / all-fallback",
                "c_x": r"$\rho_1$",
                "c_y": "ALG / OPT",
                **{k: style.POLICIES[k].label for k in A_LABELED},
                "bl1_eq_a7": style.POLICIES["bl1"].label + " = " + style.POLICIES["a7"].label,
                # C47: T in math, as Fig. 6; U46: \longrightarrow, STIX's full-height arrow (Liberation Sans' U+2192,
                # which \to sets, prints at about 40% of the cap height, low between T and the infinity sign)
                "limit": r"revocable-only limit, $T\longrightarrow\infty$",
                "g3b": "core ratio bound",                                    # C46 (M6): no design ID drawn
                "g3b_of": style.POLICIES["bl5_g1"].label,                      # whose bound (the caption's)
                "framing": "Algorithm 1 without projection around three inner policies, at its defaults",
                "trace_mode": "trace",
                "legend": [lab for _, lab in legend_entries()],
                "legend_pairs": [list(p) for p in PAIRS],
            }}


# ---------------------------------------------------------------------------------------------------------------
def draw_a(ax, a: dict, lab: dict) -> None:
    ser = a["series"]
    xs = [v for s in ser.values() for v in (s["x"], s["x_min"])]
    ys = [v for s in ser.values() for v in (s["y"], s["y_min"])]
    x0, x1 = min(xs) - 0.06, max(xs) + 0.06
    y0, y1 = min(ys) - 0.04, max(ys) + 0.05
    # room under the guarded pair for the label set below it (on as many lines as it has)
    n_below = max(len((lab[k].replace(" + ", "\n+ ") if k in A_TWO_LINES else lab[k]).split("\n"))
                  for k in A_LABEL_BELOW)
    f = (LABEL_OFFSET_PT[1] + n_below * LINE_STEP_PT) / style.BP_PER_IN / style.axes_rect_in(ax)[3]
    y_low = min(ser[k]["y"] for k in A_LABEL_BELOW)
    y0 = min(y0, (y_low - f * y1) / (1.0 - f))
    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)
    cr = a["criteria"]
    style.shade_region(ax, (x0, cr["x_max"]), (y0, cr["y_max"]))
    style.reference_line(ax, x=1.0)
    style.reference_line(ax, y=1.0)
    size = {k: style.policy(k).markersize * (ON_TOP_SCALE if k == A_ON_TOP else 1.0) for k in ser}
    z_cased = max(style.policy(k).zorder for k in ser) + 0.2          # C47: above every other series of (a)
    for tag in A_TAGS:
        key = TAG_KEY[tag]
        s = ser[key]
        over = dict(zorder=z_cased + 0.05) if key == A_CASED else {}
        style.errorbars(ax, key, [s["x"]], [s["y"]], [s["x_min"]], [s["x"]], orientation="x", **over)
        style.errorbars(ax, key, [s["x"]], [s["y"]], [s["y_min"]], [s["y"]], orientation="y", **over)
        top = dict(markersize=size[key], markeredgecolor="white", zorder=style.policy(key).zorder + 0.1) \
            if key == A_ON_TOP else {}
        if key == A_CASED:                                             # C47: a white casing under its marker
            kw = style.policy_kwargs(key, lines=False, label=False)
            kw.update(markerfacecolor="white", markeredgecolor="white", zorder=z_cased,
                      markeredgewidth=kw["markeredgewidth"] + 2.0 * CASING_PT)
            casing, = ax.plot([s["x"]], [s["y"]], **kw)
            casing._sublet_role = "casing"
            top = dict(zorder=z_cased + 0.1)
        style.scatter_policy(ax, key, [s["x"]], [s["y"]], **top)
    pos = {k: _pt(ax, s["x"], s["y"]) for k, s in ser.items()}

    def touching(key):
        """The markers that overlap the marker of `key` (its own included), centered relative to it."""
        return [(k, pos[k] - pos[key], size[k]) for k in ser
                if np.hypot(*(pos[k] - pos[key])) < marker_radius_pt(key, size[key]) + marker_radius_pt(k, size[k])]

    # thin arrows with small open heads from each inner policy to its guarded version, from edge to edge of the
    # marker groups at their ends; none where the markers are too close for one (BL5 just above BL5-G: the legend
    # pairs them)
    for src, dst in a["arrows"]:
        d = pos[dst] - pos[src]
        u = d / np.hypot(*d)
        sa = marker_reach_pt(touching(src), u) + ARROW_GAP_PT
        sb = marker_reach_pt(touching(dst), -u) + ARROW_GAP_PT
        if np.hypot(*d) - sa - sb < ARROW_MIN_PT:
            continue
        style.arrow(ax, (ser[src]["x"], ser[src]["y"]), (ser[dst]["x"], ser[dst]["y"]), linewidth=ARROW_PT,
                    arrowstyle="->,head_length={},head_width={}".format(*ARROW_HEAD_PT), mutation_scale=1.0,
                    shrinkA=sa, shrinkB=sb)
    # the guarded variants are also labeled directly, right of their markers, one above and one below (they nearly
    # coincide; the reference line at 1 runs just below them), each joined to its own marker by a leader
    for key in A_LABELED:
        s = ser[key]
        text = lab[key].replace(" + ", "\n+ ") if key in A_TWO_LINES else lab[key]
        dx, dy = LABEL_OFFSET_PT[0], -LABEL_OFFSET_PT[1] if key in A_LABEL_BELOW else LABEL_OFFSET_PT[1]
        style.direct_label(ax, key, s["x"], s["y"], text, dx=dx, dy=dy, ha="left", va="top" if dy < 0 else "bottom")
        u = np.array([dx, dy]) / np.hypot(dx, dy)
        ax.annotate("", xy=(s["x"], s["y"]), xytext=(dx - 1.0, dy), textcoords="offset points",
                    arrowprops=dict(arrowstyle="-", color=style.policy(key).label_color, linewidth=LEADER_PT,
                                    shrinkA=0.0, shrinkB=marker_reach_pt([(key, (0.0, 0.0), size[key])], u)
                                    + ARROW_GAP_PT), zorder=style.Z_SUBLET + 0.2)
    ax.yaxis.set_major_locator(MaxNLocator(steps=[1, 2, 5, 10]))     # no steps of 0.25: their labels are wider
    ax.xaxis.set_major_formatter(style.PLAIN)
    ax.yaxis.set_major_formatter(style.PLAIN)
    ax.set_xlabel(lab["a_x"])
    ax.set_ylabel(lab["a_y"])           # C62: centered (84 pt long on 107-pt axes, 11 pt clear of the panel letter)


def draw_b(ax, b: dict, lab: dict) -> None:
    style.reference_line(ax, y=1.0)
    agree = b.get("agree")
    hidden = {k for k in agree["pair"] if k != agree["drawn"]} if agree else set()     # C47: drawn once (B_PAIR)
    drawn = [TAG_KEY[t] for t in B_TAGS if TAG_KEY[t] not in hidden]
    for key in drawn:
        s = b["series"][key]
        style.errorbars(ax, key, s["x"], s["median"], s["ci_lo"], s["ci_hi"])
        style.plot_policy(ax, key, s["x"], s["median"])
    style.log_axis(ax, "x", ticks=[3, 10, 30, 100, 300])
    ax.xaxis.set_minor_locator(NullLocator())       # C62: labeled at 3, 10, 30, ...; no comb of minor ticks
    ax.set_xlim(min(b["intensity"]) / 1.4, max(b["intensity"]) * 1.4)
    ax.yaxis.set_major_formatter(style.PLAIN)
    ax.set_xlabel(lab["b_x"])
    ax.set_ylabel(lab["b_y"])
    # the trace lender's point is named at the bottom: a short tick up from the x axis at its x (inward, unlike the
    # scale's ticks), the name centered over it; the y axis starts low enough that the name stays TRACE_GAP_PT below
    # every drawn marker and below the interval bars of the columns it spans (C62: the drawn series only)
    i = b["modes"].index("L-tr")
    x_tr = b["intensity"][i]
    tick_pt = style.mpl.rcParams["xtick.major.size"]
    name = ax.annotate(lab["trace_mode"], xy=(x_tr, 0.0), xycoords=("data", "axes fraction"),
                       xytext=(0.0, tick_pt + TRACE_GAP_PT), textcoords="offset points", ha="center", va="baseline",
                       fontsize=style.TICK_PT, color="black")
    r = ax.figure.canvas.get_renderer()
    k_pt = style.BP_PER_IN / ax.figure.dpi
    bb, ab = name.get_window_extent(r), ax.get_window_extent(r)
    room = (bb.y1 - ab.y0) * k_pt + TRACE_GAP_PT             # pt above the x axis kept free of data
    span = [j for j, xv in enumerate(b["intensity"])
            if bb.x0 * k_pt - TRACE_GAP_PT <= _pt(ax, xv, 1.0)[0] <= bb.x1 * k_pt + TRACE_GAP_PT]
    # (value, pt it reaches below it): every drawn median with its marker, and the interval bars under the name
    low = [(v, marker_radius_pt(k, style.policy(k).markersize)) for k in drawn for v in b["series"][k]["median"]]
    low += [(b["series"][k]["ci_lo"][j], 0.0) for k in drawn for j in span]
    lo, top = ax.get_ylim()
    H = style.axes_rect_in(ax)[3] * style.BP_PER_IN
    lo = min([lo] + [(y - (room + c) / H * top) / (1.0 - (room + c) / H) for y, c in low])
    ax.set_ylim(lo, top)
    ax.plot([x_tr], [0.0], transform=ax.get_xaxis_transform(), marker=TICKUP, markersize=tick_pt,
            markeredgewidth=style.mpl.rcParams["xtick.major.width"], color="black", linestyle="none", clip_on=False,
            label="_nolegend_")


def draw_c(ax, c: dict, lab: dict) -> None:
    x = c["rho1"]
    lim = c["revocable_only_limit"]
    _, g3_label = style.theory_line(ax, x, c["G3b"], "upper", lab["g3b"])
    g3_label.set_verticalalignment("top")      # below its line: BL5's line runs too close above it
    g3_label.xyann = (0.0, -1.5)
    # the limit's label sits right-aligned just above its line's right end, joined to it by a short grey leader
    style.theory_line(ax, x, lim, "limit", lab["limit"], dy=LIMIT_LIFT_PT)
    for tag in C_TAGS:
        key = TAG_KEY[tag]
        style.plot_policy(ax, key, x, c["series"][key]["mean"])
    style.log2_axis(ax, "x", ticks=x)
    style.log_axis(ax, "y", ticks=[1, 10, 100, 1000])
    ax.yaxis.set_minor_locator(NullLocator())       # C62: decades 27 pt high; no comb of minor ticks
    ax.set_xlim(x[0] / 1.25, x[-1] * 1.25)
    ax.set_ylim(1.0, 1.0e4)
    style.end_label_inside(ax)
    ax.set_xlabel(lab["c_x"])
    ax.set_ylabel(lab["c_y"])
    i = int(np.argmax(x))
    ends = [(k, _pt(ax, x[i], c["series"][k]["mean"][i]) - _pt(ax, x[i], lim[i]), style.policy(k).markersize)
            for k in (TAG_KEY[t] for t in C_TAGS)]
    ends = [m for m in ends if np.hypot(*m[1]) < marker_radius_pt(m[0], m[2]) + LIMIT_LIFT_PT]   # under the leader
    ld = ax.annotate("", xy=(x[i], lim[i]), xytext=(0.0, LIMIT_LIFT_PT), textcoords="offset points",
                     arrowprops=dict(arrowstyle="-", color=style.THEORY_GREY, linewidth=LEADER_PT, shrinkA=0.0,
                                     shrinkB=marker_reach_pt(ends, (0.0, 1.0)) + ARROW_GAP_PT),
                     zorder=style.Z_THEORY)
    ld._sublet_role = "theory_leader"
    # BL1 = PS is named in a key on (c)'s letter line (letter_key; C62, inside the panel on two lines before): direct
    # labels at the lines collide with the revocable-only limit, which BL1 approaches


def letter_line_drop_in(fig) -> float:
    """C62: how far (inches) the axes' tops lie below the letters' line so that a key's ink on that line, its
    descenders included, ends LETTER_KEY_CLEAR_PT above the axes (style.panel_letters sets the letters' baseline
    LETTER_RISE_PT above the axes' top; at that rise the descenders of a 7-pt key reached within 0.3 pt of (b)'s
    spine)."""
    r = fig.canvas.get_renderer()
    t = fig.text(0.0, 0.5, "lp", fontsize=style.TICK_PT, va="baseline")
    descent_pt = (fig.transFigure.transform((0.0, 0.5))[1] - t.get_window_extent(r).y0) * style.BP_PER_IN / fig.dpi
    t.remove()
    return max(0.0, LETTER_KEY_CLEAR_PT + descent_pt - LETTER_RISE_PT) / style.BP_PER_IN


def letter_key(ax, letter, handles: list, labels: list, *, handlelength: float, right_in: float):
    """C62: a panel's key on the line of its bold letter (as the paper's Fig. 4 sets its keys): a frameless one-row key
    LETTER_KEY_GAP_PT right of `letter`, its labels on the letter's baseline, an artist of `ax` (role "key"). StyleError
    if it reaches the axes, the panel's top y tick label or `right_in` (inches from the page's left edge: the next
    panel's slot, or the right margin)."""
    from matplotlib.legend import Legend
    fig = ax.figure
    r = fig.canvas.get_renderer()
    W, H = (float(v) for v in fig.get_size_inches())
    lb = letter.get_window_extent(r)
    x = lb.x1 / fig.dpi / W + LETTER_KEY_GAP_PT / style.BP_PER_IN / W
    y_base = float(letter.get_position()[1])                # figure fraction (style.panel_letters)
    key = Legend(ax, handles, labels, loc="lower left", bbox_to_anchor=(x, y_base), bbox_transform=fig.transFigure,
                 frameon=False, borderaxespad=0.0, borderpad=0.0, handlelength=handlelength, ncols=len(labels),
                 handler_map=dict(style.PAIR_HANDLER_MAP))
    ax.add_artist(key)
    key._sublet_role = "key"
    # the labels' baseline on the letter's: a plain TICK_PT reference set on that baseline gives the box bottom that
    # the key's (plain) labels must have (the key laid out first: its texts take their places when it is drawn)
    ref = fig.text(0.0, y_base, "lp", fontsize=style.TICK_PT, va="baseline")
    want = ref.get_window_extent(r).y0
    ref.remove()
    key.draw(r)
    key.set_bbox_to_anchor((x, y_base + (want - key.get_texts()[0].get_window_extent(r).y0) / fig.dpi / H),
                           transform=fig.transFigure)
    kb, ab = key.get_window_extent(r), ax.get_window_extent(r)
    tol = 0.25 * fig.dpi / style.BP_PER_IN
    ticks = [t.label1.get_window_extent(r) for t in ax.yaxis._update_ticks()
             if t.label1.get_visible() and t.label1.get_text()]
    if kb.y0 < ab.y1 - tol or kb.x1 > right_in * fig.dpi + tol or \
            any(min(kb.x1, t.x1) > max(kb.x0, t.x0) and t.y1 > kb.y0 - tol for t in ticks):
        raise style.StyleError(f"{NAME}: the key {labels} on the letter line reaches the axes, a tick label or the "
                               "next panel")
    return key


def draw(data: dict):
    lab = data["labels"]
    fig = style.new_figure(NAME)
    drop = letter_line_drop_in(fig)          # C62: the axes this far below the letters' line, which holds the keys
    axes = style.panel_row(fig, (1, 1, 1), top=style.MARGIN_TOP + 2 * style.LEGEND_ROW + drop)
    draw_a(axes[0], data["a"], lab)
    draw_b(axes[1], data["b"], lab)
    draw_c(axes[2], data["c"], lab)
    align_baselines([ax.xaxis.label for ax in axes])   # C62: (c)'s mathtext label on the others' baseline
    letters = style.panel_letters(axes)
    H = float(fig.get_size_inches()[1])
    for t in letters:                       # on the letters' line, MARGIN_TOP + the legend rows below the page's top
        t.set_y(t.get_position()[1] + drop / H)
    # C62: the panels' own keys on their letters' line, as in the paper's Fig. 4: (b)'s agreeing pair (C47), drawn once,
    # and (c)'s BL1 = PS (in the upper left corner of (b) and inside (c) before)
    slots = [ax._sublet_rect_in[0] - style.LEFT_LABEL for ax in axes[1:]] + \
        [float(fig.get_size_inches()[0]) - style.MARGIN_RIGHT]
    agree = data["b"].get("agree")
    if agree:
        (handle, _), = style.guard_pair_handles([tuple(agree["pair"])], note=False)
        letter_key(axes[1], letters[1], [handle], [agree["key"]], handlelength=B_KEY_HANDLE, right_in=slots[1])
    letter_key(axes[2], letters[2], [Line2D([], [], **style.policy_kwargs("bl1"))], [lab["bl1_eq_a7"]],
               handlelength=C_KEY_HANDLE, right_in=slots[2])
    style.legend_row(fig, [], extra=legend_entries(), rows=2)
    return fig


def report(data: dict, rep: dict) -> None:
    print(f"[{NAME}] E11 revision {data['git_revision']}; G3(b) {[round(v, 3) for v in data['c']['G3b']]}")


def main(argv=None) -> dict:
    return cli(NAME, collect, draw, argv, after=report, doc=__doc__)


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
