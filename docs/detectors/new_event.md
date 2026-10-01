# New Event Detector

The New Event Detector raises alerts when previously unseen log templates, distinguished by event IDs, appear in log data. It is useful to detect unexpected types of events in the environment.

## In/out

Input and output schemas in the pipeline

|            | Schema                     | Description        |
|------------|----------------------------|--------------------|
| **Input**  | [ParserSchema](../schemas.md) | Structured log  |
| **Output** | [DetectorSchema](../schemas.md) | Alert / finding |

## At a glance

| Learns from training data | Auto-configuration | Needs `events` | Federation |
|---|---|---|---|
| ✅ | ❌ | ❌ | ✅ (binary not available) |

## Description

This detector maintains a lightweight set of observed event IDs and emits an alert when an event ID not present in the set is seen for the first time (subject to configuration).

## Example

```python
--8<-- "docs/examples/detectors/new_event.py:example"
```

## Configuration file

The configuration used by the example above. It sets only what this use case needs; every other parameter keeps its default (see [Configuration arguments](#configuration-arguments)).

```yaml
--8<-- "docs/examples/detectors/new_event.yaml"
```

The same file works unchanged in both places a detector runs:

- **Library**: load it with `yaml.safe_load` and pass the dict as `config=`, as in the example. The key under `detectors:` must match the detector's `name`.
- **[DetectMateService](https://github.com/ait-detectmate/DetectMateService)**: use it as the service's detector configuration.

## Configuration arguments

All parameters this detector accepts, grouped by the YAML block they go in. **Scope** tells whether a parameter is `specific` to this detector or `shared` with other detectors (see the [Detectors overview](../detectors.md#common-parameters-all-detectors)). Where this detector changes a shared default, the shared value is shown in brackets.

<!-- Start arguments -->
??? note "Top level"

    | Field | Type | Default | Scope | Description |
    |---|---|---|---|---|
    | `method_type` | string | new_event_detector | shared | Indicates what type of method it is. |
    | `auto_config` | boolean | True | shared | Runs the configuration step before the training process. |
    | `events` | object | {} | shared | Events configuration dict keyed by event_id. |
    | `global` | object | {} | shared | Instances monitoring event-independent header variables (e.g. hostname, level), keyed by instance name. Written as `global` in YAML. |
    | `persist` | object, null | None | shared | Periodic state saving (path, interval_seconds, events_until_save, auto_load, storage_options). None disables it. See the Persistency page. |

??? note "params"

    | Field | Type | Default | Scope | Description |
    |---|---|---|---|---|
    | `start_id` | integer | 10 | shared | Number used to start the unique ID generator. |
    | `data_use_training` | integer, null | None | shared | Data used for training, if None, training is not done. |
    | `data_use_configure` | integer, null | None | shared | Data used for configuration, if None, configuration is not done. |
    | `use_config_data_as_training` | boolean | True | shared | Combine the configured data in the training process if True. |
    | `train_buffer_max_records` | integer | 100000 | shared | Configure records kept in memory for training (use_config_data_as_training) before the buffer spills to Parquet files on disk, in parts of this many records. |
    | `train_buffer_dir` | string, null | None | shared | fsspec URI for the spilled training buffer. None uses a private per-user directory in the system temp directory. Files left by killed processes are removed automatically on local disk only. |
    | `parser` | string | PARSER | shared | Name of the parser used. |
<!-- End arguments -->
