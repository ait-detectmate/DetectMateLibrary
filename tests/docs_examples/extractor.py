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


_FENCE_RE = re.compile(r"^([`~]{3,})\s*([^\s`]*)")


def _marker_above(lines: list[str], fence_index: int) -> Marker | None:
    """Look at the non-blank line directly above the fence (allowing a single
    blank line between marker and fence).

    Return its marker, or None.
    """
    idx = fence_index - 1
    if idx >= 0 and lines[idx].strip() == "":
        idx -= 1
    if idx < 0:
        return None
    return parse_marker(lines[idx])


def extract_examples(md_path: str) -> list[Example]:
    with open(md_path, "r", encoding="utf-8") as fh:
        lines = fh.readlines()

    examples: list[Example] = []
    i = 0
    n = len(lines)
    while i < n:
        open_match = _FENCE_RE.match(lines[i])
        if not open_match:
            i += 1
            continue
        fence = open_match.group(1)
        language = open_match.group(2).lower()
        start_line = i + 1  # 1-based
        marker = _marker_above(lines, i)

        # CommonMark: a closing fence is the same fence char repeated >= len(fence)
        # times, followed only by optional trailing whitespace — no info string.
        close_re = re.compile(r"^" + re.escape(fence[0]) + "{" + str(len(fence)) + r",}[ \t]*$")

        body: list[str] = []
        j = i + 1
        while j < n and not close_re.match(lines[j]):
            body.append(lines[j])
            j += 1
        examples.append(
            Example(
                source_file=md_path,
                start_line=start_line,
                language=language,
                code="".join(body),
                marker=marker,
            )
        )
        i = j + 1  # skip past the closing fence
    return examples
