# Basic Concat Alert Aggregation

The Basic Concat alert aggregation combines the most recent alerts into one aggregated record by
concatenating their IDs and timestamps.

## In/out

Input and output schemas in the pipeline

## In/out

|            | Schema                     | Description        |
|------------|----------------------------|--------------------|
| **Input**  | [DetectorSchema](../schemas.md)    | Alerts from detectors  |
| **Output** | [AggregateSchema](../schemas.md) | Aggregated alerts    |

## Description

The aggregator keeps a sliding window of the last `buffer_size` alerts. The first aggregated record
is emitted once the window is full, and then one record for every new alert, so consecutive records
overlap. Alerts are combined in the order they arrive, not grouped by log, and the alerts' own
messages are not carried over (see [What `run()` fills in for you](../alert_aggregator.md#what-run-fills-in-for-you)).
The [tutorial](../user_guide/tutorial.md#4-add-an-alert-aggregator) shows the overlapping output.

## At a glance

| Learns from training data | Auto-configuration | Needs `events` | Federation |
|---|---|---|---|
| ❌ | ❌ | ❌ | ❌ |


## Example

```python
--8<-- "docs/examples/alert_aggregators/basic_concat.py:example_1"
```

## Configuration file

The configuration used by the example above. It sets only what this use case needs; every other parameter keeps its default (see [Configuration arguments](#configuration-arguments)).

```yaml
--8<-- "docs/examples/alert_aggregators/basic_concat.yaml"
```

Load it with `yaml.safe_load` and pass the dict as `config=`, as in the example. The key under `alert_aggregators:` must match the aggregator's `name`.

## Configuration arguments

All parameters this alert aggregator accepts, grouped by the YAML block they go in. **Scope** tells whether a parameter is `specific` to this aggregator or `shared` with other alert aggregators.

<!-- Start arguments -->
??? note "Top level"

    | Field | Type | Default | Scope | Description |
    |---|---|---|---|---|
    | `method_type` | string | basic_concat_aggregator | shared | Indicates what type of method it is. |
    | `auto_config` | boolean | False | shared | Runs the configuration step before the training process. |

???+ note "params"

    | Field | Type | Default | Scope | Description |
    |---|---|---|---|---|
    | `buffer_size` | integer | 3 | specific | Buffer size use in the aggregation. |
    | `start_id` | integer | 10 | shared | Number used to start the unique ID generator. |
    | `data_use_training` | integer, null | None | shared | Number of logs used for training. None skips training. |
    | `data_use_configure` | integer, null | None | shared | Number of logs used for the configuration step. None skips it. |
    | `use_config_data_as_training` | boolean | True | shared | Combine the configured data in the training process if True. |
    | `train_buffer_max_records` | integer | 100000 | shared | Configure records kept in memory for training (use_config_data_as_training) before the buffer spills to Parquet files on disk, in parts of this many records. |
    | `train_buffer_dir` | string, null | None | shared | Local directory for the spilled training buffer. None uses the system temp directory (TMPDIR). Each spill goes to a private detectmate-train-* directory, removed after training reads it; a killed process leaves it behind. |
<!-- End arguments -->
