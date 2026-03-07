"""Temporary tests for LogBatcherParser integration.

These tests verify that LogBatcherParser correctly wraps LogBatcher into the
CoreParser interface without requiring real API calls.
"""

from unittest.mock import MagicMock, patch

import pytest

import detectmatelibrary.schemas as schemas
from detectmatelibrary.parsers.logbatcher import LogBatcherParser, LogBatcherParserConfig
from detectmatelibrary.utils.aux import time_test_mode

time_test_mode()

LOG = "Connection from 192.168.1.1 port 22"
# LLM response format: wrapped in backticks, with {{placeholder}} variables
LLM_RESPONSE = "`Connection from {{ip}} port {{port}}`"
EXPECTED_TEMPLATE = "Connection from <*> port <*>"


def _make_parser():
    """Create a LogBatcherParser with a mocked OpenAI client."""
    with patch("detectmatelibrary.parsers.logbatcher.engine.parser.OpenAI"):
        config = LogBatcherParserConfig(api_key="test-key")
        parser = LogBatcherParser(name="TestLogBatcherParser", config=config)
    # Replace the chat method so no real HTTP calls are made
    parser._llm_parser.chat = MagicMock(return_value=LLM_RESPONSE)
    return parser


class TestLogBatcherParserInit:
    def test_is_core_parser(self):
        from detectmatelibrary.common.parser import CoreParser
        with patch("detectmatelibrary.parsers.logbatcher.engine.parser.OpenAI"):
            parser = LogBatcherParser(config=LogBatcherParserConfig(api_key="k"))
        assert isinstance(parser, CoreParser)

    def test_config_method_type(self):
        config = LogBatcherParserConfig(api_key="k")
        assert config.method_type == "logbatcher_parser"


class TestLogBatcherParserParse:
    def test_template_extracted(self):
        parser = _make_parser()
        log_schema = schemas.LogSchema({"logID": "1", "log": LOG})

        result = parser.process(log_schema)

        assert result["template"] == EXPECTED_TEMPLATE

    def test_variables_extracted(self):
        parser = _make_parser()
        log_schema = schemas.LogSchema({"logID": "1", "log": LOG})

        result = parser.process(log_schema)

        assert "192.168.1.1" in result["variables"]
        assert "22" in result["variables"]

    def test_event_id_is_int(self):
        parser = _make_parser()
        log_schema = schemas.LogSchema({"logID": "1", "log": LOG})

        result = parser.process(log_schema)

        assert isinstance(result["EventID"], int)

    def test_second_call_hits_cache(self):
        """Second identical log must not trigger a new LLM call."""
        parser = _make_parser()

        log_schema1 = schemas.LogSchema({"logID": "1", "log": LOG})
        parser.process(log_schema1)
        llm_call_count = parser._llm_parser.chat.call_count

        log_schema2 = schemas.LogSchema({"logID": "2", "log": LOG})
        parser.process(log_schema2)

        assert parser._llm_parser.chat.call_count == llm_call_count
