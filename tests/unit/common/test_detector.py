"""Tests for detectmatelibrary.common.detector."""
from detectmatelibrary.common.detector import CoreDetectorConfig, BufferMode
from detectmatelibrary.common.detector import CoreDetector, _extract_timestamp
import detectmatelibrary.schemas as sc

import pytest


class MockupConfig(CoreDetectorConfig):
    pass


class MockupDetector(CoreDetector):
    def __init__(self, name: str, config: CoreDetectorConfig) -> None:
        super().__init__(name=name, buffer_mode=BufferMode.NO_BUF, config=config)

    def detect(self, input_, output_):
        output_.score = 0.9
        output_.description = "hii"

        return True


class MockupDetector_window(CoreDetector):
    def __init__(self, name: str, config: CoreDetectorConfig) -> None:
        super().__init__(
            name=name, buffer_mode=BufferMode.WINDOW, buffer_size=3, config=config
        )

    def detect(self, input_, output_):
        output_.score = 0.9
        output_.description = "hii"

        return True


class MockupDetector_buffer(CoreDetector):
    def __init__(self, name: str, config: CoreDetectorConfig) -> None:
        super().__init__(
            name=name, buffer_mode=BufferMode.BATCH, buffer_size=3, config=config
        )

    def detect(self, input_, output_):
        output_.score = 0.9
        output_.description = "hii"

        return True


class IncompleteMockupDetector(CoreDetector):
    def __init__(self, name: str, config: CoreDetectorConfig) -> None:
        super().__init__(name=name, buffer_mode=BufferMode.NO_BUF, config=config)

    def detect(self, input_, output_):
        output_.description = "hii"

        return True


class NoneMockupDetector(CoreDetector):
    def __init__(self, name: str, config: CoreDetectorConfig) -> None:
        super().__init__(name=name, buffer_mode=BufferMode.NO_BUF, config=config)
        self.value = True

    def detect(self, input_, output_):
        output_.score = 0.9
        output_.description = "hii"
        self.value = not self.value
        return self.value


dummy_schema = {
    "parserType": "a",
    "eventID": 0,
    "template": "asd",
    "variables": [""],
    "logID": "0",
    "parsedLogID": "22",
    "parserID": "test",
    "log": "This is a parsed log.",
    "headerVariables": {"Time": "12121.12"},
}

picky_schema = {
    "parserType": "a",
    "eventID": 0,
    "template": "asd",
    "variables": [""],
    "logID": "0",
    "parsedLogID": "22",
    "parserID": "A",
    "log": "This is a parsed log.",
    "headerVariables": {"Time": "12121.12"},
}


dummy_config = {
    "detectors": {
        "TestDetector": {
            "method_type": "core_detector",
            "auto_config": True,
        }
    }
}
picky_config = {
    "detectors": {
        "TestDetector": {
            "method_type": "core_detector",
            "auto_config": True,
            "parser": "A",
        }
    }
}


pytestmark = pytest.mark.usefixtures("frozen_timestamps")


class TestCoreDetector:
    def test_input_eligible_schema(self) -> None:
        detector = MockupDetector(name="TestDetector", config=picky_config)

        data = sc.ParserSchema(picky_schema)
        assert detector.process(data) is not None

        data = sc.ParserSchema(dummy_schema)
        assert detector.process(data) is None

        detector = MockupDetector(name="TestDetector", config=dummy_config)
        data = sc.ParserSchema(picky_schema)
        assert detector.process(data) is not None

    def test_process_input_schema_not_serialized(self) -> None:
        detector = MockupDetector(name="TestDetector", config=MockupConfig())
        expected_result = sc.DetectorSchema({
            "__version__": "2.0.0",
            "detectorID": "TestDetector",
            "detectorType": "core_detector",
            "alertID": "TestDetector_10",
            "detectedTimestamp": 0,
            "logIDs": ["0"],
            "score": 0.9,
            "description": "hii",
            "logTimestamps": [12121],
            "receivedTimestamp": 0,
        })
        data = sc.ParserSchema(dummy_schema)
        result = detector.process(data)
        assert result == expected_result, f"result -> {result}"

    def test_process_input_schema_not_serialized_window_3(self) -> None:
        detector = MockupDetector_window(name="TestDetector", config=MockupConfig())
        expected_result = sc.DetectorSchema({
            "__version__": "2.0.0",
            "detectorID": "TestDetector",
            "detectorType": "core_detector",
            "alertID": "TestDetector_10",
            "detectedTimestamp": 0,
            "logIDs": ["0", "0", "0"],
            "score": 0.9,
            "description": "hii",
            "logTimestamps": [12121, 12121, 12121],
            "receivedTimestamp": 0
        })
        data = sc.ParserSchema(dummy_schema)

        assert detector.process(data) is None
        assert detector.process(data) is None

        result = detector.process(data)
        assert result == expected_result, f"result -> {expected_result} and {result}"

    def test_process_input_schema_not_serialized_buffer_3(self) -> None:
        detector = MockupDetector_window(name="TestDetector01", config=MockupConfig())
        expected_result = sc.DetectorSchema({
            "__version__": "2.0.0",
            "detectorID": "TestDetector01",
            "detectorType": "core_detector",
            "alertID": "TestDetector01_10",
            "detectedTimestamp": 0,
            "logIDs": ["0", "0", "0"],
            "score": 0.9,
            "description": "hii",
            "logTimestamps": [12121, 12121, 12121],
            "receivedTimestamp": 0,
        })
        data = sc.ParserSchema(dummy_schema)

        assert detector.process(data) is None
        assert detector.process(data) is None

        result = detector.process(data)
        assert result == expected_result, f"result -> {expected_result} and {result}"

    def test_none_detector(self) -> None:
        detector = NoneMockupDetector(name="TestDetector", config=MockupConfig())
        data = sc.ParserSchema(dummy_schema)

        assert detector.process(data) is None
        assert detector.process(data) is not None


def test_extract_timestamp_gives_one_epoch_second_per_record():
    """The detector wrapper around TimeFormatHandler (formats:

    unit/utils/test_time_format_handler.py).
    """
    records = [sc.ParserSchema({"headerVariables": {"Time": time}})
               for time in ("1772812294.5", "2026-03-04T14:18:00Z")]

    assert _extract_timestamp(records) == [1772812294, 1772633880]
    assert _extract_timestamp(records[0]) == [1772812294]
