"""Tests for BrainParser integration.

Brain is a batch algorithm bridged into the streaming CoreParser lifecycle
via train() / post_train() / parse() - see the docstring on BrainParser for
details. These tests exercise that lifecycle end-to-end with small synthetic
logs, deterministically and without any network or filesystem access.
"""

from detectmatelibrary.common.parser import CoreParser
from detectmatelibrary.parsers.brain import BrainParser, BrainParserConfig
from detectmatelibrary.parsers.brain.engine.core import LogParser as BrainCore
from detectmatelibrary.utils.aux import time_test_mode
from detectmatelibrary import schemas

time_test_mode()

TRAIN_LOGS = [
    "Connection from 192.168.1.1 port 22",
    "Connection from 192.168.1.2 port 23",
    "Connection from 192.168.1.3 port 24",
]
PARSE_LOG = "Connection from 192.168.1.4 port 25"


def _train(parser: BrainParser, logs: list[str]) -> schemas.ParserSchema:
    """Feed logs through process() (which drives train -> post_train once
    exhausted) and return the last result."""
    result = None
    for i, log in enumerate(logs):
        result = parser.process(schemas.LogSchema({"logID": str(i), "log": log}))
    assert result is not None
    return result


class TestBrainParserInit:
    def test_is_core_parser(self):
        parser = BrainParser(config=BrainParserConfig())
        assert isinstance(parser, CoreParser)

    def test_config_method_type(self):
        config = BrainParserConfig()
        assert config.method_type == "brain_parser"

    def test_no_matcher_before_training(self):
        parser = BrainParser(config=BrainParserConfig())
        assert parser.template_matcher is None


class TestBrainParserLifecycle:
    def test_parse_before_training_falls_back(self):
        parser = BrainParser(config=BrainParserConfig(data_use_training=3))
        output_data = schemas.ParserSchema()
        parser.parse(schemas.LogSchema({"log": PARSE_LOG}), output_data)

        assert output_data.template == "<Not Found>"
        assert output_data.EventID == -1
        assert output_data.variables == []

    def test_post_train_builds_matcher(self):
        parser = BrainParser(config=BrainParserConfig(data_use_training=len(TRAIN_LOGS)))
        # post_train() fires once the training quota is exhausted, which the
        # FitLogic state machine only detects on the *next* process() call.
        for i, log in enumerate(TRAIN_LOGS + [PARSE_LOG]):
            parser.process(schemas.LogSchema({"logID": str(i), "log": log}))

        assert parser.template_matcher is not None
        assert parser._buffer == []

    def test_template_has_wildcard(self):
        parser = BrainParser(config=BrainParserConfig(data_use_training=len(TRAIN_LOGS)))
        result = _train(parser, TRAIN_LOGS + [PARSE_LOG])

        assert "<*>" in result["template"]

    def test_variables_extracted(self):
        parser = BrainParser(config=BrainParserConfig(data_use_training=len(TRAIN_LOGS)))
        result = _train(parser, TRAIN_LOGS + [PARSE_LOG])

        assert "192.168.1.4" in result["variables"]
        assert "25" in result["variables"]

    def test_event_id_is_int(self):
        parser = BrainParser(config=BrainParserConfig(data_use_training=len(TRAIN_LOGS)))
        result = _train(parser, TRAIN_LOGS + [PARSE_LOG])

        assert isinstance(result["EventID"], int)
        assert result["EventID"] != -1


class TestBrainEngine:
    """The vendored Brain core, exercised directly (no CoreParser)."""

    def test_derives_expected_template(self):
        engine = BrainCore(threshold=2)
        templates = engine.parse(TRAIN_LOGS)

        assert templates == ["Connection from <*> port <*>"]

    def test_empty_batch_returns_no_templates(self):
        engine = BrainCore(threshold=2)
        assert engine.parse([]) == []
