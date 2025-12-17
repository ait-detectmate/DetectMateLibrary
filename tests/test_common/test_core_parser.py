from detectmatelibrary.common.parser import CoreParser, CoreParserConfig, get_format_variables
from detectmatelibrary.utils.aux import time_test_mode
import detectmatelibrary.schemas._op as op_schemas
import detectmatelibrary.schemas as schemas

import pydantic
import pytest
import re


class MockupConfig(CoreParserConfig):
    pass


class MockupParser(CoreParser):
    def __init__(self, name: str, config: CoreParserConfig) -> None:
        super().__init__(name=name, config=config)

    def parse(self, input_, output_):
        output_.EventID = 1
        output_.template = "hello"
        output_.variables = ["a", "b"]


class IncompleteMockupParser(CoreParser):
    def __init__(self, name: str, config: CoreParserConfig) -> None:
        super().__init__(name=name, config=config)

    def parse(self, input_, output_):
        output_.EventID = 1
        output_.variables = ["a", "b"]


class NoneMockupParser(CoreParser):
    def __init__(self, name: str, config: CoreParserConfig) -> None:
        super().__init__(name=name, config=config)
        self.value = True

    def parse(self, input_, output_):
        self.value = not self.value

        output_.EventID = 1
        output_.template = "hello"
        output_.variables = ["a", "b"]

        return self.value


time_test_mode()

default_args = {
    "parsers": {
        "TestParser": {
            "auto_config": True,
            "method_type": "core_parser"
        }
    }
}


class TestCoreParser:
    def test_initialize_default(self) -> None:
        parser = MockupParser(name="TestParser", config=default_args)

        assert isinstance(parser, CoreParser)
        assert parser.name == "TestParser"
        assert isinstance(parser.config, CoreParserConfig)
        assert parser.input_schema == schemas.LogSchema
        assert parser.output_schema == schemas.ParserSchema

    def test_incorrect_config_type(self) -> None:
        invalid_args = {
            "parsers": {
                "TestParser": {
                    "auto_config": True,
                    "method_type": "core_parser",
                    "invalid": 1
                }
            }
        }
        with pytest.raises(pydantic.ValidationError):
            MockupParser(name="TestParser", config=invalid_args)

    def test_process_correct_input_schema(self) -> None:
        parser = MockupParser(name="TestParser", config=default_args)
        data = schemas.LogSchema({"logID": 1, "log": "This is a log."}).serialize()
        result = parser.process(data)  # no error should be produced
        assert isinstance(result, bytes)  # and result should be bytes

    def test_process_incorrect_input_schema(self) -> None:
        parser = MockupParser(name="TestParser", config=default_args)
        data = schemas.DetectorSchema({"score": 0.99}).serialize()

        with pytest.raises(op_schemas.IncorrectSchema):
            parser.process(data)

    def test_process_correct_input_schema_not_serialize(self) -> None:
        parser = MockupParser(name="TestParser", config=MockupConfig())
        expected_result = schemas.ParserSchema({
            "__version__": "1.0.0",
            "parserType": "core_parser",
            "parserID": "TestParser",
            "EventID": 1,
            "template": "hello",
            "parsedLogID": 10,
            "logID": 1,
            "log": "This is a log.",
            "receivedTimestamp": 0,
            "parsedTimestamp": 0,
        })
        expected_result.variables = ["a", "b"]
        expected_result.logFormatVariables["Time"] = "0"

        data = schemas.LogSchema({"logID": 1, "log": "This is a log."})
        result = parser.process(data)

        assert result == expected_result, f"results {result} and expected {expected_result}"

    def test_process_ids(self) -> None:
        parser = MockupParser(name="TestParser", config=MockupConfig())
        data = schemas.LogSchema({
            "logID": 1, "log": "This is a log.", "logSource": "", "hostname": ""
        })

        result = parser.process(data)
        assert result.parsedLogID == 10

        result = parser.process(data)
        assert result.parsedLogID == 11

    def test_none_parser(self) -> None:
        parser = NoneMockupParser(name="TestParser", config=MockupConfig())
        data = schemas.LogSchema({
            "logID": 1, "log": "This is a log.", "logSource": "", "hostname": ""
        })

        assert parser.process(data) is None
        assert parser.process(data) is not None


class TestGetFormatVariables:
    def test_no_pattern(self) -> None:
        log = "This is a log."
        var, content = get_format_variables(None, None, log)

        assert var == {"Time": "0"}
        assert content == log

    def test_pattern_no_match(self) -> None:
        pattern = re.compile(r"(?P<date>\d{4}-\d{2}-\d{2})")
        log = "This is a log."

        var, content = get_format_variables(pattern, None, log)

        assert var == {"Time": "0"}
        assert content == log

    def test_pattern_with_match(self) -> None:
        log = "[INFO] 2024-10-05 This is a log."
        pattern = re.compile(r"\[(?P<level>\w+)\]\s(?P<Time>\d{4}-\d{2}-\d{2})")

        var, content = get_format_variables(pattern, None, log)
        assert var == {"level": "INFO", "Time": "2024-10-05"}
        assert content == log

    def test_pattern_with_time_format(self) -> None:
        log = "[INFO] 2024-10-05 14:30:00 This is a log."
        pattern = re.compile(r"\[(?P<level>\w+)\]\s(?P<Time>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})")
        time_format = "%Y-%m-%d %H:%M:%S"

        var, content = get_format_variables(pattern, time_format, log)
        assert var == {"level": "INFO", "Time": "1728138600"}
        assert content == log
