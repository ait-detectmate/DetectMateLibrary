from tests.docs_examples.extractor import extract_examples, parse_marker, Marker


def test_parse_marker_skip():
    assert parse_marker("<!-- docs-test: skip -->") == Marker(kind="skip", substring=None)


def test_parse_marker_run():
    assert parse_marker("<!-- docs-test: run -->") == Marker(kind="run", substring=None)


def test_parse_marker_expect_error_plain():
    assert parse_marker("<!-- docs-test: expect-error -->") == Marker(
        kind="expect-error", substring=None
    )


def test_parse_marker_expect_error_with_substring():
    assert parse_marker("<!-- docs-test: expect-error=extra_forbidden -->") == Marker(
        kind="expect-error", substring="extra_forbidden"
    )


def test_parse_marker_none_for_plain_comment():
    assert parse_marker("<!-- just a normal comment -->") is None


def test_parse_marker_none_for_non_comment():
    assert parse_marker("some prose line") is None


def _write(tmp_path, text):
    p = tmp_path / "doc.md"
    p.write_text(text)
    return p


def test_extract_single_python_block(tmp_path):
    p = _write(tmp_path, "intro\n\n```python\nx = 1\n```\n")
    examples = extract_examples(str(p))
    assert len(examples) == 1
    ex = examples[0]
    assert ex.language == "python"
    assert ex.code == "x = 1\n"
    assert ex.start_line == 3
    assert ex.marker is None


def test_extract_marker_directly_above(tmp_path):
    p = _write(tmp_path, "<!-- docs-test: skip -->\n```python\nbad\n```\n")
    examples = extract_examples(str(p))
    assert examples[0].marker is not None
    assert examples[0].marker.kind == "skip"


def test_extract_marker_with_one_blank_line(tmp_path):
    p = _write(tmp_path, "<!-- docs-test: run -->\n\n```bash\nls\n```\n")
    examples = extract_examples(str(p))
    assert examples[0].marker is not None
    assert examples[0].marker.kind == "run"


def test_extract_marker_not_attached_when_prose_between(tmp_path):
    p = _write(tmp_path, "<!-- docs-test: skip -->\nprose\n```python\nx\n```\n")
    examples = extract_examples(str(p))
    assert examples[0].marker is None


def test_extract_multiple_blocks_in_order(tmp_path):
    p = _write(tmp_path, "```python\na\n```\n\ntext\n\n```yaml\nb: 1\n```\n")
    examples = extract_examples(str(p))
    assert [e.language for e in examples] == ["python", "yaml"]
    assert examples[0].start_line < examples[1].start_line


def test_extract_no_language_is_empty_string(tmp_path):
    p = _write(tmp_path, "```\nplain\n```\n")
    examples = extract_examples(str(p))
    assert examples[0].language == ""


def test_extract_body_line_fence_plus_text_does_not_close(tmp_path):
    # A body line that starts with ``` but has trailing text (e.g. ```python)
    # is NOT a valid CommonMark closing fence; only the final bare ``` should close.
    text = "```text\nintro\n```python\nx = 1\nstill body\n```\n"
    p = _write(tmp_path, text)
    examples = extract_examples(str(p))
    # The ```python line starts with ``` but has trailing text; per CommonMark it
    # is NOT a valid closing fence, so the real close is the final bare ```.
    assert len(examples) == 1
    assert examples[0].language == "text"
    assert "still body" in examples[0].code
