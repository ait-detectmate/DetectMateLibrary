from detectmatelibrary.alert_aggregation.basic_concat import BasicConcatAggregation
from detectmatelibrary.schemas import AggregateSchema
from detectmatelibrary.utils.aux import time_test_mode
import detectmatelibrary.schemas as schemas
from datetime import datetime


time_test_mode()

aggregations_config = {
    "alert_aggregators": {
        "Buffer_4": {
            "method_type": "basic_concat_aggregator",
            "buffer_size": 4,
            "auto_config": False,
            "params": {},
        },
        "Buffer_6": {
            "method_type": "basic_concat_aggregator",
            "buffer_size": 6,
            "deduplicate_values": True,
            "auto_config": False,
            "params": {},
        },
    },
    "auto_config": False
}


data_global = [schemas.DetectorSchema({
    "detectorID": str(i),
    "detectorType": "dummy",
    "alertID": str(i),
    "detectionTimestamp": 0,
    "logIDs": [f"logID{i}"],
    "score": 0.2 + i / 10,
    "extractedTimestamps": [int(datetime.now().timestamp() + i)],
    "description": "hello there",
    "receivedTimestamp": 1,
    "alertsObtain": {"99 problems": "but logs aint one"}
}) for i in range(1, 4)]

data_global += [schemas.DetectorSchema({
    "detectorID": "1",
    "detectorType": "dummy",
    "alertID": "1",
    "detectionTimestamp": 0,
    "logIDs": [f"logID{1}"],
    "score": 0.3,
    "extractedTimestamps": [int(datetime.now().timestamp() + 1)],
    "description": "hello there",
    "receivedTimestamp": 1,
    "alertsObtain": {"99 problems": "but logs aint one"}
}) for i in range(1, 4)]


class TestBasicAggregation:
    def test_with_buffer_3(self):
        alert_aggregator = BasicConcatAggregation("Buffer_4", aggregations_config)
        data = data_global

        assert alert_aggregator.process(data[0]) is None
        assert alert_aggregator.process(data[1]) is None
        assert alert_aggregator.process(data[2]) is None
        result = alert_aggregator.process(data[3])
        assert result is not None
        assert isinstance(result, AggregateSchema)
        res_dict = result.as_dict()
        assert res_dict["detectorIDs"] == ["1", "2", "3", "1"]
        assert res_dict["alertIDs"] == ["1", "2", "3", "1"]
        assert res_dict["outputTimestamp"] == 0
        assert res_dict["logIDs"] == ["logID1", "logID2", "logID3", "logID1"]
        assert len(res_dict["extractedTimestamps"]) == 4
        assert res_dict["description"] == "Basic aggregation by alert concatenation"
        assert res_dict["detectorTypes"] == ["dummy"]*4

    def test_with_buffer_5(self):
        alert_aggregator = BasicConcatAggregation("Buffer_6", aggregations_config)
        data = data_global

        assert alert_aggregator.process(data[0]) is None
        assert alert_aggregator.process(data[1]) is None
        assert alert_aggregator.process(data[2]) is None
        assert alert_aggregator.process(data[3]) is None
        assert alert_aggregator.process(data[4]) is None
        result = alert_aggregator.process(data[5])
        assert result is not None
        assert isinstance(result, AggregateSchema)
        res_dict = result.as_dict()
        assert res_dict["detectorIDs"] == ["1", "2", "3"]
        assert res_dict["alertIDs"] == ["1", "2", "3"]
        assert res_dict["outputTimestamp"] == 0
        assert res_dict["logIDs"] == ["logID1", "logID2", "logID3"]
        assert len(res_dict["extractedTimestamps"]) == 3
        assert res_dict["description"] == "Basic aggregation by alert concatenation"
        assert res_dict["detectorTypes"] == ["dummy"]
