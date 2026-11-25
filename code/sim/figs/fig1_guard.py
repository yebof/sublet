"""Fig. 1: the lease contract and the guard on one run (design/figure_plan.md §1, Fig. 1; design/sim_spec_ms3.md §8.1).

(a) A symbolic timeline (M34: no numbers): purchase s, the guaranteed period [s, s+tau), the earliest announcement
s+tau, an announcement r and the death r+H; the guaranteed window [s, s+D_k) shaded, its end s+D_k marked on the
axis; the drain time T^dr and the load time lambda against H; the two reactions, a pre-warm started by r+H-lambda
(dashed) and a cold re-buy after r+H (solid), apart at r+H, since they are alternatives.

(b) The guard on one E11 run (Theorem W(b), PROVEN for the engine as implemented under C1-C3, audited). The run is
chosen by the rule of M51 (``select_run``): the first file, in sorted path order, among
code/sim/out/e11/runs/Q1/I2/1min/L-eg/BL5-G_*.json whose run is held out and whose certificate has aborted,
fb_after_t_a, held, proven_case, core_bound_ok and e_mode_ok true and W_S(t_a) = 0; the script fails if none
qualifies. x is the time since the start of the run (h; M33). Every curve is drawn relative to the safe expert's
accounted cost C_S(t), so the plotted quantities are the test value a_hat(t) + R(t) - C_S(t) (Sublet's style), the
threshold gamma C_S(t) + B(t) - C_S(t) (grey dashed; labeled with the run's gamma written out, ``threshold_label``),
C_S(t) - C_S(t) = 0 (black dotted, drawn over the test value where they meet) and ALG(t) - C_S(t) after the abort
(black solid), with a mark at t_a. Drawn as cumulative costs in USD, as the plan words it, the five curves lie
within 1.5% of the axis height of each other at every slot (the allowance B is 10.6 USD against a day's cost of
about 730 USD), so the abort and the bound ALG(T) <= C_S(T) + B(t_a - 1) of Theorem W(b) at gamma = 1 cannot be
seen; the extract keeps the cumulative series as well (``test_value``, ``threshold``, ``C_S``, ``ALG_after``).

The run files are not versioned, so the extract code/sim/out/figs/fig1.json carries every plotted value and label
and is the figure's source; ``--from-extract`` redraws the figure from it alone. Run from code/sim:
``python -m figs.fig1_guard [--from-extract [JSON]]`` (figs.common.cli).
"""
from __future__ import annotations

import sys

import numpy as np
from matplotlib.patches import Rectangle
from matplotlib.ticker import MaxNLocator

from figs import style
from figs.common import cli, math_rise_pt, printed_baselines_pt
from figs.inputs import Inputs

NAME = "fig1"
RUN_GLOB = "code/sim/out/e11/runs/Q1/I2/1min/L-eg/BL5-G_*.json"
FIRST_STUDY_GLOB = "code/sim/out/q44_study/runs/Q1/I2/1min/L-eg/BL5-G_*.json"
FLAGS = ("aborted", "fb_after_t_a", "held", "proven_case", "core_bound_ok", "e_mode_ok")
DAY_SLOTS = 288                  # I2 is a one-day instance (design §5.5, E11) on the 5-min slow grid
KEYS = ("sublet",)               # the registry keys this figure draws (FIGURE_POLICIES["fig1"])
STATUS_W = ("Theorem W(b): PROVEN for the engine as implemented under C1-C3, audited "
            "(design/Sublet_design.md Table 2.10)")


class SelectionError(RuntimeError):
    """No run file satisfies the selection rule of Fig. 1(b) (sim_spec_ms3 §8.1, M51)."""


# ---------------------------------------------------------------------------------------------------------------
# Selection rule (M51)
def qualifies(run: dict) -> bool:
    """True for a held-out run whose certificate shows Theorem W(b)'s case: an abort followed by all-fallback."""
    q = run.get("q44") or {}
    cert = q.get("certificate") or {}
    if q.get("tuning") is not False:
        return False
    if not all(cert.get(f) is True for f in FLAGS):
        return False
    w = cert.get("W_S_t_a")
    return w is not None and float(w) == 0.0


def select_run(inp: Inputs, pattern: str = RUN_GLOB) -> tuple[str, dict]:
    """(repository-relative name, run) of the first file in sorted path order that qualifies; SelectionError if
    none does. Every file read to evaluate the rule is recorded as a source."""
    names = inp.glob(pattern)
    for name in names:
        run = inp.json(name)
        if qualifies(run):
            return name, run
    raise SelectionError(f"no run file among {len(names)} matching {pattern} is held out and aborted with "
                         f"{', '.join(FLAGS)} true and W_S(t_a) = 0 (sim_spec_ms3 §8.1, M51)")


def _first_study(inp: Inputs, chosen: str, run: dict) -> dict:
    """The first study's pick under the same rule and, for E11-3 (informative), whether the file at the chosen
    path is identical in the fields the panel plots. None values with a note when its run files are absent."""
    names = inp.glob(FIRST_STUDY_GLOB)
    if not names:
        return {"pick": None, "same_path": None, "note": f"no file matches {FIRST_STUDY_GLOB} (runs/ is not "
                                                         "versioned; E11-3 then rests on the claims report)"}
    try:
        pick, _ = select_run(inp, FIRST_STUDY_GLOB)
    except SelectionError as e:
        return {"pick": None, "same_path": False, "note": str(e)}
    base = chosen.rsplit("/", 1)[-1]
    same = pick.rsplit("/", 1)[-1] == base
    out = {"pick": pick, "same_path": same}
    twin = FIRST_STUDY_GLOB.rsplit("/", 1)[0] + "/" + base
    if twin in names:
        old = inp.json(twin)
        oc, nc = old["q44"]["certificate"], run["q44"]["certificate"]
        og, ng = old["metrics"]["policy"]["guard"], run["metrics"]["policy"]["guard"]
        out["same_file"] = twin
        out["t_a"] = {"first_study": oc.get("t_a"), "e11": nc.get("t_a")}
        out["ALG_T"] = {"first_study": oc.get("ALG_T"), "e11": nc.get("ALG_T")}
        out["identical"] = {k: og.get(k) == ng.get(k) for k in ("slots", "a_hat", "C_S", "B", "rhs", "reserve",
                                                                 "t_a")}
        out["identical"]["ALG_per_slot"] = oc.get("ALG_per_slot") == nc.get("ALG_per_slot")
    return out


# ---------------------------------------------------------------------------------------------------------------
def threshold_label(gamma: float) -> str:
    """The label of the threshold gamma C_S + B with the run's gamma written out: "C_S+B" at gamma = 1 (the exact
    value), else e.g. "1.5 C_S+B". Never the glyph gamma, which Liberation Sans sets like an italic y."""
    return "$C_S+B$" if gamma == 1.0 else f"{gamma:g}" + r"$\,C_S+B$"


def collect(inp: Inputs) -> dict:
    """The extract of Fig. 1(b) from the chosen run file (and the first study's files where present)."""
    name, run = select_run(inp)
    q, pol = run["q44"], run["metrics"]["policy"]
    cert, guard, safe = q["certificate"], pol["guard"], pol["safe"]
    alg = [float(v) for v in cert["ALG_per_slot"]]
    if len(alg) != DAY_SLOTS:
        raise style.StyleError(f"{name}: ALG_per_slot has {len(alg)} slots, expected {DAY_SLOTS} (one day)")
    slot_min = 1440.0 / len(alg)
    t_a = int(guard["t_a"])
    gamma = float(guard["gamma"])
    slots = [int(s) for s in guard["slots"]]
    if slots != list(range(t_a + 1)) or int(cert["t_a"]) != t_a:
        raise style.StyleError(f"{name}: the guard's slots are not 0..t_a = {t_a}")
    C_S = [float(v) for v in safe["C_S_curve"]]
    B = [float(v) for v in safe["B_curve"]]
    if len(C_S) != DAY_SLOTS or len(B) != DAY_SLOTS:
        raise style.StyleError(f"{name}: C_S_curve or B_curve does not cover the day")
    rhs = [float(v) for v in guard["rhs"]]
    for i in slots:             # the guard's threshold equals gamma C_S + B of the safe expert's curves up to t_a
        want = gamma * C_S[i] + B[i]
        if abs(rhs[i] - want) > 1e-9 * max(1.0, abs(want)):
            raise style.StyleError(f"{name}: guard.rhs[{i}] = {rhs[i]} differs from gamma C_S + B = {want}")
    test = [float(a) + float(r) for a, r in zip(guard["a_hat"], guard["reserve"])]
    threshold = rhs[: t_a + 1] + [gamma * C_S[i] + B[i] for i in range(t_a + 1, DAY_SLOTS)]
    t_h = [i * slot_min / 60.0 for i in range(DAY_SLOTS)]
    alg_after = alg[t_a:]

    def at(a, t):                # a(t), 0 before the first slot (q44_study.certificate's convention)
        return 0.0 if t < 0 else a[t]

    # Theorem W(b) (G2's abort case with W_S(t_a) = 0 and m = 0): C_S(T) + (gamma - 1) C_S(t_a - 1) + B(t_a - 1)
    bound = C_S[-1] + (gamma - 1.0) * at(C_S, t_a - 1) + at(B, t_a - 1)
    rhs_cert = float(cert["core_bound_rhs"])    # also counts m(t_a - 1), zero up to the certificate's tolerance
    scale = max(1.0, abs(rhs_cert), abs(float(cert["ALG_T"])), max(abs(v) for v in C_S))
    if abs(bound - rhs_cert) > 2e-9 * scale:
        raise style.StyleError(f"{name}: Theorem W(b)'s bound {bound} differs from the certificate's "
                               f"core_bound_rhs {rhs_cert}")
    first = _first_study(inp, name, run)
    return {
        **{f: bool(cert[f]) for f in FLAGS},   # the certificate flags of the selection rule (§8.1), all true
        "W_S_t_a": float(cert["W_S_t_a"]),
        "run_file": name,
        "git_revision": run["meta"].get("git_revision"),
        "instance": q.get("instance"), "mode": q.get("mode"), "tag": q.get("tag"), "seeds": q.get("seeds"),
        "tuning": bool(q["tuning"]),
        "slot_min": slot_min,
        "gamma": gamma,
        "B0": float(guard["B0"]),
        "t_a": t_a,
        "t_a_h": t_a * slot_min / 60.0,
        "t_h": t_h,
        "test_value": test,                    # a_hat(t) + R(t), t = 0..t_a
        "threshold": threshold,                # gamma C_S(t) + B(t), the whole day
        "C_S": C_S,
        "B": B,
        "ALG_after": alg_after,                # ALG(t), t = t_a..T-1
        "ALG_T": float(cert["ALG_T"]),
        "bound_W_b": bound,                    # equals the certificate's core_bound_rhs (checked above)
        "excess": {                            # the plotted values: each curve minus C_S(t)
            "test_value": [v - C_S[i] for i, v in enumerate(test)],
            "threshold": [v - C_S[i] for i, v in enumerate(threshold)],
            "ALG_after": [v - C_S[t_a + i] for i, v in enumerate(alg_after)],
        },
        "same_as_first_study": first.get("same_path"),
        "first_study": first,
        "labels": {
            "a": {"s": "$s$", "s_tau": r"$s+\tau$", "r": "$r$", "s_D": "$s+D_k$", "r_H": "$r+H$", "tau": r"$\tau$",
                  "H": "$H$", "lam": r"$\lambda$", "T_dr": r"$T^{\mathrm{dr}}$",
                  "window": r"guaranteed window $D_k=\tau+H$", "prewarm": "pre-warm", "cold": "cold re-buy"},
            "b": {"x": "Time since start (h)", "y": r"Cost $-\,C_S$ (USD)", "test": r"$\hat{a}+R$",
                  "threshold": threshold_label(gamma), "C_S": "$C_S$", "ALG": "ALG", "t_a": "$t_a$"},
            "status": STATUS_W,
        },
    }


# ---------------------------------------------------------------------------------------------------------------
# Fig. 1(a) is drawn in inches: its axes' data units are inches from the axes' bottom left corner, so that the text
# rows are spaced in inches. (a) has no y axis, so its timeline starts just right of the panel letters' column.
# C62 (7-pt text, 7.97-pt bold letters; 2026-11-24): (a)'s rows are spaced for 7-pt text at about fig1_v3's
# minimum gaps (its A_AXIS_MIN, MARK_DROP, BRACKET_UP, BRACKET_STEP and A_ROW1_MIN; the window label's descent, since it
# sits on the letter's baseline, needs 0.01 in more than A_AXIS_MIN above tau_k), 0.085 in less than at 9 pt, and (b)
# takes about that height (B_TOP 1.00 -> 0.90 in: its axes 1.12 in high, 0.98 in at 9 pt with the 0.42-in bottom
# margin); the 9-pt values are in the comments. A_LEFT, A_TOP and A_BOTTOM are unchanged; (a)'s axes now end where (b)'s
# start. The window label is lowered onto the letter's printed baseline (_pdf_math_raise_in: it is mathtext, which the
# PDF backend set 0.9 pt above it), and (b)'s peak label beside t_a's onto t_a's printed baseline (PEAK_ALIGN_DOWN_PT).
A_LEFT = 0.16                    # (a): the left reserve, a bold "(a)" (0.135 in at 7.97 pt; about 0.16 in at 9 pt)
A_TOP = 0.16                     # (a): figure top to axes top; the letter (a) and the window label share the row above
A_BOTTOM = 1.50                  # (a): figure bottom to axes bottom
B_TOP = 0.90                     # (b): figure top to axes top (C62; 1.00 at 9 pt)
PREWARM_CLEAR_IN = 0.075         # (a): how far right of the mark of s + D_k the pre-warm's start mark sits (in)
A_AXIS_DROP = 0.26               # (a): the window label's baseline to the time axis (C62; 0.31 at 9 pt)
A_MARK_DROP = 0.125              # (a): the time axis to the marks' labels' baseline (C62; 0.15 at 9 pt)
A_BRACKET_UP = 0.08              # (a): the time axis to the tau and H brackets (C62; 0.09 at 9 pt)
A_DRAIN_UP = 0.17                # (a): the time axis to the T^dr bracket (C62; 0.20 at 9 pt)
A_REACT_DROP = 0.235             # (a): the time axis to the reactions' row (C62; 0.27 at 9 pt)
PEAK_ALIGN_DOWN_PT = 0.5         # (b), C62: the peak's label moves down onto t_a's baseline by at most this


def _bracket(ax, x0, x1, y, label, *, h=0.035, dy=0.015, color="black", va="bottom", lw=0.6):
    """A square bracket over [x0, x1] at height y (inches), ends pointing down, label centered above."""
    ax.plot([x0, x0, x1, x1], [y - h, y, y, y - h], color=color, linewidth=lw, solid_capstyle="butt",
            zorder=3)
    return ax.text(0.5 * (x0 + x1), y + dy, label, ha="center", va=va, fontsize=style.TICK_PT, color=color,
                   zorder=4)


def _pdf_math_raise_in(text: str, prop) -> float:
    """How far (in) the PDF backend sets the glyphs of the mathtext `text` above the baseline it is given
    (common.math_rise_pt, in inches): it rounds the expression's height up to a whole point (matplotlib's mathtext
    VectorParse), so on one baseline a lone "s" or "r" (4.8 pt high) prints 0.6 pt lower than "s+tau" or "r+H" (5.2
    and 6.2 pt). 0 for plain text. The Agg preview does not round, so there the lowered labels sit up to that much
    apart."""
    return math_rise_pt(text, prop) / style.BP_PER_IN


def draw_timeline(ax, lab: dict, letter, *, policy_key: str = KEYS[0]) -> None:
    """Fig. 1(a): a symbolic contract timeline in inches (x from the axes' left edge, y from its bottom edge). The
    window label sits in the row above the axes, on the baseline of the panel letter `letter` (panel_letters); the
    rows below it are spaced for 7-pt text (C62; A_AXIS_DROP to A_REACT_DROP; for 9-pt text as built): the tau, H and
    T^dr brackets, the time axis, its marks, the reactions.
    r - (s + tau) = (r + H) - (s + D_k) leaves room for the labels of s + D_k and r + H side by side and keeps the
    T^dr bracket clear of the shading's end; lambda is shorter than (r + H) - (s + D_k) by PREWARM_CLEAR_IN and the
    reactions' gap, so that the pre-warm starts clearly after the window's end, not at it. The reactions take the
    color of the registry key `policy_key` (MS6, design/ms6_spec.md M1, U44: figs/fig1_v2.py passes 'sublet_v2', of
    the same color; this figure keeps its key)."""
    _, y0, w, h = style.axes_rect_in(ax)
    ax.set_xlim(0.0, w)
    ax.set_ylim(0.0, h)
    ax.axis("off")
    ax.set_xticks([])                                      # axis("off") hides the tick labels but keeps them as
    ax.set_yticks([])                                      # texts, which text_overlaps would count
    y_lbl = letter.get_position()[1] * ax.figure.get_size_inches()[1] - y0     # the letter's baseline
    y_ax = y_lbl - A_AXIS_DROP                             # the time axis; the window label clears tau's and H's labels
    s, tau, r, H, tdr, gap = 0.08, 0.42, 0.90, 1.33, 0.25, 0.025
    s_tau, s_D, r_H = s + tau, s + tau + H, r + H
    lam = r_H - s_D - gap - PREWARM_CLEAR_IN               # the pre-warm's start mark clears the mark of s + D_k
    # the guaranteed window [s, s + D_k): shaded from the axis up, with its label inside at the top
    ax.add_patch(Rectangle((s, y_ax), s_D - s, y_lbl + 0.12 - y_ax, facecolor=style.SHADE_GREY, edgecolor="none",
                           zorder=0.5, clip_on=False))
    t = ax.text(s + 0.04, y_lbl, lab["window"], ha="left", va="baseline", fontsize=style.TICK_PT, zorder=4)
    t.set_y(y_lbl - _pdf_math_raise_in(lab["window"], t.get_fontproperties()))     # C62: on the letter's baseline
    # the lease from purchase to death on the time axis
    ax.annotate("", xy=(w, y_ax), xytext=(0.0, y_ax),
                arrowprops=dict(arrowstyle="-|>,head_length=0.4,head_width=0.18", color="black", linewidth=0.6,
                                shrinkA=0, shrinkB=0), zorder=2)
    ax.plot([s, r_H], [y_ax, y_ax], color="#4D4D4D", linewidth=3.0, solid_capstyle="butt", zorder=2.2)
    # the marks, the shading's end s + D_k among them, with their labels on one baseline (cap tops about 0.055 in
    # below the axis), each lowered by the amount the PDF backend raises its glyphs (_pdf_math_raise_in)
    y_mk = y_ax - A_MARK_DROP
    for x, key in ((s, "s"), (s_tau, "s_tau"), (r, "r"), (s_D, "s_D"), (r_H, "r_H")):
        ax.plot([x, x], [y_ax - 0.04, y_ax + 0.04], color="black", linewidth=0.6, zorder=3)
        t = ax.text(x, y_mk, lab[key], ha="center", va="baseline", fontsize=style.TICK_PT, zorder=4)
        t.set_y(y_mk - _pdf_math_raise_in(lab[key], t.get_fontproperties()))
    # brackets above the axis: tau and H; the drain time against H, above H's bracket and right of its label
    _bracket(ax, s, s_tau, y_ax + A_BRACKET_UP, lab["tau"])
    _bracket(ax, r, r_H, y_ax + A_BRACKET_UP, lab["H"])
    _bracket(ax, r_H - tdr, r_H, y_ax + A_DRAIN_UP, lab["T_dr"])
    # the reactions below the axis marks: a pre-warm started by r + H - lambda, a cold re-buy after r + H; each
    # stops `gap` short of r + H, so that they read as alternatives, not as one bar
    c = style.POLICIES[policy_key].color
    y_re = y_ax - A_REACT_DROP
    pw, cold = (r_H - gap - lam, r_H - gap), (r_H + gap, r_H + gap + lam)
    ax.plot(pw, [y_re, y_re], color=c, linewidth=style.SUBLET_LINE_PT, linestyle="--", zorder=3)
    ax.plot(cold, [y_re, y_re], color=c, linewidth=style.SUBLET_LINE_PT, linestyle="-", zorder=3)
    for x in (*pw, *cold):
        ax.plot([x, x], [y_re - 0.035, y_re + 0.035], color=c, linewidth=0.6, zorder=3)
    ax.text(pw[0] - 0.03, y_re, lab["prewarm"], ha="right", va="center", fontsize=style.TICK_PT, color=c, zorder=4)
    ax.text(cold[1] + 0.03, y_re, lab["cold"], ha="left", va="center", fontsize=style.TICK_PT, color=c, zorder=4)
    for seg in (pw, cold):
        ax.text(0.5 * sum(seg), y_re - 0.04, lab["lam"], ha="center", va="top", fontsize=style.TICK_PT, color=c,
                zorder=4)


def draw_trajectory(ax, data: dict) -> None:
    """Fig. 1(b): the guard's test against its threshold, relative to C_S(t)."""
    lab = data["labels"]["b"]
    t_h = np.asarray(data["t_h"], dtype=float)
    t_a = int(data["t_a"])
    ex = data["excess"]
    test = np.asarray(ex["test_value"], dtype=float)
    thr = np.asarray(ex["threshold"], dtype=float)
    alg = np.asarray(ex["ALG_after"], dtype=float)
    x_end = t_h[-1] + data["slot_min"] / 60.0
    style.reference_line(ax, x=data["t_a_h"])
    # C_S - C_S = 0, drawn over the test value's 1.5-pt line, which runs on or just above it for hours and would hide
    # the dots
    ax.plot([t_h[0], x_end], [0.0, 0.0], color="black", linestyle=":", linewidth=style.LINE_PT,
            zorder=style.Z_SUBLET + 0.1, label="_nolegend_")
    style.theory_line(ax, t_h, thr, "upper", lab["threshold"], label_xy=(x_end, thr[-1]))
    ax.plot(t_h[t_a:], alg, color="black", linestyle="-", linewidth=style.LINE_PT, zorder=2.1, label="_nolegend_")
    style.plot_policy(ax, "sublet", t_h[: t_a + 1], test, markers=False)
    ax.set_xlim(0.0, x_end)
    ticks = [0, 6, 12, 18, 24]
    ax.set_xticks(ticks)
    ax.xaxis.set_major_formatter(style.PLAIN)
    style.end_label_inside(ax)
    top = max(float(np.max(test)), float(np.max(thr)), float(np.max(alg)))
    ax.set_ylim(-0.12 * top, 1.18 * top)
    ax.yaxis.set_major_locator(MaxNLocator(4, steps=[1, 2, 2.5, 5, 10]))   # the default left two at 9 pt
    ax.yaxis.set_major_formatter(style.PLAIN)
    ax.set_xlabel(lab["x"])
    ax.set_ylabel(lab["y"])
    # direct labels: C_S at the dotted zero line, ALG below the middle of its line, t_a at the top, the test value
    # above its peak, or, for an abort too early for the label to fit left of the peak, after t_a in the top row
    ax.annotate(lab["C_S"], xy=(x_end, 0.0), xytext=(0, 1.5), textcoords="offset points", ha="right",
                va="bottom", fontsize=style.TICK_PT, color="black")
    ax.annotate(lab["ALG"], xy=(0.5 * (data["t_a_h"] + x_end), alg[len(alg) // 2]), xytext=(0, -1.5),
                textcoords="offset points", ha="center", va="top", fontsize=style.TICK_PT, color="black")
    t_lab = ax.annotate(lab["t_a"], xy=(data["t_a_h"], 1.18 * top), xytext=(2.0, -1.0), textcoords="offset points",
                        ha="left", va="top", fontsize=style.TICK_PT, color="black")
    i = int(np.argmax(test))
    peak = style.direct_label(ax, "sublet", t_h[i], test[i], lab["test"], dx=-3.0, dy=2.0, ha="right", va="bottom")
    r = ax.figure.canvas.get_renderer()
    if peak.get_window_extent(r).x0 < ax.get_window_extent(r).x0:
        peak.remove()
        style.direct_label(ax, "sublet", 1.0, 1.0, lab["test"], dx=4.0, dy=0.0, ha="left", va="top", xycoords=t_lab)
        return
    # C62: a peak label beside t_a's (their boxes level) prints on t_a's baseline, if that moves it up or by at most
    # PEAK_ALIGN_DOWN_PT down (it reads as one row with t_a's label; as built, 1.8 pt below it at 7 pt)
    bp, bt = peak.get_window_extent(r), t_lab.get_window_extent(r)
    if bp.y1 > bt.y0 and bp.y0 < bt.y1:
        b_peak, b_t = printed_baselines_pt(ax.figure, [peak, t_lab])
        if b_t - b_peak >= -PEAK_ALIGN_DOWN_PT:                  # an annotation: its offset (points) moves it
            peak.xyann = (peak.xyann[0], peak.xyann[1] + (b_t - b_peak))
            peak._sublet_baseline_shift_pt = round(b_t - b_peak, 4)


def draw(data: dict):
    fig = style.new_figure(NAME)
    (a,) = style.panel_row(fig, (1,), left=[A_LEFT], bottom=A_BOTTOM, top=A_TOP)
    (b,) = style.panel_row(fig, (1,), bottom=style.MARGIN_BOTTOM, top=B_TOP)
    letters = style.panel_letters([a, b])
    draw_timeline(a, data["labels"]["a"], letters[0])
    draw_trajectory(b, data)
    return fig


def report(data: dict, rep: dict) -> None:
    print(f"[{NAME}] {data['run_file']} t_a = {data['t_a']}; preview {rep['png']}")


def main(argv=None) -> dict:
    return cli(NAME, collect, draw, argv, after=report, doc=__doc__)


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
