"""Tests of the MS3 outputs (design/sim_spec_ms3.md §10, row test_ms3_out.py; marker needs_ms3_out): every check of
§3.3, §4.6, §5.5, §6.9 and §7.3, read from the real summaries (none from a reduced run), passes or is explained,
informative or 'elsewhere' as the spec allows; the claims report on these inputs lists no bug (written to tmp_path);
every listed job has an 'ok' record, or is a MILP job whose LB is the LP under Q39's rule (§2.5); the figure
scripts redraw from their extracts; the copy checks out/ms3_copy_<exp>.json pass, still match the copy (tree
digests), name the experiment's summaries, and all four ran on one clone commit.

Each test is skipped while a file it reads under code/sim/out/ is missing, i.e. until the run scripts of §4-§7 have
written their outputs in the clone of the MS3 runs, the outputs have been copied into the repository and the copy
checks have run (§1.2); the E11 case reads the versioned E11 files and runs already. The input root is the
repository, or SUBLET_MS3_OUT_ROOT (conftest.py), a folder with the repository's layout.
"""
import os
from pathlib import Path

import pytest

from fixtures import SIM

from sublet.experiments import ms3_claims as mcl
from sublet.experiments import ms3_common as mc

ROOT = Path(os.environ.get("SUBLET_MS3_OUT_ROOT") or SIM.parents[1])
OUT = ROOT / "code" / "sim" / "out"

# the files under code/sim/out/ that each experiment's rows read (ms3_claims: SPECS, the computed rows)
FILES = {
    "E11": ("ms3_e11_0.json", "e11/summary.json", "figs/fig1.json", "figs/fig3.json", "q44_study/summary.json"),
    "E1": ("e1/summary.json", "figs/fig2.json"),
    "E10": ("e10/summary.json",),
    "E2": ("e2/summary.json",),
    "E6": ("e6/a/summary.json", "e6/b/summary.json"),
}
ALL = tuple(f for fs in FILES.values() for f in fs) + ("figs/floats_heights.json",)
FIGURES = tuple(n for n, _, _ in mcl.figure_scripts())
# the summaries of each copied experiment (the copy check's summary_ok; E1's fig2.json is drawn after the copy)
SUMMARIES = {"e1": ("e1/summary.json",), "e10": ("e10/summary.json",), "e2": ("e2/summary.json",),
             "e6": ("e6/a/summary.json", "e6/b/summary.json")}


def _allowed(spec) -> tuple[set, set]:
    """(summary statuses, verdicts) the spec allows for a check: pass for a reproduction or a property check
    (explained too for E2-5, §6.9), informative for the rows §3.3-§7.3 mark informative; E1-1's summary status is
    'elsewhere' (§4.6), resolved from figs/fig2.json."""
    if spec.kind == "informative":
        return {"informative"}, {"informative"}
    statuses = {"pass", "explained"} if spec.explainable else {"pass"}
    verdicts = {"reproduced" if spec.kind == "reproduction" else "holds"} | ({"explained"} if spec.explainable
                                                                          else set())
    return statuses, verdicts


@pytest.mark.parametrize("exp", [pytest.param(e, marks=pytest.mark.needs_ms3_out(*fs)) for e, fs in FILES.items()])
def test_checks_from_the_summaries(exp):
    """Every check of the experiment: the summary's status is one the spec allows for it, and the claims report's
    row for it is reproduced, holds, informative or explained (with its text), never bug, missing or pending."""
    inp = mcl._Inputs(ROOT)
    specs = [s for s in mcl.SPECS if s.exp == exp]
    assert specs
    bad = []
    for rel in sorted({s.summary for s in specs if s.summary}):
        S, prob = inp.load(rel)
        assert S is not None, f"{rel}: {prob}"
        if (S.get("meta") or {}).get("reduced") is not False:
            bad.append(f"{rel}: meta.reduced {(S.get('meta') or {}).get('reduced')!r}, not false (a reduced run is "
                       "never a result)")
    for s in specs:
        statuses, verdicts = _allowed(s)
        if s.compute is None:
            S, prob = inp.load(s.summary)
            assert S is not None, f"{s.summary}: {prob}"
            st = ((S.get("checks") or {}).get(s.id) or {}).get("status")
            if st not in statuses:
                bad.append(f"{s.id}: summary status {st!r}, the spec allows {sorted(statuses)}")
        elif s.id == "E1-1":
            S, _ = inp.load(mcl.E1_SUM)
            st = ((S.get("checks") or {}).get("E1-1") or {}).get("status")
            if st != "elsewhere":
                bad.append(f"E1-1: summary status {st!r}, not 'elsewhere' (§4.6)")
        row = mcl.build_row(s, inp)
        if row["verdict"] not in verdicts:
            bad.append(f"{s.id}: verdict {row['verdict']!r} ({row['note']})")
        if row["verdict"] == "explained" and not row["explanation"]:
            bad.append(f"{s.id}: explained without a text")
    assert not bad, "\n".join(bad)


@pytest.mark.needs_ms3_out(*ALL)
def test_claims_report_lists_no_bug(tmp_path):
    """ms3_claims on the inputs writes a report (to tmp_path) with no bug row; its rows are those of the spec."""
    rep = mcl.build(ROOT, figures=False)
    assert [r["id"] for r in rep["rows"]] == [s.id for s in mcl.SPECS]
    bugs = [f"{r['id']}: {r['note']}" for r in rep["rows"] if r["verdict"] == "bug"]
    assert not bugs, "\n".join(bugs)
    assert rep["criterion"]["bug"] == [] and rep["floats"]["present"]
    pm, pj = mcl.write(rep, tmp_path)
    assert "**bug**" not in pm.read_text() and pj.is_file()


@pytest.mark.needs_ms3_out(*(f"figs/{n}.json" for n in FIGURES))
def test_figures_redraw_from_their_extracts(tmp_path, monkeypatch):
    """Every figure script redraws from its extract with finalize() passing (§1.4 item 1), in a temporary folder."""
    import tempfile
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    fg = mcl.figures_block(ROOT, OUT / "figs")
    errs = [f"{r['figure']}: {r['status']} {r['error']}" for r in fg["rows"] if r["status"] != "ok"]
    assert len(fg["rows"]) == 20 and not errs, "\n".join(errs)


@pytest.mark.parametrize("folder", [pytest.param(f, marks=pytest.mark.needs_ms3_out(f"{f}/manifest.json"))
                                    for f in mcl.JOB_FOLDERS])
def test_every_listed_job_ok(folder):
    """Every job of the folder's job list, and its '<exp>:manifest' and '<exp>:summary' records, has an 'ok' record
    (§2.4: only 'ok' counts as done; a summary built from a partial job set marks its checks over the runs that
    exist); a MILP job stopped at the wall-clock limit or by the cap is allowed, its LB being the LP (Q39, §2.5)."""
    r = mcl.jobs_block(mcl._Inputs(ROOT))["rows"][folder]
    assert r["present"] and r["n_listed"] > 0, r.get("note")
    assert r["n_blocking"] == 0 and r["n_unreadable_records"] == 0, r["blocking"]


@pytest.mark.parametrize("exp", [pytest.param(e, marks=pytest.mark.needs_ms3_out(mc.COPY_RECORD.format(exp=e)))
                                 for e in mcl.COPY_EXPS])
def test_copy_check_passed(exp):
    """The copy check of §1.2 (python -m sublet.experiments.ms3_common --check-copy EXP CLONE) passed: equal files
    and sha256, no symbolic link, every JSON file recording the clone's commit (or one of the allowed files without
    a revision), the summaries present with 'ok' summary and manifest records, no 'running' record, the run log's
    done line; the copy is unchanged since (its tree digests equal the record's: over the versioned files, and over
    all files where the run files runs/, not versioned, are present) and its summaries exist (a missing summary
    fails here rather than skipping the other tests)."""
    rec = mc.read_json(OUT / mc.COPY_RECORD.format(exp=exp))
    assert rec is not None and rec["exp"] == exp and rec["check"] == "copy"
    assert rec["pass"] is True and all(rec["checks"].values()), {k: v for k, v in rec["checks"].items() if not v}
    want = {"same_file_list", "same_sha256", "no_symlinks", "json_readable", "revisions", "revisions_recorded",
            "manifest_revision", "summary_ok", "no_running_records", "record_statuses_known", "run_log_done"}
    assert set(rec["checks"]) == want
    assert len(rec["clone_commit"]) == 40 and set(rec["revisions_found"]) == {rec["clone_commit"]}
    assert rec["n_running"] == 0 and all(x["done"] for x in rec["run_logs"].values())
    assert rec["parts"] == list(mc.COPY_PARTS.get(exp, ()))
    # the versioned files always; all files where the unversioned run files are present (the host of the runs)
    assert rec["tree_sha256_versioned"] == mc.tree_digest(OUT / exp, exp), f"out/{exp} changed after its copy check"
    runs = [OUT / exp / p / "runs" for p in mc.COPY_PARTS.get(exp, ("",))]
    if any(r.is_dir() for r in runs):
        assert rec["tree_sha256"] == mc.tree_digest(OUT / exp), f"out/{exp} changed after its copy check: rerun it"
    missing = [f for f in SUMMARIES[exp] if not (OUT / f).is_file()]
    assert not missing, f"summaries missing in the copy: {missing}"


@pytest.mark.needs_ms3_out(*(mc.COPY_RECORD.format(exp=e) for e in mcl.COPY_EXPS))
def test_copy_checks_share_one_commit():
    """The four experiments ran in one clone at one commit (E1-7 reads E10's repro.json, E6(a) E2's run files),
    the commit that §1.2 records for the clone of the MS3 runs."""
    commits = {e: (mc.read_json(OUT / mc.COPY_RECORD.format(exp=e)) or {}).get("clone_commit") for e in mcl.COPY_EXPS}
    assert len(set(commits.values())) == 1, commits
    spec = (SIM.parents[1] / "design" / "sim_spec_ms3.md").read_text(encoding="utf-8")
    assert commits["e1"] in spec, f"the clone commit {commits['e1']} is not the one design/sim_spec_ms3.md §1.2 names"


@pytest.mark.needs_ms3_out("figs/sf_e2_mu_ep.json", "e2/game.json")
def test_sf_e2_mu_ep_extract_draws_the_game_threshold():
    """M66 on the real extract: in every panel of sf_e2_mu_ep the H*_mu vertical is e2/game.json's
    meta.hstar.<mu>.<lambda_default>.H_min, a11's full-model value is kept beside it and not drawn, and H*_beta is
    a11's (M25); the fixture test in test_figs_ms3_exp.py checks the same on the synthetic inputs only."""
    import json
    rd = lambda p: json.loads((ROOT / p).read_text())                         # noqa: E731
    data = rd("code/sim/out/figs/sf_e2_mu_ep.json")["data"]
    game, por = rd("code/sim/out/e2/game.json"), rd("code/theory_checks/c2/out/por_default.json")
    tier = rd("code/analysis/out/a11_calibration.json")["table_3_8_by_tier"]["values"]["maas_a10"]["M"]["a5_2GBps"]
    lam = format(float(por["inputs"]["lambda_default"]), "g")
    assert [p["mu"] for p in data["panels"]] == [0.2, 0.5, 2.0]
    for p in data["panels"]:
        game_h = game["meta"]["hstar"][format(p["mu"], "g")][lam]["H_min"]
        assert p["verticals"] == {"H_star_mu_min": game_h, "H_star_beta_min": tier["H_star_beta_s"] / 60.0}
        assert p["H_star_mu_full_model_min"] == tier["H_star_mu_s"][str(float(p["mu"]))] / 60.0
