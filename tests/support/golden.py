"""Golden files: what an e2e chain produced on a fixed input, kept in
tests/test_data/golden/ together with the settings that produced it.

The e2e tests compare a fresh run with its golden file (fixture `golden` in
tests/e2e/conftest.py). `pytest --update-golden` rewrites the files instead;
the change then shows up in the diff and is reviewed like code. CI refuses
the option.
"""
import json
from pathlib import Path
from typing import Any

from tests.support.paths import TEST_DATA

GOLDEN_DIR = TEST_DATA / "golden"
REGENERATE = "uv run pytest tests/e2e -m '' --update-golden"


def path_of(name: str) -> Path:
    return GOLDEN_DIR / f"{name}.json"


def as_json(record: dict[str, Any]) -> dict[str, Any]:
    """The record as it reads back from its file (tuples become lists, keys
    strings)."""
    result: dict[str, Any] = json.loads(json.dumps(record))
    return result


def read(name: str) -> dict[str, Any]:
    with open(path_of(name)) as f:
        result: dict[str, Any] = json.load(f)
    return result


def write(name: str, record: dict[str, Any]) -> Path:
    path = path_of(name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(as_json(record), indent=2) + "\n")
    return path
