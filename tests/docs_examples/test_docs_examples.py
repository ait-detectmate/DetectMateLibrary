import os as _os

import pytest

from tests.docs_examples.discovery import REPO_ROOT, discover_examples
from tests.docs_examples import runners

_EXAMPLES = discover_examples()


def test_discovery_finds_json_parser_doc():
    sources = {ex.source_file for ex in _EXAMPLES}
    assert any(s.endswith("docs/parsers/json_parser.md") for s in sources)


def test_discovery_excludes_superpowers():
    assert not any("docs/superpowers/" in ex.source_file for ex in _EXAMPLES)
    assert not any("docs/design/" in ex.source_file for ex in _EXAMPLES)


# Per-file shared namespaces so multi-block python tutorials run as a unit.
_NAMESPACES: dict[str, dict] = {}


def _example_id(ex):
    rel = _os.path.relpath(ex.source_file, REPO_ROOT)
    return f"{rel}:{ex.start_line}"


@pytest.fixture(autouse=True)
def _run_from_repo_root(monkeypatch):
    monkeypatch.chdir(REPO_ROOT)


@pytest.mark.parametrize("example", _EXAMPLES, ids=[_example_id(e) for e in _EXAMPLES])
def test_doc_example(example):
    namespace = _NAMESPACES.setdefault(example.source_file, {})
    try:
        runners.dispatch(example, namespace)
    except Exception as exc:  # noqa: BLE001 - re-raise with location context
        raise AssertionError(
            f"Doc example {_example_id(example)} ({example.language}) failed:\n{exc}"
        ) from exc
