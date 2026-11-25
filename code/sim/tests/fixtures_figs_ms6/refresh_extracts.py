"""Refresh the fixture extracts tests/fixtures_figs_ms6/<name>.json of the MS6 figure tests (design/ms6_spec.md §2 U44;
README in inputs/).

Run from code/sim after any change to an MS6 figure script or to the input tree, inside the 3G scope like every
Python process:

    python tests/fixtures_figs_ms6/refresh_extracts.py [--check] [--only NAME ...]

Each MS6 figure script (figs/fig1_v2.py) is run in this process on the input tree tests/fixtures_figs_ms6/inputs/
(SUBLET_FIGS_IN_ROOT; a reduced run of the driver sublet/experiments/fig1_illustrative.py, not a result), with its PDF,
extract and preview written to a temporary folder (SUBLET_FIGS_PDF_DIR, SUBLET_FIGS_OUT_DIR), so finalize() runs on
each; the extract it writes is the fixture, unchanged. These extracts are therefore reduced-run values too, never
results.

--check writes nothing and exits 1 if a fixture differs from what it would be refreshed to (listing it); --only
limits the run to the named figures. test_fig1v2.py::test_build_on_the_input_tree_matches_the_fixture fails on a stale
fixture and names this script.
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

HERE = Path(__file__).resolve().parent                 # code/sim/tests/fixtures_figs_ms6
SIM = HERE.parents[1]                                   # code/sim
if str(SIM) not in sys.path:
    sys.path.insert(0, str(SIM))

IN_ROOT = HERE / "inputs"
SCRIPTS = {"fig1v2": "figs.fig1_v2"}
ENV = ("SUBLET_FIGS_IN_ROOT", "SUBLET_FIGS_PDF_DIR", "SUBLET_FIGS_OUT_DIR", "SUBLET_FIGS_TABLES_DIR")


def text_of(payload: dict) -> str:
    """The file text, as style.save writes an extract."""
    return json.dumps(payload, indent=1, allow_nan=False) + "\n"


def build(names: list[str]) -> dict[str, str]:
    """{name: fixture text}: each script's main() on the input tree, outputs in a temporary folder."""
    out = {}
    old = {k: os.environ.get(k) for k in ENV}
    with tempfile.TemporaryDirectory(prefix="refresh_extracts_ms6_") as tmp:
        t = Path(tmp)
        os.environ.update({"SUBLET_FIGS_IN_ROOT": str(IN_ROOT), "SUBLET_FIGS_PDF_DIR": str(t / "pdf"),
                           "SUBLET_FIGS_OUT_DIR": str(t / "out"), "SUBLET_FIGS_TABLES_DIR": str(t / "tables")})
        try:
            for name in names:
                mod = importlib.import_module(SCRIPTS[name])
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")        # GlyphSizeWarning: for full-size figures, not for the fixtures
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
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--check", action="store_true", help="write nothing; exit 1 if a fixture is stale")
    ap.add_argument("--only", nargs="+", metavar="NAME", help="only these figures")
    args = ap.parse_args(argv)
    names = args.only or list(SCRIPTS)
    bad = [n for n in names if n not in SCRIPTS]
    if bad:
        ap.error(f"unknown figure(s) {bad}; known: {list(SCRIPTS)}")
    texts = build(names)
    stale = []
    for name in names:
        dst = HERE / f"{name}.json"
        if not dst.is_file() or dst.read_text() != texts[name]:
            stale.append(name)
            if not args.check:
                dst.write_text(texts[name])
    verb = "stale" if args.check else "refreshed"
    print(f"[refresh_extracts ms6] {verb}: {stale or 'none'} (of {len(names)})")
    return 1 if (args.check and stale) else 0


if __name__ == "__main__":
    sys.exit(main())
