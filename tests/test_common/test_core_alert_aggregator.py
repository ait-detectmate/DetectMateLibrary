from detectmatelibrary.common.alert_aggregator import (
    CoreAlertAggregatorConfig, CoreAlertAggregator, BufferMode
)

from detectmatelibrary.utils.aux import time_test_mode
import detectmatelibrary.schemas as schemas

import pydantic
import pytest


class MockupConfig(CoreAlertAggregatorConfig):
    pass


class MockupAlertAggregator(CoreAlertAggregator):
    def __init__(self, name: str, config: MockupConfig, buffer_size: int = 1) -> None:
        super().__init__(
            name=name, buffer_size=buffer_size, config=config
        )

    def aggregate_alerts(self, input_, output_):
        output_["description"] = "Mockup aggregator"
        return True


class MockupAlertAggregatorBuffer(CoreAlertAggregator):
    def __init__(self, name: str, config: MockupConfig, buffer_size: int = 1) -> None:
        super().__init__(
            name=name, buffer_size=buffer_size, config=config, buffer_mode=BufferMode.BATCH
        )

    def aggregate_alerts(self, input_, output_):
        output_["description"] = "Mockup aggregator"
        return True


class NoneMockupAlertAggregator(CoreAlertAggregator):
    def __init__(self, name: str, config: MockupConfig) -> None:
        super().__init__(
            name=name, buffer_size=1, config=config
        )
        self.value = True

    def aggregate_alerts(self, input_, output_):
        output_["description"] = "Mockup aggregator"
        self.value = not self.value
        return self.value


dummy_schema = {
    "detectorID": "1",
    "detectorType": "dummy",
    "alertID": "2",
    "detectionTimestamp": 0,
    "logIDs": ["logID1"],
    "score": 0.2,
    "extractedTimestamps": [-1],
    "description": "hello there",
    "receivedTimestamp": 1,
    "alertsObtain": {"99 problems": "but logs aint one"}
}


dummy_config = {
    "alert_aggregators": {
        "TestAAG": {
            "method_type": "core_alert_aggregator",
            "auto_config": True,
        }
    }
}

time_test_mode()


class TestCoreAlertAggregator:
    def test_initialize_default(self) -> None:
        detector = MockupAlertAggregator(name="TestAAG", config=dummy_config)

        assert isinstance(detector, CoreAlertAggregator)
        assert detector.name == "TestAAG"
        assert isinstance(detector.config, CoreAlertAggregatorConfig)
        assert detector.input_schema == schemas.DetectorSchema
        assert detector.output_schema == schemas.AggregateSchema

    def test_incorrect_config_type(self) -> None:
        dummy_config2 = {
            "alert_aggregators": {
                "TestAAG": {
                    "method_type": "core_alert_aggregator",
                    "auto_config": True,
                    "incorrect_field": 4
                }
            }
        }

        with pytest.raises(pydantic.ValidationError):
            MockupAlertAggregator(name="TestAAG", config=dummy_config2)

    def test_process_correct_input_schema(self) -> None:
        detector = MockupAlertAggregator(name="TestAAG", config=dummy_config)
        data = schemas.DetectorSchema(dummy_schema).serialize()
        result = detector.process(data)  # no error should be produced
        assert isinstance(result, bytes)  # and result should be bytes

    def test_process_input_schema_not_serialized(self) -> None:
        alert_aggregator = MockupAlertAggregator(name="TestAAG", config=MockupConfig())
        expected_result = schemas.AggregateSchema({
            "__version__": "1.0.0",
            "detectorIDs": ["1"],
            "detectorTypes": ["dummy"],
            "alertIDs": ["2"],
            "outputTimestamp": 0,
            "logIDs": ["logID1"],
            "description": "Mockup aggregator",
            "extractedTimestamps": [-1],
            "alertsObtain": {}
        })
        data = schemas.DetectorSchema(dummy_schema)
        result = alert_aggregator.process(data)
        assert result == expected_result, f"result -> {result}"

    def test_process_input_schema_not_serialized_window_3(self) -> None:
        alert_aggregator = MockupAlertAggregator(name="TestDetector", config=MockupConfig(), buffer_size=3)
        expected_result = schemas.AggregateSchema({
            "__version__": "1.0.0",
            "detectorIDs": ["1", "1", "1"],
            "detectorTypes": ["dummy", "dummy", "dummy"],
            "alertIDs": ["2", "2", "2"],
            "outputTimestamp": 0,
            "logIDs": ["logID1", "logID1", "logID1"],
            "description": "Mockup aggregator",
            "extractedTimestamps": [-1, -1, -1],
            "alertsObtain": {}
        })
        data = schemas.DetectorSchema(dummy_schema)

        assert alert_aggregator.process(data) is None
        assert alert_aggregator.process(data) is None

        result = alert_aggregator.process(data)
        assert result == expected_result, f"result -> {expected_result} and {result}"

    def test_process_input_schema_not_serialized_buffer_3(self) -> None:
        alert_aggregator = MockupAlertAggregatorBuffer(
            name="TestDetector", config=MockupConfig(), buffer_size=3
        )
        expected_result = schemas.AggregateSchema({
            "__version__": "1.0.0",
            "detectorIDs": ["1", "1", "1"],
            "detectorTypes": ["dummy", "dummy", "dummy"],
            "alertIDs": ["2", "2", "2"],
            "outputTimestamp": 0,
            "logIDs": ["logID1", "logID1", "logID1"],
            "description": "Mockup aggregator",
            "extractedTimestamps": [-1, -1, -1],
            "alertsObtain": {}
        })
        data = schemas.DetectorSchema(dummy_schema)

        assert alert_aggregator.process(data) is None
        assert alert_aggregator.process(data) is None

        result = alert_aggregator.process(data)
        assert result == expected_result, f"result -> {expected_result} and {result}"

    def test_none_detector(self) -> None:
        alert_aggregator = NoneMockupAlertAggregator(name="TestDetector", config=MockupConfig())
        data = schemas.DetectorSchema(dummy_schema)

        assert alert_aggregator.process(data) is None
        assert alert_aggregator.process(data) is not None
