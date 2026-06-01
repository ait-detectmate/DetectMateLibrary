"""Pure markdown extraction for the docs example harness.

Splits a markdown file into fenced code blocks (``Example`` records) and parses
the optional ``<!-- docs-test: ... -->`` marker that may precede a block.
"""
from __future__ import annotations

from dataclasses import dataclass
import re

_MARKER_RE = re.compile(
    r"<!--\s*docs-test:\s*(skip|run|expect-error)(?:=(.*?))?\s*-->"
)


@dataclass(frozen=True)
class Marker:
    kind: str  # "skip" | "run" | "expect-error"
    substring: str | None = None


@dataclass(frozen=True)
class Example:
    source_file: str
    start_line: int  # 1-based line number of the opening ``` fence
    language: str  # lowercased fence info string, e.g. "python"; "" if none
    code: str
    marker: Marker | None


def parse_marker(line: str) -> Marker | None:
    match = _MARKER_RE.search(line)
    if not match:
        return None
    kind, substring = match.group(1), match.group(2)
    return Marker(kind=kind, substring=substring if substring else None)
