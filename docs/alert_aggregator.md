# Alert Aggregation [[Code](https://github.com/ait-detectmate/DetectMateLibrary/blob/main/src/detectmatelibrary/common/alert_aggregator.py)]

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

```python title="Alert Aggreagor API"
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

The alert aggregators are numbered from simplest to most complex, and the sidebar lists them in the same order.

| # | Alert aggregator | What it does |
|---|---|---|
| 00 | [Basic Concat Aggregator](alert_aggregators/basic_concatenation.md) | Combine a set of alerts. |
| 01 | [LogID Count Aggregator](alert_aggregators/logid_count.md) | Count how many times a log ID appears in alerts. |
| 02 | [Time Delta](alert_aggregators/time_delta.md) | Group alerts by their time difference. |
| 03 | [AlertBERT](alert_aggregators/alertbert.md) | Group alerts based on timestamps and embeddings. |


### Common parameters (all alert aggregators)

All alert aggregators inherit parameters from `CoreAlertAggregatorConfig`, `CoreConfig`, and `BasicConfig`. Each aggregator’s page explains its specific parameters.

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
    | `use_config_data_as_training` | boolean | True | Reuse configuration records as training data. |
    | `train_buffer_max_records` | integer | 100000 | Configure records kept in memory for training (use_config_data_as_training) before the buffer spills to Parquet files on disk, in parts of this many records. |
    | `train_buffer_dir` | string, null | None | Local directory for the spilled training buffer. None uses the system temp directory (TMPDIR). Each spill goes to a private detectmate-train-* directory, removed after training reads it; a killed process leaves it behind. |
    | `connector_name` | string, null | None | Add a connector to the output schema. |
    | `connector_url` | string, null | None | Set up the URL of the connector for the output schema. |
<!-- End common_arguments -->

### Density Clustering Aggregator

Time Delta and AlertBERT also accept the density clustering parameters below. [Time Delta](alert_aggregators/time_delta.md) · [AlertBERT](alert_aggregators/alertbert.md)

<!-- Start density_clustering_arguments -->
???+ note "params"

    | Field | Type | Default | Description |
    |---|---|---|---|
    | `buffer_size` | integer | 3 | The size of the buffer. |
    | `buffer_mode` | object | BufferMode.BATCH | The mode of the buffer. |
    | `delta` | number | 0.5 | The threshold for the clustering. |
<!-- End density_clustering_arguments -->
