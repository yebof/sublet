"""Refresh the fixture extracts tests/fixtures_figs/<name>.json of the MS3 figure tests (README in inputs/).

Run from code/sim after any change to a figure script, inside the 3G scope like every Python process:

    python tests/fixtures_figs/refresh_extracts.py [--check] [--only NAME ...] [--real DIR]

Two groups of fixture extracts, each refreshed the way it was made:

- Figs. 5-7 and the E1, E2, E6, E10 supplementary panels (test_figs_ms3_exp.py): every script is run in this process
  on the synthetic input tree tests/fixtures_figs/inputs/ (SUBLET_FIGS_IN_ROOT), with its PDF, extract, preview and
  table written to a temporary folder (SUBLET_FIGS_PDF_DIR, SUBLET_FIGS_OUT_DIR, SUBLET_FIGS_TABLES_DIR), so finalize()
  runs on each; the extract it writes is the fixture, except that sf_e6a's cell table keeps one block (MaaS,
  lambda' = a5, mu = 1) to stay small. These extracts are synthetic like the tree.
- Figs. 1-3 and sf_e11_inst, sf_e11_fam, sf_e11_guard (test_figs_ms3.py): copies of the real extracts in
  code/sim/out/figs/ (or --real DIR), which the scripts write when run on the real inputs; sf_e11_fam keeps the
  all_modes entry F1_m2_r16 only and sf_e11_guard every 25th sorted certificate ratio plus the last, each with a
  `fixture_note`. Rerun the U17a scripts on the real inputs first.

--check writes nothing and exits 1 if a fixture differs from what it would be refreshed to (listing it); --only
limits the run to the named figures. test_figs_ms3_exp.py::test_build_reads_only_result_files_and_matches_the_extract
and test_figs_ms3.py::test_normal_mode_on_the_versioned_inputs fail on a stale fixture and name this script.
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

HERE = Path(__file__).resolve().parent                 # code/sim/tests/fixtures_figs
SIM = HERE.parents[1]                                   # code/sim
if str(SIM) not in sys.path:
    sys.path.insert(0, str(SIM))

IN_ROOT = HERE / "inputs"
REAL_DIR = SIM / "out" / "figs"
SYNTHETIC = {"fig5": "figs.fig5_e1_e10", "fig6": "figs.fig6_e10", "fig7": "figs.fig7_e2_e6",
             "sf_e1_sched": "figs.supp.sf_e1_sched", "sf_e1_rotation": "figs.supp.sf_e1_rotation",
             "sf_e2_por": "figs.supp.sf_e2_por", "sf_e2_mu_ep": "figs.supp.sf_e2_mu_ep",
             "sf_e2_mu_cost": "figs.supp.sf_e2_mu_cost", "sf_e2_pool": "figs.supp.sf_e2_pool",
             "sf_e6a": "figs.supp.sf_e6a", "sf_e6b": "figs.supp.sf_e6b", "sf_e10_rho": "figs.supp.sf_e10_rho",
             "sf_e10_cross": "figs.supp.sf_e10_cross", "sf_e10b": "figs.supp.sf_e10b"}
REAL = ("fig1", "fig2", "fig3", "sf_e11_inst", "sf_e11_fam", "sf_e11_guard")
ENV = ("SUBLET_FIGS_IN_ROOT", "SUBLET_FIGS_PDF_DIR", "SUBLET_FIGS_OUT_DIR", "SUBLET_FIGS_TABLES_DIR")
GUARD_EVERY = 25
FAM_KEEP = ("F1", "F1_m2_r16:F-ad")


def text_of(payload: dict) -> str:
    """The file text, as style.save writes an extract."""
    return json.dumps(payload, indent=1, allow_nan=False) + "\n"


def trim_e6a(payload: dict) -> dict:
    t = payload["data"]["table"]
    payload["data"]["table"] = [r for r in t if r["group"] == "maas" and r["lam"] == "a5" and r["mu"] == 1.0]
    return payload


def trim_fam(payload: dict) -> dict:
    fam, key = FAM_KEEP
    d = payload["data"]
    d["all_modes"] = {fam: {key: d["all_modes"][fam][key]}}
    d["fixture_note"] = f"all_modes cut to {key.split(':')[0]} (tests/fixtures_figs)"
    return payload


def trim_guard(payload: dict) -> dict:
    d = payload["data"]
    for grp in ("c", "c_other"):
        for v in d[grp].values():
            n = len(v["sorted"])
            idx = list(range(0, n, GUARD_EVERY))
            if n - 1 not in idx:
                idx.append(n - 1)
            v["sorted"] = [v["sorted"][i] for i in idx]
            v["model"] = [v["model"][i] for i in idx]
            v["n"] = len(idx)
    d["fixture_note"] = f"thinned: every {GUARD_EVERY}th sorted certificate ratio (tests/fixtures_figs)"
    return payload


TRIM = {"sf_e6a": trim_e6a, "sf_e11_fam": trim_fam, "sf_e11_guard": trim_guard}


def build_synthetic(names: list[str]) -> dict[str, str]:
    """{name: fixture text} of the synthetic group: each script's main() on the input tree, outputs in a temporary
    folder."""
    out = {}
    old = {k: os.environ.get(k) for k in ENV}
    with tempfile.TemporaryDirectory(prefix="refresh_extracts_") as tmp:
        t = Path(tmp)
        os.environ.update({"SUBLET_FIGS_IN_ROOT": str(IN_ROOT), "SUBLET_FIGS_PDF_DIR": str(t / "pdf"),
                           "SUBLET_FIGS_OUT_DIR": str(t / "out"), "SUBLET_FIGS_TABLES_DIR": str(t / "tables")})
        try:
            for name in names:
                mod = importlib.import_module(SYNTHETIC[name])
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")        # GlyphSizeWarning: not needed for the fixtures
                    mod.main([])
                payload = json.loads((t / "out" / f"{name}.json").read_text())
                out[name] = text_of(TRIM.get(name, lambda p: p)(payload))
        finally:
            for k, v in old.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v
    return out


def copy_real(names: list[str], real: Path) -> dict[str, str]:
    """{name: fixture text} of the real-extract group."""
    out = {}
    for name in names:
        p = real / f"{name}.json"
        if not p.is_file():
            raise SystemExit(f"{p} is missing: run the figure script on the real inputs first")
        out[name] = text_of(TRIM.get(name, lambda q: q)(json.loads(p.read_text())))
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--check", action="store_true", help="write nothing; exit 1 if a fixture is stale")
    ap.add_argument("--only", nargs="+", metavar="NAME", help="only these figures")
    ap.add_argument("--real", type=Path, default=REAL_DIR, help=f"folder of the real extracts (default {REAL_DIR})")
    args = ap.parse_args(argv)
    names = args.only or list(SYNTHETIC) + list(REAL)
    bad = [n for n in names if n not in SYNTHETIC and n not in REAL]
    if bad:
        ap.error(f"unknown figure(s) {bad}; known: {list(SYNTHETIC) + list(REAL)}")
    texts = {**build_synthetic([n for n in names if n in SYNTHETIC]),
             **copy_real([n for n in names if n in REAL], args.real)}
    stale = []
    for name in names:
        dst = HERE / f"{name}.json"
        if not dst.is_file() or dst.read_text() != texts[name]:
            stale.append(name)
            if not args.check:
                dst.write_text(texts[name])
    verb = "stale" if args.check else "refreshed"
    print(f"[refresh_extracts] {verb}: {stale or 'none'} (of {len(names)})")
    return 1 if (args.check and stale) else 0


if __name__ == "__main__":
    sys.exit(main())
