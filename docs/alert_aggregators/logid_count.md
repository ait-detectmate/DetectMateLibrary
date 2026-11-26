# LogID Count Alert Aggregation [[Code](https://github.com/ait-detectmate/DetectMateLibrary/blob/main/src/detectmatelibrary/alert_aggregation/logid_count.py)]

The LogID Count aggregator counts occurrences of each log ID across alerts. It emits an aggregated record when a log ID reaches the configured threshold.

## In/out

|            | Schema                     | Description        |
|------------|----------------------------|--------------------|
| **Input**  | [DetectorSchema](../schemas.md)    | Alerts from detectors  |
| **Output** | [AggregateSchema](../schemas.md) | Aggregated alerts    |

## At a glance

| Learns from training data | Auto-configuration | Needs `events` | Federation |
|---|---|---|---|
| ❌ | ❌ | ❌ | ❌ |

## Description

A fixed-size table stores the count for each log ID. When the table is full, a new log ID replaces the oldest entry.

## Example

```python title="Example"
--8<-- "docs/examples/alert_aggregators/logid_count.py:example_1"
```

## Configuration file

The configuration used by the example above. It sets only what this use case needs; every other parameter keeps its default (see [Configuration arguments](#configuration-arguments)).

```yaml title="Configuration"
--8<-- "docs/examples/alert_aggregators/logid_count.yaml"
```

## Configuration arguments

Parameters are grouped by YAML block. **Scope** indicates whether a parameter is specific to this aggregator or shared with other aggregators. When a shared default is overridden, the base default appears in parentheses. [Shared parameters](../alert_aggregator.md#common-parameters-all-alert-aggregators)

<!-- Start arguments -->
??? note "Top level"

    | Field | Type | Default | Scope | Description |
    |---|---|---|---|---|
    | `method_type` | string | logid_count_aggregator | shared | Indicates what type of method it is. |
    | `auto_config` | boolean | False | shared | Runs the configuration step before the training process. |

???+ note "params"

    | Field | Type | Default | Scope | Description |
    |---|---|---|---|---|
    | `max_count` | integer | 4 | specific | Alert count threshold for a log ID. |
    | `max_memory` | integer | 5000 | specific | Maximum number of log IDs tracked at once. |
    | `start_id` | integer | 10 | shared | Number used to start the unique ID generator. |
    | `data_use_training` | integer, null | None | shared | Number of logs used for training. None skips training. |
    | `data_use_configure` | integer, null | None | shared | Number of logs used for the configuration step. None skips it. |
    | `use_config_data_as_training` | boolean | True | shared | Reuse configuration records as training data. |
    | `train_buffer_max_records` | integer | 100000 | shared | Configure records kept in memory for training (use_config_data_as_training) before the buffer spills to Parquet files on disk, in parts of this many records. |
    | `train_buffer_dir` | string, null | None | shared | Local directory for the spilled training buffer. None uses the system temp directory (TMPDIR). Each spill goes to a private detectmate-train-* directory, removed after training reads it; a killed process leaves it behind. |
    | `connector_name` | string, null | None | shared | Add a connector to the output schema. |
    | `connector_url` | string, null | None | shared | Set up the URL of the connector for the output schema. |
<!-- End arguments -->
