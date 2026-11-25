"""Fig. 2: what notice costs a lender and what it buys the platform (design/figure_plan.md §1, Fig. 2;
design/sim_spec_ms3.md §8.2 and E1(a), §4.2).

(a) Measurement L7 (no theorem): the P99 notice buffer as a share of mean lendable capacity against the window D
(the 9 windows of a9b), from code/analysis/out/a9b_notice_buffer_24h.json: the MaaS median over the 20 clusters
with a min-max band (solid), the four spot pools of L7 as dashed grey-level lines with a marker each (figure_plan §5:
MaaS solid, spot dashed), and a reference line at 100%, the mean lendable capacity (above it the contract cannot be
offered).

(b) E1(a), the calibrated rho, from code/analysis/out/a11_calibration.json: for tier t, load scenario s, lender l
(the 20 MaaS clusters and the four L7 spot pools) and 5-min contract k with an IR multiplier,
    rho = 1 + (1 + phi / alpha_lk) lambda_ts / (60 D_pd,k),   alpha_lk = a0 * ir_multiplier_lk / q_GPU
(a11's field_sources.rho). The points are aggregated per (tier, scenario, D_pd) (M32): a marker at the median over
the lenders and the contracts with that D_pd (with a thin dark edge, so that stacked markers near rho = 1 keep their
shapes) and a min-max bar in a lighter tone of the point's color, named in the key ("Median, min-max"). The load
scenarios are ordered by their tier-M load time (a11's load_time_s.maas_a10.M), in the reversed cividis ramp: the
fastest load is the lightest and the slowest, whose points lie above rho = 2, the darkest; the scenario bar lists them
from the fastest at the bottom to the slowest at the top (b.scenario_order and labels.b_scen_order in the extract).
Tier L is a diamond, not a triangle: its medians lie near the top of their ranges (most lenders at the largest rho),
and a triangle on its bar read as an upward arrow. The line rho = 2 is a threshold, not a bound: the leading factor
of C3-Cor3 (PROVEN) is 2 once H_k >= H*_beta. Check E1-1 (§4.6): at the price reference maas_p99_median the script's
rho equals a11's rows.maas_a10.<t>.<s>.by_contract.<k>.rho to 1e-12 relative; the script fails otherwise. The shares
of points with rho <= 2, over all points and over the default scenario pair (meta.default_scenarios), are printed and
stored in the extract.

C52 (design/ms7/plan.md §4, unit T1: the manuscript scan): the load scenarios of (b) carry their units (SCENARIO_SHORT:
"WAN 1 Gb/s", "WAN 10 Gb/s", "Load 2 GB/s", "Load 10 GB/s"); for the longer labels the right margin of both panels
grew to 0.20 in, the colorbar moved to 0.748 of (b)'s width (0.029 wide), and (a)'s pool legend took a column spacing
of 0.6 em (all three at 9 pt; C62 below replaces them).

C62 (2026-11-24: no text larger than the caption, 7-pt ticks, keys and labels, 7.97-pt axis labels and
letters; the figures high-end, informative and readable), the layout redrawn for the smaller text, every plotted value
and the extract's data unchanged:
- (a) takes A_SHARE of the two axes' heights and the y range A_YLIM = 0.07-600%, one decade less than at 9 pt
  (0.01-400%), whose lowest decade held only the MaaS label and the pool legend: the spot pools are named in one key
  row above the axes on the panel letter's baseline (key_a), which costs no height, and MaaS is labeled inside its
  band, above the median line, where the band is wide (maas_label). The 100% line is named "Mean capacity"
  (labels.a_ref) above its left end, where every spot pool is below it, in the reference-label grey of the other
  figures.
- (b)'s key (one entry per tier, a marker on its min-max bar, under the title "Median, min-max") moves from a row
  above the axes into the empty upper part of the panel (key_b; the entry "Median, min-max" with Tier L's diamond read
  as a fourth tier), so the gap between the panels holds only (b)'s letter (GAP_AB 0.14 in, 0.20 at 9 pt). The
  scenario colorbar becomes a bar of discrete cells split by white rules, with no outline; its left end follows from
  its measured labels, which end at the axes' right end (scenario_bar_x0), and the right margin returns to
  style.MARGIN_RIGHT. The label of rho = 2 is set in the reference-label grey.
- Labels and keys placed among the data are checked against it (check_clear: the label of the 100% line against
  the pools, the tier key and the label of rho = 2 against (b)'s markers and bars; maas_label against the median line
  and the band's top; scenario_bar_x0 against the rightmost marker): the script fails rather than set text on data.
- (b)'s markers are B_MARKER_PT (3.0 pt, style.MARKER_PT 3.5) with MEDIAN_EDGE_PT edges: 360 medians, most of them
  in the band rho = 1-1.5 at 60-125 min. Each entry of the tier key is a marker on its own min-max bar: the bars fill
  the rows' measured pitch less KEY_BAR_GAP_PT (key_b), so that the three bars no longer join into one range across
  the tiers, and each shows at least KEY_STEM_PT beyond its marker.
- (a)'s log y axis has no minor ticks, as the x axes and (b)'s y axis: eight per 0.24-in decade made a comb
  along the spine. The label of rho = 2 ends REF_LABEL_PT[0] short of the line's end, as (a)'s label starts that far in.
- The panels' heights follow the registered height (draw); at 2.5 in every check above still passes (the figure is
  registered at 2.7 in: (b)'s dense band needs it).

Run from code/sim: ``python -m figs.fig2_e1a [--from-extract [JSON]]`` (figs.common.cli).
"""
from __future__ import annotations

import sys

import numpy as np
from matplotlib import colors as mcolors
from matplotlib.cm import ScalarMappable
from matplotlib.font_manager import FontProperties
from matplotlib.legend_handler import HandlerBase
from matplotlib.lines import Line2D
from matplotlib.ticker import NullLocator
from matplotlib.transforms import Bbox

from figs import style
from figs.common import cli
from figs.inputs import Inputs

NAME = "fig2"
A9B = "code/analysis/out/a9b_notice_buffer_24h.json"
A11 = "code/analysis/out/a11_calibration.json"
CATALOG = "maas_a10"
TIERS = ("S", "M", "L")
PRICE_REF = "maas_p99_median"
E1_1_TOL = 1e-12
KEYS = ()                                   # FIGURE_POLICIES["fig2"]: no policy series
# short names of the load scenarios (sim_spec_ms3 §8.2, in sentence case), in a11's key order of
# load_time_s.maas_a10.M (collect_b sorts the scenarios by load time); C52 (design/ms7/plan.md §4, T1 scan): each rate
# with its unit, the WAN line rates in Gb/s and the a5 pair's weight-load rates (plus the 60 s engine start) in GB/s
# named "Load", so that "WAN 10 Gb/s" (1.25 GB/s, 48 s at tier M) and "Load 10 GB/s" (66 s) no longer read as one
# rate (as built "WAN 10G", "WAN 1G", "10 GB/s" and "2 GB/s")
SCENARIO_SHORT = {"warm_peer_rdma": "Warm peer", "ssd_optimized": "SSD opt.", "ssd_stock_safetensors": "SSD st.",
                  "ssd_stock_pytorch": "SSD pt.", "a5_10GBps": "Load 10 GB/s", "a5_2GBps": "Load 2 GB/s",
                  "cold_wan_10gbps": "WAN 10 Gb/s", "cold_wan_1gbps": "WAN 1 Gb/s"}                     # C52
POOL_SHORT = {"a1:A100-SXM4-80GB": "A100", "a1:A800-SXM4-80GB": "A800", "a1:GPU-series-2": "Series 2",
              "a1:H800": "H800"}
TIER_MARKERS = {"S": "o", "M": "s", "L": "D"}
DODGE = {"S": 0.94, "M": 1.0, "L": 1.06}
ORDER_TIER = "M"                            # (b): the scenarios are ordered by this tier's load time


def rho(lam_s: float, d_pd_min: float, a0: float, mult: float, q_gpu: float, phi: float) -> float:
    """a11's rho = 1 + f lambda / D_pd with f = 1 + phi / alpha, alpha = a0 * multiplier / q_GPU (lambda in s)."""
    alpha = a0 * mult / q_gpu
    return 1.0 + (1.0 + phi / alpha) * lam_s / (60.0 * d_pd_min)


# ---------------------------------------------------------------------------------------------------------------
def collect_a(inp: Inputs) -> dict:
    d = inp.json(A9B)
    windows = [int(w) for w in d["meta"]["windows_min"]]
    q = d["meta"]["default_quantile"]
    maas = d["summary"]["maas_20_clusters"]["windows"]
    pools = list(d["summary"]["spot_4_pools_L7"]["lenders"])
    return {
        "windows_min": windows,
        "quantile": q,
        "maas": {"lenders": len(d["summary"]["maas_20_clusters"]["lenders"]),
                 "median": [maas[str(w)][q]["median_b"] for w in windows],
                 "min": [maas[str(w)][q]["min_b"] for w in windows],
                 "max": [maas[str(w)][q]["max_b"] for w in windows]},
        "pools": {p: {"label": POOL_SHORT.get(p, p.split(":", 1)[-1]),
                      "b": [d["lenders"][p]["windows"][str(w)]["b"][q] for w in windows]} for p in pools},
    }


def collect_b(inp: Inputs) -> dict:
    d = inp.json(A11)
    I = d["inputs"]
    a0, q_gpu, phi = float(I["a0"]), float(I["q_GPU"]), float(I["phi"])
    lenders = list(I["maas_lenders"]) + list(I["spot_L7_lenders"])
    contracts = [k for k, c in d["contracts"].items() if c.get("slot_min") == d["meta"]["default_slot_min"]
                 and k != "protected"]
    lam = d["load_time_s"][CATALOG]
    # the scenarios by ascending load time of ORDER_TIER (ties keep a11's order): the order of (b)'s ramp and colorbar
    scen = sorted(lam[ORDER_TIER], key=lambda s: float(lam[ORDER_TIER][s]))
    dpd = {k: float(d["contracts"][k]["D_pd_min"]) for k in contracts}
    # E1-1: rho at the price reference maas_p99_median against a11's rows
    errs = []
    for t in TIERS:
        for s in scen:
            for k in contracts:
                mult = float(d["contracts"][k]["price_refs"][PRICE_REF]["multiplier"])
                mine = rho(float(lam[t][s]), dpd[k], a0, mult, q_gpu, phi)
                ref = float(d["rows"][CATALOG][t][s]["by_contract"][k]["rho"])
                errs.append(abs(mine - ref) / abs(ref))
    e1_1 = {"check": "E1-1", "price_ref": PRICE_REF, "n": len(errs), "max_rel_err": max(errs),
            "tol": E1_1_TOL, "pass": max(errs) <= E1_1_TOL}
    if not e1_1["pass"]:
        raise style.StyleError(f"check E1-1 failed: max relative error {max(errs):.3g} > {E1_1_TOL:g}")
    # every point (tier, scenario, lender, contract) with an IR multiplier at P99
    pts = []
    for t in TIERS:
        for s in scen:
            for ell in lenders:
                pc = d["ir_prices_by_lender"][ell]["contracts"]
                for k in contracts:
                    mult = pc[k]["ir_multiplier"]["p99"]
                    if mult is None:
                        continue
                    pts.append((t, s, ell, k, dpd[k], rho(float(lam[t][s]), dpd[k], a0, float(mult), q_gpu, phi)))
    default = list(d["meta"]["default_scenarios"])
    r_all = np.array([p[5] for p in pts])
    r_def = np.array([p[5] for p in pts if p[1] in default])
    shares = {"all": {"n": int(r_all.size), "n_le_2": int((r_all <= 2.0).sum()),
                      "share": float((r_all <= 2.0).mean())},
              "default_scenarios": {"scenarios": default, "n": int(r_def.size), "n_le_2": int((r_def <= 2.0).sum()),
                                    "share": float((r_def <= 2.0).mean())}}
    agg = []
    for t in TIERS:
        for s in scen:
            for D in sorted(set(dpd.values())):
                v = np.array([p[5] for p in pts if p[0] == t and p[1] == s and p[4] == D])
                if v.size:
                    agg.append({"tier": t, "scenario": s, "D_pd": D, "median": float(np.median(v)),
                                "min": float(v.min()), "max": float(v.max()), "n": int(v.size)})
    return {"points": agg, "scenarios": scen, "scenario_short": [SCENARIO_SHORT.get(s, s) for s in scen],
            "scenario_order": {"by": f"load_time_s.{CATALOG}.{ORDER_TIER}", "order": "ascending",
                               "load_time_s": [float(lam[ORDER_TIER][s]) for s in scen]},
            "tiers": list(TIERS), "dodge": [DODGE[t] for t in TIERS], "shares_rho_le_2": shares, "E1_1": e1_1,
            "inputs": {"a0": a0, "q_GPU": q_gpu, "phi": phi, "lenders": lenders, "contracts": contracts,
                       "catalog": CATALOG, "quantile": "p99"}}


def collect(inp: Inputs) -> dict:
    a, b = collect_a(inp), collect_b(inp)
    return {"a": a, "b": b, "labels": {
        "x": "Window $D$ (min)",
        "a_y": "P99 buffer (%)",
        "a_maas": "MaaS (median, range)",
        "a_ref": "Mean capacity",                                                              # C62
        "b_y": r"Calibrated $\rho$",
        "b_ref": r"$\rho=2$",
        "b_range": "Median, min–max",
        "b_tiers": {t: f"Tier {t}" for t in TIERS},
        "b_scen_order": f"Load scenarios ordered by tier-{ORDER_TIER} load time, from the fastest (lightest, bottom of "
                        "the color bar) to the slowest (darkest, top)",
        "a_y_long": "P99 notice buffer as a share of mean lendable capacity (%)",
        "status_b": "rho = 2 is the leading factor of C3-Cor3 (PROVEN) once H_k >= H*_beta; a threshold, not a bound",
        "status_a": "Measurement L7 (no theorem); the MaaS series cover one week",
    }}


# ---------------------------------------------------------------------------------------------------------------
# Layout (C62: 7-pt ticks, legends and labels, 7.97-pt axis labels and letters; the constants that hold text were
# measured at that scale, as built at 9 pt before C62 in the comments)
X_LIM = (4.2, 1700.0)
A_SHARE = 0.46                              # (a)'s share of the two axes' heights, (b) takes the rest: at 2.7 in
                                            # 0.95 and 1.11 in (at 9 pt (a) 0.85 in and (b) the rest, 1.10 in)
GAP_AB = 0.14                               # (a)'s axes bottom to (b)'s top (in): (b)'s bold letter (7.2 pt high,
                                            # baseline 1.2 pt above (b)) ends 3.1 pt below (a)'s axes and 1.5 pt
                                            # below (a)'s lowest tick label, 6 pt left of it (at 9 pt 0.20 in, which
                                            # also held (b)'s key row)
RIGHT_IN = style.MARGIN_RIGHT               # right margin of both panels (in): the centered 7-pt "1440" ends 2.6 pt
                                            # inside the page (at 9 pt 0.20 in, for the colorbar's 9-pt labels)
A_YLIM = (0.07, 600.0)                      # (a)'s y range (%): just below the band's lowest point, and room above
                                            # 100% for the reference line's label (at 9 pt 0.01-400, with the MaaS
                                            # label and the pool key below the band)
MAAS_LABEL_X = 120.0                        # (a): the MaaS label starts at this window (min), where the band is wide
MAAS_LABEL_CLEAR_PT = 1.5                   # least gap from the MaaS label to the median line and the band's top
A_LEGEND_COLSPACE = 1.0                     # (a)'s pool key, column spacing (em; at 9 pt 0.6)
CBAR_W_IN = 0.085                           # (b)'s scenario bar: width (in); its labels end at the axes' right end
CBAR_PAD_PT = 2.0                           # (b)'s scenario bar: gap from the bar to its labels
CBAR_CLEAR_IN = 0.05                        # least gap from the rightmost marker's edge to the scenario bar; draw_b
                                            # fails if the measured labels leave less
CBAR_INSET_IN = 0.03                        # the scenario bar spans (b)'s full height less this at both ends
DIVIDER_PT = 0.8                            # white rule between two scenarios' cells of the bar (no outline)
KEY_X = 52.0                                # (b)'s tier key: left end at this window (min), right of the last
                                            # point above rho = 5 (tier L at D_pd = 35 min, dodged to 37 min)
CLEAR_PT = 1.5                              # least gap from a label or key placed on a panel to the series it must
                                            # not cover (markers, lines, bars); checked, the script fails otherwise
RANGE_TONE = 0.7                            # (b): a bar keeps this share of its color's distance from white (at 0.5
                                            # the bars of the lightest scenarios nearly vanish in greyscale print)
MEDIAN_EDGE, MEDIAN_EDGE_PT = "#333333", 0.4  # (b): dark edge of the median markers, so that the stacked light markers
                                            # near rho = 1 keep their shapes (a white edge cut them into chevrons)
KEY_GREY = "#4D4D4D"                        # (b)'s tier key: face of the tier markers
LETTER_GAP_PT = 2.0                         # (a): least gap from its y label's top end to the panel letter
REF_LABEL_PT = (2.0, 1.5)                   # offset (pt) of a reference line's label from the line's end (inward)
B_MARKER_PT = 3.0                           # (b)'s median markers (style.MARKER_PT 3.5 elsewhere): most of the 360
                                            # medians lie in the band rho = 1-1.5 at 60-125 min
KEY_ROW_EM = 0.5                            # (b)'s tier key: spacing of its rows (em; 0.25 left no room for the bars)
KEY_BAR_GAP_PT = 2.0                        # (b)'s tier key: gap between two entries' min-max bars, and from the top
                                            # bar to the title's baseline
KEY_STEM_PT = 1.0                           # (b)'s tier key: least length of a bar beyond its marker, at both ends


def _x_axis(ax, labels: bool) -> None:
    style.log_axis(ax, "x", ticks=[5, 15, 30, 60, 120, 240, 480, 1440])
    ax.xaxis.set_minor_locator(NullLocator())   # a minor tick at 500 read as a doubled 480 tick
    ax.set_xlim(*X_LIM)
    if labels:
        style.end_label_inside(ax)
    else:
        ax.tick_params(axis="x", labelbottom=False)


# (a): a marker per spot pool, so that the pools, whose grey levels are close and whose lines cross, stay apart in a
# greyscale print (IEEE: "a thick line with a unique data point symbol"); shapes that (b)'s tiers do not use
POOL_MARKERS = ({"marker": "^", "markerfacecolor": "white"}, {"marker": "v"}, {"marker": "x"},
                {"marker": "<", "markerfacecolor": "white"})
POOL_MARKER_PT = 3.0
POOL_GREYS = ("#333333", "#9A9A9A")         # (a): the spot pools' greys, darkest to lightest, even steps: the
                                            # lightest stays clearly darker than the 100% reference line (#BDBDBD)


def pool_greys(n: int) -> list[str]:
    """n greys in even steps from POOL_GREYS[0] to POOL_GREYS[1] (the spot pools of (a))."""
    lo, hi = (np.asarray(mcolors.to_rgb(c)) for c in POOL_GREYS)
    return [mcolors.to_hex(lo + (hi - lo) * f) for f in (np.linspace(0.0, 1.0, n) if n > 1 else [0.0])]


def _reference_label(ax, text: str, xy, xycoords, *, ha: str, dx: float, dy: float):
    t = ax.annotate(text, xy=xy, xycoords=xycoords, xytext=(dx, dy), textcoords="offset points", ha=ha,
                    va="bottom", fontsize=style.TICK_PT, color=style.THEORY_LABEL_GREY, zorder=style.Z_REFERENCE)
    t._sublet_role = "reference_label"
    return t


def _polyline(ax, x, y, n: int = 24) -> np.ndarray:
    """Display points along the series (x, y) as drawn on `ax`: straight between its points in display space."""
    P = ax.transData.transform(np.column_stack([np.asarray(x, dtype=float), np.asarray(y, dtype=float)]))
    t = np.linspace(0.0, 1.0, n)[1:, None]
    return np.vstack([P[:1]] + [p + (q - p) * t for p, q in zip(P[:-1], P[1:])])


def check_clear(artist, paths, pad_pt: float, what: str) -> None:
    """Fail if any display point of `paths` lies within `pad_pt` of the window extent of `artist` (a label or key
    placed on the data; a list of artists: the union of their extents)."""
    arts = list(artist) if isinstance(artist, (list, tuple)) else [artist]
    fig = arts[0].get_figure(root=True)
    r = fig.canvas.get_renderer()
    bb = Bbox.union([a.get_window_extent(r) for a in arts])
    pad = pad_pt * fig.dpi / style.BP_PER_IN
    for P in paths:
        hit = (P[:, 0] > bb.x0 - pad) & (P[:, 0] < bb.x1 + pad) & (P[:, 1] > bb.y0 - pad) & (P[:, 1] < bb.y1 + pad)
        if hit.any():
            raise style.StyleError(f"fig2: {what} comes closer than {pad_pt:.2f} pt to the data it labels around")


def marker_half_pt(marker: str, size: float = B_MARKER_PT) -> float:
    """Half the extent (pt) of one of (b)'s median markers, its edge included: 'D' is a square of side `size` turned
    45 degrees, so its half diagonal is size / sqrt(2)."""
    return (size / np.sqrt(2.0) if marker == "D" else 0.5 * size) + 0.5 * MEDIAN_EDGE_PT


def b_marker_half_pt() -> float:
    """The largest half extent of (b)'s median markers (pt): the pad that the clearance checks of (b) add."""
    return max(marker_half_pt(m) for m in TIER_MARKERS.values())


def _b_paths(ax, data: dict) -> list:
    """(b)'s points as display paths: each min-max bar, and each median marker."""
    b = data["b"]
    dodge = dict(zip(b["tiers"], b["dodge"]))
    out = []
    for p in b["points"]:
        x = p["D_pd"] * dodge[p["tier"]]
        out.append(_polyline(ax, [x, x], [p["min"], p["max"]]))
        out.append(ax.transData.transform([(x, p["median"])]))
    return out


def draw_a(ax, data: dict, lab: dict) -> list:
    """(a)'s series; returns the (handle, label) pairs of the spot pools for key_a."""
    a = data["a"]
    W = np.asarray(a["windows_min"], dtype=float)
    dark = style.ramp(5, "greys")[0]
    m = a["maas"]
    med = 100 * np.asarray(m["median"])
    ax.fill_between(W, 100 * np.asarray(m["min"]), 100 * np.asarray(m["max"]), color=dark,
                    alpha=style.BAND_ALPHA, linewidth=0, zorder=1.9)
    ax.plot(W, med, color=dark, linewidth=style.LINE_PT, linestyle=style.env_linestyle("lender", "maas"), zorder=2.2)
    handles = []
    if len(a["pools"]) > len(POOL_MARKERS):
        raise ValueError(f"{len(a['pools'])} spot pools, markers for {len(POOL_MARKERS)}")
    greys = pool_greys(len(a["pools"]))
    for (p, v), mk, g in zip(a["pools"].items(), POOL_MARKERS, greys):
        kw = dict(color=g, linewidth=style.LINE_PT, linestyle=style.env_linestyle("lender", "spot"),
                  markersize=POOL_MARKER_PT, markeredgewidth=style.MARKER_EDGE_PT, markeredgecolor=g, **mk)
        ax.plot(W, 100 * np.asarray(v["b"]), zorder=2.0, **kw)
        handles.append((Line2D([], [], **kw), v["label"]))
    style.reference_line(ax, y=100.0)
    style.log_axis(ax, "y", ticks=[0.1, 1, 10, 100])
    ax.yaxis.set_minor_locator(NullLocator())   # C62: eight minor ticks per 0.24-in decade made a comb on the spine
    lo_hi = [100 * min(m["min"]), 100 * max(max(m["max"]), *(max(v["b"]) for v in a["pools"].values()))]
    if not (A_YLIM[0] < lo_hi[0] and lo_hi[1] < A_YLIM[1]):
        raise style.StyleError(f"fig2 (a): the series span {lo_hi} %, outside the y range {A_YLIM}")
    ax.set_ylim(*A_YLIM)
    _x_axis(ax, labels=False)
    ax.set_ylabel(lab["a_y"])
    # the 100% line (the buffer equals the mean lendable capacity) is named above its left end, where every spot pool
    # is still below it
    ref = _reference_label(ax, lab["a_ref"], (0.0, 100.0), ("axes fraction", "data"), ha="left", dx=REF_LABEL_PT[0],
                           dy=REF_LABEL_PT[1])
    check_clear(ref, [_polyline(ax, W, 100 * np.asarray(v["b"])) for v in a["pools"].values()],
                CLEAR_PT + 0.5 * POOL_MARKER_PT, "the label of the 100% line")
    maas_label(ax, data, lab, dark)
    return handles


def maas_label(ax, data: dict, lab: dict, color: str):
    """MaaS's direct label inside its band, above the median line, from the window MAAS_LABEL_X on: centered (in log)
    between the highest median and the lowest band maximum under the label's span. Fails if the label then comes
    closer than MAAS_LABEL_CLEAR_PT to the median line or the band's top edge."""
    m = data["a"]["maas"]
    W = np.asarray(data["a"]["windows_min"], dtype=float)
    lo, hi = 100 * np.asarray(m["median"]), 100 * np.asarray(m["max"])
    fig = ax.figure
    r = fig.canvas.get_renderer()
    t = ax.text(MAAS_LABEL_X, 1.0, lab["a_maas"], ha="left", va="center", fontsize=style.TICK_PT, color=color,
                zorder=2.3)
    t._sublet_role = "direct_label"
    bb = t.get_window_extent(r)
    inv = ax.transData.inverted()
    x1 = inv.transform((bb.x1, bb.y0))[0]
    lw, xw = np.log10(W), np.log10([MAAS_LABEL_X, x1])
    grid = np.linspace(xw[0], xw[1], 64)
    med_top = 10 ** np.interp(grid, lw, np.log10(lo)).max()
    band_top = 10 ** np.interp(grid, lw, np.log10(hi)).min()
    y = float(np.sqrt(med_top * band_top))
    t.set_y(y)
    bb = t.get_window_extent(r)
    y0, y1 = inv.transform((bb.x0, bb.y0))[1], inv.transform((bb.x0, bb.y1))[1]
    pt = fig.dpi / style.BP_PER_IN
    below = (ax.transData.transform((MAAS_LABEL_X, y0))[1] - ax.transData.transform((MAAS_LABEL_X, med_top))[1]) / pt
    above = (ax.transData.transform((MAAS_LABEL_X, band_top))[1] - ax.transData.transform((MAAS_LABEL_X, y1))[1]) / pt
    if min(below, above) < MAAS_LABEL_CLEAR_PT:
        raise style.StyleError(f"fig2 (a): the MaaS label is {below:.1f} pt above the median line and {above:.1f} pt "
                               f"below the band's top, less than {MAAS_LABEL_CLEAR_PT} pt")
    return t


def key_a(ax, letter, handles: list):
    """(a)'s key of the spot pools: one row above the axes on the baseline of the panel letter, its right end at the
    axes' right end, the handles long enough to show the dashes on both sides of the marker."""
    fig = ax.figure
    r = fig.canvas.get_renderer()
    h, t = zip(*handles)
    # without border padding the legend's bottom is its text's descent line ("lp", as matplotlib lays text out):
    # anchored that far below the letter's baseline (inches), the key's text shares the letter's baseline
    _, _, descent = r.get_text_width_height_descent("lp", FontProperties(size=style.TICK_PT), ismath=False)
    x0, _, w, _ = style.axes_rect_in(ax)
    base_in = letter.get_position()[1] * fig.get_size_inches()[1]
    return ax.legend(list(h), list(t), loc="lower right", bbox_to_anchor=(x0 + w, base_in - descent / fig.dpi),
                     bbox_transform=fig.dpi_scale_trans, ncol=len(h), frameon=False, borderpad=0.0,
                     borderaxespad=0.0, handlelength=1.8, handletextpad=0.3, columnspacing=A_LEGEND_COLSPACE)


def range_tone(color: str, keep: float = RANGE_TONE) -> str:
    """`color` mixed with white, keeping the share `keep` of its distance from white (the min-max bars of (b))."""
    rgb = np.asarray(mcolors.to_rgb(color))
    return mcolors.to_hex(1.0 - (1.0 - rgb) * keep)


class RangeKey(HandlerBase):
    """Legend handle of (b)'s encoding: a vertical min-max bar in the range tone with the median marker on it. The bar
    is drawn with no length; key_b sets it from the rows' measured pitch once the key is laid out (the handle's
    coordinates are points). (As first built at C62 each bar reached 0.35 of the handle's height past its box at
    both ends, and the three bars joined into one line from above Tier S to below Tier L.)"""

    def __init__(self, marker: str, color: str):
        super().__init__()
        self.marker, self.color = marker, color
        self.bar = self.dot = None

    def create_artists(self, legend, orig_handle, xdescent, ydescent, width, height, fontsize, trans):
        x, y = 0.5 * width - xdescent, 0.5 * height - ydescent
        self.bar = Line2D([x, x], [y, y], color=range_tone(self.color), linewidth=style.UNCERTAINTY_PT,
                          solid_capstyle="butt", transform=trans)
        self.dot = Line2D([x], [y], linestyle="none", marker=self.marker, markersize=B_MARKER_PT,
                          markerfacecolor=self.color, markeredgecolor=MEDIAN_EDGE, markeredgewidth=MEDIAN_EDGE_PT,
                          transform=trans)
        return [self.bar, self.dot]


def _text_width_in(fig, s: str, size: float) -> float:
    r = fig.canvas.get_renderer()
    return r.get_text_width_height_descent(s, FontProperties(size=size), ismath=False)[0] / fig.dpi


def scenario_bar_x0(ax, data: dict) -> float:
    """Left end of (b)'s scenario bar (axes fraction), so that its widest label ends at the axes' right end; fails if
    the bar comes closer than CBAR_CLEAR_IN to the edge of the rightmost marker."""
    fig = ax.figure
    b = data["b"]
    _, _, w, _ = style.axes_rect_in(ax)
    lab_w = max(_text_width_in(fig, s, style.TICK_PT) for s in b["scenario_short"])
    x0_in = w - lab_w - CBAR_PAD_PT / style.BP_PER_IN - CBAR_W_IN
    xs = [p["D_pd"] * d for p in b["points"] for t, d in zip(b["tiers"], b["dodge"]) if p["tier"] == t]
    right_in = (ax.transData.transform((max(xs), 1.0))[0] - ax.transAxes.transform((0.0, 0.0))[0]) / fig.dpi
    clear = x0_in - right_in - b_marker_half_pt() / style.BP_PER_IN
    if clear < CBAR_CLEAR_IN - 1e-9:
        raise style.StyleError(f"fig2 (b): the scenario bar is {clear:.3f} in clear of the rightmost marker, less "
                               f"than {CBAR_CLEAR_IN} in")
    return x0_in / w


def draw_b(ax, data: dict, lab: dict) -> float:
    b = data["b"]
    scen = b["scenarios"]                   # by ascending tier-M load time (collect_b)
    cols = style.ramp(len(scen), "cividis")[::-1]   # reversed: the fastest load the lightest, the slowest the darkest
    cmap = {s: c for s, c in zip(scen, cols)}
    dodge = dict(zip(b["tiers"], b["dodge"]))
    # each point's min-max bar in a lighter tone of its color, under its median marker with a thin dark edge; the
    # slowest scenario first, so that where markers stack near rho = 1 the fast (light) ones lie on top
    rank = {s: i for i, s in enumerate(scen)}
    for p in sorted(b["points"], key=lambda p: -rank[p["scenario"]]):
        x = p["D_pd"] * dodge[p["tier"]]
        c = cmap[p["scenario"]]
        ax.plot([x, x], [p["min"], p["max"]], color=range_tone(c), linewidth=style.UNCERTAINTY_PT, zorder=1.9,
                solid_capstyle="butt")
        ax.plot([x], [p["median"]], linestyle="none", marker=TIER_MARKERS[p["tier"]], markersize=B_MARKER_PT,
                markerfacecolor=c, markeredgecolor=MEDIAN_EDGE, markeredgewidth=MEDIAN_EDGE_PT, zorder=2.0)
    style.log2_axis(ax, "y", ticks=[1, 2, 4, 8, 16, 32])
    ymax = max(p["max"] for p in b["points"])
    ax.set_ylim(0.92, ymax * 2 ** 0.2)
    _x_axis(ax, labels=True)
    ax.set_xlabel(lab["x"])
    ax.set_ylabel(lab["b_y"])
    x0 = scenario_bar_x0(ax, data)
    # the threshold rho = 2 ends 0.03 in short of the scenario bar; its label sits above the line, ending
    # REF_LABEL_PT[0] short of the line's right end (C62: at 0 it ended 2.8 pt from the bar)
    gap = 0.03 / style.axes_rect_in(ax)[2]
    style.reference_line(ax, y=2.0, xmax=x0 - gap)
    ref = _reference_label(ax, lab["b_ref"], (x0 - gap, 2.0), ("axes fraction", "data"), ha="right",
                           dx=-REF_LABEL_PT[0], dy=REF_LABEL_PT[1])
    check_clear(ref, _b_paths(ax, data), CLEAR_PT + b_marker_half_pt(), "the label of rho = 2")
    # scenarios: a bar of discrete cells at the right, beyond the longest window, from the fastest load at the bottom
    # to the slowest at the top (as rho grows with the load time); white rules between the cells and no outline
    cm = mcolors.ListedColormap(cols)
    norm = mcolors.BoundaryNorm(np.arange(len(scen) + 1) - 0.5, len(scen))
    sm = ScalarMappable(norm=norm, cmap=cm)
    _, _, w, h = style.axes_rect_in(ax)
    f = CBAR_INSET_IN / h
    cb = style.inset_colorbar(ax, sm, rect=(x0, f, CBAR_W_IN / w, 1.0 - 2 * f), orientation="vertical",
                              ticks=list(range(len(scen))))
    cb.ax.set_yticklabels(b["scenario_short"])
    cb.ax.tick_params(length=0, pad=CBAR_PAD_PT)
    cb.outline.set_visible(False)
    for i in range(len(scen) - 1):
        cb.ax.axhline(i + 0.5, color="white", linewidth=DIVIDER_PT, zorder=3)
    return x0


def key_b(ax, data: dict, lab: dict):
    """(b)'s key in the empty upper part of the panel, left of the scenario bar: the encoding as its title ("Median,
    min-max") over one entry per tier, each a tier marker on its own min-max bar. Once the key is laid out, each bar
    spans the rows' pitch less KEY_BAR_GAP_PT, centered on its marker; fails if a bar then shows less than KEY_STEM_PT
    beyond its marker, if the top bar comes closer than KEY_BAR_GAP_PT to the title's baseline, or if the key (bars
    included) comes closer than CLEAR_PT to (b)'s markers and bars."""
    tiers = data["b"]["tiers"]
    hs = [Line2D([], []) for _ in tiers]
    hm = {h: RangeKey(TIER_MARKERS[t], KEY_GREY) for h, t in zip(hs, tiers)}
    leg = ax.legend(hs, [lab["b_tiers"][t] for t in tiers], title=lab["b_range"], loc="upper left",
                    bbox_to_anchor=(KEY_X, ax.get_ylim()[1]), bbox_transform=ax.transData, ncol=1, frameon=False,
                    borderpad=0.0, borderaxespad=0.0, handlelength=0.8, handletextpad=0.5, labelspacing=KEY_ROW_EM,
                    handler_map=hm)
    leg._legend_box.align = "left"
    fig = ax.figure
    fig.canvas.draw()                       # lays the key out: the handles' transforms place its rows
    r = fig.canvas.get_renderer()
    pt = fig.dpi / style.BP_PER_IN
    keys = [hm[h] for h in hs]
    ys = np.array([k.dot.get_transform().transform(k.dot.get_xydata())[0, 1] for k in keys])
    pitch = float(np.abs(np.diff(ys)).min()) / pt
    half = 0.5 * (pitch - KEY_BAR_GAP_PT)
    need = max(marker_half_pt(TIER_MARKERS[t]) for t in tiers) + KEY_STEM_PT
    if half < need - 1e-9:
        raise style.StyleError(f"fig2 (b): the tier key's rows are {pitch:.2f} pt apart; its bars would show less than "
                               f"{KEY_STEM_PT} pt beyond their markers")
    for k in keys:
        y = float(k.dot.get_ydata()[0])
        k.bar.set_ydata([y - half, y + half])
    _, _, descent = r.get_text_width_height_descent("lp", FontProperties(size=style.TICK_PT), ismath=False)
    baseline = leg.get_title().get_window_extent(r).y0 + descent
    top = keys[ys.argmax()].bar.get_window_extent(r).y1
    if (baseline - top) / pt < KEY_BAR_GAP_PT - 1e-6:
        raise style.StyleError(f"fig2 (b): the tier key's top bar ends {(baseline - top) / pt:.2f} pt below the "
                               f"title's baseline, less than {KEY_BAR_GAP_PT} pt")
    check_clear([leg] + [k.bar for k in keys], _b_paths(ax, data), CLEAR_PT + b_marker_half_pt(), "the tier key")
    return leg


def clear_letter(ax, letter, gap_pt: float = LETTER_GAP_PT) -> None:
    """Move the y label of `ax` down just enough that its top end lies `gap_pt` below the bottom of the panel letter
    (in (a) the label is nearly as long as the axes are tall, and centered its top end came within 1 pt of the
    letter); a label that is clear already stays centered."""
    fig = ax.figure
    r = fig.canvas.get_renderer()
    label = ax.yaxis.label
    over = label.get_window_extent(r).y1 - (letter.get_window_extent(r).y0 - gap_pt * fig.dpi / style.BP_PER_IN)
    if over > 0:
        label.set_y(label.get_position()[1] - over / ax.get_window_extent(r).height)


def draw(data: dict):
    lab = data["labels"]
    fig = style.new_figure(NAME)
    H = fig.get_size_inches()[1]
    stack = H - style.MARGIN_TOP - GAP_AB - style.MARGIN_BOTTOM          # the two axes' heights
    a_h = A_SHARE * stack
    (a,) = style.panel_row(fig, (1,), bottom=H - style.MARGIN_TOP - a_h, top=style.MARGIN_TOP, right=RIGHT_IN)
    (b,) = style.panel_row(fig, (1,), top=style.MARGIN_TOP + a_h + GAP_AB, right=RIGHT_IN)
    pools = draw_a(a, data, lab)
    draw_b(b, data, lab)
    key_b(b, data, lab)
    letters = style.panel_letters([a, b])
    key_a(a, letters[0], pools)
    clear_letter(a, letters[0])
    return fig


def report(data: dict, rep: dict) -> None:
    sh, e = data["b"]["shares_rho_le_2"], data["b"]["E1_1"]
    print(f"[{NAME}] E1-1 {'pass' if e['pass'] else 'FAIL'} (max rel err {e['max_rel_err']:.3g} over {e['n']}); "
          f"rho <= 2: {sh['all']['n_le_2']} of {sh['all']['n']} points ({sh['all']['share']:.4f}); default "
          f"scenarios {sh['default_scenarios']['n_le_2']} of {sh['default_scenarios']['n']} "
          f"({sh['default_scenarios']['share']:.4f})")


def main(argv=None) -> dict:
    return cli(NAME, collect, draw, argv, after=report, doc=__doc__)


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
