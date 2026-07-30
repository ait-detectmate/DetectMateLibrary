"""Runs every documentation example under docs/examples/ as a test.

Each .py file there is a runnable version of a code snippet shown in the
docs. Executing it here ensures the documented examples stay in sync with
the current library API.
"""

from pathlib import Path
import pytest
import runpy



home = Path(__file__).resolve().parents[2]
examples = home / "docs" / "examples"

example_files = sorted(examples.rglob("*.py"))

@pytest.mark.parametrize("example", example_files)
def test_doc_example_runs(example):
    runpy.run_path(str(example), run_name="__main__")


for i in example_files:
    print(f"{i} \n")
