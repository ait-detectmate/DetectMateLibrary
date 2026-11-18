"""Tests for detectmatelibrary.tools.workspace.create_workspace: the `mate
create` CLI, called in-process with a patched sys.argv.

That the installed console script runs and that the generated tests pass
is checked in tests/e2e/test_workspace_cli.py.
"""
import json
import sys

import pytest

from detectmatelibrary.tools.workspace import create_workspace
from detectmatelibrary.tools.workspace.utils import normalize_package_name

ROOT_FILES = [
    "LICENSE.md", ".gitignore", ".pre-commit-config.yaml", "README.md", "pyproject.toml", "data.json",
]


def _mate(monkeypatch, *args: str) -> None:
    monkeypatch.setattr(sys, "argv", ["mate", *args])
    create_workspace.main()


@pytest.mark.parametrize("type_, name, class_name", [
    ("parser", "myParser", "MyParser"),
    ("detector", "myDetector", "MyDetector"),
    ("alert_aggregator", "myAlertAggregator", "MyAlertAggregator"),
])
def test_create_writes_the_workspace(monkeypatch, tmp_path, type_, name, class_name):
    _mate(monkeypatch, "create", "--type", type_, "--name", name, "--dir", str(tmp_path))

    package = normalize_package_name(name)
    assert sorted(path.name for path in (tmp_path / package).glob("*.py")) == ["__init__.py", f"{package}.py"]
    assert f"class {class_name}(" in (tmp_path / package / f"{package}.py").read_text()
    assert all((tmp_path / file_name).exists() for file_name in ROOT_FILES)
    assert (tmp_path / "tests" / f"test_{name}.py").exists()
    with open(create_workspace.DATA_FILES[type_]) as f, open(tmp_path / "data.json") as g:
        assert json.load(g) == json.load(f)


def test_a_dash_in_the_name_gives_a_valid_package(monkeypatch, tmp_path):
    _mate(monkeypatch, "create", "--type", "parser", "--name", "custom-parser", "--dir", str(tmp_path))

    assert (tmp_path / "custom_parser" / "custom_parser.py").exists()
    test_file = tmp_path / "tests" / "test_custom-parser.py"
    assert "from custom_parser.custom_parser import " in test_file.read_text()


def test_an_existing_package_directory_is_an_error(monkeypatch, tmp_path, capsys):
    (tmp_path / "existing").mkdir()

    with pytest.raises(SystemExit) as exit_:
        _mate(monkeypatch, "create", "--type", "parser", "--name", "existing", "--dir", str(tmp_path))

    assert exit_.value.code == 1
    assert "already exists" in capsys.readouterr().err
    assert list((tmp_path / "existing").iterdir()) == []
