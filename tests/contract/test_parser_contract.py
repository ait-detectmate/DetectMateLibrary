"""Contract every parser honours: LogSchema in, ParserSchema out.

Each check runs for every parser in tests/contract/registry.py.
"""
import pytest

import detectmatelibrary.schemas as sc
from detectmatelibrary import parsers
from detectmatelibrary.schemas._classes import set_connector
from tests.contract.registry import EXCLUDED, PARSERS, cases, raw_log


def test_every_exported_parser_is_registered():
    exported = {name for name in parsers.__all__ if not name.endswith("Config")}
    registered = {case.cls.__name__ for case in PARSERS}
    assert exported - registered - set(EXCLUDED) == set()


@pytest.mark.parametrize("case", cases(PARSERS))
class TestParserOutput:
    def test_output_describes_the_log(self, case):
        parser = case.build()
        log = case.sample(7)
        parsed = parser.process(log)

        assert isinstance(parsed, sc.ParserSchema)
        assert parsed["parserID"] == case.name
        assert parsed["parserType"] == parser.config.method_type
        assert parsed["logID"] == "7"
        assert parsed["log"] == log["log"]
        assert parsed["parsedLogID"]

    def test_parsed_log_ids_are_unique(self, case):
        parser = case.build()
        first, second = parser.process(case.sample(1)), parser.process(case.sample(2))
        assert first["parsedLogID"] != second["parsedLogID"]

    def test_bytes_in_bytes_out(self, case):
        out = case.build().process(case.sample(7).serialize())

        assert isinstance(out, bytes)
        parsed = sc.ParserSchema()
        parsed.deserialize(out)
        assert parsed["logID"] == "7"
        assert parsed["parserID"] == case.name

    def test_input_is_not_modified(self, case):
        log = case.sample(7)
        before = log.copy()
        case.build().process(log)
        assert log == before

    def test_output_is_stored_through_the_connector(self, case):
        set_connector("Verification")
        parsed = case.build().process(case.sample(7))
        assert sc.ParserSchema.from_id(parsed["parsedLogID"]) == parsed


@pytest.mark.parametrize("case", cases(PARSERS))
def test_log_source_filters_the_input(case):
    parser = case.build(log_source="source_a")

    assert parser.process(case.sample(1, source="source_b")) is None
    assert parser.process(case.sample(2, source="source_a"))["parserID"] == f"{case.name}_from_source_a"


@pytest.mark.parametrize("case", cases([case for case in PARSERS if case.headers_from_log_format]))
def test_log_format_fills_the_header_variables(case):
    log = case.sample(7)
    log["log"] = "INFO " + log["log"]

    parsed = case.build(log_format="<Level> <Content>").process(log)

    assert parsed["headerVariables"]["Level"] == "INFO"
    assert parsed["log"] == log["log"]  # the output keeps the whole line


_B6 = pytest.mark.xfail(strict=True, raises=AssertionError,
                        reason="B6: TemplateCppTreeMatcher keeps the variables of a partial match")
TEMPLATE_PARSERS = [
    pytest.param(case, id=case.cls.__name__, marks=_B6 if case.cls is parsers.TemplateCppTreeMatcher else ())
    for case in PARSERS if "path_templates" in case.params
]


@pytest.mark.parametrize("case", TEMPLATE_PARSERS)
def test_a_log_that_matches_no_template_has_no_event(case):
    """The line starts like the template but lacks `acct=...`."""
    partial = "pid=9699 uid=0 auid=4294967295 ses=4294967295 msg='op=PAM:accounting"

    parsed = case.build().process(raw_log(7, text=partial))

    assert parsed["eventID"] == -1
    assert list(parsed["variables"]) == []
