"""Helpers shared by the MS5b supplementary E7 scripts figs/supp/sf_e7_intensity.py, sf_e7_decomp.py and
sf_e7_boundary.py (design/sublet_v2.md §11, W4, W9, W10; unit U39). Not a figure script (no NAME): it reads nothing.

Contents: the input names of the confirmation (``MAIN`` ... ``ANALYSIS``: the versioned summaries of
code/sim/out/sublet_v2/<part>/ and analysis.json); the registry key of each confirmation tag (``KEY_OF_TAG``: the
summaries carry no style key for the MS5b tags, so the map is the scripts' own, as figs.common.E1_TAGS is E1's; the
keys are those of style's C41 table, whose notes name the tags); the registered statistic (``med_ci``: the median and
its 95% week-bootstrap percentile interval of ms5b_common.bootstrap_median_ci, imported read-only, with its seed and
resample count as registered, W9); table access (``val``, ``weeks_of``, ``modes_of``) and the meta block of an extract
(``meta_of``: each part's git revision, `reduced` from the summaries' meta.reduced, since analysis.json has no such
flag, W13); a run file's name and digest (``run_file``, ``sha256_of``, W10); labels wrapped at a break between words
(``wrap``) and joined into a list (``join_labels``), as plain text for a data file (``plain_label``); an upper bound
at one significant digit for a caption (``bound_text``); and the LaTeX of the tables (``tex``, ``num``,
``interval``, ``week_span``, ``chunks``, ``longtable``: one-column mode, groups kept on one page, ``ONE_COLUMN``,
``KEEP_ROWS``; C50: ``cont_head``, the "Table <n>, continued" line of a longtable's head on its later pages).
"""
from __future__ import annotations

import hashlib
import math
import re
from typing import Iterable, Mapping, Sequence

from figs import style
from figs.common import MissingKey, align_baselines, text_width_in
from sublet.experiments import ms5b_common as m5

CONF = "code/sim/out/sublet_v2"
MAIN = f"{CONF}/main/summary.json"
SEEDS = f"{CONF}/seeds/summary.json"
SECOND = f"{CONF}/second/summary.json"
E3 = f"{CONF}/e3/summary.json"
FAM = f"{CONF}/fam/summary.json"
GRID = f"{CONF}/grid/summary.json"
ANALYSIS = f"{CONF}/analysis.json"
PART_FILES = {"main": MAIN, "seeds": SEEDS, "second": SECOND, "e3": E3, "fam": FAM, "grid": GRID}

# the registry key of each confirmation tag (ms5b_common.TAGS; style's C41 notes name the tag of each MS5b key)
KEY_OF_TAG = {"Sublet": "sublet_v2", "A9": "a9", "Sublet-1way": "sublet_1way", "BL1-GP": "bl1_gp",
              "Sublet-MS4": "sublet_ms4", "BL1": "bl1", "BL1-BO": "bl1_bo", "BL2": "bl2", "BL3-0": "bl3_0",
              "BL4": "bl4", "BL5-cur": "bl5_cur", "BL5": "bl5_lag", "BL5-tau60": "bl5_tau60", "BL5N": "bl5n",
              "BL1N": "bl1n", "CR": "cr", "A9-noMBB": "a9_nombb", "A9-noCommit": "a9_nocommit", "A9-noIns": "a9_noins",
              "A9-kstar": "a9_kstar", "A9-static": "a9_static", "A6": "a6", "A9-lag": "a9_lag", "BL1-lag": "bl1_lag",
              "Sublet-lag": "sublet_v2_lag", "BL1-G": "bl1_g1", "BL5-G": "bl5_g1"}
TAG_OF_KEY = {k: t for t, k in KEY_OF_TAG.items()}
if len(TAG_OF_KEY) != len(KEY_OF_TAG) or not set(KEY_OF_TAG.values()) <= set(style.POLICIES):
    raise style.StyleError("ms5b_e7_lib: KEY_OF_TAG must map each tag to its own registry key")
TRACE, HON = m5.TRACE_MODE, m5.HON_MODE
STRESS = m5.stress_modes()
E7_TAGS = m5.E7_TAGS                     # the 22 tags of §3 in its order (the rows of the tables)
BOOT = {"seed": m5.BOOT_SEED, "B": m5.BOOT_B}


def label(tag: str) -> str:
    """The registry label of a confirmation tag."""
    return style.POLICIES[KEY_OF_TAG[tag]].label


# ---------------------------------------------------------------------------------------------------------------
# statistics and table access
def med_ci(values: Iterable) -> dict:
    """{median, lo, hi, n}: the median of the non-null values with the 95% week-bootstrap percentile interval of
    ms5b_common.bootstrap_median_ci (seed 20261031, 10,000 resamples; §4.5, W9); all None with n 0 for no value."""
    v = [float(x) for x in values if x is not None]
    if not v:
        return {"median": None, "lo": None, "hi": None, "n": 0}
    b = m5.bootstrap_median_ci(v)
    return {"median": b["median"], "lo": b["ci"][0], "hi": b["ci"][1], "n": b["n"]}


def val(table: Mapping, tag: str, mode: str, cell: str, seed: int | str = 0):
    """table[tag][mode][cell][seed], None where a level is missing (a summary's `table`)."""
    return (((table.get(tag) or {}).get(mode) or {}).get(str(cell)) or {}).get(str(seed))


def weeks_of(table: Mapping, tags: Iterable[str] | None = None, modes: Iterable[str] | None = None) -> list[str]:
    """The week cells (digits) of a summary's table, in numeric order, over `tags` and `modes` (default all)."""
    ts = list(table) if tags is None else [t for t in tags if t in table]
    cells = {c for t in ts for m, by_c in table[t].items() if modes is None or m in modes for c in by_c}
    return sorted((c for c in cells if str(c).isdigit()), key=int)


def modes_of(table: Mapping, tag: str) -> list[str]:
    return list((table.get(tag) or {}))


def meta_of(parts: Mapping[str, Mapping]) -> dict:
    """The meta block of an extract: {git_revision: {part: revision}, reduced}, `reduced` true if any summary's
    meta.reduced is (analysis.json has no such flag; W13)."""
    rev, red = {}, False
    for p, s in parts.items():
        m = s.get("meta") or {}
        rev[p] = m.get("git_revision")
        if "reduced" in m:
            red = red or bool(m.get("reduced"))
    return {"git_revision": rev, "reduced": red}


def need_tags(table: Mapping, tags: Iterable[str], what: str) -> None:
    missing = [t for t in tags if t not in table]
    if missing:
        raise MissingKey(f"{what}: table has no tag {missing} (tags there: {sorted(table)})")


# ---------------------------------------------------------------------------------------------------------------
# run files (W10)
def run_file(part: str, job: str) -> str:
    """The repository-relative run file of a job id (e7h writes e7h:main:k=week:tag=BL1:c=301 as
    e7h__main__k__week__tag__BL1__c__301.json under <part>/runs/)."""
    return f"{CONF}/{part}/runs/{re.sub(r'[:=]', '__', job)}.json"


def sha256_of(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


# ---------------------------------------------------------------------------------------------------------------
# labels
_BREAKS = (", ", " + ", " (")


def _outside_math(text: str, i: int) -> bool:
    return text[:i].count("$") % 2 == 0


def wrap(fig, text: str, max_in: float) -> str:
    """`text` as one line if it is at most `max_in` wide at 9 pt, else split once into two lines at the break (after
    ', ' or ' + ', or before ' (', outside $...$) that gives the narrowest widest line; unchanged where it has no
    break. The words stay the registry label's; only the line break is added."""
    if "\n" in text or text_width_in(fig, text) <= max_in:
        return text
    best = None
    for sep in _BREAKS:
        start = 0
        while (i := text.find(sep, start)) >= 0:
            start = i + 1
            if not _outside_math(text, i):
                continue
            a, b = (text[:i + len(sep)].rstrip(), text[i + len(sep):]) if sep != " (" else (text[:i], text[i + 1:])
            w = max(text_width_in(fig, a), text_width_in(fig, b))
            if best is None or w < best[0]:
                best = (w, f"{a}\n{b}")
    return text if best is None else best[1]


# ---------------------------------------------------------------------------------------------------------------
# LaTeX
def tex(s) -> str:
    """Text for LaTeX: &, %, _ and # escaped outside $...$ (registry labels carry their math)."""
    parts = str(s).split("$")
    for j in range(0, len(parts), 2):
        parts[j] = (parts[j].replace("\\", r"\textbackslash{}").replace("&", r"\&").replace("%", r"\%")
                    .replace("_", r"\_").replace("#", r"\#"))
    return "$".join(parts)


def num(v, fmt: str = ".3f") -> str:
    """A table number, '--' for None; a minus sign in math."""
    if v is None or (isinstance(v, float) and not math.isfinite(v)):
        return "--"
    s = format(float(v), fmt)
    return f"$-${s[1:]}" if s.startswith("-") else s


def interval(lo, hi, fmt: str = ".3f") -> str:
    return "--" if lo is None or hi is None else f"[{num(lo, fmt)}, {num(hi, fmt)}]"


def week_span(weeks: Sequence[str]) -> str:
    """'301--316' for a run of consecutive weeks, '101' for one, else the list."""
    ws = [int(w) for w in weeks]
    if not ws:
        return "--"
    if len(ws) == 1:
        return str(ws[0])
    if ws == list(range(ws[0], ws[-1] + 1)):
        return f"{ws[0]}--{ws[-1]}"
    return ", ".join(str(w) for w in ws)


def week_span_text(weeks: Sequence[str]) -> str:
    """week_span with an en dash for figure text and captions drafts."""
    return week_span(weeks).replace("--", "–")


def chunks(items: Sequence, size: int) -> list[list]:
    """`items` in consecutive blocks of at most `size`, the blocks as even as possible."""
    n = max(1, math.ceil(len(items) / size))
    k = math.ceil(len(items) / n) if items else 0
    return [list(items[i:i + k]) for i in range(0, len(items), k)] if items else [[]]


ONE_COLUMN = ("% longtable: needs one-column mode (in a two-column document, between \\onecolumn and \\twocolumn, "
              "as the MS4 and MS5 supplementary longtables)")
KEEP_ROWS = 16                  # a group of at most this many rows is kept on one page


def longtable(colspec: str, caption: str, label_: str, header: Sequence[str], rows: Sequence[Sequence[str]], *,
              size: str = r"\footnotesize", tabcolsep: str = "3.0pt", groups: Sequence[int] = (),
              cont: bool = True, keep: int = KEEP_ROWS, head_top: str | None = None) -> str:
    """A longtable with booktabs rules, its caption and label on the first page and its header repeated on every
    page; `groups` lists the row indices before which a \\midrule goes. `cont` False writes a continuation block (no
    caption, no label; for a table whose columns are split into blocks): longtable steps the table counter at every
    longtable, captioned or not, so the block first steps it back and the next table keeps its number. Body rows
    end with \\tabularnewline, so that a cell of a p column may start with \\raggedright (``rag``) without the array
    package; within a group (from one index of `groups` to the next; no group without `groups`) of at most `keep` rows
    (0: none) every row but
    the last ends with \\tabularnewline*, longtable's row end without a page break, so that the group stays on one
    page. `head_top` is a header line above `header` (with its own row end; e.g. a spanning head and its
    \\cmidrule). The text opens with the comment ONE_COLUMN: longtable stops in two-column mode. C50: the head on the
    pages after the first opens with "Table <n>, continued" (cont_head)."""
    head = ((head_top + "\n") if head_top else "") + " & ".join(header) + r" \\"
    lines = [ONE_COLUMN, r"\begingroup" + size + r"\setlength{\tabcolsep}{" + tabcolsep + "}",
             *([] if cont else [r"\addtocounter{table}{-1}"]),
             r"\begin{longtable}{" + colspec + "}"]
    if cont:
        lines.append(r"\caption{" + caption + r"}\label{" + label_ + r"}\\")
    else:
        lines.append(r"\multicolumn{" + str(len(header)) + r"}{@{}l}{" + caption + r"}\\[2pt]")
    lines += [r"\toprule", head, r"\midrule\endfirsthead", cont_head(len(header)), r"\toprule", head,
              r"\midrule\endhead", r"\bottomrule\endlastfoot"]                                     # C50
    gs = set(groups)
    bounds = sorted(gs | {0, len(rows)})
    nobreak = set()
    for a, b in zip(bounds, bounds[1:]):
        if gs and keep and b - a <= keep:
            nobreak.update(range(a, b - 1))
    for i, r in enumerate(rows):
        if i in gs and i:
            lines.append(r"\midrule")
        lines.append(" & ".join(r) + (r" \tabularnewline*" if i in nobreak else r" \tabularnewline"))
    lines += [r"\end{longtable}", r"\endgroup", ""]
    return "\n".join(lines)


def cont_head(n_cols: int) -> str:
    """C50 (design/ms6_spec.md §7.2, the D5 review; §7.1 D4's script items): the first line of a longtable's head on
    the pages it continues to, "Table <n>, continued" (longtable typesets the head once, after it has stepped the table
    counter, so \\thetable is the table's number, also in a continuation block that stepped the counter back)."""
    return r"\multicolumn{" + str(n_cols) + r"}{@{}l}{Table~\thetable, continued}\\[2pt]"


def join_labels(labels: Sequence[str]) -> str:
    """Registry labels as one list: 'a and b', or 'a; b; and c' where a label holds a comma itself ('Greedy,
    back-off'), so that every label reads whole."""
    out = list(labels)
    if len(out) <= 1:
        return "".join(out)
    if any("," in x for x in out):
        return "; ".join(out[:-1]) + "; and " + out[-1]
    return ", ".join(out[:-1]) + " and " + out[-1]


NAME_PT_PER_CHAR = 3.25         # the mean width of a visible character of the 8-pt table font (Times), for name_cells


def _visible(s: str) -> str:
    """The text that a cell prints, roughly: commands, math shifts, braces and script marks dropped."""
    return re.sub(r"[${}_^]", "", re.sub(r"\\[a-zA-Z]+\s*|\\(?=[%&_#])", "", s))


def name_cells(name: str, n_rows: int, width_in: float) -> list[str]:
    """The name cells (LaTeX, ragged right) of a group of `n_rows` rows whose name column is `width_in` wide: the name
    on the first row, or, in a group of two or more rows where the name is longer than the column holds (its visible
    characters at NAME_PT_PER_CHAR), split at the last word break (after ', ' or ' + ', or before ' (', outside
    $...$) whose first part fits, the rest on the second row, so that a two-line name does not leave an empty line
    in the group."""
    cells = [rag(name)] + [""] * (n_rows - 1)
    room = width_in * 72.0 / NAME_PT_PER_CHAR
    if n_rows < 2 or len(_visible(name)) <= room:
        return cells
    best = None
    for sep in _BREAKS:
        start = 0
        while (i := name.find(sep, start)) >= 0:
            start = i + 1
            if not _outside_math(name, i):
                continue
            a, b = (name[:i + len(sep)].rstrip(), name[i + len(sep):]) if sep != " (" else (name[:i], name[i + 1:])
            if len(_visible(a)) <= room and len(_visible(b)) <= room and (best is None or len(a) > len(best[0])):
                best = (a, b)
    if best is not None:
        cells[0], cells[1] = rag(best[0]), rag(r"\quad " + best[1])
    return cells


def rag(s: str) -> str:
    """A cell of a p column set ragged right (longtable's rows end with \\tabularnewline)."""
    return r"\raggedright " + s


def bound_text(x: float) -> str:
    """x rounded up to one significant digit ('0.0001' for 9.8e-05), so that 'within' or 'at most' it stays true."""
    if x <= 0.0:
        return "0"
    step = 10.0 ** math.floor(math.log10(x))
    return format(math.ceil(x / step - 1e-9) * step, ".12g")


def plain_label(s: str) -> str:
    """A registry label as plain text (a data file): math shifts dropped, \\% as %."""
    return str(s).replace("$", "").replace("\\%", "%")


def table_head(script: str, sources: Sequence[str]) -> str:
    """The comment line that opens every table file."""
    return f"% Written by code/sim/figs/supp/{script}.py from {', '.join(sources)}; do not edit.\n"


# ---------------------------------------------------------------------------------------------------------------
# C62 (group g5-ms5b, additive): panel titles at the caption size
TITLE_GAP_PT = 3.0              # a title starts this far right of its panel letter's ink box (as common.panel_title)


def caption_title(ax, letter, text: str):
    """C62 (group g5-ms5b; additive, nothing else calls it): a panel title at the caption size (style.LABEL_PT,
    7.97 bp; design/figure_plan.md §5, *Fonts*, C62) on the baseline of the panel letter `letter` (style.
    panel_letters), TITLE_GAP_PT right of it. common.panel_title sets its titles at TICK_PT, the 9-pt scale's single
    size. A title with a mathtext part ($W_0$) is moved onto the letter's baseline as the PDF prints it
    (common.align_baselines: matplotlib rounds a mathtext line's height up to a whole pt there, and its glyphs rise
    by the rounding). Returns the title's Text (`_sublet_role` "panel_title")."""
    from matplotlib import cbook
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    fig = ax.figure
    canvas = fig.canvas if isinstance(fig.canvas, FigureCanvasAgg) else FigureCanvasAgg(fig)
    bb = letter.get_window_extent(canvas.get_renderer())
    x = (bb.x1 / fig.dpi + TITLE_GAP_PT / style.BP_PER_IN) / float(fig.get_size_inches()[0])
    t = fig.text(x, letter.get_position()[1], text, ha="left", va="baseline", fontsize=style.LABEL_PT)
    t._sublet_role = "panel_title"
    if any(cbook.is_math_text(s) for s in str(text).split("\n")):
        align_baselines([letter, t])
    return t


__all__ = ["CONF", "MAIN", "SEEDS", "SECOND", "E3", "FAM", "GRID", "ANALYSIS", "PART_FILES", "KEY_OF_TAG",
           "TAG_OF_KEY", "TRACE", "HON", "STRESS", "E7_TAGS", "BOOT", "label", "med_ci", "val", "weeks_of",
           "modes_of", "meta_of", "need_tags", "run_file", "sha256_of", "wrap", "tex", "num", "interval",
           "week_span", "week_span_text", "chunks", "longtable", "cont_head", "ONE_COLUMN", "KEEP_ROWS", "join_labels", "rag",
           "name_cells", "NAME_PT_PER_CHAR",
           "bound_text", "plain_label", "table_head"]
