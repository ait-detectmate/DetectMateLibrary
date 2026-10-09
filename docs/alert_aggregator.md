# Alert Aggregation

Alert aggregators combine the alerts produced by detectors into aggregated records.

|            | Schema                     | Description        |
|------------|----------------------------|--------------------|
| **Input**  | [DetectorSchema](schemas.md)    | Alerts from detectors  |
| **Output** | [AggregateSchema](schemas.md) | Aggregated alerts    |

This document explains the expected API and how to implement an alert aggregator.

## Overview

- Alert aggregators must inherit from `CoreAlertAggregator` and provide an `aggregate_alerts()` implementation.
- `CoreAlertAggregator.run()` handles the lifecycle and calls `aggregate_alerts()`. Aggregators use a
  sliding window (a `WINDOW` [data buffer](auxiliar/input_buffer.md)) of `buffer_size` alerts, so
  `aggregate_alerts()` always receives a **list**: the most recent `buffer_size` alerts. It is first
  called once the window is full, and then once for every new alert, so consecutive windows overlap.
  With the default `buffer_size` of 1, it is called for every alert with a list of one.
- Use a typed `Config` class (subclass of `CoreAlertAggregatorConfig`) to hold runtime parameters.

## CoreAlertAggregator: minimal API

```python
class CoreAlertAggregator(CoreComponent):
    def __init__(
        self,
        name: str = "CoreAlertAggregator",
        buffer_mode: BufferMode = BufferMode.WINDOW,
        buffer_size: int | None = 1,
        config: CoreAlertAggregatorConfig | dict[str, Any] | None = CoreAlertAggregatorConfig(),
    ) -> None:
        """buffer_mode and buffer_size set which alerts aggregate_alerts() receives per call."""

    def aggregate_alerts(
        self,
        input_: list[DetectorSchema] | DetectorSchema,
        output_: AggregateSchema,
    ) -> bool:
        """Implement the aggregation here.
        - Return True to emit output_ as the aggregated record.
        - Return False to emit nothing: process() then returns None.
        """

    def train(self, input_: DetectorSchema | list[DetectorSchema]) -> None:
        """Optional: learn from alerts. Can be a no-op."""
```

## What `run()` fills in for you

Before calling `aggregate_alerts()`, `CoreAlertAggregator.run()` collects these fields from the
alerts in the window:

- `detectorIDs`, `detectorTypes`, `alertIDs`: one entry per alert
- `logIDs`, `extractedTimestamps`: the entries of all alerts, combined into one list

After `aggregate_alerts()` returns `True`, `run()` also sets `outputTimestamp`. So
`aggregate_alerts()` only has to set `description` and `alertsObtain`.

!!! warning "The alerts' details are not carried over"
    `run()` copies only IDs and timestamps. The `description` and `alertsObtain` of the incoming
    alerts, which hold the actual alert messages, are **not** copied into the aggregate, and
    `AggregateSchema` has no `score` field at all. If your aggregator needs this information, read it
    from `input_` in `aggregate_alerts()` and write it into `output_["description"]` or
    `output_["alertsObtain"]` yourself.

## Available alert aggregators

- [Basic Concat](alert_aggregators/basic_concatenation.md)
