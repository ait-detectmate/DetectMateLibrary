"""Tests for detectmatelibrary.common.alert_aggregator."""
from detectmatelibrary.common.alert_aggregator import (
    CoreAlertAggregatorConfig, CoreAlertAggregator, BufferMode, _extract_field, _extract_list_fields
)

import detectmatelibrary.schemas as sc

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
    "detectedTimestamp": 0,
    "logIDs": ["logID1"],
    "score": 0.2,
    "logTimestamps": [-1],
    "description": "hello there",
    "receivedTimestamp": 1,
    "alertDetails": {"99 problems": "but logs aint one"}
}


dummy_config = {
    "alert_aggregators": {
        "TestAAG": {
            "method_type": "core_alert_aggregator",
            "auto_config": True,
        }
    }
}

pytestmark = pytest.mark.usefixtures("frozen_timestamps")


class TestAuxiliar:
    def test_get_field_single(self) -> None:
        expected = {"dummy"}
        input_ = sc.DetectorSchema(dummy_schema)

        assert len(field := _extract_field(input_, "detectorType")) == 1
        assert expected == set(field)

    def test_get_field_multiple(self) -> None:
        expected = {"dummy2", "dummy"}

        dummy_schema2 = dummy_schema.copy()
        dummy_schema2["detectorType"] = "dummy2"
        input_ = [dummy_schema, dummy_schema2]
        input_ = [sc.DetectorSchema(in_) for in_ in input_]

        assert len(field := _extract_field(input_, "detectorType")) == 2
        assert expected == set(field)

    def test_get_logID_timestamp_single(self) -> None:
        expected_logID = ["logID1", "logID2", "logID3"]
        expected_times = [-1, 0, 1]

        dummy_schema2 = dummy_schema.copy()
        dummy_schema2["logIDs"] = ["logID1", "logID2", "logID3", "logID1"]
        dummy_schema2["logTimestamps"] = [-1, 0, 1, 3]
        input_ = sc.DetectorSchema(dummy_schema2)

        logids, times = _extract_list_fields(
            input_, field1="logIDs", field2="logTimestamps"
        )

        assert expected_logID == logids
        assert times == expected_times

    def test_get_logID_timestamp_multiple(self) -> None:
        expected_logID = ["logID1", "logID2", "logID3"]
        expected_times = [-1, 0, 1]

        dummy_schema2 = dummy_schema.copy()
        dummy_schema2["logIDs"] = ["logID2", "logID3", "logID1"]
        dummy_schema2["logTimestamps"] = [0, 1, 3]
        input_ = [dummy_schema, dummy_schema2]
        input_ = [sc.DetectorSchema(in_) for in_ in input_]

        logids, times = _extract_list_fields(
            input_, field1="logIDs", field2="logTimestamps"
        )

        assert expected_logID == logids
        assert times == expected_times


class TestCoreAlertAggregator:
    def test_process_input_schema_not_serialized(self) -> None:
        alert_aggregator = MockupAlertAggregator(name="TestAAG", config=MockupConfig())
        expected_result = sc.AggregateSchema({
            "__version__": "2.0.0",
            "detectorIDs": ["1"],
            "detectorTypes": ["dummy"],
            "alertIDs": ["2"],
            "aggregatedTimestamp": 0,
            "logIDs": ["logID1"],
            "description": "Mockup aggregator",
            "logTimestamps": [-1],
            "alertDetails": {},
            "aggregateID": "TestAAG_10",
        })
        data = sc.DetectorSchema(dummy_schema)
        result = alert_aggregator.process(data)
        assert result == expected_result, f"result -> {result}"

    def test_process_input_schema_not_serialized_window_3(self) -> None:
        alert_aggregator = MockupAlertAggregator(name="TestDetector", config=MockupConfig(), buffer_size=3)
        expected_result = sc.AggregateSchema({
            "__version__": "1.0.0",
            "detectorIDs": ["1"],
            "detectorTypes": ["dummy"],
            "alertIDs": ["2"],
            "aggregatedTimestamp": 0,
            "logIDs": ["logID1"],
            "description": "Mockup aggregator",
            "logTimestamps": [-1],
            "alertDetails": {},
            "aggregateID": "TestDetector_10",
        })
        data = sc.DetectorSchema(dummy_schema)

        assert alert_aggregator.process(data) is None
        assert alert_aggregator.process(data) is None

        result = alert_aggregator.process(data)
        assert result == expected_result, f"result -> {expected_result} and {result}"

    def test_process_input_schema_not_serialized_buffer_3(self) -> None:
        alert_aggregator = MockupAlertAggregatorBuffer(
            name="TestDetector", config=MockupConfig(), buffer_size=3
        )
        expected_result = sc.AggregateSchema({
            "__version__": "1.0.0",
            "detectorIDs": ["1"],
            "detectorTypes": ["dummy"],
            "alertIDs": ["2"],
            "aggregatedTimestamp": 0,
            "logIDs": ["logID1"],
            "description": "Mockup aggregator",
            "logTimestamps": [-1],
            "alertDetails": {},
            "aggregateID": "TestDetector_10",
        })
        data = sc.DetectorSchema(dummy_schema)

        assert alert_aggregator.process(data) is None
        assert alert_aggregator.process(data) is None

        result = alert_aggregator.process(data)
        assert result == expected_result, f"result -> {expected_result} and {result}"

    def test_none_detector(self) -> None:
        alert_aggregator = NoneMockupAlertAggregator(name="TestDetector", config=MockupConfig())
        data = sc.DetectorSchema(dummy_schema)

        assert alert_aggregator.process(data) is None
        assert alert_aggregator.process(data) is not None
