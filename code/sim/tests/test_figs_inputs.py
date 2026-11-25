"""figs.inputs: repository-relative input names, the SUBLET_FIGS_IN_ROOT override and the source list."""
import json

import pytest

from figs import inputs, style


def test_default_root_is_repository(monkeypatch):
    monkeypatch.delenv(inputs.ENV_IN_ROOT, raising=False)
    inp = inputs.Inputs()
    assert inp.root == style.REPO
    assert inp.path("code/analysis/out/x.json") == style.REPO / "code/analysis/out/x.json"


def test_override_root_and_sources(tmp_path, monkeypatch):
    f = tmp_path / "code/sim/out/e1/summary.json"
    f.parent.mkdir(parents=True)
    f.write_text(json.dumps({"a": 1}))
    (tmp_path / "code/sim/out/e1/b.json").write_text("{}")
    monkeypatch.setenv(inputs.ENV_IN_ROOT, str(tmp_path))
    inp = inputs.Inputs()
    assert inp.json("code/sim/out/e1/summary.json") == {"a": 1}
    assert inp.json("code/sim/out/e1/summary.json") == {"a": 1}
    assert inp.sources == ["code/sim/out/e1/summary.json"]
    assert inp.glob("code/sim/out/e1/*.json") == ["code/sim/out/e1/b.json", "code/sim/out/e1/summary.json"]


@pytest.mark.parametrize("name", ["code/sim/configs/toy.json", "design/Sublet_design.md",
                                  "code/theory_checks/c2/model.py", "code/sim/out/../configs/toy.json"])
def test_rejects_names_outside_result_folders(name):
    with pytest.raises(style.StyleError):
        inputs.Inputs().path(name)
    with pytest.raises(style.StyleError):
        inputs.Inputs().glob(name)
