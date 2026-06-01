import pytest

from tests.docs_examples.extractor import Example, Marker
from tests.docs_examples import runners


def _ex(language, code, marker=None):
    return Example(
        source_file="t.md", start_line=1, language=language, code=code, marker=marker
    )


def test_config_registry_has_known_types():
    reg = runners.config_registry()
    assert ("parsers", "json_parser") in reg
    assert ("detectors", "new_value_detector") in reg


def test_python_runner_success():
    ns: dict = {}
    result = runners.dispatch(_ex("python", "y = 2 + 2\nassert y == 4\n"), ns)
    assert result == "ran"
    assert ns["y"] == 4


def test_python_runner_shared_namespace():
    ns: dict = {}
    runners.dispatch(_ex("python", "z = 10\n"), ns)
    runners.dispatch(_ex("python", "assert z == 10\n"), ns)


def test_python_runner_failure_raises():
    with pytest.raises(Exception):
        runners.dispatch(_ex("python", "raise ValueError('boom')\n"), {})


def test_python_runner_expect_error_passes_when_it_raises():
    marker = Marker(kind="expect-error", substring="boom")
    result = runners.dispatch(_ex("python", "raise ValueError('boom')\n", marker), {})
    assert result == "expected-error"


def test_python_runner_expect_error_fails_when_no_error():
    marker = Marker(kind="expect-error", substring=None)
    with pytest.raises(AssertionError):
        runners.dispatch(_ex("python", "x = 1\n", marker), {})


def test_skip_marker_returns_skipped():
    result = runners.dispatch(_ex("python", "raise RuntimeError()\n", Marker("skip")), {})
    assert result == "skipped"


def test_yaml_valid_parser_config_passes():
    code = (
        "parsers:\n"
        "  JsonParser:\n"
        "    method_type: json_parser\n"
        "    params:\n"
        "      timestamp_name: time\n"
        "      content_name: message\n"
    )
    assert runners.dispatch(_ex("yaml", code), {}) == "ran"


def test_yaml_unknown_param_fails():
    code = (
        "parsers:\n"
        "  JsonParser:\n"
        "    method_type: json_parser\n"
        "    params:\n"
        "      flatten_nested: true\n"
    )
    with pytest.raises(Exception):
        runners.dispatch(_ex("yaml", code), {})


def test_yaml_non_component_block_just_parses():
    assert runners.dispatch(_ex("yaml", "a: 1\nb: [1, 2, 3]\n"), {}) == "ran"


def test_yaml_invalid_yaml_fails():
    with pytest.raises(Exception):
        runners.dispatch(_ex("yaml", "a: [unterminated\n"), {})


def test_bash_plain_command_is_skipped():
    assert runners.dispatch(_ex("bash", "pip install detectmate\n"), {}) == "skipped"


def test_bash_yaml_heredoc_is_validated_ok():
    code = (
        "cat > config.yaml <<EOF\n"
        "parsers:\n"
        "  JsonParser:\n"
        "    method_type: json_parser\n"
        "    params:\n"
        "      content_name: message\n"
        "EOF\n"
    )
    assert runners.dispatch(_ex("bash", code), {}) == "ran"


def test_bash_yaml_heredoc_with_bad_param_fails():
    code = (
        "cat > config.yaml <<EOF\n"
        "parsers:\n"
        "  JsonParser:\n"
        "    method_type: json_parser\n"
        "    params:\n"
        "      ignore_parse_errors: true\n"
        "EOF\n"
    )
    with pytest.raises(Exception):
        runners.dispatch(_ex("bash", code), {})
