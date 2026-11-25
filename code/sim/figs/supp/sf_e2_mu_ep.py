"""sf_e2_mu_ep: E2's per-episode ratios at mu / beta~ in {0.2, 0.5, 2} (design/sim_spec_ms3.md §8.7; plan §4, part
S-F).

(a)-(c): Fig. 7(a) at mu = 0.2, 0.5 and 2 (e2/summary.json episodes.<group>.<H>.<mu>.<rule>, `trace`, alignment 1,
M19): per rule and lender group (MaaS solid, spot dashed) the median line, A1's band from the median to the P95
(MaaS filled, spot as a dashed outline; the other rules' P95 are in the extract), the exact CR*(H) of C2's game at
that mu (e2/game.json, switch beta~, lambda = 0.715 beta~) continued at 2 - alpha past its last grid point only where
that point lies at or above C2-T4's H*_mu (game.json meta.hstar), and reference verticals at H*_mu and H*_beta,
H*_beta's label left of its line where H*_mu's line would run through it. H*_mu is the threshold of the core game
that the drawn CR*(H) belongs to, game.json meta.hstar.<mu>.<lambda>.H_min (M66), in all three panels; a11's
full-model C2-SW value (tier M; 10.2 min against the game's 3.49 min at mu = 2, within 0.5% of it in (a) and (b)) is
not drawn and is kept per panel as H_star_mu_full_model_min for the caption, with `verticals_source` naming the
source of each value. H*_beta is a11's (tier M, M25), as in Fig. 7(a), which keeps a11's H*_mu (M25). The fixed rule
drawn is the pre-warm rule at mu <= 1 where the coincidence table says it differs from A1, and "always cold" at
mu = 2, where A1 equals the pre-warm rule (§6.4; the caption says so), as a larger marker behind ALG*; BL6 where it
runs (H > 0), its markers smaller with a dark edge on top of ALG* (Fig. 7(a)). The three panels share the y scale.
Trace episodes leave C2's core: per-episode ratios are diagnostics.

C62 (2026-11-24; the look of Fig. 7(a)): the three panels share one y axis, labeled once, with
SHARED_GUTTER_IN between them; "P95" at the MaaS band's top edge; the exact curve's label clear of the spot band's
dashed outline (draw_episode_panel's cr_clear_bands); the notice H in math; H ticks thinned at half an em of the 7-pt
labels; the key's Spot sample with whole dashes; the panel titles on their letters' baseline. The data and their
extract entries are unchanged. C62 fix round: the axes' tops title_drop_in below the letters' line (about 1.8 pt
more), so that the titles' mu ends TITLE_CLEAR_PT above the tops of (b)'s and (c)'s y spines (0.8 pt as built).

Run from code/sim: python -m figs.supp.sf_e2_mu_ep [--from-extract [JSON]].
"""
from __future__ import annotations

import sys
from typing import Any, Mapping, Sequence

from figs import style
from figs.common import cli, need
from figs.fig7_e2_e6 import (A11, A11_TIER, E2, GAME, GROUPS, H_TICK_GAP_PT, LABELS, MAIN_LABELS, POR,
                             SHARED_GUTTER_IN, STATUS, band_top_label, centered_dashes, cr_curve, draw_episode_panel,
                             episode_block, episode_handles, episode_range, h_values, panel_titles, verticals)
from figs.inputs import Inputs

NAME = "sf_e2_mu_ep"
HEADLINE_MU = 1.0                   # Fig. 7's mu (Q23); this figure shows the other grid values
style.register_supplementary(NAME, "W2", 2.2)
KEYS = ("a1", "prewarm", "cold", "bl6")
# C62 fix round: a panel title's descenders end this far above its axes' top (the y spine's end, or the top spine of a
# framed panel), half a spine width included (title_drop_in)
TITLE_CLEAR_PT = 1.0
LETTER_RISE_PT = 1.2                # style.panel_letters: the letters' baseline this far above the axes' top


def title_drop_in() -> float:
    """C62 fix round (group g2's figures with panel titles over the axes: sf_e2_mu_ep, sf_e2_mu_cost, sf_e2_pool,
    sf_e6a): how far (inches) the axes' tops lie below their standard place, the letters and titles staying where they
    were (raise_texts), so that the descenders of a panel title at the caption size (style.LABEL_PT) end
    TITLE_CLEAR_PT above the axes' top, half a spine width included. With the letters' baseline LETTER_RISE_PT above
    the axes, the titles' mu met the tops of (b)'s and (c)'s y spines here and in sf_e2_mu_cost (0.8 pt apart in the
    PDF's ink), and the descenders of "Spot," and "MaaS," crossed sf_e6a's top frame. The descent is the ink of "p"
    (the deepest of the titles' glyphs: mu and beta reach less far), from its outline (TextPath, in pt; the canvas's
    text extent, set in whole pixels at the figure's 100 dpi, gave 1.44 pt for 1.65)."""
    from matplotlib.font_manager import FontProperties
    from matplotlib.textpath import TextPath
    descent_pt = -float(TextPath((0.0, 0.0), "p", size=style.LABEL_PT, prop=FontProperties()).vertices[:, 1].min())
    return max(0.0, TITLE_CLEAR_PT + descent_pt + 0.5 * style.AXES_PT - LETTER_RISE_PT) / style.BP_PER_IN


def raise_texts(texts: Sequence, drop_in: float) -> None:
    """Move figure texts (the panel letters and titles) up by drop_in inches: back to the line they take over axes at
    the standard top, the axes having been placed drop_in lower (title_drop_in)."""
    for t in texts:
        x, y = t.get_position()
        t.set_position((x, y + drop_in / float(t.get_figure(root=True).get_size_inches()[1])))


def side_mus(por: Mapping) -> list[float]:
    """The mu / beta~ grid of por_default.json inputs without the headline value."""
    return [float(m) for m in need(por, "inputs", "mu_over_beta_tilde", what=POR) if float(m) != HEADLINE_MU]


def rules_at(mu: float) -> tuple[str, ...]:
    return ("a1", "prewarm" if mu <= HEADLINE_MU else "cold", "bl6")


def panel_verticals(a11: Mapping, cr: Mapping) -> tuple[dict, float, dict]:
    """(verticals drawn, a11's full-model H*_mu in min, sources) of one panel (M66): H*_mu at the threshold of C2's
    core game that the drawn CR*(H) belongs to (cr_curve's hstar_H_min, game.json meta.hstar.<mu>.<lambda>.H_min),
    H*_beta from a11 (M25); a11's full-model C2-SW H*_mu is returned beside them, not drawn."""
    full = verticals(a11, cr["mu"])
    mu, lam = format(cr["mu"], "g"), format(cr["lam"], "g")
    tier = ".".join(A11_TIER)
    src = {"H_star_mu_min": f'{GAME} meta.hstar["{mu}"]["{lam}"].H_min (C2\'s core game, switch beta~; M66)',
           "H_star_beta_min": f"{A11} {tier}.H_star_beta_s (M25)",
           "H_star_mu_full_model_min": f'{A11} {tier}.H_star_mu_s["{float(cr["mu"])}"] (full-model C2-SW; not drawn)'}
    return ({"H_star_mu_min": cr["hstar_H_min"], "H_star_beta_min": full["H_star_beta_min"]},
            full["H_star_mu_min"], src)


def build(inp: Inputs) -> dict:
    e2, game, por, a11 = inp.json(E2), inp.json(GAME), inp.json(POR), inp.json(A11)
    h_end = max(max(h_values(need(e2, "episodes", g, what=E2))) for g in GROUPS)
    panels = []
    for mu in side_mus(por):
        rules = rules_at(mu)
        ep = episode_block(e2, mu, rules)
        cr = cr_curve(game, por, mu, h_end=h_end)
        vert, full, src = panel_verticals(a11, cr)
        panels.append({"mu": mu, "rules": list(rules), **{r: ep[r] for r in rules},
                       "fixed_rule_shown_at": ep["shown_at"].get(rules[1], {}),
                       "CR_exact": {"H_min": cr["H_min"], "CR": cr["CR"]}, "CR_extension": cr["extension"],
                       "hstar_H_min": cr["hstar_H_min"], "verticals": vert, "H_star_mu_full_model_min": full,
                       "verticals_source": src})
    # C62: the notice H in math as in Fig. 7 (MAIN_LABELS); the exact curve keeps the supplement's design name
    # (C2 core), with H in math too
    labels = {**LABELS, "H": MAIN_LABELS["H"], "cr": "exact CR*($H$), C2 core", "status": STATUS,
              "panel": r"$\mu/\tilde{{\beta}}$ = {:g}", "p95": P95,
              "note": "at mu = 2 A1 equals the pre-warm rule and is drawn as ALG*; trace episodes leave C2's core"}
    return {"panels": panels, "labels": labels, "sources": list(inp.sources)}


P95 = "P95"                         # C62: the top edge of ALG*'s MaaS band, as Fig. 7(a) (band_top_label)


def draw(data: Mapping) -> Any:
    """C62 (the look of Fig. 7): the three panels share one y axis (their y scale was shared already), so that its
    tick labels and label are drawn once and the room of two y labels goes to the data; the light y grid across
    them; H ticks thinned at half an em of the 7-pt labels (H_TICK_GAP_PT); "P95" at the MaaS band's top edge
    (band_top_label); the exact curve's label clear of the bands' edges (cr_clear_bands); the panel titles on their
    letters' baseline (panel_titles); the Spot sample of the key with whole dashes (centered_dashes)."""
    lab = data["labels"]
    fig = style.new_figure(NAME)
    drop = title_drop_in()                         # C62 fix round: the titles' mu clear of (b)'s and (c)'s y spines
    axes = style.panel_row(fig, (1, 1, 1), sharey=(False, True, True), top=style.MARGIN_TOP + style.LEGEND_ROW + drop,
                           left=(None, SHARED_GUTTER_IN, SHARED_GUTTER_IN))       # legend=True's top, less drop
    crs =[{"H_min": p["CR_exact"]["H_min"], "CR": p["CR_exact"]["CR"], "extension": p["CR_extension"]}
           for p in data["panels"]]
    rngs = [episode_range(p, cr, p["rules"]) for p, cr in zip(data["panels"], crs)]
    yr = (min(r[0] for r in rngs), max(r[1] for r in rngs))
    for i, (ax, p, cr) in enumerate(zip(axes, data["panels"], crs)):
        draw_episode_panel(ax, p, cr, p["verticals"], lab, p["rules"], yrange=yr, h_gap_pt=H_TICK_GAP_PT,
                           cr_clear_bands=True)
        if i:
            ax.set_ylabel("")
            ax.tick_params(axis="y", labelleft=False)
    for ax, p in zip(axes, data["panels"]):
        band_top_label(ax, p, text=lab.get("p95", P95))
    letters, titles = panel_titles(axes, [lab["panel"].format(p["mu"]) for p in data["panels"]])    # each mu
    raise_texts(letters + titles, drop)
    style.legend_row(fig, [], extra=episode_handles(KEYS) + centered_dashes(style.env_handles("lender")))
    return fig


def main(argv: Sequence[str] | None = None) -> dict:
    return cli(NAME, build, draw, argv, supplementary=True, doc=__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
