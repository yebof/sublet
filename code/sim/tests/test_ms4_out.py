"""Tests of the MS4 outputs (design/sim_spec_ms4.md §10, row test_ms4_out.py; marker needs_ms4_out, C19): every check
of §3.11, §4.9, §5.7, §6.9 and §7.9, read from the copied summaries (none from a reduced run), has a status the spec
allows; the claims report on these inputs lists no bug (written to tmp_path); every listed job has an 'ok' record, or
is a MILP job whose LB is the LP under Q39's rule (§2.5); every MS4 figure redraws from its extract; the copy records
out/ms3_copy_<exp>.json of e3, e4, e5, e7 and e8 pass, still match the copy (tree digests) and name one clone commit,
the one §1.2 and §11.2 record; every A8 run of E3, E5 and E7 records the B0_rule of M36 (ms4_common.B0_RULE; the
allowance sweep its own rule) and a certificate, in the summaries and, where the run files are present, in each run;
Table III's float and every MS4 figure extract are what their scripts write from the copied summaries, and the
float's measured height is that of the float.

Each test is skipped while a file it reads under code/sim/out/ is missing, i.e. until the run scripts of §3-§7 have
written their outputs in the clean clone of the MS4 runs, the outputs have been copied into the repository and the
copy checks have run (§1.2). The input root is the repository, or SUBLET_MS4_OUT_ROOT (conftest.py), a folder with the
repository's layout. On a root that holds the reduced fixture tree tests/fixtures_figs_ms4/inputs/ the tests that run
fail where the tree is reduced (meta.reduced true), as they must.
"""
import json
import math
import os
from pathlib import Path

import pytest

from fixtures import SIM

from sublet.experiments import e7
from sublet.experiments import ms3_common as mc
from sublet.experiments import ms4_claims as mcl
from sublet.experiments import ms4_common as m4

ROOT = Path(os.environ.get("SUBLET_MS4_OUT_ROOT") or SIM.parents[1])
OUT = ROOT / "code" / "sim" / "out"

# the files under code/sim/out/ that each experiment's rows read (ms4_claims: SPECS, also_reduced, E7's parts)
FILES = {
    "E7": tuple(f"e7/{p}/summary.json" for p in mcl.E7_PARTS),
    "E3": ("e3/summary.json", "e3/gate.json"),
    "E5": ("e5/summary.json",),
    "E4": ("e4/summary.json",),
    "E8": ("e8/summary.json",),
}
ALL = tuple(f for fs in FILES.values() for f in fs) + ("e7/table3.json", "figs/floats_heights_ms4.json")
FIGURES = tuple(n for n, _, _ in mcl.figure_scripts())
# the files of each copied experiment that the copy must hold (the copy check's summary_ok covers the summaries)
COPIED = {"e3": ("e3/summary.json", "e3/gate.json"), "e4": ("e4/summary.json",), "e5": ("e5/summary.json",),
          "e7": FILES["E7"] + ("e7/table3.json",), "e8": ("e8/summary.json",)}
A8_SUMMARIES = ("e7/main/summary.json", "e3/summary.json", "e5/summary.json")


def _read(rel: str) -> dict:
    d = mc.read_json(OUT / rel)
    assert d is not None, f"{OUT / rel} is not a JSON object"
    return d


def _allowed(spec) -> tuple[set, set]:
    """(summary statuses, verdicts) the spec allows for a check: pass for a reproduction or a property check,
    informative for the rows §3.11-§7.9 mark informative (no MS4 check allows 'explained')."""
    if spec.kind == "informative":
        return {"informative"}, {"informative"}
    return {"pass"}, {"reproduced" if spec.kind == "reproduction" else "holds"}


@pytest.mark.parametrize("exp", [pytest.param(e, marks=pytest.mark.needs_ms4_out(*fs)) for e, fs in FILES.items()])
def test_checks_from_the_summaries(exp):
    """Every check of the experiment: its summaries (E7's four parts, E3's with the gate record) are not reduced, the
    summary's status is one the spec allows for it (for E7 also every part entry of main's combined entry), and the
    claims report's row for it is reproduced, holds or informative, never bug, missing or pending."""
    inp = mcl.m3._Inputs(ROOT)
    specs = [s for s in mcl.SPECS if s.exp == exp]
    assert specs
    bad = []
    for rel in FILES[exp]:
        S = _read(rel)
        if (S.get("meta") or {}).get("reduced") is not False:
            bad.append(f"{rel}: meta.reduced {(S.get('meta') or {}).get('reduced')!r}, not false (a reduced run is "
                       "never a result)")
    for s in specs:
        statuses, verdicts = _allowed(s)
        S, prob = inp.load(s.summary)
        assert S is not None, f"{s.summary}: {prob}"
        e = (S.get("checks") or {}).get(s.id) or {}
        if e.get("status") not in statuses:
            bad.append(f"{s.id}: summary status {e.get('status')!r}, the spec allows {sorted(statuses)}")
        if exp == "E7":
            for p, pe in (e.get("parts") or {}).items():
                ps = (pe or {}).get("status")
                if ps not in statuses:
                    bad.append(f"{s.id}: part {p} status {ps!r}")
        row = mcl.build_row(s, inp)
        if row["verdict"] not in verdicts:
            bad.append(f"{s.id}: verdict {row['verdict']!r} ({row['note']})")
    assert not bad, "\n".join(bad)


@pytest.mark.needs_ms4_out(*ALL)
def test_claims_report_lists_no_bug(tmp_path):
    """ms4_claims on the inputs writes a report (to tmp_path) with no bug row and the criterion of §1.4 item 2
    holding; its rows are those of the spec; Table III's height is recorded next to its budget (§1.4 item 5); the
    caption drafts have their numbers."""
    rep = mcl.build(ROOT, figures=False)
    assert [r["id"] for r in rep["rows"]] == [s.id for s in mcl.SPECS]
    bugs = [f"{r['id']}: {r['note']}" for r in rep["rows"] if r["verdict"] == "bug"]
    assert not bugs, "\n".join(bugs)
    assert rep["criterion"]["bug"] == [] and rep["criterion"]["holds"], rep["criterion"]["text"]
    fl = rep["floats"]
    assert fl["present"] and [r["name"] for r in fl["rows"]] == ["table3_e7"]
    assert all(isinstance(fl["rows"][0][k], (int, float)) for k in ("measured_pages", "budget_pages"))
    assert rep["captions"]["fig4"]["text"] and rep["captions"]["fig4"]["within_limit"]
    assert rep["captions"]["table3"]["certificates"] and not rep["captions"]["table3"]["notes"]
    pm, pj = mcl.write(rep, tmp_path)
    assert "**bug**" not in pm.read_text() and pj.is_file()


@pytest.mark.needs_ms4_out(*(f"figs/{n}.json" for n in FIGURES))
def test_figures_redraw_from_their_extracts(tmp_path, monkeypatch):
    """Every MS4 figure script redraws from its extract with finalize() passing (§1.4 item 1), in a temporary
    folder."""
    import tempfile
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    fg = mcl.figures_block(ROOT, OUT / "figs")
    errs = [f"{r['figure']}: {r['status']} {r['error']}" for r in fg["rows"] if r["status"] != "ok"]
    assert len(fg["rows"]) == len(FIGURES) == 9 and not errs, "\n".join(errs)


@pytest.mark.needs_ms4_out("e7/table3.json", "figs/floats_heights_ms4.json")
def test_table3_float_is_current(monkeypatch):
    """paper/floats/table3_e7.tex is what figs/table3_e7.py writes from the copied e7/table3.json (byte for byte), and
    floats_heights_ms4.json measured that file (its sha256): a float written before a rerun, or a height measured on
    another float, fails."""
    import hashlib
    from figs import table3_e7 as t3w
    from figs.inputs import Inputs
    tex = ROOT / "paper" / "floats" / "table3_e7.tex"
    if not tex.is_file():
        pytest.skip(f"{tex} is not written yet (python -m figs.table3_e7 after the copy, §9)")
    monkeypatch.setenv("SUBLET_FIGS_IN_ROOT", str(ROOT))
    data = json.loads(json.dumps(t3w.build(Inputs()), allow_nan=False))
    assert t3w.float_tex(data) == tex.read_text(encoding="utf-8"), f"{tex} is not current: rerun figs.table3_e7"
    rec = (_read("figs/floats_heights_ms4.json").get("floats") or {}).get("table3_e7") or {}
    assert rec.get("sha256") == hashlib.sha256(tex.read_bytes()).hexdigest(), \
        "floats_heights_ms4.json measured another table3_e7.tex: rerun floats_heights.py --ms4"


@pytest.mark.parametrize("name", [pytest.param(n, marks=pytest.mark.needs_ms4_out(f"figs/{n}.json")) for n in FIGURES])
def test_figure_extracts_are_current(name, monkeypatch):
    """Each MS4 figure's extract code/sim/out/figs/<name>.json holds what its script builds from the copied
    summaries (data and sources), so that a figure drawn before a rerun, or from partial outputs, fails (as
    test_figs_ms4.py checks the fixture extracts against the fixture tree)."""
    import importlib
    from figs.common import json_number
    from figs.inputs import Inputs
    mod = dict((n, m) for n, m, _ in mcl.figure_scripts())[name]
    monkeypatch.setenv("SUBLET_FIGS_IN_ROOT", str(ROOT))
    inp = Inputs()
    data = json.loads(json.dumps(importlib.import_module(mod).build(inp), allow_nan=False, default=json_number))
    ext = _read(f"figs/{name}.json")
    assert data == ext["data"], f"code/sim/out/figs/{name}.json is not current: rerun python -m {mod}"
    assert ext["sources"] == inp.sources


@pytest.mark.parametrize("folder", [pytest.param(f, marks=pytest.mark.needs_ms4_out(f"{f}/manifest.json"))
                                    for f in mcl.JOB_FOLDERS])
def test_every_listed_job_ok(folder):
    """Every job of the folder's job list, and its '<exp>:manifest' and '<exp>:summary' records, has an 'ok' record
    (§2.4: only 'ok' counts as done); a MILP job stopped at the wall-clock limit or by the cap is allowed, its LB
    being the LP (Q39, §2.5)."""
    r = mcl.jobs_block(mcl.m3._Inputs(ROOT))["rows"][folder]
    assert r["present"] and r["n_listed"] > 0, r.get("note")
    assert r["n_blocking"] == 0 and r["n_unreadable_records"] == 0, r["blocking"]


@pytest.mark.parametrize("exp", [pytest.param(e, marks=pytest.mark.needs_ms4_out(mc.COPY_RECORD.format(exp=e)))
                                 for e in mcl.COPY_EXPS])
def test_copy_check_passed(exp):
    """The copy check of §1.2 (python -m sublet.experiments.ms3_common --check-copy EXP CLONE; E7's four parts
    through C20, E4's repro/ files without a revision) passed: equal files and sha256, no symbolic link, every JSON
    file recording the clone's commit (or one of the allowed files without a revision), the summaries present with
    'ok' summary and manifest records, no 'running' record, each part's run log with its done line; the copy is
    unchanged since (tree digests: over the versioned files, and over all files where the run files runs/ are
    present) and holds the experiment's summaries."""
    rec = mc.read_json(OUT / mc.COPY_RECORD.format(exp=exp))
    assert rec is not None and rec["exp"] == exp and rec["check"] == "copy"
    assert rec["pass"] is True and all(rec["checks"].values()), {k: v for k, v in rec["checks"].items() if not v}
    want = {"same_file_list", "same_sha256", "no_symlinks", "json_readable", "revisions", "revisions_recorded",
            "manifest_revision", "summary_ok", "no_running_records", "record_statuses_known", "run_log_done"}
    assert set(rec["checks"]) == want
    assert len(rec["clone_commit"]) == 40 and set(rec["revisions_found"]) == {rec["clone_commit"]}
    assert rec["n_running"] == 0 and all(x["done"] for x in rec["run_logs"].values())
    assert rec["parts"] == list(mc.COPY_PARTS.get(exp, ()))
    assert rec["no_revision_allowed_under"] == list(mc.COPY_NO_REVISION.get(exp, ()))
    assert rec["tree_sha256_versioned"] == mc.tree_digest(OUT / exp, exp), f"out/{exp} changed after its copy check"
    runs = [OUT / exp / p / "runs" for p in mc.COPY_PARTS.get(exp, ("",))]
    if any(r.is_dir() for r in runs):
        assert rec["tree_sha256"] == mc.tree_digest(OUT / exp), f"out/{exp} changed after its copy check: rerun it"
    missing = [f for f in COPIED[exp] if not (OUT / f).is_file()]
    assert not missing, f"files missing in the copy: {missing}"


@pytest.mark.needs_ms4_out(*(mc.COPY_RECORD.format(exp=e) for e in mcl.COPY_EXPS))
def test_copy_checks_share_one_commit():
    """The five experiments ran in one clean clone at one commit (§1.2: one clone holds every MS4 lock folder, so
    that the slot semaphore is shared, and the gate's MILP jobs are jobs of E3's grid), the commit that §11.2 of
    design/sim_spec_ms4.md records for the clone of the MS4 runs."""
    commits = {e: (mc.read_json(OUT / mc.COPY_RECORD.format(exp=e)) or {}).get("clone_commit") for e in mcl.COPY_EXPS}
    assert len(set(commits.values())) == 1 and None not in commits.values(), commits
    spec = (SIM.parents[1] / "design" / "sim_spec_ms4.md").read_text(encoding="utf-8")
    assert commits["e3"] in spec, f"the clone commit {commits['e3']} is not the one design/sim_spec_ms4.md §11.2 names"


def _parts_entry(main: dict, cid: str) -> dict:
    return ((main.get("checks") or {}).get(cid) or {}).get("parts") or {}


@pytest.mark.needs_ms4_out(*dict.fromkeys(A8_SUMMARIES + FILES["E7"]))
def test_a8_runs_record_b0_rule_and_a_certificate():
    """Every A8 run of E3, E5 and E7, as the summaries count them: E7-6's rules found in every part outside the
    allowance sweep are ms4_common.B0_RULE alone and the sweep's are its own (B0_RULE among them), with no failure;
    E7-1 counts one available certificate per A8 run in every part; E3's B0_rule is B0_RULE and E3-5 counts no
    unavailable certificate; E5-5's B0_rules are B0_RULE for every Sublet run, with none unavailable or lost."""
    main = _read("e7/main/summary.json")
    rules = _parts_entry(main, "E7-6")
    assert set(rules) == set(mcl.E7_PARTS), rules
    for p, e in rules.items():
        assert e.get("n_failures") == 0 and e.get("status") == "pass", (p, e.get("failures"))
        if p == "allow":
            sweep = {m4.THEORY_RULE if s == "auto" else f"{mc.num_key(float(s))}*BL0a" for s in e7.ALLOW_B0}
            assert m4.B0_RULE in e["rules_found"] and set(e["rules_found"]) <= sweep, e["rules_found"]
        else:
            assert e["rules_found"] == [m4.B0_RULE], (p, e["rules_found"])
    for p, e in _parts_entry(main, "E7-1").items():
        cert = e.get("certificates") or {}
        assert e.get("n_unavailable") == 0 and cert.get("n") == e.get("n_runs") > 0, (p, e)
    e3 = _read("e3/summary.json")
    assert e3["meta"]["B0_rule"] == m4.B0_RULE
    c = e3["checks"]["E3-5"]
    assert c["n"] > 0 and c["by_case"]["unavailable"]["runs"] == 0 and c["n_failures"] == 0
    c = _read("e5/summary.json")["checks"]["E5-5"]
    assert c["B0_rules"] == {m4.B0_RULE: c["runs"]} and c["runs"] > 0
    assert c["unavailable"] == 0 and c["n_runs_lost"] == 0


def _a8_records(exp: str, path: Path) -> list:
    """(label, record, expected B0_rule) of every A8 run in one run file of E3, E5 or E7: E7's runs[i].a8 of an A8
    file (the allowance sweep's rule from the file's b0), E3's Sublet runs and every sub-run of its Sublet-siloed
    runs, E5's runs of an A8 file."""
    d = json.loads(path.read_text())
    out = []
    if exp == "e7":
        if d.get("policy_id") != "A8":
            return out
        b0 = d.get("b0")
        want = m4.B0_RULE if b0 is None else m4.THEORY_RULE if b0 == "auto" else f"{mc.num_key(float(b0))}*BL0a"
        for i, r in enumerate(d.get("runs") or []):
            out.append((f"{path.name} runs[{i}]", r.get("a8"), want))
    elif exp == "e3":
        for i, r in enumerate(d.get("runs") or []):
            if r.get("policy_id") == "A8":
                out.append((f"{path.name} runs[{i}] ({r.get('tag')})", r, m4.B0_RULE))
            elif r.get("policy_id") == "SILOED" and r.get("inner_id") == "A8":
                out += [(f"{path.name} runs[{i}] ({r.get('tag')}) sub_runs[{j}]", s, m4.B0_RULE)
                        for j, s in enumerate(r.get("sub_runs") or [])]
    elif d.get("policy_id") == "A8":
        out += [(f"{path.name} runs[{i}]", r, m4.B0_RULE) for i, r in enumerate(d.get("runs") or [])]
    return out


@pytest.mark.needs_ms4_out("e3/manifest.json", "e5/manifest.json", *(f"e7/{p}/manifest.json" for p in mcl.E7_PARTS))
def test_a8_run_files_record_b0_rule_and_a_certificate():
    """Where the run files are present (runs/ is not versioned: on the host of the runs, after the copy), every A8 run
    of E3 (Sublet and every Sublet-siloed sub-run), E5 and E7 records B0_rule ms4_common.B0_RULE (the sweep's runs
    their own rule), B0_usd = B0_SHARE x bl0a_usd under that rule (1e-12 relative), gamma 1, kappa null outside the
    theory point, and an available certificate with its case."""
    folders = {"e3": [OUT / "e3" / "runs" / "cells"], "e5": [OUT / "e5" / "runs"],
               "e7": [OUT / "e7" / p / "runs" for p in mcl.E7_PARTS]}
    if not any(d.is_dir() for ds in folders.values() for d in ds):
        pytest.skip(f"no run files under {OUT} (runs/ is not versioned; present on the host of the runs)")
    bad, n = [], {e: 0 for e in folders}
    for exp, dirs in folders.items():
        for d in dirs:
            for path in sorted(d.glob("*.json")) if d.is_dir() else []:
                for label, r, want in _a8_records(exp, path):
                    n[exp] += 1
                    r = r if isinstance(r, dict) else {}
                    cert = r.get("certificate") if isinstance(r.get("certificate"), dict) else {}
                    if r.get("B0_rule") != want:
                        bad.append(f"{exp} {label}: B0_rule {r.get('B0_rule')!r}, not {want!r}")
                    if want == m4.B0_RULE and not (isinstance(r.get("B0_usd"), float) and isinstance(
                            r.get("bl0a_usd"), float) and math.isclose(r["B0_usd"], m4.B0_SHARE * r["bl0a_usd"],
                                                                       rel_tol=m4.SHARE_TOL, abs_tol=0.0)):
                        bad.append(f"{exp} {label}: B0_usd {r.get('B0_usd')!r} is not {m4.B0_SHARE} x bl0a_usd")
                    if r.get("gamma") != m4.GAMMA or (want != m4.THEORY_RULE and r.get("kappa") is not None):
                        bad.append(f"{exp} {label}: gamma {r.get('gamma')!r}, kappa {r.get('kappa')!r}")
                    if cert.get("available") is not True or r.get("certificate_case") not in m4.CASES[:3]:
                        bad.append(f"{exp} {label}: certificate available {cert.get('available')!r}, case "
                                   f"{r.get('certificate_case')!r}")
    assert all(n[e] > 0 for e in n if any(d.is_dir() for d in folders[e])), n
    assert not bad, "\n".join(bad[:50])
