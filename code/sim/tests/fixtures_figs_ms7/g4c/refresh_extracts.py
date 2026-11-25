"""Refresh the fixture extracts tests/fixtures_figs_ms7/g4c/<name>.json of the tests of the X3 supplementary scripts
sf_s1_v2, sf_e5_v2, sf_e8_v2 and sf_e9_v2 (tests/test_figs_ms7_c.py; design/ms7/w_spec.md §4, unit W-G4, writer C;
README in inputs/).

Run from code/sim after any change to one of the four scripts, to figs/supp/ms7_x3_lib.py or to the input tree, inside
the 3G scope like every Python process:

    python tests/fixtures_figs_ms7/g4c/refresh_extracts.py [--check] [--only NAME ...]

Each script of SCRIPTS runs in this process on the input tree tests/fixtures_figs_ms7/g4c/inputs/ (SUBLET_FIGS_IN_ROOT;
reduced-mode outputs of the X3 drivers and the frozen analysis on them, not results), its PDF, tables, extract and
preview written to a temporary folder (SUBLET_FIGS_PDF_DIR, SUBLET_FIGS_OUT_DIR, SUBLET_FIGS_TABLES_DIR), so finalize()
runs on the figure; the extract it writes is the fixture, unchanged. These extracts are reduced-mode values, never
results. --check writes nothing and exits 1 if a fixture differs from what it would be refreshed to (listing it);
--only limits the run to the named scripts. tests/test_figs_ms7_c.py fails on a stale fixture and names this script.
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

HERE = Path(__file__).resolve().parent                 # code/sim/tests/fixtures_figs_ms7/g4c
SIM = HERE.parents[2]                                   # code/sim
if str(SIM) not in sys.path:
    sys.path.insert(0, str(SIM))

IN_ROOT = HERE / "inputs"
SCRIPTS: dict[str, str] = {"sf_s1_v2": "figs.supp.sf_s1_v2", "sf_e5_v2": "figs.supp.sf_e5_v2",
                           "sf_e8_v2": "figs.supp.sf_e8_v2", "sf_e9_v2": "figs.supp.sf_e9_v2"}
ENV = ("SUBLET_FIGS_IN_ROOT", "SUBLET_FIGS_PDF_DIR", "SUBLET_FIGS_OUT_DIR", "SUBLET_FIGS_TABLES_DIR")


def text_of(payload: dict) -> str:
    """The file text, as style.save writes an extract."""
    return json.dumps(payload, indent=1, allow_nan=False) + "\n"


def build(names: list[str]) -> dict[str, str]:
    """{name: fixture text}: each script's main() on the input tree, outputs in a temporary folder."""
    out = {}
    old = {k: os.environ.get(k) for k in ENV}
    with tempfile.TemporaryDirectory(prefix="refresh_extracts_g4c_") as tmp:
        t = Path(tmp)
        os.environ.update({"SUBLET_FIGS_IN_ROOT": str(IN_ROOT), "SUBLET_FIGS_PDF_DIR": str(t / "pdf"),
                           "SUBLET_FIGS_OUT_DIR": str(t / "out"), "SUBLET_FIGS_TABLES_DIR": str(t / "tables")})
        try:
            for name in names:
                mod = importlib.import_module(SCRIPTS[name])
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")        # GlyphSizeWarning: not needed for the fixtures
                    mod.main([])
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
            print(f"stale: tests/fixtures_figs_ms7/g4c/{n}.json")
        return 1 if stale else 0
    for n in names:
        (HERE / f"{n}.json").write_text(new[n])
    print(f"[refresh_extracts g4c] wrote {len(names)} fixture extract(s) ({len(stale)} changed)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
