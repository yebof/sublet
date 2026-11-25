"""sf_e11_fam: E11's families F1-F3 (design/sim_spec_ms3.md §8.7; design/figure_plan.md §4, part S-F).

From code/sim/out/e11/summary.json D5.families (ALG/OPT, the mean over the policy seeds p0-p9, exact OPT):
(a) F1 (the C3-T4 family) at rho = 16 under its adaptive lender F-ad, against m;
(b) F2 (the O1 family) at rho = 16 under the oblivious safe-site lender F-ss, against m;
(c) F3 (C3-P5's insurance family) at T = 48 under the eager lender F-eg, against rho_1, with the revocable-only limit
    a1 rho1 / a2 for T -> infinity (C3-P5, PROVEN).
In (a) and (b) the pathwise G3 envelope (G2, PROVEN, audited) of the lagged RetroRenting-style rule with the one-way
guard (E11's tag BL5-G, bl5_g1) is drawn as the mean over p0-p9 of
q44.certificate.cor_G3_rhs / q44.opt of its run files code/sim/out/e11/runs/Q6/<instance>/core/<mode>/
BL5-G_c0_*.json (one file per policy seed; under the oblivious lenders the lender seed equals the policy seed, so
the files are BL5-G_c0_l<p>_p<p>.json there). F-iid, F-eg and the other rho are in the extract (``all_modes``) and in
E11's tables.md. BL1 and BL1-G go to the extract only: BL1 shares RR-renew's color without sharing its family, so
check_color_reuse forbids both in one figure. Where two drawn policies coincide on every point of a panel (A7 and
A7 + guard on F1 and F2, BL5-G and BL5 on F2, BL5-G and A2 with the theory r-bar on F3), the pair is drawn once, as
the first of PAIRS, and named in the panel's key, "equal". A pair drawn as two lines that agrees within one marker
size (3.5 pt) on the panel's y axis on every point is named in the key too, "agree within p%" with p its largest
relative difference rounded up to a whole percent (figs.common.agreement; on F1: BL5-G and BL5, equal at m = 4 and 8
only, and Marking and RR-renew), or "equal" where it is equal at every point. A key entry's handle shows the pair's
two samples side by side (style.MarkerPair; an inner policy before its guarded configuration), which the legend row
names: the names of a guarded configuration are wider than a panel (C46, design/ms6_spec.md M2; as built at 9 pt,
the keys "Lagged RetroRenting + one-way guard ≈ RetroRenting-style, lagged (within 10%)" and "PD heuristic + one-way
guard = PD heuristic" left (a) no room for the data), so the key names the agreement and the extract keeps the texts
with the names for the caption (labels.coincide_names, labels.near_names). The extract's ``near`` gives each
candidate pair's largest |log10 ratio|, that agreement and the points where it is equal, and ``labels.near`` each
candidate's key text. A drawn series
more than a decade above every other drawn value (BL5 on F3) is shown off scale: up arrows in its color at the top
edge, named with its range. Each panel's y axis is as tall as its data, theory lines and labels need under the key
(upper left in (a) and (b), lower right in (c)) and the off-scale row, and starts below 1 only where a marker at 1
would touch the x axis ((b)). At most six policy lines per panel (plan §5): A3 is drawn in (c), and its F1 and F2 values are
in the extract.

MS6 C46 (design/ms6_spec.md M2, M4): the guarded series are their configurations' keys (BL5-G bl5_g1, PS-G a7_g1, BL5
bl5_lag), named by their registry labels in the legend row; the data tags are E11's. The envelope's label names no
policy (it is BL5-G's; labels.envelope_of, for the caption) and no design ID: "core ratio bound", as Fig. 3(c) names
the same bound (C47, print check of the gate; "G3 envelope" before), and the limit's T is set in math ($T\\to\\infty$,
as Fig. 6). The keys name agreements (above). C47 (print check of the gate, U46): labels.caption, a caption draft for
the supplement, names F1-F3 by their results, says whose bound the core ratio bound is (it bounds no unguarded policy,
and A2 with the theory r-bar ends above it on F2) and names each key's pairs; draw() writes it, since the keys' near
pairs depend on the panels' final scales. The limit's arrow is \\longrightarrow, as in Fig. 3(c)'s same label.

C62 (the type scale of the caption; figures high-end, informative, readable): the margins of style; the keys' handles
are the pair's two markers alone, 1.6 em long (with their lines in 2.4 em before, each half drew a stub of line on both
sides of its marker, which read as a dash between the pair; the legend row shows the lines), as Fig. 3(b)'s key; a
decade-labeled y axis has unlabeled minor ticks at 2 and 5 times the decades only (MINOR_MANT; eight per decade
before, a comb on decades of about 45 pt), and one labeled at 1, 2 and 5 times the decades none. The legend keeps its
two rows (one row of the eight registry names is wider than the page). The keys' pairs, and so labels.caption, are
those of the 9-pt build: the extract is unchanged.

Run files are read, so the extract code/sim/out/figs/sf_e11_fam.json carries every plotted value and label and is the
figure's source; ``--from-extract`` redraws from it alone. Run from code/sim:
``python -m figs.supp.sf_e11_fam [--from-extract [JSON]]`` (figs.common.cli).
"""
from __future__ import annotations

import math
import re
import sys

import numpy as np
from matplotlib.lines import Line2D
from matplotlib.path import Path
from matplotlib.ticker import FixedLocator
from matplotlib.transforms import offset_copy

from figs import style
from figs.common import AGREE_NEAR, AGREE_SAME, agreement, cli, text_width_in
from figs.inputs import Inputs

NAME = "sf_e11_fam"
WIDTH, HEIGHT = "W2", 2.5
SUMMARY = "code/sim/out/e11/summary.json"
RUN_DIR = "code/sim/out/e11/runs/Q6"
TAG_KEY = {"BL5-G": "bl5_g1", "BL5": "bl5_lag", "PS": "a7", "PS-G": "a7_g1", "A2-th": "a2_theory", "A3": "a3",
           "RR_RENEW": "rr_renew", "MARKING": "marking"}      # C46 (M2-M4): the configuration keys
KEYS = tuple(TAG_KEY.values())
PANELS = {   # panel: (family, instance filter, mode, x field, tags drawn)
    "a": ("F1", "_r16", "F-ad", "m", ("BL5", "A2-th", "PS", "PS-G", "RR_RENEW", "MARKING", "BL5-G")),
    "b": ("F2", "_r16", "F-ss", "m", ("BL5", "A2-th", "PS", "PS-G", "RR_RENEW", "MARKING", "BL5-G")),
    "c": ("F3", "_T48", "F-eg", "rho1", ("BL5", "A3", "PS", "PS-G", "A2-th", "BL5-G")),
}
EXTRA_TAGS = {"a": ("A3",), "b": ("A3",), "c": ()}       # in the extract, not drawn (at most six lines per panel)
# pairs of policies named in a panel: where the second of a pair in PAIRS equals the first on every point it is drawn
# once, as the first, and named in the key, KEY_SAME; any other pair (of PAIRS or NEAR_PAIRS) of drawn series is drawn
# as two lines and named in the key, KEY_NEAR, where it agrees within one marker size (style.MARKER_PT) on the panel's
# y axis on every point (the texts with the names, common.AGREE_SAME and AGREE_NEAR, are in the extract)
PAIRS = (("a7_g1", "a7"), ("bl5_g1", "a2_theory"), ("bl5_g1", "bl5_lag"))
NEAR_PAIRS = (("marking", "rr_renew"),)
# where a panel's key goes (not data): "top", in the upper left corner above the data (under the off-scale row, if
# any; the y axis reaches high enough for both), or "bottom", in the lower right corner under the lowest lines, where
# it must not cross a line (StyleError)
KEY_AT = {"a": "top", "b": "top", "c": "bottom"}
KEY_SAME = "equal"                   # C46: a key's text, beside the pair's two samples (the legend row names them)
KEY_NEAR = "agree within {pct}%"
ENV_LABEL = -1               # the point of the envelope at which it is labeled (index into x)
ENV_LIFT_PT = 4.0            # envelope label set this far above a marker it is lifted over
OFF_SCALE_DEC = 1.0          # a drawn series more than this many decades above every other drawn value is off scale
ARROW_PT = (6.0, 1.0)        # off-scale markers (up arrows at the top edge): size and line width
UP_ARROW = Path([(0.0, -1.0), (0.0, 1.0), (-0.5, 0.35), (0.0, 1.0), (0.5, 0.35)],
                [Path.MOVETO, Path.LINETO, Path.MOVETO, Path.LINETO, Path.LINETO])       # an open up arrow
GAP_PT = 2.0                 # gaps between the stacked elements of a panel's top and bottom
TOP_TICK_PT = 6.0            # a y tick is labeled only this far or further below the axes top
MINOR_MANT = (2.0, 5.0)      # C62: unlabeled minor ticks at these times the decades on a decade-labeled y axis
LINE_H_PT = 1.2 * style.TICK_PT     # height of a line of label text
KEY_KW = dict(frameon=False, handlelength=1.6)       # C46: room for a pair's two samples (C62: markers, 2.4 em with
#                                                       their lines before), as Fig. 3(b)'s key
ENVELOPE = ("a", "b")
SEEDS = 10
LEGEND = ("bl5_g1", "a7_g1", "a7", "a2_theory", "a3", "rr_renew", "marking", "bl5_lag")

style.register_supplementary(NAME, WIDTH, HEIGHT)


def _sig3(v: float, up: bool) -> str:
    """`v` rounded outward (up or down) to three significant digits, with thousands separators (2601.6 -> '2,600'
    down, 3727.5 -> '3,730' up), so that a stated range contains the values it summarizes."""
    if v == 0:
        return "0"
    q = 10.0 ** (math.floor(math.log10(abs(v))) - 2)
    r = (math.ceil(v / q - 1e-9) if up else math.floor(v / q + 1e-9)) * q
    return f"{r:,.0f}" if abs(r) >= 1 else f"{r:.3g}"


def _same(u, v) -> bool:
    return all(abs(a - b) <= 1e-12 * max(1.0, abs(b)) for a, b in zip(u, v))


def _envelope(inp: Inputs, inst: str, mode: str) -> dict:
    names = inp.glob(f"{RUN_DIR}/{inst}/core/{mode}/BL5-G_c0_*.json")
    if len(names) != SEEDS:
        raise style.StyleError(f"{inst} {mode}: {len(names)} BL5-G run files, expected {SEEDS} (p0-p9)")
    vals, seeds = [], []
    for n in names:
        run = inp.json(n)
        if run["meta"]["policy"] != "A8":
            raise style.StyleError(f"{n} is not an A8 run")
        c = run["q44"]["certificate"]
        vals.append(float(c["cor_G3_rhs"]) / float(run["q44"]["opt"]))
        seeds.append(run["q44"]["seeds"]["policy"])
    if sorted(seeds) != list(range(SEEDS)):
        raise style.StyleError(f"{inst} {mode}: policy seeds {sorted(seeds)} are not 0-{SEEDS - 1}")
    return {"mean": float(np.mean(vals)), "per_seed": vals, "seeds": seeds, "run_files": names}


def collect(inp: Inputs) -> dict:
    S = inp.json(SUMMARY)
    fams = S["D5"]["families"]
    out = {"git_revision": S["meta"]["git_revision"], "all_modes": fams}
    off_labels = {}
    for p, (fam, flt, mode, xf, tags) in PANELS.items():
        keys = [k for k in fams[fam] if k.split(":")[0].endswith(flt) and k.endswith(":" + mode)]
        keys.sort(key=lambda k: fams[fam][k][xf])
        x = [fams[fam][k][xf] for k in keys]
        theory = []                  # the envelope's and the limit's values
        if p in ENVELOPE:
            env = [_envelope(inp, k.split(":")[0], mode) for k in keys]
            theory += [e["mean"] for e in env]
        if p == "c":
            limit = [fams[fam][k]["bounds"]["revocable_only_asymptote_a1rho1_over_a2"] for k in keys]
            theory += limit
        ser, coincide, near = {}, [], []
        for tag in tags + EXTRA_TAGS[p]:
            r = [fams[fam][k]["ratio"][tag] for k in keys]
            ser[TAG_KEY[tag]] = {"tag": tag, "x": x, "y": [v["mean"] for v in r], "min": [v["min"] for v in r],
                                 "max": [v["max"] for v in r], "runs": [v["runs"] for v in r], "ci_lo": None,
                                 "ci_hi": None, "ci_note": "means over the policy seeds p0-p9; no interval",
                                 "drawn": tag in tags}
        # a drawn series whose least value lies more than OFF_SCALE_DEC decades above every other drawn value (series,
        # envelope, limit) is drawn as off-scale markers at the top edge, named with its range
        other = {k: max(v["y"]) for k, v in ser.items() if v["drawn"]}
        off_scale = []
        for k, v in ser.items():
            rest = [m for j, m in other.items() if j != k] + theory
            if v["drawn"] and rest and np.log10(min(v["y"]) / max(rest)) > OFF_SCALE_DEC:
                v["off_scale"] = True
                off_scale.append(k)
                off_labels.setdefault(p, {})[k] = (f"{style.POLICIES[k].label}, {_sig3(min(v['y']), False)}–"
                                                   f"{_sig3(max(v['y']), True)}, off scale")
        # pairs equal on every point: the second is drawn as the first; the other pairs of drawn series are named in
        # the key, with their agreement, where they agree within one marker size on the panel's y axis (decided when
        # drawn)
        for a, b in PAIRS + NEAR_PAIRS:
            if not all(k in ser and ser[k]["drawn"] and not ser[k].get("off_scale") for k in (a, b)):
                continue
            eq = [_same([u], [v]) for u, v in zip(ser[a]["y"], ser[b]["y"])]
            if all(eq) and (a, b) in PAIRS:
                ser[b]["drawn"] = False
                ser[b]["coincides_with"] = a
                coincide.append([a, b])
            else:
                ag = agreement(ser[a]["y"], ser[b]["y"])
                if ag is None:                          # not given at the same points: no near pair, no key
                    continue
                near.append({"pair": [a, b], "equal_at": [xv for xv, e in zip(x, eq) if e],
                             "max_abs_log10_ratio": float(max(abs(np.log10(u / v))
                                                              for u, v in zip(ser[a]["y"], ser[b]["y"]))),
                             **ag})
        panel = {"family": fam, "mode": mode, "x_field": xf, "instances": keys, "x": x, "series": ser,
                 "coincide": coincide, "near": near, "off_scale": off_scale}
        if p in ENVELOPE:
            panel["envelope"] = {"x": x, "y": [e["mean"] for e in env], "per_seed": [e["per_seed"] for e in env],
                                 "run_files": [e["run_files"] for e in env]}
            out[f"envelope_{fam}"] = {"m": x, "mean": panel["envelope"]["y"],
                                      "per_seed": panel["envelope"]["per_seed"],
                                      "run_files": panel["envelope"]["run_files"]}
        if p == "c":
            panel["limit"] = limit
        out[p] = panel
    out["labels"] = {
        "a_x": r"$m$ (F1, $\rho=16$, adaptive)", "b_x": r"$m$ (F2, $\rho=16$, safe-site)",
        "c_x": r"$\rho_1$ (F3, $T=48$, eager)", "y": "ALG / OPT",
        # C47 (U46): the limit's arrow \longrightarrow, STIX's full-height arrow, as Fig. 3(c) draws the same label
        # (Liberation Sans' U+2192, which \to sets, sits low and small between T and infinity)
        "envelope": "core ratio bound", "limit": r"revocable-only limit, $T\longrightarrow\infty$",
        "envelope_of": style.POLICIES["bl5_g1"].label,            # C46: whose envelope (BL5-G's), for the caption
        "coincide": {f"{a}|{b}": KEY_SAME for a, b in PAIRS},
        "near": {p: {"|".join(n["pair"]): (KEY_SAME if n["within_pct"] == 0 else KEY_NEAR).format(
                     pct=n["within_pct"]) for n in out[p]["near"]} for p in PANELS},
        # the same with the policies' names, for the caption (C46)
        "coincide_names": {f"{a}|{b}": AGREE_SAME.format(a=style.POLICIES[a].label, b=style.POLICIES[b].label)
                           for a, b in PAIRS},
        "near_names": {p: {"|".join(n["pair"]): (AGREE_SAME if n["within_pct"] == 0 else AGREE_NEAR).format(
                           a=style.POLICIES[n["pair"][0]].label, b=style.POLICIES[n["pair"][1]].label,
                           pct=n["within_pct"]) for n in out[p]["near"]} for p in PANELS},
        "off_scale": off_labels,
        "status": {"G2_envelope": "PROVEN, audited (pathwise; the certificate of Lagged RetroRenting + one-way guard)",
                   "C3-P5": "PROVEN (the revocable-only limit, T -> infinity)",
                   "scope": "exact core instances of the families; ALG/OPT is the mean over 10 policy seeds"},
    }
    return out


# ---------------------------------------------------------------------------------------------------------------
def _forms(text: str) -> tuple[str, str, str]:
    """The forms of a key text, fewest lines first: on one line; broken before the tolerance; then also before the
    "≈" or "=" (the forms of common.agree_key)."""
    two = text.replace(" (within", "\n(within")
    return text, two, two.replace(" ≈ ", "\n≈ ", 1).replace(" = ", "\n= ", 1)


def _pair_handle(a: str, b: str):
    """A key entry's handle: the markers of a and b side by side (style.MarkerPair), a guarded configuration after
    the other policy (an inner policy before its guarded version, as style.guard_pair_handles draws a pair). C62: the
    markers alone (the legend row shows the lines; each half of a 2.4-em handle drew a stub of line on both sides of
    its marker, which read as a dash between the pair)."""
    keys = sorted((a, b), key=lambda k: style.policy(k).group == "guarded")
    return style.MarkerPair([Line2D([], [], **style.policy_kwargs(k, lines=False)) for k in keys])


def _key(ax, entries, at: str, top_pt: float = 0.0):
    """A frameless key in the upper left corner of `ax`, `top_pt` below the axes top (`at` "top"), or in its lower
    right corner ("bottom"), one entry per pair (a, b, text): the handle the pair's two samples (_pair_handle), the
    text in the first of its forms (_forms) that fits the panel. Returns the key (added to the axes) or None."""
    if not entries:
        return None
    from matplotlib.legend import Legend
    rc = style.mpl.rcParams
    handle_pt = (KEY_KW["handlelength"] + rc["legend.handletextpad"] + 2 * rc["legend.borderpad"]) * style.TICK_PT
    w = style.axes_rect_in(ax)[2] * style.BP_PER_IN
    texts = [next((f for f in _forms(t) if text_width_in(ax.figure, f) * style.BP_PER_IN + handle_pt <= w),
                  _forms(t)[-1]) for _, _, t in entries]
    corner = (0.0, 1.0 - top_pt / (style.axes_rect_in(ax)[3] * style.BP_PER_IN)) if at == "top" else (1.0, 0.0)
    leg = Legend(ax, [_pair_handle(a, b) for a, b, _ in entries], texts,
                 loc="upper left" if at == "top" else "lower right", bbox_to_anchor=corner, bbox_transform=ax.transAxes,
                 borderaxespad=0.0 if at == "top" else 0.2, handler_map=dict(style.PAIR_HANDLER_MAP), **KEY_KW)
    ax.add_artist(leg)
    return leg


def _scale(H: float, reserve: float, elems: list, low: tuple) -> tuple[float, float]:
    """(pt per decade, y bottom) of a log axis `H` pt high whose top `reserve` pt are kept free: each element (y, c),
    a value and the pt that it or its label reaches above it, ends below that reserve, and the lowest marker (y, r),
    of radius r, clears the x spine by GAP_PT (the bottom drops below 1 only for that)."""
    b = 1.0
    for _ in range(50):
        s = min((H - reserve - c) / np.log10(y / b) for y, c in elems)
        nb = min(1.0, low[0] / 10 ** ((low[1] + GAP_PT) / s))
        if abs(nb - b) <= 1e-12 * b:
            break
        b = nb
    return s, b


def _panel(ax, P: dict, lab: dict, p: str) -> list:
    """Panel `p`, with its key: every pair drawn once and every near pair within one marker size (C46: none is named
    beside the panel letter any more). Returns the key's entries (a, b, text) (C47: for the caption)."""
    ser = P["series"]
    shown = {k: v for k, v in ser.items() if v["drawn"] and not v.get("off_scale")}
    order = style.legend_order(shown)[::-1]                  # the guarded configurations last (on top)
    lines = [style.plot_policy(ax, k, shown[k]["x"], shown[k]["y"]) for k in order]
    style.log2_axis(ax, "x", ticks=P["x"])
    ax.set_xlim(P["x"][0] / 1.3, P["x"][-1] * 1.3)
    style.end_label_inside(ax)
    ax.set_xlabel(lab[f"{p}_x"])
    fig = ax.figure
    k_pt = style.BP_PER_IN / fig.dpi
    r = fig.canvas.get_renderer()
    H = style.axes_rect_in(ax)[3] * style.BP_PER_IN
    # the name on the first line, the range on the second (C46: the name, "RetroRenting-style, lagged", has a comma)
    off = {k: re.sub(r", (?=[0-9][0-9,.]*–)", ",\n", lab["off_scale"][p][k], count=1) for k in P["off_scale"]}
    radius = {k: 0.5 * style.policy(k).markersize + style.MARKER_EDGE_PT for k in shown}
    low = min(((min(v["y"]), radius[k]) for k, v in shown.items()), key=lambda t: t[0])
    exact = [(a, b, lab["coincide"][f"{a}|{b}"]) for a, b in P["coincide"]]
    near = []
    off_pt = sum(ARROW_PT[0] + GAP_PT + LINE_H_PT * (t.count("\n") + 1) + GAP_PT for t in off.values())
    while True:
        # the key holds the pairs drawn once that are not named beside the panel letter and the near pairs within
        # one marker size; the y scale keeps the off-scale row and a key at the top free of every element below them,
        # and is recomputed, from the key without near pairs up, until the near pairs within tolerance on it are those
        # in the key (more entries only compress the scale, so the set only grows, to the smallest key that names
        # every pair it brings together)
        entries = exact + [(n["pair"][0], n["pair"][1], lab["near"][p]["|".join(n["pair"])]) for n in near]
        key = _key(ax, entries, KEY_AT[p], off_pt)
        reserve = off_pt
        if key is not None and KEY_AT[p] == "top":
            reserve += key.get_window_extent(r).height * k_pt + GAP_PT
        elems = [(max(v["y"]), radius[k]) for k, v in shown.items()]
        if "limit" in P:
            elems.append((P["limit"][int(np.argmax(P["x"]))], 1.5 + LINE_H_PT))      # its label above its end
        env_label = None
        if "envelope" in P:
            e, i = P["envelope"], ENV_LABEL
            elems.append((max(e["y"]), 0.5))
            above = [v["y"][i] for v in shown.values() if v["y"][i] > e["y"][i]]
            # the envelope's label goes under its line at its point if no line ends above it there and the band down
            # to the lines within the label's width holds it on the resulting scale; else above the point, or above
            # the highest line there (A2 on F2)
            s_below, _ = _scale(H, reserve, elems, low)
            w_lab = text_width_in(fig, lab["envelope"]) * style.BP_PER_IN
            x_pt = [ax.transData.transform((xv, 1.0))[0] * k_pt for xv in e["x"]]
            band = min(np.log10(e["y"][j] / max(v["y"][j] for v in shown.values()))
                       for j in range(len(x_pt)) if x_pt[i] - w_lab <= x_pt[j]) * s_below
            if not above and band >= 1.5 + LINE_H_PT + max(radius.values()) + GAP_PT:
                env_label = ("below", e["y"][i])
            else:
                env_label = ("above", max([e["y"][i]] + above))
                elems.append((env_label[1], (ENV_LIFT_PT if above else 1.5) + LINE_H_PT))
        s, b = _scale(H, reserve, elems, low)
        if s <= 0:
            raise style.StyleError(f"{NAME} ({p}): the key leaves no room for the data")
        within = [n for n in P["near"] if n["max_abs_log10_ratio"] * s <= style.MARKER_PT]
        if len(within) == len(near):
            break
        near = within
        if key is not None:
            key.remove()
    top = b * 10 ** (H / s)
    ax.set_ylim(b, top)
    # labeled ticks at the decades, or at 1, 2 and 5 times them on an axis of under two decades, clear of the top
    mant = (1.0,) if np.log10(top / b) >= 2.0 else (1.0, 2.0, 5.0)
    ticks = [m * 10.0 ** k for k in range(0, int(np.floor(np.log10(top))) + 1) for m in mant]
    ticks = [t for t in ticks if b <= t and np.log10(top / t) * s >= TOP_TICK_PT]
    style.log_axis(ax, "y", ticks=ticks)
    # minor ticks only up to the highest labeled tick: none in the band above it, which holds the key; C62: at 2 and 5
    # times the decades where only the decades are labeled (no comb of eight per decade), none where 1, 2 and 5 are
    minor = MINOR_MANT if len(mant) == 1 else ()
    ax.yaxis.set_minor_locator(FixedLocator([m * 10.0 ** k for k in range(-1, int(np.log10(max(ticks))) + 1)
                                             for m in minor if b <= m * 10.0 ** k <= max(ticks)]))
    if env_label is not None:
        e = P["envelope"]
        side, y_lab = env_label
        lifted = side == "above" and y_lab > e["y"][ENV_LABEL]
        _, t = style.theory_line(ax, e["x"], e["y"], "upper", lab["envelope"], label_xy=(e["x"][ENV_LABEL], y_lab),
                                 dy=-1.5 if side == "below" else (ENV_LIFT_PT if lifted else None))
        if side == "below":
            t.set_verticalalignment("top")
    if "limit" in P:
        style.theory_line(ax, P["x"], P["limit"], "limit", lab["limit"])
    # off-scale series: up arrows in the series' color at the top edge, at every x, named with their range under them
    y_off = 0.0
    for k, t in off.items():
        v = ser[k]
        tr = offset_copy(ax.get_xaxis_transform(), fig=fig, y=-(y_off + 0.5 * ARROW_PT[0]), units="points")
        style.plot_policy(ax, k, v["x"], [1.0] * len(v["x"]), lines=False, marker=UP_ARROW, markersize=ARROW_PT[0],
                          markeredgewidth=ARROW_PT[1], markerfacecolor="none", transform=tr, clip_on=False)
        style.direct_label(ax, k, v["x"][0], 1.0, t, dx=-0.5 * ARROW_PT[0], dy=-(y_off + ARROW_PT[0] + GAP_PT),
                           ha="left", va="top", xycoords=("data", "axes fraction"))
        y_off += ARROW_PT[0] + GAP_PT + LINE_H_PT * (t.count("\n") + 1) + GAP_PT
    if key is not None and KEY_AT[p] == "bottom":            # its entries, inside its padding, cross no line
        bb = key.get_window_extent(r).padded(-style.mpl.rcParams["legend.borderpad"] * style.TICK_PT / k_pt)
        if any(ln.get_path().transformed(ln.get_transform()).intersects_bbox(bb, filled=False) for ln in lines):
            raise style.StyleError(f"{NAME} ({p}): the key in the lower right corner crosses a line")
    return entries


def draw(data: dict):
    lab = data["labels"]
    fig = style.new_figure(NAME)
    axes = style.panel_row(fig, (1, 1, 1), legend=2)
    keys = {}
    for ax, p in zip(axes, "abc"):
        keys[p] = _panel(ax, data[p], lab, p)
        ax.set_ylabel(lab["y"])
    style.panel_letters(axes)
    drawn = [k for p in "abc" for k, s in data[p]["series"].items() if s["drawn"]]
    style.legend_row(fig, [k for k in LEGEND if k in drawn], rows=2)
    # C47: the caption draft names the keys' pairs, which the panels decide on their final scales; it goes into the
    # extract with the data (style.save after draw), and a redraw from the extract writes the same text
    lab["caption"] = caption(data, keys)
    return fig


CAPTION = ("ALG / OPT on the exact core families of the guard study of Fig.~\\ref{{fig:guard}} (OPT exact; the mean "
           "over the {seeds} policy seeds): (a) F1, the adaptive-lender family of Theorem~\\ref{{thm:lower}}, at "
           "$\\rho=16$; (b) F2, the same family with $T=96$ under the oblivious safe-site lender "
           "(Theorems~\\ref{{thm:lower}} and~\\ref{{thm:public}}), at $\\rho=16$; (c) F3, the insurance family of "
           "Proposition~\\ref{{prop:insurance}}, at $T=48$ under the eager lender, with its revocable-only limit for "
           "$T\\to\\infty$. The dashed core ratio bound in (a) and (b) is that of {owner}: its per-run bound "
           "$(1+\\gamma)C_S(T)+\\kappa B_{{\\rm on}}(T)$, implied by Theorem~\\ref{{thm:envelope}}, over OPT, the "
           "mean over the seeds; it does not bound the other policies. Keys: {keys}.{off}")


def caption(data: dict, keys: dict) -> str:
    """labels.caption (C47): the caption draft, with each panel's key entries by the policies' names (pairs drawn once,
    labels.coincide_names; pairs within one marker size, labels.near_names) and the off-scale series."""
    lab = data["labels"]

    def tex(t: str) -> str:
        return t.replace("%", "\\%").replace("≈", "$\\approx$")

    parts = []
    for p in "abc":
        names = [lab["coincide_names"][f"{a}|{b}"] + " (drawn once)" if [a, b] in data[p]["coincide"]
                 else lab["near_names"][p][f"{a}|{b}"] for a, b, _ in keys[p]]
        if names:
            parts.append(f"({p}) " + "; ".join(tex(n) for n in names))
    off = [f" In ({p}), {style.POLICIES[k].label} lies off scale ({_sig3(min(data[p]['series'][k]['y']), False)}--"
           f"{_sig3(max(data[p]['series'][k]['y']), True)})." for p in "abc" for k in data[p]["off_scale"]]
    return CAPTION.format(seeds=SEEDS, owner=lab["envelope_of"], keys="; ".join(parts) if parts else "none",
                          off="".join(off))


def report(data: dict, rep: dict) -> None:
    print(f"[{NAME}] envelopes F1 {[round(v, 3) for v in data['a']['envelope']['y']]}, "
          f"F2 {[round(v, 3) for v in data['b']['envelope']['y']]}")


def main(argv=None) -> dict:
    return cli(NAME, collect, draw, argv, supplementary=True, after=report, doc=__doc__)


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
