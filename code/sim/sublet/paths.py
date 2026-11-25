"""Repository paths and importers of reference code (design/sim_spec.md §3.4.1).

Reference theory and analysis modules are imported only through this module (§2.2),
so that `sys.path` is changed in one place and at most once per directory. Imports through it
never write bytecode (sys.dont_write_bytecode is set while the module loads), so no `.pyc` file
under code/theory_checks/ or code/analysis/ is created or changed.

MS2 (design/sim_spec_ms2.md §2.4, C9): `C2`, `import_c2` and `import_ref`. Reference modules that
run on import (c2/alg_check_targeted.py, c2/audit/switch_cost_crossover.py,
c2/audit/recheck_c2.py, c3/audit/a2_P_equiv_and_termination.py) are not importable here.

MS3 (design/sim_spec_ms3.md §2.3, C11): `import_ref("o1_lb")` (c3/o1/o1_lb.py, main guard at line 231) and
`import_c2().det_game` (c2/det_game.py, main guard at line 164) and `.necessity_lb`
(c2/audit/necessity_lb.py, main guard at line 116; it imports c2/audit/alg_star_exact.py, main guard at
line 177). On import they define functions and constants and add their folders to sys.path; det_game also
calls np.seterr(invalid="ignore", over="ignore") (as families.py does) and o1_lb sets OMP_NUM_THREADS=1 if
unset; none of them computes or writes anything.
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path
from types import SimpleNamespace

REPO = Path(__file__).resolve().parents[3]
ANALYSIS = REPO / "code" / "analysis"
ANALYSIS_OUT = ANALYSIS / "out"
C3 = REPO / "code" / "theory_checks" / "c3"
O1 = C3 / "o1"
C2 = REPO / "code" / "theory_checks" / "c2"
SIM = REPO / "code" / "sim"
SIM_OUT = SIM / "out"
CONFIGS = SIM / "configs"
DATA = Path("/mnt/data/datasets")

# import_ref: module name -> directory (all import-safe: no module-level work beyond sys.path)
REF_MODULES = {"core": C3, "pd": C3, "check_c4_lower": C3, "check_c3_upper": C3, "check_c3_benchmark": C3,
               "check_c5_la": C3, "fam": O1, "o1_ub": O1}
# MS3 C11: kept apart from REF_MODULES, whose key set the MS1/MS2 test of C9 fixes
MS3_REF_MODULES = {"o1_lb": O1}


def _on_path(directory: Path) -> None:
    d = str(directory)
    if d not in sys.path:
        sys.path.insert(0, d)


def _import_from(directory: Path, name: str):
    """Put `directory` on sys.path (once) and import the module `name` from it without writing
    bytecode. Raises ImportError if a module of that name was already imported from elsewhere."""
    _on_path(directory)
    old = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        mod = importlib.import_module(name)
    finally:
        sys.dont_write_bytecode = old
    src = getattr(mod, "__file__", None)
    if src is None or Path(src).resolve().parent != directory.resolve():
        raise ImportError(f"module {name!r} resolved to {src}, not to {directory}")
    return mod


def import_core():
    """Return the reference module `core` (code/theory_checks/c3/core.py)."""
    return _import_from(C3, "core")


def import_a9():
    """Return the analysis module `a9_notice_buffer` (code/analysis/a9_notice_buffer.py)."""
    return _import_from(ANALYSIS, "a9_notice_buffer")


def import_ref(name: str):
    """Return the reference module `name` of code/theory_checks/c3 (core, pd, check_c4_lower,
    check_c3_upper, check_c3_benchmark, check_c5_la) or c3/o1 (fam, o1_ub, o1_lb); C3 and O1 are put on
    sys.path once, since the scripts import each other by name."""
    allowed = {**REF_MODULES, **MS3_REF_MODULES}
    if name not in allowed:
        raise ValueError(f"import_ref: unknown reference module {name!r}; allowed {sorted(allowed)}")
    _on_path(O1)
    _on_path(C3)
    return _import_from(allowed[name], name)


def import_c2() -> SimpleNamespace:
    """Namespace with the C2 reference modules `model`, `families` and `det_game` (code/theory_checks/c2) and
    `model_switch_cost` and `necessity_lb` (c2/audit); C2 and C2/audit are put on sys.path once."""
    audit = C2 / "audit"
    _on_path(audit)
    _on_path(C2)
    return SimpleNamespace(model=_import_from(C2, "model"), families=_import_from(C2, "families"),
                           model_switch_cost=_import_from(audit, "model_switch_cost"),
                           det_game=_import_from(C2, "det_game"), necessity_lb=_import_from(audit, "necessity_lb"))
