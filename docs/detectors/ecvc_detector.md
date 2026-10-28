# ECVC Detector

The Event Count Vector Clustering Detector (ECVC) detects anomalies by calculating the distance between the count vectors from training and new ones. The method can be found in [this publication](https://dl.acm.org/doi/10.1145/3660768).

## In/out

Input and output schemas in the pipeline

|            | Schema                     | Description        |
|------------|----------------------------|--------------------|
| **Input**  | [ParserSchema](../schemas.md) | Structured log  |
| **Output** | [DetectorSchema](../schemas.md) | Alert / finding |

## At a glance

| Learns from training data | Auto-configuration | Needs `events` | Federation |
|---|---|---|---|
| ✅ | ✅ picks the window length | ❌ | ✅ |

## Description

A count vector is formed by counting the number of appearances of each event ID in a sequence of a specific window size.

The detector slides a window of `fixed_window_size` consecutive logs over the stream. During training it stores the count vector of every full window; during detection it scores each window by the distance of its count vector to the closest learned one and alerts when that distance exceeds the threshold derived from the validation split. An alert's `logIDs` lists every log in the window. With a window size of k, the first k − 1 logs that reach detection cannot alert, because their window is not full yet.

Count vectors learned during training are stored via [persistency](../auxiliar/persistency.md), so a trained model can be saved and restored with a `persist:` block. A count vector is only comparable within the window it was counted over, so restored state adopts its persisted window size (with a warning when it differs from `fixed_window_size`) and skips auto-configuration. State that mixes window sizes, for example merged from nodes that chose different sizes, has no valid size and raises an error.

Few distinct count vectors leave the validation split empty (at the default `validation_per` of 0.2, four or fewer). The threshold then stays at 0, so any window whose count vector was not learned alerts, and the detector logs a warning.

The count vectors detection scores against are built when the training phase ends. A configure phase without a training phase (`data_use_configure` set, `data_use_training` not) therefore learns no count vectors from training: the detector logs a warning when it is built and does not alert unless learned state is restored (`auto_load`, `import_state` or federation). The same holds when training ends before a single window filled, for example `data_use_training: 3` with `fixed_window_size: 5`; the detector then logs a warning when training ends.

### Auto configuration

With `auto_config: True` the detector spends the configure phase feeding one window per candidate size in `min_window_size .. max_window_size` (inclusive) and tracking how stable the count vectors of those windows are. The longest candidate whose count vectors are classified `STABLE` or `STATIC` is written to `fixed_window_size`, so the resulting configuration can be replayed verbatim with `auto_config: False`. With `use_config_data_as_training` (the default), the configure logs are then trained at the chosen size.

Candidates whose window never filled during the configure phase, or filled too few times to classify, are skipped, so a short configure phase simply narrows the choice.

If no candidate is stable, no window size is meaningful for this log stream. Rather than fall back to an arbitrary size and alert on nearly every window, the detector generates an empty configuration: **no instance of the detector is created**, `fixed_window_size` stays `None`, and it neither trains nor alerts for the rest of the run. A warning names the range that was searched. The same applies to `auto_config: False` without a `fixed_window_size`: the detector stays inert.

To let the detector pick the window size, give it a configure phase and a training phase instead of a `fixed_window_size`:

```yaml
detectors:
  ECVCDetector:
    method_type: ecvc_detector
    auto_config: true
    params:
      data_use_configure: 200   # logs used to choose the window size
      data_use_training: 1000   # logs used to learn the count vectors afterwards
```

`window_size`, the name `fixed_window_size` had before auto-configuration, is still accepted as a deprecated alias: it loads as `fixed_window_size` with a `DeprecationWarning`. Setting both is an error.

!!! note "Upgrading from `window_size`"
    `data_use_training` and `data_use_configure` now count logs, not windows: at window size k, a training phase of N logs counts N − k + 1 windows, and none when N < k. The default window size is now `None` instead of 10, so a configuration with neither a `fixed_window_size` nor a configure phase is inert: the detector neither trains nor alerts, and warns once.

## Example

```python
--8<-- "docs/examples/detectors/ecvc_detector.py:example"
```

## Configuration file

The configuration used by the example above. It sets only what this use case needs; every other parameter keeps its default (see [Configuration arguments](#configuration-arguments)).

```yaml
--8<-- "docs/examples/detectors/ecvc_detector.yaml"
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
    | `method_type` | string | ecvc_detector | shared | Indicates what type of method it is. |
    | `auto_config` | boolean | True | shared | Runs the configuration step before the training process. Has no effect unless data_use_configure is set. |
    | `events` | object | {} | shared | Events configuration dict keyed by event_id. |
    | `global` | object | {} | shared | Instances monitoring event-independent header variables (e.g. hostname, level), keyed by instance name. Written as `global` in YAML. |
    | `persist` | object, null | None | shared | Periodic state saving (path, interval_seconds, events_until_save, auto_load, storage_options). None disables it. See Saving state (persist) on the Detectors page. |

???+ note "params"

    | Field | Type | Default | Scope | Description |
    |---|---|---|---|---|
    | `fixed_window_size` | integer, null | None | specific | Length of the window of consecutive logs a count vector is built over. When set it overrides the `auto_config_params` window range and skips auto-configuration; auto-configuration writes its own choice here. While it is None the detector is unconfigured and neither trains nor alerts. |
    | `validation_per` | number | 0.2 | specific | Fraction of the learned count vectors held out as a validation split and used to derive the anomaly threshold. |
    | `seed` | integer | 0 | specific | Random seed used to shuffle count vectors into train/validation splits. |
    | `threshold_method` | string | mean | specific | Method used to derive the anomaly threshold from the validation split: 'mean' averages the distance scores, 'default' uses a fixed threshold of 0. |
    | `start_id` | integer | 10 | shared | Number used to start the unique ID generator. |
    | `data_use_training` | integer, null | None | shared | Number of logs used for training. None skips training. |
    | `data_use_configure` | integer, null | None | shared | Number of logs used for the configuration step. None skips it. |
    | `use_config_data_as_training` | boolean | True | shared | Combine the configured data in the training process if True. |
    | `train_buffer_max_records` | integer | 100000 | shared | Configure records kept in memory for training (use_config_data_as_training) before the buffer spills to Parquet files on disk, in parts of this many records. |
    | `train_buffer_dir` | string, null | None | shared | Local directory for the spilled training buffer. None uses the system temp directory (TMPDIR). Each spill goes to a private detectmate-train-* directory, removed after training reads it; a killed process leaves it behind. |
    | `parser` | string | PARSER | shared | Name of the parser used. |
    | `allow_fed` | boolean | False | shared | Builds the stores needed to take part in federation. |

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
