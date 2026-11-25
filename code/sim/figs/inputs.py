"""Input files of the figure scripts (design/sim_spec_ms3.md §0 item 6, §8, §10 test_figs_ms3.py).

A figure script names every file it reads by its repository-relative path, e.g.
``"code/sim/out/e1/summary.json"`` or ``"code/analysis/out/a11_calibration.json"``, and reads it through an
``Inputs`` object:

    inp = Inputs()
    summary = inp.json("code/sim/out/e1/summary.json")
    ...
    style.save(fig, "fig5", data, sources=inp.sources)

``Inputs`` checks each name with ``style.check_source`` (only code/analysis/out/, code/theory_checks/**/out/ and
code/sim/out/), records it for ``save(..., sources=...)`` in the order of first use, and opens it under the input
root: the repository, or the folder named by the environment variable SUBLET_FIGS_IN_ROOT, which mirrors the
repository's layout (``<root>/code/sim/out/e1/summary.json``). Tests set SUBLET_FIGS_IN_ROOT to a temporary folder
of fixture files, so a script runs on fixture summaries with the same names it records for the real ones.

``path(name)`` gives the file to open, for readers other than JSON (text files, ``glob`` over run folders);
``glob(pattern)`` lists the repository-relative names under the input root that match a pattern, in sorted order;
``extract(name)`` reads a figure's own extract code/sim/out/figs/<name>.json under the input root (the
``--from-extract`` default of every figure script, figs.common.cli).
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from figs import style

ENV_IN_ROOT = "SUBLET_FIGS_IN_ROOT"
EXTRACT_DIR = "code/sim/out/figs"


def extract_name(name: str) -> str:
    """Repository-relative name of a figure's extract, where style.save writes it by default."""
    return f"{EXTRACT_DIR}/{name}.json"


def in_root() -> Path:
    """The folder that repository-relative input names resolve against: SUBLET_FIGS_IN_ROOT, else the repository."""
    env = os.environ.get(ENV_IN_ROOT)
    return Path(env).resolve() if env else style.REPO


class Inputs:
    """The files one figure script reads; ``sources`` is the list to pass to ``style.save``."""

    def __init__(self) -> None:
        self.root = in_root()
        self.sources: list[str] = []

    def _name(self, name: str | os.PathLike) -> str:
        rel = style.check_source(name)
        if rel not in self.sources:
            self.sources.append(rel)
        return rel

    def path(self, name: str | os.PathLike) -> Path:
        """The file to open for the repository-relative ``name``, recorded as a source."""
        return self.root / self._name(name)

    def json(self, name: str | os.PathLike) -> Any:
        """``name`` parsed as JSON, recorded as a source."""
        with open(self.path(name), encoding="utf-8") as f:
            return json.load(f)

    def extract(self, name: str) -> Any:
        """The extract of figure `name` (code/sim/out/figs/<name>.json under the input root) parsed as JSON,
        recorded as a source."""
        return self.json(extract_name(name))

    def text(self, name: str | os.PathLike) -> str:
        """``name`` as text, recorded as a source."""
        return self.path(name).read_text(encoding="utf-8")

    def glob(self, pattern: str) -> list[str]:
        """Repository-relative names under the input root matching ``pattern`` (sorted; not recorded until read)."""
        style.check_source(pattern.split("*", 1)[0] + "x")
        return sorted(p.relative_to(self.root).as_posix() for p in self.root.glob(pattern) if p.is_file())
