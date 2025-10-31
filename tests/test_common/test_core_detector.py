from detectmatelibrary.common.detector import CoreDetectorConfig, BufferMode
from detectmatelibrary.common.detector import CoreDetector
from detectmatelibrary.utils.aux import time_test_mode
import detectmatelibrary.schemas as schemas

import pydantic
import pytest


class MockupConfig(CoreDetectorConfig):
    pass


class MockupDetector(CoreDetector):
    def __init__(self, name: str, config: CoreDetectorConfig) -> None:
        super().__init__(name=name, buffer_mode=BufferMode.NO_BUFF, config=config)

    def detect(self, input_, output_):
        output_.score = 0.9
        output_.description = "hii"


class MockupDetector_window(CoreDetector):
    def __init__(self, name: str, config: CoreDetectorConfig) -> None:
        super().__init__(
            name=name, buffer_mode=BufferMode.WINDOW, buffer_size=3, config=config
        )

    def detect(self, input_, output_):
        output_.score = 0.9
        output_.description = "hii"


class MockupDetector_buffer(CoreDetector):
    def __init__(self, name: str, config: CoreDetectorConfig) -> None:
        super().__init__(
            name=name, buffer_mode=BufferMode.WINDOW, buffer_size=3, config=config
        )

    def detect(self, input_, output_):
        output_.score = 0.9
        output_.description = "hii"


class IncompleteMockupDetector(CoreDetector):
    def __init__(self, name: str, config: CoreDetectorConfig) -> None:
        super().__init__(name=name, buffer_mode=BufferMode.NO_BUFF, config=config)

    def detect(self, input_, output_):
        output_.description = "hii"


class NoneMockupDetector(CoreDetector):
    def __init__(self, name: str, config: CoreDetectorConfig) -> None:
        super().__init__(name=name, buffer_mode=BufferMode.NO_BUFF, config=config)
        self.value = True

    def detect(self, input_, output_):
        output_.score = 0.9
        output_.description = "hii"
        self.value = not self.value
        return self.value


dummy_schema = {
    "parserType": "a",
    "EventID": 0,
    "template": "asd",
    "variables": [""],
    "logID": 0,
    "parsedLogID": 22,
    "parserID": "test",
    "log": "This is a parsed log.",
    "logFormatVariables": {"timestamp": "12121.12"},
}


dummy_config = {
    "detectors": {
        "TestDetector": {
            "method_type": "core_detector",
            "auto_config": True,
        }
    }
}


time_test_mode()


class TestCoreDetector:
    def test_initialize_default(self) -> None:
        detector = MockupDetector(name="TestDetector", config=dummy_config)

        assert isinstance(detector, CoreDetector)
        assert detector.name == "TestDetector"
        assert isinstance(detector.config, CoreDetectorConfig)
        assert detector.input_schema == schemas.PARSER_SCHEMA
        assert detector.output_schema == schemas.DETECTOR_SCHEMA

    def test_incorrect_config_type(self) -> None:
        dummy_config2 = {
            "detectors": {
                "TestDetector": {
                    "method_type": "core_detector",
                    "auto_config": True,
                    "incorrect_field": 4
                }
            }
        }

        with pytest.raises(pydantic.ValidationError):
            MockupDetector(name="TestDetector", config=dummy_config2)

    def test_process_correct_input_schema(self) -> None:
        detector = MockupDetector(name="TestDetector", config=dummy_config)
        data = schemas.initialize(schemas.PARSER_SCHEMA, **dummy_schema)
        data_serialized = schemas.serialize(schemas.PARSER_SCHEMA, data)
        result = detector.process(data_serialized)  # no error should be produced
        assert isinstance(result, bytes)  # and result should be bytes

    def test_process_incorrect_input_schema(self) -> None:
        detector = MockupDetector(name="TestDetector", config=dummy_config)
        data = schemas.initialize(schemas.LOG_SCHEMA, **{"log": "This is a log."})
        data_serialized = schemas.serialize(schemas.LOG_SCHEMA, data)
        with pytest.raises(schemas.IncorrectSchema):
            detector.process(data_serialized)

    def test_process_input_schema_not_serialized(self) -> None:
        detector = MockupDetector(name="TestDetector", config=MockupConfig())
        expected_result = schemas.initialize(schemas.DETECTOR_SCHEMA, **{
            "__version__": "1.0.0",
            "detectorID": "TestDetector",
            "detectorType": "core_detector",
            "alertID": 10,
            "detectionTimestamp": 0,
            "logIDs": [0],
            "score": 0.9,
            "description": "hii",
            "extractedTimestamps": [12121],
            "receivedTimestamp": 0,
        })
        data = schemas.initialize(schemas.PARSER_SCHEMA, **dummy_schema)
        result = detector.process(data)
        assert result == expected_result, f"result -> {result}"

    def test_process_input_schema_not_serialized_window_3(self) -> None:
        detector = MockupDetector_window(name="TestDetector", config=MockupConfig())
        expected_result = schemas.initialize(schemas.DETECTOR_SCHEMA, **{
            "__version__": "1.0.0",
            "detectorID": "TestDetector",
            "detectorType": "core_detector",
            "alertID": 10,
            "detectionTimestamp": 0,
            "logIDs": [0, 0, 0],
            "score": 0.9,
            "description": "hii",
            "extractedTimestamps": [12121, 12121, 12121],
            "receivedTimestamp": 0
        })
        data = schemas.initialize(schemas.PARSER_SCHEMA, **dummy_schema)

        assert detector.process(data) is None
        assert detector.process(data) is None

        result = detector.process(data)
        assert result == expected_result, f"result -> {expected_result} and {result}"

    def test_process_input_schema_not_serialized_buffer_3(self) -> None:
        detector = MockupDetector_window(name="TestDetector01", config=MockupConfig())
        expected_result = schemas.initialize(schemas.DETECTOR_SCHEMA, **{
            "__version__": "1.0.0",
            "detectorID": "TestDetector01",
            "detectorType": "core_detector",
            "alertID": 10,
            "detectionTimestamp": 0,
            "logIDs": [0, 0, 0],
            "score": 0.9,
            "description": "hii",
            "extractedTimestamps": [12121, 12121, 12121],
            "receivedTimestamp": 0,
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

    def test_none_detector(self) -> None:
        detector = NoneMockupDetector(name="TestDetector", config=MockupConfig())
        data = schemas.initialize(schemas.PARSER_SCHEMA, **dummy_schema)

        assert detector.process(data) is None
        assert detector.process(data) is not None
