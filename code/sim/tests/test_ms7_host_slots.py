"""MS7 addition C57 (design/ms7/registration.md §5): MS3_HOST_SLOTS, the host's slots of the MS3 semaphore.

ms3_common.host_slots() and ms3_lib.sh read the same variable (1..6, default 4); max_workers is
min(MS3_WORKERS, host_slots()); without the variable every value is the MS3 one (test_ms3_common.test_max_workers).
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from sublet.experiments import ms3_common as mc

LIB = Path(mc.__file__).with_name("ms3_lib.sh")


def _e11(root: Path) -> Path:
    (root / "out" / "e11").mkdir(parents=True)
    (root / "out" / "e11" / "summary.json").write_text("{}")
    return root


def test_host_slots_default_and_range(tmp_path, monkeypatch):
    monkeypatch.delenv("MS3_HOST_SLOTS", raising=False)
    monkeypatch.delenv("MS3_WORKERS", raising=False)
    assert mc.host_slots() == mc.MAX_SLOTS == 4
    root = _e11(tmp_path)
    assert mc.max_workers(root) == 4
    monkeypatch.setenv("MS3_HOST_SLOTS", "6")
    assert mc.host_slots() == 6 and mc.max_workers(root) == 6
    for w, n in (("2", 2), ("9", 6), ("0", 0), ("5", 5)):
        monkeypatch.setenv("MS3_WORKERS", w)
        assert mc.max_workers(root) == n
    for bad in ("0", "7", "-1", "x"):
        monkeypatch.setenv("MS3_HOST_SLOTS", bad)
        with pytest.raises(ValueError):
            mc.host_slots()
    monkeypatch.setenv("MS3_HOST_SLOTS", "3")
    monkeypatch.delenv("MS3_WORKERS", raising=False)
    assert mc.max_workers(root) == 3
    assert mc.max_workers(tmp_path / "none") == 0           # no E11 summary: no job runs


def _source(env_slots):
    env = {k: v for k, v in os.environ.items() if k != "MS3_HOST_SLOTS"}
    if env_slots is not None:
        env["MS3_HOST_SLOTS"] = env_slots
    script = f'source "{LIB}"; echo "N=$MS3_N_SLOTS H=$MS3_HOST_SLOTS"'
    return subprocess.run(["bash", "-c", script], capture_output=True, text=True, env=env, timeout=60)


def test_ms3_lib_reads_the_same_variable():
    r = _source(None)
    assert r.returncode == 0 and r.stdout.strip() == "N=4 H=4"
    r = _source("6")
    assert r.returncode == 0 and r.stdout.strip() == "N=6 H=6"
    for bad in ("7", "0", "x"):
        r = _source(bad)
        assert r.returncode == 2 and "MS3_HOST_SLOTS must be in 1..6" in r.stderr
