"""Environment of the audit scripts of the full-model guard (code/sim/audit/; design/theory/audit_guard.md, section
"Audit of the full-model guard"; outputs in code/sim/out/audit_fm/, written by run_all.sh).

The folder: x1_load_same_list.py (X1, finding F1), x3_obs_mutation.py (X3, F2), x2_random_search.py (X2, forced
aborts on the rich instances; with AUDIT_WC=1 the F5 probe), x2p_effect.py (F5's effect on G), x4_natural_aborts.py
(X4), x7_reclaim_ms.py and x7b_reclaim_day.py (X7, X7b: violations 'reclaim'), x8_reserve_tight.py (X8, the reserve
is attained), identity.py (the fixes leave the Q44 study's A8 runs unchanged) and run_all.sh (each step in its own
3G scope, one worker). The scripts are run from this folder (run_all.sh does so).

Puts code/sim, code/sim/tests, code/theory_checks/c3, c3/o1 and code/analysis on sys.path, as conftest.py does, sets
OMP_NUM_THREADS=1 if unset and imports tests/test_guard.py as TG for its instance builders (_rich_instance, _ms,
_full, _q_slot, _N) and its random inner policies (_RandomInner). The scripts check the guard from the engine's
ledger, lease records and instance only, plus the a-hat(t), R(t) and budgets that the guard logs; they do not use
the oracles of test_guard.py.

route_over_wc(on) is the probe of finding F5 (not applied in guard.py): it makes T0gBound route G over W^C (every
counted replica) instead of W^B by marking every replica's lease as surely alive in T0gBound._replicas' output,
which is the only use of that mask (evaluate's W^B); the guard's code is not changed."""
import os
import sys
from pathlib import Path

sys.dont_write_bytecode = True
os.environ.setdefault("OMP_NUM_THREADS", "1")
SIM = Path(__file__).resolve().parents[1]
REPO = SIM.parents[1]
C3 = REPO / "code" / "theory_checks" / "c3"
OUT = SIM / "out" / "audit_fm"
for _d in (REPO / "code" / "analysis", C3 / "o1", C3, SIM / "tests", SIM):
    while str(_d) in sys.path:
        sys.path.remove(str(_d))
    sys.path.insert(0, str(_d))

import numpy as np  # noqa: E402

import test_guard as TG  # noqa: E402,F401  (helpers: _rich_instance, _RandomInner, _ms, _full, _q_slot, _N)
from sublet.algos import guard as _guard  # noqa: E402

_REPLICAS = _guard.T0gBound._replicas


def _replicas_wc(self, obs, actions):
    st = _REPLICAS(self, obs, actions)
    if st is None:
        return None
    reps, counted, n_unc = st
    return [(j, l, lid, np.ones(len(inB), dtype=bool), lo, hi) for (j, l, lid, inB, lo, hi) in reps], counted, n_unc


def route_over_wc(on: bool) -> None:
    """F5 probe: T0gBound's G over W^C (on) or W^B as built (off)."""
    _guard.T0gBound._replicas = _replicas_wc if on else _REPLICAS
