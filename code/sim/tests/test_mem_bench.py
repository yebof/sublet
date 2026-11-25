"""Tests of bench/mem_bench.py, the memory benchmark of design/sim_spec.md §9.3 (§10 S37): the skip
threshold and cap units, the families solved on the merged relaxation, and the 7-day size records."""
import importlib.util

import pytest

from fixtures import SIM

from sublet.opt.relax import merged_relaxation


def _mem_bench():
    spec = importlib.util.spec_from_file_location("mem_bench", SIM / "bench" / "mem_bench.py")
    mb = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mb)
    return mb


def test_constants():
    """§10 S37: SKIP_ABOVE_MB = 2560 MiB, the same unit as CAP_MB = 3072 for the 3G cap; the E7 families
    (and only they) are solved on the merged relaxation; every E7 case is an LP."""
    mb = _mem_bench()
    assert mb.SKIP_ABOVE_MB == 2560.0 and mb.CAP_MB == 3072.0
    assert mb.MERGED_FAMILIES == ("e7r", "e7f", "e7s")
    assert set(mb.MERGED_FAMILIES) <= set(mb.FAMILIES)
    for fam in mb.MERGED_FAMILIES:
        assert {m for m, _, _ in mb.FAMILIES[fam][1]} == {"lp"}, fam


@pytest.mark.needs_a12
def test_estimate_family_records(tmp_path, monkeypatch):
    """§10 S37: estimate_family of an E7 family (e7s, 1 day) records merged: true, the site counts before
    and after merged_relaxation and estimate_size of both models ('estimates' = merged, the model the E7
    cases solve; 'estimates_unmerged'); e1 records merged: false and the unmerged estimates only. The
    files go to OUT (here tmp_path)."""
    import json
    from sublet import config as C
    from sublet.instance import build_instance
    from sublet.lender import Lender
    from sublet.opt.milp import estimate_size
    mb = _mem_bench()
    monkeypatch.setattr(mb, "OUT", tmp_path)
    rec = mb.estimate_family("e7s", 1)
    assert rec["status"] == "ok", rec.get("traceback")
    assert rec["merged"] is True and rec["n_sites_merged"] < rec["n_sites_unmerged"]
    assert set(rec["estimates"]) == set(rec["estimates_unmerged"]) == {"lp/slow"}
    m, u = rec["estimates"]["lp/slow"], rec["estimates_unmerged"]["lp/slow"]
    assert 0 < m["n_vars"] < u["n_vars"] and 0 < m["nnz"] < u["nnz"]
    assert json.loads((tmp_path / "est_e7s_1d.json").read_text())["n_sites_merged"] == rec["n_sites_merged"]
    # the recorded sizes are those of the instance and of its merged relaxation
    inst = build_instance(mb.case_config("e7s", 1))
    sched = Lender(inst, C.lender_model(inst.config), C.rng_streams(inst.seed)["lender"]).static_schedule()
    inst_m, sched_m, _ = merged_relaxation(inst, sched)
    assert (inst.m, inst_m.m) == (rec["n_sites_unmerged"], rec["n_sites_merged"])
    assert estimate_size(inst_m, sched_m, grid="slow")["nnz"] == m["nnz"]
    assert estimate_size(inst, sched, grid="slow")["nnz"] == u["nnz"]
    rec = mb.estimate_family("e1", 1)
    assert rec["status"] == "ok", rec.get("traceback")
    assert rec["merged"] is False and "estimates_unmerged" not in rec and "n_sites_merged" not in rec
    assert set(rec["estimates"]) == {f"{meth}/{gr}" for meth in ("lp", "milp", "eager") for gr in ("slow", "fast")}
