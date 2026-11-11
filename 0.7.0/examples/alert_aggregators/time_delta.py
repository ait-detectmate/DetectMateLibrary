# --8<-- [start:example_1]
import yaml

from detectmatelibrary.alert_aggregation.time_delta import (
    TimeDeltaAggregation,
)
from detectmatelibrary.schemas import AggregateSchema, DetectorSchema

with open("docs/examples/alert_aggregators/time_delta.yaml") as f:
    config = yaml.safe_load(f)


def make_alert(alert_id: str, timestamp: float) -> DetectorSchema:
    return DetectorSchema(
        {
            "detectorID": "detector",
            "detectorType": "dummy",
            "alertID": alert_id,
            "detectedTimestamp": 0,
            "logIDs": [f"log-{alert_id}"],
            "score": 0.0,
            "logTimestamps": [timestamp],
            "description": "test alert",
            "receivedTimestamp": 0,
            "alertDetails": {},
        }
    )


aggregator = TimeDeltaAggregation(config)
first = make_alert("a", 0)
second = make_alert("b", 6)
third = make_alert("c", 9)
fourth = make_alert("d", 15)

first_output = AggregateSchema()
aggregator.aggregate_alerts(first, first_output)

second_output = AggregateSchema()
aggregator.aggregate_alerts(second, second_output)

third_output = AggregateSchema()
aggregator.aggregate_alerts(third, third_output)

fourth_output = AggregateSchema()
aggregator.aggregate_alerts(fourth, fourth_output)

print(first_output["alertDetails"]["a"] == "0")  # True
print(second_output["alertDetails"]["b"] == "1")  # True
print(third_output["alertDetails"]["c"] == "1")  # True
print(fourth_output["alertDetails"]["d"] == "2")  # True

# --8<-- [end:example_1]
