from src.components.common.detector import CoreDetector, ConfigCore
import src.schemas as schemas

import pydantic
import pytest


class MockupDetector(CoreDetector):
    def __init__(self, name: str, config: ConfigCore) -> None:
        super().__init__(name=name, buffer_mode="no_buf", config=config)

    def detect(self, data):
        result = schemas.initialize(schemas.DETECTOR_SCHEMA, **{"score": 0.99})
        return result

    def train(self, data):
        pass


class TestCoreDetector:
    def test_initialize_default(self) -> None:
        detector = MockupDetector(name="TestDetector", config={})

        assert isinstance(detector, CoreDetector)
        assert detector.name == "TestDetector"
        assert isinstance(detector.config, ConfigCore)
        assert detector.input_schema == schemas.PARSER_SCHEMA
        assert detector.output_schema == schemas.DETECTOR_SCHEMA

    def test_incorrect_config_type(self) -> None:
        with pytest.raises(pydantic.ValidationError):
            MockupDetector(name="TestDetector", config={"param1": "invalid_type", "param2": 0.5})

    def test_process_correct_input_schema(self) -> None:
        detector = MockupDetector(name="TestDetector", config={})
        data = schemas.initialize(schemas.PARSER_SCHEMA, **{"log": "This is a parsed log."})
        data_serialized = schemas.serialize(schemas.PARSER_SCHEMA, data)
        result = detector.process(data_serialized)  # no error should be produced
        assert isinstance(result, bytes)  # and result should be bytes

    def test_process_incorrect_input_schema(self) -> None:
        detector = MockupDetector(name="TestDetector", config={})
        data = schemas.initialize(schemas.LOG_SCHEMA, **{"log": "This is a log."})
        data_serialized = schemas.serialize(schemas.LOG_SCHEMA, data)
        with pytest.raises(schemas.IncorrectSchema):
            detector.process(data_serialized)

    def test_process_input_schema_not_serialized(self) -> None:
        detector = MockupDetector(name="TestDetector", config={})
        expected_result = schemas.initialize(schemas.DETECTOR_SCHEMA, **{"score": 0.99})
        data = schemas.initialize(schemas.PARSER_SCHEMA, **{"log": "This is a parsed log."})
        result = detector.process(data)
        assert result == expected_result
