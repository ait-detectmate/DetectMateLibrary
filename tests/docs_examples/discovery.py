"""Discover in-scope docs examples for the harness."""
from __future__ import annotations

from pathlib import Path

from tests.docs_examples.extractor import Example, extract_examples

# Repo root = three levels up from this file (tests/docs_examples/discovery.py).
_REPO_ROOT = Path(__file__).resolve().parents[2]
_DOCS_ROOT = _REPO_ROOT / "docs"
_EXCLUDED_DIRS = ("superpowers", "design")


def _in_scope(md_path: Path) -> bool:
    rel = md_path.relative_to(_DOCS_ROOT)
    return rel.parts[0] not in _EXCLUDED_DIRS if rel.parts else True


def discover_examples() -> list[Example]:
    examples: list[Example] = []
    for md_path in _DOCS_ROOT.rglob("*.md"):
        if not _in_scope(md_path):
            continue
        examples.extend(extract_examples(str(md_path)))
    examples.sort(key=lambda e: (e.source_file, e.start_line))
    return examples


REPO_ROOT = _REPO_ROOT
