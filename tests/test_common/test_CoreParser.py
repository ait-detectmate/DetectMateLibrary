from src.components.common.parser import CoreParser, CoreParserConfig
import src.schemas as schemas

import pydantic
import pytest


class MockupConfig(CoreParserConfig):
    parserType: str = "TestType"
    parserID: str = "TestParser"


class MockupParser(CoreParser):
    def __init__(self, name: str, config: CoreParserConfig) -> None:
        super().__init__(name=name, config=config)

    def parse(self, input_, output_):
        output_.EventID = 1
        output_.template = "hello"
        output_.variables.extend(["a", "b"])
        output_.logFormatVariables["t"] = "c"


class IncompleteMockupParser(CoreParser):
    def __init__(self, name: str, config: CoreParserConfig) -> None:
        super().__init__(name=name, config=config)

    def parse(self, input_, output_):
        output_.EventID = 1
        output_.variables.extend(["a", "b"])
        output_.logFormatVariables["t"] = "c"


class TestCoreParser:
    def test_initialize_default(self) -> None:
        parser = MockupParser(name="TestParser", config={})

        assert isinstance(parser, CoreParser)
        assert parser.name == "TestParser"
        assert isinstance(parser.config, CoreParserConfig)
        assert parser.input_schema == schemas.LOG_SCHEMA
        assert parser.output_schema == schemas.PARSER_SCHEMA

    def test_incorrect_config_type(self) -> None:
        with pytest.raises(pydantic.ValidationError):
            MockupParser(name="TestParser", config={"param1": "invalid_type", "param2": 0.5})

    def test_process_correct_input_schema(self) -> None:
        parser = MockupParser(name="TestParser", config={})
        data = schemas.initialize(schemas.LOG_SCHEMA, **{
            "logID": 1, "log": "This is a log."
        })
        data_serialized = schemas.serialize(schemas.LOG_SCHEMA, data)
        result = parser.process(data_serialized)  # no error should be produced
        assert isinstance(result, bytes)  # and result should be bytes

    def test_process_incorrect_input_schema(self) -> None:
        parser = MockupParser(name="TestParser", config={})
        data = schemas.initialize(schemas.DETECTOR_SCHEMA, **{"score": 0.99})
        data_serialized = schemas.serialize(schemas.DETECTOR_SCHEMA, data)
        with pytest.raises(schemas.IncorrectSchema):
            parser.process(data_serialized)

    def test_process_correct_input_schema_not_serialize(self) -> None:
        parser = MockupParser(name="TestParser", config=MockupConfig())
        expected_result = schemas.initialize(schemas.PARSER_SCHEMA, **{
            "__version__": "1.0.0",
            "parserType": "TestType",
            "parserID": "TestParser",
            "EventID": 1,
            "template": "hello",
            "parsedLogID": 10,
            "logID": 1,
            "log": "This is a log."
        })
        expected_result.variables.extend(["a", "b"])
        expected_result.logFormatVariables["t"] = "c"

        data = schemas.initialize(schemas.LOG_SCHEMA, **{
            "logID": 1, "log": "This is a log."
        })
        result = parser.process(data)

        assert result == expected_result, f"results {result} and expected {expected_result}"

    def test_process_ids(self) -> None:
        parser = MockupParser(name="TestParser", config=MockupConfig())
        data = schemas.initialize(schemas.LOG_SCHEMA, **{
            "logID": 1, "log": "This is a log.", "logSource": "", "hostname": ""
        })

        result = parser.process(data)
        assert result.parsedLogID == 10

        result = parser.process(data)
        assert result.parsedLogID == 11

    def test_incomplete_parser(self) -> None:
        parser = IncompleteMockupParser(name="TestParser", config=MockupConfig())
        data = schemas.initialize(schemas.LOG_SCHEMA, **{
            "logID": 1, "log": "This is a log.", "logSource": "", "hostname": ""
        })

        with pytest.raises(schemas.NotCompleteSchema):
            parser.process(data)
