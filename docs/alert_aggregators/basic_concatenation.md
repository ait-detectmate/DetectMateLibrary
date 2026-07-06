# Basic Concat Alert Aggregation

The basic concat alert aggregation approach aggregates x number of alerts into one output schema.

|            | Schema                     | Description        |
|------------|----------------------------|--------------------|
| **Input**  | [DetectorSchema](../schemas.md)    | Alerts from detectors  |
| **Output** | [OutputSchema](../schemas.md) | Aggregated alerts    |


# Configuration example

```yaml
alert_aggregators:
    BasicConcatAggregator:
        method_type: "basic_concat_aggregator"
        buffer_size: 3
        auto_config: False
```

## Example usage

```python
from detectmatelibrary.alert_aggregation.basic_concat import BasicConcatAggregation

import detectmatelibrary.schemas as schemas

input_ = schemas.DetectorSchema({
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
})

alert_aggregator = BasicConcatAggregation(
    "BasicConcatAggregator", aggregations_config
)
alert_aggregator.process(input_)
```
