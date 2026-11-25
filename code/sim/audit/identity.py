"""Identity check of the audit fixes F1 and F2 on the Q44 study (design/theory/audit_guard.md, "Audit of the full-model
guard"; code/sim/audit/, run by run_all.sh, output code/sim/out/audit_fm/identity.json).

The fixes change nothing for the study's inner policies: F1 prices a Load on a lease bought in the same list, and no
inner policy of the study (A7, BL1, BL5) issues a Load; F2 gives the inner policy a private copy of its observation,
and no inner policy writes to it. So rerunning a study run of A8 on the fixed code must give its run file bit for
bit. The study's run files are not versioned (.gitignore: code/sim/out/q44_study/runs/, about 400 MB and
regenerable); the script reads them from code/sim/out/q44_study/runs/ as the study's Tier 1 rerun on commit 472b353
wrote them (each file's meta.git_revision and sha256 are recorded), for the A8 tags of blocks Q1, Q2 (trace-driven
cells; tags PS-G, PS-G1, PS-GR, BL1-G, BL5-G: inner A7 with safe 'fb+pd', S_rbar 1 and 'pd', BL1 and BL5) and Q6
(core families; PS-G, PS-GR, BL1-G, BL5-G), picks for every (block, tag, lender mode) one run with an abort and one
without (where both exist, cycling over the cells and seeds), reruns each exactly as the study's runner did
(q44_study.run_cells via drivers/run.py's build and make_policy; q44_study.run_family via from_core), and compares
with ==: every ledger
component (the totals) and the guard's report (t_a, the test values a-hat(t), the reserves, T0g's G, S, Q and forms,
the wind-down log, the execution counts, S's curves, the inner policy's report), without its wall-clock entries
(keys containing 'time_s' or 'wall_s'). A probe (Probe) also records, per run, the Loads in the inner policy's
action lists (the lists that guard.slot_terms prices in mode E) and the writes of the inner policy to its copies of
the observation (each copy that guard.inner_obs makes is compared, after the run, with a second copy taken when it was
made); both are 0 for the study's inner policies, which is why the fixes leave the runs unchanged. The probe wraps the
two functions without changing what they return. Usage: identity.py [max runs per (block, tag, mode)] (default 2).

Scope in time: the 'correlated' lender (the study's mode L-co) draws its shocks per (source lender, onset, target
lender) since 2026-10-19 (design/sim_spec.md §6.6 and §10 S11), where commit 472b353 drew them per source site. On
code after that change the L-co samples are not reproducible and their comparisons fail for that reason alone; the
recorded identity.json was written before the change. Run this script on a checkout before the S11 change, or read
its L-co rows as not comparable."""
import copy
import dataclasses
import hashlib
import json
import subprocess
import sys
import time
from collections import defaultdict

import numpy as np

import audit_env  # noqa: F401
from audit_env import OUT, REPO
from sublet.algos import guard as G
from sublet.drivers import run as drun
from sublet.engine import EngineConfig, simulate
from sublet.experiments import q44_study as qs
from sublet.instance import from_core
from sublet.metrics import _jsonable
from sublet.types import LenderModel, Load

BLOCKS = {"Q1": ("PS-G", "PS-G1", "PS-GR", "BL1-G", "BL5-G"), "Q2": ("PS-G", "PS-G1", "PS-GR", "BL1-G", "BL5-G"),
          "Q6": ("PS-G", "PS-GR", "BL1-G", "BL5-G")}
RUNS = "code/sim/out/q44_study/runs"
GUARD = "code/sim/sublet/algos/guard.py"
REPORT_KEYS = ("t_a", "aborted", "mode", "guard", "terms", "t0g", "wd", "exec", "book", "at_abort", "alg_prev",
               "budget_t_a", "W_S_t_a", "a_hat_t_a", "safe", "test", "wind_down", "reserve", "on_unavailable", "inner")


def no_times(x):
    """x without the wall-clock entries of the reports (keys containing 'time_s' or 'wall_s'), at any depth."""
    if isinstance(x, dict):
        return {k: no_times(v) for k, v in x.items() if "time_s" not in k and "wall_s" not in k}
    if isinstance(x, list):
        return [no_times(v) for v in x]
    return x


def git(*args) -> bytes:
    return subprocess.run(["git", "-C", str(REPO), *args], check=True, capture_output=True).stdout


def study_runs() -> dict:
    """{(block, tag, mode): [path relative to the repository, ...]} of the A8 run files of BLOCKS, sorted."""
    out = defaultdict(list)
    for block, tags in BLOCKS.items():
        for f in (REPO / RUNS / block).rglob("*.json"):
            tag = f.name.split("_c")[0]
            if tag in tags and "_error" not in f.name and not f.name.startswith("cell"):
                out[(block, tag, f.parent.name)].append(str(f.relative_to(REPO)))
    return {k: sorted(v) for k, v in sorted(out.items())}


def select(runs: dict, per: int) -> list:
    """Per (block, tag, mode): up to `per` paths, alternating a run with an abort and one without, each picked
    cyclically by a counter so that the picks spread over the cells, instances and seeds."""
    sel = []
    k = 0
    for key, paths in runs.items():
        ta = {p: json.loads((REPO / p).read_text())["metrics"]["policy"]["t_a"] for p in paths}
        groups = [[p for p in paths if ta[p] is not None], [p for p in paths if ta[p] is None]]
        for i in range(per):
            g, j = (groups[i % 2], i // 2) if groups[i % 2] else (groups[(i + 1) % 2], i)
            if not g:
                break
            p = g[(k + j) % len(g)]
            if p not in sel:
                sel.append(p)
        k += 1
    return sel


def _same(a, b) -> bool:
    """Field values equal, also in type (an array by shape, dtype and values)."""
    if type(a) is not type(b):
        return False
    if isinstance(a, np.ndarray):
        return a.shape == b.shape and a.dtype == b.dtype and bool(np.array_equal(a, b))
    return a == b


class Probe:
    """Counts the Loads in the lists that guard.slot_terms prices and the inner policy's writes to its observation
    copies (guard.inner_obs), for one run; restores both functions on exit."""

    def __enter__(self):
        self.loads, self.copies = 0, []
        self._st, self._io = G.slot_terms, G.inner_obs
        st, io = self._st, self._io

        def slot_terms(view, obs, actions):
            self.loads += sum(1 for a in actions if isinstance(a, Load))
            return st(view, obs, actions)

        def inner_obs(obs):
            cp = io(obs)
            self.copies.append((cp, io(cp)))
            return cp
        G.slot_terms, G.inner_obs = slot_terms, inner_obs
        return self

    def __exit__(self, *exc):
        G.slot_terms, G.inner_obs = self._st, self._io
        return False

    def writes(self) -> int:
        """Copies that differ from their second copy in some field (checked after the run)."""
        return sum(1 for cp, snap in self.copies
                   if any(not _same(getattr(cp, f.name), getattr(snap, f.name)) for f in dataclasses.fields(cp)))


def rerun(js: dict):
    q = js["q44"]
    block, tag, mode = q["block"], q["tag"], q["mode"]
    b = qs.load_block(block)
    l, p = int(q["seeds"]["lender"]), int(q["seeds"]["policy"])
    if q["grid"] == "core":                                       # q44_study.run_family
        fam = next(f for f in b["families"] if f["id"] == q["family"])
        I, F, desc = qs.family_core(fam, q["values"])
        fmode = qs.FAMILY_MODES[mode]
        pid = qs.POLICIES[tag]["id"]
        info = qs.POLICIES[tag].get("information", "I1")
        model = LenderModel(schedule=fmode["schedule"], information=info, params=dict(fmode["params"]))
        inst, _ = from_core(I, [np.zeros(0, dtype=np.int64)] * int(I.a.shape[0]))
        params = copy.deepcopy(qs.POLICIES[tag]["params"])
        vals, _imeta = drun.driver_inputs(pid, params, inst)
        pol = drun.make_policy({"policy": {"id": pid, "params": params}}, inst, inputs=vals)
        return simulate(inst, pol, model, EngineConfig(check_invariants=True), lender_seed=l, policy_seed=p)
    inst = next(i for i in b["instances"] if i["id"] == q["instance"])   # q44_study.run_cells
    c = int(q["cell"])
    spec = drun.load_run_spec(qs.run_spec(b, inst, tag, mode, c, [p], q["resolved_tag_params"]))
    I, model, ecfg = drun.build(spec, c)
    pol = drun.make_policy(spec, I)
    assert l == c, (l, c)                                         # lender seeds = config seeds
    return simulate(I, pol, model, ecfg, lender_seed=l, policy_seed=p)


def main():
    per = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    t0 = time.time()
    head = git("rev-parse", "HEAD").decode().strip()
    code_diff = git("diff", "--stat", "HEAD", "--", "code/sim/sublet").decode().strip()
    sel = select(study_runs(), per)
    rows, n_same = [], 0
    for path in sel:
        raw = (REPO / path).read_bytes()
        js = json.loads(raw)
        with Probe() as pr:
            res = rerun(js)
        n_writes = pr.writes()
        comp = {k: float(v) for k, v in res.components.items()}
        rep = no_times(json.loads(json.dumps(_jsonable(res.metrics["policy"]))))
        ref_rep = no_times(js["metrics"]["policy"])
        comp_diff = sorted(k for k in set(comp) | set(js["components"]) if comp.get(k) != js["components"].get(k))
        rep_diff = [k for k in REPORT_KEYS if rep.get(k) != ref_rep.get(k)]
        same = not comp_diff and not rep_diff and not res.invariant_failures
        n_same += int(same)
        q = js["q44"]
        rows.append({"path": path, "block": q["block"], "instance": q["instance"], "mode": q["mode"], "tag": q["tag"],
                     "inner": ref_rep.get("inner_id"), "cell": q["cell"], "seeds": q["seeds"], "t_a": ref_rep["t_a"],
                     "total": comp["total"], "total_committed": js["components"]["total"],
                     "components_equal": not comp_diff, "components_differ": comp_diff,
                     "report_equal": not rep_diff, "report_differs": rep_diff,
                     "report_equal_all_keys": rep == ref_rep, "identical": same,
                     "inner_loads": pr.loads, "inner_obs_copies": len(pr.copies), "inner_obs_writes": n_writes,
                     "file_sha256": hashlib.sha256(raw).hexdigest(),
                     "run_git_revision": js["meta"].get("git_revision")})
        print(f"{'OK  ' if same else 'DIFF'} {path} total {comp['total']!r} t_a {ref_rep['t_a']} loads {pr.loads} "
              f"obs writes {n_writes} of {len(pr.copies)}"
              + ("" if same else f" components {comp_diff} report {rep_diff}"), flush=True)
    cnt = defaultdict(int)
    for r in rows:
        cnt[f"{r['block']}:{r['inner']}"] += 1
    summary = {"what": "rerun of A8 runs of the Q44 study (run files of code/sim/out/q44_study/runs/, not versioned) "
                       "on the code with the audit fixes F1 and F2 (code/sim/audit/identity.py); inner_loads and "
                       "inner_obs_writes are the probe's counts (0 expected)",
               "head": head, "code_sim_sublet_diff_to_head": code_diff,
               "guard_py_sha256": hashlib.sha256((REPO / GUARD).read_bytes()).hexdigest(),
               "run_file_revisions": sorted({r["run_git_revision"] for r in rows}),
               "runs": len(rows), "identical": n_same,
               "inner_loads": sum(r["inner_loads"] for r in rows),
               "inner_obs_writes": sum(r["inner_obs_writes"] for r in rows),
               "inner_obs_copies": sum(r["inner_obs_copies"] for r in rows),
               "all_identical": n_same == len(rows), "aborted_runs": sum(r["t_a"] is not None for r in rows),
               "by_block_inner": dict(sorted(cnt.items())),
               "modes": sorted({f"{r['block']}:{r['mode']}" for r in rows}),
               "tags": sorted({r["tag"] for r in rows}),
               "compared": {"components": "every ledger component, ==",
                            "report": list(REPORT_KEYS), "report_without": "keys containing 'time_s' or 'wall_s'"},
               "wall_s": round(time.time() - t0, 1), "rows": rows}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "identity.json").write_text(json.dumps(summary, indent=1) + "\n")
    print(f"identical {n_same} of {len(rows)} runs ({summary['aborted_runs']} with an abort); head {head[:7]}; "
          f"run files of {summary['run_file_revisions']}; {summary['wall_s']} s")
    return 0 if summary["all_identical"] and summary["inner_loads"] == summary["inner_obs_writes"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
