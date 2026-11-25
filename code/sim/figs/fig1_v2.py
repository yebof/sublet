"""Fig. 1 v2, the paper's Fig. 1: the lease contract and Sublet's projection on one illustrative run (design/ms6_spec.md
§1.1 M1, §2 U44; design/figure_plan.md §1, Fig. 1; design/ms6/inventory_w8_gate.md §4). It replaces the frozen fig1
(figs/fig1_guard.py) in the manuscript; fig1 stays frozen (style.LEGACY_PENDING), since the MS3 claims report reads
its extract.

(a) The frozen timeline (fig1_guard.draw_timeline, at fig1's placement), with the subscripts of contract k fixed
(consistency C-14 of design/ms6/inventory_consistency.md): tau_k, H_k, D_k = tau_k + H_k and r + H_k, and the
reactions in Sublet's color (sublet_v2, the color of the frozen panel's key).

(b) One illustrative run of Sublet (A8P around A9 at the allowance min{W_k, LB'}): the record
code/sim/out/fig1v2/run.json of sublet/experiments/fig1_illustrative.py (the pilot cell Q44 I2 c1, a development
cell of one day, under the eager stress lender L-eg, policy seed 0), with its manifest, whose sha256 of the record
and checks (logged run = unlogged run, the log's consistency, the pilot's ALG within 1e-9) must hold. As in the
frozen panel, x is the time since the start of the run (h) and every series is drawn relative to the safe expert's
accounted cost C_S(t) (y "Cost - C_S (USD)"): the threshold gamma C_S + B (grey dashed, its label the run's gamma
written out, "C_S+B" at gamma = 1: fig1_guard.threshold_label; C47: and at each projected slot a short solid grey tick
at that slot's threshold, across the stem, above the executed line, TICK_HALF_PT either side of the slot's middle:
the threshold's steps in the first hour are about 3 pt wide and lay under the executed line, so the first circles
showed no threshold under them), the executed list's test value a_hat + R (Sublet's
line), and, at each projected slot, the inner list's own test value a_hat_E + R_E (Sublet's open marker at the
slot's middle, joined to the executed value by a 0.6-pt stem in Sublet's color: the cut that the projection made);
C_S - C_S = 0 is black dotted, labeled C_S. The threshold and the executed test value are step lines (each slot's
value held over the slot), so that each slot's test value is compared with that slot's threshold over the whole slot,
as the guard compares them; a polyline would cross a rising threshold between two slots without a crossing in the
run. The labels are placed on the panel's free space next to their series (common.place_label), the threshold's in
the theory grey, the others in Sublet's label color. The figure fails (StyleError) if the run aborted or projected no
slot, if an executed test value exceeds the threshold by more than the guard's tolerance (the run record's guard_tol,
guard.GUARD_TOL, times max(1, |threshold|)), or if an inner test value at a projected slot does not: the caption claims
the opposite.

No design ID is drawn. The extract code/sim/out/figs/fig1v2.json carries every plotted value and label, the run's
provenance (the run file and its sha256, the run's git revision and dirty flag from the manifest, the cell, the
lender, the seed and the tag's parameters) and labels.caption, a caption draft (at most CAPTION_LINES lines of about
CAPTION_LINE_CHARS characters, every number read from the run) that cites the paper's numbers of Theorem W(a) (Theorem
16), Remark R (Lemma 11) and Proposition P (Proposition 15) by their labels of design/ms6_spec.md §5 (labels.refs),
and the status labels of the three results as their sources state them (labels.status). Run from code/sim:
``python -m figs.fig1_v2 [--from-extract [JSON]]`` (figs.common.cli).
"""
from __future__ import annotations

import hashlib
import math
import re
import sys
from typing import Mapping

import numpy as np
from matplotlib.ticker import FixedLocator, MaxNLocator

from figs import style
from figs.common import cli, place_label, points_pt
from figs.fig1_guard import A_BOTTOM, A_LEFT, A_TOP, B_TOP, draw_timeline, threshold_label
from figs.inputs import Inputs

NAME = "fig1v2"
RUN = "code/sim/out/fig1v2/run.json"
MANIFEST = "code/sim/out/fig1v2/manifest.json"
KEY = "sublet_v2"                # the registry key this figure draws (FIGURE_POLICIES["fig1v2"])
STEM_PT = 0.6                    # the stem from the executed test value to the inner list's (not in §5)
TICK_HALF_PT = 3.5               # C47: half the width of the grey tick at a projected slot's threshold (not in §5)
CAPTION_LINES = 6                # figure plan §5, "Captions": at most 6 lines for a single-column figure
CAPTION_LINE_CHARS = 70          # about this many characters per line of an 8-pt single-column caption (estimate)
X_STEPS_H = (1, 2, 3, 6, 12)     # x tick steps (h): the smallest with at most 4 intervals over the run
LABELS_A = {"s": "$s$", "s_tau": r"$s+\tau_k$", "r": "$r$", "s_D": "$s+D_k$", "r_H": "$r+H_k$", "tau": r"$\tau_k$",
            "H": "$H_k$", "lam": r"$\lambda$", "T_dr": r"$T^{\mathrm{dr}}$",
            "window": r"guaranteed window $D_k=\tau_k+H_k$", "prewarm": "pre-warm", "cold": "cold re-buy"}
# the results the caption cites: design name, the paper's label and number (design/ms6_spec.md §5)
REFS = (("Theorem W(a)", "thm:fullmodel", "Theorem 16"), ("Remark R", "lem:projection", "Lemma 11"),
        ("Proposition P", "prop:noabort", "Proposition 15"))
# status labels as their sources state them (design/ms6/inventory_w8_gate.md §4.5)
STATUS = (
    {"result": "Theorem W(a), W(b)", "status": "PROVEN for the engine as implemented, under the conditions C1-C3 of "
     "T0gBound; numerically checked; audited (audit_guard.md, last section)",
     "source": "design/theory/c3_c4_c5_general.md §0, row W(a), W(b)"},
    {"result": "Remark R", "status": "PROVEN; audited (audit_guard.md, \"Audit addendum (P6)\"); bit-for-bit identity "
     "of the code numerically checked under (F)", "source": "design/theory/c3_c4_c5_general.md §0, row R"},
    {"result": "Proposition P", "status": "PROVEN ((a)-(c) and the Consequence for its instance class; (d) under its "
     "three hypotheses); numerically checked; audited", "source": "design/Sublet_design.md Table 2.10, row P"},
    {"result": "Lemma P.1", "status": "PROVEN; audited", "source": "design/Sublet_design.md Table 2.10, row P.1"},
)


def _sha256(path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def x_ticks(hours: float) -> list:
    """Ticks every X_STEPS_H step (the smallest with at most 4 intervals) from 0 to the run's end."""
    step = next((s for s in X_STEPS_H if hours / s <= 4.0 + 1e-9), X_STEPS_H[-1])
    return [i * step for i in range(int(math.floor(hours / step + 1e-9)) + 1)]


def caption(d: Mapping) -> str:
    """The caption draft (M1): (a) in one sentence; (b) an illustrative run of Sublet on its cell, named in the paper's
    words (C47, print check of the gate: "one-day pilot instance, cell c", with the run's span where it is not the
    whole day; not "the one-day instance I2", which reads as the information class I2 of Tables I and II), under the
    eager stress lender; the projected slots at which the inner policy's proposals exceed the threshold (grey: its
    dashed line and its ticks at those slots) while the executed list stays under it, citing Lemma 11 (Remark R) and
    Theorem 16(a) (Theorem W(a)); and no abort with the conditions of Proposition 15 (Proposition P) that the run
    meets, S on all-fallback and T0g in bound form at every slot (s_fb_all, t0g_bound_all; C47: the bare "no abort
    (Proposition 15)" omitted them), or a bare "no abort" without the citation if the run does not meet them. Results
    by \\ref; every number from the run. The threshold is written with its gamma ("$C_S+B$" at gamma = 1), so gamma
    needs no clause of its own, and the y label says that the values are relative to C_S (both clauses left out to keep
    the six lines with the cell named)."""
    hours = d["hours"]
    span = "" if abs(hours - 24.0) < 1e-9 else f", first {hours:g} h"
    g = "" if d["gamma"] == 1.0 else f"{d['gamma']:g}"
    cell = d.get("cell") or {}
    kind = "pilot instance" if cell.get("development_cell") else "instance"
    where = f"one-day {kind}, cell {cell['c']}{span}" if "c" in cell else f"one-day {kind}{span}"
    abort = (r"no abort ($S$ on all-fallback, T0g in bound form; Proposition~\ref{prop:noabort})"
             if d.get("s_fb_all") and d.get("t0g_bound_all") else "no abort")
    return (r"(a) Contract $k$: guaranteed window $D_k=\tau_k+H_k$, drain time $T^{\mathrm{dr}}$ and load time "
            r"$\lambda$ against the notice $H_k$. (b) Illustrative run of Sublet (" + where +
            r"; eager stress lender): at the "
            f"{d['projected_slots']} projected slots the inner policy's proposals (circles) exceed the threshold "
            f"${g}C_S+B$ (grey) and the executed list stays under it "
            r"(Lemma~\ref{lem:projection}, Theorem~\ref{thm:fullmodel}(a)); " + abort + ".")


def printed_chars(tex: str) -> int:
    """About the number of printed characters of a caption in LaTeX: a \\ref as 2 characters, math without its
    markup."""
    s = re.sub(r"\\ref\{[^}]*\}", "00", tex)
    s = s.replace("~", " ")
    s = re.sub(r"\\mathrm\{([^}]*)\}", r"\1", s)
    s = re.sub(r"\\(tau|lambda|gamma)", "x", s)
    return len(re.sub(r"[${}_^\\]", "", s))


def collect(inp: Inputs) -> dict:
    """The extract of Fig. 1 v2 from the run record and its manifest."""
    run = inp.json(RUN)
    man = inp.json(MANIFEST)
    sha = _sha256(inp.path(RUN))
    if man.get("run_sha256") != sha:
        raise style.StyleError(f"{RUN}: sha256 {sha} differs from its manifest's run_sha256 {man.get('run_sha256')}")
    if not (man.get("checks") or {}).get("pass"):
        raise style.StyleError(f"{MANIFEST}: the run's checks do not pass ({man.get('checks')})")
    s, ser, grid = run["summary"], run["series"], run["grid"]
    if s["aborted"] or s["t_a"] is not None:
        raise style.StyleError(f"{RUN}: the run aborted at slot {s['t_a']}; the panel shows a run without an abort")
    T, slot_min, gamma = int(grid["T_slow"]), float(grid["slow_min"]), float(run["gamma"])
    test = np.asarray(ser["test_value"], dtype=float)
    thr = np.asarray(ser["threshold"], dtype=float)
    C_S = np.asarray(ser["C_S"], dtype=float)
    B = np.asarray(ser["B"], dtype=float)
    proj = [bool(p) for p in ser["projected"]]
    if not (len(test) == len(thr) == len(C_S) == len(B) == len(proj) == T) or not np.isfinite(test).all():
        raise style.StyleError(f"{RUN}: the series do not cover the run's {T} slots")
    want = gamma * C_S + B
    if np.any(np.abs(thr - want) > 1e-9 * np.maximum(1.0, np.abs(want))):
        raise style.StyleError(f"{RUN}: the threshold differs from gamma C_S + B")
    lim = thr + float(run["guard_tol"]) * np.maximum(1.0, np.abs(thr))
    if np.any(test > lim):
        raise style.StyleError(f"{RUN}: the executed test value exceeds the threshold at slots "
                               f"{np.flatnonzero(test > lim)[:5].tolist()}")
    idx = [t for t in range(T) if proj[t]]
    if not idx or len(idx) != int(s["projected_slots"]):
        raise style.StyleError(f"{RUN}: {len(idx)} projected slots in the series, {s['projected_slots']} in the "
                               "summary; the panel needs at least one")
    inner = [float(ser["inner_test_value"][t]) for t in idx]
    low = [t for t, v in zip(idx, inner) if not v > lim[t]]
    if low:
        raise style.StyleError(f"{RUN}: at the projected slots {low[:5]} the inner list's test value does not "
                               "exceed the threshold")
    t_h = [t * slot_min / 60.0 for t in range(T)]
    hours = T * slot_min / 60.0
    out = {
        "run_file": RUN, "run_sha256": sha, "manifest": MANIFEST,
        "git_revision": man.get("git_revision"), "tracked_files_dirty": man.get("tracked_files_dirty"),
        "reduced": bool(man.get("reduced")), "pilot_check": (man.get("checks") or {}).get("pilot"),
        "cell": run["cell"], "window": run.get("window"), "mode": run["mode"], "policy_seed": run["policy_seed"],
        "lender_seed": run["lender_seed"], "tag": run["tag"], "tag_params": run["tag_params"],
        "policy_id": run["policy"]["id"],
        "n_slots": T, "slot_min": slot_min, "hours": hours, "gamma": gamma,
        "t_h": t_h,
        "test_value": test.tolist(), "threshold": thr.tolist(), "C_S": C_S.tolist(), "B": B.tolist(),
        "candidate": list(ser["candidate"]),
        "projected": idx,                                   # the projected slots
        "inner_test_value": inner,                          # a_hat_E + R_E of A_E(t) at those slots
        "excess": {                                         # the plotted values: each series minus C_S(t)
            "test_value": (test - C_S).tolist(),
            "threshold": (thr - C_S).tolist(),
            "inner": [v - float(C_S[t]) for t, v in zip(idx, inner)],
        },
        "ALG_T": float(s["ALG_T"]), "ALG_cum_T": float(ser["ALG_cum"][-1]), "aborted": False,
        "projected_slots": len(idx), "projection": s["projection"], "projected_runs": s["projected_runs"],
        "B_T": float(s["B_T"]), "online_lb": s.get("online_lb"), "s_fb_all": s["s_fb_all"],
        "t0g_bound_all": s["t0g_bound_all"], "min_margin_usd": float(s["min_margin_usd"]),
        "inner_excess_usd": s["inner_excess_usd"],
    }
    cap = caption(out)
    n_chars = printed_chars(cap)
    out["labels"] = {
        "a": dict(LABELS_A),
        "b": {"x": "Time since start (h)", "y": r"Cost $-\,C_S$ (USD)", "test": r"$\hat{a}+R$",
              "inner": r"$\hat{a}_E+R_E$", "threshold": threshold_label(gamma), "C_S": "$C_S$"},
        "caption": cap, "caption_printed_chars": n_chars,
        "caption_lines_est": math.ceil(n_chars / CAPTION_LINE_CHARS),
        "refs": [{"design": a, "label": b, "paper": c} for a, b, c in REFS],
        "status": [dict(x) for x in STATUS],
    }
    if out["labels"]["caption_lines_est"] > CAPTION_LINES:
        raise style.StyleError(f"{NAME}: the caption draft has about {n_chars} printed characters, more than "
                               f"{CAPTION_LINES} lines of about {CAPTION_LINE_CHARS}")
    return out


# ---------------------------------------------------------------------------------------------------------------
def _steps(t_h, v, x_end):
    """A step line's points: each value held from its slot's start to the next slot's start, the last to x_end."""
    return np.append(np.asarray(t_h, dtype=float), x_end), np.append(np.asarray(v, dtype=float), v[-1])


def quiet_stretch(n: int, projected) -> tuple:
    """(first, last) slot of the longest run of slots without a projected slot (the first such run on a tie): the
    executed test value's label goes next to its line in the middle third of it, away from the stems."""
    best, start = (0, -1), 0
    for t in [*sorted(projected), n]:
        if t - start > best[1] - best[0] + 1:
            best = (start, t - 1)
        start = t + 1
    return best


def draw_run(ax, data: dict) -> None:
    """Fig. 1(b): the executed and the inner list's test values against the threshold, relative to C_S(t)."""
    lab = data["labels"]["b"]
    p = style.policy(KEY)
    dt = data["slot_min"] / 60.0
    x_end = data["hours"]
    ex = data["excess"]
    test, thr = np.asarray(ex["test_value"]), np.asarray(ex["threshold"])
    xs = np.asarray([data["t_h"][t] + 0.5 * dt for t in data["projected"]])     # the slot's middle
    inner = np.asarray(ex["inner"])
    exec_at = test[np.asarray(data["projected"])]
    ax.plot([0.0, x_end], [0.0, 0.0], color="black", linestyle=":", linewidth=style.LINE_PT,
            zorder=style.Z_SUBLET + 0.1, label="_nolegend_")                     # C_S - C_S, over the test value
    xt, yt = _steps(data["t_h"], thr, x_end)
    _, thr_lab = style.theory_line(ax, xt, yt, "upper", lab["threshold"], drawstyle="steps-post")
    thr_lab.remove()                                                            # placed on free space below
    xe, ye = _steps(data["t_h"], test, x_end)
    style.plot_policy(ax, KEY, xe, ye, markers=False, drawstyle="steps-post")
    # not clipped: a projected first or last slot's marker sits on the axes' edge
    ax.vlines(xs, exec_at, inner, colors=p.color, linewidth=STEM_PT, zorder=p.zorder - 0.02, label="_nolegend_",
              clip_on=False)
    style.plot_policy(ax, KEY, xs, inner, lines=False, markerfacecolor="white", markeredgecolor=p.color,
                      zorder=p.zorder + 0.05, label="_nolegend_", clip_on=False)
    ax.set_xlim(0.0, x_end)
    # C47 (print check of the gate): at each projected slot a short grey tick at that slot's threshold, across the
    # stem and over the executed line, so that each circle shows above its own threshold (in the first hour the
    # threshold rises from 2.4 to 16 USD over about 3 pt of the axis, under the executed line and the circles)
    half = TICK_HALF_PT / (style.axes_rect_in(ax)[2] * style.BP_PER_IN / x_end)       # in hours
    thr_at = thr[np.asarray(data["projected"])]
    ticks = ax.hlines(thr_at, xs - half, xs + half, colors=style.THEORY_GREY, linewidth=style.LINE_PT,
                      zorder=p.zorder + 0.03, label="_nolegend_")          # clipped at the axes' sides
    ticks._sublet_role = "threshold_tick"
    ax.xaxis.set_major_locator(FixedLocator(x_ticks(x_end)))
    ax.xaxis.set_major_formatter(style.PLAIN)
    style.end_label_inside(ax)
    lo = min(0.0, float(test.min()), float(thr.min()))
    hi = max(float(inner.max()), float(thr.max()), float(test.max()))
    span = hi - lo
    ax.set_ylim(lo - 0.10 * span, hi + 0.08 * span)
    ax.yaxis.set_major_locator(MaxNLocator(5, steps=[1, 2, 2.5, 5, 10]))   # 0, 10, 20, 30 on the run's axis
    ax.yaxis.set_major_formatter(style.PLAIN)
    ax.set_xlabel(lab["x"])
    ax.set_ylabel(lab["y"])
    # direct labels on the free space: C_S at the right end of the dotted zero line, as in the frozen panel; the
    # threshold's next to its line and nearer to it than to the test value; the inner list's next to its markers;
    # the executed test value's next to its line in the middle third of the longest stretch without a projected slot,
    # nearer to it than to the markers and the threshold
    ax.annotate(lab["C_S"], xy=(x_end, 0.0), xytext=(0, 1.5), textcoords="offset points", ha="right", va="bottom",
                fontsize=style.TICK_PT, color="black")
    pt_thr, pt_test = points_pt(ax, xt, yt), points_pt(ax, xe, ye)
    pt_in = points_pt(ax, xs, inner)
    q0, q1 = quiet_stretch(data["n_slots"], data["projected"])
    m0, m1 = q0 + (q1 - q0 + 1) // 3, q1 - (q1 - q0 + 1) // 3              # its middle third
    pt_quiet = points_pt(ax, data["t_h"][m0:m1 + 1], test[m0:m1 + 1])
    placed = [place_label(ax, lab["threshold"], pt_thr, others=np.vstack([pt_test, pt_in]),
                          color=style.THEORY_LABEL_GREY),
              place_label(ax, lab["inner"], pt_in, others=pt_test, color=p.label_color),
              place_label(ax, lab["test"], pt_quiet, others=np.vstack([pt_in, pt_thr]), color=p.label_color)]
    missing = [t for t, x in zip(("threshold", "inner", "test"), placed) if x is None]
    if missing:
        raise style.StyleError(f"{NAME}: no free space for the labels {missing} in (b)")
    placed[0]._sublet_role = thr_lab._sublet_role             # the threshold's label is a theory label


def draw(data: dict):
    fig = style.new_figure(NAME)
    (a,) = style.panel_row(fig, (1,), left=[A_LEFT], bottom=A_BOTTOM, top=A_TOP)
    (b,) = style.panel_row(fig, (1,), bottom=style.MARGIN_BOTTOM, top=B_TOP)
    letters = style.panel_letters([a, b])
    draw_timeline(a, data["labels"]["a"], letters[0], policy_key=KEY)
    draw_run(b, data)
    return fig


def report(data: dict, rep: dict) -> None:
    print(f"[{NAME}] {data['run_file']} ({data['cell']['cell']} {data['mode']} p{data['policy_seed']}): projected "
          f"{data['projected_slots']}, no abort; caption about {data['labels']['caption_lines_est']} lines; preview "
          f"{rep['png']}")


def main(argv=None) -> dict:
    return cli(NAME, collect, draw, argv, after=report, doc=__doc__)


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
