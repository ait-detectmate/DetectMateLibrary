from src.components.common.detector import CoreDetector, CoreDetectorConfig
import src.schemas as schemas

from datetime import datetime
import pydantic
import pytest


class MockupConfig(CoreDetectorConfig):
    detectorID: str = "TestDetector01"
    detectorType: str = "TestType"


class MockupDetector(CoreDetector):
    def __init__(self, name: str, config: CoreDetectorConfig) -> None:
        super().__init__(name=name, buffer_mode="no_buf", config=config)

    def detect(self, input_, output_):
        output_.score = 0.9
        output_.predictionLabel = True


class MockupDetector_window(CoreDetector):
    def __init__(self, name: str, config: CoreDetectorConfig) -> None:
        super().__init__(
            name=name, buffer_mode="window", buffer_size=3, config=config
        )

    def detect(self, input_, output_):
        output_.score = 0.9
        output_.predictionLabel = True


class MockupDetector_buffer(CoreDetector):
    def __init__(self, name: str, config: CoreDetectorConfig) -> None:
        super().__init__(
            name=name, buffer_mode="window", buffer_size=3, config=config
        )

    def detect(self, input_, output_):
        output_.score = 0.9
        output_.predictionLabel = True


class IncompleteMockupDetector(CoreDetector):
    def __init__(self, name: str, config: CoreDetectorConfig) -> None:
        super().__init__(name=name, buffer_mode="no_buf", config=config)

    def detect(self, input_, output_):
        output_.predictionLabel = True


dummy_schema = {
    "parserType": "a",
    "EventID": 1,
    "template": "asd",
    "variables": [""],
    "logID": 12,
    "parsedLogID": 22,
    "parserID": "test",
    "log": "This is a parsed log.",
    "logFormatVariables": {"timestamp": "12121"},
}


class TestCoreDetector:
    def test_initialize_default(self) -> None:
        detector = MockupDetector(name="TestDetector", config={})

        assert isinstance(detector, CoreDetector)
        assert detector.name == "TestDetector"
        assert isinstance(detector.config, CoreDetectorConfig)
        assert detector.input_schema == schemas.PARSER_SCHEMA
        assert detector.output_schema == schemas.DETECTOR_SCHEMA

    def test_incorrect_config_type(self) -> None:
        with pytest.raises(pydantic.ValidationError):
            MockupDetector(name="TestDetector", config={"param1": "invalid_type", "param2": 0.5})

    def test_process_correct_input_schema(self) -> None:
        detector = MockupDetector(name="TestDetector", config={})
        data = schemas.initialize(schemas.PARSER_SCHEMA, **dummy_schema)
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
        detector = MockupDetector(name="TestDetector", config=MockupConfig())
        expected_result = schemas.initialize(schemas.DETECTOR_SCHEMA, **{
            "__version__": "1.0.0",
            "detectorID": "TestDetector01",
            "detectorType": "TestType",
            "alertID": 10,
            "detectionTimestamp": int(datetime.now().timestamp()),
            "logIDs": [12],
            "predictionLabel": True,
            "score": 0.9,
            "extractedTimestamps": [12121]
        })
        data = schemas.initialize(schemas.PARSER_SCHEMA, **dummy_schema)
        result = detector.process(data)
        assert result == expected_result, f"result -> {result}"

    def test_process_input_schema_not_serialized_window_3(self) -> None:
        detector = MockupDetector_window(name="TestDetector", config=MockupConfig())
        expected_result = schemas.initialize(schemas.DETECTOR_SCHEMA, **{
            "__version__": "1.0.0",
            "detectorID": "TestDetector01",
            "detectorType": "TestType",
            "alertID": 10,
            "detectionTimestamp": int(datetime.now().timestamp()),
            "logIDs": [12, 12, 12],
            "predictionLabel": True,
            "score": 0.9,
            "extractedTimestamps": [12121, 12121, 12121]
        })
        data = schemas.initialize(schemas.PARSER_SCHEMA, **dummy_schema)

        assert detector.process(data) is None
        assert detector.process(data) is None

        result = detector.process(data)
        assert result == expected_result, f"result -> {expected_result} and {result}"

    def test_process_input_schema_not_serialized_buffer_3(self) -> None:
        detector = MockupDetector_window(name="TestDetector", config=MockupConfig())
        expected_result = schemas.initialize(schemas.DETECTOR_SCHEMA, **{
            "__version__": "1.0.0",
            "detectorID": "TestDetector01",
            "detectorType": "TestType",
            "alertID": 10,
            "detectionTimestamp": int(datetime.now().timestamp()),
            "logIDs": [12, 12, 12],
            "predictionLabel": True,
            "score": 0.9,
            "extractedTimestamps": [12121, 12121, 12121]
        })
        data = schemas.initialize(schemas.PARSER_SCHEMA, **dummy_schema)

        assert detector.process(data) is None
        assert detector.process(data) is None

        result = detector.process(data)
        assert result == expected_result, f"result -> {expected_result} and {result}"

    def test_incomplete_detector(self) -> None:
        detector = IncompleteMockupDetector(name="TestDetector", config=MockupConfig())
        data = schemas.initialize(schemas.PARSER_SCHEMA, **dummy_schema)

        with pytest.raises(schemas.NotCompleteSchema):
            detector.process(data)
