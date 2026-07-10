from detectmatelibrary.alert_aggregation.basic_concat import BasicConcatAggregation


from detectmatelibrary.utils.aux import time_test_mode

import detectmatelibrary.schemas as schemas


time_test_mode()

aggregations_config = {
    "alert_aggregators": {
        "Buffer_3": {
            "method_type": "basic_concat_aggregator",
            "buffer_size": 3,
        },
        "Buffer_5": {
            "method_type": "basic_concat_aggregator",
            "buffer_size": 5,
        },
    }
}


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


class TestBasicAggregation:
    def test_with_buffer_3(self):
        alert_aggregator = BasicConcatAggregation("Buffer_3", aggregations_config)
        data = schemas.DetectorSchema(dummy_schema).serialize()

        assert alert_aggregator.process(data) is None
        assert alert_aggregator.process(data) is None
        assert (result := alert_aggregator.process(data)) is not None
        assert isinstance(result, bytes)

    def test_with_buffer_5(self):
        alert_aggregator = BasicConcatAggregation("Buffer_5", aggregations_config)
        data = schemas.DetectorSchema(dummy_schema).serialize()

        assert alert_aggregator.process(data) is None
        assert alert_aggregator.process(data) is None
        assert alert_aggregator.process(data) is None
        assert alert_aggregator.process(data) is None
        assert (result := alert_aggregator.process(data)) is not None
        assert isinstance(result, bytes)
