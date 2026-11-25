"""X15: mutation sensitivity of tests/test_guard_projection.py, above all of Remark R's identity check.

Claim and source. design/theory/c3_c4_c5_general.md §9, Remark R(f), the code statement of Remark R: A8P around an
inner policy E and A8 around Proj(E) of Definition R3 give equal lists at every slow and fast slot, equal ledgers and
equal reports. tests/test_guard_projection.py checks it in test_remark_r_identity and, on the paths of R1-R3 that
this test's grid leaves unobserved, in test_remark_r_coverage. The audit addendum of step P6 (design/sublet_v2.md
§5), finding REMARK_R-F4, found that 7 of 14 mutations of ProjectedGuarded passed test_remark_r_identity. This
script measures what each of the two tests, and the whole file, catch.

Method. Each of the 14 mutations below (those of the P6 auditor's harness, with its numbering; M9 and M13 were not
used) replaces one fragment of ProjectedGuarded's code in sublet/algos/guard.py, so that A8P departs from R1-R3 or
from its report. They are applied one at a time to guard.py in a temporary copy of code/sim (sublet, tests without
the figure fixtures, configs, conftest.py), with copies of code/analysis and code/theory_checks beside it in the
layout that conftest.py and sublet/paths.py expect; the checkout is never changed. Against each mutation, pytest runs,
in this order and one process at a time, with the quick suite's marker selection and -x: test_remark_r_identity
alone, test_remark_r_coverage alone, and the whole file. Each pytest runs in its own systemd scope capped at 3G
without swap, on one worker (as the steps of run_all.sh; --no-scope runs it without a scope). A run that fails
(pytest exit status 1) catches the mutation, status 0 misses it, and any other status (a collection error, a killed
scope) is an error. The unmutated copy runs first and must pass all three runs.

Output (stdout). The code state (HEAD, sha256 of guard.py and of the test file), one line per run as it ends, and a
table: mutation, outcome of each of the three runs (caught or missed, with the first failing test), and for a
mutation that test_remark_r_identity misses, the path that its grid leaves unobserved (from the P6 audit). Exit
status 1 if the unmutated copy fails a run, if a run ends with an error, if a mutation survives the whole file, or if
a mutation survives both test_remark_r_identity and test_remark_r_coverage: every mutation of the list changes a
quantity that Remark R(f)'s comparison checks (lists, ledger, report, counters) on test_remark_r_coverage's grid, so
none is semantically equivalent there. Exit status 2 if a mutation's fragment does not occur exactly once in guard.py
(the code changed and the list must be updated). About 15-25 min.

Usage: x15_mutations.py [--no-scope] [--keep] [--work DIR] [--only M1,M2,...]
"""
from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

SIM = Path(__file__).resolve().parents[1]
REPO = SIM.parents[1]
GUARD = Path("sublet") / "algos" / "guard.py"
TEST = "tests/test_guard_projection.py"
QUICK = ("not needs_raw and not needs_ms2_checks and not needs_ms3_out and not needs_ms4_out and not needs_ms5_out "
         "and not needs_ms5b_out")
RUNS = (("identity", TEST + "::test_remark_r_identity"), ("coverage", TEST + "::test_remark_r_coverage"),
        ("file", TEST))

# (id, what it changes, fragment of guard.py, replacement)
MUTS = (
    ("M1", "R2: a dropped action's result carries the reason 'guard_x', not 'guard'",
     'REFUSAL = "guard"', 'REFUSAL = "guard_x"'),
    ("M2", "R2: the remapped results are not sorted by index",
     "        out.sort(key=lambda r: r.index)\n        return out", "        return out"),
    ("M3", "R1: the candidates in the order E, P0, P1..., K0",
     "        own: dict[int, int] = {}                 # held lease",
     "        out = [out[0]] + [c for c in out[1:] if c[0] == 'P0'] + [c for c in out[1:] if c[0] != 'P0']\n"
     "        own: dict[int, int] = {}                 # held lease"),
    ("M4", "R3 (iv): A_E(t)'s T0g evaluation committed, not the executed candidate's",
     "        tb.commit(ev)\n        self.budget = float(R)\n        self.modes.append(\"E\")",
     "        tb.commit(ev_E[4] if ev_E is not None else ev)\n        self.budget = float(R)\n"
     "        self.modes.append(\"E\")"),
    ("M5", "R3 (ii): the allowance read before SafeExpert.step",
     "        sx.step(obs)                                         # step 2\n"
     "        B_t = rt.allowance(sx.B_on)", "        B_t = rt.allowance(sx.B_on)\n        sx.step(obs)"),
    ("M6", "R3, fast filter: replicas that the executed list unloads stay admissible",
     " and int(rid) not in unl}", "}"),
    ("M7", "R3, on_fast: FastObs.results reach the inner policy without the remap",
     "            obs = dataclasses.replace(obs, results=self._inner_results(obs.results))", "            pass"),
    ("M8", "R1: K0 with new Release objects instead of E's own first Releases",
     "[acts[own[lid]] if lid in own else Release(lid) for lid in k0], [own.get(lid) for lid in k0]",
     "[Release(lid) for lid in k0], [None for lid in k0]"),
    ("M10", "R2: a dropped action's result carries ok True",
     "out += [ActionResult(i, a, False, None, (), self.REFUSAL)",
     "out += [ActionResult(i, a, True, None, (), self.REFUSAL)"),
    ("M11", "R3 (iv): the remap state kept after an abort",
     "        self._map = None\n        if pick is None:",
     "        if pick is not None:\n            self._map = None\n        if pick is None:"),
    ("M12", "R1: P1's floor(n_b / 4) rung removed",
     "{nb - 1, nb // 2, nb // 4, 1}", "{nb - 1, nb // 2, 1}"),
    ("M14", "report: dropped fast actions not counted (dropped_fast)",
     "        self.dropped_fast += len(acts) - len(keep)", "        self.dropped_fast += 0"),
    ("M15", "report: guard Releases not counted (projection['guard_releases'])",
     '        pr["guard_releases"] += sum(1 for i in src if i is None)', '        pr["guard_releases"] += 0'),
    ("M16", "allowance 'lb': B(t) one slot stale",
     "        Q = sx.fb_inc\n        tb.begin(obs)",
     "        Q = sx.fb_inc\n        if self.olb is not None:\n            B_t = float(self.olb.B_series[-2]) "
     "if len(self.olb.B_series) > 1 else 0.0\n        tb.begin(obs)"),
)

# why test_remark_r_identity's grid cannot see a mutation (P6 audit, REMARK_R-F4; test_remark_r_coverage's grid
# has each of these paths)
IDENTITY_GAP = {
    "M1": "no inner policy of its grid reads a result's reason",
    "M2": "no inner policy of its grid depends on the order of the results",
    "M6": "no inner policy of its grid names, in on_fast, a replica that its executed list unloaded",
    "M7": "its only inner policy with on_fast (_FastInner) ignores FastObs.results",
    "M11": "no inner policy with on_fast aborts right after a projected slot",
    "M12": "its random inner policies (almost) never issue 8 Buys in one list",
    "M14": "no fast action is dropped",
}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def make_copy(work: Path) -> Path:
    """code/sim (sublet, tests, configs, conftest.py), code/analysis and code/theory_checks under work/code; returns
    the copy of code/sim."""
    plain = shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache", ".ruff_cache")
    code = work / "code"
    shutil.copytree(SIM / "sublet", code / "sim" / "sublet", ignore=plain)
    shutil.copytree(SIM / "tests", code / "sim" / "tests",
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "fixtures_figs*"))
    shutil.copytree(SIM / "configs", code / "sim" / "configs", ignore=plain)
    shutil.copy2(SIM / "conftest.py", code / "sim" / "conftest.py")
    shutil.copytree(REPO / "code" / "analysis", code / "analysis",
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "fig", "bench"))
    shutil.copytree(REPO / "code" / "theory_checks", code / "theory_checks", ignore=plain)
    return code / "sim"


def run_pytest(sim: Path, target: str, basetemp: Path, scope: bool) -> dict:
    """One pytest run: {'status': 'pass' | 'fail' | 'error', 'rc', 'secs', 'first' (first failing test), 'tail'}."""
    cmd = [sys.executable, "-m", "pytest", "-q", "-x", "-rf", "-p", "no:cacheprovider", "--basetemp", str(basetemp),
           "-m", QUICK, target]
    if scope:
        cmd = ["systemd-run", "--user", "--scope", "-q", "-p", "MemoryMax=3G", "-p", "MemorySwapMax=0", "env",
               "OMP_NUM_THREADS=1", "PYTHONDONTWRITEBYTECODE=1"] + cmd
    t0 = time.time()
    p = subprocess.run(cmd, cwd=sim, capture_output=True, text=True,
                       env={**os.environ, "OMP_NUM_THREADS": "1", "PYTHONDONTWRITEBYTECODE": "1"})
    lines = [ln for ln in (p.stdout + p.stderr).splitlines() if ln.strip()]
    first = next((ln.split()[1].split("::")[-1] for ln in lines if ln.startswith("FAILED ")), None)
    status = {0: "pass", 1: "fail"}.get(p.returncode, "error")
    return {"status": status, "rc": p.returncode, "secs": time.time() - t0, "first": first, "tail": lines[-3:]}


def cell(r: dict) -> str:
    if r["status"] == "pass":
        return "missed"
    if r["status"] == "fail":
        return f"caught ({r['first']})"
    return f"ERROR rc={r['rc']}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--no-scope", action="store_true", help="run pytest without a systemd scope")
    ap.add_argument("--keep", action="store_true", help="keep the temporary copy")
    ap.add_argument("--work", default=None, help="folder for the temporary copy (default: a new temporary folder)")
    ap.add_argument("--only", default=None, help="comma-separated mutation ids (default: all)")
    a = ap.parse_args()
    scope = not a.no_scope and shutil.which("systemd-run") is not None
    only = None if a.only is None else set(a.only.split(","))
    muts = [m for m in MUTS if only is None or m[0] in only]
    t_all = time.time()
    head = subprocess.run(["git", "-C", str(REPO), "rev-parse", "--short", "HEAD"], capture_output=True,
                          text=True).stdout.strip()
    print(f"# X15 {time.strftime('%Y-%m-%dT%H:%M:%S')} HEAD={head}; python {sys.version.split()[0]}; "
          f"{'one 3G systemd scope per pytest run' if scope else 'no systemd scope'}; marker selection: {QUICK}")
    work = Path(tempfile.mkdtemp(prefix="x15_", dir=a.work))
    try:
        sim = make_copy(work)
        g = sim / GUARD
        bt = work / "basetemp"
        print(f"# copy in {work} ({time.time() - t_all:.0f} s): guard.py sha256 {sha(g)}, {TEST} sha256 "
              f"{sha(sim / TEST)}", flush=True)
        pristine = g.read_text()
        stale = [(m[0], pristine.count(m[2])) for m in muts if pristine.count(m[2]) != 1]
        if stale:
            print(f"STALE mutations (fragment not found exactly once in guard.py): {stale}")
            return 2
        bad = []
        base = {}
        for key, target in RUNS:                                             # the unmutated copy
            base[key] = r = run_pytest(sim, target, bt, scope)
            print(f"unmutated {key}: {r['status']} ({r['secs']:.0f} s)", flush=True)
            if r["status"] != "pass":
                print(f"   {r['tail']}", flush=True)
                bad.append(f"unmutated copy: {key} {r['status']}")
        if bad:
            print("FAIL: the unmutated copy does not pass; no mutation was run:", bad)
            return 1
        rows = []
        for mid, what, old, new in muts:
            g.write_text(pristine.replace(old, new))
            try:
                res = {}
                for key, target in RUNS:
                    res[key] = r = run_pytest(sim, target, bt, scope)
                    print(f"{mid} {key}: {cell(r)} ({r['secs']:.0f} s)", flush=True)
                    if r["status"] == "error":
                        print(f"   {r['tail']}", flush=True)
            finally:
                g.write_text(pristine)
            rows.append((mid, what, res))
        print()
        print("| mutation | what it changes | test_remark_r_identity | test_remark_r_coverage | Remark R(f) check | "
              "whole file | why test_remark_r_identity misses it |")
        print("|---|---|---|---|---|---|---|")
        for mid, what, res in rows:
            either = "caught" if "fail" in (res["identity"]["status"], res["coverage"]["status"]) else "missed"
            why = IDENTITY_GAP.get(mid, "(no recorded reason)") if res["identity"]["status"] == "pass" else ""
            print(f"| {mid} | {what} | {cell(res['identity'])} | {cell(res['coverage'])} | {either} | "
                  f"{cell(res['file'])} | {why} |")
            if any(r["status"] == "error" for r in res.values()):
                bad.append(f"{mid}: a run ended with an error")
            if res["file"]["status"] == "pass":
                bad.append(f"{mid}: survives the whole file")
            if either == "missed":
                bad.append(f"{mid}: survives test_remark_r_identity and test_remark_r_coverage")
        n = len(rows)
        n_id = sum(res["identity"]["status"] == "fail" for _m, _w, res in rows)
        n_cov = sum(res["coverage"]["status"] == "fail" for _m, _w, res in rows)
        n_either = sum("fail" in (res["identity"]["status"], res["coverage"]["status"]) for _m, _w, res in rows)
        n_file = sum(res["file"]["status"] == "fail" for _m, _w, res in rows)
        print()
        print(f"caught: test_remark_r_identity {n_id} of {n}, test_remark_r_coverage {n_cov} of {n}, either {n_either} "
              f"of {n}, whole file {n_file} of {n}")
        print("unmutated copy: " + ", ".join(f"{k} {base[k]['secs']:.0f} s" for k, _t in RUNS))
        print(f"wall time {time.time() - t_all:.0f} s")
        if bad:
            print("FAIL:", "; ".join(bad))
            return 1
        print("OK: every mutation is caught by the Remark R(f) check and by the whole file")
        return 0
    finally:
        if a.keep:
            print(f"# kept {work}")
        else:
            shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
