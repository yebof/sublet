"""The MS5b claims report (design/sublet_v2.md §11, W11 and W15 item 2; unit U40).

Reads the confirmation's outputs under an input root (code/sim/out/sublet_v2/<part>/summary.json, manifest.json and
jobs/ of the six parts, analysis.json, the copy record code/sim/out/ms3_copy_sublet_v2.json), the pre-registration
design/sublet_v2_prereg.md, the note design/sublet_v2.md, design/Sublet_design.md, the MS5b figure and float extracts
code/sim/out/figs/<name>.json, the supplementary tables paper/supplement/tables/, the float heights
code/sim/out/figs/floats_heights_ms5b.json and the rebuild record code/sim/out/figs/rebuild.json, and writes
code/sim/out/ms5b_claims.md and ms5b_claims.json on the MS5 pattern (ms5_claims, whose helpers and those of
ms4_claims and ms3_claims it imports unchanged), with the MS3 verdict vocabulary: one row per check of W11, in its
order, then the small glyphs of the MS5b figures, the copy record, the job records of the six parts against their job
lists, the rebuild record and the caption drafts of the MS5b figures and Table III v2.

  python -m sublet.experiments.ms5b_claims [--root DIR] [--out-dir DIR] [--no-figures] [--only NAME ...]
                                           [--extracts DIR]

  --root DIR      the input root, a folder with the repository's layout (code/sim/out/sublet_v2/main/summary.json,
                  design/sublet_v2_prereg.md, ...): default SUBLET_FIGS_IN_ROOT (the variable of figs.inputs), else
                  the repository; the run files runs/ are not versioned, so the F rows need a root that holds them
                  (the checkout the confirmation was copied into); the tests pass copies of the MS5b fixture tree
                  tests/fixtures_figs_ms5b/inputs/
  --out-dir DIR   where ms5b_claims.md and ms5b_claims.json go: default the repository's code/sim/out when the root
                  is the repository; required with any other root
  --no-figures    skip the figure reruns (the 'figures' block says so)
  --only NAME     rerun only these figures (names of figs.rebuild.MS5B_SCRIPTS: fig4v2, sf_e3_v2, ...)
  --extracts DIR  the folder of the figure extracts <name>.json for the figure reruns and the caption drafts
                  (default <root>/code/sim/out/figs); the rows always read <root>/code/sim/out/figs

Run from code/sim in the 3 GB scope. Exit 0 once the report is written, whatever its verdicts.

Rows (W11, in its order; every row computed here, since the confirmation's summaries hold no checks block):
  G-1   each part's gate record (summary meta.confirmation_gate, e7h.gate): ok; the pre-registration at HEAD; one
        HEAD over the parts (the freeze commit at which the confirmation ran); the pre-registration's sha256 then
        equal to that of design/sublet_v2_prereg.md under the root now; the analysis script's sha256 on disk and at
        HEAD then equal to the one the pre-registration records now ('analysis_sha256: <hex>') and to the sha256 of
        experiments/ms5b_analysis.py now (the module this report runs, and the root's copy where the root holds
        one); no dirty path; the pilot anchor an ancestor with §5 and §6 unchanged since it; and, where the root is
        the top of a git work tree whose history holds the freeze commit (the repository), the pre-registration and
        the analysis script at that commit (git show, read-only) with those sha256 (freeze_in_git; null on a tree
        without git, a note where the history lacks the commit)
  G-2   every part's meta.reduced false, and one commit: every summary's and manifest's meta.git_revision the same
  G-3   the copy record (ms5b_common.check_copy): pass with every check true, exp sublet_v2, the six parts, the
        clone's commit that of G-2; the copy unchanged since: the digest of the six part folders without runs/
        (ms3_common's tree digest) equal to tree_sha256_versioned, and, where every part holds its runs/, the digest
        of all their files equal to tree_sha256 (analysis.json and analysis.md, written after the copy check, are
        not in either)
  G-4   per part: meta.jobs equal to meta.jobs_ok and to the job list's length, meta.jobs_not_ok empty, no missing
        run (meta.n_missing 0, `missing` empty), and every listed job with an 'ok' record (jobs_block; Q39's rule:
        an e3 MILP job stopped at the wall-clock limit or by the cap leaves the LP as its LB and is not blocking)
  G-5   every run of every part has status ok and no invariant failure, and the parts hold meta.n_runs runs
  A-1   (reproduction) ms5b_analysis.analyse(ms5b_analysis.load(<root>/code/sim)) recomputed here equals
        analysis.json on every key but meta (after the JSON round trip of ms3_common's writer); analysis.json's
        meta.sha256 equals the pre-registration's analysis_sha256 and the sha256 of the module run, its
        pilot_dry_run is false and its git_revision is the summaries' commit
  A-2   analysis.json's config equals ms5b_analysis.CONFIG and the values the pre-registration registers (§5:
        "CONFIG `H5_status` 'primary'", ...)
  H1, H2, H2b, H3, H4, H5, H6   (kind 'hypothesis') from analysis.json's `pass`: holds if true; if false, explained
        only when every consequence row of the hypothesis holds (CONSEQUENCES: H2b's "reported as measured" and its
        wording rule, C-H2b and R-18; H5's "the sharing claim leaves the main text and E3 is reported as measured",
        C-H5 and R-16; H6's "reported as measured", R-18), with a text that gives the measured failure and quotes
        the registered consequence from the *Consequences.* paragraph of design/sublet_v2.md §6 (for H2b also the
        wording rule of its registered statement, "The paper says ..."), else bug (also
        while a consequence row is only missing; a hypothesis without a consequence row here, H1-H4, which held at
        the confirmation, is then a bug); null is missing (H6 with no threshold: informative). The claim is the
        statement as registered (the pre-registration's §5 "As registered" table, copied); H3 carries the status
        labels of Theorem W and Proposition P, copied.
  C-H5  (consequence of H5) no main-text figure or float extract that W6 puts in the paper carries E3 data:
        code/sim/out/figs/fig4v2.json and table3_v2.json (required) and the other main-text figures of style.FIGURES
        but the replaced fig4 (the frozen Figs. 1-3 and 5-7, where present) hold no string with
        code/sim/out/sublet_v2/e3/ or code/sim/out/e3/ anywhere, their sources included, and no key H5, e3 or E3
        (analysis.json's H5 entry, an E3 block); and
        design/Sublet_design.md §2.7 has the sharing item (a bullet with "sharing claim", "E3", "main text" and "any
        policy"); informative while H5 holds (the checks then only reported)
  C-H2b (consequence of H2b) the caption draft of fig4v2 (data.labels.caption, else data.caption) states H2b's
        count ("<k> of <n>", "<k>/<n>"; k the weeks in which a policy of H2b's set has W0 at or below Sublet's, or the
        weeks below it; since C51, design/ms6_spec.md §7.2, Table III v2's note leaves the count to Section VII's
        "Pre-registered outcomes", so table3_v2's draft need not state it), and both drafts, fig4v2's and table3_v2's,
        name H1's set: by the phrase "H1's set" (Fig. 4's caption refers to the
        set by name and its panel (a) labels the policies, W1) or by naming every policy of the set (its tag as a
        whole token, or its registry label where no longer registry label starts: names_policy; LaTeX wrappers
        such as \\mbox and braces ignored: plain_caption); no caption of any extract in code/sim/out/figs/ says
        "every baseline"; informative while H2b holds (the checks then only reported)
  R-1 ... R-18   one per item that §6 reports with no threshold or as measured, each mapped to its supplementary
        table (R_ITEMS): holds when paper/supplement/tables/<file> exists and the extract of the script that
        writes it, code/sim/out/figs/<figure>.json, has data.tables.<file>.scope (the key the file name or its
        stem; a mapping) covering the scope derived here from the summaries and analysis.json; else missing
        (naming what is not covered). Required dimensions: tags, modes, cells (the summaries' cell ids: '301',
        'gap:c301', 'short:c301', 'I2:c3', 'b8:c301', 'F1_m2_r4:F-ad', ...), seeds, and parts, families and
        hypotheses where the item is about them. Coverage (uncovered): every required value is listed, compared as
        strings, under one of the dimension's scope keys (DIM_KEYS: modes also under 'levels'; cells also under
        any key whose name contains cell, week, day, instance or alignment, as the U39 scripts name them), a config
        seed in either spelling ('c301', '301'); a composite cell is also covered when each ':' part is listed
        under any key ('b8' also as 8 under 'b'); a mapping entry counts with its keys and values, a scalar entry
        (n_runs, u) as itself. R-15 (H4's pairs "by family and lender", W4) requires families and modes. R-4
        also needs the table's data file e7v2_rc_runs.csv (each run's RC, fallback and stranding totals, the
        print check's reading of prereg l.235): missing when it is absent or its extract records no entry
        tables.e7v2_rc_runs, a bug when its sha256 or its number of data rows differs from that entry.
  D-1   paper/supplement/tables/ms5b_deviations.tex lists exactly the items that the pre-registration's §7 names
        as deviations reported in the paper (B1, B2, B3, B5, B12, B13 and C2, parsed from its sentence "Under the
        note's §6, ...") with their texts: a row of a tabular (first cell the item, e.g. 'B1' or 'B.1') or a
        \\item[B1] of a list; its text (the other cells) equal to the item's text in §7 word for word after the
        markup is removed (LaTeX commands, braces, math shift, markdown emphasis and code marks; words compared
        case-insensitively), the item's italic title and its closing 'Recorded: ...' sentence each optional
  F-1 ... F-9   (reproduction) each MS5b figure of figs.rebuild.MS5B_SCRIPTS and Table III v2 (TABLE3_V2): its
        script's build(Inputs()) on the root, after the JSON round trip of figs.common.cli, equals the versioned
        extract's data (a built 'sources' key, which Table III's extract keeps outside data, compared with the
        extract's sources), its recorded sources equal the extract's, every runs/ file among those sources is
        listed in the extract with a sha256 (W10: a {path: sha256} mapping, or objects with path or file and
        sha256, anywhere in the extract), and every listed file has that sha256 under the root now; missing when
        the script, the extract or a runs/ file under the root is absent
  FL-1  (informative) the measured heights of Table III v2, Table II v2 and Algorithm 1 v2 from
        code/sim/out/figs/floats_heights_ms5b.json against their budgets (floats_heights.py --ms5b, C43), each
        record's sha256 equal to that of its float now (a stale record is a bug)
  RB-1  the record of the MS5b exit rebuild (W15 item 5): ms5_claims' RB-1 conditions (status pass, CHECK=1, the
        full list, a clean clone, coverage, every output identical, hand-set files unchanged, the record current)
        and the MS5b ones: the heights 'ms5b' equal, every hand-set file of figs.rebuild.HAND_SET checked, and the
        record's entries today's figs.rebuild.entries(); a record without the 'ms5b' heights (an earlier
        milestone's exit run) is missing
Verdicts (MS3 vocabulary): reproduced (A-1, F rows), holds, informative (FL-1; a consequence row whose hypothesis
held), explained (H rows only, by the rule above, with text), bug, missing, pending. Every row that reads the
summaries or analysis.json (G, A, H, C and R rows) is a bug when a summary has meta.reduced true, and an F row or a
C row when an extract it reads has data.meta.reduced true (a smoke run, never a result); a malformed input makes its
row a bug.

Criterion (W11): it holds iff no row is a bug and every row other than reproduced, holds and informative is
explained with its text (ms3_claims.criterion); a missing row keeps it from holding. The blocks below do not enter
it: tests/test_ms5b_out.py fails on a blocking job.

Blocks: figures (ms4_claims.figures_block on the eight MS5b figure scripts, rerun with --from-extract into a
temporary folder; Table III v2 is a float and not rerun), copy_checks (ms5_claims.copy_block on sublet_v2), jobs
(jobs_block: the six part folders), rebuild (ms5_claims.rebuild_block), captions (the drafts of the MS5b figures and
Table III v2 from their extracts, a reduced one noted).

Output schema of ms5b_claims.json (key paths; the .md shows the same content as tables):
  meta.module, meta.spec, meta.git_revision, meta.written, meta.input_root, meta.input_root_is_repository,
  meta.out_dir, meta.inputs.<repository-relative name>   'ok' | 'missing' | 'invalid JSON: ...' (files read)
  criterion.*   as ms3_claims.criterion
  rows[]   one per check, in the order of SPECS: id, group ('G', 'A', 'H', 'C', 'R', 'D', 'F', 'FL', 'RB'),
           section, kind ('reproduction' | 'property' | 'hypothesis' | 'consequence' | 'informative'), claim.spec,
           claim.summary (H rows: the registered statement), status_label, status_label_note, reference.value,
           reference.values, reference.file, regenerated.value {path: value}, regenerated.file, summary_status
           (the row's computed status), verdict, explanation (H rows that are explained), note
  figures.*, copy_checks.*, rebuild.*   as ms5_claims'
  jobs.rows.<part> for the six parts: manifest, present, n_listed, by_status, n_blocking, blocking, n_milp_lp_fallback,
           milp_lp_fallback, n_unlisted_records, n_unreadable_records; jobs.n_blocking, jobs.note
  captions.<name> for the eight figures and table3_v2: text, n_chars, reduced, source, notes
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Optional

from .. import paths
from . import ms3_claims as m3
from . import ms3_common as mc
from . import ms4_claims as m4c
from . import ms5_claims as c5
from . import ms5b_analysis as ma
from . import ms5b_common as m5

SPEC_DOC = "design/sublet_v2.md"
OUT_MD, OUT_JSON = "ms5b_claims.md", "ms5b_claims.json"
ENV_IN_ROOT = m3.ENV_IN_ROOT

OUT = "code/sim/out"
CONF = f"{OUT}/{m5.CONF_DIR}"                       # code/sim/out/sublet_v2
PARTS = m5.CONF_PARTS                               # main, seeds, second, e3, fam, grid
SUMS = {p: f"{CONF}/{p}/summary.json" for p in PARTS}
MANIFESTS = {p: f"{CONF}/{p}/manifest.json" for p in PARTS}
ANALYSIS_JSON = f"{CONF}/analysis.json"
COPY_REC = f"{OUT}/{m5.COPY_RECORD}"
PREREG, NOTE, DESIGN = m5.PREREG, m5.SPEC, "design/Sublet_design.md"
FIGS = f"{OUT}/figs"
REBUILD = c5.REBUILD
FLOATS_MS5B = f"{FIGS}/floats_heights_ms5b.json"
FLOAT_NAMES_MS5B = {"table3_v2": "Table III v2", "table2_policies_v2": "Table II v2",
                    "alg1_guard_v2": "Algorithm 1 v2"}           # W2, W5; floats_heights.py BUDGETS_MS5B (C43)
FLOATS_DIR, TABLES_DIR = "paper/floats", "paper/supplement/tables"
DEVIATIONS = f"{TABLES_DIR}/ms5b_deviations.tex"
HYPOTHESES = ("H1", "H2", "H2b", "H3", "H4", "H5", "H6")
VERDICTS, OK_VERDICTS = m3.VERDICTS, m3.OK_VERDICTS
E3_PATHS = (f"{CONF}/e3/", f"{OUT}/e3/")            # C-H5: a string naming one of these is E3 data
E3_KEYS = {"H5", "e3", "E3"}                        # C-H5: a key carrying analysis.json's H5 or an E3 block
EVERY_BASELINE = "every baseline"                   # C-H2b: H2b's registered wording (§6)
HEX64 = re.compile(r"[0-9a-f]{64}")
DIFFS_MAX = 10

# H1's set by tag with the MS5b registry key of each (style C41's notes; BL5 is the lagged build, bl5_lag)
H1_KEYS = {"BL1": "bl1", "BL1-BO": "bl1_bo", "BL2": "bl2", "BL3-0": "bl3_0", "BL4": "bl4", "BL5": "bl5_lag",
           "BL5-cur": "bl5_cur"}
# Table III v2's rows that are tags of part main (W2; BL0a is no tag)
TABLE3_V2_TAGS = ("Sublet", "Sublet-1way", "BL1-GP", "BL1N", "BL5N", "BL1", "BL1-BO", "BL5-cur", "BL5-tau60", "BL2",
                  "BL3-0", "BL4", "A6")
BOUNDARY_MODES = m5.SECOND_MODES + (m5.B999_MODE,)  # L-vr, L-rf, L-ad and the p99.9 buffer (§4.4(b))
FAM_REPORTED_MODES = ("F-ad", "F-eg")               # §6: the Q6 family runs under F-ad and F-eg

# status labels copied from design/sublet_v2.md §2.6 and the pre-registration's §7 C1 (never upgraded)
W_AB = m3.W_AB      # "Theorem W(a)(b) (PROVEN for the engine as implemented under C1-C3, audited); W(c) (CONJECTURE)"
PROP_P = ("Proposition P (a)-(c) and its Consequence PROVEN, audited, for its instance class, and (d) under its three "
          "float hypotheses")

_RB = m3._figs_import("figs.rebuild")               # stdlib only at import (figs/rebuild.py)
# F rows: (name, repository-relative script, module) of each MS5b figure (C42's MS5B_SCRIPTS, in its order), then
# Table III v2 (C42's TABLE3_V2)
F_ENTRIES = tuple((name, script, ".".join(Path(script).relative_to("code/sim").with_suffix("").parts))
                  for name, script in _RB.MS5B_SCRIPTS.items()) + \
    ((_RB.TABLE3_V2[0], _RB.TABLE3_V2[1], _RB.TABLE3_V2[2]),)
UNITS = {"fig4v2": "U37", "table3_v2": "U38", "ms5b_deviations.tex": "U38"}     # the others: U39


# ---------------------------------------------------------------- inputs
class _Inputs(m3._Inputs):
    """ms3_claims' inputs (each JSON file read once) with text files and the rows computed so far (an H row reads
    its consequence rows, which W11 lists after it)."""

    def __init__(self, root: Path):
        super().__init__(root)
        self.rows: dict = {}
        self._texts: dict = {}
        self.cache: dict = {}

    def text(self, rel: str) -> tuple[Optional[str], Optional[str]]:
        """(text, None), or (None, 'missing' | 'unreadable: ...')."""
        if rel not in self._texts:
            p = self.root / rel
            if not p.is_file():
                self._texts[rel] = (None, "missing")
            else:
                try:
                    self._texts[rel] = (p.read_text(encoding="utf-8"), None)
                except (OSError, UnicodeDecodeError) as err:
                    self._texts[rel] = (None, f"unreadable: {err}"[:200])
            self.status[rel] = self._texts[rel][1] or "ok"
        return self._texts[rel]

    def row(self, cid: str) -> dict:
        """The row of check `cid`, computed once."""
        if cid not in self.rows:
            self.rows[cid] = _row_or_bug(SPEC_BY_ID[cid], self)
        return self.rows[cid]


def _d(x) -> dict:
    return x if isinstance(x, dict) else {}


def _l(x) -> list:
    return x if isinstance(x, list) else []


def _sha256(p: Path) -> Optional[str]:
    return c5._sha256(p)


def _parts(inp) -> tuple[dict, list]:
    """({part: summary} of the parts present, [problems]): 'missing' or the JSON problem per absent part."""
    got, probs = {}, []
    for p in PARTS:
        S, prob = inp.load(SUMS[p])
        if S is None:
            probs.append(f"{SUMS[p]} {prob}")
        else:
            got[p] = S
    return got, probs


def _reduced(inp) -> list:
    """The part summaries with meta.reduced true (a smoke run: every row reading them is a bug)."""
    got, _ = _parts(inp)
    return [SUMS[p] for p, S in got.items() if m3._reduced(S)]


def _absent_any(probs: list) -> dict:
    """The entry of a row whose inputs are absent (missing) or not JSON objects (bug)."""
    bad = [x for x in probs if not x.endswith(" missing")]
    return {"status": "bug_input" if bad else "missing", "_note": "; ".join(probs)}


def _commit(got: dict) -> Optional[str]:
    """The one meta.git_revision of the part summaries, None if they record several or none."""
    revs = {_d(S.get("meta")).get("git_revision") for S in got.values()}
    return next(iter(revs)) if len(revs) == 1 and isinstance(next(iter(revs)), str) else None


# ---------------------------------------------------------------- G rows
def freeze_in_git(root: Path, head) -> Optional[dict]:
    """{'prereg_sha256', 'analysis_sha256'} of design/sublet_v2_prereg.md and experiments/ms5b_analysis.py at the
    commit `head` in the root's own git history (read-only: rev-parse, cat-file, show), a value None where the file is
    not at that commit; {'commit_absent': True} when the history lacks the commit; None when the root is not the top
    of a git work tree (a test or fixture tree) or git fails."""
    if not isinstance(head, str) or not re.fullmatch(r"[0-9a-f]{40}", head):
        return None

    def git(*args) -> Optional[subprocess.CompletedProcess]:
        try:
            return subprocess.run(["git", "-C", str(root), *args], capture_output=True, timeout=60)
        except (OSError, subprocess.SubprocessError):
            return None
    top = git("rev-parse", "--show-toplevel")
    if top is None or top.returncode != 0 or \
            Path(top.stdout.decode("utf-8", "replace").strip()).resolve() != Path(root).resolve():
        return None
    has = git("cat-file", "-e", f"{head}^{{commit}}")
    if has is None:
        return None
    if has.returncode != 0:
        return {"commit_absent": True}
    out = {}
    for key, rel in (("prereg_sha256", PREREG), ("analysis_sha256", m5.ANALYSIS_REL)):
        blob = git("show", f"{head}:{rel}")
        out[key] = hashlib.sha256(blob.stdout).hexdigest() if blob is not None and blob.returncode == 0 else None
    return out


def _g1(inp) -> dict:
    got, probs = _parts(inp)
    pre, pprob = inp.text(PREREG)
    if probs or pre is None:
        return _absent_any(probs + ([] if pre is not None else [f"{PREREG} {pprob}"]))
    pre_sha = hashlib.sha256(pre.encode("utf-8")).hexdigest()
    line = m5.prereg_sha256_recorded(pre)
    module_sha = m5.analysis_sha256()
    root_copy = inp.root / m5.ANALYSIS_REL
    root_sha = _sha256(root_copy) if root_copy.is_file() else None
    fails, heads = [], {}
    if line is None:
        fails.append(f"{PREREG} records no line 'analysis_sha256: <64 hex>'")
    if module_sha != line:
        fails.append(f"experiments/ms5b_analysis.py (this module's) sha256 {str(module_sha)[:12]} is not the "
                     f"pre-registration's {str(line)[:12]}")
    if root_sha is not None and root_sha != line:
        fails.append(f"{m5.ANALYSIS_REL} under the root has sha256 {root_sha[:12]}, not the pre-registration's")
    for p, S in got.items():
        g = _d(_d(S.get("meta")).get("confirmation_gate"))
        rec = _d(g.get("record"))
        heads[p] = rec.get("head")
        why = []
        if g.get("ok") is not True:
            why.append(f"gate ok {g.get('ok')!r} ({g.get('reason')})")
        if rec.get("prereg_at_head") is not True:
            why.append("the pre-registration was not at HEAD")
        if rec.get("prereg_sha256") != pre_sha:
            why.append(f"the pre-registration's sha256 then {str(rec.get('prereg_sha256'))[:12]} is not its sha256 "
                       f"now {pre_sha[:12]}")
        for k in ("analysis_sha256_prereg", "analysis_sha256_head", "analysis_sha256_disk"):
            if rec.get(k) != line:
                why.append(f"{k} {str(rec.get(k))[:12]} is not the pre-registration's {str(line)[:12]}")
        if rec.get("dirty_paths") != []:
            why.append(f"dirty paths {rec.get('dirty_paths')!r}"[:200])
        pil = _d(rec.get("pilot"))
        if pil.get("anchor_is_ancestor") is not True or pil.get("sections_changed_since_anchor") != []:
            why.append(f"pilot anchor ancestor {pil.get('anchor_is_ancestor')!r}, sections changed since it "
                       f"{pil.get('sections_changed_since_anchor')!r}")
        if why:
            fails.append(f"{p}: " + "; ".join(why))
    hs = sorted({h for h in heads.values() if isinstance(h, str)})
    if len(hs) != 1 or any(not isinstance(h, str) for h in heads.values()):
        fails.append(f"the parts' gate records name the heads {heads}")
    notes, git_ok = [], None
    git = freeze_in_git(inp.root, hs[0]) if len(hs) == 1 else None
    if git is not None and git.get("commit_absent"):
        notes.append(f"the root's git history lacks the freeze commit {hs[0][:12]}: not verified in git")
    elif git is not None:
        git_ok = git["prereg_sha256"] == pre_sha and git["analysis_sha256"] == line
        if git["prereg_sha256"] != pre_sha:
            fails.append(f"{PREREG} at the freeze commit {hs[0][:12]} (git) has sha256 "
                         f"{str(git['prereg_sha256'])[:12]}, not that of the file now {pre_sha[:12]}")
        if git["analysis_sha256"] != line:
            fails.append(f"{m5.ANALYSIS_REL} at the freeze commit (git) has sha256 {str(git['analysis_sha256'])[:12]}, "
                         f"not the pre-registration's {str(line)[:12]}")
    return {"status": "fail" if fails else "pass", "freeze_commit": hs[0] if len(hs) == 1 else None,
            "prereg_sha256": pre_sha, "analysis_sha256_prereg": line, "analysis_sha256_module": module_sha,
            "analysis_sha256_root": root_sha, "freeze_in_git": git_ok,
            "n_parts": len(got), "failures": fails[:20],
            "_note": "; ".join(fails[:6] + notes) or None, "_reduced": bool(_reduced(inp))}


def _g2(inp) -> dict:
    got, probs = _parts(inp)
    if probs:
        return _absent_any(probs)
    fails = []
    red = {p: _d(S.get("meta")).get("reduced") for p, S in got.items()}
    not_false = {p: v for p, v in red.items() if v is not False}
    if not_false:
        fails.append(f"meta.reduced not false in {not_false}")
    revs = {p: _d(S.get("meta")).get("git_revision") for p, S in got.items()}
    for p in got:
        M, prob = inp.load(MANIFESTS[p])
        revs[f"{p}/manifest"] = _d(_d(M).get("meta")).get("git_revision") if M is not None else f"<{prob}>"
    commits = sorted({str(v) for v in revs.values()})
    if len(commits) != 1 or not re.fullmatch(r"[0-9a-f]{40}", commits[0]):
        fails.append(f"git revisions {revs}")
    return {"status": "fail" if fails else "pass", "reduced": red, "commits": commits, "n_files": len(revs),
            "_note": "; ".join(fails) or None, "_reduced": bool(_reduced(inp))}


def _digests(top: Path) -> tuple[Optional[str], Optional[str], bool]:
    """(versioned digest, full digest, every part holds runs/) of the six part folders of the copy (as
    ms5b_common.check_copy records tree_sha256_versioned and tree_sha256)."""
    tree = {p: f for p, f in mc._tree(top).items() if p.split("/", 1)[0] in PARTS} if top.is_dir() else {}
    if not tree:
        return None, None, False
    dig = {p: mc._digest(f) for p, f in tree.items()}
    ver = mc._tree_digest({p: d for p, d in dig.items() if "/runs/" not in f"/{p}"})
    runs = all((top / p / "runs").is_dir() for p in PARTS)
    return ver, mc._tree_digest(dig), runs


def _g3(inp) -> dict:
    rec, prob = inp.load(COPY_REC)
    if rec is None:
        return m3._absent(COPY_REC, prob)
    got, _ = _parts(inp)
    commit = _commit(got)
    fails = []
    failed = [k for k, v in _d(rec.get("checks")).items() if v is not True]
    if rec.get("pass") is not True or failed or not _d(rec.get("checks")):
        fails.append(f"pass {rec.get('pass')!r}, failed checks {failed}")
    if rec.get("exp") != m5.CONF_DIR or rec.get("check") != "copy":
        fails.append(f"exp {rec.get('exp')!r}, check {rec.get('check')!r}")
    if rec.get("parts") != list(PARTS):
        fails.append(f"parts {rec.get('parts')!r}, not {list(PARTS)}")
    if rec.get("clone_commit") != commit:
        fails.append(f"clone commit {rec.get('clone_commit')!r}, the summaries' {commit!r}")
    ver, full, runs = _digests(inp.root / CONF)
    if ver != rec.get("tree_sha256_versioned"):
        fails.append("the copy's versioned files changed since the copy check (tree_sha256_versioned)")
    if runs and full != rec.get("tree_sha256"):
        fails.append("the copy's files changed since the copy check (tree_sha256, runs/ included)")
    return {"status": "fail" if fails else "pass", "pass": rec.get("pass"), "failed": failed,
            "clone_commit": rec.get("clone_commit"), "n_files_copy": rec.get("n_files_copy"),
            "versioned_current": ver == rec.get("tree_sha256_versioned"),
            "full_current": (full == rec.get("tree_sha256")) if runs else None, "time": rec.get("time"),
            "_note": "; ".join(fails) or (None if runs else "runs/ absent under the root: only the versioned digest "
                                                            "compared"),
            "_reduced": bool(_reduced(inp))}


def _g4(inp) -> dict:
    got, probs = _parts(inp)
    if probs:
        return _absent_any(probs)
    jb = _jobs(inp)
    fails, per = [], {}
    for p, S in got.items():
        m = _d(S.get("meta"))
        r = jb["rows"][p]
        e = {"jobs": m.get("jobs"), "jobs_ok": m.get("jobs_ok"), "jobs_not_ok": m.get("jobs_not_ok"),
             "n_missing": m.get("n_missing"), "missing": len(_l(S.get("missing"))) if "missing" in S else None,
             "n_listed": r.get("n_listed"), "n_blocking": r.get("n_blocking"),
             "n_milp_lp_fallback": r.get("n_milp_lp_fallback")}
        per[p] = e
        why = []
        if not isinstance(e["jobs"], int) or e["jobs"] != e["jobs_ok"] or e["jobs"] != e["n_listed"]:
            why.append(f"jobs {e['jobs']!r}, jobs_ok {e['jobs_ok']!r}, listed {e['n_listed']!r}")
        if e["jobs_not_ok"]:
            why.append(f"jobs_not_ok {e['jobs_not_ok']!r}"[:200])
        if e["n_missing"] != 0 or e["missing"] != 0:
            why.append(f"missing runs: n_missing {e['n_missing']!r}, missing {e['missing']!r}")
        if not r.get("present"):
            why.append(r.get("note") or "no job list")
        elif r.get("n_blocking") or r.get("n_unreadable_records"):
            why.append(f"{r.get('n_blocking')} listed job(s) without an 'ok' record, "
                       f"{r.get('n_unreadable_records')} unreadable record(s)")
        if why:
            fails.append(f"{p}: " + "; ".join(why))
    return {"status": "fail" if fails else "pass", "parts": per, "n_blocking": jb["n_blocking"],
            "n_milp_lp_fallback": sum(r.get("n_milp_lp_fallback") or 0 for r in jb["rows"].values()),
            "_note": "; ".join(fails) or None, "_reduced": bool(_reduced(inp))}


def _g5(inp) -> dict:
    got, probs = _parts(inp)
    if probs:
        return _absent_any(probs)
    fails, n, bad_status, bad_inv = [], 0, [], []
    for p, S in got.items():
        runs = _l(S.get("runs"))
        n += len(runs)
        want = _d(S.get("meta")).get("n_runs")
        if want != len(runs):
            fails.append(f"{p}: {len(runs)} runs, meta.n_runs {want!r}")
        for r in runs:
            r = _d(r)
            if r.get("status") != "ok":
                bad_status.append(f"{p}:{r.get('job')}:{r.get('mode')}:{r.get('seed')} {r.get('status')!r}")
            if r.get("n_invariant_failures") != 0:
                bad_inv.append(f"{p}:{r.get('job')}:{r.get('mode')}:{r.get('seed')} {r.get('n_invariant_failures')!r}")
    if bad_status:
        fails.append(f"{len(bad_status)} run(s) not ok ({bad_status[:3]})")
    if bad_inv:
        fails.append(f"{len(bad_inv)} run(s) with invariant failures or none recorded ({bad_inv[:3]})")
    return {"status": "fail" if fails else "pass", "n_runs": n, "n_not_ok": len(bad_status),
            "n_invariant_failures": len(bad_inv), "_note": "; ".join(fails) or None,
            "_reduced": bool(_reduced(inp))}


# ---------------------------------------------------------------- A rows
def _diff(a: Any, b: Any, where: str = "$", out: Optional[list] = None) -> list:
    """The paths at which two JSON values differ (at most DIFFS_MAX + 1)."""
    out = [] if out is None else out
    if len(out) > DIFFS_MAX:
        return out
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b), key=str):
            if k not in a or k not in b:
                out.append(f"{where}.{k} ({'only recomputed' if k in a else 'only in analysis.json'})")
            else:
                _diff(a[k], b[k], f"{where}.{k}", out)
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            out.append(f"{where} (length {len(a)} recomputed, {len(b)} in analysis.json)")
        else:
            for i, (x, y) in enumerate(zip(a, b)):
                _diff(x, y, f"{where}[{i}]", out)
    elif a != b or type(a) is not type(b) and not (m3._num(a) and m3._num(b)):
        out.append(f"{where} ({a!r} recomputed, {b!r} in analysis.json)"[:200])
    return out


def recompute_analysis(root: Path) -> dict:
    """analyse(load(<root>/code/sim)) as analysis.json holds it without meta (ms3_common's JSON writer)."""
    res = ma.analyse(ma.load(Path(root) / "code" / "sim"))
    return json.loads(mc._json_text(res, False))


def _a1(inp) -> dict:
    A, prob = inp.load(ANALYSIS_JSON)
    if A is None:
        return m3._absent(ANALYSIS_JSON, prob)
    got, probs = _parts(inp)
    pre, pprob = inp.text(PREREG)
    if probs or pre is None:
        return _absent_any(probs + ([] if pre is not None else [f"{PREREG} {pprob}"]))
    if "a1" not in inp.cache:
        inp.cache["a1"] = recompute_analysis(inp.root)
    new = inp.cache["a1"]
    old = {k: v for k, v in A.items() if k != "meta"}
    diffs = _diff(new, old)
    meta = _d(A.get("meta"))
    line, module_sha = m5.prereg_sha256_recorded(pre), m5.analysis_sha256()
    fails = []
    if diffs:
        fails.append(f"{len(diffs) if len(diffs) <= DIFFS_MAX else f'more than {DIFFS_MAX}'} difference(s): "
                     + "; ".join(diffs[:5]))
    if not (meta.get("sha256") == line == module_sha) or line is None:
        fails.append(f"analysis.json meta.sha256 {str(meta.get('sha256'))[:12]}, the pre-registration's "
                     f"{str(line)[:12]}, the module's {str(module_sha)[:12]}")
    if meta.get("pilot_dry_run") is not False:
        fails.append(f"meta.pilot_dry_run {meta.get('pilot_dry_run')!r}")
    if meta.get("git_revision") != _commit(got):
        fails.append(f"meta.git_revision {meta.get('git_revision')!r}, the summaries' {_commit(got)!r}")
    return {"status": "fail" if fails else "pass", "equal": not diffs, "n_differences": len(diffs),
            "differences": diffs[:DIFFS_MAX], "sha256": meta.get("sha256"), "analysis_sha256_prereg": line,
            "analysis_sha256_module": module_sha, "pilot_dry_run": meta.get("pilot_dry_run"),
            "git_revision": meta.get("git_revision"), "parts_found": new.get("parts_found"),
            "_note": "; ".join(fails) or None, "_reduced": bool(_reduced(inp))}


CONFIG_RE = re.compile(r"CONFIG `(\w+)` (?:'([^']*)'|([-+0-9.eE]+|None))")


def registered_config(prereg: str) -> dict:
    """The CONFIG values that the pre-registration registers ("CONFIG `H5_status` 'primary'", ...; a number or None
    unquoted)."""
    out = {}
    for m in CONFIG_RE.finditer(prereg):
        k, s, v = m.group(1), m.group(2), m.group(3)
        if s is not None:
            out[k] = s
        elif v == "None":
            out[k] = None
        else:
            out[k] = float(v) if any(c in v for c in ".eE") else int(v)
    return out


def _a2(inp) -> dict:
    A, prob = inp.load(ANALYSIS_JSON)
    if A is None:
        return m3._absent(ANALYSIS_JSON, prob)
    pre, pprob = inp.text(PREREG)
    if pre is None:
        return {"status": "missing", "_note": f"{PREREG} {pprob}"}
    reg = registered_config(pre)
    cfg = A.get("config")
    fails = []
    if not reg:
        fails.append(f"{PREREG} registers no CONFIG value")
    if cfg != reg:
        fails.append(f"analysis.json config {cfg!r} is not the registered {reg!r}")
    if dict(ma.CONFIG) != reg:
        fails.append(f"ms5b_analysis.CONFIG {ma.CONFIG!r} is not the registered {reg!r}")
    return {"status": "fail" if fails else "pass", "config": cfg, "registered": reg, "module": dict(ma.CONFIG),
            "_note": "; ".join(fails) or None, "_reduced": bool(_reduced(inp))}


# ---------------------------------------------------------------- H rows
# the consequence rows of each hypothesis (W11): explained only when every one holds; H1-H4 have none (they held)
CONSEQUENCES = {"H2b": ("C-H2b", "R-18"), "H5": ("C-H5", "R-16"), "H6": ("R-18",)}
H_FIELDS = {
    "H1": ("wins", "n_weeks", "median_margin.median", "median_margin.ci", "sign_test.p", "median_margin.wilcoxon.p",
           "pass"),
    "H2": ("weeks_below_1", "weeks_below_set", "n_weeks", "median_W0", "pass"),
    "H2b": ("weeks_below_set", "n_weeks", "failing_weeks", "pass"),
    "H3": ("n_runs", "n_not_held", "n_envelope_violations", "n_aborts_s_fb_bound_form", "n_missing_guarded_runs",
           "aborts", "one_way_aborts", "projected_slots", "K0", "pass"),
    "H4": ("n_counted_pairs", "#mismatches", "#missing_pairs", "identity_holds", "sublet_projected_runs", "wording",
           "pass"),
    "H5": ("kind", "b[*].b", "b[*].le_MS4", "b[*].shared_below_siloed", "failing", "pass"),
    "H6": ("n", "median_price", "threshold", "n_loss", "pass"),
}


def registered_statements(prereg: str) -> dict:
    """{H: (kind, statement)} of the pre-registration's §5 "As registered" table."""
    i = prereg.find("*As registered.*")
    out = {}
    if i < 0:
        return out
    for ln in prereg[i:].splitlines()[1:]:
        m = re.match(r"^\| (H\d+b?) \| ([^|]+) \| (.+) \|$", ln)
        if m:
            out[m.group(1)] = (m.group(2).strip(), m.group(3).strip())
        elif out and not ln.startswith("|"):
            break
    return out


def registered_consequences(note: str) -> list:
    """The sentences of the *Consequences.* paragraph of design/sublet_v2.md §6, each with the hypotheses that its
    lead names ('H2b or H6 fails: ...' -> ['H2b', 'H6'])."""
    sec = m5.sections(note, ("6",)).get("6") or ""
    para = next((ln for ln in sec.splitlines() if ln.startswith("*Consequences.*")), "")
    body = para[len("*Consequences.*"):].strip()
    out = []
    for s in re.split(r"(?<=\.)\s+(?=H\d)", body):
        lead = s.split(":", 1)[0]
        out.append((re.findall(r"\bH\d+b?\b", lead), s.strip()))
    return out


def _f4(v) -> str:
    """A ratio with four decimals (as §6's medians are given), or the value as it is."""
    return f"{v:.4f}" if m3._num(v) else repr(v)


def _measured_failure(hid: str, h: dict) -> str:
    """What failed, from analysis.json."""
    if hid in ("H2", "H2b"):
        weeks = [r for r in _l(h.get("weeks")) if not _d(r).get("below_all")]
        bits = []
        for r in weeks:
            s = _d(r).get("Sublet")
            low = {t: v for t, v in _d(_d(r).get("others")).items() if not (m3._num(v) and m3._num(s) and s < v)}
            bits.append(f"week {r.get('week')}: Sublet {_f4(s)}, " + ", ".join(f"{t} {_f4(v)}" for t, v in low.items()))
        return (f"Sublet's W0 below that of every policy of {hid}'s set in {h.get('weeks_below_set')} of "
                f"{h.get('n_weeks')} weeks" + ("; not in " + "; ".join(bits) if bits else
                                               " (16 of 16 registered)"))
    if hid == "H5":
        bits = []
        for r in map(_d, _l(h.get("b"))):
            if r.get("le_MS4") is False:
                bits.append(f"b = {r.get('b')}: Sublet's shared ALG/LB {_f4(r.get('Sublet_shared'))} above "
                            f"Sublet-MS4's {_f4(r.get('Sublet_MS4_shared'))}")
            if r.get("shared_below_siloed") is False:
                bits.append(f"b = {r.get('b')}: Sublet shared {_f4(r.get('Sublet_shared'))} not below siloed "
                            f"{_f4(r.get('Sublet_siloed'))}")
        return ("median over the seeds: " + "; ".join(bits)) if bits else \
            f"pass false with no failing b (b rows {[r.get('b') for r in map(_d, _l(h.get('b')))]})"
    keys = [f for f in H_FIELDS.get(hid, ()) if not f.startswith("#") and "[" not in f]
    return "; ".join(f"{k} {m3._fmt(m4c._none(m4c._get(h, k)))}" for k in keys)


def _h(inp, hid: str) -> dict:
    A, prob = inp.load(ANALYSIS_JSON)
    if A is None:
        return m3._absent(ANALYSIS_JSON, prob)
    pre, _ = inp.text(PREREG)
    reg = registered_statements(pre or "").get(hid)
    h = A.get(hid)
    red = bool(_reduced(inp))
    if not isinstance(h, dict):
        return {"status": "missing", "_note": f"no entry {hid} in {ANALYSIS_JSON}", "_reduced": red}
    e = {**h, "claim": f"{hid} ({reg[0]}): {reg[1]}" if reg else None, "_reduced": red}
    if hid in ("H2", "H2b"):
        e["failing_weeks"] = [r.get("week") for r in map(_d, _l(h.get("weeks"))) if not r.get("below_all")]
    if hid == "H5":
        e["failing"] = [r.get("b") for r in map(_d, _l(h.get("b")))
                        if r.get("le_MS4") is False or r.get("shared_below_siloed") is False]
    if reg is None:
        e["_note"] = f"{PREREG}: no registered statement of {hid} (§5, As registered)"
    passed = h.get("pass")
    if passed is True:
        e["status"] = "pass"
        return e
    if passed is None:
        if hid == "H6" and "threshold" in h and h.get("threshold") is None:
            e.update(status="informative", _note="H6 has no threshold (CONFIG H6_threshold None): reported as measured")
        else:
            e.update(status="missing", _note=f"analysis.json gives {hid} no verdict (pass null): {h.get('note')}")
        return e
    if passed is not False:
        e.update(status="bug_input", _note=f"{hid}.pass is {passed!r}, not a boolean")
        return e
    measured = _measured_failure(hid, h)
    note, nprob = inp.text(NOTE)
    quotes = [s for hs, s in registered_consequences(note or "") if hid in hs]
    cons = CONSEQUENCES.get(hid, ())
    rows = {c: inp.row(c) for c in cons}
    not_holding = {c: r["verdict"] for c, r in rows.items() if r["verdict"] != "holds"}
    why = []
    if not quotes:
        why.append(f"{NOTE} §6 quotes no consequence of {hid}" + (f" ({NOTE} {nprob})" if nprob else ""))
    if not cons:
        why.append(f"no consequence row of this report applies {hid}'s registered consequence (W11 lists "
                   "consequence rows for H2b and H5; H1-H4 held at the confirmation)")
    if not_holding:
        why.append("consequence row(s) not holding: " + ", ".join(f"{c} {v}" for c, v in not_holding.items()))
    e["consequence_rows"] = {c: r["verdict"] for c, r in rows.items()}
    if why:
        e.update(status="fail", _note=f"{hid} fails ({measured}); " + "; ".join(why))
        return e
    # H2b's statement carries its own wording rule ("The paper says ..."), which C-H2b applies with §6's consequence
    rule = re.search(r"The paper says [^.]*\.", reg[1]) if reg and hid == "H2b" else None
    e.update(status="explained",
             explanation=f"{hid} fails as registered: {measured}. Registered consequence ({NOTE} §6): "
                         + " ".join(f'"{q}"' for q in quotes)
                         + (f' Wording rule of the registered statement: "{rule.group(0)}"' if rule else "")
                         + " Applied: " + ", ".join(f"{c} holds" for c in cons) + ".")
    return e


# ---------------------------------------------------------------- C rows
def _extract(inp, name: str) -> tuple[Optional[dict], Optional[str]]:
    return inp.load(f"{FIGS}/{name}.json")


def _caption(payload: Optional[dict]) -> Optional[str]:
    """An extract's caption draft: data.labels.caption, else data.caption."""
    data = _d(_d(payload).get("data"))
    c = _d(data.get("labels")).get("caption")
    if not isinstance(c, str):
        c = data.get("caption")
    return c if isinstance(c, str) else None


def _ext_reduced(payload: Optional[dict]) -> bool:
    return _d(_d(_d(payload).get("data")).get("meta")).get("reduced") is True


def _strings(x) -> list:
    """Every string in a JSON value, keys included."""
    out = []
    if isinstance(x, str):
        out.append(x)
    elif isinstance(x, dict):
        for k, v in x.items():
            out.append(str(k))
            out += _strings(v)
    elif isinstance(x, list):
        for v in x:
            out += _strings(v)
    return out


def _keys(x) -> set:
    """Every key of the mappings in a JSON value."""
    if isinstance(x, dict):
        return {str(k) for k in x} | {k for v in x.values() for k in _keys(v)}
    if isinstance(x, list):
        return {k for v in x for k in _keys(v)}
    return set()


def sharing_item(design: str) -> Optional[str]:
    """The bullet of design/Sublet_design.md §2.7 that bars an empirical sharing claim from E3 in the main text for
    any policy (H5's registered consequence as W3 reads it), or None."""
    m = re.search(r"^### 2\.7 .*?(?=^### |\Z)", design, re.M | re.S)
    if m is None:
        return None
    for ln in m.group(0).splitlines():
        low = ln.lower()
        if ln.lstrip().startswith("-") and all(w in low for w in ("sharing claim", "e3", "main text", "any policy")):
            return ln.strip()
    return None


MAIN_TEXT_V2 = ("fig4v2", "table3_v2")               # W6: the paper's Fig. 4 and Table III
MAIN_TEXT_REPLACED = ("fig4", "table3_e7")          # W6: frozen, replaced by them, not in the paper


def main_text_extracts() -> list:
    """The extracts of the paper's main-text figures and generated float (W6): Fig. 4 v2 and Table III v2, which
    C-H5 requires, then the other main-text figures of style.FIGURES (the frozen Figs. 1-3 and 5-7), checked where
    present."""
    style = m3._figs_import("figs.style")
    return list(MAIN_TEXT_V2) + [k for k, v in style.FIGURES.items()
                                 if v.main and k not in MAIN_TEXT_V2 and k not in MAIN_TEXT_REPLACED]


def _c_h5(inp) -> dict:
    A, prob = inp.load(ANALYSIS_JSON)
    if A is None:
        return m3._absent(ANALYSIS_JSON, prob)
    red = bool(_reduced(inp))
    fails, missing, carries, reduced_ext = [], [], {}, []
    for name in main_text_extracts():
        P, p2 = _extract(inp, name)
        if P is None:
            if name in MAIN_TEXT_V2:
                missing.append(f"{FIGS}/{name}.json {p2}")
            continue
        hits = sorted({s for s in _strings(P) if any(e in s for e in E3_PATHS)})
        keys = sorted(_keys(P) & E3_KEYS)
        carries[name] = (hits + keys)[:5]
        if hits:
            fails.append(f"{name}'s extract names E3 files ({hits[:3]})")
        if keys:
            fails.append(f"{name}'s extract carries E3 data under the key(s) {keys}")
        if _ext_reduced(P):
            reduced_ext.append(name)
    design, dprob = inp.text(DESIGN)
    item = sharing_item(design) if design is not None else None
    if design is None:
        missing.append(f"{DESIGN} {dprob}")
    elif item is None:
        fails.append(f"{DESIGN} §2.7 has no bullet barring an empirical sharing claim from E3 in the main text for "
                     "any policy")
    h5 = _d(A.get("H5")).get("pass")
    e = {"H5_pass": h5, "extracts_with_e3": carries,
         "design_item": item if item is None or len(item) <= 120 else item[:117] + "...",
         "_reduced": red or bool(reduced_ext)}
    if h5 is True:
        e.update(status="informative", _note="H5 held: its consequence does not apply (the checks are reported)"
                 + (f"; {'; '.join(fails + missing)}" if fails or missing else ""))
    elif fails:
        e.update(status="fail", _note="; ".join(fails))
    elif missing:
        e.update(status="missing", _note="; ".join(missing))
    else:
        e["status"] = "pass"
    if reduced_ext:
        e["_note"] = "; ".join(x for x in (e.get("_note"), f"extract(s) from a reduced run: {reduced_ext}") if x)
    return e


def h1_set_names(tag: str) -> list:
    """The names under which a caption may name a policy of H1's set: its tag and its registry label."""
    out = [tag]
    key = H1_KEYS.get(tag)
    if key:
        style = m3._figs_import("figs.style")
        p = style.POLICIES.get(key)
        if p is not None:
            out.append(p.label)
    return out


def plain_caption(text: str) -> str:
    """A caption or label without the LaTeX markup that does not change what it names: the box and text wrappers
    (\\mbox, \\hbox, \\text, \\textrm, \\textup), braces, ties and repeated white space ('SpotHedge-style,
    \\mbox{$N_{\\mathrm{Extra}}=0$}' and the registry's 'SpotHedge-style, $N_{\\mathrm{Extra}}=0$' read the same)."""
    t = re.sub(r"\\(?:mbox|hbox|text|textrm|textup)\b", "", text)
    t = t.replace("{", "").replace("}", "").replace("~", " ")
    return re.sub(r"\s+", " ", t).strip()


def names_policy(text: str, tag: str) -> bool:
    """Whether `text` names the policy of H1's set with tag `tag`: its tag as a whole token ('BL5' not inside
    'BL5-cur' or 'BL5N'), or its registry label at a place where no longer name of the registry starts ('Greedy
    renting'; 'RetroRenting-style' not as the start of 'RetroRenting-style, lagged'), both read by plain_caption."""
    style = m3._figs_import("figs.style")
    text = plain_caption(text)
    labels = {plain_caption(p.label) for p in style.POLICIES.values()}
    tg, *labs = h1_set_names(tag)
    if re.search(rf"(?<![A-Za-z0-9-]){re.escape(tg)}(?![A-Za-z0-9-])", text):
        return True
    for lab in map(plain_caption, labs):
        longer = [x for x in labels if len(x) > len(lab) and x.startswith(lab)]
        for m in re.finditer(re.escape(lab), text):
            if not any(text.startswith(x, m.start()) for x in longer):
                return True
    return False


H1_SET_PHRASE = re.compile(r"\bH1(?:'|’|\\textquoteright\s*)s\s+(?:comparison\s+)?set\b")


def names_h1_set(text: str) -> tuple[bool, list]:
    """(whether `text` names H1's set, the policies of the set it does not name): by the phrase "H1's set" (Fig. 4's
    caption refers to the set by name and panel (a) labels its policies, W1), or by naming every policy of the set
    (Table III's caption lists it, W2)."""
    unnamed = [t for t in m5.H1_SET if not names_policy(text, t)]
    return bool(H1_SET_PHRASE.search(text)) or not unnamed, unnamed


def states_count(text: str, k: int, n: int) -> bool:
    """Whether `text` states the count k of n ('3 of 16', '3 of the 16', '3 out of 16', '3/16')."""
    return re.search(rf"(?<![\d.]){k}\s*(?:/|of|out\s+of)\s*(?:the\s+)?{n}(?!\d)", plain_caption(text)) is not None


def _c_h2b(inp) -> dict:
    A, prob = inp.load(ANALYSIS_JSON)
    if A is None:
        return m3._absent(ANALYSIS_JSON, prob)
    h = _d(A.get("H2b"))
    n, below = h.get("n_weeks"), h.get("weeks_below_set")
    red = bool(_reduced(inp))
    fails, missing, reduced_ext, caps = [], [], [], {}
    counts = [k for k in ((n - below) if isinstance(n, int) and isinstance(below, int) else None, below)
              if isinstance(k, int)]
    for name in ("fig4v2", "table3_v2"):
        P, p2 = _extract(inp, name)
        if P is None:
            missing.append(f"{FIGS}/{name}.json {p2}")
            continue
        if _ext_reduced(P):
            reduced_ext.append(name)
        cap = _caption(P)
        caps[name] = cap
        if cap is None:
            fails.append(f"{name}'s extract has no caption draft")
            continue
        if name == "fig4v2" and not any(states_count(cap, k, n) for k in counts):    # C51: Fig. 4's draft only
            fails.append(f"{name}'s caption does not state H2b's count ({' or '.join(f'{k} of {n}' for k in counts)})")
        named, unnamed = names_h1_set(cap)
        if not named:
            fails.append(f"{name}'s caption neither says \"H1's set\" nor names {unnamed} of H1's set")
    every = []
    figs = inp.root / FIGS
    for p in sorted(figs.glob("*.json")) if figs.is_dir() else []:
        P, _ = inp.load(f"{FIGS}/{p.name}")
        cap = _caption(P)
        if cap and EVERY_BASELINE in cap.lower():
            every.append(p.name)
    if every:
        fails.append(f"caption(s) saying '{EVERY_BASELINE}': {every}")
    e = {"H2b_pass": h.get("pass"), "count": counts, "n_weeks": n, "captions": caps, "every_baseline": every,
         "_reduced": red or bool(reduced_ext)}
    if h.get("pass") is True:
        e.update(status="informative", _note="H2b held: its consequence does not apply (the checks are reported)"
                 + (f"; {'; '.join(fails + missing)}" if fails or missing else ""))
    elif fails:
        e.update(status="fail", _note="; ".join(fails))
    elif missing:
        e.update(status="missing", _note="; ".join(missing))
    else:
        e["status"] = "pass"
    if reduced_ext:
        e["_note"] = "; ".join(x for x in (e.get("_note"), f"extract(s) from a reduced run: {reduced_ext}") if x)
    return e


# ---------------------------------------------------------------- R rows
def _dims(runs, dims=("tags", "modes", "cells", "seeds")) -> dict:
    field = {"tags": "tag", "modes": "mode", "cells": "cell", "seeds": "seed"}
    return {d: sorted({str(_d(r).get(field[d])) for r in runs}) for d in dims}


def _runs_of(got: dict, part: str, kind: Optional[str] = None, pred: Optional[Callable] = None) -> list:
    S = got.get(part)
    if S is None:
        raise LookupError(f"{SUMS[part]} missing")
    return [r for r in map(_d, _l(S.get("runs"))) if (kind is None or r.get("kind") == kind)
            and (pred is None or pred(r))]


def _reported(A: Optional[dict], key: str) -> dict:
    v = _d(_d(A).get("reported")).get(key)
    if not isinstance(v, dict):
        raise LookupError(f"{ANALYSIS_JSON} reported.{key} missing")
    return v


def _is_lag(tag) -> bool:
    t = m5.TAGS.get(tag)
    return t is not None and t.kind == "lag"


def _scope_weeks(got, A) -> dict:
    return _dims(_runs_of(got, "main", "week", lambda r: r.get("seed") == 0), ("tags", "cells"))


def _scope_pareto(got, A) -> dict:
    pf = _reported(A, "pareto_front")
    tags = set(_dims(_runs_of(got, "main", "week"), ("tags",))["tags"])
    return {"cells": sorted(pf), "tags": [t for t in ma.PARETO_TAGS if t in tags]}


def _scope_crossings(got, A) -> dict:
    cr = _reported(A, "intensity_crossings")
    return {"tags": sorted(cr), "cells": sorted({str(c) for v in cr.values() for c in _d(v)})}


def _scope_rc(got, A) -> dict:
    rc = _reported(A, "RC")
    return {"tags": sorted(rc), "modes": sorted({m for v in rc.values() for m in _d(v)}),
            "cells": sorted({c for v in rc.values() for x in _d(v).values() for c in _d(x)}),
            "seeds": sorted({s for v in rc.values() for x in _d(v).values() for y in _d(x).values() for s in _d(y)})}


def _scope_boundary(got, A) -> dict:
    return _dims(_runs_of(got, "second", "week", lambda r: r.get("mode") in BOUNDARY_MODES), ("tags", "modes", "cells"))


def _scope_e5(got, A) -> dict:
    return _dims(_runs_of(got, "second", "e5"), ("tags", "modes", "cells"))


def _scope_lag(got, A) -> dict:
    return _dims(_runs_of(got, "second", "week", lambda r: _is_lag(r.get("tag"))), ("tags", "cells"))


def _scope_gap(got, A) -> dict:
    return _dims(_runs_of(got, "second", "gap"), ("tags", "cells"))


def _scope_q44(got, A) -> dict:
    return _dims(_runs_of(got, "grid", "q44"), ("tags", "cells"))


def _scope_seeds(got, A) -> dict:
    return _dims(_runs_of(got, "seeds", "week"))


def _scope_grid(got, A) -> dict:
    return _dims(_runs_of(got, "grid", None, lambda r: r.get("kind") in ("week", "gap")))


def _scope_q6(got, A) -> dict:
    return _dims(_runs_of(got, "fam", "fam", lambda r: str(r.get("src", "")).startswith("F")
                          and r.get("mode") in FAM_REPORTED_MODES))


def _scope_h3(got, A) -> dict:
    g = [(p, _d(x).get("tag")) for p, S in got.items() for x in _l(S.get("guarded"))]
    if any(p not in got for p in PARTS):
        raise LookupError("a part summary is missing")
    return {"parts": sorted({p for p, _ in g}), "tags": sorted({str(t) for _, t in g})}


def _scope_f3(got, A) -> dict:
    return _dims(_runs_of(got, "fam", "fam", lambda r: r.get("fam") == "F3"), ("tags", "cells"))


def _scope_pairs(got, A) -> dict:
    """H4's pairs by family and lender (W4: the table is by family and lender, not by instance)."""
    S = got.get("fam")
    if S is None:
        raise LookupError(f"{SUMS['fam']} missing")
    pairs = _l(_d(S.get("fam")).get("pairs"))
    return {"families": sorted({str(_d(x).get("fam")) for x in pairs}),
            "modes": sorted({str(_d(x).get("mode")) for x in pairs})}


def _scope_e3(got, A) -> dict:
    return _dims(_runs_of(got, "e3", "e3cell"), ("tags", "modes", "cells"))


def _scope_t3(got, A) -> dict:
    """Table III v2's rows over its 16 weeks (main, policy seed 0) and its gap days (second's gap runs, W2)."""
    return _dims(_runs_of(got, "main", "week", lambda r: r.get("seed") == 0 and r.get("tag") in TABLE3_V2_TAGS)
                 + _runs_of(got, "second", "gap", lambda r: r.get("tag") in TABLE3_V2_TAGS), ("tags", "cells"))


def _scope_outcomes(got, A) -> dict:
    if not isinstance(A, dict):
        raise LookupError(f"{ANALYSIS_JSON} missing")
    return {"hypotheses": [h for h in HYPOTHESES if h in A]}


@dataclass(frozen=True)
class RItem:
    """One item reported with no threshold or as measured (§6), its supplementary table and the figure script that
    writes it (W4), the scope the table must cover, and the table's data file in the same folder, if any, whose
    sha256 and row count the extract records under tables.<its stem>."""
    id: str
    item: str
    source: str
    table: str
    figure: str
    scope: Callable
    data: Optional[str] = None


R_ITEMS = (
    RItem("R-1", "the transplants (Sublet against BL1N and BL5N per week) and the decomposition rows: per-week L-tr "
          "r0 and W0 of every tag of part main", "§6, reported in full", "e7v2_weeks.tex", "sf_e7_decomp",
          _scope_weeks),
    RItem("R-2", "the per-week Pareto front of L-tr r0 and W0 over every tag of §3 that is not an ablation of A9",
          "§6, reported in full", "e7v2_pareto.tex", "sf_e7_decomp", _scope_pareto),
    RItem("R-3", "the stress-intensity curve and each policy's crossing of 1, every tag and week with its grid",
          "§6, reported in full", "e7v2_crossings.tex", "sf_e7_intensity", _scope_crossings),
    RItem("R-4", "RC under every mode, with each run's fallback and stranding totals and MS4's fallback share after "
          "reclaims", "§6, reported in full; §4.5", "e7v2_rc.tex", "sf_e7_decomp", _scope_rc, "e7v2_rc_runs.csv"),
    RItem("R-5", "L-vr, L-rf, L-ad and the p99.9 buffer (part second)", "§6, reported in full",
          "e7v2_boundary.tex", "sf_e7_boundary", _scope_boundary),
    RItem("R-6", "the E5 menus (part second)", "§6, reported in full", "e7v2_e5.tex", "sf_e7_boundary", _scope_e5),
    RItem("R-7", "lagged demand (part second)", "§6, reported in full", "e7v2_lag.tex", "sf_e7_boundary", _scope_lag),
    RItem("R-8", "the gap-day ALG/LB (part second)", "§6, reported in full", "e7v2_gap.tex", "sf_e7_boundary",
          _scope_gap),
    RItem("R-9", "Q44 criteria T and S on the development-exposed cells (part grid)", "§6, reported in full",
          "e7v2_q44.tex", "sf_e7_grid_dev", _scope_q44),
    RItem("R-10", "policy seeds 1-2 (part seeds)", "§6, reported in full", "e7v2_seeds.tex", "sf_e7_decomp",
          _scope_seeds),
    RItem("R-11", "the development-exposed E7 grid, its week runs and gap reruns (part grid)", "§6, reported in full",
          "e7v2_grid.tex", "sf_e7_grid_dev", _scope_grid),
    RItem("R-12", "the Q6 family runs under F-ad and F-eg (part fam)", "§6, reported in full", "fam_v2_q6.tex",
          "sf_fam_v2", _scope_q6),
    RItem("R-13", "H3's counts: aborts, switches of S, robust-form slots, projected slots, dropped actions and K0 "
          "uses, by part and row", "§6, H3 (reported)", "e7v2_h3.tex", "sf_e7_decomp", _scope_h3),
    RItem("R-14", "F3 against BL1-G, BL5-G and A9 alone", "§6, H4 (reported, no criterion)", "fam_v2_f3.tex",
          "sf_fam_v2", _scope_f3),
    RItem("R-15", "H4's counted pairs by family and lender", "§6, H4", "fam_v2_pairs.tex", "sf_fam_v2",
          _scope_pairs),
    RItem("R-16", "E3, every policy shared and siloed (reported as measured)", "§6, H5's consequence; W3",
          "e3_v2.tex", "sf_e3_v2", _scope_e3),
    RItem("R-17", "Table III's intervals and per-week values (its weeks and gap days)", "W2",
          "e7v2_table3_intervals.tex", "sf_e7_decomp", _scope_t3),
    RItem("R-18", "the pre-registered outcomes: each hypothesis's kind, criterion, measured value, holds or fails "
          "(a failed criterion is reported as measured)", "§6; prereg §8", "ms5b_outcomes.tex", "sf_e7_decomp",
          _scope_outcomes),
)


def table_scope(payload: Optional[dict], table: str) -> tuple[Optional[dict], Optional[str]]:
    """(scope, None) of a table in an extract's tables block (data.tables, else the top-level tables; keyed by the
    file name or its stem), or (None, why). The scope is a mapping; uncovered() reads its entries."""
    for blk in (_d(_d(payload).get("data")).get("tables"), _d(payload).get("tables")):
        if not isinstance(blk, dict):
            continue
        ent = blk.get(table, blk.get(Path(table).stem))
        if ent is None:
            continue
        sc = _d(ent).get("scope")
        if not isinstance(sc, dict) or not sc:
            return None, f"tables.{table}.scope is not a non-empty mapping"
        return sc, None
    return None, f"the extract has no tables.{table} (or tables.{Path(table).stem})"


# R rows: the scope keys under which a figure script may list each required dimension (W4 leaves the keys to the
# scripts; the U39 scripts name the week cells 'weeks', the gap days 'days', the family instances 'instances', E5's
# lender levels 'levels'): a key of DIM_KEYS, and for cells also every key whose name contains CELL_KEY_RE
DIM_KEYS = {"tags": ("tags",), "modes": ("modes", "levels"), "seeds": ("seeds",), "cells": ("cells",),
            "parts": ("parts",), "hypotheses": ("hypotheses",), "families": ("families",)}
CELL_KEY_RE = re.compile(r"cell|week|day|instance|alignment")


def _scalar(x) -> str:
    """A scope value as a string ('8' for 8 and 8.0; JSON's spelling otherwise)."""
    if isinstance(x, float) and x.is_integer():
        return str(int(x))
    if isinstance(x, bool) or x is None:
        return json.dumps(x)
    return str(x)


def _flat(x) -> set:
    """The values of a scope entry as strings: a list's items and a mapping's keys and values, recursively; a scalar
    stands for itself."""
    if isinstance(x, dict):
        return {_scalar(k) for k in x} | {s for v in x.values() for s in _flat(v)}
    if isinstance(x, list):
        return {s for v in x for s in _flat(v)}
    return {_scalar(x)}


def _alts(v: str) -> set:
    """A value and the spellings of the same config seed ('c301' and '301')."""
    if re.fullmatch(r"c\d+", v):
        return {v, v[1:]}
    if re.fullmatch(r"\d+", v):
        return {v, f"c{v}"}
    return {v}


def uncovered(required: dict, scope: dict) -> dict:
    """{dimension: values of `required` that `scope` does not list}. A required value is covered when it, or another
    spelling of the same config seed ('c301', '301'), is listed under one of the dimension's keys (DIM_KEYS; for cells
    also any key whose name contains CELL_KEY_RE). A composite cell ('short:c301', 'b8:c301', 'F1_m2_r4:F-ad') is also
    covered when each of its ':' parts is listed under any key of the scope ('b8' also as 8 under a key 'b'). A
    dimension with no such key in `scope` is reported as '<absent>' with its first required values."""
    every = {k: _flat(v) for k, v in scope.items()}
    union = set().union(*every.values()) if every else set()
    out = {}
    for dim, want in required.items():
        keys = [k for k in scope if k in DIM_KEYS.get(dim, (dim,))
                or (dim == "cells" and isinstance(k, str) and CELL_KEY_RE.search(k))]
        if not keys and dim != "cells":
            if want:
                out[dim] = ["<absent>"] + [str(x) for x in list(want)[:5]]
            continue
        have = set().union(*(every[k] for k in keys)) if keys else set()

        def part_listed(x: str) -> bool:
            m = re.fullmatch(r"([a-z]+)(\d+)", x)
            return bool(_alts(x) & union) or bool(m and m.group(1) in every and m.group(2) in every[m.group(1)])

        def covered(v: str) -> bool:
            if _alts(v) & have:
                return True
            return dim == "cells" and ":" in v and all(part_listed(x) for x in v.split(":"))
        miss = [str(x) for x in want if not covered(str(x))]
        if miss:
            out[dim] = (["<absent>"] if not keys else []) + miss
    return out


def _r(inp, item: RItem) -> dict:
    got, probs = _parts(inp)
    A, aprob = inp.load(ANALYSIS_JSON)
    red = bool(_reduced(inp))
    e = {"table": f"{TABLES_DIR}/{item.table}", "figure": item.figure, "_reduced": red}
    try:
        req = item.scope(got, A)
    except LookupError as err:
        return {**e, **_absent_any(probs + ([] if A is not None else [f"{ANALYSIS_JSON} {aprob}"]) or [str(err)])}
    e["required"] = {k: len(v) for k, v in req.items()}
    exists = (inp.root / TABLES_DIR / item.table).is_file()
    P, prob = _extract(inp, item.figure)
    why = []
    if not exists:
        why.append(f"{TABLES_DIR}/{item.table} absent (unit {UNITS.get(item.figure, 'U39')})")
    if P is None:
        why.append(f"{FIGS}/{item.figure}.json {prob}")
        if prob != "missing":
            return {**e, "status": "bug_input", "_note": "; ".join(why)}
    else:
        if _ext_reduced(P):
            e["_reduced"] = True
        sc, sprob = table_scope(P, item.table)
        if sc is None:
            why.append(f"{item.figure}: {sprob}")
        else:
            unc = uncovered(req, sc)
            e["uncovered"] = {k: v[:10] for k, v in unc.items()}
            if unc:
                why.append(f"{item.figure}'s scope of {item.table} does not cover " +
                           "; ".join(f"{k} {v[:5]}{' ...' if len(v) > 5 else ''}" for k, v in unc.items()))
    e["table_exists"] = exists
    if item.data is not None and P is not None:
        e["data_file"] = f"{TABLES_DIR}/{item.data}"
        absent, wrong = _data_file(inp, P, item.data, e)
        why += absent
        if wrong:
            return {**e, "status": "fail", "_note": "; ".join(why + wrong)}
    e.update(status="missing" if why else "pass", _note="; ".join(why) or None)
    return e


def _data_file(inp, P: dict, data: str, e: dict) -> tuple[list, list]:
    """(absent, wrong) for a table's data file: absent names a missing file or extract entry; wrong a sha256 or a
    number of data rows (lines after the header) unlike the extract's entry tables.<stem>. Fills e's data_rows and
    data_sha256_equal."""
    f = inp.root / TABLES_DIR / data
    ent = None
    for blk in (_d(_d(P).get("data")).get("tables"), _d(P).get("tables")):
        if isinstance(blk, dict) and isinstance(blk.get(Path(data).stem), dict):
            ent = blk[Path(data).stem]
            break
    absent = [] if f.is_file() else [f"{TABLES_DIR}/{data} absent"]
    if ent is None:
        absent.append(f"the extract records no tables.{Path(data).stem}")
    if absent:
        return absent, []
    raw = f.read_bytes()
    rows = max(raw.count(b"\n") - 1, 0)
    e.update(data_rows=rows, data_sha256_equal=hashlib.sha256(raw).hexdigest() == ent.get("sha256"))
    wrong = []
    if not e["data_sha256_equal"]:
        wrong.append(f"{TABLES_DIR}/{data}: sha256 unlike the extract's tables.{Path(data).stem}.sha256")
    if rows != ent.get("n_rows"):
        wrong.append(f"{TABLES_DIR}/{data}: {rows} data rows, the extract records {ent.get('n_rows')}")
    return [], wrong


# ---------------------------------------------------------------- D-1
def prereg_items(prereg: str) -> dict:
    """{'B1': text, ...}: the numbered items of the pre-registration's §7 under its lettered headings."""
    sec = m5.sections(prereg, ("7",)).get("7") or ""
    out, letter = {}, None
    for ln in sec.splitlines():
        h = re.match(r"^\*([A-Z])\. ", ln)
        if h:
            letter = h.group(1)
            continue
        m = re.match(r"^(\d+)\. (.+)$", ln)
        if m and letter:
            out[f"{letter}{m.group(1)}"] = m.group(2).strip()
    return out


def prereg_deviations(prereg: str) -> list:
    """The items that the pre-registration's §7 names as deviations reported in the paper (its sentence "Under the
    note's §6, ... with their reasons: B1 (...), B2, ... and C2.")."""
    m = re.search(r"Under the note's §6, the items that change[^\n]*?with their reasons:(.*?)\.(?:\s|$)", prereg)
    if m is None:
        return []
    body = re.sub(r"\([^()]*\)", "", m.group(1))
    return re.findall(r"\b([A-E]\d{1,2})\b", body)


def words_md(text: str) -> list:
    """The words of a markdown text with its markup removed (emphasis, code marks, math shift, TeX commands)."""
    t = re.sub(r"\\[A-Za-z]+\*?", " ", text)
    return [w.lower() for w in re.findall(r"[A-Za-z0-9]+", t)]


def words_tex(text: str) -> list:
    """The words of a LaTeX text with its markup removed (comments, commands, braces, math shift)."""
    t = re.sub(r"(?<!\\)%[^\n]*", " ", text)
    t = re.sub(r"\\([_%&#$])", r"\1", t)
    t = re.sub(r"\\[A-Za-z]+\*?", " ", t)
    return [w.lower() for w in re.findall(r"[A-Za-z0-9]+", t)]


def item_variants(text: str) -> list:
    """The word lists a table may give for a §7 item: the whole text, without its italic title, without its closing
    'Recorded: ...' sentence, and without both."""
    title = re.match(r"^\*([^*]+)\*", text)
    rest = text[title.end():] if title else text
    out = []
    for t in (text, rest):
        out.append(words_md(t))
        k = t.rfind("Recorded:")
        if k > 0:
            out.append(words_md(t[:k]))
    return out


def tex_items(tex: str) -> dict:
    """{'B1': [words], ...} of a hand-set table: the rows of its tabular whose first cell is an item ('B1', 'B.1',
    with any markup) and the \\item[B1] entries of a list."""
    t = re.sub(r"(?<!\\)%[^\n]*", " ", tex)
    out = {}
    for m in re.finditer(r"\\item\s*\[([^\]]*)\](.*?)(?=\\item\b|\\end\{)", t, re.S):
        k = re.sub(r"[^A-Za-z0-9]", "", re.sub(r"\\[A-Za-z]+", "", m.group(1)))
        if re.fullmatch(r"[A-E]\d{1,2}", k):
            out[k] = words_tex(m.group(2))
    body = re.sub(r"\\(toprule|midrule|bottomrule|hline|endhead|endfirsthead|endfoot|endlastfoot)\b", " ", t)
    body = re.sub(r"\\cmidrule(\([^)]*\))?\{[^}]*\}", " ", body)
    for row in re.split(r"\\\\(?:\[[^\]]*\])?", body):
        cells = re.split(r"(?<!\\)&", row)
        if len(cells) < 2:
            continue
        first = cells[0].rsplit("}", 1)[-1] if re.search(r"\\begin\{", cells[0]) else cells[0]
        k = re.sub(r"[^A-Za-z0-9]", "", re.sub(r"\\[A-Za-z]+", "", first))
        if re.fullmatch(r"[A-E]\d{1,2}", k):
            out[k] = words_tex(" ".join(cells[1:]))
    return out


# C58 (design/ms7/w_spec.md W-D8; design/ms7/plan.md D3): the table's rows in the paper's names, in §7's order
DEVIATION_TITLES = {"B1": "H3's abort clause", "B2": "Refuting the no-abort proposition",
                    "B3": "Runs that H3's endpoint selects", "B5": "Allowance of the guarded comparison rows",
                    "B12": "RetroRenting + notice layer as built", "B13": "Empty demand in critical-ratio renting",
                    "C2": "Hypotheses of the no-abort proposition"}
DESIGN_IDS = re.compile(r"\b(?:a8p?|a9|bl\d[a-z0-9]*|sublet 1way|u\d\d)\b")      # on words_tex's lower-case words


def titled_items(tex: str) -> dict:
    """C58: {'B1': [words], ...} of the rows whose first cell is an item's title of DEVIATION_TITLES."""
    t = re.sub(r"(?<!\\)%[^\n]*", " ", tex)
    out = {}
    for row in re.split(r"\\\\(?:\[[^\]]*\])?", t):
        cells = re.split(r"(?<!\\)&", row)
        if len(cells) < 2:
            continue
        head = " ".join(cells[0].replace("\\addlinespace", " ").split())
        for k, title in DEVIATION_TITLES.items():
            if head.endswith(title):
                out[k] = words_tex("&".join(cells[1:]))
    return out


def _d1(inp) -> dict:
    tex, prob = inp.text(DEVIATIONS)
    pre, pprob = inp.text(PREREG)
    if pre is None:
        return {"status": "missing", "_note": f"{PREREG} {pprob}"}
    want = prereg_deviations(pre)
    items = prereg_items(pre)
    e = {"registered": want, "listed": None}
    if tex is None:
        return {**e, "status": "missing" if prob == "missing" else "bug_input",
                "_note": f"{DEVIATIONS} {prob} (hand-set by unit U38)"}
    got = tex_items(tex)
    c58 = not got                       # C58: rows titled in the paper's names (design/ms7/plan.md D3), not 'B1', ...
    if c58:
        got = titled_items(tex)
    e["listed"] = list(got)
    fails = []
    if not want:
        fails.append(f"{PREREG} §7 names no deviation item")
    extra, absent = [k for k in got if k not in want], [k for k in want if k not in got]
    if extra or absent:
        fails.append(f"items listed but not registered {extra}, registered but not listed {absent}")
    bad = []
    for k in want:
        if c58 and k in got:            # C58: each row states its item with its reason; the verbatim text stays in §7
            if k not in items:
                bad.append(f"{k} (no item {k} in {PREREG} §7)")
            elif len(got[k]) < 20 or DESIGN_IDS.search(" ".join(got[k])):
                bad.append(f"{k} (fewer than 20 words or a design ID)")
            continue
        if k in got and k in items and got[k] not in item_variants(items[k]):
            ref = item_variants(items[k])[0]
            i = next((j for j, (a, b) in enumerate(zip(got[k], ref)) if a != b), min(len(got[k]), len(ref)))
            bad.append(f"{k} (first difference at word {i}: {' '.join(got[k][i:i + 4])!r} against "
                       f"{' '.join(ref[i:i + 4])!r})")
        elif k not in items:
            bad.append(f"{k} (no item {k} in {PREREG} §7)")
    if bad:
        fails.append("texts not copied from the pre-registration's §7: " + "; ".join(bad))
    e["text_differs"] = bad
    return {**e, "status": "fail" if fails else "pass", "_note": "; ".join(fails) or None}


# ---------------------------------------------------------------- F rows
def runs_listed(payload) -> dict:
    """{repository-relative runs/ path: sha256} that an extract lists (W10): {path: sha256} mappings, and objects
    with 'path' (or 'file') and 'sha256', anywhere in it."""
    out = {}

    def walk(x):
        if isinstance(x, dict):
            p = x.get("path", x.get("file"))
            if isinstance(p, str) and "/runs/" in p and isinstance(x.get("sha256"), str):
                out[p] = x["sha256"]
            for k, v in x.items():
                if isinstance(k, str) and "/runs/" in k and isinstance(v, str) and HEX64.fullmatch(v):
                    out[k] = v
                else:
                    walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    walk(payload)
    return out


def build_figure(root: Path, module: str) -> tuple[dict, list]:
    """(data after figs.common.cli's JSON round trip, recorded sources) of a figure or float script's build() on the
    files under `root` (SUBLET_FIGS_IN_ROOT set for the call)."""
    saved = os.environ.get(ENV_IN_ROOT)
    os.environ[ENV_IN_ROOT] = str(root)
    try:
        m3._figs_import("figs.style")
        from figs.common import json_number
        from figs.inputs import Inputs
        inp = Inputs()
        data = json.loads(json.dumps(m3._figs_import(module).build(inp), allow_nan=False, default=json_number))
        return data, list(inp.sources)
    finally:
        if saved is None:
            os.environ.pop(ENV_IN_ROOT, None)
        else:
            os.environ[ENV_IN_ROOT] = saved


def _f(inp, name: str, script: str, module: str) -> dict:
    e = {"figure": name, "script": script}
    rel = f"{FIGS}/{name}.json"
    if not (paths.REPO / script).is_file():
        return {**e, "status": "missing", "_note": f"{script} absent (unit {UNITS.get(name, 'U39')})"}
    P, prob = inp.load(rel)
    if P is None:
        return {**e, **m3._absent(rel, prob)}
    if name not in (P.get("figure"), P.get("table")):
        return {**e, "status": "fail", "_note": f"{rel} is the extract of {P.get('figure') or P.get('table')!r}"}
    e["_reduced"] = _ext_reduced(P)
    try:
        data, sources = build_figure(inp.root, module)
    except FileNotFoundError as err:
        return {**e, "status": "missing", "_note": f"an input of {script} is absent under the root ({err})"[:300]}
    ext = P.get("data")
    if isinstance(data, dict) and "sources" in data and isinstance(ext, dict) and "sources" not in ext:
        data = {k: v for k, v in data.items() if k != "sources"}
    diffs = _diff(data, ext, "$.data")
    src_eq = sources == list(_l(P.get("sources")))
    listed = runs_listed(P)
    run_srcs = [s for s in _l(P.get("sources")) if isinstance(s, str) and "/runs/" in s]
    unlisted = [s for s in run_srcs if s not in listed]
    wrong, absent = [], []
    for p, sha in sorted(listed.items()):
        f = inp.root / p
        if not f.is_file():
            absent.append(p)
        elif _sha256(f) != sha:
            wrong.append(p)
    fails = []
    if diffs:
        fails.append(f"the build differs from {rel}: " + "; ".join(x.replace(" analysis.json", " the extract")
                                                                    for x in diffs[:4]))
    if not src_eq:
        fails.append(f"the build's sources differ from the extract's ({len(sources)} against "
                     f"{len(_l(P.get('sources')))})")
    if unlisted:
        fails.append(f"{len(unlisted)} runs/ source(s) without a sha256 in the extract (W10): {unlisted[:3]}")
    if wrong:
        fails.append(f"{len(wrong)} runs/ file(s) whose sha256 is not the recorded one: {wrong[:3]}")
    e.update(equal=not diffs, sources_equal=src_eq, n_runs_listed=len(listed), n_runs_sources=len(run_srcs),
             runs_unlisted=unlisted[:10], runs_sha256_differ=wrong[:10], runs_absent=absent[:10])
    if fails:
        e.update(status="fail", _note="; ".join(fails))
    elif absent:
        e.update(status="missing", _note=f"{len(absent)} listed runs/ file(s) absent under the root: {absent[:3]}")
    else:
        e["status"] = "pass"
    return e


# ---------------------------------------------------------------- FL-1, RB-1
def _fl1(inp) -> dict:
    F, prob = inp.load(FLOATS_MS5B)
    if F is None:
        return {**m3._absent(FLOATS_MS5B, prob), "_note": f"{FLOATS_MS5B} {prob} (paper/layout_check/pageplan/"
                                                            "floats_heights.py --ms5b writes it)"}
    fl = _d(F.get("floats"))
    rows, fails, missing = {}, [], []
    for k, label in FLOAT_NAMES_MS5B.items():
        v = _d(fl.get(k))
        rows[k] = {f: v.get(f) for f in ("measured_pages", "budget_pages", "within_budget", "difference_pages")}
        if not v:
            missing.append(f"{label} ({k}) not measured")
            continue
        if not m3._num(v.get("measured_pages")):
            fails.append(f"{label}: measured_pages {v.get('measured_pages')!r}")
        src = v.get("source") if isinstance(v.get("source"), str) else f"{FLOATS_DIR}/{k}.tex"
        now = _sha256(inp.root / src)
        if v.get("sha256") != now:
            fails.append(f"{label}: the record's sha256 is not that of {src} now (a stale measurement)")
    e = {"floats": rows, "written": F.get("written")}
    if fails:
        return {**e, "status": "fail", "_note": "; ".join(fails)}
    if missing:
        return {**e, "status": "missing", "_note": "; ".join(missing)}
    over = [FLOAT_NAMES_MS5B[k] for k, r in rows.items() if r["within_budget"] is False]
    return {**e, "status": "informative",
            "_note": "measured heights " + ", ".join(f"{FLOAT_NAMES_MS5B[k]} {m3._fmt(r['measured_pages'], 4)} page "
                                                     f"(budget {m3._fmt(r['budget_pages'], 4)})"
                                                     for k, r in rows.items())
                     + (f"; over budget: {', '.join(over)} (informative, W11)" if over else "")}


def _rebuild_entries() -> list:
    """Today's figs.rebuild.entries() as [name, kind, outputs] (test-only registrations of other test modules, named
    test_*, set aside as tests/test_ms5_out.py does)."""
    style = m3._figs_import("figs.style")
    leaked = {k: style.FIGURES.pop(k) for k in [k for k in style.FIGURES if k.startswith("test_")]}
    try:
        return [[e.name, e.kind, list(e.outputs)] for e in _RB.entries()]
    finally:
        style.FIGURES.update(leaked)


def _rb1(inp) -> dict:
    R, prob = inp.load(REBUILD)
    if R is None:
        return m3._absent(REBUILD, prob)
    heights = _d(R.get("heights"))
    if "ms5b" not in heights:
        return {"status": "missing", "git_revision": _d(R.get("meta")).get("git_revision"),
                "_note": f"{REBUILD} has no 'ms5b' float heights: it is an earlier milestone's exit run; the MS5b exit "
                         "rebuild (W15 item 5, CHECK=1 in a clean clone of the merge commit) is not copied in yet"}
    e = c5._rb1(inp)
    probs = list(e.get("problems") or [])
    if _d(heights.get("ms5b")).get("equal") is not True:
        probs.append(f"float heights ms5b equal {_d(heights.get('ms5b')).get('equal')!r}")
    checked = {_d(h).get("path") for h in _l(R.get("hand_set"))}
    lacking = [p for p in _RB.HAND_SET if p not in checked]
    if lacking:
        probs.append(f"hand-set file(s) not checked: {lacking}")
    try:
        now = _rebuild_entries()
    except Exception as err:            # a list error of figs.rebuild (RebuildError)
        now = None
        probs.append(f"figs.rebuild.entries() fails: {type(err).__name__}: {err}"[:200])
    rec = [[_d(x).get("name"), _d(x).get("kind"), _l(_d(x).get("outputs"))] for x in _l(R.get("entries"))]
    if now is not None and rec != now:
        probs.append("the record's entries are not today's rebuild list (figs.rebuild.entries()): rerun the exit "
                     "rebuild")
    return {**e, "heights_equal": {**_d(e.get("heights_equal")), "ms5b": _d(heights.get("ms5b")).get("equal")},
            "problems": probs, "status": "fail" if probs else "pass", "_note": "; ".join(probs) or None}


# ---------------------------------------------------------------- the rows
@dataclass(frozen=True)
class Spec:
    """One row of W11: id, group, section, kind, the row's claim, the status label (None: `label_note` says what it
    tests), the reference (text and file), the entry's fields shown as the regenerated and reference values (paths
    as ms4_claims._get), the regenerated value's file, whether the row may be explained (H rows), and the function
    that computes its entry."""
    id: str
    group: str
    section: str
    kind: str
    claim: str
    label: Optional[str]
    label_note: Optional[str] = None
    reference: str = ""
    reference_file: str = ""
    fields: tuple = ()
    ref_fields: tuple = ()
    regenerated_file: Optional[str] = None
    explainable: bool = False
    compute: Optional[Callable] = None


def _rows_spec() -> tuple:
    gate = "code/sim/sublet/experiments/ms5b_common.py (check_confirmation, check_copy); " + PREREG + " §8"
    rows = [
        Spec("G-1", "G", "§4.3", "property",
             claim="each part's gate record: ok, the pre-registration at HEAD, one HEAD (the freeze commit), the "
                   "pre-registration's and the analysis script's sha256 then equal to theirs now, a clean tree, the "
                   "pilot anchor an ancestor with §5 and §6 unchanged",
             label=None, label_note="the confirmation's gate (§4.3)",
             reference="the pre-registration now and its analysis_sha256 line; experiments/ms5b_analysis.py now",
             reference_file=f"{PREREG}; {m5.ANALYSIS_REL}",
             fields=("freeze_commit", "prereg_sha256", "analysis_sha256_prereg", "analysis_sha256_module",
                     "analysis_sha256_root", "freeze_in_git", "n_parts", "#failures"),
             regenerated_file=f"{CONF}/<part>/summary.json meta.confirmation_gate", compute=_g1),
        Spec("G-2", "G", "§4.3", "property", claim="no part from a reduced run, and one commit over the summaries "
                                                   "and manifests of the six parts",
             label=None, label_note="the provenance of the confirmation's outputs",
             reference="meta.reduced false; one meta.git_revision", reference_file=gate,
             fields=("commits", "n_files", "reduced"),
             regenerated_file=f"{CONF}/<part>/summary.json, manifest.json meta", compute=_g2),
        Spec("G-3", "G", "§4.3", "property",
             claim="the copy check passed against the clean clone of the summaries' commit, and the copy is "
                   "unchanged since (tree digests over the six part folders)",
             label=None, label_note="the copy of the confirmation's outputs (§4.3; prereg §8)",
             reference="every check true; the clone's commit; the tree digests", reference_file=COPY_REC,
             fields=("pass", "failed", "clone_commit", "n_files_copy", "versioned_current", "full_current"),
             regenerated_file=f"{COPY_REC} (and the tree digests recomputed by this report)", compute=_g3),
        Spec("G-4", "G", "§4.5", "property",
             claim="every listed job of the six parts has an 'ok' record (Q39's MILP rule for part e3), and no run "
                   "is missing",
             label=None, label_note="the job records and the missing-run rule (§4.5)",
             reference="jobs = jobs_ok = the job list; jobs_not_ok, missing empty", reference_file=gate,
             fields=("parts.*.jobs", "parts.*.n_blocking", "n_blocking", "n_milp_lp_fallback"),
             regenerated_file=f"{CONF}/<part>/manifest.json, jobs/, summary.json meta", compute=_g4),
        Spec("G-5", "G", "§4.5", "property", claim="every run of every part ok, with no invariant failure",
             label=None, label_note="the engine's invariants", reference="status ok; n_invariant_failures 0",
             reference_file="design/Sublet_design.md §5.2",
             fields=("n_runs", "n_not_ok", "n_invariant_failures"),
             regenerated_file=f"{CONF}/<part>/summary.json runs", compute=_g5),
        Spec("A-1", "A", "§4.3, §6", "reproduction",
             claim="the analysis recomputed by experiments/ms5b_analysis.py from the six summaries equals "
                   "analysis.json except meta; the script's sha256 equals the pre-registration's analysis_sha256",
             label=None, label_note="the frozen analysis (§4.3)",
             reference="analysis.json without meta; the pre-registration's analysis_sha256",
             reference_file=f"{ANALYSIS_JSON}; {PREREG}",
             fields=("equal", "n_differences", "sha256", "analysis_sha256_prereg", "analysis_sha256_module",
                     "pilot_dry_run", "git_revision"),
             regenerated_file="ms5b_analysis.analyse(ms5b_analysis.load(<root>/code/sim)), recomputed by this "
                              "report", compute=_a1),
        Spec("A-2", "A", "§6", "property", claim="the analysis's CONFIG is the one the pre-registration registers",
             label=None, label_note="the values the pilot set (§6)",
             reference="the pre-registration's CONFIG values (§5, As registered)", reference_file=PREREG,
             fields=("config",), ref_fields=("registered",), regenerated_file=f"{ANALYSIS_JSON} config",
             compute=_a2),
    ]
    for hid in HYPOTHESES:
        lab = f"{W_AB}; {PROP_P}" if hid == "H3" else None
        rows.append(Spec(hid, "H", "§6", "hypothesis",
                         claim=f"{hid} as registered (the pre-registration's §5); verdict from analysis.json `pass`, "
                               "a failure explained only by its consequence rows",
                         label=lab, label_note=None if lab else "a pre-registered hypothesis, a measurement",
                         reference="the registered statement and threshold", reference_file=f"{PREREG} §5",
                         fields=H_FIELDS[hid], ref_fields=("threshold",) if hid in ("H1", "H6") else (),
                         regenerated_file=f"{ANALYSIS_JSON} {hid}", explainable=True,
                         compute=lambda inp, h=hid: _h(inp, h)))
    rows += [
        Spec("C-H5", "C", "§6, W3", "consequence",
             claim="H5's consequence: no main-text figure or float extract (fig4v2, table3_v2; the frozen Figs. 1-3 "
                   "and 5-7) carries E3 data, and design §2.7 bars an empirical sharing claim from E3 in the main "
                   "text for any policy",
             label=None, label_note="H5's registered consequence as W3 reads it",
             reference="no E3 file or E3 key in the extracts; the §2.7 item",
             reference_file=f"{FIGS}/fig4v2.json, table3_v2.json, fig1-3, fig5-7.json; {DESIGN} §2.7",
             fields=("H5_pass", "extracts_with_e3", "design_item"),
             regenerated_file=f"{FIGS}/fig4v2.json, table3_v2.json and the other main-text extracts (every string and "
                              f"key, sources included); {DESIGN} §2.7",
             compute=_c_h5),
        Spec("C-H2b", "C", "§6, W1, W2", "consequence",
             claim="H2b's consequence: Fig. 4's and Table III's caption drafts state H2b's count and name H1's set; "
                   "no extract caption says 'every baseline'",
             label=None, label_note="H2b's registered wording rule",
             reference="H2b's count from analysis.json; H1's set (ms5b_common.H1_SET)",
             reference_file=f"{ANALYSIS_JSON} H2b; {FIGS}/*.json labels.caption",
             fields=("H2b_pass", "count", "n_weeks", "every_baseline"),
             regenerated_file=f"{FIGS}/fig4v2.json, table3_v2.json labels.caption; the captions of {FIGS}/*.json",
             compute=_c_h2b),
    ]
    for it in R_ITEMS:
        rows.append(Spec(it.id, "R", it.source, "property", claim=f"{it.item}: the table covers its scope",
                         label=None, label_note="reported with no threshold, or as measured (§6)",
                         reference="the scope derived from the summaries and analysis.json",
                         reference_file=f"{CONF}/<part>/summary.json; {ANALYSIS_JSON}",
                         fields=("table_exists", "required", "uncovered")
                         + (("data_rows", "data_sha256_equal") if it.data else ()),
                         regenerated_file=f"{TABLES_DIR}/{it.table}; {FIGS}/{it.figure}.json tables.{it.table}.scope",
                         compute=lambda inp, x=it: _r(inp, x)))
    rows.append(Spec("D-1", "D", "prereg §7", "property",
                     claim="ms5b_deviations.tex lists exactly the deviations that the pre-registration's §7 names "
                           "(B1, B2, B3, B5, B12, B13, C2), each with its text",
                     label=None, label_note="the deviations reported with their reasons (prereg §7)",
                     reference="the pre-registration's §7 items", reference_file=f"{PREREG} §7",
                     fields=("registered", "listed", "#text_differs"), regenerated_file=DEVIATIONS, compute=_d1))
    for i, (name, script, module) in enumerate(F_ENTRIES, 1):
        rows.append(Spec(f"F-{i}", "F", "W10", "reproduction",
                         claim=f"{name}: the build on the root equals its versioned extract, and the runs/ files it "
                               "lists have the recorded sha256",
                         label=None, label_note="the provenance of a figure or float (W10)",
                         reference=f"the versioned extract {FIGS}/{name}.json", reference_file=script,
                         fields=("equal", "sources_equal", "n_runs_listed", "n_runs_sources", "#runs_unlisted",
                                 "#runs_sha256_differ"),
                         regenerated_file=f"{module}.build on the root (this report)",
                         compute=lambda inp, n=name, s=script, m=module: _f(inp, n, s, m)))
    rows += [
        Spec("FL-1", "FL", "W5, W14", "informative", claim="the heights of the v2 floats against their budgets",
             label=None, label_note="the page arithmetic (W14), informative",
             reference="BUDGETS_MS5B of floats_heights.py", reference_file="paper/layout_check/pageplan/"
                                                                          "floats_heights.py",
             fields=("floats.*.measured_pages", "floats.*.budget_pages"), regenerated_file=FLOATS_MS5B, compute=_fl1),
        Spec("RB-1", "RB", "W15", "property",
             claim="the MS5b exit rebuild: CHECK=1 in a clean clone, every output identical, the three float-height "
                   "measurements equal, the record current and its entries today's list",
             label=None, label_note="the frozen rebuild (W15 item 5)",
             reference="every output byte-identical; heights equal; today's rebuild list",
             reference_file="code/sim/figs/rebuild.py",
             fields=("mode", "git_revision", "n_outputs", "n_identical", "heights_equal", "#problems"),
             regenerated_file=f"{REBUILD} (read by this report)", compute=_rb1),
    ]
    return tuple(rows)


# ---------------------------------------------------------------- verdicts and rows
READS_SUMMARIES = ("G", "A", "H", "C", "R")          # groups whose rows read the summaries or analysis.json


def verdict(kind: str, status: Optional[str], explainable: bool = False) -> tuple[str, Optional[str]]:
    """(verdict, note) of a row's computed status: pass gives reproduced or holds by kind; explained only on an H row
    (the consequence rule); informative on the informative row, a consequence row whose hypothesis held, and H6
    without a threshold; fail and malformed inputs give bug; missing and pending stay."""
    if status == "pass":
        return ("reproduced" if kind == "reproduction" else "informative" if kind == "informative" else "holds"), None
    if status in ("fail", "bug_input"):
        return "bug", None
    if status == "explained":
        return ("explained", None) if explainable else ("bug", "status 'explained' on a row W11 does not let be "
                                                               "explained")
    if status == "informative":
        return ("informative", None) if kind in ("informative", "consequence", "hypothesis") else \
            ("bug", "status 'informative' where W11 sets a pass condition")
    if status in ("missing", "pending"):
        return status, None
    return "bug", f"status {status!r} outside the vocabulary"


def build_row(spec: Spec, inp) -> dict:
    """One row of the report for `spec` (module docstring, rows[])."""
    entry = spec.compute(inp)
    reduced = bool(entry.pop("_reduced", False)) or (spec.group in READS_SUMMARIES and bool(_reduced(inp)))
    status = entry.get("status")
    v, vnote = verdict(spec.kind, status, spec.explainable)
    expl = entry.get("explanation") if v == "explained" else None
    if v == "explained" and not expl:
        v, vnote = "bug", "explained without a text"
    notes = [x for x in (entry.get("_note"), vnote) if x]
    if status == "fail" and not notes:
        notes.append("the computed check fails")
    if status in ("missing", "pending") and not notes:
        notes.append("no reason recorded")
    if reduced:
        v, expl = "bug", None
        red = _reduced(inp)
        notes.insert(0, f"{', '.join(red) or 'an extract it reads'} from a reduced run (meta.reduced true; smoke), "
                        "never a result")
    return {"id": spec.id, "group": spec.group, "section": spec.section, "kind": spec.kind,
            "claim": {"spec": spec.claim, "summary": entry.get("claim") if isinstance(entry.get("claim"), str)
                      else None},
            "status_label": spec.label, "status_label_note": spec.label_note if spec.label is None else None,
            "reference": {"value": spec.reference, "values": m4c._values(entry, spec.ref_fields),
                          "file": spec.reference_file},
            "regenerated": {"value": m4c._values(entry, spec.fields), "file": spec.regenerated_file},
            "summary_status": None if status == "bug_input" else status, "verdict": v, "explanation": expl,
            "note": "; ".join(dict.fromkeys(notes)) or None}


def _row_or_bug(spec: Spec, inp) -> dict:
    """build_row, or, where an input has a shape the drivers never write and reading it raises, a 'bug' row that
    names the error, so that the report is still written."""
    try:
        return build_row(spec, inp)
    except Exception as err:
        return {"id": spec.id, "group": spec.group, "section": spec.section, "kind": spec.kind,
                "claim": {"spec": spec.claim, "summary": None}, "status_label": spec.label,
                "status_label_note": spec.label_note if spec.label is None else None,
                "reference": {"value": spec.reference, "values": {}, "file": spec.reference_file},
                "regenerated": {"value": {}, "file": spec.regenerated_file},
                "summary_status": None, "verdict": "bug", "explanation": None,
                "note": f"the row's input has a shape the drivers do not write ({type(err).__name__}: {err})"[:300]}


def criterion(rows: list) -> dict:
    """W11 (ms3_claims.criterion): no bug, no missing row, every non-passing row explained with text."""
    return m3.criterion(rows)


# ---------------------------------------------------------------- blocks
def _jobs(inp) -> dict:
    if "jobs" not in inp.cache:
        inp.cache["jobs"] = jobs_block(inp)
    return inp.cache["jobs"]


def jobs_block(inp) -> dict:
    """Every listed job of the six parts (manifest.json `jobs`, plus the records 'e7h:manifest' and 'e7h:summary')
    against its record jobs/<id>.json (only 'ok' counts as done): the jobs by status ('no record' where the record is
    absent), the jobs without an 'ok' record outside Q39's rule ('blocking'), and the MILP jobs of part e3 whose LB
    falls back to the LP under that rule (ms4_claims.LB_MILP_PREFIXES, status wall_limit or oom_at_3G)."""
    rows = {}
    for part in PARTS:
        man_rel = MANIFESTS[part]
        M, prob = inp.load(man_rel)
        e = {"manifest": man_rel, "present": M is not None, "n_listed": None, "by_status": {}, "n_blocking": None,
             "blocking": [], "n_milp_lp_fallback": None, "milp_lp_fallback": [], "n_unlisted_records": None,
             "n_unreadable_records": None}
        if M is None:
            e["note"] = f"{man_rel} {prob}"
            rows[part] = e
            continue
        listed = [(_d(j).get("id"), _d(j).get("kind")) for j in _l(M.get("jobs"))]
        listed += [(mc.job_id(m5.DRIVER_EXP, "manifest"), "pool"), (mc.job_id(m5.DRIVER_EXP, "summary"), "pool")]
        recs, bad = m3._job_statuses(inp.root / CONF / part)
        by_status: dict = {}
        blocking, fallback = [], []
        for jid, kind in listed:
            st = recs.get(jid, "no record") if isinstance(jid, str) else "no job id"
            by_status[st] = by_status.get(st, 0) + 1
            if st == "ok":
                continue
            item = {"job": jid, "kind": kind, "status": st}
            lb_job = kind == "milp" and isinstance(jid, str) and jid.startswith(m4c.LB_MILP_PREFIXES)
            (fallback if lb_job and st in m3.MILP_LP_FALLBACK else blocking).append(item)
        ids = {j for j, _ in listed}
        e.update(n_listed=len(listed) - 2, by_status=dict(sorted(by_status.items())), n_blocking=len(blocking),
                 blocking=blocking[:m3.JOBS_LIST_MAX], n_milp_lp_fallback=len(fallback),
                 milp_lp_fallback=fallback[:m3.JOBS_LIST_MAX], n_unlisted_records=sum(1 for j in recs if j not in ids),
                 n_unreadable_records=bad)
        rows[part] = e
    n_block = sum(r["n_blocking"] or 0 for r in rows.values())
    absent = [k for k, r in rows.items() if not r["present"]]
    note = (f"{n_block} listed job(s) without an 'ok' record outside Q39's MILP rule" if n_block else
            "every listed job has an 'ok' record, or is a MILP job whose LB is the LP under Q39's rule")
    if len(absent) == len(rows):
        note = f"no job list (manifest.json) for {', '.join(absent)}"
    elif absent:
        note += f"; no job list for {', '.join(absent)}"
    return {"rows": rows, "n_blocking": n_block, "note": note}


def copy_block(inp) -> dict:
    """ms5_claims.copy_block on the record of out/sublet_v2 (ms3_copy_sublet_v2.json)."""
    return c5.copy_block(inp, exps=(m5.CONF_DIR,))


def rebuild_block(inp) -> dict:
    return c5.rebuild_block(inp)


def captions_block(inp, extracts: Path) -> dict:
    """The caption drafts of the MS5b figures and Table III v2 (W1, W2, W4): each extract's data.labels.caption (else
    data.caption), a draft from a reduced run noted."""
    out = {}
    same = Path(extracts).resolve() == (inp.root / FIGS).resolve()
    for name, _, _ in F_ENTRIES:
        p = Path(extracts) / f"{name}.json"
        P, prob = inp.load(f"{FIGS}/{name}.json") if same else c5._load_abs(p)
        text = _caption(P)
        red = _ext_reduced(P)
        notes = []
        if P is None:
            notes.append(f"{p} {prob}")
        elif text is None:
            notes.append("the extract has no caption draft")
        if red:
            notes.append("drafted from a reduced run (never a result)")
        out[name] = {"text": text, "n_chars": len(text) if text else None, "reduced": red, "source": str(p),
                     "notes": notes}
    return out


def figure_scripts() -> list[tuple[str, str, str]]:
    """(figure name, module, script relative to code/sim) of the eight MS5b figure scripts (MS5B_SCRIPTS' order);
    Table III v2 is a float and is not rerun."""
    return [(n, m, str(Path(s).relative_to("code/sim"))) for n, s, m in F_ENTRIES if n in _RB.MS5B_SCRIPTS]


def figures_block(root: Path, extracts: Path, only=None) -> dict:
    """ms4_claims.figures_block on the MS5b figure scripts: each rerun with --from-extract <extracts>/<name>.json in
    this process, every output in a temporary folder that is removed afterwards; a script not yet written is an
    'error' row."""
    return m4c.figures_block(root, extracts, only, scripts=figure_scripts())


# ---------------------------------------------------------------- the report
def build(root=None, *, figures: bool = True, only=None, extracts=None) -> dict:
    """The report (module docstring, ms5b_claims.json) from the files under the input root."""
    root = Path(root).resolve() if root is not None else m3._default_root()
    inp = _Inputs(root)
    rows = [inp.row(s.id) for s in SPECS]
    crit = criterion(rows)
    cp = copy_block(inp)
    jb = _jobs(inp)
    rb = rebuild_block(inp)
    ex = Path(extracts).resolve() if extracts is not None else root / FIGS
    cap = captions_block(inp, ex)
    fg = figures_block(root, ex, only) if figures else \
        {"run": False, "extracts": str(ex), "rows": [], "counts": {}, "note": "not run (--no-figures)"}
    meta = {"module": "sublet.experiments.ms5b_claims", "spec": f"{SPEC_DOC} §11 (W11, W15)",
            "git_revision": mc.git_revision(), "written": mc._now(), "input_root": str(root),
            "input_root_is_repository": m3._is_repo(root), "inputs": dict(sorted(inp.status.items()))}
    return {"meta": meta, "criterion": crit, "rows": rows, "figures": fg, "copy_checks": cp, "jobs": jb,
            "rebuild": rb, "captions": cap}


GROUPS = {"G": "Gates and provenance", "A": "The analysis", "H": "Hypotheses", "C": "Consequences",
          "R": "Reported in full", "D": "Deviations", "F": "Figures and floats", "FL": "Float heights",
          "RB": "Rebuild"}


def markdown(rep: dict) -> str:
    """ms5b_claims.md: the head (criterion, figures, copy check, jobs, rebuild), one table per group of rows with
    their notes and explanations, then the figures' small glyphs, the copy check, the jobs, the rebuild record and
    the caption drafts."""
    fmt, kv, cell = m3._fmt, m3._kv, m3._cell
    m, c = rep["meta"], rep["criterion"]
    L = ["# MS5b claims report (design/sublet_v2.md §11, W11)", ""]
    where = "the repository" if m["input_root_is_repository"] else \
        f"`{m['input_root']}` (not the repository: a test, fixture or checkout tree)"
    L.append(f"Written {m['written']} by `{m['module']}` at revision {m['git_revision']}; inputs under {where}.")
    L.append("")
    L.append(f"**Criterion of W11: {'holds' if c['holds'] else 'does not hold'}.** {c['reasons']}.")
    L.append("")
    L.append(f"Rows: {c['n_rows']}; " + ", ".join(f"{v} {n}" for v, n in c["counts"].items()) + ".")
    L.append("")
    fg = rep["figures"]
    if fg["run"]:
        cn = fg["counts"]
        n_small = sum(1 for r in fg["rows"] if r["n_small_glyphs"])
        L.append(f"Figures (W15 item 1): {cn.get('ok', 0)} of {len(fg['rows'])} redrawn from their extracts with "
                 f"finalize() passing, {cn.get('missing', 0)} extract(s) missing, {cn.get('error', 0)} error(s); "
                 f"{n_small} figure(s) with mathtext glyphs below {m3._script_min_pt():g} pt (listed below).")
    else:
        L.append("Figures (W15 item 1): not rerun (--no-figures).")
    L.append("")
    cp = rep["copy_checks"]
    L.append("Copy check: " + "; ".join(
        f"{exp} {('pass' if e['pass'] else 'FAIL') if e['present'] else 'no record'}"
        for exp, e in cp["records"].items()) + f" ({cp['note']}).")
    L.append("")
    jb = rep["jobs"]
    L.append("Jobs: " + "; ".join(
        (f"{k} {r['n_listed']} listed, " + ", ".join(f"{st} {n}" for st, n in r["by_status"].items())
         if r["present"] else f"{k} no job list") for k, r in jb["rows"].items()) + f" ({jb['note']}).")
    L.append("")
    rb = rep["rebuild"]
    L.append(f"Rebuild (W15 item 5): {rb.get('note')}" + (f"; pass {fmt(rb.get('pass'))}" if rb["present"] else "")
             + ".")
    L.append("")
    for g in dict.fromkeys(r["group"] for r in rep["rows"]):
        rs = [r for r in rep["rows"] if r["group"] == g]
        L.append(f"## {g}: {GROUPS.get(g, g)}")
        L.append("")
        L.append("| Check | Claim | Status label | Reference (file) | Regenerated (file) | Verdict |")
        L.append("|---|---|---|---|---|---|")
        for r in rs:
            lab = r["status_label"] or f"none: {r['status_label_note']}"
            k = kv(r["reference"]["values"])
            ref = r["reference"]["value"] + (f" ({k})" if k else "")
            claim = r["claim"]["spec"] + (f" [{r['section']}]" if r["section"] else "")
            L.append("| " + " | ".join(cell(x) for x in (
                r["id"], claim, lab, f"{ref}; `{r['reference']['file']}`",
                f"{kv(r['regenerated']['value']) or '–'}; `{r['regenerated']['file']}`", f"**{r['verdict']}**"))
                + " |")
        L.append("")
        notes = [r for r in rs if r["explanation"] or r["note"] or r["claim"]["summary"]]
        for r in notes:
            bits = []
            if r["claim"]["summary"]:
                bits.append(f"registered: {r['claim']['summary']}")
            if r["explanation"]:
                bits.append(f"explained: {r['explanation']}")
            if r["note"]:
                bits.append(r["note"])
            L.append(f"- {r['id']}: " + ". ".join(b.rstrip(". ") for b in bits) + ".")
        if notes:
            L.append("")
    L.append("## Figures: small glyphs (W15 item 1)")
    L.append("")
    if fg["run"]:
        L.append(f"| Figure | Script | Status | Small glyphs | Glyphs below {m3._script_min_pt():g} pt (size, text) |")
        L.append("|---|---|---|---|---|")
        for r in fg["rows"]:
            what = ", ".join(m3._glyph(g) for g in r["small_glyphs"]) if r["status"] == "ok" else \
                (r["error"] or f"extract `{r['extract']}` missing")
            L.append("| " + " | ".join(cell(x) for x in (r["figure"], f"`{r['script']}`", r["status"],
                                                          r["n_small_glyphs"] if r["status"] == "ok" else "–",
                                                          what or "none")) + " |")
        L.append("")
        L.append(f"{fg['note']}; extracts from `{fg['extracts']}`.")
    else:
        L.append(f"{fg['note']}.")
    L.append("")
    L.append("## Copy check (§4.3)")
    L.append("")
    L.append(mc.md_table(["Folder", "Record", "Present", "Pass", "Commit", "Time", "Failed checks"],
                         [[exp, f"`{e['file']}`", fmt(e["present"]), fmt(e["pass"]), e["commit"], e["time"],
                           ", ".join(e["failed"]) or "–"] for exp, e in cp["records"].items()]).rstrip("\n"))
    L.append("")
    L.append(f"{cp['note'][0].upper() + cp['note'][1:]}.")
    L.append("")
    L.append("## Jobs (§4.5; Q39)")
    L.append("")
    L.append(mc.md_table(["Part", "Job list", "Listed", "Records by status", "Without 'ok' (blocking)",
                          "MILP, LB = LP (Q39)"],
                         [[k, f"`{r['manifest']}`", r["n_listed"], fmt(r["by_status"]) if r["present"] else "–",
                           r["n_blocking"], r["n_milp_lp_fallback"]] for k, r in jb["rows"].items()]).rstrip("\n"))
    L.append("")
    L.append(f"{jb['note'][0].upper() + jb['note'][1:]}.")
    for k, r in jb["rows"].items():
        if r["blocking"]:
            L.append("")
            L.append(f"- {k}: " + "; ".join(f"`{x['job']}` ({x['kind']}, {x['status']})" for x in r["blocking"])
                     + (f"; ... ({r['n_blocking']} in all)" if r["n_blocking"] > len(r["blocking"]) else ""))
    L.append("")
    L.append("## Rebuild record (W15 item 5)")
    L.append("")
    if rb["present"]:
        L.append(f"`{rb['file']}`: status {rb['status']}, mode {rb['mode']}, ONLY {fmt(rb['only'])}, revision "
                 f"{rb['git_revision']} (tracked files dirty: {fmt(rb['tracked_files_dirty'])}), written "
                 f"{rb['written']}; {rb['n_identical']} of {rb['n_outputs']} outputs identical over {rb['n_scripts']} "
                 f"scripts; float heights equal {fmt(rb['heights_equal'])}; hand-set files unchanged "
                 f"{fmt(rb['hand_set_ok'])}.")
    else:
        L.append(f"{rb['note']}.")
    L.append("")
    L.append("## Caption drafts (W1, W2, W4)")
    L.append("")
    for name, cp_ in rep["captions"].items():
        if cp_["text"]:
            L.append(f"{name} ({cp_['n_chars']} characters): {cp_['text']}"
                     + (f" ({'; '.join(cp_['notes'])})" if cp_["notes"] else ""))
        else:
            L.append(f"{name}: no draft ({'; '.join(cp_['notes']) or 'missing'}).")
        L.append("")
    return "\n".join(L).rstrip("\n") + "\n"


def write(rep: dict, out_dir) -> tuple[Path, Path]:
    out = Path(out_dir)
    rep["meta"]["out_dir"] = str(out.resolve())
    pj = mc.dump_json(rep, out / OUT_JSON)
    pm = mc.write_text(markdown(rep), out / OUT_MD)
    return pm, pj


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m sublet.experiments.ms5b_claims",
                                 description=__doc__.strip().split("\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", type=Path, default=None,
                    help=f"input root with the repository's layout (default {ENV_IN_ROOT}, else the repository)")
    ap.add_argument("--out-dir", type=Path, default=None,
                    help="folder of ms5b_claims.md and .json (default the repository's code/sim/out when the root is "
                         "the repository; required otherwise)")
    ap.add_argument("--no-figures", action="store_true", help="skip the figure reruns")
    ap.add_argument("--only", nargs="+", metavar="NAME", default=None, help="rerun only these figures")
    ap.add_argument("--extracts", type=Path, default=None,
                    help="folder of the figure extracts <name>.json (default <root>/code/sim/out/figs)")
    a = ap.parse_args(argv)
    root = a.root.resolve() if a.root is not None else m3._default_root()
    if a.out_dir is None:
        if not m3._is_repo(root):
            ap.error(f"--out-dir is required when the input root ({root}) is not the repository")
        a.out_dir = paths.SIM_OUT
    rep = build(root, figures=not a.no_figures, only=a.only, extracts=a.extracts)
    pm, pj = write(rep, a.out_dir)
    c, fg = rep["criterion"], rep["figures"]
    figs = (", ".join(f"{k} {v}" for k, v in fg["counts"].items()) if fg["run"] else "not run")
    print(f"[ms5b_claims] wrote {pm} and {pj}: criterion {'holds' if c['holds'] else 'does not hold'} ("
          + ", ".join(f"{v} {n}" for v, n in c["counts"].items() if n) + f"); figures: {figs}", flush=True)
    return 0


SPECS = _rows_spec()
SPEC_BY_ID = {s.id: s for s in SPECS}

if __name__ == "__main__":
    sys.exit(main())
