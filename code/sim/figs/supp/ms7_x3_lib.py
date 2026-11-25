"""Helpers shared by the supplementary scripts of the MS7 runs X3 (Sublet's own sensitivity and fidelity studies,
design/ms7/registration.md §2-§3): figs/supp/sf_s1_v2.py, sf_e5_v2.py, sf_e8_v2.py and sf_e9_v2.py (design/ms7/w_spec.md
§4, unit W-G4, writer C; change C58). Not a figure script (no NAME; figs/rebuild.py lists figs/supp/sf_*.py only): it
draws nothing and reads nothing by itself.

Contents:
- inputs: ``MissingInput`` (exit code 2, the file named) and ``load`` (a JSON input of a script through figs.inputs, a
  missing file stopping the build with the file named and whether it is an MS7 run output, which exists only once the
  runs are copied in, design/ms7/registration.md);
- provenance: ``provenance`` (the analysis's own record, ms7_sens_analysis.run_analysis's meta: its sha256 against the
  registration, registered_full_inputs, each input summary's sha256, revision, reduced flag and gate) and
  ``check_registered`` (a full, non-reduced analysis must be a registered one: its sha256 is the registered one and
  every input is a full run that passed an enforced gate; else StyleError, so that an analysis changed after the runs
  never reaches the supplement);
- the reduced guard: ``guard_reduced`` (data from a reduced (smoke) run is never written into paper/ or code/sim/out/:
  every output folder, the PDF's, the extract's and the tables', must then lie outside both; stage 3's guards of
  fig4_v3, table3_v3 and table5_alglb, extended to the supplementary tables) and ``run`` (figs.common.cli with the
  guard before any output is written and MissingInput turned into exit code 2);
- data files: ``csv_text`` and ``csv_entry`` (one CSV data file per experiment beside its tables, every per-run value;
  the extract records its columns, row count and sha256, and ``write_csv`` refuses to write a file of another sha256,
  as sf_e7_decomp's e7v2_rc_runs.csv);
- names and numbers: ``key_of`` and ``label_of`` (the registry key and label of a tag: the confirmation's tags by
  figs/supp/ms5b_e7_lib.KEY_OF_TAG, the MS7 tags by style.MS7_KEY_OF_TAG), ``plain`` (a label as plain text for a data
  file), ``pct`` and ``pp`` (a saving in percent and a margin in percentage points of the all-fallback cost, one
  decimal, LaTeX minus), ``span`` (a min-max range), ``week_list`` (the weeks as text), and the LaTeX helpers of
  ms5b_e7_lib (tex, num, longtable, rag, table_head), re-exported.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import sys
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence

from figs import common, style
from figs.inputs import Inputs
from figs.supp import ms5b_e7_lib as L

tex, longtable, rag, table_head, ONE_COLUMN = L.tex, L.longtable, L.rag, L.table_head, L.ONE_COLUMN
cont_head = L.cont_head
REPO = style.REPO
VERSIONED = (REPO / "paper", REPO / "code" / "sim" / "out")     # never a reduced output's folder


def num(v, fmt: str = ".3f") -> str:
    """ms5b_e7_lib.num without a negative zero: a value that rounds to zero prints unsigned ('0.000', not '$-$0.000';
    MS7 print check, 2026-11-11)."""
    s = L.num(v, fmt)
    if s.startswith("$-$"):
        try:
            if float(s[3:].replace(",", "")) == 0.0:
                return s[3:]
        except ValueError:
            pass
    return s


class MissingInput(SystemExit):
    """A required input file is missing (exit code 2, the file named)."""


def load(inp: Inputs, name: str, *, script: str, run_inputs: Sequence[str]) -> Any:
    """The JSON input `name` (repository-relative) through `inp`; MissingInput naming the file when it is absent."""
    p = inp.path(name)
    if not p.is_file():
        what = ("an MS7 run output (design/ms7/registration.md; copied in after the runs)" if name in run_inputs
                else "a versioned result file")
        raise MissingInput(f"[{script}] required input {name} is missing under {inp.root} ({what})")
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def sha256_of(inp: Inputs, name: str) -> str:
    return hashlib.sha256(inp.path(name).read_bytes()).hexdigest()


# ---------------------------------------------------------------------------------------------------------------
# provenance
def provenance(ana: Mapping, what: str) -> dict:
    """The analysis's record of itself (ms7_sens_analysis.run_analysis's meta), as the extract keeps it: exp, git
    revision, analysis sha256, the registration's record, registered_full_inputs, reduced, and per input summary its
    sha256, revision, reduced flag and gate (ok, enforced)."""
    m = ana.get("meta")
    if not isinstance(m, Mapping):
        raise common.MissingKey(f"{what}: no meta block (not an output of ms7_sens_analysis.py)")
    reg = m.get("registration") or {}
    return {"exp": m.get("exp"), "git_revision": m.get("git_revision"), "analysis_sha256": m.get("analysis_sha256"),
            "registration": {k: reg.get(k) for k in ("path", "registered_sha256", "matches")},
            "registered_full_inputs": m.get("registered_full_inputs"), "reduced": bool(m.get("reduced")),
            "inputs": [{k: x.get(k) for k in ("file", "sha256", "git_revision", "reduced", "gate_ok",
                                              "gate_enforced")} for x in (m.get("input_records") or [])]}


def check_registered(prov: Mapping, script: str) -> None:
    """A non-reduced analysis must be the registered one on full inputs (design/ms7/registration.md §1, §5): StyleError
    otherwise, naming the record."""
    if prov.get("reduced"):
        return
    if prov.get("registered_full_inputs") is not True or (prov.get("registration") or {}).get("matches") is not True:
        raise style.StyleError(
            f"[{script}] the analysis {prov.get('exp')} is not a registered analysis of full runs "
            f"(registration matches {(prov.get('registration') or {}).get('matches')}, registered_full_inputs "
            f"{prov.get('registered_full_inputs')}; design/ms7/registration.md §1): rerun it on the copied outputs")


def check_input_shas(prov: Mapping, inp: Inputs, names: Mapping[str, str], script: str) -> dict:
    """The sha256 of each summary that the script reads beside the analysis ({analysis's 'out/<rel>':
    repository-relative name}) against the one the analysis recorded: StyleError where they differ (the analysis was
    made from other summaries, or records none for it). Returns {name: sha256}."""
    rec = {x.get("file"): x.get("sha256") for x in prov.get("inputs") or []}
    out = {}
    for rel, name in names.items():
        sha = sha256_of(inp, name)
        if rec.get(rel) is None:                 # review: an analysis that recorded no such input is refused too
            raise style.StyleError(f"[{script}] the analysis records no sha256 for {rel}, so {name} is not known to be "
                                   f"the summary that the analysis read: rerun the analysis")
        if rec[rel] != sha:
            raise style.StyleError(f"[{script}] {name} is not the summary that the analysis read (sha256 {sha[:12]} "
                                   f"against the analysis's record {str(rec[rel])[:12]}): rerun the analysis")
        out[name] = sha
    return out


# ---------------------------------------------------------------------------------------------------------------
# the reduced guard and the command line
def _inside(p: Path, roots: Iterable[Path]) -> bool:
    p = p.resolve()
    return any(p == r.resolve() or r.resolve() in p.parents for r in roots)


def output_folders() -> dict[str, Path]:
    """The folders a supplementary script writes: its PDF's (common.supp_pdf_dir), its extract's and preview's
    (style.output_dirs) and its tables' (common.tables_dir)."""
    return {"pdf": common.supp_pdf_dir(), "extract": style.output_dirs()[1], "tables": common.tables_dir()}


def guard_reduced(data: Mapping, script: str) -> None:
    """Data from a reduced (smoke) run is never written into paper/ or code/sim/out/ (stage 3's guard, review of W-G2:
    a reduced extract there would end the rebuild entry's pending state): every output folder must then lie outside
    both (set SUBLET_FIGS_PDF_DIR, SUBLET_FIGS_OUT_DIR and, or through it, the tables' folder to scratch folders)."""
    if not (data.get("meta") or {}).get("reduced"):
        return
    bad = {k: str(v) for k, v in output_folders().items() if _inside(v, VERSIONED)}
    if bad:
        raise SystemExit(f"[{script}] the inputs are from a reduced run (meta.reduced): nothing is written into paper/ "
                         f"or code/sim/out/ (folders {bad}); set {style.ENV_PDF_DIR}, {style.ENV_OUT_DIR} and "
                         f"{common.ENV_TABLES_DIR} to scratch folders")


def run(script: str, build: Callable[[Inputs], dict], draw: Callable[[dict], Any], argv, *,
        after: Callable[[dict, dict], None], doc: str) -> dict:
    """figs.common.cli for a supplementary figure with tables: the reduced guard before the figure is drawn (so
    before anything is written, from the inputs or from the extract) and again before the tables; a missing input
    stops with exit code 2 and the file named."""
    def draw_checked(data: Mapping) -> Any:
        guard_reduced(data, script)
        return draw(data)

    def after_checked(data: Mapping, rep: Mapping) -> None:
        guard_reduced(data, script)
        after(data, rep)

    try:
        return common.cli(script, build, draw_checked, argv, supplementary=True, after=after_checked, doc=doc)
    except MissingInput as err:
        print(err.code, file=sys.stderr)
        raise SystemExit(2) from None


# ---------------------------------------------------------------------------------------------------------------
# data files
def _cell(v) -> str:
    if v is None:
        return ""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, float):
        if not math.isfinite(v):
            return ""
        return format(v, ".9g")
    return str(v)


def csv_text(columns: Sequence[str], rows: Iterable[Sequence]) -> str:
    """A CSV data file: the header, then one line per row (floats with 9 significant digits, None empty)."""
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(columns)
    for r in rows:
        if len(r) != len(columns):
            raise style.StyleError(f"a CSV row has {len(r)} cells, not {len(columns)}: {r}")
        w.writerow([_cell(v) for v in r])
    return buf.getvalue()


def csv_entry(file: str, columns: Sequence[str], rows: Sequence[Sequence]) -> dict:
    """The extract's entry of a data file: file name, columns, rows (the values written), row count and sha256."""
    text = csv_text(columns, rows)
    return {"file": file, "columns": list(columns), "rows": [list(r) for r in rows], "n_rows": len(rows),
            "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest()}


def write_csv(entry: Mapping, script: str) -> Path:
    """The data file of `entry` (common.write_table), refused if its text differs from the recorded sha256."""
    text = csv_text(entry["columns"], entry["rows"])
    if hashlib.sha256(text.encode("utf-8")).hexdigest() != entry["sha256"]:
        raise style.StyleError(f"[{script}] {entry['file']} differs from the sha256 that the extract records")
    return common.write_table(entry["file"], text)


# ---------------------------------------------------------------------------------------------------------------
# names and numbers
KEY_OF_TAG = {**L.KEY_OF_TAG, **style.MS7_KEY_OF_TAG}


def key_of(tag: str) -> str:
    if tag not in KEY_OF_TAG:
        raise common.MissingKey(f"no registry key for the tag {tag!r} (ms5b_e7_lib.KEY_OF_TAG, style.MS7_KEY_OF_TAG)")
    return KEY_OF_TAG[tag]


def label_of(tag: str) -> str:
    return style.POLICIES[key_of(tag)].label


def plain(s: str) -> str:
    """A registry label as plain text (math shifts and braces dropped, \\mathrm{...} unwrapped; a data file)."""
    import re
    s = re.sub(r"\\mathrm\{([^}]*)\}", r"\1", str(s))
    s = s.replace(r"\tau", "tau").replace(r"\geq", ">=").replace(r"\bar{k}", "kbar").replace(r"\%", "%")
    return s.replace("$", "").replace("{", "").replace("}", "")


def pct(v, d: int = 1) -> str:
    """A saving in percent with `d` decimals ('--' for none; LaTeX minus)."""
    return num(v, f".{d}f")


def pp(v_r0, d: int = 1) -> str:
    """A difference of r0 (cost over the all-fallback bill) in percentage points: 100 x v, `d` decimals."""
    return num(None if v_r0 is None else 100.0 * float(v_r0), f".{d}f")


def span(lo, hi, fmt: str = ".1f", scale: float = 1.0) -> str:
    """The range from lo to hi as '[a, b]' (as sf_s1's intervals), '--' when either end is missing, the value alone
    where the two agree at the printed precision."""
    if lo is None or hi is None:
        return "--"
    a, b = num(scale * float(lo), fmt), num(scale * float(hi), fmt)
    return a if a == b else f"[{a}, {b}]"


def week_list(weeks: Sequence[str]) -> str:
    """The weeks as text ('301--304', '101'; ms5b_e7_lib.week_span)."""
    return L.week_span(weeks)


def weeks_text(weeks: Sequence[str], noun: str = "week") -> str:
    """'weeks 301--304', or 'week 101' for one (noun 'config seed': 'config seeds ...')."""
    return f"{noun}{'' if len(weeks) == 1 else 's'} {week_list(weeks)}"


def median(xs) -> float | None:
    v = sorted(float(x) for x in xs if x is not None)
    if not v:
        return None
    n = len(v)
    return v[n // 2] if n % 2 else 0.5 * (v[n // 2 - 1] + v[n // 2])


def extent(xs) -> tuple[float | None, float | None]:
    v = [float(x) for x in xs if x is not None]
    return (min(v), max(v)) if v else (None, None)


def count_text(k: int, n: int) -> str:
    return f"{k}/{n}"


__all__ = ["MissingInput", "load", "sha256_of", "provenance", "check_registered", "check_input_shas",
           "output_folders", "guard_reduced", "run", "csv_text", "csv_entry", "write_csv", "KEY_OF_TAG", "key_of",
           "label_of", "plain", "pct", "pp", "span", "week_list", "weeks_text", "median", "extent", "count_text", "tex",
           "num",
           "longtable", "rag", "table_head", "ONE_COLUMN", "cont_head", "VERSIONED"]
