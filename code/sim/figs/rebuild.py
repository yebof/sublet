"""The frozen rebuild of every figure from its JSON extract (design/sim_spec_ms5.md §8; deliverable D43, unit U30;
open choices M29-M33; design/Sublet_design.md Table 5.12, row MS5; design/figure_plan.md §6.3). Run through
code/sim/figs/run_all.sh, which sets the mode from its environment and runs this module in a 3 GB scope.

The list (M29). The entries come from the code, never from a hand-written table of figures:
  main     every main-text script figs/fig<N>_*.py (by N, then by file name: C42), imported here; its NAME is a
           figure of style.FIGURES with main true. Outputs paper/figures/<name>.pdf, code/sim/out/figs/<name>.json
           and <name>.png.
  supp     every supplementary script figs/supp/sf_*.py (by path), imported here, so that the MS3 scripts' own
           style.register_supplementary calls are made; its NAME is a supplementary figure of style.FIGURES.
           Outputs paper/supplement/figures/<name>.pdf, the extract and the preview, and the tables of the
           script's TABLES (or TABLE) in paper/supplement/tables/.
  float    Table III, figs/table3_e7.py: paper/floats/table3_e7.tex (with --out, since it ignores
           SUBLET_FIGS_PDF_DIR; rebuild_probe.json) and its extract code/sim/out/figs/table3_e7.json; and (C42)
           Table III v2, figs/table3_v2.py: paper/floats/table3_v2.tex and code/sim/out/figs/table3_v2.json, run
           the same way (--from-extract --out).
  print_sheet  figs/print_sheet.py (C28): code/sim/out/figs/print_check.pdf from the main-text figure PDFs (under
           CHECK=1 the rebuilt ones; a main-text figure that this run did not rebuild, with ONLY, is copied from the
           versioned PDF into the sheet's input folder, and the record says so).
  heights  paper/layout_check/pageplan/floats_heights.py, plain, --ms4 (M31) and --ms5b (C42): floats_heights.json,
           floats_heights_ms4.json and floats_heights_ms5b.json in code/sim/out/figs/, re-measured into the work
           folder and compared with the
           versioned file on every key but 'written'. The script is run from the root's copy, which resolves the
           floats, the class and the probes relative to itself (so that 'source' stays repository-relative).
  hand_set the hand-set floats paper/floats/table1_price_of_revocation.tex, table2_policies.tex, alg1_guard.tex and
           the print-check record code/sim/out/figs/print_check.md (M32), and (C42) the MS5b hand-set floats
           paper/floats/table2_policies_v2.tex, alg1_guard_v2.tex and the supplementary table
           paper/supplement/tables/ms5b_deviations.tex: no extract; listed with their sha256 and checked unchanged:
           by the run (the sha256 before and after it), and, for the floats, against the sha256 that the float's
           versioned heights record holds for the float it measured (floats_heights.json for the three frozen
           floats, floats_heights_ms5b.json for the two v2 floats: HAND_SET_HEIGHTS).
  record   code/sim/out/figs/rebuild.json, this rebuild's record (listed, never compared).
A registered figure without a script, or a script whose NAME is not registered as its kind, is a list error.

Coverage. Every file under paper/figures/, paper/supplement/figures/, paper/supplement/tables/, paper/floats/ and
code/sim/out/figs/ of the root must be an output of an entry ('unlisted' otherwise), and every output of every entry
but the record must exist ('missing' otherwise), whatever ONLY selects (§8.1).

Modes (§8.2), set by run_all.sh from its environment:
  in place (default)  the outputs are rewritten where they live (the root); each is compared with its sha256 before
                      the run. A float-heights file that differs only in 'written' is left as it is, so that git
                      status shows no change when the rebuild is exact (the record rebuild.json, which holds the times
                      of the run, is the one file that changes); one that differs elsewhere is moved into place.
  --check (CHECK=1)   every output goes to the work folder, which mirrors the root's layout (<work>/paper/figures/,
                      <work>/paper/supplement/{figures,tables}/, <work>/paper/floats/, <work>/code/sim/out/figs/:
                      SUBLET_FIGS_PDF_DIR, SUBLET_FIGS_OUT_DIR, SUBLET_FIGS_TABLES_DIR, table3_e7.py --out), and each
                      is compared byte for byte with the root's file of the same path. The record goes to
                      <work>/rebuild.json (the integrator copies it to code/sim/out/figs/rebuild.json, §8.4).
  --only REGEX        only the entries whose name or module matches (re.search); the coverage and the hand-set
                      checks still cover every entry.
  --dry-run           prints the list and the coverage, runs nothing.
  --keep              keeps the work folder; without it the rebuilt files are removed at the end and the folder keeps
                      only rebuild.json (under --check) and rebuild.log.
  --root DIR          a folder with the repository's layout in place of the repository (tests): the extracts are read
                      from it (SUBLET_FIGS_IN_ROOT), the outputs compared with its files; the code is this checkout's.
  --work DIR          the work folder (new or empty; default a new folder under TMPDIR).
Each script runs as one child in its own scope, one after another, from code/sim:
  systemd-run --user --scope -q -p MemoryMax=3G -p MemorySwapMax=0 env [-u SUBLET_FIGS_IN_ROOT | SUBLET_FIGS_IN_ROOT=
    <root>] OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 SUBLET_FIGS_PDF_DIR=<out>/<pdf folder> SUBLET_FIGS_OUT_DIR=
    <out>/code/sim/out/figs SUBLET_FIGS_TABLES_DIR=<out>/paper/supplement/tables TMPDIR=<work>/tmp
    timeout --foreground -k 10 600 /usr/bin/time -f '%e %M %x' -o <time file> <python> -m figs.<module> --from-extract
with <out> the root in place and the work folder under --check. A figure or float whose extract is missing is not run
(status 'no_extract'). The rebuild passes (exit 0) iff the list has no error, the coverage holds, every child exits 0,
every output of the entries run is identical (the float heights: equal on every key but 'written'), every hand-set
file is unchanged, no child wrote a file that is not an output of its entry, and under --check no file of the root's
five folders changed. Exit 1 otherwise, 2 on a usage error, 124 when terminated (SIGTERM, SIGINT).

The record (§8.3; M30): rebuild.json with
  status ('pass', 'fail', 'error', 'terminated'), pass, error
  meta       module, spec, mode ('in_place' | 'check'), only, root, root_is_repository, repository, git_revision and
             tracked_files_dirty (of the checkout that holds the code: read-only git), work_dir, kept, written,
             started, finished, wall_s, host, cpus, load_average_start, child_prefix, child_limit_s, versions
             (python, numpy, scipy, matplotlib, pymupdf, pillow, poppler, ghostscript, pdflatex: the tools on which
             byte identity depends, read as out/ms5spec/rebuild_probe.py reads them, poppler from pdffonts -v), fonts
             {Liberation Sans regular, bold, italic; STIXGeneral: path, sha256} (matplotlib's font lookup)
  entries[]  name, kind, script, module, outputs, extract, run (selected by --only)
  coverage   n_entries, n_listed, n_present, unlisted, missing, ok, errors (list errors)
  scripts[]  per entry run: name, kind, module, command, status ('ok', 'failed', 'timeout', 'no_extract'), exit,
             wall_s, time_wall_s, peak_rss_kb, stdout_tail, stderr_tail, and for the print sheet its inputs
  outputs[]  per output of an entry run: path, entry, sha256 (rebuilt), versioned_sha256, identical; for a
             difference the first differing byte, the differing JSON keys or the first differing .tex line
  heights    per mode ('plain', 'ms4'): file, versioned, rebuilt, equal, differing_keys (every key but 'written'),
             moved_into_place (in place)
  hand_set[] path, exists, sha256, sha256_after, unchanged, heights_record, heights_sha256, matches_heights_record, ok
  unexpected written files that no entry run lists (under --check: in the work folder; in place: changed or new
             files of the root's five folders)
  repo_check under --check: the root's files of the five folders that changed during the run (must be none)
  totals     n_scripts, n_ok, failed, n_outputs, n_identical, different, not_written, wall_s_sum, peak_rss_kb_max

Run from code/sim: python -m figs.rebuild [--check] [--only REGEX] [--dry-run] [--keep] [--root DIR] [--work DIR]

MS5b addition C42 (design/sublet_v2.md §11, W12, W16): Table III v2 as a generated float (TABLE3_V2, listed by the file
names of W2, so that the list holds it before figs/table3_v2.py exists; once the script exists its NAME must be
table3_v2); the heights entry floats_heights_ms5b (--ms5b, C43), whose record key is 'ms5b' (the earlier entries keep
'plain' and 'ms4'); each hand-set float checked against its own heights record (HAND_SET_HEIGHTS), the two v2 floats
and ms5b_deviations.tex in HAND_SET; the main-text scripts sorted by (N, file name), since figs/fig4_e7_e3.py and
figs/fig4_v2.py share N = 4. The MS5b figures of MS5B_SCRIPTS, registered in style.FIGURES by C41 before units U37
and U39 write their scripts, are listed from that map while their script does not exist (at the place their script
will take, without the tables that a script declares), so that the coverage expects their outputs and the frozen
figures still rebuild; such an entry cannot pass (its extract is missing, or its child fails without the module).
Every earlier entry, output and record field is unchanged.

MS6 addition C46 (design/ms6_spec.md M1, §2 U42): fig1v2, the paper's Fig. 1, registered in style.FIGURES before unit
U44 writes figs/fig1_v2.py, is listed from MS6_SCRIPTS while that script does not exist, by C42's rule; once it exists
the entry is the script's (NAME 'fig1v2'), between fig1 and fig2. Every earlier entry is unchanged.

MS7 addition C58 (design/ms7/w_spec.md §3, §4 unit W-G2): the MS7 main-text figures of MS7_SCRIPTS (fig1v3, whose
script exists, and fig4v3, the paper's Fig. 3, figs/fig4_v3.py) are listed from that map while a script is missing, by
C42's rule; Tables IV and V (MS7_FLOATS: table3_v3 and table5_alglb, figs/table3_v3.py and figs/table5_alglb.py) are
float entries after Table III v2, run as it is (--from-extract --out), each script's NAME checked. An entry of
MS7_PENDING is pending in a root while none of its outputs exists there and one of the MS7 run outputs it is built
from (MS7_PENDING's paths, the scripts' RUN_INPUTS: X1's, X3's and X4's analyses, copied into code/sim/out/ after the
runs) is missing there: the coverage does not count its outputs as missing (coverage.pending names it), it is not run
(status 'pending', which totals.pending lists and totals.failed does not), its outputs are not compared, and the
record's entries mark it (pending). Once the run outputs are in the root, the entry is an ordinary one: its outputs
must exist and be rebuilt identically, so a final render that was not done fails the rebuild. Every earlier entry,
output and record field is unchanged.

MS7 addition C58 (design/ms7/w_spec.md §4, unit W-G4; registration of unit W-G4-0): the eight supplementary figures of
the runs X1-X5 (MS7_SUPP_SCRIPTS: sf_lag_v2, sf_oos, sf_bl_ms7, sf_stress_ms7, sf_s1_v2, sf_e5_v2, sf_e8_v2, sf_e9_v2,
registered in style.FIGURES by style.SUPP_POLICIES_MS7's blocks) are supplementary entries, listed from that map while a
script is missing (C42's rule: the PDF, extract and preview as outputs), and from the script once it exists, at the path
the map names: then the tables and data files of its TABLES join the outputs, and the script must declare RUN_INPUTS, a
non-empty tuple of repository-relative files under code/sim/out/ with at least one in an MS7 run folder (MS7_RUN_DIRS),
the run outputs it is built from (a list error otherwise). The entry's run inputs (Entry.run_inputs) are the script's
RUN_INPUTS, or MS7_SUPP_RUN_INPUTS (each figure's analysis of design/ms7/registration.md §3) while the script is
missing; such an entry is pending by MS7_PENDING's rule (is_pending, pending_inputs), so a writer changes only its own
script. Every earlier entry, output and record field is unchanged. C58 (review of W-G4): an MS7 entry (pending_inputs
not empty) whose extract in the root records meta.reduced (a smoke run's) is a list error of the coverage
(reduced_extracts), so a reduced extract can neither end the pending state nor pass the rebuild.

MS8 addition (design/ms8/plan.md W; design/ms8/registration.md): the supplementary figures of the runs X6 and X7
(MS8_SUPP_SCRIPTS, one delimited block per writer unit; X7: sf_e8q) follow the rule of MS7_SUPP_SCRIPTS: listed from
the map while a script is missing (run inputs MS8_SUPP_RUN_INPUTS), from the script once it exists, at the map's path,
with RUN_INPUTS that name at least one file in an MS8 run folder (MS8_RUN_DIRS: code/sim/out/e7b/, e8q/); pending by
MS7_PENDING's rule (is_pending, pending_inputs) until the run outputs are copied in, and a reduced extract is a list
error (reduced_extracts). Each figure's set and size are in figs/style.py's SUPP_POLICIES_MS8, in its writer unit's
block (X6's sf_cap with its registry keys: MS8 unit F6; X7's sf_e8q: MS8 unit F7).
Every earlier entry, output and record field is unchanged.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import importlib
import json
import os
import platform
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

SIM = Path(__file__).resolve().parents[1]               # code/sim
REPO = SIM.parents[1]
SPEC = "design/sim_spec_ms5.md §8"

CAP = ("systemd-run", "--user", "--scope", "-q", "-p", "MemoryMax=3G", "-p", "MemorySwapMax=0")
ENV_FIXED = ("OMP_NUM_THREADS=1", "PYTHONDONTWRITEBYTECODE=1")
TIME_BIN, TIME_FMT = "/usr/bin/time", "%e %M %x"
CHILD_LIMIT_S = 600                                      # per child (the probe's limit; the longest took 2.3 s)
KILL_AFTER_S = 10
TAIL = 10                                                # stdout and stderr lines kept per child in the record

ENV_IN_ROOT = "SUBLET_FIGS_IN_ROOT"                      # figs.inputs.ENV_IN_ROOT
ENV_PDF, ENV_OUT, ENV_TABLES = "SUBLET_FIGS_PDF_DIR", "SUBLET_FIGS_OUT_DIR", "SUBLET_FIGS_TABLES_DIR"
MAIN_PDF_DIR = "paper/figures"
SUPP_PDF_DIR = "paper/supplement/figures"
TABLES_DIR = "paper/supplement/tables"
FLOATS_DIR = "paper/floats"
EXTRACT_DIR = "code/sim/out/figs"
COVERAGE_DIRS = (MAIN_PDF_DIR, SUPP_PDF_DIR, TABLES_DIR, FLOATS_DIR, EXTRACT_DIR)       # §8.1
HEIGHTS_SCRIPT = "paper/layout_check/pageplan/floats_heights.py"
HEIGHTS = (("floats_heights", (), f"{EXTRACT_DIR}/floats_heights.json"),
           ("floats_heights_ms4", ("--ms4",), f"{EXTRACT_DIR}/floats_heights_ms4.json"),
           ("floats_heights_ms5b", ("--ms5b",), f"{EXTRACT_DIR}/floats_heights_ms5b.json"),           # C42
           # C58 (design/ms7/w_spec.md §3): the MS7 floats on mock pages with the ms7 label stub; --allow-missing until
           # the two script-written tables (table3_v3, table5_alglb) exist
           ("floats_heights_ms7", ("--ms7", "--allow-missing"), f"{EXTRACT_DIR}/floats_heights_ms7.json"))
HEIGHTS_IGNORED = ("written",)                           # M31: compared on every key but this
HEIGHTS_RECORD = f"{EXTRACT_DIR}/floats_heights.json"    # the sha256 of the hand-set floats it measured
HAND_SET = (f"{FLOATS_DIR}/table1_price_of_revocation.tex", f"{FLOATS_DIR}/table2_policies.tex",
            f"{FLOATS_DIR}/alg1_guard.tex", f"{EXTRACT_DIR}/print_check.md",                  # M32
            f"{FLOATS_DIR}/table2_policies_v2.tex", f"{FLOATS_DIR}/alg1_guard_v2.tex",
            f"{TABLES_DIR}/ms5b_deviations.tex",                                              # C42 (W4, W5)
            f"{FLOATS_DIR}/table_notation.tex", f"{FLOATS_DIR}/table2_glossary.tex",           # C58: the MS7 floats
            f"{FLOATS_DIR}/alg1_guard_v3.tex", f"{FLOATS_DIR}/alg2_crr.tex", f"{TABLES_DIR}/alg_s1_guard.tex")
# C42: the heights record of each hand-set float that HEIGHTS_RECORD does not measure (the v2 floats: floats_heights.py
# --ms5b, C43)
HAND_SET_HEIGHTS = {f"{FLOATS_DIR}/table2_policies_v2.tex": f"{EXTRACT_DIR}/floats_heights_ms5b.json",
                    f"{FLOATS_DIR}/alg1_guard_v2.tex": f"{EXTRACT_DIR}/floats_heights_ms5b.json",
                    **{f"{FLOATS_DIR}/{n}.tex": f"{EXTRACT_DIR}/floats_heights_ms7.json"           # C58
                       for n in ("table_notation", "table2_glossary", "alg1_guard_v3", "alg2_crr")}}
# C42: Table III v2 (design/sublet_v2.md §11, W2), written by figs/table3_v2.py (unit U38): name, script, module
TABLE3_V2 = ("table3_v2", "code/sim/figs/table3_v2.py", "figs.table3_v2")
# C42: the MS5b figures (W1, W3, W4) and their scripts (units U37 and U39), listed from here while a script is missing
MS5B_SCRIPTS = {"fig4v2": "code/sim/figs/fig4_v2.py", "sf_e3_v2": "code/sim/figs/supp/sf_e3_v2.py",
                "sf_e7_intensity": "code/sim/figs/supp/sf_e7_intensity.py",
                "sf_e7_decomp": "code/sim/figs/supp/sf_e7_decomp.py",
                "sf_e7_boundary": "code/sim/figs/supp/sf_e7_boundary.py",
                "sf_e7_grid_dev": "code/sim/figs/supp/sf_e7_grid_dev.py",
                "sf_fam_v2": "code/sim/figs/supp/sf_fam_v2.py", "sf_e7_links": "code/sim/figs/supp/sf_e7_links.py"}
# C46: the MS6 figure registered before its script (unit U44), listed from here while the script is missing (C42's rule)
MS6_SCRIPTS = {"fig1v2": "code/sim/figs/fig1_v2.py"}
# C58: the MS7 main-text figures (w_spec §3: MS7_SCRIPTS = {fig1v3, fig4v3}), listed from here while a script is missing
MS7_SCRIPTS = {"fig1v3": "code/sim/figs/fig1_v3.py", "fig4v3": "code/sim/figs/fig4_v3.py"}
# C58: Tables IV and V of the MS7 manuscript (w_spec §2.8, unit W-G2): name, script, module, as TABLE3_V2
MS7_FLOATS = (("table3_v3", "code/sim/figs/table3_v3.py", "figs.table3_v3"),
              ("table5_alglb", "code/sim/figs/table5_alglb.py", "figs.table5_alglb"))
# C58: the entries built from the MS7 runs (design/ms7/registration.md), with the run outputs each reads (its script's
# RUN_INPUTS): pending in a root while none of its outputs exists and one of these is missing there (module docstring)
MS7_PENDING = {"fig4v3": ("code/sim/out/e7c/analysis.json", "code/sim/out/e7r/analysis.json"),
               "table3_v3": ("code/sim/out/e7c/analysis.json", "code/sim/out/e7r/analysis.json",
                             "code/sim/out/e7r/eval/summary.json"),
               "table5_alglb": ("code/sim/out/s1v2/analysis.json",)}
# C58 (w_spec §4, unit W-G4): the supplementary figures of the MS7 runs X1-X5, listed from here while a script is missing
# (C42's rule); a script that exists must be at this path
MS7_SUPP_SCRIPTS = {name: f"code/sim/figs/supp/{name}.py" for name in (
    "sf_lag_v2", "sf_oos", "sf_bl_ms7", "sf_stress_ms7", "sf_s1_v2", "sf_e5_v2", "sf_e8_v2", "sf_e9_v2")}
# C58 (W-G4): the run outputs of each, while its script is missing (each figure's analysis, design/ms7/registration.md
# §3); once the script exists its RUN_INPUTS take their place
MS7_SUPP_RUN_INPUTS = {"sf_lag_v2": ("code/sim/out/e7c/analysis.json",),
                       "sf_oos": ("code/sim/out/e7o/analysis.json",),
                       "sf_bl_ms7": ("code/sim/out/e7r/analysis.json",),
                       "sf_stress_ms7": ("code/sim/out/e7r/analysis.json",),
                       "sf_s1_v2": ("code/sim/out/s1v2/analysis.json",),
                       "sf_e5_v2": ("code/sim/out/e5v2/analysis.json",),
                       "sf_e8_v2": ("code/sim/out/e8v2/analysis.json",),
                       "sf_e9_v2": ("code/sim/out/e9v2/analysis.json",)}
# C58 (W-G4): the folders the MS7 runs are copied into (design/ms7/registration.md; a W-G4 script's RUN_INPUTS name at
# least one file in one of them, so that its entry stays pending until the runs are copied in)
MS7_RUN_DIRS = tuple(f"code/sim/out/{d}/" for d in ("e7c", "e7o", "e7r", "s1v2", "e5v2", "e8v2", "e9v2"))
# MS8 (design/ms8/plan.md W; module docstring): the supplementary figures of the MS8 runs X6 and X7
# (design/ms8/registration.md), by MS7_SUPP_SCRIPTS' rule: listed from MS8_SUPP_SCRIPTS while a script is missing (with
# MS8_SUPP_RUN_INPUTS as run inputs), from the script once it exists (its RUN_INPUTS, at least one in MS8_RUN_DIRS);
# pending while a run input is missing and no output exists. Each writer unit adds its figures in its own block below
MS8_RUN_DIRS = tuple(f"code/sim/out/{d}/" for d in ("e7b", "e8q"))
MS8_SUPP_SCRIPTS: dict[str, str] = {}
MS8_SUPP_RUN_INPUTS: dict[str, tuple] = {}
# MS8 block X7 (sf_e8q)
MS8_SUPP_SCRIPTS["sf_e8q"] = "code/sim/figs/supp/sf_e8q.py"
MS8_SUPP_RUN_INPUTS["sf_e8q"] = ("code/sim/out/e8q/analysis.json", "code/sim/out/e8q/summary.json")
# end MS8 block X7
# MS8 block X6 (sf_cap; unit F6: its keys and set in figs/style.py's MS8 unit F6 block)
MS8_SUPP_SCRIPTS["sf_cap"] = "code/sim/figs/supp/sf_cap.py"
MS8_SUPP_RUN_INPUTS["sf_cap"] = ("code/sim/out/e7b/analysis.json",)
# end MS8 block X6
RECORD = f"{EXTRACT_DIR}/rebuild.json"
RECORD_NAME, LOG_NAME = "rebuild.json", "rebuild.log"
MAX_KEYS = 40
FONTS = (("Liberation Sans regular", "Liberation Sans", "normal", "normal"),
         ("Liberation Sans bold", "Liberation Sans", "bold", "normal"),
         ("Liberation Sans italic", "Liberation Sans", "normal", "italic"),
         ("STIXGeneral", "STIXGeneral", "normal", "normal"))


class RebuildError(RuntimeError):
    """The list cannot be built (a registered figure without a script, or a script whose figure is not registered)."""


class Terminated(BaseException):
    """SIGTERM or SIGINT: the record is written with status 'terminated'."""


def _on_signal(signum, _frame):
    raise Terminated(f"signal {signal.Signals(signum).name}")


# ---------------------------------------------------------------- the list (M29)
@dataclass(frozen=True)
class Entry:
    """One entry of the rebuild: a script with the files it writes, a hand-set file or the record (module
    docstring). `outputs` are repository-relative; `extract` is the file a figure or float reads (None otherwise);
    `args` are the script's arguments after its module or path; C58 (W-G4): `run_inputs` are the MS7 run outputs that an
    MS7 supplementary figure is built from (empty for every other entry; pending_inputs)."""
    name: str
    kind: str
    script: str | None
    module: str | None
    outputs: tuple
    extract: str | None = None
    args: tuple = ()
    run_inputs: tuple = ()

    @property
    def runs(self) -> bool:
        return self.kind not in ("hand_set", "record")


def _import(module: str):
    if str(SIM) not in sys.path:
        sys.path.insert(0, str(SIM))
    return importlib.import_module(module)


def _tables_of(mod) -> tuple:
    """The supplementary tables a script writes: its TABLES, else its TABLE, else none."""
    t = getattr(mod, "TABLES", None)
    if t is None:
        t = (mod.TABLE,) if isinstance(getattr(mod, "TABLE", None), str) else ()
    return tuple(t)


def _script_key(kind: str, script: str) -> tuple:
    """The list order of a figure script (a path): main-text scripts by N, then by file name (C42: fig4_e7_e3.py
    before fig4_v2.py), then supplementary scripts by path."""
    name = Path(script).name
    if kind == "main":
        return (0, int(re.match(r"fig(\d+)", name).group(1)), name)
    return (1, 0, str(script))


def _supp_run_inputs(mod, dirs: tuple = MS7_RUN_DIRS, ms: str = "MS7") -> tuple[tuple, str | None]:
    """C58 (W-G4): (RUN_INPUTS, None) of an MS7 supplementary script, or ((), why) when it does not declare a non-empty
    tuple of repository-relative files under code/sim/out/ with at least one in a folder of MS7_RUN_DIRS; MS8: of an
    MS8 supplementary script with `dirs` MS8_RUN_DIRS and `ms` 'MS8'."""
    ri = getattr(mod, "RUN_INPUTS", None)
    if not isinstance(ri, (tuple, list)) or not ri or not all(isinstance(p, str) for p in ri):
        return (), f"declares no RUN_INPUTS (a non-empty tuple of the {ms} run outputs it reads)"
    ri = tuple(ri)
    bad = [p for p in ri if not p.startswith("code/sim/out/") or p.startswith(f"{EXTRACT_DIR}/") or ".." in p]
    if bad:
        return (), f"RUN_INPUTS {bad} are not run outputs under code/sim/out/"
    if not any(p.startswith(dirs) for p in ri):
        return (), f"RUN_INPUTS {list(ri)} name no file in an {ms} run folder {list(dirs)}"
    return ri, None


def figure_scripts() -> list[tuple[str, str, str]]:
    """(kind, module, script path relative to the repository) of the figure scripts: figs/fig<N>_*.py by N and file
    name, then figs/supp/sf_*.py by path."""
    figs = SIM / "figs"
    main = sorted(figs.glob("fig[0-9]*_*.py"), key=lambda p: _script_key("main", p.name))
    supp = sorted((figs / "supp").glob("sf_*.py"))
    return [(kind, ".".join(p.relative_to(SIM).with_suffix("").parts), p.relative_to(REPO).as_posix())
            for kind, ps in (("main", main), ("supp", supp)) for p in ps]


def entries() -> list[Entry]:
    """The rebuild's list (module docstring): the figures of style.FIGURES with their scripts (main text, then the
    supplement), Table III and Table III v2, the print sheet, the three float-height measurements, the hand-set files
    and the record. Raises RebuildError on a figure without a script (an MS5b figure of MS5B_SCRIPTS is listed from
    that map until its script exists, C42; fig1v2 of MS6_SCRIPTS likewise, C46; C58: the figures of MS7_SCRIPTS and
    MS7_SUPP_SCRIPTS likewise) or a script whose figure is not registered as its kind; C58 (W-G4): or an MS7
    supplementary script away from its MS7_SUPP_SCRIPTS path or without valid RUN_INPUTS (_supp_run_inputs)."""
    style = _import("figs.style")
    found, errors = {}, []
    run_inputs = {}                             # C58 (W-G4): the MS7 supplementary figures' run inputs
    for kind, module, script in figure_scripts():
        mod = _import(module)                   # a supplementary script registers its size on import
        name = getattr(mod, "NAME", None)
        if not isinstance(name, str):
            errors.append(f"{script} has no NAME")
            continue
        if name in found:
            errors.append(f"{script} and {found[name][2]} both draw {name!r}")
            continue
        found[name] = (kind, module, script, _tables_of(mod))
        if name in MS7_SUPP_SCRIPTS:            # C58 (W-G4): at the map's path, with its RUN_INPUTS
            run_inputs[name], why = _supp_run_inputs(mod)
            if script != MS7_SUPP_SCRIPTS[name]:
                errors.append(f"{script} draws {name!r}, whose script is {MS7_SUPP_SCRIPTS[name]} (MS7_SUPP_SCRIPTS)")
            if why:
                errors.append(f"{script}: {why} (design/ms7/w_spec.md §4, W-G4)")
        if name in MS8_SUPP_SCRIPTS:            # MS8: as MS7_SUPP_SCRIPTS, with the MS8 run folders
            run_inputs[name], why = _supp_run_inputs(mod, MS8_RUN_DIRS, "MS8")
            if script != MS8_SUPP_SCRIPTS[name]:
                errors.append(f"{script} draws {name!r}, whose script is {MS8_SUPP_SCRIPTS[name]} (MS8_SUPP_SCRIPTS)")
            if why:
                errors.append(f"{script}: {why} (design/ms8/plan.md W)")
    # C42: an MS5b figure registered before its script exists; C46: and fig1v2 (MS6_SCRIPTS)
    for name, script in {**MS5B_SCRIPTS, **MS6_SCRIPTS, **MS7_SCRIPTS,                   # C58: and MS7_SCRIPTS,
                         **MS7_SUPP_SCRIPTS, **MS8_SUPP_SCRIPTS}.items():                 # C58 (W-G4); MS8
        spec = style.FIGURES.get(name)
        if name not in found and spec is not None and not (REPO / script).is_file():
            module = ".".join(Path(script).relative_to("code/sim").with_suffix("").parts)
            found[name] = ("main" if spec.main else "supp", module, script, ())
            if name in MS7_SUPP_RUN_INPUTS:
                run_inputs[name] = tuple(MS7_SUPP_RUN_INPUTS[name])
            if name in MS8_SUPP_RUN_INPUTS:                                                # MS8
                run_inputs[name] = tuple(MS8_SUPP_RUN_INPUTS[name])
    found = dict(sorted(found.items(), key=lambda kv: _script_key(kv[1][0], kv[1][2])))
    for name, (kind, _, script, _) in found.items():
        spec = style.FIGURES.get(name)
        if spec is None:
            errors.append(f"{script} draws {name!r}, which style.FIGURES does not register")
        elif spec.main != (kind == "main"):
            errors.append(f"{script} draws {name!r}, registered as {'main-text' if spec.main else 'supplementary'}")
    for name, spec in style.FIGURES.items():
        if name not in found:
            errors.append(f"style.FIGURES registers {name!r} ({'main text' if spec.main else 'supplement'}), which no "
                          "script draws")
    if errors:
        raise RebuildError("; ".join(errors))
    out = []
    for name, (kind, module, script, tables) in found.items():
        pdf = f"{MAIN_PDF_DIR if kind == 'main' else SUPP_PDF_DIR}/{name}.pdf"
        outs = (pdf, f"{EXTRACT_DIR}/{name}.json", f"{EXTRACT_DIR}/{name}.png") + \
            tuple(f"{TABLES_DIR}/{t}" for t in tables)
        out.append(Entry(name, kind, script, module, outs, f"{EXTRACT_DIR}/{name}.json",
                         run_inputs=run_inputs.get(name, ())))                                    # C58 (W-G4)
    t3 = _import("figs.table3_e7").NAME
    out.append(Entry(t3, "float", "code/sim/figs/table3_e7.py", "figs.table3_e7",
                     (f"{FLOATS_DIR}/{t3}.tex", f"{EXTRACT_DIR}/{t3}.json"), f"{EXTRACT_DIR}/{t3}.json"))
    v2, v2_script, v2_module = TABLE3_V2         # C42: by W2's file names; its script's NAME must be the same
    if (REPO / v2_script).is_file() and getattr(_import(v2_module), "NAME", None) != v2:
        raise RebuildError(f"{v2_script} must have NAME {v2!r} (design/sublet_v2.md §11, W2)")
    out.append(Entry(v2, "float", v2_script, v2_module, (f"{FLOATS_DIR}/{v2}.tex", f"{EXTRACT_DIR}/{v2}.json"),
                     f"{EXTRACT_DIR}/{v2}.json"))
    for t, t_script, t_module in MS7_FLOATS:     # C58: Tables IV and V, as Table III v2; each script's NAME the same
        if (REPO / t_script).is_file() and getattr(_import(t_module), "NAME", None) != t:
            raise RebuildError(f"{t_script} must have NAME {t!r} (design/ms7/w_spec.md §2.8)")
        out.append(Entry(t, "float", t_script, t_module, (f"{FLOATS_DIR}/{t}.tex", f"{EXTRACT_DIR}/{t}.json"),
                         f"{EXTRACT_DIR}/{t}.json"))
    ps = _import("figs.print_sheet").NAME
    out.append(Entry(ps, "print_sheet", "code/sim/figs/print_sheet.py", "figs.print_sheet",
                     (f"{EXTRACT_DIR}/{ps}.pdf",)))
    for name, args, rel in HEIGHTS:
        out.append(Entry(name, "heights", HEIGHTS_SCRIPT, None, (rel,), args=args))
    for rel in HAND_SET:                        # named by file name: print_check.md is not the sheet print_check
        out.append(Entry(Path(rel).name, "hand_set", None, None, (rel,)))
    out.append(Entry("rebuild", "record", "code/sim/figs/rebuild.py", "figs.rebuild", (RECORD,)))
    return out


def select(ents: list[Entry], only: str | None) -> list[Entry]:
    """The entries that run: every script entry, or those whose name or module matches `only` (re.search)."""
    rx = re.compile(only) if only else None
    return [e for e in ents if e.runs and (rx is None or rx.search(e.name) or (e.module and rx.search(e.module)))]


def files_under(root: Path, dirs=COVERAGE_DIRS) -> list[str]:
    """The root-relative paths of every file under the folders `dirs` of `root`."""
    out = set()
    for d in dirs:
        top = Path(root) / d
        if top.is_dir():
            out |= {p.relative_to(root).as_posix() for p in top.rglob("*") if p.is_file()}
    return sorted(out)


def pending_inputs(e: Entry) -> tuple:
    """C58: the MS7 run outputs an entry is built from: MS7_PENDING's (Fig. 3 v3, Tables IV and V), else (W-G4) the
    entry's run_inputs (an MS7 supplementary figure: its script's RUN_INPUTS, or MS7_SUPP_RUN_INPUTS while the script is
    missing); () for every other entry."""
    return tuple(MS7_PENDING[e.name]) if e.name in MS7_PENDING else tuple(e.run_inputs)


def is_pending(root: Path, e: Entry) -> bool:
    """C58: an entry of MS7_PENDING (W-G4: or an MS7 supplementary figure) whose outputs do not exist in `root` while
    one of the MS7 run outputs it is built from (pending_inputs) is missing there (module docstring)."""
    inputs = pending_inputs(e)
    if not inputs:
        return False
    root = Path(root)
    return not any((root / p).is_file() for p in e.outputs) and any(not (root / p).is_file() for p in inputs)


def _extract_reduced(data: dict) -> bool:
    """meta.reduced of an extract: at the top level, else under `data` (style.save's layout; MS8 addition)."""
    def flag(meta) -> bool:
        r = meta.get("reduced") if isinstance(meta, dict) else None
        return any(bool(v) for v in r.values()) if isinstance(r, dict) else bool(r)     # per part, or one flag

    inner = data.get("data")
    return flag(data.get("meta")) or flag(inner.get("meta") if isinstance(inner, dict) else None)


def reduced_extracts(root: Path, ents: list[Entry]) -> list[str]:
    """C58 (review of W-G4): the list errors of the MS7 entries (pending_inputs not empty) whose extract in `root`
    records meta.reduced, an extract of a smoke run (module docstring). MS8 addition (2026-11-24, review of unit F6,
    finding 11): style.save writes an extract as {figure, size_in, sources, data} with the script's meta under `data`,
    so meta.reduced is read at the top level and, failing that, under `data` (before, an extract written by save() was
    never caught; the MS7 entries are checked the same way)."""
    out = []
    for e in ents:
        if not pending_inputs(e) or not e.extract or not (Path(root) / e.extract).is_file():
            continue
        data = _read_json(Path(root) / e.extract)
        if isinstance(data, dict) and _extract_reduced(data):
            out.append(f"{e.extract}: the extract of a reduced (smoke) run (meta.reduced); an MS7 entry is built from "
                       "the copied run outputs only (C58)")
    return out


def coverage(root: Path, ents: list[Entry]) -> dict:
    """§8.1: the files of the five folders without an entry ('unlisted') and the outputs of the entries (the record
    excepted) that do not exist ('missing'); C58: the outputs of a pending entry are not missing ('pending' names
    the entry)."""
    listed = {p for e in ents for p in e.outputs}
    present = files_under(root)
    unlisted = [p for p in present if p not in listed]
    pending = [e.name for e in ents if is_pending(root, e)]                                         # C58
    missing = sorted(p for e in ents if e.kind != "record" and e.name not in pending for p in e.outputs
                     if not (Path(root) / p).is_file())
    errors = reduced_extracts(root, ents)                                                         # C58 (W-G4)
    return {"n_entries": len(ents), "n_listed": len(listed), "n_present": len(present), "unlisted": unlisted,
            "missing": missing, "ok": not unlisted and not missing and not errors, "errors": errors,
            "pending": pending}


# ---------------------------------------------------------------- comparison
def sha256(p: Path) -> str | None:
    p = Path(p)
    if not p.is_file():
        return None
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def snapshot(root: Path, dirs=COVERAGE_DIRS) -> dict:
    """{root-relative path: (sha256, mtime_ns)} of every file under the folders `dirs` of `root`."""
    out = {}
    for rel in files_under(root, dirs):
        p = Path(root) / rel
        out[rel] = (sha256(p), p.stat().st_mtime_ns)
    return out


def _sha(snap: dict, rel: str) -> str | None:
    return (snap.get(rel) or (None, None))[0]


def json_diff(a, b, path: str = "", out: list | None = None, ignore_top: tuple = ()) -> list[str]:
    """Key paths (dotted, [i] for list items) where a and b differ; a missing key, a type change or a different leaf
    each count once; the top-level keys in `ignore_top` are skipped; at most MAX_KEYS + 1 entries are collected."""
    out = [] if out is None else out
    if len(out) > MAX_KEYS:
        return out
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b), key=str):
            if not path and k in ignore_top:
                continue
            p = f"{path}.{k}" if path else str(k)
            if k not in a or k not in b:
                out.append(p + (" (only versioned)" if k in b else " (only rebuilt)"))
            else:
                json_diff(a[k], b[k], p, out)
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            out.append(f"{path} (length {len(a)} vs {len(b)})")
        for i, (x, y) in enumerate(zip(a, b)):
            json_diff(x, y, f"{path}[{i}]", out)
    elif type(a) is not type(b) or a != b:
        out.append(path or "(root)")
    return out


def heights_diff(rebuilt: dict, versioned: dict) -> list[str]:
    """M31: the key paths where two float-height records differ, on every key but 'written'."""
    return json_diff(rebuilt, versioned, ignore_top=HEIGHTS_IGNORED)


def _first_diff(a: bytes, b: bytes) -> int | None:
    n = min(len(a), len(b))
    for i in range(0, n, 4096):
        if a[i:i + 4096] != b[i:i + 4096]:
            return next(j for j in range(i, min(i + 4096, n)) if a[j] != b[j])
    return None if len(a) == len(b) else n


def compare_bytes(new: Path, old: Path) -> dict:
    """sha256 of both files and whether they are byte-identical; for a difference the first differing byte, and the
    differing keys of a JSON file or the first differing line of a .tex file."""
    new, old = Path(new), Path(old)
    r = {"sha256": sha256(new), "versioned_sha256": sha256(old)}
    r["identical"] = r["sha256"] is not None and r["sha256"] == r["versioned_sha256"]
    if r["identical"] or r["sha256"] is None or r["versioned_sha256"] is None:
        return r
    a, b = new.read_bytes(), old.read_bytes()
    r.update(size=len(a), versioned_size=len(b), first_diff_offset=_first_diff(a, b))
    if new.suffix == ".json":
        try:
            keys = json_diff(json.loads(a), json.loads(b))
            r.update(differing_keys=keys[:MAX_KEYS], differing_keys_truncated=len(keys) > MAX_KEYS)
        except ValueError as err:
            r["json_error"] = str(err)[:200]
    elif new.suffix == ".tex":
        la, lb = a.decode("utf-8", "replace").splitlines(), b.decode("utf-8", "replace").splitlines()
        i = next((k for k, (x, y) in enumerate(zip(la, lb)) if x != y), min(len(la), len(lb)))
        r["first_diff_line"] = {"line": i + 1, "rebuilt": (la[i] if i < len(la) else None),
                                "versioned": (lb[i] if i < len(lb) else None)}
    return r


def hand_set_check(root: Path, before: dict, after: dict) -> list[dict]:
    """M32: each hand-set file exists and is unchanged by the run (sha256 before and after), and each hand-set float
    has the sha256 that its versioned heights record (floats_heights.json; C42: HAND_SET_HEIGHTS for the v2 floats)
    holds for the float it measured."""
    recs = {}
    out = []
    for rel in HAND_SET:
        sha, sha2 = _sha(before, rel), _sha(after, rel)
        e = {"path": rel, "exists": sha is not None, "sha256": sha, "sha256_after": sha2,
             "unchanged": sha is not None and sha == sha2, "heights_record": None, "heights_sha256": None,
             "matches_heights_record": None}
        if rel.startswith(FLOATS_DIR + "/"):
            e["heights_record"] = hrec = HAND_SET_HEIGHTS.get(rel, HEIGHTS_RECORD)
            if hrec not in recs:
                rec = _read_json(Path(root) / hrec) or {}
                recs[hrec] = rec.get("floats") if isinstance(rec.get("floats"), dict) else {}
            e["heights_sha256"] = (recs[hrec].get(Path(rel).stem) or {}).get("sha256")
            e["matches_heights_record"] = sha is not None and sha == e["heights_sha256"]
        e["ok"] = e["unchanged"] and e["matches_heights_record"] is not False
        out.append(e)
    return out


def _read_json(p: Path):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


# ---------------------------------------------------------------- provenance (§8.3)
def git(*args) -> str | None:
    """Read-only git in the checkout of this code (--no-optional-locks: git status does not rewrite .git/index)."""
    try:
        r = subprocess.run(["git", "--no-optional-locks", "-C", str(REPO), *args], capture_output=True, text=True,
                           timeout=60)
        return r.stdout if r.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        return None


def _tool_line(cmd: list, stream: str = "stdout") -> str | None:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        text = r.stdout if stream == "stdout" else r.stderr
        return text.splitlines()[0].strip() if text.strip() else None
    except (OSError, subprocess.SubprocessError):
        return None


def versions() -> dict:
    """The tools on which byte identity depends, read as out/ms5spec/rebuild_probe.py reads them, and poppler's
    version from pdffonts -v (stderr)."""
    out = {"python": platform.python_version()}
    for mod, key in (("numpy", "numpy"), ("scipy", "scipy"), ("matplotlib", "matplotlib"), ("fitz", "pymupdf"),
                     ("PIL", "pillow")):
        try:
            m = importlib.import_module(mod)
            out[key] = getattr(m, "__version__", None) or getattr(m, "VersionBind", None)
        except Exception as err:          # informative only
            out[key] = f"unavailable: {err!r}"
    out["poppler"] = _tool_line(["/usr/bin/pdffonts", "-v"], "stderr")
    out["ghostscript"] = _tool_line(["/usr/bin/gs", "--version"])
    out["pdflatex"] = _tool_line([str(Path.home() / ".local" / "bin" / "pdflatex"), "--version"])
    return out


def fonts() -> dict:
    """{font: {path, sha256}} of the four font files the figures embed, by matplotlib's font lookup after figs.style
    has registered Liberation Sans (null where the lookup fails)."""
    _import("figs.style")
    from matplotlib import font_manager as fm
    from matplotlib.font_manager import FontProperties
    out = {}
    for key, fam, weight, sty in FONTS:
        try:
            p = fm.findfont(FontProperties(family=fam, weight=weight, style=sty), fallback_to_default=False)
        except ValueError:
            p = None
        out[key] = {"path": p, "sha256": sha256(Path(p)) if p else None}
    return out


def now() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


def write_json(path: Path, obj) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.partial")
    tmp.write_text(json.dumps(obj, indent=1, allow_nan=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)
    return path


class Log:
    """Lines to stdout and, once a folder is set, to <work>/rebuild.log."""

    def __init__(self):
        self.f = None

    def open(self, path: Path) -> None:
        self.f = open(path, "a", encoding="utf-8")

    def line(self, s: str) -> None:
        s = f"[rebuild {time.strftime('%H:%M:%S')}] {s}"
        print(s, flush=True)
        if self.f:
            self.f.write(s + "\n")
            self.f.flush()

    def block(self, title: str, text: str) -> None:
        if self.f and text:
            self.f.write(f"----- {title} -----\n{text}{'' if text.endswith(chr(10)) else chr(10)}"
                         f"----- end {title} -----\n")
            self.f.flush()

    def close(self) -> None:
        if self.f:
            self.f.close()
            self.f = None


# ---------------------------------------------------------------- the run
@dataclass
class Run:
    """One rebuild: the mode, the root, the work folder and the folder the outputs go to (`out`: the root in place,
    the work folder under --check)."""
    root: Path
    work: Path
    check: bool
    only: str | None
    keep: bool
    log: Log = field(default_factory=Log)

    @property
    def out(self) -> Path:
        return self.work if self.check else self.root

    @property
    def is_repo(self) -> bool:
        return self.root.resolve() == REPO.resolve()


def child_env(run: Run, e: Entry, pdf_dir: Path | None = None) -> list[str]:
    """The env arguments of a child (module docstring): the input root, the fixed variables, the output folders and
    TMPDIR."""
    o = run.out
    pdf = pdf_dir if pdf_dir is not None else o / (MAIN_PDF_DIR if e.kind == "main" else SUPP_PDF_DIR)
    root_env = ["-u", ENV_IN_ROOT] if run.is_repo else [f"{ENV_IN_ROOT}={run.root.resolve()}"]
    return root_env + list(ENV_FIXED) + [f"{ENV_PDF}={pdf}", f"{ENV_OUT}={o / EXTRACT_DIR}",
                                         f"{ENV_TABLES}={o / TABLES_DIR}", f"TMPDIR={run.work / 'tmp'}"]


def argv_of(run: Run, e: Entry) -> list[str]:
    py = sys.executable
    if e.kind in ("main", "supp"):
        return [py, "-m", e.module, "--from-extract"]
    if e.kind == "float":
        return [py, "-m", e.module, "--from-extract", "--out", str(run.out / FLOATS_DIR)]
    if e.kind == "print_sheet":
        return [py, "-m", e.module]
    if e.kind == "heights":
        return [py, str(run.root / HEIGHTS_SCRIPT), *e.args, "--out", str(heights_file(run, e))]
    raise ValueError(f"{e.name}: kind {e.kind!r} has no script")


def heights_file(run: Run, e: Entry) -> Path:
    """Where a float-height measurement goes: <work>/heights/<file> in both modes (in place it is moved into place
    only when it differs on a key other than 'written')."""
    return run.work / "heights" / Path(e.outputs[0]).name


def print_inputs(run: Run, ents: list[Entry], rebuilt: set) -> tuple[Path, dict]:
    """The print sheet's input folder and the origin of each main-text PDF in it: in place the root's
    paper/figures/; under --check <work>/print_in/ with the rebuilt PDF of every main-text figure this run rebuilt
    and a copy of the versioned PDF of the others."""
    if not run.check:
        return run.root / MAIN_PDF_DIR, {e.name: "versioned (in place)" for e in ents if e.kind == "main"}
    d = run.work / "print_in"
    d.mkdir(parents=True, exist_ok=True)
    origin = {}
    for e in ents:
        if e.kind != "main":
            continue
        pdf = e.outputs[0]
        src = run.work / pdf if e.name in rebuilt and (run.work / pdf).is_file() else run.root / pdf
        if src.is_file():
            shutil.copy2(src, d / Path(pdf).name)
            origin[e.name] = "rebuilt" if src.is_relative_to(run.work) else "versioned (not rebuilt in this run)"
        else:
            origin[e.name] = "missing"
    return d, origin


def run_child(run: Run, e: Entry, env: list[str], argv: list[str]) -> dict:
    """One child in its own 3 GB scope under `timeout` and /usr/bin/time, from code/sim."""
    pr = run.work / "_time"
    pr.mkdir(parents=True, exist_ok=True)
    (run.work / "tmp").mkdir(parents=True, exist_ok=True)
    tfile = pr / f"{e.name}.txt"
    if tfile.exists():
        tfile.unlink()
    cmd = list(CAP) + ["env"] + env + ["timeout", "--foreground", "-k", str(KILL_AFTER_S), str(CHILD_LIMIT_S),
                                       TIME_BIN, "-f", TIME_FMT, "-o", str(tfile)] + argv
    t0 = time.perf_counter()
    r = subprocess.run(cmd, cwd=str(SIM), capture_output=True, text=True)
    wall = time.perf_counter() - t0
    run.log.block(f"{e.name} stdout", r.stdout)
    run.log.block(f"{e.name} stderr", r.stderr)
    out = {"name": e.name, "kind": e.kind, "module": e.module, "script": e.script, "command": cmd,
           "exit": r.returncode, "wall_s": round(wall, 3), "time_wall_s": None, "peak_rss_kb": None,
           "stdout_tail": r.stdout.splitlines()[-TAIL:], "stderr_tail": r.stderr.splitlines()[-TAIL:]}
    try:
        last = [ln for ln in tfile.read_text().splitlines() if ln.strip()][-1].split()
        out.update(time_wall_s=float(last[0]), peak_rss_kb=int(last[1]))
    except (OSError, IndexError, ValueError):
        pass
    out["status"] = "ok" if r.returncode == 0 else ("timeout" if r.returncode in (124, 137) else "failed")
    return out


def run_entries(run: Run, ents: list[Entry], todo: list[Entry]) -> list[dict]:
    """Every selected entry, one after another (figures, Table III, the print sheet, the float heights)."""
    rows, rebuilt = [], set()
    for e in todo:
        if is_pending(run.root, e):              # C58: built from MS7 run outputs that the root does not hold yet
            rows.append({"name": e.name, "kind": e.kind, "module": e.module, "script": e.script, "status": "pending",
                         "exit": None, "wall_s": None, "peak_rss_kb": None,
                         "note": "pending: the MS7 run outputs " + ", ".join(p for p in pending_inputs(e)  # C58
                                                                           if not (run.root / p).is_file())
                                 + " are missing and none of its outputs exists"})
            run.log.line(f"{e.name}: pending (its MS7 run outputs are missing)")
            continue
        if e.extract is not None and not (run.root / e.extract).is_file():
            rows.append({"name": e.name, "kind": e.kind, "module": e.module, "script": e.script, "status": "no_extract",
                         "exit": None, "wall_s": None, "peak_rss_kb": None, "note": f"{e.extract} missing"})
            run.log.line(f"{e.name}: not run, {e.extract} missing")
            continue
        extra = {}
        pdf_dir = None
        if e.kind == "print_sheet":
            pdf_dir, extra["inputs"] = print_inputs(run, ents, rebuilt)
        if e.kind == "heights":
            heights_file(run, e).parent.mkdir(parents=True, exist_ok=True)
        r = run_child(run, e, child_env(run, e, pdf_dir), argv_of(run, e))
        r.update(extra)
        rows.append(r)
        if r["status"] == "ok":
            rebuilt.add(e.name)
        run.log.line(f"{e.name}: {r['status']} (exit {r['exit']}), {r['wall_s']:.1f} s, peak RSS "
                     f"{r.get('peak_rss_kb')} kB")
    return rows


def compare_outputs(run: Run, todo: list[Entry], before: dict) -> tuple[list, dict]:
    """(outputs[], heights) of the entries run: under --check each output in the work folder against the root's file;
    in place each output against its sha256 before the run; the float heights on every key but 'written'."""
    outs, heights = [], {}
    for e in todo:
        if e.kind == "heights":
            new, ver = heights_file(run, e), run.root / e.outputs[0]
            a, b = _read_json(new), _read_json(ver)
            keys = heights_diff(a, b) if isinstance(a, dict) and isinstance(b, dict) else None
            h = {"file": e.outputs[0], "versioned": str(ver), "rebuilt": str(new), "rebuilt_exists": new.is_file(),
                 "versioned_exists": ver.is_file(), "differing_keys": keys[:MAX_KEYS] if keys is not None else None,
                 "equal": keys == [], "ignored_keys": list(HEIGHTS_IGNORED), "moved_into_place": False}
            if not run.check and keys and new.is_file():
                os.replace(new, ver)                       # it differs: the output is rewritten where it lives
                h["moved_into_place"] = True
            heights["plain" if not e.args else e.args[0].lstrip("-")] = h      # 'plain', 'ms4', 'ms5b' (C42)
            continue
        for rel in e.outputs:
            if run.check:
                c = compare_bytes(run.work / rel, run.root / rel)
                written = c["sha256"] is not None
            else:
                p = run.root / rel
                sha, old = sha256(p), before.get(rel)
                c = {"sha256": sha, "versioned_sha256": _sha(before, rel),
                     "identical": sha is not None and sha == _sha(before, rel)}
                # in place, an output is rewritten (style.save and write_table rename a new file into place)
                written = sha is not None and (old is None or p.stat().st_mtime_ns != old[1] or sha != old[0])
            outs.append({"path": rel, "entry": e.name, **c, "written": written})
    return outs, heights


def unexpected(run: Run, ents: list[Entry], todo: list[Entry], before: dict, after: dict) -> list[str]:
    """Files written that no entry run lists: under --check every file under <work>/paper and <work>/code that is not
    an output of an entry run; in place every file of the root's five folders that is new or changed and is no output
    of an entry run (the record excepted)."""
    allowed = {p for e in todo for p in e.outputs} | {RECORD}
    if run.check:
        files = []
        for top in ("paper", "code"):
            d = run.work / top
            files += [p.relative_to(run.work).as_posix() for p in d.rglob("*") if p.is_file()] if d.is_dir() else []
        return sorted(p for p in files if p not in allowed)
    return sorted(p for p, st in after.items() if before.get(p) != st and p not in allowed)


def totals(scripts: list, outs: list, heights: dict) -> dict:
    walls = [r["wall_s"] for r in scripts if r.get("wall_s") is not None]
    rss = [r["peak_rss_kb"] for r in scripts if r.get("peak_rss_kb") is not None]
    return {"n_scripts": len(scripts), "n_ok": sum(r["status"] == "ok" for r in scripts),
            "failed": [r["name"] for r in scripts if r["status"] not in ("ok", "pending")],          # C58
            "pending": [r["name"] for r in scripts if r["status"] == "pending"], "n_outputs": len(outs),
            "n_identical": sum(1 for o in outs if o["identical"]),
            "different": [o["path"] for o in outs if o["written"] and not o["identical"]],
            "not_written": [o["path"] for o in outs if not o["written"]],
            "heights_equal": {k: h["equal"] for k, h in heights.items()},
            "wall_s_sum": round(sum(walls), 2), "peak_rss_kb_max": max(rss) if rss else None}


def verdict(rec: dict) -> tuple[bool, list[str]]:
    """(pass, reasons): the rebuild passes iff nothing below is found (module docstring)."""
    why = []
    cov = rec["coverage"]
    if cov.get("errors"):
        why.append(f"list errors: {cov['errors']}")
    if cov["unlisted"]:
        why.append(f"{len(cov['unlisted'])} file(s) without an entry: {cov['unlisted'][:10]}")
    if cov["missing"]:
        why.append(f"{len(cov['missing'])} listed file(s) missing: {cov['missing'][:10]}")
    t = rec["totals"]
    if t["failed"]:
        why.append(f"{len(t['failed'])} script(s) not ok: {t['failed']}")
    if t["different"]:
        why.append(f"{len(t['different'])} output(s) differ: {t['different']}")
    if t["not_written"]:
        why.append(f"{len(t['not_written'])} output(s) not written: {t['not_written'][:10]}")
    for k, h in rec["heights"].items():
        if not h["equal"]:
            why.append(f"float heights ({k}) differ: {h['differing_keys']}")
    bad = [h["path"] for h in rec["hand_set"] if not h["ok"]]
    if bad:
        why.append(f"hand-set file(s) changed or not as measured: {bad}")
    if rec["unexpected"]:
        why.append(f"{len(rec['unexpected'])} unexpected file(s) written: {rec['unexpected'][:10]}")
    if rec.get("repo_check") and rec["repo_check"]["changed"]:
        why.append(f"the root's files changed under --check: {rec['repo_check']['changed'][:10]}")
    return not why, why


def _cleanup(run: Run) -> None:
    """Without --keep: remove the rebuilt files, keep rebuild.json (under --check) and rebuild.log."""
    if run.keep or not run.work.is_dir():
        return
    for p in run.work.iterdir():
        if p.name in (RECORD_NAME, LOG_NAME):
            continue
        if p.is_dir():
            shutil.rmtree(p, ignore_errors=True)
        else:
            p.unlink()


def rebuild(root: Path, work: Path | None, *, check: bool, only: str | None, keep: bool) -> tuple[int, dict, Path]:
    """One rebuild (module docstring): (exit code, record, record path)."""
    root = Path(root).resolve()
    if work is None:
        work = Path(tempfile.mkdtemp(prefix="sublet_rebuild_"))
    else:
        work = Path(work).resolve()
        if work.exists() and any(work.iterdir()):
            raise ValueError(f"the work folder {work} is not empty")
        work.mkdir(parents=True, exist_ok=True)
    run = Run(root, work, check, only, keep)
    run.log.open(work / LOG_NAME)
    t0 = time.perf_counter()
    dirty = git("status", "--porcelain", "--untracked-files=no")
    rec = {"status": "started", "pass": False, "error": None,
           "meta": {"module": "figs.rebuild", "spec": SPEC, "mode": "check" if check else "in_place", "only": only,
                    "root": str(root), "root_is_repository": run.is_repo, "repository": str(REPO),
                    "git_revision": (git("rev-parse", "HEAD") or "").strip() or None,
                    "tracked_files_dirty": None if dirty is None else bool(dirty.strip()),
                    "work_dir": str(work), "kept": keep, "written": None, "started": now(), "finished": None,
                    "wall_s": None, "host": os.uname().nodename, "cpus": os.cpu_count(),
                    "load_average_start": list(os.getloadavg()), "child_prefix": list(CAP) + ["env"],
                    "child_limit_s": CHILD_LIMIT_S, "versions": None, "fonts": None},
           "entries": [], "coverage": None, "scripts": [], "outputs": [], "heights": {}, "hand_set": [],
           "unexpected": [], "repo_check": None, "totals": None}
    path = work / RECORD_NAME if check else root / RECORD
    code = 1
    old_handlers = {s: signal.signal(s, _on_signal) for s in (signal.SIGTERM, signal.SIGINT)}
    try:
        rec["meta"]["versions"], rec["meta"]["fonts"] = versions(), fonts()
        ents = entries()
        todo = select(ents, only)
        rec["entries"] = [{"name": e.name, "kind": e.kind, "script": e.script, "module": e.module,
                           "outputs": list(e.outputs), "extract": e.extract, "run": e in todo,
                           "pending": is_pending(root, e)} for e in ents]                         # C58: pending
        rec["coverage"] = coverage(root, ents)
        run.log.line(f"{'CHECK' if check else 'in place'}: root {root}, work folder {work}, {len(ents)} entries, "
                     f"{len(todo)} to run (ONLY {only!r}); git {rec['meta']['git_revision']} "
                     f"(dirty {rec['meta']['tracked_files_dirty']})")
        before = snapshot(root)
        rec["scripts"] = run_entries(run, ents, todo)
        after = snapshot(root)
        pending = {r["name"] for r in rec["scripts"] if r["status"] == "pending"}               # C58: not run
        rec["outputs"], rec["heights"] = compare_outputs(run, [e for e in todo if e.name not in pending], before)
        rec["hand_set"] = hand_set_check(root, before, after)
        rec["unexpected"] = unexpected(run, ents, todo, before, after)
        if check:            # a file of the root's five folders rewritten during the run, even with the same bytes
            changed = sorted(p for p in set(before) | set(after) if before.get(p) != after.get(p))
            rec["repo_check"] = {"folders": list(COVERAGE_DIRS), "n_files": len(after), "changed": changed}
        rec["totals"] = totals(rec["scripts"], rec["outputs"], rec["heights"])
        ok, why = verdict(rec)
        rec.update(status="pass" if ok else "fail", **{"pass": ok}, reasons=why)
        code = 0 if ok else 1
    except RebuildError as err:
        rec.update(status="error", error=str(err))
        if rec["coverage"] is None:
            rec["coverage"] = {"n_entries": 0, "n_listed": 0, "n_present": 0, "unlisted": [], "missing": [],
                               "ok": False, "errors": [str(err)]}
    except Terminated as err:
        rec.update(status="terminated", error=str(err))
        code = 124
    except Exception as err:            # recorded, not raised
        import traceback
        rec.update(status="error", error=f"{type(err).__name__}: {err}", traceback=traceback.format_exc())
    finally:
        rec["meta"]["finished"] = rec["meta"]["written"] = now()
        rec["meta"]["wall_s"] = round(time.perf_counter() - t0, 2)
        write_json(path, rec)
        t = rec.get("totals") or {}
        run.log.line(f"{rec['status']}: {t.get('n_scripts')} script(s), {t.get('n_identical')} of {t.get('n_outputs')} "
                     f"output(s) identical, heights equal {t.get('heights_equal')}; record {path}")
        for r in rec.get("reasons") or ([rec["error"]] if rec.get("error") else []):
            run.log.line(f"  {r}")
        run.log.close()
        _cleanup(run)
        for s, h in old_handlers.items():
            signal.signal(s, h)
    return code, rec, path


def dry_run(root: Path, only: str | None) -> int:
    """Print the list (the entries that would run marked '*'), and the coverage."""
    ents = entries()
    todo = select(ents, only)
    cov = coverage(Path(root).resolve(), ents)
    kinds = {}
    for e in ents:
        kinds[e.kind] = kinds.get(e.kind, 0) + 1
    print(f"[rebuild] {len(ents)} entries (" + ", ".join(f"{k} {n}" for k, n in kinds.items())
          + f"), {len(todo)} to run (ONLY {only!r}); root {Path(root).resolve()}")
    for e in ents:
        mark = "*" if e in todo else " "
        print(f"{mark} {e.kind:<11} {e.name:<28} {e.module or e.script or '-':<32} {' '.join(e.outputs)}")
    print(f"[rebuild] coverage: {cov['n_present']} file(s) in {', '.join(COVERAGE_DIRS)}; {len(cov['unlisted'])} "
          f"without an entry, {len(cov['missing'])} listed file(s) missing")
    for p in cov["unlisted"]:
        print(f"  without an entry: {p}")
    for p in cov["missing"]:
        print(f"  missing: {p}")
    for n in cov.get("pending") or []:                   # C58
        print(f"  pending (MS7 run outputs missing): {n}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m figs.rebuild", description=__doc__.split("\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="outputs to the work folder, compared byte for byte")
    ap.add_argument("--only", default=None, metavar="REGEX", help="only the entries whose name or module matches")
    ap.add_argument("--dry-run", action="store_true", help="print the list and the coverage, run nothing")
    ap.add_argument("--keep", action="store_true", help="keep the rebuilt files in the work folder")
    ap.add_argument("--root", type=Path, default=REPO, help="a folder with the repository's layout (default: this "
                                                             "repository)")
    ap.add_argument("--work", type=Path, default=None, help="the work folder, new or empty (default: under TMPDIR)")
    a = ap.parse_args(argv)
    if a.only is not None:
        try:
            re.compile(a.only)
        except re.error as err:
            ap.error(f"--only: {err}")
    if not a.root.is_dir():
        ap.error(f"--root {a.root} is not a folder")
    if a.work is not None and a.work.exists() and (not a.work.is_dir() or any(a.work.iterdir())):
        ap.error(f"--work {a.work} is not a new or empty folder")
    if a.dry_run:
        return dry_run(a.root, a.only)
    code, _, _ = rebuild(a.root, a.work, check=a.check, only=a.only, keep=a.keep)
    return code


if __name__ == "__main__":
    sys.exit(main())
