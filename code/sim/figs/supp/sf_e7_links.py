"""sf_e7_links: MS4's pooling panel, the old Fig. 4(b), redrawn with the MS5b registry keys (design/sublet_v2.md §11,
W4, W7; design/sim_spec_ms4.md §8.1; plan §4, part S-F).

An MS4 result on development-exposed alignments (sublet_v2.md §4.1, D5: E7 alignments 1-4 were read in development),
not a confirmation result: it is labeled so in the panel and the caption, and claims nothing. MS4's Sublet (A8 around
the lagged BL5 at B0 = 10% of the run's BL0a, MS4 spec M36) is drawn as sublet_ms4 ("Lagged RetroRenting + one-way
guard ($B_0=10\\%$ BL0a)"), MS4's BL5 (the lagged build) as bl5_lag and BL1 as bl1 (C41, W7): no legacy key.

Input (versioned): code/sim/out/e7/main/summary.json of MS4 (links.<n>.<tag>.saving_pct for the routing graphs with n
cross-region links; the main grid runs.1.<tag> for n = 5, as fig4_e7_e3.build reads them; the intervals are the MS4
driver's 95% bootstrap intervals of the median over the alignments x policy seeds of meta.grids, not recomputed: this is
MS4's statistic, not a median over the confirmation weeks). The script checks that MS4's tags Sublet, BL5 and BL1 carry
the legacy style keys sublet, bl5 and bl1 and that meta.B0_rule is MS4's 10% of BL0a, so that the MS5b keys name the
policies that ran. No runs/ file is read (meta.runs_files is empty).

Layout (W1 x 2.2 in, C41): one panel, the saving over BL0a in percent (overflow accounting) against the number of
cross-region routing links n, medians with their 95% intervals, the three policies dodged in x by
fig4_e7_e3.DODGE_LINKS (sublet_ms4 drawn last), a reference line at 0 (the level of BL0a), as fig4_e7_e3.draw_b. The
legend's labels are longer than W1's row (4.65 in at 9 pt in two rows, about 3.6 in at C62's 7 pt against 3.43 in),
so the series are labeled directly (W4: a
legend that does not fit is replaced by direct labels), each label in its policy's label color on the free space
nearest to its series and nearer to it than to the others (common.place_label): BL1's registry label; where
sublet_ms4 and the lagged BL5 agree within common.AGREE_MAX_PCT at every n (common.agree_entry; in MS4's E7 they are
equal) one label for both (labels.pair, "equal" or "within p%"), the guard's allowance and the two markers in the
caption, else each its own label (sublet_ms4's registry label up to its parenthesis, which the caption gives). The
provenance "MS4, development-exposed" (labels.key_title) is a black label on the free space nearest to the left end of
the reference line at 0 (on MS4's E7 the empty band between that line and the data). Where a label fits nowhere, the
y range grows by LABEL_RAISE of its height at the top (then at both ends) until all fit, at most MAX_RAISE times. An
earlier build set a four-line key on headroom above the data, which took about 40% of the height (print check of
2026-11-03).

Run from code/sim: python -m figs.supp.sf_e7_links [--from-extract [JSON]] (figs.common.cli).
"""
from __future__ import annotations

import sys
from typing import Any, Mapping, Sequence

import numpy as np

from figs import style
from figs.common import (AGREE_MAX_PCT, MissingKey, agree_entry, cli, finite, maybe, need, num_items, place_label,
                         points_pt)
from figs.fig4_e7_e3 import DODGE_LINKS, MU, series_entry
from figs.inputs import Inputs
from figs.supp.ms4_lib import drop_idle_halos

NAME = "sf_e7_links"
E7 = "code/sim/out/e7/main/summary.json"
KEYS = style.SUPP_POLICIES_MS5B[NAME]          # sublet_ms4, bl5_lag, bl1
# MS4's tags with the legacy style key their summary records and the MS5b key drawn (C41, W7)
TAGS = {"sublet_ms4": ("Sublet", "sublet"), "bl5_lag": ("BL5", "bl5"), "bl1": ("BL1", "bl1")}
DRAW = ("bl1", "bl5_lag", "sublet_ms4")         # drawing order and dodge slots: sublet_ms4 last
B0_RULE = "0.1*BL0a"                            # MS4's allowance (M36), checked against meta.B0_rule
LABEL_BREAK = " ("                              # sublet_ms4's direct label ends before its parenthesis (the caption's)
LABEL_RAISE = 0.06                              # the y range grows by this share of its height until the labels fit ...
MAX_RAISE = 12                                  # ... at most this many times (not in §8)
NEAR_STEPS = 12                                 # points per segment of a series for the labels' nearness (not in §8)
style.register_supplementary(NAME, "W1", 2.2)
LABELS = {"x": "Cross-region links", "y": "Saving (%)", "key_title": "MS4, development-exposed",
          "pair": "Lagged RetroRenting, with and\nwithout one-way guard ({rel})"}


def short_label(key: str) -> str:
    """A series' direct label: its registry label, sublet_ms4's up to its parenthesis (the allowance is in the
    caption)."""
    return style.POLICIES[key].label.split(LABEL_BREAK)[0]


def caption(d: Mapping) -> str:
    g = d["grid"]
    al, se = g["alignments"], g["policy_seeds"]
    ag = d.get("agree")
    fill = {k: style.POLICIES[k].fill for k in ("sublet_ms4", "bl5_lag")}
    rel = ("" if not ag else " Their medians are equal at every number of cross-region links." if ag["within_pct"] == 0
           else f" Their medians agree within {ag['within_pct']}% at every number of cross-region links.")
    return (f"MS4's E7 result on the development-exposed alignments {', '.join(str(a) for a in al)} (policy seeds "
            f"{', '.join(str(s) for s in se)}; not a confirmation result): saving over all-fallback (overflow "
            f"accounting) against the cross-region links of the routing graph, medians with MS4's 95% bootstrap "
            f"intervals. {short_label('sublet_ms4')} ({fill['sublet_ms4']} markers) is the lagged RetroRenting-style "
            f"rule ({fill['bl5_lag']} markers) in the one-way guard at B0 = 10% of all-fallback.{rel}")


def build(inp: Inputs) -> dict:
    e7 = inp.json(E7)
    meta = need(e7, "meta", what=E7)
    tags = need(meta, "tags", what=f"{E7} meta")
    for key, (tag, legacy) in TAGS.items():
        got = (tags.get(tag) or {}).get("style_key")
        if got != legacy:
            raise MissingKey(f"{E7}: meta.tags.{tag}.style_key is {got!r}, not {legacy!r} (drawn as {key})")
    if meta.get("B0_rule") != B0_RULE:
        raise style.StyleError(f"{E7}: meta.B0_rule is {meta.get('B0_rule')!r}, not MS4's {B0_RULE!r}")
    links_meta = need(meta, "links", what=f"{E7} meta")
    ns = [x for x, _, _ in num_items(links_meta)]
    blinks = e7.get("links") if isinstance(e7.get("links"), Mapping) else {}
    series = {}
    for key, (tag, _) in TAGS.items():
        s = {"tag": tag, "links": [], "median": [], "ci_lo": [], "ci_hi": [], "n": [], "note": [], "source": []}
        for n in ns:
            nk = format(float(n), "g")
            if nk in blinks:
                block, src = maybe(blinks, nk, tag)[0], f"links.{nk}.{tag}"
            else:                                        # all links: the main grid (MS4 §3.10)
                block, src = maybe(e7, "runs", MU, tag)[0], f"runs.{format(float(MU), 'g')}.{tag}"
            med, lo, hi, cnt, note = series_entry(block, "saving_pct")
            for f, v in zip(("links", "median", "ci_lo", "ci_hi", "n", "note", "source"),
                            (n, med, lo, hi, cnt, note, src)):
                s[f].append(v)
        series[key] = s
    grids = need(meta, "grids", what=f"{E7} meta")
    d = {"series": series, "agree": agree_entry("sublet_ms4", "bl5_lag", series["sublet_ms4"]["median"],
                                                series["bl5_lag"]["median"], AGREE_MAX_PCT),
         "cross_region_links": {format(float(n), "g"): links_meta.get(format(float(n), "g")) for n in ns},
         "grid": {"alignments": list(grids.get("alignments") or []),
                  "policy_seeds": list(grids.get("policy_seeds") or [])},
         "labels": dict(LABELS),
         "meta": {"git_revision": {"e7_main": meta.get("git_revision")}, "reduced": bool(meta.get("reduced")),
                  "B0_rule": meta.get("B0_rule"), "ms4_tags": {k: v[0] for k, v in TAGS.items()},
                  "sources": list(inp.sources), "runs_files": []}}
    d["labels"]["caption"] = caption(d)
    return d


def label_specs(data: Mapping) -> list[tuple[str, tuple[str, ...]]]:
    """(text, keys) of the direct labels: BL1's; one for sublet_ms4 and the lagged BL5 where they agree (data's
    `agree`), else one each."""
    out = [(short_label("bl1"), ("bl1",))]
    ag = data.get("agree")
    if ag and set(ag["pair"]) == {"sublet_ms4", "bl5_lag"}:
        rel = "equal" if ag["within_pct"] == 0 else f"within {ag['within_pct']}%"
        out.append((data["labels"]["pair"].format(rel=rel), ("sublet_ms4", "bl5_lag")))
    else:
        out += [(short_label("sublet_ms4"), ("sublet_ms4",)), (short_label("bl5_lag"), ("bl5_lag",))]
    return out


def _near(ax, xy: Sequence[tuple]) -> np.ndarray:
    """The points (pt) along the series' polylines (NEAR_STEPS per segment), for free_spot."""
    pts = []
    for x, y in xy:
        ok = np.isfinite(x) & np.isfinite(y)
        x, y = x[ok], y[ok]
        if len(x) > 1:
            t = np.linspace(0.0, 1.0, NEAR_STEPS)
            x = np.concatenate([a + (b - a) * t for a, b in zip(x[:-1], x[1:])])
            y = np.concatenate([a + (b - a) * t for a, b in zip(y[:-1], y[1:])])
        pts.append(points_pt(ax, x, y))
    return np.concatenate(pts) if pts else np.zeros((0, 2))


def place_labels(ax, data: Mapping, xy: Mapping, links) -> list:
    """The direct labels and the provenance label, on free space; the y range grows (LABEL_RAISE) until all fit."""
    specs = label_specs(data)
    y0, y1 = ax.get_ylim()
    step = LABEL_RAISE * (y1 - y0)
    tries = [(k, 0) for k in range(MAX_RAISE + 1)] + [(k, k) for k in range(1, MAX_RAISE + 1)]
    for top, bottom in tries:
        ax.set_ylim(y0 - bottom * step, y1 + top * step)
        placed = []
        for text, keys in specs:
            others = [xy[k] for k in DRAW if k not in keys]
            t = place_label(ax, text, _near(ax, [xy[k] for k in keys]), others=_near(ax, others),
                            color=style.policy(keys[0]).label_color)
            if t is None:
                break
            placed.append(t)
        else:
            # the panel's provenance on the free space nearest to the left end of the reference line at 0
            xs = np.linspace(ax.get_xlim()[0], float(np.nanmin(links)), 10)
            t = place_label(ax, data["labels"]["key_title"], points_pt(ax, xs, np.zeros_like(xs)), color="black")
            if t is not None:
                return placed + [t]
        for t in placed:
            t.remove()
    raise style.StyleError(f"{NAME}: the direct labels fit nowhere on the free space")


def draw(data: Mapping) -> Any:
    lab = data["labels"]
    fig = style.new_figure(NAME)
    (ax,) = style.panel_row(fig, (1,))
    n = len(DRAW)
    vals = [0.0]
    links = finite(data["series"][DRAW[0]]["links"])
    xy = {}
    for i, key in enumerate(DRAW):
        s = data["series"][key]
        x = finite(s["links"]) + DODGE_LINKS * (i - (n - 1) / 2)
        y, lo, hi = finite(s["median"]), finite(s["ci_lo"]), finite(s["ci_hi"])
        style.plot_policy(ax, key, x, y)
        ok = np.isfinite(y) & np.isfinite(lo) & np.isfinite(hi)
        if ok.any():
            style.errorbars(ax, key, x[ok], y[ok], lo[ok], hi[ok])
        vals += [v for v in np.concatenate([y, lo, hi]) if np.isfinite(v)]
        xy[key] = (x, y)
    style.reference_line(ax, y=0.0)
    ax.set_xticks(list(links))
    ax.xaxis.set_major_formatter(style.PLAIN)
    ax.set_xlim(float(np.nanmin(links)) - 0.5, float(np.nanmax(links)) + 0.5)
    lo, hi = min(vals), max(vals)
    pad = 0.08 * (hi - lo) if hi > lo else 1.0
    ax.set_ylim(lo - pad, hi + pad)
    ax.yaxis.set_major_formatter(style.PLAIN)
    ax.set_xlabel(lab["x"])
    ax.set_ylabel(lab["y"])
    texts = place_labels(ax, data, xy, links)
    drop_idle_halos(ax, texts)                     # text in the PDF where its halo would mask nothing
    return fig


def main(argv: Sequence[str] | None = None) -> dict:
    return cli(NAME, build, draw, argv, supplementary=True, doc=__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
