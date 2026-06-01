from tests.docs_examples.extractor import parse_marker, Marker


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
