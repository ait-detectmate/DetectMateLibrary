# Event Sequence Detector

The Event Sequence Detector raises alerts when a run of consecutive event IDs appears in an order that was never observed during training. It is useful to detect broken or unexpected workflows in an environment where the individual events are all benign on their own.

## In/out

Input and output schemas in the pipeline

|            | Schema                     | Description        |
|------------|----------------------------|--------------------|
| **Input**  | [ParserSchema](../schemas.md) | Structured log  |
| **Output** | [DetectorSchema](../schemas.md) | Alert / finding |

## At a glance

| Learns from training data | Auto-configuration | Needs `events` | Federation |
|---|---|---|---|
| ✅ | ✅ picks the window length | ❌ | ✅ (binary not available) |

## Description

The detector slides a window of `fixed_window_size` event IDs over the log stream. During training every full window is stored as a known sequence; during detection a window whose exact sequence is not in that set is reported as an anomaly.

Because a novel event stays inside the window for `fixed_window_size` steps, a single unexpected event produces up to `fixed_window_size` consecutive alerts  --  one per window it invalidates. This is intentional: each of those windows is a distinct sequence that was never trained.

Sequences are stored as fixed-length n-grams, so a persisted model is only meaningful at the length it was trained with. When state is restored via [persistency](../auxiliar/persistency.md) at a different `fixed_window_size`, the detector logs a warning, adopts the persisted length, and skips auto-configuration.

### Auto configuration

With `auto_config: True` the detector spends the configure phase feeding one window per candidate length in `min_window_size .. max_window_size` (inclusive) and tracking how stable the resulting sequences are. The longest candidate whose sequences are classified `STABLE` or `STATIC` is written to `fixed_window_size`, so the resulting configuration can be replayed verbatim with `auto_config: False`.

Candidates whose window never filled during the configure phase are skipped, so a short configure phase simply narrows the choice.

If no candidate is stable, no window length is meaningful for this log stream. Rather than fall back to an arbitrary length and alert on nearly every window, the detector generates an empty configuration: **no instance of the detector is created**, `fixed_window_size` stays `None`, and it neither trains nor alerts for the rest of the run. A warning names the range that was searched. The same applies to `auto_config: False` without a `fixed_window_size`  --  the detector stays inert.

Longer windows are more specific and therefore alert more readily; if the auto-configured length is too sensitive, narrow the range or set `fixed_window_size` explicitly.

To let the detector pick the window length, give it a configure phase instead of a `fixed_window_size`:

```yaml
detectors:
  LoginSequenceDetector:
    method_type: event_sequence_detector
    auto_config: true
    params:
      data_use_configure: 200   # logs used to choose the window length
      data_use_training: 1000   # logs used to learn the sequences afterwards
```

## Example

```python
--8<-- "docs/examples/detectors/event_sequence.py:example"
```

The sequences learned so far are available via `detector.get_known_sequences()`, which returns a set of event-ID tuples.

## Configuration file

The configuration used by the example above. It sets only what this use case needs; every other parameter keeps its default (see [Configuration arguments](#configuration-arguments)).

```yaml
--8<-- "docs/examples/detectors/event_sequence.yaml"
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
    | `method_type` | string | event_sequence_detector | shared | Indicates what type of method it is. |
    | `auto_config` | boolean | True | shared | Runs the configuration step before the training process. |
    | `events` | object | {} | shared | Events configuration dict keyed by event_id. |
    | `global` | object | {} | shared | Instances monitoring event-independent header variables (e.g. hostname, level), keyed by instance name. Written as `global` in YAML. |
    | `persist` | object, null | None | shared | Periodic state saving (path, interval_seconds, events_until_save, auto_load, storage_options). None disables it. See the Persistency page. |

???+ note "params"

    | Field | Type | Default | Scope | Description |
    |---|---|---|---|---|
    | `fixed_window_size` | integer, null | None | specific | Length of the sliding EventID window. A window whose exact EventID sequence was not seen during training is reported as an anomaly. When set it overrides the `auto_config_params` window range and skips auto-configuration; auto-configuration writes its own choice here. While it is None the detector is unconfigured and neither trains nor alerts. |
    | `start_id` | integer | 10 | shared | Number used to start the unique ID generator. |
    | `data_use_training` | integer, null | None | shared | Data used for training, if None, training is not done. |
    | `data_use_configure` | integer, null | None | shared | Data used for configuration, if None, configuration is not done. |
    | `use_config_data_as_training` | boolean | True | shared | Combine the configured data in the training process if True. |
    | `train_buffer_max_records` | integer | 100000 | shared | Configure records kept in memory for training (use_config_data_as_training) before the buffer spills to Parquet files on disk, in parts of this many records. |
    | `train_buffer_dir` | string, null | None | shared | fsspec URI for the spilled training buffer. None uses a private per-user directory in the system temp directory. Files left by killed processes are removed automatically on local disk only. |
    | `parser` | string | PARSER | shared | Name of the parser used. |

??? note "auto_config_params (read only while auto_config is true)"

    | Field | Type | Default | Scope | Description |
    |---|---|---|---|---|
    | `classification.index` | boolean | True | specific | Segment-mean test over equal-count segments. |
    | `classification.time` | boolean | False | specific | Segment-mean test over equal-duration segments. Needs timestamp_variable. |
    | `classification.segment_thresholds` | array | [1.1, 0.3, 0.1, 0.01] | specific | Upper bound on the mean change rate, one per segment; the list length is the segment count. Used by index and time. |
    | `classification.slope_index` | boolean | False | specific | Change-centroid test on the index axis. |
    | `classification.slope_time` | boolean | False | specific | Change-centroid test on the time axis. Needs timestamp_variable. |
    | `classification.slope_threshold` | number | -0.05 | specific | A variable is STABLE when its change centroid (-0.5 to +0.5) is at or below this. Used by slope_index and slope_time. |
    | `classification.decision` | string | consensus | specific | How the enabled methods' verdicts combine: consensus needs all of them, majority needs more than half. |
    | `timestamp_variable` | string, null | None | specific | Header variable (from the parser's log_format) holding each event's time. Required by the time and slope_time classification methods. |
    | `timestamp_format` | string, null | None | specific | Format of timestamp_variable. None detects it automatically. |
    | `min_window_size` | integer | 2 | specific | Shortest window length tried by the configure phase. Must be >= 1. |
    | `max_window_size` | integer | 10 | specific | Longest window length tried by the configure phase; the longest length whose sequences are STABLE or STATIC wins. Must be >= min_window_size. |
<!-- End arguments -->
