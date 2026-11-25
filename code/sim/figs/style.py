"""Figure style of the Sublet manuscript: design/figure_plan.md §5 (adopted on 2026-10-19), with the type
scale of C62 (2026-11-24; below), which replaces §5's 9-pt rule.

Rules for the figure scripts code/sim/figs/fig<N>_<exp>.py (one script per figure, run from code/sim as
``python -m figs.fig<N>_<exp>``; ``from figs import style``):

* A figure script reads only result files in code/analysis/out/, code/theory_checks/*/out/ (any depth, e.g.
  c3/o1/out/) or code/sim/out/. It never reads raw traces or configs, never types a plotted number by hand, and
  lists the files it read in ``save(..., sources=[...])``, which rejects any other location. Where a script reads
  unversioned run files (Fig. 1(b) and the G3(b) line of Fig. 3(c) read code/sim/out/e11/runs/, as do
  sf_e11_fam and sf_e11_guard), its versioned JSON extract code/sim/out/figs/<name>.json is the figure's source.
* ``fig = new_figure(name)`` gives the registered size (widths W1 = 252/72.27 in, W2 = 516/72.27 in, the TeX
  \\columnwidth and \\textwidth of IEEEtran; heights from FIGURES). ``panel_row`` places the axes with fixed
  margins in inches. tight_layout, constrained_layout and bbox_inches="tight" are never used, and finalize()
  fails if a layout engine is set or a panel was moved after panel_row placed it.
* Policies are drawn with the registry POLICIES (one fixed (color, marker, fill) triple per policy; legend labels
  of decision 11: A6 "Two-timescale PD", A7 "PD heuristic"; only A8 around BL5 is "Sublet"). Theory lines are grey
  and labeled at their right end (``theory_line``), never in the legend; reference lines (the level 1 of BL0a or
  OPT, thresholds such as rho = 2, H*_mu, H*_beta) use ``reference_line``.
* ``save(fig, name, data, sources=...)`` writes the PDF to paper/figures/<name>.pdf (CreationDate None, layers with
  more than 5,000 marks rasterized at 600 dpi, each embedded font subset with a tag of its own), the plotted
  numbers to code/sim/out/figs/<name>.json and a 300-dpi PNG preview code/sim/out/figs/<name>.png. It writes
  nothing and raises FigureCheckError if a glyph is missing from the fonts (matplotlib would draw an empty box or a
  dummy symbol) or if ``finalize`` fails: the page is not W1 or W2 wide and of the registered height (tolerance
  0.5 bp), a text is outside [TEXT_MIN_PT, TEXT_MAX_PT] = [7, 7.970] pt (C62: never larger than the caption, below),
  pdffonts lists a Type 3, a non-embedded or a DejaVu font, a layout engine is set, a panel was moved, ink lies
  outside the page, or two texts overlap. The missing glyph and the last five conditions are failures that §5 does
  not list. Ink outside the page is typically an x tick label at the right end of a row's
  last panel, which the 0.06-in right margin does not hold when centered; ``end_label_inside`` right-aligns it
  (``symlog_minutes`` does so by default). finalize warns (FigureWarning) about any warning that pdffonts prints,
  and (GlyphSizeWarning) about mathtext glyphs below SCRIPT_MIN_PT (4.9 pt), i.e. below a first-level sub- or
  superscript of 7-pt text, which mathtext sets at 0.7 of the text size (§5 allows those where a symbol needs
  them, such as OPT_eager, LB_react and H*_mu). The output roots can be overridden by the arguments pdf_dir and out_dir or by the environment
  variables SUBLET_FIGS_PDF_DIR and SUBLET_FIGS_OUT_DIR (tests write only under a temporary folder).
* LaTeX includes the PDF with \\includegraphics and no width, so the figure is never rescaled.

Importing this module applies RC (Liberation Sans, embedded as TrueType, pdf.fonttype 42; never DejaVu Sans) to
matplotlib.rcParams. It first checks that matplotlib finds Liberation Sans; if the font cache lacks it, the
user-level cache (matplotlib.get_cachedir(), never a system file) is rebuilt and the files that fc-list reports
are registered in this process; if the font still cannot be found, the import fails with StyleError.

Nimbus Sans, the fallback of §5, is a family fallback only: font.sans-serif lists it after Liberation Sans, so it
would be used only if Liberation Sans were missing, which the import-time require_font() rules out. It is not a
per-glyph fallback: matplotlib builds its glyph fallback chain from font.family, which is "sans-serif" and resolves
to Liberation Sans alone, so a glyph that Liberation Sans lacks is not taken from Nimbus Sans; save() fails on it.
Listing Nimbus Sans in font.family would make it a per-glyph fallback, but it is an OpenType/CFF font, which
matplotlib embeds as CID Type 0C with a font-type mismatch that pdffonts reports. Mathtext takes the glyphs that
Liberation Sans lacks from stixsans (mathtext.fallback).

MS3 addition C13 (design/sim_spec_ms3.md §2.3): the registry keys a3_rot ("A3, rotation") and cold ("Always cold")
for supplementary figures only, and SUPP_POLICIES, the policy set of each supplementary MS3 figure (§8.7).

MS4 addition C18 (design/sim_spec_ms4.md §2.3, §8.2): seven registry keys for supplementary figures only, listed in
SUPP_ONLY_KEYS_MS4 (E4's psi-PDs psi_01, psi_03, psi_05; E5's A6 redundancy modes a6_red_off, a6_always2 and BL3's
N_Extra variants bl3_n0, bl3_n1), each next to its family's key, so that legend_order lists the variants in
parameter order: psi_01, psi_03, psi_05 before a2_frac (psi = 1), bl3_n0, bl3_n1 before bl3 (N_Extra 2), and
a6_red_off, a6_always2 after a6_siloed, A6's default 'rule' first (with 'off' first, sf_e5's two-row legend of its
seven keys is wider than a W2 row; as placed it fits, tests/test_ms4_additions.py); SUPP_POLICIES_MS4, the policy set
of each supplementary MS4 figure; and the registration of the eight MS4 supplementary figures at their §8.2 sizes
(sf_e3_u, E3's u sweep, was dropped with M41). The MS3 maps SUPP_POLICIES and SUPP_ONLY_KEYS are unchanged.

MS5 addition C29 (design/sim_spec_ms5.md §2.3, §7): SUPP_POLICIES_MS5, the policy set of each supplementary MS5 figure
(sf_s1: Sublet; sf_e9: Sublet, A6 and lb, the registry's computed lower bound, which draws the LP bound's time;
sf_slack: none), and the registration of the three MS5 supplementary figures at their §7 sizes (sf_s1 and sf_slack
W2 x 2.5 in, sf_e9 W2 x 2.2 in). No key, label or triple is new or changed; the MS3 and MS4 maps keep their values.

MS5b addition C41 (design/sublet_v2.md §11, W1, W3, W4, W7, W8, W12): 24 registry keys for the MS5b figures and floats
(MS5B_KEYS; the table _REGISTRY_MS5B with each key's tag of ms5b_common.TAGS in its note), each placed after an anchor
of its family so that legend_order lists a family's variants together (the MS4 C18 rule; the order of the earlier keys
among themselves is unchanged). In MS5b figures and floats "Sublet" is A8P around A9 (sublet_v2, with Sublet's line,
marker and z-order); A9, CR, the five A9 ablations, Sublet one-way and Sublet's lagged and siloed runs share Sublet's
blue (family sublet), the BL1 and BL5 variants and transplants their family's color, and BL3-0 (bl3_0) is green. A key
with an earlier key's label takes its (color, marker, fill) (sublet_v2, sublet_v2_siloed, bl1_gp, bl5_cur). Labels
use \\geq, which mathtext and LaTeX both accept. The main-text figure fig4v2 (W2 x 2.4 in, the paper's Fig. 4) with its
set in FIGURE_POLICIES; SUPP_POLICIES_MS5B, the sets of the seven supplementary MS5b figures, registered at their W4
sizes; the key sets MS5B_KEYS and LEGACY_KEYS (sublet, sublet_siloed, bl5, bl1_guard: they keep their labels and are
drawn by frozen figures only); LEGACY_PENDING, every frozen figure that draws a legacy key with the MS6 item that
settles it (W8); figure_sets(), every map's sets in one; and check_legacy(), which fails if a figure draws an MS5b key
with a legacy key or draws a legacy key without a LEGACY_PENDING entry. Within each MS5b set no two keys share a
(marker, fill) (greyscale), and no key takes a (color, marker) pair that the MS3 and MS4 tests pin. No earlier key,
label, color, triple or set changes; the decision-11 sentence above holds for the frozen figures.

MS6 addition C46 (design/ms6_spec.md §1.1 M1-M5, §2 U42; the entry gate, MS5b's W8): the key a7_g1 "PD heuristic +
one-way guard" (MS6_KEYS; A8 around A7 at Algorithm 1's defaults: E11's tag PS-G), in A7's green (family a7, group
guarded) with a filled thin diamond, a (color, marker) pair no other key has, placed after a7_guard; and, as bl5_g1
and sublet_ms4 split the guard around the lagged BL5 by its allowance (M4), the key a7_ms4 "PD heuristic + one-way guard
($B_0=10\\%$ BL0a)" (A8 around A7 at MS4's allowance: E7's and S1's tag A7G), with sublet_ms4's allowance suffix, a
filled X in the same green, placed after a7_g1. The sets of the frozen figures move to the configuration keys (M2,
M4): the figures of Algorithm 1's defaults (fig3, fig5, sf_e1_sched, sf_e11_inst, sf_e11_fam, sf_e11_guard, and
sf_e7_allow, whose axis sweeps B0) draw bl5_g1 and a7_g1, the figures of MS4's allowance (sf_e3_util, sf_e3_mu, sf_e5,
sf_e7_mix, sf_e7_mu, sf_s1, sf_e9) draw sublet_ms4 and a7_ms4; bl5 becomes bl5_lag and bl1_guard bl1_g1; a siloed run
is its key drawn in the sharing line style (env_linestyle('sharing', 'siloed'), as sf_e3_v2 draws it), so
sublet_siloed leaves the sets. Sublet's blue, circle and 1.5-pt line then mean A8P around A9
(sublet_v2) in every figure but the frozen fig1 and fig4. The legacy entries keep their labels and triples (fig1, fig4
and the MS4 Table III draw them); a7_guard joins LEGACY_KEYS; LEGACY_PENDING keeps fig1 (superseded by fig1v2, M1; the
MS3 claims report reads fig1.json) and fig4; check_legacy() also fails on a figure that draws an MS6 key with a legacy
key, so a7_g1 and a7_ms4 never share a figure with a7_guard. fig1v2, the paper's Fig. 1 (M1), is registered at fig1's
size (W1 x 2.4 in) with the set (sublet_v2,). guard_pair_handles() gives M5's paired legend entries: one entry per inner
policy that shows its open marker beside its guarded configuration's filled marker under the inner policy's registry
label, and the entry GUARD_PAIR_NOTE; it is the one stated exception to "legend labels are registry labels" (figure plan
§5), and legend_row and corner_legend draw such a pair side by side (PAIR_HANDLER_MAP). Two (marker, fill) pairs occur
twice in the moved sets, which the C41 triples of bl1_g1 and sublet_ms4 fix: bl1_g1 and bl2 (v, filled) in fig3 and
sf_e11_inst, sublet_ms4 and bl3 (<, filled) in sf_e5. Fig. 3 labels bl1_g1 directly in (a), its only panel; sf_e11_inst
tells the two apart by their places in its dodge order (bl1_g1 right of Greedy renting, bl2 last); sf_e5 keeps both in
its legend rows and tells them apart by BL3's black edge and lighter fill (the print check judges both in greyscale).

MS7 addition C58 (design/ms7/w_spec.md §2.2, §4 W-G1): fig1v3, the paper's Fig. 1 (figs/fig1_v3.py), registered at
W2 x 1.9 in with the set (sublet_v2,); no key, label, triple or earlier set changes.

MS7 addition C58 (design/ms7/w_spec.md §2.8, §4 W-G2): two registry keys for the MS7 tags that a main-text figure or
table prints (MS7_KEYS, appended to the registry): a9p "Critical-ratio renting,
protected only" (e7r's tag A9-P) in Sublet's blue with a filled left triangle, and mpc "MPC" (e7r's tag MPC-T, the MPC
baseline at the setting of rule T) in CoCaR-style's yellow with its black edge and a filled diamond; fig4v3, the
paper's Fig. 3 (figs/fig4_v3.py), registered at fig4v2's size (W2 x 2.4 in) with its set in FIGURE_POLICIES; and
TABLE_POLICIES_MS7, the keys that Tables IV and V (figs/table3_v3.py, figs/table5_alglb.py) print, in row order. No
earlier key, label, triple or set changes.

MS7 addition C61 (after the X4/X5 runs, 2026-11-10): a9p's label becomes "Protected-only renting", the name the text
and the supplement use (it was "Critical-ratio renting, protected only", which wrapped to three lines in Table IV), and
its marker a filled star, so that it no longer mirrors critical-ratio planning's filled right triangle in Fig. 3(c);
(color, marker, fill) stays a triple of its own. No other key changes.

MS7 addition C58 (design/ms7/w_spec.md §4, unit W-G4; registration of unit W-G4-0): the registry keys of the MS7 tags
that the supplementary figures and tables of the runs X1-X5 (design/ms7/registration.md §2, §3) print, appended after
MS7_KEYS (MS7_SUPP_KEYS; MS7_KEY_OF_TAG maps each MS7 tag to its key, figs/supp/ms5b_e7_lib.KEY_OF_TAG the
confirmation's); SUPP_POLICIES_MS7, the policy sets of the eight supplementary figures sf_lag_v2, sf_oos (X1, X2),
sf_bl_ms7, sf_stress_ms7 (X4, X5), sf_s1_v2, sf_e5_v2, sf_e8_v2 and sf_e9_v2 (X3), each figure's set and size in the
block of its writer ("# W-G4 block A ..." to "# end W-G4 block A", B, C), so that a writer changes its own block only;
figure_sets() includes the map; and two environment factors for the line style, 'demand' (revealed, lagged: X1) and
'calibration' (out of sample, in sample: X2). No earlier key, label, triple or set changes.

MS7 addition C59 (RC19(3)): the labels of sublet_ms4 and a7_ms4 write MS4's allowance in words,
"($B_0=10\\%$ of the all-fallback bill)", as the main text names that configuration (as built, C41 and C46,
"($B_0=10\\%$ BL0a)"); no other key, label, color, triple or set changes.

MS7 addition C62 (2026-11-24: no text in any figure larger than the caption text; the figures
high-end, informative and readable): the type scale is CAPTION_PT = 8 * 72 / 72.27 bp (7.970 bp, IEEEtran's
\\footnotesize caption at the 10-pt body) for the bold panel letters (LETTER_PT), the axis labels and the panel titles
(LABEL_PT), and TICK_PT = 7 pt for tick labels, legends, direct labels, annotations and colorbar ticks; finalize()
fails on a text outside [TEXT_MIN_PT, TEXT_MAX_PT] = [7, CAPTION_PT] pt (tolerance TEXT_TOL_PT: CAPTION_PT passes,
8.0 bp fails), and warns below SCRIPT_MIN_PT = 0.7 * 7 = 4.9 pt (a first-level script of 7-pt text). This replaces
the 9-pt rule decided at the print check of 2026-10-22 (every text at 9 pt, nothing outside [9, 10] pt, scripts down
to 6.3 pt), which design/figure_plan.md §5 states. The margins that hold text shrink by what the smaller text frees
(bottom 0.42 -> 0.38 in, top 0.13 -> 0.12 in, legend row 0.24 -> 0.21 in, y-label reserve 0.50 -> 0.43 in, shared
y-axis reserve 0.14 -> 0.11 in; the derivation at the constants), so the panels gain that space; the legend's column
spacing returns to its 7-pt value, 1.0 em (0.8 em at 9 pt: 7.0 pt between columns, as 7.2 pt was). Line widths,
marker sizes, pads, tick lengths and dash patterns are unchanged; no key, label, triple, set or figure size changes.

Adopted decisions used here (§8): 7, Fig. 3(a) shades the pre-set criteria region x <= 1.10, y <= 1.05
(shade_region); 11, the legend labels above; 13, the sans-serif style of §5.

Choices where §5 is silent (marked "not in §5" below): tick and label pads 2 pt (so that a y label and four-character
tick labels fit the 0.43-in reserve and an x label fits the 0.38-in bottom margin); dash patterns in points
(dashed 3.0/1.6, dotted 1.0/1.4, dash-dot 4.0/1.4/1.0/1.4); reference policy lines BL0a/BL0b 0.75 pt; theory labels
in the theory grey, drawn above the data with a white halo; panel letters with their baseline 1.2 pt above the axes
top at the left edge of the panel's slot; the legend row centered over the panels in the top 0.21 in; an x tick
label at the right end of an axis right-aligned (end_label_inside).
"""
from __future__ import annotations

import hashlib
import json
import logging
import math
import os
import re
import shutil
import string
import subprocess
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Sequence

import matplotlib as mpl
import numpy as np
from matplotlib import font_manager as _fm
from matplotlib import colors as _mcolors
from matplotlib import patheffects as _pe
from matplotlib import ticker as _ticker
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.collections import Collection, LineCollection, QuadMesh
from matplotlib.figure import Figure
from matplotlib.font_manager import FontProperties
from matplotlib.legend_handler import HandlerTuple
from matplotlib.lines import Line2D
from matplotlib.mathtext import MathTextParser
from matplotlib.text import Text

REPO = Path(__file__).resolve().parents[3]
DEFAULT_PDF_DIR = REPO / "paper" / "figures"
DEFAULT_OUT_DIR = REPO / "code" / "sim" / "out" / "figs"
ENV_PDF_DIR = "SUBLET_FIGS_PDF_DIR"
ENV_OUT_DIR = "SUBLET_FIGS_OUT_DIR"
PDFFONTS = "/usr/bin/pdffonts"
PDFINFO = "/usr/bin/pdfinfo"


class StyleError(RuntimeError):
    """A figure, layout or registry rule of §5 is violated."""


class FigureCheckError(StyleError):
    """finalize() found a page, text-size, font or layout problem."""


class FigureWarning(UserWarning):
    """finalize() found something to look at that is not a failure: pdffonts printed a warning, or (the subclass
    GlyphSizeWarning) a mathtext glyph is set below SCRIPT_MIN_PT."""


class GlyphSizeWarning(FigureWarning):
    """A mathtext glyph is smaller than SCRIPT_MIN_PT (4.9 pt). Mathtext sets one script level at 0.7 of the text
    size (4.9 pt in a 7-pt label, 5.58 pt in a 7.97-pt one); §5 allows a first-level sub- or superscript where a
    symbol needs it (OPT_eager, LB_react, H*_mu), so only a smaller glyph (a second script level) warns."""


# ---------------------------------------------------------------------------------------------------------------
# Sizes (§5 "Sizes"; §3.1: LaTeX lengths are TeX points, 1/72.27 in; PDF pages are in bp, 1/72 in)
TEX_PT_PER_IN = 72.27
BP_PER_IN = 72.0
W1 = 252 / TEX_PT_PER_IN          # \columnwidth, 3.487 in = 251.06 bp
W2 = 516 / TEX_PT_PER_IN          # \textwidth, 7.140 in = 514.07 bp
WIDTHS = {"W1": W1, "W2": W2}
PAGE_TOL_BP = 0.5
SUPP_HEIGHT_RANGE = (1.8, 2.5)    # supplementary figures: same widths, heights 1.8-2.5 in

# Margins in inches. C62 re-derived the five that hold text for its type scale: each is its 9-pt value less exactly
# what the smaller text frees, measured at 600 dpi on Liberation Sans (layout boxes and ink agree within 0.001 in):
# an x label under its tick labels 0.037 in, a y label beside four-character tick labels 0.065-0.068 in (plain and
# mathtext labels), the bold panel letter above the axes 0.010 in, a legend row 0.025 in (two rows 0.058 in), a
# two-digit tick label's width 0.031 in; rounded to 0.01 in, so that each keeps the room the 9-pt scale left beside
# its text within 0.005 in. The 9-pt values (2026-10-22 to C62) are in the comments; the right margin holds no text.
MARGIN_RIGHT = 0.06
MARGIN_BOTTOM = 0.38              # x tick labels and x label (0.42 at 9 pt)
MARGIN_TOP = 0.12                 # panel letters, top y tick label (0.13 at 9 pt)
LEGEND_ROW = 0.21                 # added to the top margin for a legend row (0.24 at 9 pt)
LEFT_LABEL = 0.43                 # y label and tick labels of a panel (0.50 at 9 pt)
LEFT_SHARED = 0.11                # a panel that shares the y axis of its left neighbor (0.14 at 9 pt)
GEOMETRY_TOL_IN = 0.005           # finalize(): a panel moved by more than this after panel_row placed it

# Text sizes. MS7 addition C62 (2026-11-24): no text in a figure is larger than the caption text, which is
# IEEEtran's \footnotesize at the 10-pt body, 8 TeX pt = 8 * 72 / 72.27 bp = 7.970 bp (matplotlib's points are bp;
# the captions measure 7.97 bp in the built paper and supplement). The scale has two sizes: CAPTION_PT for the bold
# panel letters, the axis labels and the panel titles, and 7 pt for every other text (tick labels, legends, direct
# labels, annotations, colorbar ticks and labels); nothing below TEXT_MIN_PT = 7 pt or above TEXT_MAX_PT = CAPTION_PT.
# C62 replaces the rule of 2026-10-22 (every text at 9 pt, nothing outside [9, 10] pt, after the IEEE Author Center's
# "approximately 9-10 point when viewed at full size", literature/sources/ieee-graphics-guidelines.md, decided at the
# print check), which had replaced the 7-8 pt of 2026-10-19 (decision 13)
CAPTION_PT = 8 * BP_PER_IN / TEX_PT_PER_IN   # 7.970 bp, the caption text
TEXT_MIN_PT = 7.0
TEXT_MAX_PT = CAPTION_PT
TEXT_TOL_PT = 1e-6                # finalize()'s tolerance: a text at exactly CAPTION_PT passes, 8 bp (0.03 above) fails
LABEL_PT = CAPTION_PT             # axis labels, panel titles
TICK_PT = 7.0                     # tick labels, legend, direct labels, colorbar ticks, annotations
LETTER_PT = CAPTION_PT            # panel letters, bold
SCRIPT_MIN_PT = 0.7 * TEXT_MIN_PT  # a first-level mathtext sub- or superscript of 7-pt text (4.9 pt) is allowed
TICK_PAD_PT = 2.0                 # not in §5
LABEL_PAD_PT = 2.0                # not in §5

# Lines and markers (§5 "Lines and markers")
LINE_PT = 1.0
SUBLET_LINE_PT = 1.5
MARKER_PT = 3.5
SUBLET_MARKER_PT = 4.0
MARKER_EDGE_PT = 0.6
AXES_PT = 0.6
UNCERTAINTY_PT = 0.6
BAND_ALPHA = 0.18
THEORY_GREY = "#7F7F7F"
THEORY_PT = 0.75
THEORY_LOWER_PT = 0.9
REFERENCE_GREY = "#BDBDBD"
REFERENCE_PT = 0.5
REFERENCE_POLICY_PT = 0.75        # BL0a / BL0b drawn as reference lines; not in §5
GRID_GREY = "#E6E6E6"
GRID_PT = 0.4
SHADE_GREY = "#EFEFEF"            # shaded regions (Fig. 3(a)'s criteria region, decision 7); not in §5
HALO_PT = 0.8                     # white halo on each side of a theory line on a heatmap
LABEL_HALO_PT = 2 * HALO_PT + 0.5  # stroke width of the white halo around a theory label; not in §5

# Export (§5 "Export and checks")
RASTER_MARKS = 5000
RASTER_DPI = 600
PREVIEW_DPI = 300

FONT_FAMILY = "Liberation Sans"
FONT_FALLBACK = "Nimbus Sans"
BANNED_FONT = "DejaVu"

Z_REFERENCE = 1.0
Z_THEORY = 1.5
Z_DATA = 2.0
Z_SUBLET = 2.6                    # Sublet is drawn last among the data
Z_THEORY_LABEL = Z_SUBLET + 0.5   # theory labels above the data, with a white halo; not in §5


# ---------------------------------------------------------------------------------------------------------------
# Figure registry (§1 and §5 "Sizes")
@dataclass(frozen=True)
class FigureSpec:
    name: str
    width: str            # "W1" or "W2"
    height_in: float
    main: bool = True

    @property
    def width_in(self) -> float:
        return WIDTHS[self.width]

    @property
    def size_in(self) -> tuple[float, float]:
        return (self.width_in, self.height_in)


FIGURES: dict[str, FigureSpec] = {s.name: s for s in (
    FigureSpec("fig1", "W1", 2.4),
    FigureSpec("fig2", "W1", 2.7),
    FigureSpec("fig3", "W2", 2.4),
    FigureSpec("fig4", "W2", 2.2),
    FigureSpec("fig5", "W2", 2.2),
    FigureSpec("fig6", "W1", 2.2),
    FigureSpec("fig7", "W2", 2.4),
)}


def register_supplementary(name: str, width: str, height_in: float) -> FigureSpec:
    """Register a supplementary figure (part S-F): width W1 or W2, height 1.8-2.5 in."""
    if width not in WIDTHS:
        raise StyleError(f"{name}: width must be 'W1' or 'W2', not {width!r}")
    lo, hi = SUPP_HEIGHT_RANGE
    if not lo <= float(height_in) <= hi:
        raise StyleError(f"{name}: supplementary height {height_in} in is outside [{lo}, {hi}] in")
    old = FIGURES.get(name)
    if old is not None and old.main:
        raise StyleError(f"{name} is a main-text figure")
    spec = FigureSpec(name, width, float(height_in), main=False)
    if old is not None and old != spec:
        raise StyleError(f"{name} is already registered as {old}")
    FIGURES[name] = spec
    return spec


def figure_spec(name: str) -> FigureSpec:
    try:
        return FIGURES[name]
    except KeyError:
        main = sorted(k for k, s in FIGURES.items() if s.main)
        raise StyleError(f"figure {name!r} is not registered (main text: {main}; supplementary figures: "
                         "register_supplementary)") from None


def new_figure(name: str) -> Figure:
    """A Figure at the registered size with an Agg canvas (no pyplot state)."""
    spec = figure_spec(name)
    fig = Figure(figsize=spec.size_in, dpi=100)
    FigureCanvasAgg(fig)
    fig._sublet_name = name
    return fig


# ---------------------------------------------------------------------------------------------------------------
# Fonts
def _font_path(family: str) -> str | None:
    try:
        path = _fm.fontManager.findfont(FontProperties(family=family), fallback_to_default=False,
                                        rebuild_if_missing=False)
    except ValueError:
        return None
    try:
        name = _fm.get_font(path).family_name
    except Exception:
        return None
    return path if name == family else None


def _fc_list_files(family: str) -> list[str]:
    exe = shutil.which("fc-list")
    if exe is None:
        return []
    try:
        out = subprocess.run([exe, f":family={family}", "file"], capture_output=True, text=True, timeout=30,
                             check=False).stdout
    except (OSError, subprocess.SubprocessError):
        return []
    files = []
    for line in out.splitlines():
        p = line.strip().rstrip(":").strip()
        if p and Path(p).suffix.lower() in (".ttf", ".otf", ".ttc") and Path(p).is_file():
            files.append(p)
    return sorted(set(files))


def require_font(family: str = FONT_FAMILY, *, rebuild: bool = True) -> str:
    """Path of the regular face of `family` as matplotlib resolves it; raises StyleError if it cannot be found.

    If the font manager lacks the family: (1) with rebuild=True, rebuild the user-level font cache
    (matplotlib.get_cachedir(); system files are never touched) and take its font list into this process;
    (2) register the files that fc-list reports for the family in this process. Then fail clearly."""
    path = _font_path(family)
    if path is None and rebuild:
        fresh = _fm._load_fontmanager(try_read_cache=False)       # writes <cachedir>/fontlist-v*.json
        _fm.fontManager.ttflist = fresh.ttflist
        _fm.fontManager.afmlist = fresh.afmlist
        _fm.fontManager._findfont_cached.cache_clear()
        path = _font_path(family)
    if path is None:
        for f in _fc_list_files(family):
            try:
                _fm.fontManager.addfont(f)
            except Exception:
                pass
        path = _font_path(family)
    if path is None:
        raise StyleError(f"matplotlib cannot find the font {family!r} (design/figure_plan.md §5 requires it; "
                         f"fc-list :family='{family}' lists {_fc_list_files(family) or 'nothing'}). Install the "
                         f"fonts-liberation package or put the .ttf files in ~/.local/share/fonts, then rerun.")
    return path


FONT_PATH = require_font(FONT_FAMILY)


# ---------------------------------------------------------------------------------------------------------------
# rcParams (§5 "Fonts", "Lines and markers", "Axes, legends and panels")
OKABE_ITO = ("#0072B2", "#E69F00", "#009E73", "#D55E00", "#CC79A7", "#56B4E9", "#F0E442", "#000000")

RC: dict = {
    "font.family": "sans-serif",
    "font.sans-serif": [FONT_FAMILY, FONT_FALLBACK],
    "font.size": TICK_PT,
    "font.weight": "normal",
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
    "svg.fonttype": "none",
    "pdf.use14corefonts": False,
    "mathtext.fontset": "custom",
    "mathtext.rm": FONT_FAMILY,
    "mathtext.sf": FONT_FAMILY,
    "mathtext.it": f"{FONT_FAMILY}:italic",
    "mathtext.bf": f"{FONT_FAMILY}:bold",
    "mathtext.bfit": f"{FONT_FAMILY}:italic:bold",
    "mathtext.cal": f"{FONT_FAMILY}:italic",
    "mathtext.tt": "Liberation Mono",
    "mathtext.fallback": "stixsans",
    "mathtext.default": "it",
    "axes.labelsize": LABEL_PT,
    "axes.titlesize": LABEL_PT,
    "axes.titleweight": "normal",
    "figure.titlesize": LABEL_PT,
    "xtick.labelsize": TICK_PT,
    "ytick.labelsize": TICK_PT,
    "legend.fontsize": TICK_PT,
    "legend.title_fontsize": TICK_PT,
    "axes.linewidth": AXES_PT,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": False,
    "axes.axisbelow": True,
    "axes.labelpad": LABEL_PAD_PT,
    "axes.unicode_minus": True,
    "axes.formatter.useoffset": False,
    "axes.formatter.use_mathtext": False,
    "axes.prop_cycle": mpl.cycler(color=list(OKABE_ITO)),
    "axes.edgecolor": "black",
    "axes.labelcolor": "black",
    "text.color": "black",
    "xtick.color": "black",
    "ytick.color": "black",
    "xtick.direction": "out",
    "ytick.direction": "out",
    "xtick.top": False,
    "ytick.right": False,
    "xtick.major.size": 3.0,
    "xtick.major.width": 0.6,
    "xtick.minor.size": 1.5,
    "xtick.minor.width": 0.4,
    "ytick.major.size": 3.0,
    "ytick.major.width": 0.6,
    "ytick.minor.size": 1.5,
    "ytick.minor.width": 0.4,
    "xtick.major.pad": TICK_PAD_PT,
    "xtick.minor.pad": TICK_PAD_PT,
    "ytick.major.pad": TICK_PAD_PT,
    "ytick.minor.pad": TICK_PAD_PT,
    "grid.color": GRID_GREY,
    "grid.linewidth": GRID_PT,
    "grid.linestyle": "-",
    "lines.linewidth": LINE_PT,
    "lines.markersize": MARKER_PT,
    "lines.markeredgewidth": MARKER_EDGE_PT,
    "lines.scale_dashes": False,
    "lines.dashed_pattern": [3.0, 1.6],
    "lines.dotted_pattern": [1.0, 1.4],
    "lines.dashdot_pattern": [4.0, 1.4, 1.0, 1.4],
    "lines.dash_capstyle": "butt",
    "lines.solid_capstyle": "butt",
    "patch.linewidth": 0.6,
    "hatch.linewidth": 0.4,
    "errorbar.capsize": 0.0,
    "legend.frameon": False,
    "legend.numpoints": 1,
    "legend.scatterpoints": 1,
    "legend.handlelength": 2.0,
    "legend.handletextpad": 0.4,
    "legend.columnspacing": 1.0,     # C62: 1.0 em at 7 pt (7.0 pt); 0.8 em at 9 pt (7.2 pt), 2026-10-22 to C62
    "legend.labelspacing": 0.3,
    "legend.borderpad": 0.2,
    "legend.borderaxespad": 0.2,
    "image.cmap": "cividis",
    "figure.dpi": 100,
    "figure.autolayout": False,
    "figure.constrained_layout.use": False,
    "savefig.dpi": RASTER_DPI,
    "savefig.bbox": None,
    "savefig.transparent": False,
    "savefig.facecolor": "white",
}


def apply() -> None:
    """Apply RC to matplotlib.rcParams (done once at import)."""
    mpl.rcParams.update(RC)


apply()


# ---------------------------------------------------------------------------------------------------------------
# Panels
def panel_row(fig: Figure, ratios: Sequence[float] = (1.0,), *, legend: bool | int = False,
              sharey: Sequence[bool] | None = None, left: Sequence[float | None] | None = None,
              bottom: float = MARGIN_BOTTOM, top: float | None = None, right: float = MARGIN_RIGHT) -> list:
    """Axes of a row of panels with axes widths in `ratios` and fixed margins in inches.

    Each panel reserves LEFT_LABEL (0.43 in) on its left, or LEFT_SHARED (0.11 in) where sharey[i] is True (it then
    shares the y axis of panel i-1 and hides its y tick labels); `left[i]` (inches, e.g. from ytick_reserve() for
    name tick labels) overrides the reserve of panel i. `bottom` and `top` are the distances from the figure's
    bottom and top edges to the axes (defaults: 0.38 in, and 0.12 in plus 0.21 in per legend row: one if `legend`
    is True, `legend` rows if it is an integer, for legend_row(..., rows=2)); a stacked row
    (Figs. 1 and 2) passes both."""
    W, H = (float(v) for v in fig.get_size_inches())
    ratios = [float(r) for r in ratios]
    n = len(ratios)
    if n == 0 or min(ratios) <= 0:
        raise StyleError(f"ratios must be positive, got {ratios}")
    share = [False] * n if sharey is None else [bool(s) for s in sharey]
    if len(share) != n or share[0]:
        raise StyleError("sharey needs one entry per panel and the first panel has no left neighbor")
    reserve = [LEFT_SHARED if s else LEFT_LABEL for s in share]
    if left is not None:
        if len(left) != n:
            raise StyleError("left needs one entry per panel")
        reserve = [r if v is None else float(v) for r, v in zip(reserve, left)]
    top_in = MARGIN_TOP + LEGEND_ROW * int(legend) if top is None else float(top)
    avail = W - sum(reserve) - float(right)
    h = H - float(bottom) - top_in
    if avail <= 0 or h <= 0:
        raise StyleError(f"no room for the axes: width {avail:.3f} in, height {h:.3f} in")
    total = sum(ratios)
    axes = []
    x = 0.0
    for i, r in enumerate(ratios):
        slot_left = x
        x += reserve[i]
        w = avail * r / total
        ax = fig.add_axes((x / W, float(bottom) / H, w / W, h / H), sharey=axes[i - 1] if share[i] else None)
        if share[i]:
            ax.tick_params(axis="y", labelleft=False)
        ax._sublet_rect_in = (x, float(bottom), w, h)
        ax._sublet_slot_left_in = slot_left
        axes.append(ax)
        x += w
    return axes


def axes_rect_in(ax) -> tuple[float, float, float, float]:
    """(x0, y0, width, height) of the axes in inches from the figure's bottom left corner."""
    W, H = ax.figure.get_size_inches()
    b = ax.get_position(original=True)
    return (b.x0 * W, b.y0 * H, b.width * W, b.height * H)


def _is_math(s: str) -> bool:
    """Whether matplotlib renders `s` with mathtext (an even number, at least two, of unescaped dollar signs)."""
    n = len(re.findall(r"(?<!\\)\$", s))
    return n >= 2 and n % 2 == 0


def ytick_reserve(fig: Figure, labels: Iterable[str], *, ylabel: bool = False, gap: float = 0.03) -> float:
    """Left reserve (inches) that fits the widest of `labels` as y tick labels (TICK_PT, 7 pt), plus the tick and its
    pad, plus a y label (LABEL_PT, 7.97 pt) if `ylabel`; for panels with name tick labels (Fig. 4(a)) or wide
    numbers."""
    canvas = fig.canvas if isinstance(fig.canvas, FigureCanvasAgg) else FigureCanvasAgg(fig)
    r = canvas.get_renderer()
    prop = FontProperties(size=TICK_PT)
    width_px = max((r.get_text_width_height_descent(str(s), prop, ismath=_is_math(str(s)))[0] for s in labels),
                   default=0.0)
    w = width_px / fig.dpi + (mpl.rcParams["ytick.major.size"] + mpl.rcParams["ytick.major.pad"]) / BP_PER_IN
    if ylabel:
        lprop = FontProperties(size=LABEL_PT)
        _, hpx, _ = r.get_text_width_height_descent("Ag", lprop, ismath=False)
        w += hpx / fig.dpi + mpl.rcParams["axes.labelpad"] / BP_PER_IN
    return w + gap


LETTER_SPINE_GAP_PT = 2.0          # a letter ends at least this far left of its panel's y spine; not in §5


def panel_letters(axes: Sequence, letters: Sequence[str] | None = None, *, dx: float = 0.0) -> list[Text]:
    """Bold "(a)", "(b)", ... (LETTER_PT, 7.97 pt) at the top left of each panel's slot (the left edge of its y-label
    reserve), with the baseline 1.2 pt above the axes top, so that letters of one row align. Where the reserve is
    narrower than the letter (a panel that shares its left neighbor's y axis, LEFT_SHARED), the letter would sit on
    the top of its own y spine, with the descender of ")" touching it; it is then right-aligned LETTER_SPINE_GAP_PT
    left of the spine instead, reaching into the gap above the neighbor's top right corner."""
    out = []
    for i, ax in enumerate(axes):
        fig = ax.figure
        W, H = fig.get_size_inches()
        x0, y0, w, h = axes_rect_in(ax)
        slot = getattr(ax, "_sublet_slot_left_in", x0 - LEFT_LABEL)
        letter = letters[i] if letters is not None else "abcdefghijklmnopqrstuvwxyz"[i]
        t = fig.text((max(slot, 0.0) + dx) / W, (y0 + h + 1.2 / BP_PER_IN) / H, f"({letter})", ha="left",
                     va="baseline", fontsize=LETTER_PT, fontweight="bold")
        canvas = fig.canvas if isinstance(fig.canvas, FigureCanvasAgg) else FigureCanvasAgg(fig)
        width_in = t.get_window_extent(canvas.get_renderer()).width / fig.dpi
        gap = LETTER_SPINE_GAP_PT / BP_PER_IN
        if max(slot, 0.0) + dx + width_in > x0 - gap and x0 - gap - width_in >= 0.0:
            t.set_x((x0 - gap - width_in) / W)          # (not at the page's left edge: Fig. 1(a) has no spine)
        t._sublet_role = "panel_letter"
        out.append(t)
    return out


# ---------------------------------------------------------------------------------------------------------------
# Policy registry (§5 "Registry"; Okabe-Ito palette; decision 11 for the A6 and A7 labels)
GROUPS = ("sublet", "guarded", "ours", "baseline", "reference", "benchmark")   # legend order (§5)
FILLS = ("filled", "open", "line")    # "line": a line marker (x) or no marker; then the line style identifies it


@dataclass(frozen=True)
class Policy:
    key: str
    label: str
    color: str
    marker: str | None                # matplotlib marker code; None: drawn as a line only
    fill: str                         # "filled", "open" (white face) or "line"
    linestyle: str = "-"
    group: str = "baseline"
    family: str = ""                  # variants of one family may share a color within a figure
    edgecolor: str | None = None      # marker edge if not the color (yellow markers have a black edge)
    linewidth: float = LINE_PT
    markersize: float = MARKER_PT
    zorder: float = Z_DATA
    note: str = ""

    @property
    def triple(self) -> tuple[str, str, str]:
        """(color, marker, fill); for a line without markers: (color, "none", "line" + line style)."""
        if self.marker is None:
            return (self.color.upper(), "none", f"line{self.linestyle}")
        return (self.color.upper(), self.marker, self.fill)

    @property
    def text_color(self) -> str:
        return self.edgecolor or self.color

    @property
    def label_color(self) -> str:
        """The color of a direct label: text_color, darkened toward black where needed so that the text has at least
        4.5:1 contrast against white (the WCAG level for normal text; not in §5). Light policy colors (orange,
        sky blue, reddish purple) in small text otherwise print faint, in greyscale above all (IEEE: "Contrast different
        elements of the figure with both color and brightness"); the dark ones are unchanged."""
        return readable_on_white(self.text_color)


def _rel_luminance(rgb) -> float:
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


TEXT_CONTRAST = 4.5                    # direct labels against white (WCAG AA, normal text); not in §5


def readable_on_white(color: str, contrast: float = TEXT_CONTRAST) -> str:
    """`color`, or the same hue mixed with black in steps of 1% until its contrast against white, (1.05) /
    (L + 0.05) for the relative luminance L, is at least `contrast`."""
    rgb = np.asarray(mpl.colors.to_rgb(color))
    for k in range(101):
        c = rgb * (1.0 - k / 100.0)
        if 1.05 / (_rel_luminance(c) + 0.05) >= contrast:
            return mpl.colors.to_hex(c) if k else color
    return "#000000"


# theory labels: the theory grey darkened to 4.5:1 against white (#7F7F7F is 4.0:1; the lines keep #7F7F7F)
THEORY_LABEL_GREY = readable_on_white(THEORY_GREY)


_REGISTRY = (
    Policy("sublet", "Sublet", "#0072B2", "o", "filled", "-", "sublet", "sublet", linewidth=SUBLET_LINE_PT,
           markersize=SUBLET_MARKER_PT, zorder=Z_SUBLET, note="A8 around BL5 (narayana2020retrorenting)"),
    Policy("sublet_siloed", "Sublet, siloed", "#0072B2", "o", "open", "--", "sublet", "sublet",
           zorder=Z_SUBLET - 0.05, note="per-borrower sub-instance runs (Q41 (a))"),
    Policy("a7_guard", "PD heuristic + guard", "#009E73", "D", "filled", "-", "guarded", "a7", note="A8 around A7"),
    Policy("bl1_guard", "Greedy + guard", "#E69F00", "^", "filled", "-", "guarded", "bl1", note="A8 around BL1"),
    Policy("a7", "PD heuristic", "#009E73", "D", "open", "-", "ours", "a7",
           note="practical Sublet, a labeled heuristic"),
    Policy("a6", "Two-timescale PD", "#CC79A7", "h", "filled", "-", "ours", "a6", note='"Sublet as specified"'),
    Policy("a6_siloed", "Two-timescale PD, siloed", "#CC79A7", "h", "open", "--", "ours", "a6"),
    Policy("a6_red_off", "Two-timescale PD, no spare", "#CC79A7", "s", "filled", "-", "ours", "a6",
           note="supplementary figures only (MS4 C18): A6 with redundancy 'off'; a6 is its default 'rule'"),
    Policy("a6_always2", "Two-timescale PD, spare always", "#CC79A7", "P", "filled", "-", "ours", "a6",
           note="supplementary figures only (MS4 C18): A6 with redundancy 'always2'"),
    Policy("psi_01", r"$\psi$-PD, $\psi=0.1$", "#CC79A7", "<", "open", "-", "ours", "pd",
           note="supplementary figures only (MS4 C18): A5's fractional psi-PD; psi = 1 is A2 fractional"),
    Policy("psi_03", r"$\psi$-PD, $\psi=0.3$", "#CC79A7", "D", "open", "-", "ours", "pd",
           note="supplementary figures only (MS4 C18): A5's fractional psi-PD"),
    Policy("psi_05", r"$\psi$-PD, $\psi=0.5$", "#CC79A7", "p", "open", "-", "ours", "pd",
           note="supplementary figures only (MS4 C18): A5's fractional psi-PD"),
    Policy("a2_frac", "A2 fractional", "#CC79A7", "x", "line", "-", "ours", "pd", note="PD variants"),
    Policy("a2_r1", r"A2, $\bar{r}=1$", "#CC79A7", "^", "open", "-", "ours", "pd", note="PD variants"),
    Policy("a2_theory", r"A2, theory $\bar{r}$", "#CC79A7", "^", "filled", "-", "ours", "pd", note="PD variants"),
    Policy("a3", "A3", "#CC79A7", "v", "filled", "-", "ours", "pd", note="PD variants"),
    Policy("a3_rot", "A3, rotation", "#CC79A7", "d", "open", "-", "ours", "pd",
           note="supplementary figures only (MS3 C13): A3-rot, reference mode plus X3, reaction cold"),
    Policy("a4", "A4", "#CC79A7", "v", "open", "-", "ours", "pd", note="PD variants"),
    Policy("a5", "A5", "#CC79A7", "*", "filled", "-", "ours", "pd", note="PD variants"),
    Policy("rr_renew", "RR-renew", "#E69F00", "p", "filled", "-", "ours", "o1", note="BL1 never shares its figures"),
    Policy("marking", "Marking", "#E69F00", "p", "open", "-", "ours", "o1", note="BL1 never shares its figures"),
    Policy("a1", "ALG*", "#0072B2", "h", "filled", "-", "ours", "a1", note="C2-T4's rule; never with Sublet"),
    Policy("bl5", "RetroRenting-style", "#56B4E9", "s", "open", "-", "baseline", "bl5"),
    Policy("bl1", "Greedy renting", "#E69F00", "^", "open", "-", "baseline", "bl1"),
    Policy("bl2", "Per-borrower ski rental", "#D55E00", "v", "filled", "-", "baseline", "bl2"),
    Policy("bl3_n0", r"SpotHedge-style, $N_{\mathrm{Extra}}=0$", "#F0E442", "p", "filled", "-", "baseline", "bl3",
           edgecolor="#000000", note="supplementary figures only (MS4 C18): N_Extra = 0; bl3 is its default 2; a "
                                     "pentagon since U25's review (a star at 3.5 pt has no interior: its filled and "
                                     "open forms read reversed in sf_e5)"),
    Policy("bl3_n1", r"SpotHedge-style, $N_{\mathrm{Extra}}=1$", "#F0E442", "d", "filled", "-", "baseline", "bl3",
           edgecolor="#000000", note="supplementary figures only (MS4 C18): N_Extra = 1"),
    Policy("bl3", "SpotHedge-style", "#F0E442", "<", "filled", "-", "baseline", "bl3", edgecolor="#000000"),
    Policy("bl4", "CoCaR-style", "#F0E442", "P", "filled", "-", "baseline", "bl4", edgecolor="#000000"),
    Policy("prewarm", "Pre-warm", "#56B4E9", "h", "open", "-", "baseline", "prewarm",
           note="pre-warm if H >= lambda; never with BL5"),
    Policy("cold", "Always cold", "#56B4E9", "d", "filled", "-", "baseline", "prewarm",
           note="supplementary figures only (MS3 C13): the fixed cold rule; never with BL5"),
    Policy("bl6", "Notice-oblivious", "#D55E00", "X", "filled", "-", "baseline", "bl6", note="never with BL2"),
    Policy("bl0a", "All-fallback", "#4D4D4D", None, "line", "-", "reference", "references",
           linewidth=REFERENCE_POLICY_PT, zorder=Z_REFERENCE),
    Policy("bl0b", "Provision for peak", "#4D4D4D", None, "line", "-.", "reference", "references",
           linewidth=REFERENCE_POLICY_PT, zorder=Z_REFERENCE),
    Policy("opt", "OPT", "#000000", "*", "filled", "-", "benchmark", "benchmarks"),
    Policy("opt_eager", r"OPT$_{\mathrm{eager}}$", "#000000", "s", "open", "-", "benchmark", "benchmarks"),
    Policy("lb", "Lower bound", "#000000", None, "line", "--", "benchmark", "benchmarks"),
)
POLICIES: dict[str, Policy] = {p.key: p for p in _REGISTRY}

# Policy sets of the main-text figures as documented in design/figure_plan.md §1 (union over the panels). C46
# (design/ms6_spec.md M2, M4): fig3 and fig5 draw the configuration keys of Algorithm 1's defaults (bl5_g1 for the
# frozen sublet, bl5_lag for bl5, bl1_g1 for bl1_guard, a7_g1 for a7_guard); the frozen fig1 and fig4 keep theirs
FIGURE_POLICIES: dict[str, tuple[str, ...]] = {
    "fig1": ("sublet",),
    "fig2": (),
    "fig3": ("bl5_g1", "a7_g1", "bl1_g1", "a7", "a6", "bl5_lag", "bl1", "bl2"),
    "fig4": ("sublet", "sublet_siloed", "a7_guard", "a7", "a6", "a6_siloed", "bl5", "bl1", "bl2", "bl4",
             "bl0a", "bl0b", "opt"),
    "fig5": ("bl5_g1", "a2_frac", "a2_r1", "a2_theory", "a3", "rr_renew"),
    "fig6": ("rr_renew", "a2_theory", "marking"),
    "fig7": ("a1", "prewarm", "bl6"),
}

# MS3 C13 (design/sim_spec_ms3.md §2.3, §8.7): policy sets of the supplementary MS3 figures. The keys a3_rot and
# cold are used only here, never in FIGURE_POLICIES. C46 (design/ms6_spec.md M2, M4): sf_e1_sched and the sf_e11
# figures draw the configuration keys of Algorithm 1's defaults, as fig3 and fig5 do
SUPP_POLICIES: dict[str, tuple[str, ...]] = {
    "sf_e1_sched": ("bl5_g1", "a2_frac", "a2_r1", "a2_theory", "a3"),
    "sf_e1_rotation": ("a3", "a3_rot"),
    "sf_e2_por": (),
    "sf_e2_mu_ep": ("a1", "prewarm", "cold", "bl6"),
    "sf_e2_mu_cost": ("a1",),
    "sf_e2_pool": ("a1",),
    "sf_e6a": (),
    "sf_e6b": ("a6",),
    "sf_e10_rho": ("rr_renew", "a2_theory", "a3", "marking"),
    "sf_e10_cross": ("rr_renew", "a2_theory", "marking"),
    "sf_e10b": ("a3", "a4"),
    "sf_e11_inst": FIGURE_POLICIES["fig3"],
    "sf_e11_fam": ("bl5_g1", "bl5_lag", "a7", "a7_g1", "a2_theory", "a3", "rr_renew", "marking"),
    "sf_e11_guard": ("bl5_g1", "a7_g1", "bl1_g1"),
}
SUPP_ONLY_KEYS = ("a3_rot", "cold")

# MS4 C18 (design/sim_spec_ms4.md §2.3, §8.2): policy sets of the supplementary MS4 figures, beside the MS3 maps.
# The keys of SUPP_ONLY_KEYS_MS4 are used only here, never in FIGURE_POLICIES. A6 ("rule") and BL3 (N_Extra 2)
# keep their keys; E4's combiner keeps a5 and its psi = 1 PD a2_frac. C46 (design/ms6_spec.md M2, M4): the figures of
# MS4's allowance (E3, E5, E7 main) draw sublet_ms4 for the frozen sublet, and its siloed runs in the sharing line style
# (no siloed key; a6_siloed stays), bl5_lag for bl5 and a7_ms4 for a7_guard (E7's A7G ran at MS4's allowance);
# sf_e7_allow, whose axis sweeps B0 (with
# Algorithm 1's default B0 as one of its points), draws bl5_g1 (M4)
SUPP_POLICIES_MS4: dict[str, tuple[str, ...]] = {
    "sf_e3_util": ("sublet_ms4", "a6", "a6_siloed", "bl2", "bl5_lag"),
    "sf_e3_mu": ("sublet_ms4", "a6", "a6_siloed", "bl2", "opt"),
    "sf_e4": ("psi_01", "psi_03", "psi_05", "a2_frac", "a5"),
    "sf_e5": ("sublet_ms4", "a6_red_off", "a6", "a6_always2", "bl3_n0", "bl3_n1", "bl3"),
    "sf_e7_mix": ("sublet_ms4", "a7_ms4", "a7", "a6", "bl5_lag", "bl1", "bl2", "bl4"),
    "sf_e7_mu": ("sublet_ms4", "a7_ms4", "a7", "a6", "bl5_lag", "bl1", "bl2", "bl4"),
    "sf_e7_allow": ("bl5_g1", "bl5_lag"),
    "sf_e8": (),
}
SUPP_ONLY_KEYS_MS4 = ("psi_01", "psi_03", "psi_05", "a6_red_off", "a6_always2", "bl3_n0", "bl3_n1")

# MS4 C18: the sizes of the supplementary MS4 figures (§8.2); a figure script registers its own size again, which
# register_supplementary accepts when it is the same. C46 (design/ms6_spec.md M3, M4): sf_e7_mu 2.5 in high (was 2.2),
# since its legend needs a third row for the two guards' labels at MS4's allowance and its panels keep their height.
# C59 (RC19(3)): sf_e3_mu 2.4 in high (was 2.2), one legend row more for the guard's label in words on two lines
for _name, _width, _height in (("sf_e3_util", "W2", 2.2), ("sf_e3_mu", "W1", 2.4), ("sf_e4", "W1", 2.2),
                               ("sf_e5", "W2", 2.5), ("sf_e7_mix", "W2", 2.2), ("sf_e7_mu", "W2", 2.5),
                               ("sf_e7_allow", "W1", 2.2), ("sf_e8", "W1", 2.2)):
    register_supplementary(_name, _width, _height)

# MS5 C29 (design/sim_spec_ms5.md §2.3, §7): policy sets of the supplementary MS5 figures, beside the MS3 and MS4
# maps, with registry keys only; lb, the computed lower bound (black, dashed), draws E9's LP bound (§7.2). C46
# (design/ms6_spec.md M2, M4): S1 and E9 ran at MS4's allowance, so both draw sublet_ms4
SUPP_POLICIES_MS5: dict[str, tuple[str, ...]] = {
    "sf_s1": ("sublet_ms4",),
    "sf_e9": ("sublet_ms4", "a6", "lb"),
    "sf_slack": (),
}

# MS5 C29: the sizes of the supplementary MS5 figures (§7.1-§7.3), registered as MS4's are
for _name, _width, _height in (("sf_s1", "W2", 2.5), ("sf_e9", "W2", 2.2), ("sf_slack", "W2", 2.5)):
    register_supplementary(_name, _width, _height)
del _name, _width, _height

# MS5b C41 (design/sublet_v2.md §11, W7, W8, W12): the registry keys of the MS5b figures and floats, one per tag of
# the confirmation that a figure draws (the tags of ms5b_common.TAGS in the notes). "Sublet" is A8P around A9
# (sublet_v2) in every MS5b figure; the legacy keys of LEGACY_KEYS keep their labels until MS6 (W8). Colors: Sublet's
# blue for A9, its decomposition, Sublet one-way and Sublet's lagged and siloed runs (family sublet), BL1's orange and
# BL5's sky blue for their variants and transplants (families bl1, bl5), and BL3-0 in green, not yellow, since bl3_n0
# and bl4 share #F0E442. A key whose label is an earlier key's takes that key's (color, marker, fill): sublet_v2 and
# sublet_v2_siloed sublet's and sublet_siloed's, bl1_gp bl1_guard's, bl5_cur bl5's (bl3_0 bl3_n0's marker). Within
# every set of SUPP_POLICIES_MS5B and fig4v2 no two keys share a (marker, fill), whatever their colors, so that the
# series stay apart in greyscale (BL1's orange and BL5's sky blue print alike); no key takes a (color, marker) pair
# that tests/test_ms3_additions.py or test_ms4_additions.py pins (a3_rot, cold, the psi-PDs, the A6 modes, bl3_n0,
# bl3_n1).
_C41 = "MS5b C41 (design/sublet_v2.md §11, W7): "
_REGISTRY_MS5B = (
    Policy("sublet_v2", "Sublet", "#0072B2", "o", "filled", "-", "sublet", "sublet", linewidth=SUBLET_LINE_PT,
           markersize=SUBLET_MARKER_PT, zorder=Z_SUBLET,
           note=_C41 + "tag Sublet: A8P around A9 at the allowance min{W_k, LB'} (kappa None)"),
    Policy("sublet_v2_siloed", "Sublet, siloed", "#0072B2", "o", "open", "--", "sublet", "sublet",
           zorder=Z_SUBLET - 0.05, note=_C41 + "Sublet's per-borrower sub-instance runs of E3 (part e3, siloed)"),
    Policy("sublet_v2_lag", "Sublet, lagged", "#0072B2", "v", "filled", "-", "sublet", "sublet",
           note=_C41 + "tag Sublet-lag: Sublet with inner A9 on slot t - 1's demand (part second)"),
    Policy("sublet_1way", "Sublet, one-way", "#0072B2", "D", "filled", "-", "guarded", "sublet",
           note=_C41 + "tag Sublet-1way: A8P with project false around A9 at Sublet's allowance"),
    Policy("bl1_gp", "Greedy + guard", "#E69F00", "^", "filled", "-", "guarded", "bl1",
           note=_C41 + "tag BL1-GP: A8P around BL1 at Sublet's allowance"),
    Policy("bl1_g1", "Greedy + one-way guard", "#E69F00", "v", "filled", "-", "guarded", "bl1",
           note=_C41 + "tag BL1-G: A8 around BL1 at Algorithm 1's defaults (E11's configuration; part fam)"),
    Policy("bl5_g1", "Lagged RetroRenting + one-way guard", "#56B4E9", ">", "filled", "-", "guarded", "bl5",
           note=_C41 + "tag BL5-G: A8 around the lagged BL5 at Algorithm 1's defaults (E11's configuration; part fam)"),
    # C59 (RC19(3)): the allowance in words, as the main text names it (as built "($B_0=10\%$ BL0a)")
    Policy("sublet_ms4", r"Lagged RetroRenting + one-way guard ($B_0=10\%$ of the all-fallback bill)", "#56B4E9", "<",
           "filled", "-",
           "guarded", "bl5", note=_C41 + "tag Sublet-MS4: A8 around the lagged BL5, B0 = 0.1 BL0a (MS4's allowance)"),
    Policy("a9", "Critical-ratio renting", "#0072B2", "s", "filled", "-", "ours", "sublet",
           note=_C41 + "tag A9: the inner policy alone"),
    Policy("cr", "Critical-ratio planning", "#0072B2", ">", "filled", "-", "ours", "sublet",
           note=_C41 + "tag CR: A9's planning half alone (A9.1, A9.2)"),
    Policy("a9_nombb", "Critical-ratio renting, no make-before-break", "#0072B2", "d", "filled", "-", "ours",
           "sublet", note=_C41 + "tag A9-noMBB: ablation of A9.4"),
    Policy("a9_nocommit", "Critical-ratio renting, no commitment rule", "#0072B2", "d", "open", "-", "ours", "sublet",
           note=_C41 + "tag A9-noCommit: ablation of A9.3's commitment rule"),
    Policy("a9_noins", "Critical-ratio renting, no insurance", "#0072B2", "p", "open", "-", "ours", "sublet",
           note=_C41 + "tag A9-noIns: ablation of C2-T2's insurance"),
    Policy("a9_kstar", r"Critical-ratio renting, $k^{\ast}$ contract", "#0072B2", "h", "open", "-", "ours", "sublet",
           note=_C41 + "tag A9-kstar: the baselines' k* for every purchase (ablation of A9.3's contract rule)"),
    Policy("a9_static", "Critical-ratio renting, no site marking", "#0072B2", "P", "open", "-", "ours", "sublet",
           note=_C41 + "tag A9-static: BL1's static site order (ablation of A9.5's marking)"),
    Policy("a9_lag", "Critical-ratio renting, lagged", "#0072B2", "X", "open", "-", "ours", "sublet",
           note=_C41 + "tag A9-lag: A9 on slot t - 1's demand (part second)"),
    Policy("bl1n", "Greedy + notice layer", "#E69F00", "D", "open", "-", "ours", "bl1",
           note=_C41 + "tag BL1N: BL1's planning with A9's revocation layer A9.3-A9.5 (transplant)"),
    Policy("bl5n", "RetroRenting + notice layer", "#56B4E9", "X", "filled", "-", "ours", "bl5",
           note=_C41 + "tag BL5N: BL5-cur with A9.3's base contract and A9.4 (partial transplant)"),
    Policy("bl5_cur", "RetroRenting-style", "#56B4E9", "s", "open", "-", "baseline", "bl5",
           note=_C41 + "tag BL5-cur: BL5 on the revealed slot (use_current_slot), the main RetroRenting-style row"),
    Policy("bl5_tau60", r"RetroRenting, $\tau\geq1$ h", "#56B4E9", ">", "open", "-", "baseline", "bl5",
           note=_C41 + "tag BL5-tau60: BL5-cur over the contracts with tau_k at least 60 min"),
    Policy("bl5_lag", "RetroRenting-style, lagged", "#56B4E9", "<", "open", "-", "baseline", "bl5",
           note=_C41 + "tag BL5: BL5's lagged build (the legacy bl5's policy)"),
    Policy("bl1_bo", "Greedy, back-off", "#E69F00", "v", "open", "-", "baseline", "bl1",
           note=_C41 + "tag BL1-BO: BL1 with the generic site back-off (backoff_cap 288)"),
    Policy("bl1_lag", "Greedy renting, lagged", "#E69F00", ">", "filled", "-", "baseline", "bl1",
           note=_C41 + "tag BL1-lag: BL1 on slot t - 1's demand (part second)"),
    Policy("bl3_0", r"SpotHedge-style, $N_{\mathrm{Extra}}=0$", "#009E73", "p", "filled", "-", "baseline", "bl3",
           note=_C41 + "tag BL3-0: BL3 with n_extra 0; green, since bl3_n0 (the same policy in MS4's E5) is yellow "
                       "like bl4"),
)
# each new key follows an anchor of its family in the registry order, which legend_order reads within a group (the
# MS4 C18 rule); the order of the earlier keys among themselves is unchanged
_MS5B_AFTER = {"sublet_siloed": ("sublet_v2", "sublet_v2_siloed", "sublet_v2_lag"),
               "bl1_guard": ("sublet_1way", "bl1_gp", "bl1_g1", "bl5_g1", "sublet_ms4", "a9", "cr", "a9_nombb",
                             "a9_nocommit", "a9_noins", "a9_kstar", "a9_static", "a9_lag", "bl1n", "bl5n"),
               "bl5": ("bl5_cur", "bl5_tau60", "bl5_lag"), "bl1": ("bl1_bo", "bl1_lag"), "bl3": ("bl3_0",)}
_new = {p.key: p for p in _REGISTRY_MS5B}
_old = dict(POLICIES)
if set(_new) & set(_old) or sorted(k for ks in _MS5B_AFTER.values() for k in ks) != sorted(_new):
    raise StyleError("C41: the MS5b keys must be new and placed once each")
POLICIES.clear()
for _k, _p in _old.items():
    POLICIES[_k] = _p
    POLICIES.update((k, _new[k]) for k in _MS5B_AFTER.get(_k, ()))
MS5B_KEYS: tuple[str, ...] = tuple(_new)
# W7, W8: never in an MS5b figure; C46 (design/ms6_spec.md M2, M3): with a7_guard, which a7_g1 and a7_ms4 supersede in
# every figure but the frozen fig4; none is drawn with an MS5b or MS6 key (check_legacy), and each keeps its label and
# triple
LEGACY_KEYS = ("sublet", "sublet_siloed", "bl5", "bl1_guard", "a7_guard")
del _k, _p, _new, _old

# MS6 C46 (design/ms6_spec.md §1.1 M3, §2 U42): a7_g1, A8 around A7 under its paper name (design/ms6/
# inventory_consistency.md §5; Table II v2's row), in A7's green (family a7: a policy and its guarded version share a
# color) with a filled thin diamond, as BL5's and BL1's guarded configurations turn their inner policy's open marker
# into another filled one. Its triple and its (color, marker) pair are its own: a7_guard's filled diamond keeps the
# label "PD heuristic + guard" (the two never share a figure: check_legacy), and the thin diamonds of a3_rot, cold,
# bl3_n1 and the A9 ablations are in other colors. Placed after a7_guard, so that legend_order lists it with the
# guarded policies. a7_ms4 is the same guard at MS4's allowance (E7's and S1's tag A7G), as sublet_ms4 is bl5_g1's: its
# label carries sublet_ms4's allowance suffix, so that the two guards that E7 and S1 ran at that allowance print it
# alike (M4 keys a configuration by its allowance), in the same green with a filled X, a triple and a (color, marker)
# pair that no other key has and a (marker, fill) that no other key of sf_e7_mix's and sf_e7_mu's sets draws; placed
# after a7_g1.
_C46 = "MS6 C46 (design/ms6_spec.md M3, M4): "
_REGISTRY_MS6 = (
    Policy("a7_g1", "PD heuristic + one-way guard", "#009E73", "d", "filled", "-", "guarded", "a7",
           note=_C46 + "tag PS-G: A8 around A7 at Algorithm 1's defaults (E11; fig3, sf_e11_*)"),
    # C59 (RC19(3)): sublet_ms4's allowance suffix in words (as built "($B_0=10\%$ BL0a)")
    Policy("a7_ms4", r"PD heuristic + one-way guard ($B_0=10\%$ of the all-fallback bill)", "#009E73", "X", "filled",
           "-", "guarded", "a7",
           note=_C46 + "tag A7G: A8 around A7 at MS4's allowance B0 = 0.1 BL0a (E7 main, S1; sf_e7_mix, sf_e7_mu, the "
                       "E7 and S1 tables), as sublet_ms4 is the guard around the lagged BL5 at it"),
)
_MS6_AFTER = {"a7_guard": ("a7_g1", "a7_ms4")}
_new = {p.key: p for p in _REGISTRY_MS6}
_old = dict(POLICIES)
if set(_new) & set(_old) or sorted(k for ks in _MS6_AFTER.values() for k in ks) != sorted(_new):
    raise StyleError("C46: the MS6 keys must be new and placed once each")
POLICIES.clear()
for _k, _p in _old.items():
    POLICIES[_k] = _p
    POLICIES.update((k, _new[k]) for k in _MS6_AFTER.get(_k, ()))
MS6_KEYS: tuple[str, ...] = tuple(_new)
del _k, _p, _new, _old, _C46

# C46 (M1): Fig. 1 of the paper is fig1v2, at the frozen fig1's size, with (a) the timeline and (b) one illustrative run
# of Sublet (A8P around A9); the frozen fig1 stays registered (LEGACY_PENDING) and is not in the manuscript
FIGURES["fig1v2"] = FigureSpec("fig1v2", FIGURES["fig1"].width, FIGURES["fig1"].height_in)
FIGURE_POLICIES["fig1v2"] = ("sublet_v2",)

# MS7 C58 (design/ms7/w_spec.md §2.2, §4 W-G1): Fig. 1 of the paper is fig1v3, a schematic at two-column width (W2 x
# 1.70 in since C62, 1.9 in before) of the lease (a), the platform's control plane (b) and one slot of Algorithm 1 (c), in Sublet's color; fig1v2
# stays registered and is not in the manuscript
FIGURES["fig1v3"] = FigureSpec("fig1v3", "W2", 1.70)                     # C62: 1.9 -> 1.70 in
FIGURE_POLICIES["fig1v3"] = ("sublet_v2",)

# C41: Fig. 4 of the paper is fig4v2 (W1, W6; the frozen fig4 of MS4 stays registered and is not in the manuscript),
# with the union of W1's panels (a) and (c), BL0a's reference line and BL0b's arrow
FIGURES["fig4v2"] = FigureSpec("fig4v2", "W2", 2.4)
FIGURE_POLICIES["fig4v2"] = ("sublet_v2", "bl1_gp", "bl1n", "bl5n", "bl5_cur", "bl5_tau60", "bl1", "bl1_bo", "bl2",
                             "bl3_0", "bl4", "bl0a", "bl0b")

# MS7 C58 (design/ms7/w_spec.md §2.8, §4 W-G2): the registry keys of the MS7 tags that a main-text figure or table
# prints (the tags of sublet.experiments.ms7_baselines in the notes), each new and appended to the registry (as built:
# not after an anchor of its family, C41's rule, so that the anchors' successors that the MS5b tests pin stay; a9p is
# the one key of its group in fig4v3's legend and no figure draws mpc, so no legend groups them otherwise): a9p in
# Sublet's blue (family sublet), with a filled left triangle (a filled star since C61), a (marker, fill) that no other
# key of fig4v3's set has; mpc in CoCaR-style's yellow with its black edge (family bl4: MPC is a receding-horizon form
# of CoCaR-style's window LP, baselines/mpc.py), with a filled diamond, a triple of its own. Table IV prints both.
_C58 = "MS7 C58 (design/ms7/w_spec.md §2.8, unit W-G2): "
_REGISTRY_MS7 = (
    Policy("a9p", "Protected-only renting", "#0072B2", "*", "filled", "-", "ours", "sublet",
           note=_C58 + "tag A9-P of e7r (registry A9P): A9 with every client insured at its flagged site, no revocable "
                       "lease (what revocable leasing is worth)"),
    Policy("mpc", "MPC", "#F0E442", "D", "filled", "-", "baseline", "bl4", edgecolor="#000000",
           note=_C58 + "tag MPC-T of e7r: the MPC baseline (receding-horizon LP with forecasts, online-I1) at the "
                       "setting of rule T of e7r_select.py (least median trace cost on the development weeks)"),
)
_new = {p.key: p for p in _REGISTRY_MS7}
if set(_new) & set(POLICIES) or len(_new) != len(_REGISTRY_MS7):
    raise StyleError("C58: the MS7 keys must be new and placed once each")
POLICIES.update(_new)
MS7_KEYS: tuple[str, ...] = tuple(_new)
del _new, _C58

# MS7 C58 (design/ms7/w_spec.md §2.8, cut K1; unit W-G2): Fig. 3 of the paper is fig4v3 (figs/fig4_v3.py), at fig4v2's
# size: (a) fig4v2's (a), each bar's name followed by its policy's marker, which keys (c)'s baselines; (b) the per-week
# margins; (c) the trace cost against W0 of Sublet, critical-ratio planning, the ablations of critical-ratio renting,
# protected-only critical-ratio renting and (a)'s baselines, with the notice layer added to greedy and RetroRenting-style
# renting drawn as arrows to bl1n and bl5n; BL0a's reference line and BL0b's arrow in (a). fig4v2 stays registered and
# is not in the manuscript
FIGURES["fig4v3"] = FigureSpec("fig4v3", "W2", 2.4)
FIGURE_POLICIES["fig4v3"] = ("sublet_v2", "cr", "a9_nombb", "a9_nocommit", "a9_kstar", "a9_static", "a9p", "bl1n",
                             "bl5n", "bl5_cur", "bl5_tau60", "bl1", "bl1_bo", "bl2", "bl3_0", "bl4", "bl0a", "bl0b")
# MS7 C58: the keys that the MS7 tables print, in row order: Table IV (figs/table3_v3.py, label tab:e7) and Table V
# (figs/table5_alglb.py, label tab:alglb)
TABLE_POLICIES_MS7: dict[str, tuple[str, ...]] = {
    "table3_v3": ("sublet_v2", "bl1_gp", "bl1n", "bl5n", "bl1", "bl1_bo", "bl5_cur", "bl5_tau60", "bl2", "bl3_0", "bl4",
                  "mpc", "a9p", "bl0a"),
    "table5_alglb": ("sublet_v2", "bl1_gp", "bl1", "bl1_bo", "bl5_cur", "bl5_tau60", "bl3_0", "bl4", "bl0a"),
}

# C41: policy sets of the supplementary MS5b figures (W3, W4), beside the MS3-MS5 maps. sf_e3_v2 draws siloed runs in
# the sharing line style (env_linestyle('sharing', 'siloed')), so A9, BL1, BL5-cur and Sublet-MS4 need no siloed key;
# sf_fam_v2 leaves RR_RENEW and MARKING to its tables, since their orange is BL1's (another family; check_policies);
# sf_e7_links is MS4's pooling panel with the MS5b keys of its three policies; sf_e7_grid_dev the keys it draws (U39b).
SUPP_POLICIES_MS5B: dict[str, tuple[str, ...]] = {
    "sf_e3_v2": ("sublet_v2", "sublet_v2_siloed", "sublet_ms4", "a9", "bl5_cur", "bl1", "opt"),
    "sf_e7_intensity": ("sublet_v2", "bl1_gp", "sublet_ms4", "a9", "bl1n", "bl5n", "bl5_cur", "bl5_tau60", "bl1",
                        "bl1_bo", "bl3_0", "bl4"),
    "sf_e7_decomp": ("sublet_v2", "sublet_1way", "bl1_gp", "a9", "cr", "a9_nombb", "a9_nocommit", "a9_noins",
                     "a9_kstar", "a9_static", "bl1n", "bl5n", "bl5_cur", "bl1"),
    "sf_e7_boundary": ("sublet_v2", "sublet_v2_lag", "bl1_gp", "sublet_ms4", "a9", "a9_lag", "bl1n", "bl5n", "bl5_cur",
                       "bl5_tau60", "bl5_lag", "bl1", "bl1_bo", "bl1_lag", "bl3_0", "bl4"),
    # U39b: the seven keys sf_e7_grid_dev draws (part grid's Sublet, A9, BL1-GP, lagged BL5 and BL1, and E11's BL1-G,
    # BL5-G and BL5); its table e7v2_grid.tex names the other E7 tags. C41 listed the 22 E7 tags, which no panel draws
    # legibly, and E11's guarded rows take the (marker, fill) of two of them (bl2, cr)
    "sf_e7_grid_dev": ("sublet_v2", "bl1_gp", "bl1_g1", "bl5_g1", "a9", "bl5_lag", "bl1"),
    "sf_fam_v2": ("sublet_v2", "bl1_gp", "bl1_g1", "bl5_g1", "a9", "a9_noins"),
    "sf_e7_links": ("sublet_ms4", "bl5_lag", "bl1"),
}

# C41: the sizes of the supplementary MS5b figures (W4's registered set), registered as MS4's and MS5's are. C59
# (RC19(3)): sf_e7_boundary 2.5 in high (was 2.4), for the third line of the guard's name in words
for _name, _width, _height in (("sf_e3_v2", "W2", 2.2), ("sf_e7_intensity", "W2", 2.5), ("sf_e7_decomp", "W2", 2.4),
                               ("sf_e7_boundary", "W2", 2.5), ("sf_e7_grid_dev", "W2", 2.4), ("sf_fam_v2", "W2", 2.2),
                               ("sf_e7_links", "W1", 2.2)):
    register_supplementary(_name, _width, _height)
del _name, _width, _height, _C41

# C41 (W8): every frozen figure that draws a legacy key, with the MS6 item that settles it (design Table 5.12, MS6's
# entry gate: the relabel sublet -> "Lagged RetroRenting + one-way guard", sublet_siloed, bl5 -> "RetroRenting-style,
# lagged", bl1_guard -> "Greedy + one-way guard", then the rebuild and the print check of these figures). C46
# (design/ms6_spec.md M1, M2, M4): the gate settles the other fourteen by drawing the configuration keys (the sets
# above); fig1 and fig4 stay frozen, each replaced in the manuscript by its v2 figure
LEGACY_PENDING: dict[str, str] = {
    "fig1": "MS6 (W8, M1): not in the manuscript (its Fig. 1 is fig1v2, panel (b) redrawn from an illustrative "
            "A8P(A9) run); the frozen MS3 output is not relabeled, since the MS3 claims report reads fig1.json",
    "fig4": "W1, W6: not in the manuscript (its Fig. 4 is fig4v2); the frozen MS4 output is not relabeled",
}

# MS7 C58 (design/ms7/w_spec.md §4, unit W-G4; registration of unit W-G4-0): the registry keys of the MS7 tags that the
# supplementary figures and tables of the runs X1-X5 print (design/ms7/registration.md §2; the tags in the notes and in
# MS7_KEY_OF_TAG), appended after MS7_KEYS as those were (the C41 anchors keep their successors), in the order that
# legend_order then gives a figure: each kind in the family order of the revealed rows (RetroRenting-style, greedy, ski
# rental, SpotHedge-style, CoCaR-style). Each key has a (color, marker, fill) triple and a label that no other key has,
# its family's color (BL1's orange, BL2's vermillion, BL3's green as bl3_0's, BL4's and MPC's yellow with its black edge,
# BL5's sky blue; the lookahead MPC the benchmarks' black, in their group, legend last: a labeled reference that no
# comparison set holds), and no (color, marker) pair that tests/test_ms3_additions.py or test_ms4_additions.py pins.
# Labels in the registry's style: X1's lagged forms "<label>, lagged" (Greedy + guard's "inner lagged": its guard's test
# reads the realized slot, e7c_tags), X4's contract-only transplants "<label>, $\bar{k}$ contract" (as a9_kstar's
# "$k^{\ast}$ contract"), SpotHedge-style's spares "$N_{\mathrm{Extra}}=n$ per pool" (as built) or "per LLM", the tuned
# settings "<family label>, tuned (trace)" (rule T of e7r_select.py, least median trace cost) and "(worst case)" (rule
# W, least median W0); MPC-T keeps mpc's "MPC" (Table IV and the glossary print it, its setting tuned), the as-built MPC
# is "MPC, as built". Markers: the lagged keys distinct in (marker, fill) within sf_lag_v2's set; the spares a right
# triangle per pool and a hexagon per LLM, filled for one spare and open for two; a tuned family's T filled and W open
# of one marker (BL1 thin diamond, BL2 right and BL3 left triangle, BL4 hexagon, MPC mpc's diamond; BL5 a filled up and
# an open down triangle, since no sky-blue marker is free in both fills); within every set of SUPP_POLICIES_MS7, and
# for the tuned settings beside the as-built baselines and Sublet, no (marker, fill) twice
# (tests/test_ms7_supp_registry.py)
_G4 = "MS7 C58 (design/ms7/w_spec.md §4, unit W-G4): "
_REGISTRY_MS7_SUPP = (
    # X1 (e7c_tags.TAGS, part lag): the lagged forms of the notice-aware and primary baselines; Sublet-lag, A9-lag,
    # BL1-lag and BL5 (the lagged RetroRenting-style) have their MS5b keys
    Policy("bl1_gp_lag", "Greedy + guard, inner lagged", "#E69F00", "s", "filled", "-", "guarded", "bl1",
           note=_G4 + "tag BL1-GP-lag of e7c: BL1-GP with the inner BL1 on slot t - 1's demand; the guard's test reads "
                      "the realized slot"),
    Policy("bl1n_lag", "Greedy + notice layer, lagged", "#E69F00", "D", "filled", "-", "ours", "bl1",
           note=_G4 + "tag BL1N-lag of e7c: BL1N on slot t - 1's demand"),
    Policy("bl5n_lag", "RetroRenting + notice layer, lagged", "#56B4E9", "D", "open", "-", "ours", "bl5",
           note=_G4 + "tag BL5N-lag of e7c: BL5N in BL5's lagged build"),
    Policy("bl5_tau60_lag", r"RetroRenting, $\tau\geq1$ h, lagged", "#56B4E9", "^", "open", "-", "baseline", "bl5",
           note=_G4 + "tag BL5-tau60-lag of e7c: BL5-tau60 in BL5's lagged build"),
    Policy("bl1_bo_lag", "Greedy, back-off, lagged", "#E69F00", "<", "filled", "-", "baseline", "bl1",
           note=_G4 + "tag BL1-BO-lag of e7c: BL1-BO on slot t - 1's demand"),
    Policy("bl2_lag", "Per-borrower ski rental, lagged", "#D55E00", "v", "open", "-", "baseline", "bl2",
           note=_G4 + "tag BL2-lag of e7c: BL2 on slot t - 1's demand (siloed runner)"),
    Policy("bl3_0_lag", r"SpotHedge-style, $N_{\mathrm{Extra}}=0$, lagged", "#009E73", "p", "open", "-", "baseline",
           "bl3", note=_G4 + "tag BL3-0-lag of e7c: BL3-0 on slot t - 1's demand"),
    Policy("bl4_lag", "CoCaR-style, lagged", "#F0E442", "P", "open", "-", "baseline", "bl4", edgecolor="#000000",
           note=_G4 + "tag BL4-lag of e7c: BL4 with demand 'previous0' (no lookahead in the first window)"),
    # X4 (ms7_baselines.MS7_TAGS): the contract-only transplants (A9.3's base contract kbar in place of k*)
    Policy("bl5_cur_c2", r"RetroRenting-style, $\bar{k}$ contract", "#56B4E9", "p", "open", "-", "baseline", "bl5",
           note=_G4 + "tag BL5-cur-c2 of e7r: BL5-cur with kbar contracts (BL5N without make-before-break)"),
    Policy("bl1_c2", r"Greedy renting, $\bar{k}$ contract", "#E69F00", "<", "open", "-", "baseline", "bl1",
           note=_G4 + "tag BL1-c2 of e7r: BL1's planning (A9 with BL1's flags) with kbar contracts"),
    Policy("bl2_c2", r"Per-borrower ski rental, $\bar{k}$ contract", "#D55E00", "s", "filled", "-", "baseline", "bl2",
           note=_G4 + "tag BL2-c2 of e7r: BL2 with kbar contracts (siloed runner)"),
    Policy("bl3_0_c2", r"SpotHedge-style, $N_{\mathrm{Extra}}=0$, $\bar{k}$ contract", "#009E73", "^", "filled", "-",
           "baseline", "bl3", note=_G4 + "tag BL3-0-c2 of e7r: BL3-0 with kbar contracts"),
    Policy("bl4_c2", r"CoCaR-style, $\bar{k}$ contract", "#F0E442", "v", "open", "-", "baseline", "bl4",
           edgecolor="#000000", note=_G4 + "tag BL4-c2 of e7r: BL4 with kbar in its contract sets"),
    # X4: SpotHedge-style with spares, per pool as built (also while N_Tar = 0) and per LLM (none while N_Tar = 0, kbar)
    Policy("bl3_1", r"SpotHedge-style, $N_{\mathrm{Extra}}=1$ per pool", "#009E73", ">", "filled", "-", "baseline",
           "bl3", note=_G4 + "tag BL3-1 of e7r: BL3 with one spare per pool, as built (MS4 E5's BL3-1; bl3_n1's "
                             "policy, in BL3's MS5b green)"),
    Policy("bl3_2", r"SpotHedge-style, $N_{\mathrm{Extra}}=2$ per pool", "#009E73", ">", "open", "-", "baseline", "bl3",
           note=_G4 + "tag BL3-2 of e7r and of s1v2.LOCAL_TAGS (E5 v2): BL3 at its default n_extra 2, as built (bl3's "
                      "policy, in BL3's MS5b green)"),
    Policy("bl3_1_llm", r"SpotHedge-style, $N_{\mathrm{Extra}}=1$ per LLM", "#009E73", "h", "filled", "-", "baseline",
           "bl3", note=_G4 + "tag BL3-1-llm of e7r: one spare per LLM, none while N_Tar = 0, kbar contracts"),
    Policy("bl3_2_llm", r"SpotHedge-style, $N_{\mathrm{Extra}}=2$ per LLM", "#009E73", "h", "open", "-", "baseline",
           "bl3", note=_G4 + "tag BL3-2-llm of e7r: two spares per LLM, none while N_Tar = 0, kbar contracts"),
    # X4: the tuned settings, rules T and W of e7r_select.py (tags '<family>-T', '<family>-W'; MPC-T is mpc)
    Policy("bl5_t", "RetroRenting-style, tuned (trace)", "#56B4E9", "^", "filled", "-", "baseline", "bl5",
           note=_G4 + "tag BL5-T of e7r: BL5's setting of rule T (least median r0 under L-tr on weeks 113-116)"),
    Policy("bl5_w", "RetroRenting-style, tuned (worst case)", "#56B4E9", "v", "open", "-", "baseline", "bl5",
           note=_G4 + "tag BL5-W of e7r: BL5's setting of rule W (least median W0 on weeks 113-116)"),
    Policy("bl1_t", "Greedy renting, tuned (trace)", "#E69F00", "d", "filled", "-", "baseline", "bl1",
           note=_G4 + "tag BL1-T of e7r: BL1's setting of rule T"),
    Policy("bl1_w", "Greedy renting, tuned (worst case)", "#E69F00", "d", "open", "-", "baseline", "bl1",
           note=_G4 + "tag BL1-W of e7r: BL1's setting of rule W"),
    Policy("bl2_t", "Per-borrower ski rental, tuned (trace)", "#D55E00", ">", "filled", "-", "baseline", "bl2",
           note=_G4 + "tag BL2-T of e7r: BL2's setting of rule T"),
    Policy("bl2_w", "Per-borrower ski rental, tuned (worst case)", "#D55E00", ">", "open", "-", "baseline", "bl2",
           note=_G4 + "tag BL2-W of e7r: BL2's setting of rule W"),
    Policy("bl3_t", "SpotHedge-style, tuned (trace)", "#009E73", "<", "filled", "-", "baseline", "bl3",
           note=_G4 + "tag BL3-T of e7r: BL3's setting of rule T"),
    Policy("bl3_w", "SpotHedge-style, tuned (worst case)", "#009E73", "<", "open", "-", "baseline", "bl3",
           note=_G4 + "tag BL3-W of e7r: BL3's setting of rule W"),
    Policy("bl4_t", "CoCaR-style, tuned (trace)", "#F0E442", "h", "filled", "-", "baseline", "bl4", edgecolor="#000000",
           note=_G4 + "tag BL4-T of e7r: BL4's setting of rule T"),
    Policy("bl4_w", "CoCaR-style, tuned (worst case)", "#F0E442", "h", "open", "-", "baseline", "bl4",
           edgecolor="#000000", note=_G4 + "tag BL4-W of e7r: BL4's setting of rule W"),
    # X4: MPC as built (tuning and confirmation weeks), its W setting, and the oracle forecast (L-tr and L-hon only)
    Policy("mpc_built", "MPC, as built", "#F0E442", "s", "filled", "-", "baseline", "bl4", edgecolor="#000000",
           note=_G4 + "tag MPC of e7r: the MPC baseline at its defaults (persistence forecast, W 60 min, replan every "
                      "slot, k*), the grid's g00"),
    Policy("mpc_w", "MPC, tuned (worst case)", "#F0E442", "D", "open", "-", "baseline", "bl4", edgecolor="#000000",
           note=_G4 + "tag MPC-W of e7r: MPC's setting of rule W (mpc is MPC-T)"),
    Policy("mpc_oracle", "MPC, oracle forecast", "#000000", "d", "filled", "-", "benchmark", "benchmarks",
           note=_G4 + "tag MPC-oracle of e7r: MPC with the realized demand of the window (lookahead 60 min), a labeled "
                      "reference that no comparison set holds"),
)
_new = {p.key: p for p in _REGISTRY_MS7_SUPP}
if set(_new) & set(POLICIES) or len(_new) != len(_REGISTRY_MS7_SUPP):
    raise StyleError("C58 (W-G4): the MS7 supplementary keys must be new and placed once each")
POLICIES.update(_new)
MS7_SUPP_KEYS: tuple[str, ...] = tuple(_new)
del _new

# MS7 C58 (W-G4): the registry key of each MS7 tag (the tags of e7c_tags.TAGS, ms7_baselines.MS7_TAGS, the tuned tags
# of e7r_select.py and s1v2.LOCAL_TAGS that no MS5b key draws); the confirmation's tags, which X1-X5 also run, keep
# their MS5b keys (figs/supp/ms5b_e7_lib.KEY_OF_TAG)
MS7_KEY_OF_TAG: dict[str, str] = {
    "BL1-GP-lag": "bl1_gp_lag", "BL1N-lag": "bl1n_lag", "BL5N-lag": "bl5n_lag", "BL5-tau60-lag": "bl5_tau60_lag",
    "BL1-BO-lag": "bl1_bo_lag", "BL2-lag": "bl2_lag", "BL3-0-lag": "bl3_0_lag", "BL4-lag": "bl4_lag",
    "BL5-cur-c2": "bl5_cur_c2", "BL1-c2": "bl1_c2", "BL2-c2": "bl2_c2", "BL3-0-c2": "bl3_0_c2", "BL4-c2": "bl4_c2",
    "A9-P": "a9p", "BL3-1": "bl3_1", "BL3-2": "bl3_2", "BL3-1-llm": "bl3_1_llm", "BL3-2-llm": "bl3_2_llm",
    "BL5-T": "bl5_t", "BL5-W": "bl5_w", "BL1-T": "bl1_t", "BL1-W": "bl1_w", "BL2-T": "bl2_t", "BL2-W": "bl2_w",
    "BL3-T": "bl3_t", "BL3-W": "bl3_w", "BL4-T": "bl4_t", "BL4-W": "bl4_w",
    "MPC": "mpc_built", "MPC-T": "mpc", "MPC-W": "mpc_w", "MPC-oracle": "mpc_oracle",
}
if len(set(MS7_KEY_OF_TAG.values())) != len(MS7_KEY_OF_TAG) or not set(MS7_KEY_OF_TAG.values()) <= set(POLICIES):
    raise StyleError("C58 (W-G4): MS7_KEY_OF_TAG must map each tag to its own registry key")

# MS7 C58 (W-G4): the policy sets of the supplementary figures of X1-X5, each in legend order, and their sizes (the
# closest existing supplementary figure's: sf_e7_decomp's W2 x 2.4 in for the E7-type figures, sf_e7_intensity's for the
# stress regimes, sf_s1's, sf_e5's, sf_e8's and sf_e9's for X3's); a figure script registers its size again, which
# register_supplementary accepts when it is the same. Each writer changes only its own block below (a set must keep
# check_policies, unique labels and no (marker, fill) twice; a size must be one that tests/test_figs_style.py's ink
# tests cover)
SUPP_POLICIES_MS7: dict[str, tuple[str, ...]] = {}
# W-G4 block A (sf_lag_v2, sf_oos)
# X1 (e7c_analysis.py): the eleven lagged tags of part lag and the lagged RetroRenting-style (BL5 of main), one row each
# in panels (b) and (c), named by their labels (C58, W-G4 A)
SUPP_POLICIES_MS7["sf_lag_v2"] = ("sublet_v2_lag", "bl1_gp_lag", "a9_lag", "bl1n_lag", "bl5n_lag", "bl5_lag", "bl1_lag",
                                  "bl5_tau60_lag", "bl1_bo_lag", "bl2_lag", "bl3_0_lag", "bl4_lag")
# X2 (e7o_analysis.py): the rows of panels (b) and (c), Sublet, A9 and the seven primary baselines (C58, W-G4 A: fifteen
# rows of 9-pt names do not fit the panel's height; the tables print all fifteen tags of each fold)
SUPP_POLICIES_MS7["sf_oos"] = ("sublet_v2", "a9", "bl5_cur", "bl5_lag", "bl1", "bl1_bo", "bl2", "bl3_0", "bl4")
# C58 (W-G4 A): 2.5 in (a legend row above rows of 9-pt names at least 10.2 pt apart)
register_supplementary("sf_lag_v2", "W2", 2.5)
register_supplementary("sf_oos", "W2", 2.5)
# end W-G4 block A
# W-G4 block B (sf_bl_ms7, sf_stress_ms7)
# X4 (e7r_analysis.py): Sublet, protected-only renting, the as-built primary baselines with their kbar transplants
# (AS_BUILT_C2), SpotHedge-style's spares, MPC (tuned by rule T) and its oracle reference; the tuned settings (bl*_t,
# bl*_w, mpc_built, mpc_w) can replace keys of this set (they are distinct beside the as-built baselines and Sublet)
SUPP_POLICIES_MS7["sf_bl_ms7"] = ("sublet_v2", "a9p", "bl5_cur", "bl1", "bl2", "bl3_0", "bl4", "mpc", "bl5_cur_c2",
                                  "bl1_c2", "bl2_c2", "bl3_0_c2", "bl4_c2", "bl3_1", "bl3_2", "bl3_1_llm", "bl3_2_llm",
                                  "mpc_oracle")
# X5 (e7r_analysis.py): the i.i.d. intensity curves of Sublet, critical-ratio renting, protected-only renting
# (lender-invariant), the primary baselines and the notice-aware policies (C58, W-G4 B as built: critical-ratio
# planning and the k* ablation, A9's ablations, are in the tables only, so that each panel's legend leaves room for
# the data); every tag under every lender is in the tables
SUPP_POLICIES_MS7["sf_stress_ms7"] = ("sublet_v2", "bl1_gp", "a9", "bl1n", "bl5n", "a9p", "bl5_cur", "bl5_tau60",
                                      "bl5_lag", "bl1", "bl1_bo", "bl2", "bl3_0", "bl4")
# C58 (W-G4 B, as built): sf_bl_ms7 at 2.5 in, so that its nine or ten named rows (ten where MPC and its oracle forecast
# are rows of their own) stand further apart than the 13.25-pt height of a name with kbar
register_supplementary("sf_bl_ms7", "W2", 2.5)
register_supplementary("sf_stress_ms7", "W2", 2.5)
# end W-G4 block B
# W-G4 block C (sf_s1_v2, sf_e5_v2, sf_e8_v2, sf_e9_v2)
# C58 (W-G4, writer C): X3 (ms7_sens_analysis.py), the keys each figure draws (the other policies of its runs are in
# its tables): S1 v2's tornado draws Sublet alone (its saving per setting, filled where it costs less than BL1-BO and
# BL5-cur in every week; A9, BL1-BO, BL5-cur and part w0's BL4 in the tables), E5 v2 the six policies (with BL3-0 and
# BL3-2), E8 v2 the five (A6 from E8's stored runs; Sublet the reference at (1, 1)), E9 v2 Sublet and A9 (the guard's
# parts in black and grey, no policy; E9's LP bound is not drawn); sf_e8_v2 at W2 for its three panels (W-G4-0: W1),
# 2.5 in high since C62 (2.2 in as built at 9 pt)
SUPP_POLICIES_MS7["sf_s1_v2"] = ("sublet_v2",)
SUPP_POLICIES_MS7["sf_e5_v2"] = ("sublet_v2", "a9", "bl5_cur", "bl1_bo", "bl3_0", "bl3_2")
SUPP_POLICIES_MS7["sf_e8_v2"] = ("sublet_v2", "a9", "a6", "bl5_cur", "bl1_bo")
SUPP_POLICIES_MS7["sf_e9_v2"] = ("sublet_v2", "a9")
register_supplementary("sf_s1_v2", "W2", 2.5)
register_supplementary("sf_e5_v2", "W2", 2.5)
register_supplementary("sf_e8_v2", "W2", 2.5)        # C62: 2.2 -> 2.5 in, nearly square scatter panels
register_supplementary("sf_e9_v2", "W2", 2.2)
# end W-G4 block C
del _G4

# MS8 (design/ms8/plan.md, unit W): the supplementary figures of the runs X6 and X7 (design/ms8/registration.md). Shared
# by the writer units: SUPP_POLICIES_MS8 (each figure's set, in legend order), MS8_SUPP_KEYS (the MS8 registry keys,
# appended after MS7_SUPP_KEYS in block order) and MS8_KEY_OF_TAG (the registry key of each MS8 tag that no earlier key
# draws). Each writer changes only its own block ("# MS8 unit <U> block ..." to "# end MS8 unit <U> block"): a key has a
# (color, marker, fill) triple and a label that no other key has; within every set no (marker, fill) twice; a size is
# one that tests/test_figs_style.py's ink tests cover. figure_sets() includes the map. No earlier key, label, triple or
# set changes.
SUPP_POLICIES_MS8: dict[str, tuple[str, ...]] = {}
MS8_SUPP_KEYS: tuple[str, ...] = ()
MS8_KEY_OF_TAG: dict[str, str] = {}
# MS8 unit F6 block (sf_cap; X6, budget caps, e7b_tags.CAP_TAGS)
# The seven naive spend caps of algos/budget_cap.py (labeled baselines, no guarantee): around critical-ratio renting
# (A9) in reddish purple, a family of their own (five purple series beside Sublet's blue read apart, five more blue ones
# would not), around greedy renting (BL1) in BL1's orange; labels "<inner policy's label>, cap <X>" with X = B(t)
# (Sublet's allowance), 0 or 5% (of the all-fallback bill so far), the latched cap (releases every lease once at its
# first bind) and the slot-count cap (also prices the slot's purchases and rent), as the supplement's Section S-D.4.1
# names them. Markers: no (marker, fill) twice beside Sublet's filled circle, and no (color, marker) pair that
# tests/test_ms3_additions.py or test_ms4_additions.py pins (purple 'd', '<', 'D', 'p', 's', 'P')
_F6 = "MS8 unit F6 (design/ms8/plan.md D2, X6): "
_REGISTRY_MS8_F6 = (
    Policy("cap_cr_b", r"Critical-ratio renting, cap $B(t)$", "#CC79A7", ">", "filled", "-", "baseline", "cap_cr",
           note=_F6 + "tag CR-cap-B of e7b: A9 under a naive cap at Sublet's allowance B(t), counting the cost so far"),
    Policy("cap_cr_0", "Critical-ratio renting, cap 0", "#CC79A7", ">", "open", "-", "baseline", "cap_cr",
           note=_F6 + "tag CR-cap-0 of e7b: A9 under a naive cap with no allowance"),
    Policy("cap_cr_5", "Critical-ratio renting, cap 5%", "#CC79A7", "o", "open", "-", "baseline", "cap_cr",
           note=_F6 + "tag CR-cap-5 of e7b: A9 under a naive cap at 5% of the all-fallback cost so far"),
    Policy("cap_cr_latch", r"Critical-ratio renting, latched cap $B(t)$", "#CC79A7", "H", "filled", "-", "baseline",
           "cap_cr", note=_F6 + "tag CR-cap-B-latch of e7b: the cap at B(t) that releases every lease once at its "
                                "first bind and stops"),
    Policy("cap_cr_slot", r"Critical-ratio renting, slot-count cap $B(t)$", "#CC79A7", "X", "filled", "-",
           "baseline", "cap_cr", note=_F6 + "tag CR-cap-B-slot of e7b: the cap at B(t) that also prices the slot's "
                                            "purchases and rent"),
    Policy("cap_gr_b", r"Greedy renting, cap $B(t)$", "#E69F00", "P", "filled", "-", "baseline", "bl1",
           note=_F6 + "tag GR-cap-B of e7b: BL1 under a naive cap at Sublet's allowance B(t)"),
    Policy("cap_gr_0", "Greedy renting, cap 0", "#E69F00", "s", "open", "-", "baseline", "bl1",
           note=_F6 + "tag GR-cap-0 of e7b: BL1 under a naive cap with no allowance"),
)
_new = {p.key: p for p in _REGISTRY_MS8_F6}
if set(_new) & set(POLICIES) or len(_new) != len(_REGISTRY_MS8_F6):
    raise StyleError("MS8 F6: the MS8 keys must be new and placed once each")
POLICIES.update(_new)
MS8_SUPP_KEYS += tuple(_new)
MS8_KEY_OF_TAG.update({"CR-cap-B": "cap_cr_b", "CR-cap-0": "cap_cr_0", "CR-cap-5": "cap_cr_5",
                       "CR-cap-B-latch": "cap_cr_latch", "CR-cap-B-slot": "cap_cr_slot", "GR-cap-B": "cap_gr_b",
                       "GR-cap-0": "cap_gr_0"})
# X6 (e7b_analysis.py): Sublet and the seven caps, in every panel that draws them; the references A9, BL1 and BL1-GP are
# in the tables only. W2 x 2.5 in (a two-row legend over four panels, sf_bl_ms7's size)
SUPP_POLICIES_MS8["sf_cap"] = ("sublet_v2", "cap_cr_b", "cap_cr_0", "cap_cr_5", "cap_cr_latch", "cap_cr_slot",
                               "cap_gr_b", "cap_gr_0")
register_supplementary("sf_cap", "W2", 2.5)
del _new, _F6
# end MS8 unit F6 block
# MS8 unit F7 block (sf_e8q; X7, the request-level replay with a queue, e8q.TAGS and the bill BL0a)
# X7 (e8q_analysis.py): Sublet, critical-ratio renting, RetroRenting-style and greedy back-off (the replayed policies,
# their MS5b keys) and All-fallback (bl0a, the replayed all-fallback bill: its own fluid error in panel (a)); no new key.
# W2 x 2.5 in (three panels under a one-row legend, sf_e8_v2's size)
SUPP_POLICIES_MS8["sf_e8q"] = ("sublet_v2", "a9", "bl5_cur", "bl1_bo", "bl0a")
register_supplementary("sf_e8q", "W2", 2.5)
# end MS8 unit F7 block


def figure_sets() -> dict[str, tuple[str, ...]]:
    """C41: {figure: policy set} over every registry map (FIGURE_POLICIES, SUPP_POLICIES, SUPP_POLICIES_MS4,
    SUPP_POLICIES_MS5, SUPP_POLICIES_MS5B; C58: and SUPP_POLICIES_MS7; MS8: and SUPP_POLICIES_MS8)."""
    out: dict[str, tuple[str, ...]] = {}
    for m in (FIGURE_POLICIES, SUPP_POLICIES, SUPP_POLICIES_MS4, SUPP_POLICIES_MS5, SUPP_POLICIES_MS5B,
              SUPP_POLICIES_MS7, SUPP_POLICIES_MS8):                                       # C58 (W-G4); MS8
        out.update(m)
    return out


def check_legacy(sets: Mapping[str, Iterable[str]] | None = None, pending: Mapping[str, str] | None = None) -> None:
    """C41 (W7, W8): raise StyleError if a figure of `sets` ({figure: keys}; default figure_sets()) draws an MS5b key
    (C46: or an MS6 key, so that a7_g1 and a7_ms4 never share a figure with a7_guard) together with a legacy key, draws
    a legacy key without an entry in `pending` (default LEGACY_PENDING), or has an entry there although it draws no legacy
    key."""
    sets = figure_sets() if sets is None else sets
    pending = LEGACY_PENDING if pending is None else pending
    bad = []
    for name, keys in sets.items():
        ks = set(keys)
        legacy = sorted(ks & set(LEGACY_KEYS))
        for milestone, added in (("MS5b", MS5B_KEYS), ("MS6", MS6_KEYS)):
            new = sorted(ks & set(added))
            if legacy and new:
                bad.append(f"{name} draws the {milestone} keys {new} with the legacy keys {legacy}")
        if legacy and name not in pending:
            bad.append(f"{name} draws the legacy keys {legacy} without a LEGACY_PENDING entry")
        if not legacy and name in pending:
            bad.append(f"{name} has a LEGACY_PENDING entry but draws no legacy key")
    if bad:
        raise StyleError("legacy keys (W7, W8): " + "; ".join(bad))


def policy(key: str, policies: Mapping[str, Policy] | None = None) -> Policy:
    reg = POLICIES if policies is None else policies
    try:
        return reg[key]
    except KeyError:
        raise StyleError(f"unknown policy key {key!r}; known: {sorted(reg)}") from None


def check_unique(keys: Iterable[str], policies: Mapping[str, Policy] | None = None) -> None:
    """Raise StyleError if two distinct policies in `keys` (the series of one figure) share a (color, marker,
    fill) triple. A key may repeat (one policy drawn at several environment levels, which the line style
    distinguishes)."""
    seen: dict[tuple, str] = {}
    clashes = []
    for k in dict.fromkeys(keys):
        t = policy(k, policies).triple
        if t in seen:
            clashes.append(f"{seen[t]} and {k} share {t}")
        else:
            seen[t] = k
    if clashes:
        raise StyleError("policies of one figure must not share a (color, marker, fill) triple: " + "; ".join(clashes))


def check_color_reuse(keys: Iterable[str], policies: Mapping[str, Policy] | None = None) -> None:
    """Raise StyleError if two policies of one figure share a color without being variants of one family (§5:
    a color is reused only by policies that never share a figure or by the variants of one family)."""
    by_color: dict[str, Policy] = {}
    bad = []
    for k in dict.fromkeys(keys):
        p = policy(k, policies)
        q = by_color.setdefault(p.color.upper(), p)
        if q.key != p.key and q.family != p.family:
            bad.append(f"{q.key} ({q.family}) and {p.key} ({p.family}) share {p.color}")
    if bad:
        raise StyleError("a color is shared within a figure only by one family's variants: " + "; ".join(bad))


def check_policies(keys: Iterable[str], policies: Mapping[str, Policy] | None = None) -> None:
    keys = list(keys)
    check_unique(keys, policies)
    check_color_reuse(keys, policies)


def legend_order(keys: Iterable[str]) -> list[str]:
    """Distinct keys in the legend order of §5: Sublet, other guarded policies, our other policies, baselines,
    (reference lines,) benchmarks; registry order within a group."""
    index = {k: i for i, k in enumerate(POLICIES)}
    ks = list(dict.fromkeys(keys))
    return sorted(ks, key=lambda k: (GROUPS.index(policy(k).group), index[k]))


# Line style per environment factor (§5 "Grammar"): one factor per figure.
ENV_LINESTYLES: dict[str, dict[str, str]] = {
    "lender": {"maas": "-", "spot": "--"},
    "information": {"private": "-", "public": "--"},
    "sharing": {"shared": "-", "siloed": "--"},
    # C58 (W-G4): X1's demand (each slot revealed before the platform acts, or the previous slot's) and X2's calibration
    # window (the trace lenders calibrated on the other window of the series, or on the whole series, the evaluated
    # window included)
    "demand": {"revealed": "-", "lagged": "--"},
    "calibration": {"oos": "-", "is": "--"},
}
ENV_LABELS: dict[str, dict[str, str]] = {
    "lender": {"maas": "MaaS", "spot": "Spot"},
    "information": {"private": "Private information", "public": "Public information"},
    "sharing": {"shared": "Shared", "siloed": "Siloed"},
    "demand": {"revealed": "Revealed slot", "lagged": "Lagged one slot"},                 # C58 (W-G4)
    "calibration": {"oos": "Out of sample", "is": "In sample"},                         # C58 (W-G4)
}


def env_linestyle(factor: str, level: str) -> str:
    try:
        return ENV_LINESTYLES[factor][level]
    except KeyError:
        raise StyleError(f"unknown environment factor/level {factor!r}/{level!r}; known: {ENV_LINESTYLES}") from None


def _note_env(fig: Figure | None, factor: str) -> None:
    if fig is None:
        return
    used = getattr(fig, "_sublet_env_factor", None)
    if used is not None and used != factor:
        raise StyleError(f"line style carries one environment factor per figure: {used!r} is used, not {factor!r}")
    fig._sublet_env_factor = factor


def policy_kwargs(key: str, *, env: tuple[str, str] | None = None, lines: bool = True, markers: bool = True,
                  label: bool = True) -> dict:
    """Line2D keyword arguments of a policy: color, marker (white face if open, 0.6-pt edge), line width (Sublet
    1.5 pt), marker size (Sublet 4 pt), z-order (Sublet last); `env` = (factor, level) sets the line style."""
    p = policy(key)
    ls = env_linestyle(*env) if env is not None else p.linestyle
    kw = dict(color=p.color, linewidth=p.linewidth, linestyle=ls if lines else "none", zorder=p.zorder)
    if p.marker is not None and markers:
        face = "white" if p.fill == "open" else p.color
        kw.update(marker=p.marker, markersize=p.markersize, markeredgewidth=MARKER_EDGE_PT,
                  markeredgecolor=p.edgecolor or p.color, markerfacecolor=face)
    else:
        kw.update(marker="None")
    kw["label"] = p.label if label else "_nolegend_"
    return kw


def plot_policy(ax, key: str, x, y, *, env: tuple[str, str] | None = None, lines: bool = True,
                markers: bool = True, **overrides) -> Line2D:
    """Draw one policy series. For a series drawn at several environment levels (MaaS / spot), the legend entry
    is the policy's; env_handles() adds the line-style entries."""
    if env is not None:
        _note_env(ax.figure, env[0])
    kw = policy_kwargs(key, env=env, lines=lines, markers=markers)
    kw.update(overrides)
    (line,) = ax.plot(x, y, **kw)
    line._sublet_policy = key
    return line


def scatter_policy(ax, key: str, x, y, **overrides) -> Line2D:
    """Markers only (no line), in the policy's style."""
    return plot_policy(ax, key, x, y, lines=False, **overrides)


def policy_hline(ax, key: str, y: float, **overrides) -> Line2D:
    """A policy drawn as a horizontal reference line (BL0a, BL0b) with its legend label."""
    kw = policy_kwargs(key, markers=False)
    kw.update(overrides)
    line = ax.axhline(y, **kw)
    line._sublet_policy = key
    return line


def errorbars(ax, key: str, x, y, lo, hi, *, orientation: str = "y", **overrides):
    """95% bootstrap intervals as 0.6-pt bars without caps in the policy's color (black for the yellow BL3/BL4,
    their marker edge color: yellow 0.6-pt bars do not read on white)."""
    p = policy(key)
    x, y, lo, hi = (np.asarray(v, dtype=float) for v in (x, y, lo, hi))
    err = np.vstack([y - lo, hi - y]) if orientation == "y" else np.vstack([x - lo, hi - x])
    kw = dict(fmt="none", ecolor=p.text_color, elinewidth=UNCERTAINTY_PT, capsize=0, zorder=p.zorder - 0.01,
              label="_nolegend_")
    kw.update(overrides)
    if orientation == "y":
        return ax.errorbar(x, y, yerr=err, **kw)
    return ax.errorbar(x, y, xerr=err, **kw)


def band(ax, key: str, x, lo, hi, **overrides):
    """95% bootstrap band in the policy's color at alpha 0.18. Not for the yellow BL3/BL4 (StyleError): #F0E442 at
    alpha 0.18 is almost white, so their intervals are drawn with errorbars(), whose bars take the black edge."""
    p = policy(key)
    if p.edgecolor is not None and p.edgecolor.upper() != p.color.upper():
        raise StyleError(f"a band in {p.color} at alpha {BAND_ALPHA} does not read on white; draw the intervals of "
                         f"{key} with errorbars()")
    kw = dict(color=p.color, alpha=BAND_ALPHA, linewidth=0, zorder=p.zorder - 0.02, label="_nolegend_")
    kw.update(overrides)
    return ax.fill_between(x, lo, hi, **kw)


def direct_label(ax, key: str, x: float, y: float, text: str | None = None, *, dx: float = 3.0, dy: float = 0.0,
                 ha: str = "left", va: str = "center", **overrides) -> Text:
    """A label (TICK_PT, 7 pt) next to a point, in the policy's label color (Policy.label_color: the policy's color,
    darkened for a light color; black for the yellow BL3/BL4)."""
    p = policy(key)
    kw = dict(xytext=(dx, dy), textcoords="offset points", ha=ha, va=va, fontsize=TICK_PT, color=p.label_color)
    kw.update(overrides)
    return ax.annotate(p.label if text is None else text, xy=(x, y), **kw)


def arrow(ax, xy_from, xy_to, *, color: str = THEORY_GREY, linewidth: float = 0.6, **overrides):
    """A thin arrow (e.g. from an inner policy to its guarded version in Fig. 3(a))."""
    props = dict(arrowstyle="-|>,head_length=0.45,head_width=0.22", color=color, linewidth=linewidth,
                 shrinkA=2.0, shrinkB=2.5)
    props.update(overrides)
    return ax.annotate("", xy=xy_to, xytext=xy_from, arrowprops=props)


# ---------------------------------------------------------------------------------------------------------------
# Theory and reference lines (§5 "Lines and markers", "Grammar")
THEORY_STYLES: dict[str, dict] = {
    "upper": dict(linestyle="--", linewidth=THEORY_PT),        # proven upper bound
    "lower": dict(linestyle=":", linewidth=THEORY_LOWER_PT),   # proven lower bound
    "exact": dict(linestyle="-", linewidth=THEORY_PT),         # exact theory value
    "limit": dict(linestyle="-", linewidth=THEORY_PT),         # limit for T -> infinity (labeled as a limit)
    "unproven": dict(linestyle="-.", linewidth=THEORY_PT),     # unproven or informal value
}
_LIMIT_WORDS = ("limit", "\\infty", "∞", "t\\to", "t →")      # matched in the lower-cased label


def halo(line: Line2D, width: float = HALO_PT) -> Line2D:
    """A solid white line under `line`, `width` pt wider on each side, so that a theory line reads on a heatmap."""
    ax = line.axes
    (under,) = ax.plot(line.get_xdata(), line.get_ydata(), color="white", linestyle="-",
                       linewidth=line.get_linewidth() + 2 * width, zorder=line.get_zorder() - 0.001,
                       solid_capstyle="round", label="_nolegend_")
    under._sublet_role = "halo"
    return under


def theory_line(ax, x, y, kind: str, label: str, *, where: str = "inside", label_xy: tuple | None = None,
                dx: float | None = None, dy: float | None = None, on_heatmap: bool = False, **overrides):
    """A grey theory line (#7F7F7F) in the style of its kind, labeled at its right end and kept out of the legend.

    kind: "upper" (proven upper bound, dashed 0.75 pt), "lower" (proven lower bound, dotted 0.9 pt), "exact"
    (exact theory value, solid), "limit" (limit for T -> infinity, solid; the label must say so) or "unproven"
    (unproven or informal, dash-dot). where="inside" puts the label above the line's last point, right-aligned
    (inside the axes, the right margin is 0.06 in); "right" puts it just right of the last point. The line is drawn
    behind the data; the label is drawn above the data with a white halo, so that no line or band covers it.
    `on_heatmap` adds a white halo to the line as well. Returns (line, label text)."""
    if kind not in THEORY_STYLES:
        raise StyleError(f"theory line kind must be one of {sorted(THEORY_STYLES)}, not {kind!r}")
    if not str(label).strip():
        raise StyleError("a theory line is labeled at its right end; give a label")
    if kind == "limit" and not any(w in label.lower() for w in _LIMIT_WORDS):
        raise StyleError(f"a limit is labeled as such (include 'limit' or T -> infinity): {label!r}")
    kw = dict(color=THEORY_GREY, zorder=Z_THEORY, label="_nolegend_")
    kw.update(THEORY_STYLES[kind])
    kw.update(overrides)
    (line,) = ax.plot(x, y, **kw)
    line._sublet_role = f"theory:{kind}"
    if on_heatmap:
        halo(line)
    if label_xy is None:
        xs, ys = np.asarray(x, dtype=float).ravel(), np.asarray(y, dtype=float).ravel()
        if xs.size == 1 and ys.size > 1:
            xs = np.full_like(ys, xs[0])
        if ys.size == 1 and xs.size > 1:
            ys = np.full_like(xs, ys[0])
        ok = np.isfinite(xs) & np.isfinite(ys)
        if not ok.any():
            raise StyleError(f"theory line {label!r} has no finite point")
        i = int(np.flatnonzero(ok)[np.argmax(xs[ok])])
        label_xy = (xs[i], ys[i])
    if where == "inside":
        offs, ha, va = (0.0 if dx is None else dx, 1.5 if dy is None else dy), "right", "bottom"
    elif where == "right":
        offs, ha, va = (2.0 if dx is None else dx, 0.0 if dy is None else dy), "left", "center"
    else:
        raise StyleError(f"where must be 'inside' or 'right', not {where!r}")
    txt = ax.annotate(label, xy=label_xy, xytext=offs, textcoords="offset points", ha=ha, va=va,
                      fontsize=TICK_PT, color=THEORY_LABEL_GREY if line.get_color() == THEORY_GREY else
                      readable_on_white(line.get_color()), zorder=Z_THEORY_LABEL)
    txt._sublet_role = f"theory_label:{kind}"
    txt.set_path_effects([_pe.withStroke(linewidth=LABEL_HALO_PT, foreground="white")])
    return line, txt


def reference_line(ax, *, y: float | None = None, x: float | None = None, **overrides) -> Line2D:
    """A 0.5-pt #BDBDBD solid reference line (the level 1 of BL0a or OPT; thresholds such as rho = 2, H*_mu and
    H*_beta, which are not bounds), behind the data and out of the legend."""
    if (x is None) == (y is None):
        raise StyleError("give exactly one of x and y")
    kw = dict(color=REFERENCE_GREY, linewidth=REFERENCE_PT, linestyle="-", zorder=Z_REFERENCE, label="_nolegend_")
    kw.update(overrides)
    line = ax.axhline(y, **kw) if y is not None else ax.axvline(x, **kw)
    line._sublet_role = "reference"
    return line


def shade_region(ax, x: tuple[float, float], y: tuple[float, float], *, color: str = SHADE_GREY, **overrides):
    """A light grey rectangle behind the data (Fig. 3(a)'s pre-set criteria region, decision 7)."""
    from matplotlib.patches import Rectangle
    kw = dict(facecolor=color, edgecolor="none", linewidth=0, zorder=0.5, label="_nolegend_")
    kw.update(overrides)
    r = Rectangle((x[0], y[0]), x[1] - x[0], y[1] - y[0], **kw)
    ax.add_patch(r)
    return r


# ---------------------------------------------------------------------------------------------------------------
# Axes (§5 "Axes, legends and panels")
def _plain(v: float, _pos=None) -> str:
    if not np.isfinite(v):
        return ""
    if abs(v - round(v)) <= 1e-9 * max(1.0, abs(v)):
        s = str(int(round(v)))
    else:
        s = f"{v:.6g}"
    return s.replace("-", "−")


PLAIN = _ticker.FuncFormatter(_plain)


class _YGrid(LineCollection):
    """The y grid lines of one axes, laid out when drawn: at the major y ticks inside the y limits, from the start to
    the end of the bottom spine's bounds (or across the x limits where the spine has none), so that a label column
    right of the data (theory labels, §5 amendment of 2026-10-20) has no grid line running through its text."""

    def __init__(self, ax):
        super().__init__([], colors=GRID_GREY, linewidths=GRID_PT, linestyles="-", zorder=0.5)
        self._sublet_ax = ax

    def draw(self, renderer):
        ax = self._sublet_ax
        lo, hi = sorted(ax.get_ylim())
        bounds = ax.spines["bottom"].get_bounds()
        x0, x1 = bounds if bounds is not None else ax.get_xlim()
        self.set_segments([[(x0, y), (x1, y)] for y in ax.yaxis.get_majorticklocs() if lo <= y <= hi])
        super().draw(renderer)


def ygrid(ax) -> None:
    """The optional #E6E6E6 0.4-pt y grid for log ratio axes, behind the data, ending where the x spine ends (_YGrid;
    the clipping is not in §5)."""
    ax.set_axisbelow(True)
    ax.yaxis.grid(False)
    if not any(isinstance(c, _YGrid) for c in ax.collections):
        ax.add_collection(_YGrid(ax), autolim=False)


def log2_axis(ax, which: str = "x", ticks: Sequence[float] | None = None) -> None:
    """Base-2 log axis with integer labels (rho, m, b): 1, 2, 4, 8, ... and no minor ticks."""
    axis = ax.xaxis if which == "x" else ax.yaxis
    (ax.set_xscale if which == "x" else ax.set_yscale)("log", base=2)
    axis.set_major_locator(_ticker.FixedLocator(list(ticks)) if ticks is not None
                           else _ticker.LogLocator(base=2, subs=(1.0,), numticks=64))
    axis.set_major_formatter(PLAIN)
    axis.set_minor_locator(_ticker.NullLocator())


def log_axis(ax, which: str = "y", ticks: Sequence[float] | None = None) -> None:
    """Base-10 log axis with plain tick labels (1, 10, 100, ...) for ratios that span more than a decade."""
    axis = ax.xaxis if which == "x" else ax.yaxis
    (ax.set_xscale if which == "x" else ax.set_yscale)("log", base=10)
    axis.set_major_locator(_ticker.FixedLocator(list(ticks)) if ticks is not None
                           else _ticker.LogLocator(base=10, subs=(1.0,), numticks=64))
    axis.set_major_formatter(PLAIN)
    axis.set_minor_formatter(_ticker.NullFormatter())


def _align_end_label(ax) -> None:
    """Right-align the major x tick label at the right end of the x axis; center the others."""
    left, right = ax.get_xlim()           # `right` is the value at the right edge (the lower one if inverted)
    locs = list(ax.xaxis.get_majorticklocs())
    tol = 1e-9 * max(abs(right - left), abs(right), 1e-300)
    center = mpl.rcParams["xtick.alignment"]
    for loc, tk in zip(locs, ax.xaxis.get_major_ticks(len(locs))):
        tk.label1.set_horizontalalignment("right" if abs(loc - right) <= tol else center)


def end_label_inside(ax) -> None:
    """Keep the x tick label at the right end of the x axis on the page: it is right-aligned to its tick, the others
    stay centered. Centered there, a label wider than twice the 0.06-in right margin (three digits at 7 pt) crosses
    the page edge in a row's last panel, and finalize() fails. The alignment follows later changes of the x limits
    (set_xlim, autoscaling)."""
    if getattr(ax, "_sublet_end_label_cid", None) is None:
        ax._sublet_end_label_cid = ax.callbacks.connect("xlim_changed", _align_end_label)
    _align_end_label(ax)


H_TICKS_MIN = (0, 1, 2, 5, 10, 30, 60, 240)    # no 120: at 9 pt it overlapped the right-aligned 240 in a W1 panel


def symlog_minutes(ax, which: str = "x", ticks: Sequence[float] = H_TICKS_MIN, linthresh: float = 1.0, *,
                   end_inside: bool = True) -> None:
    """Symlog axis for the notice H in minutes, linear below 1 min, with plain tick labels. On an x axis whose last
    tick is its upper limit (240 min), `end_inside` right-aligns that label (end_label_inside)."""
    axis = ax.xaxis if which == "x" else ax.yaxis
    (ax.set_xscale if which == "x" else ax.set_yscale)("symlog", linthresh=linthresh, linscale=1.0)
    axis.set_major_locator(_ticker.FixedLocator(list(ticks)))
    axis.set_major_formatter(PLAIN)
    axis.set_minor_locator(_ticker.NullLocator())
    if which == "x" and end_inside:
        end_label_inside(ax)


# ---------------------------------------------------------------------------------------------------------------
# Colors for non-policy categories and heatmaps (§5 "Grammar")
RAMP_RANGES = {"cividis": (0.0, 0.85), "greys": (0.35, 0.9)}
RATIO_CMAP = "PuOr"


def ramp(n: int, kind: str = "cividis") -> list[str]:
    """n colors of a categorical ramp (load scenarios, mu levels, cost components, lender pools)."""
    if kind not in RAMP_RANGES:
        raise StyleError(f"ramp kind must be one of {sorted(RAMP_RANGES)}")
    if n < 1:
        raise StyleError("ramp needs n >= 1")
    lo, hi = RAMP_RANGES[kind]
    cmap = mpl.colormaps["cividis" if kind == "cividis" else "Greys"]
    pos = [0.5 * (lo + hi)] if n == 1 else list(np.linspace(lo, hi, n))
    if kind == "greys":
        pos = pos[::-1]        # darkest first
    return [_mcolors.to_hex(cmap(p)) for p in pos]


def ratio_norm(vmin: float, vmax: float) -> _mcolors.LogNorm:
    """Log norm centered at 1 for ratio heatmaps (PuOr): symmetric in log around 1, covering [vmin, vmax]."""
    if not (vmin > 0 and vmax > 0):
        raise StyleError("ratio_norm needs positive vmin and vmax")
    m = max(vmax, 1.0 / vmin, 1.0 + 1e-9)
    return _mcolors.LogNorm(vmin=1.0 / m, vmax=m)


def inset_colorbar(ax, mappable, *, rect: Sequence[float] = (0.55, 0.90, 0.40, 0.045),
                   orientation: str = "horizontal", label: str | None = None, ticks: Sequence[float] | None = None):
    """A colorbar inside the panel (axes fraction rect), ticks and label at TICK_PT (7 pt), plain tick labels."""
    cax = ax.inset_axes(list(rect))
    cb = ax.figure.colorbar(mappable, cax=cax, orientation=orientation, ticks=ticks)
    cb.outline.set_linewidth(0.4)
    cax.tick_params(labelsize=TICK_PT, length=2.0, width=0.4, pad=1.5)
    long_axis = cax.xaxis if orientation == "horizontal" else cax.yaxis
    long_axis.set_major_formatter(PLAIN)
    long_axis.set_minor_locator(_ticker.NullLocator())
    if label:
        cb.set_label(label, fontsize=TICK_PT, labelpad=1.5)
    return cb


# ---------------------------------------------------------------------------------------------------------------
# Legends (§5 "Axes, legends and panels")
def policy_handles(keys: Iterable[str], *, lines: bool = True, markers: bool = True) -> list[tuple[Line2D, str]]:
    out = []
    for k in legend_order(keys):
        kw = policy_kwargs(k, lines=lines or policy(k).marker is None, markers=markers)
        out.append((Line2D([], [], **kw), kw["label"]))
    return out


def env_handles(factor: str, *, color: str = "#000000") -> list[tuple[Line2D, str]]:
    """Legend entries that explain the line style of the figure's environment factor (e.g. MaaS solid, spot
    dashed), in black, so that a dashed sample is not read as one of the grey theory lines (#4D4D4D before
    2026-10-22, close to the theory grey)."""
    return [(Line2D([], [], color=color, linewidth=LINE_PT, linestyle=ls), ENV_LABELS[factor][lvl])
            for lvl, ls in ENV_LINESTYLES[factor].items()]


# C46 (design/ms6_spec.md M5): paired legend entries, an inner policy beside its guarded configuration
# the note names the filled marker of a pair ("paired"), since unpaired policies with filled markers (Two-timescale PD,
# per-borrower ski rental) share the legend (print check of the gate)
GUARD_PAIR_NOTE = "paired, filled: + one-way guard (Algorithm 1 without projection)"
PAIR_PAD = 0.3      # gap between the two samples of a pair, in units of the legend's font size; not in §5


class MarkerPair(tuple):
    """A legend handle of two samples drawn side by side, the inner policy's and then its guarded configuration's
    (guard_pair_handles). legend_row and corner_legend draw it with PAIR_HANDLER_MAP; a legend made otherwise must pass
    handler_map=PAIR_HANDLER_MAP, since matplotlib's default handler for a tuple draws its samples on top of each
    other."""


PAIR_HANDLER_MAP = {MarkerPair: HandlerTuple(ndivide=None, pad=PAIR_PAD)}


def guard_pair_handles(pairs: Iterable[tuple[str, str]], *, lines: bool = False,
                       note: bool = True) -> list[tuple[object, str]]:
    """C46 (design/ms6_spec.md M5): (handle, label) pairs for legend_row(..., extra=...) or corner_legend, one per
    (inner_key, guarded_key) of `pairs` in the given order, then (if `note`) one explanatory entry. A pair's handle is
    a MarkerPair: the inner policy's open marker beside the filled marker of the same policy inside Algorithm 1
    without projection, each in its registry style (with its line if `lines`); its label is the inner policy's
    registry label. The explanatory entry has an empty handle and the label GUARD_PAIR_NOTE, "paired, filled: + one-way
    guard (Algorithm 1 without projection)" (M5's "filled: ...", naming the pair's filled marker, since unpaired
    policies with filled markers can share the legend).

    This is the one stated exception to "legend labels are registry labels" (design/figure_plan.md §5), recorded by
    design/ms6_spec.md M5: one entry stands for two registry keys, and the guarded key's own label is replaced by
    the note. It serves Fig. 3 and sf_e11_inst. Raises StyleError unless each pair is an inner policy with an open
    marker and a key of the group 'guarded' with a filled marker, of one family and one color, and no key repeats."""
    pairs = [tuple(p) for p in pairs]
    if not pairs:
        raise StyleError("guard_pair_handles needs at least one (inner, guarded) pair")
    bad, seen = [], set()
    for pair in pairs:
        if len(pair) != 2:
            raise StyleError(f"guard_pair_handles: {pair!r} is not an (inner, guarded) pair")
        inner, guarded = (policy(k) for k in pair)
        if inner.group == "guarded" or inner.fill != "open":
            bad.append(f"{inner.key} is not an inner policy with an open marker")
        if guarded.group != "guarded" or guarded.fill != "filled":
            bad.append(f"{guarded.key} is not a guarded policy with a filled marker")
        if inner.family != guarded.family or inner.color.upper() != guarded.color.upper():
            bad.append(f"{inner.key} and {guarded.key} are not one family in one color")
        bad.extend(f"{k} is in two pairs" for k in pair if k in seen)
        seen.update(pair)
    if bad:
        raise StyleError("guard_pair_handles (M5): " + "; ".join(bad))
    out: list[tuple[object, str]] = []
    for inner, guarded in pairs:
        samples = [Line2D([], [], **policy_kwargs(k, lines=lines, label=False)) for k in (inner, guarded)]
        out.append((MarkerPair(samples), policy(inner).label))
    if note:
        out.append((Line2D([], [], linestyle="none", marker="None"), GUARD_PAIR_NOTE))
    return out


def legend_row(fig: Figure, keys: Iterable[str], *, extra: Sequence[tuple] = (), lines: bool = True,
               markers: bool = True, ncol: int | None = None, rows: int = 1):
    """One frameless legend row in the top 0.21 in of a figure made with panel_row(legend=True), centered over
    the panels, in the order of §5; `extra` (handle, label) pairs follow. With rows=2 (panels placed with
    panel_row(legend=2)), the entries fill two rows in the top 0.42 in, for a legend that one row cannot
    hold (not in §5). Raises StyleError if a panel reaches into the legend reserve (the panels were placed
    without it) or if the rows do not fit."""
    pairs = policy_handles(keys, lines=lines, markers=markers) + list(extra)
    if not pairs:
        raise StyleError("legend_row needs at least one entry")
    handles, labels = zip(*pairs)
    rows = int(rows)
    if rows not in (1, 2):
        raise StyleError(f"legend_row: rows must be 1 or 2, not {rows}")
    reserve = LEGEND_ROW * rows
    W, H = (float(v) for v in fig.get_size_inches())
    rects = [ax._sublet_rect_in for ax in fig.axes if hasattr(ax, "_sublet_rect_in")]
    need = MARGIN_TOP + reserve - GEOMETRY_TOL_IN
    short = [f"{H - (r[1] + r[3]):.2f}" for r in rects if H - (r[1] + r[3]) < need]
    if not rects or short:
        raise StyleError("legend_row needs the legend reserve above every panel (top margin "
                         f"{MARGIN_TOP + reserve:.2f} in): place the panels with panel_row(..., legend="
                         f"{'True' if rows == 1 else rows})"
                         + (f"; panel top margins {short} in" if short else "; no panel_row axes"))
    xc = 0.5 * (min(r[0] for r in rects) + max(r[0] + r[2] for r in rects)) / W
    leg = fig.legend(list(handles), list(labels), loc="center", bbox_to_anchor=(xc, 1.0 - 0.5 * reserve / H),
                     bbox_transform=fig.transFigure, ncol=ncol or -(-len(handles) // rows), frameon=False,
                     borderaxespad=0.0, borderpad=0.0, handler_map=dict(PAIR_HANDLER_MAP))     # C46: MarkerPair
    leg._sublet_role = "legend_row"
    canvas = fig.canvas if isinstance(fig.canvas, FigureCanvasAgg) else FigureCanvasAgg(fig)
    bb = leg.get_window_extent(canvas.get_renderer())
    w_in = bb.width / fig.dpi
    if w_in > W - MARGIN_RIGHT + 1e-6 or bb.height / fig.dpi > reserve + 1e-6:
        leg.remove()
    if w_in > W - MARGIN_RIGHT + 1e-6:
        raise StyleError(f"legend row is {w_in:.2f} in wide, wider than the figure less its right margin "
                         f"({W - MARGIN_RIGHT:.3f} in); label some series directly or move entries to the caption")
    xc_in = min(max(xc * W, 0.5 * w_in), W - MARGIN_RIGHT - 0.5 * w_in)   # centered over the panels, on the page
    leg.set_bbox_to_anchor((xc_in / W, 1.0 - 0.5 * reserve / H), transform=fig.transFigure)
    if bb.height / fig.dpi > reserve + 1e-6:
        raise StyleError(f"legend row is {bb.height / fig.dpi:.2f} in high, more than {reserve:.2f} in")
    return leg


def corner_legend(ax, keys: Iterable[str], *, loc: str = "upper left", extra: Sequence[tuple] = (),
                  lines: bool = True, markers: bool = True, **overrides):
    """A frameless legend in an empty corner of a single-column figure's panel, in the order of §5 (C46: a MarkerPair
    of `extra` drawn side by side, PAIR_HANDLER_MAP)."""
    pairs = policy_handles(keys, lines=lines, markers=markers) + list(extra)
    handles, labels = zip(*pairs)
    kw = dict(loc=loc, frameon=False)
    kw.update(overrides)
    kw["handler_map"] = {**PAIR_HANDLER_MAP, **(kw.get("handler_map") or {})}
    return ax.legend(list(handles), list(labels), **kw)


# ---------------------------------------------------------------------------------------------------------------
# Export and checks (§5 "Export and checks")
def _marks(a) -> int:
    if isinstance(a, Line2D):
        try:
            return int(np.size(a.get_xdata(orig=False)))
        except Exception:
            return 0
    if isinstance(a, QuadMesh):
        c = a.get_coordinates()
        return int(max(c.shape[0] - 1, 0) * max(c.shape[1] - 1, 0))
    if isinstance(a, Collection):
        return int(max(len(a.get_offsets()), len(a.get_paths())))
    return 0


def rasterize_dense(fig: Figure, threshold: int = RASTER_MARKS) -> list:
    """Rasterize every artist with more than `threshold` marks (points, markers, cells); returns them."""
    done = []
    for a in fig.findobj():
        if _marks(a) > threshold:
            if not a.get_rasterized():
                a.set_rasterized(True)
            done.append(a)
    return done


def _visible_texts(fig: Figure) -> list[Text]:
    out = []
    for t in fig.findobj(Text):
        s = t.get_text()
        if not t.get_visible() or not s or not s.strip():
            continue
        if t.axes is not None and not t.axes.get_visible():
            continue
        out.append(t)
    return out


def text_sizes(fig: Figure) -> list[tuple[float, str]]:
    """(size in pt, text) of every visible non-empty text of the figure."""
    return [(float(t.get_fontsize()), t.get_text()) for t in _visible_texts(fig)]


def math_glyph_sizes(fig: Figure) -> list[tuple[float, str]]:
    """(size in pt of its smallest glyph, text) of every visible text of the figure with a mathtext line. Mathtext
    sets a sub- or superscript at 0.7 of the text size per level, so r"LB$_{\\mathrm{react}}$" at 7 pt has 4.9-pt
    glyphs. A multi-line text is parsed line by line, as matplotlib lays it out (each line is mathtext or plain text
    on its own), so a label such as "LB$_T$\\n(C3-T4)" never hands a newline to the mathtext parser (which would log
    "Font 'default' does not have a glyph for '\\n'")."""
    parser = MathTextParser("path")
    out = []
    for t in _visible_texts(fig):
        s = t.get_text()
        if t.get_usetex():
            continue
        sizes = []
        for line in s.split("\n"):
            if not _is_math(line):
                continue
            try:
                vp = parser.parse(line, dpi=72, prop=t.get_fontproperties())
            except Exception:    # a string mathtext cannot parse fails at savefig, before this check
                continue
            sizes += [float(g[1]) for g in vp.glyphs]
        if sizes:
            out.append((min(sizes), s))
    return out


def ink_outside_sides(fig: Figure, tol_pt: float = 0.5, dpi: float = RASTER_DPI, pad: float = 0.3) -> dict[str, bool]:
    """{side: whether ink lies more than `tol_pt` beyond that page edge} for the sides left, right, top and bottom.
    The figure is rendered once as a PNG with a `pad`-inch white border around the page and read back with PIL; the
    image's own pixel size gives the scale (sx = nx / (W + 2 pad), sy = ny / (H + 2 pad)), since the bordered canvas
    is often a pixel smaller than (W + 2 pad) dpi x (H + 2 pad) dpi (savefig rounds the border box), e.g. 1547 x 560
    px for W2 x 2.2 in at 200 dpi. Any pixel darker than 245 in a channel counts as ink. The border moves only what
    is placed through fig.transFigure (figure, axes, data and offset-point coordinates); an artist placed in absolute
    inches (transform=fig.dpi_scale_trans) is not moved and would be checked `pad` inches left of and below where the
    PDF draws it, so the figure scripts never place one that way."""
    import io
    from matplotlib.transforms import Bbox
    from PIL import Image
    W, H = (float(v) for v in fig.get_size_inches())
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=dpi, bbox_inches=Bbox([[-pad, -pad], [W + pad, H + pad]]),
                facecolor="white", transparent=False, metadata={"Software": None}, pil_kwargs={"compress_level": 0})
    with Image.open(io.BytesIO(buf.getvalue())) as im:
        img = np.asarray(im.convert("RGB"))
    ny, nx = img.shape[:2]
    if nx < 2 or ny < 2:
        raise FigureCheckError(f"the bordered rendering is {nx} x {ny} px; cannot check ink outside the page")
    ink = (img < 245).any(axis=2)                                     # anything not white
    sx, sy = nx / (W + 2 * pad), ny / (H + 2 * pad)
    t = tol_pt / BP_PER_IN
    x_lo, x_hi = int((pad - t) * sx), int(np.ceil((pad + W + t) * sx))
    y_top, y_bot = int((pad - t) * sy), int(np.ceil((pad + H + t) * sy))       # image rows run from the top
    return {"left": bool(ink[:, :max(x_lo, 0)].any()), "right": bool(ink[:, x_hi:].any()),
            "top": bool(ink[:max(y_top, 0), :].any()), "bottom": bool(ink[y_bot:, :].any())}


def texts_outside_page(fig: Figure, tol_pt: float = 0.5, dpi: float = RASTER_DPI) -> list[str]:
    """Texts whose ink lies partly outside the page, e.g. a centered tick label at the right end of an x axis, which
    the 0.06-in right margin does not hold (end_label_inside right-aligns it), or a mathtext accent (the tilde of
    beta~) above a panel title at the page top. The figure is rendered once with a 0.3-in border around the page
    (ink_outside_sides, at every figure size); on each side where ink appears beyond `tol_pt`, the drawn texts whose
    layout box crosses that side are named ("ink outside the page (<sides>)" if none is, e.g. an accent that rises
    above its text's layout box). Layout boxes alone overstate mathtext (a sub- or superscript in a y label reaches a
    few points beyond its ink), hence the rendering. finalize() fails on a non-empty result (a failure that §5 does
    not list: the PDF would cut the ink off)."""
    sides = ink_outside_sides(fig, tol_pt=tol_pt, dpi=dpi)
    if not any(sides.values()):
        return []
    r = _drawn_renderer(fig)
    Wp, Hp, tol = fig.bbox.width, fig.bbox.height, tol_pt * fig.dpi / BP_PER_IN
    out = []
    for txt in drawn_texts(fig, r):
        bb = txt.get_window_extent(r)
        crosses = {"left": bb.x0 < -tol, "right": bb.x1 > Wp + tol, "bottom": bb.y0 < -tol, "top": bb.y1 > Hp + tol}
        if any(crosses[k] and sides[k] for k in sides):
            out.append(txt.get_text())
    return out or [f"ink outside the page ({', '.join(k for k, v in sides.items() if v)})"]


def _drawn_renderer(fig: Figure):
    canvas = fig.canvas if isinstance(fig.canvas, FigureCanvasAgg) else FigureCanvasAgg(fig)
    canvas.draw()
    return canvas.get_renderer()


def drawn_texts(fig: Figure, renderer=None) -> list[Text]:
    """The visible non-empty texts that a drawing of the figure shows: of the tick labels only those of the ticks
    drawn (inside the view limits, in an axes not switched off), the other texts if visible and in a visible axes. Draws the figure (Agg) unless
    `renderer` is given."""
    if renderer is None:
        _drawn_renderer(fig)
    tick_ids, drawn = set(), []
    for ax in fig.axes:
        for axis in (ax.xaxis, ax.yaxis):
            for tk in list(axis.majorTicks) + list(axis.minorTicks):
                tick_ids.update((id(tk.label1), id(tk.label2)))
            if not ax.axison:                   # ax.axis("off"): its tick labels are never drawn
                continue
            try:
                drawn += [lab for tk in axis._update_ticks() for lab in (tk.label1, tk.label2)]
            except Exception:
                drawn += [lab for tk in list(axis.majorTicks) for lab in (tk.label1, tk.label2)]
    out = []
    for txt in [x for x in fig.findobj(Text) if id(x) not in tick_ids] + drawn:
        s = txt.get_text()
        if not txt.get_visible() or not s or not s.strip() or (txt.axes is not None and not txt.axes.get_visible()):
            continue
        out.append(txt)
    return out


def text_overlaps(fig: Figure, tol_pt: float = 0.5) -> list[tuple[str, str]]:
    """Pairs of drawn texts (drawn_texts: tick labels, axis labels, legend entries, direct and theory labels, panel
    letters, colorbar labels) whose layout boxes overlap by more than `tol_pt` in both directions: two labels set
    on top of each other, which no figure means to draw. finalize() fails on a non-empty result (a failure that §5
    does not list; added with the 9-pt text of the print check, 2026-10-22)."""
    r = _drawn_renderer(fig)
    tol = tol_pt * fig.dpi / BP_PER_IN
    boxes = []
    for t in drawn_texts(fig, r):
        bb = t.get_window_extent(r)
        if bb.width > 0 and bb.height > 0:
            boxes.append((t.get_text(), bb))
    out = []
    for i, (sa, a) in enumerate(boxes):
        for sb, b in boxes[i + 1:]:
            if min(a.x1, b.x1) - max(a.x0, b.x0) > tol and min(a.y1, b.y1) - max(a.y0, b.y0) > tol:
                out.append((sa, sb))
    return out


def _run(cmd: list[str]) -> tuple[str, str]:
    exe = cmd[0]
    if not Path(exe).is_file():
        raise FigureCheckError(f"{exe} is not installed (poppler-utils); finalize() needs it")
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=60, check=False)
    if r.returncode != 0:
        raise FigureCheckError(f"{' '.join(cmd)} failed: {r.stderr.strip()}")
    return r.stdout, r.stderr


def pdf_page(pdf_path: str | os.PathLike) -> tuple[int, float, float]:
    """(pages, width in bp, height in bp) of the first page, from pdfinfo."""
    out, _ = _run([PDFINFO, str(pdf_path)])
    mp = re.search(r"^Pages:\s+(\d+)", out, re.M)
    ms = re.search(r"^Page size:\s+([0-9.]+) x ([0-9.]+) pts", out, re.M)
    if mp is None or ms is None:
        raise FigureCheckError(f"cannot read the page size of {pdf_path} from pdfinfo")
    return int(mp.group(1)), float(ms.group(1)), float(ms.group(2))


def pdf_fonts(pdf_path: str | os.PathLike) -> list[dict]:
    """The rows of pdffonts: name, type, encoding, emb, sub, uni."""
    return _pdffonts(pdf_path)[0]


def _pdffonts(pdf_path: str | os.PathLike) -> tuple[list[dict], str]:
    out, err = _run([PDFFONTS, str(pdf_path)])
    lines = out.splitlines()
    rows = []
    for line in lines[2:]:
        tok = line.split()
        if len(tok) < 8:
            continue
        rows.append(dict(name=tok[0], type=" ".join(tok[1:-6]), encoding=tok[-6], emb=tok[-5], sub=tok[-4],
                         uni=tok[-3]))
    return rows, err


def finalize(fig: Figure, name: str, pdf_path: str | os.PathLike, *,
             png_path: str | os.PathLike | None = None) -> dict:
    """Check the saved PDF and the figure against §5; raise FigureCheckError listing every problem. Checks: one
    page whose width is the registered width (251.06 bp for W1, 514.07 bp for W2) and whose height is the
    registered height, each within 0.5 bp; every visible text in [TEXT_MIN_PT, TEXT_MAX_PT] = [7, 7.970] pt (C62:
    none larger than the caption, within TEXT_TOL_PT, so that CAPTION_PT passes and 8.0 bp fails); no Type 3,
    non-embedded or DejaVu font (pdffonts); no layout engine, no panel moved after panel_row placed it, no ink
    outside the page (texts_outside_page) and no two texts overlapping (text_overlaps). Warns (GlyphSizeWarning) if
    a mathtext glyph is below SCRIPT_MIN_PT (4.9 pt, a first-level script of 7-pt text) and (FigureWarning) if
    pdffonts prints a warning. Then write a 300-dpi PNG preview to `png_path` (if given). Returns a report: text_pt
    (the nominal text sizes), min_glyph_pt (the smallest glyph, mathtext scripts included) and small_glyphs ([size,
    text] of the mathtext texts with glyphs below SCRIPT_MIN_PT)."""
    spec = figure_spec(name)
    problems = []
    pages, w_bp, h_bp = pdf_page(pdf_path)
    exp_w, exp_h = spec.width_in * BP_PER_IN, spec.height_in * BP_PER_IN
    if pages != 1:
        problems.append(f"{pages} pages, expected 1")
    if abs(w_bp - exp_w) > PAGE_TOL_BP:
        problems.append(f"page width {w_bp:.2f} bp, expected {exp_w:.2f} bp ({spec.width})")
    if abs(h_bp - exp_h) > PAGE_TOL_BP:
        problems.append(f"page height {h_bp:.2f} bp, expected {exp_h:.2f} bp ({spec.height_in} in)")
    fonts, fonts_stderr = _pdffonts(pdf_path)
    for f in fonts:
        if "Type 3" in f["type"]:
            problems.append(f"Type 3 font {f['name']}")
        if f["emb"] != "yes":
            problems.append(f"font {f['name']} is not embedded")
        if BANNED_FONT.lower() in f["name"].lower():
            problems.append(f"DejaVu font {f['name']} (never DejaVu Sans)")
    sizes = text_sizes(fig)
    bad = [(s, t) for s, t in sizes if s < TEXT_MIN_PT - TEXT_TOL_PT or s > TEXT_MAX_PT + TEXT_TOL_PT]
    span = f"[{TEXT_MIN_PT:g}, {TEXT_MAX_PT:.3f}] pt"          # C62: [7, 7.970] pt
    for s, t in bad[:10]:
        problems.append(f"text {t[:40]!r} at {s:g} pt is outside {span}")
    if len(bad) > 10:
        problems.append(f"{len(bad) - 10} more texts outside {span}")
    if fig.get_layout_engine() is not None:
        problems.append(f"layout engine {type(fig.get_layout_engine()).__name__} is set (margins are fixed)")
    for i, ax in enumerate(fig.axes):
        want = getattr(ax, "_sublet_rect_in", None)
        if want is None:
            continue
        got = axes_rect_in(ax)
        if max(abs(a - b) for a, b in zip(got, want)) > GEOMETRY_TOL_IN:
            problems.append(f"axes {i} moved from {tuple(round(v, 3) for v in want)} to "
                            f"{tuple(round(v, 3) for v in got)} in after panel_row")
    outside = texts_outside_page(fig)
    if outside:
        problems.append(f"text partly outside the page: {outside[:5]} (right-align an x tick label at the end of "
                        "the axis with end_label_inside)")
    overlaps = text_overlaps(fig)
    if overlaps:
        problems.append(f"{len(overlaps)} pairs of texts overlap: {overlaps[:5]}")
    if problems:
        raise FigureCheckError(f"{name}: " + "; ".join(problems))
    glyphs = math_glyph_sizes(fig)
    small = sorted({(round(g, 3), t) for g, t in glyphs if g < SCRIPT_MIN_PT - 1e-6})
    if small:
        warnings.warn(f"{name}: mathtext glyphs below {SCRIPT_MIN_PT:g} pt (C62: a first-level script of 7-pt text"
                      f"): {small[:5]}", GlyphSizeWarning, stacklevel=2)
    if fonts_stderr.strip():
        # e.g. text set explicitly in Nimbus Sans (OpenType/CFF), which matplotlib embeds as CID Type 0C with a
        # font-type mismatch that poppler reports
        warnings.warn(f"{name}: pdffonts reports: {fonts_stderr.strip()[:300]}", FigureWarning, stacklevel=2)
    if png_path is not None:
        Path(png_path).parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(png_path, format="png", dpi=PREVIEW_DPI, metadata={"Software": None})
    all_glyphs = [s for s, _ in sizes] + [g for g, _ in glyphs]
    return dict(name=name, pages=pages, width_bp=w_bp, height_bp=h_bp, fonts=[f["name"] for f in fonts],
                text_pt=sorted({s for s, _ in sizes}),
                min_glyph_pt=round(min(all_glyphs), 3) if all_glyphs else None,
                small_glyphs=[[g, t] for g, t in small], outside_page=outside)


def _jsonable(o, path: str = "data"):
    if isinstance(o, Mapping):
        out = {}
        for k, v in o.items():
            if not isinstance(k, (str, int)) or isinstance(k, bool):
                raise StyleError(f"{path}: JSON keys must be strings or integers, not {k!r}")
            out[str(k)] = _jsonable(v, f"{path}.{k}")
        return out
    if isinstance(o, np.ndarray):
        return _jsonable(o.tolist(), path)
    if isinstance(o, (list, tuple)):
        return [_jsonable(v, f"{path}[{i}]") for i, v in enumerate(o)]
    if isinstance(o, (bool, np.bool_)):
        return bool(o)
    if isinstance(o, (int, np.integer)):
        return int(o)
    if isinstance(o, (float, np.floating)):
        f = float(o)
        if math.isnan(f):
            return None
        if math.isinf(f):
            raise StyleError(f"{path}: an infinite value cannot be a plotted number")
        return f
    if o is None or isinstance(o, str):
        return o
    raise StyleError(f"{path}: cannot write {type(o).__name__} to JSON")


_SOURCE_ROOTS = ("code/analysis/out/", "code/sim/out/")


def check_source(path: str | os.PathLike) -> str:
    """Repo-relative form of a file a figure script read; StyleError unless it lies in code/analysis/out/,
    code/theory_checks/**/out/ or code/sim/out/."""
    p = Path(path)
    if p.is_absolute():
        try:
            p = p.resolve().relative_to(REPO)
        except ValueError:
            raise StyleError(f"figure scripts read only code/analysis/out/, code/theory_checks/*/out/ or "
                             f"code/sim/out/; {path} is outside the repository") from None
    rel = p.as_posix()
    parts = p.parts
    ok = any(rel.startswith(r) for r in _SOURCE_ROOTS) or (
        rel.startswith("code/theory_checks/") and "out" in parts[2:-1])
    if not ok or ".." in parts:
        raise StyleError(f"figure scripts read only code/analysis/out/, code/theory_checks/*/out/ or code/sim/out/; "
                         f"not {rel}")
    return rel


def output_dirs(pdf_dir: str | os.PathLike | None = None,
                out_dir: str | os.PathLike | None = None) -> tuple[Path, Path]:
    """(PDF folder, JSON/PNG folder): the arguments, else SUBLET_FIGS_PDF_DIR / SUBLET_FIGS_OUT_DIR, else
    paper/figures and code/sim/out/figs."""
    pd = Path(pdf_dir) if pdf_dir is not None else Path(os.environ.get(ENV_PDF_DIR) or DEFAULT_PDF_DIR)
    od = Path(out_dir) if out_dir is not None else Path(os.environ.get(ENV_OUT_DIR) or DEFAULT_OUT_DIR)
    return pd, od


_MISSING_GLYPH = re.compile(r"Glyph \d+ .*missing from font")
_MATHTEXT_LOGGER = "matplotlib.mathtext"


class _MathtextGlyphLog(logging.Handler):
    """Collects mathtext's "Font ... does not have a glyph for ..., substituting with a dummy symbol"."""

    def __init__(self):
        super().__init__(level=logging.WARNING)
        self.messages: list[str] = []

    def emit(self, record):
        msg = record.getMessage()
        if "does not have a glyph for" in msg:
            self.messages.append(msg)


def _savefig_pdf(fig: Figure, name: str, path: Path) -> None:
    """fig.savefig as PDF; raises FigureCheckError if a glyph is missing from the fonts. Text: the glyph fallback
    chain is Liberation Sans alone (font.family "sans-serif"; see the module docstring), and matplotlib warns
    "Glyph N (...) missing from font(s) Liberation Sans" and draws an empty box. Mathtext: the glyph is in neither
    the mathtext fonts nor stixsans, and mathtext logs that it substitutes a dummy symbol. Other warnings are passed
    on once each."""
    log = logging.getLogger(_MATHTEXT_LOGGER)
    handler = _MathtextGlyphLog()
    old_level = log.level
    if log.getEffectiveLevel() > logging.WARNING:
        log.setLevel(logging.WARNING)
    log.addHandler(handler)
    try:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            fig.savefig(path, format="pdf", dpi=RASTER_DPI, metadata={"CreationDate": None}, bbox_inches=None)
    finally:
        log.removeHandler(handler)
        log.setLevel(old_level)
    missing, passed = [], set()
    for w in caught:
        msg = str(w.message)
        if issubclass(w.category, UserWarning) and _MISSING_GLYPH.search(msg):
            missing.append(msg)
        elif (w.category, msg) not in passed:
            passed.add((w.category, msg))
            warnings.warn_explicit(w.message, w.category, w.filename, w.lineno, source=w.source)
    missing += handler.messages
    if missing:
        raise FigureCheckError(f"{name}: glyphs missing from the fonts (drawn as empty boxes or dummy symbols): "
                               + "; ".join(sorted(set(missing))[:5]))


_SUBSET_NAME = re.compile(rb"(/(?:BaseFont|FontName) /)([A-Z]{6})(\+[^\s/\[\]<>(){}%]+)")


def _font_program(pdf: bytes, font_name: bytes) -> bytes:
    """The raw stream of the font program (FontFile, FontFile2 or FontFile3) of the font descriptor whose
    /FontName is `font_name`; b"" if it is not found."""
    d = re.search(rb"/FontName /" + re.escape(font_name) + rb"(?=[\s/\[\]<>(){}%])", pdf)   # not a longer name
    if d is None:
        return b""
    i = d.start()
    m = re.search(rb"/FontFile[23]? (\d+) 0 R", pdf[i:pdf.find(b"endobj", i)])
    if m is None:
        return b""
    j = re.search(rb"(?<![0-9])%s 0 obj" % m.group(1), pdf)
    if j is None:
        return b""
    k = pdf.find(b"stream", j.end())
    e = pdf.find(b"endstream", k)
    return pdf[k:e] if 0 <= k < e else b""


def retag_font_subsets(pdf_path: str | os.PathLike, name: str) -> dict[str, str]:
    """Give each embedded font subset of the PDF a tag of its own; returns {old name: new name}.

    matplotlib 3.10 derives the six-letter tag of a subset (e.g. FRZNSF+LiberationSans) from the font file's whole
    character map, so every subset of a face gets the same tag in every figure, and the paper PDF that pdfTeX builds
    from the figures carries different subsets under one name. The new tag is derived from SHA-256 of (figure name,
    PostScript name, embedded font program), so it is deterministic and differs between figures and between
    subsets. The tag keeps its length, so the PDF's byte offsets stay valid."""
    path = Path(pdf_path)
    pdf = path.read_bytes()
    faces = {m.group(2) + m.group(3): m.group(3)[1:] for m in _SUBSET_NAME.finditer(pdf)}
    new, used = {}, set()
    for old, ps in sorted(faces.items()):
        seed = name.encode() + b"\0" + ps + b"\0" + _font_program(pdf, old)
        for salt in range(1000):
            n = int.from_bytes(hashlib.sha256(seed + salt.to_bytes(2, "big")).digest()[:8], "big")
            tag = "".join(string.ascii_uppercase[(n // 26 ** i) % 26] for i in range(6)).encode()
            if tag not in used:
                break
        used.add(tag)
        new[old] = tag
    if not new:
        return {}
    out = _SUBSET_NAME.sub(lambda m: m.group(1) + new[m.group(2) + m.group(3)] + m.group(3), pdf)
    if len(out) != len(pdf):
        raise FigureCheckError(f"{name}: renaming the font subsets changed the PDF's length")
    path.write_bytes(out)
    return {old.decode(): (new[old] + b"+" + ps).decode() for old, ps in faces.items()}


def save(fig: Figure, name: str, data: Mapping, *, sources: Sequence[str | os.PathLike] = (),
         pdf_dir: str | os.PathLike | None = None, out_dir: str | os.PathLike | None = None) -> dict:
    """Write <pdf_dir>/<name>.pdf and <out_dir>/<name>.json (the plotted numbers, with the files read) and
    <out_dir>/<name>.png, after finalize() passes. On a missing glyph or a failed check nothing is written and
    FigureCheckError is raised. Layers with more than 5,000 marks are rasterized at 600 dpi; the PDF has no
    CreationDate, and each font subset in it has a tag of its own (retag_font_subsets)."""
    spec = figure_spec(name)
    tag = getattr(fig, "_sublet_name", None)
    if tag is not None and tag != name:
        raise StyleError(f"figure was made as {tag!r}, not {name!r}")
    if not isinstance(data, Mapping) or not data:
        raise StyleError("data must be a non-empty mapping of the plotted numbers")
    payload = {"figure": name, "size_in": [round(spec.width_in, 4), spec.height_in],
               "sources": [check_source(s) for s in sources], "data": _jsonable(data)}
    text = json.dumps(payload, indent=1, allow_nan=False) + "\n"
    pdf_dir_p, out_dir_p = output_dirs(pdf_dir, out_dir)
    pdf_dir_p.mkdir(parents=True, exist_ok=True)
    out_dir_p.mkdir(parents=True, exist_ok=True)
    pdf_path = pdf_dir_p / f"{name}.pdf"
    json_path = out_dir_p / f"{name}.json"
    png_path = out_dir_p / f"{name}.png"
    rasterize_dense(fig)
    tmp_pdf = pdf_dir_p / f".{name}.partial.pdf"
    tmp_png = out_dir_p / f".{name}.partial.png"
    try:
        _savefig_pdf(fig, name, tmp_pdf)
        retag_font_subsets(tmp_pdf, name)
        report = finalize(fig, name, tmp_pdf, png_path=tmp_png)
        os.replace(tmp_pdf, pdf_path)
        os.replace(tmp_png, png_path)
    finally:
        for t in (tmp_pdf, tmp_png):
            if t.exists():
                t.unlink()
    tmp_json = out_dir_p / f".{name}.partial.json"
    tmp_json.write_text(text)
    os.replace(tmp_json, json_path)
    report.update(pdf=str(pdf_path), json=str(json_path), png=str(png_path))
    return report


__all__ = [
    "W1", "W2", "WIDTHS", "FIGURES", "FigureSpec", "register_supplementary", "figure_spec", "new_figure",
    "CAPTION_PT", "TEXT_MIN_PT", "TEXT_MAX_PT", "TEXT_TOL_PT", "LABEL_PT", "TICK_PT", "LETTER_PT", "SCRIPT_MIN_PT",
    "MARGIN_RIGHT", "MARGIN_BOTTOM", "MARGIN_TOP", "LEGEND_ROW", "LEFT_LABEL", "LEFT_SHARED", "panel_row",
    "axes_rect_in", "ytick_reserve", "panel_letters", "readable_on_white", "TEXT_CONTRAST", "THEORY_LABEL_GREY", "RC", "apply", "require_font", "Policy", "POLICIES",
    "FIGURE_POLICIES", "SUPP_POLICIES", "SUPP_ONLY_KEYS", "SUPP_POLICIES_MS4", "SUPP_ONLY_KEYS_MS4",
    "SUPP_POLICIES_MS5", "policy",
    "check_unique", "check_color_reuse",
    "check_policies", "legend_order",
    "ENV_LINESTYLES", "env_linestyle", "policy_kwargs", "plot_policy", "scatter_policy", "policy_hline",
    "errorbars", "band", "direct_label", "arrow", "THEORY_STYLES", "theory_line", "halo", "reference_line",
    "shade_region", "ygrid", "log2_axis", "log_axis", "end_label_inside", "symlog_minutes", "PLAIN", "ramp",
    "ratio_norm", "RATIO_CMAP", "inset_colorbar", "policy_handles", "env_handles", "legend_row", "corner_legend",
    "rasterize_dense", "text_sizes", "math_glyph_sizes", "ink_outside_sides", "texts_outside_page", "drawn_texts",
    "text_overlaps", "pdf_page",
    "pdf_fonts", "finalize",
    "retag_font_subsets", "check_source", "output_dirs", "save", "StyleError", "FigureCheckError", "FigureWarning",
    "GlyphSizeWarning",
]
