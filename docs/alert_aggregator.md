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
- `logIDs`, `logTimestamps`: the entries of all alerts, combined into one list

After `aggregate_alerts()` returns `True`, `run()` also sets `aggregatedTimestamp`. So the only
fields left for `aggregate_alerts()` to fill are `description` and `alertDetails`.

!!! warning "The alerts' details are not carried over"
    `run()` copies only the fields listed above. Everything else in the incoming alerts is dropped
    unless your `aggregate_alerts()` keeps it, including their `detectedTimestamp` and
    `receivedTimestamp`.

## Alert aggregator methods

The alert aggregator are numbered from simplest to most complex, and the sidebar lists them in the same order.

| # | Detector | What it detects |
|---|---|---|
| 00 | [Basic Concat Aggregator](alert_aggregators/basic_concatenation.md) | Concat a set of alerts. |
| 01 | [LogID Count Aggregator](alert_aggregators/logid_count.md) | Count the amount of times a logID is in alerts. |
| 02 | [Density Cluster](alert_aggregators/density_cluster.md) | Add description... ADD_DENSITY_CLUSTER|


### Common parameters (all alert aggregators)

There are some parameters, that **every** alert aggregator inherits from `CoreAlertAggregatorConfig`/`CoreConfigCoreAlertAggregator`/`BasicConfig`, regardless of what it does. The other parameters, that are **specific** for the respective detector, are explained right at the detectors documentation page, later on.

<!-- Start common_arguments -->
???+ note "Top level"

    | Field | Type | Default | Description |
    |---|---|---|---|
    | `auto_config` | boolean | False | Runs the configuration step before the training process. |

???+ note "params"

    | Field | Type | Default | Description |
    |---|---|---|---|
    | `start_id` | integer | 10 | Number used to start the unique ID generator. |
    | `data_use_training` | integer, null | None | Number of logs used for training. None skips training. |
    | `data_use_configure` | integer, null | None | Number of logs used for the configuration step. None skips it. |
    | `use_config_data_as_training` | boolean | True | Combine the configured data in the training process if True. |
    | `train_buffer_max_records` | integer | 100000 | Configure records kept in memory for training (use_config_data_as_training) before the buffer spills to Parquet files on disk, in parts of this many records. |
    | `train_buffer_dir` | string, null | None | Local directory for the spilled training buffer. None uses the system temp directory (TMPDIR). Each spill goes to a private detectmate-train-* directory, removed after training reads it; a killed process leaves it behind. |
<!-- End common_arguments -->
