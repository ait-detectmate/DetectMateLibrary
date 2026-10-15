
# --8<-- [start:example_1]
import yaml
from detectmatelibrary.alert_aggregation.basic_concat import BasicConcatAggregation

import detectmatelibrary.schemas as schemas

with open("docs/examples/alert_aggregators/basic_concat.yaml") as f:
    aggregations_config = yaml.safe_load(f)


input_ = schemas.DetectorSchema({
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
})

alert_aggregator = BasicConcatAggregation(
    "BasicConcatAggregator", aggregations_config
)
alert_aggregator.process(input_)

# --8<-- [end:example_1]
