"""Information discipline and plan class of the MS2 policies (design/sim_spec_ms2.md §2.2, §2.3; §17.2).

test_static_imports scans sublet/algos/ and sublet/baselines/ with the ast module: the policies import
only numpy, scipy, the standard library, sublet.types, sublet.calib, sublet.timing, sublet.policies.base,
active_units from sublet.instance, sublet.paths for ANALYSIS_OUT (and import_c2 in algos/c2rule.py only),
and modules of sublet.algos and sublet.baselines; registry.py imports no policy module; no file is read
except a11_calibration.json and a5b_exposure_thresholds.json. test_plan_class_p1 runs every engine policy
and checks plan class P1 (§2.3)."""
import ast
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from fixtures import SIM, policy_actions_recorder

from sublet.types import Buy, LenderModel

SUBLET = SIM / "sublet"
POLICY_DIRS = ("algos", "baselines")
ALLOWED_SUBLET = {"sublet.types", "sublet.calib", "sublet.timing", "sublet.policies.base"}
ALLOWED_NAMES = {"sublet.instance": {"active_units"}, "sublet.paths": {"ANALYSIS_OUT"}}
C2RULE_EXTRA = {"sublet.paths": {"import_c2"}}
THIRD_PARTY = {"numpy", "scipy"}
ALLOWED_FILES = ("a11_calibration.json", "a5b_exposure_thresholds.json")
READ_METHODS = {"read_text", "read_bytes", "read_csv", "read_json", "read_parquet", "loadtxt", "genfromtxt",
                "fromfile", "load_json"}          # calls that read a file, whatever the receiver
FILE_MODULES = {"io", "os", "gzip", "bz2", "lzma", "codecs", "json", "pickle", "np", "numpy", "pd", "pandas",
                "shelve", "csv", "tarfile", "zipfile", "yaml"}   # receivers of open() / load() that read files
FILE_EXT = (".json", ".npz", ".npy", ".csv", ".txt", ".pkl", ".parquet", ".log", ".md")
DRIVER_LAZY = ("sublet.drivers.predict", "sublet.drivers.bench", "sublet.drivers.provision")


def _policy_files() -> list[Path]:
    out = []
    for d in POLICY_DIRS:
        out += sorted((SUBLET / d).glob("*.py"))
    assert out, "no policy module found"
    return out


def _module_name(path: Path) -> str:
    rel = path.relative_to(SIM).with_suffix("")
    parts = list(rel.parts)
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _is_module(dotted: str) -> bool:
    """Whether `dotted` (sublet...) names a module or package of the source tree."""
    p = SIM.joinpath(*dotted.split("."))
    return p.with_suffix(".py").is_file() or (p / "__init__.py").is_file()


def _imports(path: Path):
    """(kind, module, name, lineno) for every import of the file: kind 'module' for `import x` and for
    `from p import m` where p.m is a module; kind 'name' for `from p import n` of a non-module name."""
    tree = ast.parse(path.read_text(), filename=str(path))
    mod = _module_name(path)
    pkg = mod if path.name == "__init__.py" else mod.rpartition(".")[0]
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                out.append(("module", a.name, a.asname or a.name.split(".")[0], node.lineno))
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                base = pkg.split(".")
                base = base[:len(base) - (node.level - 1)]
                src = ".".join(base + ([node.module] if node.module else []))
            else:
                src = node.module
            for a in node.names:
                full = f"{src}.{a.name}"
                if src.startswith("sublet") and _is_module(full):
                    out.append(("module", full, a.asname or a.name, node.lineno))
                else:
                    out.append(("name", src, a.name, node.lineno))
    return tree, out


def _attr_uses(tree, alias: str) -> set:
    """Attributes accessed on the name `alias` (alias.X)."""
    return {n.attr for n in ast.walk(tree)
            if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) and n.value.id == alias}


def _violations(path: Path) -> list[str]:
    tree, imps = _imports(path)
    mod = _module_name(path)
    allowed_names = {k: set(v) for k, v in ALLOWED_NAMES.items()}
    if mod == "sublet.algos.c2rule":
        for k, v in C2RULE_EXTRA.items():
            allowed_names[k] |= v
    bad = []
    for kind, src, name, line in imps:
        top = src.split(".")[0]
        where = f"{path.relative_to(SIM)}:{line}"
        if top != "sublet":
            if top in THIRD_PARTY or top in sys.stdlib_module_names:
                continue
            bad.append(f"{where}: third-party module {src!r}")
            continue
        if kind == "module":
            if src in ALLOWED_SUBLET or src.startswith(("sublet.algos.", "sublet.baselines.")) \
                    or src in ("sublet.algos", "sublet.baselines"):
                continue
            if src in allowed_names:
                used = _attr_uses(tree, name) if name != src.split(".")[0] else set()
                if used and used <= allowed_names[src]:
                    continue
                bad.append(f"{where}: module {src!r} used for {sorted(used)}; allowed {sorted(allowed_names[src])}")
                continue
            bad.append(f"{where}: module {src!r} is not allowed")
        else:
            if src in ALLOWED_SUBLET or src.startswith(("sublet.algos", "sublet.baselines")):
                continue
            if name in allowed_names.get(src, set()):
                continue
            bad.append(f"{where}: name {name!r} from {src!r} is not allowed")
    if mod == "sublet.baselines.wrappers":
        bad += [f"{path.name}: imports the registry" for kind, src, name, _ in imps
                if src == "sublet.algos.registry" or (src == "sublet.algos" and name == "registry")]
    return bad


def _is_read(call: ast.Call) -> bool:
    """A call that reads a file: the builtin open(), open() or load() of a file module (io, json, numpy, ...)
    or of a path expression, and the read methods of READ_METHODS. Methods called open or load on other
    objects (e.g. ExecutionLayer.open) are not file reads."""
    f = call.func
    if isinstance(f, ast.Name):
        return f.id == "open"
    if not isinstance(f, ast.Attribute):
        return False
    if f.attr in READ_METHODS:
        return True
    if f.attr in ("open", "load"):
        recv = ast.unparse(f.value)
        return recv in FILE_MODULES or "path" in recv.lower() or "ANALYSIS_OUT" in recv
    return False


def _file_reads(path: Path) -> list[str]:
    """Calls that read files and string constants that name files; a module that reads must name only the
    two calibration files, and every file name it holds must be one of them."""
    tree = ast.parse(path.read_text(), filename=str(path))
    strings = [n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)]
    names = [s for s in strings if s.endswith(FILE_EXT) and " " not in s]
    bad = [f"{path.name}: file name {s!r}" for s in names if Path(s).name not in ALLOWED_FILES]
    reads = [(ast.unparse(n.func), n.lineno) for n in ast.walk(tree) if isinstance(n, ast.Call) and _is_read(n)]
    if reads and not any(Path(s).name in ALLOWED_FILES for s in names):
        bad += [f"{path.name}:{line}: {fn}() without one of {ALLOWED_FILES}" for fn, line in reads]
    return bad


def test_static_imports():
    """§2.2: exactly the allowed imports in sublet/algos/ and sublet/baselines/ (AST scan, also of imports
    inside functions); registry.py imports no sublet module and importing it loads no policy module;
    import_c2 only in algos/c2rule.py; no file reads except a11_calibration.json and
    a5b_exposure_thresholds.json."""
    files = _policy_files()
    names = {_module_name(p) for p in files}
    assert {"sublet.algos.registry", "sublet.algos.common"} <= names
    bad = []
    for p in files:
        bad += _violations(p)
        bad += _file_reads(p)
    assert not bad, "\n".join(bad)
    _, imps = _imports(SUBLET / "algos" / "registry.py")
    assert all(not src.startswith("sublet") for _, src, _, _ in imps), imps
    users = [p.name for p in files if any(n == "import_c2" for _, _, n, _ in _imports(p)[1])
             or "import_c2" in _attr_uses(_imports(p)[0], "paths")]
    assert set(users) <= {"c2rule.py"}, users
    reg = _loaded_after("sublet.algos.registry")
    assert reg <= {"sublet", "sublet.algos", "sublet.algos.registry"}, sorted(reg)
    drv = _loaded_after("sublet.drivers.run")
    algos = {m for m in drv if m.startswith("sublet.algos.")}
    assert algos <= {"sublet.algos.registry", "sublet.algos.common"}, sorted(algos)
    assert not any(m.startswith("sublet.baselines") for m in drv), sorted(drv)
    assert not drv & set(DRIVER_LAZY), sorted(drv & set(DRIVER_LAZY))


def _loaded_after(module: str) -> set:
    """The sublet modules loaded by `import module` in a fresh interpreter."""
    code = ("import json, sys; sys.dont_write_bytecode = True; sys.path.insert(0, %r)\n"
            "import %s\n"
            "print(json.dumps(sorted(m for m in sys.modules if m.startswith('sublet'))))\n") % (str(SIM), module)
    out = subprocess.run([sys.executable, "-c", code], cwd=str(SIM), capture_output=True, text=True, timeout=300)
    assert out.returncode == 0, out.stderr
    return set(json.loads(out.stdout.strip().splitlines()[-1]))


# ---------------------------------------------------------------- plan class P1
MULTI = "ms2_multi_small.json"
SINGLE = "ms2_single_site.json"
A1P = {"contract_rev": "s5_tau5_H60"}
P1_CASES = {
    "A2": (MULTI, "A2", {}, "I1"),
    "A2_theory": (MULTI, "A2", {"rbar": "theory"}, "I1"),
    "A3": (MULTI, "A3", {}, "I1"),
    "A4_I1": (MULTI, "A4", {}, "I1"),
    "A4_I2": (MULTI, "A4", {}, "I2"),
    "A5": (MULTI, "A5", {}, "I1"),
    "A6": (MULTI, "A6", {}, "I1"),
    "A6_I2": (MULTI, "A6", {}, "I2"),
    "BL0a": (MULTI, "BL0a", {}, "I1"),
    "BL1": (MULTI, "BL1", {}, "I1"),
    "BL3": (MULTI, "BL3", {}, "I1"),
    "BL4": (MULTI, "BL4", {}, "I1"),
    "BL4_oracle": (MULTI, "BL4", {"demand": "oracle"}, "I1"),
    "BL5": (MULTI, "BL5", {}, "I1"),
    "BL6_A2": (MULTI, "BL6", {"inner": "A2"}, "I1"),
    "BL6_A6": (MULTI, "BL6", {"inner": "A6"}, "I1"),
    "BL7_A2": (MULTI, "BL7", {"inner": "A2"}, "I1"),
    "BL7_A6": (MULTI, "BL7", {"inner": "A6"}, "I1"),
    "A1": (SINGLE, "A1", A1P, "I1"),
    "BL6_A1": (SINGLE, "BL6", {"inner": "A1", "inner_params": A1P}, "I1"),
    "BL7_A1": (SINGLE, "BL7", {"inner": "A1", "inner_params": A1P}, "I1"),
    "RR_RENEW": ("family", "RR_RENEW", {}, "I1"),
    "MARKING": ("family", "MARKING", {}, "I2"),
    "BL2": (MULTI, "BL2", {}, "I1"),
    "SILOED_A2": (MULTI, "SILOED", {"inner": "A2"}, "I1"),
    "A7": (MULTI, "A7", {}, "I1"),
    "A8": (MULTI, "A8", {}, "I1"),
}
P1_HORIZON_MIN = 720          # half a day of the MS2 configs (the plan class does not depend on the length)


def _check_p1(res, rec, tag):
    """Plan class P1 on one engine run: actions only Buy (n_replicas 1), Release, Drain, SetAdmission;
    gpu_only_lease_slots = 0; empty invariant_failures (with check_invariants on)."""
    assert res.invariant_failures == [], (tag, res.invariant_failures[:5])
    kinds = {type(a).__name__ for _, a in rec.actions}
    assert kinds <= {"Buy", "Release", "Drain", "SetAdmission"}, (tag, kinds)
    assert all(a.n_replicas == 1 for _, a in rec.actions if isinstance(a, Buy)), tag
    assert res.metrics["gpu_only_lease_slots"] == 0, tag
    return kinds


def test_policy_registry_cases_cover_simulate_runner():
    """Every id with runner 'simulate' or 'siloed' of §4.2 has a case in test_plan_class_p1."""
    from sublet.algos import registry
    ids = {pid for pid in registry.POLICY_IDS if registry.entry(pid).runner in ("simulate", "siloed")}
    assert ids == {c[1] for c in P1_CASES.values()}


@pytest.mark.parametrize("case", list(P1_CASES))
def test_plan_class_p1(case):
    """§2.3: every engine policy, through drivers.run.make_policy (driver inputs from the instance), runs in
    plan class P1 with the engine's invariant checks on: A2-A6 and the baselines on ms2_multi_small.json (BL6
    and BL7 around A2 and A6 too), A1 and BL6/BL7 around A1 on ms2_single_site.json with contract_rev, the
    family policies on a T4/O1 family instance (MARKING under I2), BL2 and SILOED (inner A2) through
    run_siloed; BL0b and BL8 have no engine run."""
    from sublet.drivers import run as drun
    from sublet.drivers.siloed import run_siloed
    from sublet.engine import EngineConfig, simulate
    inst_src, pid, params, info = P1_CASES[case]
    spec_pol = {"policy": {"id": pid, "params": params}}
    if inst_src == "family":
        import fam
        from sublet.instance import from_core
        F = fam.Fam(4, 8, 2, 1, 48)
        inst, _ = from_core(F.core_instance(), [np.zeros(0, np.int64)] * 4)
        model = LenderModel(schedule="safe_site", information=info)
        ecfg = EngineConfig(check_invariants=True)
    else:
        spec = drun.load_run_spec({"schema_version": 1, "name": f"p1_{case}", "instance": inst_src,
                                   "overrides": {"time.horizon_min": P1_HORIZON_MIN},
                                   "lender_model": {"information": info}, "policy": spec_pol["policy"]})
        inst, model, ecfg = drun.build(spec, spec["seeds"]["config"][0])
        spec_pol = spec
    assert ecfg.check_invariants
    recs = []
    if pid in ("BL2", "SILOED"):
        if pid == "SILOED":
            inner = {"policy": {"id": params["inner"], "params": params.get("inner_params", {})}}
        else:
            inner = spec_pol

        def factory(sub):
            rec = policy_actions_recorder(drun.make_policy(inner, sub))
            recs.append(rec)
            return rec
        d = run_siloed(inst, factory, model, ecfg, policy_seed=0)
        assert d["invariant_failures"] == [] and len(d["results"]) == len(recs) == inst.n
        kinds = set()
        for res, rec in zip(d["results"], recs):
            kinds |= _check_p1(res, rec, case)
    else:
        rec = policy_actions_recorder(drun.make_policy(spec_pol, inst))
        res = simulate(inst, rec, model, ecfg, policy_seed=0)
        kinds = _check_p1(res, rec, case)
    # a non-vacuous check: the runs buy leases (BL0a never does; A5 on day 0 has an empty predicted plan, and the
    # combiner then follows whichever of FP (all fallback) and R is cheaper at t = 0, §13.4)
    if pid not in ("BL0a", "A5"):
        assert "Buy" in kinds, (case, "the run bought nothing")
