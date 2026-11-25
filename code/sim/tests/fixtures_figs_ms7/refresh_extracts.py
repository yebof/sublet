"""Refresh the fixture extracts tests/fixtures_figs_ms7/<name>.json of the MS7 figure and table tests (Fig. 3 v3,
figs/fig4_v3.py; Tables IV and V, figs/table3_v3.py and figs/table5_alglb.py; design/ms7/w_spec.md §4, unit W-G2;
README in inputs/).

Run from code/sim after any change to one of the three scripts or to the input tree, inside the 3G scope like every
Python process:

    python tests/fixtures_figs_ms7/refresh_extracts.py [--check] [--only NAME ...]

Each script of SCRIPTS runs in this process on the input tree tests/fixtures_figs_ms7/inputs/ (SUBLET_FIGS_IN_ROOT;
reduced-mode outputs of the MS7 drivers and their analyses, not results), its PDF or float, extract and preview written
to a temporary folder (SUBLET_FIGS_PDF_DIR, SUBLET_FIGS_OUT_DIR), so finalize() runs on the figure; the extract it
writes is the fixture, unchanged. These extracts are reduced-mode values, never results. --check writes nothing and
exits 1 if a fixture differs from what it would be refreshed to (listing it); --only limits the run to the named
scripts. tests/test_figs_ms7_fig4.py and tests/test_tables_ms7.py fail on a stale fixture and name this script.
"""
from __future__ import annotations

import argparse
import importlib
import json
import os
import sys
import tempfile
import warnings
from pathlib import Path

HERE = Path(__file__).resolve().parent                 # code/sim/tests/fixtures_figs_ms7
SIM = HERE.parents[1]                                   # code/sim
if str(SIM) not in sys.path:
    sys.path.insert(0, str(SIM))

IN_ROOT = HERE / "inputs"
SCRIPTS: dict[str, tuple[str, list]] = {               # name: (module, argv)
    "fig4v3": ("figs.fig4_v3", []),
    "table3_v3": ("figs.table3_v3", []),               # the float goes to SUBLET_FIGS_PDF_DIR (float_dir)
    "table5_alglb": ("figs.table5_alglb", []),
}
ENV = ("SUBLET_FIGS_IN_ROOT", "SUBLET_FIGS_PDF_DIR", "SUBLET_FIGS_OUT_DIR", "SUBLET_FIGS_TABLES_DIR")


def text_of(payload: dict) -> str:
    """The file text, as style.save and the table scripts write an extract."""
    return json.dumps(payload, indent=1, allow_nan=False) + "\n"


def build(names: list[str]) -> dict[str, str]:
    """{name: fixture text}: each script's main() on the input tree, outputs in a temporary folder."""
    out = {}
    old = {k: os.environ.get(k) for k in ENV}
    with tempfile.TemporaryDirectory(prefix="refresh_extracts_ms7_") as tmp:
        t = Path(tmp)
        os.environ.update({"SUBLET_FIGS_IN_ROOT": str(IN_ROOT), "SUBLET_FIGS_PDF_DIR": str(t / "pdf"),
                           "SUBLET_FIGS_OUT_DIR": str(t / "out"), "SUBLET_FIGS_TABLES_DIR": str(t / "tables")})
        try:
            for name in names:
                module, argv = SCRIPTS[name]
                mod = importlib.import_module(module)
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")        # GlyphSizeWarning: for full-size figures, not for the fixtures
                    mod.main(list(argv))
                out[name] = text_of(json.loads((t / "out" / f"{name}.json").read_text()))
        finally:
            for k, v in old.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true", help="write nothing; exit 1 if a fixture is stale")
    ap.add_argument("--only", nargs="+", choices=sorted(SCRIPTS), default=None)
    a = ap.parse_args(argv)
    names = a.only or list(SCRIPTS)
    new = build(names)
    stale = [n for n in names if not (HERE / f"{n}.json").is_file() or (HERE / f"{n}.json").read_text() != new[n]]
    if a.check:
        for n in stale:
            print(f"stale: tests/fixtures_figs_ms7/{n}.json")
        return 1 if stale else 0
    for n in names:
        (HERE / f"{n}.json").write_text(new[n])
    print(f"[refresh_extracts ms7] wrote {len(names)} fixture extract(s) ({len(stale)} changed)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
