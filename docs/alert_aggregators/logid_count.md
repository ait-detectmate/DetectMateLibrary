# LogID Count Alert Aggregation

The logID count alert aggregation tracks how many times each log ID appears in the alerts, and if it exceeds a specified threshold, it triggers the aggregation.

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

A log ID counter stores, in a fixed-size table, the counts for different log IDs. If the count for any log ID from the Detector Schemas exceeds a defined threshold, it returns an alert aggregation.

The fixed-size table operates as a FIFO: once it is full, it removes the oldest entry and inserts the new log ID.
## Example

```python
--8<-- "docs/examples/alert_aggregators/logid_count.py:example_1"
```

## Configuration file

The configuration used by the example above. It sets only what this use case needs; every other parameter keeps its default (see [Configuration arguments](#configuration-arguments)).

```yaml
--8<-- "docs/examples/alert_aggregators/logid_count.yaml"
```

## Configuration arguments

All parameters this detector accepts, grouped by the YAML block they go in. **Scope** tells whether a parameter is `specific` to this detector or `shared` with other detectors (see the [Alert Aggregation overview](../alert_aggregator.md#common-parameters-all-alert-aggregators)). Where this detector changes a shared default, the shared value is shown in brackets.

<!-- Start arguments -->
??? note "Top level"

    | Field | Type | Default | Scope | Description |
    |---|---|---|---|---|
    | `method_type` | string | logid_count_aggregator | shared | Indicates what type of method it is. |
    | `auto_config` | boolean | False | shared | Runs the configuration step before the training process. |

???+ note "params"

    | Field | Type | Default | Scope | Description |
    |---|---|---|---|---|
    | `max_count` | integer | 4 | specific | Max count of alerts in a specific logID. |
    | `max_memory` | integer | 5000 | specific | Max number of logIDs store in the count memory. |
    | `start_id` | integer | 10 | shared | Number used to start the unique ID generator. |
    | `data_use_training` | integer, null | None | shared | Number of logs used for training. None skips training. |
    | `data_use_configure` | integer, null | None | shared | Number of logs used for the configuration step. None skips it. |
    | `use_config_data_as_training` | boolean | True | shared | Combine the configured data in the training process if True. |
    | `train_buffer_max_records` | integer | 100000 | shared | Configure records kept in memory for training (use_config_data_as_training) before the buffer spills to Parquet files on disk, in parts of this many records. |
    | `train_buffer_dir` | string, null | None | shared | Local directory for the spilled training buffer. None uses the system temp directory (TMPDIR). Each spill goes to a private detectmate-train-* directory, removed after training reads it; a killed process leaves it behind. |
    | `connector_name` | string, null | None | shared | No description provided. |
    | `connector_url` | string, null | None | shared | Setup the url of the connector in the output schema. |
<!-- End arguments -->
