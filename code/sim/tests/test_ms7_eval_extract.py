"""Tests of the MS7 Section VI-C and VII extract figs/ms7_eval_extract.py and its output
code/sim/out/ms7/eval_extract.json (design/ms7/w_spec.md, unit W-X).

Quick (versioned JSON inputs only; under a second each except the copies of the check tests):
- the extract's parts econ, guard, allowance and fam_f3, recomputed by the script's functions on the repository's
  versioned inputs, equal the versioned extract (it is not stale), and every input listed under meta.inputs exists
  with the recorded sha256;
- an independent recomputation by another code path: the total-accounting saving, the USD saving and the margin over
  the cheapest primary baseline from part main's ledger totals (ALG) plus Fig. 4 v2's own capacity; the guarded week
  runs and their S-on-FB count and the range of Sublet's B(T) from the guarded records alone; Sublet's F3 runs and
  aborts against sf_e7_decomp's H3 table; alpha_N from its formula on the recorded m, K and N, and week 301's N
  against the driver input N_bound that design/sublet_v2_prereg.md resolved for Sublet;
- every key the value registry is to read (REGISTRY_KEYS) resolves to a number;
- the script exits 2 when an input is missing (empty --root) and 1 when a check fails (a copy of the inputs with one
  Sublet F3 abort moved off slot 0, and one with a guarded week run whose S left FB), writing nothing and naming
  the failed check on stderr.
With the a12 outputs (needs_a12; the week instances' inputs are versioned, no raw trace; about 3 s): two week
instances rebuilt by the script's week_instances equal the extract's by_week entries (with their instance_hash
checked against part main's job records), and the recorded planner check of Sublet's safe expert holds.
"""
from __future__ import annotations

import hashlib
import json
import math
import shutil
import statistics
from pathlib import Path

import pytest

from fixtures import SIM

from figs import ms7_eval_extract as X

REPO = SIM.parents[1]
OUT = REPO / "code/sim/out/ms7/eval_extract.json"
STALE = ("code/sim/out/ms7/eval_extract.json is stale: rerun code/sim/figs/ms7_eval_extract.py (3G cap) from the "
         "repository root")
# the keys the integrator registers in paper/values (design/ms7/w_spec.md §3 Values); each must be a number
REGISTRY_KEYS = (
    "econ.own_capacity_usd.median", "econ.saving_vs_fallback.pct_total.median",
    "econ.saving_vs_fallback.pct_total.min", "econ.saving_vs_fallback.pct_total.max",
    "econ.saving_vs_fallback.usd.median", "econ.margin_vs_cheapest_primary.usd.median",
    "econ.margin_vs_cheapest_primary.usd.min", "econ.margin_vs_cheapest_primary.usd.max",
    "econ.margin_vs_cheapest_primary.weeks_positive", "econ.n_weeks",
    "guard.week.runs", "guard.week.s_fb_all", "guard.week_main.runs", "guard.sublet_week.runs",
    "allowance.sublet_week.B_T.min", "allowance.sublet_week.B_T.max", "allowance.sublet_week.B_T.min_floor",
    "allowance.sublet_week.B_T.max_ceil",
    "fam_f3.by_tag.Sublet.runs", "fam_f3.by_tag.Sublet.aborts", "fam_f3.by_tag.Sublet.abort_slot_min",
    "fam_f3.by_tag.Sublet.abort_slot_max", "fam_f3.by_tag.Sublet.aborts_at_slot0",
    "alpha_N.m", "alpha_N.K", "alpha_N.N.min", "alpha_N.N.max", "alpha_N.value.min", "alpha_N.value.max",
    "alpha_N.rbar.min", "alpha_N.rbar.max", "alpha_N.rho.min", "alpha_N.rho.max",
)


@pytest.fixture(scope="module")
def extract() -> dict:
    return json.loads(OUT.read_text(encoding="utf-8"))


def _jsonish(x):
    return json.loads(json.dumps(x))


def _get(d, path: str):
    for k in path.split("."):
        d = d[k]
    return d


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


# ---------------------------------------------------------------- the versioned extract is current
def test_json_parts_equal_a_recomputation(extract):
    rd = X.Reader(REPO)
    g = X._guarded(rd)
    got = {"econ": X.economics(rd), "guard": X.guard(rd, g), "allowance": X.allowance(g), "fam_f3": X.fam_f3(rd, g)}
    for part, v in got.items():
        assert _jsonish(v) == extract[part], f"{part}: {STALE}"


def test_inputs_recorded_with_their_sha256(extract):
    inputs = extract["meta"]["inputs"]
    for rel in (X.TABLE3, X.FIG4V2, X.ANALYSIS, *X.SUMMARY.values(), *X.BUILD_INPUTS):
        assert rel in inputs, f"{rel} is not recorded under meta.inputs"
    for rel, h in inputs.items():
        p = Path(rel) if rel.startswith("/") else REPO / rel
        assert p.is_file(), f"recorded input {rel} is missing"
        assert _sha(p) == h, f"{rel} changed since the extract was written: {STALE}"
    assert not any(rel.startswith("/mnt/data") for rel in inputs), "the week instances read a raw trace"


def test_registry_keys_are_numbers(extract):
    for k in REGISTRY_KEYS:
        v = _get(extract, k)
        assert isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v), k


# ---------------------------------------------------------------- independent recomputation
def test_economics_from_the_ledger_totals(extract):
    main = json.loads((REPO / X.SUMMARY["main"]).read_text())
    own = json.loads((REPO / X.FIG4V2).read_text())["data"]["a"]["own_capacity_usd"]["by_week"]
    primary = json.loads((REPO / X.ANALYSIS).read_text())["H2"]["set"]
    alg = {(r["tag"], r["cell"]): (r["ALG"], r["bl0a_usd"]) for r in main["runs"]
           if r["kind"] == "week" and r["mode"] == "L-tr" and r["seed"] == 0}
    weeks = sorted({c for _t, c in alg}, key=int)
    assert weeks == extract["econ"]["weeks"]
    pct, usd, mar = [], [], []
    for w in weeks:
        s, f = alg[("Sublet", w)][0] + own[w], alg[("Sublet", w)][1] + own[w]
        best = min(alg[(t, w)][0] for t in primary) + own[w]
        pct.append(100.0 * (f - s) / f)
        usd.append(f - s)
        mar.append(best - s)
    e = extract["econ"]
    assert statistics.median(pct) == pytest.approx(e["saving_vs_fallback"]["pct_total"]["median"], rel=1e-9)
    assert statistics.median(usd) == pytest.approx(e["saving_vs_fallback"]["usd"]["median"], rel=1e-9)
    assert statistics.median(mar) == pytest.approx(e["margin_vs_cheapest_primary"]["usd"]["median"], rel=1e-9)
    assert min(mar) > 0 and e["margin_vs_cheapest_primary"]["weeks_positive"] == len(weeks)
    # Table III v2's overflow saving is 100 (1 - r0); the total-accounting one is far smaller (own capacity)
    assert e["saving_vs_fallback"]["pct_total"]["median"] < e["saving_vs_fallback"]["pct_overflow_median"]


def test_guard_and_allowance_from_the_guarded_records(extract):
    n = fb = 0
    bt = []
    for p in ("main", "seeds", "second", "e3", "fam", "grid"):      # every part, the week runs found by job name
        s = json.loads((REPO / X.SUMMARY[p]).read_text())
        for x in s["guarded"]:
            if ":k=week:" not in x["job"]:
                continue
            n += 1
            fb += x["s_fb_all"] is True
            if x["tag"] == "Sublet":
                bt.append(x["online_lb"]["B_T"])
    assert (n, fb) == (extract["guard"]["week"]["runs"], extract["guard"]["week"]["s_fb_all"])
    a = extract["allowance"]["sublet_week"]
    assert (len(bt), min(bt), max(bt)) == (a["runs"], a["B_T"]["min"], a["B_T"]["max"])
    assert a["B_T"]["max_ceil"] == math.ceil(max(bt)) and a["B_T"]["min_floor"] == math.floor(min(bt))
    assert a["excess_max"] < 0 and a["B_T_eq_Wk_T"] == a["runs"]


def test_f3_against_the_h3_table(extract):
    h3 = json.loads((REPO / "code/sim/out/figs/sf_e7_decomp.json").read_text())["data"]["tables"]["e7v2_h3"]["rows"]
    s = extract["fam_f3"]["by_tag"]
    for tag in ("Sublet", "BL1-GP", "BL1-G", "BL5-G"):
        row = next(r for r in h3 if r["part"] == "fam" and r["tag"] == tag and r["group"] == "F3")
        assert (row["runs"], row["aborts"]) == (s[tag]["runs"], s[tag]["aborts"]), tag
    assert s["Sublet"]["abort_slots"] == [0] and s["Sublet"]["aborts_at_slot0"] == s["Sublet"]["aborts"]


def test_alpha_n_formula(extract):
    a = extract["alpha_N"]
    for w, b in a["by_week"].items():
        assert (b["m"], b["K"]) == (a["m"], a["K"])
        assert b["N"] == max(b["n_units"] * b["T_slow"], 3) and b["requests"] <= b["N"]
        assert b["rbar"] == math.ceil(2 * math.log(b["N"]))
        assert b["value"] == pytest.approx(4 * b["rbar"] * math.log(a["m"] * a["K"] + 2) + 1, rel=1e-12)
    assert a["d"] == a["m"] * a["K"] + 1
    assert a["N_info_class"] == "online-I1 + a-priori N"
    # week 301's N against the driver input that the pre-registration resolved for Sublet (bench_e7f c301, L-tr)
    row = next(ln for ln in (REPO / "design/sublet_v2_prereg.md").read_text(encoding="utf-8").splitlines()
               if ln.startswith("| Sublet |") and '"N_bound":' in ln)
    assert '"N_bound": %d,' % a["by_week"]["301"]["N"] in row and "bench_e7f c301, L-tr" in row
    assert a["value"]["min"] == min(b["value"] for b in a["by_week"].values())
    assert a["value"]["max"] == max(b["value"] for b in a["by_week"].values())
    assert sorted(a["by_week"], key=int) == extract["econ"]["weeks"]
    # C13(b): the week's rho is the largest over the LLMs, each at least 1
    for w, b in a["by_week"].items():
        assert b["rho"] == max(v[0] for v in b["rho_by_llm"].values()) and b["rho"] >= 1, w
    assert a["rho"] == {"min": min(b["rho"] for b in a["by_week"].values()),
                        "max": max(b["rho"] for b in a["by_week"].values())}


# ---------------------------------------------------------------- exit codes
def test_missing_input_exits_2(tmp_path, capsys):
    out = tmp_path / "x.json"
    assert X.main(["--root", str(tmp_path / "empty"), "--out", str(out), "--no-planner-check"]) == 2
    assert not out.exists()
    assert f"missing input {X.TABLE3}" in capsys.readouterr().err


def _copy_inputs(root: Path) -> None:
    for rel in (X.TABLE3, X.FIG4V2, X.ANALYSIS, *X.SUMMARY.values()):
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO / rel, root / rel)


def _edit(root: Path, rel: str, fn) -> None:
    d = json.loads((root / rel).read_text())
    fn(d)
    (root / rel).write_text(json.dumps(d))


def test_failed_checks_exit_1(tmp_path, capsys):
    def f3_slot(d):
        x = next(x for x in d["guarded"] if x["tag"] == "Sublet" and x.get("aborted") and x["cell"].startswith("F3"))
        x["t_a"] = 5

    def s_left_fb(d):
        next(x for x in d["guarded"] if x["tag"] == "Sublet")["s_fb_all"] = False

    for name, rel, fn, msg in (("f3", X.SUMMARY["fam"], f3_slot, "Sublet's F3 aborts at slots [0, 5]"),
                               ("fb", X.SUMMARY["seeds"], s_left_fb, "S not on FB at every slot")):
        root = tmp_path / name
        _copy_inputs(root)
        _edit(root, rel, fn)
        out = tmp_path / f"{name}.json"
        assert X.main(["--root", str(root), "--out", str(out), "--no-planner-check"]) == 1, name
        assert not out.exists()
        err = capsys.readouterr().err
        assert "check failed" in err and msg in err, (name, err)


# ---------------------------------------------------------------- the week instances (a12 outputs)
@pytest.mark.needs_a12
def test_week_instances_rebuild(extract):
    weeks = ["301", "314"]
    got = X.week_instances(X.Reader(REPO), weeks, planner_check=False)
    for w in weeks:
        assert _jsonish(got["by_week"][w]) == extract["alpha_N"]["by_week"][w], f"week {w}: {STALE}"
    chk = extract["alpha_N"]["planner_check"]
    assert chk is not None and chk["matches"] is True and chk["policy"] == "ProjectedGuarded"
    b = extract["alpha_N"]["by_week"][chk["week"]]
    assert (chk["rbar"], chk["N_bound"], chk["d"]) == (b["rbar"], b["N"], extract["alpha_N"]["d"])
