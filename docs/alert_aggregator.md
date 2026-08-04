# Components: Alert Aggregation

Alert aggregation aggregates alerts from detectors.

|            | Schema                     | Description        |
|------------|----------------------------|--------------------|
| **Input**  | [DetectorSchema](schemas.md)    | Alerts from detectors  |
| **Output** | [AggregateSchema](schemas.md) | Aggregated alerts    |

This document explains expected APIs, how to implement a parser, testing tips and common pitfalls.

## Overview

- Alert aggregation must inherit from `CoreAlertAggregation` and provide a `aggregate_alerts()` implementation.
- `CoreParser.run()` handles lifecycle and calls `aggregate_alerts()` for each input; implement pure alert aggregation logic inside `aggregate_alerts()` where possible.
- Use a typed `Config` class (subclass of `CoreAlertAggregationConfig`) to hold runtime parameters.

## CoreParser — minimal API

Recommended signatures and behavior:

```python
class CoreAlertAggregation:
 def aggregate_alerts(
        self,
        input_: list[DetectorSchema] | DetectorSchema,
        output_: AggregateSchema,
    ) -> bool:
        return True

    @override
    def train(
        self, input_: DetectorSchema | list[DetectorSchema]
    ) -> None:
        pass
```

## Available alert aggregation

- [Basic Concat](alert_aggregators/basic_concatenation.md)

Go back to [Index](index.md)
