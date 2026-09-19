# Event Sequence Detector

The Event Sequence Detector raises alerts when a run of consecutive event IDs appears in an order that was never observed during training. It is useful to detect broken or unexpected workflows in an environment where the individual events are all benign on their own.

## In/out

Input and output schemas in the pipeline

|            | Schema                     | Description        |
|------------|----------------------------|--------------------|
| **Input**  | [ParserSchema](../schemas.md) | Structured log  |
| **Output** | [DetectorSchema](../schemas.md) | Alert / finding |

## Description

The detector slides a window of `fixed_window_size` event IDs over the log stream. During training every full window is stored as a known sequence; during detection a window whose exact sequence is not in that set is reported as an anomaly.

Because a novel event stays inside the window for `fixed_window_size` steps, a single unexpected event produces up to `fixed_window_size` consecutive alerts  --  one per window it invalidates. This is intentional: each of those windows is a distinct sequence that was never trained.

Sequences are stored as fixed-length n-grams, so a persisted model is only meaningful at the length it was trained with. When state is restored via [persistency](../auxiliar/persistency.md) at a different `fixed_window_size`, the detector logs a warning, adopts the persisted length, and skips auto-configuration.

### Auto configuration

With `auto_config: True` the detector spends the configure phase feeding one window per candidate length in `min_window_size .. max_window_size` (inclusive) and tracking how stable the resulting sequences are. The longest candidate whose sequences are classified `STABLE` or `STATIC` is written to `fixed_window_size`, so the resulting configuration can be replayed verbatim with `auto_config: False`.

Candidates whose window never filled during the configure phase are skipped, so a short configure phase simply narrows the choice.

If no candidate is stable, no window length is meaningful for this log stream. Rather than fall back to an arbitrary length and alert on nearly every window, the detector generates an empty configuration: **no instance of the detector is created**, `fixed_window_size` stays `None`, and it neither trains nor alerts for the rest of the run. A warning names the range that was searched. The same applies to `auto_config: False` without a `fixed_window_size`  --  the detector stays inert.

Longer windows are more specific and therefore alert more readily; if the auto-configured length is too sensitive, narrow the range or set `fixed_window_size` explicitly.

## Configuration arguments

Only parameters specific to this detector are listed below -- see [Common parameters](../detectors.md#common-parameters-all-detectors) in the Detectors overview for the rest.

<!-- Start arguments -->
| Field  | Type  | Default Value| Description|
|-------|------|-----|---|
|method_type|string|event_sequence_detector|Indicates what type of method it is.|
|min_window_size|integer|2|Shortest window length tried during the auto-configuration phase. Only used while fixed_window_size is None.|
|max_window_size|integer|10|Longest window length tried during the auto-configuration phase. The longest length whose sequences are classified STABLE or STATIC wins.|
|fixed_window_size|integer, null|None|Length of the sliding EventID window. A window whose exact EventID sequence was not seen during training is reported as an anomaly. When set it overrides min_window_size/max_window_size and skips auto-configuration; auto-configuration writes its own choice here. While it is None the detector is unconfigured and neither trains nor alerts.|
<!-- End arguments -->

## Examples
### Service usage

To use it in [DetectMateService](https://github.com/ait-detectmate/DetectMateService), you can use the example below.

<!-- Start config -->
```yaml
detectors:
    <COMPONENT_NAME>:
        method_type: event_sequence_detector
        auto_config: true
        params:
            start_id: 10
            data_use_training: null
            data_use_configure: null
            use_config_data_as_training: true
            parser: PARSER
            global_instances: {}
            min_window_size: 2
            max_window_size: 10
            fixed_window_size: null
        events: {}
```
<!-- End config -->
### Library usage
To use it as a python script, you can follow the example below.

```python
--8<-- "docs/examples/detectors/event_sequence.py:example"
```

The sequences learned so far are available via `detector.get_known_sequences()`, which returns a set of event-ID tuples.

Go back [Index](../index.md)
