"""Helpers shared by the supplementary scripts of the MS7 baseline and stress study (X4, X5; e7r):
figs/supp/sf_bl_ms7.py and sf_stress_ms7.py (design/ms7/w_spec.md §4, unit W-G4 B; design/ms7/registration.md §2,
§3; change C58). Not a figure script (no NAME): it reads nothing itself.

Contents: the run outputs of e7r as their repository-relative names (``ANALYSIS``, ``SELECTION``, ``TUNE``,
``CONFIRM``: copied into code/sim/out/e7r/ after the runs, design/ms7/registration.md §4); ``MissingInput`` and
``read`` (a missing input stops the script with exit code 2 and names the file, as figs/fig4_v3.py and table3_v3.py);
the registry key of every e7r tag (``KEY_OF_TAG``: the confirmation's keys of figs/supp/ms5b_e7_lib.KEY_OF_TAG and the
MS7 keys of style.MS7_KEY_OF_TAG) and its label; the order in which the tables list the tags (``tag_order``: the
confirmation's tags in its §3 order, then the transplants, protected-only renting, the spares, MPC, the tuned settings
and the oracle reference, then any other tag, so that every tag of an analysis appears); the lender modes as the
supplement names them (``mode_text``: the tags of the confirmation's lender table, Table S-prereg-tags, for the
confirmation's and the i.i.d. lenders; words for the regional and peak-aligned lenders, which that table does not
define); the numbers of a table cell (``med_range``, ``wtl``); the extract's meta block (``meta_of``); the guard
that keeps a reduced (smoke) input out of the versioned folders (``guard_reduced``: neither paper/ nor
code/sim/out/figs/ receives anything built from meta.reduced input; review of W-G2 for figs/fig4_v3.py); and, for the
two figures (C62), ``title`` (a panel title at the caption size on its letter's baseline) and ``raise_letters``.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from figs import style
from figs.common import MissingKey, align_baselines, supp_pdf_dir, tables_dir
from figs.inputs import Inputs
from figs.supp import ms5b_e7_lib as L

E7R = "code/sim/out/e7r"
ANALYSIS = f"{E7R}/analysis.json"
SELECTION = f"{E7R}/tune/selection.json"
TUNE = f"{E7R}/tune/summary.json"
CONFIRM = f"{E7R}/confirm/summary.json"
RUN_OUTPUTS = (ANALYSIS, SELECTION, TUNE, CONFIRM)
SEED = "0"

KEY_OF_TAG: dict[str, str] = {**L.KEY_OF_TAG, **style.MS7_KEY_OF_TAG}
if len(set(KEY_OF_TAG.values())) != len(KEY_OF_TAG):
    raise style.StyleError("ms7_e7r_lib: two e7r tags share a registry key")
TAG_OF_KEY: dict[str, str] = {k: t for t, k in KEY_OF_TAG.items()}

TRACE, HON = "L-tr", "L-hon"
# the supplement's names of the lender modes (its Table S-prereg-tags defines L-tr, L-eg, L-ss, L-co, L-iid-p and
# L-hon; the regional and peak-aligned lenders of the baseline study are named in words)
MODE_WORDS = {"L-co-reg-0.5": "regional 0.5", "L-co-reg-1": "regional 1", "L-pk": "peak-aligned"}
MODE_PLAIN = {"L-co-reg-0.5": "regional 0.5", "L-co-reg-1": "regional 1", "L-pk": "peak-aligned"}


class MissingInput(SystemExit):
    """A required input file is missing (exit code 2, the file named)."""


def read(inp: Inputs, name: str, script: str) -> Any:
    """`name` parsed as JSON through `inp` (recorded as a source); MissingInput naming the file if it is absent."""
    p = inp.path(name)
    if not p.is_file():
        what = ("an MS7 run output (design/ms7/registration.md; copied in after the runs)" if name in RUN_OUTPUTS
                else "a versioned result file")
        raise MissingInput(f"[{script}] required input {name} is missing under {inp.root} ({what})")
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def key(tag: str) -> str:
    """The registry key of an e7r tag (MissingKey if the registry has none)."""
    if tag not in KEY_OF_TAG:
        raise MissingKey(f"{ANALYSIS}: tag {tag!r} has no registry key (ms5b_e7_lib.KEY_OF_TAG, "
                         f"style.MS7_KEY_OF_TAG)")
    return KEY_OF_TAG[tag]


def label(tag: str) -> str:
    """The registry label of an e7r tag."""
    return style.POLICIES[key(tag)].label


# the groups of the tables, in order: (name, the kinds or roles of the analysis's tag block that belong to it)
GROUP_ORDER = ("confirmation", "transplant-c2", "protected-only", "spares", "mpc", "tuned-T", "tuned-W",
               "mpc-reference", "other")
GROUP_TEXT = {"confirmation": "the confirmation's policies",
              "transplant-c2": r"the transplants of the $\bar{k}$ contract", "protected-only": "protected-only renting",
              "spares": "the spare variants", "mpc": "MPC at its tuned settings",
              "tuned-T": "the settings of rule T", "tuned-W": "the settings of rule W",
              "mpc-reference": "the lookahead reference", "other": "other policies"}


def group_of(tag: str, info: Mapping) -> str:
    """The table group of a tag from its analysis block (family 'ms5b': the confirmation's; kind 'tuned': rule T or W
    by the tag's suffix, MPC-T and MPC-W in group 'mpc')."""
    kind = info.get("kind")
    if info.get("family") == "ms5b":
        return "confirmation"
    if kind == "tuned":
        if tag.startswith("MPC-"):
            return "mpc"
        return "tuned-W" if tag.endswith("-W") else "tuned-T"
    if kind in ("transplant-c2", "protected-only", "spares", "mpc-reference"):
        return kind
    if kind == "mpc":
        return "mpc"
    return "other"


_CONF_ORDER = tuple(L.E7_TAGS)


def tag_order(tags: Mapping[str, Mapping]) -> list[str]:
    """Every tag of `tags` ({tag: analysis block}) in the tables' order: by GROUP_ORDER, the confirmation's tags in its
    §3 order (ms5b_e7_lib.E7_TAGS), the others by the order of style.POLICIES of their keys, then by name."""
    reg = {k: i for i, k in enumerate(style.POLICIES)}

    def rank(t):
        g = group_of(t, tags[t])
        inner = _CONF_ORDER.index(t) if t in _CONF_ORDER else len(_CONF_ORDER) + reg.get(KEY_OF_TAG.get(t, ""), 10 ** 6)
        return (GROUP_ORDER.index(g), inner, t)
    return sorted(tags, key=rank)


def mode_text(mode: str) -> str:
    """A lender mode as the supplement's tables print it."""
    return MODE_WORDS.get(mode, mode)


def mode_plain(mode: str) -> str:
    """A lender mode in a data file."""
    return MODE_PLAIN.get(mode, mode)


# ---------------------------------------------------------------------------------------------------------------
# cells
def num(v, d: int = 3) -> str:
    """A table number with d decimals ('--' for None; a minus sign in math; no '-0.000')."""
    if v is None:
        return "--"
    s = f"{float(v):.{d}f}"
    if float(s) == 0.0:
        s = s.lstrip("-")
    return f"$-${s[1:]}" if s.startswith("-") else s


def med_range(st: Mapping | None, d: int = 3) -> str:
    """'median (min--max)' of a stats block {median, min, max}; the median alone where min equals max; '--' without a
    value."""
    if not st or st.get("median") is None:
        return "--"
    m, lo, hi = num(st["median"], d), num(st.get("min"), d), num(st.get("max"), d)
    return m if lo == hi == m else f"{m} ({lo}--{hi})"


def wtl(mg: Mapping | None) -> str:
    """Weeks won, tied and lost of a margin block, 'w/t/l', with '+m' for the m missing weeks that count as losses."""
    if not mg:
        return "--"
    s = f"{mg['wins']}/{mg['ties']}/{mg['losses']}"
    return s + (f"+{mg['missing']}" if mg.get("missing") else "")


def stats_of(st: Mapping | None) -> dict | None:
    """The fields of an analysis stats or margin block that the extracts keep."""
    if st is None:
        return None
    return {k: st.get(k) for k in ("n", "n_missing", "median", "min", "max", "wins", "ties", "losses", "missing",
                                   "losses_with_missing") if k in st}


# ---------------------------------------------------------------------------------------------------------------
# meta and the guard
def meta_of(parts: Mapping[str, Mapping | None]) -> dict:
    """{git_revision: {part: revision}, reduced}: `reduced` true if any input's meta.reduced is (the analysis records
    it from part eval's summary, the selection from part tune's)."""
    rev, red = {}, {}
    for p, s in parts.items():
        m = (s or {}).get("meta") or {}
        rev[p] = m.get("git_revision")
        red[p] = bool(m.get("reduced"))
    return {"git_revision": rev, "reduced_by_input": red, "reduced": any(red.values())}


def _inside(p: Path, top: Path) -> bool:
    p, top = Path(p).resolve(), Path(top).resolve()
    return p == top or top in p.parents


VERSIONED = (style.REPO / "paper", style.DEFAULT_OUT_DIR)


def guard_reduced(data: Mapping, script: str) -> None:
    """Data built from a reduced (smoke) run is never written into paper/ (figure, tables) or code/sim/out/figs/
    (extract, preview): SystemExit naming the folders unless SUBLET_FIGS_PDF_DIR, SUBLET_FIGS_OUT_DIR and the tables'
    folder point elsewhere (a reduced extract there would end the rebuild entry's pending state, figs/rebuild.py)."""
    if not (data.get("meta") or {}).get("reduced"):
        return
    targets = {"figure": supp_pdf_dir(), "extract": style.output_dirs()[1], "tables": tables_dir()}
    bad = [f"{k} {v}" for k, v in targets.items() if any(_inside(v, top) for top in VERSIONED)]
    if bad:
        raise SystemExit(f"[{script}] the inputs are from a reduced run (meta.reduced): nothing is written into "
                         f"paper/ or code/sim/out/figs/ ({'; '.join(bad)}); set {style.ENV_PDF_DIR}, "
                         f"{style.ENV_OUT_DIR} and SUBLET_FIGS_TABLES_DIR to scratch folders")


def check_weeks(an: Mapping, what: str) -> list[str]:
    """The analysis's weeks as strings (MissingKey if it has none)."""
    ws = [str(w) for w in (an.get("weeks") or [])]
    if not ws:
        raise MissingKey(f"{what}: no weeks")
    return ws


def join(items: Iterable[str]) -> str:
    return L.join_labels(list(items))


_WORDS = ("no", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve")


def count(n: int) -> str:
    """A count in words up to twelve, else in digits (with a thousands comma)."""
    n = int(n)
    return _WORDS[n] if 0 <= n < len(_WORDS) else f"{n:,}"


# ---------------------------------------------------------------------------------------------------------------
# figures (C62)
TITLE_GAP_PT = 3.0              # a panel title starts this far right of its letter's box (common.panel_title)


def title(letter, text: str):
    """A panel title at style.LABEL_PT (C62: the caption size, as the axis labels; common.panel_title sets TICK_PT) on
    its letter's baseline, TITLE_GAP_PT right of the letter's box, a mathtext title moved onto the letter's baseline as
    printed (common.align_baselines)."""
    fig = letter.get_figure(root=True)
    bb = letter.get_window_extent(fig.canvas.get_renderer())
    x = (bb.x1 / fig.dpi + TITLE_GAP_PT / style.BP_PER_IN) / float(fig.get_size_inches()[0])
    t = fig.text(x, letter.get_position()[1], text, ha="left", va="baseline", fontsize=style.LABEL_PT)
    t._sublet_role = "title"
    align_baselines([letter, t])
    return t


def raise_letters(letters, room_in: float) -> None:
    """Move the panel letters up by `room_in` (axes placed that much below the standard top, style.panel_letters)."""
    for t in letters:
        fig = t.get_figure(root=True)
        x, y = t.get_position()
        t.set_position((x, y + room_in / float(fig.get_size_inches()[1])))


MODE_RANK = ("L-tr", "L-hon", "L-eg", "L-ss", "L-co", "L-iid-0.05", "L-iid-0.2", "L-iid-0.0005", "L-iid-0.002",
             "L-iid-0.0124", "L-co-reg-0.5", "L-co-reg-1", "L-pk")


def mode_rank(m: str) -> tuple:
    """The order of the lender modes in the tables and the data file: the confirmation's seven, then the new six."""
    return (MODE_RANK.index(m) if m in MODE_RANK else len(MODE_RANK), m)


__all__ = ["E7R", "ANALYSIS", "SELECTION", "TUNE", "CONFIRM", "RUN_OUTPUTS", "SEED", "KEY_OF_TAG", "TAG_OF_KEY",
           "TRACE", "HON", "MODE_WORDS", "MODE_PLAIN", "MissingInput", "read", "key", "label", "GROUP_ORDER",
           "GROUP_TEXT", "group_of", "tag_order", "mode_text", "mode_plain", "num", "med_range", "wtl", "stats_of",
           "meta_of", "VERSIONED", "guard_reduced", "check_weeks", "join", "count", "MODE_RANK", "mode_rank",
           "TITLE_GAP_PT", "title", "raise_letters"]
