"""Runs every documentation example under docs/examples/ as a test.

Each .py file there is a runnable version of a code snippet shown in the
docs. Executing it here ensures the documented examples stay in sync
with the current library API.
"""

from pathlib import Path
import pytest
import runpy

home = Path(__file__).resolve().parents[2]
examples = home / "docs" / "examples"

# Extra markers for the examples that are slow or need something besides the library.
EXTRA_MARKS = {
    "alert_aggregators/alertbert.py": [pytest.mark.slow, pytest.mark.needs_cxx],
    "detectors/deeplog.py": [pytest.mark.slow],
    "detectors/logbert.py": [pytest.mark.slow],
    "others/quickstart_2.py": [pytest.mark.needs_redis],
    "others/schemas.py": [pytest.mark.needs_mongo],
}

example_files = [
    pytest.param(path, marks=EXTRA_MARKS.get(path.relative_to(examples).as_posix(), []))
    for path in sorted(examples.rglob("*.py"))
]


@pytest.fixture(autouse=True)
def _run_from_repository_root(monkeypatch):
    """The examples use paths relative to the repository root, as the docs show
    them."""
    monkeypatch.chdir(home)


@pytest.mark.docs
@pytest.mark.parametrize("example", example_files)
def test_doc_example_runs(example):
    runpy.run_path(str(example), run_name="__main__")
