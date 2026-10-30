# Time Delta Alert Aggregation

The time-delta alert aggregator implements alert aggregation by grouping alerts according their time-difference as proposed by [Landauer et al.](https://dl.acm.org/doi/pdf/10.1145/3510581).

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

This class implements alert aggregation by considering the differences between the timestamps of alerts.

Two alerts will be assigned to the same group if the time difference between them is below a certain threshold delta.
The time difference is computed based on the timestamps of the last logs associated with each alert as these determine the earliest time at which the alert was detected.
Important: It is assumed that the alerts arrive in order of their timestamps!

## Example

```python
--8<-- "docs/examples/alert_aggregators/time_delta.py:example_1"
```

## Configuration file

The configuration used by the example above. It sets only what this use case needs; every other parameter keeps its default (see [Configuration arguments](#configuration-arguments)).

```yaml
--8<-- "docs/examples/alert_aggregators/time_delta.yaml"
```

Load it with `yaml.safe_load` and pass the dict as `config=`, as in the example. The key under `alert_aggregators:` must match the aggregator's `name`.

## Configuration arguments

All parameters this alert aggregator accepts, grouped by the YAML block they go in. **Scope** tells whether a parameter is `specific` to this aggregator or `shared` with other alert aggregators.

<!-- Start arguments -->
??? note "Top level"

    | Field | Type | Default | Scope | Description |
    |---|---|---|---|---|
    | `method_type` | string | time_delta_aggregator | shared | The kind of aggregation method. |
    | `auto_config` | boolean | False | shared | Runs the configuration step before the training process. |

???+ note "params"

    | Field | Type | Default | Scope | Description |
    |---|---|---|---|---|
    | `buffer_size` | integer | 3 | specific | The size of the buffer. |
    | `buffer_mode` | object | BufferMode.BATCH | specific | The mode of the buffer. |
    | `delta` | number | 10.0 | specific | The threshold for the clustering. |
    | `start_id` | integer | 10 | shared | Number used to start the unique ID generator. |
    | `data_use_training` | integer, null | None | shared | Number of logs used for training. None skips training. |
    | `data_use_configure` | integer, null | None | shared | Number of logs used for the configuration step. None skips it. |
    | `use_config_data_as_training` | boolean | True | shared | Combine the configured data in the training process if True. |
    | `train_buffer_max_records` | integer | 100000 | shared | Configure records kept in memory for training (use_config_data_as_training) before the buffer spills to Parquet files on disk, in parts of this many records. |
    | `train_buffer_dir` | string, null | None | shared | Local directory for the spilled training buffer. None uses the system temp directory (TMPDIR). Each spill goes to a private detectmate-train-* directory, removed after training reads it; a killed process leaves it behind. |
    | `connector_name` | string, null | None | shared | Add a connector in the output schema. |
    | `connector_url` | string, null | None | shared | Setup the url of the connector in the output schema. |
<!-- End arguments -->
