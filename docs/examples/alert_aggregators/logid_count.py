# --8<-- [start:example_1]
from detectmatelibrary.alert_aggregation.logid_count import LogIDCountAggegation

import detectmatelibrary.schemas as schemas

import yaml


with open("docs/examples/alert_aggregators/logid_count.yaml") as f:
    config = yaml.safe_load(f)


def generate_schema(log_id: str | list[str]) -> schemas.DetectorSchema:
    log_id = log_id if isinstance(log_id, list) else [log_id]
    return schemas.DetectorSchema({
        "detectorID": "1",
        "detectorType": "dummy",
        "alertID": "2",
        "detectionTimestamp": 0,
        "logIDs": log_id,
        "score": 0.2,
        "extractedTimestamps": [-1],
        "description": "hello there",
        "receivedTimestamp": 1,
        "alertsObtain": {"99 problems": "but logs aint one"}
    })


alert_aggregator = LogIDCountAggegation("LogIDCountAggregator", config=config)

print(alert_aggregator.process(generate_schema("a")) is None)  # True
print(alert_aggregator.process(generate_schema("b")) is None)  # True
print(alert_aggregator.process(generate_schema("a")) is None)  # False

# --8<-- [end:example_1]
