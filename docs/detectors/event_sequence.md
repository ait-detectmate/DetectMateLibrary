# Event Sequence Detector

The Event Sequence Detector raises alerts when a run of consecutive event IDs appears in an order that was never observed during training. It is useful to detect broken or unexpected workflows in an environment where the individual events are all benign on their own.

|            | Schema                     | Description        |
|------------|----------------------------|--------------------|
| **Input**  | [ParserSchema](../schemas.md) | Structured log  |
| **Output** | [DetectorSchema](../schemas.md) | Alert / finding |

## Description

The detector slides a window of `fixed_window_size` event IDs over the log stream. During training every full window is stored as a known sequence; during detection a window whose exact sequence is not in that set is reported as an anomaly.

Because a novel event stays inside the window for `fixed_window_size` steps, a single unexpected event produces up to `fixed_window_size` consecutive alerts — one per window it invalidates. This is intentional: each of those windows is a distinct sequence that was never trained.

Sequences are stored as fixed-length n-grams, so a persisted model is only meaningful at the length it was trained with. When state is restored via [persistency](../auxiliar/persistency.md) at a different `fixed_window_size`, the detector logs a warning, adopts the persisted length, and skips auto-configuration.

## Auto configuration

With `auto_config: True` the detector spends the configure phase feeding one window per candidate length in `min_window_size .. max_window_size` (inclusive) and tracking how stable the resulting sequences are. The longest candidate whose sequences are classified `STABLE` or `STATIC` is written to `fixed_window_size`, so the resulting configuration can be replayed verbatim with `auto_config: False`.

Candidates whose window never filled during the configure phase are skipped, so a short configure phase simply narrows the choice.

If no candidate is stable, no window length is meaningful for this log stream. Rather than fall back to an arbitrary length and alert on nearly every window, the detector generates an empty configuration: **no instance of the detector is created**, `fixed_window_size` stays `None`, and it neither trains nor alerts for the rest of the run. A warning names the range that was searched. The same applies to `auto_config: False` without a `fixed_window_size` — the detector stays inert.

Longer windows are more specific and therefore alert more readily; if the auto-configured length is too sensitive, narrow the range or set `fixed_window_size` explicitly.

## Configuration example

```yaml
detectors:
    EventSequenceDetector:
        method_type: event_sequence_detector
        auto_config: False
        params:
            fixed_window_size: 3
```

With auto configuration:

```yaml
detectors:
    EventSequenceDetector:
        method_type: event_sequence_detector
        auto_config: True
        data_use_configure: 500
        params:
            min_window_size: 2
            max_window_size: 10
```

| Parameter | Default | Description |
|---|---|---|
| `fixed_window_size` | `None` | Length of the sliding event-ID window. Overrides `min_window_size`/`max_window_size` and skips auto configuration. Auto configuration writes its own choice here. While it is `None` the detector neither trains nor alerts. Must be `>= 1`. |
| `min_window_size` | `2` | Shortest window length tried during auto configuration. Must be `>= 1`. |
| `max_window_size` | `10` | Longest window length tried during auto configuration. Must be `>= min_window_size`. |

## Example usage

```python
from detectmatelibrary.detectors.event_sequence_detector import EventSequenceDetector, \
    EventSequenceDetectorConfig
import detectmatelibrary.schemas as schemas

detector = EventSequenceDetector(
    name="EventSequenceTest",
    config=EventSequenceDetectorConfig(auto_config=False, fixed_window_size=3),
)

parser_data = schemas.ParserSchema({
    "parserType": "test",
    "EventID": 1,
    "template": "test template",
    "variables": ["var1"],
    "logID": "1",
    "parsedLogID": "1",
    "parserID": "test_parser",
    "log": "test log message",
    "logFormatVariables": {"timestamp": "123456"}
})


alert = detector.process(parser_data)
```

The sequences learned so far are available via `detector.get_known_sequences()`, which returns a set of event-ID tuples.

Go back [Index](../index.md)
