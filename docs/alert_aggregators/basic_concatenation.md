# Basic Concat Alert Aggregation

The basic concat alert aggregation approach aggregates x number of alerts into one output schema.

|            | Schema                     | Description        |
|------------|----------------------------|--------------------|
| **Input**  | [DetectorSchema](../schemas.md)    | Alerts from detectors  |
| **Output** | [AggregateSchema](../schemas.md) | Aggregated alerts    |


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
--8<-- "docs/examples/alert_aggregators/basic_concat.py:example_1"
```
