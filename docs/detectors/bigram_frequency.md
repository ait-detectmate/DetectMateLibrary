# Bigram Frequency Detector

The Bigram Frequency Detector raises alerts when a variable's character bigrams (pairs of neighbouring letters/characters) appear improbable under a learned per-variable bigram frequency model. Optionally, an English-language bigram table can be consulted as a fallback for bigrams not yet seen during training.

## In/out

Input and output schemas in the pipeline

|            | Schema                     | Description        |
|------------|----------------------------|--------------------|
| **Input**  | [ParserSchema](../schemas.md) | Structured log  |
| **Output** | [DetectorSchema](../schemas.md) | Alert / finding |

## At a glance

| Learns from training data | Auto-configuration | Needs `events` | Federation |
|---|---|---|---|
| ✅ | ✅ picks the variables to monitor | ✅ unless `auto_config: true` | ✅ (binary not available) |

## Description

For each configured variable, the detector walks every observed value character-by-character (with virtual boundary characters before the first and after the last) and updates a per-(event, variable) bigram frequency table. At detect time, the average per-bigram conditional probability of a new value is computed against this table. Values scoring below `prob_thresh` are flagged. When `default_freqs` is enabled, a built-in English bigram table acts as a fallback for bigrams unseen during training.

## Example

```python
--8<-- "docs/examples/detectors/bigram_frequency.py:example"
```

## Configuration file

The configuration used by the example above. It sets only what this use case needs; every other parameter keeps its default (see [Configuration arguments](#configuration-arguments)).

```yaml
--8<-- "docs/examples/detectors/bigram_frequency.yaml"
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
    | `method_type` | string | bigram_frequency_detector | shared | Indicates what type of method it is. |
    | `auto_config` | boolean | True | shared | Runs the configuration step before the training process. |
    | `events` | object | {} | shared | Events configuration dict keyed by event_id. |
    | `global` | object | {} | shared | Instances monitoring event-independent header variables (e.g. hostname, level), keyed by instance name. Written as `global` in YAML. |
    | `persist` | object, null | None | shared | Periodic state saving (path, interval_seconds, events_until_save, auto_load, storage_options). None disables it. See the Persistency page. |

???+ note "params"

    | Field | Type | Default | Scope | Description |
    |---|---|---|---|---|
    | `prob_thresh` | number | 0.05 | specific | Limit for the average probability of character pairs below which anomalies are reported. |
    | `default_freqs` | boolean | False | specific | Initialize the probabilities with default values from https://github.com/markbaggett/freq. |
    | `skip_repetitions` | boolean | True | specific | Only use distinct values for character-pair counting. This counteracts the problem of imbalanced word frequencies that distort the frequency table generated in a single run. |
    | `start_id` | integer | 10 | shared | Number used to start the unique ID generator. |
    | `data_use_training` | integer, null | None | shared | Data used for training, if None, training is not done. |
    | `data_use_configure` | integer, null | None | shared | Data used for configuration, if None, configuration is not done. |
    | `use_config_data_as_training` | boolean | True | shared | Combine the configured data in the training process if True. |
    | `train_buffer_max_records` | integer | 100000 | shared | Configure records kept in memory for training (use_config_data_as_training) before the buffer spills to Parquet files on disk, in parts of this many records. |
    | `train_buffer_dir` | string, null | None | shared | Local directory for the spilled training buffer. None uses the system temp directory (TMPDIR). Each spill goes to a private detectmate-train-* directory, removed after training reads it; a killed process leaves it behind. |
    | `parser` | string | PARSER | shared | Name of the parser used. |
    | `allow_fed` | boolean | False | shared | Allow to do the federation |

??? note "auto_config_params (read only while auto_config is true)"

    | Field | Type | Default | Scope | Description |
    |---|---|---|---|---|
    | `classification.index` | boolean | True | shared | Segment-mean test over equal-count segments. |
    | `classification.time` | boolean | False | shared | Segment-mean test over equal-duration segments. Needs timestamp_variable. |
    | `classification.segment_thresholds` | array | [1.1, 0.3, 0.1, 0.01] | shared | Upper bound on the mean change rate, one per segment; the list length is the segment count. Used by index and time. |
    | `classification.slope_index` | boolean | False | shared | Change-centroid test on the index axis. |
    | `classification.slope_time` | boolean | False | shared | Change-centroid test on the time axis. Needs timestamp_variable. |
    | `classification.slope_threshold` | number | -0.05 | shared | A variable is STABLE when its change centroid (-0.5 to +0.5) is at or below this. Used by slope_index and slope_time. |
    | `classification.decision` | string | consensus | shared | How the enabled methods' verdicts combine: consensus needs all of them, majority needs more than half. |
    | `timestamp_variable` | string, null | None | shared | Header variable (from the parser's log_format) holding each event's time. Required by the time and slope_time classification methods. |
    | `timestamp_format` | string, null | None | shared | Format of timestamp_variable. None detects it automatically. |
    | `use_stable_vars` | boolean | True | shared | Monitor the variables the configure phase classifies as STABLE. |
    | `use_static_vars` | boolean | True | shared | Monitor the variables the configure phase classifies as STATIC (a single value). |
<!-- End arguments -->
